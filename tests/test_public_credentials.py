"""Public-output privacy regression; synthetic IDs only, no personal documents."""
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('public_credentials', Path(__file__).resolve().parents[1] / 'scripts/public_credentials.py')
privacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(privacy)

SYNTHETIC_ID = 'YB9999/99UY9999-9/99/123456'


class PublicCredentialTests(unittest.TestCase):
    def test_all_generated_public_text_locations_are_masked(self):
        files = {name: ('Belge no: ' + SYNTHETIC_ID).encode() for name in ['index.html', 'llms.txt', 'assets/profile.js', 'assets/labels.svg', 'assets/profile.css', 'profile.php']}
        report = privacy.mask_public_credentials(files)
        self.assertEqual(report['identifiers_masked'], 6)
        self.assertTrue(all(SYNTHETIC_ID.encode() not in value and b'****' in value for value in files.values()))
        self.assertNotIn(SYNTHETIC_ID, json.dumps(report))

    def test_decoded_json_cannot_reveal_an_escaped_number(self):
        escaped = '\\u0059' + SYNTHETIC_ID[1:].replace('/', '\\u002f')
        files = {'assets/profile.json': ('{"claims":[{"credential_number":"' + escaped + '"}]}').encode()}
        privacy.mask_public_credentials(files)
        self.assertEqual(json.loads(files['assets/profile.json'])['claims'][0]['credential_number'], '****')

    def test_escaped_slashes_and_html_entities_are_masked(self):
        for value in [SYNTHETIC_ID.replace('/', '\\/'), SYNTHETIC_ID.replace('/', '&#47;'), SYNTHETIC_ID.lower()]:
            self.assertEqual(privacy.mask_text(value), ('****', 1))

    def test_manufacturer_identifiers_and_trade_names_are_preserved(self):
        source = 'MYK belgeli Isıtma ve Gaz Yakıcı Cihaz Servis Personeli (Seviye 4). Manual 0020228723_05; TD-20230100; 300032122 Rev.04; VUW TR 236/5-3; E01/F04.'
        files = {'index.html': source.encode(), 'assets/verified-faults.json': json.dumps({'model': source}).encode()}
        original = dict(files)
        self.assertEqual(privacy.mask_public_credentials(files)['identifiers_masked'], 0)
        self.assertEqual(files, original)

    def test_binary_assets_are_never_modified_and_pass_is_idempotent(self):
        files = {'index.html': SYNTHETIC_ID.encode(), 'certificate.pdf': b'%PDF already separately redacted', 'portrait.webp': b'RIFF image'}
        privacy.mask_public_credentials(files)
        first = dict(files)
        self.assertEqual(privacy.mask_public_credentials(files)['identifiers_masked'], 0)
        self.assertEqual(files, first)
