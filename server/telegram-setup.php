<?php
declare(strict_types=1);
/* Yalnız CLI worker tarafından çağrılır; ziyaretçi isteği webhook ayarını değiştirmez. */
function st_auto_webhook(): void {
    $lock=fopen(st_private().'/webhook-setup.lock','c');if(!$lock)return;
    try{
        if(!flock($lock,LOCK_EX|LOCK_NB))return;
        $cfg=st_prepare_webhook_config();
        if(!$cfg['telegram_token']||!$cfg['telegram_chat_id']||(!$cfg['telegram_admin_ids']&&!ctype_digit((string)$cfg['telegram_chat_id'])))return;
        $db=st_db();$fingerprint=hash('sha256',$cfg['site_url'].'|'.$cfg['telegram_token'].'|'.$cfg['telegram_webhook_secret']);
        $old=json_decode($db->query("SELECT v FROM meta WHERE k='webhook_setup'")->fetchColumn()?:'null',true);
        if(is_array($old)&&($old['fingerprint']??'')===$fingerprint&&($old['until']??0)>time())return;
        $info=st_telegram('getWebhookInfo',[]);$url=$info['result']['url']??'';
        if($url!==''&&parse_url($url,PHP_URL_HOST)!==parse_url($cfg['site_url'],PHP_URL_HOST))throw new RuntimeException('Bot başka bir siteye bağlı; yönetim ekranındaki Telegram onayını bağla düğmesiyle doğru siteyi seçin.');
        $r=st_telegram('setWebhook',['url'=>rtrim($cfg['site_url'],'/').'/api.php?action=webhook','secret_token'=>$cfg['telegram_webhook_secret'],'allowed_updates'=>['callback_query']]);
        if(($r['result']??false)!==true)throw new RuntimeException('Telegram onay bağlantısı doğrulanamadı.');
        $db->prepare("INSERT INTO meta(k,v) VALUES('webhook_setup',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v")->execute([json_encode(['fingerprint'=>$fingerprint,'until'=>time()+86400])]);
        $db->prepare("INSERT INTO meta(k,v) VALUES('webhook_error','') ON CONFLICT(k) DO UPDATE SET v=excluded.v")->execute();
    }catch(Throwable $e){st_db()->prepare("INSERT INTO meta(k,v) VALUES('webhook_error',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v")->execute([$e instanceof STTelegramError?$e->getMessage():$e->getMessage()]);}
    finally{flock($lock,LOCK_UN);fclose($lock);}
}
