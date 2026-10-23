/* Shared enhancements. Built navigation URLs are the single routing source. */
(() => {
 'use strict';
 document.addEventListener('DOMContentLoaded',()=>{
  // Header/footer URLs already contain the deployment base. Never prefix them again.
  const homeURL=()=>{
   const home=document.querySelector('.premium-header .premium-brand[href],.premium-footer .premium-footer-brand[href]');
   return new URL(home?.getAttribute('href')||'./',document.baseURI);
  };
  document.querySelectorAll('[data-usta-open],a[href$="#ai-usta"],a[href$="#aiUstaWizard"]').forEach(link=>link.addEventListener('click',event=>{
   if(new URL(link.href,document.baseURI).origin!==location.origin)return;
   if(!window.STUstaWizard||!document.getElementById('aiUstaWizard'))return;
   event.preventDefault();window.STUstaWizard.open(link.dataset.ustaDevice||undefined);
  }));
  document.querySelectorAll('[data-ticket-open]').forEach(button=>button.addEventListener('click',()=>{
   if(typeof window.toggleServiceTicketModal==='function')window.toggleServiceTicketModal(true);
   else {const target=homeURL();target.hash='servis-talebi';location.href=target.href;}
  }));
  document.querySelectorAll('a[href]').forEach(link=>{
   const url=new URL(link.href,document.baseURI);
   if(url.origin===location.origin&&url.pathname===location.pathname&&!url.hash)link.setAttribute('aria-current','page');
  });
 });
})();
