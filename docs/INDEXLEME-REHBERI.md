# Site sahibi için indeksleme rehberi

24 Ekim 2026. Bu adımlar, üretim paketi gerçekten ana alan adına yayımlandıktan sonra uygulanır. Mevcut çalışma ana siteye kurulmuş sayılmaz. GitHub Pages test önizlemesinin `noindex` olması amaçlıdır; bu adres için indeksleme talep etmeyin.

Yerel paket 203 ziyaretçi sayfası içerir; 201'i dizine uygun, 404 ve seçim ekranı `noindex` durumundadır. Bu sayılar **Google'ın dizine aldığı sayfa sayısı değildir**. Gerçek durum Search Console'dan okunur. Katalogdaki seçim, model veya rehber kayıtlarının her biri ayrı yayımlanmış URL sayılmaz.

## 1. Önce gerçek sunucu yanıtını kontrol edin

- Ana sayfa, bir ilçe/hizmet sayfası ve kaynaklı bir model rehberi doğru HTTPS adresinde **200** dönmeli; giriş ekranı, doğrulama engeli veya hata sayfası göstermemeli.
- Dizine alınması istenen sayfanın HTML'inde ve HTTP `X-Robots-Tag` başlığında yanlışlıkla `noindex` bulunmamalı. Üretime test dosyalarının taşınmadığını gerçek yanıt üzerinden kontrol edin.
- Her önemli sayfada tek, doğru canonical bulunmalı. HTTP/www/eski adresler amaçlanan HTTPS adrese yönlenmeli; yönlendirme döngüsü olmamalı.
- Önizleme de üretim canonical/OG/şema adreslerini kullanır; `noindex` önizlemede ayrıca kalır. Canlıya yüklemeden önce önizleme adresinden görülen üretim canonical'ını yanlışlıkla GitHub adresine çevirmeyin.
- robots.txt önemli içeriğin taranmasını engellememeli. Gizli API/yönetim yollarının engelleri korunur. `noindex` için tarayıcının sayfaya erişebilmesi gerektiğini unutmayın.

Yerel dosya testleri bu sunucu kontrollerinin yerine geçmez. Sorun varsa önce onu düzeltin; yeniden gönderim teknik engeli kaldırmaz.

## 2. Search Console'da doğru üretim URL'sini inceleyin

Doğrulanmış `saglamkombiklima.com.tr` mülkünde **URL Denetimi** kullanın. Ana sayfa, önemli bir hizmet/ilçe URL'si ve bir model rehberiyle başlayın. Filtre, takip parametresi veya `#` seçimi yerine canonical adresi kullanın.

Kayıtlı dizin sonucundaki son tarama, sayfa getirme, kullanıcı canonical'ı ve Google'ın seçtiği canonical bilgilerini okuyun. **Canlı URL'yi test et**, Google'ın sayfayı o anda alabilmesini sınar; dizine alındığını veya alınacağını kanıtlamaz. Beklenmeyen WAF/CDN engeli varsa sunucu günlükleriyle birlikte araştırın; yalnız User-Agent yazısından bot kimliği doğrulanmaz.

## 3. Sitemap'i gönderin

Üretim sitemap adresi: `https://saglamkombiklima.com.tr/sitemap.xml`.

Dosya yalnız gerçek, canonical, dizine uygun sayfaları içermeli. `noindex`, yönetim/API, filtre kopyaları veya teorik kombinasyon URL'leri eklenmemeli. Yeni içerik güncellemesinden sonra `lastmod` gerçekten değişen içeriği yansıtmalı. Sitemap'in başarıyla okunması, içindeki bütün URL'lerin tarandığı veya dizine alındığı anlamına gelmez.

Son metadata adımı sitemap'i gerçek dosya kümesinden üretir; güvenilir güncelleme zamanı yoksa isteğe bağlı `lastmod` alanını eklemez. `llms.txt` sitemap veya Search Console başvurusu değildir; 25 ilçe ve gerçekten yayımlanmış rehberlerin okunabilir özetidir.

## 4. Gerekirse önemli sayfa için indeksleme isteyin

Önemli bir yeni sayfa veya anlamlı biçimde düzeltilmiş sayfa teknik olarak erişilebiliyorsa URL Denetimi üzerinden **Dizine eklenmesini iste** kullanılabilir. Bu bir öncelik veya kabul garantisi değildir. Aynı adresi tekrar tekrar göndermek sonucu hızlandırmaz; her kelime sırası ve seçim kombinasyonu için talep oluşturmayın.

İçerikte kullanıcının sorusunu gerçekten tamamlayan açıklama, ilgili rehbere doğal bağlantı ve doğru üretici kapsamı bulunmalı. Bir modelin belgesi yoksa başka modele ait tabloyla doldurmayın. Mevcut sayfanın değerini artırmak, yeni kopya sayfa üretmekten önce gelir.

## 5. Durumu doğru yorumlayın

| Search Console durumu | Nasıl ilerlenir? |
| --- | --- |
| Keşfedildi — şu anda dizine eklenmiş değil | Google URL'yi biliyor, henüz taramış olmayabilir. Erişim, sitemap ve dahili keşfi inceleyin. Bu etiket tek başına düşük kalite, URL deseni veya tarama bütçesi sorunu kanıtı değildir. |
| Tarandı — şu anda dizine eklenmiş değil | İçerik gerçekten alındı mı, kullanıcı ihtiyacı karşılanıyor mu, başka sayfayla aynı amaç/kapsam mı, canonical doğru mu inceleyin. Tek başına ceza göstergesi değildir. |
| Doğru canonical'a sahip alternatif sayfa | Beklenen kopya/parametre adresiyse normal olabilir. Asıl amaçlanan canonical doğruysa bunu zorla ayrı indeksletmeyin. |
| `noindex` nedeniyle hariç | Önizleme/404/seçim ekranında beklenebilir. Asıl hizmet sayfasındaysa HTML ve sunucu başlığını düzeltin; robots.txt ile taramayı kapatarak çözmeye çalışmayın. |

Önceki ekrandaki “keşfedildi” sayısı, bugünkü durumun veya tek bir nedenin teşhisi değildir. Manuel işlem olup olmadığını ilgili Search Console raporundan ayrıca okuyun; dizine alınmama ile manuel işlem aynı şey değildir.

## 6. Sonucu düzenli izleyin

Haftalık kontrolde önemli canonical sayfaların durumunu ve organik gösterim/tıklamalarını önceki dönemle karşılaştırın. Kullanıcının gerçek servis talebi ve tamamlanan ücretli işi ayrı takip edin. Bing Webmaster Tools ve Yandex Webmaster için ilgili site/sitemap raporları ayrıca değerlendirilir; bir arama motorundaki durum diğerinin sonucu değildir.

Taranabilirlik gerekli bir teknik koşuldur; sıralama, her sorguda görünme, AI önerisi veya müşteri sayısı garantisi sağlamaz. Bu rehber hesap bağlamaz ve otomatik indeksleme başvurusu yapmaz.

Şema incelemesinde bir hizmet, bir ilçe ve bir model sayfasını örnekleyin: tek `@graph`, doğru üretim URL'leri ve görünür içerikle aynı bilgi bulunmalı. Kaynaklı model rehberi `TechArticle`, gerçek hizmet `Service` olarak ayrılır; SSS yalnız görünür sorulara aittir. Google FAQ zengin sonucunu Mayıs 2026'da kaldırdığı için SSS'nin arama sonucunda açılmasını beklemeyin. Armut 4.8 rozeti, işletmenin kendi sitesinde Google yıldız sonucu sağlayacak `AggregateRating` olarak sunulmaz. Google Rich Results Test yalnız desteklediği özellikleri sınar; bütün Schema.org türlerini göstermemesi tek başına bozuk JSON-LD demek değildir.

Resmî kaynaklar: [URL Denetimi](https://support.google.com/webmasters/answer/9012289), [Sayfa indeksleme raporu](https://support.google.com/webmasters/answer/7440203), [Yeniden tarama isteme](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl), [Sitemap rehberi](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview), [Google noindex](https://developers.google.com/search/docs/crawling-indexing/block-indexing), [Canonical](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls).

Şema kaynakları (24 Ekim 2026'da kontrol edildi): [Genel şema kuralları](https://developers.google.com/search/docs/appearance/structured-data/sd-policies), [Self-serving işletme değerlendirmeleri](https://developers.google.com/search/docs/appearance/structured-data/review-snippet#self-serving-reviews), [Güncel FAQ/llms.txt değişiklik kaydı](https://developers.google.com/search/updates).
