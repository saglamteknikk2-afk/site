"""Retain optional matrix selections in the existing service-ticket workflow."""
from __future__ import annotations

import re

MARKER = '// HYBRID-SERVICE-HANDOFF:v1'
FRAGMENT = r'''  function fragment(){
    // HYBRID-SERVICE-HANDOFF:v1
    // A hash is UI state, not a new indexable neighbourhood or error-code URL.
    const p=new URLSearchParams(location.search||'');
    new URLSearchParams(location.hash.slice(1)).forEach((value,key)=>p.set(key,value));
    const s=selection(),requested=p.get('cihaz'),device=data.devices[requested]?requested:s.device;
    if(!['cihaz','ilce','mahalle','marka','semt','islem','belirti','ariza','model','kod','code','arama'].some(k=>p.has(k))){update();return}
    revision++;
    const query=(p.get('arama')||'').slice(0,800),inferred=query?window.STResolveQuery(data,query,device):{};
    const item=data.devices[device],need=(p.get('belirti')||p.get('ariza')||'').slice(0,200);
    const requestedService=item.services.find(row=>row.name===need);
    const requestedSymptom=item.symptoms.find(row=>row.name===need);
    apply({device,district:p.get('ilce')||inferred.district||s.district,brand:p.get('marka')||inferred.brand||s.brand,neighborhood:p.get('mahalle')||inferred.neighborhood||s.neighborhood,locality:p.get('semt')||inferred.locality||s.locality,path:p.get('islem')||requestedService?.path||inferred.path||'',symptom:requestedSymptom?.name||inferred.symptom||'',query});
    const explicitModel=p.has('model')||p.has('kod')||p.has('code');
    if(explicitModel){el('svcModel').value=[p.get('model'),p.get('kod')||p.get('code')].filter(Boolean).join(' · ').slice(0,120)}
    else if(query){el('svcModel').value=[inferred.model,inferred.error_code].filter(Boolean).join(' · ').slice(0,120)}
    if(query||need){
      const detail=[query,need&&!requestedService&&!requestedSymptom?'Belirti: '+need:''].filter(Boolean);
      el('svcDetail').value=[...new Set(detail)].join('\n').slice(0,800);
    }
    if(query)el('svcQuery').value=query;
    update(true);
    if(location.hash){box.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'})}
  }
'''


def apply_service_handoff(files: dict[str, bytes]) -> dict:
    changed = []
    for name in ['assets/servis-sec.js', 'servis-sec.js']:
        if name not in files:
            continue
        source = files[name].decode('utf-8')
        if MARKER in source:
            continue
        pattern = r'  function fragment\(\)\{[\s\S]*?\n  \}\n(?=  deviceOptions\(box\.dataset\.defaultDevice)'
        source, count = re.subn(pattern, lambda _: FRAGMENT, source, count=1)
        if count != 1:
            raise ValueError('Unexpected service selection source; refusing an unverified handoff patch: ' + name)
        files[name] = source.encode('utf-8')
        changed.append(name)
    if not any(name in files for name in ['assets/servis-sec.js', 'servis-sec.js']):
        raise ValueError('Missing service selection script.')
    return {'files': changed, 'preserved_context': ['device', 'district', 'neighborhood', 'brand', 'optional model', 'optional code', 'symptom or service'],
            'destination': 'Existing service page, WhatsApp message and ticket payload; no provider calls during build.'}
