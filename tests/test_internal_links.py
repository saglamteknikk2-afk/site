"""Internal navigation stays factual, bounded, crawlable and source preserving."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


builder = module('crawl_builder', ROOT / 'scripts/build_site.py')
linking = module('internal_links', ROOT / 'scripts/internal_links.py')
models = module('crawl_models', ROOT / 'scripts/enhance_models.py')
render = module('crawl_home', ROOT / 'scripts/render_home.py')
registry = module('crawl_registry', ROOT / 'scripts/brand_registry.py')
landings = module('crawl_landings', ROOT / 'scripts/landing_actions.py')


def strip_directories(text):
    pattern = r'<details\b[^>]*id="(?:st-hub-directory|st-district-navigation|st-brand-models)"[^>]*>'
    while match := re.search(pattern, text):
        depth = 0
        for token in re.finditer(r'</?details\b[^>]*>', text[match.start():]):
            depth += -1 if token[0].startswith('</') else 1
            if depth == 0:
                text = text[:match.start()] + text[match.start() + token.end():]
                break
        else:
            raise AssertionError('Unclosed generated directory')
    return text


class InternalLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        files = builder.archive_files(ROOT)
        builder.overlay(files, ROOT / 'server')
        builder.overlay(files, ROOT / 'overrides')
        registry.build_registry(files)
        render.render_home(files, ROOT)
        models.enhance_files(files)
        landings.enhance_landings(files)
        cls.original = files
        cls.files = copy.copy(files)
        cls.stats = linking.enhance_files(cls.files)
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name) / 'production'
        builder.build(ROOT, cls.output, 'production', '')
        cls.built = {p.relative_to(cls.output).as_posix(): p.read_bytes() for p in cls.output.rglob('*.html')}
        cls.graph = linking.analyze_graph(cls.built)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_all190_indexable_pages_reachable_within_three_html_links(self):
        self.assertEqual(self.graph['visitor_routes'], 203)
        self.assertEqual(self.graph['indexable_routes'], 190)
        self.assertEqual(self.graph['reachable_indexable_routes'], 190)
        self.assertLessEqual(self.graph['max_indexable_depth'], 3)
        self.assertEqual(self.graph['unreachable_indexable'], [])
        self.assertEqual(self.graph['unlinked_indexable'], [])
        self.assertEqual(self.graph['unresolved_internal_pages'], [])

    def test_real_build_invokes_enhancer_and_css_only_where_needed(self):
        self.assertGreater(self.stats['pages_enhanced'], 0)
        for name in self.stats['touched_pages']:
            text = self.built[name].decode()
            self.assertIn('assets/internal-links.css', text)
            self.assertRegex(text, r'class="st-reading-links(?:\s|\")')
        self.assertIn('assets/internal-links.css', self.built['index.html'].decode())

    def test_no_new_route_canonical_schema_model_or_sitemap(self):
        self.assertEqual(set(self.files), set(self.original))
        for name in self.stats['touched_pages']:
            before, after = self.original[name].decode(), self.files[name].decode()
            for pattern in [r'<h1\b[\s\S]*?</h1>', r'<link\b[^>]*rel="canonical"[^>]*>', r'<script\b[^>]*type="application/ld\+json"[^>]*>[\s\S]*?</script>']:
                self.assertEqual(re.findall(pattern, before), re.findall(pattern, after), name)
            clean = strip_directories(after)
            clean = re.sub(r'<nav\b[^>]*data-st-reading-links="1"[^>]*>[\s\S]*?</nav>', '', clean)
            clean = clean.replace('<link rel="stylesheet" href="assets/internal-links.css">', '')
            self.assertEqual(before, clean, name)
        for name in ['sitemap.xml', 'assets/verified-faults.json', 'assets/organic-catalog.json']:
            self.assertEqual(self.original[name], self.files[name])

    def test_each_context_module_has_three_to_six_real_missing_links(self):
        for name in self.stats['touched_pages']:
            text = self.files[name].decode()
            existing = {linking.canonical_href(href, name) for href in linking.parse(self.original[name].decode()).main_links}
            modules = re.findall(r'<nav\b[^>]*data-st-reading-links="1"[^>]*>([\s\S]*?)</nav>', text)
            for nav in modules:
                hrefs = linking.parse('<main>' + nav + '</main>').main_links
                self.assertGreaterEqual(len(hrefs), 3, name)
                self.assertLessEqual(len(hrefs), 6, name)
                self.assertEqual(len(hrefs), len(set(hrefs)), name)
                for href in hrefs:
                    self.assertIn(urlsplit(linking.canonical_href(href, name)).path.lstrip('/'), self.files, name)
                    self.assertNotIn(linking.canonical_href(href, name), existing, (name, href))

    def test_regions_have_all25_combi_and25_climate_links_without_a_duplicate_list(self):
        catalog = json.loads(self.files['assets/servis-katalog.json'])
        links = {urlsplit(linking.canonical_href(href, 'bolgeler.html')).path for href in linking.parse(self.files['bolgeler.html'].decode()).main_links}
        for district in catalog['districts']:
            for device in ('kombi', 'klima'):
                self.assertIn('/' + linking.slug(district) + '-' + device + '-servisi.html', links)
        self.assertGreater(self.stats['hub_links_added'], 0)
        self.assertNotIn('id="st-district-links"', self.files['bolgeler.html'].decode())

    def test_missing_region_destination_is_repaired_without_new_urls(self):
        files = copy.copy(self.original)
        text = files['bolgeler.html'].decode()
        text, removed = re.subn(r'<a\b[^>]*href="(?:/(?:site/)?)?kucukcekmece-klima-servisi\.html"[^>]*>[\s\S]*?</a>', '', text, count=1)
        self.assertEqual(removed, 1)
        files['bolgeler.html'] = text.encode()
        result = linking.enhance_files(files)
        self.assertGreater(result['hub_links_added'], 0)
        self.assertIn('href="kucukcekmece-klima-servisi.html"', files['bolgeler.html'].decode())
        self.assertEqual(set(files), set(self.original))

    def test_all_verified_model_pages_link_to_their_own_device_and_brand_filter(self):
        faults = json.loads(self.files['assets/verified-faults.json'])
        for model in faults['models']:
            name = Path(model['path']).name
            text = self.files[name].decode()
            self.assertIn('data-st-reading-links="1"', text)
            links = linking.parse(text).main_links
            self.assertIn(model['device'] + '-servisi.html', links)
            self.assertTrue(any(href.startswith('model-ariza-kodlari.html?') and 'brand=' in href for href in links), name)
        depths = {row['path'].lstrip('/'): row['depth'] for row in self.graph['routes']}
        self.assertTrue(all(depths[Path(model['path']).name] <= 3 for model in faults['models']))

    def test_brand_sources_keep_prose_and_receive_only_verified_exact_models(self):
        catalog = json.loads(self.files['assets/servis-katalog.json'])
        districts = {linking.slug(name) for name in catalog['districts']}
        for name, before in self.original.items():
            match = re.fullmatch(r'(.+)-(?:kombi|klima)-servisi\.html', name)
            if name in {linking.slug(n) + '-servisi.html' for n in catalog['semts']}:
                self.assertEqual(before, self.files[name], name)
            if match and match[1] not in districts:
                after = self.files[name].decode()
                self.assertIn('id="st-brand-models"', after)
                clean = strip_directories(after).replace('<link rel="stylesheet" href="assets/internal-links.css">', '')
                self.assertEqual(before.decode(), clean, name)
                self.assertNotIn('scope_confirmed=', after)

    def test_idempotent_and_every_district_has_the_requested_navigation(self):
        before = copy.copy(self.files)
        result = linking.enhance_files(self.files)
        self.assertEqual(before, self.files)
        self.assertEqual(result['links_added'], 0)
        catalog = json.loads(self.files['assets/servis-katalog.json'])
        for district in catalog['districts']:
            for device in ('kombi', 'klima'):
                name = linking.slug(district) + '-' + device + '-servisi.html'
                text = self.files[name].decode()
                self.assertIn('id="st-district-navigation"', text)
                self.assertIn('Yakın hizmet bölgeleri', text)
                self.assertIn('İlgili 5 belirti rehberi', text)
                self.assertNotIn('en sık görülen', text.lower())
                links = {linking.canonical_href(href, name) for href in linking.parse(text).main_links}
                self.assertIn('/' + device + '-servisi.html', links)
                for target in linking.DISTRICT_SYMPTOMS[device]: self.assertIn('/' + target, links)
                for nearby in linking.NEARBY_DISTRICTS[district]:
                    self.assertIn('/' + linking.slug(nearby) + '-' + device + '-servisi.html', links)

    def test_all_six_hubs_have_direct_static_links_to_every_published_category(self):
        catalog = json.loads(self.files['assets/servis-katalog.json'])
        index = json.loads(self.files['assets/page-index.json'])
        required = {row['path'] for row in index if row['kind'] in ('district', 'brand')}
        required.update('/' + linking.slug(name) + '-servisi.html' for name in catalog['semts'])
        required.update(row['path'] for config in catalog['devices'].values() for row in config['symptoms'])
        for name in linking.HUBS:
            text = self.files[name].decode()
            self.assertIn('data-st-link-directory="hub"', text)
            links = {urlsplit(linking.canonical_href(href, name)).path for href in linking.parse(text).main_links}
            self.assertTrue(required <= links, (name, sorted(required - links)))
        self.assertEqual(self.stats['directory_pages']['hub'], 6)
        self.assertEqual(self.stats['directory_pages']['district'], 50)
        self.assertEqual(self.stats['directory_pages']['brand-models'], 16)

    def test_emitted_links_and_styles_are_document_relative(self):
        for name in self.stats['touched_pages']:
            text = self.files[name].decode()
            before = self.original[name].decode()
            self.assertIn('href="assets/internal-links.css"', text)
            old_links = set(linking.parse(before).main_links)
            for href in set(linking.parse(text).main_links) - old_links:
                self.assertFalse(href.startswith(('/', 'https:', 'http:')), (name, href))
        self.assertEqual(linking.relative_href('/assets/internal-links.css', 'docs/help.html'), '../assets/internal-links.css')
        self.assertEqual(linking.relative_href('/kombi-servisi.html#bilgi', 'docs/help.html'), '../kombi-servisi.html#bilgi')

    def test_graph_does_not_count_javascript_or_nofollow_as_crawl_paths(self):
        files = {'index.html': b'<a class="at-brand" href="/"></a><script>const href="/hidden.html"</script><a href="/hidden.html" rel="nofollow">Hidden</a>', 'hidden.html': b'<main><h1>Hidden</h1></main>', '404.html': b'<meta name="robots" content="noindex">'}
        graph = linking.analyze_graph(files)
        self.assertEqual(graph['unreachable_indexable'], ['hidden.html'])

    def test_cli_gate_and_report(self):
        report = Path(self.temp.name) / 'crawl-report.json'
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/internal_links.py'), str(self.output), '--check', '--report', str(report)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(report.read_text())['reachable_indexable_routes'], 190)


if __name__ == '__main__':
    unittest.main()
