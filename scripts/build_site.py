#!/usr/bin/env python3
"""Deterministic, dependency-free preview/production builder. Never deploys."""
from __future__ import annotations
import argparse
import base64
import hashlib
import html
import io
import importlib.util
import json
import posixpath
import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA256 = '1e1af83e7bc6233f8af88f89a5873440288caed73cb4173483106f050ec5eb7b'
TEXT_SUFFIXES = {'.html', '.js', '.css', '.json', '.xml', '.txt', '.svg', '.php'}
PRIVATE_NAMES = {'owner-admin.html', 'owner-admin.js', 'trusted-proxies.json'}
PREVIEW_MARKER = '<meta name="saglam-test-site" content="static-preview">'
LOCAL_PREVIEW_FORMS = {'regionFinder', 'svcSearchForm', 'homeGuideSearch'}
# Same manufacturer document 300032122 Rev.04; repair its malformed archive URL.
SOURCE_URL_REPLACEMENTS = {
    'https://www.baymak.com.tr/media/4994/baymak-duotec-premix-tam-yogusmali-kombi-kullanma-k%E8%80%83avuzu.pdf':
    'https://www.baymak.com.tr/media/4608/baymak-duotec-premix-tam-yogusmali-kombi-kullanma-k%C4%B1lavuzu.pdf',
}

def visitor(path: Path) -> bool:
    return path.suffix == '.html' and path.name not in PRIVATE_NAMES and not re.match(r'(google|yandex_).*\.html$', path.name)

def blocked_preview(path: PurePosixPath) -> bool:
    return (path.suffix.lower() in {'.php', '.sqlite', '.db', '.log', '.env'}
            or path.name in PRIVATE_NAMES or path.name.startswith('.') and path.name != '.nojekyll'
            or any(x.lower() in {'private', '_private', 'server', 'private-examples', 'node_modules', '.git'} for x in path.parts)
            or bool(re.match(r'(google|yandex_).*\.html$', path.name)))

def archive_files(root: Path, integrity: dict | None = None) -> dict[str, bytes]:
    parts = sorted((root / 'preview-parts').glob('part-*.txt'))
    if [p.name for p in parts] != [f'part-{i:03d}.txt' for i in range(43)]:
        raise ValueError('Expected exactly part-000.txt through part-042.txt')
    encoded = ''.join(p.read_text(encoding='ascii') for p in parts)
    archive = base64.b64decode(re.sub(r'\s+', '', encoded), validate=True)
    archive_sha256 = hashlib.sha256(archive).hexdigest()
    if archive_sha256 != ARCHIVE_SHA256:
        raise ValueError('Original preview archive SHA-256 mismatch')
    if integrity is not None:
        integrity.update(archive_sha256=archive_sha256, archive_bytes=len(archive))
    result = {}
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for item in z.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in item.filename or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError(f'Unsafe archive path: {item.filename}')
            if not item.is_dir():
                result[path.as_posix()] = z.read(item)
    return result

def overlay(files: dict[str, bytes], directory: Path) -> None:
    if not directory.exists():
        return
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symlinks are not build inputs: {path}')
        if path.is_file():
            files[path.relative_to(directory).as_posix()] = path.read_bytes()

def sync_catalog_data(files: dict[str, bytes]) -> None:
    """Publish backend JSON and browser/search data from the same reviewed rows.

    A data addition without its readable HTML destination is a build error.
    Existing explanatory search entries remain; scoped definitions are derived.
    """
    if 'assets/verified-faults.json' not in files:
        return
    faults = json.loads(files['assets/verified-faults.json'])
    for model in faults['models']:
        page = PurePosixPath(model['path']).name
        text = files.get(page, b'').decode('utf-8')
        if model.get('manual', {}).get('source_available') is False:
            if any(row.get('matchable') is not False for row in model['codes']):
                raise ValueError('Unavailable manual must not have automatic code definitions: ' + model['id'])
            unavailable = model['manual']['url']
            def source_link(match):
                return '<span aria-disabled="true">Üretici kaynağı (bağlantı şu anda kullanılamıyor)</span>' if html.unescape(match[2]) == unavailable else match[0]
            text = re.sub(r'<a\b[^>]*\bhref=(["\'])(.*?)\1[^>]*>[\s\S]*?</a>', source_link, text, flags=re.I)
            note = '<aside class="mb-scope-note" data-manual-unavailable="true" role="note"><strong>Üretici belgesine şu anda erişilemiyor.</strong> Aşağıdaki tablo geçmiş belge kaydıdır; güncel teknik açıklama olarak otomatik kullanılmaz. Tam model ve belge sürümü yeniden doğrulanmalıdır.</aside>'
            if 'data-manual-unavailable=' not in text:
                text = re.sub(r'(<section\b[^>]*class="[^"\n]*\bfault-table-section\b[^"\n]*"[^>]*>)', lambda m: note + m[0], text, count=1)
            files[page] = text.encode('utf-8')
        for row in model['codes']:
            if not re.search(r'\bid=["\']' + re.escape(row['anchor']) + r'["\']', text):
                raise ValueError('Fault definition has no readable HTML anchor: ' + model['id'] + ' / ' + row['code'])
    encode = lambda data: json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    files['assets/verified-faults.js'] = b'window.ST_VERIFIED_FAULTS=' + encode(faults) + b';\n'
    if 'assets/organic-catalog.json' in files:
        catalog = json.loads(files['assets/organic-catalog.json'])
        unavailable_ids = {model['id'] for model in faults['models'] if model.get('manual', {}).get('source_available') is False}
        for model in catalog.get('models', []):
            if model.get('id') in unavailable_ids:
                model.update(code_definitions_verified=False, verified_source=False, source_unavailable=True)
        catalog['guides'] = [row for row in catalog['guides'] if not row.get('code_definition_verified')]
        for model in faults['models']:
            for row in model['codes']:
                if row.get('matchable') is False or row.get('source_conflict'):
                    continue
                catalog['guides'].append({'device':model['device'], 'brand':model['brand'], 'model':model['label'], 'model_id':model['id'], 'error_code':row['code'], 'path':model['path']+'#'+row['anchor'], 'status':'published', 'code_definition_verified':True, 'verified_source':True})
        payload = encode(catalog)
        files['assets/organic-catalog.json'] = payload + b'\n'
        files['assets/organic-catalog.js'] = b'window.ST_ORGANIC_CATALOG=' + payload + b';\n'
        if 'organic-catalog.js' in files:
            files['organic-catalog.js'] = files['assets/organic-catalog.js']

def local_url(url: str, prefix: str) -> str:
    """Mount one root URL exactly once; keep external/protocol-relative URLs intact."""
    if not url.startswith('/') or url.startswith('//'):
        return url
    if prefix and (url == prefix or url.startswith(prefix + '/') or url.startswith(prefix + '#') or url.startswith(prefix + '?')):
        return url
    # The immutable archive was exported for /site/. Editable sources use /.
    if url.startswith('/site/'):
        url = url[len('/site'):]
    elif url == '/site':
        url = '/'
    return prefix + url

def normalize_javascript(text: str, prefix: str, files: dict[str, bytes]) -> str:
    """Rewrite published file URLs, never JS path predicates or base fragments.

    A '/' or '/maps/embed' literal may describe an external URL or a comparison;
    it is not evidence of site navigation. Real home navigation uses the shared
    header URL. Template HTML and generated data use the same known-file rule.
    """
    def rewrite(match):
        url = match[2]
        candidate = url
        if prefix and (candidate == prefix or candidate.startswith(prefix + '/')):
            candidate = candidate[len(prefix):] or '/'
        if candidate.startswith('/site/'):
            candidate = candidate[len('/site'):]
        key = re.split(r'[?#]', candidate, maxsplit=1)[0].lstrip('/')
        if key not in files:
            return match[0]
        return match[1] + local_url(url, prefix) + match[1]
    return re.sub(r'(["\'`])(/(?!/)[^"\'`<>\s]*)(?=\1)\1', rewrite, text)

def normalize_paths(text: str, prefix: str, files: dict[str, bytes] | None = None) -> str:
    """Idempotent markup/CSS URL normalization, with semantic inline JS handling."""
    def markup(part):
        def srcset(match):
            value = re.sub(r'(^|,\s*)(/(?!/)[^,\s]+)', lambda m: m[1] + local_url(m[2], prefix), match[2])
            return 'srcset=' + match[1] + value + match[1]
        part = re.sub(r'\bsrcset=(["\'])(.*?)\1', srcset, part)
        part = re.sub(r'(["\'`])(/(?!/)[^"\'`<>\s]*)(?=\1)\1',
                      lambda m: m[1] + local_url(m[2], prefix) + m[1], part)
        return re.sub(r'url\(\s*(/(?!/)[^\s)]+)', lambda m: 'url(' + local_url(m[1], prefix), part)
    if files is None:
        return markup(text)
    chunks = re.split(r'(<script\b[^>]*>[\s\S]*?</script\s*>)', text, flags=re.I)
    for i, part in enumerate(chunks):
        script = re.fullmatch(r'(<script\b[^>]*>)([\s\S]*?)(</script\s*>)', part, flags=re.I)
        if script:
            chunks[i] = markup(script[1]) + normalize_javascript(script[2], prefix, files) + script[3]
        else:
            chunks[i] = markup(part)
    return ''.join(chunks)

def clean_preview_html(text: str) -> str:
    if re.search(r'<meta\b[^>]*name=["\']saglam-test-site["\']', text, re.I):
        text = re.sub(r'<meta\b[^>]*name=["\']robots["\'][^>]*>', '', text, flags=re.I)
    text = re.sub(r'<meta\b[^>]*name=["\']saglam-test-site["\'][^>]*>', '', text, flags=re.I)
    text = re.sub(r'<div\b[^>]*id=["\']st-preview-banner["\'][^>]*>[\s\S]*?</div>', '', text, flags=re.I)
    text = re.sub(r'<(?:link|script)\b[^>]*(?:preview-readability|preview-enhancements)[^>]*>(?:</script>)?', '', text, flags=re.I)
    return text

def allow_local_preview_forms(text: str) -> str:
    """Permit known local navigation/search handlers; keep write forms blocked."""
    def mark(match):
        tag = match[0]
        form_id = re.search(r'\bid=["\']([^"\']+)["\']', tag, re.I)
        if not form_id or form_id[1] not in LOCAL_PREVIEW_FORMS:
            return tag
        tag = re.sub(r'\s+data-preview-local=["\'][^"\']*["\']', '', tag, flags=re.I)
        return tag[:-1] + ' data-preview-local="true">'
    return re.sub(r'<form\b[^>]*>', mark, text, flags=re.I)

def insert_head(text: str, addition: str) -> str:
    return re.sub(r'(<head\b[^>]*>)', lambda m: m[1] + addition, text, count=1, flags=re.I)

def production_seo(text: str, tags: list[str]) -> str:
    # Keep edited canonical/schema when supplied; otherwise restore original SEO.
    additions = []
    for tag in tags:
        if 'application/ld+json' in tag and 'application/ld+json' in text:
            continue
        if re.match(r'<link', tag, re.I) and re.search(r'rel=["\']canonical["\']', text, re.I):
            continue
        if 'og:url' in tag and re.search(r'property=["\']og:url["\']', text, re.I):
            continue
        if re.search(r'name=["\']robots["\']', tag, re.I) and re.search(r'name=["\']robots["\']', text, re.I):
            continue
        additions.append(tag)
    return insert_head(text, ''.join(additions))

def apply_brand(text: str, brand: dict) -> str:
    """Replace legacy business-logo references with the supplied image, centrally."""
    def favicon(match):
        tag = re.sub(r'href=["\'][^"\']*["\']', 'href="' + brand['favicon'] + '"', match[0])
        tag = re.sub(r'\s+(?:type|sizes)=["\'][^"\']*["\']', '', tag)
        return tag[:-1] + ' type="image/png">'
    text = re.sub(r'<link\b(?=[^>]*rel=["\'](?:shortcut )?icon["\'])[^>]*>', favicon, text, flags=re.I)
    text = re.sub(r'(?P<quote>["\'])(?P<origin>https://saglamkombiklima\.com\.tr)?(?:/site/|/|\./)?logo\.(?:png|svg)(?P=quote)',
                  lambda m: m['quote'] + (m['origin'] or '') + brand['logo'] + m['quote'], text)
    for alias in brand.get('logo_aliases', []):
        text = text.replace(alias, brand['logo'])
    return text

def version_assets(text: str, files: dict[str, bytes], prefix: str = '/site', name: str = 'index.html') -> str:
    """Version HTML assets from final served bytes, including custom mounts."""
    def rewrite(match):
        path = match['path']
        if urlsplit(path).scheme or path.startswith('//'):
            return match[0]
        key = path[len(prefix):] if prefix and path.startswith(prefix + '/') else path
        key = key.lstrip('/') if key.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(name), key))
        if not key.startswith('assets/') or key not in files:
            return match[0]
        version = hashlib.sha256(files[key]).hexdigest()[:10]
        return match['start'] + match['quote'] + path + '?v=' + version + match['quote']
    return re.sub(r'(?P<start>\b(?:src|href)=)(?P<quote>["\'])(?P<path>[^"\'?]+\.(?:css|js))(?:\?[^"\']*)?(?P=quote)',
                  rewrite, text)

def error_page_base(text: str, mode: str, prefix: str) -> str:
    """A 404 can be served at an arbitrary missing path; resolve its assets first.

    Github project pages expose their project segment. The local regression
    server uses the build's declared mount; official hosting uses its root.
    Normal visitor pages require neither a base tag nor a configured mount.
    """
    mount = prefix.strip('/') if mode == 'preview' else ''
    code = '''<script data-st-error-base>(function(){var h=location.hostname.toLowerCase(),p=location.pathname.split('/').filter(Boolean),m=DOCUMENT_MOUNT;if(h==='github.io'||h.endsWith('.github.io'))m=p[0]||'';else if(h==='saglamkombiklima.com.tr'||h==='www.saglamkombiklima.com.tr')m='';var b=document.createElement('base');b.href=new URL(m?m+'/':'./',location.origin+'/').href;document.head.prepend(b);})();</script>'''.replace('DOCUMENT_MOUNT', json.dumps(mount))
    return insert_head(text, code)

def error_page_resources(text: str) -> str:
    """Prevent speculative 404 asset requests before the computed base exists.

    Only the error document needs this: a server may return it for any missing
    nested path. Parser-written resource tags retain normal defer ordering, while
    the preload scanner cannot mistake their URLs for missing-path resources.
    Canonical, noindex, navigation and readable error text remain ordinary HTML.
    """
    def write(match):
        tag = match[0]
        if tag.lower().startswith('<link') and re.search(r'\brel=["\']canonical["\']', tag, re.I):
            return tag
        payload = json.dumps(tag, ensure_ascii=False).replace('<', '\\u003c')
        return '<script data-st-404-resource>document.write(' + payload + ');</script>'
    pattern = r'<script\b(?=[^>]*\bsrc=)[^>]*>\s*</script\s*>|<link\b(?=[^>]*\bhref=)[^>]*>|<(?:img|source|image)\b[^>]*>'
    return re.sub(pattern, write, text, flags=re.I)

def build(root: Path, output: Path, mode: str, prefix: str) -> dict:
    output = output.resolve()
    protected = [root / name for name in ('overrides', 'server', 'scripts', 'tests', 'docs', 'components', 'preview-parts', '.git')]
    if output == root or output in root.parents or any(output == p or p in output.parents or output in p.parents for p in protected):
        raise ValueError('Output must be a separate generated directory')
    archive_integrity = {}
    files = archive_files(root, archive_integrity)
    if mode == 'production':
        overlay(files, root / 'server')
        installation = root / 'docs/PLESK-KURULUM.md'
        if installation.is_file():
            files['KURULUM-ONCESI.txt'] = installation.read_bytes()
    overlay(files, root / 'overrides')
    for name, content in list(files.items()):
        if PurePosixPath(name).suffix in TEXT_SUFFIXES:
            for old, new in SOURCE_URL_REPLACEMENTS.items():
                content = content.replace(old.encode('utf-8'), new.encode('utf-8'))
            files[name] = content
    sync_catalog_data(files)
    brand = json.loads((root / 'components/brand.json').read_text())
    for key in ('logo', 'favicon'):
        if not brand[key].startswith('/assets/brand/') or brand[key].lstrip('/') not in files:
            raise ValueError('Missing canonical brand asset: ' + key)
    registry_path = root / 'scripts/brand_registry.py'
    if registry_path.exists():
        spec = importlib.util.spec_from_file_location('saglam_brand_registry', registry_path)
        registry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(registry)
        registry.build_registry(files)
    home_renderer_path = root / 'scripts/render_home.py'
    if home_renderer_path.exists():
        spec = importlib.util.spec_from_file_location('saglam_render_home', home_renderer_path)
        home_renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(home_renderer)
        home_renderer.render_home(files, root)
    enhancement_count = 0
    enhancer_path = root / 'scripts/enhance_models.py'
    if enhancer_path.exists():
        spec = importlib.util.spec_from_file_location('saglam_enhance_models', enhancer_path)
        enhancer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(enhancer)
        enhancement_count = enhancer.enhance_files(files)
    landing_path = root / 'scripts/landing_actions.py'
    if landing_path.exists():
        spec = importlib.util.spec_from_file_location('saglam_landing_actions', landing_path)
        landings = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(landings)
        landings.enhance_landings(files)
    linking_path = root / 'scripts/internal_links.py'
    if linking_path.exists():
        spec = importlib.util.spec_from_file_location('saglam_internal_links', linking_path)
        linking = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(linking)
        linking.enhance_files(files)
    master_stats = {}
    master_path = root / 'scripts/master_content.py'
    if master_path.exists():
        spec = importlib.util.spec_from_file_location('saglam_master_content', master_path)
        master = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(master)
        master_stats = master.enhance_files(files)
    files.pop('TEST-KAPSAMI.txt', None)
    files.pop('CNAME', None)
    files.pop('reviews-section.html', None)  # source fragment, not a public route
    seo = json.loads((root / 'scripts/production-seo.json').read_text())
    html_count = 0
    built = {}
    for name, content in sorted(files.items()):
        path = PurePosixPath(name)
        if mode == 'preview' and blocked_preview(path):
            continue
        if path.suffix.lower() in {'.db', '.sqlite', '.sqlite3', '.log', '.env'} or any(x in {'private', '_private', 'templates'} for x in path.parts):
            continue
        if path.suffix in TEXT_SUFFIXES:
            text = content.decode('utf-8')
            if visitor(Path(name)):
                for element, css_class in [('header','at-header'), ('footer','at-footer')]:
                    component = root / 'components' / (element + '.html')
                    if component.exists():
                        if element == 'footer':
                            text = re.sub(r'<nav\b[^>]*class=["\'][^"\']*\bat-mobile-contact\b[^"\']*["\'][^>]*>[\s\S]*?</nav>', '', text, flags=re.I)
                        pattern = r'<' + element + r'\b[^>]*class=["\'][^"\']*\b' + css_class + r'\b[^"\']*["\'][^>]*>[\s\S]*?</' + element + '>'
                        text = re.sub(pattern, lambda _: component.read_text(), text, count=1, flags=re.I)
            if visitor(Path(name)):
                text = clean_preview_html(text)
                text = re.sub(r'(<html\b)([^>]*>)', lambda m: m[1] + f' data-st-mode="{mode}"' + re.sub(r'\s+data-st-mode=["\'][^"\']*["\']', '', m[2], flags=re.I), text, count=1, flags=re.I)
                text = re.sub(r'(<body\b)([^>]*>)', lambda m: m[1] + f' data-st-mode="{mode}"' + re.sub(r'\s+data-st-mode=["\'][^"\']*["\']', '', m[2], flags=re.I), text, count=1, flags=re.I)
                text = allow_local_preview_forms(text)
                if 'assets/environment.js' in files:
                    text = insert_head(text, '<script src="/assets/environment.js"></script>')
                if 'assets/brand-registry.js' in files and 'assets/brand-registry.js' not in text:
                    text = insert_head(text, f'<script src="{prefix}/assets/brand-registry.js" defer></script>')
                if mode == 'preview':
                    text = insert_head(text, '<meta name="robots" content="noindex,nofollow,noarchive">' + PREVIEW_MARKER
                        + '<meta http-equiv="Content-Security-Policy" content="form-action &#39;none&#39;; frame-src &#39;none&#39;; object-src &#39;none&#39;; worker-src &#39;none&#39;; base-uri &#39;self&#39;">'
                        + f'<script src="{prefix}/assets/preview-guard.js"></script>')
                    banner = '<div id="st-preview-banner" role="note">TEST ÖN İZLEMESİ · Form, konum ve ileti gönderimi kapalıdır. Bilgiler kaydedilmez.</div>'
                    text = re.sub(r'(<body\b[^>]*>)', lambda m: m[1] + banner, text, count=1, flags=re.I)
                else:
                    text = production_seo(text, seo.get(name, []))
                if 'assets/premium.css' in files and 'assets/premium.css' not in text:
                    text = text.replace('</head>', f'<link rel="stylesheet" href="{prefix}/assets/premium.css"></head>')
                if 'assets/premium.js' in files and 'assets/premium.js' not in text:
                    text = text.replace('</body>', f'<script src="{prefix}/assets/premium.js" defer></script></body>')
                additions = []
                if name == 'model-ariza-kodlari.html':
                    additions = ['assets/model-browser.css', 'assets/model-browser.js']
                elif name.endswith('-ariza-kodlari.html'):
                    additions = ['assets/model-page.js']
                for asset in additions:
                    if asset in files and asset not in text:
                        tag = f'<link rel="stylesheet" href="{prefix}/{asset}">' if asset.endswith('.css') else f'<script src="{prefix}/{asset}" defer></script>'
                        target = '</head>' if asset.endswith('.css') else '</body>'
                        text = text.replace(target, tag + target)
                text = re.sub(r'<meta\b[^>]*\bcharset\s*=[^>]*>', '', text, flags=re.I)
                if not re.search(r'<link\b[^>]*rel=["\'](?:shortcut )?icon["\']', text, re.I):
                    text = insert_head(text, f'<link rel="icon" href="{brand["favicon"]}" type="image/png">')
                text = insert_head(text, '<meta charset="UTF-8">')
                if name == '404.html':
                    text = error_page_base(text, mode, prefix)
                html_count += 1
            elif path.name == 'owner-admin.html' and mode == 'production':
                text = re.sub(r'(<html\b)([^>]*>)', lambda m: m[1] + ' data-st-mode="production"' + re.sub(r'\s+data-st-mode=["\'][^"\']*["\']', '', m[2], flags=re.I), text, count=1, flags=re.I)
                if 'assets/environment.js' in files:
                    text = insert_head(text, '<script src="/assets/environment.js"></script>')
            text = apply_brand(text, brand)
            if path.suffix in {'.js', '.json'}:
                text = normalize_javascript(text, prefix, files)
            elif path.suffix in {'.html', '.svg', '.css'}:
                text = normalize_paths(text, prefix, files)
            content = text.encode('utf-8')
        built[name] = content
    if mode == 'preview':
        built['assets/preview-guard.js'] = (root / 'scripts/preview-guard.js').read_bytes()
        # Allow crawling so robots noindex can actually be observed.
        built['robots.txt'] = b'User-agent: *\nAllow: /\n'
        built.pop('sitemap.xml', None)
    built['.nojekyll'] = b''
    for module_name in ('semantic_seo', 'portable_paths'):
        module_path = root / 'scripts' / (module_name + '.py')
        if module_path.exists():
            spec = importlib.util.spec_from_file_location('saglam_' + module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if module_name == 'portable_paths':
                module.enhance_files(built, prefix)
            else:
                module.enhance_files(built)
    # All runtime assets are transformed now. Hash the bytes actually served,
    # rather than source bytes which may have different deployment paths.
    for name in built:
        if visitor(Path(name)):
            built[name] = version_assets(built[name].decode('utf-8'), built, prefix, name).encode('utf-8')
            if name == '404.html':
                built[name] = error_page_resources(built[name].decode('utf-8')).encode('utf-8')
    digest = hashlib.sha256()
    for name, content in sorted(built.items()):
        digest.update(name.encode() + b'\0' + hashlib.sha256(content).digest())
    report = {'schema_version': 1, 'mode': mode, 'base_path': prefix or '/', 'archive_sha256': archive_integrity['archive_sha256'],
              'archive_sha256_kind': 'immutable-source-archive', 'archive_bytes': archive_integrity['archive_bytes'],
              'visitor_pages': html_count, 'model_pages_enhanced': enhancement_count, 'files': len(built), 'content_sha256': digest.hexdigest(),
              'static_master': master_stats, 'production_deployed': False}
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name, content in sorted(built.items()):
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    (output / 'build-info.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['preview', 'production'], default='preview')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--base-path', help='Preview URL prefix; default /site. Production always uses /.')
    parser.add_argument('--root', type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args()
    prefix = '/' + (args.base_path or '/site').strip('/') if args.mode == 'preview' else ''
    if prefix == '/':
        prefix = ''
    if prefix and not re.fullmatch(r'/[a-zA-Z0-9_/-]+', prefix):
        parser.error('Invalid base path')
    output = args.output or args.root / ('_site' if args.mode == 'preview' else 'build/production')
    print(json.dumps(build(args.root.resolve(), output, args.mode, prefix), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
