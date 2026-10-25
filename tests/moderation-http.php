<?php
declare(strict_types=1);
/* Actual local HTTP/PHP/SQLite webhook journey. Synthetic customers only. */
$root=dirname(__DIR__);$public=realpath($argv[1]??$root.'/build/production');
if(!$public)throw new RuntimeException('Production build required.');
$base=sys_get_temp_dir().'/st-moderation-http-'.bin2hex(random_bytes(8));$doc=$base.'/public';$private=$base.'/private';mkdir($doc.'/assets',0700,true);mkdir($private,0700,true);
$remove=static function(string $path)use(&$remove):void{if(is_dir($path)){foreach(scandir($path) as $name)if($name!=='.'&&$name!=='..')$remove($path.'/'.$name);rmdir($path);}else @unlink($path);};
$process=null;$checks=[];$requests=0;$cookie='';$csrf='';
$check=static function(bool $ok,string $name)use(&$checks):void{$checks[]=['name'=>$name,'passed'=>$ok];if(!$ok)throw new RuntimeException($name);};
try{
    foreach(glob($public.'/*.php') as $file)copy($file,$doc.'/'.basename($file));
    foreach(['servis-katalog.json','organic-catalog.json','verified-faults.json','brand-registry.json','trusted-proxies.json'] as $file)if(is_file($public.'/assets/'.$file))copy($public.'/assets/'.$file,$doc.'/assets/'.$file);
    file_put_contents($doc.'/index.html','<script id="st-review-seeds" type="application/json">'.json_encode([['author'=>'QA Eski Kayıt','comment'=>'Eski siteden sentetik yorum; gerçek müşteri değildir.','date'=>'01 Oca 2025','rating'=>5,'service'=>'Kombi Tamiri']]).'</script>');
    $socket=stream_socket_server('tcp://127.0.0.1:0',$errno,$error);if(!$socket)throw new RuntimeException('Loopback socket unavailable.');$address=stream_socket_get_name($socket,false);fclose($socket);$origin='http://'.$address;$secret=bin2hex(random_bytes(24));
    file_put_contents($private.'/site_apileri,.txt',implode("\n",['SITE_URL='.$origin,'TELEGRAM_WEBHOOK_SECRET='.$secret,'TELEGRAM_CHAT_ID=10000002','TELEGRAM_ADMIN_IDS=10000001','TELEGRAM_BOT_TOKEN=','GEMINI_API_KEY=','IP_LOCATION_LOOKUP=0','VISIT_NOTIFICATIONS=0','DAILY_REPORT=0','WEEKLY_REPORT=0','MONTHLY_REPORT=0'])."\n");
    $process=proc_open([getenv('SAGLAM_PHP_BIN')?:PHP_BINARY,'-d','display_errors=0','-S',$address,'-t',$doc],[0=>['pipe','r'],1=>['file',$base.'/server.stdout','a'],2=>['file',$base.'/server.stderr','a']],$pipes,$doc,['PATH'=>getenv('PATH')?:'','SAGLAM_PRIVATE_DIR'=>$private]);
    if(!is_resource($process))throw new RuntimeException('PHP server did not start.');fclose($pipes[0]);
    for($i=0;$i<80;$i++){$probe=@stream_socket_client('tcp://'.$address,$errno,$error,0.1);if($probe){fclose($probe);break;}usleep(25000);}
    $request=static function(string $method,string $action,?array $data=null,array $headers=[])use($origin,&$requests,&$cookie,&$csrf):array{
        $requests++;$all=['Accept: application/json'];if($cookie!=='')$all[]='Cookie: '.$cookie;
        if($method==='POST'){$all[]='Content-Type: application/json';$all[]='Origin: '.$origin;$all[]='X-CSRF-Token: '.$csrf;}
        foreach($headers as $key=>$value)$all[]=$key.': '.$value;
        $options=['http'=>['method'=>$method,'header'=>implode("\r\n",$all),'ignore_errors'=>true,'timeout'=>5]];if($method==='POST')$options['http']['content']=json_encode($data??[]);
        $body=@file_get_contents($origin.'/api.php?action='.$action,false,stream_context_create($options));$response=$http_response_header??[];
        preg_match('~^HTTP/\S+ (\d+)~',$response[0]??'',$match);foreach($response as $header)if(preg_match('/^Set-Cookie:\s*(st_session=[^;]+)/i',$header,$m))$cookie=$m[1];
        return ['status'=>(int)($match[1]??0),'data'=>is_string($body)?json_decode($body,true):null];
    };
    $r=$request('GET','bootstrap');$csrf=$r['data']['csrf']??'';$check($r['status']===200&&$csrf!=='','Actual production bootstrap creates a CSRF session');
    $db=new PDO('sqlite:'.$private.'/site.sqlite',null,null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC]);$db->exec('PRAGMA busy_timeout=5000');
    $review=['author'=>'QA Aynı İsim','district'=>'Küçükçekmece','service'=>'Kombi Bakımı / Onarımı','rating'=>5,'comment'=>'İlk sentetik yorum metni; gerçek müşteri değildir.','consent'=>true];$ids=[];
    foreach([1,2] as $i){$review['comment']='Sentetik yorum '.$i.'; gerçek müşteri değildir.';$r=$request('POST','review',$review,['Idempotency-Key'=>'qa-moderation-review-000'.$i]);$check($r['status']===201&&($r['data']['status']??'')==='pending','Review '.$i.' genuinely saves pending through PHP');$ids[]=$r['data']['id'];}
    $headers=['X-Telegram-Bot-Api-Secret-Token'=>$secret];
    foreach($ids as $id){$q=$db->prepare('SELECT nonce FROM reviews WHERE id=?');$q->execute([$id]);$nonce=$q->fetchColumn();$q->closeCursor();$r=$request('POST','webhook',['callback_query'=>['id'=>'qa-approve-'.$id,'from'=>['id'=>10000001],'message'=>['chat'=>['id'=>10000002],'message_id'=>11],'data'=>'r:a:'.$id.':'.$nonce]],$headers);$check($r['status']===200,'Existing approval callback still succeeds');}
    $r=$request('GET','reviews');$check(count($r['data']['reviews']??[])===2,'Both actual approved reviews are public before deletion');
    $message=['from'=>['id'=>10000001],'chat'=>['id'=>10000002],'message_id'=>100,'text'=>'/sil'];
    $r=$request('POST','webhook',['message'=>$message]);$check($r['status']===403,'Message webhook requires its secret before reading admin text');
    $bad=$message;$bad['from']['id']=99999999;$r=$request('POST','webhook',['message'=>$bad],$headers);$check($r['status']===403,'Message webhook rejects an unauthorized Telegram sender');
    $r=$request('POST','webhook',['message'=>$message],$headers);$check($r['status']===200&&(int)$db->query('SELECT count(*) FROM telegram_review_dialogs')->fetchColumn()===1,'Slash command asks for a name through the actual webhook');
    $message['message_id']=101;$message['text']='QA Aynı';$r=$request('POST','webhook',['message'=>$message],$headers);
    $rows=$db->query('SELECT token,review_id FROM telegram_review_confirmations ORDER BY review_id')->fetchAll();$check($r['status']===200&&count($rows)===2,'Actual name reply creates separate confirmations for same-name reviews');
    $callback=['id'=>'qa-delete-1','from'=>['id'=>10000001],'message'=>['chat'=>['id'=>10000002],'message_id'=>12],'data'=>'rd:d:'.$rows[0]['token']];
    $bad=$callback;$bad['message']['chat']['id']=99999999;$r=$request('POST','webhook',['callback_query'=>$bad],$headers);$check($r['status']===403,'Delete callback rejects a different chat');
    $r=$request('POST','webhook',['callback_query'=>$callback],$headers);$check($r['status']===200,'Explicit Sil callback succeeds through actual PHP');
    $r=$request('GET','reviews');$check(count($r['data']['reviews']??[])===1&&in_array($rows[0]['review_id'],$r['data']['deleted_ids']??[],true),'Public endpoint removes only that review and supplies its durable deleted ID');
    $request('POST','webhook',['callback_query'=>$callback],$headers);$check((int)$db->query('SELECT count(*) FROM reviews')->fetchColumn()===1,'Replayed Telegram deletion never deletes another review');
    $message['message_id']=102;$message['text']='/sil QA Eski';$r=$request('POST','webhook',['message'=>$message],$headers);
    $token=$db->query("SELECT token FROM telegram_review_confirmations WHERE review_id='existing-0'")->fetchColumn();$check($r['status']===200&&is_string($token),'Legacy static seed can be found by name via /sil');
    $callback['id']='qa-delete-seed';$callback['data']='rd:d:'.$token;$r=$request('POST','webhook',['callback_query'=>$callback],$headers);$check($r['status']===200,'Legacy static seed accepts explicit deletion');
    $r=$request('GET','reviews');$check(in_array('existing-0',$r['data']['deleted_ids']??[],true),'Legacy deletion persists and is returned for static-seed filtering');
    $queued=(int)$db->query('SELECT count(*) FROM outbox')->fetchColumn();$request('POST','query',['query'=>'Küçükçekmece kombi servisi']);$check((int)$db->query('SELECT count(*) FROM outbox')->fetchColumn()===$queued,'Site searches no longer enqueue individual Telegram notices');
    $check((int)$db->query('SELECT count(*) FROM outbox WHERE sent<>0 OR attempts<>0')->fetchColumn()===0,'No Telegram or external provider was contacted');
    $report=['passed'=>true,'checks'=>count($checks),'cases'=>$checks,'actual_php_requests'=>$requests,'provider_requests'=>0];
    if(!is_dir($root.'/build/backend-qa'))mkdir($root.'/build/backend-qa',0770,true);file_put_contents($root.'/build/backend-qa/moderation-http.json',json_encode($report,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE)."\n");echo json_encode(['passed'=>true,'checks'=>count($checks),'actual_php_requests'=>$requests,'provider_requests'=>0])."\n";
}finally{if(is_resource($process)){proc_terminate($process);proc_close($process);}$remove($base);}
