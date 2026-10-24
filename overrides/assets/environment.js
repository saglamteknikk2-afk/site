'use strict';
/* Runs before application scripts. The host can make a build safer, never promote
 * a preview build into a live service. No account keys are read in the browser. */
(() => {
  const host = location.hostname.toLowerCase();
  const github = host === 'github.io' || host.endsWith('.github.io');
  const mode = document.documentElement.dataset.stMode || document.querySelector('meta[name="st-mode"]')?.content || document.body?.dataset.stMode;
  const preview = github || window.ST_PREVIEW === true || mode === 'preview' || !/^https?:$/.test(location.protocol);
  const officialProduction = !preview && ['saglamkombiklima.com.tr', 'www.saglamkombiklima.com.tr'].includes(host);
  let root;
  try { root = document.currentScript?.src ? new URL('../', document.currentScript.src) : new URL('./', location.href); }
  catch (_) { root = new URL('./', location.href); }
  const href = value => new URL(String(value).replace(/^\/+/, ''), root).href;
  window.STEnvironment = Object.freeze({preview, officialProduction, root: root.href, href});

  if (preview) {
    window.ST_PREVIEW = true;
    let robots = document.querySelector('meta[name="robots"]');
    if (!robots) { robots = document.createElement('meta'); robots.name = 'robots'; document.head.append(robots); }
    robots.content = 'noindex, nofollow';
  }

  if (preview && !window.ST_HOST_PREVIEW_GUARD) {
    window.ST_HOST_PREVIEW_GUARD = true;
    const message = 'Bu test ön izlemesinde gönderim kapalıdır. Bilgileriniz kaydedilmedi ve ileti gönderilmedi.';
    window.ST_PREVIEW_MESSAGE = message;
    const denied = () => Promise.reject(Object.assign(new Error(message), {code: 'PREVIEW_DISABLED'}));
    const safe = (input, options = {}) => {
      try {
        const request = input instanceof Request ? input : null;
        const target = new URL(request ? request.url : String(input), location.href);
        const method = String(options.method || request?.method || 'GET').toUpperCase();
        return target.origin === location.origin && ['GET', 'HEAD'].includes(method) && !/\.php(?:\/|$)/i.test(target.pathname);
      } catch (_) { return false; }
    };
    const originalFetch = window.fetch.bind(window);
    window.fetch = (input, options) => safe(input, options) ? originalFetch(input, options) : denied();
    const originalOpen = XMLHttpRequest.prototype.open, originalSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function (method, url, ...rest) { this.stHostPreviewAllowed = safe(url, {method}); return originalOpen.call(this, method, url, ...rest); };
    XMLHttpRequest.prototype.send = function (body) { if (!this.stHostPreviewAllowed) throw new Error(message); return originalSend.call(this, body); };
    if (navigator.sendBeacon) navigator.sendBeacon = () => false;
    window.WebSocket = window.EventSource = class { constructor() { throw new Error(message); } };
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition = (_, fail) => { if (fail) queueMicrotask(() => fail({code: 1, message})); };
      navigator.geolocation.watchPosition = (_, fail) => { if (fail) queueMicrotask(() => fail({code: 1, message})); return 0; };
    }
    const localForm = (form, submitter) => form.matches('[data-preview-local="true"]') && safe(submitter?.getAttribute('formaction') || form.action || location.href, {method: submitter?.getAttribute('formmethod') || form.method || 'GET'});
    const inform = hostElement => {
      const container = hostElement || document.body;
      let status = container.querySelector('[data-preview-status]');
      if (!status) { status = document.createElement('p'); status.dataset.previewStatus = ''; status.role = 'status'; status.setAttribute('aria-live', 'polite'); container.append(status); }
      status.textContent = message;
    };
    const originalSubmit = HTMLFormElement.prototype.submit;
    HTMLFormElement.prototype.submit = function () { if (localForm(this)) return originalSubmit.call(this); inform(this); };
    document.addEventListener('submit', event => {
      if (localForm(event.target, event.submitter)) return;
      event.preventDefault(); event.stopImmediatePropagation(); inform(event.target);
    }, true);
    document.addEventListener('click', event => {
      const link = event.target.closest('a[href]');
      if (link && /^(?:https?:\/\/(?:wa\.me|api\.whatsapp\.com|t\.me)\/|tel:|sms:|mailto:)|\.php(?:[?#]|$)/i.test(link.getAttribute('href'))) {
        event.preventDefault(); event.stopImmediatePropagation(); inform(link.closest('section,main,footer,header') || document.body);
      }
    }, true);
  }

  function finish() {
    if (officialProduction) document.querySelectorAll('#st-preview-banner,[data-preview-banner]').forEach(banner => { banner.hidden = true; });
    const conceal = scope => {
      const selector = '.st-honey,[data-honeypot],input[name="website"],#ticketWebsite,#yorumWebsite,#contactWebsite';
      const targets = [...scope.querySelectorAll(selector)];
      if (scope.matches?.(selector)) targets.unshift(scope);
      targets.forEach(target => {
        const container = target.closest('.st-honey,[data-honeypot]') || (target.matches('input') ? target.closest('label') || target : target);
        container.setAttribute('aria-hidden', 'true');
        container.style.setProperty('display', 'none', 'important');
        container.style.setProperty('visibility', 'hidden', 'important');
        if (target.matches('input')) target.tabIndex = -1;
        container.querySelectorAll('input,select,textarea,button,a').forEach(field => { field.tabIndex = -1; field.setAttribute('aria-hidden', 'true'); });
      });
    };
    conceal(document);
    new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(node => { if (node.nodeType === 1) conceal(node); }))).observe(document.body, {childList: true, subtree: true});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', finish, {once: true});
  else finish();
})();
