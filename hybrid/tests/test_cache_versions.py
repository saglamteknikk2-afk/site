import hashlib,importlib.util,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cache_versions import version_assets

class CacheVersionsTests(unittest.TestCase):
    def test_changed_resource_gets_new_content_version_and_other_query_survives(self):
        files={'index.html':b'<script src="assets/app.js?v=old&amp;lang=tr#start"></script>', 'assets/app.js':b'new application'}
        version_assets(files);text=files['index.html'].decode();digest=hashlib.sha256(files['assets/app.js']).hexdigest()[:12]
        self.assertIn('lang=tr&amp;v='+digest+'#start',text);self.assertNotIn('v=old',text)
    def test_catalogue_changes_invalidate_controller_and_html(self):
        files={'index.html':b'<script src="assets/hybrid-matrix.js"></script>',
               'assets/hybrid-matrix.js':b"new URL('hybrid-matrix-data.json',script)",
               'assets/hybrid-matrix-data.json':b'{"changed":true}'}
        version_assets(files)
        self.assertIn(hashlib.sha256(files['assets/hybrid-matrix-data.json']).hexdigest()[:12].encode(),files['assets/hybrid-matrix.js'])
        self.assertIn(hashlib.sha256(files['assets/hybrid-matrix.js']).hexdigest()[:12].encode(),files['index.html'])
    def test_delayed_dataset_versions_and_external_urls_remain_correct(self):
        files={'index.html':b'<script data-diagnostic-sources="[&quot;assets/data.js?v=old&quot;]"></script><a href="https://wa.me/123">WhatsApp</a>', 'assets/data.js':b'actual data'}
        version_assets(files);once=dict(files);version_assets(files)
        self.assertEqual(files,once);self.assertIn(hashlib.sha256(files['assets/data.js']).hexdigest()[:12].encode(),files['index.html']);self.assertIn(b'https://wa.me/123',files['index.html'])

if __name__=='__main__':unittest.main()
