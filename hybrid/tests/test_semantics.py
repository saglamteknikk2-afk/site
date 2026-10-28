import importlib.util
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

MODULE = Path(__file__).resolve().parents[1] / 'semantics.py'
spec = importlib.util.spec_from_file_location('hybrid_semantics', MODULE)
semantics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(semantics)


def fixture(name, *, robots='', body='', graph=None):
    canonical = semantics.ORIGIN if name == 'index.html' else semantics.ORIGIN + name
    return ('<!doctype html><html><head><title>Test</title><meta name="description" content="Bakım ve arıza ön bilgisi.">'
            f'<meta name="robots" content="{robots}"><link rel="canonical" href="{canonical}">'
            '<script type="application/ld+json">' + json.dumps({'@context':'https://schema.org','@graph':graph or []})
            + '</script></head><body><main><h1>Servis bilgisi</h1>' + body + '</main></body></html>').encode()


def initial_files():
    return {'assets/servis-verileri.js': b'window.ST_SERVICE_DATA={"districts":["Avcilar"]};',
            'robots.txt': b'User-agent: *\nAllow: /\nDisallow: /private/\nDisallow: /api.php\n',
            'llms-full.txt': b'Original detailed source inventory',
            'index.html': fixture('index.html'),
            'kombi-basinci.html': fixture('kombi-basinci.html', body='<details><summary>Ne zaman başladı?</summary><p>Isıtma sırasında <strong>değeri</strong> not edin.</p></details>'),
            'foreign-ariza-kodlari.html': fixture('foreign-ariza-kodlari.html', robots='noindex,follow'),
            'aydinlatma.html': fixture('aydinlatma.html', body='<details class="st-hub-faq"><summary>Servis alabilir miyim?</summary><p>Evet.</p></details>'),
            '404.html': fixture('404.html', robots='noindex,follow'),
            'servis-sec.html': fixture('servis-sec.html', robots='noindex,follow')}


def graph(files, name):
    payload = semantics.SCRIPT.findall(files[name].decode())
    assert len(payload) == 1
    return json.loads(payload[0])['@graph']


class SemanticBuildTests(unittest.TestCase):
    def test_address_and_reference_normalization(self):
        files=initial_files()
        files['index.html']=fixture('index.html', graph=[{'@type':'WebSite','publisher':{'@id':semantics.ORIGIN+'#isletme'}}])
        semantics.apply_semantics(files)
        nodes=graph(files,'index.html')
        business=next(n for n in nodes if 'LocalBusiness' in n.get('@type',[]))
        self.assertEqual(business['@id'],semantics.BUSINESS_ID)
        self.assertEqual(business['address'],semantics.BUSINESS_ADDRESS)
        self.assertNotIn('geo',business)
        self.assertNotIn('priceRange',business)
        self.assertEqual(next(n for n in nodes if n['@type']=='WebSite')['publisher']['@id'],semantics.BUSINESS_ID)

    def test_faq_is_exact_visible_text(self):
        files=initial_files();semantics.apply_semantics(files)
        nodes=graph(files,'kombi-basinci.html')
        faq=next(n for n in nodes if n['@type']=='FAQPage')
        self.assertEqual(faq['mainEntity'],[{'@type':'Question','name':'Ne zaman başladı?',
                         'acceptedAnswer':{'@type':'Answer','text':'Isıtma sırasında değeri not edin.'}}])

    def test_fallback_faq_is_visible_and_not_only_schema(self):
        files=initial_files();semantics.apply_semantics(files)
        source=files['index.html'].decode();page=semantics.Page(source)
        faq=next(n for n in graph(files,'index.html') if n['@type']=='FAQPage')
        self.assertEqual(page.faq()[0][0],faq['mainEntity'][0]['name'])
        self.assertIn('class="hybrid-faq',source)

    def test_policy_and_foreign_pages_do_not_claim_service(self):
        files=initial_files();semantics.apply_semantics(files)
        for name in ['aydinlatma.html','foreign-ariza-kodlari.html']:
            types=[t for n in graph(files,name) for t in (n['@type'] if isinstance(n['@type'],list) else [n['@type']])]
            self.assertNotIn('Service',types)
            self.assertNotIn('FAQPage',types)
        self.assertNotIn('Servis alabilir miyim?',files['aydinlatma.html'].decode())

    def test_inventory_and_sitemap_exclude_noindex_and_private(self):
        files=initial_files();report=semantics.apply_semantics(files)
        paths=report['inventory']['paths']
        self.assertEqual(paths,['aydinlatma.html','index.html','kombi-basinci.html'])
        self.assertEqual(report['inventory']['actual_canonical_pages'],3)
        self.assertFalse(report['inventory']['fixed_count_enforced'])
        xml=ET.fromstring(files['sitemap.xml'])
        self.assertEqual(len(list(xml)),3)
        self.assertIn('3 indexlenebilir',files['llms.txt'].decode())
        self.assertNotIn('foreign-ariza-kodlari.html',files['llms.txt'].decode())
        self.assertNotIn('404.html',files['llms.txt'].decode())
        self.assertEqual(files['llms-full.txt'],b'Original detailed source inventory')

    def test_private_robots_exclusions_retained(self):
        files=initial_files();semantics.apply_semantics(files)
        self.assertIn(b'Disallow: /private/',files['robots.txt'])
        self.assertIn(b'Disallow: /api.php',files['robots.txt'])
        self.assertEqual(files['robots.txt'].count(b'Sitemap:'),1)

    def test_service_scope_uses_actual_district_or_brand(self):
        files=initial_files()
        files['assets/servis-verileri.js'] = ('window.ST_SERVICE_DATA=' + json.dumps({
            'districts':['Küçükçekmece'], 'devices':{'kombi':{'brands':['Baymak']}}})+';').encode()
        files['kucukcekmece-kombi-servisi.html']=fixture('kucukcekmece-kombi-servisi.html')
        files['baymak-kombi-servisi.html']=fixture('baymak-kombi-servisi.html')
        semantics.apply_semantics(files)
        local=next(n for n in graph(files,'kucukcekmece-kombi-servisi.html') if n['@type']=='Service')
        brand=next(n for n in graph(files,'baymak-kombi-servisi.html') if n['@type']=='Service')
        self.assertEqual(local['areaServed'],{'@type':'AdministrativeArea','name':'Küçükçekmece, İstanbul'})
        self.assertEqual(brand['brand'],{'@type':'Brand','name':'Baymak'})

    def test_other_canonical_is_not_advertised_as_a_second_page(self):
        files=initial_files()
        files['alias.html']=fixture('alias.html').replace(b'/alias.html',b'/kombi-basinci.html')
        report=semantics.apply_semantics(files)
        self.assertNotIn('alias.html',report['inventory']['paths'])
        self.assertNotIn(b'/alias.html',files['sitemap.xml'])
        self.assertFalse(any(n['@type']=='Service' for n in graph(files,'alias.html')))

    def test_replacing_service_keeps_webpage_references_valid(self):
        files=initial_files();url=semantics.ORIGIN+'kombi-basinci.html'
        files['kombi-basinci.html']=fixture('kombi-basinci.html',graph=[
            {'@type':'WebPage','@id':url+'#sayfa','mainEntity':{'@id':url+'#hizmet'}},
            {'@type':'Service','@id':url+'#hizmet'}])
        semantics.apply_semantics(files)
        nodes=graph(files,'kombi-basinci.html')
        page=next(n for n in nodes if n['@type']=='WebPage')
        self.assertEqual(page['mainEntity'],{'@id':url+'#service'})
        self.assertTrue(any(n.get('@id')==page['mainEntity']['@id'] for n in nodes))

    def test_idempotent_schema_and_inventory(self):
        files=initial_files();semantics.apply_semantics(files);once=dict(files)
        semantics.apply_semantics(files)
        self.assertEqual(files,once)


if __name__=='__main__':unittest.main()
