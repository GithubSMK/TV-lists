# -*- coding: utf-8 -*-
"""
TV-lists Akıllı IPTV Kanal Düzenleyici ve M3U8 Üretici
Hedef Depo: https://github.com/GithubSMK/TV-lists
"""

import os
import sys
import time
import uuid
import re
from collections import defaultdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import requests

# Terminal çıktıları için UTF-8 yapılandırması
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)

# ==============================================================================
# 1. YAPILANDIRMA: ALAN ADLARI VE YEDEK HAVUZU (MIRROR POOL)
# ==============================================================================
# Sitelerin kapanması veya yenilerinin açılması durumunda buradaki listeyi
# kolayca güncelleyebilirsiniz. Kod otomatik olarak ilk çalışan sunucuyu bulur.
# İleride yeni bir domain açılırsa buraya tek satır eklemeniz yeterlidir:
MIRROR_DOMAINS = [
    "kool.ws",
    "geil.to",
    "voltop.net",
    "kool.to",
    "vavoo.net"
]

# Ortam değişkeni desteği (İsteğe bağlı: GitHub Actions veya yerel env üzerinden geçersiz kılmak için)
# Örn: TV_MIRROR_DOMAINS="kool.ws,geil.to,voltop.net"
if os.environ.get("TV_MIRROR_DOMAINS"):
    custom_domains = [d.strip() for d in os.environ["TV_MIRROR_DOMAINS"].split(",") if d.strip()]
    if custom_domains:
        MIRROR_DOMAINS = custom_domains

# Oturum / Token alma uç noktaları (Ping Endpoints)
PING_ENDPOINTS = [
    "https://www.vypn.net/api/app/ping",
    "https://cache.vypn.net/api/app/ping",
    "https://www.vavoo.tv/api/app/ping"
]

# API Rotaları ve Protokol Sabitleri
STREAM_ROUTE = "vavoo-iptv"
CATALOG_ENDPOINT = "mediahubmx-catalog.json"
SIG_HEADER = "mediahubmx-signature"
PKG_NAME = "net.vypn.app"
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
CLIENT_VERSION = "3.1.4"

# ==============================================================================
# 2. YAPILANDIRMA: KANAL GRUPLARI VE ÇIKTI DOSYALARI
# İleride yeni bir ülke eklemek isterseniz aşağıdaki sözlüğe yeni satır ekleyebilirsiniz:
# ==============================================================================
COUNTRY_GROUPS = {
    "Turkey": "TR.m3u8",
    "Netherlands": "NL.m3u8",
    # "Germany": "DE.m3u8",
    # "United Kingdom": "UK.m3u8",
    # "France": "FR.m3u8",
}


def get_auth_signature(max_retries=3):
    """
    Uzak servis üzerinden oturum belirteci (token) alır.
    """
    uid = str(uuid.uuid4())
    ts = int(time.time() * 1000)

    payload = {
        "reason": "app-focus",
        "locale": "en",
        "theme": "dark",
        "metadata": {
            "device": {"type": "desktop", "uniqueId": uid},
            "os": {"name": "win32", "version": "Windows 10 Pro", "abis": ["x64"], "host": "Lenovo"},
            "app": {"platform": "electron"},
            "version": {"package": PKG_NAME, "binary": "3.1.0", "js": "3.1.0"}
        },
        "appFocusTime": 0,
        "playerActive": False,
        "playDuration": 0,
        "devMode": False,
        "hasAddon": True,
        "castConnected": False,
        "package": PKG_NAME,
        "version": "3.1.0",
        "process": "app",
        "firstAppStart": ts,
        "lastAppStart": ts,
        "ipLocation": None,
        "adblockEnabled": True,
        "proxy": {"supported": ["ss"], "engine": "Mu", "enabled": False, "autoServer": True},
        "iap": {"supported": False}
    }

    headers = {
        "User-Agent": BROWSER_UA,
        "Accept": "*/*",
        "Content-Type": "application/json; charset=utf-8"
    }

    for attempt in range(1, max_retries + 1):
        for url in PING_ENDPOINTS:
            try:
                r = requests.post(url, json=payload, headers=headers, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    sig = data.get("sig") or data.get("addonSig") or data.get("signature") or data.get("token")
                    if sig:
                        print(f"🔑 Oturum anahtarı doğrulandı: {sig[:20]}...")
                        return sig
            except Exception:
                continue
        if attempt < max_retries:
            time.sleep(1)

    print("⚠️ Oturum anahtarı alınamadı, devam ediliyor...")
    return None


def get_working_domain(signature=None, domains=None):
    """
    Havuzdaki alan adlarını sırayla test eder ve hem katalog hem de API
    yanıtı veren ilk çalışan aktif sunucuyu seçer.
    """
    if domains is None:
        domains = MIRROR_DOMAINS

    print("🔍 Aktif ayna (mirror) sunucu kontrol ediliyor...")
    headers = {
        "User-Agent": BROWSER_UA,
        "Accept": "application/json",
        "Accept-Language": "de",
        "Content-Type": "application/json; charset=utf-8"
    }
    if signature:
        headers[SIG_HEADER] = signature

    probe_body = {
        "language": "de",
        "region": "AT",
        "catalogId": "iptv",
        "id": "iptv",
        "adult": False,
        "search": "",
        "sort": "name",
        "filter": {"group": "Turkey"},
        "cursor": 0,
        "clientVersion": CLIENT_VERSION
    }

    for domain in domains:
        url = f"https://{domain}/{CATALOG_ENDPOINT}"
        try:
            print(f"   ⏳ Deneniyor: {domain:<15}", end=" ", flush=True)
            r = requests.post(url, json=probe_body, headers=headers, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and "items" in data:
                    print(f"✅ AKTİF ({len(data.get('items', []))} örnek kanal yanıt verdi)")
                    return domain
                else:
                    print("⚠️ Geçersiz veri formatı")
            else:
                print(f"❌ (HTTP {r.status_code})")
        except requests.exceptions.RequestException:
            print("❌ (Erişilemedi)")
            continue

    fallback = domains[0] if domains else "kool.ws"
    print(f"⚠️ Havuzdaki sunuculardan canlı yanıt alınamadı. Varsayılan '{fallback}' ile devam ediliyor...")
    return fallback


def clean_channel_name(raw_name):
    """
    Kanal isimlerindeki gereksiz teknik uzantıları (.s, .c, .b, (1), vb.) temizler.
    Örn: 'TRT 1 HD .c' -> 'TRT 1 HD', '24 .s' -> '24'
    """
    if not raw_name:
        return "İsimsiz Kanal"
    name = re.sub(r'\s*(\.[a-zA-Z0-9]{1,3})+$', '', raw_name)
    name = re.sub(r'\s*\((?:\d+|[A-Za-z]{1,3})\)\s*$', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name if name else raw_name.strip()


def normalize_for_matching(text):
    """
    Kanal isimlerini karşılaştırma için standartlaştırır.
    Bozuk karakter boşluklarını ve Türkçe karakterleri düzeltir.
    """
    t = text.upper()
    t = t.replace("İ", "I").replace("Ğ", "G").replace("Ü", "U").replace("Ş", "S").replace("Ö", "O").replace("Ç", "C")
    # Bozuk OCR/yazım düzeltmeleri (Örn: S NEMA -> SINEMA)
    t = re.sub(r'S\s*N\s*E\s*M\s*A', 'SINEMA', t)
    t = re.sub(r'M\s*N\s*K\s*A', 'MINIKA', t)
    t = re.sub(r'O\s*C\s*U\s*K', 'COCUK', t)
    t = re.sub(r'B\s*E\s*N\s*G\s*T\s*R\s*K', 'BENGUTURK', t)
    t = re.sub(r'L\s*K\s*E\s*TV', 'ULKETV', t)
    t = re.sub(r'AK\s*T\s*TV', 'AKITTV', t)
    t = re.sub(r'M\s*Z\s*K', 'MUZIK', t)
    return t


def get_turkish_category(name):
    """
    Türkiye kanallarını gelişmiş kurallarla kategorilere ayırır.
    """
    n = normalize_for_matching(name)

    # 1. Ulusal Kanallar (Ana akım)
    if any(x in n for x in [
        "TRT 1", "TRT1", "ATV", "KANAL D", "SHOW TV", "SHOW HD", "STAR TV", "STAR HD",
        "NOW TV", "NOW HD", "FOX", "TV8", "TV 8", "KANAL 7", "BEYAZ TV", "A2", "TEVE2",
        "FLASH TV", "360 TV", "360 HD", "TRT 2", "TRT AVAZ", "TRT TURK", "TV4"
    ]):
        return "🇹🇷 Ulusal"

    # 2. Spor Kanalları
    if any(x in n for x in [
        "SPOR", "SPORT", "BEIN SPORTS", "BEIN SPORT", "S SPORT", "TIVIBU SPOR",
        "SMART SPOR", "EUROSPORT", "TRT SPOR", "A SPOR", "FIGHT", "RACING", "NBA",
        "WWE", "F1", "FORMULA", "AT YARISI", "TJK", "FB TV", "GS TV", "BJK TV", "EXXEN"
    ]):
        return "🇹🇷 Spor"

    # 3. Sinema & Dizi
    if any(x in n for x in [
        "SINEMA", "CINEMA", "MOVIE", "MOVIES", "FILM", "DIZI", "SALON",
        "BEIN MOVIES", "BEIN CONNECT", "FILMBOX", "FX", "ACTION", "KOMEDI", "DRAM"
    ]):
        return "🇹🇷 Sinema & Dizi"

    # 4. Haber & Ekonomi
    if any(x in n for x in [
        "HABER", "NEWS", "CNN", "NTV", "BLOOMBERG", "A HABER", "TRT HABER",
        "TV100", "HALK TV", "TELE1", "SOZCU", "SZC", "EKOL", "24 TV", "24 HABER",
        "TGRT", "ULUSAL KANAL", "KRT", "ULKETV", "ULKE TV", "AKITTV", "AKIT TV",
        "BENGUTURK", "BENGU TURK", "TVNET", "A PARA"
    ]):
        return "🇹🇷 Haber & Ekonomi"

    # 5. Belgesel & Yaşam
    if any(x in n for x in [
        "BELGESEL", "DOCU", "NAT GEO", "NATIONAL GEO", "DISCOVERY", "HISTORY",
        "DMAX", "TLC", "ANIMAL PLANET", "VIASAT", "YABAN", "HABITAT", "INVESTIGATION",
        "CRIME", "LOVE NATURE", "DA VINCI", "KITCHEN"
    ]):
        return "🇹🇷 Belgesel & Yaşam"

    # 6. Çocuk
    if any(x in n for x in [
        "COCUK", "KIDS", "CARTOON", "DISNEY", "BABY", "MINIKA",
        "NICKELODEON", "NICKTOONS", "BOOMERANG", "MOONBUG", "DUCK TV", "TRT COCUK"
    ]):
        return "🇹🇷 Çocuk"

    # 7. Müzik & Radyo
    if any(x in n for x in [
        "MUZIK", "MUSIC", "POWER", "KRAL", "NR1", "NUMBER1", "NUMBER 1", "DREAM",
        "TRT MUZIK", "MTV", "TRACE", "MEZZO", "TEMPO", "RADYO", "RADIO", "FM",
        "ALEM", "AKUSTIK"
    ]):
        return "🇹🇷 Müzik & Radyo"

    # 8. Dini Kanallar
    if any(x in n for x in [
        "DIYANET", "SEMERKAND", "KABE", "HILAL", "LALEGUL", "VAHDET", "BERAT", "AL ZAHRA"
    ]):
        return "🇹🇷 Dini"

    # 9. Yerel Kanallar (Şehir isimleri veya yerel ibareler)
    yerel_sehirler = [
        "ADANA", "ADIYAMAN", "AFYON", "AGRI", "AKSARAY", "AMASYA", "ANKARA", "ANTALYA",
        "ARDAHAN", "ARTVIN", "AYDIN", "BALIKESIR", "BARTIN", "BATMAN", "BAYBURT", "BILECIK",
        "BINGOL", "BITLIS", "BOLU", "BURDUR", "BURSA", "CANAKKALE", "CANKIRI", "CORUM",
        "DENIZLI", "DIYARBAKIR", "DUZCE", "EDIRNE", "ELAZIG", "ERZINCAN", "ERZURUM", "ESKISEHIR",
        "GAZIANTEP", "GIRESUN", "GUMUSHANE", "HAKKARI", "HATAY", "IGDIR", "ISPARTA", "ISTANBUL",
        "IZMIR", "KAHRAMANMARAS", "KARABUK", "KARAMAN", "KARS", "KASTAMONU", "KAYSERI", "KILIS",
        "KIRIKKALE", "KIRKLARELI", "KIRSEHIR", "KOCAELI", "KONYA", "KUTAHYA", "MALATYA", "MANISA",
        "MARDIN", "MERSIN", "MUGLA", "MUS", "NEVSEHIR", "NIGDE", "ORDU", "OSMANIYE", "RIZE",
        "SAKARYA", "SAMSUN", "SANLIURFA", "SIIRT", "SINOP", "SIVAS", "SIRNAK", "TEKIRDAG",
        "TOKAT", "TRABZON", "TUNCELI", "USAK", "VAN", "YALOVA", "YOZGAT", "ZONGULDAK",
        "ALANYA", "KIBRIS", "KIBRIS TV", "ADA TV", "MERCAN", "AKSU", "ALTAS", "EGE", "GUNEYDOGU"
    ]
    if any(s in n for s in yerel_sehirler):
        return "🇹🇷 Yerel Kanallar"

    # 10. Genel / Diğer
    return "🇹🇷 Genel"


def get_dutch_category(name):
    """
    Hollanda kanallarını kategorilere ayırır.
    """
    n = normalize_for_matching(name)

    # 1. Algemeen & NPO (Ulusal)
    if any(x in n for x in [
        "NPO", "RTL", "SBS", "VERONICA", "NET 5", "NET5", "BVN", "BBC NL"
    ]):
        return "🇳🇱 Algemeen & NPO"

    # 2. Sport
    if any(x in n for x in [
        "SPORT", "ESPN", "ZIGGO", "EUROSPORT", "VIAPLAY", "RACING"
    ]):
        return "🇳🇱 Sport"

    # 3. Films & Series
    if any(x in n for x in [
        "FILM", "MOVIE", "CINEMA", "HBO", "COMEDY CENTRAL", "STAR", "PARAMOUNT"
    ]):
        return "🇳🇱 Films & Series"

    # 4. Documentaire & Lifestyle
    if any(x in n for x in [
        "DISCOVERY", "NAT GEO", "NATIONAL GEO", "HISTORY", "INVESTIGATION",
        "ANIMAL PLANET", "CURIOSITY", "LOVE NATURE", "24 KITCHEN", "NJAM"
    ]):
        return "🇳🇱 Documentaire & Lifestyle"

    # 5. Kids
    if any(x in n for x in [
        "KIDS", "NICKELODEON", "NICK JR", "NICKTOONS", "CARTOON", "DISNEY",
        "BABY", "BOOMERANG", "PEBBLE", "DUCK TV", "JIMJAM", "KETNET"
    ]):
        return "🇳🇱 Kids"

    # 6. Muziek & Radio
    if any(x in n for x in [
        "192 TV", "MTV", "SLAM", "DANCE TELEVISION", "MUSIC", "RADIO", "ORANJE",
        "TV ORANJE", "MEZZO", "100%"
    ]):
        return "🇳🇱 Muziek"

    # 7. Regionaal (Yerel / Bölgesel)
    if any(x in n for x in [
        "AT 5", "ALMERE", "TWENTE", "DEN HAAG", "L1", "LANSINGERLAND", "LOE TV",
        "BR6", "IDEAAL", "A1 TV", "REGIO"
    ]):
        return "🇳🇱 Regionaal"

    # 8. Overig
    return "🇳🇱 Overig"


def get_channel_category(name, country_group):
    """
    Ülkeye göre uygun kategori belirleme fonksiyonunu çağırır.
    """
    if country_group == "Turkey":
        return get_turkish_category(name)
    elif country_group == "Netherlands":
        return get_dutch_category(name)
    else:
        return f"{country_group}"


def fetch_group_channels(group_name, signature, active_domain=None):
    """
    Belirli bir ülke grubunun tüm sayfalarını aktif sunucu üzerinden çeker.
    Eğer aktif sunucu yanıt vermezse havuzdaki diğer sunuculara otomatik geçer (failover).
    """
    candidate_domains = [active_domain] + [d for d in MIRROR_DOMAINS if d != active_domain] if active_domain else MIRROR_DOMAINS

    for domain in candidate_domains:
        catalog_url = f"https://{domain}/{CATALOG_ENDPOINT}"
        session = requests.Session()
        headers = {
            "User-Agent": BROWSER_UA,
            "Accept": "application/json",
            "Accept-Language": "de",
            "Content-Type": "application/json; charset=utf-8"
        }
        if signature:
            headers[SIG_HEADER] = signature
        session.headers.update(headers)

        channels = []
        cursor = 0
        max_pages = 25
        fetch_success = False

        for _ in range(max_pages):
            body = {
                "language": "de",
                "region": "AT",
                "catalogId": "iptv",
                "id": "iptv",
                "adult": False,
                "search": "",
                "sort": "name",
                "filter": {"group": group_name},
                "cursor": cursor,
                "clientVersion": CLIENT_VERSION
            }

            try:
                r = session.post(catalog_url, json=body, timeout=15)
                if r.status_code != 200:
                    break
                data = r.json()
                items = data.get("items", [])
                if not items:
                    fetch_success = True
                    break

                for itm in items:
                    raw_name = itm.get("name", "")
                    clean_name = clean_channel_name(raw_name)

                    # Kanal ID ve oynatma linki tespiti
                    chid = ""
                    if isinstance(itm.get("ids"), dict):
                        chid = itm["ids"].get("id", "")
                    if not chid:
                        chid = itm.get("id", "")

                    url = itm.get("url") or itm.get("play") or ""
                    if not url and chid:
                        url = f"https://{domain}/{STREAM_ROUTE}/play/{chid}"
                    elif url and "/play/" in url:
                        m = re.search(r'/play/([^/?#]+)', url)
                        if m:
                            url = f"https://{domain}/{STREAM_ROUTE}/play/{m.group(1)}"
                        else:
                            url = re.sub(r'https?://[^/]+/play/', f'https://{domain}/{STREAM_ROUTE}/play/', url)

                    if not url:
                        continue

                    # Logo tespiti
                    images = itm.get("images", {}) if isinstance(itm.get("images"), dict) else {}
                    logo = images.get("logo") or images.get("poster") or itm.get("logo") or itm.get("poster") or ""

                    # EPG / TVG ID
                    tvg_id = ""
                    if isinstance(itm.get("ids"), dict):
                        tvg_id = itm["ids"].get("tvg", "")

                    # Akıllı Kategori Tespiti
                    category = get_channel_category(clean_name, group_name)

                    channels.append({
                        "name": clean_name,
                        "raw_name": raw_name,
                        "url": url,
                        "group": group_name,
                        "category": category,
                        "logo": logo,
                        "tvg_id": tvg_id
                    })

                fetch_success = True
                cursor = data.get("nextCursor")
                if not cursor or cursor == 0:
                    break
            except Exception:
                break

        if fetch_success and len(channels) > 0:
            return group_name, channels, domain

    return group_name, [], active_domain or MIRROR_DOMAINS[0]


def generate_m3u8(channels, output_file, group_title, active_domain):
    """
    Kanalları kategorilerine göre sıralı ve standart M3U8 formatında kaydeder.
    """
    tr_order = [
        "🇹🇷 Ulusal", "🇹🇷 Spor", "🇹🇷 Sinema & Dizi", "🇹🇷 Haber & Ekonomi",
        "🇹🇷 Belgesel & Yaşam", "🇹🇷 Çocuk", "🇹🇷 Müzik & Radyo", "🇹🇷 Dini",
        "🇹🇷 Yerel Kanallar", "🇹🇷 Genel"
    ]
    nl_order = [
        "🇳🇱 Algemeen & NPO", "🇳🇱 Sport", "🇳🇱 Films & Series",
        "🇳🇱 Documentaire & Lifestyle", "🇳🇱 Kids", "🇳🇱 Muziek",
        "🇳🇱 Regionaal", "🇳🇱 Overig"
    ]
    priority_order = tr_order if group_title == "Turkey" else nl_order

    def sort_key(ch):
        cat = ch["category"]
        cat_idx = priority_order.index(cat) if cat in priority_order else 999
        return (cat_idx, ch["name"])

    # Kanalları kategori önceliğine ve alfabetik sıraya göre diz
    sorted_channels = sorted(channels, key=sort_key)

    lines = [
        "#EXTM3U",
        f"#EXT-X-USER-AGENT:{BROWSER_UA}",
        f"#EXT-X-REFERER:https://{active_domain}/",
        f"#EXT-X-ORIGIN:https://{active_domain}"
    ]

    category_counts = defaultdict(int)

    for ch in sorted_channels:
        logo_part = f' tvg-logo="{ch["logo"]}"' if ch["logo"] else ""
        tvg_id_part = f' tvg-id="{ch["tvg_id"]}"' if ch["tvg_id"] else ""
        extinf = f'#EXTINF:-1{tvg_id_part} tvg-name="{ch["name"]}"{logo_part} group-title="{ch["category"]}",{ch["name"]}'
        lines.append(extinf)
        lines.append(ch["url"])
        category_counts[ch["category"]] += 1

    content = "\n".join(lines) + "\n"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    file_size_kb = round(len(content.encode('utf-8')) / 1024, 1)
    print(f"💾 [{group_title}] -> '{output_file}' kaydedildi ({len(channels)} kanal, {file_size_kb} KB, Sunucu: {active_domain}).")
    print(f"   📂 Kategori Dağılımı:")
    for cat in priority_order:
        if cat in category_counts:
            print(f"      • {cat:28}: {category_counts[cat]:3d} kanal")
    for cat, cnt in category_counts.items():
        if cat not in priority_order:
            print(f"      • {cat:28}: {cnt:3d} kanal")


def main():
    print("\n" + "=" * 65)
    print(f"▶️ TV-LISTS LİSTE KAZIMA BAŞLADI: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Hedef Ülkeler : {', '.join(COUNTRY_GROUPS.keys())}")
    print(f"🌐 Mirror Havuzu : {', '.join(MIRROR_DOMAINS)}")
    print("=" * 65)

    start_time = time.time()
    sig = get_auth_signature()

    # Havuzdaki çalışan aktif domain'i belirle
    active_domain = get_working_domain(signature=sig)
    print(f"🚀 Seçilen Aktif Sunucu: https://{active_domain}")
    print("-" * 65)

    groups_to_fetch = list(COUNTRY_GROUPS.keys())
    print(f"📡 Toplam {len(groups_to_fetch)} grup paralel olarak çekiliyor...")

    results = {}
    with ThreadPoolExecutor(max_workers=min(5, len(groups_to_fetch))) as executor:
        futures = [executor.submit(fetch_group_channels, g, sig, active_domain) for g in groups_to_fetch]
        for f in futures:
            group_name, ch_list, domain_used = f.result()
            results[group_name] = (ch_list, domain_used)
            print(f" 📺 [{group_name:15}]: {len(ch_list):4d} kanal bulundu (Kaynak: {domain_used})")

    print("-" * 65)
    for group_name, output_file in COUNTRY_GROUPS.items():
        ch_list, domain_used = results.get(group_name, ([], active_domain))
        if ch_list:
            generate_m3u8(ch_list, output_file, group_name, domain_used)
        else:
            print(f"⚠️ [{group_name}] için hiç kanal bulunamadı, dosya oluşturulmadı.")

    duration = round(time.time() - start_time, 2)
    print("=" * 65)
    print(f"🎉 Tüm işlemler {duration} saniyede başarıyla tamamlandı! [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")


if __name__ == "__main__":
    main()
