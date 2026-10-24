"""Curated HTML navigation and a static-anchor crawl graph. Never creates routes."""
from __future__ import annotations
import argparse
from collections import Counter, deque
import html
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote, urlencode, urljoin, urlsplit

ORIGIN = 'https://saglamkombiklima.com.tr'
MARKER = 'data-st-reading-links="1"'


def visitor(name: str) -> bool:
    leaf = PurePosixPath(name).name
    return name.endswith('.html') and leaf != 'owner-admin.html' and not re.match(r'(google|yandex_).*\.html$', leaf)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.main_links = []
        self.in_main = False
        self.noindex = False
        self.home = ''
        self.h1 = []
        self.in_h1 = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'main': self.in_main = True
        if tag == 'h1': self.in_h1 = True
        if tag == 'meta' and attrs.get('name', '').lower() == 'robots':
            self.noindex |= 'noindex' in re.split(r'[\s,]+', attrs.get('content', '').lower())
        if tag == 'a' and attrs.get('href') and 'nofollow' not in attrs.get('rel', '').lower().split():
            self.links.append(attrs['href'])
            if self.in_main: self.main_links.append(attrs['href'])
            if 'at-brand' in attrs.get('class', '').split(): self.home = attrs['href']

    def handle_endtag(self, tag):
        if tag == 'main': self.in_main = False
        if tag == 'h1': self.in_h1 = False

    def handle_data(self, value):
        if self.in_h1: self.h1.append(value)


def parse(text: str) -> Page:
    page = Page()
    page.feed(text)
    return page


def canonical_href(href: str, source='index.html') -> str:
    """Source archive URLs use /site/; editable sources use / ."""
    url = urlsplit(urljoin(ORIGIN + '/' + source, href))
    if url.scheme not in ('http', 'https') or url.netloc != urlsplit(ORIGIN).netloc:
        return ''
    path = url.path.removeprefix('/site/') if url.path.startswith('/site/') else url.path.lstrip('/')
    path = path or 'index.html'
    return '/' + path + (('?' + url.query) if url.query else '') + (('#' + url.fragment) if url.fragment else '')


def slug(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', value.translate(str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosuCGIOSU')).lower()).strip('-')


# Existing sources relate these semt descriptions to the named district guides.
# Ambiguous semt names remain descriptions; these links never choose an address.
LOCAL_CONTEXT = {
    'Küçükçekmece': ('Sefaköy', 'sefakoy-servisi.html'),
    'Sarıyer': ('Kilyos / Kumköy', 'kilyos-servisi.html'),
    'Başakşehir': ('Bahçeşehir', 'bahcesehir-servisi.html'),
    'Güngören': ('Merter', 'merter-servisi.html'),
    'Gaziosmanpaşa': ('500 Evler', '500-evler-servisi.html'),
    'Sultangazi': ('500 Evler', '500-evler-servisi.html'),
}


SERVICE_CONTEXT = {
    'kombi-servisi.html': ('Servis kapsamını model ve kullanım bilgisiyle tamamlayın.', ['hizmetler.html', 'kombi-modeli-nasil-ogrenilir.html', 'kombi-hata-kodu.html', 'iletisim.html']),
    'kombi-tamiri.html': ('Onarım talebinde model, ekran gösterimi ve yapılacak kontrolü ayrı değerlendirin.', ['kombi-servisi.html', 'kombi-modeli-nasil-ogrenilir.html', 'kombi-hata-kodu.html', 'servis-oncesi-guvenli-kontrol.html']),
    'kombi-bakimi.html': ('Planlı bakımın zamanı ile devam eden arıza belirtisini birbirinden ayırın.', ['kombi-servisi.html', 'kombi-bakimi-ne-zaman-yapilir.html', 'kombi-hata-kodu.html', 'servis-oncesi-guvenli-kontrol.html']),
    'klima-servisi.html': ('Klima talebinizi cihaz etiketi ve istediğiniz işlemin kapsamıyla tamamlayın.', ['hizmetler.html', 'klima-modeli-nasil-ogrenilir.html', 'klima-filtre-temizligi.html', 'klima-hata-kodu.html']),
    'klima-tamiri.html': ('Arıza incelemesinde model belgesi ile güvenli ilk gözlemleri birlikte kullanın.', ['klima-servisi.html', 'klima-modeli-nasil-ogrenilir.html', 'klima-hata-kodu.html', 'servis-oncesi-guvenli-kontrol.html']),
    'klima-bakimi.html': ('Kullanıcının yapabileceği filtre bakımı ile servis kontrolünün sınırlarını ayırın.', ['klima-servisi.html', 'klima-filtre-temizligi.html', 'klima-su-akitiyor.html', 'servis-oncesi-guvenli-kontrol.html']),
    'klima-montaji.html': ('Yeni konum, mevcut cihaz ve bağlantı kontrolü için ilgili işlem rehberlerini karşılaştırın.', ['klima-servisi.html', 'klima-sokumu.html', 'klima-gaz-kontrolu.html', 'klima-modeli-nasil-ogrenilir.html']),
    'klima-sokumu.html': ('Söküm ile sonraki kurulumun kapsamını ayrı görüşün; model ve yeni yer bilgisi ayrıca gereklidir.', ['klima-servisi.html', 'klima-montaji.html', 'klima-modeli-nasil-ogrenilir.html', 'iletisim.html']),
    'klima-gaz-kontrolu.html': ('Soğutmama belirtisi tek başına gaz işlemi kararı değildir; belirti ve kontrol kapsamını ayrı okuyun.', ['klima-servisi.html', 'klima-sogutmuyor.html', 'klima-modeli-nasil-ogrenilir.html', 'servis-oncesi-guvenli-kontrol.html']),
    'petek-temizligi.html': ('Petek temizliği talebini sıcak su ve genel ısıtma şikâyetinden ayırın.', ['kombi-servisi.html', 'kombi-petek-isitmiyor.html', 'kombi-basinci.html', 'hizmetler.html']),
    'kombi-sicak-su.html': ('Yalnız sıcak suyu etkileyen durumla basınç veya kodla birlikte görülen sorunu ayrı kaydedin.', ['kombi-servisi.html', 'kombi-modeli-nasil-ogrenilir.html', 'kombi-basinci.html', 'kombi-hata-kodu.html']),
    'kombi-petek-isitmiyor.html': ('Isıtma, sıcak su ve temizlik beklentisini birbirine karıştırmadan ilgili rehberi seçin.', ['kombi-servisi.html', 'petek-temizligi.html', 'kombi-sicak-su.html', 'kombi-basinci.html']),
    'klima-sogutmuyor.html': ('Hava akışı, ekrandaki gösterim ve soğutucu devre kontrolü farklı değerlendirmelerdir.', ['klima-servisi.html', 'klima-filtre-temizligi.html', 'klima-hata-kodu.html', 'klima-gaz-kontrolu.html']),
    'klima-su-akitiyor.html': ('Suyun görüldüğü yer ile bakım veya montaj talebini ayrı anlatmaya yardımcı rehberler.', ['klima-servisi.html', 'klima-bakimi.html', 'klima-montaji.html', 'servis-oncesi-guvenli-kontrol.html']),
}


def enhance_files(files: dict[str, bytes]) -> dict:
    pages = {name: parse(content.decode('utf-8')) for name, content in files.items() if visitor(name)}
    catalog = json.loads(files.get('assets/servis-katalog.json', b'{}'))
    faults = json.loads(files.get('assets/verified-faults.json', b'{}'))
    model_pages = {}
    for model in faults.get('models', []):
        model_pages.setdefault(PurePosixPath(model['path']).name, []).append(model)
    districts = {slug(name): name for name in catalog.get('districts', [])}
    changed = []
    added = 0
    hub_added = 0

    def label(target):
        return ' '.join(pages[target].h1).strip() or target.removesuffix('.html').replace('-', ' ')

    def add_module(name, title, intro, candidates, identifier='st-reading-links'):
        nonlocal added
        if name not in pages: return 0
        text = files[name].decode('utf-8')
        if f'id="{identifier}"' in text: return 0
        existing = {canonical_href(href, name) for href in pages[name].main_links}
        links = []
        used = set()
        for href, title_text in candidates:
            href = canonical_href(href, name)
            target = urlsplit(href).path.lstrip('/')
            if target not in pages or target == name or href in existing or href in used:
                continue
            links.append((href, title_text or label(target)))
            used.add(href)
            if len(links) == 6: break
        if len(links) < 3: return 0
        items = ''.join('<li><a href="' + html.escape(href, quote=True) + '">' + html.escape(text) + '<span aria-hidden="true">↗</span></a></li>' for href, text in links)
        section = '<nav id="' + identifier + '" class="st-reading-links" ' + MARKER + ' aria-labelledby="' + identifier + '-title"><h2 id="' + identifier + '-title">' + html.escape(title) + '</h2><p>' + html.escape(intro) + '</p><ul>' + items + '</ul></nav>'
        if '</main>' not in text: return 0
        text = text.replace('</main>', section + '</main>', 1)
        if 'assets/internal-links.css' in files and 'assets/internal-links.css' not in text:
            text = text.replace('</head>', '<link rel="stylesheet" href="/assets/internal-links.css"></head>', 1)
        files[name] = text.encode('utf-8')
        pages[name] = parse(text)
        changed.append(name)
        added += len(links)
        return len(links)

    # The current region directory already has all50 anchors. Repair only omissions.
    if 'bolgeler.html' in pages:
        existing = {urlsplit(canonical_href(href, 'bolgeler.html')).path for href in pages['bolgeler.html'].main_links}
        missing = []
        for district_slug, district in districts.items():
            for device in ('kombi', 'klima'):
                target = district_slug + '-' + device + '-servisi.html'
                if target in pages and '/' + target not in existing:
                    missing.append(('/' + target, district + ' ' + device + ' servis bilgileri'))
        if missing:
            text = files['bolgeler.html'].decode('utf-8')
            links = ''.join('<li><a href="' + href + '">' + html.escape(title) + '</a></li>' for href, title in missing)
            text = text.replace('</main>', '<nav class="st-reading-links" id="st-district-links" aria-labelledby="st-district-links-title"><h2 id="st-district-links-title">İlçe ve cihaz rehberleri</h2><ul>' + links + '</ul></nav></main>', 1)
            if 'assets/internal-links.css' in files and 'assets/internal-links.css' not in text:
                text = text.replace('</head>', '<link rel="stylesheet" href="/assets/internal-links.css"></head>', 1)
            files['bolgeler.html'] = text.encode('utf-8')
            pages['bolgeler.html'] = parse(text)
            changed.append('bolgeler.html');added += len(missing);hub_added += len(missing)

    for name, group in model_pages.items():
        if name not in pages: continue
        model = group[0]
        device, brand = model['device'], model['brand']
        filtered = '/model-ariza-kodlari.html?' + urlencode({'device': device, 'brand': brand})
        candidates = [('/' + device + '-servisi.html', device.capitalize() + ' servis ve işlem kapsamı'), (filtered, brand + ' ' + device + ' model aileleri'), ('/' + device + '-modeli-nasil-ogrenilir.html', 'Cihaz etiketindeki tam modeli bulma'), ('/' + device + '-hata-kodu.html', 'Model bilinmiyorsa kodu nasıl kaydetmeli?'), ('/' + slug(brand) + '-' + device + '-servisi.html', brand + ' ' + device + ' servis rehberi')]
        add_module(name, 'Model belgesinden sonraki adım', brand + ' ' + device + ' için model seçimi ve servis kapsamını inceleyin. Bu sayfadaki kod açıklamasını başka bir ürün ailesine aktarmayın.', candidates)

    for name, (intro, targets) in SERVICE_CONTEXT.items():
        add_module(name, 'İşlem ve belirtinize göre devam edin', intro, [('/' + target, '') for target in targets])

    # Only related semt descriptions already supported by existing local guides.
    for district_slug, district in districts.items():
        if district not in LOCAL_CONTEXT: continue
        semt, semt_page = LOCAL_CONTEXT[district]
        for device in ('kombi', 'klima'):
            name = district_slug + '-' + device + '-servisi.html'
            if name not in pages: continue
            existing_pages = {urlsplit(canonical_href(href, name)).path for href in pages[name].main_links}
            if '/' + semt_page in existing_pages: continue
            other = 'klima' if device == 'kombi' else 'kombi'
            candidates = [('/' + semt_page, semt + ' semt tarifini doğrulayın'), ('/' + district_slug + '-' + other + '-servisi.html', district + ' ' + other + ' rehberi'), ('/bolgeler.html', 'Başka bir ilçe veya mahalle seçin'), ('/iletisim.html', 'Adres ve işlem kapsamını görüşün')]
            add_module(name, 'Semt tarifini resmî adresle tamamlayın', semt + ' bir konum tarifi olarak kullanılıyorsa resmî ilçe ve mahalleyi ayrıca kontrol edin. Bu bağlantılar adresinizi sizin yerinize seçmez.', candidates)

    policy = {
        'hakkimizda.html': ('İşletme bilgileri ve hizmet kapsamı', 'Firma bilgilerini kontrol edin; bölge ve işlem rehberleriyle talebinizin kapsamını tamamlayın.', ['isletme-bilgileri.html', 'bolgeler.html', 'hizmetler.html']),
        'iletisim.html': ('Talebin kapsamını önceden inceleyin', 'İletişim bilgilerinin yanında hizmet bölgesi ve yapılacak işlemin kapsamını da kontrol edebilirsiniz.', ['isletme-bilgileri.html', 'bolgeler.html', 'hizmetler.html']),
        'isletme-bilgileri.html': ('İşletme, yayın ve hizmet bilgileri', 'İşletme verisini servis yaklaşımı ve kaynak kullanım ilkeleriyle birlikte inceleyin.', ['hakkimizda.html', 'kaynak-ve-yayin-ilkeleri.html', 'bolgeler.html', 'hizmetler.html']),
    }
    for name, (title, intro, targets) in policy.items():
        add_module(name, title, intro, [('/' + target, '') for target in targets])
    return {'pages_enhanced': len(set(changed)), 'links_added': added, 'hub_links_added': hub_added, 'touched_pages': sorted(set(changed))}


def analyze_graph(files: dict[str, bytes]) -> dict:
    pages = {name: parse(content.decode('utf-8')) for name, content in files.items() if visitor(name)}
    home = pages.get('index.html')
    base = urlsplit(urljoin(ORIGIN + '/', home.home if home and home.home else '/')).path
    base = re.sub(r'index\.html$', '', base)
    if not base.endswith('/'): base += '/'
    graph = {name: set() for name in pages}
    unresolved = set()
    for name, page in pages.items():
        for href in page.links:
            url = urlsplit(urljoin(ORIGIN + base + name, href))
            if url.scheme not in ('http', 'https') or url.netloc != urlsplit(ORIGIN).netloc: continue
            if not url.path.startswith(base):
                if url.path.endswith('.html'): unresolved.add((name, url.path))
                continue
            target = unquote(url.path[len(base):]) or 'index.html'
            if target in pages: graph[name].add(target)
            elif target.endswith('.html') and not re.match(r'(google|yandex_).*\.html$', PurePosixPath(target).name): unresolved.add((name, url.path))
    depths = {'index.html': 0} if home else {}
    queue = deque(depths)
    while queue:
        current = queue.popleft()
        for target in sorted(graph[current]):
            if target not in depths:
                depths[target] = depths[current] + 1
                queue.append(target)
    indexable = {name for name, page in pages.items() if not page.noindex}
    incoming = Counter(target for name in graph for target in graph[name] if target != name)
    reached = indexable & depths.keys()
    return {'schema_version': 1, 'method': 'Static HTML a[href] links only; JavaScript, forms, assets, external and nofollow links excluded. Verification/admin files are not visitor routes. Query/fragment variants are one graph node.', 'visitor_routes': len(pages), 'indexable_routes': len(indexable), 'reachable_indexable_routes': len(reached), 'max_indexable_depth': max((depths[name] for name in reached), default=None), 'depth_histogram': dict(sorted(Counter(depths[name] for name in reached).items())), 'unreachable_indexable': sorted(indexable - depths.keys()), 'unlinked_indexable': sorted(name for name in indexable if name != 'index.html' and not incoming[name]), 'unresolved_internal_pages': [{'source': source, 'target': target} for source, target in sorted(unresolved)], 'routes': [{'path': '/' + name, 'indexable': name in indexable, 'depth': depths.get(name), 'incoming': incoming[name], 'outgoing': len(graph[name])} for name in sorted(pages)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--expected-indexable', type=int, default=201)
    parser.add_argument('--max-depth', type=int, default=3)
    args = parser.parse_args()
    files = {p.relative_to(args.directory).as_posix(): p.read_bytes() for p in args.directory.rglob('*.html')}
    report = analyze_graph(files)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    summary = {key: value for key, value in report.items() if key not in ('routes', 'method')}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.check and (report['indexable_routes'] != args.expected_indexable or report['unreachable_indexable'] or report['unlinked_indexable'] or report['unresolved_internal_pages'] or report['max_indexable_depth'] is None or report['max_indexable_depth'] > args.max_depth):
        raise SystemExit(1)


if __name__ == '__main__': main()
