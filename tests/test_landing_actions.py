import importlib.util
import json
from pathlib import Path
import unittest
from urllib.parse import unquote

spec=importlib.util.spec_from_file_location('landings',Path(__file__).resolve().parents[1]/'scripts/landing_actions.py')
landings=importlib.util.module_from_spec(spec);spec.loader.exec_module(landings)

class LandingTests(unittest.TestCase):
    def test_existing_intent_urls_and_context_survive(self):
        source=b'<h1>Kombi servisi</h1><div class="at-quickfacts"><span>Service</span></div>'
        files={'kombi-servisi.html':source,'ariza-rehberi.html':source}
        routes=landings.enhance_landings(files)
        self.assertEqual([r['path'] for r in routes],['/kombi-servisi.html'])
        rendered=unquote(files['kombi-servisi.html'].decode())
        self.assertIn('tel:05346225515',rendered)
        self.assertIn('https://saglamkombiklima.com.tr/kombi-servisi.html',rendered)
        self.assertEqual(files['ariza-rehberi.html'],source)
        self.assertEqual(json.loads(files['assets/ad-landing-map.json'])['routes'],routes)
    def test_contact_actions_are_not_duplicated(self):
        files={'klima-servisi.html':b'<h1>Klima servisi</h1><div class="at-quickfacts"></div>'}
        landings.enhance_landings(files);landings.enhance_landings(files)
        self.assertEqual(files['klima-servisi.html'].count(b'data-service-contact'),1)

if __name__=='__main__':unittest.main()
