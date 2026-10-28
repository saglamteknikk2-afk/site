"""Minimal correction of paths returned by the uploaded browser query resolver.

This adapts accepted local routes to document-relative URLs. It does not change
query inference, model scope, code definitions, or the untouched PHP backend.
"""
from __future__ import annotations


def correct_routes(files: dict[str, bytes]) -> dict:
    name = 'assets/servis-search.js'
    text = files[name].decode('utf-8')
    replacements = [
        (
            "  const q = norm(query), catalog = window.ST_ORGANIC_CATALOG || {};",
            "  const q = norm(query), catalog = window.ST_ORGANIC_CATALOG || {};\n"
            "  // Accept the archive's local route spelling and return mount-independent links.\n"
            "  const routeKey = value => {\n"
            "    const path = String(value || '').replace(/^(?:\\.\\/|\\/)/, '');\n"
            "    return /^[a-z0-9-]+\\.html$/.test(path) ? path : '';\n"
            "  };",
        ),
        (
            "  const faultModelPath = fault?.model?.path && /^\\/[a-z0-9-]+\\.html$/.test(fault.model.path)\n    ? fault.model.path : '';",
            "  const faultModelPath = routeKey(fault?.model?.path);",
        ),
        (
            "  const allowed = new Set(catalog.published_routes || []);",
            "  const allowed = new Set((catalog.published_routes || []).map(routeKey).filter(Boolean));",
        ),
        (
            "  const knownPath = path => allowed.has(path) ? path : '';",
            "  const knownPath = path => allowed.has(routeKey(path)) ? routeKey(path) : '';",
        ),
    ]
    for before, after in replacements:
        if text.count(before) != 1:
            raise ValueError('Unexpected resolver source; refusing an unverified route patch')
        text = text.replace(before, after, 1)
    files[name] = text.encode('utf-8')
    return {
        'files': [name],
        'kind': 'browser route spelling only',
        'preserved': ['model inference', 'code scope', 'flexKey', 'PHP backend'],
    }
