from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from redirects import MARKER, RULE, apply_redirects


class LegacyRedirectTests(unittest.TestCase):
    def source(self):
        return (b'Options -Indexes\n<IfModule mod_rewrite.c>\nRewriteEngine On\n'
                b'RewriteRule ^index\\.html$ / [R=301,L]\n</IfModule>\n'
                b'<FilesMatch "\\.env$">\nRequire all denied\n</FilesMatch>\n')

    def test_preserves_source_rules_and_is_idempotent(self):
        source = self.source()
        files = {'.htaccess': source, 'kombi-hata-kodu.html': b'<main>Guide</main>'}
        self.assertEqual(apply_redirects(files)['status_code'], 301)
        updated = files['.htaccess']
        self.assertEqual(updated.replace((MARKER + '\n' + RULE + '\n').encode(), b''), source)
        self.assertEqual(apply_redirects(files)['status'], 'already-applied')
        self.assertEqual(files['.htaccess'], updated)

    def test_rule_only_matches_observed_exact_path(self):
        pattern = RULE.split(' ')[1]
        self.assertTrue(re.fullmatch(pattern, 'kombi-hata-kodu.h'))
        for path in ['kombi-hata-kodu.html', 'xkombi-hata-kodu.h',
                     'foo/kombi-hata-kodu.h', 'kombi-hata-kodu.h/extra',
                     'kombi-hata-koduXh', 'other.h']:
            self.assertFalse(re.fullmatch(pattern, path), path)
        self.assertEqual(RULE.split()[2], '/kombi-hata-kodu.html')
        self.assertNotIn('?', RULE)  # Apache retains the original query, without inventing a new URL.

    def test_refuses_missing_destination_or_rewrite_scope(self):
        with self.assertRaises(ValueError):
            apply_redirects({'.htaccess': self.source()})
        with self.assertRaises(ValueError):
            apply_redirects({'.htaccess': b'Options -Indexes', 'kombi-hata-kodu.html': b''})


if __name__ == '__main__':
    unittest.main()
