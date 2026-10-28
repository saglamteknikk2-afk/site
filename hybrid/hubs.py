"""Crawlable contextual bridges and progressive region selection, without URL multiplication."""
from __future__ import annotations
import html,json,re,unicodedata
from pathlib import Path
from urllib.parse import parse_qs,urlsplit,unquote

ROOT=Path(__file__).resolve().parent

def norm(s):
    s=str(s).translate(str.maketrans('çğıöşüÇĞİÖŞÜ','cgiosuCGIOSU')).lower()
    return re.sub(r'[^a-z0-9]+',' ',s).strip()
def slug(s):return norm(s).replace(' ','-')
def js_data(files,name,var):
    text=files[name].decode();m=re.search(r'window\.'+var+r'\s*=\s*(\{.*?\});',text,re.S)
    if not m:raise ValueError('Missing catalogue '+name)
    return json.loads(m[1])
def route(path):return str(path or '').lstrip('/').split('#')[0].split('?')[0]
def indexable(text):return not re.search(r'<meta\b[^>]*name=["\']robots["\'][^>]*content=["\'][^"\']*noindex',text,re.I)
def title(text):
    m=re.search(r'<h1\b[^>]*>(.*?)</h1>',text,re.S);return html.unescape(re.sub('<[^>]+>',' ',m[1])).strip() if m else ''
def anchor(path,label):return '<a href="'+html.escape(path,quote=True)+'">'+html.escape(label)+'</a>'
def block(heading,links,description=''):
    seen=set();valid=[]
    for path,label in links:
        if path and path not in seen:seen.add(path);valid.append('<li>'+anchor(path,label)+'</li>')
    return '<section class="hybrid-bridges" aria-label="'+html.escape(heading,quote=True)+'"><h2>'+html.escape(heading)+'</h2>'+('<p>'+html.escape(description)+'</p>' if description else '')+'<nav aria-label="'+html.escape(heading,quote=True)+'"><ul>'+''.join(valid)+'</ul></nav></section>' if valid else ''

def model_local(m,files):
    path=route(m.get('path'));text=files.get(path,b'').decode()
    if not path or not text or not indexable(text):return False
    market=norm(m.get('market',''))
    foreign=('birlesik krallik','fransa','polonya','vietnam','singapur','north america','levant','us ca','gb ie')
    if any(x in market for x in foreign):return False
    if market and not (market.startswith('tr') or market in {'turkiye','turkiye pazari'}):return False
    if re.search(r'-(?:uk|gb-ie|fr|ru-by|by|us|us-ca|he-pl|nl-ca1)-',path+'-'):return False
    if m.get('requires_scope_confirmation') and not market.startswith('tr'):return False
    if m.get('matchable') is False:return False
    return True

def _widget(region,device,districts,brand='',need_path=''):
    name=region['name'];district=name if name in districts else (region.get('districts') or [''])[0]
    return ('<section class="hybrid-matrix" data-hybrid-matrix data-district="'+html.escape(district,quote=True)+'" data-device="'+device+'" data-brand="'+html.escape(brand,quote=True)+'" data-need-path="'+html.escape(need_path,quote=True)+'" aria-labelledby="hybridMatrixTitle">'
      '<h2 id="hybridMatrixTitle">Cihazınıza göre devam edin</h2><p>Marka veya modeli bilmiyorsanız boş bırakabilirsiniz.</p>'
      '<div data-matrix-controls hidden><div class="hybrid-fields"><label>Cihazınız<select data-field="device"><option value="kombi">Kombi</option><option value="klima">Klima</option></select></label>'
      '<label>Marka <span>(isteğe bağlı)</span><select data-field="brand"><option value="">Markayı bilmiyorum</option></select></label>'
      '<label>Belirti veya işlem<select data-field="need"><option value="">Servis bilgilerini göster</option></select></label></div>'
      '<details class="hybrid-options"><summary>Model veya hata kodu ekleyin <span>(isteğe bağlı)</span></summary><div class="hybrid-fields">'
      '<label>Model<select data-field="model"><option value="">Modeli bilmiyorum</option></select></label>'
      '<label data-custom-model-label hidden>Model adını yazın <span>(isteğe bağlı)</span><input data-field="customModel" maxlength="100" autocomplete="off"></label>'
      '<label>Ekrandaki kod <span>(isteğe bağlı)</span><input data-field="code" maxlength="24" autocomplete="off" placeholder="Örn. E01 veya F22"></label></div></details>'
      '<details class="hybrid-options"><summary>İlçe veya mahalleyi değiştirin</summary><div class="hybrid-fields"><label>İlçe<select data-field="district"></select></label>'
      '<label>Mahalle <span>(isteğe bağlı)</span><select data-field="neighborhood"><option value="">Mahallemi bilmiyorum / listede yok</option></select></label></div></details>'
      '<div class="hybrid-actions"><button type="button" data-matrix-show>Arızamı bul →</button><button type="button" class="hybrid-reset" data-matrix-reset>Baştan başla ↺</button></div>'
      '<div class="hybrid-result" data-matrix-result hidden role="status" aria-live="polite"></div></div>'
      '<noscript><p>İlgili marka ve belirti rehberlerini aşağıdaki bağlantılardan açabilirsiniz.</p></noscript></section>')

def apply_hubs(files):
    from service_editorial import load_services
    authored_services=load_services()
    data=js_data(files,'assets/servis-verileri.js','ST_SERVICE_DATA')
    models=json.loads(files['assets/verified-faults.json'])['models']
    regions=json.loads(files['assets/hybrid-regions.json'])
    district_rows=regions['districts']; districts={r['name']:r for r in district_rows}
    neighborhood_map={(norm(n['district']),norm(n['name'])):(n['district'],n['name']) for n in data['neighborhoods']}
    district_norm={norm(x):x for x in data['districts']}
    eligible={n for n,b in files.items() if n.endswith('.html') and not n.startswith(('assets/','google','yandex')) and indexable(b.decode()) and n!='404.html'}
    titles={n:title(files[n].decode()) for n in eligible}
    brands={}
    for kind,device in data['devices'].items():
        for b in device['brands']:
            p=slug(b)+'-'+kind+'-servisi.html'
            if p in eligible:brands[(kind,b)]=p
    # Existing Mitsubishi spelling is deliberately retained.
    for b,p in [('Mitsubishi Heavy Industries','mitsubishi-heavy-industries-klima-servisi.html'),('Mitsubishi Electric','mitsubishi-electric-klima-servisi.html')]:
        if p in eligible:brands[('klima',b)]=p
    local_models=[m for m in models if model_local(m,files)]
    source_rewrites=0
    for filename in [n for n in files if n.endswith('.html')]:
        text=files[filename].decode()
        def rewrite(m):
            nonlocal source_rewrites
            value=html.unescape(m['value']);u=urlsplit(value)
            if route(u.path)!='servis-sec.html':return m[0]
            params=parse_qs(u.query+'&'+u.fragment)
            dist=params.get('ilce',[''])[0];neigh=params.get('mahalle',[''])[0]
            match=neighborhood_map.get((norm(dist),norm(neigh)))
            if not match:return m[0]
            dist,neigh=match
            kind=params.get('cihaz',['klima' if '-klima-' in filename else 'kombi'])[0]
            if kind not in {'kombi','klima'}:kind='kombi'
            target=slug(dist)+'-'+kind+'-servisi.html'
            if target not in files:return m[0]
            source_rewrites+=1
            return 'href='+m['quote']+target+'#mahalle-'+slug(neigh)+m['quote']
        text=re.sub(r'href=(?P<quote>["\'])(?P<value>[^"\']*)(?P=quote)',rewrite,text)
        files[filename]=text.encode()
    # RegionFinder takes its destination from the now meaningful static anchors.
    region_js='assets/premium-regions.js'
    if region_js in files:
        text=files[region_js].decode()
        text=text.replace("if(climate&&record.type==='neighborhood'){", "if(climate&&record.type==='neighborhood'&&record.href.includes('#mahalle-'))return record.href.replace('-kombi-servisi.html','-klima-servisi.html');\n    if(climate&&record.type==='neighborhood'){")
        files[region_js]=text.encode()
    per_page={};widgets=0;service_widgets=0
    regional={}
    for r in district_rows:
        for kind in ['kombi','klima']:regional[slug(r['name'])+'-'+kind+'-servisi.html']=(r,kind)
    for r in regions['localities']:regional[slug(r['name'])+'-servisi.html']=(r,'kombi')
    for n in sorted(eligible):
        text=files[n].decode();links=[];heading='İlgili servis ve arıza rehberleri'
        kind='klima' if '-klima-' in n or n.startswith('klima-') else 'kombi'
        if n in regional:
            r,kind=regional[n];heading=r['name']+' için marka ve arıza rehberleri'
            available=[(brand,p) for (k,brand),p in brands.items() if k==kind]
            # Navigation examples are stable; location never changes a model's technical scope.
            sample=sorted(available,key=lambda item:norm(item[0]))[:3]
            links += [(p,b+' '+kind+' servisi') for b,p in sample]
            scoped=[m for m in local_models if m['device']==kind and m['brand'] in {b for b,p in sample}]
            links += [(route(m['path'])+'#kodlar',m['brand']+' '+m['label']+' kod rehberi') for m in scoped[:2]]
            from regions import load_editorial
            authored=load_editorial()[n]
            authored_links=[(x['path'],x['label']) for section in authored['sections'] for x in section.get('links',[])]
            links += authored_links[:3]
            links += [('markalar.html','Diğer bütün markalar'),('ariza-rehberi.html','Diğer belirtiler'),('bolgeler.html','Bütün hizmet bölgeleri')]
            widget=_widget(r,kind,districts)
            marker='</section><!-- HYBRID-REGION:END -->'
            if '<div data-editorial-selector></div>' in text:text=text.replace('<div data-editorial-selector></div>',widget,1)
            elif marker in text:text=text.replace(marker,marker+widget,1)
            else:text=text.replace('</main>',widget+'</main>',1)
            widgets+=1
        else:
            if n in authored_services and '<div data-editorial-service-selector></div>' in text:
                page=authored_services[n]
                initial_kind='klima' if page['device']=='klima' else 'kombi'
                widget=_widget({'name':'','districts':[]},initial_kind,districts,
                               page.get('brand',''),n if page['type']=='symptom' else '')
                text=text.replace('<div data-editorial-service-selector></div>',widget,1)
                service_widgets+=1
            matched=[(b,k) for (k,b),p in brands.items() if p==n]
            current_models=[m for m in models if route(m.get('path'))==n]
            if matched:
                brand,kind=matched[0];heading=brand+' için model ve bölge bağlantıları'
                links += [(route(m['path'])+'#kodlar',brand+' '+m['label']) for m in local_models if m['brand']==brand and m['device']==kind][:4]
                other='klima' if kind=='kombi' else 'kombi'
                if (other,brand) in brands:links.append((brands[(other,brand)],brand+' '+other+' servisi'))
            elif current_models:
                m=current_models[0];kind=m['device'];heading=m['brand']+' cihazınız için servis ve belirtiler'
                if (kind,m['brand']) in brands:links.append((brands[(kind,m['brand'])],m['brand']+' '+kind+' servisi'))
                links += [(route(x['path'])+'#kodlar',x['brand']+' '+x['label']) for x in local_models if x['brand']==m['brand'] and x['device']==kind and route(x['path'])!=n][:2]
            elif n in {'index.html','bolgeler.html','markalar.html','hizmetler.html','ariza-rehberi.html','model-ariza-kodlari.html'}:
                continue
            elif n.startswith(('kombi-','klima-','petek-','baymak-e1')):
                heading=titles[n]+' için sonraki adımlar'
                links += [(p,b+' '+kind+' servisi') for (k,b),p in brands.items() if k==kind][:3]
            else:continue
            links += [(slug(d)+'-'+kind+'-servisi.html',d+' '+kind+' servisi') for d in ['Küçükçekmece','Avcılar','Bağcılar']]
            links += [('bolgeler.html','Diğer bütün ilçeler'),('markalar.html','Marka seçimi'),('ariza-rehberi.html','Belirti rehberi')]
        links=[(p,l) for p,l in links if route(p) in eligible and route(p)!=n][:10]
        rendered=block(heading,links,'' if n in regional else 'Hata kodunu cihazın tam modeline göre okuyun; bölge seçimi teknik kodun anlamını değiştirmez.')
        if rendered:text=text.replace('</main>',rendered+'</main>',1);per_page[n]=len(links)
        if n in regional or n in authored_services:
            assets='<link rel="stylesheet" href="assets/hybrid-matrix.css"><script src="assets/hybrid-matrix.js" defer></script>'
            text=text.replace('</head>',assets+'</head>',1)
        elif rendered:text=text.replace('</head>','<link rel="stylesheet" href="assets/hybrid-matrix.css"></head>',1)
        files[n]=text.encode()
    # Crawlable home -> region, brand and service hubs; one compact district directory.
    for hub in ['index.html','bolgeler.html']:
        text=files[hub].decode()
        links=[]
        for r in district_rows:
            for k in ['kombi','klima']:links.append((slug(r['name'])+'-'+k+'-servisi.html',r['name']+' '+k+' servisi'))
        links += [(slug(r['name'])+'-servisi.html',r['name']+' servis bilgileri') for r in regions['localities']]
        directory='<details class="hybrid-directory"><summary>İlçe ve semt servis rehberleri</summary>'+block('Hizmet bölgenizi seçin',links)+'</details>'
        if hub=='index.html':directory+=block('Marka ve cihaz rehberleri',[(p,b+' '+k+' servisi') for (k,b),p in brands.items()]+[('model-ariza-kodlari.html','Model ve kod rehberleri'),('ariza-rehberi.html','Belirtiye göre ilerleyin')])
        text=text.replace('</main>',directory+'</main>',1)
        text=text.replace('</head>','<link rel="stylesheet" href="assets/hybrid-matrix.css"></head>',1)
        files[hub]=text.encode()
    # Guarantee reachability by attaching only genuinely orphaned content to its natural hub.
    def graph():
        g={}
        for n in eligible:
            refs=re.findall(r'<a\b[^>]*href=["\']([^"\']+)',files[n].decode(),re.I)
            g[n]={route(html.unescape(x)) or n for x in refs if not urlsplit(html.unescape(x)).scheme}
        found={'index.html'};todo=['index.html']
        while todo:
            for n in g.get(todo.pop(),set())&eligible:
                if n not in found:found.add(n);todo.append(n)
        return found
    missing=eligible-graph()
    if missing:
        text=files['ariza-rehberi.html'].decode();extra=block('Diğer bilgi sayfaları',[(n,titles[n] or n) for n in sorted(missing)])
        files['ariza-rehberi.html']=text.replace('</main>',extra+'</main>',1).encode()
    data_models=[]
    for m in local_models:
        data_models.append({'id':m['id'],'device':m['device'],'brand':m['brand'],'label':m['label'],'path':route(m['path']),
          'codes':[{'code':c['code'],'anchor':c.get('anchor',''),'meaning':c.get('meaning','')} for c in m.get('codes',[])]})
    payload={'schema_version':1,'districts':[{'name':r['name'],'slug':r.get('slug',slug(r['name'])),'neighborhoods':r['neighborhoods']} for r in district_rows],
      'devices':{k:{'label':v['label'],'brands':v['brands'],'needs':[x for x in v['services']+v['symptoms'] if route(x['path']) in eligible and route(x['path']) not in {'klima-montaji.html','klima-sokumu.html'}]} for k,v in data['devices'].items()},
      'brand_routes':[{'device':k,'brand':b,'path':p} for (k,b),p in brands.items()], 'models':data_models,'routes':sorted(eligible)}
    # These aggregate intents have no single entry (or only narrower aliases) in
    # the legacy complaint list. Keep their own purpose selected on landing.
    for path,label in [('kombi-hata-kodu.html','Kombi hata kodu'),
                       ('klima-hata-kodu.html','Klima hata kodu'),
                       ('petek-temizligi.html','Petek temizliği')]:
        kind='klima' if path.startswith('klima-') else 'kombi'
        payload['devices'][kind]['needs'].insert(0,{'name':label,'path':path,'terms':[]})
    files['assets/hybrid-matrix-data.json']=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()
    files['assets/hybrid-matrix.js']=(ROOT/'assets/matrix.js').read_bytes()
    files['assets/hybrid-matrix.css']=(ROOT/'assets/matrix.css').read_bytes()
    return {'region_widgets':widgets,'service_widgets':service_widgets,'contextual_bridge_pages':len(per_page),'contextual_links':sum(per_page.values()),'neighborhood_links_to_content':source_rewrites,
            'local_model_scopes':len(local_models),'indexable_orphans':sorted(eligible-graph()),'formerly_unreachable_connected':sorted(missing),'brand_routes':len(brands)}
