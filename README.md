# Sağlam Teknik — Premium test sitesi

Bu depo yalnızca GitHub Pages test ön izlemesidir. Ana siteye, alan adına veya canlı müşteri verilerine otomatik yayın yapmaz. Ön izleme adresi: https://saglamteknikk2-afk.github.io/site/

## Düzenlenebilir kaynaklar

- `overrides/`: yeni ana sayfa, CSS, JavaScript, görseller ve public veri dosyaları. Aynı yoldaki arşiv veya sunucu dosyasının üzerine yazar.
- `components/`: bütün ziyaretçi sayfalarının ortak başlık ve alt bilgi parçaları.
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
