/* Actual generated home in Chromium; synthetic API responses, no external delivery. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright'),{startServer}=require('./interaction_http.cjs');
const root=path.resolve(__dirname,'..'),directory=path.resolve(process.argv[2]||path.join(root,'build/production'));
(async()=>{
 const server=await startServer(directory,''),browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']}),checks=[],errors=[],external=[];
 const check=(ok,name)=>{checks.push({name,passed:!!ok});assert(ok,name);};
 const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});let report,reviewRefresh=false;
 const liveReviews=()=>[
  {id:'qa-linked',author:'QA Hizmet Kaydı',comment:'Sentetik hizmet kaydıyla eşleşen yorum.',rating:5,date:'24 Eki 2026',created:1792843200,status:'approved',cat:'klima',service:'Klima bakımı',service_verified:true,decided:1892843200},
  {id:'qa-old-ms',author:'QA Milisaniye',comment:'Sentetik milisaniye tarihli değerlendirme.',rating:5,date:'21 Eki 2026',created:1792584000000,status:'approved',cat:'kombi',service:'Kombi bakımı'},
  {id:'qa-invalid-date',author:'QA Tarihsiz',comment:'Sentetik geçersiz tarihli değerlendirme.',rating:5,date:'31.02.2026',status:'approved',cat:'kombi',service:'Kombi bakımı'},
  {id:'qa-numeric-date',author:'QA Sayısal Tarih',comment:'Sentetik sayısal tarihli değerlendirme.',rating:5,date:'22.10.2026',status:'approved',cat:'kombi',service:'Kombi bakımı'},
  {id:'qa-newest',author:'QA Yeni Yorum',comment:'Sentetik yeni değerlendirme örneği.',rating:5,date:'25 Eki 2026',created:1792929600,status:'approved',cat:'kombi',service:'Kombi bakımı',service_verified:false},
  {id:'qa-date-only',author:'QA Yazılı Tarih',comment:'Sentetik yalnız gün tarihli değerlendirme.',rating:5,date:'23 Ekim 2026',status:'approved',cat:'klima',service:'Klima bakımı'},
  ...(reviewRefresh?[{id:'qa-refresh',author:'QA Son Onaylanan',comment:'Odak yenilemesiyle gelen sentetik değerlendirme.',rating:5,date:'26.10.2026',status:'approved',cat:'kombi',service:'Kombi bakımı'}]:[])
 ];
 try{
  await page.route('**/*',route=>{
   const url=new URL(route.request().url());
   if(url.origin!==server.origin){external.push(url.href);return route.abort();}
   if(/\.php$/.test(url.pathname))return route.fulfill({contentType:'application/json',body:JSON.stringify(url.searchParams.get('action')==='reviews'?{ok:true,deleted_ids:['existing-0','existing-2'],reviews:liveReviews()}:url.searchParams.get('action')==='bootstrap'?{ok:true,csrf:'1700000000.'+'a'.repeat(64)}:{ok:true,recorded:true})});
   return route.continue();
  });
  page.on('pageerror',error=>errors.push(error.message));await page.goto(server.origin+'/',{waitUntil:'networkidle'});
  check(await page.locator('.p-entry-buttons button').count()===4,'Four device/AI entry buttons are present');
  check(await page.locator('#serviceEntryActions').isHidden(),'No duplicate service action panel before category choice');
  for(const device of ['Kombi','Klima','Petek']){
   const button=page.locator(`[data-service-device="${device}"]`);await button.scrollIntoViewIfNeeded();const before=await page.evaluate(()=>scrollY);await button.click();
   check(await page.locator('#serviceEntryActions').isVisible()&&Math.abs(await page.evaluate(()=>scrollY)-before)<3,device+' selection opens actions without scrolling the page');
   for(const level of ['standard','priority']){
    await page.locator(`#serviceEntryActions [data-ticket-level="${level}"]`).click();
    check(await page.locator('#serviceTicketModal').isVisible()&&await page.locator('#ticketDevice').inputValue()===device&&await page.locator('#ticketServiceLevel').inputValue()===level,device+' '+level+' opens the correct contact form');
    check(await page.locator('#ticketPriorityFee').count()===0,'No fee before '+device+' '+level+' final review');
    await page.keyboard.press('Escape');
   }
  }
  check(await page.locator('.pr-review').first().getAttribute('data-review-id')==='site-qa-newest','Newest approved live review is first');
  check(JSON.stringify(await page.locator('.pr-review').evaluateAll(cards=>cards.map(card=>card.dataset.reviewId)))===JSON.stringify(['site-qa-newest','site-qa-linked','site-qa-date-only','site-qa-numeric-date','site-qa-old-ms','existing-1']),'Shuffled Turkish, numeric and millisecond dates sort newest first, ignoring approval time');
  check(await page.locator('.pr-order').innerText()==='Sıralama: En yeni yorumlar önce','Newest-first order is stated beside the displayed reviews');
  await page.locator('#btnCatKlima').click();
  check(JSON.stringify((await page.locator('.pr-review').evaluateAll(cards=>cards.map(card=>card.dataset.reviewId))).slice(0,2))===JSON.stringify(['site-qa-linked','site-qa-date-only']),'Service filters preserve newest-first order');
  await page.locator('#btnCatAll').click();
  while(await page.locator('#premiumReviewsMore').isVisible())await page.locator('#premiumReviewsMore').click();
  check(await page.locator('.pr-review').last().getAttribute('data-review-id')==='site-qa-invalid-date','Impossible dates stay at the end instead of silently changing to another calendar day');
  await page.locator('#btnCatAll').click();
  reviewRefresh=true;await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await page.waitForFunction(()=>document.querySelector('.pr-review')?.dataset.reviewId==='site-qa-refresh');
  check(await page.locator('.pr-review').first().getAttribute('data-review-id')==='site-qa-refresh','Newly approved reviews move to the top on refresh rather than append at the bottom');

  check(await page.locator('[data-review-id="existing-0"],[data-review-id="existing-2"]').count()===0,'Deleted original seed IDs do not reappear');
  check((await page.locator('[data-review-id="site-qa-newest"] .pr-review-origin').innerText()).includes('Müşteri yorumu')&&!await page.locator('[data-review-id="site-qa-newest"] .is-service-verified').count(),'Publication approval does not claim a verified service');
  check(await page.locator('[data-review-id="site-qa-linked"] .is-service-verified').count()===1,'Only a service-linked review gets the service verification badge');
  check(!await page.locator('#yorumlar').innerText().then(text=>/Mevcut sitedeki değerlendirme/.test(text)),'Obsolete imported-review wording is absent');
  await page.evaluate(()=>window.scrollTo(0,0));await page.locator('#atMenuToggle').click();await page.locator('header a[href$="#yorumlar"]').first().click();
  const alignment=await page.evaluate(()=>{const header=document.querySelector('.at-header'),rect=header.getBoundingClientRect();return {heading:document.querySelector('#yorumlar .pr-intro').getBoundingClientRect().top,header:{top:rect.top,bottom:rect.bottom,position:getComputedStyle(header).position},menu_expanded:document.getElementById('atMenuToggle').getAttribute('aria-expanded')};});
  const visibleOverlay=['fixed','sticky'].includes(alignment.header.position)&&alignment.header.top<=12&&alignment.header.bottom>12;
  const expectedTop=12+(visibleOverlay?alignment.header.bottom:0);
  check(Math.abs(alignment.heading-expectedTop)<2,'Reviews heading aligns at12px below the viewport or an actually visible fixed header');
  check(alignment.menu_expanded==='false','Reviews navigation closes the mobile menu before positioning the heading');
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile home has no horizontal overflow');
  // A delayed result must not be attached to changed wizard inputs or Telegram context.
  await page.evaluate(async()=>{
   window.__qaContext={device:'Kombi',brand:'Vaillant',model:'',model_id:'',code:'',step:4};window.__qaRecords=[];
   window.STUstaWizard={getContext:()=>({...window.__qaContext})};window.STDiagnosticGuide=()=>({source:'guide',text:'Sentetik ilk bilgi.'});window.stRecordAIResult=data=>window.__qaRecords.push(data);
   document.getElementById('deviceSelect').value='Kombi';document.getElementById('issueInput').value='İlk sentetik soru';document.getElementById('askBtn').disabled=false;
   window.stApi=()=>new Promise(resolve=>window.__qaResolve=resolve);window.__qaPending=window.diagnoseIssue();
   window.__qaContext.brand='ECA';document.getElementById('issueInput').value='Değişen sentetik soru';window.__qaResolve({source:'ai',text:'ESKİ YANIT GÖSTERİLMEMELİ'});await window.__qaPending;
  });
  check(!await page.locator('#aiResponseText').innerText().then(text=>text.includes('ESKİ YANIT'))&&(await page.evaluate(()=>window.__qaRecords.length))===0,'Changed input suppresses a stale AI result and its notification');
  check(errors.length===0&&server.errors.length===0,'Home entry/reviews journey has no browser or local static HTTP errors');
  report={passed:true,checks:checks.length,cases:checks,review_alignment:alignment,mocked_api:true,provider_requests:0,external_requests:external,page_errors:errors,build:JSON.parse(fs.readFileSync(path.join(directory,'build-info.json'),'utf8'))};
 }catch(error){report={passed:false,checks:checks.length,cases:checks,error:error.stack,page_errors:errors,server_errors:server.errors};process.exitCode=1;}
 finally{await browser.close();await server.close();}
 fs.mkdirSync(path.join(root,'build'),{recursive:true});fs.writeFileSync(path.join(root,'build/home-entry-reviews.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,checks:report.checks,error:report.error}));
})();
