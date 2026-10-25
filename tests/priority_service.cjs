/* Actual browser quote/consent UI, explicit synthetic API responses. No provider. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const repository=path.resolve(__dirname,'..'),reportPath=path.join(repository,'build/priority-service-browser.json');
const checks=[];const check=(name,ok)=>{checks.push({name,passed:!!ok});assert(ok,name);};
const html=`<!doctype html><html lang="tr"><head><meta charset="utf-8"><style>body{font:16px sans-serif;margin:20px}form{max-width:500px}label{display:block;margin:8px 0}input:not([type=checkbox]),textarea,select{display:block;max-width:100%;width:300px}button{min-height:44px;margin:6px} [hidden]{display:none!important}</style></head><body><form id="serviceTicketForm"><label>Hizmet<select id="ticketServiceLevel"><option value="standard">Standart servis</option><option value="priority">Öncelikli servis</option></select></label><div data-priority-contact-fields><label>Ad<input id="ticketName" value="Sentetik Test" required></label><label>Telefon<input id="ticketPhone" value="05340000000" required></label><label>İlçe<input id="ticketDistrict" value="Küçükçekmece" required></label><label>Cihaz<select id="ticketDevice"><option>Kombi</option><option>Klima</option></select></label><label>Belirti<textarea id="ticketIssue" required>Sentetik cihaz çalışmıyor.</textarea></label></div><p id="error" role="alert"></p><button id="ticketSubmitBtn" type="submit">Servis talebini gönder</button></form></body></html>`;
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']}),page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 try{
  await page.setContent(html);
  await page.evaluate(()=>{
   window.__quotes=[];window.__tickets=[];window.__serverFee=2500;window.__quoteSeconds=600;window.ST_PREVIEW=false;
   window.stApi=async(action,payload)=>{if(action!=='priority-quote')throw Error('Unexpected API action');window.__quotes.push({action,payload});const now=Math.floor(Date.now()/1000);return {ok:true,priority_quote:'synthetic-signed-quote',fee_try:window.__serverFee,fee_label:window.__serverFee===2500?'2.500 TL':'4.000 TL',timezone:'Europe/Istanbul',server_now:now,expires_at:now+window.__quoteSeconds,valid_until:'25.10.2026 21:00:00',terms_version:'2026-10-25.1',terms_text:'Sentetik açık hizmet bedeli onayı; bu testte ödeme alınmaz.'};};
  });
  await page.addScriptTag({path:path.join(repository,'overrides/assets/priority-service.js')});
  await page.evaluate(()=>{
   const form=document.getElementById('serviceTicketForm');
   window.__payload=()=>({name:document.getElementById('ticketName').value,phone:document.getElementById('ticketPhone').value,district:document.getElementById('ticketDistrict').value,device:document.getElementById('ticketDevice').value,issue:document.getElementById('ticketIssue').value,website:''});
   form.onsubmit=async event=>{event.preventDefault();const button=document.getElementById('ticketSubmitBtn');button.disabled=true;try{const next=await STPriorityTicket.beforeSubmit(form,__payload());if(next.ready)window.__tickets.push(next.payload);}catch(error){document.getElementById('error').textContent=error.message;}finally{button.disabled=false;button.textContent=STPriorityTicket.submitLabel(form);}};
  });
  check('Initial form displays no priority fee',await page.locator('#ticketPriorityFee').count()===0);
  await page.click('#ticketSubmitBtn');
  check('Standard request passes through unchanged without a quote',await page.evaluate(()=>__tickets.length===1&&__quotes.length===0&&!('service_level' in __tickets[0])));
  await page.selectOption('#ticketServiceLevel','priority');
  check('Priority choice displays Onaya gönder with no initial price',await page.locator('#ticketSubmitBtn').innerText()==='Onaya gönder'&&await page.locator('#ticketPriorityFee').count()===0);
  await page.click('#ticketSubmitBtn');await page.locator('#ticketPriorityFee').waitFor();
  check('First submit requests only a fee quote and creates no ticket',await page.evaluate(()=>__quotes.length===1&&__tickets.length===1));
  check('The final review displays the explicit server-authoritative fee',await page.locator('#ticketPriorityFee').innerText()==='2.500 TL');
  check('Final review shows terms, expiry and Talep et',await page.locator('#ticketPriorityConsent').count()===1&&await page.locator('#ticketPriorityReview').innerText().then(text=>text.includes('21:00:00')&&text.includes('hizmet bedeli'))&&await page.locator('#ticketSubmitBtn').innerText()==='Talep et');
  check('Contact group is hidden only after its values are preserved',await page.locator('[data-priority-contact-fields]').isHidden()&&await page.inputValue('#ticketName')==='Sentetik Test');
  await page.click('#ticketSubmitBtn');
  check('Unchecked acceptance cannot create the ticket',await page.evaluate(()=>__tickets.length===1));
  await page.check('#ticketPriorityConsent');await page.click('#ticketSubmitBtn');
  check('Only the explicit accepted final click hands a priority request to the caller',await page.evaluate(()=>__tickets.length===2&&__tickets[1].service_level==='priority'&&__tickets[1].priority_accepted===true&&__tickets[1].priority_quote==='synthetic-signed-quote'&&__tickets[1].priority_terms_version==='2026-10-25.1'&&!('priority_fee_try' in __tickets[1])));
  await page.click('.ah-priority-edit');
  check('Editing contacts removes the old quote and consent',await page.locator('[data-priority-contact-fields]').isVisible()&&await page.locator('#ticketPriorityConsent').count()===0&&await page.locator('#ticketSubmitBtn').innerText()==='Onaya gönder');
  await page.fill('#ticketDistrict','Avcılar');await page.evaluate(()=>window.__serverFee=4000);await page.click('#ticketSubmitBtn');
  check('A new quote shows the new fee and demands fresh consent',await page.locator('#ticketPriorityFee').innerText()==='4.000 TL'&&!await page.isChecked('#ticketPriorityConsent'));
  await page.evaluate(()=>{STPriorityTicket.handleError(document.getElementById('serviceTicketForm'),{status:410,message:'Ücret onayının süresi doldu.'});});
  check('Server expiry resets consent and requires a visible re-quote',await page.locator('#ticketPriorityConsent').count()===0&&await page.locator('#ticketSubmitBtn').innerText()==='Onaya gönder'&&(await page.locator('#ticketPriorityReview').innerText()).includes('süresi doldu'));
  await page.evaluate(()=>{window.__quoteSeconds=0.12;});await page.click('#ticketSubmitBtn');
  await page.waitForFunction(()=>!document.getElementById('ticketPriorityConsent'));
  check('Local expiry cannot leave a stale accepted price usable',await page.locator('#ticketSubmitBtn').innerText()==='Onaya gönder');
  await page.evaluate(()=>{window.ST_PREVIEW=true;window.ST_PRIORITY_POLICY={enabled:true,night_end:'08:00'};window.__quoteSeconds=600;});
  const quoteCount=await page.evaluate(()=>__quotes.length);await page.click('#ticketSubmitBtn');await page.check('#ticketPriorityConsent');await page.click('#ticketSubmitBtn');
  check('Preview final action sends no API call or service request',await page.evaluate(count=>__quotes.length===count&&__tickets.length===2,quoteCount));
  check('Preview truthfully says no request or message was sent',/kaydedilmedi.*gönderilmedi/.test(await page.locator('[data-preview-status]').innerText()));
  await page.selectOption('#ticketServiceLevel','standard');
  check('Switching back to standard removes all priority price/consent controls',await page.locator('#ticketPriorityFee').count()===0&&await page.locator('#ticketPriorityConsent').count()===0&&await page.locator('#ticketSubmitBtn').innerText()==='Servis talebini gönder');
  check('No JavaScript errors',errors.length===0);
  check('Mobile document does not overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  const report={passed:true,checks:checks.length,cases:checks,mock_api_requests:await page.evaluate(()=>__quotes.length),real_api_requests:0,provider_requests:0,page_errors:errors};fs.mkdirSync(path.dirname(reportPath),{recursive:true});fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
 }finally{await browser.close();}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
