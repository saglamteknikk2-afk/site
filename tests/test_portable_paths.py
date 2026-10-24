import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('portable_paths', ROOT/'scripts/portable_paths.py')
paths = importlib.util.module_from_spec(spec); spec.loader.exec_module(paths)

class PortablePathsTests(unittest.TestCase):
    def files(self):
        return {'index.html':b'', 'guide.html':b'', 'api.php':b'',
                'assets/a.css':b'', 'assets/a.js':b'', 'assets/bg.svg':b'',
                'assets/owner-admin.js':b'', 'assets/fonts/a.woff2':b'',
                'home.js':b'old', 'assets/home.js':b'new'}
    def test_markup_is_identical_at_each_mount_and_external_urls_survive(self):
        f=self.files()
        for prefix in ('','/site','/qa-preview'):
            html=f'<a href="{prefix}/guide.html#E01">go</a><script src="{prefix}/assets/a.js"></script><a href="https://manufacturer.test/site/manual.pdf">source</a>'
            out=paths.rewrite_html(html,'index.html',f,{},prefix)
            self.assertIn('href="guide.html#E01"',out)
            self.assertIn('src="assets/a.js"',out)
            self.assertIn('https://manufacturer.test/site/manual.pdf',out)
    def test_css_uses_stylesheet_directory(self):
        f=self.files()
        css=".bg{background:url('/site/assets/bg.svg')}@font-face{src:url(/assets/fonts/a.woff2)}"
        out=paths.rewrite_css(css,'assets/a.css',f,{},'/site')
        self.assertIn("url('bg.svg')",out);self.assertIn('url(fonts/a.woff2)',out)
    def test_nested_admin_api_is_parent_relative(self):
        f=self.files()
        self.assertEqual(paths.rewrite_js("fetch('/api.php?action=bootstrap')",'assets/owner-admin.js',f,{},''),"fetch('../api.php?action=bootstrap')")
    def test_js_predicates_and_codes_are_untouched(self):
        f=self.files()
        text="const root='/';const embed='/maps/embed';const kind='/klima-';const codes=['E1','E01','F.28','F28'];fetch('/site/api.php?action=ai');"
        out=paths.rewrite_js(text,'assets/a.js',f,{},'/site')
        self.assertIn("root='/'",out);self.assertIn("embed='/maps/embed'",out);self.assertIn("kind='/klima-'",out)
        self.assertIn("['E1','E01','F.28','F28']",out);self.assertIn("fetch('api.php?action=ai')",out)
    def test_dynamic_url_concatenations_keep_empty_query_and_fragment(self):
        f=self.files();f['servis-sec.html']=b''
        source="const a='/index.html?'+params+'#ai-usta';const b='/servis-sec.html#'+location;"
        out=paths.rewrite_js(source,'assets/a.js',f,{},'')
        self.assertIn("'index.html?'+params+'#ai-usta'",out)
        self.assertIn("'servis-sec.html#'+location",out)
    def test_obsolete_root_scripts_are_removed_and_references_redirected(self):
        f=self.files();f['index.html']=b'<script src="home.js"></script>'
        result=paths.enhance_files(f)
        self.assertNotIn('home.js',f);self.assertEqual(f['assets/home.js'],b'new')
        self.assertEqual(f['index.html'],b'<script src="assets/home.js"></script>')
        self.assertIn('home.js',result['removed_files'])
    def test_inline_semantic_urls_are_not_relativized(self):
        f=self.files();text='<script type="application/ld+json">{"url":"https://saglamkombiklima.com.tr/guide.html"}</script>'
        self.assertEqual(paths.rewrite_html(text,'index.html',f,{},'/site'),text)
    def test_srcset_and_nested_admin_resource(self):
        f=self.files()
        out=paths.rewrite_html('<img srcset="/assets/bg.svg 1x, /site/assets/bg.svg 2x"><script src="/assets/a.js"></script>','assets/owner-admin.html',f,{},'/site')
        self.assertIn('srcset="bg.svg 1x, bg.svg 2x"',out);self.assertIn('src="a.js"',out)

if __name__=='__main__':unittest.main()
