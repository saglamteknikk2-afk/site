/* Optional browser regression: node tests/preview-guard.cjs (Playwright required).
 * All requests are fulfilled/aborted in memory; no real endpoint is contacted. */
'use strict';
const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
const assert=require('assert/strict');
(async()=>{
  const executablePath=process.env.CHROMIUM_BIN||(fs.existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined);
  const browser=await chromium.launch({headless:true,executablePath,args:['--no-sandbox']});
  try {
    const page=await browser.newPage();const contacted=[];const errors=[];
    const guard=fs.readFileSync(path.join(__dirname,'../scripts/preview-guard.js'),'utf8');
    await page.route('**/*',async route=>{
      const u=new URL(route.request().url());
      if(u.origin==='https://preview.test'&&u.pathname==='/site/')return route.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><html><head><meta charset="utf-8"><script src="/site/assets/preview-guard.js"></script></head><body><form id="send"><input name="name" value="Deneme"><button type="submit">Gönder</button></form><a id="wa" href="https://wa.me/905346225515" target="_blank">WhatsApp</a><script>window.appSawPreview=window.ST_PREVIEW;</script></body></html>'});
      if(u.origin==='https://preview.test'&&u.pathname==='/site/assets/preview-guard.js')return route.fulfill({contentType:'text/javascript',body:guard});
      if(u.origin==='https://preview.test'&&u.pathname==='/site/data.json')return route.fulfill({contentType:'application/json',body:'{"local":true}'});
      contacted.push(route.request().url());return route.abort();
    });
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('https://preview.test/site/');
    assert.equal(await page.evaluate(()=>window.appSawPreview),true,'Guard must precede application code');
    assert.deepEqual(await page.evaluate(async()=>fetch('/site/data.json').then(r=>r.json())),{local:true},'Local read-only dataset remains usable');
    for(const target of ['/site/api.php?action=bootstrap','https://api.example.test/send']) {
      assert.equal(await page.evaluate(async target=>{try{await fetch(target);return false}catch(e){return e.code==='PREVIEW_DISABLED'}},target),true,'Disallowed fetch fails truthfully');
    }
    assert.equal(await page.evaluate(async()=>{try{await fetch('/site/data.json',{method:'POST',body:'data'});return false}catch(e){return e.code==='PREVIEW_DISABLED'}}),true,'POST blocked even to local non-PHP URL');
    assert.equal(await page.evaluate(()=>{try{const x=new XMLHttpRequest();x.open('POST','/site/api.php');x.send('data');return false}catch(e){return e.message.includes('kaydedilmedi')}}),true,'XHR cannot send');
    assert.equal(await page.evaluate(()=>navigator.sendBeacon('/site/api.php','data')),false,'Beacon cannot send');
    await page.locator('#send button').click();
    assert.match(await page.locator('[data-preview-status]').textContent(),/kaydedilmedi.*gönderilmedi/);
    assert.equal(await page.locator('#send input').inputValue(),'Deneme','Form values remain for inspection');
    await page.evaluate(()=>document.querySelector('#send').submit());
    assert.equal(await page.locator('[data-preview-status]').count(),1,'Native submit is also denied');
    assert.equal(await page.evaluate(()=>new Promise(resolve=>navigator.geolocation.getCurrentPosition(()=>resolve(false),e=>resolve(e.code===1)))),true,'No geolocation prompt or position read');
    await page.locator('#wa').click();assert.equal(page.url(),'https://preview.test/site/','Messaging target is inert');
    assert.deepEqual(contacted,[],'No network side effects');assert.deepEqual(errors,[],'No browser errors');
    const report={passed:true,assertions:15,network_side_effects:contacted,browser_errors:errors};
    const out=path.join(__dirname,'../build/preview-guard-report.json');fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');process.stdout.write(JSON.stringify(report)+'\n');
  } finally {await browser.close();}
})().catch(e=>{process.stderr.write(e.stack+'\n');process.exitCode=1;});
