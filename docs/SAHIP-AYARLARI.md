# Özel ayarlar ve haritalar

Bu dosya kurulum bilgisidir; gerçek anahtar veya müşteri kaydı içermez. GitHub Pages testinde sunucu özellikleri çalıştırılmaz. Ana canlı site bu çalışma sırasında değiştirilmedi.

## PHP hostingde dosya yerleşimi

```text
alan-adi/
  httpdocs/                    # Üretim paketinin webroot içeriği
  private/
    saglam-teknik/
      site_apileri,.txt         # Mevcut API ayarları, korunur
      haritalar.json            # Harita bağlantıları
      site.sqlite              # Mevcut kayıtlar, varsa korunur
```

Virgülsüz `site_apileri.txt` eski adı da desteklenir; ikisi varsa virgüllü ad önceliklidir. Özel klasör farklı yerdeyse `SAGLAM_PRIVATE_DIR` mevcut mutlak yolu göstermelidir. Özel klasörü web kökünün içine taşımayın. Örneklerdeki boş değerlerle mevcut dosyanızı ezmeyin.

## Haritalar sonradan nasıl açılır?

`templates/private/saglam-teknik/haritalar.json.ornek` dosyasını özel klasörünüze `haritalar.json` adıyla koyun. Aşağıdaki iki alana işletmenin gerçek paylaşım bağlantılarını yazın:

```json
{
  "google_url": "",
  "yandex_url": "",
  "google_embed_url": "",
  "yandex_embed_url": ""
}
```

Paylaşım linkleri girildiğinde PHP sürümündeki kartlar yol tarifi bağlantısını açar. İsteğe bağlı embed alanları yalnız Google/Yandex iframe src URL’si içindir; HTML yapıştırılmaz. Gömülü harita yalnız ziyaretçi açmayı seçtiğinde yüklenir. Boş/geçersiz linkler sahte konum göstermez. Harita paylaşım linki için API anahtarı gerekmez.

## Gemini ve bildirimler

Mevcut API dosyası ve dört Gemini anahtar yuvası korunur. Anahtarları sohbete, GitHub’a veya tarayıcıya koymayın. Kullanılan modelin hesapta erişilebilirliği ve ücretsiz plan sınırları gerçek hesap üzerinden kontrol edilmelidir. Aynı projedeki anahtarlar aynı kotayı paylaşır.

AI cevabı bildirim gönderilmesini beklemez. Bildirimler mevcut kalıcı kuyruğa yazılır; üretimde mevcut `worker.php` görevinin çalışması gerekir. Örnek cron komutu (hostingde gerçek yol kullanılmalı):

```sh
php /tam/yol/httpdocs/worker.php
```

Dakikada bir çalışma başlangıç için uygundur. Bu çalışma sırasında canlı cron, webhook veya Telegram ayarı değiştirilmedi.

## Gerçek veri ve reklamlar

Önizlemede mevcut 62 yayımlı statik yorum korunur. PHP sürümü ayrıca mevcut onaylı yorumları kendi API’sinden okur; özel veritabanı test ortamına taşınmaz. Yeni yorumların yönetici onayı ve yayın izni korunur.

SEO ve reklam hesapları bu depoya bağlanmış değildir. Ads yönetimi veya sürekli canlı izleme kurulmuş sayılmaz. Hesap bağlantıları ve bütçe kapsamı belirlenmeden reklam başlatılmamalıdır.
