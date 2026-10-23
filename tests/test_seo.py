"""SEO release regressions with small local fixtures; no PHP or network."""
import importlib.util
from html import escape
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('site_checker',ROOT/'scripts/check_site.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
ORIGIN='https://saglamkombiklima.com.tr'


class SEOTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.page('index.html',[ORIGIN+'/'])
        self.page('kombi.html',[ORIGIN+'/kombi.html'])
        self.page('servis-sec.html',[],noindex=True)
        # Keep the existing checker's non-visitor exclusions.
        (self.root/'owner-admin.html').write_text('Private administration page')
        (self.root/'googleverification.html').write_text('Verification token')
        self.sitemap([ORIGIN+'/',ORIGIN+'/kombi.html'])

    def page(self,name,canonicals,*,noindex=False,preview=False):
        head=''.join('<link rel="canonical" href="'+escape(url,quote=True)+'">' for url in canonicals)
        if noindex: head+='<meta name="robots" content="noindex,follow">'
        if preview: head+='<script src="/site/assets/preview-guard.js"></script>'
        banner='<div id="st-preview-banner">Static preview</div>' if preview else ''
        mode='preview' if preview else 'production'
        (self.root/name).write_text(f'<!doctype html><html><head>{head}</head><body data-st-mode="{mode}">{banner}<h1>Servis bilgisi</h1></body></html>')

    def sitemap(self,urls):
        entries=''.join('<url><loc>'+escape(url)+'</loc></url>' for url in urls)
        (self.root/'sitemap.xml').write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+entries+'</urlset>')

    def errors(self,mode='production'):
        return checker.check(self.root,mode)['errors']

    def test_valid_release_excludes_noindex_and_nonvisitor_pages(self):
        self.assertEqual(self.errors(),[])

    def test_missing_canonical_fails(self):
        self.page('kombi.html',[])
        self.assertTrue(any('kombi.html: expected exactly one canonical, got 0' in error for error in self.errors()))

    def test_duplicate_canonical_fails_even_when_both_are_correct(self):
        self.page('kombi.html',[ORIGIN+'/kombi.html',ORIGIN+'/kombi.html'])
        self.assertTrue(any('expected exactly one canonical, got 2' in error for error in self.errors()))

    def test_wrong_domain_path_and_parameter_canonicals_fail(self):
        for url in ['https://example.invalid/kombi.html',ORIGIN+'/',ORIGIN+'/site/kombi.html',ORIGIN+'/kombi.html?model=24','/kombi.html']:
            with self.subTest(url=url):
                self.page('kombi.html',[url])
                self.assertTrue(any('kombi.html: canonical must be ' in error for error in self.errors()))

    def test_missing_sitemap_fails(self):
        (self.root/'sitemap.xml').unlink()
        self.assertIn('Missing sitemap.xml',self.errors())

    def test_missing_indexable_url_fails(self):
        self.sitemap([ORIGIN+'/'])
        self.assertIn('sitemap.xml: missing indexable URL '+ORIGIN+'/kombi.html',self.errors())

    def test_duplicate_sitemap_url_fails(self):
        self.sitemap([ORIGIN+'/',ORIGIN+'/kombi.html',ORIGIN+'/kombi.html'])
        self.assertIn('sitemap.xml: duplicate URL '+ORIGIN+'/kombi.html',self.errors())

    def test_noindex_and_nonexistent_sitemap_urls_fail(self):
        for extra in ['/servis-sec.html','/removed.html','/owner-admin.html']:
            with self.subTest(extra=extra):
                self.sitemap([ORIGIN+'/',ORIGIN+'/kombi.html',ORIGIN+extra])
                self.assertIn('sitemap.xml: URL is not an indexable visitor page '+ORIGIN+extra,self.errors())

    def test_malformed_or_wrong_sitemap_document_fails(self):
        for xml in ['<urlset>','<html></html>']:
            with self.subTest(xml=xml):
                (self.root/'sitemap.xml').write_text(xml)
                self.assertTrue(any(error.startswith('sitemap.xml:') for error in self.errors()))

    def test_preview_needs_no_production_canonical_or_sitemap(self):
        for name in ['index.html','kombi.html','servis-sec.html']:
            self.page(name,[],noindex=True,preview=True)
        (self.root/'owner-admin.html').unlink()
        (self.root/'sitemap.xml').unlink()
        (self.root/'assets').mkdir();(self.root/'assets/preview-guard.js').write_text('window.ST_PREVIEW=true;')
        (self.root/'robots.txt').write_text('User-agent: *\nAllow: /\n')
        self.assertEqual(self.errors('preview'),[])
        self.page('kombi.html',[],preview=True)
        self.assertIn('kombi.html: noindex missing',self.errors('preview'))


if __name__=='__main__': unittest.main()
