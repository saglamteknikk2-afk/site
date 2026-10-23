"""Check shared brand coverage without widening any manufacturer fault scope."""
import copy
import importlib.util
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


builder = module('brand_builder', ROOT / 'scripts/build_site.py')
registry_builder = module('brand_registry', ROOT / 'scripts/brand_registry.py')


class BrandRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = builder.archive_files(ROOT)
        builder.overlay(cls.original, ROOT / 'overrides')
        cls.files = copy.copy(cls.original)
        cls.report = registry_builder.build_registry(cls.files)
        cls.registry = json.loads(cls.files['assets/brand-registry.json'])
        cls.services = json.loads(cls.files['assets/servis-katalog.json'])

    def test_existing_device_brands_and_aliases_retained(self):
        original = json.loads(self.original['assets/servis-katalog.json'])
        for device, config in original['devices'].items():
            self.assertTrue(set(config['brands']) <= set(self.services['devices'][device]['brands']))
        for brand, aliases in original['brand_aliases'].items():
            self.assertTrue(set(aliases) <= set(self.services['brand_aliases'][brand]))

    def test_no_manufacturer_fault_table_changes(self):
        self.assertEqual(self.files['assets/verified-faults.json'], self.original['assets/verified-faults.json'])
        self.assertEqual(self.files['assets/organic-catalog.json'], self.original['assets/organic-catalog.json'])
        models = json.loads(self.files['assets/verified-faults.json'])['models']
        for row in self.registry['brands']:
            for device, ids in row['guides_by_device'].items():
                self.assertEqual(ids, [m['id'] for m in models if m['device'] == device and m['brand'] == row['name']])

    def test_legacy_supplier_never_becomes_a_fault_alias(self):
        row = next(x for x in self.registry['brands'] if x['name'] == 'Isısan')
        self.assertEqual(row['kind'], 'legacy_supplier')
        self.assertEqual(row['devices'], ['kombi', 'klima'])
        self.assertEqual(row['verified_model_ids'], [])
        self.assertNotIn('Bosch', row['aliases'])
        self.assertNotIn('Buderus', row['aliases'])
        self.assertTrue(all(source['official'] for source in row['sources']))

    def test_lists_and_service_javascript_use_one_registry(self):
        service_js = self.files['assets/servis-verileri.js'].decode()
        self.assertEqual(json.loads(service_js.removeprefix('window.ST_SERVICE_DATA=').strip().removesuffix(';')), self.services)
        page = self.files['markalar.html'].decode()
        cards = re.findall(r'data-brand="([^"]+)" data-device="([^"]+)"', page)
        for device in ('kombi', 'klima'):
            expected = [r['name'] for r in self.registry['brands'] if device in r['devices']]
            self.assertEqual(self.services['devices'][device]['brands'], expected)
            self.assertEqual([name for name, kind in cards if kind == device], expected)
        self.assertEqual(self.report['device_brands'], {'kombi': 35, 'klima': 37})

    def test_unrelated_device_brand_intake_is_preserved(self):
        files = copy.copy(self.original)
        data = json.loads(files['assets/servis-katalog.json'])
        data['devices']['petek'] = {'label': 'Petek', 'brands': ['Özel tesisat kaydı']}
        files['assets/servis-katalog.json'] = json.dumps(data).encode()
        registry_builder.build_registry(files)
        actual = json.loads(files['assets/servis-katalog.json'])
        self.assertEqual(actual['devices']['petek'], data['devices']['petek'])

    def test_alias_runtime_preserves_device_and_guide_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'registry.js'
            script.write_bytes(b'global.window={};\n' + self.files['assets/brand-registry.js'] + '''
const assert=require('node:assert/strict'),api=window.STBrands;
assert.equal(api.find('ISISAN','kombi').name,'Isısan');
assert.equal(api.find('Isisan','klima').guide_count,0);
assert.equal(api.find('E.C.A.','klima').name,'ECA');
assert.equal(api.find('Daxom','klima'),null);
assert.equal(api.find('Daxom','kombi').guide_count,0);
assert.ok(api.find('Bosch','kombi').guide_count>0);
assert.deepEqual(api.find('Isisan','kombi').verified_model_ids,[]);
assert.equal(new Set(api.names('kombi')).size,35);
assert.equal(new Set(api.names('klima')).size,37);
'''.encode())
            subprocess.run(['node', str(script)], check=True, capture_output=True, text=True)


if __name__ == '__main__':
    unittest.main()
