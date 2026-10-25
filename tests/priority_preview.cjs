/* Real generated /site preview, including its CSP and submit guard. No PHP mocks. */
'use strict';
const fs=require('node:fs'),path=require('node:path');const {chromium}=require('playwright');const {startServer}=require('./interaction_http.cjs');
const repository=path.resolve(__dirname,'..'),directory=path.resolve(process.argv[2]||'_site'),base=process.argv[3]||'/site',reportPath=path.join(repository,'build/priority-preview-browser.json');
(async()=>{
 const start=JSON.parse(fs.readFileSync(path.join(directory,'build-info.json'),'utf8')),server=await startServer(directory,base),browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']}),page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block'}),checks=[],api=[],external=[],errors=[];
 const check=(ok,name)=>{checks.push({name,passed:!!ok});if(!ok)throw Error(name);};let report;
 try{
  await page.route('**/*',route=>{const url=new URL(route.request().url());if(url.origin!==server.origin){external.push(url.href);return route.abort();}if(/\.php(?:$|\/)/i.test(url.pathname)){api.push({path:url.pathname,method:route.request().method()});return route.abort();}return route.continue();});
  page.on('pageerror',error=>errors.push(error.message));await page.goto(server.origin+base+'/',{waitUntil:'networkidle'});await page.waitForFunction(()=>window.STPriorityTicket);
  check(await page.evaluate(()=>window.ST_PREVIEW===true&&document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content.includes('form-action')),'Full built preview has its actual guard and restrictive CSP');
  await page.locator('.usta-ticket').first().click();await page.selectOption('#ticketServiceLevel','priority');
  await page.fill('#ticketName','QA Önizleme');await page.fill('#ticketPhone','05340000000');await page.fill('#ticketDistrict','Küçükçekmece');await page.fill('#ticketIssue','Sentetik öncelikli servis önizleme denemesi.');
  check(await page.locator('#ticketPriorityFee').count()===0&&await page.locator('#ticketSubmitBtn').innerText()==='Onaya gönder','No fee appears on the initial preview contact form');
  await page.click('#ticketSubmitBtn');await page.locator('#ticketPriorityFee').waitFor();
  check(['2.500 TL','4.000 TL'].includes(await page.locator('#ticketPriorityFee').innerText()),'First action shows the configured design fee through the real preview guard');
  check(await page.locator('#ticketSubmitBtn').innerText()==='Talep et'&&!await page.isChecked('#ticketPriorityConsent'),'Final preview action is explicit and requires fresh consent');
  await page.check('#ticketPriorityConsent');await page.click('#ticketSubmitBtn');
  check(/kaydedilmedi.*gönderilmedi/.test(await page.locator('#ticketPriorityReview [data-preview-status]').innerText()),'Final preview clearly says the request was not saved or sent');
  check(await page.locator('#ticketSuccessMsg').isHidden(),'Preview does not show a fake successful service record');
  check(api.length===0&&external.length===0,'Neither quote nor final action contacts a real API or external service');
  check(errors.length===0&&server.errors.length===0,'No JavaScript or static HTTP errors');
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile preview has no horizontal overflow');
  const end=JSON.parse(fs.readFileSync(path.join(directory,'build-info.json'),'utf8'));check(start.content_sha256===end.content_sha256,'Preview build stayed unchanged during the check');
  report={passed:true,checks:checks.length,cases:checks,api_requests:api,external_requests:external,page_errors:errors,server_errors:server.errors,build_start:start,build_end:end,mock_responses:0,provider_requests:0};
 }catch(error){process.exitCode=1;report={passed:false,error:error.message,checks:checks.length,cases:checks,api_requests:api,external_requests:external,page_errors:errors,server_errors:server.errors};console.error(error.stack);}
 finally{await browser.close();await server.close();fs.mkdirSync(path.dirname(reportPath),{recursive:true});fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');}
 console.log(JSON.stringify({passed:report.passed,checks:report.checks,api_requests:api.length,mock_responses:0,report:path.relative(repository,reportPath)}));
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
