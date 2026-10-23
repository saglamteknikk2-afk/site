(function () {
  'use strict';
  function preview() {
    return window.ST_PREVIEW === true || document.body?.dataset.stMode === 'preview' ||
      document.documentElement.dataset.stMode === 'preview' || !/^https?:$/.test(location.protocol);
  }
  function mapURL(value, provider, embed) {
    if (typeof value !== 'string' || !value || value.length > 4096 || /[\u0000-\u0020\u007f<>"\\]/.test(value)) return '';
    try {
      const u = new URL(value);
      if (u.protocol !== 'https:' || u.username || u.password || u.port && u.port !== '443') return '';
      const h = u.hostname.toLowerCase(), p = u.pathname;
      if (provider === 'google') {
        if (embed) return ['google.com', 'www.google.com', 'google.com.tr', 'www.google.com.tr'].includes(h) && p === '/maps/embed' && u.search ? u.href : '';
        if (['maps.app.goo.gl', 'g.page'].includes(h)) return /^\/[A-Za-z0-9_/-]+$/.test(p) ? u.href : '';
        if (h === 'goo.gl') return /^\/maps\/[A-Za-z0-9_-]+\/?$/.test(p) ? u.href : '';
        if (['google.com', 'www.google.com', 'google.com.tr', 'www.google.com.tr'].includes(h)) return /^\/maps(?:\/|$)/.test(p) ? u.href : '';
        if (['maps.google.com', 'maps.google.com.tr'].includes(h)) return p === '/' || /^\/maps(?:\/|$)/.test(p) ? u.href : '';
      }
      if (provider === 'yandex' && ['yandex.com', 'yandex.com.tr', 'yandex.ru', 'yandex.eu', 'www.yandex.com', 'www.yandex.com.tr', 'www.yandex.ru'].includes(h)) {
        return (embed ? /^\/map-widget\/v1\/?$/.test(p) && u.search : /^\/maps(?:\/|$)/.test(p)) ? u.href : '';
      }
    } catch (_) {}
    return '';
  }
  function reset(card, message) {
    const link = card.querySelector('[data-map-link]'), status = card.querySelector('[data-map-status]');
    card.classList.remove('is-configured');
    if (link) { link.removeAttribute('href'); link.setAttribute('aria-disabled', 'true'); link.tabIndex = -1; link.textContent = 'Konum bağlantısı yakında'; }
    if (status) status.textContent = message || 'Konum bağlantısı yakında';
    const button = card.querySelector('[data-map-embed]'); if (button) button.hidden = true;
  }
  function configure(card, data) {
    const provider = card.dataset.mapProvider, url = mapURL(data?.url, provider, false);
    if (!url) return;
    const link = card.querySelector('[data-map-link]'), status = card.querySelector('[data-map-status]');
    card.classList.add('is-configured');
    if (link) { link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.removeAttribute('aria-disabled'); link.removeAttribute('tabindex'); link.textContent = provider === 'google' ? 'Google Haritalar’da aç ↗' : 'Yandex Haritalar’da aç ↗'; }
    if (status) status.textContent = 'İşletmenin paylaşılan konum bağlantısı';
    const embed = mapURL(data?.embed_url, provider, true), button = card.querySelector('[data-map-embed]'), canvas = card.querySelector('[data-map-canvas]');
    if (embed && button && canvas) {
      button.hidden = false;
      button.addEventListener('click', function () {
        const frame = document.createElement('iframe');
        frame.src = embed; frame.title = (provider === 'google' ? 'Google' : 'Yandex') + ' işletme haritası';
        frame.loading = 'lazy'; frame.referrerPolicy = 'no-referrer'; frame.allowFullscreen = true;
        frame.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-popups');
        canvas.replaceChildren(frame); canvas.hidden = false; button.hidden = true;
      }, { once: true });
    }
  }
  async function start() {
    const sections = [...document.querySelectorAll('[data-business-maps]')];
    if (!sections.length) return;
    const cards = sections.flatMap(section => [...section.querySelectorAll('.st-map-card[data-map-provider]')]);
    cards.forEach(card => reset(card));
    if (preview()) return;
    let endpoint;
    try {
      endpoint = new URL(sections[0].dataset.api || '/api.php?action=business-maps', location.href);
      if (endpoint.origin !== location.origin || !/^\/(?:server\/)?api\.php$/.test(endpoint.pathname) || endpoint.searchParams.get('action') !== 'business-maps') return;
    } catch (_) { return; }
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 3500);
    try {
      const response = await fetch(endpoint.href, { credentials: 'same-origin', headers: { Accept: 'application/json' }, signal: controller.signal });
      if (!response.ok) throw new Error('unavailable');
      const data = await response.json();
      if (data.ok !== true || !data.maps || typeof data.maps !== 'object') throw new Error('unavailable');
      cards.forEach(card => configure(card, data.maps[card.dataset.mapProvider]));
    } catch (_) { cards.forEach(card => reset(card, 'Konum bağlantısı şu anda alınamıyor')); }
    finally { clearTimeout(timer); }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
