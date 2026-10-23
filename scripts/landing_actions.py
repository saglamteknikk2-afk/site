"""Keep ad intent on existing service URLs and expose an immediate contact action."""
import html
import json
import re
from urllib.parse import quote

ORIGIN = 'https://saglamkombiklima.com.tr'
SERVICE_ROUTES = {
    'kombi-servisi.html', 'klima-servisi.html', 'petek-temizligi.html',
    'kombi-bakimi.html', 'kombi-tamiri.html', 'klima-bakimi.html', 'klima-tamiri.html',
    'klima-montaji.html', 'klima-sokumu.html', 'klima-gaz-kontrolu.html',
    'klima-filtre-temizligi.html',
}

def enhance_landings(files: dict[str, bytes]) -> list[dict]:
    routes = []
    for name in sorted(files):
        if not (name in SERVICE_ROUTES or name.endswith('-servisi.html')):
            continue
        text = files[name].decode('utf-8')
        heading = re.search(r'<h1\b[^>]*>([\s\S]*?)</h1>', text, re.I)
        if not heading:
            continue
        title = html.unescape(re.sub(r'<[^>]+>', ' ', heading[1]))
        title = re.sub(r'\s+', ' ', title).strip()[:180]
        url = ORIGIN + '/' + name
        routes.append({'title': title, 'url': url, 'path': '/' + name})
        if 'data-service-contact' in text:
            continue
        message = 'Merhaba Sağlam Teknik, ' + title + ' için servis uygunluğunu görüşmek istiyorum. ' + url
        actions = ('<div class="p-intent-actions" data-service-contact>'
                   '<a class="p-button" href="tel:05346225515" data-contact-intent="call">Hemen ara <span aria-hidden="true">↗</span></a>'
                   '<a class="p-button p-button-light" href="https://wa.me/905346225515?text=' + quote(message, safe='') + '" target="_blank" rel="noopener noreferrer" data-contact-intent="whatsapp">WhatsApp <span aria-hidden="true">↗</span></a></div>')
        text, added = re.subn(r'(<div\b[^>]*class="at-quickfacts"[^>]*>[\s\S]*?</div>)', lambda m: m[1] + actions, text, count=1)
        if added:
            files[name] = text.encode('utf-8')
    files['assets/ad-landing-map.json'] = (json.dumps({'schema_version': 1, 'policy': 'Use the matching existing canonical service URL as the ad final URL; no automatic keyword redirects or campaign changes.', 'routes': routes}, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    return routes
