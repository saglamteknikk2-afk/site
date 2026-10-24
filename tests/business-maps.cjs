/* Optional real-DOM regression. Every browser request is handled in memory;
 * no business API, map service, notification or production config is contacted. */
'use strict';
const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
const assert=require('assert/strict');
(async()=>{
  const base=path.join(__dirname,'..');
  const markup=fs.readFileSync(path.join(base,'templates/business-maps-section.html'),'utf8');
  const script=fs.readFileSync(path.join(base,'overrides/assets/business-maps.js'),'utf8');
  const executablePath=process.env.CHROMIUM_BIN||(fs.existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined);
  const browser=await chromium.launch({headless:true,executablePath,args:['--no-sandbox']});
  let checks=0;
  const equal=(actual,expected,message)=>{checks++;assert.deepEqual(actual,expected,message);};
  try {
    async function scenario({windowPreview=false,bodyPreview=false,maps,mount='/'}) {
      const page=await browser.newPage();const api=[];const external=[];const errors=[];
      page.on('pageerror',error=>errors.push(error.message));
      await page.route('**/*',async route=>{
        const u=new URL(route.request().url());
        if(u.origin==='https://maps-test.invalid'&&u.pathname===mount)return route.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><html><head><meta charset="utf-8"><script>window.ST_PREVIEW='+windowPreview+'</script></head><body'+(bodyPreview?' data-st-mode="preview"':'')+'>'+markup+'<script>'+script+'</script></body></html>'});
        if(u.origin==='https://maps-test.invalid'&&u.pathname===mount+'api.php'){
          api.push(u.href);return route.fulfill({contentType:'application/json',body:JSON.stringify({ok:true,maps:maps||{}})});
        }
        external.push(u.href);return route.abort();
      });
      await page.goto('https://maps-test.invalid'+mount);
      if(windowPreview||bodyPreview){
        equal(api.length,0,'Preview must not contact even the sanitized API');
        equal(await page.locator('[data-map-link][href]').count(),2,'Preview keeps useful local navigation');
        equal(await page.locator('[data-map-link][aria-disabled="true"]').count(),0,'Local navigation is enabled without pretending maps are configured');
      }else{
        await page.waitForFunction(()=>document.querySelector('[data-business-maps]').getAttribute('aria-busy')==='false');
        equal(api.length,1,'Production fetches the single sanitized endpoint');
      }
      equal(external.length,0,'No external map request before explicit embed click');
      equal(errors,[],'No browser errors');
      return {page,api,external};
    }
    for(const preview of [{windowPreview:true},{bodyPreview:true}]){
      const {page}=await scenario(preview);await page.close();
    }
    const maps={google:{url:'https://www.google.com/maps/place/Test',embed_url:'https://www.google.com/maps/embed?pb=test'},yandex:{url:'https://yandex.com.tr/maps/org/123',embed_url:''}};
    const valid=await scenario({maps});
    equal(await valid.page.locator('.st-map-card.is-configured').count(),2,'Both validated provider links enabled');
    equal(await valid.page.locator('[data-map-provider="google"] [data-map-link]').getAttribute('rel'),'noopener noreferrer','New-tab link isolation');
    equal(await valid.page.locator('iframe').count(),0,'Embeds require consent click');
    await valid.page.locator('[data-map-provider="google"] [data-map-embed]').click();
    equal(await valid.page.locator('iframe').count(),1,'Explicit click creates one validated embed');
    equal(await valid.page.locator('iframe').getAttribute('src'),maps.google.embed_url,'Embed source stays the allowed URL');
    equal(await valid.page.locator('[data-map-provider="google"] [data-map-embed]').isHidden(),true,'Embed button is consumed');
    await valid.page.close();
    // Invalid Google host remains disabled while a valid Yandex link makes the
    // asynchronous completion observable without relying on an arbitrary sleep.
    const invalid=await scenario({maps:{google:{url:'https://www.google.com.evil.invalid/maps/place/Test',embed_url:'https://www.google.com/maps/embed?pb=test'},yandex:maps.yandex}});
    equal(await invalid.page.locator('[data-map-provider="google"] [data-map-link]').getAttribute('href'),'https://maps-test.invalid/bolgeler.html','Lookalike host falls back to real local area navigation');
    equal(await invalid.page.locator('[data-map-provider="google"] [data-map-embed]').isHidden(),true,'Rejected share URL cannot enable an embed');
    await invalid.page.close();
    const empty=await scenario({maps:{}});
    equal(await empty.page.locator('[data-map-provider="google"] [data-map-link]').getAttribute('href'),'https://maps-test.invalid/bolgeler.html','Unconfigured Google card opens regions');
    equal(await empty.page.locator('[data-map-provider="yandex"] [data-map-link]').getAttribute('href'),'https://maps-test.invalid/iletisim.html','Unconfigured Yandex card opens contact');
    equal(await empty.page.locator('iframe').count(),0,'Unconfigured maps cannot create embeds');
    equal(await empty.page.getByText('Konum bağlantısı yakında').count(),0,'Passive placeholder removed');
    await empty.page.close();
    const mounted=await scenario({maps,mount:'/site/'});
    equal(mounted.api[0],'https://maps-test.invalid/site/api.php?action=business-maps','API remains inside deployment mount');
    equal(await mounted.page.locator('.st-map-card.is-configured').count(),2,'Configured maps work in a deployment subdirectory');
    await mounted.page.close();
    process.stdout.write(JSON.stringify({checks,errors:0,real_network_requests:0})+'\n');
  } finally {await browser.close();}
})().catch(error=>{process.stderr.write(error.stack+'\n');process.exitCode=1;});
