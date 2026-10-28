# Sağlam Teknik hibrit içerik sistemi

Bu dizin, kullanıcının 28 Ekim 2026 tarihinde yüklediği `a1.zip` dosya ağacını
temel alan üretim ve GitHub Pages önizlemesinin düzenlenebilir kaynağıdır.
Tasarım ve mevcut ziyaretçi URL'leri korunur. Bölge içeriği JSON'dan derleme
sırasında HTML'ye yazılır; JavaScript filtreleri bu HTML'yi tamamlar.

## Tekrarlanabilir kaynak

`data/base-a1.patch.json.gz`, depoda zaten bulunan değişmez görselleri yeniden
yüklemek yerine mevcut `saglamkombiklima-seo.zip` arşivinin dosya farklarını
kaydeder. `source.py` elde edilen **576 dosyanın her birinin SHA-256 değerini**
yüklenen a1 dosyasıyla karşılaştırır. Bir bayt farklıysa derleme durur.
Orijinal a1 arşivi eldeyse `--source /path/a1.zip` doğrudan aynı ağacı kullanır.
Arşiv SHA-256 değeri: `1e80b965aea63e83311acd02134d5b478b235f3a6324aa50755136597a959f41`.

## Üretim ve önizleme

```sh
python hybrid/build.py --mode production --output build/production --zip build/saglam-teknik-hibrit.zip
python hybrid/build.py --mode preview --output _site
python -m unittest discover -s hybrid/tests -p 'test_*.py'
python hybrid/audit.py build/production --mode production --report build/production-audit.json
python hybrid/audit.py _site --mode preview --report build/preview-audit.json
node hybrid/tests/test_matching.cjs build/production build/matching-js.json
php hybrid/tests/test_matching.php build/production build/matching-js.json
```

`hybrid-matrix.yml` bu kaynağı yayımlar; eski `scripts/build_site.py` yeni hibrit
üretim paketi için kullanılmaz. Eski kaynak ve kullanıcı commit'leri silinmez.
Özel ayarlar veya müşteri veritabanı bu kaynakta/dağıtımda bulunmaz.

- Üretim: PHP ve mevcut özel dosya okuyucusu korunur; test koruması eklenmez.
- GitHub Pages: PHP ve yönetim dosyaları çıkarılır; noindex ve gönderim koruması uygulanır.
- Teknik rapor: `teknik-rapor.html`, arama dizinine kapalı.
- Üretim ZIP'indeki `build-info.json` dosyası içerik ağacını doğrular; ZIP özeti
  arşivin dışında `.zip.json` içinde verilir, arşivin kendi özeti içine yazılmaz.

## Verinin anlamı

599 mahalle mevcut hizmet kataloğudur; güncel resmî idari envanter olduğu iddia
edilmez. Komşuluk türev verisi ve ODbL atfı `data/regions.json` içinde açıklanır.
Model kodları yalnız mevcut üretici belge kapsamıyla eşleştirilir. Her marka,
model ve hata kodunun eksiksiz doğrulandığı veya her sorguda sıralama alınacağı
iddia edilmez. `llms.txt` gerçek canonical envanterinden üretilir; 192'ye yapay
olarak tamamlanmaz.

Hız kontrolleri yerel Chromium/Lighthouse ölçümleridir; canlı PageSpeed, saha
Core Web Vitals, Ads Quality Score ve gerçek Telegram/Gemini teslimi ayrı
kanıt gerektirir. Dosya denetimleri bunların yerine geçmez.
