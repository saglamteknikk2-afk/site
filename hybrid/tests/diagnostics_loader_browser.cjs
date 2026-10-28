'use strict';
// Local browser proof, including a click while model data is deliberately slow.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const http=require('node:http');
const {chromium}=require('playwright');
const directory=path.resolve(process.argv[2]);
const sources=['verified-faults.js','organic-catalog.js','model-directory.js'];
const type={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.json':'application/json','.svg':'image/svg+xml','.webp':'image/webp','.woff2':'font/woff2'};
const server=http.createServer((req,res)=>{
 let pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
 if(pathname.endsWith('/'))pathname+='index.html';
 const filename=path.join(directory,pathname);
 if(!filename.startsWith(directory+path.sep)){res.writeHead(403).end();return;}
 if(!fs.existsSync(filename)){res.writeHead(404).end();return;}
 res.setHeader('Content-Type',type[path.extname(filename)]||'application/octet-stream');res.end(fs.readFileSync(filename));
});
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port+'/';
 const launch={headless:true,args:['--no-sandbox']};
 if(process.env.CHROMIUM_PATH)launch.executablePath=process.env.CHROMIUM_PATH;
 else if(fs.existsSync('/usr/bin/chromium'))launch.executablePath='/usr/bin/chromium';
 const browser=await chromium.launch(launch);
 const page=await browser.newPage({viewport:{width:360,height:700}});
 const errors=[],requests=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',async route=>{
  const target=new URL(route.request().url());
  if(target.pathname.endsWith('.php')){await route.fulfill({status:200,contentType:'application/json',body:'{"ok":true,"reviews":[]}'});return;}
  const filename=path.basename(target.pathname);
  if(sources.includes(filename)){
   requests.push(filename);
   if(filename==='verified-faults.js')await new Promise(resolve=>setTimeout(resolve,1500));
  }
  await route.continue();
 });
 try{
  await page.goto(url,{waitUntil:'domcontentloaded'});
  await page.waitForTimeout(250);
  assert.deepEqual(requests,[],'No large diagnostic data download before interaction/visibility');
  assert.equal(await page.evaluate(()=>window.STDiagnostics.state),'idle');
  await page.locator('.at-header a.premium-ai-link').click();
  assert.equal(await page.locator('#aiUstaWizard').getAttribute('aria-busy'),'true');
  assert.equal(await page.evaluate(()=>window.STDiagnostics.state),'loading');
  assert.equal(await page.evaluate(()=>!!window.ST_VERIFIED_FAULTS),false);
  const ready=await page.evaluate(()=>window.STDiagnosticsReady);
  assert.equal(ready.ready,true);
  assert.deepEqual(requests,sources,'Data-only scripts load once in their original order');
  assert.equal(await page.evaluate(()=>window.STDiagnostics.state),'ready');
  assert.equal(await page.locator('#aiUstaWizard').getAttribute('aria-busy'),null);
  assert.equal(await page.evaluate(()=>window.STModelDirectory.list('kombi','Vaillant').length)>10,true);
  await page.locator('#aiUstaWizard [data-choice="Kombi"]').click();
  assert.equal(await page.evaluate(()=>window.STUstaWizard.getContext().device),'Kombi');
  assert.equal(errors.length,0,errors.join('\n'));
  const report={scope:'Real local Chromium; 1500 ms delayed first dataset; no provider submissions',
    data_requests:requests,initial_large_data_requests:0,ready:ready.ready,errors,
    vaillant_model_names:await page.evaluate(()=>window.STModelDirectory.list('kombi','Vaillant').length),
    device:await page.evaluate(()=>window.STUstaWizard.getContext().device)};
  const fallback=await browser.newPage({viewport:{width:360,height:700}});
  const fallbackErrors=[];fallback.on('pageerror',e=>fallbackErrors.push(e.message));
  await fallback.route('**/assets/verified-faults.js*',route=>route.abort('failed'));
  await fallback.route('**/*.php*',route=>route.fulfill({status:200,contentType:'application/json',body:'{"ok":true,"reviews":[]}'}));
  await fallback.goto(url,{waitUntil:'domcontentloaded'});
  await fallback.locator('.at-header a.premium-ai-link').click();
  const failed=await fallback.evaluate(()=>window.STDiagnosticsReady);
  assert.equal(failed.ready,false,'A failed dataset must resolve to the safe fallback');
  assert.equal(await fallback.locator('#aiUstaWizard').getAttribute('aria-busy'),null);
  await fallback.locator('#aiUstaWizard [data-choice="Kombi"]').click();
  assert.equal(await fallback.evaluate(()=>window.STUstaWizard.getContext().device),'Kombi');
  assert.equal(fallbackErrors.length,0);
  report.failed_resource_fallback={ready:false,device:'Kombi',errors:fallbackErrors};
  await fallback.close();
  if(process.argv[3])fs.writeFileSync(process.argv[3],JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
 } finally{await browser.close();server.close();}
})().catch(error=>{console.error(error);server.close();process.exitCode=1;});
