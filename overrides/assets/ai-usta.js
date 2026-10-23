'use strict';
(() => {
  const root = document.getElementById('aiUstaWizard');
  if (!root) return;
  const el = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const state = {step:0,device:'',brand:'',model:'',model_id:'',scope_confirmed:false,symptom:'',answer:'',code:'',district:'',neighborhood:'',detail:'',last_detail_step:1,skip_model:false};
  const symptoms = {
    Kombi:[['heat','Petekler ısınmıyor'],['water','Sıcak su yok / değişiyor'],['pressure','Basınç değişiyor'],['leak','Su akıtıyor'],['noise','Sesli çalışıyor'],['off','Hiç çalışmıyor'],['error','Hata kodu var']],
    Klima:[['cool','Soğutmuyor'],['heat','Isıtmıyor'],['leak','Su damlatıyor'],['noise','Sesli çalışıyor'],['ice','Buzlanıyor'],['odor','Koku yapıyor'],['off','Hiç çalışmıyor'],['error','Hata kodu var']],
    Petek:[['heat','Petekler soğuk'],['partial','Kısmen ısınıyor'],['leak','Su sızdırıyor'],['noise','Ses geliyor'],['service','Bakım istiyorum']]
  };
  const catalog = () => window.ST_SERVICE_DATA || {};
  const brands = () => window.STBrands?.names(state.device.toLowerCase()) || catalog().devices?.[state.device.toLowerCase()]?.brands || [];
  const models = () => state.device === 'Petek' ? [] : (window.STFaults?.models(state.device.toLowerCase(), state.brand) || (window.ST_VERIFIED_FAULTS?.models || []).filter(m => m.device === state.device.toLowerCase() && (!state.brand || m.brand === state.brand)));
  const selectedModel = () => models().find(m => m.id === state.model_id);
  const symptomText = () => state.symptom === 'other' ? 'Kendi anlatımım' : symptoms[state.device]?.find(s => s[0] === state.symptom)?.[1] || '';
  const hasCode = () => state.symptom === 'error' || !!state.code;
  function clearResult() { el('aiResultBox')?.classList.add('hidden'); }
  function resetModel() { Object.assign(state, {model:'',model_id:'',scope_confirmed:false,code:''}); }
  function compose() {
    el('deviceSelect').value = state.device || 'Kombi';
    el('issueInput').value = [state.brand && 'Marka: '+state.brand, state.model && 'Model: '+state.model, symptomText(), state.code && 'Ekrandaki hata kodu: '+state.code, state.answer, state.district && 'İlçe: '+state.district, state.neighborhood && 'Mahalle / semt: '+state.neighborhood, state.detail && 'Açıklamam: '+state.detail].filter(Boolean).join('. ').slice(0,1200);
    if (el('ticketDevice') && state.device) el('ticketDevice').value = state.device;
    if (el('ticketDistrict') && state.district) el('ticketDistrict').value = state.district;
    root.dispatchEvent(new CustomEvent('usta:change', {bubbles:true, detail:{...state,issue:el('issueInput').value}}));
  }
  function deviceIcon(kind) {
    const paths = kind === 'Kombi' ? '<rect x="10" y="5" width="22" height="29" rx="3"/><rect x="15" y="12" width="12" height="7" rx="1"/><path d="M15 25h12m-11 9v5m10-5v5"/>' : kind === 'Klima' ? '<rect x="4" y="8" width="34" height="17" rx="3"/><path d="M8 19h26M12 30v7m9-7v10m9-10v7M29 13h4"/>' : '<rect x="5" y="10" width="32" height="23" rx="2"/><path d="M11 13v17m7-17v17m7-17v17m7-17v17M9 33v5m24-5v5"/>';
    return '<span class="usta-choice-icon" aria-hidden="true"><svg viewBox="0 0 42 42" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'+paths+'</svg></span>';
  }
  function choice(value, label, subtitle='') {
    return `<button type="button" class="usta-choice" data-choice="${esc(value)}">${label}${subtitle?`<small>${esc(subtitle)}</small>`:''}</button>`;
  }
  function scopeFields() {
    const model = selectedModel();
    if (!model) return '';
    const required = model.matchable !== false && (model.requires_scope_confirmation || model.requires_document_match);
    return `<div id="ustaModelScope">${model.market?`<p class="usta-note"><strong>Belgenin pazarı / bölgesi:</strong> ${esc(model.market)}</p>`:''}${model.scope_note?`<p class="usta-note">${esc(model.scope_note)}</p>`:''}${model.matchable===false?'<p class="usta-note">Bu belge kapasiteye veya benzer ada bakılarak otomatik eşleştirilemez. Cihazın belge ve ürün numarası ayrıca kontrol edilmelidir.</p>':''}${model.requires_document_match?`<p class="usta-note"><strong>Eşleşmesi gereken belge:</strong> ${esc(model.manual?.title||model.label)}</p>`:''}${required?`<label class="usta-scope-check"><input id="ustaScopeConfirmed" type="checkbox"${state.scope_confirmed?' checked':''}> Etiketteki ülke/ürün kodu ve gerekiyorsa belge numarası bu üretici belgesiyle eşleşiyor.</label>`:''}<details class="usta-free"><summary>Model kapsamı ve üretici kaynağı</summary><p class="usta-note">${esc((model.model_names||[]).join(' · '))}</p>${model.manual?.url?`<a href="${esc(model.manual.url)}" target="_blank" rel="noopener noreferrer">Üretici belgesini aç ↗</a>`:''}</details></div>`;
  }
  function modelFields() {
    if (!state.brand) return '<p class="usta-note">Marka ve tam model bilinmeden kodun anlamını tahmin etmiyoruz. Ekrandaki kodu not edebilir veya doğrudan güvenli yönlendirmeye geçebilirsiniz.</p>';
    const list = models();
    let options = '';
    for (const model of list) {
      const names = model.matchable===false && model.requires_document_match ? [model.label] : model.model_names?.length ? model.model_names : [model.label];
      for (const name of names) {
        const label = /^\d+\s*(?:kw|btu)?$/i.test(name) ? model.label : name;
        options += `<option value="${esc(model.id+'|'+name)}"${state.model_id===model.id&&state.model===name?' selected':''}>${esc(label.toLowerCase().startsWith(model.brand.toLowerCase())?label:model.brand+' '+label)}</option>`;
      }
    }
    return `<p class="usta-note"><strong>${esc(state.brand)}</strong> · Etiketteki tam adı biliyorsanız seçin. Bilmiyorsanız atlayabilirsiniz.</p>${list.length?`<label class="usta-field-label">Tam model / üretici belgesi<select id="ustaVerifiedModel" class="usta-field"><option value="">Modeli seçin / bilmiyorum</option>${options}</select></label>`:'<p class="usta-note">Bu marka için modele özel doğrulanmış bir kod tablosu henüz yok. Başka markanın kodlarını bu cihaza uygulamıyoruz.</p>'}<label class="usta-field-label">Model listede yoksa <span>(isteğe bağlı)</span><input id="ustaModel" class="usta-field" maxlength="120" value="${esc(state.model_id?'':state.model)}" placeholder="Etiketteki tam model adını yazabilirsiniz"></label>${scopeFields()}`;
  }
  function codeFields() {
    const codes = (selectedModel()?.codes || []).filter(code => code.matchable!==false && !code.source_conflict);
    return `${hasCode()&&codes.length?`<p class="usta-note">Bu modelin belgesindeki kodlardan birini seçin:</p><div class="usta-code-grid">${codes.slice(0,8).map(c=>`<button type="button" class="usta-code" data-fault-code="${esc(c.code)}">${esc(c.code)}</button>`).join('')}</div><label class="usta-field-label">Diğer kodlar<select id="ustaCodeSelect" class="usta-field"><option value="">Kod seçin / aşağıya yazın</option>${codes.map(c=>`<option${state.code===c.code?' selected':''}>${esc(c.code)}</option>`).join('')}</select></label>`:''}<label class="usta-field-label">${hasCode()?'Ekrandaki kod':'Varsa ekrandaki kod'} <span>(isteğe bağlı)</span><input id="ustaCode" class="usta-field" maxlength="40" value="${esc(state.code)}" placeholder="E1, E01, F.28… aynen yazın" autocomplete="off"></label><p class="usta-note">E1 ve E01 ayrı kodlardır. Modeli bilmeden bir kod anlamı seçmeyiz.</p>`;
  }
  function fields() {
    if (state.step===0) return `<div class="usta-grid usta-grid--devices">${['Kombi','Klima','Petek'].map(d=>choice(d,deviceIcon(d)+d,d==='Kombi'?'Isıtma / sıcak su':d==='Klima'?'Isıtma / soğutma':'Radyatör / tesisat')).join('')}</div>`;
    if (state.step===1) return `<div class="usta-grid">${(symptoms[state.device]||[]).map(([key,label])=>choice(key,esc(label))).join('')}</div>`;
    if (state.step===2) {
      const names = brands();
      return `<div class="usta-grid">${names.slice(0,6).map(name=>`<button class="usta-choice" type="button" data-brand="${esc(name)}">${esc(name)}</button>`).join('')}</div><label class="usta-field-label">Tüm markalar<select id="ustaBrand" class="usta-field"><option value="">Marka seçin</option>${names.map(name=>`<option${state.brand===name?' selected':''}>${esc(name)}</option>`).join('')}</select></label>${state.brand?`<button type="button" class="usta-next" data-brand="${esc(state.brand)}">${esc(state.brand)} ile devam et →</button>`:''}<button type="button" class="usta-back" data-brand="">Markayı bilmiyorum, devam et →</button>`;
    }
    if (state.step===3) return modelFields()+codeFields()+`<button type="button" class="usta-back" data-unknown-code>Modeli / kodu bilmiyorum, devam et →</button>`;
    return `<dl class="usta-summary"><dt>Cihaz / belirti</dt><dd>${esc(state.device+' · '+symptomText())}</dd>${state.brand||state.model?`<dt>Marka / model</dt><dd>${esc([state.brand,state.model].filter(Boolean).join(' · '))}</dd>`:''}${state.code?`<dt>Ekrandaki kod</dt><dd>${esc(state.code)}</dd>`:''}${state.detail?`<dt>Anlatımınız</dt><dd>${esc(state.detail)}</dd>`:''}</dl><details id="ustaLocationContext" class="usta-free"><summary>Servis için bölge ekleyin <span>(isteğe bağlı)</span></summary><div class="usta-fields"><label>İlçe<select id="ustaDistrict" class="usta-field"><option value="">Daha sonra paylaşırım</option>${(catalog().districts||[]).map(d=>`<option${state.district===d?' selected':''}>${esc(d)}</option>`).join('')}</select></label><label>Mahalle / semt<input id="ustaNeighborhood" class="usta-field" maxlength="80" value="${esc(state.neighborhood)}" placeholder="Örn. Atakent"></label></div></details>`;
  }
  function showLocal() {
    compose();
    if (safetyCheck()) return;
    if (typeof window.STDiagnosticGuide==='function' && typeof window.renderDiagnostic==='function') window.renderDiagnostic(window.STDiagnosticGuide(state.device,el('issueInput').value,{...state}));
  }
  function result(from) { state.last_detail_step=from; go(4); }
  function afterSymptom() {
    compose();
    if (safetyCheck()) return;
    if (state.device==='Petek') { state.skip_model=true; result(1); }
    else go(2);
  }
  function chooseBrand(name) {
    const canonical = window.STBrands?.find(name,state.device.toLowerCase())?.name || name;
    const priorCode = state.brand ? '' : state.code;
    if (state.brand!==canonical) resetModel();
    state.brand=canonical; state.code=priorCode || state.code; state.skip_model=!canonical && !hasCode();
    clearResult();
    if (state.skip_model) result(2); else go(3);
  }
  function render(focus=true) {
    compose();
    const sequence = state.device==='Petek' ? [0,1,4] : state.skip_model ? [0,1,2,4] : [0,1,2,3,4];
    const position = Math.max(0,sequence.indexOf(state.step));
    const labels=['Cihaz','Belirti','Marka','Model / kod','İlk yönlendirme'];
    el('ustaStepLabel').textContent=(position+1)+' / '+sequence.length+' · '+labels[state.step];
    const progress=el('ustaProgress'); progress.setAttribute('aria-valuemax',sequence.length); progress.setAttribute('aria-valuenow',position+1);
    progress.replaceChildren(...sequence.map((_,i)=>{const span=document.createElement('span');span.classList.toggle('is-complete',i<=position);return span;}));
    const titles=['Hangi cihazda sorun var?','Ne sorun yaşıyorsunuz?','Cihazın markası nedir?',hasCode()?'Model ve ekrandaki kod':'Modelini biliyor musunuz?','İlk yönlendirmeniz hazır'];
    const notes=['Bir cihaz seçerek başlayın.','Bir belirti seçin veya aşağıya kendi cümlenizle yazın.','Markayı seçin; bilmiyorsanız bu soruyu atlayabilirsiniz.','Tam model, kodları doğru belgeyle değerlendirmemize yardımcı olur. Bu adımı atlayabilirsiniz.','Bilgileriniz aşağıda. İsterseniz bu bilgilerle arayın veya WhatsApp’a aktarın.'];
    const view=el('ustaStep'); view.innerHTML=`<h3 id="ustaQuestion">${esc(titles[state.step])}</h3><p>${esc(notes[state.step])}</p>${fields()}`;
    view.querySelectorAll('[data-choice]').forEach(button=>button.addEventListener('click',()=>{
      clearResult();
      if (state.step===0) {
        const device=button.dataset.choice;
        if (state.device!==device) { resetModel(); Object.assign(state,{brand:'',symptom:'',answer:'',detail:'',skip_model:false});el('ustaExtraIssue').value=''; }
        state.device=device; go(1);
      } else {
        state.symptom=button.dataset.choice;state.answer='';state.detail=el('ustaExtraIssue').value.trim();state.code=window.STFaults?.extract(state.detail)||'';afterSymptom();
      }
    }));
    view.querySelectorAll('[data-brand]').forEach(button=>button.addEventListener('click',()=>chooseBrand(button.dataset.brand)));
    el('ustaBrand')?.addEventListener('change',event=>{if(event.target.value)chooseBrand(event.target.value);});
    el('ustaVerifiedModel')?.addEventListener('change',event=>{
      const value=event.target.value,priorCode=state.model_id?'':state.code;resetModel();state.code=priorCode;
      if(value){const split=value.indexOf('|');state.model_id=value.slice(0,split);state.model=value.slice(split+1);}
      clearResult();render(false);
    });
    el('ustaModel')?.addEventListener('input',event=>{state.model=event.target.value.trim();state.model_id='';state.scope_confirmed=false;state.code='';el('ustaModelScope')?.remove();if(el('ustaVerifiedModel'))el('ustaVerifiedModel').value='';compose();clearResult();});
    const bind=(id,key)=>el(id)?.addEventListener('input',event=>{state[key]=event.target.value.trim();compose();clearResult();safetyCheck();});
    bind('ustaCode','code');bind('ustaNeighborhood','neighborhood');
    el('ustaScopeConfirmed')?.addEventListener('change',event=>{state.scope_confirmed=event.target.checked;compose();clearResult();});
    el('ustaDistrict')?.addEventListener('change',event=>{state.district=event.target.value;state.neighborhood='';compose();if(el('ustaNeighborhood'))el('ustaNeighborhood').value='';});
    el('ustaCodeSelect')?.addEventListener('change',event=>{state.code=event.target.value;if(el('ustaCode'))el('ustaCode').value=state.code;compose();});
    view.querySelectorAll('[data-fault-code]').forEach(button=>button.addEventListener('click',()=>{state.code=button.dataset.faultCode;compose();result(3);}));
    view.querySelector('[data-unknown-code]')?.addEventListener('click',()=>result(3));
    el('ustaBack').hidden=state.step===0;el('ustaNext').hidden=state.step!==3;el('ustaNext').textContent='İlk yönlendirmeyi göster →';
    el('ustaExtraWrap').hidden=state.step!==1;el('ustaSubmitWrap').hidden=state.step!==4;
    const contacts=root.querySelector('.usta-direct-contacts');if(contacts)contacts.hidden=state.step===4||!!root.dataset.emergency;
    if(focus)view.focus({preventScroll:true});
    if(state.step===4)showLocal();
  }
  function go(step) { state.step=step;render(); }
  function showEmergency(type) {
    clearResult();const gas=type==='gas',phone=gas?'187':'112';
    el('ustaSafety').hidden=false;el('ustaSafetyTitle').textContent=gas?'Gaz kokusunda önce güvenlik':'Duman veya yangın varsa önce güvenlik';
    el('ustaSafetyText').textContent=gas?'Elektrik düğmelerine ve prizlere dokunmayın; ateş yakmayın. Ortamdan ayrılıp güvenli bir yerden 187 Doğal Gaz Acil hattını arayın. Cihaza müdahale etmeyin.':'Cihazı kullanmayı sürdürmeyin. Duman, yangın veya yaralanma varsa güvenli biçimde uzaklaşın ve 112 Acil Çağrı Merkezi’ni arayın.';
    el('ustaSafetyCall').href='tel:'+phone;el('ustaSafetyCall').textContent=phone+' Acil hattını ara';el('askBtn').disabled=true;root.dataset.emergency=type;
    const contacts=root.querySelector('.usta-direct-contacts');if(contacts)contacts.hidden=true;
    el('ustaSafety').focus();
  }
  function safetyCheck() {
    const text=[state.detail,state.answer].join(' ').toLocaleLowerCase('tr-TR');
    if(/gaz\s*kok|doğal\s*gaz.*kaç|dogal\s*gaz.*kac/.test(text)){showEmergency('gas');return true;}
    if(/duman|yangın|yangin|yanık kok|yanik kok/.test(text)){showEmergency('burn');return true;}
    if(root.dataset.emergency)return true;
    el('ustaSafety').hidden=true;el('askBtn').disabled=false;return false;
  }
  function reset() {
    Object.assign(state,{step:0,device:'',brand:'',model:'',model_id:'',scope_confirmed:false,symptom:'',answer:'',code:'',district:'',neighborhood:'',detail:'',last_detail_step:1,skip_model:false});
    delete root.dataset.emergency;el('ustaExtraIssue').value='';clearResult();safetyCheck();render();
  }
  el('ustaBack').addEventListener('click',()=>{clearResult();go(state.step===4?state.last_detail_step:Math.max(0,state.step-1));});
  el('ustaNext').addEventListener('click',()=>{if(!safetyCheck())result(3);});
  el('ustaRestart').addEventListener('click',reset);
  el('ustaExtraIssue').addEventListener('input',event=>{state.detail=event.target.value.trim();compose();clearResult();safetyCheck();});
  el('ustaFreeNext').addEventListener('click',()=>{
    if(!state.device){go(0);return;}
    if(state.detail.length<3){el('ustaExtraIssue').setCustomValidity('Lütfen belirtinizi birkaç kelimeyle yazın.');el('ustaExtraIssue').reportValidity();el('ustaExtraIssue').addEventListener('input',()=>el('ustaExtraIssue').setCustomValidity(''),{once:true});return;}
    state.symptom='other';state.answer='';state.code=window.STFaults?.extract(state.detail)||'';afterSymptom();
  });
  el('ustaGas').addEventListener('click',()=>showEmergency('gas'));el('ustaFire').addEventListener('click',()=>showEmergency('burn'));
  el('ustaSafetyDismiss').addEventListener('click',()=>{delete root.dataset.emergency;state.answer='';state.detail='';el('ustaExtraIssue').value='';safetyCheck();compose();const contacts=root.querySelector('.usta-direct-contacts');if(contacts)contacts.hidden=state.step===4;});
  el('ustaLocalGuide').addEventListener('click',showLocal);
  if(!root.querySelector('.usta-direct-contacts')){
    const contacts=document.createElement('div');contacts.className='usta-direct-contacts';contacts.style.cssText='display:flex;gap:20px;flex-wrap:wrap;padding:18px 0;font-size:15px';
    contacts.innerHTML='<a href="tel:05346225515">Servisi ara ↗</a><a id="ustaQuickWhatsapp" href="https://wa.me/905346225515" target="_blank" rel="noopener noreferrer">WhatsApp’a aktar ↗</a>';
    el('ustaExtraWrap').after(contacts);
    contacts.querySelector('a:last-child').addEventListener('click',()=>{compose();contacts.querySelector('a:last-child').href='https://wa.me/905346225515?text='+encodeURIComponent('Merhaba Sağlam Teknik. Cihaz: '+(state.device||'Belirtilmedi')+'. '+el('issueInput').value+'\nServis uygunluğunu görüşmek istiyorum.');});
  }
  window.STUstaWizard={
    open(device){
      if(['Kombi','Klima','Petek'].includes(device)){
        if(state.device!==device){resetModel();Object.assign(state,{brand:'',symptom:'',answer:'',detail:'',skip_model:false});el('ustaExtraIssue').value='';}
        state.device=device;go(1);
      }else go(0);
      root.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});
    },
    getContext(){return {...state};},
    submit(){
      compose();if(safetyCheck())return;
      if(state.step!==4){if(state.device&&state.symptom)result(state.step);else go(state.device?1:0);return;}
      if(window.ST_PREVIEW){showLocal();const source=el('aiSource');if(source)source.textContent+=' · Test sürümünde AI bağlantısı kapalı';return;}
      if(typeof window.diagnoseIssue==='function')window.diagnoseIssue();
    }
  };
  const query=new URLSearchParams(location.search),legacy=new URLSearchParams(location.hash.slice(1));
  const param=key=>query.get(key)||legacy.get(key)||'';
  if(param('usta')==='1'){
    state.device=param('cihaz')==='klima'?'Klima':'Kombi';
    const name=param('marka');state.brand=window.STBrands?.find(name,state.device.toLowerCase())?.name||name;state.model=param('model');state.step=1;
  }
  render(false);
})();
