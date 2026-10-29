"""Keep semantic actions readable and poll the private tracking view in place."""
from pathlib import Path
import posixpath
import re

ROOT = Path(__file__).resolve().parent


def apply_interface_repairs(files):
    files['assets/interface-repairs.css'] = (ROOT/'assets/interface-repairs.css').read_bytes()
    files['assets/customer-tracking.js'] = (ROOT/'runtime/assets/customer-tracking.js').read_bytes()
    tracking = files['servis-takip.html'].decode('utf-8')
    if 'assets/customer-tracking.js' not in tracking:
        scripts = list(re.finditer(r'<script\b[^>]*>([\s\S]*?)</script>', tracking))
        target = [m for m in scripts if "action=service-status" in m[1] and '15000' in m[1]]
        if len(target) != 1:
            raise ValueError('Expected exactly one original customer tracking script.')
        match = target[0]
        tracking = tracking[:match.start()]+'<script src="assets/customer-tracking.js" defer></script>'+tracking[match.end():]
    tracking = tracking.replace('Canlı takip: 15 saniyede bir güncellenir.', 'Canlı takip: 3 saniyede bir güncellenir.')
    files['servis-takip.html'] = tracking.encode('utf-8')
    styled = []
    for name, data in list(files.items()):
        if not name.endswith('.html') or name.startswith(('google','yandex','inceleme/')):
            continue
        text = data.decode('utf-8')
        if '</head>' not in text or 'interface-repairs.css' in text:
            continue
        href = posixpath.relpath('assets/interface-repairs.css', posixpath.dirname(name) or '.')
        text = text.replace('</head>', '<link rel="stylesheet" href="'+href+'"></head>', 1)
        files[name] = text.encode('utf-8'); styled.append(name)
    return {'contrast_stylesheet':'assets/interface-repairs.css', 'styled_pages':len(styled),
            'tracking_script':'assets/customer-tracking.js', 'tracking_poll_ms':3000,
            'tracking_mode':'partial DOM refresh; no full page reload; one request at a time; paused while hidden'}
