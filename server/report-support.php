<?php
declare(strict_types=1);
/* Legacy worker/admin interface; all period totals and queue dedupe now share
 * analytics.php with the request-driven first-traffic fallback. */
require_once __DIR__.'/analytics.php';
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
    $kind=strpos($window['id'],'monthly:')===0?'monthly':'weekly';
    $prepared=DateTimeImmutable::createFromFormat('!d.m.Y H:i:s',$window['prepared_at'],new DateTimeZone('Europe/Istanbul'));
    return st_analytics_report($db,$kind,$window['from'],$window['to'],$prepared?$prepared->getTimestamp():null)['text'];
}
function st_enqueue_period_report(string $period,?DateTimeImmutable $now=null): bool {
    if(!st_config()['daily_report'])return false;
    $window=st_report_window($period,$now);
    $db=st_db();
    if((st_config()[$period.'_report']??true)!==true)return false;
    $prepared=($now??new DateTimeImmutable('now',new DateTimeZone('Europe/Istanbul')))->getTimestamp();
    $report=st_analytics_report($db,$period,$window['from'],$window['to'],$prepared);
    return st_analytics_enqueue_report($db,$report,$prepared);
}
