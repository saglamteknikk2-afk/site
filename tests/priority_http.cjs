/* Actual mobile browser -> PHP8.2/SQLite priority checkout. No API/provider mocks. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),net=require('node:net'),crypto=require('node:crypto');
const {spawn,spawnSync}=require('node:child_process');const {chromium}=require('playwright');
const repository=path.resolve(__dirname,'..'),publicRoot=path.resolve(process.argv[2]||'build/production'),php=process.env.SAGLAM_PHP_BIN||'php',output=path.join(repository,'build/backend-qa/priority-http.json');
const checks=[],requests=[],pageErrors=[],external=[];let fixture='',server,browser,stderr='',privateRoot,origin,report;
const check=(ok,name)=>{checks.push({name,passed:!!ok});if(!ok)throw Error(name);};
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function runPHP(code,args=[]){const r=spawnSync(php,['-r',code,...args],{encoding:'utf8',env:{PATH:process.env.PATH||''}});if(r.status!==0||r.error)throw Error('PHP helper failed: '+(r.error?.message||r.stderr));return r.stdout.trim();}
function digest(dir){const h=crypto.createHash('sha256');function walk(at){for(const n of fs.readdirSync(at).sort()){const p=path.join(at,n),s=fs.lstatSync(p);if(s.isSymbolicLink())throw Error('Symlink in QA build');if(s.isDirectory())walk(p);else{h.update(path.relative(dir,p));h.update('\0');h.update(fs.readFileSync(p));}}}walk(dir);return h.digest('hex');}
async function freePort(){const s=net.createServer();await new Promise(resolve=>s.listen(0,'127.0.0.1',resolve));const port=s.address().port;await new Promise(resolve=>s.close(resolve));return port;}
function inspect(){return JSON.parse(runPHP(String.raw`$db=new PDO('sqlite:'.$argv[1]);$db->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE,PDO::FETCH_ASSOC);echo json_encode(['tickets'=>$db->query('SELECT id,name,phone,district,device,issue FROM tickets ORDER BY rowid')->fetchAll(),'acceptances'=>$db->query('SELECT * FROM priority_service_acceptances ORDER BY rowid')->fetchAll(),'outbox'=>$db->query('SELECT id,payload,sent,attempts FROM outbox ORDER BY created')->fetchAll()]);`,[path.join(privateRoot,'site.sqlite')]));}
const actionResponse=(page,action)=>page.waitForResponse(r=>new URL(r.url()).pathname==='/api.php'&&new URL(r.url()).searchParams.get('action')===action&&r.request().method()==='POST');
(async()=>{
 const initial=digest(publicRoot);
 try{
  check(['priority-service.php','review-moderation.php','service-operations.php','assets/priority-service.js'].every(name=>fs.existsSync(path.join(publicRoot,name))),'Production contains the priority backend and frontend');
  fixture=fs.mkdtempSync(path.join(os.tmpdir(),'st-priority-browser-'));fs.chmodSync(fixture,0o700);const webroot=path.join(fixture,'httpdocs');privateRoot=path.join(fixture,'private');fs.cpSync(publicRoot,webroot,{recursive:true});fs.mkdirSync(privateRoot,{mode:0o700});
  const port=await freePort();origin='http://127.0.0.1:'+port;
  fs.writeFileSync(path.join(privateRoot,'site_apileri,.txt'),['SITE_URL='+origin,'ADMIN_ACCESS_KEY='+crypto.randomBytes(24).toString('hex'),'TELEGRAM_WEBHOOK_SECRET='+crypto.randomBytes(24).toString('hex'),'TELEGRAM_ADMIN_IDS=10000001','TELEGRAM_CHAT_ID=10000002','TELEGRAM_BOT_TOKEN=','GEMINI_API_KEY=','GEMINI_API_KEY_1=','GEMINI_API_KEY_2=','GEMINI_API_KEY_3=','GEMINI_API_KEY_4=','IP_LOCATION_LOOKUP=0','VISIT_NOTIFICATIONS=0','DAILY_REPORT=0','WEEKLY_REPORT=0','MONTHLY_REPORT=0','TELEGRAM_POLLING=0'].join('\n')+'\n',{mode:0o600});
  server=spawn(php,['-d','display_errors=0','-d','log_errors=1','-S','127.0.0.1:'+port,'-t',webroot],{cwd:webroot,env:{PATH:process.env.PATH||'',SAGLAM_PRIVATE_DIR:privateRoot},stdio:['ignore','ignore','pipe']});server.stderr.on('data',b=>stderr+=b.toString());
  for(let i=0;i<100;i++){if(server.exitCode!==null)throw Error('PHP server exited: '+stderr);const ready=await new Promise(resolve=>{const socket=net.connect(port,'127.0.0.1');socket.once('connect',()=>{socket.destroy();resolve(true);});socket.once('error',()=>resolve(false));});if(ready)break;if(i===99)throw Error('PHP startup timed out');await pause(30);}
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']});const context=await browser.newContext({viewport:{width:390,height:844},serviceWorkers:'block',reducedMotion:'reduce'});
  await context.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin===origin)return route.continue();external.push(u.origin+u.pathname);return route.abort();});const page=await context.newPage();page.on('pageerror',e=>pageErrors.push(e.message));page.on('response',r=>{const u=new URL(r.url());if(u.origin===origin&&u.pathname.endsWith('.php'))requests.push({path:u.pathname,action:u.searchParams.get('action'),status:r.status(),method:r.request().method()});});
  await page.goto(origin+'/',{waitUntil:'networkidle'});await page.waitForFunction(()=>window.STPriorityTicket&&typeof stToken==='function');const csrf=await page.evaluate(()=>stToken());
  check(await page.evaluate(()=>window.ST_PREVIEW!==true),'Actual production mode is active');
  const initialDB=inspect();check(initialDB.tickets.length===0&&initialDB.acceptances.length===0&&initialDB.outbox.length===0,'Fresh fixture has no tickets, acceptances or queued messages');
  await page.locator('.usta-ticket').first().click();await page.selectOption('#ticketServiceLevel','priority');
  await page.fill('#ticketName','QA Priority Browser');await page.fill('#ticketPhone','05340000008');await page.fill('#ticketDistrict','Küçükçekmece / Atakent');await page.selectOption('#ticketDevice','Kombi');await page.fill('#ticketIssue','Sentetik gerçek PHP öncelikli servis testi.');
  check(await page.locator('#ticketPriorityFee').count()===0&&await page.locator('#ticketSubmitBtn').innerText()==='Onaya gönder','No fee is shown before contacts and the first confirmation action');
  const quoteWait=actionResponse(page,'priority-quote');await page.click('#ticketSubmitBtn');const quoteResponse=await quoteWait,quote=await quoteResponse.json(),base=quoteResponse.request().postDataJSON();
  check(quoteResponse.status()===200&&quote.ok===true&&[2500,4000].includes(quote.fee_try)&&typeof quote.priority_quote==='string','First action obtains an actual signed PHP quote');
  check(inspect().tickets.length===0&&inspect().acceptances.length===0&&inspect().outbox.length===0,'Quote action creates no service ticket, acceptance or notification');
  check(await page.locator('#ticketPriorityFee').innerText()===quote.fee_label&&await page.locator('#ticketSubmitBtn').innerText()==='Talep et','Final page visibly shows exactly the PHP fee before Talep et');
  const evidence=path.join(repository,'build');fs.mkdirSync(evidence,{recursive:true});
  await page.locator('#serviceTicketModal .ah-modal-card').screenshot({path:path.join(evidence,'priority-service-quote-mobile.png')});
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile quote review has no horizontal document overflow');
  await page.setViewportSize({width:1440,height:1000});await page.locator('#serviceTicketModal .ah-modal-card').screenshot({path:path.join(evidence,'priority-service-quote-desktop.png')});
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Desktop quote review has no horizontal document overflow');
  await page.setViewportSize({width:390,height:844});
  const api=async(payload,key)=>{const response=await context.request.post(origin+'/api.php?action=ticket',{headers:{Origin:origin,'X-CSRF-Token':csrf,'Idempotency-Key':key},data:payload});requests.push({path:'/api.php',action:'ticket',status:response.status(),method:'POST',transport:'playwright-shared-cookie-api'});return {status:response.status(),data:await response.json()};};
  const accepted={...base,priority_quote:quote.priority_quote,priority_accepted:true,priority_terms_version:quote.terms_version};
  let result=await api({...accepted,priority_accepted:false},'qa-priority-unchecked-00001');check(result.status===400&&result.data.ok===false,'Actual API rejects unchecked fee consent');
  result=await api({...accepted,priority_fee_try:1},'qa-priority-forged-fee-0001');check(result.status===400&&result.data.ok===false,'Actual API rejects a client-forged amount');
  result=await api({...accepted,district:'Avcılar'},'qa-priority-contact-edit-001');check(result.status===409&&result.data.ok===false,'Actual API rejects changed contact information under an old quote');
  check(inspect().tickets.length===0&&inspect().acceptances.length===0&&inspect().outbox.length===0,'Rejected final requests still save no ticket or notification');
  await page.click('#ticketSubmitBtn');check(inspect().tickets.length===0,'Unchecked browser control also blocks actual creation');
  await page.check('#ticketPriorityConsent');fs.mkdirSync(path.dirname(output),{recursive:true});await page.locator('#serviceTicketModal .ah-modal-card').screenshot({path:path.join(path.dirname(output),'priority-review-mobile.png')});
  const savedWait=actionResponse(page,'ticket');await page.click('#ticketSubmitBtn');const savedResponse=await savedWait,saved=await savedResponse.json(),savedPayload=savedResponse.request().postDataJSON(),idem=savedResponse.request().headers()['idempotency-key'];
  check(savedResponse.status()===201&&saved.ok===true&&saved.delivery==='queued','Final accepted click saves through real PHP with an honest queued state');
  let db=inspect();check(db.tickets.length===1&&db.acceptances.length===1&&db.outbox.length===1,'Exactly one ticket, one consent and one notification are committed');
  check(db.acceptances[0].ticket_id===saved.id&&Number(db.acceptances[0].fee_try)===quote.fee_try&&db.acceptances[0].terms_version===quote.terms_version,'Actual database binds the accepted fee and terms to the exact ticket');
  const notification=JSON.parse(db.outbox[0].payload),notificationText=notification.text||notification.caption||'';check(notificationText.includes(String(quote.fee_try))||notificationText.includes(quote.fee_label),'Owner notification includes the server-verified priority fee');
  result=await api(savedPayload,idem);check(result.status===200&&result.data.id===saved.id,'Retrying the same request key returns the original ticket');
  result=await api(savedPayload,'qa-priority-reused-quote-01');check(result.status===409&&result.data.ok===false,'A different request key cannot reuse one quote for a second ticket');
  check(inspect().tickets.length===1&&inspect().acceptances.length===1&&inspect().outbox.length===1,'Repeated requests do not duplicate the fee record or owner notification');
  const standard={name:'QA Standard Browser',phone:'05340000009',district:'Avcılar',device:'Petek',issue:'Sentetik standart servis testi.',website:''};result=await api(standard,'qa-standard-after-priority1');
  check(result.status===201&&result.data.ok===true,'Standard service remains available without any priority quote');db=inspect();
  check(db.tickets.length===2&&db.acceptances.length===1&&db.outbox.length===2,'Standard request does not inherit a priority fee');
  check(db.outbox.every(row=>Number(row.sent)===0&&Number(row.attempts)===0),'Blank provider settings make no actual delivery attempt');
  check(pageErrors.length===0&&external.length===0&&!/PHP (?:Fatal error|Warning)|Uncaught/.test(stderr),'No browser errors, external requests or PHP runtime errors');
  check(digest(publicRoot)===initial,'Original production build was not modified');
  report={passed:true,checks:checks.length,cases:checks,actual_php_requests:requests.length,requests,mock_responses:0,provider_requests:0,production_private_read:false,build_info:JSON.parse(fs.readFileSync(path.join(publicRoot,'build-info.json'),'utf8')),scope:'Actual mobile priority checkout, signed PHP quotes, invalid consent/amount/contact rejection, SQLite atomic acceptance, idempotency and standard-service regression. Blank provider keys; no live notification.'};
 }catch(error){process.exitCode=1;report={passed:false,checks:checks.length,cases:checks,error:error.message,page_errors:pageErrors,requests,php_errors:stderr.match(/.*(?:PHP (?:Fatal|Warning)|Uncaught).*/g)||[]};console.error(error.stack);}
 finally{if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await Promise.race([new Promise(resolve=>server.once('exit',resolve)),pause(1000)]);}if(fixture)fs.rmSync(fixture,{recursive:true,force:true});fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');}
 console.log(JSON.stringify({passed:report.passed,checks:report.checks,actual_php_requests:report.actual_php_requests,report:path.relative(repository,output)}));
})();
