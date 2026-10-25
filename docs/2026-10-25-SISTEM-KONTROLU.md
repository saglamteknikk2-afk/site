# Sağlam Teknik sistem teslimi

Bu sürüm GitHub Pages tasarım önizlemesi ve PHP 8.2 üretim paketi olarak ayrı üretilir. GitHub Pages müşteri kaydı, Telegram ve Gemini çalıştırmaz. Ana alan adına otomatik yükleme yapılmaz.

## Müşteri akışı

- Ana sayfada Kombi, Klima, Petek & Tesisat ve AI Usta girişleri bulunur. Cihaz seçiminden arıza sorgusu, standart kayıt veya öncelikli kayda geçilir.
- AI Usta tek kart içinde ilerler; adım değişiminde sayfa konumu korunur. Tek model seçimi vardır. Manuel model alanı istenirse açılır, modeli bilmeden devam edilebilir.
- Model/seri tanıma dizini 532 ad içerir. Bu sayı tam model, seri ve mevcut kılavuzda geçen adların toplamıdır; bütün Türkiye pazarının eksiksiz envanteri veya 532 ayrı doğrulanmış arıza tablosu değildir. Her kaydın kaynağı ve kapsamı assets/model-directory.json içinde bulunur. Yeni katalog adları kod anlamı üretmez.
- Arıza kodu yalnız aynı tam modelin mevcut kılavuzuna bağlanır. Kaynaksız model için başka cihazın kodu kullanılmaz. Acil belirtilerde güvenlik yönlendirmesi öne çıkar.

## Servis ve ücret

İstanbul saatiyle 08.00 dahil–21.00 hariç öncelikli servis bedeli 2.500 TL; 21.00 dahil–ertesi gün 08.00 hariç 4.000 TL'dir. İletişim bilgileri ve ilk “Onaya gönder” işlemi fiyat teklifini açar. Ücret, kapsam ve işaretlenmemiş kabul kutusu görülmeden son “Talep et” ile kayıt oluşmaz. Ücretin değiştiği saat sınırında yeni onay gerekir. Bu işlem karttan ödeme tahsil etmez.

Servis, ücret kabulü, bölgesel sıra ve bildirim aynı veritabanı işlemiyle saklanır. Ekip Aldım, Yoldayım, Tamamlandı veya İptal durumlarını yönetim ekranından veya yetkili Telegram hesabından seçer. Öncelikli talep ekip kabulünden sonra öncelik kazanır. Gerçek kayıtlardan ilçe gruplaması yapılır; geçmiş kayıtlar kabul edilmeden güncel sıraya katılmaz. Bu özellik canlı araç takibi, yol süreli harita optimizasyonu veya kesin varış garantisi değildir.

## Yorum ve bildirim

Yorumlar gerçek tarihlerine göre yeniden eskiye gösterilir. Yayın onayı ile hizmet doğrulaması ayrıdır. Hizmet doğrulama rozeti yalnız ilgili veri mevcutsa gösterilir.

Telegram'da `/sil` ismi sorar, eşleşen kayıtları gösterir, süreli Sil/İptal düğmeleri sunar. Yetki, sohbet ve tekrar kontrol edilir. Eski yorumlar kalıcı kimlikleriyle silme kaydına alınır; yeniden yüklenince geri görünmez. Çalışan arayüz API'den silinen kimlikleri alır. Arama motorunun önbelleği ve eski statik HTML kopyası anında silinmiş sayılmaz.

Tamamlanan AI sorusu ve ekranda gösterilen cevap aynı olay kimliğiyle bildirilir. Başarısız istemci isteği tekrar denenir; sayfa ilk başarılı kayıt oluşmadan kapanırsa bellekteki tekrar bilgisi kaybolabilir. Sunucuya kaydedilmiş bildirimler kalıcı kuyruktadır. Gönderim yalnız Telegram teslim onayıyla başarılı sayılır. Tekil “Siteden arama” bildirimi kaldırılmıştır.

## Yayın ve bağlantılar

Üretim ZIP'inin kökü web dosyalarıdır; özel anahtarlar, müşteri veritabanı, ham belgeler ve GitHub önizleme gönderim engeli bu pakete eklenmez. Mevcut web dosyaları ve private klasörünün yedeği alınmalıdır. Mevcut private/saglam-teknik ayarları ve müşteri veritabanı korunmalıdır; çalışan sunucuya boş bir private klasörü yüklenmemelidir.

Yönetim için owner-admin.html açılır. Erişim anahtarı özel ayar dosyasındaki ADMIN_ACCESS_KEY veya özel yonetim.key dosyasındadır. Telegram ve AI test düğmeleri yönetimde bulunur. Test düğmesi gerçek sağlayıcıya istek gönderir; sonuç ayrı doğrulanmalıdır. Telegram webhook'unun aynı botu kullanan başka siteyi etkileyeceği dikkate alınmalıdır.

Plesk zamanlanmış görevinde worker.php her dakika çalıştırılmalıdır. Trafikte ve yönetim işlemlerinde sınırlı yedek denemeler yapılır; trafik yokken düzenli tekrar ve rapor teslimi için zamanlanmış görev gerekir. Dört Gemini anahtarı mevcut özel dosyadaki GEMINI_API_KEY_1–4 alanlarından okunabilir; kota ve sağlayıcı erişimi ayrı koşullardır.

## Arama motorları ve kapsam

Mevcut değerli URL'ler korunur. Aynı niyet için kelime sırası değişen yeni URL'ler üretilmez. İç bağlantılar, tekil canonical, sitemap ve kaynaklı model rehberleri aynı derlemeden üretilir. Yabancı pazar veya erişilemeyen kaynak rehberlerinde mevcut noindex politikası korunur. LLMS dosyası okunabilir kaynak özeti sağlar; sıralama veya AI tarafından önerilme garantisi vermez.

Test raporlarında gerçek yerel PHP/SQLite istekleri, sentetik API yanıtları ve dış sağlayıcı kontrolleri ayrı belirtilir. Yerel testin geçmesi canlı Plesk, Telegram, Gemini, Search Console veya resmî belge geçerliliğinin doğrulandığı anlamına gelmez. Altı maskeli PDF ve yedi sayfa bağımsız olarak incelenmiştir; orijinaller kamuya açık pakete eklenmez.
