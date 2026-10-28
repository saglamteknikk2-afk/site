"""Build crawlable region content from the versioned editorial/geographic data."""
from __future__ import annotations

import html
import json
from pathlib import Path
import re

DATA_PATH = Path(__file__).with_name('data') / 'regions.json'


def slug(value: str) -> str:
    value = value.translate(str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosuCGIOSU')).lower()
    return re.sub(r'[^a-z0-9]+', '-', value).strip('-')


def load_regions() -> dict:
    return json.loads(DATA_PATH.read_text(encoding='utf-8'))


def _notes(notes: list[dict], place: str) -> str:
    cards = []
    for row in notes:
        cards.append('<article class="hybrid-region-note"><h3>' + html.escape(row['title'])
                     + '</h3><p>' + html.escape(row['text']) + '</p><a href="'
                     + html.escape(row['path'], quote=True) + '">' + html.escape(place)
                     + ' talebinden ilgili belirti rehberine geçin →</a></article>')
    return '<div class="hybrid-note-grid">' + ''.join(cards) + '</div>'


def _neighborhoods(region: dict, device: str) -> str:
    links = []
    for name in region['neighborhoods']:
        anchor = 'mahalle-' + slug(name)
        links.append('<li id="' + anchor + '"><a href="#' + anchor
                     + '" data-hybrid-neighborhood="' + html.escape(name, quote=True)
                     + '" data-hybrid-district="' + html.escape(region['name'], quote=True)
                     + '" data-hybrid-device="' + device + '">' + html.escape(name) + '</a></li>')
    return ('<nav aria-label="' + html.escape(region['name'], quote=True)
            + ' mahalleleri"><ul class="hybrid-neighborhoods">' + ''.join(links) + '</ul></nav>')


def district_block(region: dict, device: str, files: dict[str, bytes]) -> str:
    name = region['name']; label = 'kombi' if device == 'kombi' else 'klima'
    same = region['slug'] + '-' + ('klima' if device == 'kombi' else 'kombi') + '-servisi.html'
    neighbor_links = []
    for nearby in region['neighbors']:
        route = slug(nearby) + '-' + device + '-servisi.html'
        if route in files:
            neighbor_links.append('<li><a href="' + route + '">' + html.escape(nearby)
                                  + ' ' + label + ' servisi</a></li>')
    return ('<!-- HYBRID-REGION:START --><section id="bolge-rehberi" '
            'class="hybrid-region glass-box rounded-3xl p-6 sm:p-8 detail-prose" '
            'data-hybrid-region="' + html.escape(name, quote=True) + '" data-device="' + device + '">'
            '<h2>' + html.escape(name) + ' adresiniz için ' + label + ' servis rehberi</h2>'
            '<p>' + html.escape(region['address_note']) + '</p>'
            '<div class="hybrid-selected-context" data-hybrid-context role="status" aria-live="polite"></div>'
            '<h3>' + html.escape(name) + ' mahalleleri: doğru adresle ilerleyin</h3>'
            '<p>Mahalle adları sitedeki hizmet kaydından gelir. Mahallenizi seçip cihazınızın belirtisine '
            'uygun rehberle ilerleyebilirsiniz. Listede bulamadığınız adresi ayrıca iletebilirsiniz.</p>'
            + _neighborhoods(region, device)
            + '<h3>' + html.escape(name) + ' talebinde gözlenebilecek belirtiler</h3>'
            '<p>Sorunun hangi kullanımda ortaya çıktığını ve varsa ekrandaki uyarıyı not edin. '
            'Aşağıdaki rehberler, cihazın davranışını güvenle tarif etmenize yardımcı olur.</p>'
            + _notes(region['notes'][device], name)
            + '<h3>' + html.escape(name) + ' ile ortak kara sınırı bulunan hizmet bölgeleri</h3>'
            '<p>Bağlantılar açık sınır verisinde ortak çizgi tespit edilen ilçeleri gösterir; '
            'sürüş rotası, sıra veya varış süresi anlamına gelmez.</p>'
            '<ul class="hybrid-related-links">' + ''.join(neighbor_links) + '</ul>'
            '<p class="hybrid-data-source">Komşuluk verisi: © OpenStreetMap katkıda bulunanlar, '
            'ODbL 1.0. Türetilmiş ilçe komşuluk verisi aynı lisansla sunulur. '
            'Lisans: https://opendatacommons.org/licenses/odbl/1-0/</p>'
            + ('<p><a href="' + same + '">' + html.escape(name) + ' '
               + ('klima' if device == 'kombi' else 'kombi') + ' hizmetini inceleyin →</a></p>' if same in files else '')
            + '</section><!-- HYBRID-REGION:END -->')


def locality_block(locality: dict, data: dict, files: dict[str, bytes]) -> str:
    name = locality['name']; by_name = {r['name']:r for r in data['districts']}
    links = []
    for district in locality['districts']:
        region = by_name[district]
        for device in ['kombi','klima']:
            path = region['slug'] + '-' + device + '-servisi.html'
            if path in files: links.append('<li><a href="' + path + '#bolge-rehberi">'
                                          + html.escape(district) + ' ' + device + ' mahalle rehberi</a></li>')
    return ('<!-- HYBRID-REGION:START --><section id="bolge-rehberi" '
            'class="hybrid-region glass-box rounded-3xl p-6 sm:p-8 detail-prose" '
            'data-hybrid-locality="' + html.escape(name, quote=True) + '">'
            '<h2>' + html.escape(name) + ' adresini cihaz ihtiyacıyla eşleştirin</h2>'
            '<p>' + html.escape(locality['scope_note']) + '</p>'
            '<h3>' + html.escape(name) + ' için ilçe ve mahalle rehberleri</h3>'
            '<ul class="hybrid-related-links">' + ''.join(links) + '</ul>'
            '<h3>Belirtiye göre güvenli ilk adımlar</h3>' + _notes(locality['notes'], name)
            + '<p>Marka ve model bilinmiyorsa görülen belirtiyle devam edebilirsiniz. '
            'Bir hata kodunun anlamı tam modelin belgesiyle doğrulanmadıkça kesin teşhis olarak sunulmaz. '
            'Talebin uygunluğu ve yapılacak işlem iletişim sırasında netleştirilir.</p>'
            '</section><!-- HYBRID-REGION:END -->')


def _install(text: str, lead: str, block: str) -> str:
    text, count = re.subn(r'<p\b(?=[^>]*class="[^"]*\bat-lead\b)[^>]*>.*?</p>',
                         lambda m:'<p class="at-lead">'+html.escape(lead)+'</p>', text, count=1, flags=re.S)
    if count != 1: raise ValueError('Expected exactly one lead paragraph for region page')
    # Older SEO uploads may contain a generated hub. The base a1 export does not.
    text = re.sub(r'<!-- ST-HUB:v1 --><section\b[^>]*class="st-hub\b[^"\n]*"[^>]*>.*?</section>', '', text, flags=re.S)
    text = re.sub(r'<!-- HYBRID-REGION:START -->.*?<!-- HYBRID-REGION:END -->', '', text, flags=re.S)
    text, count = re.subn(r'(<div\b[^>]*class="[^"]*\bat-content\b[^"\n]*"[^>]*>)',
                         lambda m:m[0]+block, text, count=1)
    if count != 1: raise ValueError('Expected at-content insertion target')
    return text


def apply_regions(files: dict[str, bytes]) -> dict:
    data = load_regions(); changed=[]; leads=[]
    for region in data['districts']:
        for device in ['kombi','klima']:
            name=region['slug']+'-'+device+'-servisi.html'
            if name not in files: raise ValueError('Missing district route: '+name)
            lead=region['leads'][device];leads.append(lead)
            files[name]=_install(files[name].decode(),lead,district_block(region,device,files)).encode()
            changed.append(name)
    for locality in data['localities']:
        name=locality['slug']+'-servisi.html'
        if name not in files: raise ValueError('Missing locality route: '+name)
        leads.append(locality['lead'])
        files[name]=_install(files[name].decode(),locality['lead'],locality_block(locality,data,files)).encode()
        changed.append(name)
    if len(set(leads))!=55: raise ValueError('Region lead paragraphs must be distinct')
    files['assets/hybrid-regions.json']=(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n').encode()
    return {'district_pages':50,'locality_pages':5,'neighborhood_records':sum(len(r['neighborhoods']) for r in data['districts']),
            'unique_leads':len(set(leads)),'static_neighborhood_anchors':1198,'region_routes':changed,
            'data_source':'hybrid/data/regions.json','public_data':'assets/hybrid-regions.json',
            'indexing_guarantee':False,'statistical_local_fault_claims':False}
