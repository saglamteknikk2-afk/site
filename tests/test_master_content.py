"""Master copy is exact, bounded, repeatable, and preserves local research."""
import copy
import hashlib
import html
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


master = module('master_content_tests', ROOT / 'scripts/master_content.py')
builder = module('master_builder', ROOT / 'scripts/build_site.py')


class ReadPage(HTMLParser):
    """Independent text/table reader: no production replacement helpers."""
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.in_title = False
        self.title = []
        self.in_lead = False
        self.lead = []
        self.cell = None
        self.cells = []
        self.links = []
        self.feed(text)

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        if tag == 'title': self.in_title = True
        if tag == 'p' and 'at-lead' in attrs.get('class', '').split(): self.in_lead = True
        if tag == 'meta': self.meta[attrs.get('name') or attrs.get('property')] = attrs.get('content')
        if tag in ('td', 'th'): self.cell = []
        if tag == 'a' and attrs.get('href'): self.links.append(attrs['href'])

    def handle_endtag(self, tag):
        if tag == 'title': self.in_title = False
        if tag == 'p': self.in_lead = False
        if tag in ('td', 'th') and self.cell is not None:
            self.cells.append(re.sub(r'\s+', ' ', ''.join(self.cell)).strip())
            self.cell = None

    def handle_data(self, value):
        if self.in_title: self.title.append(value)
        if self.in_lead: self.lead.append(value)
        if self.cell is not None: self.cell.append(value)


def fragment(text, tag, identifier):
    # Researched source bodies have no nested <article>; compare every byte,
    # including technical examples, all four FAQ answers and neighborhood links.
    start = text.index('<' + tag + ' id="' + identifier + '"')
    end = text.index('</' + tag + '>', start) + len(tag) + 3
    return text[start:end]


class MasterContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(master.DATA_PATH.read_text())
        files = builder.archive_files(ROOT)
        builder.overlay(files, ROOT / 'server')
        builder.overlay(files, ROOT / 'overrides')
        # Exercise the hook at its intended point, after existing navigation.
        for name, file, hook in [
            ('master_registry', 'brand_registry.py', 'build_registry'),
            ('master_models', 'enhance_models.py', 'enhance_files'),
            ('master_landings', 'landing_actions.py', 'enhance_landings'),
            ('master_links', 'internal_links.py', 'enhance_files'),
        ]:
            getattr(module(name, ROOT / 'scripts' / file), hook)(files)
        cls.before = files
        cls.files = copy.copy(files)
        cls.report = master.enhance_files(cls.files)
        catalog = json.loads(files['assets/servis-katalog.json'])
        cls.districts = {master._slug(district) + '-' + device + '-servisi.html': (district, device)
                         for district in catalog['districts'] for device in ('kombi', 'klima')}

    def test_extracted_data_has_all_requested_source_rows(self):
        self.assertEqual(self.data['source_sha256'], 'b9d18615da5e2edf9a55505a223e287001add42bfc612dd19d99866d70fc6e00')
        self.assertEqual(len(self.data['brand_meta']), 8)
        self.assertEqual(len(self.data['region_chips']), 12)
        self.assertEqual(set(self.data['matrix_html']), {'kombi', 'klima'})
        template_hashes = {'kombi': 'd10faae168585e4d968a634e6245564cdbf33b3db587910f4ed19d8a115d69fd',
                           'klima': '2f4eed7de55a1a6351b449f2e9a77111dc1696312943eef21fe4884f8b358e86'}
        for device, rows in [('kombi', 8), ('klima', 5)]:
            self.assertEqual(hashlib.sha256(self.data['matrix_html'][device].encode()).hexdigest(), template_hashes[device])
            page = ReadPage(self.data['matrix_html'][device])
            self.assertEqual(len(page.cells), (rows + 1) * 4, device)
        # Guard entire rows/cells, including the final brands, against truncation.
        self.assertIn('501 (5P3), 108, 101, 104, 601', ReadPage(self.data['matrix_html']['kombi']).cells)
        self.assertIn('E1, E3, E4, E6, F0, F1, H3, P0, EC', ReadPage(self.data['matrix_html']['klima']).cells)

    def test_all50_receive_the_exact_source_cells_and_district_metadata(self):
        self.assertEqual((self.report['district_pages'], self.report['kombi_district_pages'], self.report['klima_district_pages']), (50, 25, 25))
        self.assertEqual(self.report['matrix_rows'], 325)
        for name, (district, device) in self.districts.items():
            before = self.before[name].decode()
            after = self.files[name].decode()
            with self.subTest(name=name):
                names = list(dict.fromkeys(html.unescape(value) for value in re.findall(r'mahalle=[^"]+">([^<]+)</a>', before)))
                first_six = ', '.join(names[:6]) or district + ' merkez'
                expected = self.data['matrix_html'][device].replace('{$ilce}', html.escape(district)).replace('{$mahalleMetni}', html.escape(first_six))
                page = ReadPage(after)
                self.assertEqual(page.cells, ReadPage(expected).cells)
                values = {key: value.replace('{$ilce}', district).replace('{$mahalleMetni}', first_six)
                          for key, value in self.data['district_meta'][device].items()}
                self.assertEqual(''.join(page.title), values['title'])
                self.assertEqual(page.meta['description'], values['desc'])
                self.assertEqual(page.meta['og:title'], values['title'])
                self.assertEqual(page.meta['og:description'], values['desc'])
                self.assertEqual(''.join(page.lead), values['lead'])
                self.assertEqual(after.count('data-st-master-matrix="' + device + '"'), 1)
                self.assertIn(master.MATRIX_NOTE, html.unescape(after))

    def test_researched_bodies_4faq_technical_examples_and599_links_per_device_unchanged(self):
        totals = {'kombi': 0, 'klima': 0}
        for name, (_, device) in self.districts.items():
            before, after = self.before[name].decode(), self.files[name].decode()
            with self.subTest(name=name):
                body = fragment(before, 'article', 'local-guide-body')
                self.assertIn(body, after)
                self.assertEqual(body.count('class="local-faq-item"'), 4)
                self.assertEqual(before.count('mahalle='), after.count('mahalle='))
                self.assertIn('yerel-', body)
                totals[device] += before.count('mahalle=')
        self.assertEqual(totals, {'kombi': 599, 'klima': 599})
        self.assertEqual(self.report['preserved_neighborhood_links'], 1198)

    def test_eight_brands_exact_metadata_and_twelve_region_chips(self):
        self.assertEqual((self.report['brand_pages'], self.report['region_chip_groups']), (8, 8))
        expected = [(row['path'], row['label']) for row in self.data['region_chips']]
        for name, values in self.data['brand_meta'].items():
            text = self.files[name].decode()
            with self.subTest(name=name):
                page = ReadPage(text)
                self.assertEqual(''.join(page.title), values['title'])
                self.assertEqual(''.join(page.lead), values['lead'])
                self.assertEqual(page.meta['description'], values['desc'])
                block = re.search(r'<div class="region-list" data-st-master-regions="1">(.*?)</div>', text).group(1)
                chips = re.findall(r'<a class="region-chip" href="([^"]+)">([^<]+)</a>', block)
                self.assertEqual(chips, expected)
                for path, _ in chips: self.assertIn(path, self.files)

    def test_baymak_e1_exact_user_metadata_while_guide_body_stays(self):
        name = 'baymak-e1-hatasi.html'
        page = ReadPage(self.files[name].decode())
        self.assertEqual(self.report['baymak_e1_pages'], 1)
        self.assertEqual(''.join(page.title), self.data['baymak_e1']['title'])
        self.assertEqual(''.join(page.lead), self.data['baymak_e1']['lead'])
        self.assertEqual(page.meta['description'], self.data['baymak_e1']['desc'])
        before = self.before[name].decode()
        body = before[before.index('<article'):before.index('</article>') + len('</article>')]
        self.assertIn(body, self.files[name].decode())

    def test_second_run_is_byte_identical_and_no_routes_or_diagnostic_assets_change(self):
        expected = dict(self.files)
        again = master.enhance_files(self.files)
        self.assertEqual(self.files, expected)
        self.assertEqual(again['changed_pages'], [])
        self.assertEqual(set(self.before), set(self.files))
        for name, content in self.before.items():
            if not name.endswith('.html'):
                self.assertEqual(self.files[name], content, name)
        self.assertEqual(hashlib.sha256(self.files['assets/brand/logo-ribbon.png']).hexdigest(),
                         hashlib.sha256(self.before['assets/brand/logo-ribbon.png']).hexdigest())

    def synthetic(self, summary):
        return ('<!doctype html><html><head><title>Old</title><meta data-content="keep" name="description" content="Old"></head>'
                '<body><main><h1 class="at-title">Küçükçekmece kombi servisi</h1><p class="other at-lead">Old lead</p>'
                '<div class="at-content">' + summary + '<article id="local-guide-body"><section><p>KEEP EXACT &amp; unique.</p></section></article>'
                '<a href="servis-sec.html#cihaz=kombi&amp;mahalle=A%26B">A &amp; B &lt;Merkez&gt;</a></div></main></body></html>')

    def test_balanced_nested_div_summary_replacement_does_not_consume_unique_body(self):
        old = '<div data-keep="old" class="x at-summary"><p>Old <strong>summary</strong></p><div><table><tr><td>old</td></tr></table><div>nested</div></div><script>const x="</div>";</script></div>'
        text = self.synthetic(old)
        files = {'assets/servis-katalog.json': json.dumps({'districts': ['Küçükçekmece']}).encode(), 'kucukcekmece-kombi-servisi.html': text.encode()}
        master.enhance_files(files)
        after = files['kucukcekmece-kombi-servisi.html'].decode()
        self.assertNotIn('data-keep="old"', after)
        self.assertNotIn('const x=', after)
        self.assertIn('<article id="local-guide-body"><section><p>KEEP EXACT &amp; unique.</p></section></article>', after)
        self.assertIn('A &amp; B &lt;Merkez&gt;', after)
        self.assertNotIn('A & B <Merkez>', after)
        self.assertIn('data-content="keep"', after)
        expected = dict(files); master.enhance_files(files); self.assertEqual(files, expected)

    def test_paragraph_or_missing_summary_get_one_balanced_matrix(self):
        for summary in ['<p class="at-summary">Old summary</p>', '']:
            with self.subTest(summary=summary):
                files = {'assets/servis-katalog.json': json.dumps({'districts': ['Küçükçekmece']}).encode(), 'kucukcekmece-kombi-servisi.html': self.synthetic(summary).encode()}
                master.enhance_files(files)
                after = files['kucukcekmece-kombi-servisi.html'].decode()
                self.assertEqual(after.count('data-st-master-matrix="kombi"'), 1)
                self.assertIn('KEEP EXACT &amp; unique.', after)

    def test_title_cleanup_is_bounded_to_headings_and_metadata(self):
        old = 'Baxi 200 / / Assure 500'
        scope = ' (ülke/ürün kodu teyidi gerekir)'
        controller = ', Vitotronic kontrol (nesil teyidi gerekir)'
        text = '<html><head><title>' + old + scope + '</title><meta property="og:title" content="' + old + '"></head><body><main><h1>' + old + controller + '</h1><p id="scope-note">' + old + scope + controller + '</p></main></body></html>'
        files = {'scope-example.html': text.encode(), 'assets/models.json': json.dumps({'label': old}).encode()}
        before_json = files['assets/models.json']
        master.enhance_files(files)
        after = files['scope-example.html'].decode()
        self.assertIn('<title>Baxi 200 / 400 / 600 / 800 / Assure 500</title>', after)
        self.assertIn('<h1>Baxi 200 / 400 / 600 / 800 / Assure 500 (Vitotronic)</h1>', after)
        self.assertIn('<p id="scope-note">' + old + scope + controller + '</p>', after)
        self.assertEqual(files['assets/models.json'], before_json)


if __name__ == '__main__':
    unittest.main()
