'use strict';
// Real mobile DOM/selection checks. No provider submissions or live index claims.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
(async()=>{
 const base=process.argv[2],origin=new URL(base).origin;
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage']});
 const ctx=await browser.newContext({viewport:{width:360,height:800},reducedMotion:'reduce'});
 await ctx.route('**/*',r=>new URL(r.request().url()).origin===origin?r.continue():r.abort());
 const page=await ctx.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  const narratives=['combi-brands','clima-brands','symptoms'].flatMap(n=>JSON.parse(fs.readFileSync(path.join(__dirname,'../data/service-editorial',n+'.json'),'utf8')).pages);
  const brands=Object.fromEntries(narratives.filter(p=>p.type==='brand').map(p=>[p.route,p.brand]));
  for(const [route,brand] of Object.entries(brands)){
   await page.goto(new URL(route,base).href,{waitUntil:'networkidle'});
   await page.waitForFunction(()=>document.querySelector('[data-matrix-controls]')?.hidden===false);
   assert.equal((await page.locator('[data-field="brand"]').inputValue()).toLocaleLowerCase('tr'),brand.toLocaleLowerCase('tr'));
   assert.equal(await page.locator('[data-field="district"]').inputValue(),'');
   assert.equal(await page.locator('[data-field="model"]').inputValue(),'');
   assert.equal(await page.locator('.editorial-section').count(),3);
   await page.locator('[data-matrix-show]').click();
   assert((await page.locator('[data-matrix-result]').innerText()).toLocaleLowerCase('tr').includes(brand.toLocaleLowerCase('tr')));
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  }
  const matrix=await (await page.request.get(new URL('assets/hybrid-matrix-data.json',base).href)).json();
  for(const narrative of narratives.filter(p=>p.type==='symptom')){
   await page.goto(new URL(narrative.route,base).href,{waitUntil:'networkidle'});
   await page.waitForFunction(()=>document.querySelector('[data-matrix-controls]')?.hidden===false);
   const selected=await page.locator('[data-field="need"]').inputValue();
   const kind=await page.locator('[data-field="device"]').inputValue();
   assert.equal(matrix.devices[kind].needs.find(n=>n.name===selected)?.path,narrative.route,narrative.route+' has wrong initial intent');
   assert.equal(await page.locator('[data-field="model"]').inputValue(),'');
  }
  await page.goto(new URL('kombi-su-akitiyor.html',base).href,{waitUntil:'networkidle'});
  await page.waitForFunction(()=>document.querySelector('[data-matrix-controls]')?.hidden===false);
  assert((await page.locator('[data-field="need"]').inputValue()).includes('su'));
  await page.locator('[data-field="brand"]').selectOption('Baymak');
  await page.locator('[data-hybrid-matrix] summary').filter({hasText:'Model veya hata kodu'}).click();
  await page.locator('[data-field="model"]').selectOption('baymak-kombi-duotec-33-42-45');
  await page.locator('[data-field="code"]').fill('E1');
  await page.locator('[data-hybrid-matrix] summary').filter({hasText:'İlçe veya mahalle'}).click();
  await page.locator('[data-field="district"]').selectOption('Küçükçekmece');
  await page.locator('[data-field="neighborhood"]').selectOption('Atakent');
  await page.locator('[data-matrix-show]').click();
  await page.locator('[data-matrix-result] a').filter({hasText:'Bu bilgilerle servis talebi'}).click();
  await page.waitForURL(/servis-sec\.html#/);
  assert((await page.locator('#svcModel').inputValue()).includes('Duotec'));
  assert((await page.locator('#svcModel').inputValue()).includes('E1'));
  assert.equal(await page.locator('#svcDistrict').inputValue(),'Küçükçekmece');
  assert.equal(await page.locator('#svcNeighborhood').inputValue(),'Atakent');
  assert((await page.locator('#svcSymptom').inputValue()).includes('su'));
  await page.goto(new URL('dizin-inceleme.html',base).href,{waitUntil:'networkidle'});
  assert.equal(await page.locator('[data-index-row]').count(),123);
  for(const [status,count] of [['not_indexed',64],['indexed',44],['parameter',15]]){
   await page.locator('#indexStatus').selectOption(status);
   assert.equal(await page.locator('[data-index-row]:visible').count(),count);
  }
  await page.locator('#indexStatus').selectOption('');await page.locator('#indexSearch').fill('Regal');
  assert.equal(await page.locator('[data-index-row]:visible').count(),1);
  await page.locator('#indexOpen').click();assert.equal(await page.locator('[data-index-row][open]').count(),1);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.equal(errors.length,0,errors.join('; '));
  const result={scope:'Actual local Chromium, mobile; no external/provider submission',brand_preselection_pages:16,model_optional:true,symptom_preselection_pages:13,model_code_location_survive_service_handoff:true,report_rows:123,report_filters:[64,44,15],mobile_no_overflow:true,errors};
  if(process.argv[3])fs.writeFileSync(process.argv[3],JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
 }finally{await ctx.close();await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
