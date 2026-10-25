'use strict';
// The preview simulates a quote only. Production fees always come from PHP.
(() => {
 const states=new WeakMap();let previewPolicy=null;
 const by=(form,id)=>form.querySelector('#'+id);
 const preview=()=>window.ST_PREVIEW===true||window.STEnvironment?.preview===true||location.protocol==='file:';
 const create=(tag,text,className)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;};
 const stateFor=form=>{if(!states.has(form))states.set(form,{quote:null,version:0,signature:'',timer:null,received:0,loading:false});return states.get(form);};
 const level=form=>by(form,'ticketServiceLevel')?.value||'standard';
 const signature=payload=>JSON.stringify(['name','phone','district','device','issue'].map(key=>String(payload[key]||'').trim()));
 function panel(form){let node=by(form,'ticketPriorityReview');if(!node){node=create('section',undefined,'ah-priority-review');node.id='ticketPriorityReview';node.hidden=true;node.setAttribute('aria-label','Öncelikli servis son onayı');node.setAttribute('aria-live','polite');const button=by(form,'ticketSubmitBtn');button?button.before(node):form.append(node);}return node;}
 function submitLabel(form){return level(form)==='priority'?(stateFor(form).quote?'Talep et':'Onaya gönder'):'Servis talebini gönder';}
 function updateLabel(form){const button=by(form,'ticketSubmitBtn');if(button)button.textContent=submitLabel(form);}
 function showContacts(form,show){form.querySelectorAll('[data-priority-contact-fields]').forEach(node=>node.hidden=!show);}
 function reset(form,message=''){
  const state=stateFor(form);if(state.timer)clearTimeout(state.timer);state.timer=null;state.quote=null;state.signature='';state.version++;
  const node=panel(form);node.replaceChildren();node.hidden=!message;if(message)node.append(create('p',message,'ah-form-note'));
  showContacts(form,true);updateLabel(form);
 }
 function expired(form){const state=stateFor(form);return !!state.quote&&state.quote.server_now+(performance.now()-state.received)/1000>=state.quote.expires_at;}
 function payloadNow(form,original){return {...original,name:by(form,'ticketName')?.value||'',phone:by(form,'ticketPhone')?.value||'',district:by(form,'ticketDistrict')?.value||'',device:by(form,'ticketDevice')?.value||'',issue:by(form,'ticketIssue')?.value||''};}
 function previewQuote(policy){
  if(!policy||policy.enabled!==true||!/^([01][0-9]|20):[0-5][0-9]$/.test(String(policy.night_end||'')))throw Error('Öncelikli servis saatleri henüz netleşmedi. Telefonla uygunluğu görüşebilirsiniz.');
  const now=Math.floor(Date.now()/1000),parts=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Istanbul',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(new Date(now*1000)).filter(part=>part.type!=='literal').map(part=>[part.type,Number(part.value)]));
  const seconds=parts.hour*3600+parts.minute*60+parts.second,[hour,minute]=policy.night_end.split(':').map(Number),end=hour*3600+minute*60,night=seconds>=75600||(end>0&&seconds<end),fee=night?4000:2500;
  const until=Math.min(...[75600,end].map(boundary=>{const delta=(boundary-seconds+86400)%86400;return delta===0?86400:delta;})),expiry=now+Math.min(600,until),label=new Intl.NumberFormat('tr-TR').format(fee)+' TL';
  return {ok:true,preview:true,fee_try:fee,fee_label:label,timezone:'Europe/Istanbul',server_now:now,expires_at:expiry,terms_version:'2026-10-25.1',terms_text:label+' öncelikli servis hizmet bedelini ve hizmet koşullarını kabul ediyorum. Öncelik ve varış uygunluğu ekiple görüşülerek kesinleşir. Ek işlem veya parça gerekirse kapsamı ve bedeli ayrıca onayıma sunulur. Bu adım ödeme tahsilatı yapmaz.',valid_until:new Intl.DateTimeFormat('tr-TR',{timeZone:'Europe/Istanbul',dateStyle:'short',timeStyle:'medium'}).format(new Date(expiry*1000))};
 }
 function renderQuote(form,quote,payload){
  const node=panel(form),state=stateFor(form);node.replaceChildren();node.hidden=false;
  const heading=create('h3','Öncelikli servis son onayı');heading.id='ticketPriorityTitle';heading.tabIndex=-1;
  const amount=create('p',quote.fee_label,'ah-priority-fee');amount.id='ticketPriorityFee';
  const detail=create('p',[payload.name,payload.device,payload.district].filter(Boolean).join(' · '),'ah-form-note');
  const terms=create('p',quote.terms_text,'ah-priority-terms');
  const expiry=create('p','Ücret onayı: '+quote.valid_until+' (İstanbul) saatine kadar. Tarife değişirse yeniden onay istenir.','ah-form-note');
  const checkbox=create('input');checkbox.type='checkbox';checkbox.id='ticketPriorityConsent';checkbox.required=true;
  const label=create('label');label.className='ah-priority-consent';label.append(checkbox,document.createTextNode(' '+quote.fee_label+' bedelini ve yukarıdaki koşulları kabul ediyorum.'));
  const edit=create('button','Bilgileri düzenle','ah-priority-edit');edit.type='button';edit.addEventListener('click',()=>{reset(form);by(form,'ticketName')?.focus({preventScroll:true});});
  node.append(heading,detail,amount,terms,expiry,label,edit);
  if(quote.preview)node.append(create('p','Tasarım ön izlemesi: bu adım kayıt açmaz veya mesaj göndermez.','ah-form-note'));
  state.quote=quote;state.received=performance.now();state.signature=signature(payload);showContacts(form,false);updateLabel(form);
  const delay=Math.max(1,(quote.expires_at-quote.server_now)*1000);
  state.timer=setTimeout(()=>reset(form,'Ücret onayının süresi doldu. Güncel bedeli yeniden görüntüleyip onaylayın.'),delay);
  const card=form.closest('.ah-modal-card');if(card)card.scrollTop=0;heading.focus({preventScroll:true});
 }
 async function beforeSubmit(form,payload){
  if(level(form)==='standard')return {ready:true,payload};
  if(level(form)!=='priority')throw Error('Hizmet seçimini kontrol edin.');
  const state=stateFor(form);
  if(state.loading)return {ready:false};
  if(state.quote&&(state.signature!==signature(payload)||expired(form)))reset(form);
  if(!state.quote){
   const version=state.version;state.loading=true;
   try{
    const input={...payload,service_level:'priority'};
    const quote=preview()?previewQuote(previewPolicy||window.ST_PRIORITY_POLICY||window.ST_PRIORITY_SERVICE_POLICY):await window.stApi('priority-quote',input);
    if(state.version!==version||level(form)!=='priority'||signature(payloadNow(form,payload))!==signature(payload))throw Error('Bilgileriniz değişti. Güncel bilgilerle yeniden onay isteyin.');
    if(!quote||quote.ok!==true||![2500,4000].includes(quote.fee_try)||typeof quote.fee_label!=='string'||typeof quote.terms_text!=='string'||typeof quote.terms_version!=='string'||!Number.isFinite(quote.server_now)||!Number.isFinite(quote.expires_at)||quote.expires_at<=quote.server_now||(!quote.preview&&typeof quote.priority_quote!=='string'))throw Error('Hizmet bedeli doğrulanamadı. Yeniden deneyin veya bizi arayın.');
    renderQuote(form,quote,payload);return {ready:false};
   }finally{state.loading=false;}
  }
  if(!by(form,'ticketPriorityConsent')?.checked)throw Error('Öncelikli servis bedelini ve koşullarını onaylayın.');
  if(preview()){
   const status=create('p','Bu test ön izlemesinde talebiniz kaydedilmedi ve ileti gönderilmedi.','ah-form-note');status.dataset.previewStatus='';panel(form).querySelector('[data-preview-status]')?.remove();panel(form).append(status);return {ready:false};
  }
  return {ready:true,payload:{...payload,service_level:'priority',priority_quote:state.quote.priority_quote,priority_accepted:true,priority_terms_version:state.quote.terms_version}};
 }
 function initialize(form){
  if(!form||form.dataset.priorityInitialized)return;form.dataset.priorityInitialized='1';stateFor(form);
  by(form,'ticketServiceLevel')?.addEventListener('change',()=>reset(form));
  for(const id of ['ticketName','ticketPhone','ticketDistrict','ticketDevice','ticketIssue']){
   const input=by(form,id);input?.addEventListener(input.tagName==='SELECT'?'change':'input',()=>{const state=stateFor(form);if(state.quote||state.loading)reset(form);});
  }
  form.addEventListener('reset',()=>queueMicrotask(()=>reset(form)));updateLabel(form);
 }
 function setLevel(form,value){initialize(form);const select=by(form,'ticketServiceLevel');if(select)select.value=value==='priority'?'priority':'standard';reset(form);}
 function onError(form,error){if(level(form)==='priority'&&error?.status===410){reset(form,error.message);return true;}return false;}
 window.STPriorityTicket={beforeSubmit,reset,initialize,setLevel,onError,handleError:onError,submitLabel,configurePreview:policy=>{previewPolicy={...policy};}};
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>initialize(document.getElementById('serviceTicketForm')),{once:true});else initialize(document.getElementById('serviceTicketForm'));
})();
