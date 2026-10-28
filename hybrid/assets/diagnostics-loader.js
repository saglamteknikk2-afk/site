/* Load diagnostic datasets when needed; keep the initial, accessible wizard usable. */
(() => {
  'use strict';
  const script = document.currentScript;
  const root = document.getElementById('aiUstaWizard');
  let sources;
  try { sources = JSON.parse(script?.dataset.diagnosticSources || '[]'); } catch (_) { sources = []; }
  if (!root || !sources.length) return;
  const origin = new URL('../', script.src);
  let state = 'idle', pending = null, finish;
  window.STDiagnosticsReady = new Promise(resolve => { finish = resolve; });
  const notice = document.createElement('p');
  notice.className = 'usta-note st-diagnostics-status';
  notice.setAttribute('role', 'status');
  notice.setAttribute('aria-live', 'polite');
  notice.hidden = true;
  root.prepend(notice);
  const loaded = new Set();
  function loadScript(value) {
    const url = new URL(value, origin);
    if (url.origin !== location.origin || !url.pathname.startsWith(origin.pathname)) {
      return Promise.reject(new Error('Invalid local diagnostic resource'));
    }
    if (loaded.has(url.href)) return Promise.resolve();
    return new Promise((resolve, reject) => {
      const node = document.createElement('script');
      const timeout = setTimeout(() => {
        node.remove(); reject(new Error('Diagnostic resource timed out'));
      }, 10000);
      node.src = url.href;
      node.async = false;
      node.onload = () => { clearTimeout(timeout); loaded.add(url.href); resolve(); };
      node.onerror = () => { clearTimeout(timeout); node.remove(); reject(new Error('Diagnostic resource unavailable')); };
      document.head.append(node);
    });
  }
  function load() {
    if (pending) return pending;
    state = 'loading';
    root.setAttribute('aria-busy', 'true');
    notice.hidden = false;
    notice.textContent = 'Arıza rehberi hazırlanıyor…';
    pending = sources.reduce((chain, value) => chain.then(() => loadScript(value)), Promise.resolve())
      .then(() => {
        state = 'ready';
        root.removeAttribute('aria-busy');
        notice.hidden = true;
        const result = {ready: true}; finish(result);
        document.dispatchEvent(new CustomEvent('st:diagnostics-ready'));
        return result;
      })
      .catch(() => {
        state = 'failed';
        root.removeAttribute('aria-busy');
        notice.hidden = false;
        notice.textContent = 'Model listesi yüklenemedi. Belirti üzerinden devam edebilir veya servisi arayabilirsiniz.';
        const result = {ready: false}; finish(result);
        return result;
      });
    return pending;
  }
  window.STDiagnostics = Object.freeze({load, get state() { return state; }});
  const aiTrigger = target => target.closest?.(
    '[data-usta-open],[data-service-ai],[data-entry-diagnose],a[href$="#ai-usta"],a[href$="#aiUstaWizard"]'
  );
  // Defer only interactions whose meaning depends on a complete diagnostic
  // dataset. Navigation, ticket forms and ordinary reading remain immediate.
  document.addEventListener('click', event => {
    if (state === 'ready' || state === 'failed') return;
    const target = event.target.closest?.('button,a,input,select,textarea');
    if (!target || (!root.contains(target) && !aiTrigger(target))) return;
    if (target.matches('a[href^="tel:"],a[href^="https://wa.me/"]')) return;
    event.preventDefault(); event.stopImmediatePropagation();
    if (!root.contains(target)) root.scrollIntoView({block: 'start', behavior: 'auto'});
    const choice = target.getAttribute('data-choice'), id = target.id;
    load().then(() => {
      // Another queued action may have re-rendered the wizard while loading.
      const current = target.isConnected ? target : id ? document.getElementById(id)
        : choice ? [...root.querySelectorAll('[data-choice]')].find(node => node.getAttribute('data-choice') === choice) : null;
      if (!current) return;
      if (current.matches('input,select,textarea')) current.focus({preventScroll: true});
      else current.click();
    });
  }, true);
  root.addEventListener('focusin', () => { void load(); }, {once: true});
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { observer.disconnect(); void load(); }
    }, {rootMargin: '0px', threshold: 0});
    observer.observe(root);
  } else {
    // Older browsers get the full feature once the page is parsed.
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => { void load(); }, {once: true});
    else void load();
  }
})();
