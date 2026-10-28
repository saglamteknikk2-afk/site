'use strict';
// Actual DOM checks of the optional region selector. No provider/form submissions.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require('playwright');
(async()=>{
 const base=process.argv[2]||'http://127.0.0.1:8766/preview/';
 const origin=new URL(base).origin;
 const options={headless:true,args:['--no-sandbox','--disable-dev-shm-usage']};
 if(process.env.CHROMIUM_PATH)options.executablePath=process.env.CHROMIUM_PATH;
 else if(fs.existsSync('/usr/bin/chromium'))options.executablePath='/usr/bin/chromium';
 const browser=await chromium.launch(options);const context=await browser.newContext({viewport:{width:360,height:800},reducedMotion:'reduce'});
 await context.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(new URL('avcilar-kombi-servisi.html',base).href,{waitUntil:'networkidle'});
  await page.waitForFunction(()=>{const el=document.querySelector('[data-matrix-controls]');return el&&!el.hidden;});
  const root=page.locator('[data-hybrid-matrix]');const field=n=>root.locator('[data-field="'+n+'"]');
  assert.equal(await field('model').inputValue(),'');assert.equal(await field('brand').inputValue(),'');
  assert.equal(await field('brand').locator('option').count(),36,'all35combi brands plusunknown');
  assert.equal(await field('district').locator('option').count(),26,'all25districts plusunknown');
  assert.equal(await root.locator('[data-custom-model-label]').isVisible(),false);
  await root.locator('[data-matrix-show]').click();
  const result=root.locator('[data-matrix-result]');await result.waitFor({state:'visible'});
  assert.equal(await result.locator('.hybrid-actions a').first().getAttribute('href'),'avcilar-kombi-servisi.html#bolge-rehberi');
  await field('brand').selectOption('Baymak');assert.equal(await field('model').inputValue(),'');
  await root.locator('[data-matrix-show]').click();assert.match(await result.textContent(),/Baymak/);
  assert.equal(await result.locator('.hybrid-actions a').first().getAttribute('href'),'avcilar-kombi-servisi.html#bolge-rehberi');
  await root.locator('summary').filter({hasText:'Model veya hata kodu'}).click();
  await field('model').selectOption('baymak-kombi-duotec-33-42-45');await field('code').fill('E1');
  await root.locator('[data-matrix-show]').click();assert.equal(await result.locator('.hybrid-actions a').first().getAttribute('href'),'baymak-kombi-duotec-33-42-45-ariza-kodlari.html#kod-e01');
  await field('model').selectOption('');await field('code').fill('E99');await root.locator('[data-matrix-show]').click();
  assert.match(await result.textContent(),/tam model gerekir/);assert.doesNotMatch(await result.textContent(),/elektronik kart arızası/i);
  await field('model').selectOption('__custom');await field('customModel').fill('Listede olmayan eski model');await root.locator('[data-matrix-show]').click();
  assert.match(await result.textContent(),/Listede olmayan eski model/);
  await root.locator('summary').filter({hasText:'İlçe veya mahalleyi'}).click();
  await field('district').selectOption('Küçükçekmece');await field('neighborhood').selectOption('Atakent');
  await root.locator('[data-matrix-reset]').click();assert.equal(await field('district').inputValue(),'Avcılar');assert.equal(await field('model').inputValue(),'');assert.equal(await field('code').inputValue(),'');
  await field('device').selectOption('klima');assert.equal(await field('brand').locator('option').count(),38,'all37climatebrands plusunknown');assert.equal(await field('model').inputValue(),'');assert.equal(await field('code').inputValue(),'');await field('brand').selectOption('Baymak');await root.locator('[data-matrix-show]').click();assert.equal(await result.locator('.hybrid-actions a').first().getAttribute('href'),'avcilar-klima-servisi.html#bolge-rehberi');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await field('brand').focus();await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement?.dataset?.field),'need');
  // Region search must open the district content anchor rather than a blank form.
  await page.goto(new URL('bolgeler.html',base).href,{waitUntil:'networkidle'});
  await page.locator('#regionQuery').fill('Küçükçekmece Atakent klima');await page.locator('#regionQuery').press('Enter');
  await page.waitForURL(/kucukcekmece-klima-servisi\.html#mahalle-atakent/);
  assert.equal(await page.locator('#mahalle-atakent').count(),1);
  // Failure to fetch enhancement data must leave useful static content and links.
  const fallback=await context.newPage();await fallback.route('**/hybrid-matrix-data.json',r=>r.abort());await fallback.goto(new URL('avcilar-kombi-servisi.html',base).href,{waitUntil:'networkidle'});assert.equal(await fallback.locator('[data-matrix-controls]').isVisible(),false);assert(await fallback.locator('.hybrid-bridges a[href]').count()>0);assert(await fallback.locator('[id^=mahalle-]').count()>0);await fallback.close();
  assert.equal(errors.length,0,errors.join('; '));
  const report={scope:'Local Chromium selectors and navigation only; no provider/form delivery',optional_fields:true,combi_brand_options:35,district_options:25,known_model_code_route:true,unknown_model_code_not_guessed:true,custom_model_optional:true,reset_and_keyboard:true,mobile_360_no_document_overflow:true,regionfinder_climate_content_anchor:true,cross_device_resets_model_and_code:true,climate_brand_options:37,failed_enhancement_keeps_static_content:true,errors};
  if(process.argv[3])fs.writeFileSync(process.argv[3],JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
 }finally{await context.close();await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
