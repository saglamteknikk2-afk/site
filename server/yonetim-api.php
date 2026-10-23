<?php
declare(strict_types=1);
define('ST_LIBRARY_MODE',true);require __DIR__.'/api.php';

function st_owner_verify(): void {
    $key=(string)(st_config()['admin_access_key']??'');
    if(!$key && is_file(st_private().'/yonetim.key'))$key=trim((string)file_get_contents(st_private().'/yonetim.key'));
    $provided=$_SERVER['HTTP_X_ADMIN_KEY']??'';
    if(strlen($key)<32 || strlen($key)>256 || !is_string($provided) || !hash_equals($key,$provided)) {
        if(in_array('sqlite',PDO::getAvailableDrivers(),true))st_rate('owner-auth',30);
        st_fail('Yönetim erişim anahtarı doğrulanamadı. Paketteki YONETIMI_AC.txt bağlantısını kullanın.',403);
    }
}

function st_owner_state(): array {
    $c=st_config();$sqlite=in_array('sqlite',PDO::getAvailableDrivers(),true);$writable=is_writable(st_private());$reviews=[];$tickets=[];$queue=[];$pending=0;$ai_error='';
    if($sqlite && $writable){$db=st_db();$reviews=$db->query("SELECT r.id,r.author,r.district,r.service,r.rating,r.comment,r.status,MAX(r.notification_sent,COALESCE(o.sent,0)) AS notification_sent,o.last_error AS notification_error,COALESCE(r.telegram_message_id,o.telegram_message_id) AS telegram_message_id FROM reviews r LEFT JOIN outbox o ON o.id='review:'||r.id ORDER BY r.created DESC LIMIT 100")->fetchAll();$tickets=$db->query("SELECT t.id,t.name,t.phone,t.district,t.device,t.issue,t.created,MAX(t.notification_sent,COALESCE(o.sent,0)) AS notification_sent,o.last_error AS notification_error,COALESCE(t.telegram_message_id,o.telegram_message_id) AS telegram_message_id FROM tickets t LEFT JOIN outbox o ON o.id='ticket:'||t.id ORDER BY t.created DESC LIMIT 100")->fetchAll();$queue=$db->query('SELECT id,sent,attempts,last_error,telegram_message_id,due FROM outbox ORDER BY created DESC LIMIT 30')->fetchAll();$pending=(int)$db->query('SELECT count(*) FROM outbox WHERE sent=0')->fetchColumn();$ai_error=$db->query("SELECT v FROM meta WHERE k='ai_error'")->fetchColumn()?:'';}
    return ['ok'=>true,'site_url'=>$c['site_url'],'telegram_set'=>(bool)$c['telegram_token'],'gemini_set'=>(bool)$c['gemini_key'],'gemini_model'=>$c['gemini_model'],'telegram_chat_id'=>$c['telegram_chat_id'],'telegram_admin_ids'=>implode(',',$c['telegram_admin_ids']),'visit_notifications'=>$c['visit_notifications'],'telegram_polling'=>$c['telegram_polling'],'webhook_secret_valid'=>(bool)preg_match('/^[A-Za-z0-9_-]{32,256}$/D',$c['telegram_webhook_secret']),'sqlite_available'=>$sqlite,'curl_available'=>function_exists('curl_init'),'private_writable'=>$writable,'api_file'=>'private/saglam-teknik/site_apileri,.txt','reviews'=>$reviews,'tickets'=>$tickets,'notifications'=>$queue,'pending_notifications'=>$pending,'ai_error'=>$ai_error,'webhook_error'=>isset($db)?($db->query("SELECT v FROM meta WHERE k='webhook_error'")->fetchColumn()?:''):''];
}

function st_owner_settings(array $a): array {
    $old=[];
    $c=st_config_update(function(array $c)use($a,&$old): array {
        $old=$c;
        foreach(['telegram_token','gemini_key','gemini_model'] as $field){$value=$a[$field]??'';if(!is_string($value))throw new DomainException('Anahtar alanlarını kontrol edin.');if(trim($value)!=='')$c[$field]=trim($value);}
        foreach(['site_url','telegram_chat_id'] as $field)if(array_key_exists($field,$a)){$value=$a[$field];if(!is_string($value))throw new DomainException('Ayar alanlarını kontrol edin.');$c[$field]=$field==='site_url'?rtrim(trim($value),'/'):trim($value);}
        if(array_key_exists('telegram_admin_ids',$a)){if(!is_string($a['telegram_admin_ids']))throw new DomainException('Onay kullanıcı ID alanını kontrol edin.');$c['telegram_admin_ids']=array_values(array_filter(array_map('trim',explode(',',$a['telegram_admin_ids'])),function($v){return $v!=='';}));}
        if(array_key_exists('visit_notifications',$a))$c['visit_notifications']=$a['visit_notifications']===true;
        return $c;
    });
    if($c['telegram_token']!==$old['telegram_token'] || $c['telegram_chat_id']!==$old['telegram_chat_id'])st_db()->exec('UPDATE outbox SET due=0 WHERE sent=0 AND lease<'.time());
    return ['ok'=>true,'message'=>'Ayarlar TXT dosyasına kaydedildi. Telegram ve AI testlerini çalıştırın.'];
}

function st_owner_dispatch(): void {
    st_owner_verify();$action=$_GET['action']??'';$method=$_SERVER['REQUEST_METHOD']??'GET';
    if($action==='state' && $method==='GET')st_json(st_owner_state());
    if($method!=='POST')st_fail('İşlem bulunamadı.',404);
    st_require_csrf();$a=st_body();st_rate('owner-action',120);
    if($action==='settings')st_json(st_owner_settings($a));
    if($action==='decide'){
        $id=st_text($a,'id',24,24);$status=$a['status']??'';if(!preg_match('/^[a-f0-9]{24}$/D',$id) || !in_array($status,['approved','rejected'],true))st_fail('Yorum kararı geçersiz.');
        $q=st_db()->prepare("UPDATE reviews SET status=?,decided=? WHERE id=? AND status='pending'");$q->execute([$status,time(),$id]);
        st_json(['ok'=>true,'message'=>$q->rowCount()?($status==='approved'?'Yorum yayınlandı.':'Yorum reddedildi.'):'Bu yorum daha önce işlendi.']);
    }
    if($action==='test-ai'){$r=st_ai(['device'=>'Kombi','issue'=>'Buderus kombi sesli çalışıyor']);$error=st_db()->query("SELECT v FROM meta WHERE k='ai_error'")->fetchColumn()?:'';st_json(['ok'=>true,'connected'=>$r['source']==='ai','message'=>$r['source']==='ai'?'Gemini yanıtı doğrulandı.':($error?:'Belirti rehberi çalışıyor.'),'text'=>$r['text']]);}
    if($action==='test-telegram'){
        $c=st_config();if(!$c['telegram_token'] || !$c['telegram_chat_id'])st_fail('Önce bot anahtarı ve chat ID girip kaydedin.');
        st_telegram('getMe',[]);$info=st_telegram('getWebhookInfo',[]);$event='test:'.bin2hex(random_bytes(12));st_enqueue(st_db(),$event,['text'=>'Sağlam Teknik bağlantı testi. Tarih: '.date('d.m.Y H:i:s').' (İstanbul)']);st_worker(1,$event);
        $q=st_db()->prepare('SELECT sent,telegram_message_id,last_error FROM outbox WHERE id=?');$q->execute([$event]);$r=$q->fetch();
        if(!$r['sent'] || !$r['telegram_message_id'])st_fail($r['last_error']?:'Test mesajı kuyrukta; teslim doğrulanmadı.',502);
        $url=$info['result']['url']??'';$expected=rtrim($c['site_url'],'/').'/api.php?action=webhook';
        st_json(['ok'=>true,'message'=>'Telegram test mesajı teslim edildi. Mesaj no: '.$r['telegram_message_id'].'. '.($url===$expected?'Onay bağlantısı bu siteye kayıtlı.':'Telegram onayını bağla düğmesiyle bu siteyi kaydedin.'),'message_id'=>(int)$r['telegram_message_id'],'webhook_matches'=>$url===$expected]);
    }
    if($action==='setup-webhook'){
        $c=st_prepare_webhook_config(true);
        $r=st_telegram('setWebhook',['url'=>rtrim($c['site_url'],'/').'/api.php?action=webhook','secret_token'=>$c['telegram_webhook_secret'],'allowed_updates'=>['callback_query']]);
        if(($r['result']??false)!==true)st_fail('Telegram onay bağlantısı doğrulanamadı.',502);
        st_json(['ok'=>true,'message'=>'Telegram onay bağlantısı kuruldu. Ana sayfadan bir test yorumu gönderip Telegram’da Onayla/Reddet deneyin.']);
    }
    if($action==='retry-notifications'){st_db()->exec('UPDATE outbox SET due=0 WHERE sent=0 AND lease<'.time());$r=st_worker(3);st_json(['ok'=>true,'message'=>'Telegram’a iletilen: '.($r['sent']??0).'. Kuyruk ve hata durumu aşağıda gösterilir.']);}
    if($action==='telegram-ids'){
        $r=st_telegram('getUpdates',['timeout'=>0,'allowed_updates'=>['message','callback_query']]);$ids=[];$seen=[];
        foreach($r['result']??[] as $u){$m=$u['message']??($u['callback_query']['message']??[]);$from=$u['callback_query']['from']??($m['from']??[]);$user=(string)($from['id']??'');$chat=(string)($m['chat']['id']??'');$pair=$user.':'.$chat;if($user && $chat && !isset($seen[$pair])){$seen[$pair]=true;$ids[]=['user_id'=>$user,'chat_id'=>$chat,'name'=>(string)($from['first_name']??'')];}}
        st_json(['ok'=>true,'ids'=>array_slice($ids,-10)]);
    }
    st_fail('İşlem bulunamadı.',404);
}
if(!defined('ST_OWNER_LIBRARY_MODE')){
    try{st_owner_dispatch();}
    catch(STTelegramError $e){st_fail($e->getMessage(),502);}
    catch(DomainException $e){st_fail($e->getMessage(),400);}
    catch(Throwable $e){st_fail('Yönetim işlemi tamamlanamadı. PHP PDO SQLite, cURL ve private klasörünün yazma iznini kontrol edin.',503);}
}
