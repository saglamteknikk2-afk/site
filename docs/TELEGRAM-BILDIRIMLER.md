# Sağlam Teknik — Telegram bildirim akışı

Bu dosya yalnız **GitHub kaynak kodunun üretim taslağı** içindir. GitHub Pages PHP çalıştırmaz; ana `saglamkombiklima.com.tr` yayını ve mevcut müşteri verileri bu depodan değiştirilmez.

## Telegram mesaj biçimleri
- **👤 Ziyaret (anlık):** tarih/saat (Europe/Istanbul), görüntülenen sayfa, cihaz, yaklaşık IP şehri/bölgesi. Site ziyaretçisi izin vermediyse kesin konum/ilçe/mahalle iddia edilmez. Gerçek ziyaretçi IP adresi Telegram'da yazılmaz.
- **🤖 AI Usta:** cihaz, sorulan soru, kaynağı belirlenmiş AI/rehber yanıtı, zaman, varsa izinli konum. Çok uzun yanıt, Telegram metin sınırına göre güvenli parçalara ayrılır.
- **🛠️ Servis talebi:** talep tarihi, isim, telefon, müşterinin beyan ettiği ilçe, cihaz ve arıza metni, ziyaretçi cihaz bilgisi.
- **⭐ Yorum:** kullanıcı bildirimi ve Telegram onay/red butonları korunur.
- **📊 Günlük rapor:** önceki takvim gününün toplamı, her gün İstanbul saatiyle 00:00'dan sonra ilk çalışan zamanlanmış görevde.
- **📊 Haftalık rapor:** bir önceki tamamlanmış pazartesi–pazar haftası, yeni hafta başladığında çalıştırılan worker'da; ilk kurulumda önceki tamamlanmış hafta için bir defalık rapor da oluşabilir.
- **📊 Aylık rapor:** bir önceki tamamlanmış takvim ayı, yeni ay başladığında çalıştırılan worker'da; ilk kurulumda önceki tamamlanmış ay için bir defalık rapor da oluşabilir.

Raporlardaki **ziyaret** metriği her gün için tekil oturum sayılarının toplamıdır; haftalık/aylık benzersiz gerçek kişi sayısı değildir. Telefon/WhatsApp tıklaması, form kaydı, ücretli tamamlanan iş farklı metriklerdir.

## Özgün görseller
Üretim paketinde `assets/notifications/visit.png`, `review.png`, `ticket.png` korunur; Telegram'da sendPhoto olarak kullanılır. Görsel eksikse okunabilir metin yedeğine geçilir. AI ve dönem raporları çok satırlı ikonlu metindir; yeni yapay görsel uydurulmaz. Derleme testi özgün PNG varlığını doğrular.

## Canlı sunucuya kurulumdan önce ve sonra
1. **Eski siteye dokunmadan** yeni alan adının ilgili web kökünün ve `private/saglam-teknik/` klasörünün yedeğini alın. Bu depodaki statik Pages çıktısını PHP destekli üretim sanmayın.
2. Yalnız yeni sitenin üretim dizinindeki PHP dosyaları ile özgün görsel dosyalarının mevcut olduğundan emin olun. Gerçek `site.sqlite` ve `site_apileri,.txt` dosyalarını **üzerine yazmayın**; ayrı özel klasörün izinlerini doğrulayın.
3. Yeni sitenin **web kökü dışında** mevcut gizli ayar dosyasında `VISIT_NOTIFICATIONS=1` ve `DAILY_REPORT=1` olmalı. Açıkça `VISIT_NOTIFICATIONS=0` yazıyorsa koddaki varsayılan `true` onu geçersiz kılmaz. `IP_LOCATION_LOOKUP=1` yalnızca yaklaşık IP konumu içindir; KVKK aydınlatması ve tercihleri kontrol edilmeli.
4. Plesk'te **yeni sitenin PHP kullanıcısı ve PHP sürümüyle** her dakika `worker.php` CLI olarak çalıştırılmalı. Sadece web site ziyaretinin olması Telegram kuyruğunu boşaltmaz.
5. Yeni sitenin kendi çalışma ortamında, ana siteye veya canlı botlara dokunmadan `php worker.php status` çıktısından `telegram_key_set`, `chat_id_set`, `visit_notifications`, `worker_last_run`, `pending_notifications` ve `notifications[].last_error` alanlarını kontrol edin. Gerçek bot testleri yalnız açıkça yetki verilirse yapılır.
6. Arayüzün servis talebi kabul etmesi Telegram'a teslim yapıldığını kanıtlamaz: kaydın SQLite'a yazılması, outbox kuyruğu, başarılı worker ve Telegram API teslimi ayrı aşamalardır.

## Sınırlar
- Saatlik/dakikalık kontrol değil; ziyaret bildirimi **kuyruğa derhal** yazılır, Telegram teslimi en erken cron çalıştığında gerçekleşir (normalde en fazla yaklaşık 1 dakika + ağ gecikmesi).
- Konum: IP tabanlı yaklaşık tahmin olabilir ve yanlış ilçe/şehir dönebilir. GPS ancak ziyaretçi izin verir ve istemci veriyi sunucuya gönderirse kullanılır.
- Gerçek kullanıcı, bot, canlı API veya sunucu testi bu GitHub kaynak değişikliğinden otomatik oluşmaz.
