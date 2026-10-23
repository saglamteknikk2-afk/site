/* Shared enhancements. One AI Usta entry; no autonomous network writes. */
(() => {
 'use strict';
 const prefix=document.body.dataset.stMode==='preview'&&location.pathname.startsWith('/site/')?'/site':'';
 const local=path=>prefix+path;
 document.addEventListener('DOMContentLoaded',()=>{
  // Legacy header actions join the same assistant. The source library remains available in the footer.
  document.querySelectorAll('.premium-header a[href]').forEach(link=>{
   if(/^(?:Arızanı bul|AI Usta|Marka\s*\/\s*model)$/i.test(link.textContent.replace(/✳/g,'').trim())){
    link.href=local('/')+'#ai-usta';link.dataset.ustaOpen='';
   }
  });
  document.querySelectorAll('[data-usta-open],a[href$="#ai-usta"],a[href$="#aiUstaWizard"]').forEach(link=>link.addEventListener('click',event=>{
   if(!window.STUstaWizard||!document.getElementById('aiUstaWizard'))return;
   event.preventDefault();window.STUstaWizard.open(link.dataset.ustaDevice||undefined);
  }));
  document.querySelectorAll('[data-ticket-open]').forEach(button=>button.addEventListener('click',()=>{
   if(typeof window.toggleServiceTicketModal==='function')window.toggleServiceTicketModal(true);
   else location.href=local('/')+'#servis-talebi';
  }));
  document.querySelectorAll('a[href]').forEach(link=>{
   const url=new URL(link.href,location.href);
   if(url.origin===location.origin&&url.pathname===location.pathname&&!url.hash)link.setAttribute('aria-current','page');
  });
 });
})();
