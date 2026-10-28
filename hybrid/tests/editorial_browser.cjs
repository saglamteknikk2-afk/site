'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require('playwright');
(async()=>{
 const base=process.argv[2],report=process.argv[3];
 if(!base)throw new Error('Provide a local preview URL');
 const options={headless:true,args:['--no-sandbox','--disable-dev-shm-usage']};
 if(process.env.CHROMIUM_PATH)options.executablePath=process.env.CHROMIUM_PATH;
 else if(fs.existsSync('/usr/bin/chromium'))options.executablePath='/usr/bin/chromium';
 const browser=await chromium.launch(options);
 const context=await browser.newContext({viewport:{width:360,height:800},reducedMotion:'reduce'});
 const origin=new URL(base).origin;
 await context.route('**/*',r=>new URL(r.request().url()).origin===origin?r.continue():r.abort());
 const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  const cases=['avcilar-kombi-servisi.html','kucukcekmece-kombi-servisi.html','fatih-kombi-servisi.html','sariyer-klima-servisi.html','esenyurt-klima-servisi.html'];
  const bodies=[];
  for(const route of cases){
   await page.goto(new URL(route,base).href,{waitUntil:'networkidle'});
   assert.equal(await page.locator('.at-summary,[data-st-master-matrix],.hybrid-region-note').count(),0,route+' retains old shared prose');
   assert.equal(await page.locator('.editorial-body').count(),1);
   assert.equal(await page.locator('.editorial-section').count(),3);
   assert.equal(await page.locator('.editorial-faq details').count(),2);
   bodies.push(await page.locator('.editorial-body').innerText());
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),route+' overflow');
   const first=page.locator('.editorial-aside .at-toc a').first(),href=await first.getAttribute('href');
   await first.click();assert.equal(new URL(page.url()).hash,href);
   assert(await page.locator(href).count(),route+' sidebar target missing');
  }
  assert.equal(new Set(bodies).size,cases.length);
  await page.goto(new URL('kucukcekmece-kombi-servisi.html',base).href,{waitUntil:'networkidle'});
  await page.waitForFunction(()=>document.querySelector('[data-matrix-controls]')?.hidden===false);
  await page.locator('#mahalle-atakent a').click();
  await page.waitForFunction(()=>document.querySelector('[data-field="neighborhood"]').value==='Atakent');
  const noScript=await browser.newContext({javaScriptEnabled:false,viewport:{width:360,height:800}});
  const staticPage=await noScript.newPage();
  await staticPage.goto(new URL('fatih-kombi-servisi.html',base).href,{waitUntil:'load'});
  assert.equal(await staticPage.locator('.editorial-section').count(),3);
  assert((await staticPage.locator('.editorial-body').innerText()).includes('187'));
  await noScript.close();
  await page.goto(new URL('icerik-inceleme.html',base).href,{waitUntil:'networkidle'});
  assert.equal(await page.locator('[data-review-row]').count(),55);
  await page.locator('#reviewSearch').fill('Küçükçekmece');
  assert.equal(await page.locator('[data-review-row]:visible').count(),2);
  await page.locator('#reviewOpen').click();
  assert.equal(await page.locator('[data-review-row][open]').count(),2);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'comparison page overflow');
  assert.equal(errors.length,0,errors.join('; '));
  const evidence={scope:'Actual local Chromium editorial DOM, navigation and no-JavaScript fallback; no provider submission',five_representative_bodies_distinct:true,shared_summaries_absent:true,sidebar_targets:true,same_page_neighborhood_selection:true,static_content_without_javascript:true,comparison_rows:55,comparison_search_and_open:true,mobile_no_overflow:true,errors};
  if(report)fs.writeFileSync(report,JSON.stringify(evidence,null,2)+'\n');console.log(JSON.stringify(evidence,null,2));
 }finally{await context.close();await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
