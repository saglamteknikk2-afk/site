/* Actual owner UI -> isolated PHP/SQLite; blank provider keys, no API mocks.
 * SAGLAM_PHP_BIN=/path/to/php node tests/owner_browser.cjs build/production
 */
'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),net=require('node:net'),crypto=require('node:crypto');
const {spawn,spawnSync}=require('node:child_process');
const {chromium}=require('playwright');
const repository=path.resolve(__dirname,'..'),publicRoot=path.resolve(process.argv[2]||'build/production');
const php=process.env.SAGLAM_PHP_BIN||'php';
const reportPath=path.resolve(process.env.ST_OWNER_BROWSER_REPORT||'build/backend-qa/owner-browser.json');
const checks=[],requests=[],errors=[],blocked=[],responseTasks=[];
let fixture,server,browser,stderr='',origin='',privateRoot,webroot,report;
const check=(ok,name)=>{checks.push({name,passed:!!ok});if(!ok)throw Error(name);};
function runPHP(code,args=[]){const result=spawnSync(php,['-r',code,...args],{encoding:'utf8',env:{PATH:process.env.PATH||'',...(privateRoot?{SAGLAM_PRIVATE_DIR:privateRoot}:{})}});if(result.status!==0||result.error)throw Error('PHP fixture operation failed: '+(result.error?.message||result.stderr));return result.stdout.trim();}
function snapshot(dir){const digest=crypto.createHash('sha256');function walk(current){for(const name of fs.readdirSync(current).sort()){const file=path.join(current,name),stat=fs.lstatSync(file);if(stat.isSymbolicLink())throw Error('QA input must not contain symlinks');if(stat.isDirectory())walk(file);else{digest.update(path.relative(dir,file));digest.update('\0');digest.update(fs.readFileSync(file));}}}walk(dir);return digest.digest('hex');}
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function port(){const socket=net.createServer();await new Promise(resolve=>socket.listen(0,'127.0.0.1',resolve));const number=socket.address().port;await new Promise(resolve=>socket.close(resolve));return number;}
function inspect(){return JSON.parse(runPHP(String.raw`$db=new PDO('sqlite:'.$argv[1]);$db->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE,PDO::FETCH_ASSOC);echo json_encode(['reviews'=>$db->query('SELECT id,status FROM reviews')->fetchAll(),'pending'=>(int)$db->query('SELECT count(*) FROM outbox WHERE sent=0')->fetchColumn(),'sent'=>(int)$db->query('SELECT count(*) FROM outbox WHERE sent<>0')->fetchColumn(),'attempts'=>(int)$db->query('SELECT COALESCE(sum(attempts),0) FROM outbox')->fetchColumn()]);`,[path.join(privateRoot,'site.sqlite')]));}
(async()=>{
 const initial=snapshot(publicRoot);
 try{
  check(['owner-admin.html','yonetim-api.php','review-moderation.php','service-operations.php'].every(name=>fs.existsSync(path.join(publicRoot,name))),'Frozen production build includes owner HTML/JS and all required PHP modules');
  const version=runPHP('echo PHP_VERSION;');check(JSON.parse(runPHP('echo json_encode(PDO::getAvailableDrivers());')).includes('sqlite'),'Selected PHP supports SQLite');
  fixture=fs.mkdtempSync(path.join(os.tmpdir(),'st-owner-browser-'));fs.chmodSync(fixture,0o700);webroot=path.join(fixture,'httpdocs');privateRoot=path.join(fixture,'private');fs.cpSync(publicRoot,webroot,{recursive:true});fs.mkdirSync(privateRoot,{mode:0o700});
  const number=await port();origin='http://127.0.0.1:'+number;
  const admin=crypto.randomBytes(24).toString('hex'),webhook=crypto.randomBytes(24).toString('hex');
  fs.writeFileSync(path.join(privateRoot,'site_apileri,.txt'),['SITE_URL='+origin,'ADMIN_ACCESS_KEY='+admin,'TELEGRAM_WEBHOOK_SECRET='+webhook,'TELEGRAM_ADMIN_IDS=10000001','TELEGRAM_CHAT_ID=10000002','TELEGRAM_BOT_TOKEN=','GEMINI_API_KEY=','GEMINI_API_KEY_1=','GEMINI_API_KEY_2=','GEMINI_API_KEY_3=','GEMINI_API_KEY_4=','IP_LOCATION_LOOKUP=0','VISIT_NOTIFICATIONS=0','DAILY_REPORT=0','TELEGRAM_POLLING=0'].join('\n')+'\n',{mode:0o600});
  runPHP(String.raw`define('ST_LIBRARY_MODE',true);require $argv[1].'/api.php';$db=st_db();$q=$db->prepare('INSERT INTO reviews(id,author,district,service,cat,rating,comment,status,nonce,created,consent) VALUES(?,?,?,?,?,?,?,?,?,?,?)');foreach(['a'=>'QA Onay','b'=>'QA Ret'] as $letter=>$name){$id=str_repeat($letter,24);$q->execute([$id,$name,'Küçükçekmece','Kombi Bakımı','kombi',5,'Sentetik yönetim tarayıcı testi','pending',str_repeat($letter,16),time(),1]);st_enqueue($db,'review:'.$id,['text'=>'Sentetik yorum bildirimi']);}$db->prepare('INSERT INTO tickets(id,name,phone,district,device,issue,created) VALUES(?,?,?,?,?,?,?)')->execute([str_repeat('c',24),'QA Servis','05340000000','Avcılar','Kombi','Sentetik servis talebi',time()]);st_enqueue($db,'ticket:'.str_repeat('c',24),['text'=>'Sentetik servis bildirimi']);`,[webroot]);
  server=spawn(php,['-d','display_errors=0','-d','log_errors=1','-S','127.0.0.1:'+number,'-t',webroot],{cwd:webroot,env:{PATH:process.env.PATH||'',SAGLAM_PRIVATE_DIR:privateRoot},stdio:['ignore','ignore','pipe']});server.stderr.on('data',data=>stderr+=data.toString());
  for(let i=0;i<100;i++){if(server.exitCode!==null)throw Error('PHP startup failed');const ready=await new Promise(resolve=>{const socket=net.connect(number,'127.0.0.1');socket.once('connect',()=>{socket.destroy();resolve(true);});socket.once('error',()=>resolve(false));});if(ready)break;await wait(30);}
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']});
  const context=await browser.newContext({viewport:{width:1280,height:900},serviceWorkers:'block',reducedMotion:'reduce'});
  await context.route('**/*',route=>{if(new URL(route.request().url()).origin===origin)return route.continue();blocked.push(new URL(route.request().url()).origin);return route.abort();});
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
  page.on('response',response=>{const url=new URL(response.url());if(!url.pathname.endsWith('.php'))return;responseTasks.push((async()=>{let data={};try{data=await response.json();}catch(_){}requests.push({action:url.searchParams.get('action'),status:response.status(),method:response.request().method(),ok:data.ok,connected:data.connected,csrf_shape:!!response.request().headers()['x-csrf-token']});})());});
  const response=action=>page.waitForResponse(r=>new URL(r.url()).pathname==='/yonetim-api.php'&&new URL(r.url()).searchParams.get('action')===action);
  async function clickAction(id,action,status=200){const pending=response(action);await page.locator('#'+id).click();const r=await pending;await page.waitForFunction(id=>!document.getElementById(id).disabled,id);check(r.status()===status,id+' reaches actual PHP with expected '+status);return r.json();}
  await page.goto(origin+'/owner-admin.html');check(await page.locator('#ownerLogin').isVisible()&&!await page.locator('#ownerPanel').isVisible(),'Unauthenticated owner screen hides private records');
  await page.locator('#ownerKey').fill('0'.repeat(48));let pending=response('state');await page.locator('#ownerLoginForm button').click();check((await pending).status()===403,'Invalid synthetic owner key is rejected');await page.waitForFunction(()=>/doğrulanamadı/.test(document.getElementById('ownerMessage').textContent));
  await page.locator('#ownerKey').fill(admin);pending=response('state');await page.locator('#ownerLoginForm button').click();check((await pending).status()===200,'Valid synthetic owner key authenticates through actual PHP');await page.locator('#ownerPanel').waitFor({state:'visible'});
  check(await page.locator('#ownerKey').inputValue()===''&&new URL(page.url()).hash==='','Successful login clears password field and URL secret');
  check((await page.locator('#ownerServerHealth').innerText()).includes('SQLite hazır')&&(await page.locator('#ownerTelegramHealth').innerText()).includes('Bot anahtarı eksik'),'State health honestly reports storage ready and Telegram key missing');
  check((await page.locator('#ownerAIHealth').innerText()).includes('Gemini anahtarı eksik'),'AI status explains that no provider key is configured');
  check(await page.locator('#ownerReviews .row').count()===2&&(await page.locator('#ownerTickets').innerText()).includes('QA Servis'),'Real synthetic review and service rows render in owner panel');
  check((await page.locator('#ownerQueueStatus').innerText()).includes('3'),'Owner state shows three pending notifications');
  await page.locator('#owner_telegram_chat_id').fill('10000003');await clickAction('ownerRefresh','state');
  check(await page.locator('#owner_telegram_chat_id').inputValue()==='10000003','Manual refresh preserves unsaved settings');
  await page.locator('#owner_visit_notifications').check();await page.locator('#owner_visit_notifications').uncheck();
  const saved=await clickAction('ownerSave','settings');check(saved.ok&&/kaydedildi/.test(saved.message),'Settings save confirms actual private TXT update');
  const privateText=fs.readFileSync(path.join(privateRoot,'site_apileri,.txt'),'utf8');
  check(privateText.includes(admin)&&privateText.includes(webhook),'Saving blank provider fields preserves existing synthetic management and webhook secrets');
  check(await page.locator('#owner_telegram_token').inputValue()===''&&await page.locator('#owner_gemini_key').inputValue()==='','Saved provider key fields stay blank in the UI');
  const configuration=JSON.parse(runPHP(String.raw`define('ST_LIBRARY_MODE',true);require $argv[1].'/api.php';$c=st_config();echo json_encode(['telegram_empty'=>$c['telegram_token']==='','gemini_empty'=>$c['gemini_key']==='','chat'=>$c['telegram_chat_id']]);`,[webroot]));
  check(configuration.telegram_empty&&configuration.gemini_empty&&configuration.chat==='10000003','Actual settings persist chat ID while keeping all provider credentials empty');
  let result=await clickAction('ownerTestTelegram','test-telegram',400);check(/bot anahtarı.*chat ID/i.test(result.error),'Telegram test gives actionable missing-config error without false delivery');
  result=await clickAction('ownerConnectTelegram','setup-webhook',400);check(/bilgilerini tamamlayın/.test(result.error),'Webhook button reports missing configuration without changing a real webhook');
  result=await clickAction('ownerIds','telegram-ids',502);check(/anahtarı ayarlanmadı/.test(result.error),'ID discovery safely stops before Telegram transport when token is blank');
  result=await clickAction('ownerTestAI','test-ai');check(result.connected===false&&result.text.length>40,'AI test returns honest useful local fallback through actual PHP');await page.waitForFunction(()=>document.getElementById('ownerAIReply').textContent.startsWith('Belirti rehberi:'));
  check((await page.locator('#ownerAIReply').innerText()).length>60,'Owner UI renders the local guide and does not call it an AI provider answer');
  await clickAction('ownerRetry','retry-notifications');check(inspect().sent===0&&inspect().attempts===0&&inspect().pending>=3,'Retry keeps missing-key notifications durable and unsent without any delivery attempt');
  const onay=page.locator('#ownerReviews .row').filter({hasText:'QA Onay'});pending=response('decide');await onay.getByRole('button',{name:'Onayla',exact:true}).click();check((await pending).status()===200,'Actual owner Approve button succeeds');
  await page.waitForFunction(()=>Array.from(document.querySelectorAll('#ownerReviews .row')).some(row=>row.textContent.includes('QA Onay')&&row.textContent.includes('Yayında')));
  const ret=page.locator('#ownerReviews .row').filter({hasText:'QA Ret'});pending=response('decide');await ret.getByRole('button',{name:'Reddet',exact:true}).click();check((await pending).status()===200,'Actual owner Reject button succeeds');
  await page.waitForFunction(()=>Array.from(document.querySelectorAll('#ownerReviews .row')).some(row=>row.textContent.includes('QA Ret')&&row.textContent.includes('Reddedildi')));
  const rows=inspect().reviews;check(rows.find(row=>row.id==='a'.repeat(24)).status==='approved'&&rows.find(row=>row.id==='b'.repeat(24)).status==='rejected','Moderation decisions persist in real SQLite');
  const approved=await context.request.get(origin+'/api.php?action=reviews');const publicRows=(await approved.json()).reviews;
  check(publicRows.some(row=>row.id==='a'.repeat(24))&&!publicRows.some(row=>row.id==='b'.repeat(24)),'Public endpoint exposes the owner-approved review and excludes the rejected one');
  for(const width of [390,768,1280]){await page.setViewportSize({width,height:900});check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),width+'px owner panel fits the screen');}
  for(const [name,target] of [['Siteyi aç','/'],['Site haritasını aç','/sitemap.xml'],['Tarama ayarlarını aç','/robots.txt']]){const [popup]=await Promise.all([context.waitForEvent('page'),page.getByRole('link',{name,exact:true}).click()]);await popup.waitForLoadState('domcontentloaded');check(new URL(popup.url()).pathname===target,'Owner '+target+' link opens its actual local target');await popup.close();}
  await page.locator('#ownerLogout').click();await page.locator('#ownerLogin').waitFor({state:'visible'});check(!await page.locator('#ownerPanel').isVisible()&&await page.evaluate(()=>sessionStorage.getItem('st_owner_key')===null),'Logout removes session key and hides private panel');
  await Promise.all(responseTasks);check(errors.length===0,'Owner browser has no JavaScript errors');check(blocked.length===0,'Owner and linked pages attempted no external browser requests');check(!/PHP (?:Fatal|Warning)|Uncaught/.test(stderr),'Owner PHP journeys have no warnings or fatal errors');check(snapshot(publicRoot)===initial,'Frozen production build remains byte-for-byte unchanged');
  report={passed:true,php:version,checks:checks.length,cases:checks,requests,actual_php_requests:requests.length,mock_responses:0,provider_requests:0,production_frozen:true,production_snapshot:initial,production_private_read:false,external_browser_requests:blocked,notification_delivery_attempts:inspect().attempts,scope:'Real owner login, settings, health, Telegram missing-key error paths, AI local fallback, retry, moderation, navigation and logout on an isolated copied production build; synthetic private SQLite and blank provider keys. Live provider delivery is not claimed.'};
 }catch(error){process.exitCode=1;report={passed:false,error:error.message,checks:checks.length,cases:checks,requests,page_errors:errors,external_browser_requests:blocked,php_errors:stderr.match(/.*(?:PHP (?:Fatal|Warning)|Uncaught).*/g)||[]};console.error(error.stack);}
 finally{if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await Promise.race([new Promise(resolve=>server.once('exit',resolve)),wait(1000)]);}if(fixture)fs.rmSync(fixture,{recursive:true,force:true});fs.mkdirSync(path.dirname(reportPath),{recursive:true});fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');}
 console.log(JSON.stringify({passed:report.passed,checks:report.checks,actual_php_requests:report.actual_php_requests,mock_responses:0,report:path.relative(repository,reportPath)}));
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
