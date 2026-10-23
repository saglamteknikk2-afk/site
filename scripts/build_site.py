#!/usr/bin/env python3
"""Deterministic, dependency-free preview/production builder. Never deploys."""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import importlib.util
import json
import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA256 = '1e1af83e7bc6233f8af88f89a5873440288caed73cb4173483106f050ec5eb7b'
TEXT_SUFFIXES = {'.html', '.js', '.css', '.json', '.xml', '.txt', '.svg', '.php'}
PRIVATE_NAMES = {'owner-admin.html', 'owner-admin.js', 'trusted-proxies.json'}
PREVIEW_MARKER = '<meta name="saglam-test-site" content="static-preview">'

def visitor(path: Path) -> bool:
    return path.suffix == '.html' and path.name not in PRIVATE_NAMES and not re.match(r'(google|yandex_).*\.html$', path.name)

def blocked_preview(path: PurePosixPath) -> bool:
    return (path.suffix.lower() in {'.php', '.sqlite', '.db', '.log', '.env'}
            or path.name in PRIVATE_NAMES or path.name.startswith('.') and path.name != '.nojekyll'
            or any(x.lower() in {'private', '_private', 'server', 'private-examples', 'node_modules', '.git'} for x in path.parts)
            or bool(re.match(r'(google|yandex_).*\.html$', path.name)))

def archive_files(root: Path) -> dict[str, bytes]:
    parts = sorted((root / 'preview-parts').glob('part-*.txt'))
    if [p.name for p in parts] != [f'part-{i:03d}.txt' for i in range(43)]:
        raise ValueError('Expected exactly part-000.txt through part-042.txt')
    encoded = ''.join(p.read_text(encoding='ascii') for p in parts)
    archive = base64.b64decode(re.sub(r'\s+', '', encoded), validate=True)
    if hashlib.sha256(archive).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('Original preview archive SHA-256 mismatch')
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

def normalize_paths(text: str, prefix: str) -> str:
    # The immutable archive was exported for /site/. Editable sources use /.
    text = re.sub(r'(["\'`])/site/', lambda m: m[1] + '/', text)
    text = re.sub(r'url\(\s*/site/', 'url(/', text)
    def srcset(match):
        value = re.sub(r'(^|,\s*)/site/', lambda m: m[1] + '/', match[2])
        if prefix:
            value = re.sub(r'(^|,\s*)/(?!/)', lambda m: m[1] + prefix + '/', value)
        return 'srcset=' + match[1] + value + match[1]
    # Each srcset candidate is a URL, including candidates after a comma.
    text = re.sub(r'\bsrcset=(["\'])(.*?)\1', srcset, text)
    if prefix:
        text = re.sub(r'(["\'`])/(?!/)([^"\'`<>\s]*)(?=\1)', lambda m: m[0] if m[2].startswith(prefix.lstrip('/') + '/') else m[1] + prefix + '/' + m[2], text)
        text = re.sub(r'url\(\s*/(?!/)', 'url(' + prefix + '/', text)
    return text

def clean_preview_html(text: str) -> str:
    if re.search(r'<meta\b[^>]*name=["\']saglam-test-site["\']', text, re.I):
        text = re.sub(r'<meta\b[^>]*name=["\']robots["\'][^>]*>', '', text, flags=re.I)
    text = re.sub(r'<meta\b[^>]*name=["\']saglam-test-site["\'][^>]*>', '', text, flags=re.I)
    text = re.sub(r'<div\b[^>]*id=["\']st-preview-banner["\'][^>]*>[\s\S]*?</div>', '', text, flags=re.I)
    text = re.sub(r'<(?:link|script)\b[^>]*(?:preview-readability|preview-enhancements)[^>]*>(?:</script>)?', '', text, flags=re.I)
    return text

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

def build(root: Path, output: Path, mode: str, prefix: str) -> dict:
    output = output.resolve()
    protected = [root / name for name in ('overrides', 'server', 'scripts', 'tests', 'docs', 'components', 'preview-parts', '.git')]
    if output == root or output in root.parents or any(output == p or p in output.parents or output in p.parents for p in protected):
        raise ValueError('Output must be a separate generated directory')
    files = archive_files(root)
    if mode == 'production':
        overlay(files, root / 'server')
    overlay(files, root / 'overrides')
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
                def favicon(match):
                    tag = match[0]
                    if not re.search(r'href=["\'](?:/site/|/|\./)?logo\.png["\']', tag):
                        return tag
                    tag = re.sub(r'href=["\'][^"\']*["\']', 'href="/logo.svg"', tag)
                    tag = re.sub(r'\s+type=["\'][^"\']*["\']', '', tag)
                    return tag[:-1] + ' type="image/svg+xml">'
                text = re.sub(r'<link\b(?=[^>]*rel=["\'](?:shortcut )?icon["\'])[^>]*>', favicon, text, flags=re.I)
                for element, css_class in [('header','at-header'), ('footer','at-footer')]:
                    component = root / 'components' / (element + '.html')
                    if component.exists():
                        if element == 'footer':
                            text = re.sub(r'<nav\b[^>]*class=["\'][^"\']*\bat-mobile-contact\b[^"\']*["\'][^>]*>[\s\S]*?</nav>', '', text, flags=re.I)
                        pattern = r'<' + element + r'\b[^>]*class=["\'][^"\']*\b' + css_class + r'\b[^"\']*["\'][^>]*>[\s\S]*?</' + element + '>'
                        text = re.sub(pattern, lambda _: component.read_text(), text, count=1, flags=re.I)
            text = normalize_paths(text, prefix)
            if visitor(Path(name)):
                text = clean_preview_html(text)
                text = re.sub(r'(<body\b)([^>]*>)', lambda m: m[1] + f' data-st-mode="{mode}"' + m[2], text, count=1, flags=re.I)
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
                text = insert_head(text, '<meta charset="UTF-8">')
                html_count += 1
            content = text.encode('utf-8')
        built[name] = content
    if mode == 'preview':
        built['assets/preview-guard.js'] = (root / 'scripts/preview-guard.js').read_bytes()
        # Allow crawling so robots noindex can actually be observed.
        built['robots.txt'] = b'User-agent: *\nAllow: /\n'
        built.pop('sitemap.xml', None)
    built['.nojekyll'] = b''
    digest = hashlib.sha256()
    for name, content in sorted(built.items()):
        digest.update(name.encode() + b'\0' + hashlib.sha256(content).digest())
    report = {'schema_version': 1, 'mode': mode, 'base_path': prefix or '/', 'archive_sha256': ARCHIVE_SHA256,
              'visitor_pages': html_count, 'model_pages_enhanced': enhancement_count, 'files': len(built), 'content_sha256': digest.hexdigest(),
              'production_deployed': False}
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
