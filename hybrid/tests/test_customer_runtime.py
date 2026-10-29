"""Real local PHP webhook -> SQLite -> customer HTTP feed, with stub transport.

Only the transport function in an isolated temporary copy is substituted. The
application dispatcher, authorization, event transactions and feed stay real.
"""
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from source import load_source


class CustomerRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.php = os.environ.get('PHP_BINARY') or shutil.which('php')
        if not cls.php and Path('/workspace/work/qa/php82-cli').exists(): cls.php='/workspace/work/qa/php82-cli'
        if not cls.php: raise unittest.SkipTest('PHP CLI unavailable')
        cls.tmp=tempfile.TemporaryDirectory();cls.folder=Path(cls.tmp.name)
        cls.web=cls.folder/'public';cls.web.mkdir();cls.private=cls.folder/'private';cls.private.mkdir()
        files,_=load_source(ROOT.parent)
        for name,data in files.items():
            if name.endswith('.php') and '/' not in name:(cls.web/name).write_bytes(data)
        for name in ['api.php','customer-updates.php','service-operations.php','telegram-service.php','analytics.php']:
            (cls.web/name).write_bytes((ROOT/'runtime'/name).read_bytes())
        source=(cls.web/'api.php').read_text()
        start=source.index('function st_telegram(string ');end=source.index('function st_backfill_receipts(',start)
        stub=r'''function st_telegram(string $method,array $payload,int $timeoutMs=8000): array {
            $file=getenv('ST_TEST_TRANSPORT_FILE');
            file_put_contents($file,json_encode(['method'=>$method,'payload'=>$payload],JSON_UNESCAPED_UNICODE)."\n",FILE_APPEND|LOCK_EX);
            if($method==='getMe')return ['ok'=>true,'result'=>['username'=>'LocalTestBot']];
            if($method==='getWebhookInfo')return ['ok'=>true,'result'=>['url'=>'https://local.invalid/api.php?action=webhook']];
            if($method==='answerCallbackQuery'||$method==='setWebhook')return ['ok'=>true,'result'=>true];
            if($method==='editMessageReplyMarkup')return ['ok'=>true,'result'=>['message_id'=>$payload['message_id'],'chat'=>['id'=>$payload['chat_id']]]];
            $counter=__DIR__.'/message-counter.txt';$number=is_file($counter)?(int)file_get_contents($counter):100;
            file_put_contents($counter,(string)($number+1));return ['ok'=>true,'result'=>['message_id'=>$number+1]];
        }
        '''
        (cls.web/'api.php').write_text(source[:start]+stub+source[end:])
        cls.secret='local_webhook_'+('x'*40)
        cfg='\n'.join(['SITE_URL=https://local.invalid','TELEGRAM_BOT_TOKEN='+str(987654321)+':'+('t'*36),
                       'TELEGRAM_CHAT_ID=-1001234567890','TELEGRAM_ADMIN_IDS=111,222',
                       'TELEGRAM_WEBHOOK_SECRET='+cls.secret,'DAILY_REPORT=0','VISIT_NOTIFICATIONS=0','IP_LOCATION_LOOKUP=0'])+'\n'
        (cls.private/'site_apileri,.txt').write_text(cfg)
        cls.env=dict(os.environ,SAGLAM_PRIVATE_DIR=str(cls.private),ST_TEST_TRANSPORT_FILE=str(cls.folder/'transport.jsonl'))
        seed=r'''<?php define('ST_LIBRARY_MODE',true);require __DIR__.'/api.php';$db=st_db();$out=[];
        foreach(['a','b','c','d','e','f'] as $letter){$id=str_repeat($letter,24);$db->prepare('INSERT INTO tickets(id,name,phone,district,device,issue,created) VALUES(?,?,?,?,?,?,?)')->execute([$id,'Yerel Test','5340000000','Küçükçekmece','Kombi','Test',time()]);st_transaction_begin($db);st_operations_ticket_created($db,$id,['district'=>'Küçükçekmece'],null);$db->commit();$out[$letter]=st_operations_row($db,$id);}
        $db->prepare("UPDATE ticket_operations SET service_level='priority' WHERE ticket_id=?")->execute([str_repeat('d',24)]);
        echo json_encode($out,JSON_UNESCAPED_UNICODE);
        '''
        (cls.web/'seed.php').write_text(seed)
        cls.rows=json.loads(subprocess.check_output([cls.php,str(cls.web/'seed.php')],env=cls.env,text=True))
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        cls.url=f'http://127.0.0.1:{port}/api.php'
        cls.log=(cls.folder/'server.log').open('w')
        cls.server=subprocess.Popen([cls.php,'-S',f'127.0.0.1:{port}','-t',str(cls.web)],env=cls.env,stdout=cls.log,stderr=cls.log)
        for _ in range(60):
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.1):break
            except OSError:time.sleep(.05)
        else:raise RuntimeError('Local PHP server did not start')

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,'server'):cls.server.terminate();cls.server.wait(timeout=5)
        if hasattr(cls,'log'):cls.log.close()
        if hasattr(cls,'tmp'):cls.tmp.cleanup()

    def request(self, update=None, token=None):
        url=self.url+('?action=webhook' if update is not None else '?action=service-status&kod='+token)
        headers={'Accept':'application/json'}
        if update is not None:headers.update({'Content-Type':'application/json','X-Telegram-Bot-Api-Secret-Token':self.secret})
        req=Request(url,data=json.dumps(update).encode() if update is not None else None,headers=headers)
        try:
            with urlopen(req,timeout=10) as response:return response.status,json.loads(response.read()),response.headers
        except HTTPError as error:return error.code,json.loads(error.read()),error.headers

    def callback(self, letter, action, number, actor=111, nonce=None):
        row=self.rows[letter];data=(action+':'+letter*24+':'+(nonce or row['nonce']))
        update={'update_id':number,'callback_query':{'id':'callback_'+str(number),'data':data,'from':{'id':actor},'message':{'message_id':1000+number,'chat':{'id':-1001234567890,'type':'supergroup'}}}}
        return self.request(update),update

    def message(self, text, number, actor=111, reference=None):
        message={'message_id':number,'text':text,'from':{'id':actor},'chat':{'id':-1001234567890,'type':'supergroup'}}
        if reference:message['reply_to_message']={'text':'📌 Seçili servis kaydı\nKayıt: '+reference*24+'\nYanıt yazın.'}
        update={'update_id':number,'message':message};return self.request(update),update

    def feed(self, letter):
        status,data,headers=self.request(token=self.rows[letter]['customer_token'])
        self.assertEqual(status,200,data);self.assertEqual(headers.get('Cache-Control'),'no-store');return data

    def transport(self):
        path=self.folder/'transport.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_10_accept_travel_eta_message_and_replay_reach_actual_customer_api(self):
        (status,result,_),accepted=self.callback('a','t:a',101)
        self.assertEqual(status,200,result);self.assertEqual(result['method'],'answerCallbackQuery')
        self.assertEqual(self.feed('a')['status'],'accepted')
        (status,result,_),_=self.callback('a','t:y',102)
        self.assertEqual(status,200,result);self.assertEqual(self.feed('a')['status'],'en_route')
        self.callback('a','cu:e',103)
        prompts=[r['payload'] for r in self.transport() if r['method']=='sendMessage' and r['payload'].get('reply_markup',{}).get('force_reply')]
        self.assertTrue(prompts);self.assertIn('Kayıt: '+'a'*24,prompts[-1]['text'])
        self.message('35',104,reference='a')
        self.assertEqual(self.feed('a')['eta_minutes'],35)
        self.callback('a','cu:m',105)
        (_,result,_),message=self.message('Trafik nedeniyle yaklaşık on dakika gecikiyorum.',106,reference='a')
        feed=self.feed('a');self.assertIn('yaklaşık on dakika',feed['updates'][-1]['body'])
        count=len(feed['updates']);self.request(message);self.assertEqual(len(self.feed('a')['updates']),count)
        self.request(accepted);self.assertEqual(len(self.feed('a')['updates']),count)

    def test_20_another_explicit_trip_is_not_blocked_by_an_old_open_trip(self):
        self.callback('b','t:a',201);(_,reply,_),_=self.callback('b','t:y',202)
        self.assertIn('Yolda',reply['text']);self.assertEqual(self.feed('b')['status'],'en_route')

    def test_30_invalid_eta_keeps_selected_dialog_for_corrected_reply(self):
        self.callback('c','cu:e',301)
        self.message('yarım saat',302,reference='c')
        self.assertIsNone(self.feed('c')['eta_minutes'])
        self.message('30',303,reference='c');self.assertEqual(self.feed('c')['eta_minutes'],30)

    def test_40_unauthorized_or_stale_buttons_get_feedback_without_mutating_customer(self):
        (_,reply,_),_=self.callback('d','t:a',401,actor=333)
        self.assertIn('yetkiniz yok',reply['text']);self.assertEqual(self.feed('d')['status'],'received')
        (_,reply,_),_=self.callback('d','t:a',402,nonce='0'*16)
        self.assertIn('doğrulanamadı',reply['text']);self.assertEqual(self.feed('d')['status'],'received')
        self.callback('d','t:a',403);self.callback('d','cu:v',404)
        self.assertTrue(any('VIP Servis talebiniz öncelikli' in u['body'] for u in self.feed('d')['updates']))

    def test_50_old_prompt_reply_cannot_be_sent_to_newly_selected_customer(self):
        self.callback('e','cu:m',501);self.callback('f','cu:m',502)
        self.message('Eski seçime yanıt',503,reference='e')
        self.assertEqual(self.feed('e')['updates'],[]);self.assertEqual(self.feed('f')['updates'],[])
        self.message('Doğru servise bilgi',504,reference='f')
        self.assertEqual(self.feed('f')['updates'][-1]['body'],'Doğru servise bilgi')

    def test_60_customer_subscription_delivers_each_pending_notice_once(self):
        update={'update_id':601,'message':{'message_id':601,'text':'/start '+self.rows['a']['customer_token'],'from':{'id':999},'chat':{'id':999,'type':'private'}}}
        self.request(update)
        deliveries=[r for r in self.transport() if r['method']=='sendMessage' and r['payload'].get('chat_id')=='999' and 'Servis bilgilendirmesi' in r['payload'].get('text','')]
        self.assertEqual(len(deliveries),len(self.feed('a')['updates']))
        self.request(update)
        deliveries_after=[r for r in self.transport() if r['method']=='sendMessage' and r['payload'].get('chat_id')=='999' and 'Servis bilgilendirmesi' in r['payload'].get('text','')]
        self.assertEqual(len(deliveries_after),len(deliveries))

    def test_70_legacy_customer_rows_survive_migration_and_active_delivery_lease(self):
        script=r'''<?php
        require __DIR__.'/customer-updates.php';require __DIR__.'/transaction.php';
        function st_config():array{return ['site_url'=>'https://local.invalid'];}
        function st_telegram(string $method,array $payload,int $timeoutMs=8000):array{throw new RuntimeException('A leased update must not invoke transport.');}
        $db=new PDO('sqlite::memory:',null,null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION]);
        $db->exec("CREATE TABLE tickets(id TEXT PRIMARY KEY);CREATE TABLE outbox(id TEXT PRIMARY KEY);
            CREATE TABLE ticket_operations(ticket_id TEXT PRIMARY KEY,status TEXT,service_level TEXT);
            CREATE TABLE ticket_customer_updates(id INTEGER PRIMARY KEY AUTOINCREMENT,ticket_id TEXT,kind TEXT,body TEXT,created INTEGER,telegram_sent INTEGER DEFAULT 0,telegram_attempts INTEGER DEFAULT 0,telegram_due INTEGER DEFAULT 0);
            INSERT INTO tickets(id) VALUES('aaaaaaaaaaaaaaaaaaaaaaaa');
            INSERT INTO ticket_operations(ticket_id,status,service_level) VALUES('aaaaaaaaaaaaaaaaaaaaaaaa','accepted','standard');
            INSERT INTO ticket_customer_updates(ticket_id,kind,body,created) VALUES('aaaaaaaaaaaaaaaaaaaaaaaa','manual','Önceki müşterinin mesajı',123);");
        st_customer_schema($db);$token=$db->query('SELECT customer_token FROM ticket_operations')->fetchColumn();
        st_customer_schema($db);$again=$db->query('SELECT customer_token FROM ticket_operations')->fetchColumn();
        $db->exec("UPDATE ticket_operations SET customer_chat_id='999'");
        $db->exec('UPDATE ticket_customer_updates SET telegram_lease='.(time()+60));
        $delivery=st_customer_deliver($db);
        echo json_encode(['token_stable'=>$token===$again,'token_length'=>strlen($token),'body'=>$db->query('SELECT body FROM ticket_customer_updates')->fetchColumn(),'rows'=>(int)$db->query('SELECT COUNT(*) FROM ticket_customer_updates')->fetchColumn(),'delivery'=>$delivery],JSON_UNESCAPED_UNICODE);
        '''
        (self.web/'migration.php').write_text(script)
        data=json.loads(subprocess.check_output([self.php,str(self.web/'migration.php')],env=self.env,text=True))
        self.assertTrue(data['token_stable']);self.assertEqual(data['token_length'],32)
        self.assertEqual(data['body'],'Önceki müşterinin mesajı');self.assertEqual(data['rows'],1)
        self.assertEqual(data['delivery']['sent'],0);self.assertEqual(data['delivery']['failed'],0)


if __name__=='__main__': unittest.main()
