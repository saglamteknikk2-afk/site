"""Bounded, source-based acceptance for the hybrid static build.

Passing this audit is evidence about the supplied files, not about Google's index,
ad auction quality, live PHP configuration, Telegram delivery or Gemini accuracy.
"""
from __future__ import annotations
from collections import defaultdict, deque
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit, parse_qs
import argparse
import base64
import hashlib
import html
import importlib.util
import json
import posixpath
import re
import xml.etree.ElementTree as ET

try:
    from .semantics import Page, SCRIPT, BUSINESS_ADDRESS, BUSINESS_ID, POLICY_PAGES, NON_SERVICE_HUBS
except ImportError:
    from semantics import Page, SCRIPT, BUSINESS_ADDRESS, BUSINESS_ID, POLICY_PAGES, NON_SERVICE_HUBS

ORIGIN = 'https://saglamkombiklima.com.tr/'
HOSTS = {'saglamkombiklima.com.tr', 'www.saglamkombiklima.com.tr'}
CONTACT_HOSTS = {'wa.me', 'api.whatsapp.com', 'web.whatsapp.com'}
EXCLUDE = {'404.html', 'owner-admin.html', 'servis-takip.html', 'servis-sec.html',
           'teknik-rapor.html', 'technical-report.html', 'rapor.html', 'icerik-inceleme.html'}
TEXT_SUFFIXES = {'.js','.php','.json','.txt','.html','.yml','.yaml','.env'}
SECRET_PATTERNS = {
    'google_api_key': r'AIza[0-9A-Za-z_-]{35}',
    'telegram_bot_token': r'(?<!\d)\d{7,12}:[A-Za-z0-9_-]{30,50}',
    'private_key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
}

def _without_inline_images(text):
    """Exclude only image data URI payloads from literal credential scanning.

    A large binary image's base64 can accidentally contain key-shaped ASCII.
    Keep all surrounding prose, HTML attributes and scripts in the scan. Require
    a recognized image signature; an arbitrary data string cannot hide a key.
    """
    def replace(match):
        payload=re.sub(r'\s+','',match['payload'])
        try:head=base64.b64decode(payload[:128]+'='*((-len(payload[:128]))%4),validate=True)
        except (ValueError,TypeError):return match[0]
        recognizable=(head.startswith((b'\xff\xd8\xff',b'\x89PNG\r\n\x1a\n',b'GIF87a',b'GIF89a'))
                      or head.startswith(b'RIFF') and head[8:12]==b'WEBP'
                      or b'ftypavif' in head[:32]
                      or head.lstrip().startswith((b'<svg',b'<?xml')))
        return match['header']+'[image-payload]' if recognizable else match[0]
    return re.sub(r'(?P<header>data:image/[A-Za-z0-9.+-]+;base64,)(?P<payload>[A-Za-z0-9+/=\r\n]+)',replace,text)

def ordinary(name):
    return (name.endswith('.html') and '/' not in name and name not in EXCLUDE
            and not name.startswith(('google','yandex')))

def slug(value):
    value=str(value).translate(str.maketrans('çğıöşüÇĞİÖŞÜ','cgiosuCGIOSU')).lower()
    return re.sub(r'[^a-z0-9]+','-',value).strip('-')

def _graph(payload):
    if isinstance(payload, list):return payload
    if isinstance(payload, dict):return payload.get('@graph',[payload])
    return []

def _types(node):
    types=node.get('@type',[])
    return {types} if isinstance(types,str) else set(types)

def _normalize(text):
    return ' '.join(html.unescape(re.sub('<[^>]+>',' ',text)).split())

def _eligible(name,page):
    if not ordinary(name) or 'noindex' in page.meta('robots').lower():return False
    expected=ORIGIN if name=='index.html' else ORIGIN+name
    return page.canonical()==expected

def _read_js_json(files,name,var):
    source=files.get(name,b'').decode('utf-8')
    match=re.search(r'window\.'+re.escape(var)+r'\s*=\s*(\{.*?\});',source,re.S)
    return json.loads(match[1]) if match else None

def _all_refs(value):
    if isinstance(value,dict):
        if set(value)=={'@id'}:yield value['@id']
        for child in value.values():yield from _all_refs(child)
    elif isinstance(value,list):
        for child in value:yield from _all_refs(child)

def audit(files:dict[str,bytes],mode='production',baseline=None,strict=True):
    """Return acceptance evidence; raise on actual blockers when *strict* is true.

    ``baseline`` is optional original source files, used solely to assert that
    pre-existing model-code anchors and table facts have not been silently lost.
    No customer fields, credentials, or secret matches are included in output.
    """
    if mode not in {'production','preview'}:raise ValueError('Unknown build mode')
    errors=[]; warnings=[]; docs={}; graphs={}; schema_errors=[]
    for name,data in files.items():
        if not name.endswith('.html') or name.startswith(('inceleme/','review/')):continue
        try:docs[name]=Page(data.decode('utf-8'))
        except Exception as exc:
            errors.append({'kind':'html_parse','page':name,'error':type(exc).__name__});continue
        nodes=[]
        for match in SCRIPT.finditer(data.decode('utf-8')):
            try:nodes.extend(_graph(json.loads(match[1])))
            except (ValueError,TypeError):schema_errors.append({'page':name,'kind':'invalid_json_ld'})
        graphs[name]=nodes
    errors.extend(schema_errors)
    ids={name:{e.attrs['id'] for e in page.root.all() if e.attrs.get('id')}
         | {e.attrs['name'] for e in page.root.all('a') if e.attrs.get('name')}
         for name,page in docs.items()}
    links=defaultdict(set); incoming=defaultdict(set); references=0; external_count=0
    selector_neighborhood_links=0
    for name,page in docs.items():
        for element in page.root.all():
            for attr in ('href','src','poster'):
                raw=element.attrs.get(attr)
                if not raw or raw.startswith(('data:','blob:','tel:','mailto:','sms:','javascript:')):continue
                if element.tag=='link' and 'canonical' in element.attrs.get('rel','').split():continue
                u=urlsplit(urljoin(ORIGIN+name,raw))
                if u.scheme not in {'http','https'}:continue
                if u.hostname not in HOSTS:
                    if element.tag=='a' and attr=='href' and u.hostname not in CONTACT_HOSTS:
                        external_count+=1;errors.append({'kind':'outbound_navigation','page':name,'host':u.hostname})
                    continue
                target=unquote(u.path).lstrip('/') or 'index.html'
                if target.startswith('site/'):target=target[5:] or 'index.html'
                if target.endswith('/'):target+='index.html'
                if target.endswith('.php') or target.startswith('__yonetim'):continue
                references+=1
                if target not in files:
                    errors.append({'kind':'missing_file','page':name,'target':target});continue
                anchor=unquote(u.fragment)
                if (anchor and '=' not in anchor and target in ids and anchor not in ids[target]
                    and not anchor.startswith(':~:text=')):
                    errors.append({'kind':'missing_anchor','page':name,'target':target+'#'+anchor})
                if element.tag=='a' and attr=='href' and target in docs:
                    links[name].add(target)
                    if target!=name:incoming[target].add(name)
                    params=parse_qs(u.fragment+'&'+u.query)
                    if target=='servis-sec.html' and params.get('mahalle'):selector_neighborhood_links+=1
    eligible={name for name,page in docs.items() if _eligible(name,page)}
    # Preview noindex is intentional: use the generated production inventory to
    # identify content nodes whose internal reachability still needs validation.
    if mode=='preview' and 'assets/hybrid-inventory.json' in files:
        inventory=json.loads(files['assets/hybrid-inventory.json'])
        eligible={x['path'] for x in inventory.get('pages',[]) if x.get('path') in docs}
    reached=set();queue=deque(['index.html'])
    while queue:
        current=queue.popleft()
        if current in reached:continue
        reached.add(current);queue.extend(links[current]-reached)
    orphan=sorted(eligible-reached)
    for name in orphan:errors.append({'kind':'orphan_content_page','page':name})
    sitemap_paths=set()
    if 'sitemap.xml' in files:
        try:
            xml=ET.fromstring(files['sitemap.xml'])
            sitemap_paths={unquote(urlsplit(n.text or '').path).lstrip('/') or 'index.html'
                           for n in xml.iter() if n.tag.endswith('loc')}
        except ET.ParseError:errors.append({'kind':'invalid_sitemap_xml'})
    elif mode=='production':errors.append({'kind':'missing_sitemap'})
    if mode=='production':
        for name in sorted(sitemap_paths-eligible):errors.append({'kind':'sitemap_ineligible','page':name})
        for name in sorted(eligible-sitemap_paths):errors.append({'kind':'sitemap_missing_content','page':name})
    # Current canonical pages are source truth, not an arbitrary target count.
    if 'assets/hybrid-inventory.json' in files:
        inventory=json.loads(files['assets/hybrid-inventory.json'])
        inventory_paths={x['path'] for x in inventory.get('pages',[])}
        if inventory_paths!=eligible:errors.append({'kind':'inventory_mismatch','missing':sorted(eligible-inventory_paths),'extra':sorted(inventory_paths-eligible)})
    catalogue_routes_checked=0;catalogue_code_anchors_checked=0
    for source in ('assets/hybrid-routes.json','assets/hybrid-matrix-data.json'):
        if source not in files:continue
        catalogue=json.loads(files[source])
        def check_route(raw):
            nonlocal catalogue_routes_checked
            if not isinstance(raw,str):return
            u=urlsplit(raw)
            if u.scheme or u.netloc:
                errors.append({'kind':'nonlocal_generated_route','page':source});return
            target=unquote(u.path).lstrip('/')
            catalogue_routes_checked+=1
            if target not in files:errors.append({'kind':'generated_route_missing','page':source,'target':target})
        def visit_routes(value):
            if isinstance(value,dict):
                for key,child in value.items():
                    if key=='path':check_route(child)
                    elif key=='routes' and isinstance(child,list):
                        for route in child:check_route(route)
                    else:visit_routes(child)
            elif isinstance(value,list):
                for child in value:visit_routes(child)
        if isinstance(catalogue,list):
            for path in catalogue:check_route(path)
        else:visit_routes(catalogue)
        if isinstance(catalogue,dict):
            for model in catalogue.get('models',[]):
                target=str(model.get('path','')).lstrip('/').split('#')[0].split('?')[0]
                for code in model.get('codes',[]):
                    anchor=code.get('anchor')
                    if not anchor:continue
                    catalogue_code_anchors_checked+=1
                    if anchor not in ids.get(target,set()):errors.append({'kind':'generated_code_anchor_missing','page':source,'target':target+'#'+anchor})
    all_graph_ids={node.get('@id') for nodes in graphs.values() for node in nodes if isinstance(node,dict) and node.get('@id')}
    schema_counts={'business_pages':0,'service_pages':0,'faq_pages':0,'faq_questions':0}
    for name,nodes in graphs.items():
        page=docs[name]
        if not ordinary(name):continue
        businesses=[n for n in nodes if isinstance(n,dict) and 'LocalBusiness' in _types(n)]
        if len(businesses)!=1:
            errors.append({'kind':'business_schema_count','page':name,'count':len(businesses)})
        else:
            schema_counts['business_pages']+=1
            b=businesses[0]
            if b.get('@id')!=BUSINESS_ID or b.get('address')!=BUSINESS_ADDRESS:
                errors.append({'kind':'business_facts_mismatch','page':name})
            if 'priceRange' in b or 'geo' in b:
                warnings.append({'kind':'business_fact_needs_verification','page':name})
        services=[n for n in nodes if isinstance(n,dict) and 'Service' in _types(n)]
        faqs=[n for n in nodes if isinstance(n,dict) and 'FAQPage' in _types(n)]
        schema_counts['service_pages']+=bool(services);schema_counts['faq_pages']+=bool(faqs)
        if len(services)>1:errors.append({'kind':'duplicate_service_schema','page':name})
        if len(faqs)>1:errors.append({'kind':'duplicate_faq_schema','page':name})
        if name in POLICY_PAGES|NON_SERVICE_HUBS and services:
            errors.append({'kind':'service_on_non_service_page','page':name})
        if mode=='production' and name not in eligible and (services or faqs):
            errors.append({'kind':'service_or_faq_on_ineligible_page','page':name})
        for service in services:
            if service.get('provider',{}).get('@id')!=BUSINESS_ID:errors.append({'kind':'service_provider_mismatch','page':name})
        visible=dict(page.faq())
        for faq in faqs:
            for q in faq.get('mainEntity',[]):
                schema_counts['faq_questions']+=1
                question=' '.join(q.get('name','').split())
                answer=' '.join(q.get('acceptedAnswer',{}).get('text','').split())
                if visible.get(question)!=answer:
                    errors.append({'kind':'faq_visible_parity','page':name,'question':question})
        for ref in _all_refs(nodes):
            if (ref.startswith(ORIGIN) and '#' in ref and ref not in all_graph_ids
                and ref.rsplit('#',1)[1] in {'service','hizmet','faq','business','isletme'}):
                errors.append({'kind':'dangling_schema_reference','page':name,'target':ref})
    regional={'districts':0,'district_service_pages':0,'locality_service_pages':0,'neighborhoods':0,'unique_authored_leads':0,'neighborhood_anchors':0}
    if 'assets/hybrid-regions.json' in files:
        data=json.loads(files['assets/hybrid-regions.json']);districts=data.get('districts',[]);localities=data.get('localities',[])
        leads=[]
        for row in districts:
            regional['districts']+=1;regional['neighborhoods']+=len(row.get('neighborhoods',[]))
            for device in ('kombi','klima'):
                name=row.get('slug',slug(row['name']))+'-'+device+'-servisi.html'
                if name not in docs:errors.append({'kind':'missing_regional_page','page':name});continue
                regional['district_service_pages']+=1
                lead=' '.join(row.get('leads',{}).get(device,'').split());leads.append(lead)
                if not lead or lead not in docs[name].root.text():errors.append({'kind':'regional_lead_not_rendered','page':name})
                for neighbor in row.get('neighbors',[]):
                    if neighbor not in {d['name'] for d in districts}:errors.append({'kind':'unknown_neighbor','page':name,'district':neighbor})
                for neighborhood in row.get('neighborhoods',[]):
                    anchor='mahalle-'+slug(neighborhood)
                    if anchor not in ids[name]:errors.append({'kind':'missing_neighborhood_anchor','page':name,'anchor':anchor})
                    else:regional['neighborhood_anchors']+=1
        for row in localities:
            name=row.get('slug',slug(row['name']))+'-servisi.html'
            if name not in docs:errors.append({'kind':'missing_locality_page','page':name})
            else:regional['locality_service_pages']+=1
            leads.append(' '.join(row.get('lead','').split()))
        regional['unique_authored_leads']=len(set(leads))
        if len(set(leads))!=len(leads):errors.append({'kind':'duplicate_authored_regional_lead'})
        service=_read_js_json(files,'assets/servis-verileri.js','ST_SERVICE_DATA')
        if service:
            pairs={(row['name'],n) for row in districts for n in row.get('neighborhoods',[])}
            expected={(n['district'],n['name']) for n in service.get('neighborhoods',[])}
            if pairs!=expected:errors.append({'kind':'neighborhood_source_inventory_mismatch','missing_count':len(expected-pairs),'extra_count':len(pairs-expected)})
        if selector_neighborhood_links:errors.append({'kind':'neighborhoods_still_link_to_form','links':selector_neighborhood_links})
    protected_model_tables=0;protected_code_anchors=0
    if baseline is not None:
        for name,data in baseline.items():
            if not name.endswith('-ariza-kodlari.html'):continue
            if name not in files:errors.append({'kind':'model_page_removed','page':name});continue
            old=data.decode('utf-8');new=files[name].decode('utf-8')
            anchors=set(re.findall(r'\bid=["\'](kod-[^"\']+)["\']',old))
            protected_code_anchors+=len(anchors)
            missing=anchors-ids.get(name,set())
            if missing:errors.append({'kind':'model_code_anchors_lost','page':name,'count':len(missing)})
            previous=[_normalize(t) for t in re.findall(r'<table\b[^>]*>.*?</table>',old,re.S|re.I)]
            current=[_normalize(t) for t in re.findall(r'<table\b[^>]*>.*?</table>',new,re.S|re.I)]
            for table in previous:
                if table not in current:errors.append({'kind':'model_table_fact_changed','page':name})
                else:protected_model_tables+=1
    sensitive=[]
    for name,data in files.items():
        parts=Path(name).parts
        if any(p in {'private','_private','.git'} for p in parts) or Path(name).suffix.lower() in {'.db','.sqlite','.sqlite3','.log','.env'} or Path(name).name.startswith('.env'):
            errors.append({'kind':'private_runtime_file','page':name})
        if Path(name).suffix.lower() in TEXT_SUFFIXES:
            text=_without_inline_images(data.decode('utf-8',errors='ignore'))
            for kind,pattern in SECRET_PATTERNS.items():
                if re.search(pattern,text):sensitive.append({'file':name,'kind':kind})
    errors.extend({'kind':'sensitive_pattern','file':x['file'],'pattern':x['kind']} for x in sensitive)
    if mode=='preview':
        for name,page in docs.items():
            if ordinary(name) and 'noindex' not in page.meta('robots').lower():errors.append({'kind':'preview_indexable_page','page':name})
        if any(name.endswith('.php') for name in files):errors.append({'kind':'preview_contains_php'})
        if not re.search(rb'Disallow:\s*/\s*(?:\n|$)',files.get('robots.txt',b'')):
            errors.append({'kind':'preview_robots_not_blocked'})
    else:
        for name,page in docs.items():
            source=files[name]
            if (b'seo-preview-guard.js' in source or b'id="st-preview-banner"' in source or b'data-st-mode="preview"' in source):
                errors.append({'kind':'production_contains_preview_controls','page':name})
    manifest_verified=None
    if 'build-info.json' in files:
        info=json.loads(files['build-info.json']);digest=hashlib.sha256()
        for name in sorted(n for n in files if n!='build-info.json'):
            digest.update(name.encode()+b'\0'+hashlib.sha256(files[name]).digest())
        manifest_verified=digest.hexdigest()==info.get('content_sha256')
        if not manifest_verified:errors.append({'kind':'content_manifest_mismatch'})
    result={'scope':'Static file, data and schema acceptance only; excludes live providers, Search Console and advertising outcomes',
            'mode':mode,'files':len(files),'html_documents':len(docs),'eligible_content_pages':len(eligible),
            'internal_references':references,'reachable_content_pages':len(eligible&reached),
            'orphans':orphan,'outbound_non_contact_anchors':external_count,
            'sitemap_pages':len(sitemap_paths),'schema':schema_counts,'regions':regional,
            'source_model_tables_preserved':protected_model_tables,'source_code_anchors_preserved':protected_code_anchors,
            'generated_catalogue_routes_checked':catalogue_routes_checked,
            'generated_catalogue_code_anchors_checked':catalogue_code_anchors_checked,
            'credential_pattern_matches':len(sensitive),'content_manifest_verified':manifest_verified,
            'warnings':warnings,'errors':errors,'status':'passed' if not errors else 'failed'}
    if errors and strict:
        summary='; '.join(x['kind']+(':'+x.get('page','')) for x in errors[:8])
        raise ValueError('Hybrid acceptance failed: '+summary+' ('+str(len(errors))+' issues)')
    return result

def load(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);parser.add_argument('--mode',choices=['production','preview'],default='production');parser.add_argument('--baseline',type=Path);parser.add_argument('--report',type=Path)
    args=parser.parse_args();result=audit(load(args.root),args.mode,load(args.baseline) if args.baseline else None,strict=False)
    serialized=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(serialized)
    print(serialized)
    raise SystemExit(bool(result['errors']))
