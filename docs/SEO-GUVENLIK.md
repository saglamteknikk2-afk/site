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

Son yerel SEO incelemesinde 203 ziyaretçi sayfasından 404 ve seçim ekranı dışındaki 201 sayfanın sitemap'te tek kez yer aldığı; canonical adreslerinin doğru ve tek olduğu görüldü. FAQ işaretlemesindeki soru/cevaplar görünür HTML ile eşleşiyordu. Bu, JSON-LD'nin arama sonucu zengin görünümü veya AI atfı kazanacağını kanıtlamaz. `check_site.py` bağlantı, H1, JSON sözdizimi ve önizleme ayrımına ek olarak üretimde tek self canonical ve sitemap ile dizine uygun sayfaların bire bir eşleşmesini denetler. İçerik ve kaynak doğruluğu ayrıca incelenmelidir.

Son içerik düzenlemesinde 50 ilçe/hizmet sayfasının özgün araştırılmış bölümleri ve kaynakları korundu; tekrar eden kart açıklamaları ve marka/mahalle girişleri sadeleştirildi. Beş semt sayfasına adres belirsizliği ve servis hazırlığı için ayrı yararlı açıklamalar eklendi. On altı marka sayfasında kopya paragraflar ve belirti rehberinden alınmış FAQ cevapları; gerçekten belgelenen model, ülke veya kontrolcü kapsamıyla değiştirildi. Altı klima hizmet sayfasında girişin gövdede tekrarı kaldırılıp işleme özgü karar ve hazırlık bilgisi yazıldı. Mevcut URL'ler korunur; üretici kod tabloları veya anlamları bu metin düzenlemesiyle değiştirilmez.

`scripts/audit_content.py`, 203 ziyaretçi sayfasının yalnız MAIN içeriğini tarar. Menü, alt bilgi, form, tablo ve scriptleri dışarıda tutar; en az **20 kelimelik** paragrafları iç değerlendirme eşiği olarak kullanır. Kaynak/kapsam, yorum, güvenlik ve yönlendirme modülleri ayrı sınıflanır. Son raporda tekrarlı editoryal paragraf grubu, eşik üstü yakın gövde çifti, eksik model kaynağı bağlantısı ve görünür FAQ uyuşmazlığı bulunmadı; gerekli ortak kaynak ve yönlendirme metinleri korunur. Bu sonuç bütün cümlelerin benzersiz olduğu, içeriklerin anlamsal olarak tamamen bağımsız olduğu veya Google kalite değerlendirmesinin geçildiği anlamına gelmez. Başlık/açıklama/canonical tekrarları da raporda ayrıca gösterilir.

`--strict` yalnız MAIN eksikliği, beklenen model kılavuzu bağlantısının kaybı, geçersiz JSON-LD, FAQ ile görünen metnin uyuşmaması veya en az 80 kelimelik editoryal gövdenin tam klonunda başarısız olur. Yakın benzerlik, tekil paragraf tekrarı ve gerekli ortak modüller otomatik ceza veya başarısızlık sayılmaz; editoryal inceleme sinyalidir. Mevcut model verisinde Baykan–kombi ile General, Altus, İklimsa, Vessen ve Copa–klima için doğrulanmış modele özel kod tablosu eksikleri sürer; katalog seçeneği bulunması bu boşluğu kapatmaz.

Hız değerlendirmesi gerçek sunucuda yapılmalıdır. Ana sayfa model ve organik katalog dosyalarını başlangıçta yükler; ham dosya boyutu, sıkıştırılmış ağ aktarımı veya Core Web Vitals sonucu değildir. Yayın sonrası ölçümde bu dosyaların indirme/ayrıştırma maliyeti sorun oluşturursa ihtiyaca göre yükleme ve önbellek davranışı incelenebilir. Yerel taklit ağdaki ekran görüntüleri, gerçek mobil bağlantı hızını kanıtlamaz.

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

Derlemede üretilen `assets/ad-landing-map.json`, 82 mevcut canonical hizmet/marka/ilçe/semt URL'sini listeler. `scripts/landing_actions.py` bu sayfalara doğrudan Ara ve sayfanın bağlamını taşıyan WhatsApp bağlantıları ekler. Bunlar reklam kampanyası, dönüşüm etiketi veya hesap entegrasyonu değildir. Doğru reklam niyetini doğru mevcut sayfaya bağlama ilkeleri `docs/REKLAM-NIYET-HARITASI.md` dosyasındadır.

## Kontrollerin kapsamı ve tekrar çalıştırma

Güncel kontrol sayıları her derlemenin raporundan okunmalıdır; önceki rapor farklı kaynak sürümüne ait olabilir. `build/preview-check.json`, `build/production-check.json`, `build/content-audit.json`, `build/crawl-check.json`, `build/qa-navigation/navigation-final.json`, `build/qa/browser-smoke.json`, `build/qa-interactions/interactions-final.json` ve `build/qa-model/` raporları birlikte incelenir. Bağlantı hedefinin doğrulanması, düğmenin gerçekten tıklanması, geçici durumdaki bir denetimin gizli olması ve özel ayar bekleyen işlevin pasifliği ayrı raporlanır. Doğrudan denenmeyen bir denetim denenmiş sayılmaz. Özgün mavi S logosu ortak manifestten gelir. PHP iş akışları izole test veritabanı, sahte sağlayıcı yanıtları ve yerel HTTP ile sınanır; gerçek Gemini/Telegram/WhatsApp isteği gönderilmez. Bu sonuçlar gerçek hosting ve sağlayıcı hesaplarının hazır olduğunu tek başına kanıtlamaz; GitHub Actions yayın sonucu ayrıca doğrulanır.

```sh
python scripts/build_site.py --mode preview --output _site --base-path /site
python scripts/check_site.py _site --mode preview --report build/preview-check.json
python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/build_site.py --mode production --output build/production
python scripts/check_site.py build/production --mode production --report build/production-check.json
python scripts/audit_content.py build/production --report build/content-audit.json --strict
php tests/business-runtime.php
```

Son PHP testi geçici, sentetik özel klasör ve taklit taşıyıcı kullanır; gerçek AI/Telegram isteği göndermez. `tests/preview-guard.cjs` Playwright ile taklit ağda engelleyiciyi sınar. `tests/model_ux.cjs` yerel HTTP sunucusu ve Playwright/Chromium ister; PHP yanıtlarını taklit eder, gerçek backend bağlantısını doğrulamaz. Bu ön koşullar olmadan testin çalıştığı iddia edilmez.

Kaynaklar ve mevcut çıktılar üzerinde yapılan sınırlı Google/Telegram anahtar kalıbı taramasında eşleşme görülmedi. Bu sonuç bütün Git geçmişinin, bütün sır biçimlerinin veya canlı sunucunun kapsamlı güvenlik denetimi değildir. Tam üretim kabulü; güncel yedek, gerçek özel ayarların korunması, erişim kontrolü, cron/bildirim teslimi ve kullanıcı tarafından yetkilendirilmiş canlı testlerle ayrıca yapılır.

Resmî dayanaklar: [GitHub Pages statik sınırları](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site), [Google noindex](https://developers.google.com/search/docs/crawling-indexing/block-indexing), [Google AI görünürlüğü](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), [Google canonical](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls), [Google reklam ve organik arama ayrımı](https://developers.google.com/search/docs/fundamentals/do-i-need-seo).

Aynı son denetleyiciyle `d1af1ff289b0eb6db1d0f7f123a0f474b65f37a9` kaynaklarının üretim derlemesi yeniden karşılaştırıldı: en az 20 kelimelik esas içerik paragraflarında editoryal inceleme gerektiren bire bir tekrar grubu 21’den 0’a indi. Ziyaretçi sayfa sayısı 203 kaldı. 50 ilçe, 5 semt, 16 marka ve 6 hizmet sayfasındaki düzenlemeler değerli kaynak ve adresleri korur. Son raporda gerekli ortak kaynak/güvenlik/gezinti modüllerinden 40 tekrar grubu vardır. Bu sınırlı sözcüksel denetim anlamsal benzersizlik, taranma veya sıralama garantisi değildir.

Varış/garanti/MYK beyanları `components/service-assurances.json` içinde teyit beklemektedir. İşletmenin bölgesel süre koşulları, yazılı garanti kapsamı ve geçerli belgesi doğrulanmadan “40 dk”, “1 yıl” veya belge doğrulaması kesin vaat olarak ilk ekrana taşınmaz. Arayüz süreyi görüşmeye, yazılı koşulları istemeye ve belge kapsamını sormaya yönlendirir.
