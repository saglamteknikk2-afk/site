/* Optional local preview browser QA. No requests reach real services. */
'use strict';
const {chromium}=require('playwright');
const fs=require('fs');const path=require('path');
const root=path.resolve(process.env.SAGLAM_BUILD||path.join(__dirname,'../_site'));
const output=path.resolve(process.env.SAGLAM_QA||path.join(__dirname,'../build/qa'));
const base='/site';const origin='https://premium-preview.test';
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.woff2':'font/woff2','.ttf':'font/ttf'};
const selected=[['index.html',1440,1000,true],['index.html',390,844,true],['model-ariza-kodlari.html',390,844,true],['bolgeler.html',390,844,true],['iletisim.html',390,844,true]];
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']});
 const results=[];fs.mkdirSync(path.join(output,'screenshots'),{recursive:true});
 try {
  for(const [filename,width,height,fullPage] of selected){
   const errors=[],blocked=[],missing=[],unnecessaryLogoPng=[];const page=await browser.newPage({viewport:{width,height},deviceScaleFactor:1,serviceWorkers:'block',reducedMotion:'reduce'});
   page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',async route=>{
    const u=new URL(route.request().url());
    if(/\/logo\.png$/.test(u.pathname))unnecessaryLogoPng.push(u.href);
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
   const hero=filename==='index.html'?await page.evaluate(()=>{
    const rgb=s=>s.match(/[\d.]+/g).slice(0,3).map(Number);
    const luminance=c=>c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
    const buttons=[...document.querySelectorAll('.p-hero a.p-button')].map(a=>{const s=getComputedStyle(a);let node=a,background='rgb(255, 255, 255)';while(node){const value=getComputedStyle(node).backgroundColor,parts=value.match(/[\d.]+/g).map(Number);if(parts.length===3||parts[3]>=.99){background=value;break}node=node.parentElement}const f=luminance(rgb(s.color)),b=luminance(rgb(background));return {text:a.textContent.trim(),color:s.color,background,css_background:s.backgroundColor,contrast:(Math.max(f,b)+.05)/(Math.min(f,b)+.05)};});
    const photo=document.querySelector('.p-hero-photo'),r=photo.getBoundingClientRect(),figure=photo.closest('figure').getBoundingClientRect(),logo=document.querySelector('.premium-header img');
    return {buttons,photo:{top:r.top,bottom:r.bottom,width:r.width,height:r.height,natural_width:photo.naturalWidth,inside_figure:r.left>=figure.left-1&&r.right<=figure.right+1&&r.top>=figure.top-1&&r.bottom<=figure.bottom+1,fully_visible_in_first_view:innerWidth>760||(r.top>=0&&r.bottom<=innerHeight),object_fit:getComputedStyle(photo).objectFit},logo:{url:logo.currentSrc,natural_width:logo.naturalWidth}};
   }):null;
   const localDiagnostic=filename==='index.html'?await page.evaluate(()=>{STUstaWizard.open('Kombi');document.querySelector('#ustaStep [data-choice="water"]').click();const ok=typeof stApi==='function'&&document.querySelector('#aiResponseText').textContent.includes('Sıcak su');document.getElementById('ustaRestart').click();window.scrollTo(0,0);return ok}):null;
   if(filename==='index.html')await page.screenshot({path:path.join(output,'screenshots','index-'+width+'-viewport.jpg'),type:'jpeg',quality:85,animations:'disabled'});
   const facts=await page.evaluate(()=>({title:document.title,h1:document.querySelector('h1')?.textContent.trim(),overflow:document.documentElement.scrollWidth>innerWidth+1,width:innerWidth,scroll_width:document.documentElement.scrollWidth,preview:window.ST_PREVIEW===true,noindex:document.querySelector('meta[name=robots]')?.content.includes('noindex'),failed_images:[...document.images].filter(x=>!x.complete||!x.naturalWidth).map(x=>x.currentSrc||x.src)}));
   const screenshot=path.join(output,'screenshots',filename.replace('.html','')+'-'+width+'.jpg');await page.screenshot({path:screenshot,type:'jpeg',quality:80,fullPage,animations:'disabled'});
   results.push({route:base+'/'+(filename==='index.html'?'':filename),width,height,full_page:fullPage,screenshot,...facts,badge,hero,localDiagnostic,errors,blocked,missing,unnecessaryLogoPng});await page.close();
  }
 }finally{await browser.close();}
 const report={passed:results.every(x=>!x.overflow&&!x.errors.length&&!x.blocked.length&&!x.missing.length&&!x.failed_images.length&&!x.unnecessaryLogoPng.length&&x.preview&&x.noindex&&(!x.hero||(x.hero.buttons.every(b=>b.contrast>=4.5)&&x.hero.photo.natural_width>0&&x.hero.photo.inside_figure&&x.hero.photo.fully_visible_in_first_view&&x.hero.logo.url.endsWith('/logo.svg')&&x.hero.logo.natural_width>0&&x.localDiagnostic))&&(!x.badge.required||(x.badge.visible&&x.badge.image_visible&&x.badge.natural_width>0&&x.badge.rendered_width>0&&x.badge.rendered_height>0&&Number(x.badge.opacity)>0))),pages:results};
 fs.writeFileSync(path.join(output,'browser-smoke.json'),JSON.stringify(report,null,2)+'\n');process.stdout.write(JSON.stringify(report,null,2)+'\n');if(!report.passed)process.exitCode=1;
})().catch(e=>{process.stderr.write(e.stack+'\n');process.exitCode=1;});
