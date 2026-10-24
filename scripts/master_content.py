"""Persist the supplied master copy without replacing researched local bodies.

The JSON fixture stores the owner's exact matrix cells and metadata. It is not
an official model-code registry and is never imported into diagnostic matching.
Call enhance_files(files) after existing content/link hooks and before SEO graph
generation. Only root HTML bytes are changed; no new public route is created.
"""
from __future__ import annotations

import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

DATA_PATH = Path(__file__).resolve().parents[1] / 'components/master-content.json'
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
        'meta', 'param', 'source', 'track', 'wbr'}
MATRIX_NOTE = (
    'İşletmenin paylaştığı marka/model ve kod örnekleridir. “Sık” başlıkları '
    'ilçe bazında ölçülmüş arıza sıklığı göstermez. Kod anlamı, eşdeğer yazımlar '
    've basınç değeri tam modelin üretici kılavuzuyla doğrulanır; farklı '
    'modellerde E1/E01 otomatik eşdeğer değildir.'
)


class Element:
    def __init__(self, tag, attrs, start, open_end, parent):
        self.tag = tag
        self.attrs = dict(attrs)
        self.start = start
        self.open_end = open_end
        self.parent = parent
        self.close_start = None
        self.end = None
        self.parts = []

    def has_class(self, value):
        return value in (self.attrs.get('class') or '').split()

    def text(self):
        return re.sub(r'\s+', ' ', ''.join(self.parts)).strip()


class Document(HTMLParser):
    """Track exact source spans so nested div/table contents remain balanced."""
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.lines = [0] + [m.end() for m in re.finditer('\n', source)]
        self.elements = []
        self.stack = []
        self.feed(source)
        self.close()

    def position(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def start(self, tag, pairs, closed=False):
        begin = self.position()
        node = Element(tag, pairs, begin, begin + len(self.get_starttag_text()),
                       self.stack[-1] if self.stack else None)
        self.elements.append(node)
        if closed or tag in VOID:
            node.close_start = node.open_end
            node.end = node.open_end
        else:
            self.stack.append(node)

    def handle_starttag(self, tag, pairs):
        self.start(tag, pairs)

    def handle_startendtag(self, tag, pairs):
        self.start(tag, pairs, True)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            node = self.stack[index]
            if node.tag == tag:
                node.close_start = self.position()
                closing = self.source.find('>', node.close_start)
                if closing < 0:
                    raise ValueError('Unclosed HTML end tag')
                node.end = closing + 1
                del self.stack[index:]
                return

    def handle_data(self, value):
        for node in self.stack:
            node.parts.append(value)

    def find(self, predicate):
        return next((node for node in self.elements if predicate(node)), None)


def _apply(source, edits):
    previous = len(source) + 1
    for begin, end, replacement in sorted(edits, reverse=True):
        if begin < 0 or end < begin or end > previous:
            raise ValueError('Overlapping or invalid HTML edit')
        source = source[:begin] + replacement + source[end:]
        previous = begin
    return source


def _inside(node, tag):
    parent = node.parent
    while parent:
        if parent.tag == tag:
            return True
        parent = parent.parent
    return False


def _attribute(raw, name, value):
    escaped = html.escape(value, quote=True)
    pattern = re.compile(r'((?<![\w:-])' + re.escape(name) + r'\s*=\s*)(["\'])(.*?)\2', re.I | re.S)
    if pattern.search(raw):
        return pattern.sub(lambda match: match[1] + '"' + escaped + '"', raw, count=1)
    tail = '/>' if raw.rstrip().endswith('/>') else '>'
    return raw[:raw.rfind(tail)] + ' ' + name + '="' + escaped + '"' + tail


def _clean_titles(source, replacements):
    doc = Document(source)
    edits = []

    def cleaned(value):
        for old, new in replacements:
            value = value.replace(old, new)
        return value

    for node in doc.elements:
        if node.tag in {'title', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            if node.close_start is None:
                continue
            before = source[node.open_end:node.close_start]
            after = cleaned(before)
            if after != before:
                edits.append((node.open_end, node.close_start, after))
        elif node.tag == 'meta' and node.attrs.get('content') is not None:
            before = node.attrs['content']
            after = cleaned(before)
            if after != before:
                edits.append((node.start, node.open_end,
                              _attribute(source[node.start:node.open_end], 'content', after)))
    return _apply(source, edits)


def _metadata(source, values):
    doc = Document(source)
    edits = []
    found = set()
    targets = {('name', 'description'): values['desc'],
               ('property', 'og:description'): values['desc'],
               ('property', 'og:title'): values['title']}
    for node in doc.elements:
        if node.tag == 'title' and node.close_start is not None:
            edits.append((node.open_end, node.close_start, html.escape(values['title'])))
            found.add('title')
        elif node.tag == 'meta':
            for key, value in targets.items():
                if (node.attrs.get(key[0]) or '').lower() == key[1]:
                    edits.append((node.start, node.open_end,
                                  _attribute(source[node.start:node.open_end], 'content', value)))
                    found.add(key)
    lead = doc.find(lambda node: node.tag == 'p' and node.has_class('at-lead') and _inside(node, 'main'))
    if not lead or lead.close_start is None:
        raise ValueError('Target page is missing its visible at-lead paragraph')
    edits.append((lead.open_end, lead.close_start, html.escape(values['lead'])))
    missing = ''
    if 'title' not in found:
        missing += '<title>' + html.escape(values['title']) + '</title>'
    for key, value in targets.items():
        if key not in found:
            missing += '<meta ' + key[0] + '="' + key[1] + '" content="' + html.escape(value, quote=True) + '">'
    if missing:
        head = doc.find(lambda node: node.tag == 'head')
        if not head or head.close_start is None:
            raise ValueError('Target page is missing its head element')
        edits.append((head.close_start, head.close_start, missing))
    return _apply(source, edits)


def _neighborhoods(doc):
    names = []
    count = 0
    for node in doc.elements:
        if node.tag != 'a' or not node.attrs.get('href'):
            continue
        url = urlsplit(node.attrs['href'])
        values = {**parse_qs(url.query), **parse_qs(url.fragment)}
        if 'mahalle' in values:
            count += 1
            name = node.text()
            if name and name not in names:
                names.append(name)
    return names, count


def _interpolate(value, district, neighborhoods):
    return value.replace('{$ilce}', district).replace('{$mahalleMetni}', neighborhoods)


def _matrix(template, device, district, neighborhoods):
    fragment = _interpolate(template, html.escape(district), html.escape(neighborhoods))
    opening = '<div class="at-summary">'
    if not fragment.startswith(opening):
        raise ValueError('Master matrix template is missing its summary wrapper')
    fragment = fragment.replace(opening, '<div class="at-summary" data-st-master-matrix="' + device + '">', 1)
    caption = ('\n      <caption style="caption-side:top;text-align:left;font-size:12px;line-height:1.6;padding:0 0 12px;">'
               + html.escape(MATRIX_NOTE) + ' <a href="model-ariza-kodlari.html">Tam modelin kod rehberini inceleyin.</a></caption>')
    fragment, count = re.subn(r'<table\b[^>]*>', lambda match: match[0] + caption, fragment, count=1)
    if count != 1:
        raise ValueError('Master matrix template is missing its table')
    return fragment


def _summary(source, fragment):
    doc = Document(source)
    local = doc.find(lambda node: node.attrs.get('id') == 'local-guide-body')
    if not local:
        raise ValueError('District page is missing its researched local body')
    summary = doc.find(lambda node: node.tag in {'p', 'div'} and node.has_class('at-summary')
                       and node.start < local.start and _inside(node, 'main'))
    if summary:
        if summary.end is None:
            raise ValueError('District summary has no balanced closing tag')
        return _apply(source, [(summary.start, summary.end, fragment)])
    return _apply(source, [(local.start, local.start, fragment)])


def _region_chips(source, rows):
    doc = Document(source)
    desired = {row['path'] for row in rows}
    target = None
    for node in doc.elements:
        if node.tag != 'div' or not node.has_class('region-list') or node.end is None:
            continue
        if node.attrs.get('data-st-master-regions') == '1':
            target = node
            break
        hrefs = {urlsplit(child.attrs.get('href', '')).path.removeprefix('/site/').lstrip('/')
                 for child in doc.elements if child.tag == 'a' and node.open_end <= child.start < node.end}
        if {'kucukcekmece-kombi-servisi.html', 'bagcilar-kombi-servisi.html'} <= hrefs:
            target = node
            break
    chips = ''.join('<a class="region-chip" href="' + html.escape(row['path'], quote=True)
                    + '">' + html.escape(row['label']) + '</a>' for row in rows)
    block = '<div class="region-list" data-st-master-regions="1">' + chips + '</div>'
    if target:
        # Keep any extra real destination outside the supplied twelve as well.
        for child in doc.elements:
            if child.tag != 'a' or not (target.open_end <= child.start < target.end) or child.end is None:
                continue
            path = urlsplit(child.attrs.get('href', '')).path.removeprefix('/site/').lstrip('/')
            if path and path not in desired:
                block = block[:-6] + source[child.start:child.end] + '</div>'
        return _apply(source, [(target.start, target.end, block)])
    main = doc.find(lambda node: node.tag == 'main')
    if not main or main.close_start is None:
        raise ValueError('Brand page is missing its main element')
    return _apply(source, [(main.close_start, main.close_start,
                            '<section data-st-master-region-section><h2>Servis planlayabileceğiniz bölgeler</h2>' + block + '</section>')])


def _slug(value):
    return re.sub(r'[^a-z0-9]+', '-', value.translate(str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosuCGIOSU')).lower()).strip('-')


def enhance_files(files: dict[str, bytes]) -> dict:
    data = json.loads(DATA_PATH.read_text(encoding='utf-8'))
    catalog = json.loads(files.get('assets/servis-katalog.json', b'{}'))
    district_routes = {_slug(district) + '-' + device + '-servisi.html': (district, device)
                       for district in catalog.get('districts', []) for device in ('kombi', 'klima')}
    counts = {'kombi': 0, 'klima': 0}
    brands = []
    cleanups = []
    changed = []
    neighborhoods_preserved = 0
    e1 = 0
    for name in sorted(files):
        if not name.endswith('.html') or '/' in name:
            continue
        before = files[name].decode('utf-8')
        text = _clean_titles(before, data['title_replacements'])
        if text != before:
            cleanups.append(name)
        if name in district_routes:
            doc = Document(text)
            if not doc.find(lambda node: node.attrs.get('id') == 'local-guide-body'):
                raise ValueError('Expected district route has no local guide: ' + name)
            district, device = district_routes[name]
            neighborhoods, anchor_count = _neighborhoods(doc)
            first_six = ', '.join(neighborhoods[:6]) or district + ' merkez'
            values = {key: _interpolate(value, district, first_six)
                      for key, value in data['district_meta'][device].items()}
            text = _metadata(text, values)
            text = _summary(text, _matrix(data['matrix_html'][device], device, district, first_six))
            if _neighborhoods(Document(text))[1] != anchor_count:
                raise ValueError('Neighborhood anchors changed: ' + name)
            neighborhoods_preserved += anchor_count
            counts[device] += 1
        elif name in data['brand_meta']:
            text = _metadata(text, data['brand_meta'][name])
            text = _region_chips(text, data['region_chips'])
            brands.append(name)
        elif name == 'baymak-e1-hatasi.html':
            text = _metadata(text, data['baymak_e1'])
            e1 += 1
        if text != before:
            files[name] = text.encode('utf-8')
            changed.append(name)
    return {'schema_version': 1, 'source_sha256': data['source_sha256'],
            'district_pages': sum(counts.values()), 'kombi_district_pages': counts['kombi'],
            'klima_district_pages': counts['klima'],
            'matrix_rows': counts['kombi'] * 8 + counts['klima'] * 5,
            'brand_pages': len(brands), 'brand_routes': brands,
            'region_chip_groups': len(brands), 'baymak_e1_pages': e1,
            'title_cleanup_pages': cleanups,
            'preserved_neighborhood_links': neighborhoods_preserved,
            'changed_pages': changed}
