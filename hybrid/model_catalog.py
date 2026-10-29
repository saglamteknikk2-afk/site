"""One model-name catalogue shared by the directory, AI wizard and local matrix.

Names without an exact matching manual remain usable as identification input;
they never inherit another model's code definitions. Existing code tables stay
unchanged. New tables are rendered only from individually reviewed data records.
"""
from collections import Counter
from html import escape
from pathlib import Path
import hashlib,json,re
from urllib.parse import urlsplit

from editorial_regions import replace_element
from semantics import Page

ROOT=Path(__file__).resolve().parent

def norm(value):
    value=str(value or '').translate(str.maketrans('çğıöşüÇĞİÖŞÜ','cgiosuCGIOSU')).lower()
    return ' '.join(re.findall(r'[a-z0-9]+',value))

def identity(device,brand,name):
    text=norm(name);b=norm(brand)
    if text.startswith(b+' '):text=text[len(b)+1:]
    # The exact Vaillant VUW/VCW type suffix identifies the device; a repeated
    # commercial-family prefix does not make a second model card.
    if b=='vaillant':
        match=re.search(r'\b(?:vuw|vcw|vu)\s+\d',text)
        if match:text=text[match.start():]
    return (device,b,text)

def load_expansions():
    records=[]
    for source in sorted((ROOT/'data/model-expansion').glob('*.json')):
        value=json.loads(source.read_text())
        records.extend(value.get('models',[]))
    return records

def validate_model(model):
    required={'id','device','brand','label','model_names','manual','codes','path'}
    if required-set(model):raise ValueError('Incomplete model scope: '+str(model.get('id')))
    if model['device']!='kombi' or model.get('market')!='TR' or model.get('matchable') is not True:
        raise ValueError('Expansion must identify its exact reviewed Turkish combi scope.')
    url=urlsplit(model['manual']['url'])
    if url.scheme!='https' or not url.hostname or model['manual'].get('official') is not True:
        raise ValueError('Manufacturer provenance is required.')
    if not model['model_names'] or not model['codes'] or not re.fullmatch(r'/?[a-z0-9-]+-ariza-kodlari\.html',model['path']):
        raise ValueError('Model names, real code definitions and local route are required.')
    anchors=set();codes=set()
    for code in model['codes']:
        for field in ('code','meaning','safe_observation','source_locator'):
            if not str(code.get(field,'')).strip():raise ValueError('Incomplete code evidence '+model['id'])
        code.setdefault('code_key',re.sub('[^A-Z0-9]','',code['code'].upper()))
        code.setdefault('anchor','kod-'+code['code_key'].lower())
        code.setdefault('equivalent_codes',[])
        if code['anchor'] in anchors or code['code_key'] in codes:raise ValueError('Conflicting code identity '+model['id'])
        anchors.add(code['anchor']);codes.add(code['code_key'])

def _new_page(model,files):
    name=model['path'].lstrip('/')
    if name in files:raise ValueError('An expansion cannot silently replace an existing guide: '+name)
    template=files['vaillant-kombi-ecotec-pro-236-286-5-3-ariza-kodlari.html'].decode()
    title=model['brand']+' '+model['label']+' · Kombi hata kodları'
    description=model.get('description') or model['brand']+' '+model['label']+' için üretici belgesindeki hata gösterimleri, kapsam ve güvenli gözlem notları.'
    template=re.sub(r'<title>.*?</title>',lambda _:'<title>'+escape(title)+' | Sağlam Teknik</title>',template,count=1,flags=re.S)
    template=re.sub(r'(<link\b[^>]*rel="canonical"[^>]*href=")[^"]*(")',lambda m:m[1]+'https://saglamkombiklima.com.tr/'+name+m[2],template)
    template=re.sub(r'(<meta\s+(?:name="description"|property="og:description")\s+content=")[^"]*(">)',lambda m:m[1]+escape(description,quote=True)+m[2],template)
    template=re.sub(r'(<meta\s+property="og:(?:url|title)"\s+content=")[^"]*(">)',lambda m:m[1]+escape('https://saglamkombiklima.com.tr/'+name if 'og:url' in m[0] else title,quote=True)+m[2],template)
    template=re.sub(r'<h1\b[^>]*>.*?</h1>',lambda _:'<h1>'+escape(title)+'</h1>',template,count=1,flags=re.S)
    lead='Bu tablo yalnız '+model['brand']+' '+model['label']+' belgesinin kapsadığı ürünler içindir. Kodun tam yazımını, ürün son ekini ve belgenin sürümünü birlikte kontrol edin.'
    template=re.sub(r'<p class="at-lead">.*?</p>',lambda _:'<p class="at-lead">'+escape(lead)+'</p>',template,count=1,flags=re.S)
    rows=[]
    for row in model['codes']:
        detail='<p>'+escape(row['explanation'])+'</p>' if row.get('explanation') else ''
        rows.append('<tr id="'+escape(row['anchor'],quote=True)+'" data-fault-row><th scope="row"><code>'+escape(row['code'])+'</code></th><td>'+escape(row['meaning'])+detail+'<small>'+escape(row['source_locator'])+'</small></td><td>'+escape(row['safe_observation'])+'</td></tr>')
    scope='<section class="fault-scope" id="modelScopeNote"><h2>Kılavuzun kapsadığı modeller</h2><ul>'+''.join('<li>'+escape(n)+'</li>' for n in model['model_names'])+'</ul><p>'+escape(model.get('scope_note') or 'Bu model kapsamı dışındaki cihazlara kod anlamı aktarılmaz.')+'</p><p>Üretici belgesi: '+escape(model['manual']['title'])+' · '+escape(model['manual'].get('locator',''))+'</p><p class="st-source-reference">'+escape(model['manual']['url'])+'</p></section>'
    body=(scope+'<section class="fault-table-section" id="kodlar"><h2>'+escape(model['brand']+' '+model['label'])+' kod açıklamaları</h2><label class="fault-filter-label" for="faultTableSearch">Kod veya açıklama ara</label><input id="faultTableSearch" class="fault-input" type="search" autocomplete="off"><p id="faultTableStatus" aria-live="polite"></p><div class="fault-table-wrap"><table><thead><tr><th scope="col">Kod</th><th scope="col">Üretici belgesine göre anlamı</th><th scope="col">Güvenli ilk gözlem</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></section><section><h2>Belirtiyi ve koşulları birlikte değerlendirin</h2><p>Kod tek başına değişecek parçanın kesin teşhisi değildir. Kapağı açmayın; gaz ayarı, elektrik bağlantısı ve yanma devresine müdahale etmeyin. Gaz kokusu, duman veya patlamalı ateşleme varsa cihazı tekrar deneyerek çalıştırmayın.</p><p><a href="./#ai-usta">AI Usta ile belirti üzerinden ilerle</a> · <a href="tel:05346225515">Ustamızı ara</a></p></section>')
    template=replace_element(template,lambda n:n['tag']=='div' and 'at-content' in n['attrs'].get('class','').split(),body,True)
    aside='<aside class="at-aside"><h2>'+escape(model['brand']+' cihazınız için')+'</h2><p>Model ve kodu birlikte iletin; servis uygunluğunu görüşelim.</p><a class="at-btn at-btn-primary" href="tel:05346225515">Ustamızı ara</a><p><a href="model-ariza-kodlari.html">Başka model seç</a></p></aside>'
    template=replace_element(template,lambda n:n['tag']=='aside' and 'at-aside' in n['attrs'].get('class','').split(),aside)
    # Source schema describes the template device. Let the semantic build derive
    # all entities from this new page rather than retain the template identity.
    template=re.sub(r'<script\b[^>]*type="application/ld\+json"[^>]*>.*?</script>','',template,flags=re.S)
    template=template.replace('Vaillant ecoTEC pro VUW TR 236/5-3 / 286/5-3',escape(model['brand']+' '+model['label']))
    files[name]=template.encode()

def compile_directory(directory,models,files):
    from hubs import model_local
    active={m['id']:m for m in models if model_local(m,files) and m['manual'].get('source_available') is not False}
    records={};by_identity={}
    for model in models:
        for name in model.get('model_names') or [model['label']]:
            key=identity(model['device'],model['brand'],name)
            by_identity.setdefault(key,[]).append(model)
    for key,scopes in by_identity.items():
        distinct={m['id']:m for m in scopes if m['id'] in active}
        example=scopes[0];name=next(n for n in (example.get('model_names') or [example['label']]) if identity(example['device'],example['brand'],n)==key)
        row={'device':example['device'],'brand':example['brand'],'name':name,'kind':'document-model-name','market':example.get('market','document-scope'),'status':'manual-linked' if len(distinct)==1 else 'scope-check-required','source_url':example['manual']['url'],'checked_at':example['manual'].get('checked_at'),'provenance':'model-manual','code_definitions_added':False}
        if len(distinct)==1:row['verified_model_id']=next(iter(distinct))
        records[key]=row
    omitted=[]
    for old in directory['entries']:
        key=identity(old['device'],old['brand'],old['name'])
        if key in records:continue
        # Omit a family-only card when exact documented variants are already
        # represented; it must not look like another unverified physical model.
        if old.get('kind')=='series':
            family=norm(old['name'])
            covered=any(m['device']==old['device'] and norm(m['brand'])==norm(old['brand']) and any(norm(alias)==family or norm(alias).startswith(family+' ') for alias in [m['label'],*(m.get('aliases') or [])]) for m in active.values())
            if covered:omitted.append(old['name']);continue
        row=dict(old);row.pop('verified_model_id',None)
        records[key]=row
    seen_scopes=set()
    rows=sorted(records.values(),key=lambda r:(r['device'],norm(r['brand']),norm(r['name'])))
    for row in rows:
        mid=row.get('verified_model_id')
        if mid and mid not in seen_scopes:row['id']=mid;seen_scopes.add(mid)
        else:row['id']='name-'+hashlib.sha256('|'.join(identity(row['device'],row['brand'],row['name'])).encode()).hexdigest()[:18]
        row['path']=active[mid]['path'].lstrip('/') if mid in active else ''
    counts=Counter((r['device'],r['brand']) for r in rows)
    result={**directory,'checked_at':'2026-10-29','entries':rows}
    result['coverage']={**directory.get('coverage',{}),'entries':len(rows),'manual_linked_names':sum(bool(r.get('verified_model_id')) for r in rows),'catalogue_name_only':sum(not r.get('verified_model_id') for r in rows),'by_brand_device':[{'device':d,'brand':b,'names':n} for (d,b),n in sorted(counts.items())]}
    result['policy']={**directory.get('policy',{}),'complete_market_inventory':False,'completeness':'source-backed-identification-plus-reviewed-code-scopes','notice':'Model seçimi isteğe bağlıdır. Listelenen adın kod kılavuzu eşleşmediyse farklı modelin kodu uygulanmaz.'}
    return result,omitted

def apply_model_catalog(files):
    from importlib.util import spec_from_file_location,module_from_spec
    verified=json.loads(files['assets/verified-faults.json']);old_count=len(verified['models']);ids={m['id'] for m in verified['models']}
    additions=load_expansions()
    for model in additions:
        validate_model(model)
        if model['id'] in ids:raise ValueError('Expansion duplicates an existing scope: '+model['id'])
        ids.add(model['id']);_new_page(model,files);verified['models'].append(model)
    # Runtime links resolve from the current installation path. A leading slash
    # would escape /site/ on Pages (or any Plesk subdirectory installation).
    for model in verified['models']:model['path']=model['path'].lstrip('/')
    for row in verified['coverage']:
        row['verified_model_ids']=[m['id'] for m in verified['models'] if m['brand']==row['brand'] and m['device']==row['device']]
        row['limitations']=str(row.get('limitations','')).replace('Hata kodu E1 ile E01 eşdeğer sayılmaz.','E1/E01 gibi sıfırlı yazımlar ancak aynı modelde tek ve çelişkisiz bir kayda karşılık gelirse eşleştirilir.')
    verified['checked_at']='2026-10-29'
    payload=json.dumps(verified,ensure_ascii=False,separators=(',',':'))
    files['assets/verified-faults.json']=(json.dumps(verified,ensure_ascii=False,indent=2)+'\n').encode()
    files['assets/verified-faults.js']=('window.ST_VERIFIED_FAULTS='+payload+';\n').encode()
    directory,omitted=compile_directory(json.loads(files['assets/model-directory.json']),verified['models'],files)
    spec=spec_from_file_location('model_directory_builder',ROOT.parent/'scripts/model_directory.py');module=module_from_spec(spec);spec.loader.exec_module(module)
    files['assets/model-directory.json']=(json.dumps(directory,ensure_ascii=False,indent=2)+'\n').encode()
    files['assets/model-directory.js']=module.javascript(directory).encode()
    # Keep the optional brand coverage panel aligned with the same manual IDs.
    registry=json.loads(files['assets/brand-registry.json'])
    for brand in registry['brands']:brand['verified_model_ids']=[m['id'] for m in verified['models'] if norm(m['brand'])==norm(brand['name'])]
    files['assets/brand-registry.json']=(json.dumps(registry,ensure_ascii=False,indent=2)+'\n').encode()
    files['assets/brand-registry.js']=re.sub(rb'window\.ST_BRAND_REGISTRY\s*=\s*\{.*?\};',lambda _:('window.ST_BRAND_REGISTRY='+json.dumps(registry,ensure_ascii=False,separators=(',',':'))+';').encode(),files['assets/brand-registry.js'],count=1,flags=re.S)
    # The standalone directory used a smaller organic-name list instead of the
    # larger common directory, causing the reported missing/duplicate cards.
    text=files['assets/model-browser.js'].decode()
    start=text.index('  const records=[];');end=text.index('  function brands()',start)
    replacement='''  const records=['kombi','klima'].flatMap(kind=>window.STModelDirectory?.list(kind,'')||[]).map(item=>{
    const m=data.models.find(model=>model.id===item.verified_model_id);
    return {name:modelTitle(item,item.name),exact:item.name,device:item.device,brand:item.brand,verified:!!m,sourceUnavailable:false,documentOnly:item.kind==='series',id:m?.id||'',path:m?.path||'',market:m?.market||item.market||'',scope:m?.scope_note||'',count:m?.codes?.length||0,terms:[item.brand,item.name,m?.label||''].join(' ')};
  });
  const unique=records;
'''
    text=text[:start]+replacement+text[end:]
    text=text.replace("'Model ailesi · kod tablosu bekliyor'","'Model adı · belirtiyle destek'")
    files['assets/model-browser.js']=text.encode()
    # Make the catalogue available before model-browser on the directory page.
    name='model-ariza-kodlari.html';text=files[name].decode()
    if not re.search(r'<script[^>]*src="assets/model-directory\.js',text):
        text=re.sub(r'(<script\b[^>]*src="assets/model-browser\.js)',r'<script src="assets/model-directory.js" defer></script>\1',text,count=1)
    files[name]=text.encode()
    organic=json.loads(files['assets/organic-catalog.json']);organic['published_routes']=list(dict.fromkeys(organic.get('published_routes',[])+[m['path'] for m in additions]))
    files['assets/organic-catalog.json']=(json.dumps(organic,ensure_ascii=False,indent=2)+'\n').encode()
    files['assets/organic-catalog.js']=('window.ST_ORGANIC_CATALOG='+json.dumps(organic,ensure_ascii=False,separators=(',',':'))+';\n').encode()
    return {'previous_manual_scopes':old_count,'new_manual_scopes':len(additions),'manual_scopes':len(verified['models']),'model_name_records':len(directory['entries']),'manual_linked_names':directory['coverage']['manual_linked_names'],'family_only_duplicates_omitted':omitted,'new_routes':[m['path'].lstrip('/') for m in additions],'complete_market_inventory':False}
