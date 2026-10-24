/* Actual browser navigation through the recorded editorial links. Local files only. */
'use strict';
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const root=path.resolve(process.env.SAGLAM_BUILD||path.join(__dirname,'../_site'));
const inventory=JSON.parse(fs.readFileSync(path.join(__dirname,'../docs/editorial-link-targets.json'),'utf8'));
const origin='https://editorial-preview.test';
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.woff2':'font/woff2','.ttf':'font/ttf'};
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']});
 const results=[],blocked=[],errors=[];
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce',serviceWorkers:'block'});
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>{
   const u=new URL(route.request().url());
   if(u.origin!==origin||!u.pathname.startsWith('/site/')||u.pathname.endsWith('.php')){blocked.push(u.href);return route.abort();}
   const file=path.resolve(root,decodeURIComponent(u.pathname.slice('/site/'.length))||'index.html');
   if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile())return route.fulfill({status:404,body:'Missing local fixture'});
   return route.fulfill({path:file,contentType:mime[path.extname(file)]||'application/octet-stream'});
  });
  for(const record of inventory.links){
   await page.goto(origin+'/site/'+record.source,{waitUntil:'domcontentloaded'});
   const href='/site'+record.href;
   const index=await page.locator('main a[href]').evaluateAll((links,expected)=>links.findIndex(a=>a.getAttribute('href')===expected),href);
   assert.ok(index>=0,record.source+' contains '+href);
   const link=page.locator('main a[href]').nth(index),details=link.locator('xpath=ancestor::details');
   for(const item of await details.all())if(await item.evaluate(el=>!el.open))await item.locator(':scope > summary').click();
   await Promise.all([page.waitForURL(origin+href),link.click()]);
   await page.waitForLoadState('domcontentloaded');
   assert.ok(await page.locator('h1').isVisible(),record.href+' shows its page heading');
   if(record.kind==='model'){
    await page.waitForFunction(()=>document.querySelector('#modelScopeNote')?.textContent.includes('Seçilen model:'));
    assert.ok((await page.locator('#modelScopeNote').innerText()).includes(record.model_name),'Exact selected model '+record.model_name);
    assert.ok(await page.locator('#kodlar').isVisible(),'Code table anchor visible');
    assert.equal(new URL(page.url()).searchParams.has('scope_confirmed'),false,'Selection never confirms scope');
    if(record.requires_scope_confirmation||record.matchable===false){
     const note=await page.locator('#modelScopeNote').innerText();
     assert.match(note,/ülke|belge numarası|son eki/,'Country/document warning stays visible');
     const model=await page.evaluate(id=>window.ST_VERIFIED_FAULTS.models.find(m=>m.id===id),record.model_id);
     assert.ok(model.requires_scope_confirmation||model.matchable===false,'Source scope restriction retained');
    }
   }else if(record.kind==='model_hub'){
    await page.waitForFunction(()=>window.STModelBrowser);
    assert.equal(await page.locator('[data-device-filter="kombi"]').getAttribute('aria-pressed'),'true','Boiler filter active');
   }
   results.push({source:record.source,href:record.href,kind:record.kind,passed:true});
  }
  assert.deepEqual(blocked,[],'No PHP or external service requests');assert.deepEqual(errors,[],'No browser errors');
 }finally{await browser.close();}
 const report={passed:true,links:results.length,sources:inventory.sources.length,blocked,errors,results};
 const output=path.join(__dirname,'../build/editorial-links-browser.json');fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
 process.stdout.write(JSON.stringify({passed:report.passed,links:report.links,sources:report.sources,blocked,errors})+'\n');
})().catch(e=>{process.stderr.write(e.stack+'\n');process.exitCode=1;});
