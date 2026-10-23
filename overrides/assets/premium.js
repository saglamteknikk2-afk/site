/* Shared small enhancements; no third-party analytics or autonomous network writes. */
(() => {
 'use strict';
 const prefix = document.body.dataset.stMode === 'preview' && location.pathname.startsWith('/site/') ? '/site' : '';
 const local = path => prefix + path;
 document.addEventListener('DOMContentLoaded', () => {
  const modelForm = document.getElementById('homeModelSearch');
  if (modelForm) modelForm.addEventListener('submit', event => {
   event.preventDefault();
   const query = document.getElementById('homeModelQuery')?.value.trim() || '';
   location.href = local('/model-ariza-kodlari.html') + (query ? '?' + new URLSearchParams({q:query}) : '');
  });
  document.querySelectorAll('[data-ticket-open]').forEach(button => button.addEventListener('click', () => {
   if (typeof window.toggleServiceTicketModal === 'function') window.toggleServiceTicketModal(true);
   else location.href = local('/') + '#servis-talebi';
  }));
  document.querySelectorAll('a[href]').forEach(link => {
   const url = new URL(link.href, location.href);
   if (url.origin === location.origin && url.pathname === location.pathname && !url.hash) link.setAttribute('aria-current','page');
  });
 });
})();
