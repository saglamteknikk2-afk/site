/* Every visitor route, real local HTTP/Chromium, production layout acceptance.
 * Complements navigation/interactions with decoded images and computed geometry.
 * API replies below are synthetic; this test never contacts a live service.
 */
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {startServer,publicNames}=require('./interaction_http.cjs');
const repository=path.resolve(__dirname,'..');
const directory=path.resolve(process.env.PAGE_VISUAL_BUILD||path.join(repository,'build/production'));
const output=path.resolve(process.env.PAGE_VISUAL_OUTPUT||path.join(repository,'build/qa-page-visual'));
const widths=[390,1440],height=1000;
const brand=JSON.parse(fs.readFileSync(path.join(repository,'components/brand.json'),'utf8'));
const captures=new Set(['index.html','bolgeler.html','iletisim.html','kucukcekmece-kombi-servisi.html','model-ariza-kodlari.html','404.html']);
const fold=value=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('tr-TR').replace(/ı/g,'i').replace(/\s+/g,'');
async function run(browser,server,width,names){
 const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce',serviceWorkers:'block'}),records=[],errors=[],requests={synthetic_api:0,external:[]};
 await context.route('**/*',route=>{
  const request=route.request(),url=new URL(request.url());
  if(url.origin!==server.origin){requests.external.push({url:url.href,type:request.resourceType()});return route.abort();}
  if(/\.php(?:$|\/)/i.test(url.pathname)){
   requests.synthetic_api++;
   const action=url.searchParams.get('action');
   return route.fulfill({contentType:'application/json',body:JSON.stringify(action==='bootstrap'?{ok:true,csrf:'1700000000.'+'a'.repeat(64)}:action==='reviews'?{ok:true,reviews:[]}:{ok:true,recorded:true})});
  }
  return route.continue();
 });
 let cursor=0;
 async function worker(){
  const page=await context.newPage(),state={route:''},pageErrors=[],httpErrors=[];
  page.on('pageerror',error=>pageErrors.push({route:state.route,error:error.message}));
  page.on('response',response=>{if(response.status()>=400)httpErrors.push({route:state.route,url:response.url(),status:response.status()});});
  try{
   while(cursor<names.length){
    const name=names[cursor++];state.route=name;
    try{
     const response=await page.goto(server.origin+'/'+(name==='index.html'?'':name),{waitUntil:'load'});
     assert.equal(response.status(),200,'Visitor route returns HTTP200: '+name);
     await page.evaluate(async()=>{
      await document.fonts.ready;
      for(const image of document.images)image.loading='eager';
      await Promise.all([...document.images].map(image=>image.decode().catch(()=>{})));
      await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
     });
     const facts=await page.evaluate(()=>{
      const visible=element=>{if(!element)return false;const style=getComputedStyle(element),r=element.getBoundingClientRect();return !element.hidden&&style.display!=='none'&&style.visibility!=='hidden'&&Number(style.opacity)>0&&r.width>0&&r.height>0;};
      const brandFacts=selector=>{
       const anchor=document.querySelector(selector),tagline=anchor?.querySelector('small'),image=anchor?.querySelector('img');
       if(!anchor||!tagline||!image)return {selector,present:false};
       const walker=document.createTreeWalker(anchor,NodeFilter.SHOW_TEXT),boxes=[],words=[];let node;
       while(node=walker.nextNode()){
        if(!node.textContent.trim()||node.parentElement.closest('small,svg'))continue;
        const range=document.createRange();range.selectNodeContents(node);
        const rects=[...range.getClientRects()].filter(rect=>rect.width>0&&rect.height>0);
        if(rects.length){words.push(node.textContent);boxes.push(...rects.map(rect=>({top:rect.top,left:rect.left,right:rect.right,bottom:rect.bottom})));}
       }
       const range=document.createRange();range.selectNodeContents(tagline);
       const textRect=range.getBoundingClientRect(),anchorRect=anchor.getBoundingClientRect(),tops=boxes.map(box=>box.top),clipped=[];
       for(let ancestor=tagline;ancestor&&ancestor!==document.documentElement;ancestor=ancestor.parentElement){
        const style=getComputedStyle(ancestor),rect=ancestor.getBoundingClientRect();
        if((/^(hidden|clip|auto|scroll)$/.test(style.overflowX)&&(textRect.left<rect.left-.5||textRect.right>rect.right+.5))||(/^(hidden|clip|auto|scroll)$/.test(style.overflowY)&&(textRect.top<rect.top-.5||textRect.bottom>rect.bottom+.5)))clipped.push(ancestor.tagName+'.'+ancestor.className);
       }
       return {selector,present:true,text:words.join(' '),horizontal:tops.length>0&&Math.max(...tops)-Math.min(...tops)<=2,descriptor:tagline.textContent,descriptor_visible:visible(tagline),descriptor_inside_anchor:textRect.left>=anchorRect.left-1&&textRect.right<=anchorRect.right+1,clipped,image:{src:new URL(image.currentSrc||image.src).pathname,decoded:image.complete&&image.naturalWidth>0,visible:visible(image)}};
      };
      const modal=document.querySelector('#serviceTicketModal');
      return {title:document.title,h1:document.querySelector('h1')?.textContent.trim(),document_width:document.documentElement.scrollWidth,viewport_width:innerWidth,body_font:getComputedStyle(document.body).fontFamily,failed_images:[...document.images].filter(image=>!image.complete||!image.naturalWidth).map(image=>image.currentSrc||image.src),brands:[brandFacts('.premium-header .premium-brand'),brandFacts('.premium-footer .premium-footer-brand')],preview_banner_visible:[...document.querySelectorAll('#st-preview-banner,[data-preview-banner]')].some(visible),preview_runtime:window.ST_PREVIEW===true,modal_present:!!modal,modal_visible:visible(modal),stylesheets:document.styleSheets.length};
     });
     const failures=[];
     if(!facts.h1||!facts.title)failures.push('Missing title or H1');
     if(facts.document_width>width+1)failures.push('Horizontal document overflow');
     if(facts.failed_images.length)failures.push('Image failed to decode');
     if(facts.preview_banner_visible||facts.preview_runtime)failures.push('Production showing preview mode');
     if(facts.modal_visible)failures.push('Closed service dialog visible in page flow');
     if(facts.stylesheets<2)failures.push('Missing loaded stylesheet collection');
     for(const record of facts.brands){
      if(!record.present||fold(record.text||'')!=='saglamteknik'||!record.horizontal||fold(record.descriptor||'')!=='isitma&sogutmateknolojileri'||!record.descriptor_visible||!record.descriptor_inside_anchor||record.clipped?.length||record.image?.src!==brand.logo||!record.image?.decoded||!record.image?.visible)failures.push('Inconsistent or clipped brand: '+record.selector);
     }
     const screenshot=captures.has(name)?path.join(output,name.replace('.html','')+'-'+width+'.png'):null;
     if(screenshot){await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:screenshot,animations:'disabled'});}
     records.push({route:name,width,passed:!failures.length,failures,...facts,screenshot});
    }catch(error){errors.push({route:name,width,error:error.stack});}
   }
  }finally{errors.push(...pageErrors.map(record=>({...record,width,type:'pageerror'})),...httpErrors.map(record=>({...record,width,type:'http-error'})));await page.close();}
 }
 try{await Promise.all(Array.from({length:Number(process.env.PAGE_VISUAL_WORKERS||2)},worker));}finally{await context.close();}
 return {width,passed:records.length===names.length&&records.every(record=>record.passed)&&!errors.length&&!requests.external.length,documents:records.length,errors,requests,records};
}
(async()=>{
 fs.mkdirSync(output,{recursive:true});
 const start=JSON.parse(fs.readFileSync(path.join(directory,'build-info.json'),'utf8')),names=publicNames(directory);
 assert.equal(start.mode,'production','This acceptance pass must receive the production artifact');
 assert.equal(names.length,203,'Every established visitor HTML route must be included');
 const server=await startServer(directory,''),browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']}),reports=[];
 try{for(const width of widths){const report=await run(browser,server,width,names);reports.push(report);fs.writeFileSync(path.join(output,'pages-'+width+'.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({width,passed:report.passed,documents:report.documents,failed_routes:report.records.filter(record=>!record.passed).map(record=>({route:record.route,failures:record.failures})),errors:report.errors,external_requests:report.requests.external.length}));}}
 finally{await browser.close();await server.close();}
 const end=JSON.parse(fs.readFileSync(path.join(directory,'build-info.json'),'utf8'));
 const report={passed:reports.length===2&&reports.every(item=>item.passed)&&!server.errors.length&&start.content_sha256===end.content_sha256,scope:'203 visitor pages at390px and1440px, realHTTP asset bytes, computed layout/branding/images/errors. APIs are synthetic; no live delivery or semantic content verification.',build_start:start,build_end:end,documents:reports.reduce((sum,item)=>sum+item.documents,0),server_requests:server.requests,server_errors:server.errors,reports};
 fs.writeFileSync(path.join(output,'pages-final.json'),JSON.stringify(report,null,2)+'\n');if(!report.passed)process.exitCode=1;
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
