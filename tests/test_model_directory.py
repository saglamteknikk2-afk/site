import importlib.util
import json
from pathlib import Path
import unittest
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('model_directory', ROOT/'scripts/model_directory.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ModelDirectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verified=json.loads((ROOT/'overrides/assets/verified-faults.json').read_text())
        cls.registry=json.loads((ROOT/'overrides/assets/brand-registry.json').read_text())
        cls.data=module.build(cls.verified,cls.registry)

    def test_exact_manual_names_keep_their_own_scope(self):
        by_id={m['id']:m for m in self.verified['models']}
        for row in self.data['entries']:
            if row.get('verified_model_id'):
                m=by_id[row['verified_model_id']]
                self.assertEqual(row['device'],m['device'])
                self.assertEqual(row['brand'],m['brand'])
                self.assertIn(module.key(row['name']),[module.key(n) for n in m['model_names']])
                self.assertIsNot(m.get('matchable'),False)
                self.assertIsNot(m['manual'].get('source_available'),False)

    def test_catalogue_names_never_invent_a_fault_table(self):
        self.assertEqual(self.data['policy']['new_fault_definitions'],0)
        for row in self.data['entries']:
            self.assertNotIn('codes',row)
            if row['status']=='catalogue-name-only':
                self.assertNotIn('verified_model_id',row)
                self.assertEqual(row['market'],'TR')
                self.assertIn(row['kind'],['series','model'])
                self.assertTrue(row['source_url'].startswith('https://'))

    def test_old_and_current_vaillant_models_are_separate_names(self):
        rows=[r for r in self.data['entries'] if r['brand']=='Vaillant' and r['device']=='kombi']
        self.assertGreaterEqual(len(rows),25)
        names={r['name']:r for r in rows}
        self.assertIn('VUW TR 202/3-3',names)
        self.assertIn('ecoTEC intro VUW 24/24 AS/2-1 (H-TR)',names)
        self.assertNotIn('verified_model_id',names['ecoTEC intro VUW 24/24 AS/2-1 (H-TR)'])
        self.assertNotIn('verified_model_id',names['turboTEC pro'])

    def test_registry_gaps_are_disclosed_and_not_filled_with_guesses(self):
        self.assertFalse(self.data['policy']['complete_market_inventory'])
        gaps={(g['device'],g['brand']):g for g in self.data['coverage']['gaps']}
        self.assertIn(('kombi','Isısan'),gaps)
        self.assertEqual(gaps[('kombi','Isısan')]['reason'],'device-label-manufacturer-required')

    def test_generated_files_stay_synchronized(self):
        self.assertEqual(json.loads((ROOT/'overrides/assets/model-directory.json').read_text()),self.data)
        self.assertEqual((ROOT/'overrides/assets/model-directory.js').read_text(),module.javascript(self.data))

    def test_no_duplicate_device_brand_name_or_non_https_source(self):
        identities=[(r['device'],module.key(r['brand']),module.key(r['name'])) for r in self.data['entries']]
        self.assertEqual(len(identities),len(set(identities)))
        for row in self.data['entries']:
            self.assertEqual(urlparse(row['source_url']).scheme,'https')
            self.assertTrue(urlparse(row['source_url']).hostname)


if __name__=='__main__':
    unittest.main()
