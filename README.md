# TV-lists IPTV Listeleri

Bu depo, canlı TV kanallarını otomatik olarak çeker, akıllı algoritmayla **kategorilere ayırır** ve her **3 saatte bir** güncel M3U8 çalma listeleri oluşturur.

---

## 📺 Oynatma Listesi Bağlantıları (M3U / M3U8)

IPTV oynatıcınıza (TiviMate, IPTV Smarters, VLC, Kodi, Next IPTV vb.) ekleyebileceğiniz güncel **Raw** bağlantıları:

| Ülke | Dosya | Doğrudan Oynatma Bağlantısı (Raw URL) |
| :--- | :--- | :--- |
| 🇹🇷 **Türkiye** | `TR.m3u8` | `https://raw.githubusercontent.com/GithubSMK/TV-lists/main/TR.m3u8` |
| 🇳🇱 **Hollanda** | `NL.m3u8` | `https://raw.githubusercontent.com/GithubSMK/TV-lists/main/NL.m3u8` |

> [!TIP]
> Oynatıcınıza yukarıdaki tek bir linki eklemeniz yeterlidir. Oynatıcınız tüm kanalları otomatik olarak aşağıdaki kategoriler halinde klasörleyecektir.

---

## 📂 Akıllı Kategori Yapısı

Listelerdeki kanallar özel bir metin analizi ve normalizasyon filtresinden geçirilerek oynatıcınızda en mantıklı sıralamayla gruplandırılır:

### 🇹🇷 Türkiye Listesi (`TR.m3u8`)
1. 🇹🇷 **Ulusal**: TRT 1, ATV, Kanal D, Show TV, Star TV, NOW, TV8, Kanal 7, Beyaz TV, Teve2, Flash TV vb.
2. 🇹🇷 **Spor**: BeIN Sports, S Sport, Tivibu Spor, Smart Spor, TRT Spor, A Spor, FB TV, Exxen vb.
3. 🇹🇷 **Sinema & Dizi**: BeIN Movies, Sinema TV kanalları, FilmBox, FX, dizi ve film kanalları.
4. 🇹🇷 **Haber & Ekonomi**: A Haber, CNN Türk, Habertürk, NTV, TV100, Sözcü TV, Bloomberg HT, Ekol TV vb.
5. 🇹🇷 **Belgesel & Yaşam**: Discovery Channel, National Geographic, DMAX, TLC, Viasat, Love Nature, 24 Kitchen vb.
6. 🇹🇷 **Çocuk**: Cartoon Network, Disney, Minika Çocuk, Minika Go, Boomerang, TRT Çocuk vb.
7. 🇹🇷 **Müzik & Radyo**: Power TV, Kral TV, Number1, Dream TV, TRT Müzik, popüler radyo istasyonları vb.
8. 🇹🇷 **Dini**: Diyanet TV, Semerkand TV, Kabe TV, Lalegül TV vb.
9. 🇹🇷 **Yerel Kanallar**: Türkiye'nin 81 iline ait yerel ve bölgesel televizyon kanalları.
10. 🇹🇷 **Genel**: Diğer tematik ve genel yayınlar.

### 🇳🇱 Hollanda Listesi (`NL.m3u8`)
1. 🇳🇱 **Algemeen & NPO**: NPO 1, 2, 3, RTL 4, 5, 7, 8, SBS 6, Veronica, Net 5, BVN
2. 🇳🇱 **Sport**: Ziggo Sport, ESPN, Eurosport, Viaplay
3. 🇳🇱 **Films & Series**: Film1, HBO, Comedy Central, Paramount Network
4. 🇳🇱 **Documentaire & Lifestyle**: Discovery, National Geographic, History, 24Kitchen, Njam
5. 🇳🇱 **Kids**: Nickelodeon, Nick Jr, Cartoon Network, Disney, Ketnet
6. 🇳🇱 **Muziek**: 192 TV, MTV, Slam! TV, TV Oranje, 100% NL
7. 🇳🇱 **Regionaal**: AT 5, Almere TV, Twente TV, Den Haag TV, L1
8. 🇳🇱 **Overig**: Diğer Hollanda yayınları.

---

## ⚙️ Yeni Bir Ülke Nasıl Eklenir?

İleride yeni ülkeler eklemek için `TV-lists.py` dosyasındaki `COUNTRY_GROUPS` sözlüğüne tek bir satır eklemeniz yeterlidir:

```python
COUNTRY_GROUPS = {
    "Turkey": "TR.m3u8",
    "Netherlands": "NL.m3u8",
    "Germany": "DE.m3u8",         # Örn: Almanya kanalları için
    "United Kingdom": "UK.m3u8",  # Örn: İngiltere kanalları için
    "France": "FR.m3u8",          # Örn: Fransa kanalları için
}
```

Desteklenen başlıca ülke isimleri:
* `Turkey`, `Netherlands`, `Germany`, `United Kingdom`, `France`, `Italy`, `Spain`, `Arabia`, `Balkans`, `Russia`, `Poland`, `Portugal`, `Albania`, `Romania`, `Bulgaria`

---

## 🤖 Otomasyon (GitHub Actions)

* **Güncelleme Sıklığı:** Her **3 saatte bir** (`00:00`, `03:00`, `06:00`, `09:00`, `12:00`, `15:00`, `18:00`, `21:00 UTC`) GitHub Actions tarafından arka planda otomatik çalıştırılır.
* **Manuel Tetikleme:** Dilediğiniz an depodaki **Actions** sekmesinden **"TV-lists IPTV Listelerini Guncelle"** -> **"Run workflow"** butonuna basarak da anında yeni liste oluşturabilirsiniz.
