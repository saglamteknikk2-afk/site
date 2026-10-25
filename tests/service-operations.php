<?php
declare(strict_types=1);
require __DIR__.'/../server/transaction.php';require __DIR__.'/../server/priority-service.php';require __DIR__.'/../server/service-operations.php';
$checks=[];function op_check(bool $ok,string $name):void{global $checks;$checks[]=['name'=>$name,'passed'=>$ok];if(!$ok)throw new RuntimeException($name);}
function op_reject(callable $fn,string $name):void{try{$fn();}catch(DomainException|LogicException $e){op_check(true,$name);return;}op_check(false,$name);}
function st_enqueue(PDO $db,string $id,array $payload):void{$db->prepare('INSERT OR IGNORE INTO outbox(id,payload) VALUES(?,?)')->execute([$id,json_encode($payload,JSON_UNESCAPED_UNICODE)]);}
try{
 $db=new PDO('sqlite::memory:',null,null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC]);$db->exec('PRAGMA foreign_keys=ON;CREATE TABLE tickets(id TEXT PRIMARY KEY,name TEXT,phone TEXT,district TEXT,device TEXT,issue TEXT,created INTEGER);CREATE TABLE outbox(id TEXT PRIMARY KEY,payload TEXT);');st_priority_schema($db);
 op_check(count(st_operations_districts())===25,'Canonical European Istanbul district list contains25 entries');
 op_check(st_operations_district('Küçükçekmece / Atakent')['label']==='Küçükçekmece','District matching retains Turkish letters and neighborhood context');
 op_check(st_operations_district('ISTANBUL BAGCILAR Gunesli')['label']==='Bağcılar','ASCII district spelling matches canonical name');
 op_check(st_operations_district('Avcılar / Esenyurt')['key']==='','Ambiguous multi-district input is not assigned a fabricated district');
 op_check(st_operations_district('Atakent')['key']==='','Neighborhood without district is left for operator clarification');
 st_operations_schema($db);op_check(st_operations_owner_snapshot($db)['active']===0,'Empty schema creates no service request or synthetic queue');
 $details=['name'=>'QA Synthetic','phone'=>'05340000000','district'=>'Bağcılar','device'=>'Kombi','issue'=>'Sentetik arıza öncelikli servis testi','service_level'=>'priority'];st_priority_quote($details,'synthetic-session',str_repeat('a',64));
 op_check((int)$db->query('SELECT count(*) FROM tickets')->fetchColumn()===0&&(int)$db->query('SELECT count(*) FROM ticket_operations')->fetchColumn()===0&&(int)$db->query('SELECT count(*) FROM outbox')->fetchColumn()===0,'Fee quote creates no ticket, operations row or notification');
 $insert=$db->prepare('INSERT INTO tickets VALUES(?,?,?,?,?,?,?)');
 $legacy=str_repeat('e',24);$insert->execute([$legacy,'QA Legacy','05340000000','Avcılar','Kombi','Eski sentetik başvuru',1]);
 $db->prepare('INSERT INTO priority_service_acceptances VALUES(?,?,?,?,?,?,?,?,?)')->execute([str_repeat('e',32),$legacy,2500,'TRY','test','Sentetik koşul',1,600,2]);st_operations_schema($db);
 $row=st_operations_row($db,$legacy);op_check($row['routing_confirmed']===0&&$row['status']==='received','Historical completion state is not invented and legacy request stays outside active routing');
 op_check($row['service_level']==='priority','Migration preserves legacy accepted priority fee metadata');
 op_check(st_operations_owner_snapshot($db)['active']===0,'Historical requests do not inflate the current queue');
 $ids=['first'=>str_repeat('a',24),'second'=>str_repeat('b',24),'avcilar'=>str_repeat('c',24),'priority'=>str_repeat('d',24),'unknown'=>str_repeat('f',24)];$n=0;
 foreach($ids as $key=>$id){$district=$key==='avcilar'?'Avcılar':($key==='unknown'?'Atakent':'Bağcılar / Güneşli');st_transaction_begin($db);$insert->execute([$id,'QA '.$key,'05340000000',$district,'Kombi','Sentetik açık servis başvurusu',500+(++$n>4?1:0)]);$summary=st_operations_ticket_created($db,$id,$details,$key==='priority'?['fee_try'=>2500]:null);$db->commit();}
 op_check(st_operations_owner_snapshot($db)['active']===5,'Queue contains exactly the five actual new requests');
 $summary=st_operations_public_summary($db,$ids['priority']);op_check($summary['ahead']===2&&!$summary['priority_confirmed'],'Unaccepted priority request preserves same-second FIFO behind earlier standard requests');
 op_check(st_operations_public_summary($db,$ids['unknown'])['ahead']===null,'Unresolved district does not show a fake queue position');
 $json=json_encode($summary,JSON_UNESCAPED_UNICODE);op_check(strpos($json,'05340000000')===false&&strpos($json,'QA ')===false&&!isset($summary['ticket_id']),'Customer queue response contains no other customer names, phones or IDs');
 op_check($summary['route_kind']==='district-grouping-not-live-navigation'&&!isset($summary['eta']),'Route is explicitly district grouping without invented travel time');
 op_check($summary['route_districts']===['Bağcılar','Avcılar'],'Only actual known district groups appear in route list');
 op_reject(fn()=>st_operations_ticket_created($db,str_repeat('1',24),$details),'Operations creation requires the ticket transaction');
 $before=(int)$db->query('SELECT count(*) FROM ticket_operations')->fetchColumn();st_transaction_begin($db);op_reject(fn()=>st_operations_ticket_created($db,str_repeat('1',24),$details),'A nonexistent ticket cannot acquire queue metadata');$db->rollBack();op_check($before===(int)$db->query('SELECT count(*) FROM ticket_operations')->fetchColumn(),'Rejected creation leaves operations unchanged');
 $rollback=str_repeat('2',24);st_transaction_begin($db);$insert->execute([$rollback,'QA Rollback','05340000000','Bağcılar','Kombi','Sentetik geri alma',999]);st_operations_ticket_created($db,$rollback,$details);$db->rollBack();op_check(st_operations_row($db,$rollback)===null,'Ticket rollback also rolls back queue insertion');
 $q=st_operations_set_status($db,$ids['priority'],'accepted');op_check($q['changed']&&$q['queue']['ahead']===0&&$q['queue']['priority_confirmed'],'Priority takes effect only after explicit operator acceptance');
 $events=(int)$db->query('SELECT count(*) FROM ticket_operation_events')->fetchColumn();$outbox=(int)$db->query('SELECT count(*) FROM outbox')->fetchColumn();
 $repeat=st_operations_set_status($db,$ids['priority'],'accepted');op_check(!$repeat['changed']&&(int)$db->query('SELECT count(*) FROM ticket_operation_events')->fetchColumn()===$events&&(int)$db->query('SELECT count(*) FROM outbox')->fetchColumn()===$outbox,'Repeated status action does not duplicate event or queued message');
 op_reject(fn()=>st_operations_set_status($db,$ids['second'],'completed'),'Received request cannot skip acceptance and silently become completed');
 op_reject(fn()=>st_operations_set_status($db,$ids['second'],'bogus'),'Unknown status is rejected');
 st_operations_set_status($db,$ids['first'],'accepted');st_operations_set_status($db,$ids['first'],'en_route');op_check(st_operations_public_summary($db,$ids['priority'])['ahead']===1,'A currently en-route job remains ahead of newly accepted priority');
 op_reject(fn()=>st_operations_set_status($db,$ids['priority'],'en_route'),'One technician cannot be en route to two different jobs');
 op_check(st_operations_row($db,$ids['priority'])['status']==='accepted','Rejected second en-route transition rolls back status');
 $keyboard=st_operations_keyboard($db,$ids['priority']);$data=$keyboard['inline_keyboard'][0][0]['callback_data'];op_check(strlen($data)<=64&&str_starts_with($data,'t:y:'),'Operation callback fits Telegram64byte limit and reflects current allowed action');
 $cfg=['telegram_chat_id'=>'-10001','telegram_admin_ids'=>['10001']];$query=['data'=>$data,'from'=>['id'=>10001],'message'=>['chat'=>['id'=>-10001]]];
 op_reject(fn()=>st_operations_callback($db,array_replace_recursive($query,['from'=>['id'=>99999]]),$cfg),'Unauthorized Telegram account cannot operate a ticket');
 op_reject(fn()=>st_operations_callback($db,array_replace_recursive($query,['message'=>['chat'=>['id'=>-99999]]]),$cfg),'Authorized account in a different chat is rejected');
 op_reject(fn()=>st_operations_callback($db,array_replace($query,['data'=>substr($data,0,-16).str_repeat('0',16)]),$cfg),'Forged operation nonce is rejected');
 op_check(st_operations_callback($db,['data'=>'r:a:other'],[])===null,'Review callbacks remain outside operation handler');
 st_operations_set_status($db,$ids['first'],'completed');$operation=st_operations_callback($db,$query,$cfg);op_check($operation['status']==='en_route'&&$operation['changed'],'Authorized Telegram callback really advances the persisted job');
 op_check(st_operations_owner_snapshot($db)['counts']['en_route']===1,'Owner snapshot reflects actual current field status');
 op_check(st_operations_keyboard($db,$ids['first'])['inline_keyboard']===[],'Completed request offers no stale operation controls');
 op_reject(fn()=>st_operations_set_status($db,$ids['first'],'accepted'),'Completed job cannot be revived by an old callback');
 st_operations_set_status($db,$ids['priority'],'completed');st_operations_set_status($db,$ids['second'],'cancelled');op_check(st_operations_public_summary($db,$ids['second'])['ahead']===null,'Cancelled request is removed from active queue');
 $prior=st_operations_owner_snapshot($db)['active'];st_operations_set_status($db,$legacy,'accepted');op_check(st_operations_owner_snapshot($db)['active']===$prior+1,'Historical request enters active routing only when operator accepts');
 $tickets=st_operations_enrich_tickets($db,[['id'=>$legacy]]);op_check($tickets[0]['operation']['fee_try']===2500&&$tickets[0]['operation']['routing_confirmed'],'Owner sees actual accepted fee and active status');
 op_check(!isset($tickets[0]['operation']['nonce']),'Owner ticket projection does not leak operation nonce into browser data');
 op_check((int)$db->query('SELECT count(*) FROM outbox')->fetchColumn()>0,'Status changes create durable local notifications without a provider call');
 $stages=$db->query('SELECT from_status,to_status,operator FROM ticket_operation_events')->fetchAll();op_check(count($stages)>0&&$stages[0]['operator']==='owner','Status history records actual transitions and operator');
 echo json_encode(['passed'=>true,'checks'=>count($checks),'cases'=>$checks,'provider_requests'=>0],JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT)."\n";
}catch(Throwable $error){fwrite(STDERR,json_encode(['passed'=>false,'checks'=>$checks,'error'=>$error->getMessage()],JSON_UNESCAPED_UNICODE)."\n");exit(1);}
