"""Publish document-relative resources without changing external/semantic URLs.

The archived export stays immutable. This deterministic final pass removes old
root copies, resolves CSS against its stylesheet, and keeps API requests relative
to the page that uses them (including the nested owner console).
"""
from __future__ import annotations
import json
import posixpath
import re
from urllib.parse import urlsplit

REMOVED_IMAGES = {'assets/atelier-hero.png', 'logo.png', 'images/door.png',
                  'images/floor.png', 'images/wall.png', 'images/person.png',
                  'images/natro-logo.png'}
TEXT = {'.html', '.css', '.js', '.json', '.svg'}

def aliases_for(files: dict[str, bytes]) -> dict[str, str]:
    aliases = {name: 'assets/' + name for name in files
               if '/' not in name and posixpath.splitext(name)[1] in {'.js', '.css', '.json'}
               and 'assets/' + name in files}
    aliases.update({'assets/atelier-hero.png': 'assets/atelier-hero.webp',
                    'logo.png': 'assets/brand/logo-ribbon.webp',
                    'oneri.png': 'assets/brand/armut-tavsiye.webp',
                    'assets/brand/logo-ribbon.png': 'assets/brand/logo-ribbon.webp'})
    return {a: b for a, b in aliases.items() if b in files}

def portable_url(value: str, name: str, files: dict[str, bytes], aliases: dict[str, str],
                 prefix: str = '', *, context: str = 'html') -> str:
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return value
    raw = parsed.path
    absolute = raw.startswith('/')
    candidate = raw
    if absolute:
        if prefix and (candidate == prefix or candidate.startswith(prefix + '/')):
            candidate = candidate[len(prefix):] or '/'
        if candidate == '/site' or candidate.startswith('/site/'):
            candidate = candidate[5:] or '/'
        candidate = candidate.lstrip('/')
    else:
        # Static JS URL strings are consumed by root visitor documents. The
        # private owner script is consumed exclusively by assets/owner-admin.
        base = posixpath.dirname(name) if context in {'css', 'html', 'svg'} or name == 'assets/owner-admin.js' else ''
        candidate = posixpath.normpath(posixpath.join(base, candidate))
    candidate = aliases.get(candidate, candidate)
    home = candidate in {'', '.'}
    if home:
        candidate = 'index.html'
    if candidate not in files and not candidate.endswith('.php'):
        return value
    # For JavaScript only rewrite actual root URLs or aliases, never predicates
    # such as '/' or '/klima-' used to inspect a pathname.
    if context == 'js' and (not absolute and raw not in aliases or home):
        return value
    base = posixpath.dirname(name) if context in {'css', 'html', 'svg'} or name == 'assets/owner-admin.js' else ''
    target = posixpath.relpath(candidate, base or '.')
    if home and target == 'index.html':
        target = './'
    # Empty separators can be followed by a runtime concatenation, e.g.
    # 'index.html?' + params and 'servis-sec.html#' + selectedLocation.
    has_query = '?' in value.split('#', 1)[0]
    return target + ('?' + parsed.query if has_query else '') + ('#' + parsed.fragment if '#' in value else '')

def rewrite_css(text: str, name: str, files: dict[str, bytes], aliases: dict[str, str], prefix: str) -> str:
    def replace(m):
        quote = m['quote'] or ''
        url = portable_url(m['url'], name, files, aliases, prefix, context='css')
        return 'url(' + quote + url + quote + ')'
    return re.sub(r'url\(\s*(?P<quote>["\']?)(?P<url>[^)"\']+)(?P=quote)\s*\)', replace, text)

def rewrite_js(text: str, name: str, files: dict[str, bytes], aliases: dict[str, str], prefix: str) -> str:
    def replace(m):
        url = portable_url(m['url'], name, files, aliases, prefix, context='js')
        return m['quote'] + url + m['quote']
    return re.sub(r'(?P<quote>["\'`])(?P<url>/(?!/)[^"\'`<>\s]*)(?P=quote)', replace, text)

def rewrite_html(text: str, name: str, files: dict[str, bytes], aliases: dict[str, str], prefix: str) -> str:
    def part(value):
        def attr(m):
            raw = m['value']
            if m['key'].lower() == 'srcset':
                raw = ', '.join(' '.join([portable_url(bits[0], name, files, aliases, prefix), *bits[1:]])
                                for item in raw.split(',') if (bits := item.strip().split()))
            else:
                raw = portable_url(raw, name, files, aliases, prefix)
            return m['key'] + '=' + m['quote'] + raw + m['quote']
        value = re.sub(r'\b(?P<key>href|src|action|poster|srcset|data-api)=(?P<quote>["\'])(?P<value>.*?)(?P=quote)', attr, value, flags=re.I)
        # Inline CSS resolves against the HTML document, not an assets folder.
        return rewrite_css(value, name, files, aliases, prefix)
    chunks = re.split(r'(<script\b[^>]*>[\s\S]*?</script\s*>)', text, flags=re.I)
    for i, chunk in enumerate(chunks):
        match = re.fullmatch(r'(<script\b[^>]*>)([\s\S]*?)(</script\s*>)', chunk, flags=re.I)
        if match:
            payload = match[2] if re.search(r'type=["\']application/(?:ld\+)?json["\']', match[1], re.I) else rewrite_js(match[2], name, files, aliases, prefix)
            chunks[i] = part(match[1]) + payload + match[3]
        else:
            chunks[i] = part(chunk)
    return ''.join(chunks)

def enhance_files(files: dict[str, bytes], prefix: str = '') -> dict:
    aliases = aliases_for(files)
    removed = []
    for name in sorted(set(aliases) | REMOVED_IMAGES | {'css/custom.css'}):
        # The obsolete custom stylesheet referenced the removed wall/floor PNGs
        # and is not used by any visitor document in the modern design.
        if name == 'css/custom.css' and any(name in c.decode('utf-8') for n, c in files.items() if n.endswith('.html')):
            continue
        if name in files:
            files.pop(name); removed.append(name)
    for name, raw in list(files.items()):
        suffix = posixpath.splitext(name)[1]
        if suffix not in TEXT:
            continue
        text = raw.decode('utf-8')
        if suffix in {'.html', '.svg'}:
            text = rewrite_html(text, name, files, aliases, prefix)
        elif suffix == '.css':
            text = rewrite_css(text, name, files, aliases, prefix)
        elif suffix == '.js':
            text = rewrite_js(text, name, files, aliases, prefix)
        elif suffix == '.json':
            data = json.loads(text)
            def walk(value):
                if isinstance(value, str):
                    return portable_url(value, name, files, aliases, prefix, context='json')
                if isinstance(value, list): return [walk(v) for v in value]
                if isinstance(value, dict): return {k: walk(v) for k, v in value.items()}
                return value
            text = json.dumps(walk(data), ensure_ascii=False, separators=(',', ':'))
        files[name] = text.encode('utf-8')
    return {'removed_files': removed, 'removed_count': len(removed), 'url_style': 'document-relative'}
