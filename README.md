# Sağlam Teknik — Krem Renkli Test Sitesi

Bu GitHub deposu, kullanıcının **site kremrenklı.zip** dosyasındaki tasarımın gerçek telefondan, tabletten ve bilgisayardan test edilebilmesi için ayrılmış bir **statik ön izleme** projesidir.

- Ana site **saglamkombiklima.com.tr** değişmedi. `saglam-ai-usta` Usta Topluluğu deposuna dokunulmadı.
- Ön izleme kullanıcıya ait **saglamkombiklima.com** alan adına bağlanmış değildir; yalnızca GitHub Pages varsayılan adresinde sunulur.
- **PHP/Gemini/Telegram/admin/veritabanı/müşteri kayıtları bu statik ön izlemede çalışmaz.** Krem renkli HTML/CSS/JS, görseller ve bağlantıların görünümü test edilir.
- Gizli anahtarlar veya müşteri kayıtları depoya konmamıştır. Tüm kullanıcı sayfalarında `noindex`, ayrıca `robots.txt` ile botlara erişim engeli bulunur.
- `preview-parts/part-*.txt` dosyaları güvenli ön izleme ZIP arşivinin base64 parçalarıdır. GitHub Actions otomatik birleştirir, SHA256 doğrular ve GitHub Pages'e yayınlar.
- GitHub'da **Settings → Pages → Build and deployment → Source: GitHub Actions** etkinleştirilmeden dışarıdan açılan adres çalışmayabilir.

**Ön izleme adresi (Pages etkinleştirilirse):** https://saglamteknikk2-afk.github.io/site/

Kaynak paket SHA-256: `1e1af83e7bc6233f8af88f89a5873440288caed73cb4173483106f050ec5eb7b`
