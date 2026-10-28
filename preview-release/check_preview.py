#!/usr/bin/env python3
"""Bounded static acceptance for the reviewed ZIP preview, not provider delivery."""
import hashlib, html, json, posixpath, sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote

class Document(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True);self.refs=[];self.ids=set();self.robots=[];self.scripts=[]
        self.ld=[];self.in_ld=False;self.payload='';self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.add(a['id'])
        if tag=='meta' and a.get('name')=='robots':self.robots.append(a.get('content',''))
        if tag=='script':
            if a.get('src'):self.scripts.append(a['src'])
            if a.get('type')=='application/ld+json':self.in_ld=True;self.payload=''
        for key in ['href','src','poster']:
            if a.get(key) and not (tag=='link' and a.get('rel')=='canonical'):
                self.refs.append((tag,key,a[key]))
    def handle_endtag(self,tag):
        if tag=='script' and self.in_ld:
            self.ld.append(json.loads(self.payload));self.in_ld=False
    def handle_data(self,data):
        if self.in_ld:self.payload+=data

def check(root):
    files={p.relative_to(root).as_posix():p for p in root.rglob('*') if p.is_file()}
    docs={n:Document(p.read_text()) for n,p in files.items() if n.endswith('.html')}
    issues=[];refs=0
    for n,d in docs.items():
        if n.startswith(('google','yandex','inceleme/')):continue
        if not any('noindex' in r for r in d.robots):issues.append([n,'preview must be noindex'])
        if not d.scripts or not d.scripts[0].endswith('assets/seo-preview-guard.js'):issues.append([n,'preview guard must run first'])
        for tag,key,value in d.refs:
            url=urlsplit(value)
            if url.scheme in {'tel','mailto','data','javascript','sms'}:continue
            if url.scheme or url.netloc:
                if tag=='a' and url.hostname not in {'wa.me','api.whatsapp.com'}:issues.append([n,'external navigation',value])
                continue
            path=unquote(url.path)
            if path.startswith('/site/'):path=path[6:]
            elif path.startswith('/'):issues.append([n,'unmounted root reference',value]);continue
            target=posixpath.normpath(posixpath.join(posixpath.dirname(n),path)) if path else n
            if target in {'.',''} or path.endswith('/'):target=target.rstrip('/')+'/index.html' if target not in {'.',''} else 'index.html'
            if target.endswith('.php'):continue # Removed backend; preview guard blocks requests/actions.
            refs+=1
            if target not in files:issues.append([n,'missing target',value]);continue
            anchor=unquote(url.fragment)
            if anchor and '=' not in anchor and target in docs and anchor not in docs[target].ids:
                issues.append([n,'missing anchor',value])
    if any(Path(n).suffix=='.php' for n in files):issues.append(['PHP must not be published'])
    if (root/'robots.txt').read_text()!='User-agent: *\nDisallow: /\n':issues.append(['preview robots mismatch'])
    info=json.loads((root/'build-info.json').read_text());digest=hashlib.sha256()
    for n in sorted(k for k in files if k!='build-info.json'):digest.update(n.encode()+b'\0'+hashlib.sha256(files[n].read_bytes()).digest())
    if digest.hexdigest()!=info['content_sha256']:issues.append(['content manifest mismatch'])
    result={'scope':'Static preview files and links only; no live backend/Telegram/Gemini delivery',
            'html_documents':len(docs),'internal_references':refs,'issues':issues,'source_archive_sha256':info['archive_sha256']}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if issues:raise SystemExit(1)
    return result

if __name__=='__main__':check(Path(sys.argv[1]))
