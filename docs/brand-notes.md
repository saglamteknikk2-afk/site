# Marka simgesi — test sitesi

Kullanıcının ilettiği iki S simgesi incelendi. Başlık, mobil görünüm, alt bilgi, sekme ikonu ve küçük ekranlarda daha sade ve okunur olduğu için mavi S kurdele, test sitesinin birincil logosu olarak seçildi. Alev/buz görseli eski varyant olarak depoda korunur; ana logo değildir.

Görsel dosyaları `overrides/assets/brand/logo-ribbon.png` (216 × 256, şeffaf PNG) ve `overrides/assets/brand/favicon.png` (64 × 64) olarak hazırdı; yeniden çizilmedi, piksel içeriği değiştirilmedi. Merkezi seçim `components/brand.json` içindedir. `scripts/build_site.py` bu manifest üzerinden eski logo referanslarını ve favicon etiketlerini önizleme/üretim derlemelerinde günceller. Yeniden logo değiştirmek için her sayfayı ayrı ayrı düzenlemek gerekmez.

İsim başlıkta **SAĞLAM TEKNİK** biçiminde, altında **Isıtma & Soğutma Teknolojileri** olarak gösterilir. Ortak başlık ve alt bilgi ziyaretçi sayfalarında aynı bileşenlerden derlenir. Evcil hayvanlı ana görsel ve diğer görseller değiştirilmedi.

Bu güncelleme yalnız GitHub Pages test önizlemesi için `main` dalına uygulanır; canlı `saglamkombiklima.com.tr` sunucusuna herhangi bir dosya göndermez.
