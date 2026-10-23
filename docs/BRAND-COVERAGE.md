# Ortak marka ve tedarikçi kapsamı

Kontrol: **23 Ekim 2026**. Tek düzenlenebilir kaynak `overrides/assets/brand-registry.json` dosyasıdır. Mevcut 54 kimlik korunmuş, dört kimlik ve eksik cihaz türleri eklenmiştir: **58 kimlik, 35 kombi ve 37 klima seçeneği**. Bu sayı dünya çapındaki bütün markaların eksiksiz envanteri değildir.

Marka seçebilmek, cihazın her modeline servis verilebildiği veya kodlarının doğrulandığı anlamına gelmez. `service_intake:true` belirtinin alınabileceğini; `service_status:"model-confirmation-required"` işlem/parça uygunluğunun tam modelle görüşüleceğini anlatır. Yetkili servis veya üretici bağlantısı iddiası içermez.

## Eklenen kapsam ve kanıt

| Kayıt | Cihaz | Birincil kaynak ve sınır |
|---|---|---|
| Isısan | Kombi, klima | [Rekabet Kurumu 07-01/10-5](https://www.rekabet.gov.tr/Karar?kararId=e5d4a975-b3bd-49df-a4b1-b514b6b9e7c6), H.2.1, basılı s.4; [resmî dergi s.65](https://www.rekabet.gov.tr/Dosya/dergi/33-pdf). Tarihî dağıtım/tedarik şirketi; `kind:"legacy_supplier"`. Cihaz etiketindeki gerçek ürün markası gerekir. Bosch/Buderus model veya kod eşdeğeri değildir. Kararın indekslenmiş metni okundu; canlı karar sayfası araçta 418 döndürdü. |
| ECA | Klima | [Türkiye Ecotech ürün sayfası](https://eca.com.tr/urun/ecotech-serisi-duvar-tipi-klima). Önceden yalnız kombi listesinde bulunuyordu. |
| Vaillant | Klima | [Türkiye klima ürün kataloğu](https://www.vaillant.com.tr/urunler/klimalar/). Önceden yalnız kombi listesinde bulunuyordu. |
| Daylux | Kombi, klima | [Daylux ürün kataloğu](https://daylux.com.tr/); [Daikin Türkiye kombi kapsamı duyurusu](https://www.daikin.com.tr/daikin-kis-gelmeden-kombinizin-bakimini-yaptirin-daikinden-avantajli-bakim-kampanyasi). |
| Kaira | Klima | [Daikin Türkiye Kaira ürün sayfası](https://www.daikin.com.tr/yeni-kaira-9000-btuh-duvar-tipi-r32-inverter-split-klima_183421). |
| Daxom | Kombi | [Üretici elektrikli kombi kataloğu](https://www.daxom.com/urunler/elektrikli-kombiler). Elektrikli cihaz kapsamıdır; doğalgazlı model varsayılmaz. |

Bu eklemelerle yeni model adı, hata kodu açıklaması veya SEO sayfası üretilmemiştir. Önceki marka kayıtlarının kaynağı `provenance:"existing-site-catalog"` olarak korunur; bu çalışma onları yeniden üretici belgesiyle doğruladığını iddia etmez. İklimsa mevcut kaydı bir servis/satış ağı olarak `service_network` türündedir.

## Tek kaynaktan üretim

`scripts/brand_registry.py:build_registry(files)` şu çıktıları aynı kaynaktan üretir:

- `assets/brand-registry.json` ve `assets/brand-registry.js`: `ST_BRAND_REGISTRY` verisi ve `STBrands.list(device)`, `.names(device)`, `.find(name,device)` API'si.
- `assets/servis-katalog.json` ve `assets/servis-verileri.js`: PHP arama, ön yüz arama ve eski seçiciler için aynı cihaz/marka listeleri ve yazım alternatifleri.
- `markalar.html` marka listeleri; AI Usta ve model tarayıcısı aynı `STBrands` API'sini kullanır.

`guides_by_device`, `verified_model_ids` ve `guide_count` yalnız mevcut `verified-faults.json` kayıtlarıyla derleme sırasında birleştirilir. Mevcut **93 belge ailesinin** model, pazar, kontrolör ve kod kapsamına dokunulmaz. Marka kaydı bulunmayan yeni bir model ailesi derlemeyi durdurur; listelerin sessizce ayrışmasına izin verilmez. Kılavuzu olmayan seçenekte model tarayıcısı bunu açıkça belirtir ve marka bilgisiyle AI Usta'nın belirti akışına geçer.

## Açık kalan kapsam

Isısan için ayrı üretici/model hata kodu kataloğu doğrulanmadı. Yeni ECA/Vaillant klima, Daylux, Kaira ve Daxom cihaz kapsamlarında doğrulanmış model kodu tablosu eklenmedi. Bunlar başka markanın tablosuna bağlanmaz.

Ek aramada Buderus Logacool için yabancı pazar katalogları bulundu; Türkiye kapsamı doğrulanmadığından klima listesine eklenmedi. Demrad için resmî kaynak kazan/radyatör kapsamını gösterdi; ev tipi kombi/klima kabul edilmedi. Chaffoteaux için grup marka kimliği doğrulandı ancak Türkiye cihaz kapsamı kurulamadı. Auer için kullanılabilir birincil kaynak bulunamadı. Bu kayıtlar eksiksizmiş gibi yayımlanmaz.

Doğrulama: `python -m unittest discover -s tests -p 'test_brand_registry.py'`; tarayıcı akışları `tests/brand_registry.cjs` ile, PHP marka/kod kapsamı `php tests/brand_registry.php build/production` ile kontrol edilir. Son çalıştırma: 6 birim testi, 21 tarayıcı kontrolü ve 8 PHP sorgusu geçti; üretim/ön izleme bağlantı kontrollerinde hata yok.
