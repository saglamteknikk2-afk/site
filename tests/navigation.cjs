/* Real HTTP navigation regression. Internal documents/assets are NEVER mocked.
 * Every API and external request is aborted at the browser-context boundary.
 * Run after building _site, build/production and build/qa-navigation/custom.
 * NAV_MATRIX may provide [{label,directory,base}] for an isolated build.
 */
'use strict';
const {chromium}=require('playwright');
const fs=require('fs');const path=require('path');const http=require('http');
const repository=path.resolve(__dirname,'..');
const output=path.resolve(process.env.NAV_OUTPUT||path.join(repository,'build/qa-navigation'));
const matrix=process.env.NAV_MATRIX?JSON.parse(process.env.NAV_MATRIX):[
 {label:'pages',directory:path.join(repository,'_site'),base:'/site'},
 {label:'production',directory:path.join(repository,'build/production'),base:''},
 {label:'custom',directory:path.join(repository,'build/qa-navigation/custom'),base:'/qa-preview'},
];
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.woff2':'font/woff2','.ttf':'font/ttf','.txt':'text/plain; charset=utf-8','.xml':'application/xml; charset=utf-8'};
const publicNames=directory=>fs.readdirSync(directory).filter(name=>name.endsWith('.html')&&name!=='owner-admin.html'&&!/^(?:google|yandex_)/.test(name)).sort();
const normalizeText=text=>text.replace(/\s+/g,' ').trim();
function resolveInternal(directory,base,pathname){
 let decoded;try{decoded=decodeURIComponent(pathname);}catch(_){return {error:'Malformed encoded URL'};}
 if(base&&decoded!==base&&!decoded.startsWith(base+'/'))return {error:'URL is outside its mounted base'};
 let relative=base?decoded.slice(base.length):decoded;
 relative=relative.replace(/^\//,'');if(!relative||relative.endsWith('/'))relative+='index.html';
 const file=path.resolve(directory,relative);
 if(!file.startsWith(directory+path.sep))return {error:'URL escapes webroot'};
 if(!fs.existsSync(file)||!fs.statSync(file).isFile())return {error:'Target file does not exist',relative};
 return {file,relative};
}
function stateFragment(relative,fragment){
 if(!fragment.includes('='))return false;
 const params=new URLSearchParams(fragment),keys=[...params.keys()];
 const serviceKeys=new Set(['cihaz','marka','model','ilce','mahalle','semt','belirti','arama','islem']);
 if(['servis-sec.html','iletisim.html'].includes(relative))return keys.length>0&&keys.every(key=>serviceKeys.has(key));
 const assistantKeys=new Set(['cihaz','marka','model','usta']);
 return relative==='index.html'&&params.get('usta')==='1'&&keys.every(key=>assistantKeys.has(key))&&['kombi','klima','petek'].includes((params.get('cihaz')||'').toLowerCase());
}
async function staticServer(directory,base){
 const errors=[],cache=new Map();let requests=0;
 const server=http.createServer((req,res)=>{
  requests++;const url=new URL(req.url,'http://local');
  if(base&&url.pathname===base){res.writeHead(301,{Location:base+'/'});return res.end();}
  const resolved=resolveInternal(directory,base,url.pathname);
  const forbidden=/\.php(?:$|\/)/i.test(url.pathname);
  const status=forbidden?403:resolved.error?404:200;
  if(status>=400)errors.push({path:url.pathname,status});
  const file=status===200?resolved.file:path.join(directory,'404.html');
  let body=cache.get(file);if(!body){body=fs.readFileSync(file);cache.set(file,body);}
  res.writeHead(status,{'Content-Type':status===200?(mime[path.extname(file)]||'application/octet-stream'):'text/html; charset=utf-8','Content-Length':body.length,'Cache-Control':'public,max-age=3600'});
  res.end(req.method==='HEAD'?undefined:body);
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 return {origin:'http://127.0.0.1:'+server.address().port,errors,get requests(){return requests;},close:()=>new Promise(resolve=>server.close(resolve))};
}
async function runBuild(browser,entry){
 const directory=path.resolve(entry.directory),base=entry.base.replace(/\/$/,''),buildStart=JSON.parse(fs.readFileSync(path.join(directory,'build-info.json'),'utf8'));
 if((buildStart.base_path==='/'?'':buildStart.base_path)!==base)throw Error(entry.label+': mount does not match built base_path');
 const names=publicNames(directory);if(names.length!==203)throw Error(entry.label+': expected 203 visitor pages');
 const server=await staticServer(directory,base);const result={label:entry.label,base,build_start:buildStart,documents_visited:0,rendered_internal_links:0,distinct_internal_targets:0,state_fragments:0,link_errors:[],http_errors:[],expected_seed_404:[],page_errors:[],blocked_api_requests:[],blocked_external_requests:[],clicks:[],device_clicks:[],recovery:[]};
 const targets=new Set(),records=[],renderedIDs=new Map();
 async function context(width){
  const ctx=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce',serviceWorkers:'block'});
  await ctx.route('**/*',route=>{const request=route.request(),url=new URL(request.url());if(url.origin!==server.origin){result.blocked_external_requests.push({url:url.href,method:request.method()});return route.abort();}if(/\.php(?:$|\/)/i.test(url.pathname)){result.blocked_api_requests.push({path:url.pathname,method:request.method()});return route.abort();}return route.continue();});
  return ctx;
 }
 function observe(page,phase){
  page.on('pageerror',error=>result.page_errors.push({phase:phase.value,message:error.message}));
  page.on('response',response=>{if(response.status()<400)return;const item={phase:phase.value,status:response.status(),url:response.url(),document:response.request().resourceType()==='document'};if(phase.value==='recovery-seed'&&response.request().isNavigationRequest()&&response.url()===phase.seedURL&&response.status()===404)result.expected_seed_404.push(item);else result.http_errors.push(item);});
 }
 try {
  let cursor=0;
  async function worker(){
   const ctx=await context(1440),page=await ctx.newPage(),phase={value:'rendered-link-audit'};observe(page,phase);
   try{while(cursor<names.length){const name=names[cursor++],url=server.origin+base+'/'+(name==='index.html'?'':name),response=await page.goto(url,{waitUntil:'load'});if(response.status()!==200)throw Error('Visitor route returned '+response.status()+': '+name);await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    const dom=await page.evaluate(()=>({ids:[...document.querySelectorAll('[id]')].map(el=>el.id),links:[...document.querySelectorAll('a[href]')].map(el=>({href:el.href,raw:el.getAttribute('href'),text:el.textContent.replace(/\s+/g,' ').trim()}))}));renderedIDs.set(name,new Set(dom.ids));result.documents_visited++;
    for(const link of dom.links){let target;try{target=new URL(link.href);}catch(_){result.link_errors.push({page:name,...link,error:'Invalid rendered URL'});continue;}if(target.origin!==server.origin)continue;const resolved=resolveInternal(directory,base,target.pathname);result.rendered_internal_links++;targets.add(target.pathname);if(resolved.error){result.link_errors.push({page:name,...link,error:resolved.error});continue;}records.push({page:name,...link,target:resolved.relative,fragment:target.hash.slice(1)});}
   }}finally{await ctx.close();}
  }
  await Promise.all(Array.from({length:Number(process.env.NAV_WORKERS||4)},worker));
  for(const record of records){if(!record.fragment||!record.target.endsWith('.html'))continue;let fragment;try{fragment=decodeURIComponent(record.fragment);}catch(_){result.link_errors.push({...record,error:'Invalid fragment encoding'});continue;}if(stateFragment(record.target,fragment)){result.state_fragments++;continue;}if(!renderedIDs.get(record.target)?.has(fragment))result.link_errors.push({...record,error:'Fragment has no rendered target; not a recognized state route'});}
  result.distinct_internal_targets=targets.size;
  const representatives=['kombi-servisi.html','kucukcekmece-klima-servisi.html','baymak-kombi-servisi.html','404.html'];
  const actions=[{name:'header-find',scope:'#atNavigation a',text:'Arızanı bul',destination:'assistant'}, {name:'header-ai',scope:'.premium-header .premium-ai-link',destination:'assistant'}, {name:'footer-ai',scope:'.premium-footer-links a',text:'AI Usta',destination:'assistant'}, {name:'footer-guide',scope:'.premium-footer-links a',text:'Modelinizi bulun',destination:'guide'}];
  for(const width of [1440,320]){
   const ctx=await context(width),page=await ctx.newPage(),phase={value:'actual-click'};observe(page,phase);
   try{
    for(const representative of representatives)for(const action of actions){phase.value='click:'+representative+':'+action.name+':'+width;await page.goto(server.origin+base+'/'+representative,{waitUntil:'load'});
     if(width===320&&action.name==='header-find'){const toggle=page.locator('#atMenuToggle');await toggle.click();if(await toggle.getAttribute('aria-expanded')!=='true')throw Error('Mobile menu did not open');}
     const link=action.text?page.locator(action.scope).filter({hasText:new RegExp('^\\s*'+action.text.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'\\s*$')}):page.locator(action.scope);
     if(await link.count()!==1)throw Error('Expected one clickable '+action.name+' on '+representative);const href=await link.getAttribute('href');
     const navigation=page.waitForNavigation({waitUntil:'load'});await link.click();const response=await navigation;
     const target=new URL(page.url()),expectedPath=base+'/'+(action.destination==='guide'?'model-ariza-kodlari.html':'');
     if(!response||response.status()!==200||target.pathname!==expectedPath||(action.destination==='assistant'&&target.hash!=='#ai-usta'))throw Error('Real navigation failed: '+representative+' '+action.name+' → '+page.url());
     if(action.destination==='assistant'){await page.waitForFunction(()=>window.STUstaWizard&&document.getElementById('aiUstaWizard'));}else{await page.waitForFunction(()=>window.STModelBrowser&&document.querySelector('[data-model-card]'));}
     result.clicks.push({from:representative,action:action.name,width,href,path:target.pathname,hash:target.hash,status:response.status(),mobile_menu_opened:width===320&&action.name==='header-find'});
    }
    phase.value='hero-device-clicks';await page.goto(server.origin+base+'/',{waitUntil:'load'});
    for(const device of ['Kombi','Klima','Petek']){await page.locator('#ustaRestart').click();await page.locator(`.p-hero [data-usta-device="${device}"]`).click();const state=await page.evaluate(()=>STUstaWizard.getContext());if(state.device!==device||state.step!==1)throw Error('Actual hero click did not prefill '+device);result.device_clicks.push({device,width,step:state.step,actual_dom_click:true});}
    phase.value='recovery-seed';const malformed=(base?base+base:'/site/site')+'/#ai-usta';phase.seedURL=server.origin+malformed.split('#')[0];const badResponse=await page.goto(server.origin+malformed,{waitUntil:'load'});if(badResponse.status()!==404)throw Error('Malformed prior URL must reproduce a real 404 before recovery');
    phase.value='recovery-home-click';const navigation=page.waitForNavigation({waitUntil:'load'});await page.locator('.premium-header .premium-brand').click();const response=await navigation;if(!response||response.status()!==200||new URL(page.url()).pathname!==base+'/')throw Error('Home click could not recover from the malformed prior URL');result.recovery.push({width,malformed,seed_status:badResponse.status(),home_status:response.status(),home_path:new URL(page.url()).pathname,actual_dom_click:true});
   }finally{await ctx.close();}
  }
  result.server_requests=server.requests;result.server_http_errors=server.errors;result.build_end=JSON.parse(fs.readFileSync(path.join(directory,'build-info.json'),'utf8'));result.changed_during_test=result.build_start.content_sha256!==result.build_end.content_sha256;
  result.passed=!result.changed_during_test&&result.documents_visited===203&&!result.link_errors.length&&!result.http_errors.length&&!result.page_errors.length&&!result.blocked_external_requests.length&&result.expected_seed_404.length===2&&server.errors.length===result.expected_seed_404.length&&result.clicks.length===32&&result.device_clicks.length===6&&result.recovery.length===2;
 }finally{await server.close();}
 return result;
}
(async()=>{
 fs.mkdirSync(output,{recursive:true});const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']});const builds=[];
 try{for(const entry of matrix){const result=await runBuild(browser,entry);builds.push(result);fs.writeFileSync(path.join(output,'navigation-'+entry.label+'.json'),JSON.stringify(result,null,2)+'\n');process.stdout.write(JSON.stringify({label:result.label,passed:result.passed,documents:result.documents_visited,links:result.rendered_internal_links,link_errors:result.link_errors.length,http_errors:result.http_errors.length,expected_seed_404:result.expected_seed_404.length,clicks:result.clicks.length,device_clicks:result.device_clicks.length,recoveries:result.recovery.length,blocked_api:result.blocked_api_requests.length})+'\n');}}
 finally{await browser.close();}
 const report={passed:builds.length===matrix.length&&builds.every(build=>build.passed),policy:'Internal pages/assets served by strict real HTTP mounts; no navigation/document success stubs. APIs and external requests aborted. Only deliberate malformed seed navigations explicitly expect HTTP404.',builds};fs.writeFileSync(path.join(output,'navigation-final.json'),JSON.stringify(report,null,2)+'\n');if(!report.passed)process.exitCode=1;
})().catch(error=>{fs.mkdirSync(output,{recursive:true});fs.writeFileSync(path.join(output,'navigation-failed.json'),JSON.stringify({passed:false,error:error.stack},null,2)+'\n');process.stderr.write(error.stack+'\n');process.exitCode=1;});
