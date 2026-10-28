# Sağlam Teknik — Hibrit Matris Sistemi Teknik Raporu

**Kontrol tarihi:** 28 Ekim 2026  
**Kapsam:** Kaynak kod, üretim paketi ve güvenli GitHub önizlemesi. Canlı `saglamkombiklima.com.tr` sunucusuna bu çalışmayla yükleme yapılmaz.

## 1. Uygulanan mimari

Çalışma, son yüklenen `a1.zip` içindeki dosyalara uygulanır. Kaynağın SHA-256 özeti:

```text
1e80b965aea63e83311acd02134d5b478b235f3a6324aa50755136597a959f41
```

576 kaynak dosyanın baytları doğrulanarak okunur; eski bir derleme çıktısının sessizce yeniden yayımlanması önlenir. İçerik, eşleştirme, bağlantılar, yapılandırılmış veri ve yükleme optimizasyonları aynı derleme hattında üretilir. `build-info.json` yayımlanan dosyaların gerçek içerik özetini taşır. Üretim ZIP’i deterministik biçimde oluşturulur; ZIP bütünlüğü ve dosya manifesti kontrol edilir.

Ana tasarım, mevcut adresler ve teknik arıza tabloları korunur. **25 ilçe için 50 kombi/klima sayfası, 5 semt sayfası ve mevcut 599 mahalle kaydı** aynı sistem içinde çalışır. Kombinasyon sayısını artırmak için binlerce yeni, birbirinin benzeri URL oluşturulmaz.

## 2. Bölge içeriği ve mahalle matrisi

`hybrid/data/regions.json` ilçelerin mahallelerini, komşuluk verisini, giriş paragraflarını, adres notlarını ve ilgili belirti rehberlerini tek kaynaktan yönetir. `hybrid/regions.py` bu verileri **derleme sırasında okunabilir HTML’ye** dönüştürür. Tarayıcıdaki JavaScript seçimleri kolaylaştırır; arama motorunun okuyacağı ana içerik JavaScript’in çalışmasına bağlı değildir. JavaScript geliştirmesi başarısız olduğunda bölge metni ve bağlantılar kalır.

50 ilçe servis sayfası ve 5 semt sayfası için 55 ayrı giriş paragrafı hazırlandı. İlçe/mahalle isimlerini değiştirerek aynı girişin çoğaltılması yerine adres ayrımı, sıcak su/ısıtma davranışı, kullanım modu ve güvenli gözlem gibi farklı servis kararları anlatılır. Apartman, site veya iş yeriyle ilgili bilgiler koşullu sorular olarak kullanılır; doğrulanmamış bina yoğunluğu, yerel arıza sıklığı, tamamlanmış iş veya kesin varış süresi iddiası üretilmez.

Mahalle seçimi artık yalnızca boş bir talep formuna göndermez. Bölgeler ekranındaki **1.797 mahalle bağlantısı**, ilgili cihazın ilçe içeriğine ve mahalle işaretine gider. İlçe sayfalarında **1.198 mahalle işareti** bulunur: 599 kaydın kombi ve klima karşılıklarıdır; 1.198 bağımsız mahalle sayfası değildir. Kullanıcı buradan belirti rehberine, marka/model bilgisine ve isterse servis talebine ilerler.

599 kayıt eski sitenin korunan hizmet envanteridir; güncel belediye kayıtlarının tamamının yeniden doğrulandığı iddiası değildir. Sokak listesi veya adres bilgisi uydurulmadı. Beşiktaş’taki Arnavutköy ile Arnavutköy ilçesi, Zeytinburnu’ndaki Maltepe ile Maltepe ilçesi gibi karışabilecek konumlar ayrı değerlendirilir. 500 Evler ve Merter gibi kullanımlarda açık ilçe bilgisi istenir.

Komşuluk listesi OpenStreetMap kaynaklı ilçe geometrilerinde ortak kara sınırı çizgilerinin karşılaştırılmasıyla türetilmiştir. Kaynak özeti, yöntem ve ODbL 1.0 lisans bilgisi veri dosyasına; atıf metni bölge alanına eklendi. Bu liste hukuki sınır tespiti, sürüş rotası, servis sırası veya varış süresi değildir.

## 3. Çapraz bağlantılar ve arama eşleştirmesi

`hybrid/hubs.py`, bölge → marka/model → belirti rehberi → bölge/hizmet akışlarını HTML bağlantılarıyla kurar. Mevcut kontrol çıktısında 175 sayfada 1.449 bağlamsal bağlantı üretilmiştir. Dizine uygun 187 içerik sayfasının tamamına site içinden ulaşılır; bu envanterde yetim sayfa yoktur. Yönetim, doğrulama, 404 ve kişiye özel takip adresleri içerik sayfası sayılmaz.

İlçe sayfalarında 55 seçim bileşeni bulunur. Cihaz, marka, model, mahalle ve belirti aynı bağlamda ilerler. Model veya özel açıklama zorunlu değildir. Cihaz değiştirilince önceki cihazdan kalan model/kod temizlenir. Bilinmeyen model yazılabilir; kodun anlamı doğrulanamadığında farklı modelden açıklama taşınmaz.

JavaScript ve PHP arama tarafındaki bağıl yol uyuşmazlığı giderildi. İlçe/model bulunduğu hâlde genel sayfaya düşme sorunu düzeltildi. Yayımlanmayan bir dosyaya yönlendirme yapılmasını önleyen gerçek dosya denetimi eklendi. Kelime sırası esnekliği belirti/hizmet ifadelerinde kullanılır; model isimleri benzerlik üzerinden gelişigüzel eşitlenmez.

Gerçek eşleştirme kodunda kontrol edilen örnekler:

| Sorgu | Açılan içerik |
| --- | --- |
| Küçükçekmece Baymak kombi servisi | `kucukcekmece-kombi-servisi.html` |
| Avcılar Bosch kombi vermiyor sıcak su | `kombi-sicak-su.html` |
| Baymak kombi altından su geliyor | `kombi-su-akitiyor.html` |
| Şişli Vaillant kombi ateşleme arızası | `kombi-atesleme.html` |
| Küçükçekmece petek temizliği | `petek-temizligi.html` |
| Vaillant ecoTEC pro VUW TR 236/5-3 F22 hata kodu | İlgili model sayfasındaki `#kod-f22` başlığı |

Ek olarak 875 ilçe × kombi markası seçimi ve 599 mahalle eşleşmesi kontrol edildi. E1/E01 ve F4/F04 yazımları yalnız seçili modelde çelişkisiz aynı kayda karşılık gelirse eşleşir; E10 ayrı kalır. Belirsiz Maltepe, Kadıköy veya Cumhuriyet araması sessizce başka ilçenin mahallesine atanmaz. Bu, site içi eşleştirme kapsamıdır; Google’ın her sorguda bu sayfayı göstereceği anlamına gelmez.

## 4. Teknik bilgi, yayın kapsamı ve dış bağlantılar

Kaynakta bulunan **86 model arıza tablosu ve 1.443 kod başlığı** korunmuştur. Üretilen katalogdaki 521 yol ve 1.006 kod işareti kontrol edilmiştir. Bu sayılar bütün markaların geçmiş ve güncel bütün modellerinin doğrulandığı anlamına gelmez. Model/belge/pazar kapsamı korunur; doğrulanmamış kodlara kesin anlam eklenmez. Gaz, yangın veya patlama benzeri ateşleme durumlarının güvenli yönlendirmesi sıradan ses açıklamasından önce değerlendirilir.

Üretici kaynakları belge adı, kapsam ve referans bilgisiyle korunur. 2.108 dış web gezinti bağlantısı düz metin referansına çevrilmiştir. Statik kabul kontrolünde WhatsApp dışındaki dış web bağlantısı sıfırdır; telefon ve WhatsApp iletişim katmanı korunur. Bu kural, sunucunun gerekli Gemini veya Telegram API bağlantılarını kaldırmaz.

Önceki hizmet kararı doğrultusunda klima montajı ve sökümü aktif teklif akışından çıkarılmıştır. Eski iki URL silinip 404’e dönüştürülmek yerine noindex bilgilendirme sayfası olarak korunur ve sitemap envanterine alınmaz.

## 5. Yapılandırılmış veri, bot erişimi ve envanter

İşletme kimliği tek `https://saglamkombiklima.com.tr/#business` adresinde tutarlıdır. Kullanıcının verdiği **İnönü Mahallesi, Küçükçekmece, İstanbul, TR** adresi `LocalBusiness/HVACBusiness` verisine işlendi. Sokak/bina numarası veya koordinat eklenmedi; adres kapsamı verilenden daha ayrıntılı gösterilmedi. Fiyat aralığı ve değerlendirme puanı uydurulmadı.

Kontrol edilen üretim çıktısında 201 sayfada işletme verisi, uygun 179 sayfada `Service`, 179 sayfada görünür içerikten türetilen 241 soru-cevap için `FAQPage` vardır. Gizlilik veya yönetim sayfasına ilgisiz servis şeması eklenmez. Eski `#isletme`, `#hizmet` ve soru-cevap referansları yeni kimliklerle uyumlu hâle getirilir. Görünür soru/cevap ile şemadaki metin eşleşmesi denetlenir.

Sitemap, `llms.txt` ve `assets/hybrid-inventory.json` aynı gerçek canonical envanterinden üretilir. **Bu sürümde sayı 187’dir; 192’ye tamamlamak için hayali sayfa eklenmemiştir.** Önceden noindex olan yabancı pazar rehberlerinin korunan kapsamı sitemap dışında kalır. Ayrıntılı `llms-full.txt` saklanır. Üretim robots kuralları içerik erişimine izin verir; özel dosya ve API engellerini korur.

`llms.txt` işletme özetini, yetkili servis dışı konumu, model/kod sınırlarını, iletişimi ve gerçek içerik listesini sunar. Bu dosya Google’da sıralama kontrolü değildir. FAQ verisinin doğru olması da Google’da zengin sonuç garantisi sağlamaz; Google FAQ zengin sonuç özelliği Mayıs 2026’da sona ermiştir. ChatGPT, Gemini, Claude veya Copilot’un işletmeyi önermesi garanti edilmez.

## 6. Hız, mobil kullanım ve Ads hazırlığı

İlk ekranın gerekli görselleri öncelikli tutulur; aşağıdaki görseller uygun `loading="lazy"` ve `decoding="async"` ayarlarıyla yüklenir. Yerel font alt kümeleri önceden yüklenir, mevcut `font-display: swap` korunur. Kullanılmayan birebir aynı kök dosyalar kaldırılır; bağımlı JavaScript sırası korunur. İkon CSS’i 102.521 bayttan 16.783 bayta indirildi; sitede kullanılan 10 ikon sınıfının hesaplanan görünümü karşılaştırıldı ve başvurulan sekiz glif kuralı korundu. Erişilebilirlik için renk karşıtlığı da düzenlendi.

Ana sayfadaki üç büyük arıza/model veri dosyası başlangıç zincirinden ayrıldı: yaklaşık **1,38 MB** veri AI Usta gerektiğinde yüklenir. Geciken veya başarısız veri isteğinde statik rehberler ve güvenli alternatif kullanılabilir. Gerçek tarayıcıda geciktirilmiş ilk veri isteği, yükleme tamamlanması ve başarısız kaynak durumları kontrol edildi.

Yerel Lighthouse 13.6.0 ile aynı mobil/simüle kısıtlama ayarlarında yapılan tek eski/yeni ana sayfa karşılaştırması:

| Ölçüm | Kaynak ana sayfa | Hibrit önizleme |
| --- | ---: | ---: |
| Performance | 87 | 93 |
| Accessibility | 97 | 100 |
| Best Practices | 100 | 100 |
| Aktarılan toplam veri | 2.420.955 bayt / 2.364 KiB | 781.753 bayt / 763 KiB |
| FCP | 3,2 sn | 2,6 sn |
| LCP | 3,2 sn | 2,6 sn |
| Total Blocking Time | 0 ms | 0 ms |
| CLS | 0 | 0,049 |

Bu yerel deneyde aktarılan veri %67,71 azalmış, performans puanı 87’den 93’e çıkmıştır. Önizlemede LCP öğesi test uyarı şerididir; kaynak sayfadaki LCP öğesinden farklıdır. Bu nedenle 3,2→2,6 sn LCP karşılaştırması canlı üretim sitesinin LCP kazanımı olarak sunulamaz. Önizlemenin Lighthouse SEO puanı 66’dır; kasıtlı noindex/robots kısıtlamasını içerir. Üretim HTML’sinin ayrı yerel Lighthouse SEO denetimi 100 puan almıştır; bu denetimde PHP çalıştırılmamıştır ve sonuç Google’ın sayfaları dizine aldığını göstermez. Bunlar canlı PageSpeed, gerçek kullanıcı Core Web Vitals veya tüm sayfaların hız puanı değildir; “tam puan” sonucu çıkarılamaz.

İlgili servis açılış sayfası, açık iletişim, cihaz/belirti eşleşmesi ve mobil kullanılabilirlik Ads açılış deneyimini destekler. Reklam hesabına bağlanılmadı; kampanya, dönüşüm etiketi veya reklam bütçesi değiştirilmedi. Ads Quality Score ve müşteri dönüşümü ölçülmedi.

## 7. Kontrol kanıtları ve teslim sınırı

- Statik üretim kabulü: 187 içerik/sitemap adresi, 21.195 iç dosya/işaret referansı; yetim içerik, eksik hedef ve schema/metin uyuşmazlığı bulunmadı. Dosya özeti doğrulandı; sınırlı anahtar deseni taramasında eşleşme yoktu.
- 39 Python birim testi; eşleştirme, bölge verisi, iç bağlantı, schema, yükleme, emekliye ayrılan servisler ve kabul kuralları. Üretim paketindeki 23 PHP dosyasının sözdizimi kontrol edildi. Gerçek PHP çözümleyicisinde yedi örnek, JavaScript tarafında 18 örnek ile uyum denetimi geçti. PHP regresyonu özel ayar veya dış ağ gerektirmeden çalıştırıldı.
- Yerel Chromium’da 204 ziyaretçi sayfası 360 ve 768 pikselde açıldı. Bu taramada JavaScript hatası, kaynak HTTP hatası, bozuk görsel veya yatay taşma görülmedi. Son ana sayfa kontrolünde mobil/masaüstü AI Usta ve Yorumlar hedefleri ayrıca açıldı.
- Yeni matris seçimleri, model bilinmiyor seçeneği, özel modelin isteğe bağlı kalması, sıfırlama, klavye kullanımı, cihaz değişikliği ve JavaScript geliştirmesi yokken statik içerik kontrol edildi.

**Bu kontroller canlı Telegram teslimi, Gemini cevabı, sunucudaki form kaydı veya Search Console sonucu değildir.** GitHub önizlemesi bilerek noindex durumundadır; form, konum ve sağlayıcı gönderimleri kapalıdır. Üretim ZIP’i canlı sunucu için ayrı derlenir ve bu önizleme kısıtlarını taşımaz. Canlı sunucuya otomatik geçiş yapılmaz.

Canlıya geçişte mevcut özel yapılandırma ve veritabanı korunarak üretim paketi yüklenmeli; gerçek PHP/form/Telegram/Gemini bağlantıları sunucuda doğrulanmalıdır. Ardından sitemap erişimi ve önemli ilçe/rehber URL’leri Search Console’dan kontrol edilmelidir. Dizine alınma, sıralama, reklam puanı ve iş sayısı bu raporla garanti edilmez.

## 8. Yeniden üretme ve kanıt dosyaları

```sh
python hybrid/build.py --mode production --output build/hybrid-production --zip build/saglam-teknik-hibrit.zip
python hybrid/audit.py build/hybrid-production --mode production
python -m unittest discover -s hybrid/tests -p 'test_*.py'
```

Raporun sayısal dayanakları: `build-production-log.json`, `acceptance-production.json`, `matching-final.json`, `matrix-browser.json`, `browser-audit.json`, `diagnostics-loader-browser.json`, `home-final-check.json` ve `lighthouse-comparison.json`. Bunlar farklı kapsamları ölçer; ekran sayısı, test sayısı ve işlevsel sağlayıcı teslimi aynı başarı ölçüsü olarak birleştirilmemiştir.
