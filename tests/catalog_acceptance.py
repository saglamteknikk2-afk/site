"""Audit every registered row against built browser/PHP answers and readable sources.

Structural consistency is deliberately distinct from independent manual research.
"""
from pathlib import Path
import argparse,collections,hashlib,html,json,os,re,subprocess,sys,urllib.parse,xml.etree.ElementTree as ET
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory',type=Path,nargs='?',default=ROOT/'build/production')
parser.add_argument('--report',type=Path,default=ROOT/'build/catalog-acceptance.json')
args=parser.parse_args();SITE=args.directory.resolve()
def load(n):return json.loads((ROOT/n).read_text())
def key(s):return re.sub('[^A-Z0-9]','',str(s).upper())
def norm(s):return re.sub(r'\s+',' ',html.unescape(str(s))).strip()
class P(HTMLParser):
 def __init__(self,t):
  super().__init__(convert_charrefs=True);self.rows={};self.cur=None;self.depth=0;self.links=[];self.ids=[];self.robots=[];self.text=[];self.frames=[];self.unavailable_notes=[];self.feed(t)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  hidden=(self.frames[-1]['hidden'] if self.frames else False) or 'hidden' in a or a.get('aria-hidden')=='true' or bool(re.search(r'(?:display\s*:\s*none|visibility\s*:\s*hidden)',a.get('style',''),re.I))
  note=None
  if 'data-manual-unavailable' in a:
   note={'text':[],'hidden':hidden,'in_closed_details':any(f['tag']=='details' and not f['open'] for f in self.frames)};self.unavailable_notes.append(note)
  if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.frames.append({'tag':tag,'hidden':hidden,'note':note,'open':'open' in a})
  if a.get('id'):self.ids.append(a['id'])
  if tag=='a':self.links.append(a.get('href',''))
  if tag=='meta' and a.get('name','').lower()=='robots':self.robots.append(a.get('content',''))
  if tag=='tr' and a.get('id'):self.cur=a['id'];self.rows.setdefault(self.cur,[])
 def handle_data(self,t):
  self.text.append(t)
  for frame in self.frames:
   if frame['note'] is not None:frame['note']['text'].append(t)
  if self.cur:self.rows[self.cur].append(t)
 def handle_endtag(self,tag):
  if tag=='tr':self.cur=None
  for index in range(len(self.frames)-1,-1,-1):
   if self.frames[index]['tag']==tag:del self.frames[index:];break
v=json.loads((SITE/'assets/verified-faults.json').read_text());b=json.loads((SITE/'assets/brand-registry.json').read_text());organic=json.loads((SITE/'assets/organic-catalog.json').read_text())
errors=[];warnings=[];checks=collections.Counter(); status=collections.Counter();conflicts=[]
built_js=(SITE/'assets/verified-faults.js').read_text();built_js_data=json.loads(re.search(r'window\.ST_VERIFIED_FAULTS\s*=\s*([\s\S]*?);?\s*$',built_js)[1].rstrip(';').strip())
if built_js_data!=v:errors.append('Generated browser verified-faults.js differs from central verified-faults.json')
central=load('overrides/assets/verified-faults.json')
for original,built in zip(central['models'],v['models']):
 original=dict(original,path=original['path'].lstrip('/'))
 if original!=built:errors.append('Built model record differs from reviewed central JSON: '+original['id'])
if len(central['models'])!=len(v['models']):errors.append('Built model count differs from reviewed central JSON')
modelids=[m['id'] for m in v['models']];assert len(modelids)==len(set(modelids))
byid={m['id']:m for m in v['models']}; pages={m['path'].lstrip('/'):P((SITE/m['path'].lstrip('/')).read_text()) for m in v['models']}
def execute(argv):
 result=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,check=True,timeout=60)
 return json.loads(result.stdout)
js_runtime=execute(['node',str(ROOT/'tests/catalog_acceptance.cjs'),str(SITE)])
php_runtime=execute([os.environ.get('SAGLAM_PHP_BIN','php'),str(ROOT/'tests/catalog_acceptance.php'),str(SITE)])
js=js_runtime['rows'];php=php_runtime['rows'];jsmap={(x['model_id'],x['input']):x for x in js};phpmap={(x['model_id'],x['input']):x for x in php}
for m in v['models']:
 mid=m['id'];page=pages[m['path'].lstrip('/')];manual=m['manual'];checks['model_records']+=1
 unavailable=manual.get('source_available') is False
 for field in ['url','title','locator','checked_at','official']:
  if not manual.get(field):errors.append(f'{mid}: missing manual {field}')
 if urllib.parse.urlsplit(manual.get('url','')).scheme!='https':errors.append(f'{mid}: non-https source')
 if unavailable:
  checks['unavailable_model_sources']+=1
  if manual['url'] in page.links:errors.append(f'{mid}: unavailable manual URL remains clickable')
  notes=[n for n in page.unavailable_notes if not n['hidden'] and not n['in_closed_details'] and 'erişilemiyor' in norm(' '.join(n['text'])) and 'otomatik kullanılmaz' in norm(' '.join(n['text']))]
  if len(notes)!=1:errors.append(f'{mid}: expected one visible unavailable-source note, got {len(notes)}')
  if any(c.get('matchable') is not False for c in m['codes']):errors.append(f'{mid}: unavailable source still has automatic code rows')
  if any(g.get('model_id')==mid for g in organic['guides']):errors.append(f'{mid}: unavailable source remains in organic code routes')
  search_models=[row for row in organic.get('models',[]) if row.get('id')==mid]
  if not search_models or any(row.get('code_definitions_verified') or row.get('verified_source') or not row.get('source_unavailable') for row in search_models):errors.append(f'{mid}: organic model incorrectly asserts available verified source')
 elif manual['url'] not in page.links:errors.append(f'{mid}: manual URL absent in HTML')
 for c in m['codes']:
  checks['code_records']+=1
  for field in ['code','meaning','source_locator','safe_observation','anchor']:
   if not c.get(field):errors.append(f'{mid}: code row missing {field}')
  src=c.get('source_url',manual['url']);row=norm(' '.join(page.rows.get(c['anchor'],[])))
  if not row:errors.append(f"{mid}/{c['code']}: anchor not present")
  elif norm(c['meaning']) not in row:errors.append(f"{mid}/{c['code']}: meaning missing/different in table")
  elif norm(c['safe_observation']) not in row:errors.append(f"{mid}/{c['code']}: observation missing/different in table")
  if unavailable and src==manual['url']:
   if src in page.links:errors.append(f"{mid}/{c['code']}: unavailable row source remains clickable")
  elif src not in page.links:errors.append(f"{mid}/{c['code']}: row source link absent")
  if c.get('source_conflict'):conflicts.append({'model_id':mid,'code':c['code'],'note':c.get('conflict_note','')})
  for input_code in [c['code'],*c['equivalent_codes']]:
   available=[x for x in m['codes'] if x.get('matchable') is not False]
   matches=[x for x in available if any(key(z)==key(input_code) for z in [x['code'],*x['equivalent_codes']])]
   expected='code-not-covered' if not matches else 'source-conflict' if len(matches)>1 or matches[0].get('source_conflict') else 'verified'
   for label,lookup in [('js',jsmap),('php',phpmap)]:
    actual=lookup.get((mid,input_code));checks[label+'_exact_inputs']+=1
    if not actual:errors.append(f'{label}: missing result {mid}/{input_code}');continue
    if actual['status']!=expected:errors.append(f'{label}: {mid}/{input_code} {actual["status"]} != {expected}')
    if expected=='verified':
     chosen=matches[0];expectedsource=chosen.get('source_url',manual['url'])
     if actual['meaning']!=chosen['meaning']:errors.append(f'{label}: {mid}/{input_code} wrong definition')
     if actual['source']!='manual' or actual['source_url']!=expectedsource:errors.append(f'{label}: {mid}/{input_code} wrong answer source')
     if chosen['meaning'] not in (actual['text'] or ''):errors.append(f'{label}: {mid}/{input_code} rendered answer omits source meaning')
    elif actual['meaning'] is not None or actual['source']=='manual':errors.append(f'{label}: {mid}/{input_code} unverified meaning asserted')
   status[expected]+=1
   if expected=='verified' and input_code==c['code'] and not any(g.get('model_id')==mid and key(g.get('error_code'))==key(c['code']) and g.get('code_definition_verified') is True and str(g.get('path','')).lstrip('/')==m['path'].lstrip('/')+'#'+c['anchor'] for g in organic['guides']):errors.append(f'organic verified route missing {mid}/{input_code}')
   if jsmap.get((mid,input_code))!=phpmap.get((mid,input_code)):
    # Response prose may differ; model binding, meaning, verification and sources must agree.
    a=jsmap.get((mid,input_code),{});z=phpmap.get((mid,input_code),{})
    if any(a.get(k)!=z.get(k) for k in ['model_id','input','status','code','meaning','source','source_url']):errors.append(f'JS/PHP mismatch: {mid}/{input_code}')
for label,runtime in [('js',js_runtime),('php',php_runtime)]:
 for item in runtime['scope']:
  checks[label+'_scope_guards']+=1
  if item['status']!='needs-model' or item['verified'] or item['meaning'] is not None:errors.append(label+': model scope leaked '+item['model_id']+'/'+item['kind'])
if js_runtime['scope']!=php_runtime['scope']:errors.append('JS/PHP model scope guards disagree')
# Coverage registry links are derived consistently, never brand alias = arbitrary fault alias.
for row in v['coverage']:
 for mid in row.get('verified_model_ids',[]):
  checks['coverage_ids']+=1
  if mid not in byid or any(byid[mid].get(k)!=row[k] for k in ['device','brand']):errors.append(f'bad coverage id {mid}')
for row in organic['guides']:
 if row.get('code_definition_verified'):
  checks['organic_verified_guides']+=1;mid=row.get('model_id');m=byid.get(mid)
  if not m:errors.append(f'organic guide missing model {mid}');continue
  matches=[c for c in m['codes'] if key(c['code'])==key(row['error_code']) and c.get('matchable') is not False and not c.get('source_conflict')]
  if len(matches)!=1:errors.append(f'organic verified guide without unique row {mid}/{row["error_code"]}')
# Foreign URLs: exact11 noindex,follow and excluded sitemap.
foreign_names=load('tests/fixtures/master-request.json')['foreign_slugs'];ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
urls=[n.text for n in ET.parse(SITE/'sitemap.xml').findall('s:url/s:loc',ns)]
foreign=[]
for name in sorted(foreign_names):
 p=pages.get(name) or P((SITE/name).read_text());passed=any('noindex' in x.lower() and 'nofollow' not in x.lower() for x in p.robots) and not any(urllib.parse.urlsplit(u).path=='/'+name for u in urls)
 checks['foreign_noindex_pages']+=1;foreign.append({'path':name,'robots':p.robots,'in_sitemap':any(urllib.parse.urlsplit(u).path=='/'+name for u in urls),'passed':passed})
 if not passed:errors.append('foreign indexing constraint failed: '+name)
unavailable_pages=[]
for name in sorted({m['path'].lstrip('/') for m in v['models'] if m['manual'].get('source_available') is False}):
 p=pages[name];in_sitemap=any(urllib.parse.urlsplit(u).path=='/'+name for u in urls)
 passed=any('noindex' in x.lower() and 'nofollow' not in x.lower() for x in p.robots) and not in_sitemap
 checks['unavailable_source_noindex_pages']+=1;unavailable_pages.append({'path':name,'robots':p.robots,'in_sitemap':in_sitemap,'passed':passed})
 if not passed:errors.append('unavailable source indexing constraint failed: '+name)
isisan=next(r for r in b['brands'] if r['name']=='Isısan')
if isisan.get('kind')!='legacy_supplier' or isisan.get('verified_model_ids',[]):errors.append('Isısan incorrectly asserts verified model scope')
report={
 'schema_version':1,'audit_kind':'structural-and-runtime-catalog-consistency','passed':not errors,
 'production_requests':0,'provider_requests':0,'private_config_read':False,
 'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['overrides/assets/verified-faults.json','overrides/assets/brand-registry.json','overrides/assets/fault-lookup.js','server/fault-catalog.php']},
 'build_info':json.loads((SITE/'build-info.json').read_text()),
 'inventory':{'model_families':len(v['models']),'unique_model_html':len(pages),'code_rows':sum(len(m['codes']) for m in v['models']),'nonmatchable_rows':sum(c.get('matchable') is False for m in v['models'] for c in m['codes']),'source_conflict_rows':len(conflicts),'unavailable_model_sources':sum(m['manual'].get('source_available') is False for m in v['models']),'unavailable_source_html_pages':len(unavailable_pages),'declared_complete_models':sum(bool(m['complete_code_table']) for m in v['models']),'declared_partial_models':sum(not m['complete_code_table'] for m in v['models']),'brand_records':len(b['brands']),'kombi_brand_intake':sum('kombi' in r['devices'] for r in b['brands']),'klima_brand_intake':sum('klima' in r['devices'] for r in b['brands']),'unique_manual_urls':len(set(m['manual']['url'] for m in v['models'])),'manuals_marked_official':sum(m['manual'].get('official') is True for m in v['models']),'manual_checked_at_values':dict(collections.Counter(m['manual'].get('checked_at') for m in v['models']))},
 'per_model':[{'id':m['id'],'brand':m['brand'],'device':m['device'],'path':m['path'],'code_rows':len(m['codes']),'matchable_nonconflicting_rows':sum(c.get('matchable') is not False and not c.get('source_conflict') for c in m['codes']),'source_url':m['manual']['url'],'source_available':m['manual'].get('source_available','not_independently_checked_here'),'declared_complete_table':bool(m['complete_code_table']),'market':m.get('market','unspecified'),'independent_primary_document_recheck_in_this_audit':False} for m in v['models']],
 'checks':dict(checks),'runtime_results':dict(status),'conflicted_rows_fail_closed':conflicts,'foreign_pages':foreign,'unavailable_source_pages':unavailable_pages,
 'semantic_validation':{'all_manuals_refetched':False,'all_meanings_independently_revalidated':False,'all_rows_original_primary_documents_read_in_this_audit':False,'official_flag_is_metadata_not_live_validation':True,'code_lookup_matches_registered_meaning_not_proof_of_correctness':True,'latest_source_research':[{'model_id':'eca-kombi-confeo-premix-hm-tr','code':'E99','meaning':'Donanım hatası 4','official_source_url':'https://eca.com.tr/uploads/documents/fbb/acf/66d81c49-fc4e-48e1-a78e-7ada696035db.pdf','source_location':'printed page29, error table','access_method':'indexed-extract; full17MB PDF unread in this environment','does_not_establish_proteus_or_citius_meaning':True}]},
 'limitations':['The 93 registered families are not every model of every brand in Türkiye.','Correct local dispatch does not establish all manufacturer meanings as independently rechecked.','Partial tables and excluded/conflicting rows are intentionally retained.','Foreign manual selection remains usable with explicit country/variant warning; no blocking checkbox.','This local production artifact is not the deployed production website and does not prove current production deployment or provider reachability.'],
 'errors':errors,'warnings':warnings}
args.report.parent.mkdir(parents=True,exist_ok=True)
args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({**{k:report[k] for k in ['passed','inventory','checks','runtime_results']},'error_count':len(errors),'errors':errors[:15]},ensure_ascii=False,indent=2));sys.exit(bool(errors))
