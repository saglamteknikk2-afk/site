/* Local routing regression: real DOM clicks, every request intercepted, no publishing. */
'use strict';
const {chromium}=require('playwright');
const fs=require('fs'),os=require('os'),path=require('path'),{spawnSync}=require('child_process');
const repository=path.resolve(__dirname,'..');
const output=process.env.SAGLAM_ROUTE_REPORT||path.join(repository,'build/runtime-route-check.json');
const origin='https://runtime-routing.test';
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.woff2':'font/woff2','.ttf':'font/ttf'};
const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'saglam-routing-'));
const cases=process.env.SAGLAM_ROUTE_CASES?JSON.parse(process.env.SAGLAM_ROUTE_CASES):[
 {name:'preview-site',mode:'preview',prefix:'/site'},
 {name:'preview-root',mode:'preview',prefix:''},
 {name:'preview-custom-nested',mode:'preview',prefix:'/qa-preview/nested'},
 {name:'production-root',mode:'production',prefix:''}
];
function build(item){
 if(item.directory)return path.resolve(item.directory);
 const directory=path.join(temporary,item.name);
 const result=spawnSync('python',[path.join(repository,'scripts/build_site.py'),'--mode',item.mode,'--output',directory,'--base-path',item.prefix||'/'],{encoding:'utf8'});
 if(result.status!==0)throw Error('Build failed for '+item.name+': '+result.stderr);
 return directory;
}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const report={passed:false,scope:'Local generated files only; all requests intercepted; no API, messaging or publishing',cases:[]};
 try{
  for(const item of cases){
   const directory=build(item),home=origin+item.prefix+'/',inner=home+'kombi-servisi.html';
   const context=await browser.newContext({viewport:{width:1440,height:1000},serviceWorkers:'block',reducedMotion:'reduce'});
   const page=await context.newPage();const checks=[],errors=[],missing=[];let apiMocks=0;
   const check=(name,passed)=>{checks.push({name,passed:!!passed});if(!passed)throw Error(item.name+': '+name);};
   const itemReport={name:item.name,mode:item.mode,prefix:item.prefix||'/',passed:false,checks,errors,missing,mockedAPICalls:0};report.cases.push(itemReport);
   page.on('pageerror',error=>errors.push(error.message));
   await context.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(url.origin!==origin)return route.abort();
    if(url.pathname.endsWith('.php')){apiMocks++;return route.fulfill({contentType:'application/json',body:JSON.stringify({ok:true,csrf:'local-routing-test',reviews:[],items:[]})});}
    const prefix=item.prefix+'/';
    if(!url.pathname.startsWith(prefix)){missing.push(url.pathname);return route.fulfill({status:404,body:'Outside the configured local build base'});}
    const relative=decodeURIComponent(url.pathname.slice(prefix.length))||'index.html',file=path.resolve(directory,relative);
    if(!file.startsWith(directory+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){missing.push(url.pathname);return route.fulfill({status:404,body:'Not found in generated test build'});}
    return route.fulfill({path:file,contentType:mime[path.extname(file)]||'application/octet-stream'});
   });
   const entries=[
    ['header fault guide',()=>page.locator('.premium-header .at-nav a').filter({hasText:/^Arızanı bul$/}),home+'#ai-usta'],
    ['header AI Usta',()=>page.locator('.premium-header .premium-ai-link'),home+'#ai-usta'],
    ['footer AI Usta',()=>page.locator('.premium-footer a').filter({hasText:/^AI Usta$/}),home+'#ai-usta'],
    ['header home brand',()=>page.locator('.premium-header .premium-brand'),home],
    ['footer home brand',()=>page.locator('.premium-footer .premium-footer-brand'),home]
   ];
   for(const [label,locator,expected]of entries){
    const response=await page.goto(inner,{waitUntil:'networkidle'});check(label+' starts on existing inner page',response.status()===200);
    const anchor=locator();check(label+' retains built href',await anchor.getAttribute('href')===new URL(expected).pathname+new URL(expected).hash);
    await anchor.click();await page.waitForURL(expected,{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>window.STUstaWizard);
    check(label+' click reaches home assistant',page.url()===expected&&await page.locator('#aiUstaWizard').count()===1);
   }
   for(const device of ['Kombi','Klima','Petek']){
    await page.locator(`.p-hero [data-usta-device="${device}"]`).click();
    check(device+' shortcut prefills the same widget',await page.evaluate(device=>{const current=STUstaWizard.getContext();return current.device===device&&current.step===1;},device));
   }
   await page.goto(home,{waitUntil:'networkidle'});
   // Exercise the existing fallback without opening a modal or submitting a form.
   await page.evaluate(()=>{window.toggleServiceTicketModal=undefined;});
   await page.locator('[data-ticket-open]').first().click();await page.waitForURL(home+'#servis-talebi');
   check('ticket fallback uses built home anchor',page.url()===home+'#servis-talebi');
   check('no generated route was missing '+JSON.stringify(missing),missing.length===0);
   check('no JavaScript error',errors.length===0);
   itemReport.mockedAPICalls=apiMocks;itemReport.passed=true;
   await context.close();
  }
  report.passed=true;
 }catch(error){report.error=error.message;throw error;}
 finally{
  await browser.close();fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({passed:report.passed,cases:report.cases.map(item=>({name:item.name,checks:item.checks.length,missing:item.missing.length,errors:item.errors.length})),error:report.error,report:output},null,2));
 }
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
