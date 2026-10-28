"""Render independently authored regional bodies instead of a shared article."""
from __future__ import annotations
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import hashlib,json,re

ROOT=Path(__file__).resolve().parent
DATA_PATH=ROOT/'data/regions.json'
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

def slug(value):
    value=str(value).translate(str.maketrans('çğıöşüÇĞİÖŞÜ','cgiosuCGIOSU')).lower()
    return re.sub(r'[^a-z0-9]+','-',value).strip('-')

def load_regions():return json.loads(DATA_PATH.read_text())

def load_editorial():
    pages=[]
    for path in sorted((ROOT/'data/editorial').glob('batch-*.json')):
        pages.extend(json.loads(path.read_text())['pages'])
    if len(pages)!=55 or len({p['route'] for p in pages})!=55:
        raise ValueError('All 55 independently authored regional bodies are required.')
    return {p['route']:p for p in pages}

class Ranges(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=False);self.text=text;self.offsets=[0];self.stack=[];self.nodes=[]
        for line in text.splitlines(keepends=True):self.offsets.append(self.offsets[-1]+len(line))
        self.feed(text)
    def position(self):
        line,column=self.getpos();return self.offsets[line-1]+column
    def handle_starttag(self,tag,attrs):
        node={'tag':tag,'attrs':dict(attrs),'start':self.position(),'open':self.get_starttag_text()}
        if tag not in VOID:self.stack.append(node)
    def handle_startendtag(self,tag,attrs):pass
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i]['tag']==tag:
                node=self.stack[i];node['end']=self.text.find('>',self.position())+1
                self.nodes.append(node);del self.stack[i:];break

def replace_element(text,selector,content,keep_tag=False):
    matches=[node for node in Ranges(text).nodes if selector(node)]
    if len(matches)!=1:raise ValueError('Expected exactly one regional replacement target.')
    n=matches[0];replacement=(n['open']+content+'</'+n['tag']+'>') if keep_tag else content
    return text[:n['start']]+replacement+text[n['end']:]

def link(path,label,files):
    target=path.split('#')[0].split('?')[0]
    if target not in files:raise ValueError('Editorial link has no published target: '+target)
    return '<a href="'+escape(path,quote=True)+'">'+escape(label)+'</a>'

def _neighborhoods(region,device,intro):
    links=[]
    for name in region['neighborhoods']:
        anchor='mahalle-'+slug(name)
        links.append('<li id="'+anchor+'"><a href="#'+anchor+'" data-hybrid-neighborhood="'+escape(name,quote=True)+'" data-hybrid-district="'+escape(region['name'],quote=True)+'" data-hybrid-device="'+device+'">'+escape(name)+'</a></li>')
    return ('<section class="editorial-geography"><h2>'+escape(region['name'])+' mahalleleri</h2><p>'+escape(intro)+'</p>'
            '<nav aria-label="'+escape(region['name'],quote=True)+' mahalleleri"><ul class="hybrid-neighborhoods">'+''.join(links)+'</ul></nav></section>')

def _body(page,files):
    sections=[]
    for i,section in enumerate(page['sections']):
        ident=section.get('id') or 'bolum-'+str(i+1)
        paragraphs=''.join('<p>'+escape(p)+'</p>' for p in section['paragraphs'])
        bullets=('<ul class="editorial-checks">'+''.join('<li>'+escape(item)+'</li>' for item in section['bullets'])+'</ul>') if section.get('bullets') else ''
        links=('<nav class="editorial-guides" aria-label="'+escape(section['heading'],quote=True)+'">'+''.join(link(row['path'],row['label'],files) for row in section.get('links',[]))+'</nav>') if section.get('links') else ''
        sections.append('<section id="'+escape(ident,quote=True)+'" class="editorial-section"><span id="yerel-'+str(i+1)+'" class="editorial-anchor" aria-hidden="true"></span><h2>'+escape(section['heading'])+'</h2>'+paragraphs+bullets+links+'</section>')
    faq='<section id="yerel-sorular" class="editorial-faq"><h2>'+escape(page.get('faq_heading','Servis öncesi sorular'))+'</h2>'
    for item in page['faqs']:
        faq+='<details><summary>'+escape(item['question'])+'</summary><p>'+escape(item['answer'])+'</p></details>'
    return '<article id="local-guide-body" class="editorial-body">'+''.join(sections)+faq+'</section></article>'

def _region_content(page,region,device,files,old_ids):
    place=region['name'];takeaways='<ul class="editorial-takeaways">'+''.join('<li>'+escape(x)+'</li>' for x in page['takeaways'])+'</ul>'
    header='<header class="editorial-opening"><h2>'+escape(page['headline'])+'</h2>'+takeaways+'</header>'
    body=_body(page,files)
    if device in {'kombi','klima'}:
        geography=_neighborhoods(region,device,page['neighborhood_intro'])
        neighbors=[(slug(n)+'-'+device+'-servisi.html',n+' '+device+' servisi') for n in region['neighbors']]
        same=region['slug']+'-'+('klima' if device=='kombi' else 'kombi')+'-servisi.html'
        neighbor_links=''.join('<li>'+link(path,label,files)+'</li>' for path,label in neighbors if path in files)
        related=('<details class="editorial-neighbors"><summary>Komşu ilçeler ve diğer cihaz hizmeti</summary><ul>'+neighbor_links+'<li>'+link(same,place+' '+('klima' if device=='kombi' else 'kombi')+' servisi',files)+'</li></ul>'
                 '<p class="hybrid-data-source">İlçe sınırı verisi: © OpenStreetMap katkıda bulunanlar; türev komşuluk verisi ODbL 1.0. Lisans: https://opendatacommons.org/licenses/odbl/1-0/</p></details>')
    else:
        geography='<section class="editorial-geography"><h2>'+escape(place)+' adresinizin ilçe bağlantıları</h2><p>'+escape(page['neighborhood_intro'])+'</p><nav class="editorial-guides">'
        for district in region['districts']:
            for kind in ['kombi','klima']:
                path=slug(district)+'-'+kind+'-servisi.html'
                geography+=link(path+'#bolge-rehberi',district+' '+kind+' servisi',files)
        geography+='</nav></section>';related=''
    technical=('<section id="yerel-teknik-ornek" class="editorial-model-reference"><h2>Cihazın modeline göre teknik rehber</h2><p>'
               +link('model-ariza-kodlari.html','Model ve arıza kodu rehberini açın',files)+' · '
               +link('ariza-rehberi.html','Belirti rehberlerini inceleyin',files)+'</p></section>')
    rendered=header+'<div data-editorial-selector></div>'+body+geography+technical+related
    ids=set(re.findall(r'\bid="([^"]+)"',rendered))|{'bolge-rehberi'}
    aliases=''.join('<span id="'+escape(ident,quote=True)+'" class="editorial-anchor" aria-hidden="true"></span>' for ident in sorted(old_ids-ids))
    cta='<section class="editorial-cta">'+aliases+'<h2>'+escape(page['cta']['heading'])+'</h2><p>'+escape(page['cta']['text'])+'</p><div class="at-actions"><a class="at-btn at-btn-primary" href="tel:05346225515">0534 622 55 15</a><a class="at-btn" href="./#ai-usta">AI Usta ile ilerle</a></div></section>'
    return ('<!-- HYBRID-REGION:START --><section id="bolge-rehberi" class="hybrid-region editorial-region" data-editorial-route="'+escape(page['route'],quote=True)+'" data-hybrid-region="'+escape(place,quote=True)+'" data-device="'+device+'">'+rendered+cta+'</section><!-- HYBRID-REGION:END -->')

def apply_regions(files):
    data=load_regions();pages=load_editorial();changed=[];old_body_hashes={}
    all_regions=[]
    for region in data['districts']:
        for device in ['kombi','klima']:all_regions.append((region['slug']+'-'+device+'-servisi.html',region,device))
    for region in data['localities']:all_regions.append((region['slug']+'-servisi.html',region,'mixed'))
    expected={row[0] for row in all_regions}
    if set(pages)!=expected:raise ValueError('Editorial route inventory differs from the 55 source regional routes.')
    for filename,region,device in all_regions:
        page=pages[filename];text=files[filename].decode();ranges=Ranges(text)
        old=next(node for node in ranges.nodes if node['tag']=='div' and 'at-content' in node['attrs'].get('class','').split())
        previous=text[old['start']:old['end']];old_ids=set(re.findall(r'\bid=["\']([^"\']+)',previous))
        old_body_hashes[filename]=hashlib.sha256(previous.encode()).hexdigest()
        content=_region_content(page,region,device,files,old_ids)
        text=replace_element(text,lambda n:n['tag']=='div' and 'at-content' in n['attrs'].get('class','').split(),content,True)
        text,count=re.subn(r'<p\b(?=[^>]*class="[^"]*\bat-lead\b)[^>]*>.*?</p>',lambda m:'<p class="at-lead">'+escape(page['lead'])+'</p>',text,count=1,flags=re.S)
        if count!=1:raise ValueError('Regional hero lead missing: '+filename)
        aside='<aside class="at-aside editorial-aside"><p class="at-eyebrow">'+escape(region['name'])+'</p><h2>'+escape(page['cta']['heading'])+'</h2><p>'+escape(page['cta']['text'])+'</p><div class="at-actions"><a class="at-btn at-btn-primary" href="tel:05346225515">Ustamızı ara</a><a class="at-btn" href="./#ai-usta">AI Usta</a></div><nav class="at-toc" aria-label="Bu sayfada">'+''.join('<a href="#'+escape(s.get('id') or 'bolum-'+str(i+1),quote=True)+'">'+escape(s['heading'])+'</a>' for i,s in enumerate(page['sections']))+'</nav></aside>'
        text=replace_element(text,lambda n:n['tag']=='aside' and 'at-aside' in n['attrs'].get('class','').split(),aside)
        def description(m):return m['start']+escape(page['description'],quote=True)+m['end']
        text=re.sub(r'(?P<start><meta\s+(?:name="description"|property="og:description")\s+content=")(?P<body>[^"]*)(?P<end>">)',description,text)
        text=re.sub(r'<link\b[^>]*href="assets/editorial\.css[^"]*"[^>]*>','',text)
        text=text.replace('</head>','<link rel="stylesheet" href="assets/editorial.css"></head>',1)
        files[filename]=text.encode();changed.append(filename)
        if device in {'kombi','klima'}:region.setdefault('leads',{})[device]=page['lead']
        else:region['lead']=page['lead']
    for region in data['districts']:
        region.pop('notes',None);region.pop('address_note',None)
    for region in data['localities']:region.pop('notes',None)
    files['assets/hybrid-regions.json']=(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n').encode()
    files['assets/editorial.css']=(ROOT/'assets/editorial.css').read_bytes()
    return {'district_pages':50,'locality_pages':5,'neighborhood_records':sum(len(r['neighborhoods']) for r in data['districts']),
            'unique_leads':len({p['lead'] for p in pages.values()}),'static_neighborhood_anchors':1198,'region_routes':changed,
            'independently_authored_bodies':len(pages),'legacy_regional_main_bodies_replaced':len(changed),
            'old_summary_matrices_removed':50,'rotating_note_pool_removed':True,'old_body_sha256':old_body_hashes,
            'data_source':'hybrid/data/editorial/','geography_source':'hybrid/data/regions.json','public_data':'assets/hybrid-regions.json',
            'indexing_guarantee':False,'statistical_local_fault_claims':False}
