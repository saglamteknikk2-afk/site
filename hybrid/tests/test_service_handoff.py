"""Exercise the real patched UI script through form/WhatsApp payload creation."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'hybrid'))
from service_handoff import MARKER, apply_service_handoff
from source import load_source

HARNESS = r'''
const fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const elements=new Map();
class Field{
  constructor(){this.value='';this.options=[];this.listeners={};this.dataset={};this.hidden=false;this.href='';}
  replaceChildren(...children){this.options=children;this.value=children[0]?.value||'';}
  get selectedOptions(){return this.options.filter(row=>row.value===this.value);}
  setAttribute(){} focus(){} scrollIntoView(){}
  addEventListener(type,fn){this.listeners[type]=fn;}
}
const el=id=>{if(!elements.has(id))elements.set(id,new Field());return elements.get(id)};
el('servisSecimi').dataset={defaultDevice:'kombi',compact:'true'};
const data={districts:['Küçükçekmece','Avcılar'],neighborhoods:[{district:'Küçükçekmece',name:'Atakent'},{district:'Avcılar',name:'Ambarlı'}],devices:{
  kombi:{label:'Kombi',brands:['Baymak','Bosch'],services:[{name:'Kombi servisi',path:'/kombi-servisi.html'},{name:'Kombi bakımı',path:'/kombi-bakimi.html'}],symptoms:[{name:'su akıtıyor',path:'/kombi-su-akitiyor.html'}]},
  klima:{label:'Klima',brands:['Baymak'],services:[{name:'Klima servisi',path:'/klima-servisi.html'}],symptoms:[{name:'soğutmuyor',path:'/klima-sogutmuyor.html'}]}
}};
let payload=null;
const ctx={URLSearchParams,Option:function(text,value){return {textContent:text,value}},
  document:{getElementById:el,addEventListener:(type,fn)=>{if(type==='DOMContentLoaded')ctx.ready=fn}},
  window:{ST_SERVICE_DATA:data,ST_ORGANIC_CATALOG:{published_routes:[]},STResolveQuery:()=>input.inferred||{},addEventListener:()=>{}},
  location:{hash:input.hash||'',search:input.search||''},matchMedia:()=>({matches:true}),
  stApi:async(action,value)=>{payload={action,value}},stRequestKey:()=> 'mock-request-key'};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),ctx);ctx.ready();
el('svcName').value='Test Müşteri';el('svcPhone').value='5340000000';
(async()=>{
  await el('svcTicketForm').listeners.submit({preventDefault(){},currentTarget:el('svcTicketForm')});
  process.stdout.write(JSON.stringify({model:el('svcModel').value,detail:el('svcDetail').value,
    district:el('svcDistrict').value,neighborhood:el('svcNeighborhood').value,brand:el('svcBrand').value,
    symptom:el('svcSymptom').value,device:el('svcDevice').value,service:el('svcService').value,
    whatsapp:decodeURIComponent(el('svcWhatsApp').href.split('?text=')[1]||''),payload}));
})().catch(error=>{console.error(error);process.exit(1)});
'''


class ServiceHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files, _ = load_source(ROOT)
        cls.files = {name: data for name, data in cls.files.items() if name in {'assets/servis-sec.js', 'servis-sec.js'}}
        apply_service_handoff(cls.files)

    def run_ui(self, **params):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'app.js').write_bytes(self.files['assets/servis-sec.js'])
            (root / 'input.json').write_text(json.dumps(params, ensure_ascii=False))
            result = subprocess.run(['node', '-e', HARNESS, str(root / 'app.js'), str(root / 'input.json')], capture_output=True, text=True, check=True)
            return json.loads(result.stdout)

    def test_matrix_model_code_symptom_reach_ticket_and_whatsapp(self):
        row = self.run_ui(hash='#cihaz=kombi&ilce=K%C3%BC%C3%A7%C3%BCk%C3%A7ekmece&mahalle=Atakent&marka=Baymak&model=Lambert+LPY+33Fi&kod=E01&ariza=su+ak%C4%B1t%C4%B1yor')
        self.assertEqual(row['district'], 'Küçükçekmece')
        self.assertEqual(row['neighborhood'], 'Atakent')
        self.assertEqual(row['brand'], 'Baymak')
        self.assertEqual(row['model'], 'Lambert LPY 33Fi · E01')
        self.assertEqual(row['symptom'], 'su akıtıyor')
        self.assertEqual(row['payload']['action'], 'ticket')
        for text in ['Lambert LPY 33Fi', 'E01', 'su akıtıyor', 'Baymak']:
            self.assertIn(text, row['payload']['value']['issue'])
            self.assertIn(text, row['whatsapp'])

    def test_model_is_optional_and_service_alias_is_not_lost(self):
        row = self.run_ui(hash='#cihaz=kombi&ilce=Avc%C4%B1lar&mahalle=Ambarl%C4%B1&ariza=Kombi+bak%C4%B1m%C4%B1')
        self.assertEqual(row['model'], '')
        self.assertEqual(row['service'], '/kombi-bakimi.html')
        self.assertEqual(row['payload']['value']['device'], 'Kombi')
        self.assertIn('Kombi bakımı', row['payload']['value']['issue'])
        self.assertNotIn('Model / kod:', row['payload']['value']['issue'])

    def test_hash_overrides_query_and_unknown_symptom_is_preserved_as_text(self):
        row = self.run_ui(search='?cihaz=kombi&ilce=Avc%C4%B1lar&marka=Bosch',hash='#cihaz=klima&ilce=K%C3%BC%C3%A7%C3%BCk%C3%A7ekmece&marka=Baymak&model=Bilinmeyen&code=CH10&ariza=%3Cimg+src%3Dx%3E')
        self.assertEqual(row['device'], 'klima')
        self.assertEqual(row['brand'], 'Baymak')
        self.assertIn('CH10', row['model'])
        self.assertEqual(row['detail'], 'Belirti: <img src=x>')
        self.assertIn('Belirti: <img src=x>', row['payload']['value']['issue'])

    def test_explicit_model_and_code_take_precedence_over_inferred_query(self):
        row = self.run_ui(hash='#cihaz=kombi&ilce=Avc%C4%B1lar&model=Tam+model&kod=F22&arama=serbest+anlat%C4%B1m',inferred={'model':'Başka model','error_code':'E01','device':'kombi'})
        self.assertEqual(row['model'], 'Tam model · F22')
        self.assertIn('serbest anlatım', row['payload']['value']['issue'])
        self.assertNotIn('Başka model', row['payload']['value']['issue'])

    def test_idempotent_and_refuses_unknown_source(self):
        files = dict(self.files)
        self.assertEqual(apply_service_handoff(files)['files'], [])
        self.assertEqual(files, self.files)
        self.assertIn(MARKER.encode(), files['assets/servis-sec.js'])
        with self.assertRaises(ValueError):
            apply_service_handoff({'assets/servis-sec.js': b'function other(){}'})


if __name__ == '__main__':
    unittest.main()
