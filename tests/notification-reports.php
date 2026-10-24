<?php
declare(strict_types=1);
/**
 * Sentetik ve izole Telegram rapor/mesaj/görsel testi.
 * Gerçek bot, müşteri verisi, cron ve canlı veritabanı kullanılmaz.
 * Kullanım: php tests/notification-reports.php build/production
 */
$public=realpath($argv[1]??dirname(__DIR__).'/build/production');
if(!$public||!is_file($public.'/api.php')||!is_file($public.'/report-support.php'))throw new RuntimeException('Üretim test paketi hazırlanmalı.');
$private=sys_get_temp_dir().'/saglam-report-qa-'.bin2hex(random_bytes(8));
mkdir($private,0700,true);
$clean=static function(string $path)use(&$clean):void{
    if(is_dir($path)){foreach(scandir($path) as $item)if($item!=='.'&&$item!=='..')$clean($path.'/'.$item);rmdir($path);}
    elseif(is_file($path))unlink($path);
};
$checks=[];
$check=static function(bool $ok,string $message)use(&$checks):void{
    $checks[]=$message;
    if(!$ok)throw new RuntimeException($message);
};
try{
    putenv('SAGLAM_PRIVATE_DIR='.$private);
    define('ST_LIBRARY_MODE',true);
    require $public.'/api.php';
    require $public.'/report-support.php';
    $db=st_db();
    $ins=$db->prepare('INSERT INTO daily_stats(day,metric,val) VALUES(?,?,?)');
    foreach([
        ['2026-10-10','visits',7],['2026-10-27','visits',3],
        ['2026-10-27','ai_questions',2],['2026-10-27','tickets',1],
        ['2026-10-31','visits',5],['2026-10-31','reviews',1],
        ['2026-11-01','visits',4]
    ] as $row)$ins->execute($row);
    $now=new DateTimeImmutable('2026-11-02 00:03:00',new DateTimeZone('Europe/Istanbul'));
    $w=st_report_window('weekly',$now);
    $m=st_report_window('monthly',$now);
    $check($w['from']==='2026-10-26'&&$w['to']==='2026-11-01','Geçen hafta pazartesi–pazar');
    $check($m['from']==='2026-10-01'&&$m['to']==='2026-10-31','Önceki ay tam takvim ayı');
    $wt=st_build_period_report($db,$w);
    $mt=st_build_period_report($db,$m);
    $check(strpos($wt,'Toplam ziyaret: 12')!==false&&strpos($wt,'AI Usta soruları: 2')!==false,'Haftalık ziyaret ve AI toplamları');
    $check(strpos($mt,'Toplam ziyaret: 15')!==false&&strpos($mt,'Servis talepleri: 1')!==false,'Aylık ziyaret ve servis toplamları');
    $check(st_enqueue_period_report('weekly',$now)&&st_enqueue_period_report('monthly',$now),'İki dönem bir kez kuyruğa yazıldı');
    $check(!st_enqueue_period_report('weekly',$now)&&!st_enqueue_period_report('monthly',$now),'Tekrar bildirim oluşmaz');
    $rows=$db->query("SELECT id,payload FROM outbox WHERE id LIKE 'weekly:%' OR id LIKE 'monthly:%'")->fetchAll(PDO::FETCH_ASSOC);
    $check(count($rows)===2,'Tam iki rapor kuyrukta');
    foreach($rows as $r){
        $payload=json_decode($r['payload'],true);
        $check(strpos($payload['text']??'','📊')!==false&&strpos($payload['text']??'','🛠️')!==false,'Dikey ikonlu rapor metni');
    }
    foreach(['visit.png','review.png','ticket.png'] as $name){
        $f=$public.'/assets/notifications/'.$name;
        $check(is_file($f)&&file_get_contents($f,false,null,0,8)==="\x89PNG\r\n\x1a\n",'Özgün bildirim görseli: '.$name);
    }
    $check(function_exists('st_deliver_now'),'Doğrudan Telegram teslim fonksiyonu üretim kodunda var');
    $baseCount=(int)$db->query('SELECT COUNT(*) FROM outbox')->fetchColumn();
    st_enqueue($db,'visit:direct-qa',['text'=>'Sadece sentetik ziyaret testi']);
    st_deliver_now('visit:direct-qa');
    $q=$db->query("SELECT sent,attempts FROM outbox WHERE id='visit:direct-qa'")->fetch(PDO::FETCH_ASSOC);
    $check((int)$q['sent']===0&&(int)$q['attempts']===0,'Bot ayarı yoksa anlık girişim canlı ağa bağlanmadan kuyrukta korunur');
    st_deliver_now('visit:direct-qa');
    $check((int)$db->query('SELECT COUNT(*) FROM outbox')->fetchColumn()===$baseCount+1,'Tekrar denemek aynı ziyareti çoğaltmaz');
    $original=$db->query("SELECT sent FROM outbox WHERE id='visit:direct-qa'")->fetchColumn();
    $check($original!==false,'Ziyaret olayı saklandı');
    foreach(['visit','review','ticket'] as $kind){
        $rows=st_notification_rows($kind.':synthetic',['text'=>'Sentetik bildirim']);
        $check(($rows[0][1]['_method']??'')==='sendPhoto','Telegram görsel yöntemi: '.$kind);
        $photo=st_photo_fields($rows[0][1]);
        $check($photo['photo'] instanceof CURLFile,'Görsel dosyası hazırlanabiliyor: '.$kind);
    }
    $long=str_repeat('Güvenli test yanıtı. ',300);
    $rows=st_notification_rows('ai:synthetic',['text'=>"🤖 AI Usta\n\n❓ Soru\n💡 ".$long]);
    $check(count($rows)>1,'Uzun AI soru-cevap metni güvenle bölünüyor');
    echo json_encode(['ok'=>true,'checks'=>$checks,'provider_calls'=>0,'production_data_access'=>false],JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE)."\n";
}finally{
    putenv('SAGLAM_PRIVATE_DIR');
    $clean($private);
}
