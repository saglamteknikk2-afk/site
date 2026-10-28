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
css = '<link rel="stylesheet" href="/site/assets/saglam-onarim.css">'
if 'saglam-onarim.css' not in s:
    s = s.replace("</head>", css + "</head>",1)
# Hem yeni hem eski ana sayfada ziyaretciye galeriye gidis ver.
nav = '<a class="st-saha-nav-link" href="/site/sahadan-gorseller.html">Sahadan Görseller</a>'
if 'st-saha-nav-link' not in s:
    match = re.search(r'<nav\b[^>]*\bid=["\']atNavigation["\'][^>]*>',s,re.I)
    if match:
        i = s.find("</nav>",match.end())
        if i>=0:s=s[:i]+nav+s[i:]
gallery = '''<section class="st-field-photos" aria-labelledby="st-field-title">
<h2 id="st-field-title">Sahadan Görseller</h2>
<p>Gercek kombi tamiri, klima ariza giderme ve petek temizligi calismalarimiz. Yalnizca bize ait, izinli is fotograflari yayimlanir.</p>
<a class="st-saha-link" href="/site/sahadan-gorseller.html">Sahadan calismalari goruntule</a>
</section>'''
if 'id="st-field-title"' not in s:
    s=s.replace("</main>", gallery+"</main>",1)
index.write_text(s,encoding="utf-8")
print("A1 on izleme: ana sayfa baglantilari, gorsel olculeri ve galeri eklendi")
