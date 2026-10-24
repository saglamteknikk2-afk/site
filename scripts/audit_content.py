#!/usr/bin/env python3
"""Review built MAIN content; shared modules are evidence, not a spam score."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

MIN_WORDS = 20
VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
HIDDEN = {'nav','header','footer','script','style','form','table','noscript'}
BLOCK = {'main','section','article','aside','div','p','h1','h2','h3','h4','h5','h6','li','ul','ol','details','summary','br','blockquote'}

def normalized(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

def words(text: str) -> list[str]:
    return re.findall(r'\w+', text.casefold())

def module_kind(frames: list[dict]) -> str:
    attrs=' '.join(f['attrs'] for f in frames).lower()
    if any(token in attrs for token in ['fault-scope','scope-note','scope-notes','source-note','editorial-source','brand-note','coverage']): return 'source_scope'
    if any(token in attrs for token in ['review','yorum']): return 'review'
    if any(token in attrs for token in ['safety','emergency','advisory']): return 'safety'
    if any(token in attrs for token in ['page-cta','service-cta','contact-cta','eyebrow','breadcrumb']): return 'navigation_cta'
    return 'body'

class MainContent(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[]; self.paragraphs=[]; self.main_text=[]; self.links=[]; self.metadata=defaultdict(list)
        self.active=None; self.title=False; self.h1=False; self.ld=False; self.buffer=[]; self.schemas=[];self.main_seen=False
    def handle_starttag(self, tag, pairs):
        a=dict(pairs)
        if tag=='main': self.main_seen=True
        if tag=='title': self.title=True
        if tag=='meta' and a.get('name','').lower() in {'description','robots'}: self.metadata[a['name'].lower()].append(a.get('content',''))
        if tag=='link' and 'canonical' in (a.get('rel') or '').lower().split(): self.metadata['canonical'].append(a.get('href',''))
        if tag=='script' and a.get('type')=='application/ld+json': self.ld=True; self.buffer=[]
        parent=self.stack[-1] if self.stack else {'main':False,'hidden':False}
        frame={'tag':tag,'main':parent['main'] or tag=='main','hidden':parent['hidden'] or tag in HIDDEN,'attrs':' '.join(str(a.get(k) or '') for k in ['class','id','role'])}
        if tag not in VOID: self.stack.append(frame)
        if frame['main'] and not frame['hidden']:
            if tag in BLOCK: self.main_text.append(' ')
            if tag=='h1': self.h1=True
            if tag=='a' and a.get('href'): self.links.append(a['href'])
            if tag=='p' and self.active is None: self.active={'text':[],'linked':[],'category':module_kind(self.stack),'depth':len(self.stack)}
    def handle_data(self, text):
        if self.title: self.metadata['title'].append(text)
        if self.ld: self.buffer.append(text)
        if not self.stack or not self.stack[-1]['main'] or self.stack[-1]['hidden']: return
        self.main_text.append(text)
        if self.h1: self.metadata['h1'].append(text)
        if self.active:
            self.active['text'].append(text)
            if any(f['tag']=='a' for f in self.stack): self.active['linked'].append(text)
    def handle_endtag(self, tag):
        if tag in BLOCK and self.stack and self.stack[-1]['main'] and not self.stack[-1]['hidden']: self.main_text.append(' ')
        if tag=='title': self.title=False
        if tag=='h1': self.h1=False
        if tag=='script' and self.ld:
            try: self.schemas.append(json.loads(''.join(self.buffer)))
            except ValueError: self.metadata['invalid_jsonld'].append('invalid JSON')
            self.ld=False
        if tag=='p' and self.active:
            item=self.active; self.active=None
            text=normalized(''.join(item['text'])); count=len(words(text))
            category=item['category']
            if count and len(words(' '.join(item['linked'])))/count>.6: category='navigation_cta'
            self.paragraphs.append({'text':text,'words':count,'category':category})
        for index in range(len(self.stack)-1,-1,-1):
            if self.stack[index]['tag']==tag:
                del self.stack[index:]; break

def walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values(): yield from walk(child)
    elif isinstance(value,list):
        for child in value: yield from walk(child)

def load_catalog(root: Path) -> tuple[dict, list[str], set[str], set[str]]:
    def read(name):
        path=root/'assets'/name
        return json.loads(path.read_text()) if path.is_file() else {}
    faults=read('verified-faults.json'); catalog=read('servis-katalog.json'); models=defaultdict(list)
    for model in faults.get('models',[]): models[Path(model['path']).name].append(model)
    entities=set(); districts=set(); brands=set()
    for row in faults.get('coverage',[]):
        if isinstance(row.get('brand'),str): brands.add(row['brand']);entities.add(row['brand'])
    for key in ['districts','neighborhoods','localities','brands']:
        group=catalog.get(key,[])
        for row in walk(group):
            name=row.get('name')
            if isinstance(name,str) and len(name)>2:
                entities.add(name)
                if key=='districts': districts.add(name)
                if key=='brands': brands.add(name)
        if isinstance(group,list):
            names={v for v in group if isinstance(v,str) and len(v)>2};entities.update(names)
            if key=='districts': districts.update(names)
            if key=='brands': brands.update(names)
    def slug(value): return value.translate(str.maketrans('çğıöşüÇĞİÖŞÜ','cgiosuCGIOSU')).lower().replace(' ','-')
    return models,sorted(entities,key=lambda v:(-len(v),v)),{slug(v) for v in districts},{slug(v) for v in brands}

def page_kind(name: str, models: dict, districts: set[str], brands: set[str]) -> str:
    if name in models: return 'model_guide'
    if name=='index.html': return 'home'
    if name in {'404.html','servis-sec.html'}: return 'system_tool'
    if name in {'bolgeler.html','markalar.html','model-ariza-kodlari.html','ariza-rehberi.html','hizmetler.html'}: return 'directory'
    match=re.match(r'(.+)-(kombi|klima)-servisi\.html$',name)
    if match and match[1] in districts: return 'district_service'
    if match and match[1] in brands: return 'brand_service'
    if name.endswith('-servisi.html') and not match and name not in {'kombi-servisi.html','klima-servisi.html'}: return 'locality_service'
    if name in {'hakkimizda.html','isletme-bilgileri.html','kaynak-ve-yayin-ilkeleri.html','aydinlatma.html','iletisim.html'}: return 'business_policy'
    return 'service_guide'

def audit(root: Path) -> dict:
    models,entities,districts,brands=load_catalog(root)
    entity_re=re.compile(r'(?<!\w)(?:'+'|'.join(re.escape(v.casefold()) for v in entities)+r')(?!\w)') if entities else None
    exact=defaultdict(list); parsed={}; pages=[]; main_exact=defaultdict(list); metadata_groups=defaultdict(lambda:defaultdict(list))
    for path in sorted(root.rglob('*.html')):
        if path.name=='owner-admin.html' or re.match(r'(google|yandex_).*\.html$',path.name): continue
        name=path.relative_to(root).as_posix(); parser=MainContent(); source=path.read_text(); parser.feed(source)
        kind=page_kind(path.name,models,districts,brands); substantial=[]
        for i,p in enumerate(parser.paragraphs):
            if p['words']<MIN_WORDS: continue
            item={**p,'index':i}
            if 'başvurulan kaynaktır; belediye ile servis firması' in p['text'].casefold(): item['category']='source_scope'
            if kind=='directory' and item['category']=='body': item['category']='navigation_cta'
            if kind=='model_guide' and item['category']=='body': item['category']='model_context'
            substantial.append(item); exact[p['text'].casefold()].append({'page':name,'index':i,'category':item['category']})
        body=[p for p in substantial if p['category']=='body']
        prose=normalized(' '.join(p['text'] for p in body)); text=normalized(''.join(parser.main_text))
        expected=sorted({m.get('manual',{}).get('url','') for m in models.get(path.name,[])}-{''})
        missing=[url for url in expected if url not in parser.links]
        faq=[]
        for schema in parser.schemas:
            for obj in walk(schema):
                if obj.get('@type')=='Question':
                    for label,value in [('question',obj.get('name','')),('answer',obj.get('acceptedAnswer',{}).get('text',''))]:
                        visible=MainContent();visible.feed('<main>'+str(value)+'</main>')
                        plain=normalized(''.join(visible.main_text))
                        if plain and plain not in text: faq.append({'field':label,'excerpt':plain[:160]})
        row={'path':name,'kind':kind,'main_present':parser.main_seen,'main_words':len(words(text)),'body_substantive_words':len(words(prose)),'substantive_paragraphs':len(substantial),'body_substantive_paragraphs':len(body),'paragraph_categories':dict(Counter(p['category'] for p in substantial)),'metadata':{k:normalized(' '.join(v)) if k in {'title','h1'} else v for k,v in parser.metadata.items()},'source_links':sorted({u for u in parser.links if urlsplit(u).scheme in {'http','https'} and urlsplit(u).hostname not in {'wa.me','saglamkombiklima.com.tr'}}),'expected_manual_urls':expected,'missing_manual_links':missing,'faq_visible_mismatches':faq,'claim_mentions':[m.group(0) for m in re.finditer(r'\b40\s*(?:dk|dakika)|\b1\s*yıl|\bMYK\b',text,re.I)]}
        for key in ['title','description','canonical']:
            values=row['metadata'].get(key,[]); values=[values] if isinstance(values,str) else values
            for value in values:
                if value: metadata_groups[key][value].append(name)
        parsed[name]={'row':row,'substantial':substantial,'body':prose}
        if text: main_exact[text.casefold()].append(name)
        pages.append(row)
    duplicate_groups=[]
    for key,uses in sorted(exact.items()):
        if len(uses)<2: continue
        categories={u['category'] for u in uses}; pages_used={u['page'] for u in uses}
        classification='editorial_review' if sum(u['category']=='body' for u in uses)>1 else 'shared_documented_context' if categories=={'model_context'} else 'shared_module'
        duplicate_groups.append({'id':hashlib.sha256(key.encode()).hexdigest()[:12],'words':len(words(key)),'excerpt':key[:220],'classification':classification,'occurrences':uses,'cross_page':len(pages_used)>1})
    for name,item in parsed.items():
        item['row']['unique_body_substantive_paragraphs']=sum(len(exact[p['text'].casefold()])==1 for p in item['substantial'] if p['category']=='body')
    def shingles(text):
        tokens=words(text)
        return {tuple(tokens[i:i+5]) for i in range(len(tokens)-4)}
    def score(a,b): return len(a&b)/len(a|b) if a and b else 0
    vectors={name:(shingles(p['body']),shingles(entity_re.sub('entity',p['body'].casefold()) if entity_re else p['body'])) for name,p in parsed.items() if len(words(p['body']))>=40 and p['row']['kind'] not in {'model_guide','directory','system_tool'}}
    near=[]; names=sorted(vectors)
    for i,left in enumerate(names):
        for right in names[i+1:]:
            raw=score(vectors[left][0],vectors[right][0]); masked=score(vectors[left][1],vectors[right][1])
            if raw>=.65 or masked>=.75: near.append({'pages':[left,right],'raw_5word_jaccard':round(raw,4),'entity_masked_5word_jaccard':round(masked,4),'classification':'editorial_review'})
    body_clones=defaultdict(list);violations=[]
    if not pages: violations.append({'reason':'no_visitor_pages'})
    for name,item in parsed.items():
        row=item['row']
        if not row['main_present']: violations.append({'page':name,'reason':'missing_main'})
        if row['missing_manual_links']: violations.append({'page':name,'reason':'missing_manual_link'})
        if row['faq_visible_mismatches']: violations.append({'page':name,'reason':'faq_visible_mismatch'})
        if row['metadata'].get('invalid_jsonld'): violations.append({'page':name,'reason':'invalid_jsonld'})
        if row['body_substantive_words']>=80 and row['kind'] not in {'model_guide','directory','system_tool'}:
            body_clones[item['body'].casefold()].append(name)
    for used in body_clones.values():
        if len(used)>1: violations.append({'pages':used,'reason':'exact_editorial_body_clone'})
    return {'schema_version':1,'methodology':{'scope':'Visitor HTML MAIN only; no network requests. Scripts, forms, tables, navigation, headers and footers excluded. Paragraphs under the internal word threshold remain counted in MAIN words.','substantive_min_words':MIN_WORDS,'near_repeat':'Five-word shingle Jaccard on substantive body prose; raw >=0.65 or entity-masked >=0.75. Model documents and directories excluded from body-pair scoring. Entities come from the local catalog.','strict':'Fails only missing MAIN, missing expected model-manual link, invalid JSON-LD, FAQ/visible-text mismatch, or exact editorial body clones of at least80 words. Shared modules, near-repeat signals and individual repeated paragraphs require editorial review; they do not fail strict mode.','limitations':'These are editorial review signals, not Google/Yandex/AI scores, indexing predictions or proof of spam. Unique wording alone does not establish usefulness or factual accuracy. Shared safety, navigation, sources and documented model context may be necessary.'},'summary':{'pages':len(pages),'kinds':dict(Counter(p['kind'] for p in pages)),'editorial_duplicate_groups':sum(g['classification']=='editorial_review' for g in duplicate_groups),'shared_duplicate_groups':sum(g['classification']!='editorial_review' for g in duplicate_groups),'near_repeat_pairs':len(near),'missing_manual_link_pages':sum(bool(p['missing_manual_links']) for p in pages),'faq_mismatch_pages':sum(bool(p['faq_visible_mismatches']) for p in pages),'strict_violations':len(violations)},'pages':pages,'exact_duplicate_groups':duplicate_groups,'exact_main_groups':[v for v in main_exact.values() if len(v)>1],'near_repeat_pairs':near,'strict_violations':violations,'duplicate_metadata':{key:[{'value':value,'pages':used} for value,used in values.items() if len(used)>1] for key,values in metadata_groups.items()}}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--report',type=Path);p.add_argument('--strict',action='store_true');a=p.parse_args()
    report=audit(a.directory.resolve())
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report['summary'],ensure_ascii=False,indent=2))
    else: print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(1 if a.strict and report['strict_violations'] else 0)

if __name__=='__main__': main()
