'use strict';
// Loaded synchronously before application code. This file is preview-only.
(() => {
  window.ST_PREVIEW = true;
  const message = 'Bu test ön izlemesinde gönderim kapalıdır. Bilgileriniz kaydedilmedi ve ileti gönderilmedi.';
  window.ST_PREVIEW_MESSAGE = message;
  const denied = () => Promise.reject(Object.assign(new Error(message), {code:'PREVIEW_DISABLED'}));
  const safe = (input, options={}) => {
    try {
      const request = input instanceof Request ? input : null;
      const url = new URL(request ? request.url : String(input), location.href);
      const method = String(options.method || request?.method || 'GET').toUpperCase();
      return url.origin === location.origin && ['GET','HEAD'].includes(method) && !/\.php(?:\/|$)/i.test(url.pathname);
    } catch (_) { return false; }
  };
  const fetchOriginal = window.fetch.bind(window);
  window.fetch = (input, options) => safe(input, options) ? fetchOriginal(input, options) : denied();
  const openOriginal = XMLHttpRequest.prototype.open;
  const sendOriginal = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(method,url,...rest) { this.stPreviewAllowed = safe(url,{method}); return openOriginal.call(this,method,url,...rest); };
  XMLHttpRequest.prototype.send = function(body) { if (!this.stPreviewAllowed) throw new Error(message); return sendOriginal.call(this,body); };
  if (navigator.sendBeacon) navigator.sendBeacon = () => false;
  window.WebSocket = window.EventSource = class { constructor() { throw new Error(message); } };
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition = (_,fail) => { if (fail) queueMicrotask(()=>fail({code:1,message})); };
    navigator.geolocation.watchPosition = (_,fail) => { if (fail) queueMicrotask(()=>fail({code:1,message})); return 0; };
  }
  function inform(host) {
    let status = host?.querySelector('[data-preview-status]');
    if (!status) { status=document.createElement('p'); status.dataset.previewStatus=''; status.role='status'; status.setAttribute('aria-live','polite'); (host||document.body).append(status); }
    status.textContent=message;
  }
  const submitOriginal = HTMLFormElement.prototype.submit;
  HTMLFormElement.prototype.submit = function() {
    if (this.matches('[data-preview-local="true"]')) return submitOriginal.call(this);
    inform(this);
  };
  document.addEventListener('submit', event => {
    if (event.target.matches('[data-preview-local="true"]')) return;
    event.preventDefault(); event.stopImmediatePropagation(); inform(event.target);
  }, true);
  document.addEventListener('click', event => {
    const link=event.target.closest('a[href]');
    if (link && /^(?:https?:\/\/(?:wa\.me|api\.whatsapp\.com|t\.me)\/|tel:|sms:|mailto:)|\.php(?:[?#]|$)/i.test(link.getAttribute('href'))) {
      event.preventDefault(); event.stopImmediatePropagation(); inform(link.closest('section,main,footer,header')||document.body);
    }
  }, true);
  document.addEventListener('DOMContentLoaded', () => {
    const style=document.createElement('style');
    style.textContent='#st-preview-banner{position:relative;z-index:9999;background:#163c35;color:#fff;padding:10px 16px;text-align:center;font:600 12px/1.5 system-ui,sans-serif}[data-preview-status]{color:#7d3725;background:#fff1df;padding:12px;border-radius:8px;line-height:1.6}';
    document.head.append(style);
  });
})();
