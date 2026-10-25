'use strict';
// Focused browser regression for brand-only error-code questions. No provider is called.
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
const {startServer}=require('./interaction_http.cjs');
const directory=path.resolve(process.argv[2]||'build/qa-model-guidance/preview');
const base=(process.argv[3]||'').replace(/\/$/,'');
const artifact=path.resolve(process.env.ST_TEST_ARTIFACT_DIR||'build/qa-model-guidance/evidence');
(async()=>{
 fs.mkdirSync(artifact,{recursive:true});
 const server=await startServer(directory,base);
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const errors=[],checks=[];let providerRequests=0,apiRequests=0;
 const check=(name,value)=>{checks.push({name,pass:!!value});if(!value)throw Error(name);};
 page.on('pageerror',error=>errors.push(error.message));
 await page.route('**/*',route=>{
  const url=new URL(route.request().url());
  if(url.hostname!=='127.0.0.1'){providerRequests++;return route.abort();}
  if(url.pathname.endsWith('.php')){apiRequests++;return route.fulfill({contentType:'application/json',body:'{"ok":true,"reviews":[]}'});}
  return route.continue();
 });
 const context=()=>page.evaluate(()=>STUstaWizard.getContext());
 const start=async(brand='ECA',code='e99')=>{
  await page.click('#ustaRestart');
  await page.locator('[data-choice=Kombi]').click();
  await page.locator('[data-choice=error]').click();
  await page.selectOption('#ustaBrand',brand);
  await page.fill('#ustaCode',code);
 };
 try{
  await page.goto(server.origin+base+'/');await page.waitForFunction(()=>window.STUstaWizard&&window.STFaults);
  await start();
  check('ECA exact models appear in one selector',await page.locator('#ustaVerifiedModel option').count()>=4&&await page.locator('#ustaModelChoices').count()===0);
  check('manual model field stays closed until requested',await page.locator('#ustaModel:visible').count()===0&&await page.locator('#ustaWriteModel').isVisible());
  await page.click('#ustaNext');
  check('E99 cannot silently complete without a model',(await context()).step===3&&!await page.locator('#aiResultBox').isVisible());
  check('model prompt keeps the entered code',(await page.locator('#ustaModelPrompt').innerText()).includes('e99')&&await page.inputValue('#ustaCode')==='e99');
  check('no extra brand or search field in the model question',await page.locator('#ustaStep input[type=search],#ustaBrand').count()===0);
  await page.selectOption('#ustaVerifiedModel','eca-kombi-proteus-premix-hm-tr|Proteus Premix 24 HM');
  check('exact model selection retains the raw E99 code',(await context()).model==='Proteus Premix 24 HM'&&(await context()).code==='e99');
  check('code suggestions and manufacturer scope open after the exact model',await page.locator('#ustaStep datalist option').count()>0&&await page.locator('#ustaModelScope').isVisible());
  check('model and code do not have duplicate chooser widgets',await page.locator('#ustaModelChoices,#ustaCodeSelect,[data-fault-code]').count()===0);
  check('primary action describes finding the fault',/Arızamı bul/.test(await page.locator('#ustaNext').innerText()));
  await page.click('#ustaNext');
  check('exact model continues to a local source-aware guide',(await context()).step===4&&await page.locator('#aiResultBox').isVisible());
  await page.evaluate(()=>{window.__modelTestAI=0;window.diagnoseIssue=()=>window.__modelTestAI++;window.ST_PREVIEW=false;});
  await page.click('#askBtn');
  // A model is present here; the explicit AI button may use the existing diagnosis path.
  check('exact-model explicit AI path remains available',await page.evaluate(()=>window.__modelTestAI===1));
  await start();await page.click('#ustaNext');await page.locator('[data-unknown-code]').click();
  check('explicit unknown model can finish without an endless question',(await context()).step===4&&(await context()).model_unknown&&!((await context()).model_id));
  const unknownText=await page.locator('#aiResponseText').innerText();
  check('unknown-model guidance does not claim a board fault',!/elektronik kart|başlangıç iletişim|E1\/E01|F4\/F04|E10 farklı/i.test(unknownText));
  check('unknown-model guidance requests the model label',/etiket|model/i.test(unknownText));
  await page.click('#askBtn');
  check('unknown-model code never starts an unscoped AI request',await page.evaluate(()=>window.__modelTestAI===1));
  await page.locator('#aiUstaWizard').screenshot({path:path.join(artifact,'eca-e99-unknown-model-mobile.png')});
  await page.evaluate(()=>STUstaWizard.requestModel());
  check('model selection can be reopened without losing the code',(await context()).step===3&&!(await context()).model_unknown&&await page.inputValue('#ustaCode')==='e99');
  await page.locator('#aiUstaWizard').screenshot({path:path.join(artifact,'eca-e99-model-selection-mobile.png')});
  await page.click('#ustaWriteModel');await page.fill('#ustaModel','Proteus Premix etiketteki sürüm');
  check('typing an unlisted model preserves the reported code',await page.inputValue('#ustaCode')==='e99');
  await page.click('#ustaNext');
  check('unlisted model continues without borrowing a documented model',(await context()).step===4&&!(await context()).model_id&&(await context()).model_unknown);
  check('unlisted model keeps its text and reaches honest guidance',(await context()).model.includes('Proteus Premix')&&await page.locator('#aiResultBox').isVisible()&&await page.locator('#aiSource').innerText()!=='Seçilen modelin üretici belgesi');
  await start('Isısan','E99');await page.click('#ustaNext');await page.locator('[data-unknown-code]').click();
  check('Isısan never borrows ECA or another brand model',(await context()).brand==='Isısan'&&!(await context()).model_id&&(await context()).step===4);
  await page.click('#ustaRestart');await page.locator('[data-choice=Kombi]').click();await page.locator('[data-choice=water]').click();await page.selectOption('#ustaBrand','ECA');await page.click('#ustaNext');
  check('symptom-only guidance does not force exact model selection',(await context()).step===4&&!((await context()).model_id));
  await page.evaluate(()=>STUstaWizard.requestModel());await page.fill('#ustaCode','e99');await page.click('#ustaNext');
  for(const width of [375,768,1440]){
   await page.setViewportSize({width,height:900});
   check(width+'px model choices fit the screen',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  }
  check('no JavaScript errors',errors.length===0);
  check('no local static files missing',server.errors.length===0);
  check('no real backend requests in the preview',apiRequests===0);
  const result={checks,errors,serverErrors:server.errors,APIRequests:apiRequests,blockedExternalRequests:providerRequests};
  fs.writeFileSync(path.join(artifact,'model-guidance.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify(result,null,2));
 }finally{await browser.close();await server.close();}
})().catch(error=>{console.error(error);process.exit(1);});
