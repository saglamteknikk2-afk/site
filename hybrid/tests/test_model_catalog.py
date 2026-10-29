"""Keep catalogue identification separate from verified per-model code meaning."""
from pathlib import Path
import json,re,subprocess,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from source import load_source
from model_catalog import apply_model_catalog,identity

class ModelCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files,_=load_source(ROOT.parent)
        cls.original=dict(cls.files)
        cls.metrics=apply_model_catalog(cls.files)
        cls.catalog=json.loads(cls.files['assets/model-directory.json'])

    def test_all_identification_names_share_unique_keys_and_are_available_to_directory(self):
        rows=self.catalog['entries'];keys=[identity(r['device'],r['brand'],r['name']) for r in rows]
        self.assertEqual(len(keys),len(set(keys)))
        self.assertEqual(len({r['id'] for r in rows}),len(rows))
        vaillant=[r for r in rows if r['device']=='kombi' and r['brand']=='Vaillant']
        self.assertGreaterEqual(len(vaillant),30)
        self.assertGreaterEqual(sum(bool(r.get('verified_model_id')) for r in vaillant),10)
        self.assertIn(b'assets/model-directory.js',self.files['model-ariza-kodlari.html'])
        self.assertIn(b'STModelDirectory?.list',self.files['assets/model-browser.js'])

    def test_original_code_tables_are_not_rewritten_as_other_models(self):
        for route,data in self.original.items():
            if route.endswith('-ariza-kodlari.html') and route!='model-ariza-kodlari.html':self.assertEqual(self.files[route],data,route)

    def test_new_scopes_have_physical_tables_and_all_code_anchors(self):
        data=json.loads(self.files['assets/verified-faults.json'])
        added=[m for m in data['models'] if m['path'].lstrip('/') in self.metrics['new_routes']]
        self.assertGreaterEqual(len(added),13)
        for model in added:
            self.assertFalse(model['path'].startswith('/'))
            html=self.files[model['path'].lstrip('/')].decode()
            self.assertIn(model['brand'],html)
            for row in model['codes']:
                self.assertIn('id="'+row['anchor']+'"',html)
                self.assertIn(row['meaning'].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'),html)

    def test_actual_js_preserves_different_f73_meanings_and_no_missing_code_fallback(self):
        script="const vm=require('node:vm');let s='';process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>{const d=JSON.parse(s),c={window:{ST_VERIFIED_FAULTS:d.data}};vm.createContext(c);vm.runInContext(d.js,c);const lookup=(id,code)=>c.window.STFaults.lookup({device:'kombi',brand:'Vaillant',model_id:id,code});process.stdout.write(JSON.stringify({pure:lookup('vaillant-kombi-ecotec-pure-236-286-7-2','F73'),intro:lookup('vaillant-kombi-ecotec-intro-as2-1','F73'),plus:lookup('vaillant-kombi-ecotec-plus-cs1-5','F073')}));});"
        result=subprocess.run(['node','-e',script],input=json.dumps({'data':json.loads(self.files['assets/verified-faults.json']),'js':self.files['assets/fault-lookup.js'].decode()}),text=True,capture_output=True,check=True)
        row=json.loads(result.stdout)
        self.assertTrue(row['pure']['verified']);self.assertTrue(row['intro']['verified'])
        self.assertNotEqual(row['pure']['definition']['meaning'],row['intro']['definition']['meaning'])
        self.assertFalse(row['plus']['verified']);self.assertEqual(row['plus']['status'],'code-not-covered')

if __name__=='__main__':unittest.main()
