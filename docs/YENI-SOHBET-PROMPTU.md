# Yeni sohbete başlangıç metni

Aşağıdaki metni yeni sohbete yapıştırın. Güncel çalışma zaten GitHub deposundadır; yeni site veya yeni ZIP zinciri başlatılması gerekmiyor.

---

Sağlam Teknik'in mevcut premium kombi/klima sitesine kaldığımız yerden devam edelim. Türkçe, kısa ve açık konuş. Her turda tek, sınırları belli işi ele al; baştan tasarlama, bitmeyen görev listesi çıkarma veya her adımda aynı bilgileri tekrar isteme. Önce fikir istersem yalnız öneri sun; uygulama istersem ilgili küçük değişikliği yap, gerekli kontrolleri tamamla ve sonucu göster.

Depo: https://github.com/saglamteknikk2-afk/site — dal: `main`.
Test önizlemesi: https://saglamteknikk2-afk.github.io/site/ .
Yerel çalışma varsa kökü `/workspace/work/github-premium`; başka ortamda deponun mevcut klonunu kullan.

**https://saglamkombiklima.com.tr/ canlı sitesine ve `saglamteknikk2-afk/saglam-ai-usta` Usta Topluluğu projesine dokunma.** Bu depodaki `main` yayını yalnız GitHub Pages önizlemesini günceller. Üretim paketi hazırlamak canlıya yayınlamak değildir.

Önce `git status`, `README.md`, bu dosya, `docs/SEO-GUVENLIK.md` ve `.github/workflows/pages.yml` dosyasını oku. Varsa projeye ait `AGENTS.md`/`CLAUDE.md` kurallarını da oku. Daha önce sağlanan `CLAUDE.md` yaklaşımını koru: varsayımları açıkla, en basit çözümü seç, yalnız ilgili dosyalara dokun ve sonucu uygun kontrolle doğrula. Açıkça yetkilendirilmiş küçük işi gereksiz tekrar onaylarıyla bölme; kapsamı etkileyen gerçek belirsizliği belirt.

**Düzenlenebilir kaynaklar:**

- `components/`: ana sayfa, ortak başlık/alt bilgi, AI Usta ve servis talebi parçaları.
- `overrides/`: düzenlenmiş sayfalar; `assets/` altında premium tasarım, model arayıcı, AI akışı, yorumlar ve harita arayüzü. Marka kaynağı `assets/brand-registry.json`; AI Usta/model kütüphanesi/markalar/servis seçicileri aynı veriden üretilir. Isısan tarihî tedarikçidir; Bosch/Buderus kodlarına bağlama. Ayrıntılar `docs/BRAND-COVERAGE.md`.
- `server/`: yalnız üretim paketine alınan PHP ve sunucu dosyaları; üretimde içerikleri web köküne gelir.
- `templates/business-maps-section.html` ve `templates/private/saglam-teknik/`: harita parçası ve **boş** özel ayar örnekleri.
- `scripts/`: derleme, ana sayfa birleştirme, model sayfası iyileştirmeleri ve kontroller.
- `tests/`: yerel kontroller. `preview-parts/part-000.txt`–`part-042.txt` doğrulanan eski arşivdir; sayfa düzenlemek için parçaları değiştirme. README’deki sabit SHA-256 yalnız bu başlangıç arşivine aittir; güncel derleme veya dağıtım ZIP özeti değildir.

`_site/` ve `build/production/` üretilmiş çıktıdır; asıl düzeltmeyi bunlarda yapma. Krem/bej, koyu yeşil ve sınırlı bakır kimliği koru. Son kullanıcı kararı: kendisinin gönderdiği temiz mavi S kurdele logosu. `components/brand.json` tüm logo ve favicon yollarının tek kaynağıdır; önceki alev-buz tercihi bu kararla değişmiştir. Özgün logoyu yeniden tasarlama; eski logo yolları manifestte takma ad olarak dönüştürülür. Ana başlık hizmeti açıkça anlatır; slogan tam olarak “Mevsim değişse de konforunuz değişmesin.” olarak onun altında kalır. İlk ekranda Hemen Ara, WhatsApp ve aynı AI Usta akışına giren üç cihaz kısayolu bulunur. Ana görselde kombi, klima ve petek birlikte, kedi peteğin üstünde, köpek halının ortasındadır. Mobil okunabilirlik, doğru cihaz görselleri ve kolay iletişim önceliklidir.

**Mevcut durum ve sınırlar:**

- Önizleme statiktir ve bütün ziyaretçi sayfaları `noindex` taşır. PHP/Gemini, kayıt, Telegram, konum ve ileti gönderimleri önizlemede kapalıdır. Tarayıcı içi model/kod/bölge araması ve kaynaklı yerel rehber çalışabilir. Demo işlemini gerçek kayıt veya gönderim gibi anlatma.
- Yerel üretim paketi üretilebilir; canlıya kurulmuş veya gerçek hizmetlerle uçtan uca doğrulanmış sayılmaz. Google/GitHub Actions başarısını ancak ilgili güncel çalışmayı görürsen söyle.
- Reklam hesapları bağlanmış değildir; reklam başlatma veya harcama yapma. Harita altyapısı hazır olsa da gerçek işletme bağlantıları henüz girilmiş kabul edilmez.
- Mevcut yayımlı yorumları koru. Üretimde onaylı site yorumları `api.php?action=reviews` üzerinden yüklenir; özel müşteri veritabanı test ortamına taşınmaz. Önizleme canlı yorum API'sini çağırmaz. Kullanıcı tarafından sağlanan Armut rozetini yeniden uydurma; bu görseli resmî API bağlantısı veya bağımsız güncel puan doğrulaması gibi sunma. Sahte yorum ya da `aggregateRating` üretme.

**AI Usta ve özel ayarlar:**

Ana sayfada tek AI Usta akışı vardır; ayrı ikinci marka/model arama çubuğu ekleme. Butonlu akış: cihaz → belirti → gerekiyorsa marka/tam model/kod. İsteyen yazabilsin. Güvenli ön bilgi hemen görünsün; AI bağlantısı başarısız olunca yerel rehber kaybolmasın. Doğal davet kullan: “İsterseniz cihaz ve belirti bilgilerini WhatsApp'tan iletip servis uygunluğunu görüşebilirsiniz.” WhatsApp mesajını kullanıcı gönderir. Gaz kokusunda 187; yangın/yaralanmada 112 ticari çağrıdan önce gelir. Kesin teşhis veya tehlikeli müdahale önerme.

Gemini sağlayıcısını ve sunucu tarafındaki dört anahtar yuvasını koru. Gerçek dosya web kökü dışındaki `private/saglam-teknik/site_apileri,.txt`; virgülsüz eski ad da desteklenir. Dört anahtar aynı projedeyse bağımsız kota sayılmaz. Anahtarları sohbete, Git'e, tarayıcıya veya indirilebilir pakete koyma; model adı, kota ve erişim uygunluğunu varsayma. Haritalar için aynı özel klasörde `haritalar.json` kullanılır; örneği `templates/private/saglam-teknik/haritalar.json.ornek`. Farklı kurulumda `SAGLAM_PRIVATE_DIR` mevcut özel klasöre işaret eder. Mevcut özel ayarları/veritabanını ezme. Gerçek AI/Telegram isteği, webhook veya cron kurulumu bu önizleme testi değildir.

**İçerik ve büyüme:**

Haftada üç iş sınırı yok; talep artışına uygun, ölçülebilir bir sistem hedefliyoruz. Müşteri sayısı, sıralama, bütün sorgularda görünme veya AI tavsiyesi garantisi verme. Telefon/WhatsApp tıklaması ≠ gerçek talep ≠ tamamlanan ücretli iş.

Her kelime sırası için yeni sayfa açma. Aynı niyeti güçlü canonical sayfada topla; ilçe/hizmet, belirti ve model rehberlerini anlamlı bağla. Tam model, ülke/kontrolcü kapsamı ve üretici kaynaklarını koru. Kodda önce tam eşleşmeyi kullan; `E1/E01` veya `F4/F04` gibi baştaki sıfır varyantlarını yalnız seçili model içinde tek ve çelişkisiz bir kayda bağlanıyorsa eşleştir. İki ayrı gerçek kod çakışıyorsa tam yazımı koru ve belirsiz varyanttan anlam seçme. Başka modelden kod anlamı taşıma; eksik modeli uydurma. Ülke ve kontrolcü bağlamını açıkla, rehber sonucunu kapsam onay kutusuyla engelleme; yabancı belgenin yerel cihazla uyumunu kendiliğinden doğrulama. Kaynak bulunmayan marka/modeli açıkça belirt. Özel AI etiketi, `llms.txt` veya şema ile tavsiye kazanıldığını iddia etme.

**Derleme ve kontrol** — Python 3.10+:

```sh
python scripts/build_site.py --mode preview --output _site --base-path /site
python scripts/check_site.py _site --mode preview --report build/preview-check.json
python -m unittest discover -s tests -p 'test_*.py' -v
```

Yalnız üretim paketi incelemesi gerekiyorsa:

```sh
python scripts/build_site.py --mode production --output build/production
python scripts/check_site.py build/production --mode production --report build/production-check.json
```

PHP/JS değişikliğinde ilgili sözdizimi ve davranış kontrollerini ekle. `php tests/business-runtime.php` sentetik özel klasör ve taklit sağlayıcıyla çalışır; gerçek API/bildirim göndermez. Tarayıcı testleri Playwright ve Chromium ister; `tests/model_ux.cjs` için yerel HTTP kökü ve `ST_TEST_ORIGIN` gerekir. Test dosyasının ön koşullarını oku; üretim PHP uçlarını test amacıyla çağırma.

Sonucu “değişen kaynaklar / gerçekten çalıştırılan kontroller / kalan sınır” olarak kısa raporla. Canlı Pages bağlantısını, commit'i ve Actions sonucunu yalnız doğrulandıysa ekle. Güncel son commit ve yayın durumu bu metne sabitlenmemiştir; depodan kontrol et. Her tur tek somut iyileştirmeyle ilerle.

Son tasarım oranı %70 premium / %30 mevcut sitenin güçlü servis anlatımıdır. Mobil iletişim çubuğu 78 pikseli aşmamalı ve içerik/düğmeleri örtmemelidir. `components/service-assurances.json`: 40 dk varış hâlâ pending; MYK no YB0200/11UY0032-4/02/502 ve işletmenin 1 yıl parça/işçilik garantisi kullanıcı tarafından bildirildiği için business-declared. Dış kurum doğrulaması veya üretici yetkisi iddia etme. Yapılan işlem ve temin edilip takılan parçalar servis belgesinde belirtilir.

Organik içerikte 50 ilçe, 5 semt, 16 marka ve 6 hizmet sayfası yenilendi; kaynaklı 86 model sayfası korundu. Her kelimenin farklı olması hedef değildir: menü, güvenlik ve kaynak kapsamları gerektiği yerde ortak kalır. Gerçek kullanıcı ihtiyacı, kaynak ve ayırıcı bilgi ekle; aynı metindeki bölge adını değiştirerek yeni sayfa üretme. `scripts/audit_content.py` raporunu aynı yöntemle karşılaştır; sinyalleri arama motoru garantisi gibi sunma. Reklamlar için derlenmiş `assets/ad-landing-map.json` mevcut gerçek servis URL’lerini verir, hesap yönetimi veya harcama yetkisi sağlamaz. Ana siteye geçiş için kullanıcı onayı ayrıca alınır.

**Bağlantı regresyonu:** Başlık ve alt bilgideki ana sayfa bağlantıları derleyicinin ürettiği tek kaynaktır; runtime içinde tekrar `/site` ekleme. JavaScript içindeki yalın `/` veya harici harita yol karşılaştırmalarını site URL’si gibi dönüştürme. `scripts/build_site.py` yalnız bilinen yerel dosya URL’lerini JavaScript içinde dönüştürür; HTML/CSS yolları yinelenebilir uygulanır. CSS/JS sürümleri son sunulan dosya içeriğinden alınır. `tests/navigation.cjs`, üç gerçek HTTP bağlama yolunda 203 sayfanın JavaScript sonrası bağlantılarını ve iç sayfalardan gerçek AI Usta tıklamalarını kontrol eder; API/harici istekleri durdurur. Pages iş akışı bu test ve mobil görünüm kontrolü geçmeden yayınlamaz. Yeni metin düzeni: SAĞLAM TEKNİK yatay; altında Isıtma & Soğutma Teknolojileri.

İç bağlantılar `scripts/internal_links.py` tarafından, yeni URL üretmeden bağlama göre eklenir. `python scripts/internal_links.py build/production --check --report build/crawl-check.json` üretimdeki 190 dizine uygun URL’nin gerçek HTML ağında en fazla 3 adımda bulunmasını denetler; yabancı pazar kapsamı nedeniyle noindex tutulan 11 model rehberi sitemap’e eklenmez. Marka sayfalarındaki tam model bağlantıları model_id/model parametrelerini korur. Ülke/ürün kapsamını bilgilendirme olarak göster; ayrıca onay kutusu isteme ve model uyumunu varsayma. `docs/editorial-link-targets.json` ve `tests/editorial_links.cjs` metin içi bağlantıların hedeflerini doğrular. `regionFinder`, `svcSearchForm` ve varsa `homeGuideSearch` yalnız yerel arama/gezinme olduğu için önizlemede `data-preview-local="true"` alır; gönderim formlarına bu izni verme. `tests/interactions.cjs` görünen düğme/summary denemelerini, bağlantı hedefi kontrolünü ve özelayar bekleyen durumları ayrı sayar. Arka plan regresyonu için `php tests/backend-http.php build/production` sentetik özelayarlarla gerçekyerel HTTP kullanır. Yeni durumun dizine alma açıklaması `docs/INDEXLEME-REHBERI.md` içindedir; SearchConsole durumunu yalnız URLşablonuna bakarak teşhis etme.

Son çift ortam kuralları: HTML/CSS/JS/JSON yayın yolları belgeye göre relative; CSS kendi klasörüne göre çözülür. Canonical/OG/JSON-LD her iki modda resmi domaine sabittir. environment.js ilk uygulama kodundan önce ve html[data-st-mode] sonrasında yüklenir; GitHub hostname her koşulda yazmaları engeller. Önizleme dosyasını resmi domaine taşımak korumayı kaldırmaz; canlı için production paketi kullanılır. 404 kurtarması yerel testte deklaratif mount, GitHub’da proje segmenti, resmi domainde kök kullanır.
