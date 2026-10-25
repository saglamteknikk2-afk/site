# Belgeler ve öncelikli servis hazırlığı

Bu değişiklikler çalışma alanında hazırlanmıştır. Bu kayıt canlı sunucuya veya GitHub Pages'e yeni yayın yapıldığı anlamına gelmez.

## Kamuya açık belge kopyaları

Kullanıcının sağladığı altı PDF, toplam yedi sayfadır. Kişisel alanlar, kimlik ve belge numaraları, aile/doğum bilgileri, fotoğraf, imza, QR/barkod ve doğrulama alanları yeni raster kopyalardan çıkarılmış, yıldızlar görüntüye işlenmiştir. Orijinaller Git deposuna veya kamuya açık derlemeye eklenmez. Kamuya açık kopyalarda eski metin, bağlantı, ek dosya ve kişisel PDF metadata alanları yoktur. Belgelerin meslek/kurum/kapsam bilgileri korunmuştur; MYK'daki 70 kW kapsamı gizlenmemiştir.

Maskeli kopyalar `overrides/assets/credentials/` altındadır; `index.json` onaylanan PDF'lerin SHA-256 özetlerini içerir. Hakkımızda sayfası bu kopyaları gösterir. Sağlanan belgelerin görüntüsünün incelenmesi, devlet sisteminden çevrimiçi geçerlilik doğrulaması yapıldığı anlamına gelmez. Önceki yayımlarda sahibi tarafından paylaşılmış belge numarası yeni kamuya açık çıktılarda maskelenir; geçmiş Git arşivinin silindiği iddia edilmez.

## Ücret ve son onay

Kullanıcı 25 Ekim 2026'da İstanbul saatiyle gece tarifesinin 08.00'de bitmesini onaylamıştır:

- 08.00 dahil–21.00 hariç: 2.500 TL.
- 21.00 dahil–ertesi gün 08.00 hariç: 4.000 TL.

Öncelikli servis ilk seçildiğinde fiyat gösterilmez. İletişim alanları doldurulup “Onaya gönder” seçilince fiyat, koşullar ve işaretlenmemiş kabul kutusu açılır. Son “Talep et” işleminden önce servis kaydı veya bu talebe ait bildirim oluşturulmaz. Bu işlem ödeme tahsilatı veya kesin varış/sırada birincilik garantisi değildir.

Gerçek fiyatı PHP sunucu saati belirler. İmzalı onay oturuma ve iletişim/cihaz/arıza içeriğine bağlıdır; en çok 10 dakika geçerlidir ve 08.00/21.00 sınırında sona erer. Değişen fiyat yeniden gösterilir ve yeni onay gerekir. Aynı kabul kaydı farklı başvuru anahtarıyla ikinci talep oluşturamaz. Standart talep akışı korunur. GitHub önizlemesi yalnız simülasyon gösterir ve gerçek kayıt/bildirim göndermez.

## Kontroller

`tests/priority-service.php` fiyat/saat/imza/işlem güvenliğini; `tests/priority_service.cjs` arayüz durumlarını; `tests/priority_http.cjs` gerçek yerel PHP/SQLite üzerinden son onayı doğrular. `tests/priority_preview.cjs`, üretilmiş önizlemeyi gerçek güvenlik politikası ve gönderim engeliyle sınar. Testler sahte özel ayarlar kullanır, canlı Telegram veya Gemini anahtarını okumaz. `tests/test_public_credentials.py` çıktı maskelemesini sınar. Site ve kaynakların tamamı için önceki sürümün raporu yeni yayının kanıtı olarak kullanılmamalıdır.
