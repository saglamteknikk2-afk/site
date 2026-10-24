#!/usr/bin/env python3
"""Behavior tests for release separation; no browser, PHP, or network needed."""
import importlib.util
import hashlib
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('builder',ROOT/'scripts/build_site.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
spec_zip=importlib.util.spec_from_file_location('packager',ROOT/'scripts/package_production.py')
packager=importlib.util.module_from_spec(spec_zip);spec_zip.loader.exec_module(packager)

class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)/'source';cls.root.mkdir()
        shutil.copytree(ROOT/'preview-parts',cls.root/'preview-parts')
        (cls.root/'scripts').mkdir()
        for name in ['production-seo.json','preview-guard.js']:shutil.copy2(ROOT/'scripts'/name,cls.root/'scripts'/name)
        (cls.root/'server').mkdir();(cls.root/'server/api.php').write_text('<?php echo "server";')
        (cls.root/'server/custom.txt').write_text('server')
        (cls.root/'overrides/assets').mkdir(parents=True)
        (cls.root/'overrides/custom.txt').write_text('override wins')
        regions=builder.archive_files(cls.root)['bolgeler.html'].decode().replace('href="/site/logo.png"','href="logo.png"')
        regions=regions.replace('<body', '<body data-st-mode="production"', 1)
        (cls.root/'overrides/bolgeler.html').write_text(regions)
        (cls.root/'overrides/assets/premium.css').write_text('body{color:green}')
        (cls.root/'overrides/assets/premium.js').write_text('window.premium=true;')
        (cls.root/'overrides/private').mkdir();(cls.root/'overrides/private/example.db').write_text('not public')
        (cls.root/'components').mkdir()
        shutil.copy2(ROOT/'components/brand.json',cls.root/'components/brand.json')
        shutil.copytree(ROOT/'overrides/assets/brand',cls.root/'overrides/assets/brand')
        (cls.root/'components/header.html').write_text('<header class="at-header" data-shared="header"><a href="/index.html">Sağlam Teknik</a></header>')
        (cls.root/'components/footer.html').write_text('<footer class="at-footer" data-shared="footer">Ortak alt bilgi</footer><nav class="at-mobile-contact">Tek menü</nav>')
        cls.preview=Path(cls.temp.name)/'preview';cls.production=Path(cls.temp.name)/'production'
        cls.p=builder.build(cls.root,cls.preview,'preview','/site')
        cls.r=builder.build(cls.root,cls.production,'production','')
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_archive_integrity(self):self.assertEqual(len(builder.archive_files(self.root)),486)
    def test_modes_have_same_visitor_count(self):self.assertEqual((self.p['visitor_pages'],self.r['visitor_pages']),(203,203))
    def test_backend_only_in_production(self):self.assertFalse((self.preview/'api.php').exists());self.assertTrue((self.production/'api.php').exists())
    def test_overrides_win(self):self.assertEqual((self.production/'custom.txt').read_text(),'override wins')
    def test_shared_components_global(self):
        for page in self.preview.glob('*.html'):
            self.assertIn('data-shared="header"',page.read_text());self.assertIn('data-shared="footer"',page.read_text())
    def test_shared_mobile_nav_not_duplicated(self):
        for page in self.preview.glob('*.html'):self.assertEqual(page.read_text().count('class="at-mobile-contact"'),1)
    def test_private_never_in_preview(self):self.assertFalse((self.preview/'private').exists())
    def test_legacy_logo_and_favicon_use_supplied_artwork(self):
        brand=json.loads((self.root/'components/brand.json').read_text())
        for page in self.preview.glob('*.html'):
            text=page.read_text()
            self.assertIn('href="/site'+brand['favicon']+'" type="image/png"',text)
            self.assertNotRegex(text,r'''["'](?:/site/|/|\./)?logo\.(?:svg|png)["']''')
    def test_brand_rewrites_legacy_jsonld_and_relative_references(self):
        brand=json.loads((self.root/'components/brand.json').read_text())
        source='{"logo":"https://saglamkombiklima.com.tr/logo.png"}<img src="/logo.svg"><img src="logo.png"><img src="/assets/brand/logo-ribbon.png">'
        actual=builder.apply_brand(source,brand)
        self.assertIn('https://saglamkombiklima.com.tr'+brand['logo'],actual)
        self.assertEqual(actual.count(brand['logo']),4)
    def test_old_mode_marker_is_replaced_once(self):
        text=(self.preview/'bolgeler.html').read_text()
        self.assertEqual(text.count('data-st-mode='),1)
        self.assertIn('data-st-mode="preview"',text)
    def test_changed_assets_get_fresh_urls(self):
        source='<script src="/site/assets/a.js?v=old"></script><a href="/guide.html">Guide</a>'
        first=builder.version_assets(source,{'assets/a.js':b'first'})
        second=builder.version_assets(source,{'assets/a.js':b'second'})
        self.assertNotEqual(first,second);self.assertNotIn('?v=old',first)
        self.assertIn('<a href="/guide.html">',first)
        self.assertIn('src="/site/assets/a.js?v=',first)
    def test_package_has_webroot_not_parent_folder(self):
        archive=Path(self.temp.name)/'production.zip';names=packager.package(self.production,archive)
        self.assertIn('index.html',names);self.assertIn('api.php',names)
        self.assertFalse(any(name.startswith(('production/','private/','templates/')) or name.endswith(('.db','.sqlite','.env')) for name in names))
        with zipfile.ZipFile(archive) as z:self.assertIsNone(z.testzip())
    def test_preview_all_noindex(self):
        for page in self.preview.glob('*.html'):self.assertIn('noindex',page.read_text())
    def test_robots_crawl_allowed(self):self.assertEqual((self.preview/'robots.txt').read_text(),'User-agent: *\nAllow: /\n')
    def test_global_enhancement(self):
        for page in self.preview.glob('*.html'):
            self.assertIn('/site/assets/premium.css',page.read_text());self.assertIn('/site/assets/premium.js',page.read_text())
    def test_production_has_restored_canonical(self):self.assertIn('https://saglamkombiklima.com.tr/',(self.production/'index.html').read_text());self.assertIn('rel="canonical"',(self.production/'index.html').read_text())
    def test_preview_guard_absent_production(self):self.assertNotIn('preview-guard',(self.production/'index.html').read_text())
    def test_local_search_forms_work_without_unlocking_writes(self):
        source='<form id="regionFinder"><input></form><form id="svcSearchForm"></form><form id="serviceTicketForm"></form><form id="musteriYorumFormu"></form>'
        actual=builder.allow_local_preview_forms(source)
        self.assertIn('<form id="regionFinder" data-preview-local="true">',actual)
        self.assertIn('<form id="svcSearchForm" data-preview-local="true">',actual)
        self.assertIn('<form id="serviceTicketForm">',actual)
        self.assertIn('<form id="musteriYorumFormu">',actual)
        self.assertEqual(actual,builder.allow_local_preview_forms(actual))
        self.assertIn('<form id="svcSearchForm" data-preview-local="true">',(self.preview/'servis-sec.html').read_text())
        self.assertNotIn('<form id="svcSearchForm" data-preview-local="true">',(self.production/'servis-sec.html').read_text())
    def test_path_conversion(self):
        source='<a href="/site/kombi.html"><img src="/assets/a.svg">';self.assertEqual(builder.normalize_paths(source,'/site'),'<a href="/site/kombi.html"><img src="/site/assets/a.svg">')
        self.assertEqual(builder.normalize_paths(source,''),'<a href="/kombi.html"><img src="/assets/a.svg">')
        self.assertEqual(builder.normalize_paths('"https://manufacturer.example/site/manual.pdf"','/site'),'"https://manufacturer.example/site/manual.pdf"')
        self.assertEqual(builder.normalize_paths('srcset="/site/a.webp 480w, /assets/b.webp 1400w"','/site'),'srcset="/site/a.webp 480w, /site/assets/b.webp 1400w"')
        self.assertEqual(builder.normalize_paths('<stop stop-color="#fff"/><input value=""/>','/site'),'<stop stop-color="#fff"/><input value=""/>')
    def test_mounted_urls_are_idempotent(self):
        source='<a href="/#ai-usta"><img src="/site/assets/a.webp" srcset="/assets/a.webp 480w, /site/assets/b.webp 1400w"><style>.a{background:url(/assets/a.webp)}</style>'
        for prefix in ['', '/site', '/preview/v2']:
            with self.subTest(prefix=prefix):
                once=builder.normalize_paths(source,prefix)
                self.assertEqual(once,builder.normalize_paths(once,prefix))
                self.assertIn('href="'+prefix+'/#ai-usta"',once)
                self.assertIn('srcset="'+prefix+'/assets/a.webp 480w, '+prefix+'/assets/b.webp 1400w"',once)
                self.assertIn('url('+prefix+'/assets/a.webp)',once)
    def test_javascript_rewrites_only_published_file_urls(self):
        source="const root='/';const embed='/maps/embed';const legacy='/site';const file='/site/guide.html#kodlar';const api='/api.php?action=ai';"
        files={'guide.html':b'', 'api.php':b''}
        for prefix in ['', '/site', '/preview/v2']:
            with self.subTest(prefix=prefix):
                actual=builder.normalize_javascript(source,prefix,files)
                self.assertIn("root='/'",actual)
                self.assertIn("embed='/maps/embed'",actual)
                self.assertIn("legacy='/site'",actual)
                self.assertIn("file='"+prefix+"/guide.html#kodlar'",actual)
                self.assertIn("api='"+prefix+"/api.php?action=ai'",actual)
                self.assertEqual(actual,builder.normalize_javascript(actual,prefix,files))
    def test_inline_javascript_path_predicates_not_mounted(self):
        source='<a href="/"><script>const root="/";const target="/guide.html";</script>'
        actual=builder.normalize_paths(source,'/preview/v2',{'guide.html':b''})
        self.assertIn('<a href="/preview/v2/">',actual)
        self.assertIn('root="/"',actual)
        self.assertIn('target="/preview/v2/guide.html"',actual)
    def test_custom_mount_asset_versions_use_served_bytes(self):
        asset=b'window.route="/preview/v2/guide.html";'
        source='<script src="/preview/v2/assets/a.js?v=old"></script>'
        actual=builder.version_assets(source,{'assets/a.js':asset},'/preview/v2')
        self.assertIn('?v='+hashlib.sha256(asset).hexdigest()[:10],actual)
    def test_deterministic(self):self.assertEqual(self.p,builder.build(self.root,Path(self.temp.name)/'second','preview','/site'))
    def test_corrupt_archive_rejected(self):
        p=self.root/'preview-parts/part-000.txt';old=p.read_bytes();p.write_bytes(b'!'+old[1:])
        try:
            with self.assertRaises(Exception):builder.archive_files(self.root)
        finally:p.write_bytes(old)
    def test_output_cannot_delete_inputs(self):
        with self.assertRaises(ValueError):builder.build(self.root,self.root/'overrides/nested','preview','/site')

if __name__=='__main__':unittest.main()
