#!/usr/bin/env python3
"""Build a synchronous model-name directory; never create fault definitions.

Run after changing verified-faults.json. Additional names are transcribed only
from the cited manufacturer's catalogue/manual, independently of code coverage.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'overrides/assets'
CHECKED = '2026-10-25'


def key(value: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


# Product/series names are identification aids, NOT matching fault manuals.
# Source URL, market, and record kind are retained for every additional name.
ADDITIONS = [
    ('kombi', 'Vaillant', 'series', 'https://www.vaillant.com.tr/urunler/ecotec-plus-vcw/', ['ecoTEC plus']),
    ('kombi', 'Vaillant', 'model', 'https://www.vaillant.com.tr/downloads/profesyoneller/sartnameler/cihaz-montaji-el-kitabi-gaz-yakan-cihazlar-8101048261-02-2652546.pdf', ['ecoTEC plus VUW 26CS/1-5 (N-TR)', 'ecoTEC plus VUW 32CS/1-5 (N-TR)', 'ecoTEC plus VUW 36CS/1-5 (N-TR)', 'ecoTEC plus VUW 40CS/1-5 (N-TR)']),
    ('kombi', 'Vaillant', 'series', 'https://www.vaillant.com.tr/urunler/ecotec-pure/', ['ecoTEC pure']),
    ('kombi', 'Vaillant', 'model', 'https://www.vaillant.com.tr/pdf/ecotec-pure-0020250678-03-2555262.pdf', ['ecoTEC pure VUW 236/7-2 (H-TR)', 'ecoTEC pure VUW 286/7-2 (H-TR)']),
    ('kombi', 'Vaillant', 'model', 'https://www.vaillant.com.tr/pdf/ecotec-pure-kullanm-klavuzu-1099614.pdf', ['ecoTEC pure VUW 236/7-2 (H-TR) S', 'ecoTEC pure VUW 286/7-2 (H-TR) S']),
    ('kombi', 'Vaillant', 'series', 'https://www.vaillant.com.tr/urunler/ecotec-intro/', ['ecoTEC intro']),
    ('kombi', 'Vaillant', 'model', 'https://www.vaillant.com.tr/urunler/ecotec-intro/', ['ecoTEC intro VUW 24/24 AS/2-1 (H-TR)', 'ecoTEC intro VUW 28/28 AS/2-1 (H-TR)']),
    ('kombi', 'Vaillant', 'model', 'https://www.vaillant.com.tr/musterilerimize-ozel/urunler/ecotec-ntro-tam-yogusmal-kombi-41026.html', ['ecoTEC intro VUW 18/24 AS/1-1', 'ecoTEC intro VUW 24/28 AS/1-1']),
    ('kombi', 'Vaillant', 'series', 'https://www.vaillant.com.tr/musterilerimize-ozel/urunler/ecotec-pro-tam-yogusmal-kombi-41027.html', ['ecoTEC pro']),
    ('kombi', 'Vaillant', 'series', 'https://ucretsizkesif.vaillant.com.tr/', ['ecoTEC exclusive 36 Multi']),
    ('kombi', 'Vaillant', 'series', 'https://www.vaillant.com.tr/downloads/atmotec-pro-plus-turbotec-pro-plus-0020195893-04-2329924.pdf', ['atmoTEC pro', 'atmoTEC plus', 'turboTEC pro', 'turboTEC plus']),
    ('kombi', 'Vaillant', 'model', 'https://www.vaillant.com.tr/downloads/profesyoneller/atmotec-turbotec-pro-plus-nesil-3-0020029209-03-2329923.pdf', ['VUW TR 200/3-3', 'VUW TR 200/3-5', 'VUW TR 240/3-3', 'VUW TR 240/3-5', 'VUW TR 280/3-5', 'VUW TR 202/3-3', 'VUW TR 202/3-5', 'VUW TR 242/3-3', 'VUW TR 242/3-5', 'VUW TR 282/3-5', 'VUW TR 362/3-5']),
    ('kombi', 'Vaillant', 'series', 'https://www.vaillant.com.tr/pdf/ecofit-start-montaj-ve-bakm-klavuzu-1099617.pdf', ['ecoFIT start']),
    ('kombi', 'Vaillant', 'model', 'https://www.vaillant.com.tr/pdf/ecofit-start-montaj-ve-bakm-klavuzu-1099617.pdf', ['ecoFIT start VUW 246/1-RC (H-TR)', 'ecoFIT start VUW 286/1-RC (H-TR)', 'ecoFIT start VUW 246/1-RC (H-TR) HEP', 'ecoFIT start VUW 286/1-RC (H-TR) HEP']),
    ('kombi', 'Demirdöküm', 'series', 'https://www.demirdokum.com.tr/urunler/demirdokum-exacontrol-select-36864.html', ['Nitromix', 'Atromix', 'Vintomix', 'Ademix', 'İsomix']),
    ('kombi', 'Demirdöküm', 'series', 'https://www.demirdokum.com.tr/downloads/cihaz-montaji-el-kitabi-2983632.pdf', ['Atron Condense', 'Ventomix']),
    ('kombi', 'Demirdöküm', 'series', 'https://www.demirdokum.com.tr/downloads/nitromix-ioni-sss-2949647.pdf', ['Nitromix Ioni']),
    ('kombi', 'Demirdöküm', 'model', 'https://www.demirdokum.com.tr/downloads/dd-kombi-1-2tse-e-os-tr-03-2860537.pdf', ['Atromix P 20-A/2 (H-TR)', 'Atromix P 24-A/2 (H-TR)', 'Atromix P 28-A/2 (H-TR)', 'Nitron Condense 24', 'Nitron Condense 28', 'vintomiX P 18/24-AS/1 (H-TR)', 'vintomiX P 24/28-AS/1 (H-TR)']),
    ('kombi', 'Baymak', 'series', 'https://www.baymak.com.tr/kullanici-konfor-kilavuzu/neden-tam-yogusmali-kombi-almaliyiz', ['Duotec', 'Duotec Compact', 'Lunatec', 'Novadens', 'Lambert LPY', 'Dolcevita DPY']),
    ('kombi', 'Baymak', 'series', 'https://www.baymak.com.tr/neden-tam-yogusmali-kombi-almaliyim', ['idee', 'Duotec DHW']),
    ('kombi', 'Bosch', 'series', 'https://www.bosch-homecomfort.com/tr/tr/ocs/residential/kombiler-754580-c/', ['Condens 1200 W', 'Condens 2200i W', 'Condens 5700i W']),
    ('kombi', 'ECA', 'series', 'https://eca.com.tr/isitma-sogutma/kombiler/yogusmali', ['Confeo Premix', 'Citius Premix', 'Proteus Premix']),
    ('kombi', 'ECA', 'series', 'https://eca.com.tr/upload/content/21_062022-seminerler-basn-blteni_revize2-pdf-27-06-22.pdf', ['Calora Premix', 'Arceus']),
    ('kombi', 'Viessmann', 'series', 'https://www.viessmann.com.tr/tr/urunlerimiz/kontrol-sistemi-ve-baglanti/oda-termostatlari.html', ['Vitodens 050-T', 'Vitodens 050-W', 'Vitodens 100-W', 'Vitopend 100-W', 'Vitodens Trend', 'Vitodens Connect']),
    ('klima', 'Vaillant', 'series', 'https://www.vaillant.com.tr/urunler/climavair-pure/', ['climaVAIR pure']),
    ('klima', 'Vaillant', 'model', 'https://www.vaillant.com.tr/urunler/climavair-pure/', ['VAIB2-090WNI', 'VAIB2-120WNI', 'VAIB2-180WNI', 'VAIB2-240WNI', 'VAIB2-090WNO', 'VAIB2-120WNO', 'VAIB2-180WNO', 'VAIB2-240WNO']),
    ('klima', 'Vaillant', 'series', 'https://www.vaillant.com.tr/urunler/climavair-pro/', ['climaVAIR pro']),
    ('klima', 'Vaillant', 'model', 'https://www.vaillant.com.tr/urunler/climavair-pro/', ['VAIB 1-025 WNI', 'VAIB 1-035 WNI', 'VAIB 1-050 WNI', 'VAIB 1-065 WNI', 'VAIB 1-025 WNO', 'VAIB 1-035 WNO', 'VAIB 1-050 WNO', 'VAIB 1-065 WNO']),
    ('klima', 'Vaillant', 'model', 'https://www.vaillant.com.tr/urunler/climavair-multi-cni/', ['VAM1-025CNI', 'VAM1-035CNI']),
    ('klima', 'Vaillant', 'model', 'https://www.vaillant.com.tr/urunler/climavair-multi-dni/', ['VAM1-035DNI']),
    ('klima', 'Daikin', 'series', 'https://www.daikin.com.tr/daikin-klimalar', ['Sensira', 'Shira Eco', 'Zeta Shira Plus', 'Emura', 'Ururu Sarara', 'Perfera', 'Siesta Sensira']),
    ('klima', 'Daikin', 'series', 'https://www.daikin.com.tr/klimalar/bireysel-klimalar/stylish-klimalar', ['Stylish']),
    ('klima', 'Daikin', 'model', 'https://www.daikin.com.tr/daikin-klimalar', ['FTXF71F', 'FTXF60F', 'FTXP20N9', 'FTXP25N9', 'FTXM20A', 'FTXM25A', 'FTXJ20AW', 'FTXJ20AS', 'FTXZ50N', 'FTXZ35N', 'FVXM50B', 'FVXM35B', 'ATXF71F', 'ATXF50F']),
    ('klima', 'Mitsubishi Electric', 'series', 'https://klima.mitsubishielectric.com.tr/tr', ['HareME MSZ-HR', 'Legendera MSZ-LN', 'Kirigamine Zen MSZ-EF', 'NoviroME MSZ-AY', 'EnviroME MSZ-AP']),
    ('klima', 'Mitsubishi Heavy Industries', 'series', 'https://www.iklimsa.com/duvar-tipi-klimalar/mitsubishi-heavy-duvar-tipi-klimalar', ['Premium', 'Diamond']),
    ('klima', 'Mitsubishi Heavy Industries', 'model', 'https://www.iklimsa.com/duvar-tipi-klimalar', ['SRK25ZS-WT', 'SRK35ZS-WT', 'SRK50ZS-WT', 'SRK25ZSX-W(S)', 'SRK35ZSX-W(S)', 'SRK50ZSX-W(S)']),
    ('klima', 'Baymak', 'series', 'https://www.baymak.com.tr/baymaktan-12-aya-varan-taksit-imkani-devam-ediyor', ['Elegant Soft', 'Elegant Plus', 'Elegant Air', 'Elegant Eco']),
    ('klima', 'Baymak', 'model', 'https://www.baymak.com.tr/klimalar/duvar-tipi-klima/elegant-pluss-duvar-tipi-split-klima', ['Elegant Plus 09', 'Elegant Plus 12', 'Elegant Plus 18', 'Elegant Plus 24']),
    ('klima', 'Baymak', 'series', 'https://www.baymak.com.tr/media/5057/baymak-klima-brosur.pdf', ['Elegant Prime']),
    ('klima', 'ECA', 'series', 'https://eca.com.tr/isitma-sogutma/klimalar', ['Spylos Plus', 'Niobe Black', 'Spylos', 'Ecotech', 'Niobe Blue', 'Niobe Blue Multi Split']),
    ('klima', 'Toshiba', 'series', 'https://www.toshiba-klima.com.tr/klima', ['Seiya', 'Shorai Edge White', 'Shorai Edge Black', 'Shorai Curve White', 'Shorai Curve Black', 'Haori', 'Daiseikai 10']),
    ('klima', 'Toshiba', 'series', 'https://www.toshiba-klima.com.tr/anasayfa', ['Seiya Plus', 'J2FVG']),
    ('klima', 'Altus', 'model', 'https://www.altus.com.tr/urunler/isitma-sogutma-klima', ['ALK 1840', 'ALK 2440', 'ALK 9070', 'ALK 1270']),
    ('klima', 'Kaira', 'model', 'https://kaira.com.tr/assets/pdf/Kaira_Klima_Kullan%C4%B1m_K%C4%B1lavuzu.pdf', ['DTXR25EV1B', 'DTXR35EV1B', 'DTXR50EV1B', 'DTXR71EV1B', 'DRXR25EV1B', 'DRXR35EV1B', 'DRXR50EV1B', 'DRXR71EV1B']),
    ('klima', 'Kaira', 'model', 'https://kaira.com.tr/pdf/kairabrosur.pdf', ['DTXR25E', 'DTXR35E', 'DTXR50E', 'DTXR71E', 'DRXR25E', 'DRXR35E', 'DRXR50E', 'DRXR71E']),
    ('klima', 'Samsung', 'model', 'https://www.samsung.com/tr/air-conditioners/wall-mount/ar80h-ar80h-ai-motion-wind-ai-fast-comfort-cooling-ar80h12caaw-sk/', ['AR80H12CAAW/SK']),
    ('klima', 'Samsung', 'model', 'https://www.samsung.com/tr/air-conditioners/wall-mount/ar80h-ar80h-ai-motion-wind-ai-fast-comfort-cooling-ar70h12cacw-sk/', ['AR70H12CACW/SK']),
    ('klima', 'Samsung', 'model', 'https://www.samsung.com/tr/air-conditioners/wall-mount/ar80h-ar80h-ai-motion-wind-ai-fast-comfort-cooling-ar70h24cacw-sk/', ['AR70H24CACW/SK']),
    ('klima', 'Samsung', 'model', 'https://www.samsung.com/tr/air-conditioners/wall-mount/ar80h-ar80h-ai-motion-wind-ai-fast-comfort-cooling-ar70h12cacb-sk/', ['AR70H12CACB/SK']),
    ('kombi', 'Daxom', 'series', 'https://www.daxom.com/xadmin/docs/img-elektrikli-kombi-brosur-pdoc-878945966529842596.pdf', ['Naviels']),
    ('kombi', 'Daxom', 'model', 'https://www.daxom.com/xadmin/docs/img-elektrikli-kombi-brosur-pdoc-878945966529842596.pdf', ['UKDAX-10EDT', 'UKDAX-12EDT', 'UKDAX-16EDT', 'UKDAX-18EDT', 'UKDAX-20EDT', 'UKDAX-24EDT', 'UKDAX-30EDT', 'UKDAX-36EDT', 'UKDAX-40EDT', 'UKDAX-48EDT', 'UKDAX-6EDM', 'UKDAX-10EDM', 'UKDAX-12EDM', 'UKDAX-16EDM', 'UKDAX-18EDM']),
    ('kombi', 'Copa', 'series', 'https://www.copa.com.tr/tr/dokumanlar?id=19', ['Ultimix', 'e-Lecto', 'Eomix', 'Eomix Plus', 'Nexa']),
    ('klima', 'Copa', 'series', 'https://www.copa.com.tr/tr/dokumanlar?id=19', ['Naya Line', 'Viva Line', 'Salon Tipi 48']),
    ('klima', 'General', 'model', 'https://www.iklimsa.com/kampanyalar/general-klimalar-simdi-iklimsada', ['ASHH09KJTA', 'ASHH12KLTA', 'ASHG18KMTE', 'ASHG24KMTE']),
    ('klima', 'Daylux', 'model', 'https://daylux.com.tr/multisplitklima.php', ['2DMX50N', '3DMX80N', '4DMX105N', '5DMX125N']),
]


def build(verified: dict, registry: dict) -> dict:
    records: dict[tuple[str, str, str], dict] = {}
    candidates: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for model in verified['models']:
        for name in model.get('model_names', []):
            candidates[(model['device'], key(model['brand']), key(name))].append(model)
    for identity, models in candidates.items():
        model = models[0]
        active = [m for m in models if m.get('matchable') is not False and m['manual'].get('source_available') is not False]
        entry = dict(device=model['device'], brand=model['brand'], name=next(n for n in model['model_names'] if key(n) == identity[2]), kind='document-model-name', market=model.get('market', 'document-scope'), status='manual-linked' if len(active) == 1 else 'ambiguous-manual' if active else 'source-unavailable', source_url=model['manual']['url'], checked_at=model['manual'].get('checked_at', verified.get('checked_at')), provenance='existing-verified-manual', code_definitions_added=False)
        if len(active) == 1:
            entry['verified_model_id'] = active[0]['id']
        records[identity] = entry
    for device, brand, kind, url, names in ADDITIONS:
        for name in names:
            identity = (device, key(brand), key(name))
            if identity in records:
                continue  # preserve exact manual scope; catalogue never broadens it
            records[identity] = dict(device=device, brand=brand, name=name, kind=kind, market='TR', status='catalogue-name-only', source_url=url, checked_at=CHECKED, provenance='official-catalogue-or-manual-name', code_definitions_added=False)
    entries = sorted(records.values(), key=lambda e: (e['device'], key(e['brand']), key(e['name'])))
    counts = Counter((e['device'], e['brand']) for e in entries)
    gaps = [dict(device=device, brand=brand['name'], reason='device-label-manufacturer-required' if brand.get('kind') != 'brand' else 'source-backed-name-directory-not-yet-populated') for brand in registry['brands'] for device in brand['devices'] if not counts[(device, brand['name'])]]
    return dict(schema_version=1, checked_at=CHECKED, policy=dict(purpose='model-identification', completeness='partial-source-backed', complete_market_inventory=False, new_fault_definitions=0, notice='Model ve seri adları cihazı tanımak içindir. Arıza kodu yalnız seçilen tam modelin mevcut kaynaklı tablosuyla eşleşir. Listede bulunmayan model yazılabilir veya model bilinmeden devam edilebilir.'), coverage=dict(entries=len(entries), distinct_brands=len({e['brand'] for e in entries}), manual_linked_names=sum(bool(e.get('verified_model_id')) for e in entries), catalogue_name_only=sum(e['status']=='catalogue-name-only' for e in entries), by_brand_device=[dict(device=d, brand=b, names=n) for (d,b),n in sorted(counts.items())], gaps=gaps), entries=entries)


def javascript(directory: dict) -> str:
    data = json.dumps(directory, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    return "'use strict';\n/* Generated by scripts/model_directory.py; names never create fault-code definitions. */\n(()=>{\nconst data=" + data + ";\nconst norm=value=>String(value??'').normalize('NFKC').toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').replace(/ı/g,'i').replace(/\\s+/g,' ').trim();\nconst canonicalBrand=brand=>window.STBrands?.find(brand)?.name||brand;\nconst rows=data.entries.map(row=>Object.freeze({...row}));\nwindow.STModelDirectory=Object.freeze({\nlist(device,brand){const d=norm(device),b=norm(canonicalBrand(brand));return rows.filter(row=>norm(row.device)===d&&(!b||norm(row.brand)===b)).map(row=>({...row}));},\ncoverage(){return JSON.parse(JSON.stringify(data.coverage));},\npolicy:Object.freeze({...data.policy}),\ncheckedAt:data.checked_at\n});\n})();\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    directory = build(json.loads((ASSETS/'verified-faults.json').read_text()), json.loads((ASSETS/'brand-registry.json').read_text()))
    outputs = {'model-directory.json': json.dumps(directory, ensure_ascii=False, indent=2)+'\n', 'model-directory.js': javascript(directory)}
    for filename, content in outputs.items():
        path=ASSETS/filename
        if args.check:
            if not path.is_file() or path.read_text()!=content:
                raise SystemExit('Model directory needs regeneration: '+filename)
        else:
            path.write_text(content)
    print(json.dumps(dict(passed=True, **directory['coverage']),ensure_ascii=False))


if __name__ == '__main__':
    main()
