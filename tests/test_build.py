#!/usr/bin/env python3
"""Behavior tests for release separation; no browser, PHP, or network needed."""
import importlib.util
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
        (cls.root/'overrides/bolgeler.html').write_text(regions)
        (cls.root/'overrides/assets/premium.css').write_text('body{color:green}')
        (cls.root/'overrides/assets/premium.js').write_text('window.premium=true;')
        (cls.root/'overrides/private').mkdir();(cls.root/'overrides/private/example.db').write_text('not public')
        (cls.root/'components').mkdir()
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
    def test_legacy_favicon_uses_small_svg(self):
        for page in self.preview.glob('*.html'):self.assertNotRegex(page.read_text(),r'rel="icon"[^>]*logo\.png')
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
    def test_path_conversion(self):
        source='<a href="/site/kombi.html"><img src="/assets/a.svg">';self.assertEqual(builder.normalize_paths(source,'/site'),'<a href="/site/kombi.html"><img src="/site/assets/a.svg">')
        self.assertEqual(builder.normalize_paths(source,''),'<a href="/kombi.html"><img src="/assets/a.svg">')
        self.assertEqual(builder.normalize_paths('"https://manufacturer.example/site/manual.pdf"','/site'),'"https://manufacturer.example/site/manual.pdf"')
        self.assertEqual(builder.normalize_paths('srcset="/site/a.webp 480w, /assets/b.webp 1400w"','/site'),'srcset="/site/a.webp 480w, /site/assets/b.webp 1400w"')
        self.assertEqual(builder.normalize_paths('<stop stop-color="#fff"/><input value=""/>','/site'),'<stop stop-color="#fff"/><input value=""/>')
    def test_deterministic(self):self.assertEqual(self.p,builder.build(self.root,Path(self.temp.name)/'second','preview','/site'))
    def test_corrupt_archive_rejected(self):
        p=self.root/'preview-parts/part-000.txt';old=p.read_bytes();p.write_bytes(b'!'+old[1:])
        try:
            with self.assertRaises(Exception):builder.archive_files(self.root)
        finally:p.write_bytes(old)
    def test_output_cannot_delete_inputs(self):
        with self.assertRaises(ValueError):builder.build(self.root,self.root/'overrides/nested','preview','/site')

if __name__=='__main__':unittest.main()
