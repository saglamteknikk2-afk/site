"""Small, measurable delivery changes without changing the site's design.

This module does not report a Lighthouse score, a Google Ads Quality Score, or
live-server timing.  Its counters describe static file and loading attributes.
"""
from __future__ import annotations

import html
import posixpath
import re
import struct
import json
import hashlib
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree


IMG = re.compile(r'<img\b[^>]*>', re.I)
ATTR = re.compile(r'([\w:-]+)\s*=\s*(["\'])(.*?)\2', re.S)
FONT_FILES = ('d8c30647abfe.woff2', '94d65887a83f.woff2')
DIAGNOSTIC_DATA = ('verified-faults.js', 'organic-catalog.js', 'model-directory.js')
CONTRAST_CSS = ('/* Contrast corrections measured by the local mobile Lighthouse audit. */\n'
                '.p-assurance-item small,.p-about-copy>p,.p-principle>span,.p-principle p,'
                '#ustaStep>p,.usta-choice small{color:#53624f}\n')


def _subset_icons(files: dict[str, bytes]) -> dict:
    """Remove only pure unused glyph rules; retain base rules, fonts and animation."""
    name = 'assets/icons.css'
    if name not in files:
        return {'applied': False, 'reason': 'No local icon stylesheet'}
    source = files[name].decode('utf-8')
    used = set(); dynamic = []
    for filename, raw in files.items():
        if filename.endswith(('.html', '.js', '.php', '.json', '.css', '.svg')) and not filename.endswith('icons.css'):
            text = raw.decode('utf-8', errors='replace')
            used.update(re.findall(r'\bfa-[a-z0-9-]+\b', text))
            if re.search(r'fa-\$\{|["\']fa-["\']\s*\+', text):
                dynamic.append(filename)
    if dynamic:
        return {'applied': False, 'reason': 'Dynamic icon names cannot be proven statically', 'files': dynamic}
    removed = 0; kept_glyph_rules = 0

    def rule(match):
        nonlocal removed, kept_glyph_rules
        selectors, body = match[1], match[2]
        # Retain rules with arbitrary declarations, combinators, nested syntax,
        # font-face declarations and keyframe steps exactly as supplied.
        if (not re.fullmatch(r'\s*content\s*:\s*(["\']).*?\1\s*;?\s*', body, re.S)
            or not re.fullmatch(r'\s*\.fa-[a-z0-9-]+:{1,2}before(?:\s*,\s*\.fa-[a-z0-9-]+:{1,2}before)*\s*', selectors)):
            return match[0]
        classes = set(re.findall(r'\.((?:fa-)[a-z0-9-]+)', selectors))
        if classes & used:
            kept_glyph_rules += 1
            return match[0]
        removed += 1
        return ''

    result = re.sub(r'([^{}]+)\{([^{}]+)\}', rule, source)
    # License comment and original font declarations are preserved byte-for-byte.
    assert source.split('*/', 1)[0] == result.split('*/', 1)[0]
    assert re.findall(r'@font-face\{[^{}]*\}', source) == re.findall(r'@font-face\{[^{}]*\}', result)
    files[name] = result.encode()
    return {'applied': True, 'bytes_before': len(source.encode()), 'bytes_after': len(files[name]),
            'glyph_rules_removed': removed, 'glyph_rules_retained': kept_glyph_rules,
            'used_classes': sorted(used), 'dynamic_class_construction': False,
            'retained': ['license', 'font faces', 'base utilities', 'keyframes', 'referenced glyph aliases']}


def _attrs(tag: str) -> dict[str, str]:
    return {m[1].lower(): html.unescape(m[3]) for m in ATTR.finditer(tag)}


def _set(tag: str, name: str, value: str) -> str:
    pattern = re.compile(r'\s' + re.escape(name) + r'\s*=\s*(["\']).*?\1', re.I | re.S)
    attribute = ' ' + name + '="' + html.escape(value, quote=True) + '"'
    if pattern.search(tag):
        return pattern.sub(lambda _: attribute, tag, count=1)
    return re.sub(r'\s*/?>$', lambda m: attribute + m[0], tag, count=1)


def _target(value: str, source: str) -> str:
    parsed = urlsplit(html.unescape(value))
    if parsed.scheme or parsed.netloc or not parsed.path:
        return ''
    path = unquote(parsed.path)
    if path.startswith('/site/'):
        return path[6:]
    if path.startswith('/'):
        return path.lstrip('/')
    return posixpath.normpath(posixpath.join(posixpath.dirname(source), path))


def _dimensions(data: bytes, filename: str) -> tuple[int, int] | None:
    """Read existing image metadata; never rewrite the image or invent a ratio."""
    if filename.lower().endswith('.svg'):
        try:
            root = ElementTree.fromstring(data)
            w, h = root.get('width', ''), root.get('height', '')
            if re.fullmatch(r'\d+(?:\.\d+)?(?:px)?', w) and re.fullmatch(r'\d+(?:\.\d+)?(?:px)?', h):
                return round(float(w.removesuffix('px'))), round(float(h.removesuffix('px')))
            box = root.get('viewBox', '').replace(',', ' ').split()
            if len(box) == 4:
                return round(float(box[2])), round(float(box[3]))
        except (ElementTree.ParseError, ValueError):
            return None
    if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data) >= 24:
        return struct.unpack('>II', data[16:24])
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        if data[12:16] == b'VP8X' and len(data) >= 30:
            return 1 + int.from_bytes(data[24:27], 'little'), 1 + int.from_bytes(data[27:30], 'little')
        if data[12:16] == b'VP8 ' and len(data) >= 30 and data[23:26] == b'\x9d\x01\x2a':
            return int.from_bytes(data[26:28], 'little') & 0x3fff, int.from_bytes(data[28:30], 'little') & 0x3fff
        if data[12:16] == b'VP8L' and len(data) >= 25 and data[20] == 0x2f:
            bits = int.from_bytes(data[21:25], 'little')
            return (bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1
    return None


class _References(HTMLParser):
    def __init__(self, source: str, target_set: set[str]):
        super().__init__(convert_charrefs=True)
        self.source, self.targets = source, target_set

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ('src', 'href', 'poster', 'action'):
            if attrs.get(key):
                target = _target(attrs[key], self.source)
                if target:
                    self.targets.add(target)
        for item in attrs.get('srcset', '').split(','):
            if item.strip():
                target = _target(item.strip().split()[0], self.source)
                if target:
                    self.targets.add(target)


def _references(files: dict[str, bytes]) -> set[str]:
    """Conservative static references, including ordinary quoted JS/PHP paths."""
    targets: set[str] = set()
    for name, data in files.items():
        if not name.endswith(('.html', '.svg', '.css', '.js', '.php', '.json')):
            continue
        text = data.decode('utf-8', errors='replace')
        if name.endswith(('.html', '.svg')):
            _References(name, targets).feed(text)
        if name.endswith('.css'):
            for match in re.finditer(r'url\(\s*["\']?([^\s)"\']+)', text):
                if target := _target(match[1], name):
                    targets.add(target)
        if name.endswith(('.js', '.php', '.json')):
            for match in re.finditer(r'["\']((?:\./|/)?[a-zA-Z0-9_./-]+\.(?:css|svg)(?:\?[^"\']*)?)["\']', text):
                # Relative URLs in root consumer JS resolve against the visitor document.
                # Consider both interpretations; retaining an extra file is harmless.
                if target := _target(match[1], name):
                    targets.add(target)
                if target := _target(match[1], 'index.html'):
                    targets.add(target)
    return targets


def _image_stats(files: dict[str, bytes]) -> dict:
    stats = {'image_tags': 0, 'lazy_images': 0, 'eager_images': 0,
             'missing_dimensions': 0, 'critical_image_candidate_bytes': 0}
    for name, data in files.items():
        if not name.endswith('.html') or name.startswith(('google', 'yandex', 'inceleme/')):
            continue
        initial = set()
        for match in IMG.finditer(data.decode('utf-8')):
            attrs = _attrs(match[0]); stats['image_tags'] += 1
            lazy = attrs.get('loading') == 'lazy'
            stats['lazy_images' if lazy else 'eager_images'] += 1
            if not attrs.get('width') or not attrs.get('height'):
                stats['missing_dimensions'] += 1
            if not lazy and (target := _target(attrs.get('src', ''), name)) in files:
                initial.add(target)
        stats['critical_image_candidate_bytes'] += sum(len(files[n]) for n in initial)
    return stats


def apply_performance(files: dict[str, bytes]) -> dict:
    """Mutate a build's file mapping, retaining script dependency order and design."""
    before_bytes = sum(map(len, files.values()))
    before = _image_stats(files)
    originally_identical_roots = {name for name in files if '/' not in name
                                 and name.endswith(('.css', '.svg'))
                                 and 'assets/' + name in files
                                 and files[name] == files['assets/' + name]}
    deferred_data = {'homepage_scripts': [], 'bytes_removed_from_initial_script_chain': 0}
    icon_subset = _subset_icons(files)
    changed_pages = []
    count = {'loading_attributes_changed': 0, 'decoding_added': 0,
             'intrinsic_dimensions_added': 0, 'font_preloads_added': 0}
    for name in sorted(files):
        if not name.endswith('.html') or name.startswith(('google', 'yandex', 'inceleme/')):
            continue
        source = files[name].decode('utf-8')
        seen = 0

        def optimize(match):
            nonlocal seen
            tag = match[0]; attrs = _attrs(tag); seen += 1
            # First image is the shared header mark; the hero is explicitly marked
            # in the original export. No viewport-position guessing for later images.
            critical = (seen == 1 or attrs.get('fetchpriority') == 'high'
                        or 'p-hero-photo' in attrs.get('class', '').split())
            loading = 'eager' if critical else 'lazy'
            if attrs.get('loading') != loading:
                tag = _set(tag, 'loading', loading); count['loading_attributes_changed'] += 1
            if critical and attrs.get('fetchpriority') != 'high':
                tag = _set(tag, 'fetchpriority', 'high')
            if 'decoding' not in attrs:
                tag = _set(tag, 'decoding', 'async'); count['decoding_added'] += 1
            if not attrs.get('width') or not attrs.get('height'):
                target = _target(attrs.get('src', ''), name)
                dimensions = _dimensions(files[target], target) if target in files else None
                if dimensions and all(value > 0 for value in dimensions):
                    tag = _set(_set(tag, 'width', str(dimensions[0])), 'height', str(dimensions[1]))
                    count['intrinsic_dimensions_added'] += 1
            return tag

        source = IMG.sub(optimize, source)
        if icon_subset.get('applied'):
            digest = hashlib.sha256(files['assets/icons.css']).hexdigest()[:12]
            def cache_icon(match):
                tag = match[0]; attrs = _attrs(tag)
                if _target(attrs.get('href', ''), name) != 'assets/icons.css':
                    return tag
                href = attrs['href'].split('?', 1)[0].split('#', 1)[0] + '?v=' + digest
                return _set(tag, 'href', href)
            source = re.sub(r'<link\b[^>]*>', cache_icon, source, flags=re.I)
        if name == 'index.html' and 'id="aiUstaWizard"' in source and 'assets/diagnostics-loader.js' not in source:
            sources = []
            for match in re.finditer(r'<script\b[^>]*\bsrc=(["\'])([^"\']+)\1[^>]*>\s*</script>', source):
                target = _target(match[2], name)
                if target in {'assets/' + item for item in DIAGNOSTIC_DATA}:
                    sources.append((match[0], match[2], target))
            # These three are data-only IIFEs/assignments. Keep every consumer
            # script in its original dependency order and gate interactions.
            if len(sources) == len(DIAGNOSTIC_DATA):
                values = html.escape(json.dumps([row[1] for row in sources]), quote=True)
                loader = '<script src="assets/diagnostics-loader.js" data-diagnostic-sources="' + values + '" defer></script>'
                for index, (tag, value, target) in enumerate(sources):
                    source = source.replace(tag, loader if index == 0 else '', 1)
                    deferred_data['homepage_scripts'].append(target)
                    deferred_data['bytes_removed_from_initial_script_chain'] += len(files[target])
                files['assets/diagnostics-loader.js'] = (Path(__file__).resolve().parent/'assets/diagnostics-loader.js').read_bytes()
        if name == 'index.html' and 'assets/performance.css' not in source:
            source = source.replace('</head>', '<link rel="stylesheet" href="assets/performance.css"></head>', 1)
            files['assets/performance.css'] = CONTRAST_CSS.encode()
        # The existing stylesheet already uses font-display:swap. Preload only
        # its actual Latin + Turkish glyph subsets, and only on pages using it.
        if re.search(r'<link\b[^>]*href=["\'][^"\']*(?:assets/)?fonts\.css(?:[?"\'])', source):
            preloads = []
            for font in FONT_FILES:
                target = 'assets/fonts/' + font
                if target not in files:
                    continue
                value = posixpath.relpath(target, posixpath.dirname(name) or '.')
                if re.search(r'<link\b(?=[^>]*\brel=["\']preload["\'])(?=[^>]*\bhref=["\']' + re.escape(value) + r'["\'])', source):
                    continue
                preloads.append('<link rel="preload" href="' + value + '" as="font" type="font/woff2" crossorigin>')
                count['font_preloads_added'] += 1
            if preloads:
                source = source.replace('</head>', ''.join(preloads) + '</head>', 1)
        updated = source.encode('utf-8')
        if updated != files[name]:
            files[name] = updated; changed_pages.append(name)

    # Remove only byte-identical, unreferenced root CSS/SVG duplicates. Divergent
    # JS/JSON copies are retained because changing their authority is architectural.
    referenced = _references(files)
    removed = []
    for name in sorted(list(files)):
        twin = 'assets/' + name
        if '/' not in name and name.endswith(('.css', '.svg')) and twin in files:
            if name not in referenced and name in originally_identical_roots:
                removed.append({'path': name, 'bytes': len(files[name])})
                del files[name]
    after = _image_stats(files)
    return {'scope': 'Static loading attributes and file budgets; not live speed or Ads scoring',
            'pages_changed': len(changed_pages), 'attributes': count,
            'before': before, 'after': after, 'removed_identical_unused_files': removed,
            'total_file_bytes_before': before_bytes, 'total_file_bytes_after': sum(map(len, files.values())),
            'script_loading': 'Existing dependency order and synchronous environment guard retained',
            'font_display': 'Existing swap declarations retained; two local Latin/Turkish subsets preloaded',
            'diagnostic_data_loading': deferred_data,
            'icon_stylesheet': icon_subset,
            'contrast_corrections': 'Only measured home/wizard muted text selectors; original palette retained',
            'lighthouse_measured': False, 'ads_quality_score_measured': False}
