<?php
declare(strict_types=1);
/* Synthetic SQLite plus an injected in-process Telegram transport. No credentials,
 * production storage, HTTP requests, webhook changes or real delivery. */
$root=dirname(__DIR__);$temporary=sys_get_temp_dir().'/st-notification-qa-'.bin2hex(random_bytes(6));
mkdir($temporary,0700);mkdir($temporary.'/assets',0700);mkdir($temporary.'/assets/notifications',0700);
copy($root.'/server/notification-dispatch.php',$temporary.'/notification-dispatch.php');
copy($root.'/server/transaction.php',$temporary.'/transaction.php');
class STTelegramError extends RuntimeException {public $retry_after;public function __construct(string $message,int $retry_after=0){parent::__construct($message);$this->retry_after=$retry_after;}}
$receipt_calls=[];
function st_delivery_receipt(PDO $db,string $event,int $message_id): void {global $receipt_calls;$receipt_calls[]=[$event,$message_id];}
require $root.'/server/notification-support.php';require $temporary.'/notification-dispatch.php';
$checks=[];$calls=[];$serial=100;
$assert=static function(bool $passed,string $name)use(&$checks):void{$checks[]=['name'=>$name,'passed'=>$passed];if(!$passed)throw new RuntimeException($name);};
$remove=function(string $path)use(&$remove):void{if(!is_dir($path)||is_link($path)){unlink($path);return;}foreach(scandir($path) as $name)if($name!=='.'&&$name!=='..')$remove($path.'/'.$name);rmdir($path);};
try{
 $db=new PDO('sqlite:'.$temporary.'/test.sqlite',null,null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC]);
 $db->exec('PRAGMA journal_mode=WAL;PRAGMA busy_timeout=5000;CREATE TABLE outbox(id TEXT PRIMARY KEY,payload TEXT NOT NULL,created INTEGER NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,due INTEGER NOT NULL,lease INTEGER NOT NULL DEFAULT 0,sent INTEGER NOT NULL DEFAULT 0,last_error TEXT NOT NULL DEFAULT \'\',telegram_message_id INTEGER,delivered INTEGER);CREATE TABLE tickets(id TEXT PRIMARY KEY,name TEXT);');
 $enqueue=static function(string $id,array $payload,int $created=0)use($db):void{$q=$db->prepare('INSERT OR IGNORE INTO outbox(id,payload,created,due) VALUES(?,?,?,?)');foreach(st_notification_rows($id,$payload) as [$key,$message])$q->execute([$key,json_encode($message,JSON_UNESCAPED_UNICODE),$created?:time(),time()]);};
 $row=static function(string $id)use($db):array{$q=$db->prepare('SELECT * FROM outbox WHERE id=?');$q->execute([$id]);return $q->fetch();};
 $cfg=['telegram_token'=>'10000001:synthetic-token-never-used-for-network','telegram_chat_id'=>'10000002'];
 $success=static function(string $method,array $payload,int $timeout)use(&$calls,&$serial):array{$calls[]=[$method,$payload,$timeout];return ['ok'=>true,'result'=>['message_id'=>++$serial]];};
 $png=base64_decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6jKkAAAAASUVORK5CYII=');
 foreach(['visit.png','ticket.png','review.png'] as $asset)file_put_contents($temporary.'/assets/notifications/'.$asset,$png);
 $event='ticket:'.str_repeat('a',24);$db->prepare('INSERT INTO tickets(id,name) VALUES(?,?)')->execute([str_repeat('a',24),'Sentetik müşteri']);
 $enqueue($event,['text'=>'Servis talebi','reply_markup'=>['inline_keyboard'=>[[['text'=>'Onayla','callback_data'=>'synthetic']]]]]);
 $enqueue('ticket:unrelated',['text'=>'Another pending notification']);
 $r=st_deliver_outbox($db,$cfg,6,$event,$success);
 $assert($r['sent']===1&&$r['failed']===0&&count($calls)===1,'A new event is delivered immediately without a worker');
 $assert($calls[0][0]==='sendPhoto'&&$calls[0][1]['_photo']==='ticket.png'&&isset($calls[0][1]['reply_markup']),'Original ticket photo and moderation markup are preserved');
 $assert($calls[0][1]['chat_id']==='10000002'&&$calls[0][2]>0&&$calls[0][2]<=4000,'Owner chat and bounded timeout are passed to the transport');
 $assert((int)$row($event)['sent']===1&&(int)$row($event)['telegram_message_id']===101&&(int)$row($event)['delivered']>0&&$receipt_calls[0]===[$event,101],'A valid Telegram acknowledgement is saved before reporting sent');
 $before=count($calls);$r=st_deliver_outbox($db,$cfg,6,$event,$success);
 $assert($r['sent']===0&&count($calls)===$before,'An already acknowledged event is never sent again');
 $assert((int)$row('ticket:unrelated')['sent']===0,'Immediate event delivery does not drain unrelated events');
 $fail='review:failed';$enqueue($fail,['text'=>'Yorum onay bekliyor']);
 $failure=static function():array{throw new STTelegramError('Telegram bot anahtarı kabul edilmedi.');};$stamp=time();
 $r=st_deliver_outbox($db,$cfg,6,$fail,$failure);$pending=$row($fail);
 $assert($r['failed']===1&&(int)$pending['sent']===0&&(int)$pending['attempts']===1&&(int)$pending['lease']===0,'A failed immediate attempt remains durable with released lease and attempt count');
 $assert((int)$pending['due']>=$stamp+60&&$pending['last_error']==='Telegram bot anahtarı kabul edilmedi.','The owner sees a safe delivery failure and exponential retry delay');
 $assert((int)$db->query('SELECT count(*) FROM tickets')->fetchColumn()===1,'Notification failure cannot remove an accepted customer record');
 $r=st_deliver_outbox($db,$cfg,6,$fail,$success);$assert($r['sent']===0&&(int)$row($fail)['attempts']===1,'Immediate replay respects failed-event backoff');
 $db->prepare('UPDATE outbox SET due=0 WHERE id=?')->execute([$fail]);$r=st_deliver_outbox($db,$cfg,6,$fail,$success);
 $assert($r['sent']===1&&$row($fail)['last_error']===''&&(int)$row($fail)['telegram_message_id']>0,'Due retry succeeds and clears its previous error');
 $rate='ai:rate';$enqueue($rate,['text'=>'Synthetic question and displayed answer']);$stamp=time();
 $r=st_deliver_outbox($db,$cfg,6,$rate,static function():array{throw new STTelegramError('Telegram gönderim sınırına ulaşıldı.',300);});
 $assert($r['failed']===1&&(int)$row($rate)['due']>=$stamp+300,'Telegram retry_after is respected');
 $missing='visit:missing';$enqueue($missing,['text'=>'Synthetic visitor']);$before=count($calls);
 $r=st_deliver_outbox($db,array_replace($cfg,['telegram_token'=>'']),6,$missing,$success);
 $assert(!$r['configured']&&count($calls)===$before&&(int)$row($missing)['attempts']===0&&$row($missing)['last_error']!=='','Missing configuration is visible without making a provider request');
 $active='ai:active';$enqueue($active,['text'=>'Synthetic active event']);$db->prepare('UPDATE outbox SET lease=? WHERE id=?')->execute([time()+60,$active]);
 $r=st_deliver_outbox($db,$cfg,6,$active,$success);$assert($r['sent']===0&&(int)$row($active)['sent']===0,'An active delivery lease prevents concurrent duplicate sends');
 $parallel='ai:parallel';$enqueue($parallel,['text'=>'Synthetic parallel event']);$other=new PDO('sqlite:'.$temporary.'/test.sqlite',null,null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC]);$second=null;
 $r=st_deliver_outbox($db,$cfg,6,$parallel,static function($method,$payload,$timeout)use($other,$cfg,$parallel,$success,&$second):array{$second=st_deliver_outbox($other,$cfg,6,$parallel,$success);return $success($method,$payload,$timeout);});
 $assert($r['sent']===1&&$second['sent']===0&&(int)$row($parallel)['sent']===1,'Two actual SQLite connections cannot claim the same notification concurrently');
 $transaction='ai:transaction';$enqueue($transaction,['text'=>'Transaction test']);st_transaction_begin($db);$r=st_deliver_outbox($db,$cfg,6,$transaction,$success);
 $assert(($r['deferred']??'')==='transaction'&&$db->inTransaction()&&(int)$row($transaction)['sent']===0,'A caller transaction is neither committed nor dispatched');$db->rollBack();
 $bad='ai:bad';$enqueue($bad,['text'=>'Invalid stored payload']);$db->prepare('UPDATE outbox SET payload=? WHERE id=?')->execute(['{broken',$bad]);$before=count($calls);$r=st_deliver_outbox($db,$cfg,6,$bad,$success);
 $assert($r['failed']===1&&count($calls)===$before&&$row($bad)['last_error']==='Telegram’a ulaşılamadı; bildirim kuyrukta.','Malformed stored JSON stays pending without exposing implementation details');
 $unack='ai:unack';$enqueue($unack,['text'=>'Unacknowledged reply']);$r=st_deliver_outbox($db,$cfg,6,$unack,static function():array{return ['ok'=>true,'result'=>true];});
 $assert($r['failed']===1&&(int)$row($unack)['sent']===0&&(int)$row($unack)['telegram_message_id']===0,'A response without message_id is not reported delivered');
 $unsupported='ai:unsupported';$enqueue($unsupported,['_method'=>'deleteWebhook','text'=>'Must not run']);$before=count($calls);$r=st_deliver_outbox($db,$cfg,6,$unsupported,$success);
 $assert($r['failed']===1&&count($calls)===$before,'Stored queue payload cannot invoke unrelated Telegram methods');
 $ack='ack:expired';$enqueue($ack,['_method'=>'answerCallbackQuery','callback_query_id'=>'synthetic','text'=>'Decision persisted'],time()-60);$before=count($calls);$r=st_deliver_outbox($db,$cfg,6,$ack,$success);
 $assert($r['sent']===0&&count($calls)===$before&&(int)$row($ack)['sent']===1&&strpos($row($ack)['last_error'],'zaman aşımı')!==false,'Expired Telegram UI acknowledgements cannot loop forever');
 $long='ai:long';$text=str_repeat('Üretici belgesindeki açıklama ve sorulan soru. ',240);$enqueue($long,['text'=>$text]);$parts=(int)$db->query("SELECT count(*) FROM outbox WHERE id='ai:long' OR id LIKE 'ai:long:part:%'")->fetchColumn();$before=count($calls);$r=st_deliver_outbox($db,$cfg,20,$long,$success);
 $assert($parts>1&&$r['sent']===$parts&&count($calls)-$before===$parts,'A single immediate event attempts all of its safe-length AI chunks');
 $joined='';foreach(array_slice($calls,$before) as $call)$joined.=preg_replace('/^\[\d+\/\d+\] /','',$call[1]['text']);
 $assert($joined===st_notification_text('ai',$text),'Split AI notifications retain the complete displayed answer');
 $literal='ai:percent%';$enqueue($literal,['text'=>'Literal ID']);$enqueue('ai:percentOTHER',['text'=>'Not a prefix child']);$r=st_deliver_outbox($db,$cfg,6,$literal,$success);
 $assert($r['sent']===1&&(int)$row('ai:percentOTHER')['sent']===0,'Event selection uses literal prefixes rather than SQL LIKE wildcards');
 $damaged='ticket:damaged';file_put_contents($temporary.'/assets/notifications/ticket.png','broken');$enqueue($damaged,['text'=>'A preserved customer request','reply_markup'=>['inline_keyboard'=>[]]]);$before=count($calls);$r=st_deliver_outbox($db,$cfg,6,$damaged,$success);
 $assert($r['sent']===1&&$calls[$before][0]==='sendMessage'&&strpos($calls[$before][1]['text'],'preserved customer')!==false&&isset($calls[$before][1]['reply_markup']),'Unreadable or corrupt photos fall back to readable text and preserve buttons');
 $lost='ai:lost-lease';$enqueue($lost,['text'=>'Lease ownership test']);$r=st_deliver_outbox($db,$cfg,1,$lost,static function($method,$payload,$timeout)use($db,$lost,$success):array{$db->prepare('UPDATE outbox SET lease=lease+100 WHERE id=?')->execute([$lost]);return $success($method,$payload,$timeout);});
 $assert($r['sent']===0&&$r['failed']===1&&(int)$row($lost)['sent']===0&&(int)$row($lost)['lease']>time(),'A stale lease owner cannot confirm or release another worker\'s row');
 $bounded='ai:budget';for($i=0;$i<3;$i++)$enqueue($bounded.':part:'.$i,['text'=>'Short budget part']);$slow=static function($method,$payload,$timeout)use($success):array{usleep(170000);return $success($method,$payload,$timeout);};$r=st_deliver_outbox($db,$cfg,20,$bounded,$slow,150);
 $assert($r['sent']===1,'A shared request budget stops before starting the next part');
 $secret='123456789:'.str_repeat('SecretToken',6);$safe=st_delivery_safe_error(new STTelegramError('Provider URL contains bot'.$secret));
 $assert(strpos($safe,$secret)===false&&strpos($safe,'[gizlendi]')!==false,'Safe provider error storage redacts accidental bot tokens');
 foreach(['visit'=>'visit.png','review'=>'review.png','ticket'=>'ticket.png'] as $kind=>$photo){$rows=st_notification_rows($kind.':asset',['text'=>'Synthetic event']);$assert($rows[0][1]['_photo']===$photo,'Original '.$kind.' image association is preserved');}
 $report=['passed'=>true,'checks'=>count($checks),'cases'=>$checks,'transport_calls'=>count($calls),'real_provider_requests'=>0,'production_private_read'=>false];
 $output=$root.'/build/notification-dispatch-report.json';if(!is_dir(dirname($output)))mkdir(dirname($output),0770,true);file_put_contents($output,json_encode($report,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE)."\n");
 echo json_encode(['passed'=>true,'checks'=>count($checks),'transport_calls'=>count($calls),'real_provider_requests'=>0],JSON_UNESCAPED_UNICODE)."\n";
}finally{$db=null;$other=null;$remove($temporary);}
