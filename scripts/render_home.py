"""Render the editable home components, with no external dependencies."""
from pathlib import Path
import re

def render_home(files: dict[str, bytes], root: Path) -> None:
    template = root / 'components/home.html'
    if not template.exists():
        return
    original = files['index.html'].decode('utf-8')
    head = re.search(r'<head\b[^>]*>([\s\S]*?)</head>', original, re.I).group(1)
    head = re.sub(r'<link\b[^>]*rel=["\']stylesheet["\'][^>]*>', '', head, flags=re.I)
    head = re.sub(r'<meta\b[^>]*property=["\']og:image["\'][^>]*>', '', head, flags=re.I)
    head += '<meta property="og:image" content="https://saglamkombiklima.com.tr/assets/comfort-pets.webp">'
    styles = ['tailwind.css', 'fonts.css', 'icons.css', 'atelier.css', 'ai-usta.css', 'premium.css', 'premium-reviews.css', 'business-maps.css']
    head += ''.join(f'<link rel="stylesheet" href="/assets/{name}?v=20261023-ribbon-flow">' for name in styles)
    body = template.read_text()
    sources = {'HEADER':'components/header.html','FOOTER':'components/footer.html','AI_PANEL':'components/ai-panel.html',
               'TICKET_MODAL':'components/ticket-modal.html','REVIEWS':'overrides/reviews-section.html','MAPS':'templates/business-maps-section.html'}
    for token, path in sources.items():
        full = root / path
        if not full.is_file():
            raise ValueError(f'Home component is missing: {path}')
        body = body.replace('{{'+token+'}}',full.read_text())
    if re.search(r'\{\{[A-Z_]+\}\}', body):
        raise ValueError('Unresolved home component')
    scripts = ['site.js','location.js','verified-faults.js','fault-lookup.js','fault-advisories.js','diagnostic-guide.js',
               'home.js','servis-verileri.js','organic-catalog.js','servis-search.js','ai-usta.js','atelier.js','premium-reviews.js','business-maps.js','premium.js']
    body += ''.join(f'<script src="/assets/{name}?v=20261023-ribbon-flow" defer></script>' for name in scripts)
    files['index.html'] = ('<!doctype html><html lang="tr"><head>'+head+'</head><body class="at-site" data-page-kind="home">'+body+'</body></html>').encode('utf-8')
