"""A readable report separate from customer service flows."""
from pathlib import Path
import html, json, re

def inline(text):
    text=html.escape(text)
    text=re.sub(r'`([^`]+)`',r'<code>\1</code>',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',text)
    return text

def markdown(text):
    out=[];paragraph=[];listing=False;code=False;code_lines=[];table=False
    def flush():
        if paragraph:out.append('<p>'+inline(' '.join(paragraph))+'</p>');paragraph.clear()
    for line in text.splitlines():
        if line.strip().startswith('|'):
            flush()
            if listing:out.append('</ul>');listing=False
            cells=[cell.strip() for cell in line.strip().strip('|').split('|')]
            if all(re.fullmatch(r':?-+:?',cell) for cell in cells):continue
            tag='td' if table else 'th'
            if not table:out.append('<div style="overflow:auto"><table style="border-collapse:collapse;width:100%">');table=True
            out.append('<tr>'+''.join('<'+tag+' style="border:1px solid #b8c5b0;padding:8px 12px;text-align:left">'+inline(cell)+'</'+tag+'>' for cell in cells)+'</tr>')
            continue
        if table:out.append('</table></div>');table=False
        if line.startswith('```'):
            flush()
            if listing:out.append('</ul>');listing=False
            if code:out.append('<pre><code>'+html.escape('\n'.join(code_lines))+'</code></pre>');code_lines=[]
            code=not code;continue
        if code:code_lines.append(line);continue
        if not line.strip():
            flush()
            if listing:out.append('</ul>');listing=False
            continue
        heading=re.match(r'^(#{1,4})\s+(.+)',line)
        if heading:
            flush()
            if listing:out.append('</ul>');listing=False
            n=len(heading[1]);out.append(f'<h{n}>'+inline(heading[2])+f'</h{n}>');continue
        if re.match(r'^\s*[-*]\s+',line):
            flush()
            if not listing:out.append('<ul>');listing=True
            out.append('<li>'+inline(re.sub(r'^\s*[-*]\s+','',line))+'</li>');continue
        if listing:out.append('</ul>');listing=False
        paragraph.append(line)
    flush()
    if listing:out.append('</ul>')
    if table:out.append('</table></div>')
    return '\n'.join(out)

def add_report(files,repo,metrics,provenance):
    from content_review import add_content_review
    add_content_review(files,repo,metrics)
    source=repo/'hybrid/TECHNICAL-REPORT.md'
    if not source.exists():raise ValueError('Technical report is required before publishing.')
    body=markdown(source.read_text())
    routes=metrics['regions']['region_routes']
    pages=''.join('<li><a href="'+html.escape(path,quote=True)+'">'+html.escape(path.removesuffix('.html').replace('-',' '))+'</a></li>' for path in routes)
    cards=[('İlçe servis sayfası',metrics['regions']['district_pages']),('Semt sayfası',metrics['regions']['locality_pages']),
           ('Mahalle kaydı',metrics['regions']['neighborhood_records']),('Yayımlanabilir canonical',metrics['semantics']['inventory']['actual_canonical_pages'])]
    stats=''.join('<div><strong>'+str(value)+'</strong><span>'+label+'</span></div>' for label,value in cards)
    text=('<!doctype html><html lang="tr" data-st-mode="production"><head><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,follow">'
          '<title>Hibrit Matris Teknik Raporu | Sağlam Teknik</title>'
          '<meta name="description" content="Uygulanan bölge içeriği, arama, yapılandırılmış veri ve performans değişikliklerinin teknik raporu.">'
          '<link rel="canonical" href="https://saglamkombiklima.com.tr/teknik-rapor.html">'
          '<style>body{margin:0;background:#f4f1e8;color:#173b32;font:17px/1.7 system-ui,sans-serif}main{max-width:1050px;margin:auto;padding:28px 20px 80px}a{color:#174d40;text-underline-offset:4px}h1{font-size:clamp(28px,5vw,44px);line-height:1.15}h2{margin-top:2em;border-top:1px solid #c9d0bf;padding-top:1em}h3{margin-top:1.5em}p,li{overflow-wrap:anywhere}code{background:#e7e9dc;padding:2px 4px;border-radius:3px}pre{background:#e7e9dc;padding:16px;overflow:auto}pre code{padding:0}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:24px 0}.stats div{background:#fffdf8;border:1px solid #ccd5c3;border-radius:12px;padding:16px}.stats strong{display:block;font-size:30px}.stats span{font-size:14px}.pages{columns:2;column-width:260px}.pages li{break-inside:avoid}.notice{background:#e6ecd9;border-left:4px solid #315f47;padding:14px 18px}footer{border-top:1px solid #b8c5b0;padding-top:20px;margin-top:30px;font-size:13px}</style></head><body><main>'
          '<a href="index.html">← Siteyi aç</a><div class="stats">'+stats+'</div>'
          '<p class="notice">Bu rapor kod ve dosya kontrollerini açıklar. Canlı sunucuda Telegram/Gemini teslimi, Google dizini ve reklam hesabı sonuçları ayrıca doğrulanır.</p>'
          +body+'<h2>Bölge sayfalarını tek tek açın</h2><ul class="pages">'+pages+'</ul>'
          '<footer>Esas alınan a1.zip SHA-256: <code>'+provenance['archive_sha256']+'</code><br>'
          'Kaynak dosya ağacı doğrulandı: '+str(provenance['files'])+' dosya. Bu rapor arama dizinine kapalıdır.</footer></main></body></html>')
    text=text.replace('</style>','code,footer{overflow-wrap:anywhere;word-break:break-word}pre{max-width:100%;box-sizing:border-box}</style>')
    files['teknik-rapor.html']=text.encode()
    files['KURULUM-HIBRIT.txt']=('SAĞLAM TEKNİK — HİBRİT PAKET\n\n'
        '1. Önce mevcut web dosyaları ve çalışma veritabanının yedeğini alın.\n'
        '2. ZIP içeriğini PHP destekli asıl sitenin web köküne açın. Dosyalar ZIP kökündedir.\n'
        '3. private/saglam-teknik içindeki mevcut API ayarlarını, veritabanını ve müşteri kayıtlarını koruyun. Bu paket bunları içermez.\n'
        '4. PHP dosyaları GitHub Pages üzerinde çalışmaz. GitHub önizlemesi gönderimleri bilerek kapatır.\n'
        '5. Üretim paketinde test uyarısı ve seo-preview-guard.js bulunmaz. Ana sayfada canlıya özgü test uyarısı görürseniz doğru paketi ve önbelleği kontrol edin.\n'
        '6. Canlı sunucuda mevcut cron/worker, dosya izinleri, PHP eklentileri ve özel ayar yolu ayrıca korunup kontrol edilmelidir.\n'
        '7. Gerçek servis formu, Telegram teslimi ve Gemini yanıtı canlı işletme ayarlarıyla denenmeden teslim doğrulandı denmez.\n'
        '8. sitemap.xml sadece yayımlanabilir canonical sayfaları içerir. Search Console’da önemli sayfaları URL Denetimi ile değerlendirin.\n'
        '9. teknik-rapor.html uygulama ve test kapsamını açıklar; noindex olarak bırakın.\n').encode()
