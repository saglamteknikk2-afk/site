"""Correct one observed truncated legacy URL without broad path rewriting."""
from __future__ import annotations

import re

MARKER = '# HYBRID-LEGACY-URL:v1'
RULE = r'RewriteRule ^kombi-hata-kodu\.h$ /kombi-hata-kodu.html [R=301,L]'


def apply_redirects(files: dict[str, bytes]) -> dict:
    if 'kombi-hata-kodu.html' not in files:
        raise ValueError('The legacy redirect destination must exist.')
    source = files.get('.htaccess', b'').decode('utf-8')
    if MARKER in source:
        if source.count(RULE) != 1:
            raise ValueError('Unexpected legacy redirect configuration.')
        return {'status': 'already-applied', 'exact_legacy_redirects': 1}
    engine = re.search(r'(?mi)^RewriteEngine[ \t]+On[ \t]*\r?$', source)
    end = source.find('</IfModule>', engine.end()) if engine else -1
    if not engine or end < 0:
        raise ValueError('Expected the source Apache rewrite module block.')
    newline = '\r\n' if '\r\n' in source else '\n'
    block = MARKER + newline + RULE + newline
    files['.htaccess'] = (source[:end] + block + source[end:]).encode('utf-8')
    return {'status': 'applied', 'exact_legacy_redirects': 1,
            'from': '/kombi-hata-kodu.h', 'to': '/kombi-hata-kodu.html',
            'status_code': 301, 'query_string': 'preserved',
            'scope': 'Production Apache only; existing security and host rules retained.'}
