
'use strict';
let stCsrf='',stBootstrap=null,stTokenTime=0;
async function stFetchJson(path,options={},timeoutMs=20000){
 if(location.protocol==='file:')throw Error('Bu dosya önizlemesinde form gönderilemez. PC denemesini başlatma dosyasıyla açın.');
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),timeoutMs);
 try{
  const response=await fetch(path,{credentials:'same-origin',...options,signal:controller.signal});let value;
  try{value=await response.json()}catch(e){throw Error('Form sunucusuna bağlanılamadı. Bizi arayabilir veya WhatsApp’tan ulaşabilirsiniz.')}
  if(!value||typeof value!=='object'||!response.ok||value.ok===false){const error=Error(value?.error||'İşlem tamamlanamadı.');error.status=response.status;throw error;}
  return value;
 }finally{clearTimeout(timeout)}
}
async function stToken(){
 if(stTokenTime&&Date.now()-stTokenTime>1800000)stBootstrap=null;
 if(!stBootstrap)stBootstrap=stFetchJson('/api.php?action=bootstrap',{},6000).then(a=>{
  if(typeof a.csrf!=='string'||!/^\d+\.[a-f0-9]{64}$/.test(a.csrf))throw Error('Form bağlantısı doğrulanamadı. Sayfayı yenileyip tekrar deneyin.');
  stCsrf=a.csrf;stTokenTime=Date.now();return stCsrf;
 }).catch(e=>{stBootstrap=null;throw e});return stBootstrap;
}
function stId(){if(globalThis.crypto?.randomUUID)return crypto.randomUUID();const bytes=new Uint8Array(24);crypto.getRandomValues(bytes);return Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('')}
async function stApi(action,data,key){
 if(window.stAttachLocation&&(action==='review'||action==='ticket'))stAttachLocation(data);
 for(let attempt=0;attempt<2;attempt++){
  const token=await stToken();
  try{return await stFetchJson('/api.php?action='+encodeURIComponent(action),{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':token,...(key?{'Idempotency-Key':key}:{})},body:JSON.stringify(data)},action==='ai'?18000:20000);}
  catch(error){if(attempt===0&&error.status===403&&error.message==='Sayfayı yenileyip tekrar deneyin.'){stBootstrap=null;stTokenTime=0;continue;}throw error;}
 }
}
function stEscape(value){return String(value??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]))}
function stError(id,message){const e=document.getElementById(id);if(e){e.textContent=message;e.classList.toggle('hidden',!message)}}
function stAiContact(phone){const box=document.getElementById('aiResultBox');const link=box?.querySelector('a[href^="tel:"]');const button=box?.querySelector('button');if(link){link.href='tel:'+(phone||'05346225515');link.innerHTML='<i class="fa-solid fa-phone"></i> '+(phone?phone+' Acil Hattını Ara':'Ustayı Hemen Ara')}if(button)button.classList.toggle('hidden',!!phone)}
function stRequestKey(form,data){if(window.stAttachLocation)stAttachLocation(data);const encoded=JSON.stringify(data);if(form.dataset.requestBody!==encoded){form.dataset.requestBody=encoded;form.dataset.requestKey=stId()}return form.dataset.requestKey}
function requestRegion(button){const d=button.dataset.district;const device=button.dataset.device||(location.pathname.includes('-klima-')?'klima':'kombi');window.location.href='/servis-sec.html#'+new URLSearchParams({cihaz:device,ilce:d,mahalle:button.dataset.neighborhood||''}).toString()}
function stNormalize(value){return value.toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i')}
function filterRegions(){const q=stNormalize(document.getElementById('regionSearch')?.value||'').replace(/[^a-z0-9]/g,'');let count=0,semts=0;document.querySelectorAll('[data-region-group]').forEach(group=>{let shown=0;group.querySelectorAll('[data-neighborhood]').forEach(button=>{const match=stNormalize(button.dataset.district+' '+button.dataset.neighborhood).replace(/[^a-z0-9]/g,'').includes(q);button.hidden=!match;if(match)shown++});group.hidden=shown===0;group.open=!!q&&shown>0;count+=shown});document.querySelectorAll('[data-semt-card]').forEach(card=>{card.hidden=!stNormalize(card.dataset.semt+' '+card.dataset.aliases+' '+card.dataset.district).replace(/[^a-z0-9]/g,'').includes(q);if(!card.hidden)semts++});const status=document.getElementById('regionStatus');if(status)status.textContent=(semts?semts+' semt · ':'')+count+' mahalle gösteriliyor';const empty=document.getElementById('regionEmpty');if(empty)empty.hidden=!!(count||semts)}
function filterBrands(){const q=stNormalize(document.getElementById('brandSearch')?.value||'');document.querySelectorAll('[data-brand]').forEach(e=>e.hidden=!stNormalize(e.dataset.brand).includes(q))}
function requestSearchedRegion(){const q=document.getElementById('regionSearch')?.value.trim();if(q)window.location.href='/servis-sec.html#'+new URLSearchParams({arama:q}).toString()}
window.addEventListener('DOMContentLoaded',()=>{
 const nav=document.getElementById('stMainNav'),header=nav?.closest('header');
 if(header){
  const updateOffset=()=>document.documentElement.style.setProperty('--st-header-offset',Math.ceil(header.getBoundingClientRect().height)+12+'px');
  updateOffset();if(typeof ResizeObserver==='function')new ResizeObserver(updateOffset).observe(header);else window.addEventListener('resize',updateOffset);
  const updateCurrent=()=>nav.querySelectorAll('a').forEach(a=>{const url=new URL(a.href,location.href);if(url.pathname===location.pathname&&url.hash===location.hash)a.setAttribute('aria-current',url.hash?'location':'page');else a.removeAttribute('aria-current')});
  updateCurrent();window.addEventListener('hashchange',updateCurrent);
 }
 if(document.getElementById('regionSearch'))filterRegions();if(!sessionStorage.getItem('st_visit_try')){stApi('visit',{page:location.pathname,source:(()=>{try{const r=document.referrer;if(!r)return 'direct';const h=new URL(r).hostname.toLowerCase();if(h===location.hostname)return 'direct';if(/(^|\.)google\./.test(h))return 'google';if(/(^|\.)yandex\./.test(h))return 'yandex';return 'other'}catch(e){return 'other'}})()}).then(a=>{if(a.enabled)sessionStorage.setItem('st_visit_try','1')}).catch(()=>{})}
});
// Eski logo hedefleri de ortak başlığın manifestten gelen görselini kullanır.
window.addEventListener('DOMContentLoaded',()=>{
 const logoTargets=document.querySelectorAll('[data-site-logo]');
 if(logoTargets.length){
  const sharedLogo=document.querySelector('.at-brand img, .premium-footer-brand img');
  const canonicalLogo=sharedLogo?.getAttribute('src')||'/assets/brand/logo-ribbon.png';
  const logo=new Image();
  logo.onload=()=>logoTargets.forEach(img=>{img.removeAttribute('srcset');img.src=canonicalLogo});
  logo.src=canonicalLogo;
 }
 const badge=document.getElementById('svgFallbackBadge');
 if(badge){const stamp=new Image();stamp.alt='Sağlam Teknik müşteri değerlendirme rozeti';stamp.className='w-full h-full object-cover';stamp.onload=()=>{badge.style.display='none';badge.parentElement.prepend(stamp)};stamp.src='/oneri.png'}
});
