<?php
declare(strict_types=1);
/* Real temporary SQLite and parallel PHP processes; no web, private business
 * configuration, customer database or external notification is used. */
require dirname(__DIR__).'/server/analytics.php';
function qa_analytics_db(string $path): PDO {
    $db=new PDO('sqlite:'.$path,null,null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC]);
    $db->exec('PRAGMA busy_timeout=5000');return $db;
}
function qa_analytics_enqueue(PDO $db,string $id,array $payload): void {
    $db->prepare('INSERT OR IGNORE INTO outbox(id,payload) VALUES(?,?)')->execute([$id,json_encode($payload,JSON_UNESCAPED_UNICODE)]);
}
if(($argv[1]??'')==='--race'){
    $db=qa_analytics_db($argv[2]);$now=(int)$argv[3];
    $result=$argv[4]==='visit'?st_analytics_record_visit($db,str_repeat('a',64),'parallel-event-001','Mozilla/5.0',$now):st_analytics_queue_due($db,['weekly_report'=>false,'monthly_report'=>false],$now,'qa_analytics_enqueue');
    echo json_encode($result);exit;
}
$directory=sys_get_temp_dir().'/st-analytics-'.bin2hex(random_bytes(6));mkdir($directory,0700);$checks=0;
$check=static function(bool $condition,string $message)use(&$checks):void{$checks++;if(!$condition)throw new RuntimeException($message);};
$stamp=static function(string $date):int{return (new DateTimeImmutable($date,new DateTimeZone('Europe/Istanbul')))->getTimestamp();};
$make=static function(string $name,int $now)use($directory):PDO{
    $db=qa_analytics_db($directory.'/'.$name.'.sqlite');st_analytics_schema($db,$now);
    $db->exec('CREATE TABLE outbox(id TEXT PRIMARY KEY,payload TEXT NOT NULL)');return $db;
};
$value=static function(PDO $db,string $day,string $metric):int{$q=$db->prepare('SELECT val FROM daily_stats WHERE day=? AND metric=?');$q->execute([$day,$metric]);return (int)$q->fetchColumn();};
$cursor=static function(PDO $db,string $kind,string $day):void{$db->prepare('UPDATE meta SET v=? WHERE k=?')->execute([$day,'analytics_'.$kind.'_cursor']);};
$parallel=static function(string $file,int $now,string $kind)use($check):array{
    $processes=[];$binary=getenv('SAGLAM_PHP_BIN')?:PHP_BINARY;
    for($i=0;$i<6;$i++){
        $pipes=[];$process=proc_open([$binary,__FILE__,'--race',$file,(string)$now,$kind],[0=>['pipe','r'],1=>['pipe','w'],2=>['pipe','w']],$pipes);
        if(!is_resource($process))throw new RuntimeException('Parallel PHP process unavailable');fclose($pipes[0]);$processes[]=[$process,$pipes];
    }
    $results=[];foreach($processes as [$process,$pipes]){$output=stream_get_contents($pipes[1]);$error=stream_get_contents($pipes[2]);fclose($pipes[1]);fclose($pipes[2]);$status=proc_close($process);$check($status===0&&$error==='','Parallel transaction completed without errors');$results[]=json_decode($output,true);}
    return $results;
};
try{
    $before=$stamp('2026-10-24 23:59:58');$after=$stamp('2026-10-25 00:00:01');$db=$make('visits',$before);$sid=str_repeat('a',64);
    $r=st_analytics_record_visit($db,$sid,'navigation-event-001','Mozilla/5.0',$before);
    $check($r['recorded']&&$r['unique_session']&&!$r['repeat_visit'],'First navigation counts a unique session');
    $r=st_analytics_record_visit($db,$sid,'navigation-event-001','Mozilla/5.0',$before);
    $check(!$r['recorded'],'Network retry of same event does not count again');
    $r=st_analytics_record_visit($db,$sid,'navigation-event-002','Mozilla/5.0',$before);
    $check($r['recorded']&&!$r['unique_session']&&$r['repeat_visit'],'Another entry in the same session is a repeat visit');
    st_analytics_record_visit($db,str_repeat('b',64),'navigation-event-001','Mozilla/5.0',$before);
    $check($value($db,'2026-10-24','visit_events')===3&&$value($db,'2026-10-24','visits')===2&&$value($db,'2026-10-24','visit_returns')===1,'Total entries, daily sessions and repeats differ');
    $r=st_analytics_record_visit($db,$sid,'navigation-event-001','Mozilla/5.0',$after);
    $check($r['recorded']&&$r['unique_session']&&$r['day']==='2026-10-25','Istanbul midnight starts a new day even with the same event ID');
    $r=st_analytics_record_visit($db,$sid,'navigation-event-003','Googlebot/2.1',$after);
    $check($r['bot']&&!$r['recorded']&&$value($db,'2026-10-25','visit_events')===1,'Known bot does not change visit counters');
    foreach(['bingbot/2.0','YandexBot/3.0','HeadlessChrome/130','Lighthouse','UptimeRobot/2.0','AhrefsBot'] as $ua)$check(st_analytics_is_bot($ua),'Recognized crawler or automated monitor');
    $check(!st_analytics_is_bot('Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) Safari/604.1'),'Human mobile browser is not excluded');
    $db->exec('BEGIN IMMEDIATE');st_analytics_increment($db,'tickets',1,$after);$db->exec('ROLLBACK');
    $check($value($db,'2026-10-25','tickets')===0,'Counter increment respects caller transaction rollback');
    $db->exec('BEGIN IMMEDIATE');st_analytics_record_visit($db,$sid,'navigation-event-004','Mozilla/5.0',$after);$db->exec('ROLLBACK');
    $check($value($db,'2026-10-25','visit_events')===1,'Nested visit operation does not commit caller transaction');
    foreach([['bad','navigation-event-005'],[$sid,'short']] as [$badSid,$badEvent]){
        $thrown=false;try{st_analytics_record_visit($db,$badSid,$badEvent,'Mozilla/5.0',$after);}catch(InvalidArgumentException $e){$thrown=true;}$check($thrown,'Invalid event/session IDs rejected');
    }
    $legacy=$make('legacy',$before);$legacy->prepare('INSERT INTO meta(k,v) VALUES(?,?)')->execute(['visitor:2026-10-24:'.$sid,'1']);st_analytics_increment($legacy,'visits',4,$before);
    $r=st_analytics_record_visit($legacy,$sid,'navigation-event-legacy','Mozilla/5.0',$before);
    $check(!$r['unique_session']&&$r['repeat_visit']&&$value($legacy,'2026-10-24','visits')===4,'Existing daily session marker survives upgrade without double count');
    $old=st_analytics_report($legacy,'daily','2026-10-23','2026-10-23',$after);
    $check(!$old['total_visits_complete']&&strpos($old['text'],'eski toplam ziyaret verisi yok')!==false,'Unmeasured historical total visits are explicitly unknown');
    $new=st_analytics_report($db,'daily','2026-10-25','2026-10-25',$after);
    $check($new['total_visits_complete']&&$new['stats']['total_visits']===1,'Subsequent complete tracking day has measured total');
    $check(strpos($new['text'],'00:00:01 (İstanbul)')!==false,'Report uses actual Istanbul seconds instead of pretending delivery at midnight');
    $period=$make('calendar',$stamp('2025-12-01 00:00:00'));
    foreach([['2025-12-31','visits',2],['2025-12-31','visit_events',5],['2026-01-04','visits',1],['2026-01-04','visit_events',3],['2026-01-04','visit_returns',2],['2026-01-04','ai_questions',4],['2026-01-04','ai_source_manual',3],['2026-01-04','ai_source_gemini',1],['2026-01-04','search_found',2],['2026-01-04','search_not_found',1],['2026-01-04','tickets',1],['2026-01-04','reviews',2],['2026-01-05','visit_events',100]] as [$day,$metric,$amount])st_analytics_increment($period,$metric,$amount,$stamp($day.' 12:00:00'));
    $cursor($period,'daily','2026-01-04');$cursor($period,'weekly','2025-12-29');$cursor($period,'monthly','2025-12-01');
    $due=st_analytics_queue_due($period,[],$stamp('2026-01-05 00:00:00'),'qa_analytics_enqueue');
    $check($due===['daily:2026-01-04','weekly:2025-12-29','monthly:2025-12'],'Monday in January queues completed day, cross-year week and December with legacy IDs');
    $r=st_analytics_report($period,'weekly','2025-12-29','2026-01-04',$stamp('2026-01-05 00:00:00'));
    $check($r['stats']['total_visits']===8&&$r['stats']['daily_unique_sessions']===3&&$r['stats']['repeat_visits']===2,'Calendar week excludes current Monday data and separates session totals');
    $check($r['stats']['searches']===3&&$r['stats']['ai_questions']===4&&$r['stats']['tickets']===1&&$r['stats']['reviews']===2,'Report includes searches, local/manual AI, tickets and reviews');
    $check($r['stats']['ai_sources']['manual']===3&&$r['stats']['ai_sources']['gemini']===1,'AI source counts remain distinct');
    $check(strpos($r['text'],'hafta/ay boyunca tekil kişi sayısı değildir')!==false,'Daily session sum is not labelled weekly unique people');
    $check(st_analytics_queue_due($period,[],$stamp('2026-01-05 23:00:00'),'qa_analytics_enqueue')===[],'Repeated request and cron on same completed periods do not queue twice');
    $period->exec('DELETE FROM outbox');
    $check(!st_analytics_enqueue_report($period,$r,$after,'qa_analytics_enqueue')&&(int)$period->query('SELECT COUNT(*) FROM outbox')->fetchColumn()===0,'Delivered/queued period ledger survives outbox retention');
    $leap=$make('leap',$stamp('2028-02-01 00:00:00'));$cursor($leap,'monthly','2028-02-01');$cursor($leap,'daily','2028-03-01');$cursor($leap,'weekly','2028-02-28');
    $due=st_analytics_queue_due($leap,[],$stamp('2028-03-01 00:00:00'),'qa_analytics_enqueue');
    $row=$leap->query("SELECT end_day FROM analytics_report_runs WHERE id='monthly:2028-02'")->fetchColumn();
    $check($due===['monthly:2028-02']&&$row==='2028-02-29','Leap-year monthly report ends on February 29');
    $failure=$make('failure',$stamp('2026-10-24 00:00:00'));$cursor($failure,'daily','2026-10-23');
    $thrown=false;try{st_analytics_queue_due($failure,[],$stamp('2026-10-24 00:00:00'),static function(PDO $db,string $id,array $payload):void{qa_analytics_enqueue($db,$id,$payload);throw new RuntimeException('Synthetic queue write failure');});}catch(RuntimeException $e){$thrown=true;}
    $check($thrown&&(int)$failure->query('SELECT COUNT(*) FROM outbox')->fetchColumn()===0&&(int)$failure->query('SELECT COUNT(*) FROM analytics_report_runs')->fetchColumn()===0,'Queue failure rolls back outbox, period ledger and cursor together');
    $check($failure->query("SELECT v FROM meta WHERE k='analytics_daily_cursor'")->fetchColumn()==='2026-10-23','Failed enqueue does not lose its report period');
    $check(st_analytics_queue_due($failure,[],$stamp('2026-10-24 00:00:00'),'qa_analytics_enqueue')===['daily:2026-10-23'],'Next request safely retries failed report');
    $oldMarker=$make('old-marker',$stamp('2026-11-01 00:00:00'));$cursor($oldMarker,'monthly','2026-10-01');$oldMarker->exec("INSERT INTO meta(k,v) VALUES('report-sent:monthly:2026-10','legacy')");
    $due=st_analytics_queue_due($oldMarker,[],$stamp('2026-11-01 00:00:00'),'qa_analytics_enqueue');
    $check($due===[]&&(int)$oldMarker->query('SELECT COUNT(*) FROM outbox')->fetchColumn()===0,'Legacy report-sent marker prevents requeue under the new scheduler');
    $off=$make('disabled',$stamp('2026-10-24 00:00:00'));$cursor($off,'daily','2026-10-01');
    $check(st_analytics_queue_due($off,['daily_report'=>false],$stamp('2026-10-24 00:00:00'),'qa_analytics_enqueue')===[],'Existing daily-report master switch still disables automatic report sends');
    $due=st_analytics_queue_due($off,[],$stamp('2026-10-24 00:00:00'),'qa_analytics_enqueue');
    $check(count($due)===7&&$due[0]==='daily:2026-10-01'&&end($due)==='daily:2026-10-07','Long-gap fallback is bounded and starts with oldest outstanding daily period');
    $due=st_analytics_queue_due($off,[],$stamp('2026-10-24 00:00:00'),'qa_analytics_enqueue');
    $check(count($due)===7&&$due[0]==='daily:2026-10-08','Next traffic continues catch-up without skipping days');
    $fresh=$make('new',$stamp('2026-10-24 12:00:00'));
    $check(st_analytics_queue_due($fresh,[],$stamp('2026-10-24 12:01:00'),'qa_analytics_enqueue')===[],'Empty fresh installation does not invent historical zero reports');
    $race=$make('race',$before);$results=$parallel($directory.'/race.sqlite',$before,'visit');
    $check(count(array_filter($results,static function(array $r):bool{return $r['recorded'];}))===1&&$value($race,'2026-10-24','visit_events')===1,'Concurrent retries record exactly one visit');
    $cursor($race,'daily','2026-10-23');$results=$parallel($directory.'/race.sqlite',$before,'report');
    $check(array_sum(array_map('count',$results))===1&&(int)$race->query('SELECT COUNT(*) FROM outbox')->fetchColumn()===1,'Concurrent request/cron schedulers persist one report');
    st_analytics_cleanup($db,$after+33*86400);
    $check((int)$db->query('SELECT COUNT(*) FROM analytics_visit_events')->fetchColumn()===0&&$value($db,'2026-10-24','visit_events')===3,'Old per-event hashes expire while aggregate history remains');
    echo json_encode(['passed'=>true,'checks'=>$checks,'parallel_php_processes'=>12,'provider_requests'=>0,'production_private_read'=>false])."\n";
}finally{
    foreach(glob($directory.'/*') as $file)unlink($file);rmdir($directory);
}
