/* Actual owner mobile UI and PHP/SQLite. Synthetic private config, zero provider keys. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),net=require('node:net'),crypto=require('node:crypto');
const {spawn,spawnSync}=require('node:child_process'),{chromium}=require('playwright');
const root=path.resolve(__dirname,'..'),publicRoot=path.resolve(process.argv[2]||'build/production'),php=process.env.SAGLAM_PHP_BIN||'php';
const checks=[],requests=[],errors=[],external=[];let fixture,privateRoot,webroot,server,browser,origin='',stderr='';
function check(ok,name){checks.push({name,passed:!!ok});if(!ok)throw Error(name);}
function phpJSON(code,args=[]){const r=spawnSync(php,['-r',code,...args],{encoding:'utf8',env:{PATH:process.env.PATH||''}});if(r.error||r.status!==0)throw Error(r.error?.message||r.stderr);return JSON.parse(r.stdout);}
function inspect(){return phpJSON(String.raw`$db=new PDO('sqlite:'.$argv[1]);$db->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE,PDO::FETCH_ASSOC);echo json_encode(['tickets'=>(int)$db->query('SELECT count(*) FROM tickets')->fetchColumn(),'operations'=>$db->query('SELECT ticket_id,status,service_level,routing_confirmed FROM ticket_operations ORDER BY rowid')->fetchAll(),'acceptances'=>(int)$db->query('SELECT count(*) FROM priority_service_acceptances')->fetchColumn(),'events'=>(int)$db->query('SELECT count(*) FROM ticket_operation_events')->fetchColumn(),'outbox'=>(int)$db->query('SELECT count(*) FROM outbox')->fetchColumn(),'sent'=>(int)$db->query('SELECT count(*) FROM outbox WHERE sent<>0')->fetchColumn()]);`,[path.join(privateRoot,'site.sqlite')]);}
async function freePort(){const s=net.createServer();await new Promise(resolve=>s.listen(0,'127.0.0.1',resolve));const p=s.address().port;await new Promise(resolve=>s.close(resolve));return p;}
(async()=>{
 let report;
 try{
  check(fs.existsSync(path.join(publicRoot,'service-operations.php')),'Built production contains service operations backend');
  fixture=fs.mkdtempSync(path.join(os.tmpdir(),'st-operations-browser-'));fs.chmodSync(fixture,0o700);webroot=path.join(fixture,'public');privateRoot=path.join(fixture,'private');fs.cpSync(publicRoot,webroot,{recursive:true});fs.mkdirSync(privateRoot,{mode:0o700});
  const port=await freePort();origin='http://127.0.0.1:'+port;const admin=crypto.randomBytes(24).toString('hex');
  fs.writeFileSync(path.join(privateRoot,'site_apileri,.txt'),['SITE_URL='+origin,'ADMIN_ACCESS_KEY='+admin,'TELEGRAM_BOT_TOKEN=','TELEGRAM_CHAT_ID=10000002','TELEGRAM_ADMIN_IDS=10000001','TELEGRAM_WEBHOOK_SECRET='+crypto.randomBytes(24).toString('hex'),'GEMINI_API_KEY=','GEMINI_API_KEY_1=','GEMINI_API_KEY_2=','GEMINI_API_KEY_3=','GEMINI_API_KEY_4=','IP_LOCATION_LOOKUP=0','VISIT_NOTIFICATIONS=0','DAILY_REPORT=0','TELEGRAM_POLLING=0'].join('\n')+'\n',{mode:0o600});
  server=spawn(php,['-d','display_errors=0','-S','127.0.0.1:'+port,'-t',webroot],{env:{PATH:process.env.PATH||'',SAGLAM_PRIVATE_DIR:privateRoot},stdio:['ignore','ignore','pipe']});server.stderr.on('data',data=>stderr+=data.toString());
  for(let i=0;i<100;i++){if(server.exitCode!==null)throw Error('Local PHP startup failed');const ok=await new Promise(resolve=>{const c=net.connect(port,'127.0.0.1');c.once('connect',()=>{c.destroy();resolve(true);});c.once('error',()=>resolve(false));});if(ok)break;await new Promise(resolve=>setTimeout(resolve,30));}
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']});const page=await browser.newPage({viewport:{width:390,height:844},serviceWorkers:'block',reducedMotion:'reduce'});
  await page.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin!==origin){external.push(u.origin);return route.abort();}return route.continue();});page.on('pageerror',e=>errors.push(e.message));
  const ownerResponse=()=>page.waitForResponse(r=>new URL(r.url()).pathname==='/yonetim-api.php'&&new URL(r.url()).searchParams.get('action')==='state');
  await page.goto(origin+'/owner-admin.html');check(await page.locator('#ownerLogin').isVisible()&&await page.locator('#ownerPanel').isHidden(),'Unauthenticated owner screen contains no visible private records');
  await page.fill('#ownerKey',admin);let pending=ownerResponse();await page.locator('#ownerLoginForm button').click();check((await pending).status()===200,'Actual owner API authenticates with synthetic private key');await page.locator('#ownerPanel').waitFor({state:'visible'});
  check((await page.locator('#ownerOperationCounts').innerText()).includes('Açık kayıt: 0'),'Empty owner panel shows no fabricated service queue');
  const bootstrap=await page.request.get(origin+'/api.php?action=bootstrap');const csrf=(await bootstrap.json()).csrf;check(typeof csrf==='string'&&csrf.length>32,'Actual API issues a session-bound CSRF token');
  async function api(action,data,key){const r=await page.request.post(origin+'/api.php?action='+action,{headers:{Origin:origin,'X-CSRF-Token':csrf,...(key?{'Idempotency-Key':key}:{})},data});const body=await r.json();requests.push({action,status:r.status(),ok:body.ok});return {status:r.status(),body};}
  const ticket={name:'QA İlk Kayıt',phone:'05340000000',district:'Bağcılar / Güneşli',device:'Kombi',issue:'Sentetik operasyon tarayıcı servis kaydı.'};
  const first=await api('ticket',ticket,'op-browser-first-00001');check(first.status===201&&first.body.queue.ahead===0,'Actual standard request is persisted with truthful initial district position');
  const priority={...ticket,name:'QA Öncelikli',service_level:'priority'};const quote=await api('priority-quote',priority);check(quote.status===200&&quote.body.priority_quote,'Actual priority quote comes from local PHP');
  check(inspect().tickets===1&&inspect().operations.length===1,'Quote alone adds no second ticket or queue record');
  const second=await api('ticket',{...priority,priority_accepted:true,priority_quote:quote.body.priority_quote,priority_terms_version:quote.body.terms_version},'op-browser-priority-01');check(second.status===201&&second.body.queue.ahead===1&&!second.body.queue.priority_confirmed,'Accepted customer fee alone does not bypass an earlier standard request');
  check(inspect().tickets===2&&inspect().acceptances===1,'Real API commits exactly two requests and one signed fee acceptance');
  pending=ownerResponse();await page.locator('#ownerRefresh').click();await pending;await page.waitForFunction(()=>document.querySelectorAll('#ownerTickets .row').length===2);
  check((await page.locator('#ownerRoute').innerText()).includes('Bağcılar')&&(await page.locator('#ownerOperationCounts').innerText()).includes('Açık kayıt: 2'),'Owner mobile UI groups actual requests under the canonical district');
  check((await page.locator('#ownerTickets').innerText()).includes('Müşterinin kabul ettiği hizmet bedeli'),'Priority row shows the actual accepted fee to the owner');
  async function status(id,value){const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/yonetim-api.php'&&new URL(r.url()).searchParams.get('action')==='ticket-status');await page.locator('[data-ticket-id="'+id+'"][data-ticket-status="'+value+'"]').click();const r=await response;const body=await r.json();requests.push({action:'ticket-status',status:r.status(),ok:body.ok});await page.waitForFunction(({id,value})=>!document.querySelector('[data-ticket-id="'+id+'"][data-ticket-status="'+value+'"]'),{id,value});return {status:r.status(),body};}
  let update=await status(second.body.id,'accepted');check(update.status===200&&update.body.queue.priority_confirmed&&update.body.queue.ahead===0,'Aldım button persists operator acceptance and only then prioritizes the request');
  update=await status(second.body.id,'en_route');check(update.status===200&&inspect().operations.find(r=>r.ticket_id===second.body.id).status==='en_route','Yoldayım button persists real field status');
  update=await status(second.body.id,'completed');check(update.status===200&&inspect().operations.find(r=>r.ticket_id===second.body.id).status==='completed','Tamamlandı button closes the actual operation');
  check(!await page.locator('[data-ticket-id="'+second.body.id+'"]').count(),'Completed operation has no stale mutable status controls');
  check((await page.locator('#ownerOperationCounts').innerText()).includes('Açık kayıt: 1'),'Closing one operation removes exactly that job from active group');
  update=await status(first.body.id,'cancelled');check(update.status===200&&inspect().operations.every(r=>['completed','cancelled'].includes(r.status)),'İptal closes the remaining request and preserves history');
  check((await page.locator('#ownerOperationCounts').innerText()).includes('Açık kayıt: 0'),'Owner queue returns to empty after both real records are closed');
  check(inspect().events===4&&inspect().sent===0,'Four status transitions are durable and no provider delivery is invented');
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Owner dashboard fits390pixel mobile screen without horizontal overflow');
  check(errors.length===0&&external.length===0,'Owner journey has no browser errors or external provider requests');
  report={passed:true,checks:checks.length,cases:checks,requests,provider_requests:0,api_mocks:0,page_errors:errors,external_requests:external};
 }catch(error){report={passed:false,checks:checks.length,cases:checks,error:error.stack,requests,page_errors:errors,external_requests:external,server_tail:stderr.slice(-1200)};process.exitCode=1;}
 finally{if(browser)await browser.close();if(server)server.kill();if(fixture)fs.rmSync(fixture,{recursive:true,force:true});const reportPath=path.join(root,'build/backend-qa/service-operations-browser.json');fs.mkdirSync(path.dirname(reportPath),{recursive:true});fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,checks:report.checks,error:report.error}));}
})();
