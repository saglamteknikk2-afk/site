import importlib.util
import json
from pathlib import Path
import re
import unittest
import zipfile
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'hybrid'))
spec=importlib.util.spec_from_file_location('regions',ROOT/'hybrid/regions.py')
regions=importlib.util.module_from_spec(spec);spec.loader.exec_module(regions)

class RegionTests(unittest.TestCase):
    def test_inventory_and_edges(self):
        data=regions.load_regions(); rows=data['districts'];names={r['name'] for r in rows}
        self.assertEqual(len(rows),25);self.assertEqual(sum(len(r['neighborhoods']) for r in rows),599)
        self.assertEqual(len(data['localities']),5)
        graph={r['name']:r['neighbors'] for r in rows}
        for name,adj in graph.items():
            self.assertTrue(set(adj)<=names)
            for n in adj:self.assertIn(name,graph[n])
        self.assertEqual(set(graph['Küçükçekmece']),{'Avcılar','Başakşehir','Bağcılar','Bahçelievler','Bakırköy'})

    def test_render_is_static_and_preserves_codes(self):
        with zipfile.ZipFile(ROOT/'saglamkombiklima-seo.zip') as z:
            files={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
        model_tables={n:re.findall(r'<table\b.*?</table>',v.decode(),re.S) for n,v in files.items() if n.endswith('-ariza-kodlari.html')}
        report=regions.apply_regions(files)
        self.assertEqual(report['unique_leads'],55)
        self.assertEqual(report['neighborhood_records'],599)
        for n in report['region_routes']:
            text=files[n].decode();self.assertIn('id="bolge-rehberi"',text)
            self.assertNotIn('data-st-master-matrix',text)
            self.assertNotIn('class="at-summary"',text)
            self.assertNotIn('class="hybrid-region-note"',text)
            self.assertIn('class="editorial-body"',text)
        for name,tables in model_tables.items():
            self.assertEqual(tables,re.findall(r'<table\b.*?</table>',files[name].decode(),re.S))
        k=files['kucukcekmece-kombi-servisi.html'].decode()
        self.assertIn('id="mahalle-atakent"',k)
        self.assertIn('data-hybrid-neighborhood="Atakent"',k)
        self.assertIn('ODbL 1.0',k)
        snapshot=dict(files);regions.apply_regions(files);self.assertEqual(snapshot,files)

if __name__=='__main__':unittest.main()
