'use strict';
// The shipped home submit handler + shipped VIP UI in a real browser.
// Only quote/ticket responses are synthetic; no provider or production records.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
const root=path.resolve(process.argv[2]||'build/production'),reportPath=process.argv[3];
const checks=[];
const html=`<!doctype html><html lang="tr"><head><meta charset="utf-8"><style>[hidden],.hidden{display:none!important}body{font:16px sans-serif;margin:18px}input,select,textarea{display:block;min-height:32px;margin:6px}button{min-height:44px}.ah-modal-card{max-width:620px}</style></head><body>
<div id="serviceTicketModal" class="ah-modal-card"><form id="serviceTicketForm">
<select id="ticketServiceLevel"><option value="standard">Standart servis</option><option value="priority" selected>VIP Servis</option></select>
<div data-priority-contact-fields><input id="ticketName" value="Test Müşteri" required><input id="ticketPhone" value="5555555555" required>
<select id="ticketDistrict"><option>Esenler</option><option>Avcılar</option></select>
<select id="ticketNeighborhood"><option value="">Bilmiyorum</option><option selected>Tuna</option><option>Birlik</option></select>
<select id="ticketDevice"><option>Kombi</option><option>Klima</option><option>Petek</option></select>
<textarea id="ticketIssue" required>Kombi sıcak su vermiyor.</textarea><input id="ticketWebsite" value="" type="hidden"></div>
<p id="ticketError" role="alert"></p><button id="ticketSubmitBtn" type="submit">Onaya gönder</button>
<section id="ticketSuccessMsg" class="hidden"><p></p><a id="ticketDirectWhatsappBtn">WhatsApp</a><div id="ticketTrackingPanel" hidden><p id="ticketTrackingNotice"></p><a id="ticketTrackingLink">Servisini takip et</a></div></section>
</form></div><div data-premium-reviews></div></body></html>`;
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'}),page=await context.newPage(),errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 const check=(name,ok)=>{checks.push({name,passed:!!ok});assert(ok,name);};
 try{
  await page.setContent(html);
  await page.evaluate(()=>{
   window.ST_PREVIEW=false;window.__quotes=[];window.__tickets=[];window.__delay=0;
   window.stError=(id,text)=>{document.getElementById(id).textContent=text};
   window.stRequestKey=()=> 'synthetic-request-key';
   window.stApi=async(action,payload)=>{
    if(action==='priority-quote'){
     __quotes.push(structuredClone(payload));await new Promise(resolve=>setTimeout(resolve,__delay));
     const now=Math.floor(Date.now()/1000);return {ok:true,priority_quote:'synthetic-signed-'+__quotes.length,fee_try:2500,fee_label:'2.500 TL',server_now:now,expires_at:now+600,terms_version:'2026-10-25.1',terms_text:'Sentetik test: hizmet bedelini ve koşulları kabul ediyorum.',valid_until:'29.10.2026 20:00:00'};
    }
    if(action==='ticket'){__tickets.push(structuredClone(payload));return {ok:true,delivery:'queued',queue:{message:'Talep kaydı hazır.'}};}
    throw Error('Unexpected API action '+action);
   };
  });
  await page.addScriptTag({path:path.join(root,'assets/priority-service.js')});
  await page.addScriptTag({path:path.join(root,'assets/home.js')});
  check('No fee before first confirmation',await page.locator('#ticketPriorityFee').count()===0);
  await page.locator('#ticketSubmitBtn').click();
  if(process.env.EXPECT_BASELINE_VIP_BUG==='1'){
   await page.waitForFunction(()=>document.getElementById('ticketError').textContent.includes('Bilgileriniz değişti'));
   check('Original neighbourhood-composed issue reproduces the reported false change error',await page.locator('#ticketPriorityFee').count()===0);
   check('Actual home payload already contains the selected neighbourhood',await page.evaluate(()=>__quotes[0].issue.endsWith(' | Mahalle: Tuna')));
   const result={passed:true,baseline_bug_reproduced:true,checks,provider_requests:0};
   if(reportPath)fs.writeFileSync(reportPath,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));return;
  }
  await page.locator('#ticketPriorityFee').waitFor();
  check('Selected neighbourhood no longer triggers a false field-change error',await page.locator('#ticketError').innerText()==='');
  check('Quote uses the actual home-composed issue including neighbourhood',await page.evaluate(()=>__quotes.length===1&&__quotes[0].issue==='Kombi sıcak su vermiyor. | Mahalle: Tuna'&&__tickets.length===0));
  check('Fee is visible only in the final review with Talep et',await page.locator('#ticketPriorityFee').innerText()==='2.500 TL'&&await page.locator('#ticketSubmitBtn').innerText()==='Talep et');
  await page.locator('#ticketSubmitBtn').click();
  check('Unchecked fee acceptance cannot save a ticket',await page.evaluate(()=>__tickets.length===0));
  // Browser autofill may dispatch input without a semantic change. It must not
  // erase a correctly reviewed fee or the selected address.
  await page.evaluate(()=>document.getElementById('ticketPhone').dispatchEvent(new Event('input',{bubbles:true})));
  check('An unchanged autofill/input event preserves the review',await page.locator('#ticketPriorityConsent').count()===1);
  await page.locator('#ticketPriorityConsent').check();await page.locator('#ticketSubmitBtn').click();
  await page.waitForFunction(()=>__tickets.length===1);
  check('Final explicit acceptance preserves quote, fee terms and composed address context',await page.evaluate(()=>__tickets[0].service_level==='priority'&&__tickets[0].priority_accepted===true&&__tickets[0].priority_quote==='synthetic-signed-1'&&__tickets[0].issue===__quotes[0].issue));
  check('Standard service still bypasses the VIP quote',await page.evaluate(async()=>{const r=await STPriorityTicket.beforeSubmit(document.getElementById('serviceTicketForm'),{});STPriorityTicket.setLevel(document.getElementById('serviceTicketForm'),'standard');const a=await STPriorityTicket.beforeSubmit(document.getElementById('serviceTicketForm'),{issue:'standard'});return a.ready&&a.payload.issue==='standard';}));
  await page.evaluate(()=>{const f=document.getElementById('serviceTicketForm');STPriorityTicket.setLevel(f,'priority');document.getElementById('ticketSubmitBtn').classList.remove('hidden');document.getElementById('ticketSuccessMsg').classList.add('hidden');__delay=120;});
  await page.locator('#ticketSubmitBtn').click();
  await page.evaluate(()=>document.getElementById('ticketPhone').dispatchEvent(new Event('input',{bubbles:true})));
  await page.locator('#ticketPriorityFee').waitFor();
  check('An unchanged input event during the network wait does not invalidate the quote',await page.locator('#ticketPriorityConsent').count()===1&&await page.locator('#ticketError').innerText()==='');
  await page.locator('.ah-priority-edit').click();
  await page.locator('#ticketSubmitBtn').click();
  await page.locator('#ticketNeighborhood').selectOption('Birlik');
  await page.waitForFunction(()=>!document.getElementById('ticketSubmitBtn').disabled);
  check('A genuinely changed neighbourhood discards the late quote and requires a fresh review',await page.locator('#ticketPriorityConsent').count()===0&&await page.locator('#ticketSubmitBtn').innerText()==='Onaya gönder');
  await page.locator('#ticketSubmitBtn').click();await page.locator('#ticketPriorityFee').waitFor();
  check('A new quote is bound to the new neighbourhood instead of accepting the stale one',await page.evaluate(()=>__quotes.at(-1).issue.endsWith(' | Mahalle: Birlik')&&__tickets.length===1));
  await page.locator('#ticketNeighborhood').evaluate(el=>{el.value='Tuna';el.dispatchEvent(new Event('change',{bubbles:true}))});
  check('Neighbourhood changes after a review remove the old consent',await page.locator('#ticketPriorityConsent').count()===0);
  check('No JavaScript errors',errors.length===0);
  const result={passed:true,scope:'Actual shipped home submit handler and priority script in Chromium; synthetic API responses',checks,provider_requests:0,real_records:0,errors};
  if(reportPath)fs.writeFileSync(reportPath,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
 }finally{await context.close();await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
