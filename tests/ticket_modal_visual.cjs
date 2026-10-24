/* Real local HTTP and Chromium. Geometry/style regression, no live APIs. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {startServer}=require('./interaction_http.cjs');
const root=path.resolve(__dirname,'..'),output=path.resolve(process.env.MODAL_OUTPUT||path.join(root,'build/qa-ticket-modal'));
const builds=process.env.MODAL_CASES?JSON.parse(process.env.MODAL_CASES):[
 {label:'preview',directory:path.join(root,'_site'),base:'/site'},
 {label:'production',directory:path.join(root,'build/production'),base:''}
];
const sizes=[{width:320,height:780},{width:390,height:844},{width:768,height:960},{width:1440,height:1000},{width:1920,height:1080}];
const transparent=value=>value==='transparent'||value==='rgba(0, 0, 0, 0)';
async function run(browser,entry){
 const directory=path.resolve(entry.directory),base=entry.base.replace(/\/$/,''),start=JSON.parse(fs.readFileSync(path.join(directory,'build-info.json'),'utf8'));
 const server=await startServer(directory,base),records=[],errors=[],pageErrors=[],httpErrors=[],apiRequests=[];
 try{
  for(const size of sizes){
   const context=await browser.newContext({viewport:size,reducedMotion:'reduce',serviceWorkers:'block'});
   await context.route('**/*',route=>{
    const request=route.request(),url=new URL(request.url());
    if(url.origin!==server.origin)return route.abort();
    if(/\.php$/.test(url.pathname)){
     const action=url.searchParams.get('action');apiRequests.push({action,method:request.method(),path:url.pathname});
     return route.fulfill({contentType:'application/json',body:JSON.stringify(action==='bootstrap'?{ok:true,csrf:'1700000000.'+'a'.repeat(64)}:action==='reviews'?{ok:true,reviews:[]}:{ok:true,recorded:true})});
    }
    return route.continue();
   });
   const page=await context.newPage();page.on('pageerror',error=>pageErrors.push({size,error:error.message}));page.on('response',response=>{if(response.status()>=400)httpErrors.push({url:response.url(),status:response.status()});});
   try{
    await page.goto(server.origin+base+'/',{waitUntil:'networkidle'});await page.evaluate(()=>document.fonts.ready);
    const modal=page.locator('#serviceTicketModal'),card=modal.locator('.ah-modal-card');
    assert(await modal.isHidden(),'Closed modal must not appear in document flow');
    for(const selector of ['.usta-ticket','.p-service-cta [data-ticket-open]']){
     const opener=page.locator(selector);await opener.scrollIntoViewIfNeeded();
     const before=await page.evaluate(()=>({height:document.documentElement.scrollHeight,y:scrollY}));
     await opener.click();assert(await modal.isVisible(),'Actual service button opens the dialog');
     const facts=await page.evaluate(()=>{
      const modal=document.getElementById('serviceTicketModal'),card=modal.querySelector('.ah-modal-card'),rect=element=>{const r=element.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom};};
      const ms=getComputedStyle(modal),cs=getComputedStyle(card),body=getComputedStyle(document.body),close=card.querySelector('.ah-modal-close'),submit=card.querySelector('#ticketSubmitBtn');
      return {modal:rect(modal),card:rect(card),position:ms.position,z:Number(ms.zIndex),overlay:ms.backgroundColor,cardBackground:cs.backgroundColor,padding:parseFloat(cs.paddingLeft),overflow:cs.overflowY,cardClient:card.clientHeight,cardScroll:card.scrollHeight,bodyOverflow:body.overflow,bodyOverflowY:body.overflowY,documentWidth:document.documentElement.scrollWidth,documentHeight:document.documentElement.scrollHeight,focus:document.activeElement.id,close:rect(close),closePosition:getComputedStyle(close).position,submitBackground:getComputedStyle(submit).backgroundColor,headerZ:Number(getComputedStyle(document.querySelector('header')).zIndex)||0,fields:[...card.querySelectorAll('input:not([type=hidden]),select,textarea')].filter(e=>e.offsetParent!==null&&!e.closest('.st-honey')).map(e=>({id:e.id,...rect(e),padding:parseFloat(getComputedStyle(e).paddingLeft)}))};
     });
     assert.equal(facts.position,'fixed','Dialog must be fixed, never inline content');
     assert(Math.abs(facts.modal.x)<=1&&Math.abs(facts.modal.y)<=1,'Overlay starts at viewport origin');
     assert(Math.abs(facts.modal.width-size.width)<=2&&Math.abs(facts.modal.height-size.height)<=2,'Overlay fills viewport');
     assert(facts.z>facts.headerZ&&facts.z>=1000,'Dialog layers above navigation');
     assert(!transparent(facts.overlay)&&!transparent(facts.cardBackground),'Backdrop and card have visible backgrounds');
     assert(facts.padding>=16,'Card has actual layout padding');
     assert(facts.card.width>=Math.min(260,size.width-24)&&facts.card.width<=Math.min(640,size.width),'Card uses responsive bounded width');
     assert(facts.card.x>=7&&facts.card.right<=size.width-7&&facts.card.y>=7&&facts.card.bottom<=size.height-7,'Card fits viewport margins');
     assert(['auto','scroll'].includes(facts.overflow),'Long form scrolls inside the card');
     assert(facts.bodyOverflow==='hidden'||facts.bodyOverflowY==='hidden','Background page scroll is locked');
     assert(facts.documentWidth<=size.width+1,'No horizontal page overflow');
     assert(Math.abs(facts.documentHeight-before.height)<=2,'Opening dialog adds no document-flow height');
     assert.equal(facts.focus,'ticketName','Opening focuses the name field');
     assert(facts.close.width>=32&&facts.close.height>=32&&facts.close.y>=facts.card.y&&facts.close.bottom<=facts.card.bottom,'Close control is visible and has a usable target');
     assert(!transparent(facts.submitBackground),'Submit has a styled button background');
     for(const field of facts.fields){assert(field.width>=100&&field.x>=facts.card.x&&field.right<=facts.card.right+1,field.id+' stays inside the card');assert(field.padding>=8,field.id+' has field styling');}
     const trap=await page.evaluate(()=>{
      const items=[...document.querySelector('#serviceTicketModal').querySelectorAll('button,a[href],input,select,textarea')].filter(e=>e.offsetParent!==null&&!e.disabled&&e.tabIndex!==-1);items.at(-1).focus();return {first:items[0].outerHTML,last:items.at(-1).outerHTML};
     });
     await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.outerHTML),trap.first,'Tab loops to the first dialog control');
     await page.keyboard.press('Shift+Tab');assert.equal(await page.evaluate(()=>document.activeElement.outerHTML),trap.last,'Shift+Tab loops to the last dialog control');
     await card.evaluate(e=>e.scrollTop=0);
     if(selector==='.usta-ticket'&&[390,1440].includes(size.width))await page.screenshot({path:path.join(output,`${entry.label}-${size.width}.png`),animations:'disabled'});
     await page.keyboard.press('Escape');assert(await modal.isHidden(),'Escape closes dialog');
     assert(await opener.evaluate(e=>e===document.activeElement),'Closing restores opener focus');
     assert(!(await page.evaluate(()=>document.body.classList.contains('ah-dialog-open'))),'Closing releases page scroll lock');
     await opener.click();await modal.locator('.ah-modal-close').click();assert(await modal.isHidden(),'Close button actually closes dialog');
     records.push({size,opener:selector,passed:true,...facts});
    }
    // Short viewports must keep the form usable and reopen at the beginning.
    if(size.width===390){
     await page.setViewportSize({width:390,height:560});await page.locator('.usta-ticket').click();
     assert(await card.evaluate(e=>e.scrollHeight>e.clientHeight),'Short viewport has internal form scrolling');
     await card.evaluate(e=>e.scrollTop=e.scrollHeight);assert(await card.evaluate(e=>e.scrollTop>0),'Form can be scrolled to its lower controls');
     await page.keyboard.press('Escape');await page.locator('.usta-ticket').click();
     assert.equal(await card.evaluate(e=>e.scrollTop),0,'Reopening starts at the top instead of the previous bottom');
     await page.keyboard.press('Escape');
    }
   }catch(error){errors.push({size,error:error.stack});}finally{await context.close();}
  }
 }finally{await server.close();}
 const end=JSON.parse(fs.readFileSync(path.join(directory,'build-info.json'),'utf8'));
 return {label:entry.label,passed:records.length===10&&!errors.length&&!pageErrors.length&&!httpErrors.length&&start.content_sha256===end.content_sha256,build_start:start,build_end:end,actual_button_cases:records.length,errors,page_errors:pageErrors,http_errors:httpErrors,synthetic_api_requests:apiRequests,records};
}
(async()=>{
 fs.mkdirSync(output,{recursive:true});const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']}),reports=[];
 try{for(const entry of builds){const report=await run(browser,entry);reports.push(report);fs.writeFileSync(path.join(output,'modal-'+entry.label+'.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({label:entry.label,passed:report.passed,actual_button_cases:report.actual_button_cases,errors:report.errors,page_errors:report.page_errors,http_errors:report.http_errors}));}}finally{await browser.close();}
 const result={passed:reports.length===builds.length&&reports.every(r=>r.passed),scope:'Real local HTTP/artifact bytes, desktop/tablet/mobile geometry and dialog interactions; synthetic API responses only, zero live delivery.',reports};fs.writeFileSync(path.join(output,'modal-final.json'),JSON.stringify(result,null,2)+'\n');if(!result.passed)process.exitCode=1;
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
