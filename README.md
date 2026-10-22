# Sağlam Teknik — Krem Renkli Test Sitesi

Bu depo, Sağlam Teknik'in **krem renkli yeni kombi/klima sitesi** için ayrı bir ön izleme ortamıdır.

- **Ana `saglamkombiklima.com.tr` sitesi değişmez.**
- Usta Topluluğu `saglam-ai-usta` deposundan bağımsızdır.
- `site-preview.zip` yalnızca statik HTML, CSS, JS, font ve medya dosyalarından oluşur.
- PHP, veritabanı, Gemini API anahtarları, Telegram kimlik bilgileri, yönetici ekranları ve özel ayarlar depoya konmaz.
- Tüm ön izleme sayfalarında `noindex` bulunur.
- Bu sürümde **Gemini, Telegram, servis kayıtları ve admin işlemleri gerçek anlamda çalışmaz**. Bunlar ayrı korumalı sunucu üzerinde test edilmelidir.
- Gerçek servis sitesi veya müşteri verileri bu depodan güncellenmez.

## Yayın

`site-preview.zip` dosyası bu deponun köküne eklendiğinde GitHub Actions içindeki **Ön İzleme Yayını** iş akışı statik dosyaları GitHub Pages'e aktarır. İlk seferde GitHub repo **Settings → Pages → Source: GitHub Actions** ayarı gerekir.

Planlanan ön izleme adresi: https://saglamteknikk2-afk.github.io/site/

Bu adres yalnızca iş akışı başarılı olup Pages etkinleştikten sonra çalışır.
