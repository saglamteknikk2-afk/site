"""Reconcile public SEO metadata from final HTML; never changes visible copy."""
from __future__ import annotations

from collections import Counter
import html
from html.parser import HTMLParser
import json
from pathlib import PurePosixPath
import re
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree as ET

ORIGIN = 'https://saglamkombiklima.com.tr'
BUSINESS_ID = ORIGIN + '/#isletme'
SITE_ID = ORIGIN + '/#websitesi'
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
BLOCK = {'p', 'div', 'section', 'article', 'li', 'ul', 'ol', 'br', 'h1', 'h2', 'h3', 'h4', 'blockquote'}
HIDDEN = {'script', 'style', 'template', 'noscript', 'nav', 'footer', 'header', 'form', 'button'}
SERVICE_PAGES = {
    'kombi-servisi.html', 'kombi-bakimi.html', 'kombi-tamiri.html',
    'klima-servisi.html', 'klima-bakimi.html', 'klima-tamiri.html',
    'klima-montaji.html', 'klima-sokumu.html', 'klima-gaz-kontrolu.html', 'petek-temizligi.html',
}
DIRECTORIES = {'bolgeler.html', 'markalar.html', 'hizmetler.html', 'ariza-rehberi.html', 'model-ariza-kodlari.html'}
SYSTEM_PAGES = {'404.html', 'servis-sec.html'}
LD_SCRIPT = re.compile(r'<script\b(?=[^>]*\btype\s*=\s*["\']application/ld\+json["\'])[^>]*>[\s\S]*?</script\s*>', re.I)


def normalized(value: str) -> str:
    return re.sub(r'\s+', ' ', value).strip()


def visitor(name: str) -> bool:
    leaf = PurePosixPath(name).name
    return name.endswith('.html') and leaf != 'owner-admin.html' and not re.match(r'(google|yandex_).*\.html$', leaf)


def page_url(name: str) -> str:
    return ORIGIN + ('/' if name == 'index.html' else '/' + name)


def own_url(value: str, source: str) -> str:
    """Normalize local site URLs, preserving independent manufacturer citations."""
    if value.startswith(('#', '/', './', '../')) or not urlsplit(value).scheme:
        value = urljoin(page_url(source), value)
    parsed = urlsplit(value)
    if parsed.hostname == 'saglamkombiklima.com.tr' or (parsed.hostname or '').endswith('.github.io'):
        path = parsed.path
        if path == '/site': path = '/'
        elif path.startswith('/site/'): path = path[len('/site'):]
        if path == '/index.html': path = '/'
        return ORIGIN + path + (('?' + parsed.query) if parsed.query else '') + (('#' + parsed.fragment) if parsed.fragment else '')
    return value


class Page(HTMLParser):
    """Read visible local Q&A and expandable questions; exclude forms/navigation."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.h1 = []; self.title = []; self.description = ''; self.noindex = False; self.preview = False
        self.schemas = []; self.schema_text = None; self.details = []; self.local_items = []; self.faq = []; self.links = set()

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        parent = self.stack[-1] if self.stack else {'hidden': False, 'main': False}
        hidden = parent['hidden'] or tag in HIDDEN or 'hidden' in attrs or attrs.get('aria-hidden', '').lower() == 'true' or bool(re.search(r'(?:display\s*:\s*none|visibility\s*:\s*hidden)', attrs.get('style', ''), re.I))
        frame = {'tag': tag, 'hidden': hidden, 'main': parent['main'] or tag == 'main', 'local_section': parent.get('local_section', False) or attrs.get('id') == 'yerel-sorular'}
        if tag not in VOID: self.stack.append(frame)
        if tag == 'meta':
            if attrs.get('name', '').lower() == 'robots': self.noindex |= 'noindex' in re.split(r'[\s,]+', attrs.get('content', '').lower())
            if attrs.get('name', '').lower() == 'description': self.description = attrs.get('content', '')
            if attrs.get('name', '').lower() == 'saglam-test-site': self.preview = True
        if tag == 'body' and attrs.get('data-st-mode') == 'preview': self.preview = True
        if tag == 'script' and attrs.get('type', '').lower() == 'application/ld+json': self.schema_text = []
        if tag == 'a' and attrs.get('href') and frame['main'] and not hidden: self.links.add(attrs['href'])
        if tag == 'details' and frame['main'] and not hidden:
            self.details.append({'depth': len(self.stack), 'question': [], 'answer': [], 'summary': False})
        if self.details and not hidden:
            current = self.details[-1]
            if tag == 'summary': current['summary'] = True
            elif tag in BLOCK: current['answer'].append(' ')
        if tag == 'div' and 'local-faq-item' in attrs.get('class', '').split() and frame['main'] and frame['local_section'] and not hidden:
            self.local_items.append({'depth': len(self.stack), 'question': [], 'answer': [], 'question_depth': None, 'answer_depth': None})
        if self.local_items and not hidden:
            current = self.local_items[-1]
            if tag == 'h3': current['question_depth'] = len(self.stack)
            elif tag == 'p': current['answer_depth'] = len(self.stack)

    def handle_startendtag(self, tag, pairs):
        self.handle_starttag(tag, pairs)
        if tag not in VOID: self.handle_endtag(tag)

    def handle_data(self, value):
        if self.schema_text is not None: self.schema_text.append(value)
        if any(f['tag'] == 'title' for f in self.stack): self.title.append(value)
        if not self.stack or self.stack[-1]['hidden']: return
        if any(f['tag'] == 'h1' for f in self.stack): self.h1.append(value)
        if self.details:
            current = self.details[-1]
            current['question' if current['summary'] else 'answer'].append(value)
        if self.local_items:
            current = self.local_items[-1]
            if current['question_depth'] is not None: current['question'].append(value)
            elif current['answer_depth'] is not None: current['answer'].append(value)

    def handle_endtag(self, tag):
        if tag == 'script' and self.schema_text is not None:
            try: self.schemas.append(json.loads(''.join(self.schema_text)))
            except ValueError: pass  # The generated graph replaces invalid legacy markup.
            self.schema_text = None
        if self.details:
            current = self.details[-1]
            if tag == 'summary': current['summary'] = False
            elif tag in BLOCK and self.stack and not self.stack[-1]['hidden']: current['answer'].append(' ')
            if tag == 'details' and len(self.stack) == current['depth']:
                self.details.pop()
                question = normalized(''.join(current['question']))
                answer = normalized(''.join(current['answer']))
                if question.endswith('?') and answer:
                    self.faq.append((question, answer))
        if self.local_items:
            current = self.local_items[-1]
            if tag == 'h3' and len(self.stack) == current['question_depth']: current['question_depth'] = None
            if tag == 'p' and len(self.stack) == current['answer_depth']:
                current['answer_depth'] = None; current['answer'].append(' ')
            if tag == 'div' and len(self.stack) == current['depth']:
                self.local_items.pop()
                question = normalized(''.join(current['question'])); answer = normalized(''.join(current['answer']))
                if question.endswith('?') and answer: self.faq.append((question, answer))
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]['tag'] == tag:
                del self.stack[index:]
                break


def parse(text: str) -> Page:
    page = Page(); page.feed(text)
    return page


def graph_rows(value):
    if isinstance(value, list):
        for item in value: yield from graph_rows(item)
    elif isinstance(value, dict):
        if '@graph' in value: yield from graph_rows(value['@graph'])
        else: yield value


def tag_attrs(tag: str) -> dict:
    class Tag(HTMLParser):
        def handle_starttag(self, name, pairs): self.attrs = dict(pairs)
    parser = Tag(); parser.attrs = {}; parser.feed(tag)
    return parser.attrs


def metadata(text: str, name: str, graph: list[dict]) -> str:
    url = page_url(name)
    text = LD_SCRIPT.sub('', text)
    text = re.sub(r'<link\b[^>]*>', lambda m: '' if 'canonical' in tag_attrs(m[0]).get('rel', '').lower().split() else m[0], text, flags=re.I)
    def og(match):
        attrs = tag_attrs(match[0]); prop = attrs.get('property', '').lower()
        if prop == 'og:url': return ''
        if prop in {'og:image', 'og:image:url', 'og:image:secure_url', 'og:video', 'og:audio'} and attrs.get('content'):
            return re.sub(r'\bcontent\s*=\s*(["\']).*?\1', lambda _: 'content="' + html.escape(own_url(attrs['content'], name), quote=True) + '"', match[0], flags=re.I)
        return match[0]
    text = re.sub(r'<meta\b[^>]*>', og, text, flags=re.I)
    payload = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    addition = '<link rel="canonical" href="' + html.escape(url, quote=True) + '"><meta property="og:url" content="' + html.escape(url, quote=True) + '"><script type="application/ld+json">' + payload + '</script>'
    return re.sub(r'</head\s*>', lambda _: addition + '</head>', text, count=1, flags=re.I)


def build_graph(name: str, page: Page, files: dict[str, bytes], districts: list[str], model_rows: list[dict]) -> list[dict]:
    url = page_url(name); heading = normalized(''.join(page.h1)) or normalized(''.join(page.title)).split(' | ')[0]
    business = {'@type': 'HVACBusiness', '@id': BUSINESS_ID, 'name': 'Sağlam Teknik', 'url': ORIGIN + '/', 'telephone': '+905346225515', 'description': 'İstanbul Avrupa Yakası için markalardan bağımsız özel kombi, klima ve petek teknik servisi.', 'areaServed': [{'@type': 'AdministrativeArea', 'name': district + ', İstanbul'} for district in districts]}
    for logo in ['assets/brand/logo-ribbon.webp', 'assets/brand/logo-ribbon.png']:
        if logo in files:
            business['logo'] = ORIGIN + '/' + logo
            break
    website = {'@type': 'WebSite', '@id': SITE_ID, 'url': ORIGIN + '/', 'name': 'Sağlam Teknik', 'inLanguage': 'tr-TR', 'publisher': {'@id': BUSINESS_ID}}
    webpage = {'@type': 'WebPage', '@id': url + '#sayfa', 'url': url, 'name': heading, 'inLanguage': 'tr-TR', 'isPartOf': {'@id': SITE_ID}, 'publisher': {'@id': BUSINESS_ID}, 'breadcrumb': {'@id': url + '#breadcrumb'}}
    if page.description: webpage['description'] = page.description
    for schema in page.schemas:
        for row in graph_rows(schema):
            if row.get('@type') == 'WebPage' and re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:T.*)?', str(row.get('dateModified', ''))): webpage['dateModified'] = row['dateModified']
    crumbs = [{'@type': 'ListItem', 'position': 1, 'name': 'Ana Sayfa', 'item': ORIGIN + '/'}]
    if name != 'index.html': crumbs.append({'@type': 'ListItem', 'position': 2, 'name': heading, 'item': url})
    graph = [business, website, webpage, {'@type': 'BreadcrumbList', '@id': url + '#breadcrumb', 'itemListElement': crumbs}]
    if name in SERVICE_PAGES or name.endswith('-servisi.html'):
        service = {'@type': 'Service', '@id': url + '#hizmet', 'name': heading, 'url': url, 'provider': {'@id': BUSINESS_ID}, 'mainEntityOfPage': {'@id': url + '#sayfa'}, 'areaServed': {'@type': 'AdministrativeArea', 'name': 'İstanbul Avrupa Yakası'}}
        for district in districts:
            slug = district.translate(str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosuCGIOSU')).lower()
            if name.startswith(slug + '-'):
                service['areaServed']['name'] = district + ', İstanbul'
                break
        graph.append(service); webpage['mainEntity'] = {'@id': service['@id']}
    elif model_rows or (name.startswith(('kombi-', 'klima-')) or name in {'baymak-e1-hatasi.html', 'servis-oncesi-guvenli-kontrol.html'}) and name not in DIRECTORIES:
        article = {'@type': 'TechArticle', '@id': url + '#makale', 'url': url, 'headline': heading, 'inLanguage': 'tr-TR', 'mainEntityOfPage': {'@id': url + '#sayfa'}, 'publisher': {'@id': BUSINESS_ID}}
        if page.description: article['description'] = page.description
        if 'dateModified' in webpage: article['dateModified'] = webpage['dateModified']
        citations = []
        for model in model_rows:
            manual = model.get('manual', {})
            source = manual.get('url', '')
            if source and manual.get('official') and source in page.links:
                citation = {'@type': 'CreativeWork', 'url': source, 'name': manual.get('title') or model.get('label', '')}
                if manual.get('locator'): citation['description'] = manual['locator']
                if citation not in citations: citations.append(citation)
        if citations: article['citation'] = citations
        graph.append(article); webpage['mainEntity'] = {'@id': article['@id']}
    questions = []
    for question, answer in page.faq:
        row = {'@type': 'Question', 'name': question, 'acceptedAnswer': {'@type': 'Answer', 'text': answer}}
        if row not in questions: questions.append(row)
    if questions:
        graph.append({'@type': 'FAQPage', '@id': url + '#sss', 'url': url, 'isPartOf': {'@id': url + '#sayfa'}, 'inLanguage': 'tr-TR', 'mainEntity': questions})
    return graph


def llms(pages: dict[str, Page], districts: list[str], models: dict[str, list[dict]], published: set[str], business: dict) -> str:
    claims = business.get('business_claims', {})
    qualification = claims.get('qualification', {})
    warranty = claims.get('warranty', {})
    declaration = 'MYK ve eğitim belgesi bilgisi doğrulama bekliyor; geçerli belge, kapsadığı meslek ve işlem hizmet görüşmesinde sorulmalıdır.'
    if qualification.get('status') == 'business-declared' and qualification.get('credential_number'):
        declaration = 'İşletme sahibinin beyanına göre MYK belge numarası: ' + str(qualification['credential_number']) + '. Belgenin geçerliliği ve işlem kapsamı bu dizin tarafından bağımsız doğrulanmış değildir; mesleki belge üreticinin yetkili servisi olunduğu anlamına gelmez.'
    if warranty.get('status') == 'business-declared' and warranty.get('duration') and warranty.get('scope'):
        declaration += ' İşletme sahibinin garanti beyanı: ' + str(warranty['duration']) + ' parça ve işçilik; kapsam: ' + str(warranty['scope']) + '. Yazılı servis fişi koşulları esas alınır.'
    lines = ['# Sağlam Teknik', '', '> İstanbul Avrupa Yakası için markalardan bağımsız özel kombi, klima ve petek teknik servisi.', '', 'Telefon: 0534 622 55 15 (+90 534 622 55 15). Marka üreticilerinin yetkili servisi olduğu iddia edilmez.', '', declaration, '', 'Kod anlamı yalnız belgelenmiş tam model, ülke, ürün ve kontrolcü kapsamına aittir. E1/E01 ve noktalı kodlar otomatik eşitlenmez. Kaynak/kapsam uyarısı kullanıcı onayı gerektiriyorsa atlanmaz. Listelenmeyen modeller veya tarihî ürünler için eksiksiz kapsam iddia edilmez.', '', 'Bu dosya isteğe bağlı okunabilir bağlantı özetidir; AI sistemleri tarafından kullanılma, önerilme, sıralama veya müşteri garantisi vermez.', '', '## Hizmet bölgeleri', '']
    district_routes = set()
    for district in districts:
        slug = district.translate(str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosuCGIOSU')).lower()
        links = [('Kombi', slug + '-kombi-servisi.html'), ('Klima', slug + '-klima-servisi.html')]
        district_routes.update(name for _, name in links)
        available = ['[' + label + '](' + page_url(name) + ')' for label, name in links if name in published]
        lines.append('- ' + district + (': ' + ' · '.join(available) if available else ''))
    for title, names in [('İşletme, hizmet ve kaynak bilgileri', sorted(published - set(models) - district_routes)), ('Yayımlanmış model ve belge rehberleri', sorted(name for name in models if name in published))]:
        lines += ['', '## ' + title, '']
        for name in names:
            heading = normalized(''.join(pages[name].h1)) or name
            lines.append('- [' + heading.replace('[', '(').replace(']', ')') + '](' + page_url(name) + ')')
    return '\n'.join(lines) + '\n'


def enhance_files(files: dict[str, bytes]) -> dict:
    """Mutate final file bytes before relative asset/link conversion; no deployment."""
    pages = {name: parse(data.decode('utf-8')) for name, data in files.items() if visitor(name)}
    preview = any(page.preview for page in pages.values())
    catalog = json.loads(files.get('assets/servis-katalog.json', b'{}'))
    districts = list(dict.fromkeys(value for value in catalog.get('districts', []) if isinstance(value, str)))
    faults = json.loads(files.get('assets/verified-faults.json', b'{}')); models = {}
    for model in faults.get('models', []):
        name = urlsplit(model.get('path', '')).path.removeprefix('/site/').lstrip('/')
        if name in pages: models.setdefault(name, []).append(model)
    counts = Counter()
    for name, page in pages.items():
        graph = build_graph(name, page, files, districts, models.get(name, []))
        files[name] = metadata(files[name].decode('utf-8'), name, graph).encode('utf-8')
        counts.update(row['@type'] for row in graph)
    for name in list(files):
        if PurePosixPath(name).name != 'owner-admin.html': continue
        text = re.sub(r'<meta\b[^>]*>', lambda m: '' if tag_attrs(m[0]).get('name', '').lower() == 'robots' else m[0], files[name].decode('utf-8'), flags=re.I)
        files[name] = re.sub(r'</head\s*>', '<meta name="robots" content="noindex,nofollow"></head>', text, count=1, flags=re.I).encode('utf-8')
    published = {name for name, page in pages.items() if name not in SYSTEM_PAGES and (preview or not page.noindex)}
    business = json.loads(files.get('isletme-bilgileri.json', b'{}'))
    files['llms.txt'] = llms(pages, districts, models, published, business).encode('utf-8')
    if preview:
        files['robots.txt'] = b'User-agent: *\nAllow: /\n'
        files.pop('sitemap.xml', None)
    else:
        denied = {'/api.php', '/ai-koruma.php', '/assets/owner-admin.html', '/owner-admin.html', '/__yonetim', '/private/'}
        denied.update('/' + name for name in files if name.endswith('.php'))
        files['robots.txt'] = ('User-agent: *\nAllow: /\n' + ''.join('Disallow: ' + path + '\n' for path in sorted(denied)) + 'Sitemap: ' + ORIGIN + '/sitemap.xml\n').encode('utf-8')
        namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'; ET.register_namespace('', namespace)
        sitemap = ET.Element('{' + namespace + '}urlset')
        for name in sorted(published):
            row = ET.SubElement(sitemap, '{' + namespace + '}url')
            ET.SubElement(row, '{' + namespace + '}loc').text = page_url(name)
        files['sitemap.xml'] = ET.tostring(sitemap, encoding='utf-8', xml_declaration=True) + b'\n'
    return {'visitor_pages': len(pages), 'mode': 'preview' if preview else 'production', 'schema_types': dict(sorted(counts.items())), 'districts': len(districts), 'published_model_urls': len(set(models) & published), 'sitemap_urls': 0 if preview else len(published)}
