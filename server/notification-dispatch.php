<?php
declare(strict_types=1);
/* Event delivery never configures webhooks, generates reports, or opens a DB
 * transaction belonging to a customer record. Telegram offers no idempotency
 * key: an acknowledgement lost after remote acceptance cannot be made exactly
 * once. Known receipts and active leases are always respected. */
function st_delivery_safe_error(Throwable $error): string {
    $text=$error instanceof STTelegramError?$error->getMessage():'Telegram’a ulaşılamadı; bildirim kuyrukta.';
    $text=preg_replace('/(?:bot)?[0-9]{6,15}:[A-Za-z0-9_-]{25,180}|AIza[A-Za-z0-9_-]{25,}|[a-f0-9]{48,}/i','[gizlendi]',$text);
    return substr(preg_replace('/[\x00-\x1f]/',' ',(string)$text),0,500);
}
function st_delivery_filter(?string $event_id,array &$params): string {
    if($event_id===null)return '';
    $params[]=$event_id;$params[]=$event_id;$params[]=$event_id;
    return " AND (id=? OR substr(id,1,length(?)+1)=?||':')";
}
function st_delivery_photo_payload(array $payload): array {
    $name=(string)($payload['_photo']??'');$file=__DIR__.'/assets/notifications/'.$name;
    if(in_array($name,['visit.png','review.png','ticket.png'],true)&&is_file($file)&&is_readable($file)&&filesize($file)<=2000000&&file_get_contents($file,false,null,0,8)==="\x89PNG\r\n\x1a\n")return ['sendPhoto',$payload];
    $text=['chat_id'=>$payload['chat_id'],'text'=>(string)($payload['caption']??'Sağlam Teknik bildirimi')];
    if(isset($payload['reply_markup']))$text['reply_markup']=$payload['reply_markup'];
    return ['sendMessage',$text];
}
function st_deliver_outbox(PDO $db,array $cfg,int $limit=20,?string $event_id=null,?callable $transport=null,int $budget_ms=4000): array {
    $result=['sent'=>0,'failed'=>0,'configured'=>false];
    // Never commit, roll back, or dispatch during a caller's record transaction.
    if($db->inTransaction())return $result+['deferred'=>'transaction'];
    $filter_params=[];$filter=st_delivery_filter($event_id,$filter_params);
    $missing=empty($cfg['telegram_token'])?'Telegram bot anahtarı ayarlanmadı.':(empty($cfg['telegram_chat_id'])?'Telegram sohbet kimliği ayarlanmadı.':'');
    if($missing!==''){
        $q=$db->prepare('UPDATE outbox SET last_error=? WHERE sent=0 AND lease<?'.$filter);$q->execute(array_merge([$missing,time()],$filter_params));
        return $result+['error'=>$missing];
    }
    $result['configured']=true;$transport=$transport??'st_telegram';
    $deadline=microtime(true)+max(100,min(30000,$budget_ms))/1000;$limit=max(1,min(50,$limit));
    for($i=0;$i<$limit;$i++){
        $remaining=(int)floor(($deadline-microtime(true))*1000);if($remaining<100)break;
        $db->exec('BEGIN IMMEDIATE');
        try{
            $q=$db->prepare('SELECT * FROM outbox WHERE sent=0 AND due<=? AND lease<?'.$filter.' ORDER BY due,created,id LIMIT 1');
            $q->execute(array_merge([time(),time()],$filter_params));$row=$q->fetch(PDO::FETCH_ASSOC);
            if(!$row){$db->exec('COMMIT');break;}
            $lease=time()+max(30,(int)ceil($remaining/1000)+5);
            $q=$db->prepare('UPDATE outbox SET lease=? WHERE id=? AND sent=0 AND lease<?');$q->execute([$lease,$row['id'],time()]);
            $db->exec('COMMIT');
        }catch(Throwable $error){if($db->inTransaction())$db->exec('ROLLBACK');throw $error;}
        try{
            $payload=json_decode($row['payload'],true);if(!is_array($payload))throw new RuntimeException('Invalid stored notification');
            $method=$payload['_method']??'sendMessage';unset($payload['_method']);
            if(!in_array($method,['sendMessage','sendPhoto','answerCallbackQuery'],true))throw new RuntimeException('Unsupported stored notification method');
            if($method==='answerCallbackQuery'&&(int)$row['created']<time()-30){$q=$db->prepare('UPDATE outbox SET sent=1,lease=0,last_error=? WHERE id=? AND lease=?');$q->execute(['Onay bildirimi zaman aşımına uğradı; karar kaydı korunuyor.',$row['id'],$lease]);continue;}
            if(in_array($method,['sendMessage','sendPhoto'],true))$payload['chat_id']=$cfg['telegram_chat_id'];
            if($method==='sendPhoto')[$method,$payload]=st_delivery_photo_payload($payload);
            $receipt=$transport($method,$payload,max(100,(int)floor(($deadline-microtime(true))*1000)));
            $message_id=$receipt['result']['message_id']??null;
            if(empty($receipt['ok'])||(in_array($method,['sendMessage','sendPhoto'],true)&&(!is_int($message_id)||$message_id<=0)))throw new STTelegramError('Telegram teslim onayı alınamadı; bildirim kuyrukta.');
            $db->exec('BEGIN IMMEDIATE');
            try{
                $q=$db->prepare("UPDATE outbox SET sent=1,lease=0,last_error='',telegram_message_id=?,delivered=? WHERE id=? AND lease=? AND sent=0");
                $q->execute([in_array($method,['sendMessage','sendPhoto'],true)?$message_id:null,time(),$row['id'],$lease]);
                $confirmed=$q->rowCount()>0;
                if($confirmed&&in_array($method,['sendMessage','sendPhoto'],true))st_delivery_receipt($db,$row['id'],$message_id);
                $db->exec('COMMIT');
            }catch(Throwable $error){if($db->inTransaction())$db->exec('ROLLBACK');throw $error;}
            if(!$confirmed)throw new RuntimeException('Notification lease changed before receipt persistence');
            $result['sent']++;
        }catch(Throwable $error){
            $attempt=(int)$row['attempts']+1;$message=st_delivery_safe_error($error);
            $retry=$error instanceof STTelegramError?(int)$error->retry_after:0;
            $delay=max($retry,min(3600,30*(2**min($attempt,7))));
            $q=$db->prepare('UPDATE outbox SET attempts=?,due=?,lease=0,last_error=? WHERE id=? AND lease=? AND sent=0');
            $q->execute([$attempt,time()+$delay,$message,$row['id'],$lease]);$result['failed']++;
        }
    }
    return $result;
}
function st_delivery_attempt(string $event_id,int $limit=6): array {
    try{return st_deliver_outbox(st_db(),st_config(),$limit,$event_id,null,4000);}
    catch(Throwable $error){
        // Only safe operational context is logged; never the event/customer data.
        @error_log('Sağlam Teknik bildirim denemesi tamamlanamadı; kalıcı kuyruk korunuyor.');
        return ['sent'=>0,'failed'=>1,'configured'=>false,'error'=>'Bildirim kuyruğu şu anda işlenemedi.'];
    }
}
