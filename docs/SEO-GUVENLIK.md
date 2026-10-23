# SEO, güvenlik ve ortam sınırları

23 Ekim 2026 — kaynak ve mevcut yerel çıktı incelemesi. Bu belge canlı üretim yayını, güvenlik sertifikası veya sıralama garantisi değildir. Son commit, son test sayıları ve GitHub Actions yayın sonucu teslim sırasında güncel kayıtlarla doğrulanmalıdır.

## Önizleme ve üretim

`https://saglamteknikk2-afk.github.io/site/` yalnız GitHub Pages önizlemesidir. `.github/workflows/pages.yml` içindeki `main` yayını bu adresi hedefler; ana alan adını veya Usta Topluluğu projesini yayınlamaz. GitHub Pages PHP çalıştırmaz.

`scripts/build_site.py` doğrulanmış arşivi, üretimde `server/` dosyalarını, ardından `overrides/` ve ortak bileşenleri birleştirir. `_site/` ile `build/production/` geçici çıktıdır. Üretim komutu ve isteğe bağlı Actions üretim ZIP'i yalnız paket hazırlar; dosyaları canlı sunucuya taşımaz. Paket içinde gerçek özel ayar veya müşteri veritabanı bulunmamalıdır.

Önizlemede bütün ziyaretçi HTML sayfalarına `noindex,nofollow,noarchive`, görünür test bildirimi ve ilk sırada `preview-guard.js` eklenir. robots.txt taramaya izin verir; sitemap önizlemeye alınmaz. Böylece tarayıcı `noindex` etiketini okuyabilir. `noindex` parola koruması değildir ve tarayıcı engelleyicisi güvenlik sınırı sayılmaz; önizlemeye zaten gizli veri konmaz. PHP, özel ayarlar ve yönetim dosyaları önizleme derlemesinden çıkarılır. Form, AI/API, konum ve ileti gönderimleri kapalıdır; gerçek başarı mesajı gösterilmemelidir.

Üretimde önizleme kilidi ve `/site/` öneki kaldırılır, özgün canonical/SEO etiketleri geri yüklenir. Üretimde seçici/404/yönetim gibi dizine alınmaması gereken sayfaların `noindex` kalması hata sayılmaz. Yerel dosya kontrolü; canlı yönlendirme, TLS, WAF, HTTP başlıkları, gerçek tarama veya Core Web Vitals ölçümü yerine geçmez.

## İçerik ve arama görünürlüğü

- Aynı sorgunun kelime sıraları için ayrı URL açılmaz. Aynı niyet, ilgili canonical ilçe/hizmet veya teknik rehberde karşılanır. Mahalle seçimi otomatik olarak her mahalleye bağımsız, dizine açık sayfa bulunduğu anlamına gelmez.
- Mevcut bağımsız ilçe metinleri ve kaynaklı model rehberleri korunur. Genel marka listesiyle doğrulanmış model/kod tablosu kapsamı farklıdır; bütün tarihî modellerin belgelendiği söylenmez.
- Tam model ve üretici belgesinin ülke, kontrolcü/ürün varyantı sınırları korunur. Gerekli kapsam doğrulaması kullanıcıdan alınmadan tablo kesin eşleşme sayılmaz. `E1`, `E01` ve baştaki sıfırlar otomatik eşitlenmez. Eksik açıklama başka markadan tamamlanmaz.
- Canonical, sitemap, başlık, görünür içerik, dahili bağlantılar ve JSON-LD tutarlı kalır. İşletme/iletişim/hizmet alanı bilgileri gerçek verilere dayanır. Yeni adres, şube, yorum veya yetkili servis ilişkisi uydurulmaz.
- Görünür, kaynaklı HTML hem kullanıcı hem arama sistemleri için korunur. Google/AI önerisi, her sorguda görünme veya müşteri sayısı garanti edilemez. `llms.txt` isteğe bağlı bağlantı özetidir; Google sıralama veya tavsiye anahtarı değildir.

Google Search, Gemini, ChatGPT ve diğer servislerin tarama/eğitim kontrolleri birbirinin yerine geçmez. Canlı hesap katılım ayarları veya bot erişimi bu depo üzerinden doğrulanmış değildir. Reklam satın almak organik görünürlük satın almak anlamına gelmez.

## AI, haritalar ve özel yapılandırma

Gemini anahtarları yalnız web kökü dışındaki `private/saglam-teknik/site_apileri,.txt` içinde tutulur; `site_apileri.txt` eski adı da okunabilir, virgüllü dosya önceliklidir. Mevcut dosya ve veritabanı korunur. Farklı dizilimde `SAGLAM_PRIVATE_DIR` kullanılır; özel klasörün web kökü içine veya buraya yönlenen sembolik bağlantıya yerleştirilmesi reddedilir. Gerçek anahtarlar Git'e, statik önizlemeye, loglara veya dağıtım ZIP'ine eklenmez. Örneklerin gerçek yeri `templates/private/saglam-teknik/` klasörüdür.

Dört anahtar yuvası korunmuştur; aynı projedeki anahtarlar ayrı kota kabul edilmez. Modelin hesapta kullanılabilir olduğu veya ücretsiz sınırın yeterli olduğu kodun varlığından çıkarılamaz. Kaynakta toplam AI ağ bütçesi sınırlandırılmıştır; kota/fatura/yetki hatasında diğer anahtarlarla devam edilmez. Önce kaynaklı yerel rehber gösterilir. Gerçek sağlayıcı bağlantısı ve performansı ayrıca doğrulanmadıkça “AI çalışıyor” denmez.

`haritalar.json` dosyası yalnız gerçek Google/Yandex paylaşım bağlantılarını ve isteğe bağlı iframe **src URL** değerlerini taşır. Boş örnek, doğrulanmış işletme konumu değildir. Üretim `business-maps` yanıtı yalnız izin verilen kamuya açık URL alanlarını döndürür; API anahtarı veya özel ayar içeriğini açmaz. Iframe/HTML kodu kabul edilmez, harita ziyaretçi seçerse yüklenir. Önizlemede harita API isteği yapılmaz. Kullanıcı gerçek bağlantıları henüz sağlamadıysa kartlar pasif kalır.

Sunucu tarafında parametreli SQL, CSRF/yetki kontrolleri, sınırlama, güvenli çıktı ve hata işleme korunmalıdır. Apache `.htaccess` kurallarının varlığı, Plesk/Nginx katmanında özel dosyaların gerçekten engellendiğini kanıtlamaz; canlı kurulumda ayrıca kontrol gerekir. TLS doğrulaması kapatılmaz. PHP 8.2 uyumluluğu hedeflenir; gerçek sürümün güvenlik yaması ve eklentileri hosting sağlayıcısıyla doğrulanır.

## Yorumlar ve Armut rozeti

Önizleme mevcut yayımlı değerlendirmeleri gösterebilir; canlı onaylı yorum API'sini çağırmaz, yeni yorum kaydetmez. Üretimde `api.php?action=reviews` yalnız onaylı site yorumlarını yükler; yeni kayıtlar yayın onayıyla yönetici incelemesine gider. Özel üretim veritabanı test ortamına kopyalanmaz. Mevcut API tek yanıtta en fazla 500 onaylı kayıt döndürür; daha büyük yorum arşivleri için ayrıca sayfalama gerekir. Canlıdaki bütün kayıtların korunduğu, ancak gerçek API/veritabanı kapsamı ayrıca doğrulanınca söylenebilir; bu tasarım özel kayıtların taşındığı anlamına gelmez.

`oneri.png`, kullanıcı tarafından sağlanan Armut rozetidir. Görsel yeniden üretilmez veya puanı değiştirilmez. Bu dosyanın gösterilmesi resmî Armut API entegrasyonu, güncel platform puanının bağımsız doğrulanması veya platform garantisi değildir. Site yorumlarıyla platform puanı karıştırılmaz; sahte `aggregateRating` eklenmez. Yeni profil bağlantısı veya rozet kullanım açıklaması, gerçek kaynak doğrulanmadan uydurulmaz.

## Bildirim, ölçüm ve reklam

Bildirim önce yerel outbox kuyruğuna yazılır; Telegram teslimi ve günlük raporlar üretim cron/worker kurulumu gerektirir. Kayıt yanıtı Telegram ağ isteğini beklemez. Yönetim API’sindeki `test-telegram`, `test-ai`, `setup-webhook` işlemleri ve worker çalıştırmaları gerçek sağlayıcı işlemleri yapabilir; sıradan test komutu değildir. Bu depo değişikliği gerçek cron veya webhook kurulmuş sayılmaz. Ana sitenin mevcut botuna test mesajı gönderilmez.

Reklam hesabı bağlantısı, harcama yetkisi veya çalışan otomatik reklam yönetimi kurulmuş değildir. Panel görünümü bunları tamamlanmış saydırmaz. Harcama için gerçek hesap erişimi ve açık bütçe yetkisi gerekir. Telefon/WhatsApp tıklaması, gerçek görüşme, nitelikli talep ve ücretli tamamlanan iş ayrı ölçülür. Haftada üç iş sınırı yoktur; büyüme hedefleri kanıtlanmış talep ve hizmet kapasitesiyle değerlendirilir. Bot sayısı ve AI etkileşimi müşteri sayısı değildir. Eski activity uyumluluk uç noktası hâlen recorded:false döndürür; tam ziyaret/telefon/WhatsApp/talep/ücretli iş dönüşüm sistemi bu tasarım çalışmasında kurulmuş sayılmaz. Bu sistem, hesap bağlantılarından sonra ayrı bir uygulama adımıdır.

## Kontrollerin kapsamı ve tekrar çalıştırma

İnceleme sırasında mevcut yerel raporlarda önizlemenin 203 ziyaretçi sayfasının tamamında `noindex` bulunduğu ve önizlemede PHP olmadığı görüldü. Derleme kontrolleri, önizleme engelleyicisi ve model akışı raporları yerel kanıttır. Son yerel tarayıcı raporu beş görünümün tamamında başarılıdır: eksik görsel, JavaScript hatası, yatay taşma veya gerçek API/dış ağ isteği bulunmadı. Armut rozeti gerçekten yüklendi ve görünür; mobilde kedi-köpek fotoğrafı kesilmeden gösterildi. Model akışında 32 kontrol, önizleme engelleyicisinde 15 doğrulama geçti. Önceki SVG üretim ve kontrast sorunları giderildi. Bu yerel sonuçlar canlı sağlayıcı bağlantısını kanıtlamaz; GitHub Actions yayın sonucu ayrıca doğrulanmalıdır.

```sh
python scripts/build_site.py --mode preview --output _site --base-path /site
python scripts/check_site.py _site --mode preview --report build/preview-check.json
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/build_site.py --mode production --output build/production
python scripts/check_site.py build/production --mode production --report build/production-check.json
php tests/business-runtime.php
```

Son PHP testi geçici, sentetik özel klasör ve taklit taşıyıcı kullanır; gerçek AI/Telegram isteği göndermez. `tests/preview-guard.cjs` Playwright ile taklit ağda engelleyiciyi sınar. `tests/model_ux.cjs` yerel HTTP sunucusu ve Playwright/Chromium ister; PHP yanıtlarını taklit eder, gerçek backend bağlantısını doğrulamaz. Bu ön koşullar olmadan testin çalıştığı iddia edilmez.

Kaynaklar ve mevcut çıktılar üzerinde yapılan sınırlı Google/Telegram anahtar kalıbı taramasında eşleşme görülmedi. Bu sonuç bütün Git geçmişinin, bütün sır biçimlerinin veya canlı sunucunun kapsamlı güvenlik denetimi değildir. Tam üretim kabulü; güncel yedek, gerçek özel ayarların korunması, erişim kontrolü, cron/bildirim teslimi ve kullanıcı tarafından yetkilendirilmiş canlı testlerle ayrıca yapılır.

Resmî dayanaklar: [GitHub Pages statik sınırları](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site), [Google noindex](https://developers.google.com/search/docs/crawling-indexing/block-indexing), [Google AI görünürlüğü](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), [Google canonical](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls), [Google reklam ve organik arama ayrımı](https://developers.google.com/search/docs/fundamentals/do-i-need-seo).
