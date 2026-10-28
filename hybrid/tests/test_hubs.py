import importlib.util,json,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hubs import apply_hubs,model_local
from regions import apply_regions
from source import load_source

class HubsTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.files,_=load_source(ROOT.parent)
  # Production pipeline retires these offers before this module.
  for p in ['klima-montaji.html','klima-sokumu.html']:
   cls.files[p]=re.sub(rb'<meta name="robots" content="[^"]*">',b'<meta name="robots" content="noindex,follow">',cls.files[p])
   if b'noindex' not in cls.files[p]:cls.files[p]=cls.files[p].replace(b'</head>',b'<meta name="robots" content="noindex,follow"></head>')
  apply_regions(cls.files);cls.metrics=apply_hubs(cls.files)
 def test_neighborhoods_reach_content_not_form(self):
  text=self.files['bolgeler.html'].decode()
  self.assertNotIn('servis-sec.html#ilce=',text)
  self.assertIn('kucukcekmece-kombi-servisi.html#mahalle-atakent',text)
  self.assertIn('id="mahalle-atakent"',self.files['kucukcekmece-kombi-servisi.html'].decode())
 def test_all_regions_compact_widget_and_static_fallback(self):
  self.assertEqual(self.metrics['region_widgets'],55)
  self.assertEqual(self.metrics['indexable_orphans'],[])
  for n in ['avcilar-kombi-servisi.html','avcilar-klima-servisi.html','sefakoy-servisi.html']:
   t=self.files[n].decode();self.assertEqual(t.count('data-hybrid-matrix '),1)
   self.assertIn('<noscript>',t);self.assertIn('class="hybrid-bridges"',t)
   self.assertLess(t.index('data-hybrid-matrix '),t.index('class="at-summary"') if 'class="at-summary"' in t else len(t))
 def test_scoped_model_choices_exclude_foreign_and_invalid_pages(self):
  d=json.loads(self.files['assets/hybrid-matrix-data.json']);paths={m['path'] for m in d['models']}
  self.assertIn('baymak-kombi-duotec-33-42-45-ariza-kodlari.html',paths)
  self.assertFalse(any('-gb-ie-' in p or '-us-ca-' in p or '-ru-by-' in p or '-he-pl-' in p for p in paths))
  self.assertFalse(any(n['path'] in {'klima-montaji.html','klima-sokumu.html'} for device in d['devices'].values() for n in device['needs']))
  for m in d['models']:
   text=self.files[m['path']].decode()
   self.assertIn('id="kodlar"',text)
   for c in m['codes']:
    self.assertRegex(text,'id=["\']'+re.escape(c['anchor'])+'["\']')
 def test_scope_has_known_local_routes_only(self):
  d=json.loads(self.files['assets/hybrid-matrix-data.json']);self.assertEqual(sum(len(x['neighborhoods']) for x in d['districts']),599)
  for row in d['brand_routes']:self.assertIn(row['path'],self.files)
  self.assertEqual(len(d['districts']),25)
  self.assertNotIn('klima-montaji.html',d['routes'])
 def test_regionfinder_climate_preserves_meaningful_anchor(self):
  self.assertIn("record.href.includes('#mahalle-')",self.files['assets/premium-regions.js'].decode())

if __name__=='__main__':unittest.main()
