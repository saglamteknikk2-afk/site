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
  // A single delegated listener works on older inline HTML and current components.
  // The modal can still open if home.js did not initialize.
  const modal=document.getElementById('serviceTicketModal');
  const setModal=show=>{
   if(typeof window.toggleServiceTicketModal==='function'){window.toggleServiceTicketModal(show);return;}
   if(!modal){const target=homeURL();target.hash='servis-talebi';location.href=target.href;return;}
   modal.classList.toggle('hidden',!show);
   document.body.classList.toggle('ah-dialog-open',show);
   if(show)modal.querySelector('#ticketName')?.focus({preventScroll:true});
  };
  document.querySelectorAll('[data-ticket-open],.usta-ticket').forEach(button=>{
   button.removeAttribute('onclick');
   button.addEventListener('click',event=>{event.preventDefault();setModal(true);});
  });
  modal?.querySelectorAll('.ah-modal-close').forEach(button=>{
   button.removeAttribute('onclick');
   button.addEventListener('click',()=>setModal(false));
  });
  // Keyboard close also works in the fallback case; the main handler owns it otherwise.
  document.addEventListener('keydown',event=>{
   if(event.key==='Escape'&&modal&&!modal.classList.contains('hidden')&&typeof window.toggleServiceTicketModal!=='function'){
    event.preventDefault();setModal(false);
   }
  });
  document.querySelectorAll('a[href]').forEach(link=>{
   const url=new URL(link.href,document.baseURI);
   if(url.origin===location.origin&&url.pathname===location.pathname&&!url.hash)link.setAttribute('aria-current','page');
  });
 });
})();
