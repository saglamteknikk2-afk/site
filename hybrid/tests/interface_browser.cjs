'use strict';
// Compute text/background contrast using real legacy styles and repaired controls.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const baseline=path.resolve(process.argv[2]),report=process.argv[3];
 const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(baseline,'index.html'),'utf8');
 const cssPaths=[...html.matchAll(/<link\b(?=[^>]*rel="stylesheet")[^>]*href="([^"]+)"/g)].map(m=>m[1].split('?')[0]);
 const css=cssPaths.map(p=>fs.readFileSync(path.join(baseline,p),'utf8')).join('\n')+'\n'+fs.readFileSync(path.join(root,'assets/matrix.css'),'utf8');
 const repair=fs.readFileSync(path.join(root,'assets/interface-repairs.css'),'utf8');
 const fixture=`<div class="at-content"><section class="hybrid-result"><div class="hybrid-actions"><a id="model" href="#none">Model ve arıza rehberi</a><a id="call" href="#none">Ustamızı ara</a><button id="reset" class="hybrid-reset">Baştan başla</button></div></section><div class="usta-result-actions"><a id="aiPrimary" href="#none">Servisi ara</a><a id="aiSecondary" href="#none">WhatsApp'a aktar</a></div></div><div id="serviceTicketModal" class="ah-modal" style="display:block;position:static;background:transparent"><div id="ticketSuccessMsg" class="ah-form-success"><section id="ticketTrackingPanel" class="st-tracking-card"><strong>Servis takip bağlantınız hazır</strong><a id="ticketTrackingLink" class="st-tracking-action" href="#none">Servisimi takip et</a><button id="ticketCopyTrackingBtn" class="st-tracking-copy">Bağlantıyı kopyala</button></section></div></div>`;
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext();await context.route('**/*',r=>r.abort());const page=await context.newPage();
 const ids=['model','call','reset','aiPrimary','aiSecondary','ticketTrackingLink','ticketCopyTrackingBtn'];
 const contrast=async id=>page.locator('#'+id).evaluate(el=>{
  const rgba=value=>(value.match(/[\d.]+/g)||[]).map(Number);
  const blend=(a,b)=>{const alpha=a[3]??1;return a.slice(0,3).map((v,i)=>v*alpha+b[i]*(1-alpha));};
  const style=getComputedStyle(el);let background=rgba(style.backgroundColor),node=el.parentElement;
  while((background[3]??1)<1&&node){background=[...blend(background,rgba(getComputedStyle(node).backgroundColor)),1];node=node.parentElement;}
  const fg=blend(rgba(style.color),background);
  const lum=rgb=>rgb.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
  const a=lum(fg),b=lum(background);return {color:style.color,background:style.backgroundColor,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
 });
 try{
  await page.setContent('<style>'+css+'</style>'+fixture);const before={};for(const id of ids)before[id]=await contrast(id);
  await page.addStyleTag({content:repair});
  const checks=[];
  for(const width of [360,768,1440]){
   await page.setViewportSize({width,height:1100});
   for(const id of ids){
    const el=page.locator('#'+id);
    for(const state of ['default','hover','focus']){
     await page.mouse.move(0,0);await page.locator('body').click({position:{x:1,y:1}});
     if(state==='hover')await el.hover();if(state==='focus')await el.focus();
     const result=await contrast(id);assert(result.ratio>=4.5,`${id}/${state}/${width}: ${JSON.stringify(result)}`);
     checks.push({id,state,width,...result});
    }
   }
  }
  const evidence={scope:'Real Chromium computed CSS on actual legacy stylesheet bundle and semantic controls; no provider calls',before,contrast_checks:checks.length,min_ratio:Math.min(...checks.map(r=>r.ratio)),all_text_contrast_at_least_4_5:true,checks};
  if(report)fs.writeFileSync(report,JSON.stringify(evidence,null,2)+'\n');console.log(JSON.stringify({contrast_checks:checks.length,min_ratio:evidence.min_ratio,before_primary:before.model,before_tracking:before.ticketTrackingLink},null,2));
 }finally{await context.close();await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
