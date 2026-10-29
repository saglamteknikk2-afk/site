# Sağlam Teknik — Hibrit Matris Sistemi Teknik Raporu

**Kontrol tarihi:** 29 Ekim 2026  
**Kapsam:** Kaynak kod, üretim paketi ve güvenli GitHub önizlemesi. Canlı `saglamkombiklima.com.tr` sunucusuna bu çalışmayla yükleme yapılmaz.


## VIP, müşteri takibi, butonlar ve model kataloğu onarımı

VIP ücret onayı, seçilmiş mahalle arıza metnine eklendiği hâlde aynı formun ham alanıyla karşılaştırıldığı için yanlışlıkla geçersiz oluyordu. Mahalle dahil tutarlı alan görüntüsü kullanılır; değişmeyen otomatik doldurma onayı bozmaz. Gerçek alan değişikliği ve geç gelen eski yanıt yeniden onay gerektirir. Ücret sunucuda imzalanır: 08.00–21.00 2.500 TL, 21.00–08.00 4.000 TL; açık son kabul olmadan kayıt oluşmaz.

Telegram'da kabul, yola çıkış, tahmini dakika ve serbest mesaj işlemleri kalıcı müşteri olaylarına yazılır. Aynı güncellemenin tekrar gelmesi ikinci olay oluşturmaz. Eski bir işin açık yolda kaydı yeni açık operatör güncellemesini engellemez. Grup gizliliğinde süre ve mesaj yanıtının alınması için belirli isteme ForceReply ile yanıt istenir; eski istem başka müşteriye uygulanmaz. Hata Telegram'da açıklanır. Müşteri özel takip ekranı bu olayları API'den okur.

Takip ekranı **sayfayı yeniden yüklemeden 3 saniyede bir** güncellenir; çakışan istekler engellenir, gizli sekmede durur. Günlük rapor **İstanbul saatiyle 23.00 itibarıyla günün toplamı** olarak hazırlanır; gece yarısında yinelenmez. Tam saatinde teslim için mevcut sunucu cron/worker'ı düzenli çalışmalıdır; trafik yedeği yalnız istek geldiğinde çalışabilir. Gerçek sunucunun cron ayarı bu çalışma ortamından değiştirilmedi.

Koyu zemindeki koyu yazılar matris, AI sonuçları ve müşteri takip bağlantısında düzeltildi. Gerçek eski stillerde yaklaşık1,02–1,22:1 olan sorunlu karşıtlıklar; normal, üzerine gelme ve klavye odağı durumlarında en az8,25:1 ölçüldü.

Model tanıma kataloğu, rehber ekranı, AI Usta ve bölge matrisinde ortak kullanılır. Model/seri adları aynı modelin tekrar eden aile kartından ayrılır. Listede bir adın bulunması, o ürünün kodlarının doğrulandığını göstermez. Model bilinmeden veya kullanıcı kendi modelini yazarak ilerleyebilir.

Resmî Türkiye kılavuzlarından **13 yeni belge kapsamı,32 tam model varyantı ve432 modele bağlı kod açıklaması** eklendi. Vaillant pure `/7-2`, intro `AS/2-1` ve plus `CS/1-5`; Demirdöküm Atromix, ademiX/vintomiX AS/2 ve Nitron Condense; belirli Baymak Dolcevita/Duotec/Luna nesilleri ve Protherm Gepard Condens kapsamları belgelidir. Yeni kodlarda anlam, kaynak sayfası ve güvenli gözlem vardır; Vaillant kayıtlarında ayrıca ayrıntılı açıklama bulunur.

Bazı eski Vaillant adresleri artık başka ürünlerin PDF'lerini veya boş/yönlendirilmiş sayfa döndürüyor. Böyle bir adresin eski adına dayanarak yeni kod doğrulaması yapılmadı. **Bütün markaların bütün tarihsel modellerinin kodları doğrulanmış değildir.** Model adı kataloğu ile doğrulanmış kod belgesi ayrı olgulardır. Güncel toplamlar derlemenin `model_catalog` ve `semantics` kayıtlarında bulunur.

Paylaştığın Google yardım metni de her URL'nin dizine alınmasının beklenmediğini açıklar. Parametreli form/alternatif URL'nin ana adreste birleşmesi normal olabilir. “Tarandı” veya “Keşfedildi” etiketi tek başına kopya ya da ceza kanıtı değildir; sitenin gerçek URL Denetimi sonucu yerine genel dokümandan özel teşhis çıkarılmaz.

## Paylaştığın dizin listesindeki somut farklar ve yeni değişiklikler

29 Ekim'de yeniden yüklediğin ZIP önceki a1.zip ile bayt düzeyinde aynı. Karşılaştırma **44 dizine eklenmiş içerik, 64 eklenmemiş içerik ve 15 parametreli iletişim adresi** üzerinden yapıldı. Durum etiketleri senin listenden alındı; canlı Google URL Denetimi sonucu gibi sunulmaz.

Kaynak ZIP'te 108 içerik adresinin tamamı mevcut, kendi temiz canonical adresini taşıyor ve sitemap'te. Bunlarda noindex engeli yok. “Yok” ifadesi tek başına Google'ın hangi nedenle dışladığını belirtmiyor. Daha uzun metin veya yalnız bağlantı sayısı bu liste için kesin neden göstermez.

| Aynı türde karşılaştırma | Eklenen / eklenmeyen | Gelen farklı HTML sayfası medyanı |
| --- | --- | --- |
| İlçe servisi | 15 / 35 | 16 / 8 |
| Marka servisi | 6 / 10 | 36 / 36 |
| Hizmet / belirti | 11 / 14 | 42 / 40,5 |

İlçe girişlerindeki isim değişimli kalıplar iki grupta da var. Dizine giren şablonu kopyalamak çözüm olarak seçilmedi. Önceki 55 bölge gövdesi korunarak **16 marka ve 13 arıza/hizmet sayfasının da eski ana anlatımı bütünüyle değiştirildi**. Toplam 84 ayrı ana gövde; 358 bölüm paragrafı ve 168 özel soru-cevap HTML'ye işlendi ve birlikte tekrar kontrolünden geçirildi. Marka gövdesi ürün/belge kapsamını, arıza rehberi ise tek bir belirtinin güvenli değerlendirmesini anlatır.

Bosch/ECA sıcak su bölümlerindeki anlamsal yakınlık ayrı okuyucu tarafından fark edilince Bosch anlatımı önceki kaçak işleminin belge ve onarım onayına çekildi. Viessmann'ın kontrol ünitesi/işlem geçmişi, DemirDöküm'ün ısı dağılımı anlatımından ayrıldı. Klima metinlerinde normal yoğuşma/kaçak ve geçici buz çözme/belirti ayrımları açıklaştırıldı.

15 `iletisim.html?...` adresi ayrı mahalle sayfası değildir. Aynı formun seçimlerini taşır ve dizine eklenmiş temiz `iletisim.html` adresine canonical verir. Bu tercih korundu; sitemap'e kopya formlar eklenmedi. Gerçek mahalle gezinmesi ilçe sayfasındaki ilgili başlığa açılır. Klima montaj/söküm adresleri önceki hizmet kapsamı kararın nedeniyle noindex bilgi sayfası olarak kalır.

`dizin-inceleme.html` listesindeki her adres için eski/yeni canonical, robots, iç bağlantı sayımı ve yapılan değişikliği inceleyebilirsiniz. `icerik-inceleme.html` 84 değişen anlatımı eski/yeni yan yana gösterir. İki inceleme sayfası noindex'tir.

**İşlev hatası da düzeltildi:** Matrisin model, kod ve arıza seçimi servis sayfasına geçerken kaybolabiliyordu. Artık model/kod, ilçe/mahalle, marka ve belirti/işlem servis ekranında, WhatsApp metninde ve servis talebi yükünde korunur. Model isteğe bağlıdır. `/kombi-hata-kodu.h` için üretim Apache ayarına yalnız bu eski yolu kapsayan 301 yönlendirmesi eklendi; hedef mevcut `.html` sayfasıdır.

## 1. Uygulanan mimari

Çalışma, son yüklenen `a1.zip` içindeki dosyalara uygulanır. Kaynağın SHA-256 özeti:

```text
1e80b965aea63e83311acd02134d5b478b235f3a6324aa50755136597a959f41
```

576 kaynak dosyanın baytları doğrulanarak okunur; eski bir derleme çıktısının sessizce yeniden yayımlanması önlenir. İçerik, eşleştirme, bağlantılar, yapılandırılmış veri ve yükleme optimizasyonları aynı derleme hattında üretilir. `build-info.json` yayımlanan dosyaların gerçek içerik özetini taşır. Üretim ZIP’i deterministik biçimde oluşturulur; ZIP bütünlüğü ve dosya manifesti kontrol edilir.

Ana tasarım, mevcut adresler ve model rehberlerindeki teknik arıza tabloları korunur. **25 ilçe için 50 kombi/klima sayfası, 5 semt sayfası ve mevcut 599 mahalle kaydı** aynı sistem içinde çalışır. Kombinasyon sayısını artırmak için binlerce yeni, birbirinin benzeri URL oluşturulmaz.

## 2. Bölge sayfalarının ana gövdeleri yeniden yazıldı

Önceki sürümde girişler farklı olsa da 25 kombi sayfasındaki uzun özet ve tablo, yer adları çıkarıldığında aynıydı; 25 klima sayfasında da aynı sorun vardı. Yeni bölgesel notlar ise her cihaz grubu için beş metinden dönüşümlü üretilmişti. Bu düzen yalnızca girişlerin farklılaşmasını sağlıyor, ana gövdeyi bağımsız hâle getirmiyordu.

Bu sürümde 50 ilçe ve 5 semt sayfasının **eski ana içerik bölümü bütünüyle değiştirildi**. Ortak tanıtım, yer adları değiştirilmiş uzun tablolar ve dönen not havuzu kaldırıldı. Her sayfa için ayrı giriş, üç ana bölüm, sayfaya özel sorular ve cevaplar, kısa çıkarımlar ve servis çağrısı yazıldı. Toplam 55 ayrı gövde, 210 ana bölüm paragrafı ve 110 özel soru-cevap gerçek HTML içinde doğrulandı. Teknik arıza kodu tabloları kendi model rehberlerinde korundu.

Metinler `hybrid/data/editorial/batch-*.json` dosyalarında, gerçek mahalle ve komşuluk verisi `hybrid/data/regions.json` içinde yönetilir. `hybrid/editorial_regions.py` her sayfanın ana içeriğini derleme sırasında HTML'ye yazar. İçerik JavaScript çalışmasa da okunabilir; filtreler bu anlatımı tamamlar.

Örneğin Avcılar kombi gövdesi sıcak suyun hangi kullanımda kesildiğini; Küçükçekmece kombi gövdesi Sefaköy/mahalle adresiyle cihaz bilgisinin aynı kayıtta tutulmasını; Fatih kombi gövdesi yanma ve havalandırma belirtilerinde güvenli sınırları anlatır. Bu konular o ilçede yalnızca bu arızaların olduğu veya başka markalara hizmet verilmediği anlamına gelmez. Seçim akışı bütün mevcut marka ve belirti seçeneklerini korur.

Her gövde farklı bir okuyucu tarafından da incelendi. Birbirine fazla yakın bulunan Sarıyer ve Esenyurt klima anlatımları yeniden ayrıştırıldı; birkaç dil sorunu düzeltildi. Kilyos bağlantısındaki yanlış mahalle başlığı, kaynak kaydın gerçek `Kumköy (Kilyos)` adına göre düzeltildi.

Editöryal denetim, yer ve marka isimlerini kaldırarak uzun paragraf/cümle tekrarlarını ve yakın kopyaları arar. Yazılmış paragrafların gerçekten yayımlanacak HTML gövdesine işlendiğini, eski ortak blokların kaldırıldığını da kontrol eder. **Bu kontroller Google'ın bir özgünlük puanı değildir.** Ortak menü, iletişim, doğru teknik bilgiler ve model tabloları bu editöryal karşılaştırmanın dışında tutulur; bunları farklı göstermek için gerçekler değiştirilmez.

`icerik-inceleme.html` sayfasında 55 bölge ve bu sürümde yenilenen 29 marka/arıza rotasının eski anlatımı ve yeni gövdesi yan yana okunabilir. İnceleme arama dizinine kapalıdır. Böylece yalnızca test sayısı yerine yapılan metin değişikliğinin kendisi incelenebilir.

599 mahalle kaydı, kombi ve klima karşılıklarıyla 1.198 ilçe içi başlığa bağlanır. Bölgeler ekranındaki mahalle bağlantıları ortak forma değil ilgili içeriğe ulaşır. Aynı sayfada mahalleye tıklanınca filtredeki mahalle seçimi de güncellenir. Bunlar 1.198 bağımsız mahalle URL'si değildir. Kayıtlar eski sitenin hizmet envanteridir; güncel resmî belediye toplamı iddiası yoktur. Sokak veya bina verisi uydurulmadı.

Komşuluk verisi OpenStreetMap ilçe geometrilerindeki ortak kara sınırlarından türetilmiştir. ODbL kaynak/lisans atfı korunur. Bu veri rota, sıra veya varış süresi göstermez; yapılaşma yoğunluğu, arıza sıklığı veya yapılmamış iş örnekleri metne eklenmedi.

## 3. Çapraz bağlantılar ve arama eşleştirmesi

`hybrid/hubs.py`, bölge → marka/model → belirti rehberi → bölge/hizmet akışlarını HTML bağlantılarıyla kurar. Mevcut kontrol çıktısında 188 sayfada 1.578 bağlamsal bağlantı üretilmiştir. Dizine uygun 200 içerik sayfasının tamamına site içinden ulaşılır; bu envanterde yetim sayfa yoktur. Yönetim, doğrulama, 404 ve kişiye özel takip adresleri içerik sayfası sayılmaz.

Bölge sayfalarında 55, yenilenen marka ve arıza sayfalarında 29 seçim bileşeni bulunur. Marka sayfası kendi markasıyla, belirti sayfası ilgili sorunla başlar; ilçe sayfası kendi konumuyla açılır. Diğer seçimler açıktır ve marka hiçbir ilçeyle sınırlandırılmaz. Cihaz, marka, model, mahalle ve belirti aynı bağlamda ilerler. Model veya özel açıklama zorunlu değildir. Cihaz değiştirilince önceki cihazdan kalan model/kod temizlenir. Bilinmeyen model yazılabilir; kodun anlamı doğrulanamadığında farklı modelden açıklama taşınmaz.

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

Kaynakta bulunan **86 model arıza tablosu ve 1.443 kod başlığı** korunmuştur. Üretilen katalog yolları ve kod işaretleri gerçek dosyalara karşı kontrol edilir. Bu sayılar bütün markaların geçmiş ve güncel bütün modellerinin doğrulandığı anlamına gelmez. Model/belge/pazar kapsamı korunur; doğrulanmamış kodlara kesin anlam eklenmez. Gaz, yangın veya patlama benzeri ateşleme durumlarının güvenli yönlendirmesi sıradan ses açıklamasından önce değerlendirilir.

Üretici kaynakları belge adı, kapsam ve referans bilgisiyle korunur. 2.108 dış web gezinti bağlantısı düz metin referansına çevrilmiştir. Statik kabul kontrolünde WhatsApp dışındaki dış web bağlantısı sıfırdır; telefon ve WhatsApp iletişim katmanı korunur. Bu kural, sunucunun gerekli Gemini veya Telegram API bağlantılarını kaldırmaz.

Önceki hizmet kararı doğrultusunda klima montajı ve sökümü aktif teklif akışından çıkarılmıştır. Eski iki URL silinip 404’e dönüştürülmek yerine noindex bilgilendirme sayfası olarak korunur ve sitemap envanterine alınmaz.

## 5. Yapılandırılmış veri, bot erişimi ve envanter

İşletme kimliği tek `https://saglamkombiklima.com.tr/#business` adresinde tutarlıdır. Kullanıcının verdiği **İnönü Mahallesi, Küçükçekmece, İstanbul, TR** adresi `LocalBusiness/HVACBusiness` verisine işlendi. Sokak/bina numarası veya koordinat eklenmedi; adres kapsamı verilenden daha ayrıntılı gösterilmedi. Fiyat aralığı ve değerlendirme puanı uydurulmadı.

Kontrol edilen üretim çıktısında 214 sayfada işletme verisi, uygun 192 sayfada `Service`, 192 sayfada görünür içerikten türetilen 300 soru-cevap için `FAQPage` vardır. Gizlilik veya yönetim sayfasına ilgisiz servis şeması eklenmez. Eski `#isletme`, `#hizmet` ve soru-cevap referansları yeni kimliklerle uyumlu hâle getirilir. Görünür soru/cevap ile şemadaki metin eşleşmesi denetlenir.

Sitemap, `llms.txt` ve `assets/hybrid-inventory.json` aynı gerçek canonical envanterinden üretilir. **Bu sürümde sayı 200’dür; 192’ye tamamlamak için hayali sayfa eklenmemiştir.** Önceden noindex olan yabancı pazar rehberlerinin korunan kapsamı sitemap dışında kalır. Ayrıntılı `llms-full.txt` saklanır. Üretim robots kuralları içerik erişimine izin verir; özel dosya ve API engellerini korur.

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

Değişen CSS, JavaScript ve filtre verilerinin adreslerine gerçek dosya içeriğinden hesaplanan sürüm özeti eklenir. Böylece yeni HTML açıldığında tarayıcının eski uygulama kodunu önbellekten kullanması önlenir.

Bu yerel deneyde aktarılan veri %67,71 azalmış, performans puanı 87’den 93’e çıkmıştır. Önizlemede LCP öğesi test uyarı şerididir; kaynak sayfadaki LCP öğesinden farklıdır. Bu nedenle 3,2→2,6 sn LCP karşılaştırması canlı üretim sitesinin LCP kazanımı olarak sunulamaz. Önizlemenin Lighthouse SEO puanı 66’dır; kasıtlı noindex/robots kısıtlamasını içerir. Üretim HTML’sinin ayrı yerel Lighthouse SEO denetimi 100 puan almıştır; bu denetimde PHP çalıştırılmamıştır ve sonuç Google’ın sayfaları dizine aldığını göstermez. Bunlar canlı PageSpeed, gerçek kullanıcı Core Web Vitals veya tüm sayfaların hız puanı değildir; “tam puan” sonucu çıkarılamaz.

İlgili servis açılış sayfası, açık iletişim, cihaz/belirti eşleşmesi ve mobil kullanılabilirlik Ads açılış deneyimini destekler. Reklam hesabına bağlanılmadı; kampanya, dönüşüm etiketi veya reklam bütçesi değiştirilmedi. Ads Quality Score ve müşteri dönüşümü ölçülmedi.

## 7. Kontrol kanıtları ve teslim sınırı

- Statik üretim kabulü: 200 içerik/sitemap adresi, iç dosya/işaret referansları; yetim içerik, eksik hedef ve schema/metin uyuşmazlığı bulunmadı. Dosya özeti doğrulandı; sınırlı anahtar deseni taramasında eşleşme yoktu.
- 91 Python birim testi; eşleştirme, bölge verisi, iç bağlantı, schema, yükleme, önbellek sürümleri, emekliye ayrılan servisler ve kabul kuralları. Üretim paketindeki PHP dosyalarının sözdizimi kontrol edildi. Gerçek PHP çözümleyicisinde yedi örnek, JavaScript tarafında 18 örnek ile uyum denetimi geçti. PHP regresyonu özel ayar veya dış ağ gerektirmeden çalıştırıldı.
- Yerel Chromium’da 217 uygulama sayfası ve 3 rapor, 360 ve 768 pikselde açıldı (440 görünüm). Bulunan marka dizini kimlik tekrarları düzeltildikten sonra aynı tarama tekrarlandı; JavaScript hatası, kaynak HTTP hatası, bozuk görsel, yatay taşma veya tekrarlanan HTML kimliği kalmadı. Son ana sayfa kontrolünde mobil/masaüstü AI Usta ve Yorumlar hedefleri ayrıca açıldı.
- Yeni metinlerin tamamı, önceki 55 bölge ve yeni 29 marka/arıza gövdesinin ekran görüntüleri, 84 gövdeli eski/yeni inceleme ve 123 satırlı dizin karşılaştırma ekranı, matris seçimleri, model bilinmiyor seçeneği, özel modelin isteğe bağlı kalması, sıfırlama, klavye kullanımı, cihaz değişikliği ve JavaScript geliştirmesi yokken statik içerik kontrol edildi.

**Bu kontroller canlı Telegram teslimi, Gemini cevabı, sunucudaki form kaydı veya Search Console sonucu değildir.** GitHub önizlemesi bilerek noindex durumundadır; form, konum ve sağlayıcı gönderimleri kapalıdır. Üretim ZIP’i canlı sunucu için ayrı derlenir ve bu önizleme kısıtlarını taşımaz. Canlı sunucuya otomatik geçiş yapılmaz.

Canlıya geçişte mevcut özel yapılandırma ve veritabanı korunarak üretim paketi yüklenmeli; gerçek PHP/form/Telegram/Gemini bağlantıları sunucuda doğrulanmalıdır. Ardından sitemap erişimi ve önemli ilçe/rehber URL’leri Search Console’dan kontrol edilmelidir. Dizine alınma, sıralama, reklam puanı ve iş sayısı bu raporla garanti edilmez.

## 8. Yeniden üretme ve kanıt dosyaları

```sh
python hybrid/build.py --mode production --output build/hybrid-production --zip build/saglam-teknik-hibrit.zip
python hybrid/audit.py build/hybrid-production --mode production
python -m unittest discover -s hybrid/tests -p 'test_*.py'
```

Raporun sayısal dayanakları: `build-production-log.json`, `acceptance-production.json`, `matching-final.json`, `matrix-browser.json`, `browser-audit.json`, `diagnostics-loader-browser.json`, `home-final-check.json` ve `lighthouse-comparison.json`. Bunlar farklı kapsamları ölçer; ekran sayısı, test sayısı ve işlevsel sağlayıcı teslimi aynı başarı ölçüsü olarak birleştirilmemiştir.

Editöryal kaynak kanıtları: `editorial-before-after.json`, `editorial-content-audit.json`, `editorial-rendered-audit.json`, `manual-editorial-review.json`. Derleme, kaynak metin ile gerçek HTML gövdesi uyuşmazsa durur.
