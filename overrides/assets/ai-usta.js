'use strict';
(() => {
  const root = document.getElementById('aiUstaWizard');
  if (!root) return;
  const el = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const state = {step:0,device:'',brand:'',model:'',model_id:'',model_unknown:false,scope_confirmed:false,symptom:'',answer:'',code:'',district:'',neighborhood:'',detail:'',last_detail_step:1,skip_model:false};
  let modelPrompt=false;
  let manualModel=false;
  let manualModelDraft='';
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
  // The single field suggests known names; selecting a model does not validate its market.
  let inputSuggestion = {brand:'',model_id:'',model:'',code:''};
  const normalize = value => window.STBrands?.normalize(value) || String(value||'').toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i').replace(/[^a-z0-9]+/g,' ').trim();
  const contains = (text,term) => !!term && (' '+text+' ').includes(' '+term+' ');
  function recognizeInput(value) {
    const text=normalize(value),device=state.device.toLowerCase();
    const registry=window.STBrands?.list(device) || brands().map(name=>({name,aliases:[]}));
    const brandMatches=registry.filter(item=>[item.name,...(item.aliases||[])].some(name=>contains(text,normalize(name))));
    let brand=brandMatches.length===1?brandMatches[0].name:'';
    const candidates=[];
    if(brandMatches.length<=1)for(const model of window.ST_VERIFIED_FAULTS?.models||[]) {
      if(model.device!==device||model.matchable===false)continue;
      const modelBrand=window.STBrands?.find(model.brand,device)?.name||model.brand;
      if(brand&&normalize(modelBrand)!==normalize(brand))continue;
      for(const name of model.model_names||[]) {
        const term=normalize(name);
        if(term.length<5||/^\d+(?: \d+)*(?: kw| btu| btu h)?$/.test(term))continue;
        // A bare family alias or generic single word cannot establish a model.
        if(!brand&&!/\d/.test(term)&&term.split(' ').length<2)continue;
        if(contains(text,term))candidates.push({brand:modelBrand,model_id:model.id,model:name,length:term.length});
      }
    }
    const longest=Math.max(0,...candidates.map(item=>item.length));
    const exact=candidates.filter(item=>item.length===longest);
    const unique=[...new Map(exact.map(item=>[item.model_id+'|'+item.model,item])).values()];
    const match=unique.length===1?unique[0]:null;
    if(match)brand=match.brand;
    const definition=match?(window.ST_VERIFIED_FAULTS?.models||[]).find(model=>model.id===match.model_id):null;
    return {brand,model_id:match?.model_id||'',model:match?.model||'',code:window.STFaults?.extract(value,definition)||''};
  }
  function updateInputHint() {
    const hint=el('ustaInputHint');if(!hint)return;
    const found=recognizeInput(state.detail);
    const parts=[found.brand,found.model,found.code&&'Kod: '+found.code].filter(Boolean);
    hint.textContent=parts.length?'Öneri: '+parts.join(' · ')+'. Sonraki adımda kontrol edebilirsiniz.':'';
    hint.hidden=!parts.length;
  }
  function applyInput() {
    inputSuggestion=recognizeInput(state.detail);
    if((inputSuggestion.brand&&inputSuggestion.brand!==state.brand)||(inputSuggestion.model_id&&inputSuggestion.model_id!==state.model_id))resetModel();
    if(inputSuggestion.brand)state.brand=inputSuggestion.brand;
    state.code=inputSuggestion.code;
  }
  function modelSuggestion() {
    if(!inputSuggestion.model_id||inputSuggestion.brand!==state.brand||state.model_id===inputSuggestion.model_id&&state.model===inputSuggestion.model)return '';
    if(!models().some(model=>model.id===inputSuggestion.model_id))return '';
    return `<p class="usta-note">Yazdığınız tam model için öneri:</p><button type="button" class="usta-choice" id="ustaUseSuggestedModel" data-suggested-model="${esc(inputSuggestion.model_id+'|'+inputSuggestion.model)}">${esc(inputSuggestion.model)}<small>Etiketteki ad aynıysa seçin.</small></button>`;
  }
  function useModel(value) {
    const priorCode=state.model_id?'':state.code;resetModel(true);state.code=priorCode;
    if(value){const split=value.indexOf('|'),id=value.slice(0,split);state.model=value.slice(split+1);state.model_id=id==='directory'?'':id;state.model_unknown=id==='directory';}
    clearResult();render(false);
  }
  function clearResult() { el('aiResultBox')?.classList.add('hidden'); }
  function resetModel(preserveDraft=false) { Object.assign(state, {model:'',model_id:'',model_unknown:false,scope_confirmed:false,code:''});modelPrompt=false;manualModel=false;if(!preserveDraft)manualModelDraft=''; }
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
    if (!model) return state.model?'<p class="usta-note" data-model-directory-note>Model adını aldık. Modele özel kod açıklaması için eşleşen üretici belgesi gerekir.</p>':'';
    const warning = window.STFaults?.lookup({device:state.device.toLowerCase(),brand:state.brand,model_id:model.id}).scope_warning || '';
    return `<div id="ustaModelScope">${warning?`<p class="usta-note" data-model-source-notice>${esc(warning)}</p>`:''}<details class="usta-free"><summary>Model kapsamı ve üretici kaynağı <span aria-hidden="true">+</span></summary>${model.market?`<p class="usta-note"><strong>Belgenin pazarı / bölgesi:</strong> ${esc(model.market)}</p>`:''}${model.scope_note?`<p class="usta-note">${esc(model.scope_note)}</p>`:''}${model.matchable===false?'<p class="usta-note">Bu belge kapasiteye veya benzer ada bakılarak otomatik eşleştirilemez. Cihazın belge ve ürün numarası ayrıca kontrol edilmelidir.</p>':''}${model.requires_document_match?`<p class="usta-note"><strong>Seçilen üretici belgesi:</strong> ${esc(model.manual?.title||model.label)}</p>`:''}<p class="usta-note">${esc((model.model_names||[]).join(' · '))}</p>${model.manual?.source_available!==false&&model.manual?.url?`<a href="${esc(model.manual.url)}" target="_blank" rel="noopener noreferrer">Üretici belgesini aç ↗</a>`:''}</details></div>`;
  }
  function modelFields() {
    if (!state.brand) return '<p class="usta-note">Ekrandaki kodu yazabilir veya modeli bilmeden devam edebilirsiniz.</p>';
    const list = models();
    const choices=[],seen=new Set(),verifiedValues=new Set();
    for (const model of list) {
      const names = model.matchable===false && model.requires_document_match ? [model.label] : model.model_names?.length ? model.model_names : [model.label];
      for (const name of names) {
        const label = /^\d+\s*(?:kw|btu)?$/i.test(name) ? model.label : name;
        const value=model.id+'|'+name;if(verifiedValues.has(value))continue;verifiedValues.add(value);seen.add(normalize(label));seen.add(normalize(name));
        choices.push({value,label:label.toLowerCase().startsWith(model.brand.toLowerCase())?label:model.brand+' '+label,family:model.manual?.title||model.label,selected:state.model_id===model.id&&state.model===name});
      }
    }
    for(const item of window.STModelDirectory?.list(state.device.toLowerCase(),state.brand)||[]){
      const name=String(item.name||'').trim(),key=normalize(name);if(!key||seen.has(key))continue;seen.add(key);
      const exact=typeof item.verified_model_id==='string'?list.find(model=>model.id===item.verified_model_id&&(model.model_names||[]).some(label=>normalize(label)===key)):null;
      const id=exact?.id||'directory';
      choices.push({value:id+'|'+name,label:name.toLocaleLowerCase('tr-TR').startsWith(state.brand.toLocaleLowerCase('tr-TR'))?name:state.brand+' '+name,selected:state.model===name&&(state.model_id===id||id==='directory'&&!state.model_id)});
    }
    const labels=new Map();for(const item of choices){const key=normalize(item.label);labels.set(key,(labels.get(key)||0)+1);}
    const options=choices.sort((a,b)=>a.label.localeCompare(b.label,'tr',{numeric:true})).map(item=>`<option value="${esc(item.value)}"${item.selected?' selected':''}>${esc(item.label+(labels.get(normalize(item.label))>1&&item.family?' — '+item.family:''))}</option>`).join('');
    const prompt=modelPrompt?`<p id="ustaModelPrompt" class="usta-note" role="status">${esc(state.code?state.code+' kodu için':'Hata kodunu yorumlamak için')} ${esc(state.brand)} cihazınızın tam modelini seçin. Bilmiyorsanız “Modeli bilmiyorum” ile ön bilgiye geçebilirsiniz.</p>`:'';
    const control=manualModel?`<label class="usta-field-label" for="ustaModel">Modeliniz <span>(isteğe bağlı)</span><input id="ustaModel" class="usta-field" maxlength="120" value="${esc(state.model)}" placeholder="Etiketteki model adını yazın" autocomplete="off"></label><button id="ustaChooseModel" class="usta-inline-action" type="button">← Model listesini aç</button>`:`${choices.length?`<label class="usta-field-label" for="ustaVerifiedModel">${esc(state.brand)} modeli <span>(isteğe bağlı)</span><select id="ustaVerifiedModel" class="usta-field"><option value="">Modeli seçin</option>${options}</select></label>`:'<p class="usta-note">Bu markanın model listesi hazırlanıyor. Modelinizi yazabilir veya devam edebilirsiniz.</p>'}<button id="ustaWriteModel" class="usta-inline-action" type="button">Modelim listede yok, yazayım</button>`;
    return `${prompt}${manualModel?'':modelSuggestion()}${control}${scopeFields()}`;
  }
  function codeFields() {
    const codes = (selectedModel()?.codes || []).filter(code => code.matchable!==false && !code.source_conflict);
    return `<label class="usta-field-label" for="ustaCode">Ekrandaki hata kodu <span>(isteğe bağlı)</span><input id="ustaCode" class="usta-field" maxlength="40" value="${esc(state.code)}" placeholder="Örn. E01 veya F22" autocomplete="off"${codes.length?' list="ustaDocumentedCodes"':''}></label>${codes.length?`<datalist id="ustaDocumentedCodes">${codes.map(c=>`<option value="${esc(c.code)}"></option>`).join('')}</datalist>`:''}<p class="usta-note">Kod açıklaması yalnız eşleşen model belgesinden alınır.</p>`;
  }
  function fields() {
    if (state.step===0) return `<div class="usta-grid usta-grid--devices">${['Kombi','Klima','Petek'].map(d=>choice(d,deviceIcon(d)+d,d==='Kombi'?'Isıtma / sıcak su':d==='Klima'?'Isıtma / soğutma':'Radyatör / tesisat')).join('')}</div>`;
    if (state.step===1) return `<div class="usta-grid">${(symptoms[state.device]||[]).map(([key,label])=>choice(key,esc(label))).join('')}</div>`;
    if (state.step===2) {
      const names = brands();
      return `<label class="usta-field-label" for="ustaBrand">Cihazın markası<select id="ustaBrand" class="usta-field"><option value="">Marka seçin</option>${names.map(name=>`<option${state.brand===name?' selected':''}>${esc(name)}</option>`).join('')}</select></label>${state.brand?`<button type="button" class="usta-next" data-brand="${esc(state.brand)}">${esc(state.brand)} ile devam et →</button>`:''}<button type="button" class="usta-back" data-brand="">Markayı bilmiyorum, devam et →</button>`;
    }
    if (state.step===3) return modelFields()+codeFields()+`<button type="button" class="usta-back" data-unknown-code>${state.code&&!selectedModel()?'Modeli bilmiyorum, ön bilgiye geç':'Modeli / kodu bilmiyorum, devam et'} →</button>`;
    return `<details class="usta-context-details"><summary>Seçimlerinizi görüntüleyin</summary><dl class="usta-summary"><dt>Cihaz / belirti</dt><dd>${esc(state.device+' · '+symptomText())}</dd>${state.brand||state.model?`<dt>Marka / model</dt><dd>${esc([state.brand,state.model].filter(Boolean).join(' · '))}</dd>`:''}${state.code?`<dt>Ekrandaki kod</dt><dd>${esc(state.code)}</dd>`:''}${state.detail?`<dt>Anlatımınız</dt><dd>${esc(state.detail)}</dd>`:''}</dl></details><details id="ustaLocationContext" class="usta-free"><summary>Servis için bölge ekleyin <span>(isteğe bağlı)</span></summary><div class="usta-fields"><label>İlçe<select id="ustaDistrict" class="usta-field"><option value="">Daha sonra paylaşırım</option>${(catalog().districts||[]).map(d=>`<option${state.district===d?' selected':''}>${esc(d)}</option>`).join('')}</select></label><label>Mahalle / semt<input id="ustaNeighborhood" class="usta-field" maxlength="80" value="${esc(state.neighborhood)}" placeholder="Örn. Atakent"></label></div></details>`;
  }
  function showLocal() {
    compose();
    if (safetyCheck()) return;
    if (typeof window.STDiagnosticGuide==='function' && typeof window.renderDiagnostic==='function') window.renderDiagnostic(window.STDiagnosticGuide(state.device,el('issueInput').value,{...state}));
  }
  function requestModel() {
    state.model_unknown=false;state.skip_model=false;modelPrompt=true;clearResult();go(3);
  }
  function result(from) {
    if(hasCode()&&state.brand&&!selectedModel()&&!state.model_unknown){requestModel();return;}
    state.last_detail_step=from;go(4);
  }
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
    const titles=['Cihazınızı seçin','Sorun nedir?','Markayı seçin',hasCode()?'Modeliniz ve hata kodu':'Modeli seçin','İlk değerlendirmeniz'];
    const notes=['Kombi, klima veya petek.','Bir belirti seçin veya yukarıya yazın.','Bilmiyorsanız devam edebilirsiniz.','Model seçmek zorunlu değil.','İsterseniz bu bilgilerle servis talebi bırakın.'];
    const view=el('ustaStep'); view.innerHTML=`<h3 id="ustaQuestion">${esc(titles[state.step])}</h3><p>${esc(notes[state.step])}</p>${fields()}`;
    view.querySelectorAll('[data-choice]').forEach(button=>button.addEventListener('click',()=>{
      clearResult();
      if (state.step===0) {
        const device=button.dataset.choice;
        if (state.device!==device) { resetModel(); Object.assign(state,{brand:'',symptom:'',answer:'',detail:'',skip_model:false});el('ustaExtraIssue').value='';inputSuggestion={brand:'',model_id:'',model:'',code:''}; }
        state.device=device; go(1);
      } else {
        state.symptom=button.dataset.choice;state.answer='';state.detail=el('ustaExtraIssue').value.trim();applyInput();afterSymptom();
      }
    }));
    view.querySelectorAll('[data-brand]').forEach(button=>button.addEventListener('click',()=>chooseBrand(button.dataset.brand)));
    el('ustaBrand')?.addEventListener('change',event=>{if(event.target.value)chooseBrand(event.target.value);});
    el('ustaVerifiedModel')?.addEventListener('change',event=>useModel(event.target.value));
    el('ustaUseSuggestedModel')?.addEventListener('click',event=>useModel(event.currentTarget.dataset.suggestedModel));
    el('ustaWriteModel')?.addEventListener('click',()=>{const code=state.code;resetModel(true);state.code=code;state.model=manualModelDraft;state.model_unknown=!!manualModelDraft;manualModel=true;clearResult();render(false);el('ustaModel')?.focus({preventScroll:true});});
    el('ustaChooseModel')?.addEventListener('click',()=>{manualModel=false;const code=state.code;resetModel(true);state.code=code;clearResult();render(false);el('ustaVerifiedModel')?.focus({preventScroll:true});});
    el('ustaModel')?.addEventListener('input',event=>{state.model=event.target.value.trim();manualModelDraft=state.model;state.model_id='';state.model_unknown=!!state.model;state.scope_confirmed=false;compose();clearResult();});
    const bind=(id,key)=>el(id)?.addEventListener('input',event=>{state[key]=event.target.value.trim();if(key==='code')state.model_unknown=!state.model_id&&!!state.model;compose();clearResult();safetyCheck();});
    bind('ustaCode','code');bind('ustaNeighborhood','neighborhood');
    el('ustaDistrict')?.addEventListener('change',event=>{state.district=event.target.value;state.neighborhood='';compose();if(el('ustaNeighborhood'))el('ustaNeighborhood').value='';});
    view.querySelector('[data-unknown-code]')?.addEventListener('click',()=>{state.model_unknown=!selectedModel();result(3);});
    el('ustaBack').hidden=state.step===0;el('ustaNext').hidden=state.step!==3;el('ustaNext').textContent='Arızamı bul →';
    el('ustaExtraWrap').hidden=state.step!==1;el('ustaSubmitWrap').hidden=state.step!==4;
    const contacts=root.querySelector('.usta-direct-contacts');if(contacts)contacts.hidden=state.step===4||!!root.dataset.emergency;
    updateInputHint();
    root.dataset.ustaStep=String(state.step);
    if(focus)(state.step===1?el('ustaExtraWrap'):view).focus({preventScroll:true});
    if(focus&&!matchMedia('(prefers-reduced-motion: reduce)').matches)view.animate?.([{opacity:.45},{opacity:1}],{duration:160,easing:'ease-out'});
    if(state.step===4)showLocal();
  }
  function go(step) { state.step=step;render();if(el('ustaStage'))el('ustaStage').scrollTop=0; }
  function showEmergency(type) {
    clearResult();const gas=type==='gas',phone=gas?'187':'112';
    el('ustaSafety').hidden=false;el('ustaSafetyTitle').textContent=gas?'Gaz kokusunda önce güvenlik':'Duman veya yangın varsa önce güvenlik';
    el('ustaSafetyText').textContent=gas?'Elektrik düğmelerine ve prizlere dokunmayın; ateş yakmayın. Ortamdan ayrılıp güvenli bir yerden 187 Doğal Gaz Acil hattını arayın. Cihaza müdahale etmeyin.':'Cihazı kullanmayı sürdürmeyin. Duman, yangın veya yaralanma varsa güvenli biçimde uzaklaşın ve 112 Acil Çağrı Merkezi’ni arayın.';
    el('ustaSafetyCall').href='tel:'+phone;el('ustaSafetyCall').textContent=phone+' Acil hattını ara';el('askBtn').disabled=true;root.dataset.emergency=type;
    const contacts=root.querySelector('.usta-direct-contacts');if(contacts)contacts.hidden=true;
    el('ustaSafety').focus({preventScroll:true});
    if(typeof window.stRecordAIResult==='function')window.stRecordAIResult({device:state.device||'Kombi',brand:state.brand,model:state.model,model_id:state.model_id,code:state.code,issue:[el('issueInput').value,gas?'Gaz kokusu':'Duman veya yangın'].filter(Boolean).join('. '),answer:[el('ustaSafetyTitle').textContent,el('ustaSafetyText').textContent,el('ustaSafetyCall').textContent].join('\n'),source:'emergency'});
  }
  function safetyCheck() {
    const text=[state.detail,state.answer].join(' ').toLocaleLowerCase('tr-TR');
    if(/gaz\s*kok|doğal\s*gaz.*kaç|dogal\s*gaz.*kac/.test(text)){showEmergency('gas');return true;}
    if(/duman|yangın|yangin|yanık kok|yanik kok/.test(text)){showEmergency('burn');return true;}
    if(root.dataset.emergency)return true;
    el('ustaSafety').hidden=true;el('askBtn').disabled=false;return false;
  }
  function reset() {
    Object.assign(state,{step:0,device:'',brand:'',model:'',model_id:'',model_unknown:false,scope_confirmed:false,symptom:'',answer:'',code:'',district:'',neighborhood:'',detail:'',last_detail_step:1,skip_model:false});modelPrompt=false;manualModel=false;manualModelDraft='';
    inputSuggestion={brand:'',model_id:'',model:'',code:''};delete root.dataset.emergency;el('ustaExtraIssue').value='';clearResult();safetyCheck();render();if(el('ustaStage'))el('ustaStage').scrollTop=0;
  }
  el('ustaBack').addEventListener('click',()=>{clearResult();go(state.step===4?state.last_detail_step:Math.max(0,state.step-1));});
  el('ustaNext').addEventListener('click',()=>{if(!safetyCheck())result(3);});
  el('ustaRestart').addEventListener('click',reset);
  el('ustaExtraIssue').addEventListener('input',event=>{state.detail=event.target.value.trim();updateInputHint();compose();clearResult();safetyCheck();});
  el('ustaFreeNext').addEventListener('click',()=>{
    if(!state.device){go(0);return;}
    if(state.detail.length<3){el('ustaExtraIssue').setCustomValidity('Lütfen belirtinizi birkaç kelimeyle yazın.');el('ustaExtraIssue').reportValidity();el('ustaExtraIssue').addEventListener('input',()=>el('ustaExtraIssue').setCustomValidity(''),{once:true});return;}
    state.symptom='other';state.answer='';applyInput();afterSymptom();
  });
  el('ustaExtraIssue').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.isComposing){event.preventDefault();el('ustaFreeNext').click();}});
  el('ustaGas').addEventListener('click',()=>showEmergency('gas'));el('ustaFire').addEventListener('click',()=>showEmergency('burn'));
  el('ustaSafetyDismiss').addEventListener('click',()=>{delete root.dataset.emergency;state.answer='';state.detail='';el('ustaExtraIssue').value='';updateInputHint();safetyCheck();compose();const contacts=root.querySelector('.usta-direct-contacts');if(contacts)contacts.hidden=state.step===4;});
  el('ustaLocalGuide').addEventListener('click',showLocal);
  if(!root.querySelector('.usta-direct-contacts')){
    const contacts=document.createElement('div');contacts.className='usta-direct-contacts';contacts.style.cssText='display:flex;gap:20px;flex-wrap:wrap;padding:18px 0;font-size:15px';
    contacts.innerHTML='<a href="tel:05346225515">Servisi ara ↗</a><a id="ustaQuickWhatsapp" href="https://wa.me/905346225515" target="_blank" rel="noopener noreferrer">WhatsApp’a aktar ↗</a>';
    el('ustaStep').after(contacts);
    contacts.querySelector('a:last-child').addEventListener('click',()=>{compose();contacts.querySelector('a:last-child').href='https://wa.me/905346225515?text='+encodeURIComponent('Merhaba Sağlam Teknik. Cihaz: '+(state.device||'Belirtilmedi')+'. '+el('issueInput').value+'\nServis uygunluğunu görüşmek istiyorum.');});
  }
  window.STUstaWizard={
    open(device){
      if(['Kombi','Klima','Petek'].includes(device)){
        if(state.device!==device){resetModel();Object.assign(state,{brand:'',symptom:'',answer:'',detail:'',skip_model:false});el('ustaExtraIssue').value='';inputSuggestion={brand:'',model_id:'',model:'',code:''};}
        state.device=device;go(1);
      }else go(0);
      const target=window.scrollY+root.getBoundingClientRect().top;
      window.scrollTo({top:Math.max(0,target-12),behavior:'instant'});
      const header=document.querySelector('.at-header,.premium-header,header');
      if(header){
        const rect=header.getBoundingClientRect(),position=getComputedStyle(header).position;
        if(['sticky','fixed'].includes(position)&&rect.top<=12&&rect.bottom>root.getBoundingClientRect().top){
          window.scrollTo({top:Math.max(0,target-rect.bottom-12),behavior:'instant'});
        }
      }
    },
    getContext(){return {...state};},
    requestModel,
    submit(){
      compose();if(safetyCheck())return;
      if(state.step!==4){if(state.device&&state.symptom)result(state.step);else go(state.device?1:0);return;}
      if(hasCode()&&!selectedModel()){showLocal();return;}
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
