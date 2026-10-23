<?php
/* Plesk: php /.../httpdocs/worker.php
 * Komutlar: status, test-telegram, test-ai, retry, setup-webhook */
if(PHP_SAPI!=='cli'){http_response_code(404);exit;}
define('ST_LIBRARY_MODE',true);require __DIR__.'/api.php';require __DIR__.'/telegram-setup.php';
try {
    $command=$argv[1]??'';$c=st_config();
    if($command==='setup-webhook') {
        if(!$c['telegram_chat_id'] || (!$c['telegram_admin_ids']&&!ctype_digit((string)$c['telegram_chat_id'])) || !preg_match('/^[A-Za-z0-9_-]{32,256}$/D',$c['telegram_webhook_secret']))throw new RuntimeException('Chat ID, onay kullanıcı ID ve en az 32 karakter webhook sırrını private klasöründeki site_apileri,.txt dosyasına girin.');
        st_telegram('setWebhook',['url'=>rtrim($c['site_url'],'/').'/api.php?action=webhook','secret_token'=>$c['telegram_webhook_secret'],'allowed_updates'=>['callback_query']]);
        echo "Telegram onay bağlantısı kuruldu.\n";
    }elseif($command==='status'){
        $ai_error=st_db()->query("SELECT v FROM meta WHERE k='ai_error'")->fetchColumn();
        $queue=st_db()->query('SELECT id,sent,attempts,last_error,telegram_message_id,delivered,due FROM outbox ORDER BY created DESC LIMIT 30')->fetchAll();
        echo json_encode(['telegram_key_set'=>(bool)$c['telegram_token'],'chat_id_set'=>(bool)$c['telegram_chat_id'],'admin_ids_set'=>(bool)$c['telegram_admin_ids'],'webhook_secret_valid'=>(bool)preg_match('/^[A-Za-z0-9_-]{32,256}$/D',$c['telegram_webhook_secret']),'gemini_key_set'=>(bool)$c['gemini_key'],'gemini_model'=>$c['gemini_model'],'curl_available'=>function_exists('curl_init'),'ai_error'=>$ai_error?:'','notifications'=>$queue],JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE)."\n";
    }elseif($command==='test-telegram'){
        if(!$c['telegram_token']||!$c['telegram_chat_id'])throw new RuntimeException('TXT dosyasına bot anahtarı ve chat ID girin.');
        st_telegram('getMe',[]);$webhook=st_telegram('getWebhookInfo',[]);
        $receipt=st_telegram('sendMessage',['chat_id'=>$c['telegram_chat_id'],'text'=>'Sağlam Teknik bağlantı testi. Tarih: '.date('d.m.Y H:i:s').' (İstanbul)']);
        if(!is_int($receipt['result']['message_id']??null))throw new RuntimeException('Telegram teslim onayı alınamadı.');
        echo 'Telegram test mesajı teslim edildi. Mesaj no: '.$receipt['result']['message_id']."\n";
        echo empty($webhook['result']['url'])?"Onay için setup-webhook komutunu çalıştırın.\n":"Botta webhook kayıtlı; alan adı ve onay ayarlarını kontrol edin.\n";
    }elseif($command==='test-ai'){
        $answer=st_ai(['device'=>'Kombi','issue'=>'Buderus kombi sesli çalışıyor']);
        echo json_encode(['connected'=>$answer['source']==='ai','answer'=>$answer,'error'=>st_db()->query("SELECT v FROM meta WHERE k='ai_error'")->fetchColumn()?:''],JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE)."\n";
    }else{
        if($command==='retry')st_db()->exec('UPDATE outbox SET due=0 WHERE sent=0 AND lease<'.time());
        st_auto_webhook();
        st_check_daily_report(false);
        echo json_encode(st_worker(),JSON_UNESCAPED_UNICODE)."\n";
    }
}catch(Throwable $e){fwrite(STDERR,$e->getMessage()."\n");exit(1);}
