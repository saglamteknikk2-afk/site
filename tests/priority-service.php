<?php
declare(strict_types=1);
/** Pure clock/signature/consent/transaction tests; no real data or providers. */
require dirname(__DIR__).'/server/priority-service.php';
$checks=[];
$assert=static function(bool $ok,string $name)use(&$checks):void{$checks[]=['name'=>$name,'passed'=>$ok];if(!$ok)throw new RuntimeException($name);};
$reject=static function(callable $fn,string $reason,string $name)use($assert):void{try{$fn();}catch(STPriorityException $error){$assert($error->reason()===$reason,$name);return;}throw new RuntimeException($name.' did not reject');};
$stamp=static function(string $clock):int{return (new DateTimeImmutable('2026-10-25 '.$clock,new DateTimeZone('Europe/Istanbul')))->getTimestamp();};
$session='synthetic-session-unique';$secret=str_repeat('unit-test-not-a-real-secret-',3);
$input=['name'=>'Sentetik Test','phone'=>'05340000000','district'=>'Küçükçekmece / Atakent','device'=>'Kombi','issue'=>'Sentetik test, cihaz açılmıyor.','service_level'=>'priority'];
$policy=st_priority_policy();
$assert($policy['enabled']&&$policy['night_start']==='21:00'&&$policy['night_end']==='08:00','Confirmed default policy is 21:00 through 08:00 Istanbul');
foreach(['00:00:00'=>4000,'07:59:59'=>4000,'08:00:00'=>2500,'20:59:59'=>2500,'21:00:00'=>4000,'23:59:59'=>4000] as $time=>$fee){$q=st_priority_quote($input,$session,$secret,$stamp($time));$assert($q['fee_try']===$fee&&$q['timezone']==='Europe/Istanbul','Istanbul boundary '.$time);}
$original=date_default_timezone_get();date_default_timezone_set('Pacific/Honolulu');
try{$assert(st_priority_quote($input,$session,$secret,$stamp('21:00:00'))['fee_try']===4000,'Host timezone cannot change the Istanbul tariff');}finally{date_default_timezone_set($original);}
$reject(static function()use($input,$session,$secret,$stamp){st_priority_quote($input,$session,$secret,$stamp('12:00:00'),['enabled'=>false]);},'priority_unavailable','Disabled policy returns no quote');
$reject(static function()use($input,$session,$secret,$stamp){st_priority_quote($input,$session,$secret,$stamp('12:00:00'),['enabled'=>true,'night_end'=>null]);},'policy_pending','Incomplete policy cannot quote');
foreach(['21:00','24:00','bad',8] as $end)$reject(static function()use($end){st_priority_policy(['night_end'=>$end]);},'policy_invalid','Invalid morning boundary fails closed');
$q=st_priority_quote($input,$session,$secret,$stamp('12:00:00'));
$acceptedInput=$input+['priority_quote'=>$q['priority_quote'],'priority_accepted'=>true,'priority_terms_version'=>$q['terms_version']];
$accepted=st_priority_accept($acceptedInput,$session,$secret,$stamp('12:00:05'));
$assert($accepted['fee_try']===2500&&$accepted['accepted_at']===$stamp('12:00:05')&&$accepted['terms_version']===$q['terms_version'],'Only accepted server quote supplies the saved fee and terms');
$decoded=json_decode(base64_decode(strtr(explode('.',$q['priority_quote'])[0],'-_','+/')),true);
$publicText=json_encode($decoded,JSON_UNESCAPED_UNICODE);
$assert(strpos($publicText,$input['name'])===false&&strpos($publicText,$input['phone'])===false&&strpos($publicText,$input['issue'])===false,'Signed quote contains no raw contact information');
$assert($q['expires_at']===$stamp('12:10:00'),'Normal quotes expire within ten minutes');
$dayBoundary=st_priority_quote($input,$session,$secret,$stamp('20:59:50'));
$assert($dayBoundary['expires_at']===$stamp('21:00:00'),'Day quote expires exactly at the 21:00 tariff boundary');
$reject(static function()use($input,$dayBoundary,$session,$secret,$stamp){st_priority_accept($input+['priority_quote'=>$dayBoundary['priority_quote'],'priority_accepted'=>true,'priority_terms_version'=>$dayBoundary['terms_version']],$session,$secret,$stamp('21:00:00'));},'quote_expired','Old day fee cannot be silently accepted after 21:00');
$nightBoundary=st_priority_quote($input,$session,$secret,$stamp('07:59:50'));
$assert($nightBoundary['expires_at']===$stamp('08:00:00'),'Night quote expires exactly at the 08:00 tariff boundary');
$reject(static function()use($input,$nightBoundary,$session,$secret,$stamp){st_priority_accept($input+['priority_quote'=>$nightBoundary['priority_quote'],'priority_accepted'=>true,'priority_terms_version'=>$nightBoundary['terms_version']],$session,$secret,$stamp('08:00:00'));},'quote_expired','A stale night quote must be renewed at 08:00');
$reject(static function()use($acceptedInput,$session,$secret,$stamp){$a=$acceptedInput;$a['priority_accepted']=false;st_priority_accept($a,$session,$secret,$stamp('12:00:05'));},'consent_required','Fee acceptance is mandatory');
$reject(static function()use($acceptedInput,$session,$secret,$stamp){$a=$acceptedInput;$a['priority_accepted']='true';st_priority_accept($a,$session,$secret,$stamp('12:00:05'));},'consent_required','String consent is not accepted');
$reject(static function()use($acceptedInput,$session,$secret,$stamp){$a=$acceptedInput;$a['priority_terms_version']='old';st_priority_accept($a,$session,$secret,$stamp('12:00:05'));},'quote_expired','Changed terms require a new visible quote');
$reject(static function()use($acceptedInput,$session,$secret,$stamp){$a=$acceptedInput;$a['priority_fee_try']=1;st_priority_accept($a,$session,$secret,$stamp('12:00:05'));},'invalid_fee','Client-supplied lower price is rejected');
$reject(static function()use($acceptedInput,$session,$secret,$stamp){st_priority_accept($acceptedInput,'other-session',$secret,$stamp('12:00:05'));},'session_mismatch','Quote is bound to the requesting session');
foreach(['name','phone','district','device','issue'] as $field){$reject(static function()use($field,$acceptedInput,$session,$secret,$stamp){$a=$acceptedInput;$a[$field]=$field==='phone'?'05341111111':($field==='device'?'Klima':$a[$field].' değişti');st_priority_accept($a,$session,$secret,$stamp('12:00:05'));},'contact_changed','Quote is bound to '.$field);}
$reject(static function()use($acceptedInput,$session,$secret,$stamp){$a=$acceptedInput;$parts=explode('.',$a['priority_quote']);$body=json_decode(base64_decode(strtr($parts[0],'-_','+/')),true);$body['fee_try']=1;$a['priority_quote']=rtrim(strtr(base64_encode(json_encode($body)),'+/','-_'),'=').'.'.$parts[1];st_priority_accept($a,$session,$secret,$stamp('12:00:05'));},'invalid_quote','Tampering with signed amount fails');
$reject(static function()use($acceptedInput,$session,$secret,$stamp){st_priority_accept($acceptedInput,$session,$secret,$stamp('12:10:00'));},'quote_expired','Expired quote cannot record a request');
foreach(['website'=>'spam','service_level'=>'standard','phone'=>'not-a-phone'] as $field=>$value)$reject(static function()use($field,$value,$input,$session,$secret,$stamp){$a=$input;$a[$field]=$value;st_priority_quote($a,$session,$secret,$stamp('12:00:00'));},$field==='service_level'?'invalid_service_level':'invalid_contact','Invalid quote input '.$field);
$db=new PDO('sqlite::memory:');$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);st_priority_schema($db);
$assert((int)$db->query('SELECT count(*) FROM priority_service_acceptances')->fetchColumn()===0,'Quote and validation create no service acceptance record');
try{st_priority_record($db,$accepted,str_repeat('a',24));throw new RuntimeException('Missing transaction accepted');}catch(LogicException $error){$assert(true,'Acceptance must share a real ticket transaction');}
$db->beginTransaction();st_priority_record($db,$accepted,str_repeat('a',24));$db->rollBack();
$assert((int)$db->query('SELECT count(*) FROM priority_service_acceptances')->fetchColumn()===0,'Ticket transaction rollback also removes fee acceptance');
$db->beginTransaction();st_priority_record($db,$accepted,str_repeat('a',24));$db->commit();
$row=$db->query('SELECT * FROM priority_service_acceptances')->fetch(PDO::FETCH_ASSOC);
$assert((int)$row['fee_try']===2500&&$row['terms_text']===st_priority_terms(2500)&&$row['ticket_id']===str_repeat('a',24),'Committed fee/conditions are linked to the exact ticket');
$db->beginTransaction();$reject(static function()use($db,$accepted){st_priority_record($db,$accepted,str_repeat('b',24));},'quote_already_used','Different idempotency key cannot reuse one quote for a second ticket');$db->rollBack();
$assert((int)$db->query('SELECT count(*) FROM priority_service_acceptances')->fetchColumn()===1,'Quote reuse leaves exactly one acceptance');
echo json_encode(['passed'=>true,'checks'=>count($checks),'cases'=>$checks,'provider_requests'=>0,'production_private_read'=>false],JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES)."\n";
