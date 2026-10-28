#!/usr/bin/env python3
"""Publish the supplied static SEO export, independently of legacy source builds."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import argparse, gzip, hashlib, html, json, posixpath, re, zipfile

SOURCE_NAME = 'saglamkombiklima-seo.zip'
SITE_HOSTS = {'saglamkombiklima.com.tr', 'www.saglamkombiklima.com.tr'}
CONTACT_HOSTS = {'wa.me', 'api.whatsapp.com'}
EXPECTED_SOURCE = '702e308fb7c92d08acac2c9a59fe18f8d9b1a39b3643dffeebc54f57168e365a'

def readable_reference(m):
    value = html.unescape(m['url'])
    parsed = urlsplit(value)
    if parsed.scheme not in {'http', 'https'} or parsed.hostname in CONTACT_HOSTS:
        return m[0]
    if parsed.hostname in SITE_HOSTS:
        return m[0]
    return '<span class="st-source-reference">' + m['body'] + '</span>'

def build(repo, output):
    source = repo / SOURCE_NAME
    archive_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if archive_digest != EXPECTED_SOURCE:
        raise ValueError('Uploaded archive changed; review the new archive before publishing it.')
    with zipfile.ZipFile(source) as archive:
        files = {}
        for item in archive.infolist():
            name = item.filename
            if item.is_dir(): continue
            if name.startswith('/') or '..' in Path(name).parts or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unsafe ZIP entry')
            files[name] = archive.read(item)
    from content_correction import correct_content
    from route_correction import correct_routes
    report = {'source_archive_sha256': archive_digest,
              'content_corrections': correct_content(files),
              'route_corrections': correct_routes(files)}
    removed = []
    for name in list(files):
        parts = Path(name).parts
        if (Path(name).suffix.lower() in {'.php','.db','.sqlite','.sqlite3','.log','.env'}
            or any(p in {'private','_private','.git'} for p in parts)
            or name in {'.htaccess','owner-admin.html','assets/owner-admin.html'}
            or (name.endswith('.txt') and name not in {'robots.txt','llms.txt','llms-full.txt'})):
            removed.append(name); del files[name]
    report['excluded_runtime_files'] = sorted(removed)
    files['assets/seo-preview-guard.js'] = (repo/'scripts/preview-guard.js').read_bytes()
    banner = ('<aside id="st-preview-banner" role="status">İÇERİK ÖN İZLEMESİ · '
              'Form, Telegram ve Gemini gönderimleri kapalıdır. Bilgiler kaydedilmez.</aside>')
    outbound_count = 0
    for name, data in list(files.items()):
        if not name.endswith('.html'): continue
        text = data.decode('utf-8')
        text = re.sub(r'data-st-mode="production"', 'data-st-mode="preview"', text)
        text = re.sub(r'<meta\b(?=[^>]*\bname=["\']robots["\'])[^>]*>', '', text, flags=re.I)
        error_base = ''
        if name == '404.html':
            old_base = re.search(r'<script data-st-error-base>[\s\S]*?</script>', text)
            if old_base:
                error_base = old_base[0].replace("m='';var b=", "m='';else m=p.slice(0,-1).join('/');var b=")
                text = text.replace(old_base[0], '')
        text = re.sub(r'(<head\b[^>]*>)', r'\1'+error_base+'<meta name="robots" content="noindex,nofollow"><script src="'
                      + ('../' if name.startswith('assets/') else '')
                      + 'assets/seo-preview-guard.js"></script>', text, count=1, flags=re.I)
        text = re.sub(r'(<body\b[^>]*>)', lambda m: m[0]+banner, text, count=1, flags=re.I)
        pattern = r'<a\b[^>]*\bhref=["\'](?P<url>https?://[^"\']+)["\'][^>]*>(?P<body>[\s\S]*?)</a\s*>'
        def external(m):
            nonlocal outbound_count
            result = readable_reference(m)
            if result != m[0]: outbound_count += 1
            return result
        text = re.sub(pattern, external, text, flags=re.I)
        # Same-site navigation must stay on the mounted preview, never return to production.
        def attr(m):
            value = html.unescape(m['url']); parsed = urlsplit(value)
            if parsed.hostname in SITE_HOSTS:
                candidate = unquote(parsed.path).lstrip('/') or 'index.html'
                if candidate not in files: return m[0]
                value = posixpath.relpath(candidate, posixpath.dirname(name) or '.')
                value += ('?'+parsed.query if parsed.query else '') + ('#'+parsed.fragment if parsed.fragment else '')
            elif value.startswith('/') and not value.startswith('//'):
                candidate = unquote(parsed.path).removeprefix('/site/').lstrip('/') or 'index.html'
                if candidate not in files: return m[0]
                value = posixpath.relpath(candidate, posixpath.dirname(name) or '.')
                value += ('?'+parsed.query if parsed.query else '') + ('#'+parsed.fragment if parsed.fragment else '')
            return m['key']+'='+m['quote']+html.escape(value, quote=True)+m['quote']
        # Canonical/OG/schema retain production URLs; navigation and resource attributes are portable.
        text = re.sub(r'(?P<key>href|src|action)=(?P<quote>["\'])(?P<url>.*?)(?P=quote)',
                      lambda m: m[0] if m['key']=='href' and 'canonical' in text[max(0,m.start()-35):m.start()] else attr(m), text)
        files[name] = text.encode()
    report['external_anchors_converted_to_plain_references'] = outbound_count
    for name in ['assets/home.js','home.js']:
        if name not in files: continue
        text = files[name].decode()
        text = text.replace("const link=document.createElement('a');link.href=data.source_url;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Üretici kaynağını aç ↗';",
                            "const link=document.createElement('span');link.className='st-source-reference';link.textContent='Üretici belgesi referansı';")
        files[name] = text.encode()
    name = 'assets/ai-usta.js'
    text = files[name].decode()
    text = text.replace('<a href="${esc(model.manual.url)}" target="_blank" rel="noopener noreferrer">Üretici belgesini aç ↗</a>',
                        '<span class="st-source-reference">Üretici belgesi: ${esc(model.manual?.title||model.label)}</span>')
    files[name] = text.encode()
    # Measure overflow honestly rather than hiding it at the document boundary.
    name = 'assets/seo-hub.css'
    files[name] = files[name].replace(b'html,body{overflow-x:hidden}', b'')
    files['robots.txt'] = b'User-agent: *\nDisallow: /\n'
    # Preserve the previously delivered read-only review URL on the same Pages site.
    review = repo/'review-documents'
    if (review/'manifest.json').is_file():
        manifest = json.loads((review/'manifest.json').read_text())
        compressed = b''
        for part in manifest['parts']:
            data = (review/part['name']).read_bytes()
            assert len(data)==part['bytes'] and hashlib.sha256(data).hexdigest()==part['sha256']
            compressed += data
        assert hashlib.sha256(compressed).hexdigest()==manifest['gzip_sha256']
        review_html = gzip.decompress(compressed)
        assert hashlib.sha256(review_html).hexdigest()==manifest['html_sha256']
        pdf = (review/'saglam-teknik-inceleme.pdf').read_bytes()
        assert hashlib.sha256(pdf).hexdigest()==manifest['pdf_sha256'] and pdf.startswith(b'%PDF-')
        files['inceleme/index.html']=review_html
        files['inceleme/saglam-teknik-inceleme.pdf']=pdf
        files['inceleme/dosya-bilgileri.json']=(review/'manifest.json').read_bytes()
    old = json.loads(files.pop('build-info.json'))
    info = {'schema_version':1, 'mode':'preview', 'base_path':'/site',
            'archive_sha256':archive_digest, 'archive_sha256_kind':'reviewed-uploaded-zip',
            'archive_bytes':source.stat().st_size, 'source_commit':__import__('os').environ.get('GITHUB_SHA','local'),
            'visitor_pages':sum(n.endswith('.html') and not n.startswith(('assets/','inceleme/','google','yandex')) for n in files),
            'release_report':report, 'runtime_delivery_verified':False}
    digest=hashlib.sha256()
    for name in sorted(files): digest.update(name.encode()+b'\0'+hashlib.sha256(files[name]).digest())
    info.update(files=len(files),content_sha256=digest.hexdigest())
    files['build-info.json'] = (json.dumps(info,ensure_ascii=False,indent=2)+'\n').encode()
    output.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():
        path=output/name; path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    print(json.dumps({'source_archive_sha256':archive_digest,'pages':info['visitor_pages'],'content_sha256':info['content_sha256'], 'corrections':report},ensure_ascii=False,indent=2))
    return info

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build(Path(__file__).resolve().parents[1],args.output)
