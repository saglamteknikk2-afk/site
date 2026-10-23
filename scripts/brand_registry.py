"""Build every brand selector from one registry; never invent models or routes."""
from __future__ import annotations
import html
import json
import re
from urllib.parse import urlencode


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def brand_sections(text, registry):
    for device in ('kombi', 'klima'):
        cards = []
        for row in registry['brands']:
            if device not in row['devices']:
                continue
            name = html.escape(row['name'])
            count = len(row['guides_by_device'][device])
            anchor = ('' if device == 'kombi' else 'klima-') + row['id']
            model_url = '/model-ariza-kodlari.html?' + urlencode({'device': device, 'brand': row['name']})
            intake_url = '/index.html?' + urlencode({'cihaz': device, 'marka': row['name'], 'usta': '1'}) + '#ai-usta'
            status = f'{count} üretici belgesi kapsamındaki model ailesi' if count else 'Modele özel doğrulanmış kod tablosu henüz yok'
            note = row.get('notes') or ('Bu bir satış / servis ağı adıdır. Cihaz etiketindeki ürün markasını ayrıca belirtin.' if row['kind'] == 'service_network' else 'Servis ve parça uygunluğu tam model bilgisiyle görüşülür.')
            cards.append(f'<article id="{anchor}" data-brand="{name}" data-device="{device}" class="glass-box rounded-2xl p-5"><h3 class="text-lg font-bold text-white mb-2">{name}</h3><p class="text-xs text-slate-300 leading-relaxed">{html.escape(status)}. {html.escape(note)}</p><a href="{html.escape(model_url)}" class="block mt-4 text-xs text-emerald-300 font-bold">Model ve belge kapsamı →</a><a href="{html.escape(intake_url)}" class="inline-flex mt-3 text-xs text-cyan-300">Belirtimle devam et →</a></article>')
        section = f'<section id="{device}-markalari" class="mt-8"><h2 class="text-xl font-bold text-white mb-5">{device.capitalize()} marka ve tedarikçi kayıtları</h2><div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">' + ''.join(cards) + '</div></section>'
        text, count = re.subn(r'<section\b[^>]*\bid="' + device + r'-markalari"[^>]*>[\s\S]*?</section>', lambda _: section, text, count=1)
        if count != 1:
            raise ValueError('Brand list section missing: ' + device)
    counts = {device: sum(device in b['devices'] for b in registry['brands']) for device in ('kombi', 'klima')}
    text = re.sub(r'32 kombi ve 32 klima markası için model, konum ve arıza bilgisiyle Sağlam Teknik servis planlaması\.', f"{counts['kombi']} kombi ve {counts['klima']} klima marka / tedarikçi kaydı. Doğrulanmış model kılavuzları ve servis görüşmesi kapsamı ayrı gösterilir.", text)
    return text


def build_registry(files: dict[str, bytes]) -> dict:
    registry = json.loads(files['assets/brand-registry.json'])
    faults = json.loads(files['assets/verified-faults.json'])
    services = json.loads(files['assets/servis-katalog.json'])
    rows = registry['brands']
    names = {row['name']: row for row in rows}
    if len(names) != len(rows) or len({row['id'] for row in rows}) != len(rows):
        raise ValueError('Duplicate brand identity in shared registry')
    for row in rows:
        row['guides_by_device'] = {d: [] for d in row['devices']}
        row['verified_model_ids'] = []
    for model in faults['models']:
        row = names.get(model['brand'])
        if row is None or model['device'] not in row['devices']:
            raise ValueError('Verified model has no shared brand/device: ' + model['id'])
        row['guides_by_device'][model['device']].append(model['id'])
        row['verified_model_ids'].append(model['id'])
    for row in rows:
        row['guide_count'] = len(row['verified_model_ids'])
    registry_bytes = encode(registry)
    client = files['assets/brand-registry.js']
    files['assets/brand-registry.json'] = registry_bytes + b'\n'
    files['assets/brand-registry.js'] = b'window.ST_BRAND_REGISTRY=' + registry_bytes + b';\n' + client
    for device, config in services['devices'].items():
        if device in ('kombi', 'klima'):
            config['brands'] = [r['name'] for r in rows if device in r['devices']]
    services['brands'] = services['devices']['kombi']['brands']
    services['brand_aliases'] = {r['name']: r['aliases'] for r in rows if r.get('aliases')}
    services['brand_registry_schema_version'] = registry['schema_version']
    matrix = services.get('selection_matrix', {})
    for device, entry in matrix.get('devices', {}).items():
        if device not in ('kombi', 'klima'):
            continue
        entry['brands'] = len(services['devices'][device]['brands'])
        entry['brand_options_including_unspecified'] = entry['brands'] + 1
        entry['location_brand_need_selections'] = entry['location_options'] * entry['brand_options_including_unspecified'] * (entry['services'] + entry['symptoms'])
    if matrix.get('devices'):
        matrix['total_selections'] = sum(x['location_brand_need_selections'] for x in matrix['devices'].values())
    payload = encode(services)
    files['assets/servis-katalog.json'] = payload + b'\n'
    files['assets/servis-verileri.js'] = b'window.ST_SERVICE_DATA=' + payload + b';\n'
    if 'servis-verileri.js' in files:
        files['servis-verileri.js'] = files['assets/servis-verileri.js']
    if 'markalar.html' in files:
        files['markalar.html'] = brand_sections(files['markalar.html'].decode('utf-8'), registry).encode('utf-8')
    return {'brands': len(rows), 'device_brands': {d: len(c['brands']) for d, c in services['devices'].items()}, 'verified_guides': len(faults['models'])}
