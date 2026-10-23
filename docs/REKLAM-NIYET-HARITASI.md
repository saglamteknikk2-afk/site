# Mevcut sayfalarla reklam niyeti eşlemesi

23 Ekim 2026. Bu belge ve URL listesi bir kampanya kurmaz, hesap bağlamaz veya bütçe harcamaz. Üretim paketi henüz ana siteye kurulmuş sayılmaz; GitHub Pages önizlemesi reklamın nihai adresi değildir.

`scripts/landing_actions.py`, derleme sırasında 82 mevcut hizmet, marka, ilçe ve semt sayfasını `assets/ad-landing-map.json` içine yazar. Dosya üretim çıktısının parçasıdır; `overrides/` altında elle yazılmış bir liste değildir. Aynı sayfalardaki Ara ve WhatsApp bağlantıları kullanıcıya doğrudan iletişim yolu sunar. WhatsApp taslağı sayfa başlığı ve mevcut canonical adresini taşır; mesajı kullanıcı gönderir. Bu bağlantıların varlığı dönüşüm ölçümü kurulduğu anlamına gelmez.

## Nihai URL seçim örnekleri

Reklam metni, gerçekten verilebilen hizmet ve açılan sayfanın konusu aynı olmalıdır. İşlem uygunluğu ve servis kapsamı görüşmede netleşir; belgelenmemiş fiyat, süre, şube veya yetkili servis iddiası reklama eklenmez.

| Arama / reklam niyeti | Mevcut canonical sayfa |
| --- | --- |
| Kombi için genel servis talebi | `https://saglamkombiklima.com.tr/kombi-servisi.html` |
| Kombi bakımı | `https://saglamkombiklima.com.tr/kombi-bakimi.html` |
| Kombi arızasının kontrolü ve onarımı | `https://saglamkombiklima.com.tr/kombi-tamiri.html` |
| Petek temizliği ve dolaşım değerlendirmesi | `https://saglamkombiklima.com.tr/petek-temizligi.html` |
| Klima servisi | `https://saglamkombiklima.com.tr/klima-servisi.html` |
| Klima bakımı | `https://saglamkombiklima.com.tr/klima-bakimi.html` |
| Klima tamiri | `https://saglamkombiklima.com.tr/klima-tamiri.html` |
| Yeni klima montajı | `https://saglamkombiklima.com.tr/klima-montaji.html` |
| Klima sökümü veya yer değişimi | `https://saglamkombiklima.com.tr/klima-sokumu.html` |
| Gaz/kaçak kontrolü talebi | `https://saglamkombiklima.com.tr/klima-gaz-kontrolu.html` |
| Küçükçekmece kombi servisi | `https://saglamkombiklima.com.tr/kucukcekmece-kombi-servisi.html` |
| Avcılar klima servisi | `https://saglamkombiklima.com.tr/avcilar-klima-servisi.html` |
| Baymak kombi servis talebi | `https://saglamkombiklima.com.tr/baymak-kombi-servisi.html` |

Diğer ilçe ve markalar için mevcut listeden gerçekten eşleşen sayfa seçilir. Kelime sırasını değiştirmek yeni bir açılış sayfası gerektirmez. Mahalle seçiminin her mahalle için ayrı, yayımlanmış bir sayfa oluşturduğu varsayılmaz.

## Bilgi arayan ziyaretçiyi servis arayanla karıştırmayın

Model veya hata kodu araması, doğrudan servis satın alma niyeti olduğunu kanıtlamaz. Kaynaklı model rehberi bilgi ihtiyacını karşılayabilir; kaynak kapsamı belirsizken reklamdan kesin arıza çözümü vaat edilmez. Üretici kılavuzundaki ülke, model ve kontrolcü sınırları reklamdan gelen kullanıcı için de korunur.

Gaz kokusu, duman, yangın veya yaralanma acil güvenlik yönlendirmesi gerektirir; bunlar ticari teklif akışının önüne geçer. Gaz kokusunda 187, yangın/yaralanma gibi acillerde 112 yönlendirmesi korunur.

## Ölçüm ve hesap sınırı

Telefon tıklaması ≠ gerçekleşen görüşme; WhatsApp açılışı ≠ gönderilmiş mesaj; form kaydı ≠ uygun talep; talep ≠ ücretli tamamlanan iş. Reklam optimizasyonu için kaynak, tekil talep, randevu ve iş sonucu ayrı kaydedilmelidir. Bu sürümde tam reklam atfı veya bu sonuçların reklama aktarımı kurulmuş sayılmaz. Yeni takip etiketi ve veri aktarımı, uygun hesap erişimi ve veri kullanımı koşullarıyla ayrıca uygulanır.

Reklam parametreleri ileride ölçüm amacıyla kullanılsa bile aynı hizmetin canonical adresi korunur. Parametre başına kopya sayfa üretmek veya arama motoru/ziyaretçi için farklı içerik sunmak hedef değildir. Google Ads veya Yandex Direct hesabında hiçbir değişiklik yapılmadı; bütçe, müşteri sayısı, organik sıralama ve AI tavsiyesi garantisi verilmez.
