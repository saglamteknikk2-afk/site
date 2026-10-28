"""Independent brand and symptom guides; preserve the original model code tables.

All copy is authored in source JSON and rendered into HTML at build time. The
catalogue lists actual available document scopes, never claims every model of a
brand is documented, and never transfers a code meaning between models.
"""
from html import escape
from pathlib import Path
import json
import re

from editorial_regions import Ranges, replace_element, _body, link
from hubs import norm, route, indexable, model_local

ROOT = Path(__file__).resolve().parent
BRANDS = {
    'kombi': ['ariston', 'baymak', 'bosch', 'buderus', 'demirdokum', 'eca', 'vaillant', 'viessmann'],
    'klima': ['arcelik', 'baymak', 'beko', 'daikin', 'lg', 'mitsubishi-electric',
              'mitsubishi-heavy-industries', 'samsung'],
}
SYMPTOMS = {
    'klima-calismiyor.html', 'klima-hata-kodu.html', 'klima-isitmiyor.html',
    'klima-koku-yapiyor.html', 'kombi-atesleme.html', 'kombi-bakimi.html',
    'kombi-basinci.html', 'kombi-calismiyor.html', 'kombi-sesli-calisiyor.html',
    'kombi-sicak-su.html', 'kombi-su-akitiyor.html', 'petek-temizligi.html',
    'kombi-hata-kodu.html',
}
EXPECTED = SYMPTOMS | {b+'-'+kind+'-servisi.html' for kind, brands in BRANDS.items() for b in brands}


def load_services():
    rows = []
    for source in sorted((ROOT/'data/service-editorial').glob('*.json')):
        rows.extend(json.loads(source.read_text())['pages'])
    if len(rows) != len(EXPECTED) or {p['route'] for p in rows} != EXPECTED:
        raise ValueError('All 16 brand and 13 symptom/service narratives are required.')
    return {p['route']: p for p in rows}


def _models(page, models, files):
    if page.get('type') == 'brand':
        candidates = [m for m in models if m['device'] == page['device']
                      and norm(m['brand']) == norm(page['brand'])]
        heading = page['brand']+' için kayıtlı model belgeleri'
    elif page['route'] in {'kombi-hata-kodu.html', 'klima-hata-kodu.html'}:
        candidates = [m for m in models if m['device'] == page['device']]
        heading = 'Model belgesine göre kod tablosu seçin'
    else:
        return ''
    rows = []; seen = set(); out_of_scope = []
    for m in candidates:
        path = route(m.get('path'))
        if path in seen: continue
        seen.add(path)
        label = m['brand']+' '+m['label']
        if path not in files or not indexable(files[path].decode()):
            out_of_scope.append(label)
            continue
        scope = str(m.get('market') or 'Belgenin kapsamını kontrol edin')
        status = 'Türkiye kapsamı kayıtlı' if model_local(m, files) else 'Ülke, ürün son eki ve kontrolcü kapsamı ayrıca eşleştirilmeli'
        rows.append('<li><strong>'+escape(label)+'</strong><span>'+escape(scope)+' · '+escape(status)
                    +'</span>'+link(path+'#kodlar', 'Bu model belgesinin kod tablosu', files)+'</li>')
    note = ('<p>Türkiye kapsamıyla eşleştirilmeyen '+str(len(out_of_scope))
            +' kayıt bu listede teknik yanıt olarak sunulmuyor. Cihazınız burada yoksa '
            'model seçmeden belirtiyle ilerleyebilir veya model adını kendiniz yazabilirsiniz.</p>') if out_of_scope else ''
    if not rows:
        note = '<p>Bu markanın Türkiye cihazları için yayıma uygun, eşleşmiş bir kod belgesi bu katalogda bulunmuyor. Marka ve belirtiyle destek isteyebilirsiniz; başka ülkeye ait bir kod tablosunu cihazınıza uyarlamıyoruz.</p>'
    return ('<section id="st-brand-models" class="editorial-model-catalog"><h2>'+escape(heading)
            +'</h2><p>Bu bir üreticinin tüm modellerinin listesi değildir; sitede kayıtlı kaynak belgeleri gösterir. '
            'Kod açıklaması, açtığınız tablonun model ve ürün kapsamıyla birlikte okunmalıdır.</p>'
            +('<ul class="editorial-model-list">'+''.join(rows)+'</ul>' if rows else '')+note
            +'<p>'+link('model-ariza-kodlari.html', 'Diğer markalar ve model belgeleri', files)+'</p></section>')


def apply_services(files):
    pages = load_services()
    models = json.loads(files['assets/verified-faults.json'])['models']
    changed = []
    for name, page in pages.items():
        text = files[name].decode()
        # Source brand directories sit outside at-content. Replace that directory
        # with the scoped catalogue below instead of retaining a second ID/list.
        old_directories=[n for n in Ranges(text).nodes if n['attrs'].get('data-st-link-directory')=='brand-models']
        for _ in old_directories:
            text=replace_element(text,lambda n:n['attrs'].get('data-st-link-directory')=='brand-models','')
        from semantics import Page
        document=Page(text)
        simple_title=document.title()+' | Sağlam Teknik'
        text=re.sub(r'<title>.*?</title>',lambda _: '<title>'+escape(simple_title)+'</title>',text,count=1,flags=re.S)
        text=re.sub(r'(<meta\s+property="og:title"\s+content=")[^"]*(">)',
                    lambda m:m[1]+escape(simple_title,quote=True)+m[2],text)
        target = next(n for n in Ranges(text).nodes if n['tag'] == 'div'
                      and 'at-content' in n['attrs'].get('class', '').split())
        old = text[target['start']:target['end']]
        old_ids = set(re.findall(r'\bid=["\']([^"\']+)', old))
        main = ('<section class="editorial-service" data-editorial-route="'+escape(name, quote=True)
                +'" data-service-device="'+page['device']+'"><header class="editorial-opening"><h2>'
                +escape(page['headline'])+'</h2></header><div data-editorial-service-selector></div>'
                +_body(page, files)+_models(page, models, files))
        ids = set(re.findall(r'\bid="([^"]+)"', main))
        aliases = ''.join('<span class="editorial-anchor" aria-hidden="true" id="'
                          +escape(ident, quote=True)+'"></span>' for ident in sorted(old_ids-ids))
        main += (aliases+'<section class="editorial-cta"><h2>'+escape(page['cta']['heading'])
                 +'</h2><p>'+escape(page['cta']['text'])+'</p><div class="at-actions">'
                 '<a class="at-btn at-btn-primary" href="tel:05346225515">Ustamızı ara</a>'
                 '<a class="at-btn" href="./#ai-usta">AI Usta ile ilerle</a></div></section></section>')
        text = replace_element(text, lambda n: n['tag']=='div' and 'at-content' in n['attrs'].get('class','').split(), main, True)
        text, count = re.subn(r'<p\b(?=[^>]*class="[^"]*\bat-lead\b)[^>]*>.*?</p>',
                             lambda _: '<p class="at-lead">'+escape(page['lead'])+'</p>', text, count=1, flags=re.S)
        if count != 1: raise ValueError('Missing service hero lead: '+name)
        aside = ('<aside class="at-aside editorial-aside"><p class="at-eyebrow">Sağlam Teknik</p><h2>'
                 +escape(page['cta']['heading'])+'</h2><p>'+escape(page['cta']['text'])+'</p>'
                 '<a class="at-btn at-btn-primary" href="tel:05346225515">0534 622 55 15</a>'
                 '<nav class="at-toc" aria-label="Bu sayfada">'
                 +''.join('<a href="#'+escape(s['id'], quote=True)+'">'+escape(s['heading'])+'</a>' for s in page['sections'])
                 +'</nav></aside>')
        text = replace_element(text, lambda n: n['tag']=='aside' and 'at-aside' in n['attrs'].get('class','').split(), aside)
        text = re.sub(r'(<meta\s+(?:name="description"|property="og:description")\s+content=")[^"]*(">)',
                      lambda m: m[1]+escape(page['description'], quote=True)+m[2], text)
        text = text.replace('</head>', '<link rel="stylesheet" href="assets/editorial.css"></head>', 1)
        files[name] = text.encode(); changed.append(name)
    css = files['assets/editorial.css'].decode()
    css += '\n.editorial-model-list{list-style:none;padding:0;display:grid;gap:12px}.editorial-model-list li{padding:16px;border:1px solid #bac7ad;border-radius:8px;overflow-wrap:anywhere}.editorial-model-list strong,.editorial-model-list span{display:block}.editorial-model-list span{font-size:14px;margin:6px 0}.editorial-service .editorial-body{margin-top:32px}\n'
    files['assets/editorial.css'] = css.encode()
    return {'brand_pages':16, 'symptom_service_pages':13, 'routes':sorted(changed),
            'legacy_main_bodies_replaced':len(changed), 'model_code_tables_changed':0,
            'source_directory':'hybrid/data/service-editorial/'}


def audit_services(files, strict=True):
    from editorial_audit import audit_pages, verify_rendered, _source_context
    from editorial_regions import load_editorial
    source, _, brands = _source_context()
    extra = list(load_services().values())
    pages = list(load_editorial().values())+extra
    result = audit_pages(pages, source, files, brands, strict=False, extra_routes=extra)
    rendered = verify_rendered(pages, files)
    result['rendered'] = rendered
    result['errors'].extend(rendered['errors'])
    result['status'] = 'passed' if not result['errors'] else 'failed'
    if result['errors'] and strict:
        raise ValueError('Combined editorial regression: '+json.dumps(result['errors'][:5],ensure_ascii=False))
    return result
