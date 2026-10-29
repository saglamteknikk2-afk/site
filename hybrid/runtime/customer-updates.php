<?php
declare(strict_types=1);
/** Servis müşterisinin özel takip bağlantısı ve Telegram ile onaylı bilgilendirilmesi. */
function st_customer_schema(PDO $db): void {
    $cols=array_column($db->query('PRAGMA table_info(ticket_operations)')->fetchAll(PDO::FETCH_ASSOC),'name');
    foreach(['customer_token'=>"TEXT NOT NULL DEFAULT ''",'customer_chat_id'=>"TEXT NOT NULL DEFAULT ''",'eta_minutes'=>'INTEGER','eta_updated'=>'INTEGER'] as $name=>$definition)
        if(!in_array($name,$cols,true))$db->exec('ALTER TABLE ticket_operations ADD COLUMN '.$name.' '.$definition);
    $db->exec("CREATE TABLE IF NOT EXISTS ticket_customer_updates(id INTEGER PRIMARY KEY AUTOINCREMENT,ticket_id TEXT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,kind TEXT NOT NULL,body TEXT NOT NULL,created INTEGER NOT NULL,telegram_sent INTEGER NOT NULL DEFAULT 0,telegram_attempts INTEGER NOT NULL DEFAULT 0,telegram_due INTEGER NOT NULL DEFAULT 0);
        CREATE INDEX IF NOT EXISTS ticket_customer_updates_recent ON ticket_customer_updates(ticket_id,id);
        CREATE TABLE IF NOT EXISTS telegram_customer_dialogs(actor TEXT PRIMARY KEY,ticket_id TEXT NOT NULL,mode TEXT NOT NULL,expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS telegram_customer_delete_tokens(token TEXT PRIMARY KEY,actor TEXT NOT NULL,update_id INTEGER NOT NULL,expires INTEGER NOT NULL,consumed INTEGER NOT NULL DEFAULT 0);");
    $updateCols=array_column($db->query('PRAGMA table_info(ticket_customer_updates)')->fetchAll(PDO::FETCH_ASSOC),'name');
    if(!in_array('telegram_lease',$updateCols,true))$db->exec('ALTER TABLE ticket_customer_updates ADD COLUMN telegram_lease INTEGER NOT NULL DEFAULT 0');
    $rows=$db->query("SELECT ticket_id FROM ticket_operations WHERE customer_token=''")->fetchAll(PDO::FETCH_COLUMN);
    $q=$db->prepare("UPDATE ticket_operations SET customer_token=? WHERE ticket_id=? AND customer_token=''");
    foreach($rows as $id)$q->execute([bin2hex(random_bytes(16)),$id]);
    $db->exec('CREATE UNIQUE INDEX IF NOT EXISTS ticket_operations_public_token ON ticket_operations(customer_token)');
}
function st_customer_tracking_url(PDO $db,string $id): string {
    $q=$db->prepare('SELECT customer_token FROM ticket_operations WHERE ticket_id=?');$q->execute([$id]);
    $token=(string)$q->fetchColumn();
    return preg_match('/^[a-f0-9]{32}$/D',$token)?rtrim(st_config()['site_url'],'/').'/servis-takip.html?kod='.$token:'';
}
function st_customer_by_token(PDO $db,string $token): ?array {
    if(!preg_match('/^[a-f0-9]{32}$/D',$token))return null;
    $q=$db->prepare('SELECT * FROM ticket_operations WHERE customer_token=?');$q->execute([$token]);
    $row=$q->fetch(PDO::FETCH_ASSOC);return $row?:null;
}
function st_customer_bot_username(PDO $db): string {
    $name=(string)($db->query("SELECT v FROM meta WHERE k='telegram_bot_username'")->fetchColumn()?:'');
    if(preg_match('/^[a-zA-Z0-9_]{5,32}$/D',$name))return $name;
    $last=(int)($db->query("SELECT v FROM meta WHERE k='telegram_bot_check'")->fetchColumn()?:0);
    if($last>time()-3600)return '';
    $db->prepare("INSERT INTO meta(k,v) VALUES('telegram_bot_check',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v")->execute([(string)time()]);
    try{
        $result=st_telegram('getMe',[],2400);$name=(string)($result['result']['username']??'');
        if(preg_match('/^[a-zA-Z0-9_]{5,32}$/D',$name)){
            $db->prepare("INSERT INTO meta(k,v) VALUES('telegram_bot_username',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v")->execute([$name]);return $name;
        }
    }catch(Throwable $ignored){}
    return '';
}
function st_customer_public(PDO $db,string $token): array {
    $row=st_customer_by_token($db,$token);if(!$row)throw new DomainException('Takip bağlantısı geçersiz.');
    $q=$db->prepare('SELECT kind,body,created FROM (SELECT id,kind,body,created FROM ticket_customer_updates WHERE ticket_id=? ORDER BY id DESC LIMIT 30) ORDER BY created ASC,id ASC');
    $q->execute([$row['ticket_id']]);
    $bot=st_customer_bot_username($db);
    return ['ok'=>true,'record_ref'=>substr((string)$row['ticket_id'],-8),'service_level'=>$row['service_level'],'status'=>$row['status'],'status_label'=>st_operations_labels()[$row['status']]??'Talep alındı','eta_minutes'=>$row['eta_minutes']===null?null:(int)$row['eta_minutes'],'eta_updated'=>$row['eta_updated']===null?null:(int)$row['eta_updated'],'updates'=>$q->fetchAll(PDO::FETCH_ASSOC),'telegram_url'=>$bot?'https://t.me/'.$bot.'?start='.$token:'','telegram_subscribed'=>trim((string)$row['customer_chat_id'])!==''];
}
function st_customer_update(PDO $db,string $id,string $body,string $kind='manual'): int {
    $body=trim($body);
    if($body===''||strlen($body)>2500||preg_match('/[\x00-\x08\x0b\x0c\x0e-\x1f]/',$body))throw new DomainException('Mesaj 1-800 karakter olmalıdır.');
    $n=preg_match_all('/./us',$body,$dummy);if($n===false||$n>800)throw new DomainException('Mesaj 1-800 karakter olmalıdır.');
    $q=$db->prepare('SELECT 1 FROM ticket_operations WHERE ticket_id=?');$q->execute([$id]);if(!$q->fetchColumn())throw new DomainException('Servis kaydı bulunamadı.');
    $q=$db->prepare('INSERT INTO ticket_customer_updates(ticket_id,kind,body,created) VALUES(?,?,?,?)');$q->execute([$id,$kind,$body,time()]);return (int)$db->lastInsertId();
}
/** Direct delivery only to a customer who personally started the bot. No guessed phone-to-Telegram mapping. */
function st_customer_deliver(PDO $db,?string $ticketId=null,int $max=6): array {
    if($db->inTransaction())return ['sent'=>0,'pending'=>0];
    $sql="SELECT u.id,u.body,u.ticket_id,o.customer_chat_id FROM ticket_customer_updates u JOIN ticket_operations o ON o.ticket_id=u.ticket_id WHERE u.telegram_sent=0 AND u.telegram_due<=? AND u.telegram_lease<? AND o.customer_chat_id<>''";
    $params=[time(),time()];if($ticketId!==null){$sql.=' AND u.ticket_id=?';$params[]=$ticketId;}
    $sql.=' ORDER BY u.id LIMIT '.max(1,min(15,$max));$q=$db->prepare($sql);$q->execute($params);
    $sent=0;$failed=0;
    foreach($q->fetchAll(PDO::FETCH_ASSOC) as $row){
        $lease=time()+30;$claim=$db->prepare('UPDATE ticket_customer_updates SET telegram_lease=? WHERE id=? AND telegram_sent=0 AND telegram_lease<?');$claim->execute([$lease,$row['id'],time()]);
        if($claim->rowCount()===0)continue;
        try{
            $receipt=st_telegram('sendMessage',['chat_id'=>$row['customer_chat_id'],'text'=>'Sağlam Teknik · Servis bilgilendirmesi'."\n\n".$row['body']]);
            if(empty($receipt['ok']))throw new RuntimeException('Teslim onayı alınamadı.');
            $db->prepare('UPDATE ticket_customer_updates SET telegram_sent=1,telegram_lease=0 WHERE id=? AND telegram_lease=?')->execute([$row['id'],$lease]);$sent++;
        }catch(Throwable $error){
            // No customer text, address, token or API secret is included in the technical log.
            $db->prepare('UPDATE ticket_customer_updates SET telegram_attempts=telegram_attempts+1,telegram_due=?,telegram_lease=0 WHERE id=? AND telegram_lease=?')->execute([time()+300,$row['id'],$lease]);$failed++;
        }
    }
    return ['sent'=>$sent,'failed'=>$failed];
}
function st_customer_eta(PDO $db,string $id,int $minutes,string $operator): array {
    if($minutes<5||$minutes>240)throw new DomainException('Varış süresini 5 ile 240 dakika arasında belirtin.');
    $owns=!$db->inTransaction();if($owns)st_transaction_begin($db);
    try{
        $q=$db->prepare('SELECT status FROM ticket_operations WHERE ticket_id=?');$q->execute([$id]);$status=$q->fetchColumn();
        if($status===false||in_array($status,['completed','cancelled'],true))throw new DomainException('Bu servis kaydı için varış süresi belirlenemiyor.');
        $db->prepare('UPDATE ticket_operations SET eta_minutes=?,eta_updated=?,operator=? WHERE ticket_id=?')->execute([$minutes,time(),substr($operator,0,80),$id]);
        st_customer_update($db,$id,'Tahmini varış süremiz yaklaşık '.$minutes.' dakika. Trafik ve saha koşullarına göre değişebilir; gelişmelerden sizi haberdar edeceğiz.','eta');
        if($owns)$db->commit();
    }catch(Throwable $error){if($owns&&$db->inTransaction())$db->rollBack();throw $error;}
    if($owns)st_customer_deliver($db,$id);
    return ['message'=>'✅ Servis '.substr($id,-8).' · Tahmini '.$minutes.' dakika kaydedildi.' .
        "\n🔐 Müşteri takip bağlantısı: ".st_customer_tracking_url($db,$id),
        'ticket_id'=>$id];
}
function st_customer_status_text(array $row,string $status): string {
    $vip=$row['service_level']==='priority';
    if($status==='accepted')return $vip?'✨ VIP Servis talebiniz ekibimiz tarafından kabul edildi. Size öncelikli servis planlaması yapılıyor. Varış bilgisi netleştiğinde bildireceğiz.':'✅ Servis talebiniz ekibimiz tarafından kabul edildi. Planlama bilgisini sizinle paylaşacağız.';
    if($status==='en_route')return '🚗 Sağlam Teknik ekibi yola çıktı!'.($row['eta_minutes']!==null?' Tahmini varış yaklaşık '.(int)$row['eta_minutes'].' dakika.':'')."\n".'Yol ve trafik koşullarına göre süre değişebilir. Bizi tercih ettiğiniz için teşekkürler.';
    if($status==='completed')return '✅ Servis işleminiz tamamlandı. Sağlam Teknik olarak bizi tercih ettiğiniz için teşekkür ederiz.';
    if($status==='cancelled')return 'Servis talebiniz iptal edildi. Bilgi için 0534 622 5515 numaralı telefonu arayabilirsiniz.';
    return 'Servis talebiniz kaydedildi. İncelendikten sonra size bilgi vereceğiz.';
}
function st_customer_admin(PDO $db,array $message,array $cfg): bool {
    if(!st_telegram_authorized($message['from']??[],$message['chat']??[],$cfg))return false;
    $text=trim((string)($message['text']??''));$actor=(string)$message['chat']['id'].':'.(string)$message['from']['id'];
    $waiting=$db->prepare('SELECT ticket_id,mode,expires FROM telegram_customer_dialogs WHERE actor=?');$waiting->execute([$actor]);$dialog=$waiting->fetch(PDO::FETCH_ASSOC);
    if(preg_match('~^/iptal(?:@[a-zA-Z0-9_]+)?$~ui',$text)||preg_match('~^/(?:yorum|sil)(?:@[a-zA-Z0-9_]+)?(?:\s|$)~ui',$text)){
        // Dialogs never capture names or cancellation text intended for comment moderation.
        $db->prepare('DELETE FROM telegram_customer_dialogs WHERE actor=?')->execute([$actor]);return false;
    }
    if(preg_match('~^/mesaj(?:@[a-zA-Z0-9_]+)?$~ui',$text)){
        $db->prepare('DELETE FROM telegram_customer_dialogs WHERE actor=?')->execute([$actor]);
        return st_customer_admin_delete_list($db,$actor,(string)$message['chat']['id']);
    }

    if(preg_match('/^\/(?:musteri|müşteri)(?:@[a-zA-Z0-9_]+)?\s+([a-f0-9]{24})(?:\s+(.*))?$/uis',$text,$m)){
        $row=st_operations_row($db,$m[1]);if(!$row)throw new DomainException('Servis kaydı bulunamadı.');
        $rest=trim((string)($m[2]??''));
        if($rest==='')return st_customer_admin_dialog($db,$actor,$m[1],'message',(string)$message['chat']['id']);
        return st_customer_admin_send($db,$m[1],$rest,(string)$message['chat']['id']);
    }
    if(preg_match('/^\/varis(?:@[a-zA-Z0-9_]+)?\s+([a-f0-9]{24})\s+(\d{1,3})$/ui',$text,$m)){
        $answer=st_customer_eta($db,$m[1],(int)$m[2],$actor);
        $key='customer-confirm:'.bin2hex(random_bytes(7));st_enqueue($db,$key,['text'=>$answer['message']]);st_delivery_attempt($key);return true;
    }
    if($dialog&&$dialog['expires']<time())throw new DomainException('Seçili mesaj işleminin süresi doldu. İlgili servis kaydında Müşteriye yaz veya Varış süresi düğmesine yeniden basın.');
    if(!$dialog||str_starts_with($text,'/'))return false;
    if($text==='')return true; // Text is required; photos/files cannot be forwarded to the web timeline.
    $reply=(string)($message['reply_to_message']['text']??$message['reply_to_message']['caption']??'');
    if(preg_match('/(?:^|\n)Kayıt: ([a-f0-9]{24})(?:\n|$)/u',$reply,$reference)&&!hash_equals((string)$dialog['ticket_id'],$reference[1]))throw new DomainException('Bu yanıt başka bir servisin eski mesajına ait. Güncel servis düğmesinden işlemi yeniden açın.');
    if($dialog['mode']==='eta'){
        if(!preg_match('/^\d{1,3}$/D',$text))throw new DomainException('Sadece dakika yazın: 40');
        $answer=st_customer_eta($db,$dialog['ticket_id'],(int)$text,$actor);
        $db->prepare('DELETE FROM telegram_customer_dialogs WHERE actor=?')->execute([$actor]);
        $key='customer-confirm:'.bin2hex(random_bytes(7));st_enqueue($db,$key,['text'=>$answer['message']]);st_delivery_attempt($key);return true;
    }
    $sent=st_customer_admin_send($db,$dialog['ticket_id'],$text,(string)$message['chat']['id']);
    $db->prepare('DELETE FROM telegram_customer_dialogs WHERE actor=?')->execute([$actor]);return $sent;
}
function st_customer_admin_dialog(PDO $db,string $actor,string $id,string $mode,string $room): bool {
    $q=$db->prepare('INSERT INTO telegram_customer_dialogs(actor,ticket_id,mode,expires) VALUES(?,?,?,?) ON CONFLICT(actor) DO UPDATE SET ticket_id=excluded.ticket_id,mode=excluded.mode,expires=excluded.expires');$q->execute([$actor,$id,$mode,time()+600]);
    $key='customer-prompt:'.bin2hex(random_bytes(7));
    $ref='📌 Seçili servis kaydı: '.substr($id,-8)."\nKayıt: ".$id;
    $prompt=$ref."\n".($mode==='eta'?'⏱ Bu müşteriye tahmini varış süresini dakika olarak yazın. Örnek: 40':'💬 Bu müşteriye göndermek istediğiniz mesajı yazın. Yalnızca seçilen servisin takip ekranında görünür.');
    st_enqueue($db,$key,['chat_id'=>$room,'text'=>$prompt,'reply_markup'=>['force_reply'=>true,'input_field_placeholder'=>$mode==='eta'?'5–240 arası dakika yazın':'Müşteriye bilgi mesajınızı yazın']]);st_delivery_attempt($key);return true;
}
function st_customer_admin_send(PDO $db,string $id,string $text,string $room): bool {
    $owns=!$db->inTransaction();if($owns)st_transaction_begin($db);
    try{$number=st_customer_update($db,$id,$text);if($owns)$db->commit();}catch(Throwable $error){if($owns&&$db->inTransaction())$db->rollBack();throw $error;}
    $receipt=st_customer_deliver($db,$id);$row=$db->prepare('SELECT phone FROM tickets WHERE id=?');$row->execute([$id]);$phone=preg_replace('/\D/','',(string)$row->fetchColumn());
    if(strlen($phone)===10)$phone='90'.$phone;if(strlen($phone)===11&&str_starts_with($phone,'0'))$phone='9'.$phone;
    $link='';$tracking=st_customer_tracking_url($db,$id);
    if(preg_match('/^90[0-9]{10}$/D',$phone))$link='https://wa.me/'.$phone.'?text='.rawurlencode('Sağlam Teknik: '.(function_exists('mb_substr')?mb_substr($text,0,450):substr($text,0,450)).($tracking?"\n\nServis takibiniz: ".$tracking:''));
    $buttons=$link?['inline_keyboard'=>[[['text'=>'📲 Müşteriye WhatsApp ile gönder','url'=>$link]]]]:null;
    $info='✅ Servis '.substr($id,-8).' · Mesaj bu müşterinin özel takip ekranına kaydedildi.'.($tracking?"\n🔐 Takip: ".$tracking:'')."\n".($receipt['sent']>0?'Telegram botu üzerinden de teslim edildi.':'Telegram otomatik teslimi için müşterinin botu başlatması gerekir. WhatsApp için aşağıdaki bağlantıyı açıp Gönder düğmesine basın.');
    $key='customer-confirm:'.bin2hex(random_bytes(7));$payload=['chat_id'=>$room,'text'=>$info];if($buttons)$payload['reply_markup']=$buttons;
    st_enqueue($db,$key,$payload);st_delivery_attempt($key);return true;
}

function st_customer_admin_delete_list(PDO $db,string $actor,string $room): bool {
    $q=$db->query('SELECT u.id,u.body,u.ticket_id,t.name FROM ticket_customer_updates u JOIN tickets t ON t.id=u.ticket_id ORDER BY u.id DESC LIMIT 10');
    $rows=$q->fetchAll(PDO::FETCH_ASSOC);$event='customer-list:'.bin2hex(random_bytes(7));
    if(!$rows){st_enqueue($db,$event,['text'=>'Henüz müşteriye gönderilmiş bilgi mesajı yok.']);st_delivery_attempt($event);return true;}
    foreach($rows as $i=>$row){
        $token=bin2hex(random_bytes(12));
        $db->prepare('INSERT INTO telegram_customer_delete_tokens(token,actor,update_id,expires) VALUES(?,?,?,?)')->execute([$token,$actor,$row['id'],time()+600]);
        st_enqueue($db,$event.':'.$i,['text'=>'💬 Müşteri bilgilendirmesi '.($i+1)."\n👤 ".$row['name']."\n🆔 ".$row['ticket_id']."\n".substr((string)$row['body'],0,750),'reply_markup'=>['inline_keyboard'=>[[['text'=>'🗑 Takip ekranından sil','callback_data'=>'cm:d:'.$token],['text'=>'İptal','callback_data'=>'cm:c:'.$token]]]]]);
    }
    st_delivery_attempt($event,10);return true;
}
function st_customer_delete_callback(PDO $db,array $query,array $cfg): ?string {
    $data=(string)($query['data']??'');if(strncmp($data,'cm:',3)!==0)return null;
    if(!st_telegram_authorized($query['from']??[],$query['message']['chat']??[],$cfg))throw new DomainException('Yönetim yetkisi yok.');
    if(!preg_match('/^cm:([dc]):([a-f0-9]{24})$/D',$data,$match))throw new DomainException('Mesaj silme düğmesi geçersiz.');
    $actor=(string)$query['message']['chat']['id'].':'.(string)$query['from']['id'];
    $q=$db->prepare('SELECT * FROM telegram_customer_delete_tokens WHERE token=?');$q->execute([$match[2]]);$item=$q->fetch(PDO::FETCH_ASSOC);
    if(!$item||$item['actor']!==$actor||(int)$item['expires']<time())throw new DomainException('Silme yetkisi veya süresi geçersiz.');
    if((int)$item['consumed']!==0)return 'Mesaj silme işlemi daha önce işlendi.';
    $db->prepare('UPDATE telegram_customer_delete_tokens SET consumed=1 WHERE token=?')->execute([$match[2]]);
    if($match[1]==='c')return 'Silme iptal edildi.';
    // Messages delivered to Telegram cannot be retracted by removing a timeline record.
    $db->prepare('DELETE FROM ticket_customer_updates WHERE id=?')->execute([$item['update_id']]);
    return 'Mesaj müşteri takip ekranından kaldırıldı. Daha önce Telegram ile gönderildiyse o sohbetten silinmez.';
}
function st_customer_bot_callback(PDO $db,array $query,array $cfg): ?string {
    $data=(string)($query['data']??'');if(strncmp($data,'cm:',3)===0)return st_customer_delete_callback($db,$query,$cfg);
    if(strncmp($data,'cu:',3)!==0)return null;
    if(!st_telegram_authorized($query['from']??[],$query['message']['chat']??[],$cfg))throw new DomainException('Yönetim yetkisi yok.');
    if(!preg_match('/^cu:([mev]):([a-f0-9]{24}):([a-f0-9]{16})$/D',$data,$m))throw new DomainException('Servis mesajı geçersiz.');
    $row=st_operations_row($db,$m[2]);if(!$row||!hash_equals($row['nonce'],$m[3]))throw new DomainException('Servis mesajı geçersiz veya eski.');
    $actor=(string)$query['message']['chat']['id'].':'.(string)$query['from']['id'];
    if($m[1]==='v'){
        if($row['service_level']!=='priority'||!in_array($row['status'],['accepted','en_route'],true))throw new DomainException('VIP öncelik mesajı ancak kabul edilen VIP taleplerde gönderilebilir.');
        st_customer_admin_send($db,$row['ticket_id'],'✨ VIP Servis talebiniz öncelikli planlamaya alındı. Sağlam Teknik ekibimiz gelişmeleri sizinle paylaşacak. Bizi tercih ettiğiniz için teşekkür ederiz.',(string)$query['message']['chat']['id']);
        return 'VIP müşteri bilgilendirmesi oluşturuldu.';
    }
    st_customer_admin_dialog($db,$actor,$m[2],$m[1]==='e'?'eta':'message',(string)$query['message']['chat']['id']);
    return $m[1]==='e'?'Varış süresini dakika olarak gönderin.':'Müşteri mesajını yazın.';
}
function st_customer_bot_message(PDO $db,array $message,array $cfg): bool {
    $text=trim((string)($message['text']??''));$chat=$message['chat']??[];$from=$message['from']??[];
    if(preg_match('/^\/start(?:@[a-zA-Z0-9_]+)?\s+([a-f0-9]{32})$/D',$text,$m)){
        if(($chat['type']??'')!=='private')return true;
        $row=st_customer_by_token($db,$m[1]);if(!$row)return true;
        $cid=(string)($chat['id']??'');if(!preg_match('/^[0-9]{1,20}$/D',$cid))return true;
        $db->prepare('UPDATE ticket_operations SET customer_chat_id=? WHERE ticket_id=?')->execute([$cid,$row['ticket_id']]);
        try{st_telegram('sendMessage',['chat_id'=>$cid,'text'=>'✅ Sağlam Teknik servis bildirimleri açıldı. Bu servis kaydına ait güncellemeler buraya gelecek. Bildirimleri durdurmak için /dur yazabilirsiniz.']);}catch(Throwable $ignored){}
        st_customer_deliver($db,$row['ticket_id']);return true;
    }
    if($text==='/dur'&&($chat['type']??'')==='private'){
        $db->prepare("UPDATE ticket_operations SET customer_chat_id='' WHERE customer_chat_id=?")->execute([(string)($chat['id']??'')]);
        try{st_telegram('sendMessage',['chat_id'=>(string)$chat['id'],'text'=>'Sağlam Teknik Telegram bildirimleri kapatıldı. Takip bağlantınızdan güncel bilgileri görebilirsiniz.']);}catch(Throwable $ignored){}
        return true;
    }
    if(st_telegram_authorized($from,$chat,$cfg))return st_customer_admin($db,$message,$cfg);
    return true; // Only authorized admin messages fall through to existing /yorum commands.
}
