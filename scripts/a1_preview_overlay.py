#!/usr/bin/env python3
"""Salt-okunur GitHub Pages on izlemesi icin a1 gorsel ekleri.
Canli site, form POST, Telegram veya veritabani islemez.
"""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]) if len(sys.argv)>1 else Path("_site")
index = root/"index.html"
if not index.exists():
    raise SystemExit("On izleme ana sayfasi bulunamadi")
s = index.read_text(encoding="utf-8")
css = '<link rel="stylesheet" href="assets/saglam-onarim.css">'
if 'saglam-onarim.css' not in s:
    s = s.replace("</head>", css + "</head>",1)
# Hem yeni hem eski ana sayfada ziyaretciye galeriye gidis ver.
nav = '<a class="st-saha-nav-link" href="sahadan-gorseller.html">Sahadan Görseller</a>'
if 'st-saha-nav-link' not in s:
    match = re.search(r'<nav\b[^>]*\bid=["\']atNavigation["\'][^>]*>',s,re.I)
    if match:
        i = s.find("</nav>",match.end())
        if i>=0:s=s[:i]+nav+s[i:]
gallery = '''<section class="st-field-photos" aria-labelledby="st-field-title">
<h2 id="st-field-title">Sahadan Görseller</h2>
<p>Gercek kombi tamiri, klima ariza giderme ve petek temizligi calismalarimiz. Yalnizca bize ait, izinli is fotograflari yayimlanir.</p>
<a class="st-saha-link" href="sahadan-gorseller.html">Sahadan calismalari goruntule</a>
</section>'''
if 'id="st-field-title"' not in s:
    s=s.replace("</main>", gallery+"</main>",1)
index.write_text(s,encoding="utf-8")
print("A1 on izleme: ana sayfa baglantilari, gorsel olculeri ve galeri eklendi")


# Servis seçiminde gösterişli ama işlevsiz iki farklı tanıtım bloğu
# yerine üstte görsel + işlevsel seçici; JS ve form kimlikleri korunur.
service_file=root/"servis-sec.html"
if service_file.exists():
    page=service_file.read_text(encoding="utf-8")
    page,n_intro=re.subn(r'(<div class="at-content">)\s*<article\b[^>]*>[\s\S]*?</article>',r'\1',page,count=1,flags=re.I)
    art=re.search(r'<div class="at-hero-art">(\s*<img\b[^>]*>)\s*</div>',page,flags=re.I)
    if not art:
        raise ValueError("Servis seçim sayfası görseli bulunamadı")
    visual=art.group(1)
    visual=re.sub(r'\s+alt="[^"]*"',' alt="Kombi ve klima servis görseli"',visual)
    page=page[:art.start()]+page[art.end():]
    page=page.replace('<section class="at-page-hero">','<section class="at-page-hero st-service-hero">',1)
    pat=r'(<section\b[^>]*\bid="servisSecimi"[^>]*>)([\s\S]*?)(<form\b[^>]*\bid="svcSearchForm")'
    part=re.search(pat,page,flags=re.I)
    if not part or "svc-heading" not in part.group(2):
        raise ValueError("Servis seçimi formu veya başlığı bulunamadı")
    opening=part.group(1).replace('class="glass-box','class="st-selector-optimized glass-box',1)
    new=opening+'<div class="st-selector-top"><div class="st-selector-description">'+part.group(2)+'</div><div class="st-selector-visual">'+visual+'</div></div>'+part.group(3)
    page=page[:part.start()]+new+page[part.end():]
    if "saglam-onarim.css" not in page:
        page=page.replace("</head>",'<link rel="stylesheet" href="assets/saglam-onarim.css"></head>',1)
    service_file.write_text(page,encoding="utf-8")
    print("A1 servis seçimi: çift giriş kaldırıldı, görsel seçim bölümünün yanına alındı")
