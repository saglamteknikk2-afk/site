"""Version changed public resources so a new HTML page cannot reuse old application code."""
from html import escape,unescape
from urllib.parse import urlsplit,parse_qsl,urlencode
import hashlib,json,posixpath,re

def version_assets(files):
    data_path='assets/hybrid-matrix-data.json';js='assets/hybrid-matrix.js'
    if data_path in files and js in files:
        digest=hashlib.sha256(files[data_path]).hexdigest()[:12]
        text=files[js].decode()
        text=re.sub(r'(["\'])hybrid-matrix-data\.json(?:\?v=[0-9a-f]+)?\1',
                    lambda m:m[1]+'hybrid-matrix-data.json?v='+digest+m[1],text)
        files[js]=text.encode()
    hashes={name:hashlib.sha256(data).hexdigest()[:12] for name,data in files.items()
            if posixpath.splitext(name)[1] in {'.js','.css','.json','.webp','.png','.svg','.woff2'}}
    changed=0
    def url(value,name):
        parsed=urlsplit(value)
        if parsed.scheme or parsed.netloc or not parsed.path:return value
        path=posixpath.normpath(posixpath.join(posixpath.dirname(name),parsed.path))
        if path not in hashes:return value
        query=[(k,v) for k,v in parse_qsl(parsed.query,keep_blank_values=True) if k!='v']
        query.append(('v',hashes[path]))
        return parsed.path+'?'+urlencode(query)+('#'+parsed.fragment if parsed.fragment else '')
    for name,data in list(files.items()):
        if not name.endswith('.html') or name.startswith('inceleme/'):continue
        text=data.decode()
        def attribute(m):
            nonlocal changed
            before=unescape(m['value']);after=url(before,name)
            if before==after:return m[0]
            changed+=1
            return m['key']+'='+m['quote']+escape(after,quote=True)+m['quote']
        text=re.sub(r'(?P<key>src|href)=(?P<quote>["\'])(?P<value>.*?)(?P=quote)',attribute,text)
        def diagnostics(m):
            nonlocal changed
            values=json.loads(unescape(m['value']));values=[url(v,name) for v in values]
            changed+=len(values)
            return 'data-diagnostic-sources='+m['quote']+escape(json.dumps(values,separators=(',',':')),quote=True)+m['quote']
        text=re.sub(r'data-diagnostic-sources=(?P<quote>["\'])(?P<value>.*?)(?P=quote)',diagnostics,text)
        files[name]=text.encode()
    return {'resource_references_versioned':changed,'strategy':'SHA-256 prefix of actual public resource bytes'}
