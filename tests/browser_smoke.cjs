/* Optional local preview browser QA. No requests reach real services. */
'use strict';
const {chromium}=require('playwright');
const fs=require('fs');const path=require('path');
const root=path.resolve(process.env.SAGLAM_BUILD||path.join(__dirname,'../_site'));
const output=path.resolve(process.env.SAGLAM_QA||path.join(__dirname,'../build/qa'));
const repository=path.resolve(__dirname,'..');
const production=path.resolve(process.env.SAGLAM_PRODUCTION_BUILD||path.join(repository,'build/production'));
const brand=JSON.parse(fs.readFileSync(path.join(repository,'components/brand.json'),'utf8'));
const masterRequest=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/master-request.json'),'utf8'));
const base='/site';const origin='https://premium-preview.test';
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.woff2':'font/woff2','.ttf':'font/ttf'};
const selected=[['index.html',1440,1000,true],['index.html',390,844,true],['index.html',320,844,false],['index.html',768,1000,false],['model-ariza-kodlari.html',390,844,true],['bolgeler.html',390,844,true],['iletisim.html',390,844,true],['kombi-servisi.html',390,844,true],['kucukcekmece-klima-servisi.html',390,844,true]];
const expectedLogo=brand.logo;
const expectedFavicon=brand.favicon;
const layoutOnly=process.env.SAGLAM_LAYOUT_ONLY==='1';
function assetMatches(url,expected){try{return new URL(url).pathname===new URL(expected.replace(/^\/+/,''),origin+base+'/').pathname;}catch(_){return false;}}
function routeAudit(){
 const publicNames=directory=>fs.readdirSync(directory).filter(name=>name.endsWith('.html')&&name!=='owner-admin.html'&&!/^(?:google|yandex_)/.test(name)).sort();
 const expected=Object.keys(JSON.parse(fs.readFileSync(path.join(repository,'scripts/production-seo.json'),'utf8'))).sort();
 const previewNames=publicNames(root),productionNames=publicNames(production);
 if(expected.length!==203||JSON.stringify(expected)!==JSON.stringify(previewNames)||JSON.stringify(expected)!==JSON.stringify(productionNames))throw Error('The 203 established visitor routes must be preserved in both builds');
 const isNoindex=text=>/<meta\b(?=[^>]*name=["']robots["'])(?=[^>]*content=["'][^"']*noindex)[^>]*>/i.test(text);
 if(previewNames.some(name=>!isNoindex(fs.readFileSync(path.join(root,name),'utf8'))))throw Error('Every preview visitor page must be noindex');
 if(/Disallow:\s*\/\s*$/m.test(fs.readFileSync(path.join(root,'robots.txt'),'utf8')))throw Error('Preview robots must allow reading noindex');
 const canonical=[],excluded=new Set([...masterRequest.established_nonindex_routes,...masterRequest.foreign_slugs]);
 if(masterRequest.foreign_slugs.length!==11||excluded.size!==13)throw Error('Expected exactly eleven requested foreign guides plus the two established noindex routes');
 const unavailable=new Set(JSON.parse(fs.readFileSync(path.join(production,'assets/verified-faults.json'),'utf8')).models.filter(model=>model.manual?.source_available===false).map(model=>path.basename(model.path)));
 for(const name of unavailable)excluded.add(name);
 for(const name of productionNames){const text=fs.readFileSync(path.join(production,name),'utf8'),noindex=isNoindex(text);if(noindex!==excluded.has(name))throw Error('Production indexing policy differs from the requested exact route set: '+name);const link=text.match(/<link\b(?=[^>]*rel=["']canonical["'])[^>]*>/i)?.[0],url=link?.match(/href=["']([^"']+)["']/i)?.[1],expectedURL='https://saglamkombiklima.com.tr/'+(name==='index.html'?'':name);if(name!=='404.html'&&url!==expectedURL)throw Error('Production canonical changed: '+name);if(masterRequest.foreign_slugs.includes(name)){const robots=text.match(/<meta\b(?=[^>]*name=["']robots["'])[^>]*>/i)?.[0]?.match(/content=["']([^"']+)["']/i)?.[1]?.toLowerCase().split(/[\s,]+/)||[];if(!robots.includes('noindex')||!robots.includes('follow')||robots.includes('nofollow'))throw Error('Foreign guide must remain available with noindex,follow: '+name);}if(!noindex)canonical.push(url);}
 const sitemap=[...fs.readFileSync(path.join(production,'sitemap.xml'),'utf8').matchAll(/<loc>([^<]+)<\/loc>/g)].map(m=>m[1]).sort();
 if(canonical.length!==expected.length-excluded.size||JSON.stringify(canonical.sort())!==JSON.stringify(sitemap))throw Error('Indexable production canonicals must equal the sitemap; foreign and source-unavailable guides stay excluded');
 const landings=JSON.parse(fs.readFileSync(path.join(root,'assets/ad-landing-map.json'),'utf8')).routes;
 if(landings.length!==82)throw Error('Expected the existing 82 service landing routes');
 for(const landing of landings){const localPath=landing.path.startsWith(base+'/')?landing.path.slice(base.length):landing.path;const text=fs.readFileSync(path.join(root,localPath.replace(/^\//,'')),'utf8'),block=text.match(/<div\b[^>]*data-service-contact[^>]*>([\s\S]*?)<\/div>/)?.[1],links=[...(block||'').matchAll(/<a\b[^>]*href="([^"]+)"[^>]*>/g)].map(m=>m[1]),wa=links.find(href=>href.startsWith('https://wa.me/')),message=wa&&new URL(wa.replace(/&amp;/g,'&')).searchParams.get('text');if(links.length!==2||!links.includes('tel:05346225515')||!message?.includes(landing.title)||!message?.includes(landing.url))throw Error('Service landing must preserve contextual phone/WhatsApp actions: '+landing.path);}
 const homeHTML=fs.readFileSync(path.join(root,'index.html'),'utf8'),staticReviews=[...homeHTML.matchAll(/\bclass=["']([^"']+)["']/g)].filter(match=>match[1].split(/\s+/).includes('pr-review')).length;
 if(staticReviews!==6)throw Error('Exactly the first six existing reviews must be present in static HTML');
 if(/data-st-link-directory=["']hub["']/.test(homeHTML)||homeHTML.includes('Tüm bölge, marka ve rehber bağlantıları'))throw Error('Homepage must use compact category navigation instead of the full generated directory');
 return {passed:true,visitor_routes:203,preview_noindex:203,production_indexable:canonical.length,unavailable_manual_routes:[...unavailable].sort(),sitemap_urls:sitemap.length,foreign_guides_available_noindex_follow:masterRequest.foreign_slugs.length,excluded_foreign_routes:masterRequest.foreign_slugs,contextual_service_landings:landings.length,static_review_cards:staticReviews};
}
async function reachableControl(locator){
 await locator.evaluate(el=>el.scrollIntoView({block:'center',inline:'nearest'}));
 return locator.evaluate(el=>{const r=el.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2,hit=document.elementFromPoint(x,y);return r.width>0&&r.height>0&&x>=0&&x<innerWidth&&y>=0&&y<innerHeight&&(hit===el||el.contains(hit));});
}
async function contactJourney(page,scope='.p-hero',canonicalURL=''){
 const call=page.locator(scope+' a[href^="tel:"]'),whatsapp=page.locator(scope+' a[href*="wa.me/"]');
 if(await call.count()!==1||await whatsapp.count()!==1)throw Error('Contact group must show one clear call and one WhatsApp action');
 const callHref=await call.getAttribute('href'),whatsappHref=await whatsapp.getAttribute('href'),waURL=new URL(whatsappHref);
 if(callHref.replace(/\s/g,'')!=='tel:05346225515'||waURL.hostname!=='wa.me'||waURL.pathname!=='/905346225515'||!waURL.searchParams.get('text'))throw Error('Hero contact actions must preserve the real phone and a usable WhatsApp intent');
 const landingTitle=canonicalURL?await page.locator('h1').innerText():'';
 if(canonicalURL&&(!waURL.searchParams.get('text').includes(landingTitle.replace(/\s+/g,' ').trim())||!waURL.searchParams.get('text').includes(canonicalURL)))throw Error('Landing WhatsApp intent must retain its page title and canonical URL');
 if(!/hemen\s*ara/i.test(await call.innerText())||!/whats\s*app/i.test(await whatsapp.innerText()))throw Error('Hero contact actions must have clear call/WhatsApp labels');
 const callReachable=await reachableControl(call),whatsappReachable=await reachableControl(whatsapp);
 if(!callReachable||!whatsappReachable)throw Error('Hero contact action is hidden behind another element');
 const before=page.url();await call.click();await whatsapp.click();
 if(page.url()!==before||page.context().pages().length!==1)throw Error('Preview contact test must not open an external destination');
 const denied=await page.locator('[data-preview-status]').allTextContents();
 if(!denied.some(text=>text.includes('kaydedilmedi')&&text.includes('gönderilmedi')))throw Error('Preview contact intent must explain that no message was sent');
 await page.locator('[data-preview-status]').evaluateAll(elements=>elements.forEach(el=>el.remove()));
 await page.evaluate(()=>window.scrollTo(0,0));
 return {passed:true,call_href:callHref,whatsapp_href:whatsappHref,call_reachable:callReachable,whatsapp_reachable:whatsappReachable,preview_denied_external_navigation:true,canonical_url:canonicalURL||undefined,landing_title:landingTitle||undefined};
}
async function stickyBarAudit(page,width){
 await page.evaluate(()=>window.scrollTo(0,document.scrollingElement.scrollHeight));
 const facts=await page.evaluate(()=>{const bar=document.querySelector('.premium-mobile-contact'),style=getComputedStyle(bar),r=bar.getBoundingClientRect(),footer=document.querySelector('.premium-footer').getBoundingClientRect();return {visible:style.display!=='none'&&r.height>0,height:r.height,top:r.top,bottom:r.bottom,body_bottom_padding:parseFloat(getComputedStyle(document.body).paddingBottom)||0,footer_bottom:footer.bottom};});
 const mobile=width<=760;
 if(mobile&&(!facts.visible||facts.height>78||facts.height<=0||facts.body_bottom_padding+1<facts.height||facts.footer_bottom>facts.top+1))throw Error('Mobile contact bar must be <=78px with enough page padding to expose all footer content');
 if(!mobile&&facts.visible)throw Error('Desktop/tablet view must not show the mobile fixed contact bar');
 await page.evaluate(()=>window.scrollTo(0,0));return {passed:true,...facts};
}
async function brandPresentation(page,width,capture){
 const rows=await page.evaluate(()=>{
  const fold=value=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('tr-TR').replace(/ı/g,'i').replace(/\s+/g,'');
  return ['.premium-header .premium-brand','.premium-footer .premium-footer-brand'].map(selector=>{
   const anchor=document.querySelector(selector),tagline=anchor?.querySelector('small');if(!anchor||!tagline)return {selector,passed:false,error:'Missing brand or full descriptor'};
   const walker=document.createTreeWalker(anchor,NodeFilter.SHOW_TEXT),rects=[],words=[];let node;
   while(node=walker.nextNode()){if(!node.textContent.trim()||node.parentElement.closest('small,svg'))continue;const range=document.createRange();range.selectNodeContents(node);const boxes=[...range.getClientRects()].filter(r=>r.width>0&&r.height>0);if(boxes.length){words.push(node.textContent);rects.push(...boxes.map(r=>({top:r.top,left:r.left,right:r.right,bottom:r.bottom})));}}
   const a=anchor.getBoundingClientRect(),t=tagline.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(tagline);const tr=range.getBoundingClientRect(),style=getComputedStyle(tagline),tops=rects.map(r=>r.top),horizontal=tops.length>0&&Math.max(...tops)-Math.min(...tops)<=2;
   const main=words.join(' '),descriptor=tagline.textContent.replace(/\s+/g,' ').trim();
   // Font glyphs may extend beyond their CSS line box when overflow is visible.
   // Only an ancestor that actually clips those glyphs makes the descriptor hidden.
   const clippingAncestors=[];for(let node=tagline;node&&node!==document.documentElement;node=node.parentElement){const s=getComputedStyle(node),r=node.getBoundingClientRect(),clipsX=/^(hidden|clip|auto|scroll)$/.test(s.overflowX),clipsY=/^(hidden|clip|auto|scroll)$/.test(s.overflowY);if((clipsX&&(tr.left<r.left-.5||tr.right>r.right+.5))||(clipsY&&(tr.top<r.top-.5||tr.bottom>r.bottom+.5)))clippingAncestors.push(node.tagName.toLowerCase()+'.'+node.className);}
   const fullDescriptor=fold(descriptor)==='isitma&sogutmateknolojileri',notClipped=tr.left>=a.left-1&&tr.right<=a.right+1&&!clippingAncestors.length,visible=style.display!=='none'&&style.visibility!=='hidden'&&Number(style.opacity)>0&&t.width>0&&t.height>0;
   return {selector,passed:fold(main)==='saglamteknik'&&horizontal&&fullDescriptor&&notClipped&&visible,main_text:main.replace(/\s+/g,' ').trim(),horizontal_line:horizontal,line_tops:tops,descriptor,descriptor_font_size:style.fontSize,full_descriptor:fullDescriptor,descriptor_not_clipped:notClipped,descriptor_visible:visible,clipping_ancestors:clippingAncestors};
  });
 });
 const screenshots=[];
 if(capture){for(const [name,selector] of [['header','.premium-header'],['footer','.premium-footer .premium-footer-brand']]){const target=path.join(output,'screenshots',`brand-${name}-${width}.png`);await page.locator(selector).screenshot({path:target,type:'png',animations:'disabled',style:'.premium-mobile-contact,.at-mobile-contact{visibility:hidden!important}'});screenshots.push(target);}await page.evaluate(()=>window.scrollTo({top:0,left:0,behavior:'instant'}));}
 return {passed:rows.every(row=>row.passed),rows,screenshots};
}
async function exerciseWizard(page,width){
 const stages=[];const capture=[390,1440].includes(width);
 async function stage(name,expectedStep){
  const context=await page.evaluate(()=>STUstaWizard.getContext());
  if(context.step!==expectedStep)throw Error(`Wizard ${name}: expected step ${expectedStep}, got ${context.step}`);
  const panel=page.locator('#aiUstaWizard');
  const visibleInputs=await panel.locator('input:visible,select:visible,textarea:visible').count();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
  if(overflow)throw Error(`Wizard ${name}: horizontal overflow at ${width}px`);
  const item={name,step:context.step,device:context.device,brand:context.brand,model:context.model,visible_inputs:visibleInputs,overflow};
  if(capture){item.screenshot=path.join(output,'screenshots',`ai-${name}-${width}.jpg`);item.capture='Component capture; outside fixed contact bar hidden only for this screenshot';await panel.screenshot({path:item.screenshot,type:'jpeg',quality:85,animations:'disabled',style:'.premium-mobile-contact,.at-mobile-contact{visibility:hidden!important}'});}
  stages.push(item);
 }
 await page.waitForFunction(()=>window.STUstaWizard);
 await page.locator('#ustaRestart').click();
 if(await page.locator('#aiUstaWizard').count()!==1)throw Error('All device entries must use the single AI assistant');
 await stage('device',0);
 const quickDevices=[];
 for(const device of ['Kombi','Klima','Petek']){const button=page.locator(`.p-hero [data-usta-device="${device}"]`);if(await button.count()!==1)throw Error('Missing hero device shortcut: '+device);await button.click();const context=await page.evaluate(()=>STUstaWizard.getContext());if(context.device!==device||context.step!==1)throw Error('Device shortcut must skip device selection: '+device);quickDevices.push({device,step:context.step});await page.locator('#ustaRestart').click();}
 await page.locator('.p-hero [data-usta-device="Kombi"]').click();await stage('symptom',1);
 if(!await page.locator('#ustaExtraIssue').isVisible())throw Error('Free text must be visible at symptom step');
 if(!await page.locator('#ustaExtraIssue').evaluate(el=>el.tagName==='INPUT'&&['text','search'].includes(el.type)))throw Error('Symptom front door must use one short text input');
 if(await page.locator('#aiUstaWizard input:visible').count()!==1)throw Error('Symptom front door must expose exactly one input');
 await page.locator('#ustaStep [data-choice="water"]').click();await stage('brand',2);
 const brandButton=page.locator('#ustaStep [data-brand="Bosch"]');
 if(await brandButton.count())await brandButton.click();else await page.selectOption('#ustaBrand','Bosch');
 await stage('model',3);
 const selectedModel=await page.locator('#ustaVerifiedModel option').evaluateAll(options=>options.find(o=>o.textContent.includes('Condens 2300i W'))?.value);
 if(!selectedModel)throw Error('Verified Bosch model option missing');
 await page.selectOption('#ustaVerifiedModel',selectedModel);await page.locator('#ustaNext').click();await stage('result',4);
 const known=await page.evaluate(()=>({context:STUstaWizard.getContext(),text:document.querySelector('#aiResponseText').textContent,result_visible:!document.querySelector('#aiResultBox').classList.contains('hidden'),api_function_present:typeof stApi==='function'}));
 if(!known.result_visible||!known.text.includes('Sıcak su')||known.context.brand!=='Bosch'||!known.context.model_id||!known.api_function_present)throw Error('Selected model and symptom did not produce the expected local guidance');
 await page.locator('#ustaRestart').click();await page.locator('#ustaStep [data-choice="Kombi"]').click();await page.locator('#ustaStep [data-choice="water"]').click();
 await page.locator('#ustaStep [data-brand=""]').click();
 const unknown=await page.evaluate(()=>({context:STUstaWizard.getContext(),visible:!document.querySelector('#aiResultBox').classList.contains('hidden'),text:document.querySelector('#aiResponseText').textContent.trim()}));
 if(unknown.context.step!==4||unknown.context.brand||unknown.context.model_id||!unknown.visible||!unknown.text)throw Error('Unknown-brand symptom path must give guidance without inventing a model');
 await page.locator('#ustaRestart').click();await page.locator('#ustaStep [data-choice="Petek"]').click();await page.locator('#ustaStep [data-choice="heat"]').click();
 const radiator=await page.evaluate(()=>({context:STUstaWizard.getContext(),visible:!document.querySelector('#aiResultBox').classList.contains('hidden'),text:document.querySelector('#aiResponseText').textContent.trim()}));
 if(radiator.context.step!==4||radiator.context.brand||radiator.context.model_id||!radiator.visible||!radiator.text)throw Error('Radiator symptom path must give guidance without an unrelated boiler brand/model');
 await page.locator('#ustaRestart').click();await page.evaluate(()=>window.scrollTo(0,0));
 return {passed:true,stages,quick_device_journeys:quickDevices,unknown_brand_path:true,radiator_path:true};
}
(async()=>{
 const buildStart=JSON.parse(fs.readFileSync(path.join(root,'build-info.json'),'utf8'));
 const routes=routeAudit();
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']});
 const results=[];fs.mkdirSync(path.join(output,'screenshots'),{recursive:true});fs.rmSync(path.join(output,'browser-smoke.json'),{force:true});
 try {
  for(const [filename,width,height,fullPage] of selected){
   const errors=[],blocked=[],missing=[],unnecessaryLogoPng=[];const page=await browser.newPage({viewport:{width,height},deviceScaleFactor:1,serviceWorkers:'block',reducedMotion:'reduce'});
   page.on('pageerror',e=>errors.push(e.message));
   await page.context().route('**/*',async route=>{
    const u=new URL(route.request().url());
    if(u.pathname===base+'/logo.png'&&u.pathname!==base+expectedLogo)unnecessaryLogoPng.push(u.href);
    if(u.origin!==origin||!u.pathname.startsWith(base+'/')||u.pathname.endsWith('.php')){blocked.push(u.href);return route.abort();}
    let rel=decodeURIComponent(u.pathname.slice(base.length+1));if(!rel)rel='index.html';
    const file=path.resolve(root,rel);
    if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){missing.push(u.href);return route.fulfill({status:404,body:'Local QA: file not found'});}
    return route.fulfill({path:file,contentType:mime[path.extname(file)]||'application/octet-stream'});
   });
   await page.goto(origin+base+'/'+(filename==='index.html'?'':filename),{waitUntil:'networkidle'});
   await page.evaluate(()=>document.fonts.ready);await page.locator('body').waitFor();
   await page.evaluate(async()=>{
    for(const img of document.images)img.loading='eager';
    await Promise.all([...document.images].map(img=>img.decode().catch(()=>{})));
   });
   const badge={required:filename==='index.html',visible:false,image_visible:false,natural_width:0};
   if(badge.required){
    const endorsement=page.locator('.pr-endorsement');await endorsement.scrollIntoViewIfNeeded();
    badge.visible=await endorsement.isVisible();badge.image_visible=await endorsement.locator('img').isVisible();
    Object.assign(badge,await endorsement.locator('img').evaluate(img=>({natural_width:img.naturalWidth,rendered_width:img.getBoundingClientRect().width,rendered_height:img.getBoundingClientRect().height,opacity:getComputedStyle(img).opacity})));
    if(width===390){badge.screenshot=path.join(output,'screenshots','endorsement-390.jpg');await page.screenshot({path:badge.screenshot,type:'jpeg',quality:85,animations:'disabled'});}
   }
   await page.evaluate(()=>window.scrollTo(0,0));
   const brandLayout=await brandPresentation(page,width,filename==='index.html');
   const hero=filename==='index.html'?await page.evaluate(()=>{
    const rgb=s=>s.match(/[\d.]+/g).slice(0,3).map(Number);
    const luminance=c=>c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
    const buttons=[...document.querySelectorAll('.p-hero a[href^="tel:"],.p-hero a[href*="wa.me/"]')].map(a=>{const s=getComputedStyle(a);let node=a,background='rgb(255, 255, 255)';while(node){const value=getComputedStyle(node).backgroundColor,parts=value.match(/[\d.]+/g).map(Number);if(parts.length===3||parts[3]>=.99){background=value;break}node=node.parentElement}const f=luminance(rgb(s.color)),b=luminance(rgb(background));const r=a.getBoundingClientRect(),bar=document.querySelector('.premium-mobile-contact'),barRect=bar.getBoundingClientRect(),limit=getComputedStyle(bar).display!=='none'?Math.min(innerHeight,barRect.top):innerHeight;return {text:a.textContent.trim(),color:s.color,background,css_background:s.backgroundColor,contrast:(Math.max(f,b)+.05)/(Math.min(f,b)+.05),top:r.top,bottom:r.bottom,visible_above_fixed_bar:r.top>=0&&r.bottom<=limit};});
    const photo=document.querySelector('.p-hero-photo'),r=photo.getBoundingClientRect(),figure=photo.closest('figure').getBoundingClientRect(),logo=document.querySelector('.premium-header img');
    return {buttons,photo:{top:r.top,bottom:r.bottom,width:r.width,height:r.height,natural_width:photo.naturalWidth,inside_figure:r.left>=figure.left-1&&r.right<=figure.right+1&&r.top>=figure.top-1&&r.bottom<=figure.bottom+1,fully_visible_in_first_view:r.top>=0&&r.bottom<=innerHeight,object_fit:getComputedStyle(photo).objectFit},logo:{url:logo.currentSrc,natural_width:logo.naturalWidth}};
   }):null;
   if(filename==='index.html')await page.screenshot({path:path.join(output,'screenshots','index-'+width+'-viewport.jpg'),type:'jpeg',quality:85,animations:'disabled'});
   const localDiagnostic=filename==='index.html'?(layoutOnly?{skipped:'Preliminary layout/contact pass; wizard not exercised'}:await exerciseWizard(page,width)):null;
   const serviceLanding=['kombi-servisi.html','kucukcekmece-klima-servisi.html'].includes(filename);
   if(serviceLanding)await page.screenshot({path:path.join(output,'screenshots',filename.replace('.html','')+'-'+width+'-viewport.jpg'),type:'jpeg',quality:85,animations:'disabled'});
   const contactIntent=filename==='index.html'?await contactJourney(page):serviceLanding?await contactJourney(page,'[data-service-contact]','https://saglamkombiklima.com.tr/'+filename):null;
   const stickyBar=await stickyBarAudit(page,width);
   const facts=await page.evaluate(()=>({title:document.title,h1:document.querySelector('h1')?.textContent.trim(),overflow:document.documentElement.scrollWidth>innerWidth+1,width:innerWidth,scroll_width:document.documentElement.scrollWidth,preview:window.ST_PREVIEW===true,noindex:document.querySelector('meta[name=robots]')?.content.includes('noindex'),failed_images:[...document.images].filter(x=>!x.complete||!x.naturalWidth).map(x=>x.currentSrc||x.src),logos:[...document.querySelectorAll('.premium-header img,.premium-footer img')].map(img=>({url:img.currentSrc,natural_width:img.naturalWidth})),favicon:document.querySelector('link[rel="icon"]')?.href}));
   const screenshot=path.join(output,'screenshots',filename.replace('.html','')+'-'+width+'.jpg');await page.screenshot({path:screenshot,type:'jpeg',quality:80,fullPage,animations:'disabled'});
   results.push({route:base+'/'+(filename==='index.html'?'':filename),width,height,full_page:fullPage,screenshot,...facts,badge,hero,localDiagnostic,contactIntent,stickyBar,brandLayout,errors,blocked,missing,unnecessaryLogoPng});await page.close();
  }
 }finally{await browser.close();}
 const buildEnd=JSON.parse(fs.readFileSync(path.join(root,'build-info.json'),'utf8'));
 const changedDuringCapture=buildStart.content_sha256!==buildEnd.content_sha256;
 const report={passed:!changedDuringCapture&&routes.passed&&results.every(x=>!x.overflow&&!x.errors.length&&!x.blocked.length&&!x.missing.length&&!x.failed_images.length&&!x.unnecessaryLogoPng.length&&x.preview&&x.noindex&&x.brandLayout.passed&&x.logos.length===2&&x.logos.every(logo=>assetMatches(logo.url,expectedLogo)&&logo.natural_width>0)&&assetMatches(x.favicon,expectedFavicon)&&x.stickyBar.passed&&(!x.contactIntent||x.contactIntent.passed)&&(!x.hero||(x.hero.buttons.length===2&&x.hero.buttons.every(b=>b.contrast>=4.5&&b.visible_above_fixed_bar)&&x.hero.photo.natural_width>0&&x.hero.photo.inside_figure&&assetMatches(x.hero.logo.url,expectedLogo)&&x.hero.logo.natural_width>0&&(layoutOnly||x.localDiagnostic.passed)&&x.contactIntent.passed))&&(!x.badge.required||(x.badge.visible&&x.badge.image_visible&&x.badge.natural_width>0&&x.badge.rendered_width>0&&x.badge.rendered_height>0&&Number(x.badge.opacity)>0))),scope:layoutOnly?'preliminary layout/contact; AI journey skipped':'full preview UI/contact/AI journey',build_start:buildStart,build_end:buildEnd,changed_during_capture:changedDuringCapture,routes_audit:routes,brand_manifest:{logo:expectedLogo,favicon:expectedFavicon},pages:results};
 fs.writeFileSync(path.join(output,'browser-smoke.json'),JSON.stringify(report,null,2)+'\n');process.stdout.write(JSON.stringify(report,null,2)+'\n');if(!report.passed)process.exitCode=1;
})().catch(e=>{fs.mkdirSync(output,{recursive:true});fs.writeFileSync(path.join(output,'browser-smoke.json'),JSON.stringify({passed:false,error:e.message},null,2)+'\n');process.stderr.write(e.stack+'\n');process.exitCode=1;});
