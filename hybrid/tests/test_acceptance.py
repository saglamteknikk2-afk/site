import importlib.util
import base64
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import audit
import semantics

def page(name,body='',robots=''):
    url=semantics.ORIGIN if name=='index.html' else semantics.ORIGIN+name
    return ('<!doctype html><html><head><title>Servis</title>'
            '<meta name="robots" content="'+robots+'"><link rel="canonical" href="'+url+'">'
            '</head><body><main><h1>Servis</h1>'+body+'</main></body></html>').encode()

def fixture():
    files={'index.html':page('index.html','<a href="kombi-basinci.html">Basınç</a>'),
           'kombi-basinci.html':page('kombi-basinci.html','<a href="./">Ana sayfa</a><details><summary>Ne zaman?</summary><p>Isıtma sırasında.</p></details>'),
           'assets/servis-verileri.js':b'window.ST_SERVICE_DATA={"districts":[]};',
           'robots.txt':b'User-agent: *\nAllow: /\n'}
    semantics.apply_semantics(files)
    return files

class AcceptanceTests(unittest.TestCase):
    def test_reachable_valid_fixture_passes(self):
        result=audit.audit(fixture())
        self.assertEqual(result['status'],'passed')
        self.assertEqual(result['eligible_content_pages'],2)
        self.assertEqual(result['orphans'],[])

    def test_missing_link_fails(self):
        files=fixture();files['index.html']=files['index.html'].replace(b'kombi-basinci.html',b'missing.html')
        result=audit.audit(files,strict=False)
        self.assertTrue(any(x['kind']=='missing_file' for x in result['errors']))
        with self.assertRaises(ValueError):audit.audit(files)

    def test_missing_code_anchor_fails(self):
        files=fixture();files['index.html']=files['index.html'].replace(b'kombi-basinci.html',b'kombi-basinci.html#kod-unknown')
        self.assertTrue(any(x['kind']=='missing_anchor' for x in audit.audit(files,strict=False)['errors']))

    def test_orphan_is_detected(self):
        files=fixture();files['index.html']=files['index.html'].replace(b'href="kombi-basinci.html"',b'href="./"')
        self.assertIn('kombi-basinci.html',audit.audit(files,strict=False)['orphans'])

    def test_faq_mismatch_fails(self):
        files=fixture();source=files['kombi-basinci.html'].decode()
        # Alter the visible answer, leaving schema unchanged.
        source=source.replace('<p>Isıtma sırasında.</p>','<p>Başka bir cevap.</p>')
        files['kombi-basinci.html']=source.encode()
        self.assertTrue(any(x['kind']=='faq_visible_parity' for x in audit.audit(files,strict=False)['errors']))

    def test_external_navigation_fails_but_whatsapp_allowed(self):
        files=fixture();files['index.html']=files['index.html'].replace(b'</main>',b'<a href="https://wa.me/905346225515">WhatsApp</a></main>')
        self.assertEqual(audit.audit(files)['outbound_non_contact_anchors'],0)
        files['index.html']=files['index.html'].replace(b'</main>',b'<a href="https://manufacturer.example/manual">Kaynak</a></main>')
        self.assertTrue(any(x['kind']=='outbound_navigation' for x in audit.audit(files,strict=False)['errors']))

    def test_unknown_model_table_changes_are_caught(self):
        baseline={'x-ariza-kodlari.html':page('x-ariza-kodlari.html','<h2 id="kod-e01">E01</h2><table><tr><td>E01</td><td>Ateşleme</td></tr></table>','noindex,follow')}
        files=fixture();files.update(baseline)
        files['x-ariza-kodlari.html']=files['x-ariza-kodlari.html'].replace(b'Ate\xc5\x9fleme',b'Unknown diagnosis')
        result=audit.audit(files,baseline=baseline,strict=False)
        self.assertTrue(any(x['kind']=='model_table_fact_changed' for x in result['errors']))

    def test_sitemap_noindex_page_fails(self):
        files=fixture();files['kombi-basinci.html']=files['kombi-basinci.html'].replace(b'content=""',b'content="noindex,follow"',1)
        self.assertTrue(any(x['kind']=='sitemap_ineligible' for x in audit.audit(files,strict=False)['errors']))

    def test_preview_php_fails(self):
        files=fixture();files['api.php']=b'<?php echo "test";'
        self.assertTrue(any(x['kind']=='preview_contains_php' for x in audit.audit(files,mode='preview',strict=False)['errors']))

    def test_secret_report_has_no_secret_value(self):
        files=fixture();secret='AIza'+'a'*35;files['assets/key.js']=('const key="'+secret+'";').encode()
        report=audit.audit(files,strict=False)
        self.assertEqual(report['credential_pattern_matches'],1)
        self.assertNotIn(secret,json.dumps(report))

    def test_generated_route_and_code_targets_are_checked(self):
        files=fixture()
        files['assets/hybrid-matrix-data.json']=json.dumps({
            'routes':['nonexistent.html'],
            'models':[{'path':'kombi-basinci.html','codes':[{'anchor':'kod-never-published'}]}]
        }).encode()
        kinds={x['kind'] for x in audit.audit(files,strict=False)['errors']}
        self.assertIn('generated_route_missing',kinds)
        self.assertIn('generated_code_anchor_missing',kinds)

    def test_binary_image_pattern_is_excluded_but_adjacent_script_is_scanned(self):
        files=fixture();secret='AIza'+'a'*35
        # Make a JPEG-signature binary payload whose encoded representation
        # includes a coincidental literal key-shaped substring.
        blob=b'\xff\xd8\xff\xe0\0\0'+base64.b64decode(secret+'a')+b'\xff\xd9'
        encoded=base64.b64encode(blob).decode()
        self.assertIn(secret,encoded)
        files['review.html']=('<img src="data:image/jpeg;base64,'+encoded+'">').encode()
        report=audit.audit(files,strict=False)
        self.assertEqual(report['credential_pattern_matches'],0)
        files['review.html']+=('<script>const key="'+secret+'";</script>').encode()
        report=audit.audit(files,strict=False)
        self.assertEqual(report['credential_pattern_matches'],1)
        self.assertNotIn(secret,json.dumps(report))

if __name__=='__main__':unittest.main()
