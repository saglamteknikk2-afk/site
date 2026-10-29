"""Exercise the actual SQLite report queue around the Istanbul 23:00 boundary."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PHP = shutil.which('php') or ('/workspace/work/qa/php82-cli' if Path('/workspace/work/qa/php82-cli').exists() else None)

HARNESS = r'''<?php
declare(strict_types=1);
date_default_timezone_set('UTC');
require __DIR__.'/analytics.php';
$input=json_decode(file_get_contents($argv[1]),true);
$db=new PDO('sqlite:'.__DIR__.'/reports.sqlite');
$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);
$db->exec('CREATE TABLE outbox(id TEXT PRIMARY KEY,payload TEXT NOT NULL)');
$stamp=static function(string $value):int{return (new DateTimeImmutable($value,new DateTimeZone('Europe/Istanbul')))->getTimestamp();};
$enqueue=static function(PDO $db,string $id,array $payload):void{
    $db->prepare('INSERT OR IGNORE INTO outbox(id,payload) VALUES(?,?)')->execute([$id,json_encode($payload,JSON_UNESCAPED_UNICODE)]);
};
st_analytics_schema($db,$stamp($input['started']));
foreach($input['stats']??[] as $row)st_analytics_increment($db,$row[1],$row[2],$stamp($row[0]));
foreach($input['cursors']??[] as $kind=>$day)$db->prepare('UPDATE meta SET v=? WHERE k=?')->execute([$day,'analytics_'.$kind.'_cursor']);
foreach($input['sent']??[] as $id)$db->prepare('INSERT INTO meta(k,v) VALUES(?,?)')->execute(['report-sent:'.$id,'1']);
$result=[];
foreach($input['calls'] as $call){
    $throw=(bool)($call['fail']??false);
    $writer=static function(PDO $db,string $id,array $payload)use($enqueue,$throw):void{$enqueue($db,$id,$payload);if($throw)throw new RuntimeException('Synthetic queue error');};
    try{$due=st_analytics_queue_due($db,$call['config']??['weekly_report'=>false,'monthly_report'=>false],$stamp($call['at']),$writer);$error='';}
    catch(Throwable $e){$due=[];$error=$e->getMessage();}
    $messages=[];foreach($db->query('SELECT id,payload FROM outbox ORDER BY id') as $row)$messages[$row['id']]=json_decode($row['payload'],true);
    $cursor=$db->query("SELECT v FROM meta WHERE k='analytics_daily_cursor'")->fetchColumn();
    $result[]=['due'=>$due,'error'=>$error,'messages'=>$messages,'daily_cursor'=>$cursor,'runs'=>(int)$db->query('SELECT COUNT(*) FROM analytics_report_runs')->fetchColumn()];
}
$reports=[];foreach($input['reports']??[] as $row)$reports[]=st_analytics_report($db,$row['kind'],$row['from'],$row['to'],$stamp($row['at']));
echo json_encode(['calls'=>$result,'reports'=>$reports],JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);
'''


@unittest.skipUnless(PHP, 'PHP CLI is required for SQLite scheduling integration')
class Report2300Tests(unittest.TestCase):
    def execute(self, **data):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)
            shutil.copyfile(ROOT/'hybrid/runtime/analytics.php',target/'analytics.php')
            # This helper is part of the immutable original source; staging it
            # avoids reaching the real site's configuration or private folder.
            import sys
            sys.path.insert(0,str(ROOT/'hybrid'))
            from source import load_source
            files,_=load_source(ROOT)
            (target/'transaction.php').write_bytes(files['transaction.php'])
            (target/'run.php').write_text(HARNESS)
            (target/'input.json').write_text(json.dumps(data,ensure_ascii=False))
            proc=subprocess.run([PHP,str(target/'run.php'),str(target/'input.json')],capture_output=True,text=True,check=True)
            return json.loads(proc.stdout)

    def test_2300_queues_current_day_once_and_never_repeats_at_midnight(self):
        r=self.execute(started='2026-10-29 12:00:00',stats=[['2026-10-29 18:00:00','tickets',4]],calls=[
            {'at':'2026-10-29 22:59:59'}, {'at':'2026-10-29 23:00:00'},
            {'at':'2026-10-29 23:00:01'}, {'at':'2026-10-30 00:00:00'},
            {'at':'2026-10-30 22:59:59'}, {'at':'2026-10-30 23:00:00'}])['calls']
        self.assertEqual([x['due'] for x in r],[[],['daily:2026-10-29'],[],[],[],['daily:2026-10-30']])
        self.assertEqual(r[-1]['runs'],2)
        text=r[1]['messages']['daily:2026-10-29']['text']
        self.assertIn('23:00:00 (İstanbul)',text)
        self.assertIn('günün kalan saatleri bu özette yer almaz',text)
        self.assertIn('Servis talepleri: 4',text)

    def test_server_utc_is_not_used_for_the_istanbul_boundary(self):
        r=self.execute(started='2026-10-29 18:00:00+00:00',calls=[
            {'at':'2026-10-29 19:59:59+00:00'}, {'at':'2026-10-29 20:00:00+00:00'}])['calls']
        self.assertEqual(r[0]['due'],[])
        self.assertEqual(r[1]['due'],['daily:2026-10-29'])

    def test_missed_2300_is_caught_up_once_after_midnight(self):
        r=self.execute(started='2026-10-29 12:00:00',calls=[
            {'at':'2026-10-30 00:05:00'}, {'at':'2026-10-30 00:06:00'}],reports=[
            {'kind':'daily','from':'2026-10-29','to':'2026-10-29','at':'2026-10-30 00:05:00'}])
        self.assertEqual(r['calls'][0]['due'],['daily:2026-10-29'])
        self.assertEqual(r['calls'][1]['due'],[])
        self.assertTrue(r['reports'][0]['period_complete'])
        self.assertNotIn('günün kalan saatleri',r['reports'][0]['text'])

    def test_existing_sent_markers_prevent_a_duplicate_after_upgrade(self):
        r=self.execute(started='2026-10-29 10:00:00',cursors={'daily':'2026-10-28'},sent=['daily:2026-10-28'],calls=[
            {'at':'2026-10-29 23:00:00'}])['calls'][0]
        self.assertEqual(r['due'],['daily:2026-10-29'])
        self.assertNotIn('daily:2026-10-28',r['messages'])
        self.assertEqual(r['daily_cursor'],'2026-10-30')

    def test_write_failure_rolls_back_report_ledger_and_cursor_then_retries(self):
        r=self.execute(started='2026-10-29 10:00:00',calls=[
            {'at':'2026-10-29 23:00:00','fail':True}, {'at':'2026-10-29 23:00:02'}])['calls']
        self.assertEqual(r[0]['messages'],[])
        self.assertEqual(r[0]['runs'],0)
        self.assertEqual(r[0]['daily_cursor'],'2026-10-29')
        self.assertEqual(r[1]['due'],['daily:2026-10-29'])

    def test_completed_week_and_month_boundaries_are_preserved(self):
        r=self.execute(started='2026-10-01 00:00:00',cursors={'daily':'2026-11-01','weekly':'2026-10-26','monthly':'2026-10-01'},calls=[
            {'at':'2026-11-01 00:00:00','config':{}},
            {'at':'2026-11-02 00:00:00','config':{}}])['calls']
        self.assertEqual(r[0]['due'],['monthly:2026-10'])
        self.assertEqual(r[1]['due'],['daily:2026-11-01','weekly:2026-10-26'])

    def test_master_switch_does_not_consume_reports_when_disabled(self):
        r=self.execute(started='2026-10-29 10:00:00',calls=[
            {'at':'2026-10-29 23:00:00','config':{'daily_report':False}},
            {'at':'2026-10-29 23:00:01'}])['calls']
        self.assertEqual(r[0]['due'],[])
        self.assertEqual(r[0]['daily_cursor'],'2026-10-29')
        self.assertEqual(r[1]['due'],['daily:2026-10-29'])


if __name__=='__main__':unittest.main()
