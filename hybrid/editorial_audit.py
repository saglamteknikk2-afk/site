"""Detect recycled editorial bodies before publishing a regional content release.

These checks are regression guards for the site's own prose.  They do not
measure a Google threshold, prove factual correctness, or certify originality.
Shared navigation, source tables, and short safety facts are not compared here.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit
import argparse
import itertools
import json
import re
import statistics
import zipfile

ROOT = Path(__file__).resolve().parent
WORD = re.compile(r"[a-z0-9]+")


def normalize(value):
    value = str(value).translate(str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosuCGIOSU')).lower()
    return ' '.join(WORD.findall(value))


def _masker(data, brands=()):
    names = {'İstanbul', 'Avrupa Yakası', 'Sağlam Teknik', *brands}
    for row in data.get('districts', []):
        names.add(row['name'])
        names.update(row.get('neighborhoods', []))
    for row in data.get('localities', []):
        names.add(row['name'])
    terms = sorted({normalize(name) for name in names if normalize(name)}, key=len, reverse=True)
    pattern = re.compile(r'(?<![a-z0-9])(?:' + '|'.join(re.escape(n) for n in terms) + r')(?![a-z0-9])')
    return lambda text: pattern.sub('yer', normalize(text))


def _source_context():
    data = json.loads((ROOT/'data/regions.json').read_text())
    archive = ROOT.parent/'saglamkombiklima-seo.zip'
    files = {}; brands = []
    if archive.exists():
        with zipfile.ZipFile(archive) as z:
            files = {name: b'' for name in z.namelist() if not name.endswith('/')}
            text = z.read('assets/brand-registry.js').decode()
            match = re.search(r'window\.ST_BRAND_REGISTRY\s*=\s*(\{.*?\});', text, re.S)
            if match:
                registry = json.loads(match[1])
                for row in registry.get('brands', []):
                    brands.append(row['name']); brands.extend(row.get('aliases', []))
    return data, files, brands


def load_pages(data_dir=None):
    pages = []
    for path in sorted(Path(data_dir or ROOT/'data/editorial').glob('batch-*.json')):
        record = json.loads(path.read_text())
        if not isinstance(record, dict) or not isinstance(record.get('pages'), list):
            raise ValueError('Expected editorial pages list: ' + path.name)
        pages.extend(record['pages'])
    return pages


def prose(page):
    """Yield author-written blocks, excluding link labels and schema/UI strings."""
    for field in ('lead', 'neighborhood_intro'):
        if page.get(field): yield field, str(page[field])
    for i, section in enumerate(page.get('sections', [])):
        for j, text in enumerate(section.get('paragraphs', [])):
            yield f'section-{i+1}-paragraph-{j+1}', str(text)
        for j, text in enumerate(section.get('bullets', [])):
            yield f'section-{i+1}-bullet-{j+1}', str(text)
    for i, row in enumerate(page.get('faqs', [])):
        if row.get('answer'):yield f'faq-{i+1}', str(row['answer'])
    if page.get('cta', {}).get('text'):yield 'cta', str(page['cta']['text'])


def _grams(text, n=5):
    words = text.split()
    return {' '.join(words[i:i+n]) for i in range(max(0, len(words)-n+1))}


def audit_editorial(pages=None, files=None, strict=True, data_dir=None):
    source, source_files, brands = _source_context()
    pages = load_pages(data_dir) if pages is None else list(pages)
    result=audit_pages(pages, source, source_files if files is None else files, brands, strict=False)
    if files is not None:
        rendered=verify_rendered(pages,files)
        result['rendered']=rendered
        result['errors'].extend(rendered['errors'])
        result['status']='passed' if not result['errors'] else 'failed'
    if result['errors'] and strict:
        raise ValueError('Editorial content regression: '+json.dumps([{'kind':e['kind'],'page':e.get('page')} for e in result['errors'][:8]],ensure_ascii=False))
    return result


def verify_rendered(pages,files):
    """Ensure the authored bodies, not just the data/lead, reached visible HTML."""
    try:
        from .semantics import Page
    except ImportError:
        from semantics import Page
    errors=[];rendered=0;paragraphs=0;faq=0
    for page in pages:
        route=page.get('route','')
        if route not in files:
            errors.append({'kind':'missing_rendered_editorial_page','page':route});continue
        document=Page(files[route].decode('utf-8'))
        markers=[e for e in document.root.all() if e.attrs.get('data-editorial-route')==route]
        if len(markers)!=1:
            errors.append({'kind':'rendered_editorial_marker_count','page':route,'count':len(markers)});continue
        bodies=[e for e in markers[0].all('article') if 'editorial-body' in e.attrs.get('class','').split()]
        if len(bodies)!=1:
            errors.append({'kind':'rendered_editorial_body_count','page':route,'count':len(bodies)});continue
        body=bodies[0];visible=normalize(body.text())
        for section in page.get('sections',[]):
            heading=normalize(section.get('heading',''))
            if heading and heading not in visible:
                errors.append({'kind':'authored_section_not_rendered','page':route,'section':section.get('id')})
            for paragraph in section.get('paragraphs',[]):
                paragraphs+=1
                if normalize(paragraph) not in visible:
                    errors.append({'kind':'authored_paragraph_not_rendered','page':route,'section':section.get('id')})
        for item in page.get('faqs',[]):
            faq+=1
            if normalize(item.get('question','')) not in visible or normalize(item.get('answer','')) not in visible:
                errors.append({'kind':'authored_faq_not_rendered','page':route})
        old=[e for e in document.root.all() if 'at-summary' in e.attrs.get('class','').split()
             or 'hybrid-region-note' in e.attrs.get('class','').split() or 'data-st-master-matrix' in e.attrs]
        if old:errors.append({'kind':'old_recycled_region_block_retained','page':route,'count':len(old)})
        rendered+=1
    return {'pages_checked':len(pages),'rendered_bodies':rendered,'authored_section_paragraphs_checked':paragraphs,
            'authored_faq_answers_checked':faq,'errors':errors}


def audit_pages(pages, source, files=None, brands=(), strict=True, extra_routes=()):
    """Core entry point also accepts bounded fixtures for meaningful regression tests."""
    errors = []; warnings = []; claim_disclaimers = []; by_route = {}; blocks = []; headings = defaultdict(list)
    expected = {}
    for row in source.get('districts', []):
        for device in ('kombi', 'klima'):
            expected[row['slug']+'-'+device+'-servisi.html'] = (row, device)
    for row in source.get('localities', []):
        expected[row['slug']+'-servisi.html'] = (row, 'mixed')
    for page in extra_routes:
        expected[page['route']] = (page, page.get('device', 'mixed'))
    counts = Counter(page.get('route') for page in pages)
    for route, count in counts.items():
        if count != 1:errors.append({'kind':'duplicate_editorial_route', 'page':route, 'count':count})
    missing = sorted(set(expected)-set(counts)); extra = sorted(set(counts)-set(expected))
    if missing:errors.append({'kind':'missing_editorial_routes', 'pages':missing})
    if extra:errors.append({'kind':'unexpected_editorial_routes', 'pages':extra})
    masked = _masker(source, brands)
    exact_paragraphs = defaultdict(list); sentences = defaultdict(list); page_grams = {}
    for page in pages:
        route = page.get('route','')
        if route not in expected:continue
        row, device = expected[route]
        all_blocks = list(prose(page)); full_text = ' '.join(t for _,t in all_blocks)
        body_words = len(normalize(full_text).split())
        if body_words < 220:errors.append({'kind':'insubstantial_editorial_body','page':route,'words':body_words})
        if body_words > 650:warnings.append({'kind':'long_editorial_body_review','page':route,'words':body_words})
        if len(page.get('sections', [])) < 3:errors.append({'kind':'missing_substantive_sections','page':route})
        local_ids = []
        for i, section in enumerate(page.get('sections', [])):
            local_ids.append(section.get('id',''))
            section_text = ' '.join(section.get('paragraphs', [])+section.get('bullets', []))
            if len(normalize(section_text).split()) < 25:
                errors.append({'kind':'thin_editorial_section','page':route,'section':i+1})
            heading = section.get('heading','')
            if len(normalize(heading).split()) >= 5:headings[masked(heading)].append((route,'section-'+str(i+1),heading))
            for link in section.get('links', []):
                path = str(link.get('path','')); parsed = urlsplit(path)
                if parsed.scheme or parsed.netloc:
                    errors.append({'kind':'external_editorial_link','page':route,'target':path});continue
                target = unquote(parsed.path).lstrip('/')
                if target and files is not None and target not in files:
                    errors.append({'kind':'missing_editorial_link','page':route,'target':path})
        if not all(local_ids) or len(set(local_ids)) != len(local_ids):
            errors.append({'kind':'invalid_editorial_section_ids','page':route})
        if len(page.get('faqs', [])) < 2:errors.append({'kind':'missing_page_faq','page':route})
        for i, faq in enumerate(page.get('faqs', [])):
            question = faq.get('question','')
            if len(normalize(question).split()) >= 5:headings[masked(question)].append((route,'faq-'+str(i+1),question))
            if not question or not faq.get('answer'):errors.append({'kind':'empty_page_faq','page':route})
        if not page.get('headline') or not page.get('lead'):
            errors.append({'kind':'missing_editorial_entry','page':route})
        if len(normalize(page.get('headline','')).split()) >= 4:
            headings[masked(page['headline'])].append((route,'headline',page['headline']))
        for location, text in all_blocks:
            normalized = masked(text); words = len(normalized.split())
            if words >= 18:
                exact_paragraphs[normalized].append({'page':route,'block':location,'text':text})
            if words >= 40:blocks.append((route,location,text,normalized,_grams(normalized)))
            for sentence in re.split(r'(?<=[.!?])\s+', text):
                normalized_sentence = masked(sentence)
                if len(normalized_sentence.split()) >= 14:
                    sentences[normalized_sentence].append({'page':route,'block':location,'text':sentence})
        page_grams[route] = _grams(masked(full_text))
        by_route[route]={'device':device,'words':body_words,'sections':len(page.get('sections', [])),
                         'faq':len(page.get('faqs', [])),'authored_paragraphs':len(all_blocks),'focus':page.get('focus','')}
        claim_patterns = {
            'unsubstantiated_frequency':r'(?i)(?:en\s+sık|çok\s+sık|sık\s+görülen|yaygın\s+arız|daha\s+çok\s+arız)',
            'unsubstantiated_local_stock':r'(?i)(?:yapılar(?:ın)?\s+çoğu|binalar(?:ın)?\s+çoğu|yoğun\s+eski\s+yap|bölgenin\s+sert\s+suyu)',
            'unsubstantiated_promise':r'(?i)(?:\d+\s*dakikada\s+(?:gel|var)|kesin\s+(?:çöz|teşhis)|aynı\s+gün\s+garanti)',
        }
        for kind, pattern in claim_patterns.items():
            for match in re.finditer(pattern,full_text):
                # A clear refusal to promise a diagnosis is not a diagnosis promise.
                tail=full_text[match.end():match.end()+75]
                if kind=='unsubstantiated_promise' and re.search(r'(?i)(?:söylenmez|verilmez|verilmemelidir|konulamaz|oluşturmaz)',tail):
                    claim_disclaimers.append({'page':route,'kind':'explicit_limit_on_remote_diagnosis'})
                else:warnings.append({'kind':kind,'page':route,'review_required':True})
    repeats = [values for values in exact_paragraphs.values() if len({v['page'] for v in values})>1]
    for values in repeats:
        errors.append({'kind':'repeated_editorial_paragraph_after_location_mask','occurrences':values})
    sentence_repeats = [values for values in sentences.values() if len({v['page'] for v in values})>1]
    for values in sentence_repeats:
        errors.append({'kind':'repeated_long_editorial_sentence_after_location_mask','occurrences':values})
    for values in headings.values():
        if len({v[0] for v in values})>1:
            errors.append({'kind':'repeated_substantive_heading_after_location_mask',
                           'occurrences':[{'page':p,'block':b,'text':t} for p,b,t in values]})
    near = []
    for a,b in itertools.combinations(blocks,2):
        if a[0] == b[0] or a[3] == b[3] or not a[4] or not b[4]:continue
        overlap = len(a[4]&b[4])/min(len(a[4]),len(b[4]))
        if overlap >= .65:
            detail={'a':a[0],'a_block':a[1],'b':b[0],'b_block':b[1],'five_word_containment':round(overlap,4),
                    'a_text':a[2],'b_text':b[2]}
            near.append(detail);errors.append({'kind':'near_duplicate_editorial_paragraph',**detail})
    whole_pairs=[]
    for a,b in itertools.combinations(sorted(page_grams),2):
        if by_route[a]['device']!=by_route[b]['device']:continue
        aa=page_grams[a];bb=page_grams[b];union=aa|bb
        score=len(aa&bb)/len(union) if union else 0
        whole_pairs.append({'a':a,'b':b,'five_word_jaccard':round(score,4)})
        if score>=.4:errors.append({'kind':'near_duplicate_editorial_body',**whole_pairs[-1]})
    whole_pairs.sort(key=lambda x:x['five_word_jaccard'],reverse=True)
    report={'scope':'Authored page bodies only; no Google originality, ranking, indexing or factual-certification score',
            'methods':{'entity_mask':'All source district, neighborhood, locality, business and brand names normalized before comparisons',
                       'paragraph_guard':'Exact reuse >=18 words across pages; near reuse >=40 words and >=0.65 five-word containment',
                       'sentence_guard':'Exact reuse >=14 words across pages',
                       'heading_guard':'Exact normalized substantive section headings or FAQ questions >=5 words',
                       'page_guard':'Five-word Jaccard >=0.4 is an internal regression flag, not a search-engine threshold'},
            'expected_pages':len(expected),'pages':len(pages),'per_page':by_route,
            'repeated_long_paragraph_groups':len(repeats),'repeated_long_sentence_groups':len(sentence_repeats),
            'near_duplicate_paragraphs':len(near),'most_similar_pairs':whole_pairs[:15],
            'pair_median_five_word_jaccard':round(statistics.median(p['five_word_jaccard'] for p in whole_pairs),4) if whole_pairs else 0,
            'explicit_claim_disclaimers':claim_disclaimers,
            'warnings':warnings,'errors':errors,'status':'passed' if not errors else 'failed'}
    if errors and strict:
        raise ValueError('Editorial content regression: '+json.dumps([{'kind':e['kind'],'page':e.get('page')} for e in errors[:8]],ensure_ascii=False))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path);p.add_argument('--report',type=Path);args=p.parse_args()
    result=audit_editorial(strict=False,data_dir=args.data_dir)
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in {'per_page','errors'}},ensure_ascii=False,indent=2))
    if result['errors']:raise SystemExit(1)
