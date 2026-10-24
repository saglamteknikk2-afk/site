"""Regressions for a reviewed code silently remaining stale in browser/search."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('catalog_builder', Path(__file__).resolve().parents[1] / 'scripts/build_site.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class CatalogSyncTests(unittest.TestCase):
    def fixture(self):
        model = {'id':'qa-model', 'device':'kombi', 'brand':'QA', 'label':'Exact Model', 'path':'/qa.html', 'codes':[{'code':'E99', 'anchor':'kod-e99', 'meaning':'Reviewed meaning'}]}
        catalog = {'guides':[{'error_code':'E01', 'code_definition_verified':True}, {'purpose':'model-required-explainer', 'code_definition_verified':False}]}
        return {'assets/verified-faults.json':json.dumps({'models':[model]}).encode(), 'assets/verified-faults.js':b'window.ST_VERIFIED_FAULTS={"models":[]};', 'assets/organic-catalog.json':json.dumps(catalog).encode(), 'organic-catalog.js':b'stale', 'qa.html':b'<tr id="kod-e99"><td>E99</td></tr>'}

    def test_reviewed_addition_replaces_stale_browser_and_search_definitions(self):
        files = self.fixture()
        builder.sync_catalog_data(files)
        browser = json.loads(files['assets/verified-faults.js'].decode().removeprefix('window.ST_VERIFIED_FAULTS=').strip().removesuffix(';'))
        self.assertEqual(browser, json.loads(files['assets/verified-faults.json']))
        guides = json.loads(files['assets/organic-catalog.json'])['guides']
        self.assertEqual([row['error_code'] for row in guides if row.get('code_definition_verified')], ['E99'])
        self.assertTrue(any(row.get('purpose') == 'model-required-explainer' for row in guides))
        self.assertEqual(files['organic-catalog.js'], files['assets/organic-catalog.js'])

    def test_new_code_without_readable_destination_cannot_build(self):
        files = self.fixture()
        files['qa.html'] = b'<tr id="kod-e01"></tr>'
        with self.assertRaisesRegex(ValueError, 'qa-model / E99'):
            builder.sync_catalog_data(files)

    def test_revoked_definition_is_removed_and_regeneration_is_idempotent(self):
        files = self.fixture()
        data = json.loads(files['assets/verified-faults.json'])
        data['models'][0]['codes'][0]['source_conflict'] = True
        files['assets/verified-faults.json'] = json.dumps(data).encode()
        builder.sync_catalog_data(files)
        self.assertFalse(any(row.get('code_definition_verified') for row in json.loads(files['assets/organic-catalog.json'])['guides']))
        once = copy.copy(files)
        builder.sync_catalog_data(files)
        self.assertEqual(files, once)

    def test_unavailable_source_is_explicit_and_never_a_dead_clickable_link(self):
        files = self.fixture()
        data = json.loads(files['assets/verified-faults.json'])
        data['models'][0]['manual'] = {'url':'https://manufacturer.invalid/missing.pdf', 'source_available':False}
        files['assets/verified-faults.json'] = json.dumps(data).encode()
        with self.assertRaisesRegex(ValueError, 'Unavailable manual'):
            builder.sync_catalog_data(files)
        data['models'][0]['codes'][0]['matchable'] = False
        files['assets/verified-faults.json'] = json.dumps(data).encode()
        files['qa.html'] = b'<section class="fault-table-section"><a href="https://manufacturer.invalid/missing.pdf">Source</a><tr id="kod-e99"><td>E99</td></tr></section>'
        builder.sync_catalog_data(files)
        builder.sync_catalog_data(files)
        self.assertEqual(files['qa.html'].count(b'data-manual-unavailable='), 1)
        self.assertNotIn(b'href="https://manufacturer.invalid/missing.pdf"', files['qa.html'])
        self.assertFalse(any(row.get('code_definition_verified') for row in json.loads(files['assets/organic-catalog.json'])['guides']))
