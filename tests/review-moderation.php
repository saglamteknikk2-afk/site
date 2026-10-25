<?php
declare(strict_types=1);
/* Real SQLite + production helper; synthetic identities, zero provider calls. */
$tmp=sys_get_temp_dir().'/st-review-moderation-'.bin2hex(random_bytes(8));mkdir($tmp,0700,true);
putenv('SAGLAM_PRIVATE_DIR='.$tmp);
file_put_contents($tmp.'/site_apileri,.txt',"SITE_URL=https://fixture.invalid\nTELEGRAM_CHAT_ID=10000002\nTELEGRAM_ADMIN_IDS=10000001,10000003\nTELEGRAM_BOT_TOKEN=\nIP_LOCATION_LOOKUP=0\nVISIT_NOTIFICATIONS=0\nDAILY_REPORT=0\n");
define('ST_LIBRARY_MODE',true);require dirname(__DIR__).'/server/api.php';
$checks=[];$check=static function(bool $ok,string $name)use(&$checks):void{$checks[]=['name'=>$name,'passed'=>$ok];if(!$ok)throw new RuntimeException($name);};
$reject=static function(callable $fn,string $name)use($check):void{$rejected=false;try{$fn();}catch(DomainException $error){$rejected=true;}$check($rejected,$name);};
$remove=static function(string $path)use(&$remove):void{if(is_dir($path)){foreach(scandir($path) as $name)if($name!=='.'&&$name!=='..')$remove($path.'/'.$name);rmdir($path);}else @unlink($path);};
try{
    $db=st_db();$cfg=st_config();
    $row=static function(string $id,string $comment='Sentetik kontrol için yorum metni.')use($db):void{$db->prepare("INSERT INTO reviews(id,author,district,service,cat,rating,comment,status,nonce,created,consent) VALUES(?,?,'Küçükçekmece','Kombi Bakımı / Onarımı','kombi',5,?,'approved',?, ?,1)")->execute([$id,'QA Test Ustası',$comment,str_repeat('a',16),time()]);};
    $first=str_repeat('a',24);$second=str_repeat('b',24);$row($first);$row($second,'Aynı isimde ikinci ve farklı sentetik yorum.');
    $msg=['from'=>['id'=>10000001],'chat'=>['id'=>10000002],'message_id'=>1,'text'=>'/sil'];
    $check(st_telegram_authorized($msg['from'],$msg['chat'],$cfg),'Configured admin is authorized only in the configured chat');
    $check(!st_telegram_authorized($msg['from'],[],array_replace($cfg,['telegram_chat_id'=>''])),'Missing chat ID never authorizes even when configuration is empty');
    $unchanged=st_telegram_error(400,'Bad Request: message is not modified: specified reply markup is exactly the same');
    $check($unchanged->telegram_code===400&&$unchanged->telegram_reason==='message_not_modified','Real Telegram error parser exposes only the exact idempotent edit reason');
    $check(st_telegram_error(400,'Bad Request: message cannot be edited')->telegram_reason===''&&st_telegram_error(500,'message is not modified')->telegram_reason==='','Other Telegram failures cannot acquire idempotent-success metadata');
    $reject(static function()use($db,$cfg,$msg){$bad=$msg;$bad['from']['id']=99999999;st_review_bot_message($db,$bad,$cfg);},'Unknown Telegram sender cannot initiate deletion');
    $reject(static function()use($db,$cfg,$msg){$bad=$msg;$bad['chat']['id']=99999999;st_review_bot_message($db,$bad,$cfg);},'Authorized user in another chat cannot initiate deletion');
    $check((int)$db->query('SELECT count(*) FROM telegram_review_dialogs')->fetchColumn()===0,'Denied senders leave no conversation state');
    $check(st_review_bot_message($db,$msg,$cfg),'Slash command begins an authenticated name conversation');
    $check((int)$db->query('SELECT count(*) FROM telegram_review_dialogs')->fetchColumn()===1,'Name prompt is saved with expiry');
    $queued=(int)$db->query('SELECT count(*) FROM outbox')->fetchColumn();st_review_bot_message($db,$msg,$cfg);
    $check((int)$db->query('SELECT count(*) FROM outbox')->fetchColumn()===$queued,'Repeated Telegram update never sends duplicate prompts');
    $msg['message_id']=2;$msg['text']='QA Test';st_review_bot_message($db,$msg,$cfg);
    $tokens=$db->query('SELECT token,review_id,actor FROM telegram_review_confirmations ORDER BY review_id')->fetchAll();
    $check(count($tokens)===2,'Two same-name reviews get distinct exact-record confirmations');
    $q=$db->query("SELECT payload FROM outbox WHERE id LIKE 'moderation:%' ORDER BY id")->fetchAll();$buttons=[];
    foreach($q as $item){$p=json_decode($item['payload'],true);foreach($p['reply_markup']['inline_keyboard'][0]??[] as $button)$buttons[]=$button;}
    $check(count($buttons)===4&&strlen($buttons[0]['callback_data'])<=64,'Each result has Telegram-sized Sil and İptal controls');
    $query=['from'=>['id'=>10000001],'message'=>['chat'=>['id'=>10000002]],'data'=>'rd:d:'.$tokens[0]['token']];
    $reject(static function()use($db,$cfg,$query){$bad=$query;$bad['from']['id']=10000003;st_review_bot_callback($db,$bad,$cfg);},'Another authorized admin cannot reuse the first admin confirmation');
    $cancel=$query;$cancel['data']='rd:c:'.$tokens[0]['token'];$check(strpos(st_review_bot_callback($db,$cancel,$cfg),'iptal')!==false,'İptal consumes the confirmation without deleting');
    $check((int)$db->query('SELECT count(*) FROM reviews')->fetchColumn()===2,'Cancel keeps both reviews');
    $query['data']='rd:d:'.$tokens[1]['token'];$db->prepare('UPDATE telegram_review_confirmations SET expires=? WHERE token=?')->execute([time()-1,$tokens[1]['token']]);
    $reject(static function()use($db,$cfg,$query){st_review_bot_callback($db,$query,$cfg);},'Expired confirmation cannot delete a review');
    $db->prepare('UPDATE telegram_review_confirmations SET expires=? WHERE token=?')->execute([time()+600,$tokens[1]['token']]);
    $check(strpos(st_review_bot_callback($db,$query,$cfg),'kaldırıldı')!==false,'Fresh accepted confirmation physically removes the exact review');
    $check((int)$db->query('SELECT count(*) FROM reviews')->fetchColumn()===1,'The other same-name review stays intact');
    $check(in_array($second,st_review_deleted_ids($db),true),'Persistent deleted ID is exposed for client filtering');
    $check(strpos(st_review_bot_callback($db,$query,$cfg),'daha önce')!==false,'Repeated delete callback is harmless');
    $seeds=[['id'=>'existing-0','author'=>'QA Seed','comment'=>'Eski siteden sentetik yorum.','date'=>'01 Oca 2025'],['id'=>'existing-1','author'=>'Başka QA','comment'=>'Başka yorum.']];
    $file=$tmp.'/index.html';file_put_contents($file,'<script id="st-review-seeds" type="application/json">'.json_encode(array_map(static function($r){unset($r['id']);return $r;},$seeds)).'</script>');
    $parsed=st_review_seed_rows($file);$check(array_column($parsed,'id')===['existing-0','existing-1'],'Original seed index IDs are preserved without reindexing');
    $check(count(st_review_find($db,'QA Seed',$seeds))===1,'Legacy static reviews can be found by customer name');
    st_transaction_begin($db);$deleted=st_review_delete($db,'existing-0',$seeds);$db->commit();
    $check($deleted&&in_array('existing-0',st_review_deleted_ids($db,$seeds),true),'Legacy deletion creates a durable stable-ID tombstone');
    $check(count(st_review_find($db,'QA Seed',$seeds))===0,'Deleted static seed does not reappear on the next name search');
    $copy=['id'=>str_repeat('c',24),'author'=>'QA Seed','comment'=>'Eski siteden sentetik yorum.'];
    $check(st_review_filter_deleted($db,[$copy])===[],'Reimporting the same review under another ID cannot resurrect it');
    $check(count(st_review_filter_deleted($db,[$seeds[1]]))===1,'Unrelated older review is preserved');
    $msg['message_id']=3;$msg['text']='normal sohbet';$check(st_review_bot_message($db,$msg,$cfg)===false,'Unrelated admin messages are ignored');
    $check(st_review_bot_callback($db,['data'=>'r:a:legacy'],$cfg)===null,'Existing approve and reject callbacks stay with their existing handler');
    $check((int)$db->query('SELECT count(*) FROM outbox WHERE attempts>0 OR sent<>0')->fetchColumn()===0,'No live Telegram delivery occurred without configured credentials');
    echo json_encode(['passed'=>true,'checks'=>count($checks),'cases'=>$checks,'provider_requests'=>0],JSON_UNESCAPED_UNICODE)."\n";
}finally{$remove($tmp);}
