# Sağlam Teknik – Krem Renkli Test Sitesi

Bu depo yalnızca yeni krem renkli kombi/klima sitesinin **statik test ön izlemesi** içindir.

**Ana saglamkombiklima.com.tr sitesi** ve **saglam-ai-usta Usta Topluluğu** kodları değiştirilmez.

Klasördeki `preview-parts/chunk-*.txt` dosyaları, 487 statik dosyadan oluşan temizlenmiş test ZIP'inin kodlanmış parçalarıdır. GitHub Actions parçaları SHA-256 ile doğrular, açar ve GitHub Pages'e aktarır.

**Önemli:** GitHub Pages PHP çalıştırmadığından Gemini, Telegram, servis kaydı, gerçek veritabanı ve yönetici sistemi bu ön izleme ortamında devre dışıdır. Bu depo hiçbir gizli Gemini anahtarı veya müşteri verisi içermez. Test sayfalarında noindex işaretlemesi ve robots.txt engeli vardır.

Pages etkinse test adresi: https://saglamteknikk2-afk.github.io/site/

İlk etkinleştirme: GitHub depo **Settings → Pages → Build and deployment → Source: GitHub Actions**. Başarılı yayın kontrolü: **Actions → Saglam Teknik Krem Test Yayini**.
