<?php
declare(strict_types=1);
/* Telegram moderation keeps stable tombstones independently of review imports. */
function st_review_moderation_schema(PDO $db): void {
    $db->exec("CREATE TABLE IF NOT EXISTS review_tombstones(review_id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,deleted INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS telegram_review_dialogs(actor TEXT PRIMARY KEY,expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS telegram_review_confirmations(token TEXT PRIMARY KEY,actor TEXT NOT NULL,review_id TEXT NOT NULL,expires INTEGER NOT NULL,consumed INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS telegram_moderation_updates(k TEXT PRIMARY KEY,created INTEGER NOT NULL);");
}
function st_telegram_authorized(array $from,array $chat,array $cfg): bool {
    $user=(string)($from['id']??'');$room=(string)($chat['id']??'');
    $admins=array_map('strval',$cfg['telegram_admin_ids']??[]);
    if(ctype_digit((string)($cfg['telegram_chat_id']??'')))$admins[]=(string)$cfg['telegram_chat_id'];
    return $user!==''&&$room!==''&&$room===(string)($cfg['telegram_chat_id']??'')&&in_array($user,$admins,true);
}
function st_review_fingerprint(array $review): string {
    return hash('sha256',st_normalize(trim((string)($review['author']??''))).'|'.st_normalize(trim((string)($review['comment']??''))));
}
function st_review_seed_rows(?string $file=null): array {
    $file=$file??__DIR__.'/index.html';
    $html=is_file($file)?file_get_contents($file):'';
    if(!is_string($html)||!preg_match('~<script\b(?=[^>]*\bid=["\']st-review-seeds["\'])[^>]*>(.*?)</script>~si',$html,$match))return [];
    $data=json_decode($match[1],true);$rows=[];
    if(!is_array($data))return [];
    foreach($data as $index=>$review)if(is_array($review)&&!empty($review['author']))$rows[]=array_replace($review,['id'=>'existing-'.$index,'source'=>'existing']);
    return $rows;
}
function st_review_deleted_ids(PDO $db,?array $seeds=null): array {
    $rows=$db->query('SELECT review_id,fingerprint FROM review_tombstones')->fetchAll();
    $ids=array_column($rows,'review_id');$fingerprints=array_fill_keys(array_column($rows,'fingerprint'),true);
    foreach($seeds??st_review_seed_rows() as $row)if(isset($fingerprints[st_review_fingerprint($row)]))$ids[]=$row['id'];
    return array_values(array_unique($ids));
}
function st_review_filter_deleted(PDO $db,array $rows): array {
    $deleted=$db->query('SELECT review_id,fingerprint FROM review_tombstones')->fetchAll();
    $ids=array_fill_keys(array_column($deleted,'review_id'),true);$fingerprints=array_fill_keys(array_column($deleted,'fingerprint'),true);
    return array_values(array_filter($rows,static function(array $row)use($ids,$fingerprints):bool{return !isset($ids[$row['id']])&&!isset($fingerprints[st_review_fingerprint($row)]);}));
}
function st_review_find(PDO $db,string $name,?array $seeds=null): array {
    $term=st_normalize(trim($name));if(strlen($term)<2)return [];
    $all=array_merge($db->query("SELECT id,author,comment,rating,service,created,status FROM reviews ORDER BY created DESC,id DESC LIMIT 2000")->fetchAll(),$seeds??st_review_seed_rows());
    $all=st_review_filter_deleted($db,$all);$found=[];$seen=[];
    foreach($all as $row){
        if(strpos(st_normalize((string)$row['author']),$term)===false)continue;
        $fingerprint=st_review_fingerprint($row);if(isset($seen[$fingerprint]))continue;$seen[$fingerprint]=true;
        $found[]=$row;
    }
    return $found;
}
function st_review_delete(PDO $db,string $id,?array $seeds=null): bool {
    $seeds=$seeds??st_review_seed_rows();$q=$db->prepare('SELECT id,author,comment FROM reviews WHERE id=?');$q->execute([$id]);$row=$q->fetch();
    if(!$row)foreach($seeds as $seed)if($seed['id']===$id){$row=$seed;break;}
    if(!$row)return false;
    $fingerprint=st_review_fingerprint($row);$ids=[$id];
    foreach($seeds as $seed)if(st_review_fingerprint($seed)===$fingerprint)$ids[]=$seed['id'];
    foreach($db->query('SELECT id,author,comment FROM reviews')->fetchAll() as $saved)if(st_review_fingerprint($saved)===$fingerprint)$ids[]=$saved['id'];
    $insert=$db->prepare('INSERT OR IGNORE INTO review_tombstones(review_id,fingerprint,deleted) VALUES(?,?,?)');
    foreach(array_unique($ids) as $target){
        $insert->execute([$target,$fingerprint,time()]);
        $db->prepare('DELETE FROM reviews WHERE id=?')->execute([$target]);
        $db->prepare('DELETE FROM outbox WHERE id=? OR id LIKE ?')->execute(['review:'.$target,'review:'.$target.':%']);
    }
    return true;
}
function st_review_bot_message(PDO $db,array $message,array $cfg): bool {
    if(!st_telegram_authorized($message['from']??[],$message['chat']??[],$cfg))throw new DomainException('Yönetim yetkisi yok.');
    $text=is_string($message['text']??null)?trim($message['text']):'';
    $actor=(string)$message['chat']['id'].':'.(string)$message['from']['id'];
    $q=$db->prepare('SELECT expires FROM telegram_review_dialogs WHERE actor=?');$q->execute([$actor]);$waiting=(int)$q->fetchColumn()>time();
    $command=(bool)preg_match('~^/sil(?:@[a-zA-Z0-9_]+)?(?:\s+(.*))?$~ui',$text,$match);
    $cancel=(bool)preg_match('~^/iptal(?:@[a-zA-Z0-9_]+)?$~ui',$text);
    if(!$command&&!$waiting&&!$cancel)return false;
    $key='msg:'.$actor.':'.(string)($message['message_id']??'');
    st_transaction_begin($db);
    try{
        $done=$db->prepare('SELECT 1 FROM telegram_moderation_updates WHERE k=?');$done->execute([$key]);
        if($done->fetchColumn()){$db->commit();return true;}
        $db->prepare('INSERT INTO telegram_moderation_updates(k,created) VALUES(?,?)')->execute([$key,time()]);
        $name=$command?trim($match[1]??''):$text;
        $chat=(string)$message['chat']['id'];$event='moderation:'.hash('sha256',$key);
        if($cancel){
            $db->prepare('DELETE FROM telegram_review_dialogs WHERE actor=?')->execute([$actor]);
            st_enqueue($db,$event,['chat_id'=>$chat,'text'=>'Yorum silme işlemi iptal edildi.']);
        }elseif($command&&$name===''){
            $db->prepare('INSERT INTO telegram_review_dialogs(actor,expires) VALUES(?,?) ON CONFLICT(actor) DO UPDATE SET expires=excluded.expires')->execute([$actor,time()+600]);
            st_enqueue($db,$event,['chat_id'=>$chat,'text'=>'Hangi müşterinin yorumunu arayayım? İsmini yazın. Vazgeçmek için /iptal yazabilirsiniz.']);
        }else{
            $db->prepare('DELETE FROM telegram_review_dialogs WHERE actor=?')->execute([$actor]);
            if(strlen($name)<2||strlen($name)>160||str_starts_with($name,'/'))$rows=[];
            else $rows=st_review_find($db,$name);
            if(!$rows)st_enqueue($db,$event,['chat_id'=>$chat,'text'=>'Bu isimle görünür bir yorum bulunamadı. /sil ile yeniden arayabilirsiniz.']);
            else foreach(array_slice($rows,0,10) as $index=>$row){
                $token=bin2hex(random_bytes(16));$db->prepare('INSERT INTO telegram_review_confirmations(token,actor,review_id,expires) VALUES(?,?,?,?)')->execute([$token,$actor,$row['id'],time()+600]);
                preg_match('/^.{0,180}/us',(string)($row['comment']??''),$excerpt);
                $date=!empty($row['created'])?date('d.m.Y H:i',(int)$row['created']):(string)($row['date']??'Tarih belirtilmemiş');
                st_enqueue($db,$event.':'.$index,['chat_id'=>$chat,'text'=>'🗑 Yorum silme onayı'."\n👤 ".$row['author']."\n📅 ".$date."\n💬 ".($excerpt[0]??'')."\n\nBu yorumu siteden kaldırmak için Sil seçin. Onay 10 dakika geçerlidir.".(count($rows)>10?"\nİlk 10 eşleşme gösteriliyor; daha belirgin isimle arayabilirsiniz.":''),'reply_markup'=>['inline_keyboard'=>[[['text'=>'🗑 Sil','callback_data'=>'rd:d:'.$token],['text'=>'İptal','callback_data'=>'rd:c:'.$token]]]]]);
            }
        }
        $db->commit();
    }catch(Throwable $error){if($db->inTransaction())$db->rollBack();throw $error;}
    st_delivery_attempt($event);return true;
}
function st_review_bot_callback(PDO $db,array $query,array $cfg): ?string {
    $data=$query['data']??'';if(!is_string($data)||!str_starts_with($data,'rd:'))return null;
    if(!st_telegram_authorized($query['from']??[],$query['message']['chat']??[],$cfg))throw new DomainException('Yönetim yetkisi yok.');
    if(!preg_match('/^rd:([dc]):([a-f0-9]{32})$/D',$data,$match))throw new DomainException('Geçersiz silme onayı.');
    $actor=(string)$query['message']['chat']['id'].':'.(string)$query['from']['id'];
    st_transaction_begin($db);
    try{
        $q=$db->prepare('SELECT * FROM telegram_review_confirmations WHERE token=?');$q->execute([$match[2]]);$row=$q->fetch();
        if(!$row||$row['actor']!==$actor)throw new DomainException('Silme onayı bu kullanıcıya ait değil.');
        if((int)$row['consumed']!==0){$db->commit();return 'Bu silme onayı daha önce işlendi.';}
        if((int)$row['expires']<time())throw new DomainException('Silme onayı sona erdi. /sil ile yeniden arayın.');
        $db->prepare('UPDATE telegram_review_confirmations SET consumed=1 WHERE token=?')->execute([$match[2]]);
        $deleted=$match[1]==='d'?st_review_delete($db,$row['review_id']):false;
        $db->commit();return $match[1]==='c'?'Silme işlemi iptal edildi.':($deleted?'Yorum siteden kaldırıldı.':'Yorum daha önce kaldırılmış.');
    }catch(Throwable $error){if($db->inTransaction())$db->rollBack();throw $error;}
}
