"""Show user-supplied Search Console cohorts against the actual built files.

The status labels are historical user evidence, not live Google index results.
This noindex review never changes canonical policy or creates service URLs.
"""
from __future__ import annotations
from collections import defaultdict
from html import escape
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit
import json

ORIGIN = 'https://saglamkombiklima.com.tr/'
REVIEW_PAGES = {'dizin-inceleme.html', 'icerik-inceleme.html', 'teknik-rapor.html'}
STATUS = {'indexed': 'Listende dizine eklenmiş', 'not_indexed': 'Listende dizine eklenmemiş',
          'parameter': 'İletişim formu parametresi'}
CATEGORY = {'district': 'İlçe servisi', 'locality': 'Semt servisi', 'brand': 'Marka servisi',
            'service_or_symptom': 'Hizmet / belirti rehberi', 'model': 'Model kod rehberi',
            'hub_or_business': 'Ana / kurumsal sayfa', 'parameter': 'İletişim formu seçimi'}


class Snapshot(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.canonical = []
        self.robots = []
        self.title = []
        self._title = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'title':
            self._title = True
        elif tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        elif tag == 'link' and 'canonical' in attrs.get('rel', '').split():
            self.canonical.append(attrs.get('href', ''))
        elif tag == 'meta' and attrs.get('name', '').lower() == 'robots':
            self.robots.append(attrs.get('content', ''))

    def handle_endtag(self, tag):
        if tag == 'title':
            self._title = False

    def handle_data(self, value):
        if self._title:
            self.title.append(value)


def _target(source, href):
    url = urlsplit(urljoin(ORIGIN + source, href))
    if url.scheme not in {'http', 'https'} or url.hostname not in {'saglamkombiklima.com.tr', 'www.saglamkombiklima.com.tr'}:
        return None
    path = unquote(url.path).lstrip('/') or 'index.html'
    if path.startswith('site/'):
        path = path[5:] or 'index.html'
    if path.endswith('/'):
        path += 'index.html'
    return str(PurePosixPath(path))


def _current(files):
    docs = {name: Snapshot(data.decode('utf-8')) for name, data in files.items()
            if name.endswith('.html') and '/' not in name and name not in REVIEW_PAGES
            and not name.startswith(('google', 'yandex'))}
    incoming = defaultdict(set)
    for name, page in docs.items():
        for href in page.links:
            dest = _target(name, href)
            if dest in docs and dest != name:
                incoming[dest].add(name)
    return docs, incoming


def _code(values, fallback):
    return '<br>'.join('<code>' + escape(value) + '</code>' for value in values) if values else escape(fallback)


def _repair(row, route, files, metrics, before_count, current_count):
    category = row['category']
    text = files.get(route, b'').decode('utf-8')
    region_routes = set(metrics.get('regions', {}).get('region_routes', []))
    service_routes = metrics.get('service_editorial', {}).get('routes', [])
    if isinstance(service_routes, dict):
        service_routes = service_routes.keys()
    if route in {'klima-montaji.html','klima-sokumu.html'}:
        return 'Önceki hizmet kapsamı kararın uyarınca aktif tekliften çıkarıldı; eski adres noindex bilgilendirme sayfası olarak korunuyor. Bu URL için dizine ekleme hedeflenmiyor.'
    if route in region_routes or 'data-hybrid-region=' in text:
        return 'Bölgenin ana gövdesi ayrı yazıldı. Gerçek mahalle listesi ve komşu ilçe bağlantıları, cihaz / marka / belirti seçimleriyle birlikte korunuyor.'
    if category == 'model':
        link_note = ('Gelen sayfa sayısı ' + str(before_count) + ' → ' + str(current_count) + '.') if current_count != before_count else 'Gelen sayfa bağlantıları aşağıdaki sayımla gösteriliyor.'
        return 'Mevcut model ve kod tablosu korunuyor; başka modelin kod açıklaması aktarılmadı. ' + link_note
    if category == 'brand':
        changed = (route in service_routes or 'data-service-editorial' in text or 'data-narrative-route=' in text)
        return ('Markanın ana anlatımı ve model seçimi düzenlendi. ' if changed else 'Markanın mevcut servis ve model içeriği korunuyor. ') + 'Model belgesi ve belirti rehberleri aynı marka içinde değerlendiriliyor; tüm modeller doğrulanmış sayılmıyor.'
    if category == 'service_or_symptom':
        changed = (route in service_routes or 'data-service-editorial' in text or 'data-narrative-route=' in text)
        return ('Belirtiye / işleme özel ana metin yeniden düzenlendi. ' if changed else 'Belirtiye / işleme ait rehber ve adresi korunuyor. ') + 'İlgili cihaz, marka ve bölge sayfalarıyla bağlantı kuruldu; belirti kesin parça teşhisi olarak sunulmuyor.'
    return 'Mevcut adres ve sayfanın görevi korundu. Teknik erişilebilirlik ile Google’ın dizine alma kararı ayrı değerlendirilir.'


def add_index_review(files, repo, metrics):
    """Add a mobile-readable, filterable noindex comparison for 108 + 15 URLs."""
    cohorts = json.loads((repo / 'hybrid/data/index-cohorts.json').read_text())
    evidence = json.loads((repo / 'hybrid/evidence/index-cohort-before.json').read_text())
    old = {row['path']: row for row in evidence['rows']}
    docs, incoming = _current(files)
    rows = []
    sequence = 0
    for status, paths in [('indexed', cohorts['indexed_user_report']), ('not_indexed', cohorts['not_indexed_user_report'])]:
        for route in paths:
            sequence += 1
            before = old[route]
            current = docs.get(route)
            if current is None:
                raise ValueError('Index review route is missing from build: ' + route)
            previous_in = before['inbound_pages']
            current_in = len(incoming[route])
            caption = ' '.join(current.title).strip() or route
            search = ' '.join([route, caption, CATEGORY[before['category']], STATUS[status]])
            compare = ('<div class="compare"><section><h3>Gönderdiğin ZIP</h3><dl><dt>Canonical</dt><dd>'
                       + _code(before['canonical'], 'Yok') + '</dd><dt>Robots meta</dt><dd>'
                       + _code(before['robots'], 'noindex yok; meta belirtilmemiş') + '</dd><dt>Gelen farklı HTML sayfası</dt><dd>'
                       + str(previous_in) + '</dd><dt>Sitemap</dt><dd>' + ('Var' if before['in_sitemap'] else 'Yok') + '</dd></dl></section>'
                       '<section><h3>Bu üretim paketi</h3><dl><dt>Canonical</dt><dd>' + _code(current.canonical, 'Yok')
                       + '</dd><dt>Robots meta</dt><dd>' + _code(current.robots, 'noindex yok; meta belirtilmemiş')
                       + '</dd><dt>Gelen farklı HTML sayfası</dt><dd>' + str(current_in) + '</dd><dt>Dosya</dt><dd>Mevcut</dd></dl></section></div>')
            repair = _repair(before, route, files, metrics, previous_in, current_in)
            rows.append('<details class="item" data-index-row data-status="' + status + '" data-category="'
                        + escape(before['category'], quote=True) + '" data-search="' + escape(search, quote=True) + '"><summary><span>'
                        + str(sequence) + '. ' + escape(caption) + '</span><small>' + escape(STATUS[status]) + ' · '
                        + escape(CATEGORY[before['category']]) + '</small><code>' + escape(route) + '</code></summary>'
                        '<p><a href="' + escape(route, quote=True) + '" target="_blank" rel="noopener">Sayfayı aç ↗</a></p>'
                        + compare + '<p class="action">' + escape(repair) + '</p></details>')
    contact_before = evidence['parameterized_contact']
    contact_now = docs['iletisim.html']
    for query in cohorts['parameter_contact_user_report']:
        sequence += 1
        rows.append('<details class="item parameter" data-index-row data-status="parameter" data-category="parameter" data-search="'
                    + escape(unquote(query).replace('+', ' ') + ' iletişim parametre mahalle form', quote=True) + '"><summary><span>'
                    + str(sequence) + '. İletişim formu seçimi</span><small>Listendeki eklenmemiş sorgu varyasyonu</small><code>'
                    + escape(query) + '</code></summary><p><a href="' + escape(query, quote=True) + '" target="_blank" rel="noopener">Form seçimini aç ↗</a></p>'
                    '<p>Bu adres ayrı bir mahalle içeriği değildir. Cihaz, konum veya marka bilgisi aynı iletişim formuna aktarılır. Ana iletişim adresi paylaştığın dizine eklenmiş listede bulunuyor.</p>'
                    '<dl><dt>ZIP canonical</dt><dd>' + _code(contact_before['canonical'], 'Yok') + '</dd><dt>Bu paketin canonical adresi</dt><dd>'
                    + _code(contact_now.canonical, 'Yok') + '</dd></dl><p class="action">Sorgu varyasyonları sitemap’e eklenmedi. Formun seçimleri korunur; bağımsız olarak dizine girmeleri hedeflenmez.</p></details>')
    if len(rows) != 123:
        raise ValueError('Unexpected Search Console cohort length: ' + str(len(rows)))
    groups = evidence['cohort_by_category']
    matched_rows = []
    for category in ['district', 'locality', 'brand', 'service_or_symptom', 'model', 'hub_or_business']:
        group = groups[category]
        a, b = group['indexed'], group['not_indexed']
        med = lambda value: '—' if value is None else str(value).replace('.', ',')
        matched_rows.append('<tr><th scope="row">' + CATEGORY[category] + '</th><td>' + str(a['count']) + '</td><td>' + str(b['count'])
                            + '</td><td>' + med(a['median_inbound_pages']) + ' / ' + med(b['median_inbound_pages']) + '</td></tr>')
    style = '''body{margin:0;background:#f4f1e8;color:#173b32;font:16px/1.7 system-ui,sans-serif}main{max-width:1160px;margin:auto;padding:24px 18px 70px}h1{font-size:clamp(28px,5vw,44px);line-height:1.2}h2{margin-top:1.8em}h3{line-height:1.4}a{color:#174d40;text-underline-offset:4px}p,li,code,dd{overflow-wrap:anywhere}code{font-size:.86em}nav{display:flex;flex-wrap:wrap;gap:18px}nav a{padding:8px 0;min-height:32px}.notice,.action{background:#e5ecd9;border-left:4px solid #375e41;padding:14px 18px}.item{margin:14px 0;padding:18px;background:#fffdf8;border:1px solid #bdcab2;border-radius:10px;min-width:0}.item>summary{cursor:pointer;font-weight:700;min-height:48px}.item>summary span,.item>summary small,.item>summary code{display:block}.item>summary small{font-size:13px;color:#52654d;font-weight:500}.item>summary code{margin-top:5px;font-weight:400}.compare{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px}.compare section{background:#f1f3e9;padding:14px;min-width:0}.compare section:first-child{background:#eee8dd}dl{margin:0}dt{font-weight:700;margin-top:10px}dd{margin:0}.controls{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:14px}input,select,button{font:inherit;box-sizing:border-box;min-height:46px;border:1px solid #8fA57f;border-radius:6px}input,select{display:block;width:100%;padding:10px;background:#fffdf8;color:#173b32}label{font-weight:650}button{padding:10px 16px;color:#fff;background:#315f47;cursor:pointer;margin:8px 8px 8px 0}.table-scroll{overflow:auto}table{border-collapse:collapse;width:100%;background:#fffdf8}th,td{border:1px solid #bdcab2;text-align:left;padding:10px;vertical-align:top}small{font-size:13px}.parameter{border-left:4px solid #78955e}footer{border-top:1px solid #bdcab2;margin-top:25px;padding-top:16px}body [hidden]{display:none!important}@media(max-width:760px){.compare,.controls{grid-template-columns:1fr}.item{padding:14px}.compare section{padding:12px}}'''
    script = '''(()=>{const rows=[...document.querySelectorAll('[data-index-row]')],q=document.getElementById('indexSearch'),s=document.getElementById('indexStatus'),out=document.getElementById('indexCount');const norm=x=>x.toLocaleLowerCase('tr').normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').replace(/ı/g,'i');function filter(){const query=norm(q.value.trim());let n=0;for(const row of rows){row.hidden=!!((s.value&&row.dataset.status!==s.value)||(query&&!norm(row.dataset.search).includes(query)));if(!row.hidden)n++;}out.textContent=n+' adres gösteriliyor';}q.addEventListener('input',filter);s.addEventListener('change',filter);document.getElementById('indexOpen').addEventListener('click',()=>rows.filter(r=>!r.hidden).forEach(r=>r.open=true));document.getElementById('indexClose').addEventListener('click',()=>rows.forEach(r=>r.open=false));filter();})();'''
    text = ('<!doctype html><html lang="tr" data-st-mode="production"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,follow"><title>Dizine Giren ve Girmeyen Sayfalar | Sağlam Teknik</title>'
            '<link rel="canonical" href="' + ORIGIN + 'dizin-inceleme.html"><style>' + style + '</style></head><body><main>'
            '<a href="index.html">← Siteyi aç</a><h1>Paylaştığın dizin listesinin sayfa karşılaştırması</h1>'
            '<p>44 dizine eklenmiş sayfa, 64 eklenmemiş sayfa ve 15 iletişim formu varyasyonu ayrı ayrı gösteriliyor. Her satırı açıp kaynak ZIP ile bu üretim paketini karşılaştırabilirsiniz.</p>'
            '<p class="notice"><strong>Bu etiketler canlı Google sonucu değildir.</strong> Durumlar senin paylaştığın Search Console listesine aittir. “Yok” ifadesinden kesin dışlanma nedeni çıkarılamaz. Bu ekran üretilen dosyaları inceler; canlı sunucu başlıklarını, Google’ın seçtiği canonical adresi veya son taramasını doğrulamaz.</p>'
            '<nav><a href="icerik-inceleme.html">Bölge, marka ve arıza metinlerini karşılaştır</a><a href="teknik-rapor.html">Teknik rapor</a><a href="bolgeler.html">Bölgeleri aç</a><a href="markalar.html">Markaları aç</a></nav>'
            '<h2>Aynı tür sayfaları kıyaslayınca</h2><div class="table-scroll"><table><thead><tr><th>Sayfa türü</th><th>Listende eklenen</th><th>Listende eklenmeyen</th><th>ZIP’te gelen sayfa medyanı<br>eklenen / eklenmeyen</th></tr></thead><tbody>'
            + ''.join(matched_rows) + '</tbody></table></div>'
            '<p>Markalarda iki gruba da medyan 36 farklı HTML sayfası bağlanıyor. Belirti / hizmet rehberlerinde bu değer 42 ve 40,5. Dolayısıyla yalnız bağlantı adedi veya metin uzunluğu Google’ın kararını açıklamıyor. İlçe sayfalarında kaynak ZIP’in ortak uzun gövdeleri ve isim değişimli girişleri ayrı bir içerik zayıflığıydı; bazı benzer sayfaların dizinde olması bu zayıflığı ortadan kaldırmıyor.</p>'
            '<p>108 asıl adresin tamamı gönderdiğin ZIP’te mevcut, sitemap’te, kendi canonical adresini taşıyor ve noindex taşımıyor. İletişimin 15 sorgu varyasyonu ise aynı canonical formda birleşiyor. Bunları 15 eksik mahalle sayfası saymak doğru olmaz.</p>'
            '<h2>Her adresi tek tek inceleyin</h2><div class="controls"><label for="indexSearch">Sayfa, marka, ilçe veya mahalle ara<input id="indexSearch" type="search" autocomplete="off" placeholder="Örn. Avcılar, Baymak, Atakent, Regal"></label>'
            '<label for="indexStatus">Paylaştığın listedeki grup<select id="indexStatus"><option value="">Tüm 123 adres</option><option value="not_indexed">Dizine eklenmemiş 64 asıl sayfa</option><option value="indexed">Dizine eklenmiş 44 asıl sayfa</option><option value="parameter">15 form parametresi</option></select></label></div>'
            '<p id="indexCount" role="status" aria-live="polite">123 adres gösteriliyor</p><button type="button" id="indexOpen">Görünenleri aç</button><button type="button" id="indexClose">Kapat</button><noscript><p>Arama için JavaScript gerekir. Başlıkları tek tek açabilir veya tarayıcınızın sayfada bul özelliğini kullanabilirsiniz.</p></noscript>'
            + ''.join(rows) + '<h2>Bu karşılaştırmanın sınırı</h2><p>Gelen sayfa sayımı, rapor ve doğrulama dosyaları dışındaki kök HTML sayfalarında bulunan bağlantıların farklı kaynak sayfa sayısıdır. Bu bir Google bağlantı puanı değildir. Kontroller üretim dosyalarına aittir; GitHub önizlemesi ayrıca noindex tutulur ve PHP gönderimleri orada kapalıdır.</p>'
            '<p>11 yabancı pazar model rehberinin noindex tercihi korunur; kapsamı farklı Termodinamik elektrikli kombi sayfası ayrıca değerlendirilir. Kod tablolarını başka bir modelin açıklamasıyla genişletmek indeksleme çözümü değildir. Canlı kurulumdan sonra Search Console’da neden, son tarama ve seçilen canonical ayrı denetlenmelidir.</p>'
            '<footer>İnceleme: 29 Ekim 2026. Kaynak a1.zip SHA-256: <code>' + escape(evidence['input_archive_sha256']) + '</code>. Bu inceleme sayfası arama dizinine kapalıdır.</footer><script>' + script + '</script></main></body></html>')
    files['dizin-inceleme.html'] = text.encode('utf-8')
    return {'content_urls': 108, 'indexed_user_list': 44, 'not_indexed_user_list': 64,
            'parameter_urls': 15, 'report': 'dizin-inceleme.html', 'index_status_source': 'user-supplied-list-not-live'}
