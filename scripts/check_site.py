#!/usr/bin/env python3
"""Check generated pages without network access or executing PHP."""
from __future__ import annotations
import argparse
import json
import re
from xml.etree import ElementTree
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids=[]; self.refs=[]; self.robots=[]; self.scripts=[]; self.h1=0; self.mode=''; self.jsonld=[]; self.ld_active=False; self.ld_buffer=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if a.get('id'): self.ids.append(a['id'])
        if tag=='h1': self.h1+=1
        if tag=='body': self.mode=a.get('data-st-mode','')
        if tag=='meta' and a.get('name','').lower()=='robots': self.robots.append(a.get('content',''))
        if tag=='script' and a.get('src'): self.scripts.append(a['src'])
        if tag=='script' and a.get('type','').lower()=='application/ld+json': self.ld_active=True;self.ld_buffer=[]
        for attr in ('href','src','action','poster'):
            if a.get(attr): self.refs.append((tag,attr,a[attr]))
        if a.get('srcset'):
            for candidate in a['srcset'].split(','):
                if candidate.strip():self.refs.append((tag,'srcset',candidate.split()[0]))
    def handle_data(self,data):
        if self.ld_active:self.ld_buffer.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self.ld_active:self.jsonld.append(''.join(self.ld_buffer));self.ld_active=False

def check(root: Path, mode: str, base_path: str='/site') -> dict:
    errors=[]; warnings=[]; refs=0; pages=0; noindex=0; schemas=0; id_cache={}
    if not (root/'index.html').is_file(): errors.append('Missing index.html')
    for path in sorted(root.rglob('*')):
        if not path.is_file(): continue
        rel=path.relative_to(root).as_posix()
        if path.suffix=='.svg':
            try:ElementTree.fromstring(path.read_bytes())
            except ElementTree.ParseError:errors.append(f'{rel}: invalid SVG XML')
        if mode=='preview' and (path.suffix in {'.php','.db','.sqlite','.env'} or path.name in {'owner-admin.html','owner-admin.js','trusted-proxies.json'}):
            errors.append(f'Private/server file in preview: {rel}')
        if path.suffix!='.html' or path.name=='owner-admin.html' or re.match(r'(google|yandex_).*\.html$', path.name): continue
        text=path.read_text(); page=Page(); page.feed(text); pages+=1
        for item,count in Counter(page.ids).items():
            if count>1: errors.append(f'{rel}: duplicate id {item}')
        for value in page.jsonld:
            try:json.loads(value);schemas+=1
            except (ValueError,TypeError):errors.append(f'{rel}: invalid JSON-LD')
        if page.h1 != 1: errors.append(f'{rel}: expected one H1, got {page.h1}')
        if any('noindex' in r.lower() for r in page.robots): noindex+=1
        if page.mode!=mode: errors.append(f'{rel}: missing/wrong build mode marker')
        if mode=='preview':
            if not any('noindex' in r.lower() for r in page.robots): errors.append(f'{rel}: noindex missing')
            if 'id="st-preview-banner"' not in text: errors.append(f'{rel}: preview banner missing')
            if not page.scripts or not page.scripts[0].endswith('/assets/preview-guard.js'): errors.append(f'{rel}: preview guard is not first script')
        elif 'st-preview-banner' in text or 'preview-guard.js' in text or 'static-preview' in text:
            errors.append(f'{rel}: preview controls leaked into production')
        for tag,attr,value in page.refs:
            parsed=urlsplit(value)
            if parsed.scheme or parsed.netloc: continue
            raw=unquote(parsed.path)
            if not raw:
                if parsed.fragment and unquote(parsed.fragment) not in page.ids:errors.append(f'{rel}: missing page anchor {value}')
                continue
            if mode=='preview' and raw.startswith('/'):
                if not (raw==base_path or raw.startswith(base_path+'/')):
                    errors.append(f'{rel}: unprefixed URL {value}'); continue
                raw=raw[len(base_path):] or '/'
            if mode=='production' and raw.startswith('/site/'):
                errors.append(f'{rel}: preview prefix in production URL {value}')
            target=(root/raw.lstrip('/')) if raw.startswith('/') else path.parent/raw
            target=target.resolve()
            if target.is_dir(): target=target/'index.html'
            if target.suffix=='.php' and mode=='preview': continue # guard prevents this operation
            refs+=1
            if not target.exists(): errors.append(f'{rel}: missing {attr} target {value}')
            elif parsed.fragment and target.suffix=='.html' and not (target.name in {'servis-sec.html','iletisim.html'} and '=' in unquote(parsed.fragment)):
                if target not in id_cache:
                    other=Page();other.feed(target.read_text());id_cache[target]=other.ids
                if unquote(parsed.fragment) not in id_cache[target]:errors.append(f'{rel}: missing target anchor {value}')
    if mode=='preview':
        robots=(root/'robots.txt').read_text() if (root/'robots.txt').exists() else ''
        if re.search(r'Disallow:\s*/\s*$', robots,re.M): errors.append('robots.txt blocks noindex crawling')
    report={'passed':not errors,'mode':mode,'visitor_pages':pages,'noindex_pages':noindex,'jsonld_blocks':schemas,'references_checked':refs,'errors':errors,'warnings':warnings}
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--mode',choices=['preview','production'],required=True);p.add_argument('--base-path',default='/site');p.add_argument('--report',type=Path);a=p.parse_args()
    r=check(a.directory.resolve(),a.mode,a.base_path.rstrip('/'))
    data=json.dumps(r,ensure_ascii=False,indent=2)+'\n'
    if a.report: a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(data)
    if a.report:
        shown={k:v for k,v in r.items() if k not in {'errors','warnings'}}
        shown.update(error_count=len(r['errors']),errors=r['errors'][:10],warning_count=len(r['warnings']))
        print(json.dumps(shown,ensure_ascii=False,indent=2))
    else:print(data,end='')
    raise SystemExit(0 if r['passed'] else 1)
if __name__=='__main__': main()
