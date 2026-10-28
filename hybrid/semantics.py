"""Generate structured facts and discovery files from the published HTML inventory.

Schema is derived from visible page content.  The llms catalogue is an optional
inventory; neither it nor FAQ markup is a ranking or indexing guarantee.
"""
from __future__ import annotations

from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit
import json
import re
import xml.etree.ElementTree as ET

ORIGIN = 'https://saglamkombiklima.com.tr/'
BUSINESS_ID = ORIGIN + '#business'
BUSINESS_ADDRESS = {
    '@type': 'PostalAddress', 'streetAddress': 'İnönü Mahallesi',
    'addressLocality': 'Küçükçekmece', 'addressRegion': 'İstanbul',
    'addressCountry': 'TR',
}
NON_CONTENT = {'404.html', 'owner-admin.html', 'servis-takip.html', 'servis-sec.html', 'icerik-inceleme.html'}
POLICY_PAGES = {
    'aydinlatma.html', 'hakkimizda.html', 'isletme-bilgileri.html',
    'kaynak-ve-yayin-ilkeleri.html', 'iletisim.html',
}
NON_SERVICE_HUBS = {'bolgeler.html', 'markalar.html', 'model-ariza-kodlari.html'}
SCRIPT = re.compile(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script\s*>', re.I | re.S)
VOID_TAGS = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}


class Element:
    def __init__(self, tag, attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def text(self):
        if (self.tag in {'script', 'style'} or self.attrs.get('aria-hidden') == 'true'
                or 'hidden' in self.attrs):
            return ''
        return ' '.join(' '.join(c.text() if isinstance(c, Element) else c
                                for c in self.children).split())

    def all(self, tag=None):
        result = [self] if tag is None or self.tag == tag else []
        for c in self.children:
            if isinstance(c, Element):
                result.extend(c.all(tag))
        return result


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = Element('document')
        self.stack = [self.root]
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Element(tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def meta(self, name):
        return next((e.attrs.get('content', '') for e in self.root.all('meta')
                     if e.attrs.get('name', '').lower() == name), '')

    def canonical(self):
        return next((e.attrs.get('href', '') for e in self.root.all('link')
                     if 'canonical' in e.attrs.get('rel', '').split()), '')

    def title(self):
        headings = self.root.all('h1') or self.root.all('title')
        return headings[0].text() if headings else 'Sağlam Teknik'

    def faq(self):
        """Read question/answer pairs, excluding model selectors and nested UI."""
        pairs = []
        seen = set()
        for detail in self.root.all('details'):
            summaries = [c for c in detail.children if isinstance(c, Element) and c.tag == 'summary']
            if not summaries:
                continue
            question = summaries[0].text().strip()
            if '?' not in question:
                continue
            paragraphs = []
            for c in detail.children:
                if isinstance(c, Element) and c.tag not in {'summary', 'details', 'nav', 'ul', 'ol'}:
                    paragraphs.extend(p.text() for p in c.all('p') if p.text())
            answer = ' '.join(paragraphs)
            if question and answer and question not in seen:
                seen.add(question)
                pairs.append((question, answer))
        return pairs


def _ordinary(name):
    return (name.endswith('.html') and '/' not in name and name not in NON_CONTENT
            and not name.startswith(('google', 'yandex')))


def _eligible(name, page):
    if not _ordinary(name) or 'noindex' in page.meta('robots').lower():
        return False
    canonical = urlsplit(page.canonical())
    expected = '/' if name == 'index.html' else '/' + name
    return (canonical.scheme == 'https' and canonical.netloc == 'saglamkombiklima.com.tr'
            and canonical.path == expected and not canonical.query and not canonical.fragment)


def _service_page(name, eligible):
    return eligible and name not in POLICY_PAGES | NON_SERVICE_HUBS


def _normalize_references(value):
    if isinstance(value, str):
        return value.replace(ORIGIN + '#isletme', BUSINESS_ID)
    if isinstance(value, list):
        return [_normalize_references(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalize_references(v) for k, v in value.items()}
    return value


def _relink(value, mapping, removed):
    """Keep references coherent when replacing existing Service/FAQ nodes."""
    if isinstance(value, str):
        return mapping.get(value, value)
    if isinstance(value, list):
        return [updated for item in value if (updated := _relink(item, mapping, removed)) is not None]
    if isinstance(value, dict):
        if set(value) == {'@id'} and value['@id'] in removed:
            return None
        return {key: updated for key, item in value.items()
                if (updated := _relink(item, mapping, removed)) is not None}
    return value


def _types(node):
    types = node.get('@type', [])
    return {types} if isinstance(types, str) else set(types)


def _business(districts):
    return {
        '@type': ['HVACBusiness', 'LocalBusiness'], '@id': BUSINESS_ID,
        'name': 'Sağlam Teknik', 'url': ORIGIN, 'telephone': '+905346225515',
        'description': 'İstanbul Avrupa Yakası için markalardan bağımsız özel kombi, klima ve petek teknik servisi.',
        'address': dict(BUSINESS_ADDRESS),
        'logo': ORIGIN + 'assets/brand/logo-ribbon.webp',
        'areaServed': [{'@type': 'AdministrativeArea', 'name': n + ', İstanbul'} for n in districts],
    }


def _slug(value):
    value = value.translate(str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosuCGIOSU')).lower()
    return re.sub(r'[^a-z0-9]+', '-', value).strip('-')


def _group(name, district_routes):
    if name == 'index.html' or name in {'hizmetler.html', 'kombi-servisi.html', 'klima-servisi.html', 'petek-temizligi.html'}:
        return 'Ana hizmetler'
    if name in district_routes:
        return 'İlçe servisleri'
    if re.fullmatch(r'.+-(?:kombi|klima)-servisi\.html', name):
        return 'Marka servisleri'
    if name.endswith('-servisi.html'):
        return 'Semt servisleri'
    if name.endswith('-ariza-kodlari.html'):
        return 'Model ve arıza kodu rehberleri'
    if name in POLICY_PAGES | NON_SERVICE_HUBS:
        return 'İşletme, bölge ve yayın bilgileri'
    return 'Belirti ve bakım rehberleri'


def _visible_faq(name, title):
    if name.endswith('-ariza-kodlari.html'):
        question = 'Bu sayfadaki hata kodları başka modellere uygulanabilir mi?'
        answer = ('Kod açıklamaları yalnız sayfada adı geçen model ve üretici belgesi kapsamı içindir. '
                  'Tam model veya belge eşleşmiyorsa kodun anlamı doğrulanmış sayılmaz.')
    else:
        question = title.rstrip('.') + ' için servis talebine ne eklemeliyim?'
        answer = ('İlçe ve mahalleyi, cihazın marka ve varsa tam modelini, gördüğünüz kodu ve '
                  'belirtinin ne zaman başladığını paylaşın. Modeli bilmiyorsanız bunu belirterek '
                  'devam edebilirsiniz; işlem kapsamı ve ücret görüşmede netleştirilir.')
    return ('<section class="hybrid-faq at-shell" aria-label="Servis öncesi sorular">'
            '<h2>Servis öncesi bilgi</h2><details class="st-hub-faq"><summary>' + escape(question)
            + '</summary><p>' + escape(answer) + '</p></details></section>')


def apply_semantics(files: dict[str, bytes]) -> dict:
    service_data = json.loads(re.search(r'window\.ST_SERVICE_DATA\s*=\s*(\{.*?\});',
                              files['assets/servis-verileri.js'].decode(), re.S)[1])
    districts = service_data['districts']
    district_routes = {_slug(district) + '-' + device + '-servisi.html': district
                       for district in districts for device in ['kombi', 'klima']}
    branded_routes = {_slug(brand) + '-' + device + '-servisi.html': brand
                      for device, data in service_data.get('devices', {}).items()
                      for brand in data.get('brands', [])}
    if 'assets/verified-faults.json' in files:
        documented = json.loads(files['assets/verified-faults.json'])
        for model in documented.get('models', []):
            if model.get('path') and model.get('brand'):
                branded_routes[model['path'].lstrip('/')] = model['brand']
    locality_routes = {_slug(row['name']) + '-servisi.html': row
                       for row in service_data.get('localities', [])}
    report = {'business_pages': 0, 'service_pages': 0, 'faq_pages': 0, 'faq_questions': 0,
              'visible_faq_sections_added': [], 'removed_irrelevant_policy_faqs': [],
              'address_source': 'User supplied: İnönü Mahallesi, Küçükçekmece, İstanbul, TR; no building/street number supplied.',
              'inventory': {}, 'notes': [
                  'FAQ markup is descriptive; Google FAQ rich results ended in May 2026.',
                  'llms.txt is an optional discovery catalogue, not a Google ranking control.',
                  'Only existing indexable self-canonical pages are listed; no pages are added to satisfy a requested count.',
              ]}

    for name in sorted(files):
        if not _ordinary(name):
            continue
        source = files[name].decode('utf-8')
        page = Page(source)
        eligible = _eligible(name, page)
        service = _service_page(name, eligible)
        # Older generated policy sections asked about buying unrelated repair service.
        if name in POLICY_PAGES:
            source, removed = re.subn(
                r'<details\b[^>]*class=["\'][^"\']*st-hub-faq[^"\']*["\'][^>]*>.*?</details>',
                '', source, flags=re.S)
            if removed:
                report['removed_irrelevant_policy_faqs'].append(name)
            page = Page(source)
        if service and not page.faq():
            faq = _visible_faq(name, page.title())
            source = source.replace('</main>', faq + '</main>', 1)
            page = Page(source)
            report['visible_faq_sections_added'].append(name)

        nodes = []
        for script in SCRIPT.finditer(source):
            payload = json.loads(script[1])
            if isinstance(payload, dict) and '@graph' in payload:
                nodes.extend(payload['@graph'])
            elif isinstance(payload, list):
                nodes.extend(payload)
            elif isinstance(payload, dict):
                nodes.append(payload)
        canonical = page.canonical() or ORIGIN + name
        pairs = page.faq() if name not in POLICY_PAGES and eligible else []
        mapping = {}
        removed_ids = set()
        for node in nodes:
            identifier = node.get('@id')
            if not identifier:
                continue
            if 'Service' in _types(node):
                if service:
                    mapping[identifier] = canonical + '#service'
                else:
                    removed_ids.add(identifier)
            if 'FAQPage' in _types(node):
                if pairs:
                    mapping[identifier] = canonical + '#faq'
                else:
                    removed_ids.add(identifier)
        preserve = []
        known_ids = set()
        for node in nodes:
            if (_types(node) & {'LocalBusiness', 'HVACBusiness', 'Service', 'FAQPage'}
                    or node.get('@id') in {BUSINESS_ID, ORIGIN + '#isletme'}):
                continue
            node = _relink(_normalize_references(node), mapping, removed_ids)
            identifier = node.get('@id')
            if identifier and identifier in known_ids:
                continue
            if identifier:
                known_ids.add(identifier)
            preserve.append(node)

        graph = [_business(districts), *preserve]
        report['business_pages'] += 1
        if service:
            # Retain actual subject scope from the existing Service node when possible.
            previous = next((n for n in nodes if 'Service' in _types(n)), {})
            description = page.meta('description')
            node = {'@type': 'Service', '@id': canonical + '#service',
                    'name': page.title(), 'serviceType': page.title(),
                    'url': canonical, 'provider': {'@id': BUSINESS_ID},
                    'areaServed': previous.get('areaServed') or _business(districts)['areaServed'],
                    'mainEntityOfPage': {'@id': canonical + '#sayfa'}}
            if description:
                node['description'] = description
            if previous.get('brand'):
                node['brand'] = previous['brand']
            if name in district_routes:
                node['areaServed'] = {'@type': 'AdministrativeArea',
                                      'name': district_routes[name] + ', İstanbul'}
            elif name in locality_routes:
                row = locality_routes[name]
                node['areaServed'] = {'@type': 'Place', 'name': row['name'] + ', İstanbul'}
                if row.get('district'):
                    node['areaServed']['containedInPlace'] = {
                        '@type': 'AdministrativeArea', 'name': row['district'] + ', İstanbul'}
            if name in branded_routes:
                node['brand'] = {'@type': 'Brand', 'name': branded_routes[name]}
            graph.append(node)
            report['service_pages'] += 1
        if pairs:
            graph.append({'@type': 'FAQPage', '@id': canonical + '#faq',
                          'mainEntity': [{'@type': 'Question', 'name': question,
                                          'acceptedAnswer': {'@type': 'Answer', 'text': answer}}
                                         for question, answer in pairs]})
            report['faq_pages'] += 1
            report['faq_questions'] += len(pairs)
        source = SCRIPT.sub('', source)
        graph_text = json.dumps({'@context': 'https://schema.org', '@graph': graph},
                                ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
        schema = '<script type="application/ld+json" data-hybrid-schema>' + graph_text + '</script>'
        source = source.replace('</head>', schema + '</head>', 1)
        if name in {'iletisim.html', 'isletme-bilgileri.html'} and 'data-hybrid-address' not in source:
            address = ('<address data-hybrid-address class="at-shell">Sağlam Teknik · '
                       'İnönü Mahallesi, Küçükçekmece, İstanbul, TR</address>')
            source = source.replace('</main>', address + '</main>', 1)
        files[name] = source.encode('utf-8')

    inventory = []
    for name, data in sorted(files.items()):
        if not _ordinary(name):
            continue
        page = Page(data.decode())
        if _eligible(name, page):
            inventory.append({'path': name, 'url': page.canonical(), 'title': page.title(),
                              'description': page.meta('description'), 'group': _group(name, district_routes)})

    # Preserve the user's detailed archival catalogue; do not overwrite it with the new list.
    if 'llms-full.txt' not in files and 'llms.txt' in files:
        files['llms-full.txt'] = files['llms.txt']
    lines = ['# Sağlam Teknik — Kombi, Klima ve Petek Servisi', '',
             '> İstanbul Avrupa Yakası’ndaki 25 ilçede kombi bakımı ve tamiri, klima bakımı ve tamiri, '
             'petek temizliği için markalardan bağımsız özel teknik servis.', '',
             '## İşletme özeti',
             '- İşletme: Sağlam Teknik.',
             '- Konum: İnönü Mahallesi, Küçükçekmece, İstanbul, TR.',
             '- Telefon: 0534 622 55 15 (+90 534 622 55 15).',
             '- WhatsApp: https://wa.me/905346225515',
             '- Yetkili servis değildir; üretici veya yetkili servis ağı adına hizmet verdiği söylenmemelidir.',
             '- İşlem kapsamı, servis uygunluğu ve ücret müşteriyle görüşülerek netleştirilir.',
             '- Arıza kodunun anlamı yalnız tam model ve üretici belgesi eşleştiğinde doğrulanmış sayılır.',
             '- Bir markanın listelenmesi tüm modellerine ait kodların doğrulandığı anlamına gelmez.',
             '- Yabancı pazar/kontrol kartı belgeleri Türkiye’deki benzer modele kendiliğinden uygulanamaz.',
             '- İlçe, mahalle, cihaz, marka ve belirti seçimi tek başına kesin arıza teşhisi değildir.',
             '- Gaz kokusu, duman veya patlama benzeri ateşleme servis randevusundan önce güvenlik değerlendirmesi gerektirir.',
             '- Servis ön bilgisi yerinde teknik incelemenin yerine geçmez.', '',
             '## Yayın envanteri',
             f'Bu katalog, derleme sırasında doğrulanan {len(inventory)} indexlenebilir ve kendi adresini '
             'canonical gösteren HTML sayfasını listeler. Mahalle/filtre durumları ayrı sayfa olarak sayılmaz.',
             'Ayrıntılı önceki kaynak dökümü: ' + ORIGIN + 'llms-full.txt', '']
    groups = ['Ana hizmetler', 'İlçe servisleri', 'Marka servisleri', 'Semt servisleri',
              'Belirti ve bakım rehberleri', 'Model ve arıza kodu rehberleri',
              'İşletme, bölge ve yayın bilgileri']
    for group in groups:
        rows = [i for i in inventory if i['group'] == group]
        if not rows:
            continue
        lines.extend(['## ' + group, ''])
        for row in rows:
            title = row['title'].replace('[', '(').replace(']', ')')
            description = ' '.join(row['description'].split())
            lines.append(f"- [{title}]({row['url']}): {description}")
        lines.append('')
    files['llms.txt'] = ('\n'.join(lines).rstrip() + '\n').encode('utf-8')
    sitemap = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for row in inventory:
        ET.SubElement(ET.SubElement(sitemap, 'url'), 'loc').text = row['url']
    files['sitemap.xml'] = ET.tostring(sitemap, encoding='utf-8', xml_declaration=True)
    report['inventory'] = {'requested_llms_count': 192, 'actual_canonical_pages': len(inventory),
                           'fixed_count_enforced': False,
                           'paths': [r['path'] for r in inventory],
                           'reason': 'Inventory follows actual eligible pages, not a marketing count.'}
    files['assets/hybrid-inventory.json'] = (json.dumps({'schema_version': 1, 'pages': inventory},
                                                       ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    # Production rules retain all private endpoint exclusions; no AI-specific bypass of private paths.
    robots = files.get('robots.txt', b'User-agent: *\nAllow: /\n').decode('utf-8')
    robots = re.sub(r'^Sitemap:.*\n?', '', robots, flags=re.M).rstrip()
    if not re.search(r'^User-agent:\s*\*\s*$', robots, re.M):
        robots = 'User-agent: *\nAllow: /\n' + robots
    files['robots.txt'] = (robots + '\nSitemap: ' + ORIGIN + 'sitemap.xml\n').encode()
    return report
