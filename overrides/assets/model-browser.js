'use strict';
(() => {
  const root=document.getElementById('modelBrowser');if(!root)return;
  const el=id=>document.getElementById(id),norm=s=>String(s||'').toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i').replace(/[^a-z0-9]+/g,' ').trim();
  const data=window.ST_VERIFIED_FAULTS||{models:[],coverage:[]},organic=window.ST_ORGANIC_CATALOG||{models:[]},registry=window.STBrands;
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const state={device:'',brand:'',query:'',limit:30};
  const displayLabel=value=>String(value).replace(' (ülke/ürün kodu teyidi gerekir)','').replace(', Vitotronic kontrol (nesil teyidi gerekir)',' (Vitotronic)');
  const modelTitle=(m,n)=>displayLabel(norm(n).startsWith(norm(m.brand))?n:m.brand+' '+n);
  const records=[];
  for(const m of data.models){
    const names=m.model_names?.length?m.model_names:[m.label];
    for(const n of names){
      // Generic capacities are a document scope, never an invented commercial model.
      const generic=/^\d+(?:[.,]\d+)?\s*(?:kw|btu|btu\/h)?$/i.test(n.trim())||m.matchable===false&&m.requires_document_match;
      records.push({name:generic?displayLabel(m.brand+' · '+m.label):modelTitle(m,n),exact:n,device:m.device,brand:m.brand,verified:m.manual?.source_available!==false,sourceUnavailable:m.manual?.source_available===false,documentOnly:generic,id:m.id,path:m.path,market:m.market||'',scope:m.scope_note||'',count:m.codes?.length||0,terms:[m.brand,n,m.label.replace(/\d+/g,''),...(m.aliases||[]).filter(a=>! /\d/.test(a))].join(' ')});
    }
  }
  const seen=new Set(records.map(r=>[r.device,norm(r.brand),norm(r.exact)].join('|')));
  for(const m of organic.models){const key=[m.device,norm(m.brand),norm(m.name)].join('|');if(seen.has(key))continue;seen.add(key);records.push({name:modelTitle(m,m.name),exact:m.name,device:m.device,brand:m.brand,verified:false,terms:[m.brand,m.name,...(m.terms||[])].join(' ')});}
  const unique=records.filter((r,i,a)=>a.findIndex(x=>x.device===r.device&&x.name===r.name&&x.id===r.id)===i);
  function brands(){const value=registry?.find(state.brand,state.device)?.name||state.brand;const list=(registry?registry.names(state.device):[...new Set(data.coverage.filter(c=>!state.device||c.device===state.device).map(c=>c.brand).concat(unique.filter(r=>!state.device||r.device===state.device).map(r=>r.brand)))]).sort((a,b)=>a.localeCompare(b,'tr'));el('modelBrand').replaceChildren(new Option('Tüm markalar',''),...list.map(b=>new Option(b,b)));state.brand=list.includes(value)?value:'';el('modelBrand').value=state.brand;}
  function route(r){if(!r.verified)return '/index.html?'+new URLSearchParams({cihaz:r.device,marka:r.brand,model:r.exact,usta:'1'})+'#ai-usta';const url=new URL(r.path,document.baseURI);url.searchParams.set('model',r.exact);url.searchParams.set('model_id',r.id);url.hash='kodlar';return url.pathname+url.search+url.hash;}
  function render(){
    const q=norm(state.query),parts=q.split(' ').filter(Boolean);const list=unique.filter(r=>(!state.device||r.device===state.device)&&(!state.brand||norm(r.brand)===norm(state.brand))&&parts.every(p=>norm(r.terms).includes(p))).sort((a,b)=>Number(b.verified)-Number(a.verified)||a.name.localeCompare(b.name,'tr'));
    const shown=list.slice(0,state.limit);el('modelResults').innerHTML=shown.map(r=>`<a class="mb-card${r.verified?'':' mb-card--pending'}" href="${esc(route(r))}" data-model-card data-verified="${r.verified}"><span class="mb-card-meta">${r.device==='klima'?'Klima':'Kombi'} · ${r.verified?r.documentOnly?'Belge / kontrol serisi':'Üretici belgesi var':'Model ailesi · kod tablosu bekliyor'}</span><h2>${esc(r.name)}</h2><p>${r.verified?esc(r.market?('Belge pazarı: '+r.market+'. '):'')+(r.documentOnly?'Kapasite tek başına model eşleştirmez. Belge kapsamını kontrol edin.':esc('Üretici kaynağına göre hazırlanmıştır. Cihaz etiketindeki tam adı ve varsa ürün son ekini kontrol edin.')):r.sourceUnavailable?'Kayıtlı üretici belgesine şu anda erişilemiyor. Kod anlamı güncel kaynakla yeniden doğrulanmalı; belirtinizle devam edebilirsiniz.':'Bu adın modele özel kodları henüz doğrulanmadı. Belirtinizle devam edebilirsiniz.'}</p><span class="mb-card-link">${r.verified?'Kodları aç':'Belirtimle devam et'} <span aria-hidden="true">↗</span></span></a>`).join('');
    el('modelStatus').textContent=list.length+' model / belge kaydı'+(list.length>shown.length?' · ilk '+shown.length+' gösteriliyor':'')+'.';
    el('modelMore').hidden=list.length<=state.limit;
    el('modelEmpty').hidden=list.length!==0;
    const coverage=registry?registry.list(state.device).filter(c=>(!state.brand||norm(c.name)===norm(state.brand))&&(!q||[c.name,...(c.aliases||[])].some(n=>norm(n).includes(q)))):data.coverage.filter(c=>(!state.device||c.device===state.device)&&(!state.brand||norm(c.brand)===norm(state.brand))&&(!q||norm(c.brand).includes(q)));
    el('brandCoverage').innerHTML=coverage.map(c=>{const n=(c.verified_model_ids||[]).length,name=c.name||c.brand,device=state.device||(c.device||c.devices?.join(' / '));return `<li><strong>${esc(name)}</strong><span>${esc(device==='klima'?'Klima':device==='kombi'?'Kombi':'Kombi / Klima')} · ${n?n+' belgelenmiş model ailesi':'Modele özel doğrulanmış kod tablosu henüz yok'}${c.kind==='legacy_supplier'?' · Tarihî tedarikçi kaydı':''}</span></li>`;}).join('');
    if(!list.length){const brand=registry?.find(state.brand||state.query,state.device),name=brand?.name||state.brand;el('modelEmpty').querySelector('p').textContent=name?name+' için bu filtrede doğrulanmış model kodu tablosu yok. '+(brand?.notes||'Marka listesinde bulunmak tüm modellerin kodlarının doğrulandığı anlamına gelmez. Belirtinizle devam edebilirsiniz.'):'Bu aramayla eşleşen bir kayıt bulamadık. Başka modele ait kodları cihazınıza uygulamayın.';el('modelEmpty').querySelector('a').href='/index.html?'+new URLSearchParams({...(state.device?{cihaz:state.device}:{}),...(name?{marka:name}:{}),usta:'1'})+'#ai-usta';}
  }
  el('modelSearch').addEventListener('input',e=>{state.query=e.target.value;state.limit=30;render();});el('modelBrand').addEventListener('change',e=>{state.brand=e.target.value;state.limit=30;render();});
  root.querySelectorAll('[data-device-filter]').forEach(b=>b.addEventListener('click',()=>{state.device=b.dataset.deviceFilter;state.limit=30;root.querySelectorAll('[data-device-filter]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));brands();render();}));
  el('modelMore').addEventListener('click',()=>{state.limit+=30;render();});
  el('modelReset').addEventListener('click',()=>{state.device='';state.brand='';state.query='';state.limit=30;el('modelSearch').value='';root.querySelectorAll('[data-device-filter]').forEach(x=>x.setAttribute('aria-pressed',String(!x.dataset.deviceFilter)));brands();render();el('modelSearch').focus();});
  const params=new URLSearchParams(location.hash.slice(1)),query=new URLSearchParams(location.search);const device=query.get('device')||query.get('cihaz')||params.get('device')||params.get('cihaz');state.device=['kombi','klima'].includes(device)?device:'';state.brand=query.get('brand')||query.get('marka')||params.get('brand')||params.get('marka')||'';state.query=query.get('q')||query.get('arama')||params.get('q')||params.get('arama')||'';el('modelSearch').value=state.query;root.querySelectorAll('[data-device-filter]').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.deviceFilter===state.device)));brands();render();
  window.STModelBrowser={count:unique.length,brand_count:registry?.list().length||0,refresh:render};
})();
