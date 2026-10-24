<?php
declare(strict_types=1);
/**
 * Sadece zamanlanmış worker tarafından çağrılır.
 * Raporlar İstanbul takvimine göre kapanan haftayı/ayı özetler.
 * Her dönem için meta + outbox aynı işlemde yazılır; tekrar gönderim oluşmaz.
 */
function st_report_window(string $period, ?DateTimeImmutable $now=null): array {
    $tz=new DateTimeZone('Europe/Istanbul');
    $now=($now??new DateTimeImmutable('now',$tz))->setTimezone($tz);
    if($period==='weekly'){
        $this_start=$now->modify('monday this week')->setTime(0,0);
        $start=$this_start->modify('-7 days');
        $end=$this_start->modify('-1 day');
        $label='HAFTALIK';
        $id='weekly:'.$start->format('Y-m-d');
    }elseif($period==='monthly'){
        $this_start=$now->modify('first day of this month')->setTime(0,0);
        $start=$this_start->modify('first day of previous month');
        $end=$this_start->modify('-1 day');
        $label='AYLIK';
        $id='monthly:'.$start->format('Y-m');
    }else{
        throw new InvalidArgumentException('Rapor dönemi geçersiz.');
    }
    return ['id'=>$id,'label'=>$label,'from'=>$start->format('Y-m-d'),
            'to'=>$end->format('Y-m-d'),'prepared_at'=>$now->format('d.m.Y H:i:s')];
}
function st_build_period_report(PDO $db,array $window): string {
    $q=$db->prepare('SELECT metric,SUM(val) AS total FROM daily_stats WHERE day BETWEEN ? AND ? GROUP BY metric');
    $q->execute([$window['from'],$window['to']]);
    $stats=[];
    foreach($q->fetchAll(PDO::FETCH_ASSOC) as $row)$stats[$row['metric']]=(int)$row['total'];
    $number=static function(string $metric)use($stats):int{return $stats[$metric]??0;};
    $searches=$number('search_found')+$number('search_not_found');
    return "📊 SAĞLAM TEKNİK · ".$window['label']." SİTE RAPORU\n"
        ."📅 Dönem: ".date('d.m.Y',strtotime($window['from']))." – ".date('d.m.Y',strtotime($window['to']))."\n"
        ."🕒 Hazırlanma: ".$window['prepared_at']." (İstanbul)\n\n"
        ."👥 Toplam ziyaret: ".$number('visits')." (günlük tekil oturumların toplamı)\n"
        ."🔎 Site aramaları: ".$searches."\n"
        ."✅ Bulunan: ".$number('search_found')."\n"
        ."⚠️ Bulunamayan: ".$number('search_not_found')."\n"
        ."🤖 AI Usta soruları: ".$number('ai_questions')."\n"
        ."🛠️ Servis talepleri: ".$number('tickets')."\n"
        ."⭐ Yeni yorumlar: ".$number('reviews');
}
function st_enqueue_period_report(string $period,?DateTimeImmutable $now=null): bool {
    if(!st_config()['daily_report'])return false;
    $window=st_report_window($period,$now);
    $db=st_db();
    $db->exec('BEGIN IMMEDIATE');
    try{
        // Outbox daha sonra temizlense de aynı rapor bir daha kuyruğa yazılmaz.
        $q=$db->prepare('INSERT OR IGNORE INTO meta(k,v) VALUES(?,?)');
        $q->execute(['report-sent:'.$window['id'],$window['prepared_at']]);
        if($q->rowCount()===0){$db->exec('COMMIT');return false;}
        st_enqueue($db,$window['id'],['text'=>st_build_period_report($db,$window)]);
        $db->exec('COMMIT');
        return true;
    }catch(Throwable $e){
        if($db->inTransaction())$db->exec('ROLLBACK');
        throw $e;
    }
}
