<?php
declare(strict_types=1);
/** Transactional service callbacks and operator replies. No network in mutation. */
function st_telegram_service_schema(PDO $db): void {
    $db->exec('CREATE TABLE IF NOT EXISTS telegram_service_receipts(k TEXT PRIMARY KEY,result TEXT NOT NULL,created INTEGER NOT NULL)');
}
function st_telegram_service_text(string $text,int $limit=180): string {
    preg_match_all('/./us',$text,$parts);
    return implode('',array_slice($parts[0]??[] ,0,$limit));
}
function st_telegram_service_update(PDO $db,array $update,array $cfg): ?array {
    $query=is_array($update['callback_query']??null)?$update['callback_query']:null;
    $message=is_array($update['message']??null)?$update['message']:null;
    $callback=$query!==null&&is_string($query['data']??null)&&preg_match('/^(?:t:|cu:|cm:)/',$query['data']);
    $ticket='';$operation=null;
    if($callback){
        $room=$query['message']['chat']??[];$from=$query['from']??[];
        $key='callback:'.hash('sha256',(string)($query['id']??json_encode($query)));
        if(preg_match('/^(?:t:|cu:)[a-z]:([a-f0-9]{24}):/D',$query['data'],$match))$ticket=$match[1];
    }elseif($message!==null){
        $room=$message['chat']??[];$from=$message['from']??[];
        if(!st_telegram_authorized($from,$room,$cfg))return null;
        $text=trim((string)($message['text']??''));$actor=(string)($room['id']??'').':'.(string)($from['id']??'');
        $waiting=$db->prepare('SELECT ticket_id FROM telegram_customer_dialogs WHERE actor=?');$waiting->execute([$actor]);$ticket=(string)($waiting->fetchColumn()?:'');
        $command=preg_match('~^/(?:musteri|müşteri|varis|mesaj)(?:@[a-zA-Z0-9_]+)?(?:\s|$)~ui',$text);
        if(!$command&&$ticket==='')return null;
        $cancel=preg_match('~^/iptal(?:@[a-zA-Z0-9_]+)?$~ui',$text);
        if(str_starts_with($text,'/')&&!$command&&!$cancel)return null;
        // Comment moderation remains a separate workflow with its own receipts.
        if(preg_match('~^/(?:yorum|sil)(?:@[a-zA-Z0-9_]+)?(?:\s|$)~ui',$text))return null;
        if(!is_int($message['message_id']??null)||$message['message_id']<=0)throw new DomainException('Telegram mesaj kimliği bulunamadı.');
        $key='message:'.hash('sha256',$actor.':'.$message['message_id']);
    }else return null;
    $authorized=st_telegram_authorized($from,$room,$cfg);
    if(!$authorized)return ['ok'=>false,'message'=>'Bu servis kaydını yönetme yetkiniz yok.','callback_id'=>(string)($query['id']??''),'ticket_id'=>'','event_ids'=>[]];
    st_transaction_begin($db);
    try{
        $read=$db->prepare('SELECT result FROM telegram_service_receipts WHERE k=?');$read->execute([$key]);$prior=$read->fetchColumn();
        if($prior!==false){$db->commit();$result=json_decode((string)$prior,true);$result['replayed']=true;return $result;}
        $last=(int)$db->query('SELECT COALESCE(MAX(rowid),0) FROM outbox')->fetchColumn();
        if($callback){
            $answer=st_customer_bot_callback($db,$query,$cfg);
            if($answer===null)$operation=st_operations_callback($db,$query,$cfg);
            $answer=$answer??($operation['message']??'Servis işlemi bulunamadı.');
            if($operation!==null&&!empty($query['message']['message_id'])){
                st_enqueue($db,'service-markup:'.hash('sha256',$key),['_method'=>'editMessageReplyMarkup','chat_id'=>$room['id'],'message_id'=>(int)$query['message']['message_id'],'reply_markup'=>$operation['reply_markup']]);
            }
        }else{
            st_customer_admin($db,$message,$cfg);$answer='Müşteri bilgilendirmesi işlendi.';
            if($cancel){$answer='Müşteri mesajı işlemi iptal edildi.';st_enqueue($db,'service-cancel:'.hash('sha256',$key),['chat_id'=>$room['id'],'text'=>$answer]);}
        }
        $events=$db->query('SELECT id FROM outbox WHERE rowid>'.$last.' ORDER BY rowid')->fetchAll(PDO::FETCH_COLUMN);
        $result=['ok'=>true,'message'=>$answer,'callback_id'=>(string)($query['id']??''),'ticket_id'=>$ticket,'event_ids'=>$events];
        $db->prepare('INSERT INTO telegram_service_receipts(k,result,created) VALUES(?,?,?)')->execute([$key,json_encode($result,JSON_UNESCAPED_UNICODE),time()]);
        $db->commit();return $result;
    }catch(DomainException $error){
        if($db->inTransaction())$db->rollBack();
        $result=['ok'=>false,'message'=>$error->getMessage(),'callback_id'=>(string)($query['id']??''),'ticket_id'=>$ticket,'event_ids'=>[]];
        if(!$callback){
            $id='service-input-error:'.hash('sha256',$key);
            st_enqueue($db,$id,['chat_id'=>$room['id'],'text'=>$result['message']]);$result['event_ids']=[$id];
        }
        return $result;
    }catch(Throwable $error){if($db->inTransaction())$db->rollBack();throw $error;}
}
function st_telegram_service_reply(array $result): array {
    if(($result['callback_id']??'')==='')return ['ok'=>true];
    // Telegram executes a method returned by the webhook response. Feedback is
    // sent before slow notification transport, including when an action fails.
    return ['method'=>'answerCallbackQuery','callback_query_id'=>$result['callback_id'],'text'=>st_telegram_service_text((string)$result['message']),'show_alert'=>true];
}
function st_telegram_service_schedule_delivery(array $result): void {
    register_shutdown_function(static function()use($result):void{
        if(function_exists('fastcgi_finish_request'))fastcgi_finish_request();
        try{
            foreach(array_slice($result['event_ids']??[],0,8) as $id)st_delivery_attempt((string)$id);
            if(($result['ticket_id']??'')!=='')st_customer_deliver(st_db(),$result['ticket_id'],6);
        }catch(Throwable $ignored){@error_log('Sağlam Teknik: servis bilgisi kaydedildi; gönderim kuyruğu yeniden denenecek.');}
    });
}
