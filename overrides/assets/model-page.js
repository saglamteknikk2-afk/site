'use strict';
(() => {
  const table=document.querySelector('.fault-table-section');if(!table)return;
  const file=location.pathname.split('/').pop();
  const models=(window.ST_VERIFIED_FAULTS?.models||[]).filter(m=>String(m.path).split('/').pop()===file);if(!models.length)return;
  const params=new URLSearchParams(location.search),selected=models.find(m=>m.id===params.get('model_id'))||models[0];
  const wanted=params.get('model')||'',exact=(selected.model_names||[]).find(n=>n===wanted);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let family=selected.label.split('—')[0].trim();
  if(!(selected.brand==='Baxi'&&family.includes('Assure 500')))family=family.replace(/\s+\d+(?:\s*\/\s*\d+){2,}(?:\s*kw)?/ig,'').trim();
  family=family.replace(' (ülke/ürün kodu teyidi gerekir)','').replace(', Vitotronic kontrol (nesil teyidi gerekir)',' (Vitotronic)');
  if(family.length>85)family=(selected.model_names?.[0]||family.slice(0,72))+' ailesi';
  const identity=family.toLowerCase().startsWith(selected.brand.toLowerCase())?family:selected.brand+' '+family;
  const heading=document.querySelector('.at-page-hero h1');if(heading)heading.textContent=identity+' · '+(selected.device==='klima'?'Klima':'Kombi')+' hata kodları';
  if(heading)document.title=heading.textContent+' | Sağlam Teknik';
  table.id='kodlar';table.hidden=false;
  const lead=document.querySelector('.at-page-hero .at-lead');if(lead)lead.textContent='Modelinizin üretici belgesinde doğrulanan gösterimler aşağıda. Kodun yazımını aynen koruyun; bu açıklamalar kesin parça teşhisi değildir.';
  const scope=document.querySelector('.fault-scope');
  const note=document.createElement('aside');note.className='mb-scope-note';note.setAttribute('aria-label','Model ve belge kapsamı');
  const scopeRequired=selected.requires_scope_confirmation||selected.requires_document_match||selected.matchable===false;
  note.innerHTML=`${exact?`<strong>Seçilen model: ${esc(exact)}</strong>`:''}<span>${scopeRequired?'Belgeyi cihazınıza uygulamadan önce ülke, ürün son eki ve varsa belge numarasının eşleştiğini kontrol edin.':'Cihaz etiketindeki tam model adı bu üretici belgesinin kapsamında olmalıdır.'}</span>${selected.market?`<p>Belgenin pazarı / bölgesi: <strong>${esc(selected.market)}</strong></p>`:''}${selected.scope_note?`<p>${esc(selected.scope_note)}</p>`:''}${selected.matchable===false?'<p>Kapasite veya marka benzerliğinden otomatik kod yorumu yapılmaz. Belge kapsamını ve gösterge örüntüsünü kontrol edin.</p>':''}`;
  const existingNote=document.getElementById('modelScopeNote');
  if(existingNote){if(exact){const selectedLine=document.createElement('strong');selectedLine.textContent='Seçilen model: '+exact;existingNote.prepend(selectedLine);}}else table.before(note);
  if(scope&&!scope.closest('details')){const details=document.createElement('details');details.className='mb-scope-notes';const summary=document.createElement('summary');summary.textContent='Kapsamdaki modeller ve üretici kaynağı';scope.replaceWith(details);details.append(summary,scope);}
  const nav=document.createElement('div');nav.className='mb-table-links';nav.innerHTML='<a href="model-ariza-kodlari.html">← Başka model ara</a><a href="index.html#aiUstaWizard">Kod yok, belirtimle devam et →</a>';if(!document.querySelector('.mb-table-links'))table.before(nav);
  // No invented model selector: exact model names and scope come from the dataset.
  // Existing row ids, filtering and per-code references remain untouched.
  if(location.hash==='#kodlar')requestAnimationFrame(()=>table.scrollIntoView({block:'start'}));
})();
