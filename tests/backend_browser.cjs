/* Real browser -> real local PHP. Synthetic private data only; no API mocks.
 * Usage: SAGLAM_PHP_BIN=php CHROMIUM_BIN=/usr/bin/chromium node tests/backend_browser.cjs build/production
 */
'use strict';
const fs=require('fs'),path=require('path'),os=require('os'),net=require('net'),crypto=require('crypto');
const {spawn,spawnSync}=require('child_process');
const {chromium}=require('playwright');
const repository=path.resolve(__dirname,'..');
const publicRoot=path.resolve(process.argv[2]||path.join(repository,'build/production'));
const reportPath=path.join(repository,'build/backend-qa/backend-browser.json');
const php=process.env.SAGLAM_PHP_BIN||'php';
const checks=[],requests=[],blocked=[],pageErrors=[],localFailures=[],responseTasks=[];
let fixture='',server,browser,origin='',stderr='',beforeHash='';
function check(ok,name){checks.push({name,passed:!!ok});if(!ok)throw Error(name);}
function runPHP(args){const r=spawnSync(php,args,{encoding:'utf8',env:{PATH:process.env.PATH||''}});if(r.error||r.status!==0)throw Error('PHP helper failed: '+(r.error?.message||r.stderr));return r.stdout.trim();}
function snapshot(directory){const hash=crypto.createHash('sha256');let count=0;function walk(dir){for(const name of fs.readdirSync(dir).sort()){const file=path.join(dir,name),stat=fs.lstatSync(file);if(stat.isSymbolicLink())throw Error('Public QA input must not contain symlinks');if(stat.isDirectory())walk(file);else if(stat.isFile()){hash.update(path.relative(directory,file));hash.update('\0');hash.update(fs.readFileSync(file));hash.update('\0');count++;}}}walk(directory);return {sha256:hash.digest('hex'),files:count};}
async function freePort(){return new Promise((resolve,reject)=>{const socket=net.createServer();socket.once('error',reject);socket.listen(0,'127.0.0.1',()=>{const port=socket.address().port;socket.close(()=>resolve(port));});});}
async function waitForServer(port){for(let i=0;i<100;i++){if(server.exitCode!==null)throw Error('PHP server exited: '+stderr);const ready=await new Promise(resolve=>{const socket=net.connect(port,'127.0.0.1');socket.once('connect',()=>{socket.destroy();resolve(true);});socket.once('error',()=>resolve(false));});if(ready)return;await new Promise(resolve=>setTimeout(resolve,30));}throw Error('PHP loopback startup timed out');}
function inspect(){return JSON.parse(runPHP(['-r',String.raw`$db=new PDO('sqlite:'.$argv[1]);$db->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE,PDO::FETCH_ASSOC);echo json_encode(['tickets'=>$db->query('SELECT id,name,phone,district,device,issue,notification_sent FROM tickets ORDER BY created,rowid')->fetchAll(),'reviews'=>$db->query('SELECT id,author,comment,status FROM reviews ORDER BY created,rowid')->fetchAll(),'outbox_count'=>(int)$db->query('SELECT count(*) FROM outbox')->fetchColumn(),'notification_attempts'=>(int)$db->query('SELECT count(*) FROM outbox WHERE sent<>0 OR attempts<>0 OR lease<>0')->fetchColumn()]);`,path.join(fixture,'private/site.sqlite')]));}
function apiResponse(page,action){return page.waitForResponse(response=>new URL(response.url()).pathname==='/api.php'&&new URL(response.url()).searchParams.get('action')===action&&response.request().method()==='POST');}
async function savedResponse(promise,name){const response=await promise,data=await response.json();check(response.status()===201&&data.ok===true&&/^[a-f0-9]{24}$/.test(data.id||'')&&data.delivery==='queued',name+' really saves through PHP with queued notification');return data;}
async function visibleText(page,selector,pattern){await page.waitForFunction(({selector,source})=>{const el=document.querySelector(selector);return el&&!el.hidden&&!el.classList.contains('hidden')&&new RegExp(source,'i').test(el.textContent);},{selector,source:pattern.source});}
(async()=>{
 let report;
 try{
  check(fs.existsSync(path.join(publicRoot,'api.php'))&&fs.existsSync(path.join(publicRoot,'index.html')),'Production HTML/assets/PHP build exists');
  const original=snapshot(publicRoot);beforeHash=original.sha256;
  const version=runPHP(['-r','echo PHP_VERSION;']);
  check(JSON.parse(runPHP(['-r','echo json_encode(PDO::getAvailableDrivers());'])).includes('sqlite'),'Selected PHP engine supports SQLite');
  fixture=fs.mkdtempSync(path.join(os.tmpdir(),'st-browser-php-'));fs.chmodSync(fixture,0o700);
  const webroot=path.join(fixture,'httpdocs'),privateRoot=path.join(fixture,'private');
  fs.cpSync(publicRoot,webroot,{recursive:true});fs.mkdirSync(privateRoot,{mode:0o700});
  const port=await freePort();origin='http://127.0.0.1:'+port;
  const admin=crypto.randomBytes(24).toString('hex');
  fs.writeFileSync(path.join(privateRoot,'site_apileri,.txt'),['SITE_URL='+origin,'ADMIN_ACCESS_KEY='+admin,'TELEGRAM_WEBHOOK_SECRET='+crypto.randomBytes(24).toString('hex'),'TELEGRAM_ADMIN_IDS=10000001','TELEGRAM_CHAT_ID=10000002','TELEGRAM_BOT_TOKEN=','GEMINI_API_KEY=','GEMINI_API_KEY_1=','GEMINI_API_KEY_2=','GEMINI_API_KEY_3=','GEMINI_API_KEY_4=','IP_LOCATION_LOOKUP=0','VISIT_NOTIFICATIONS=0','DAILY_REPORT=0','TELEGRAM_POLLING=0'].join('\n')+'\n',{mode:0o600});
  // Explicit environment prevents inherited provider credentials from entering PHP.
  server=spawn(php,['-d','display_errors=0','-d','log_errors=1','-S','127.0.0.1:'+port,'-t',webroot],{cwd:webroot,env:{PATH:process.env.PATH||'',SAGLAM_PRIVATE_DIR:privateRoot},stdio:['ignore','ignore','pipe']});
  server.stderr.on('data',data=>{stderr+=data.toString();});server.on('error',error=>{stderr+=error.message;});
  await waitForServer(port);
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']});
  const context=await browser.newContext({viewport:{width:1440,height:1000},serviceWorkers:'block',reducedMotion:'reduce'});
  await context.route('**/*',route=>{const url=new URL(route.request().url());if(url.origin===origin)return route.continue();blocked.push(url.origin+url.pathname);return route.abort();});
  const page=await context.newPage();page.on('pageerror',error=>pageErrors.push(error.message));
  page.on('response',response=>{const url=new URL(response.url());if(url.origin===origin&&response.status()>=400)localFailures.push({path:url.pathname,status:response.status()});if(url.origin===origin&&url.pathname.endsWith('.php'))responseTasks.push((async()=>{const headers=response.request().headers(),action=url.searchParams.get('action')||'';let data=null;try{data=await response.json();}catch(_){}requests.push({path:url.pathname,action,method:response.request().method(),status:response.status(),csrf_valid_shape:/^\d+\.[a-f0-9]{64}$/.test(headers['x-csrf-token']||''),idempotency_present:!!headers['idempotency-key'],source:data?.source||undefined,pending:data?.status==='pending',bootstrap_token_valid:action==='bootstrap'?/^\d+\.[a-f0-9]{64}$/.test(data?.csrf||''):undefined});})());});
  await page.goto(origin+'/',{waitUntil:'networkidle'});
  await page.waitForFunction(()=>typeof stToken==='function'&&window.STUstaWizard);
  check(await page.evaluate(()=>window.ST_PREVIEW!==true&&document.body.dataset.stMode!=='preview'),'Copied page runs in production mode, without preview API simulation');
  const csrf=await page.evaluate(()=>stToken());
  check(/^\d+\.[a-f0-9]{64}$/.test(csrf),'Browser obtains a real PHP CSRF bootstrap token');
  const cookie=(await context.cookies(origin)).find(cookie=>cookie.name==='st_session');
  check(cookie?.httpOnly&&cookie.sameSite==='Strict','Actual browser stores HttpOnly SameSite Strict session cookie');
  // Submit the actual homepage service form.
  await page.locator('[data-ticket-open]').first().click();
  await page.locator('#ticketName').fill('QA Browser Modal');await page.locator('#ticketPhone').fill('05340000001');
  await page.locator('#ticketDistrict').fill('Küçükçekmece / Atakent');await page.locator('#ticketDevice').selectOption('Kombi');
  await page.locator('#ticketIssue').fill('Sentetik tarayıcı testi: sıcak su dalgalanıyor.');
  const modalResponse=apiResponse(page,'ticket');await page.locator('#ticketSubmitBtn').click();
  const modal=await savedResponse(modalResponse,'Homepage service modal');await visibleText(page,'#ticketSuccessMsg',/kaydedildi/);
  check(inspect().tickets.some(row=>row.id===modal.id&&row.name==='QA Browser Modal'&&row.notification_sent===0),'Modal form fields are persisted in isolated SQLite, not marked delivered');
  // A second, independent frontend serializer: contact form.
  await page.goto(origin+'/iletisim.html',{waitUntil:'networkidle'});
  await page.locator('#contactName').fill('QA Browser Contact');await page.locator('#contactPhone').fill('05340000002');
  await page.locator('#contactDistrict').fill('Avcılar');await page.locator('#contactDevice').selectOption('Klima');
  await page.locator('#contactModel').fill('Sentetik model bilgisi');await page.locator('#contactIssue').fill('Sentetik test: klima soğutmuyor.');
  const contactResponse=apiResponse(page,'ticket');await page.locator('#contactSubmit').click();
  const contact=await savedResponse(contactResponse,'Contact form');await visibleText(page,'#contactStatus',/kaydedildi/);
  check(inspect().tickets.some(row=>row.id===contact.id&&row.device==='Klima'&&row.issue.includes('Sentetik model bilgisi')&&row.district==='Avcılar'),'Contact serializer preserves device, model, symptom and location');
  // Third frontend serializer: selector summary -> actual service request.
  await page.goto(origin+'/servis-sec.html#cihaz=kombi&ilce=K%C3%BC%C3%A7%C3%BCk%C3%A7ekmece&mahalle=Atakent&marka=Baymak',{waitUntil:'networkidle'});
  await page.waitForFunction(()=>document.querySelector('#svcBrand')?.value==='Baymak');
  check(await page.locator('#svcDistrict').inputValue()==='Küçükçekmece'&&await page.locator('#svcNeighborhood').inputValue()==='Atakent','Real selector honors district/neighborhood/brand deep link');
  await page.locator('#svcOptions').evaluate(el=>el.open=true);
  await page.locator('#svcModel').fill('Sentetik model');await page.locator('#svcDetail').fill('Sentetik seçim ekranı talebi.');
  await page.locator('#svcRecord').click();await page.locator('#svcName').fill('QA Browser Selector');await page.locator('#svcPhone').fill('05340000003');
  const selectorResponse=apiResponse(page,'ticket');await page.locator('#svcTicketButton').click();
  const selector=await savedResponse(selectorResponse,'Service selector');await visibleText(page,'#svcTicketStatus',/kaydedildi/);
  check(inspect().tickets.some(row=>row.id===selector.id&&row.district==='Küçükçekmece / Atakent'&&row.issue.includes('Baymak')&&row.issue.includes('Sentetik model')),'Selector submits its actual brand/model/location summary to PHP');
  check(inspect().tickets.length===3,'Three UI journeys create exactly three distinct tickets');
  // Submit a genuine pending review, approve through actual owner PHP, then reload.
  await page.goto(origin+'/',{waitUntil:'networkidle'});
  const author='QA Browser Review',comment='Yalnızca izole test veritabanındaki sentetik tarayıcı yorumu.';
  await page.locator('#yorumIsim').fill(author);await page.locator('#yorumIlce').fill('Küçükçekmece');
  await page.locator('#yorumHizmet').selectOption('Kombi Bakımı / Onarımı');await page.locator('#yorumPuan').selectOption('5');
  await page.locator('#yorumMetni').fill(comment);await page.locator('#yorumYayinOnayi').check();
  const reviewResponse=apiResponse(page,'review');await page.locator('#yorumGonderBtn').click();
  const review=await savedResponse(reviewResponse,'Review form');await visibleText(page,'#yorumOnayMsg',/incelemeye|onay/);
  check(review.status==='pending'&&inspect().reviews.find(row=>row.id===review.id)?.status==='pending','UI review is pending in actual SQLite');
  check(!((await page.locator('#reviewsContainer').innerText()).includes(comment)),'Pending review is not displayed by the actual frontend');
  const publicBefore=await context.request.get(origin+'/api.php?action=reviews');
  requests.push({path:'/api.php',action:'reviews',method:'GET',status:publicBefore.status(),transport:'playwright-shared-cookie-api-context'});
  check(!(await publicBefore.json()).reviews.some(row=>row.id===review.id),'Actual public reviews endpoint excludes pending review');
  const ownerCsrf=await page.evaluate(()=>stToken());
  const approved=await context.request.post(origin+'/yonetim-api.php?action=decide',{headers:{Origin:origin,'X-CSRF-Token':ownerCsrf,'X-Admin-Key':admin},data:{id:review.id,status:'approved'}});
  requests.push({path:'/yonetim-api.php',action:'decide',method:'POST',status:approved.status(),csrf_valid_shape:/^\d+\.[a-f0-9]{64}$/.test(ownerCsrf),transport:'playwright-shared-cookie-api-context'});
  check(approved.status()===200&&inspect().reviews.find(row=>row.id===review.id)?.status==='approved','Actual authenticated owner endpoint approves synthetic pending review');
  await page.reload({waitUntil:'networkidle'});
  await page.waitForFunction(comment=>document.querySelector('#reviewsContainer')?.textContent.includes(comment),comment);
  check(await page.locator('.pr-review').filter({hasText:comment}).count()===1,'Reloaded real frontend renders approved review exactly once');
  // Explicit AI opt-in against real PHP with every provider key empty.
  await page.locator('.p-device-shortcuts [data-usta-device="Klima"]').click();
  await page.locator('#ustaStep [data-choice="cool"]').click();await page.locator('#ustaStep [data-brand=""]').click();
  await page.waitForFunction(()=>STUstaWizard.getContext().step===4);
  check(await page.locator('#aiResponseText').innerText().then(text=>text.trim().length>40),'Local symptom guide is useful before any AI submission');
  await Promise.all(responseTasks);
  check(!requests.some(row=>row.action==='ai'),'Guided local answer performs no automatic AI request');
  const aiResponse=apiResponse(page,'ai');await page.locator('#askBtn').click();const ai=await aiResponse,aiData=await ai.json();
  check(ai.status()===200&&aiData.source==='guide'&&String(aiData.text||'').length>40,'Explicit AI request reaches actual PHP and returns safe no-key fallback');
  await page.waitForFunction(()=>document.querySelector('#aiLoading').classList.contains('hidden')&&!document.querySelector('#askBtn').disabled);
  check((await page.locator('#aiSource').innerText()).includes('Belirti rehberi')&&(await page.locator('#aiResponseText').innerText()).trim().length>40,'No-key backend fallback is rendered through the actual UI result contract');
  await Promise.all(responseTasks);
  const formPosts=requests.filter(row=>row.method==='POST'&&['ticket','review','ai'].includes(row.action));
  check(formPosts.length===5&&formPosts.every(row=>row.csrf_valid_shape),'All five UI submissions use actual session-bound CSRF tokens');
  check(formPosts.filter(row=>['ticket','review'].includes(row.action)).every(row=>row.idempotency_present),'All UI record submissions send idempotency keys');
  check(requests.some(row=>row.action==='bootstrap'&&row.bootstrap_token_valid),'Browser actually requested PHP bootstrap; no synthetic response');
  const stored=inspect();check(stored.notification_attempts===0&&stored.outbox_count>=4,'Notifications remain durable, unsent and unattempted; no worker runs');
  check(pageErrors.length===0,'No JavaScript page errors in real frontend/backend journeys');
  check(localFailures.length===0,'No failed local HTTP responses during joined UI journeys');
  check(blocked.length===0,'Frontend did not attempt external provider/navigation requests');
  check(!/PHP (?:Fatal|Warning)|Uncaught/.test(stderr),'PHP produced no warnings or fatal errors');
  const after=snapshot(publicRoot);check(after.sha256===beforeHash,'Production build stayed frozen throughout joined QA');
  report={passed:true,php:version,checks:checks.length,cases:checks,production_snapshot:{...original,path:path.relative(repository,publicRoot)},production_frozen:true,actual_requests:requests,actual_php_requests:requests.length,mock_responses:0,external_browser_requests:blocked,provider_requests:0,notification_delivery_attempts:0,production_private_read:false,persisted_tickets:stored.tickets.length,persisted_reviews:stored.reviews.length,scope:'Copied production HTML/assets/PHP, real loopback browser and SQLite, synthetic private configuration, blank provider keys; no live credential/delivery validation'};
 }catch(error){report={passed:false,error:error.message,checks:checks.length,cases:checks,production_snapshot:{sha256:beforeHash},actual_requests:requests,mock_responses:0,page_errors:pageErrors,local_failures:localFailures,external_browser_requests:blocked,php_error_excerpt:stderr.match(/.*(?:PHP (?:Fatal|Warning)|Uncaught).*/g)||[]};process.stderr.write(error.stack+'\n');process.exitCode=1;
 }finally{
  if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{server.once('exit',resolve);setTimeout(resolve,1000);});}
  if(fixture)fs.rmSync(fixture,{recursive:true,force:true});fs.mkdirSync(path.dirname(reportPath),{recursive:true});fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');
 }
 process.stdout.write(JSON.stringify({passed:report.passed,checks:report.checks,actual_php_requests:report.actual_php_requests,mock_responses:0,report:path.relative(repository,reportPath)})+'\n');
})().catch(error=>{process.stderr.write(error.stack+'\n');process.exitCode=1;});
