/* One device entry, three clear actions, and navigation to the actual section. */
(() => {
  'use strict';
  function init() {
    const entry=document.querySelector('.p-service-entry');
    const panel=document.getElementById('serviceEntryActions');
    const header=document.querySelector('.at-header');
    const offset=()=>Math.ceil(header?.getBoundingClientRect().height||76)+18;
    const updateOffset=()=>document.documentElement.style.setProperty('--st-nav-offset',offset()+'px');
    updateOffset();window.addEventListener('resize',updateOffset,{passive:true});
    if(entry&&panel){
      entry.querySelectorAll('[data-service-device]').forEach(button=>button.addEventListener('click',()=>{
        const device=button.dataset.serviceDevice;
        entry.querySelectorAll('[data-service-device]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
        document.getElementById('serviceEntryTitle').textContent=(device==='Petek'?'Petek & Tesisat':device)+' için nasıl yardımcı olalım?';
        panel.querySelector('[data-entry-diagnose]').dataset.ustaDevice=device;
        panel.querySelectorAll('[data-ticket-device]').forEach(item=>item.dataset.ticketDevice=device);
        panel.hidden=false;
      }));
      entry.querySelector('[data-service-ai]')?.addEventListener('click',()=>window.STUstaWizard?.open());
    }
    const align=target=>{
      document.getElementById('atMenuToggle')?.getAttribute('aria-expanded')==='true'&&document.getElementById('atMenuToggle').click();
      const top=Math.max(0,target.getBoundingClientRect().top+window.scrollY-12);
      const behavior=document.documentElement.style.scrollBehavior;
      document.documentElement.style.scrollBehavior='auto';
      window.scrollTo({top,left:0,behavior:'auto'});
      const rect=header?.getBoundingClientRect();
      if(rect&&['fixed','sticky'].includes(getComputedStyle(header).position)&&rect.top<=12&&rect.bottom>12&&rect.bottom>target.getBoundingClientRect().top){
        window.scrollBy({top:-rect.bottom,left:0,behavior:'auto'});
      }
      document.documentElement.style.scrollBehavior=behavior;
      target.tabIndex=-1;target.focus({preventScroll:true});
    };
    document.addEventListener('click',event=>{
      const link=event.target.closest?.('a[href]');if(!link)return;
      let url;try{url=new URL(link.href,location.href);}catch(_){return;}
      if(url.origin!==location.origin||url.pathname.replace(/index\.html$/,'')!==location.pathname.replace(/index\.html$/,''))return;
      if(['#ai-usta','#aiUstaWizard'].includes(url.hash)&&window.STUstaWizard){
        event.preventDefault();event.stopImmediatePropagation();
        document.getElementById('atMenuToggle')?.getAttribute('aria-expanded')==='true'&&document.getElementById('atMenuToggle').click();
        window.STUstaWizard.open(link.dataset.ustaDevice||undefined);return;
      }
      const target=url.hash==='#yorumlar'?document.querySelector('#yorumlar .pr-intro'):url.hash==='#yorumFormKutusu'?document.getElementById('yorumFormKutusu'):null;
      if(target){event.preventDefault();event.stopImmediatePropagation();align(target);}
    },true);
    const alignInitialHash=()=>{
      const target=['#ai-usta','#aiUstaWizard'].includes(location.hash)?document.getElementById('aiUstaWizard'):location.hash==='#yorumlar'?document.querySelector('#yorumlar .pr-intro'):location.hash==='#yorumFormKutusu'?document.getElementById('yorumFormKutusu'):null;
      if(target)requestAnimationFrame(()=>align(target));
    };
    if(document.readyState==='complete')alignInitialHash();else window.addEventListener('load',alignInitialHash,{once:true});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
