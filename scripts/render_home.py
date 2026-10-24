"""Render the editable home components, with no external dependencies."""
from pathlib import Path
import html
import json
import re

def render_assurances(data: dict) -> tuple[str, str]:
    cards, notes = [], []
    for item in data['items']:
        # Pending business claims never become published guarantees by implication.
        title = item['declared_title'] if item['status'] in {'verified', 'business-declared'} else item['title']
        cards.append('<a href="#servis-kosullari"><strong>' + html.escape(title) + '</strong><span>' + html.escape(item['detail']) + '</span></a>')
        notes.append('<details><summary>' + html.escape(title) + '</summary><p>' + html.escape(item['conditions']) + '</p></details>')
    return ''.join(cards), ''.join(notes)

def render_reviews(reviews: list[dict]) -> str:
    cards = []
    esc = lambda value: html.escape(str(value))
    for index, review in enumerate(reviews[:6]):
        author = review.get('author') or 'Müşteri'
        rating = max(1, min(5, int(review.get('rating', 5))))
        initial = author.replace('*', '').strip()[:1].upper() or 'S'
        meta = ' · '.join(str(review[k]) for k in ('date', 'service') if review.get(k))
        cards.append(f'<article class="pr-review" data-review-id="existing-{index}"><div class="pr-review-head"><span class="pr-review-avatar" aria-hidden="true">{esc(initial)}</span><div class="pr-review-identity"><h3>{esc(author)}</h3><p class="pr-review-meta">{esc(meta)}</p></div></div><span class="pr-review-rating" role="img" aria-label="5 üzerinden {rating} puan">' + '★' * rating + '☆' * (5-rating) + '</span><blockquote>' + esc(review.get('comment') or 'Bu değerlendirmeye yazılı not eklenmemiş.') + '</blockquote><p class="pr-review-origin">Mevcut sitedeki değerlendirme</p></article>')
    return ''.join(cards)

def render_home(files: dict[str, bytes], root: Path) -> None:
    template = root / 'components/home.html'
    if not template.exists():
        return
    original = files['index.html'].decode('utf-8')
    head = re.search(r'<head\b[^>]*>([\s\S]*?)</head>', original, re.I).group(1)
    head = re.sub(r'<link\b[^>]*rel=["\']stylesheet["\'][^>]*>', '', head, flags=re.I)
    head = re.sub(r'<meta\b[^>]*property=["\']og:image["\'][^>]*>', '', head, flags=re.I)
    head += '<meta property="og:image" content="https://saglamkombiklima.com.tr/assets/comfort-pets.webp">'
    styles = ['tailwind.css', 'fonts.css', 'icons.css', 'atelier.css', 'ai-usta.css', 'premium.css', 'ticket-modal.css', 'premium-reviews.css', 'business-maps.css']
    head += ''.join(f'<link rel="stylesheet" href="/assets/{name}?v=20261024-hybrid">' for name in styles)
    body = template.read_text()
    assurances, notes = render_assurances(json.loads((root / 'components/service-assurances.json').read_text()))
    body = body.replace('{{ASSURANCES}}', assurances).replace('{{PROMISE_NOTES}}', notes)
    sources = {'HEADER':'components/header.html','FOOTER':'components/footer.html','AI_PANEL':'components/ai-panel.html',
               'TICKET_MODAL':'components/ticket-modal.html','REVIEWS':'overrides/reviews-section.html','MAPS':'templates/business-maps-section.html'}
    for token, path in sources.items():
        full = root / path
        if not full.is_file():
            raise ValueError(f'Home component is missing: {path}')
        body = body.replace('{{'+token+'}}',full.read_text())
    reviews = json.loads((root / 'components/reviews.json').read_text())
    body = body.replace('<div id="reviewsContainer" class="pr-review-list" aria-label="Müşteri değerlendirmeleri"></div>', '<div id="reviewsContainer" class="pr-review-list" aria-label="Müşteri değerlendirmeleri">' + render_reviews(reviews) + '</div>')
    body = body.replace('Diğer değerlendirmeleri göster', 'Daha Fazla Yorum Göster')
    body = body.replace('Değerlendirmeleri okumak ve yorum formunu kullanmak için JavaScript’i etkinleştirin.', 'İlk altı değerlendirme yukarıda okunabilir. Diğer yorumlar ve yorum formu için JavaScript’i etkinleştirin.')
    body = body.replace('Mevcut sitedeki değerlendirmeler yükleniyor.', 'Mevcut siteden aktarılan değerlendirmeler.')
    seed_json = json.dumps(reviews, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    body += '<script id="st-review-seeds" type="application/json">' + seed_json + '</script>'
    if re.search(r'\{\{[A-Z_]+\}\}', body):
        raise ValueError('Unresolved home component')
    scripts = ['site.js','location.js','verified-faults.js','fault-lookup.js','fault-advisories.js','diagnostic-guide.js',
               'home.js','servis-verileri.js','organic-catalog.js','servis-search.js','ai-usta.js','atelier.js','premium-reviews.js','business-maps.js','premium.js']
    body += ''.join(f'<script src="/assets/{name}?v=20261024-hybrid" defer></script>' for name in scripts)
    files['index.html'] = ('<!doctype html><html lang="tr"><head>'+head+'</head><body class="at-site" data-page-kind="home">'+body+'</body></html>').encode('utf-8')
