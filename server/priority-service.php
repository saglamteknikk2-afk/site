<?php
declare(strict_types=1);
/** Server-authoritative priority-service quotes. No network or records on quote.
 * The caller owns authentication/CSRF and commits acceptance with the ticket.
 */
final class STPriorityException extends DomainException {
    private $reason;
    public function __construct(string $reason,string $message,int $status=400){parent::__construct($message,$status);$this->reason=$reason;}
    public function reason(): string{return $this->reason;}
}
function st_priority_policy(array $override=[]): array {
    $policy=['enabled'=>true,'timezone'=>'Europe/Istanbul','day_fee_try'=>2500,'night_fee_try'=>4000,'night_start'=>'21:00','night_end'=>'08:00','quote_ttl'=>600,'terms_version'=>'2026-10-25.1'];
    foreach(['enabled','night_end'] as $key)if(array_key_exists($key,$override))$policy[$key]=$override[$key];
    if(!is_bool($policy['enabled']))throw new STPriorityException('policy_invalid','Öncelikli servis ayarı geçersiz.',503);
    if($policy['night_end']!==null&&(!is_string($policy['night_end'])||!preg_match('/^(?:[01][0-9]|20):[0-5][0-9]$/D',$policy['night_end'])))throw new STPriorityException('policy_invalid','Öncelikli servisin gündüz başlangıç saati geçersiz.',503);
    if($policy['enabled']&&$policy['night_end']===null)throw new STPriorityException('policy_pending','Öncelikli servis saatleri henüz netleşmedi. Telefonla uygunluğu görüşebilirsiniz.',503);
    return $policy;
}
function st_priority_require_policy(array $override=[]): array {
    $policy=st_priority_policy($override);
    if(!$policy['enabled'])throw new STPriorityException('priority_unavailable','Öncelikli servis şu anda çevrim içi talebe açık değil. Uygunluğu telefonla görüşebilirsiniz.',503);
    return $policy;
}
function st_priority_details(array $input): array {
    $out=[];
    foreach(['name'=>[2,80],'phone'=>[10,25],'district'=>[2,120],'device'=>[2,40],'issue'=>[5,2000]] as $key=>$range){
        $value=$input[$key]??null;
        if(!is_string($value)||preg_match('//u',$value)!==1)throw new STPriorityException('invalid_contact','İletişim ve cihaz bilgilerinizi kontrol edin.');
        $value=trim($value);$length=preg_match_all('/./us',$value,$unused);if($length!==false)$length+=preg_match_all('/[\x{10000}-\x{10ffff}]/u',$value);
        if($length<$range[0]||$length>$range[1]||preg_match('/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/',$value))throw new STPriorityException('invalid_contact','İletişim ve cihaz bilgilerinizi kontrol edin.');
        $out[$key]=$value;
    }
    if(!preg_match('/^[+0-9 ()-]+$/D',$out['phone'])||strlen(preg_replace('/\D/','',$out['phone']))<10||strlen(preg_replace('/\D/','',$out['phone']))>15)throw new STPriorityException('invalid_contact','Telefon numarasını kontrol edin.');
    if(!in_array($out['device'],['Kombi','Klima','Petek'],true))throw new STPriorityException('invalid_contact','Cihaz türünü kontrol edin.');
    if(($input['service_level']??'')!=='priority')throw new STPriorityException('invalid_service_level','Öncelikli servis seçimini kontrol edin.');
    if(!empty($input['website']))throw new STPriorityException('invalid_contact','Başvuru doğrulanamadı.');
    return $out;
}
function st_priority_context_hash(array $input,string $secret): string {
    return hash_hmac('sha256',json_encode(st_priority_details($input),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR),$secret);
}
function st_priority_clock(int $now,array $policy): array {
    $tz=new DateTimeZone('Europe/Istanbul');$local=(new DateTimeImmutable('@'.$now))->setTimezone($tz);
    $minutes=(int)$local->format('H')*60+(int)$local->format('i');
    [$hour,$minute]=array_map('intval',explode(':',$policy['night_end']));$end=$hour*60+$minute;
    $night=$minutes>=1260||($end>0&&$minutes<$end);
    $boundaries=[];
    foreach(['21:00',$policy['night_end']] as $time){$next=new DateTimeImmutable($local->format('Y-m-d').' '.$time.':00',$tz);if($next->getTimestamp()<=$now)$next=$next->modify('+1 day');$boundaries[]=$next->getTimestamp();}
    return ['fee_try'=>$night?4000:2500,'period'=>$night?'night':'day','next_boundary'=>min($boundaries)];
}
function st_priority_terms(int $fee): string {
    return number_format($fee,0,',','.').' TL öncelikli servis hizmet bedelini ve hizmet koşullarını kabul ediyorum. Öncelik ve varış uygunluğu ekiple görüşülerek kesinleşir. Ek işlem veya parça gerekirse kapsamı ve bedeli ayrıca onayıma sunulur. Bu adım ödeme tahsilatı yapmaz.';
}
function st_priority_encode(array $claims,string $secret): string {
    if(strlen($secret)<32)throw new STPriorityException('signing_unavailable','Talep doğrulaması şu anda kullanılamıyor.',503);
    $body=rtrim(strtr(base64_encode(json_encode($claims,JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR)),'+/','-_'),'=');
    return $body.'.'.hash_hmac('sha256','priority-service-v1.'.$body,$secret);
}
function st_priority_quote(array $input,string $session,string $secret,?int $now=null,array $override=[]): array {
    $policy=st_priority_require_policy($override);$now=$now??time();
    if($session==='')throw new STPriorityException('session_required','Form bağlantısını yenileyin.',403);
    $hash=st_priority_context_hash($input,$secret);$clock=st_priority_clock($now,$policy);
    $claims=['v'=>1,'quote_id'=>bin2hex(random_bytes(16)),'fee_try'=>$clock['fee_try'],'currency'=>'TRY','issued_at'=>$now,'expires_at'=>min($now+$policy['quote_ttl'],$clock['next_boundary']),'terms_version'=>$policy['terms_version'],'session_hash'=>hash_hmac('sha256','session.'.$session,$secret),'contact_hash'=>$hash,'night_end'=>$policy['night_end']];
    return ['ok'=>true,'priority_quote'=>st_priority_encode($claims,$secret),'quote_id'=>$claims['quote_id'],'fee_try'=>$claims['fee_try'],'currency'=>'TRY','fee_label'=>number_format($claims['fee_try'],0,',','.').' TL','timezone'=>'Europe/Istanbul','period'=>$clock['period'],'server_now'=>$now,'issued_at'=>$now,'expires_at'=>$claims['expires_at'],'valid_until'=>(new DateTimeImmutable('@'.$claims['expires_at']))->setTimezone(new DateTimeZone('Europe/Istanbul'))->format('d.m.Y H:i:s'),'terms_version'=>$claims['terms_version'],'terms_text'=>st_priority_terms($claims['fee_try']),'message'=>'Bedeli ve koşulları inceleyin. Talep yalnız son onayınızdan sonra kaydedilir.'];
}
function st_priority_accept(array $input,string $session,string $secret,?int $now=null,array $override=[]): array {
    $policy=st_priority_require_policy($override);$now=$now??time();
    if(($input['priority_accepted']??false)!==true)throw new STPriorityException('consent_required','Öncelikli servis bedelini ve koşullarını onaylayın.');
    $token=$input['priority_quote']??null;
    if(!is_string($token)||strlen($token)>4096||!preg_match('/^([A-Za-z0-9_-]+)\.([a-f0-9]{64})$/D',$token,$parts))throw new STPriorityException('invalid_quote','Hizmet bedelini yeniden görüntüleyip onaylayın.');
    if(strlen($secret)<32||!hash_equals(hash_hmac('sha256','priority-service-v1.'.$parts[1],$secret),$parts[2]))throw new STPriorityException('invalid_quote','Hizmet bedeli doğrulanamadı. Yeniden onay isteyin.');
    $decoded=base64_decode(strtr($parts[1],'-_','+/'),true);$claims=is_string($decoded)?json_decode($decoded,true):null;
    if(!is_array($claims)||($claims['v']??null)!==1||!is_int($claims['issued_at']??null)||!is_int($claims['expires_at']??null)||!is_int($claims['fee_try']??null)||!preg_match('/^[a-f0-9]{32}$/D',(string)($claims['quote_id']??''))||($claims['currency']??'')!=='TRY')throw new STPriorityException('invalid_quote','Hizmet bedeli doğrulanamadı.');
    if($claims['issued_at']>$now+5||$claims['expires_at']<=$now||$claims['expires_at']-$claims['issued_at']>600)throw new STPriorityException('quote_expired','Ücret onayının süresi doldu. Güncel bedeli yeniden görüntüleyip onaylayın.',410);
    if(($claims['terms_version']??'')!==$policy['terms_version']||($claims['night_end']??null)!==$policy['night_end']||($input['priority_terms_version']??null)!==$policy['terms_version'])throw new STPriorityException('quote_expired','Hizmet koşulları güncellendi. Bedeli yeniden görüntüleyip onaylayın.',410);
    if($session===''||!hash_equals(hash_hmac('sha256','session.'.$session,$secret),(string)($claims['session_hash']??'')))throw new STPriorityException('session_mismatch','Bu ücret onayı farklı bir oturuma ait.',403);
    if(!hash_equals(st_priority_context_hash($input,$secret),(string)($claims['contact_hash']??'')))throw new STPriorityException('contact_changed','Bilgileriniz değişti. Bedeli yeniden görüntüleyip onaylayın.',409);
    $clock=st_priority_clock($now,$policy);
    if($claims['fee_try']!==$clock['fee_try'])throw new STPriorityException('quote_expired','Saat tarifesi değişti. Güncel bedeli yeniden görüntüleyip onaylayın.',410);
    if(array_key_exists('priority_fee_try',$input)&&$input['priority_fee_try']!==$claims['fee_try'])throw new STPriorityException('invalid_fee','İstemciden gönderilen ücret kabul edilmedi.');
    return ['quote_id'=>$claims['quote_id'],'fee_try'=>$claims['fee_try'],'currency'=>'TRY','terms_version'=>$claims['terms_version'],'terms_text'=>st_priority_terms($claims['fee_try']),'quote_issued_at'=>$claims['issued_at'],'quote_expires_at'=>$claims['expires_at'],'accepted_at'=>$now,'timezone'=>'Europe/Istanbul'];
}
function st_priority_schema(PDO $db): void {
    $db->exec('CREATE TABLE IF NOT EXISTS priority_service_acceptances(quote_id TEXT PRIMARY KEY,ticket_id TEXT NOT NULL UNIQUE,fee_try INTEGER NOT NULL,currency TEXT NOT NULL,terms_version TEXT NOT NULL,terms_text TEXT NOT NULL,quote_issued_at INTEGER NOT NULL,quote_expires_at INTEGER NOT NULL,accepted_at INTEGER NOT NULL)');
}
function st_priority_record(PDO $db,array $accepted,string $ticketId): void {
    if(!$db->inTransaction())throw new LogicException('Priority acceptance must share the ticket transaction.');
    if(!preg_match('/^[a-f0-9]{24}$/D',$ticketId))throw new LogicException('Invalid ticket identity.');
    $check=$db->prepare('SELECT ticket_id FROM priority_service_acceptances WHERE quote_id=?');$check->execute([$accepted['quote_id']]);$prior=$check->fetchColumn();
    if($prior!==false)throw new STPriorityException('quote_already_used','Bu ücret onayı için talep zaten kaydedildi. Yeniden kayıt açmadan durumunu kontrol edin.',409);
    $db->prepare('INSERT INTO priority_service_acceptances(quote_id,ticket_id,fee_try,currency,terms_version,terms_text,quote_issued_at,quote_expires_at,accepted_at) VALUES(?,?,?,?,?,?,?,?,?)')->execute([$accepted['quote_id'],$ticketId,$accepted['fee_try'],$accepted['currency'],$accepted['terms_version'],$accepted['terms_text'],$accepted['quote_issued_at'],$accepted['quote_expires_at'],$accepted['accepted_at']]);
}
