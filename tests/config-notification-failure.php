<?php
declare(strict_types=1);
/* Invalid synthetic Telegram configuration must not lose a saved ticket. */
$directory=sys_get_temp_dir().'/st-config-failure-'.bin2hex(random_bytes(6));mkdir($directory,0700);
$config="TELEGRAM_BOT_TOKEN=invalid-synthetic-token\nTELEGRAM_CHAT_ID=invalid-synthetic-chat\nGEMINI_API_KEY=\nIP_LOCATION_LOOKUP=0\nDAILY_REPORT=0\n";
file_put_contents($directory.'/site_apileri,.txt',$config);putenv('SAGLAM_PRIVATE_DIR='.$directory);
define('ST_LIBRARY_MODE',true);require dirname(__DIR__).'/server/api.php';
$checks=0;$assert=static function(bool $condition,string $name)use(&$checks):void{$checks++;if(!$condition)throw new RuntimeException($name);};
try{
    $cfg=st_config();$assert(count($cfg['configuration_errors'])===2,'Configuration diagnostics identify both invalid Telegram fields');
    $db=st_db();$id=str_repeat('a',24);st_transaction_begin($db);
    $db->prepare('INSERT INTO tickets(id,name,phone,district,device,issue,created) VALUES(?,?,?,?,?,?,?)')->execute([$id,'Sentetik QA','05340000000','Küçükçekmece','Kombi','Sentetik arıza gözlemi',time()]);
    st_enqueue($db,'ticket:'.$id,['text'=>'Sentetik müşteri talebi']);$db->commit();
    $result=st_delivery_attempt('ticket:'.$id);
    $assert($result['failed']===1&&$result['sent']===0,'Invalid token fails locally before any provider request');
    $row=$db->query('SELECT * FROM outbox')->fetch();
    $assert((int)$row['sent']===0&&(int)$row['attempts']===1&&strpos($row['last_error'],'biçimi geçersiz')!==false,'Actionable failure persists without marking delivery');
    $assert((int)$db->query('SELECT COUNT(*) FROM tickets')->fetchColumn()===1,'Customer record survives notification failure');
    $db->exec('UPDATE outbox SET due=0');st_delivery_attempt('ticket:'.$id);
    $assert((int)$db->query('SELECT COUNT(*) FROM outbox')->fetchColumn()===1,'Retry reuses the same durable notification');
    $assert(file_get_contents($directory.'/site_apileri,.txt')===$config,'Reading invalid settings never rewrites the owner configuration');
    echo json_encode(['passed'=>true,'checks'=>$checks,'provider_requests'=>0,'customer_data_used'=>false])."\n";
}finally{
    $db=null;foreach(glob($directory.'/*') as $file)unlink($file);rmdir($directory);putenv('SAGLAM_PRIVATE_DIR');
}
