<?php
declare(strict_types=1);
/* Local counters and calendar reports. No IP, credentials or network transport
 * is stored here; notification delivery is handled by the durable outbox. */
function st_analytics_time(?int $now=null): DateTimeImmutable {
    return (new DateTimeImmutable('@'.($now??time())))->setTimezone(new DateTimeZone('Europe/Istanbul'));
}
function st_analytics_date(string $day): DateTimeImmutable {
    $date=DateTimeImmutable::createFromFormat('!Y-m-d',$day,new DateTimeZone('Europe/Istanbul'));
    if(!$date||$date->format('Y-m-d')!==$day)throw new InvalidArgumentException('Rapor tarihi geçersiz.');
    return $date;
}
function st_analytics_transaction(PDO $db,callable $operation) {
    $owner=!$db->inTransaction();
    if($owner)$db->exec('BEGIN IMMEDIATE');
    try{$result=$operation();if($owner)$db->exec('COMMIT');return $result;}
    catch(Throwable $e){if($owner&&$db->inTransaction())$db->exec('ROLLBACK');throw $e;}
}
function st_analytics_schema(PDO $db,?int $now=null): void {
    $db->exec("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS daily_stats(day TEXT NOT NULL,metric TEXT NOT NULL,val INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(day,metric));
        CREATE TABLE IF NOT EXISTS analytics_visit_events(id TEXT PRIMARY KEY,day TEXT NOT NULL,sid TEXT NOT NULL,created INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS analytics_visit_events_created ON analytics_visit_events(created);
        CREATE TABLE IF NOT EXISTS analytics_report_runs(id TEXT PRIMARY KEY,kind TEXT NOT NULL,start_day TEXT NOT NULL,end_day TEXT NOT NULL,queued INTEGER NOT NULL);");
    $date=st_analytics_time($now);$today=$date->format('Y-m-d');
    $first=(string)$db->query('SELECT MIN(day) FROM daily_stats')->fetchColumn();
    $q=$db->prepare("SELECT v FROM meta WHERE k='last_daily_report'");$q->execute();$legacy=(string)$q->fetchColumn();
    try{st_analytics_date($legacy);}catch(InvalidArgumentException $e){$legacy='';}
    $week=$date->modify('monday this week')->format('Y-m-d');$month=$date->format('Y-m-01');
    $starts=[
        'daily'=>$legacy!==''?min($legacy,$today):($first!==''&&$first<$today?$date->modify('-1 day')->format('Y-m-d'):$today),
        'weekly'=>$first!==''&&$first<$week?st_analytics_date($week)->modify('-7 days')->format('Y-m-d'):$week,
        'monthly'=>$first!==''&&$first<$month?st_analytics_date($month)->modify('-1 month')->format('Y-m-d'):$month,
    ];
    $insert=$db->prepare('INSERT OR IGNORE INTO meta(k,v) VALUES(?,?)');
    $insert->execute(['analytics_started_at',(string)($now??time())]);
    foreach($starts as $kind=>$start)$insert->execute(['analytics_'.$kind.'_cursor',$start]);
}
function st_analytics_increment(PDO $db,string $metric,int $amount=1,?int $now=null): void {
    if(!preg_match('/^[a-z][a-z0-9_]{0,60}$/D',$metric)||$amount<0)throw new InvalidArgumentException('İstatistik sayacı geçersiz.');
    $q=$db->prepare('INSERT INTO daily_stats(day,metric,val) VALUES(?,?,?) ON CONFLICT(day,metric) DO UPDATE SET val=val+excluded.val');
    $q->execute([st_analytics_time($now)->format('Y-m-d'),$metric,$amount]);
}
function st_analytics_is_bot(string $userAgent): bool {
    return (bool)preg_match('/(?:bot\b|spider|crawler|slurp|bingpreview|facebookexternalhit|headlesschrome|lighthouse|pagespeed|monitoring|uptimerobot|ahrefs|semrush|mj12bot|petalbot)/i',substr($userAgent,0,2048));
}
function st_analytics_record_visit(PDO $db,string $sidHash,string $eventId,string $userAgent,?int $now=null): array {
    if(!preg_match('/^[a-f0-9]{64}$/D',$sidHash)||!preg_match('/^[A-Za-z0-9_-]{16,100}$/D',$eventId))throw new InvalidArgumentException('Ziyaret anahtarı geçersiz.');
    $day=st_analytics_time($now)->format('Y-m-d');
    $result=['recorded'=>false,'bot'=>st_analytics_is_bot($userAgent),'unique_session'=>false,'repeat_visit'=>false,'day'=>$day,'event_id'=>$eventId];
    if($result['bot'])return $result;
    return st_analytics_transaction($db,static function()use($db,$sidHash,$eventId,$now,$day,$result):array{
        $id=hash('sha256',$day."\0".$sidHash."\0".$eventId);
        $q=$db->prepare('INSERT OR IGNORE INTO analytics_visit_events(id,day,sid,created) VALUES(?,?,?,?)');
        $q->execute([$id,$day,$sidHash,$now??time()]);
        if($q->rowCount()===0)return $result;
        // Preserve the pre-upgrade daily-unique key, including today's users.
        $q=$db->prepare('INSERT OR IGNORE INTO meta(k,v) VALUES(?,?)');
        $q->execute(['visitor:'.$day.':'.$sidHash,'1']);$unique=$q->rowCount()===1;
        st_analytics_increment($db,'visit_events',1,$now);
        st_analytics_increment($db,$unique?'visits':'visit_returns',1,$now);
        return array_merge($result,['recorded'=>true,'unique_session'=>$unique,'repeat_visit'=>!$unique]);
    });
}
function st_analytics_report(PDO $db,string $kind,string $start,string $end,?int $now=null): array {
    if(!in_array($kind,['daily','weekly','monthly'],true))throw new InvalidArgumentException('Rapor dönemi geçersiz.');
    $begin=st_analytics_date($start);$finish=st_analytics_date($end);
    if($finish<$begin)throw new InvalidArgumentException('Rapor aralığı geçersiz.');
    $q=$db->prepare('SELECT metric,SUM(val) AS val FROM daily_stats WHERE day>=? AND day<=? GROUP BY metric');$q->execute([$start,$end]);
    $values=[];foreach($q->fetchAll(PDO::FETCH_ASSOC) as $row)$values[$row['metric']]=(int)$row['val'];
    $q=$db->prepare("SELECT v FROM meta WHERE k='analytics_started_at'");$q->execute();$began=(int)$q->fetchColumn();
    $complete=$began>0&&$began<=$begin->getTimestamp();
    $stats=['total_visits'=>$values['visit_events']??0,'repeat_visits'=>$values['visit_returns']??0,
        'daily_unique_sessions'=>$values['visits']??0,'search_found'=>$values['search_found']??0,'search_not_found'=>$values['search_not_found']??0,
        'ai_questions'=>$values['ai_questions']??0,'tickets'=>$values['tickets']??0,'reviews'=>$values['reviews']??0];
    $stats['searches']=$stats['search_found']+$stats['search_not_found'];
    $stats['ai_sources']=[];foreach(['gemini','manual','guide','emergency'] as $source)$stats['ai_sources'][$source]=$values['ai_source_'.$source]??0;
    $labels=['daily'=>'GÜNLÜK','weekly'=>'HAFTALIK','monthly'=>'AYLIK'];
    $period=$begin->format('d.m.Y').($start!==$end?' – '.$finish->format('d.m.Y'):'');
    $text='📊 '.$labels[$kind]." SİTE RAPORU\n📅 Dönem: ".$period
        ."\n🕒 Hazırlanma: ".st_analytics_time($now)->format('d.m.Y H:i:s')." (İstanbul)\n\n"
        .'👥 Toplam ziyaret (kaydedilen girişler): '.$stats['total_visits']
        .(!$complete?' (yeni ölçüm; dönemin tamamı için eski toplam ziyaret verisi yok)':'')
        ."\n🔁 Günlük tekrar girişleri: ".$stats['repeat_visits']
        ."\n👤 Günlük tekil oturum toplamı: ".$stats['daily_unique_sessions']
        .($kind!=='daily'?' (hafta/ay boyunca tekil kişi sayısı değildir)':'')
        ."\n🔍 Aramalar: ".$stats['searches'].' (bulundu: '.$stats['search_found'].', bulunamadı: '.$stats['search_not_found'].')'
        ."\n🤖 AI Usta kullanımları: ".$stats['ai_questions']
        ."\n🧠 Yanıt kaynakları: Gemini ".$stats['ai_sources']['gemini'].', üretici belgesi '.$stats['ai_sources']['manual'].', yerel rehber '.$stats['ai_sources']['guide'].', acil yönlendirme '.$stats['ai_sources']['emergency']
        ."\n🛠️ Servis talepleri: ".$stats['tickets']."\n⭐ Yeni yorumlar: ".$stats['reviews'];
    return ['id'=>$kind.':'.($kind==='monthly'?substr($start,0,7):$start),'kind'=>$kind,'start'=>$start,'end'=>$end,'total_visits_complete'=>$complete,'stats'=>$stats,'text'=>$text];
}
function st_analytics_enqueue_report(PDO $db,array $report,?int $now=null,?callable $enqueue=null): bool {
    $enqueue=$enqueue??'st_enqueue';
    return st_analytics_transaction($db,static function()use($db,$report,$now,$enqueue):bool{
        $insert=$db->prepare('INSERT OR IGNORE INTO analytics_report_runs(id,kind,start_day,end_day,queued) VALUES(?,?,?,?,?)');
        $insert->execute([$report['id'],$report['kind'],$report['start'],$report['end'],$now??time()]);
        if($insert->rowCount()===0)return false;
        // The previous reporter used this marker and YYYY-MM monthly IDs.
        // Consume its history even after normal outbox retention removes rows.
        $marker='report-sent:'.$report['id'];$q=$db->prepare('SELECT v FROM meta WHERE k=?');$q->execute([$marker]);
        if($q->fetchColumn()!==false)return false;
        $q=$db->prepare('SELECT id FROM outbox WHERE id=?');$q->execute([$report['id']]);
        $exists=$q->fetchColumn()!==false;
        if(!$exists)$enqueue($db,$report['id'],['text'=>$report['text']]);
        $db->prepare('INSERT OR IGNORE INTO meta(k,v) VALUES(?,?)')->execute([$marker,(string)($now??time())]);
        return !$exists;
    });
}
function st_analytics_queue_due(PDO $db,array $config=[],?int $now=null,?callable $enqueue=null): array {
    if(($config['daily_report']??true)!==true)return [];
    $enqueue=$enqueue??'st_enqueue';$date=st_analytics_time($now);$today=$date->format('Y-m-d');
    $bounds=['daily'=>$today,'weekly'=>$date->modify('monday this week')->format('Y-m-d'),'monthly'=>$date->format('Y-m-01')];
    $steps=['daily'=>'+1 day','weekly'=>'+7 days','monthly'=>'+1 month'];$limits=['daily'=>7,'weekly'=>2,'monthly'=>1];
    return st_analytics_transaction($db,static function()use($db,$config,$now,$enqueue,$bounds,$steps,$limits):array{
        $queued=[];$read=$db->prepare('SELECT v FROM meta WHERE k=?');$write=$db->prepare('UPDATE meta SET v=? WHERE k=?');
        foreach($bounds as $kind=>$bound){
            if(($config[$kind==='daily'?'daily_report':$kind.'_report']??true)!==true)continue;
            $key='analytics_'.$kind.'_cursor';$read->execute([$key]);$cursor=(string)$read->fetchColumn();
            if($cursor==='')continue; // Schema initializes cursors; do not invent historical periods.
            for($i=0;$i<$limits[$kind]&&$cursor<$bound;$i++){
                $next=st_analytics_date($cursor)->modify($steps[$kind])->format('Y-m-d');
                if($next>$bound)break;
                $end=st_analytics_date($next)->modify('-1 day')->format('Y-m-d');
                $report=st_analytics_report($db,$kind,$cursor,$end,$now);
                if(st_analytics_enqueue_report($db,$report,$now,$enqueue))$queued[]=$report['id'];
                $cursor=$next;$write->execute([$cursor,$key]);
                if($kind==='daily')$db->prepare("INSERT INTO meta(k,v) VALUES('last_daily_report',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v")->execute([$cursor]);
            }
        }
        return $queued;
    });
}
function st_analytics_cleanup(PDO $db,?int $now=null): void {
    $db->prepare('DELETE FROM analytics_visit_events WHERE created<?')->execute([($now??time())-32*86400]);
}
