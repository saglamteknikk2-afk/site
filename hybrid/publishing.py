"""Production/preview separation and navigation policy, independent of the content modules."""
from pathlib import Path
from urllib.parse import urlsplit, unquote
import gzip, hashlib, html, json, posixpath, re

ORIGIN='https://saglamkombiklima.com.tr/'
RETIRED={'klima-montaji.html','klima-sokumu.html'}

def retire_offers(files):
    for name in RETIRED:
        source=files[name].decode()
        title='Klima bakım ve arıza hizmetleri | Sağlam Teknik'
        source=re.sub(r'<title>.*?</title>','<title>'+title+'</title>',source,flags=re.S)
        source=re.sub(r'<meta\b(?=[^>]*name=["\']robots["\'])[^>]*>','',source,flags=re.I)
        source=source.replace('</head>','<meta name="robots" content="noindex,follow"></head>')
        content=('<main id="main-content" class="at-shell at-content"><h1>Klima bakım ve arıza hizmetleri</h1>'
                 '<p>Klima montajı ve sökümü için bu siteden hizmet talebi alınmıyor. '
                 'Bakım, soğutma ve ısıtma sorunları için ilgili servis bilgilerini inceleyebilirsiniz.</p>'
                 '<p><a href="klima-servisi.html">Klima servisi ve bakım bilgileri</a></p></main>')
        source=re.sub(r'<main\b[^>]*>[\s\S]*?</main>',content,source,count=1)
        files[name]=source.encode()
    for name,data in list(files.items()):
        if name.endswith('.html'):
            text=data.decode()
            for target in RETIRED:
                text=re.sub(r'<a\b(?P<attrs>[^>]*href=["\'])'+re.escape(target)+r'(?P<end>["\'][^>]*)>[\s\S]*?</a>',
                            lambda m:'<a'+m['attrs']+'klima-servisi.html'+m['end']+'>Klima bakım ve arıza servisi</a>',text)
            text=text.replace('Klima Bakımı, Tamiri, Montaj ve Gaz Dolumu','Klima Bakımı ve Arıza Onarımı')
            text=text.replace('söküm-montaj ve arıza onarımı','bakım ve arıza onarımı')
            text=text.replace('klima bakımı, montajı ve tamiri','klima bakımı ve tamiri')
            files[name]=text.encode()
    for name in ['assets/servis-verileri.js','servis-verileri.js']:
        if name not in files:continue
        text=files[name].decode();match=re.search(r'window\.ST_SERVICE_DATA\s*=\s*(\{.*\});\s*$',text,re.S)
        if not match:raise ValueError('Unexpected service data format.')
        data=json.loads(match[1])
        for device in data['devices'].values():device['services']=[s for s in device['services'] if s['path'].lstrip('/') not in RETIRED]
        data['paths']=[p for p in data.get('paths',[]) if p.lstrip('/') not in RETIRED]
        for key in ['selection_matrix','source_rows','normalized_queries','status_counts']:data.pop(key,None)
        files[name]=('window.ST_SERVICE_DATA='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n').encode()
    for name in ['assets/organic-catalog.js','assets/organic-catalog.json']:
        if name not in files:continue
        text=files[name].decode();data=json.loads(text.removeprefix('window.ST_ORGANIC_CATALOG=').strip().removesuffix(';'))
        data['published_routes']=[p for p in data['published_routes'] if p.lstrip('/') not in RETIRED]
        payload=json.dumps(data,ensure_ascii=False,separators=(',',':'))
        files[name]=(('window.ST_ORGANIC_CATALOG='+payload+';\n') if name.endswith('.js') else payload+'\n').encode()
    return {'retired_service_offer_routes':sorted(RETIRED),'old_urls_preserved_as_noindex_information':True}

def apply_publication_policy(files):
    converted=0
    for name,data in list(files.items()):
        if not name.endswith('.html'):continue
        text=data.decode()
        def anchor(m):
            nonlocal converted
            parsed=urlsplit(html.unescape(m['url']))
            if parsed.hostname in {'wa.me','api.whatsapp.com'}:return m[0]
            if parsed.hostname in {'saglamkombiklima.com.tr','www.saglamkombiklima.com.tr'}:
                target=unquote(parsed.path).lstrip('/') or 'index.html'
                if target in files:
                    route=posixpath.relpath(target,posixpath.dirname(name) or '.')
                    route+=('?'+parsed.query if parsed.query else '')+('#'+parsed.fragment if parsed.fragment else '')
                    return m[0].replace(m['url'],html.escape(route,quote=True),1)
            converted+=1
            return '<span class="st-source-reference">'+m['body']+'</span>'
        text=re.sub(r'<a\b[^>]*href=["\'](?P<url>https?://[^"\']+)["\'][^>]*>(?P<body>[\s\S]*?)</a\s*>',anchor,text,flags=re.I)
        # Strip obsolete build-specific test statements from the new production artifact.
        text=re.sub(r'<aside\b[^>]*id=["\']st-preview-banner["\'][^>]*>[\s\S]*?</aside>','',text,flags=re.I)
        files[name]=text.encode()
    for name in ['assets/home.js','home.js']:
        if name not in files:continue
        text=files[name].decode().replace("const link=document.createElement('a');link.href=data.source_url;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Üretici kaynağını aç ↗';",
            "const link=document.createElement('span');link.className='st-source-reference';link.textContent='Üretici belgesi referansı';")
        files[name]=text.encode()
    name='assets/ai-usta.js';text=files[name].decode()
    text=text.replace('<a href="${esc(model.manual.url)}" target="_blank" rel="noopener noreferrer">Üretici belgesini aç ↗</a>',
                      '<span class="st-source-reference">Üretici belgesi: ${esc(model.manual?.title||model.label)}</span>')
    files[name]=text.encode()
    business=json.loads(files['isletme-bilgileri.json'])
    business['address']={'streetAddress':'İnönü Mahallesi','addressLocality':'Küçükçekmece','addressRegion':'İstanbul','addressCountry':'TR'}
    business['address_provenance']='İşletme sahibinin 28.10.2026 tarihli beyanı; sokak/bina numarası veya harita koordinatı eklenmedi.'
    business['limitations']=business.get('limitations','').replace('Adres, çalışma saatleri ve harita konumu ayrıca yapılandırılır;','Çalışma saatleri ve harita konumu ayrıca yapılandırılır;')
    files['isletme-bilgileri.json']=(json.dumps(business,ensure_ascii=False,indent=2)+'\n').encode()
    name='isletme-bilgileri.html';text=files[name].decode()
    if 'hybrid-business-address' not in text:
        text=text.replace('</main>','<section class="hybrid-business-address"><h2>İşletme bölgesi</h2><p>İnönü Mahallesi, Küçükçekmece, İstanbul, TR</p><p>Yerinde servis için adres ve randevu uygunluğu görüşmede netleştirilir.</p></section></main>')
    files[name]=text.encode()
    removed=[]
    for name in list(files):
        if name.endswith('.txt') and name not in {'robots.txt','llms.txt','llms-full.txt','assets/comfort-pets-asset-note.txt'}:
            removed.append(name);del files[name]
    # These old text reports describe a different release and are replaced by the generated report.
    return {'outbound_navigation_replaced_with_plain_references':converted,'obsolete_release_notes_removed':removed}

def preview_files(files,repo):
    files=dict(files);removed=[]
    for name in list(files):
        if Path(name).suffix.lower() in {'.php','.db','.sqlite','.sqlite3','.log','.env'} or name in {'.htaccess','owner-admin.html','assets/owner-admin.html'} or any(p in {'private','_private','.git'} for p in Path(name).parts):
            removed.append(name);del files[name]
    files['assets/seo-preview-guard.js']=(repo/'scripts/preview-guard.js').read_bytes()
    banner=('<aside id="st-preview-banner" role="status">TEST ÖN İZLEMESİ · '
            'Form, konum, Telegram ve Gemini gönderimleri kapalıdır. Bilgiler kaydedilmez.</aside>')
    for name,data in list(files.items()):
        if not name.endswith('.html') or name.startswith(('google','yandex')):continue
        text=data.decode().replace('data-st-mode="production"','data-st-mode="preview"')
        text=re.sub(r'<meta\b(?=[^>]*name=["\']robots["\'])[^>]*>','',text,flags=re.I)
        base=''
        if name=='404.html':
            old=re.search(r'<script data-st-error-base>[\s\S]*?</script>',text)
            if old:
                base=old[0].replace("m='';var b=","m='';else m=p.slice(0,-1).join('/');var b=");text=text.replace(old[0],'')
        guard=posixpath.relpath('assets/seo-preview-guard.js',posixpath.dirname(name) or '.')
        text=re.sub(r'(<head\b[^>]*>)',lambda m:m[0]+base+'<meta name="robots" content="noindex,nofollow"><script src="'+guard+'"></script>',text,count=1,flags=re.I)
        text=re.sub(r'(<body\b[^>]*>)',lambda m:m[0]+banner,text,count=1,flags=re.I)
        files[name]=text.encode()
    files['robots.txt']=b'User-agent: *\nDisallow: /\n'
    return files, {'runtime_files_excluded':len(removed),'preview_contact_and_provider_delivery_disabled':True}

def retain_review(files,repo):
    source=repo/'review-documents'
    if not (source/'manifest.json').exists():return
    manifest=json.loads((source/'manifest.json').read_text());compressed=b''
    for part in manifest['parts']:
        chunk=(source/part['name']).read_bytes();assert hashlib.sha256(chunk).hexdigest()==part['sha256'];compressed+=chunk
    page=gzip.decompress(compressed);assert hashlib.sha256(page).hexdigest()==manifest['html_sha256']
    pdf=(source/'saglam-teknik-inceleme.pdf').read_bytes();assert hashlib.sha256(pdf).hexdigest()==manifest['pdf_sha256']
    files['inceleme/index.html']=page;files['inceleme/saglam-teknik-inceleme.pdf']=pdf
    files['inceleme/dosya-bilgileri.json']=(source/'manifest.json').read_bytes()
