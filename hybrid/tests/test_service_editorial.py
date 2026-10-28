"""Keep useful service narratives visible and prevent family-wide code guesses."""
import copy
import re
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from service_editorial import apply_services, load_services, _models
from editorial_regions import apply_regions
from editorial_audit import audit_pages, verify_rendered, _source_context
from source import load_source


class ServiceEditorialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files, _ = load_source(ROOT.parent)
        apply_regions(cls.files)
        cls.metrics = apply_services(cls.files)

    def test_service_bodies_replace_old_template_and_render_all_authored_blocks(self):
        pages = list(load_services().values())
        result = verify_rendered(pages, self.files)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['rendered_bodies'], 29)
        self.assertEqual(self.metrics['brand_pages'], 16)

    def test_unknown_scope_is_not_advertised_as_a_turkey_code_table(self):
        models = [{'brand':'Example','device':'kombi','label':'Foreign 24',
                   'path':'foreign.html','market':'GB/IE','codes':[{'code':'E1','meaning':'Unsafe if transferred'}]}]
        files = {'foreign.html':b'<meta name="robots" content="noindex,follow">',
                 'model-ariza-kodlari.html':b''}
        text = _models({'brand':'Example','device':'kombi','type':'brand'}, models, files)
        self.assertNotIn('href="foreign.html', text)
        self.assertNotIn('Unsafe if transferred', text)
        self.assertIn('Türkiye cihazları', text)

    def test_name_swapped_service_body_is_a_regression(self):
        source, files, brands = _source_context()
        pages = list(load_services().values())
        changed = copy.deepcopy(pages)
        changed[1]['sections'][0]['paragraphs'] = copy.deepcopy(changed[0]['sections'][0]['paragraphs'])
        result = audit_pages(changed, {'districts':[], 'localities':[]}, files, brands,
                             strict=False, extra_routes=changed)
        self.assertTrue(any(e['kind']=='repeated_editorial_paragraph_after_location_mask' for e in result['errors']))

    def test_source_model_tables_are_untouched_by_service_editorial(self):
        original, _ = load_source(ROOT.parent)
        for path, data in original.items():
            if path.endswith('-ariza-kodlari.html'):
                self.assertEqual(self.files[path], data, path)

    def test_old_extra_brand_directory_is_replaced_without_duplicate_id(self):
        for route, page in load_services().items():
            if page['type']!='brand': continue
            text=self.files[route].decode()
            self.assertEqual(len(re.findall(r'id="st-brand-models"',text)),1,route)
            self.assertNotIn('data-st-link-directory="brand-models"',text)
            self.assertNotRegex(re.search(r'<title>(.*?)</title>',text,re.S)[1],r'\b(?:E01|E1|501|108|EA|CE|E9)\b')


if __name__ == '__main__': unittest.main()
