<?php
declare(strict_types=1);
/** Isolated loopback integration. Only synthetic configuration and SQLite data.
 * Usage: php tests/backend-http.php build/production
 * Never starts notification workers or calls real Gemini/Telegram transports.
 */
$root=dirname(__DIR__);$public=realpath($argv[1]??$root.'/build/production');
if(!$public||!is_file($public.'/api.php'))throw new RuntimeException('Build the production package before HTTP QA.');
$base=sys_get_temp_dir().'/st-http-qa-'.bin2hex(random_bytes(6));$doc=$base.'/httpdocs';$private=$base.'/private';
mkdir($base,0700);mkdir($doc,0700);mkdir($doc.'/assets',0700);mkdir($private,0700);
$remove=function(string $path)use(&$remove):void{if(is_link($path)||!is_dir($path)){@unlink($path);return;}foreach(scandir($path) as $name)if($name!=='.'&&$name!=='..')$remove($path.'/'.$name);@rmdir($path);};
$process=null;$checks=[];$requests=0;$cookie='';$csrf='';
$assert=static function(bool $ok,string $name)use(&$checks):void{$checks[]=['name'=>$name,'passed'=>$ok];if(!$ok)throw new RuntimeException($name);};
try{
 foreach(['api.php','business-config.php','ai-koruma.php','fault-catalog.php','fault-advisories.php','notification-support.php','yonetim-api.php'] as $file){if(!is_file($public.'/'.$file)||!copy($public.'/'.$file,$doc.'/'.$file))throw new RuntimeException('Missing public PHP fixture file: '.$file);}
 foreach(['servis-katalog.json','organic-catalog.json','verified-faults.json','brand-registry.json','trusted-proxies.json'] as $file){if(is_file($public.'/assets/'.$file))copy($public.'/assets/'.$file,$doc.'/assets/'.$file);}
 $socket=stream_socket_server('tcp://127.0.0.1:0',$errno,$error);if(!$socket)throw new RuntimeException('Loopback socket unavailable.');
 $address=stream_socket_get_name($socket,false);fclose($socket);$origin='http://'.$address;
 $admin=bin2hex(random_bytes(24));$webhook=bin2hex(random_bytes(24));
 file_put_contents($private.'/site_apileri,.txt',implode("\n",['SITE_URL='.$origin,'ADMIN_ACCESS_KEY='.$admin,'TELEGRAM_WEBHOOK_SECRET='.$webhook,'TELEGRAM_ADMIN_IDS=10000001','TELEGRAM_CHAT_ID=10000002','TELEGRAM_BOT_TOKEN=','GEMINI_API_KEY=','IP_LOCATION_LOOKUP=0','VISIT_NOTIFICATIONS=0','DAILY_REPORT=0'])."\n");
 $process=proc_open([PHP_BINARY,'-d','display_errors=0','-d','log_errors=1','-S',$address,'-t',$doc],[0=>['pipe','r'],1=>['file',$base.'/server.stdout','a'],2=>['file',$base.'/server.stderr','a']],$pipes,$doc,['PATH'=>getenv('PATH')?:'','SAGLAM_PRIVATE_DIR'=>$private]);
 if(!is_resource($process))throw new RuntimeException('PHP loopback server did not start.');fclose($pipes[0]);
 $ready=false;for($i=0;$i<60;$i++){$probe=@stream_socket_client('tcp://'.$address,$errno,$error,0.1);if($probe){fclose($probe);$ready=true;break;}usleep(25000);}if(!$ready)throw new RuntimeException('PHP loopback server startup timed out.');
 $request=static function(string $method,string $path,?array $payload=null,array $extra=[],?string $raw=null)use($origin,&$cookie,&$csrf,&$requests):array{
  $requests++;$headers=['Accept'=>'application/json'];if($cookie!=='')$headers['Cookie']=$cookie;
  if($method==='POST'){$headers['Origin']=$origin;$headers['Content-Type']='application/json';if($csrf!=='')$headers['X-CSRF-Token']=$csrf;}
  $headers=array_replace($headers,$extra);$lines=[];foreach($headers as $key=>$value)if($value!==null)$lines[]=$key.': '.$value;
  $options=['http'=>['method'=>$method,'header'=>implode("\r\n",$lines),'ignore_errors'=>true,'timeout'=>4]];
  if($method==='POST')$options['http']['content']=$raw??json_encode($payload??[],JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);
  $body=@file_get_contents($origin.$path,false,stream_context_create($options));$responseHeaders=$http_response_header??[];
  preg_match('/^HTTP\/\S+ (\d+)/',$responseHeaders[0]??'',$match);$status=(int)($match[1]??0);
  foreach($responseHeaders as $header)if(preg_match('/^Set-Cookie:\s*(st_session=[^;]+)/i',$header,$match))$cookie=$match[1];
  return ['status'=>$status,'data'=>is_string($body)?json_decode($body,true):null,'headers'=>$responseHeaders,'raw'=>(string)$body];
 };
 $r=$request('GET','/api.php?action=bootstrap');$csrf=$r['data']['csrf']??'';
 $assert($r['status']===200&&strlen($csrf)>60&&$cookie!=='','Bootstrap returns a session-bound CSRF token');
 $assert((bool)preg_grep('/^Set-Cookie:.*HttpOnly.*SameSite=Strict/i',$r['headers']),'Session cookie has HttpOnly and SameSite Strict');
 $db=new PDO('sqlite:'.$private.'/site.sqlite',null,null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC]);$db->exec('PRAGMA busy_timeout=5000');
 $count=static function(string $table)use($db):int{return (int)$db->query('SELECT count(*) FROM '.$table)->fetchColumn();};
 $assert((bool)preg_grep('/^Cache-Control:.*no-store/i',$r['headers'])&&(bool)preg_grep('/^X-Robots-Tag:.*noindex/i',$r['headers']),'API session response is not cached or indexed');
 $session=substr($cookie,strlen('st_session='));$fixtureSecret=(string)$db->query("SELECT v FROM meta WHERE k='secret'")->fetchColumn();
 $signed=static function(string $identity,int $stamp)use($fixtureSecret):string{return $stamp.'.'.hash_hmac('sha256',$identity.'.'.$stamp,$fixtureSecret);};
 $ticket=['name'=>'QA Sentetik','phone'=>'+90 534 000 0000','district'=>'Küçükçekmece / Atakent','device'=>'Kombi','issue'=>'Sıcak su bazen soğuyor; sentetik test kaydı.'];
 $review=['author'=>'QA Sentetik','district'=>'Küçükçekmece','service'=>'Kombi Bakımı / Onarımı','rating'=>5,'comment'=>'Yalnızca izole test veritabanındaki sentetik yorum.','consent'=>true];
 $idem=['Idempotency-Key'=>'qa-ticket-00000000001'];
 foreach([
  ['missing CSRF',['X-CSRF-Token'=>null],403,null],['invalid CSRF',['X-CSRF-Token'=>'invalid'],403,null],
  ['foreign Origin',['Origin'=>'https://foreign.invalid'],403,null],['cross-site browser',['Sec-Fetch-Site'=>'cross-site'],403,null],
  ['non JSON',['Content-Type'=>'text/plain'],415,null],['malformed JSON',[],400,'{broken'],['oversized JSON',[],413,str_repeat('x',17000)]
 ] as [$name,$headers,$status,$raw]){$r=$request('POST','/api.php?action=ticket',$ticket,array_replace($idem,$headers),$raw);$assert($r['status']===$status,'Reject '.$name.' before saving');}
 foreach([['expired token',$signed($session,time()-7201)],['future token',$signed($session,time()+61)],['other-session token',$signed(str_repeat('a',48),time())]] as [$name,$token]){$r=$request('POST','/api.php?action=ticket',$ticket,array_replace($idem,['X-CSRF-Token'=>$token]));$assert($r['status']===403,'Reject correctly signed '.$name);}
 $r=$request('POST','/api.php?action=ticket',$ticket,array_replace($idem,['Cookie'=>null]));$assert($r['status']===403,'A token without its session cookie is rejected');
 $assert($count('tickets')===0&&$count('outbox')===0,'Rejected requests persist no ticket or notification');
 $r=$request('POST','/api.php?action=ticket',$ticket);$assert($r['status']===400,'Missing idempotency key rejected');
 foreach([
  ['honeypot',array_replace($ticket,['website'=>'filled'])],['invalid phone',array_replace($ticket,['phone'=>'+90 534 BAD 0000'])],['invalid device',array_replace($ticket,['device'=>'Buzdolabı'])]
 ] as [$name,$data]){$r=$request('POST','/api.php?action=ticket',$data,$idem);$assert($r['status']===400,'Reject '.$name);}
 $db->exec('DELETE FROM rate');
 $r=$request('POST','/api.php?action=ticket',$ticket,$idem);$ticketId=$r['data']['id']??'';
 $assert($r['status']===201&&preg_match('/^[a-f0-9]{24}$/D',$ticketId)&&$r['data']['delivery']==='queued','Valid ticket is saved with truthful queued delivery');
 $assert($count('tickets')===1&&$count('outbox')===1,'Ticket and durable notification saved once');
 $r=$request('POST','/api.php?action=ticket',$ticket,$idem);$assert($r['status']===200&&$r['data']['id']===$ticketId&&$count('tickets')===1&&$count('outbox')===1,'Idempotent ticket replay does not duplicate records');
 $r=$request('POST','/api.php?action=ticket',array_replace($ticket,['issue'=>'Changed synthetic issue.']),$idem);$assert($r['status']===409&&$count('tickets')===1,'Idempotency conflict rejects changed content');
 $r=$request('POST','/api.php?action=review',array_replace($review,['consent'=>false]),['Idempotency-Key'=>'qa-review-invalid-0001']);$assert($r['status']===400,'Review requires explicit publication consent');
 $r=$request('POST','/api.php?action=review',array_replace($review,['rating'=>6]),['Idempotency-Key'=>'qa-review-invalid-0002']);$assert($r['status']===400,'Out-of-range rating rejected');
 $r=$request('POST','/api.php?action=review',$review,['Idempotency-Key'=>'qa-review-valid-00001']);$reviewId=$r['data']['id']??'';
 $assert($r['status']===201&&($r['data']['status']??'')==='pending'&&$r['data']['delivery']==='queued','Review starts pending and notification stays queued');
 $reviewCount=$count('reviews');$queueCount=$count('outbox');$r=$request('POST','/api.php?action=review',$review,['Idempotency-Key'=>'qa-review-valid-00001']);$assert($r['status']===200&&$r['data']['id']===$reviewId&&$count('reviews')===$reviewCount&&$count('outbox')===$queueCount,'Idempotent review replay cannot duplicate a pending review');
 $r=$request('POST','/api.php?action=review',array_replace($review,['comment'=>'A changed synthetic review body.']),['Idempotency-Key'=>'qa-review-valid-00001']);$assert($r['status']===409&&$count('reviews')===$reviewCount,'Review idempotency conflict preserves the original body');
 $r=$request('GET','/api.php?action=reviews');$assert($r['status']===200&&$r['data']['reviews']===[],'Pending review is not public');
 $r=$request('GET','/yonetim-api.php?action=state');$assert($r['status']===403,'Owner data is not public');
 $owner=['X-Admin-Key'=>$admin];$r=$request('GET','/yonetim-api.php?action=state',null,$owner);
 $assert($r['status']===200&&count($r['data']['reviews'])===1&&count($r['data']['tickets'])===1,'Authorized owner sees synthetic persisted records');
 $assert(strpos($r['raw'],$admin)===false&&strpos($r['raw'],$webhook)===false,'Owner state does not disclose private access or webhook keys');
 $r=$request('POST','/yonetim-api.php?action=decide',['id'=>$reviewId,'status'=>'approved'],array_replace($owner,['X-CSRF-Token'=>null]));$assert($r['status']===403,'Owner mutation also requires CSRF');
 $r=$request('POST','/yonetim-api.php?action=decide',['id'=>$reviewId,'status'=>'approved'],$owner);$assert($r['status']===200,'Owner approval succeeds');
 $r=$request('GET','/api.php?action=reviews');$assert(count($r['data']['reviews'])===1&&$r['data']['reviews'][0]['source']==='site'&&$r['data']['reviews'][0]['rating']===5,'Only approved review becomes public with typed rating');
 $db->exec('DELETE FROM rate');
 $r=$request('POST','/api.php?action=review',$review,['Idempotency-Key'=>'qa-review-reject-0001']);$rejectId=$r['data']['id'];
 $r=$request('POST','/yonetim-api.php?action=decide',['id'=>$rejectId,'status'=>'rejected'],$owner);$assert($r['status']===200,'Owner rejection succeeds');
 $request('POST','/yonetim-api.php?action=decide',['id'=>$rejectId,'status'=>'approved'],$owner);
 $assert($db->query("SELECT status FROM reviews WHERE id=".$db->quote($rejectId))->fetchColumn()==='rejected','A repeated conflicting decision cannot overwrite rejection');
 $r=$request('GET','/api.php?action=reviews');$assert(count($r['data']['reviews'])===1,'Rejected review remains private');
 $r=$request('POST','/api.php?action=review',$review,['Idempotency-Key'=>'qa-review-webhook-001']);$webhookId=$r['data']['id'];$nonce=$db->query('SELECT nonce FROM reviews WHERE id='.$db->quote($webhookId))->fetchColumn();
 $callback=['callback_query'=>['from'=>['id'=>10000001],'message'=>['chat'=>['id'=>10000002]],'data'=>'r:a:'.$webhookId.':'.$nonce]];
 $r=$request('POST','/api.php?action=webhook',$callback);$assert($r['status']===403,'Webhook requires its configured secret');
 $headers=['X-Telegram-Bot-Api-Secret-Token'=>$webhook];$wrong=$callback;$wrong['callback_query']['from']['id']=10000003;
 $r=$request('POST','/api.php?action=webhook',$wrong,$headers);$assert($r['status']===403,'Webhook rejects unauthorized admin');
 $wrong=$callback;$wrong['callback_query']['message']['chat']['id']=10000003;$r=$request('POST','/api.php?action=webhook',$wrong,$headers);$assert($r['status']===403,'Webhook rejects an authorized admin in the wrong chat');
 $wrong=$callback;$wrong['callback_query']['data']='r:a:'.$webhookId.':'.str_repeat('0',16);
 $r=$request('POST','/api.php?action=webhook',$wrong,$headers);$assert($r['status']===403,'Webhook rejects incorrect review nonce');
 // Callback id is intentionally absent: approval logic runs, provider acknowledgement does not.
 $r=$request('POST','/api.php?action=webhook',$callback,$headers);$assert($r['status']===200&&$db->query('SELECT status FROM reviews WHERE id='.$db->quote($webhookId))->fetchColumn()==='approved','Authorized synthetic webhook approves pending review without contacting Telegram');
 $r=$request('GET','/api.php?action=business-maps');$assert($r['status']===200&&!$r['data']['configured'],'Missing map configuration has an honest empty response');
 file_put_contents($private.'/haritalar.json',json_encode(['google_url'=>'https://maps.app.goo.gl/SyntheticQAMap','google_embed_url'=>'https://www.google.com/maps/embed?pb=synthetic','telegram_token'=>'SYNTHETIC_MAP_SECRET_NEVER_PUBLIC']));
 $r=$request('GET','/api.php?action=business-maps');$assert($r['status']===200&&$r['data']['configured']&&strpos($r['raw'],'SYNTHETIC_MAP_SECRET_NEVER_PUBLIC')===false,'Maps endpoint exposes only allowlisted public map fields');
 $r=$request('POST','/api.php?action=ai',['device'=>'Kombi','issue'=>'Bosch Condens 2300i W hata kodu 227','model_id'=>'bosch-kombi-condens-2300i-w','code'=>'227']);
 $assert($r['status']===200&&$r['data']['source']==='manual'&&$r['data']['code_definition_verified']===true,'Known scoped model/code uses the verified manual without Gemini');
 foreach(['E1','E01'] as $code){$r=$request('POST','/api.php?action=ai',['device'=>'Kombi','issue'=>'Modelini bilmiyorum; hata kodu '.$code,'code'=>$code]);$assert($r['status']===200&&$r['data']['source']==='guide'&&empty($r['data']['code_definition_verified']),'Unknown model '.$code.' never gets an invented meaning');}
 $data=json_decode(file_get_contents($doc.'/assets/verified-faults.json'),true);$foreign=null;$documentOnly=null;
 foreach($data['models'] as $model){if(!$foreign&&($model['matchable']??true)!==false&&!empty($model['requires_scope_confirmation'])&&!empty($model['codes']))$foreign=$model;if(!$documentOnly&&($model['matchable']??true)===false&&!empty($model['codes']))$documentOnly=$model;}
 if(!$foreign||!$documentOnly)throw new RuntimeException('Scope-guard fixture coverage is missing.');
 foreach([[$foreign,false,'Unconfirmed foreign scope'],[$documentOnly,true,'Document-only capacity scope']] as [$model,$confirmed,$name]){$r=$request('POST','/api.php?action=ai',['device'=>$model['device']==='klima'?'Klima':'Kombi','issue'=>'Ekrandaki hata kodu '.$model['codes'][0]['code'],'model_id'=>$model['id'],'code'=>$model['codes'][0]['code'],'scope_confirmed'=>$confirmed]);$assert($r['status']===200&&$r['data']['source']==='guide'&&empty($r['data']['code_definition_verified']),$name.' cannot autoanswer');}
 $r=$request('POST','/api.php?action=ai',['device'=>'Klima','issue'=>'Klima soğutmuyor']);$assert($r['status']===200&&$r['data']['source']==='guide'&&strlen($r['data']['text'])>40,'Missing Gemini keys preserve useful local fallback');
 $r=$request('POST','/api.php?action=ai',['device'=>'Kombi','issue'=>'Gaz kokusu var']);$assert($r['status']===200&&$r['data']['source']==='emergency'&&$r['data']['emergency_phone']==='187','Gas emergency takes priority over AI and commercial guidance');
 $r=$request('POST','/api.php?action=ai',['device'=>'Klima','issue'=>'Duman ve yangın var']);$assert($r['status']===200&&$r['data']['source']==='emergency'&&$r['data']['emergency_phone']==='112','Fire emergency routes to 112');
 foreach([['ticket',8,$ticket],['review',5,$review],['ai',12,['device'=>'Klima','issue'=>'Klima soğutmuyor']]] as [$action,$limit,$payload]){
  $db->exec('DELETE FROM rate');
  for($i=0;$i<$limit;$i++){$r=$request('POST','/api.php?action='.$action,$payload,['Idempotency-Key'=>'qa-rate-'.$action.'-'.str_pad((string)$i,16,'0')]);$assert($r['status']===($action==='ai'?200:201),$action.' request within configured limit '.$i);}
  $r=$request('POST','/api.php?action='.$action,$payload,['Idempotency-Key'=>'qa-rate-'.$action.'-overflow-000']);$assert($r['status']===429,$action.' overflow returns 429');
 }
 $assert((int)$db->query('SELECT count(*) FROM outbox WHERE sent<>0 OR attempts<>0 OR lease<>0')->fetchColumn()===0,'All generated notifications remain durable, unsent and unattempted');
 $assert(!preg_match('/(?:PHP (?:Fatal|Warning)|Uncaught)/',file_get_contents($base.'/server.stderr')),'No PHP warnings or fatal errors during HTTP journeys');
 $report=['passed'=>true,'php'=>PHP_VERSION,'checks'=>count($checks),'cases'=>$checks,'loopback_http_requests'=>$requests,'provider_requests'=>0,'notification_delivery_attempts'=>0,'production_private_read'=>false,'scope'=>'Synthetic private fixture, copied public PHP/data, loopback HTTP; no worker or real provider credentials'];
 if($path=getenv('ST_QA_REPORT'))file_put_contents($path,json_encode($report,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE)."\n");
 echo json_encode($report,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES)."\n";
}finally{
 if(is_resource($process)){proc_terminate($process);proc_close($process);}
 $remove($base);
}
