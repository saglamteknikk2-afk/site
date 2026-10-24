# Sağlam Teknik — Premium test sitesi

Bu depo yalnızca GitHub Pages test ön izlemesidir. Ana siteye, alan adına veya canlı müşteri verilerine otomatik yayın yapmaz. Ön izleme adresi: https://saglamteknikk2-afk.github.io/site/

## Düzenlenebilir kaynaklar

- `overrides/`: yeni ana sayfa, CSS, JavaScript, görseller ve public veri dosyaları. Aynı yoldaki arşiv veya sunucu dosyasının üzerine yazar.
- `components/`: bütün ziyaretçi sayfalarının ortak başlık ve alt bilgi parçaları. `brand.json` kullanıcının sağladığı temiz mavi S kurdele logosunun ve favicon’un tek yol kaynağıdır. Önceki alev-buz başvuruları da bu özgün logoya dönüştürülür.
- `overrides/assets/brand-registry.json`: AI Usta, model kütüphanesi, markalar ve servis seçimlerinin ortak marka kaynağı. Doğrulanmış model belgeleri ayrıca mevcut katalogdan bağlanır; marka eklemek kod tablosu üretmez.
- `server/`: yalnızca üretim paketine alınan PHP ve özgün sunucu dosyaları. İçeriği üretim web köküne taşınır; `/server/` URL'si oluşturulmaz.
- `templates/private/`: boş yapılandırma örnekleri; web köküne kopyalanmaz. Gerçek anahtar, müşteri kaydı veya veritabanı depoya konmaz. `templates/business-maps-section.html` yalnızca sayfa parçasıdır.
- `preview-parts/part-000.txt` … `part-042.txt`: önceki statik sürümün değişmeyen ZIP arşivi. Yeni sayfa düzenlemek için bu parçaları değiştirmeyin.
- `scripts/production-seo.json`: statik dışa aktarmada çıkarılan özgün canonical ve yapılandırılmış veri etiketleri. Düzenlenen sayfanın kendi etiketleri varsa onlar korunur.

Python 3.10+ yeterlidir; derleme için paket kurulumu gerekmez. `chunk-*.txt` eski dosyaları derlemeye dahil edilmez.

## Yerel ön izleme

```sh
python scripts/build_site.py --mode preview --output _site --base-path /site
python scripts/check_site.py _site --mode preview --report build/preview-check.json
python -m unittest discover -s tests -p 'test_*.py' -v
```

`_site/` içeriğini `/site/` yolunda sunun. Yerel sunucunuz kökten sunuyorsa `--base-path /` ile yeniden derleyin. Bütün ziyaretçi sayfaları `noindex,nofollow,noarchive` taşır. `robots.txt` taramaya izin verir; böylece arama motorları `noindex` etiketini görebilir.

Ön izleme PHP, yönetim ekranı, gizli ayarlar veya veritabanı içermez. Form, konum, Telegram/WhatsApp/e-posta ve API gönderimi kapalıdır; başarı veya kayıt yapılmış gibi gösterilmez. Model, kod ve bölge araması gibi tarayıcı içi özellikler kullanılabilir. Tamamen yerel çalışan arama formları `data-preview-local="true"` ile işaretlenir. Modül kodları `window.ST_PREVIEW` veya `body[data-st-mode="preview"]` ile modu anlayabilir.

## Üretim paketini incelemek

```sh
python scripts/build_site.py --mode production --output build/production
python scripts/check_site.py build/production --mode production --report build/production-check.json
```

Bu komutlar **yayın yapmaz**. Üretim paketi `/site/` önekini kaldırır, PHP dosyalarını ekler, ön izleme kilidini kaldırır ve özgün SEO etiketlerini geri getirir. Gerçek özel yapılandırma web kökünün dışında ayrıca hazırlanmalıdır. Canlı sunucuya taşıma, alan adı ve TLS işlemleri bu deponun otomasyonunda bulunmaz.

GitHub Actions; `overrides/`, `components/`, `server/`, testler, scriptler ve belgeler değiştiğinde derleme ve kontrolleri çalıştırır. Pull request'ler yayın yapmaz. `main` dalı yalnızca GitHub Pages ön izlemesini günceller. Actions → **Run workflow → production_package** seçeneği indirilebilir üretim taslak ZIP'i oluşturur; canlı siteye yüklemez.

Derleme sırası: SHA-256 doğrulanan arşiv → üretimde `server/` → `overrides/` → ortak parçalar ve moda göre URL/SEO/gönderim ayarları. Aynı kaynaklardan aynı içerik özeti üretilir; tarih veya ortam yolu çıktı içeriğine eklenmez.

Özgün arşiv SHA-256: `1e1af83e7bc6233f8af88f89a5873440288caed73cb4173483106f050ec5eb7b`.

## Premium tasarım ve organik içerik denetimi

Ana sayfa servis türü, telefon/WhatsApp ve tek AI Usta akışıyla başlar. Marka ve tam model önerileri aynı arama alanından ilerler; belge kapsamı kullanıcı onayı olmadan doğrulanmış sayılmaz.

`components/service-assurances.json` varış, garanti ve mesleki belge beyanlarının durumunu yönetir. `pending` bir beyan kesin bir süre veya garanti olarak yayımlanmaz. Bölgesel süre koşulları, garanti kapsamı ve geçerli mesleki belge işletmeden teyit edilmeden `verified` yapılmamalıdır.

`python scripts/audit_content.py build/production --strict --report build/content-audit.json` yalnız ziyaretçi HTML ana içeriğini tarar. Kopya sinyalleri editoryal inceleme içindir; Google/AI sıralama puanı değildir. Kaynak, güvenlik ve ortak gezinme metni gerekli yerlerde korunur. Strict mod kaynak/FAQ/JSON-LD/ana içerik bütünlüğünü ve tam gövde klonlarını denetler. Pages iş akışı hem önizlemeyi hem üretim dosyalarını doğrular; yalnız test sitesi yayımlanır.

`assets/ad-landing-map.json` derlemede mevcut servis adreslerinden üretilir. Reklamın nihai URL’si ilgili servis sayfası olmalıdır; kelime sırasına göre yeni sayfa veya otomatik yönlendirme oluşturulmaz. İlgili sayfalardaki WhatsApp taslağı hizmet başlığını ve sayfa adresini taşır. Bu harita reklam hesabı, bütçe veya dönüşüm ölçümü bağlantısı kurmaz. `site-zip.yml` kaynak değişikliklerinde güncel üretim ZIP artifact’ini hazırlar; ana siteye yüklemez.

## İç bağlantılar ve işlev testleri

`python scripts/internal_links.py build/production --check --report build/crawl-check.json` yalnız gerçek HTML bağlantılarından sayfa grafiğini çıkarır. Üretimdeki bütün dizine uygun sayfaların ana sayfadan en fazla üç bağlantıda bulunmasını kontrol eder. Bu kontrol Google'ın sayfayı taradığı veya dizine aldığı anlamına gelmez.

`tests/interactions.cjs` her ziyaretçi sayfasının tarayıcıda oluşan denetimlerini listeler; tek tek tıklanan düğmeler, doğrulanan bağlantı hedefleri, gizli durumlar ve ayar bekleyen denetimler ayrı raporlanır. `python tests/run_model_checks.py` tek AI Usta akışı, marka kimliği ve kaynak kapsamı kontrollerini izole kök önizlemede çalıştırır. PHP için `php tests/business-runtime.php`, `php tests/brand_registry.php build/production` ve `php tests/backend-http.php build/production` sentetik veri ve yerel sunucu kullanır; gerçek müşteri veya sağlayıcıya ileti göndermez.

Yayın ve Search Console adımları `docs/INDEXLEME-REHBERI.md` içindedir.

`node tests/backend_browser.cjs build/production` gerçek arayüzü geçici PHP sunucusu ve SQLite ile birlikte çalıştırır. API yanıtları taklit edilmez; üretim anahtarları kullanılmaz. PHP çalıştırıcısı gerekirse `SAGLAM_PHP_BIN` ile seçilir.
