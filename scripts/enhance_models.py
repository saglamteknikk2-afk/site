"""Source-preserving model-page presentation. No model/code inference or edits."""
from __future__ import annotations
import html
import json
import re
from pathlib import PurePosixPath
from urllib.parse import urlencode


def family_title(model: dict) -> str:
    family = model['label'].split('—')[0].strip()
    family = re.sub(r'\s+\d+(?:\s*/\s*\d+){2,}(?:\s*kW)?', '', family, flags=re.I).strip()
    if len(family) > 85:
        family = (model.get('model_names') or [family[:72]])[0] + ' ailesi'
    device = 'Klima' if model['device'] == 'klima' else 'Kombi'
    return f"{model['brand']} {family} · {device} hata kodları"


def enhance_html(text: str, models: list[dict]) -> str:
    if not models or 'data-st-model-enhanced="1"' in text:
        return text
    model = models[0]
    safe = lambda s: html.escape(str(s or ''), quote=True)
    title = family_title(model)
    text = re.sub(r'(<h1\b[^>]*>)[\s\S]*?(</h1>)', lambda m: m[1] + safe(title) + m[2], text, count=1)
    text = re.sub(r'<title>[\s\S]*?</title>', '<title>' + safe(title) + ' | Sağlam Teknik</title>', text, count=1)
    text = re.sub(r'(<meta\b[^>]*property="og:title"[^>]*content=")[^"]*(")', lambda m: m[1] + safe(title) + ' | Sağlam Teknik' + m[2], text, count=1)
    # Keep the full original source/model text, available on demand.
    scope_re = r'<section\b[^>]*class="[^"\n]*\bfault-scope\b[^"\n]*"[^>]*>[\s\S]*?</section>'
    def collapse(m):
        scope = re.sub(r'<h2\b[^>]*>[\s\S]*?</h2>', '<h2>Üretici belgesi ve kapsamdaki modeller</h2>', m[0], count=1)
        return '<details class="mb-scope-notes"><summary>Kapsamdaki modeller ve üretici kaynağı</summary>' + scope + '</details>'
    text = re.sub(scope_re, collapse, text, count=1)
    restricted = model.get('requires_scope_confirmation') or model.get('requires_document_match') or model.get('matchable') is False
    note = 'Belgeyi cihazınıza uygulamadan önce ülke, ürün son eki ve varsa belge numarasının eşleştiğini kontrol edin.' if restricted else 'Cihaz etiketindeki tam model adı bu üretici belgesinin kapsamında olmalıdır.'
    pieces = ['<aside id="modelScopeNote" class="mb-scope-note" aria-label="Model ve belge kapsamı"><span>' + note + '</span>']
    if model.get('market'):
        pieces.append('<p>Belgenin pazarı / bölgesi: <strong>' + safe(model['market']) + '</strong></p>')
    if model.get('scope_note'):
        pieces.append('<p>' + safe(model['scope_note']) + '</p>')
    if model.get('matchable') is False:
        pieces.append('<p>Kapasite veya marka benzerliğinden otomatik kod yorumu yapılmaz. Belge kapsamını ve gösterge örüntüsünü kontrol edin.</p>')
    pieces.append('</aside><div class="mb-table-links"><a href="/model-ariza-kodlari.html">← Başka model ara</a><a href="/index.html#aiUstaWizard">Kod yok, belirtimle devam et →</a></div>')
    def table(m):
        tag = re.sub(r'\s+id="[^"]*"', '', m[0])
        tag = tag[:-1] + ' id="kodlar" data-st-model-enhanced="1">'
        return ''.join(pieces) + tag
    text = re.sub(r'<section\b[^>]*class="[^"\n]*\bfault-table-section\b[^"\n]*"[^>]*>', table, text, count=1)
    if 'assets/model-browser.css' not in text:
        text = text.replace('</head>', '<link rel="stylesheet" href="/assets/model-browser.css"></head>')
    return text


def enhance_files(files: dict[str, bytes]) -> int:
    raw = files.get('assets/verified-faults.js', b'').decode('utf-8')
    match = re.search(r'window\.ST_VERIFIED_FAULTS\s*=\s*([\s\S]*?);?\s*$', raw)
    if not match:
        raise ValueError('Verified fault data assignment not found')
    data = json.loads(match[1].rstrip(';').strip())
    pages: dict[str, list[dict]] = {}
    for model in data['models']:
        name = PurePosixPath(model['path']).name
        pages.setdefault(name, []).append(model)
    hub_name = 'model-ariza-kodlari.html'
    if hub_name in files:
        hub = files[hub_name].decode('utf-8')
        if 'id="modelBrowser"' in hub and 'id="modelGuideDirectory"' not in hub:
            cards = []
            entries = []
            for model in data['models']:
                title = family_title(model)
                path = model['path'].replace('/site/', '/')
                entries.append('<li><a href="' + html.escape(path + '#kodlar', quote=True) + '">' + html.escape(title) + '</a></li>')
                for name in model.get('model_names') or [model['label']]:
                    if len(cards) >= 30:
                        break
                    numeric = bool(re.fullmatch(r'\d+(?:[.,]\d+)?\s*(?:kW|BTU|BTU/H)?', name, re.I))
                    label = model['label'] if numeric else name
                    if not label.lower().startswith(model['brand'].lower()):
                        label = model['brand'] + ' ' + label
                    target = path + '?' + urlencode({'model':name, 'model_id':model['id']}) + '#kodlar'
                    device = 'Klima' if model['device'] == 'klima' else 'Kombi'
                    cards.append('<a class="mb-card" data-model-card data-verified="true" href="' + html.escape(target, quote=True) + '"><span class="mb-card-meta">' + device + ' · Üretici belgesi var</span><h2>' + html.escape(label) + '</h2><p>Cihaz etiketindeki tam adı ve belgenin kapsamını kontrol edin.</p><span class="mb-card-link">Kodları aç ↗</span></a>')
            hub = hub.replace('<div id="modelResults" class="mb-grid"></div>', '<div id="modelResults" class="mb-grid">' + ''.join(cards) + '</div>')
            coverage = []
            for row in data.get('coverage', []):
                n = len(row.get('verified_model_ids', []))
                status = str(n) + ' belgelenmiş model ailesi' if n else 'Modele özel tablo henüz yok'
                device = 'Klima' if row['device'] == 'klima' else 'Kombi'
                coverage.append('<li><strong>' + html.escape(row['brand']) + '</strong><span>' + device + ' · ' + status + '</span></li>')
            hub = hub.replace('<ul id="brandCoverage"></ul>', '<ul id="brandCoverage">' + ''.join(coverage) + '</ul>')
            directory = '<details id="modelGuideDirectory" class="mb-coverage"><summary>Model ailelerinin tüm belge rehberleri</summary><ul>' + ''.join(entries) + '</ul></details>'
            hub = hub.replace('<p class="mb-scope-note">', directory + '<p class="mb-scope-note">', 1)
            files[hub_name] = hub.encode('utf-8')
    count = 0
    for name, models in pages.items():
        if name not in files:
            continue
        files[name] = enhance_html(files[name].decode('utf-8'), models).encode('utf-8')
        count += 1
    return count
