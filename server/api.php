<?php
declare(strict_types=1);
require_once __DIR__ . '/business-config.php';
require_once __DIR__ . '/ai-koruma.php';
require_once __DIR__ . '/fault-catalog.php';
require_once __DIR__ . '/fault-advisories.php';
/* Sağlam Teknik API. PHP 7.2+ ve PHP 8+ tam uyumlu, PDO SQLite ve cURL gerektirir.
 * Veritabanı/anahtarlar varsayılan olarak httpdocs'un dışındaki private klasöründedir. */
date_default_timezone_set('Europe/Istanbul');

if (!function_exists('str_starts_with')) {
    function str_starts_with(string $haystack, string $needle): bool {
        return $needle === '' || strpos($haystack, $needle) === 0;
    }
}
if (!function_exists('str_ends_with')) {
    function str_ends_with(string $haystack, string $needle): bool {
        return $needle === '' || substr($haystack, -strlen($needle)) === $needle;
    }
}
if (!defined('JSON_THROW_ON_ERROR')) {
    define('JSON_THROW_ON_ERROR', 0);
}
if (!defined('JSON_INVALID_UTF8_SUBSTITUTE')) {
    define('JSON_INVALID_UTF8_SUBSTITUTE', 0);
}

require_once __DIR__.'/notification-support.php';

function st_private(): string {
    return st_business_private_directory();
}
function st_with_config_lock(callable $operation) {
    static $locked=false;
    if($locked)return $operation();
    $lock=fopen(st_private().'/config.lock','c');
    if(!$lock)throw new RuntimeException('Ayar kilidi açılamadı.');
    try{
        if(!flock($lock,LOCK_EX))throw new RuntimeException('Ayar kilidi alınamadı.');
        $locked=true;
        return $operation();
    }finally{$locked=false;flock($lock,LOCK_UN);fclose($lock);}
}
function st_config(bool $reload=false): array {
    static $c;
    if($reload)$c=null;
    if ($c !== null) return $c;
    $p = st_private();
    $default_gemini_keys = '';
    $default_webhook_secret = '';
    $defaults = [
        'site_url'=>'https://saglamkombiklima.com.tr',
        'telegram_token'=>'',
        'telegram_chat_id'=>'',
        'telegram_admin_ids'=>[],
        'telegram_webhook_secret'=>$default_webhook_secret,
        'gemini_key'=>$default_gemini_keys,
        'gemini_model'=>'gemini-3-flash-preview',
        'visit_notifications'=>true,
        'daily_report'=>true,
        'telegram_polling'=>false,
        'ip_location_lookup'=>true,
        'trusted_proxy_cidrs'=>[],
        'geoip_csv'=>'',
        'pending_retention_days'=>90,
        'ticket_retention_days'=>365,
        'admin_access_key'=>''
    ];
    $primary=$p.'/site_apileri,.txt';$legacy=$p.'/site_apileri.txt';$example=$p.'/site_apileri,.txt.ornek';
    if(!is_file($primary) && !is_file($legacy) && is_file($example)){
        st_with_config_lock(function()use($p,$primary,$legacy,$example): void {
            if(is_file($primary)||is_file($legacy))return;
            $temporary=tempnam($p,'st-seed-');
            if($temporary!==false){try{$raw=file_get_contents($example);if($raw!==false && strlen($raw)<=65536 && file_put_contents($temporary,$raw,LOCK_EX)!==false){@chmod($temporary,0600);if(!rename($temporary,$primary))throw new RuntimeException('Ayar şablonu kaydedilemedi.');}}finally{if(is_file($temporary))unlink($temporary);}}
        });
    }
    $file=is_file($primary)?$primary:$legacy;
    $custom=[]; $gemini_slots=[];
    if(is_file($file)) {
        if(filesize($file)>65536)throw new RuntimeException('TXT ayar dosyası beklenenden büyük.');
        $fields=['SITE_URL'=>'site_url','TELEGRAM_BOT_TOKEN'=>'telegram_token','TELEGRAM_CHAT_ID'=>'telegram_chat_id','TELEGRAM_ADMIN_IDS'=>'telegram_admin_ids','TELEGRAM_WEBHOOK_SECRET'=>'telegram_webhook_secret','GEMINI_API_KEY'=>'gemini_key','GEMINI_MODEL'=>'gemini_model','DAILY_REPORT'=>'daily_report','VISIT_NOTIFICATIONS'=>'visit_notifications','TELEGRAM_POLLING'=>'telegram_polling','IP_LOCATION_LOOKUP'=>'ip_location_lookup','TRUSTED_PROXY_CIDRS'=>'trusted_proxy_cidrs','GEOIP_CSV'=>'geoip_csv','PENDING_RETENTION_DAYS'=>'pending_retention_days','TICKET_RETENTION_DAYS'=>'ticket_retention_days','ADMIN_ACCESS_KEY'=>'admin_access_key'];
        foreach($fields as $field)$fields[strtoupper($field)]=$field;
        $raw=file_get_contents($file);if($raw===false)throw new RuntimeException('TXT ayar dosyası okunamadı.');
        $raw=preg_replace('/^\xEF\xBB\xBF/','',$raw);
        foreach(preg_split('/\r\n|\n|\r/',$raw) as $line) {
            $line=trim($line);if($line==='' || $line[0]==='#' || $line[0]===';')continue;
            $parts=explode('=',$line,2);$name=strtoupper(trim($parts[0]));
            if(count($parts)===2 && preg_match('/^GEMINI_API_KEY_([1-4])$/D',$name,$match)){
                $key=trim($parts[1]);
                if($key!=='' && !preg_match('/^[A-Za-z0-9._-]{8,256}$/D',$key))throw new RuntimeException('Gemini anahtar yuvasi hatali.');
                $gemini_slots[(int)$match[1]]=$key;
                continue;
            }
            $field=$fields[$name]??null;
            if(count($parts)!==2 || !$field)throw new RuntimeException('TXT ayar dosyasının satır biçimini kontrol edin.');
            $v=trim($parts[1]);if(strlen($v)>=2 && in_array($v[0],['"',"'"],true) && $v[strlen($v)-1]===$v[0])$v=substr($v,1,-1);
            if(preg_match('/[\x00-\x1f]/',$v))throw new RuntimeException('TXT ayar değeri tek satır olmalıdır.');
            if(in_array($field,['visit_notifications','daily_report','telegram_polling','ip_location_lookup'],true)) {
                $word=strtolower($v);$yes=['1','true','yes','evet','acik','açık'];$no=['0','false','no','hayir','hayır','kapali','kapalı',''];
                if(!in_array($word,array_merge($yes,$no),true))throw new RuntimeException('TXT açma/kapama değerleri 1 veya 0 olmalıdır.');
                $custom[$field]=in_array($word,$yes,true);
            } elseif(in_array($field,['telegram_admin_ids','trusted_proxy_cidrs'],true)) {
                $custom[$field]=array_values(array_filter(array_map('trim',explode(',',$v)),function($x){return $x!=='';}));
            } elseif(str_ends_with($field,'_retention_days')) {
                if(!ctype_digit($v) || (int)$v<1 || (int)$v>3650)throw new RuntimeException('TXT saklama süresini kontrol edin.');
                $custom[$field]=(int)$v;
            } else $custom[$field]=$v;
        }
    }
    if($gemini_slots){
        ksort($gemini_slots);
        $keys=array_values(array_unique(array_filter($gemini_slots,static function($v){return $v!=='';})));
        if($keys)$custom['gemini_key']=implode(',',$keys);
    }
    $c = array_merge($defaults,$custom);
    if($c['telegram_token']==='')$c['telegram_token']=$defaults['telegram_token'];
    if($c['telegram_chat_id']==='')$c['telegram_chat_id']=$defaults['telegram_chat_id'];
    if(empty($c['telegram_admin_ids']))$c['telegram_admin_ids']=$defaults['telegram_admin_ids'];
    if($c['gemini_key']==='')$c['gemini_key']=$defaults['gemini_key'];
    if(!preg_match('/^[A-Za-z0-9_-]{32,256}$/D',(string)$c['telegram_webhook_secret']))$c['telegram_webhook_secret']=$default_webhook_secret;
    // IP_LOCATION_LOOKUP secenegini TXT'de ayarlandigi gibi kullan.
    $c['ip_location_lookup']=(bool)$c['ip_location_lookup'];

    if($c['telegram_token']!=='' && !preg_match('/^[0-9]{6,15}:[A-Za-z0-9_-]{25,180}$/D',$c['telegram_token']))throw new RuntimeException('TXT Telegram anahtarı biçimi geçersiz.');
    if($c['telegram_chat_id']!=='' && !preg_match('/^-?[0-9]{1,20}$/D',$c['telegram_chat_id']))throw new RuntimeException('TXT chat ID sayısal olmalıdır.');
    // Yanlis Telegram yonetici ID'si, yorum/servis kaydi/AI isteklerini durdurmasin.
    // Gecersiz kimlige asla onay yetkisi verme; sadece gecerli sayisal ID'leri tut.
    $valid_admin_ids=[];
    foreach($c['telegram_admin_ids'] as $id){
        $id=(string)$id;
        if(preg_match('/^[0-9]{1,20}$/D',$id))$valid_admin_ids[]=$id;
        else @error_log('SaglamTeknik API: TELEGRAM_ADMIN_IDS icinde gecersiz deger atlandi (deger loglanmadi).');
    }
    $c['telegram_admin_ids']=array_values(array_unique($valid_admin_ids));
    if($c['gemini_key']!=='' && (strlen($c['gemini_key'])>1000 || preg_match('/\s/',$c['gemini_key'])))throw new RuntimeException('TXT Gemini anahtarını kontrol edin.');
    if(!preg_match('/^[A-Za-z0-9._-]{1,100}$/D',$c['gemini_model']))throw new RuntimeException('TXT model adını kontrol edin.');
    if(!preg_match('~^https?://[^\s/?#]+$~D',$c['site_url']))throw new RuntimeException('TXT site adresini kontrol edin.');
    return $c;
}
function st_config_save_unlocked(array $c): void {
    $fields=['SITE_URL'=>'site_url','TELEGRAM_BOT_TOKEN'=>'telegram_token','TELEGRAM_CHAT_ID'=>'telegram_chat_id','TELEGRAM_ADMIN_IDS'=>'telegram_admin_ids','TELEGRAM_WEBHOOK_SECRET'=>'telegram_webhook_secret','GEMINI_API_KEY'=>'gemini_key','GEMINI_MODEL'=>'gemini_model','DAILY_REPORT'=>'daily_report','VISIT_NOTIFICATIONS'=>'visit_notifications','TELEGRAM_POLLING'=>'telegram_polling','IP_LOCATION_LOOKUP'=>'ip_location_lookup','TRUSTED_PROXY_CIDRS'=>'trusted_proxy_cidrs','GEOIP_CSV'=>'geoip_csv','PENDING_RETENTION_DAYS'=>'pending_retention_days','TICKET_RETENTION_DAYS'=>'ticket_retention_days','ADMIN_ACCESS_KEY'=>'admin_access_key'];
    if(!preg_match('~^https?://[^\s/?#]+$~D',$c['site_url']))throw new DomainException('Site adresini kontrol edin.');
    if($c['telegram_token'] && !preg_match('/^[0-9]{6,15}:[A-Za-z0-9_-]{25,180}$/D',$c['telegram_token']))throw new DomainException('Telegram bot anahtarı biçimini kontrol edin.');
    if($c['telegram_chat_id'] && !preg_match('/^-?[0-9]{1,20}$/D',$c['telegram_chat_id']))throw new DomainException('Chat ID sayısal olmalıdır.');
    foreach($c['telegram_admin_ids'] as $id)if(!preg_match('/^[0-9]{1,20}$/D',(string)$id))throw new DomainException('Onay kullanıcı ID değerlerini kontrol edin.');
    if(strlen($c['gemini_key'])>1000 || preg_match('/\s/',$c['gemini_key']))throw new DomainException('Gemini anahtarını kontrol edin.');
    if(!preg_match('/^[A-Za-z0-9._-]{1,100}$/D',$c['gemini_model']))throw new DomainException('Gemini model adını kontrol edin.');
    $lines=['# Sağlam Teknik API ayarları. Web kökü dışında tutulur.'];
    foreach($fields as $name=>$field){$value=$c[$field]??'';if(is_array($value))$value=implode(',',$value);elseif(is_bool($value))$value=$value?'1':'0';$value=(string)$value;if(preg_match('/[\x00-\x1f]/',$value))throw new DomainException('Ayar değeri tek satır olmalıdır.');$lines[]=$name.'='.$value;}
    $directory=st_private();$file=is_file($directory.'/site_apileri,.txt')?$directory.'/site_apileri,.txt':(is_file($directory.'/site_apileri.txt')?$directory.'/site_apileri.txt':$directory.'/site_apileri,.txt');
    $temporary=tempnam($directory,'st-config-');if($temporary===false)throw new RuntimeException('Ayar klasörüne yazılamadı.');
    try{if(file_put_contents($temporary,implode("\n",$lines)."\n",LOCK_EX)===false)throw new RuntimeException('Ayarlar kaydedilemedi.');@chmod($temporary,0600);if(!rename($temporary,$file))throw new RuntimeException('TXT dosyası güncellenemedi.');}
    finally{if(is_file($temporary))unlink($temporary);}
}

function st_config_update(callable $mutate): array {
    return st_with_config_lock(function()use($mutate): array {
        $current=st_config(true);$next=$mutate($current);
        if($next!==$current){st_config_save_unlocked($next);return st_config(true);}
        return $current;
    });
}
function st_prepare_webhook_config(bool $required=false): array {
    return st_config_update(function(array $c)use($required): array {
        if(!$c['telegram_token'] || !$c['telegram_chat_id'] || (!$c['telegram_admin_ids']&&!ctype_digit((string)$c['telegram_chat_id']))){
            if($required)throw new DomainException('Bot anahtarı, chat ID ve onay kullanıcı ID bilgilerini tamamlayın.');
            return $c;
        }
        if(!str_starts_with($c['site_url'],'https://'))throw new DomainException('Telegram onayı için site adresi HTTPS olmalıdır.');
        if(!preg_match('/^[A-Za-z0-9_-]{32,256}$/D',$c['telegram_webhook_secret']))$c['telegram_webhook_secret']=bin2hex(random_bytes(32));
        return $c;
    });
}

function st_ensure_webhook(bool $force=false): array {
    try {
        // Generates and securely persists a unique webhook secret outside the web root.
        $cfg = st_prepare_webhook_config();
        if (!$cfg['telegram_token'] || !$cfg['telegram_chat_id'] || !str_starts_with($cfg['site_url'], 'https://')) {
            return ['ok'=>false, 'error'=>'Token, Chat ID veya HTTPS site adresi eksik.'];
        }
        $db = st_db();
        $webhook_url = rtrim($cfg['site_url'], '/') . '/api.php?action=webhook';
        $sig = hash('sha256', $cfg['telegram_token'] . '|' . $webhook_url . '|' . $cfg['telegram_webhook_secret']);
        if (!$force) {
            $q = $db->prepare("SELECT v FROM meta WHERE k='webhook_sig'");
            $q->execute();
            if ($q->fetchColumn() === $sig) return ['ok'=>true, 'cached'=>true];
        }
        st_telegram('setWebhook', [
            'url' => $webhook_url,
            'secret_token' => $cfg['telegram_webhook_secret'],
            'allowed_updates' => ['callback_query']
        ]);
        $db->prepare("INSERT INTO meta(k,v) VALUES('webhook_sig',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v")->execute([$sig]);
        return ['ok'=>true, 'cached'=>false];
    } catch (Throwable $e) {
        return ['ok'=>false, 'error'=>$e->getMessage()];
    }
}

function st_normalize(string $s): string {
    $s=strtr($s,['ç'=>'c','ğ'=>'g','ı'=>'i','ö'=>'o','ş'=>'s','ü'=>'u','Ç'=>'C','Ğ'=>'G','İ'=>'I','Ö'=>'O','Ş'=>'S','Ü'=>'U']);
    $s=trim(preg_replace('/[^a-z0-9]+/',' ',strtolower($s)));
    $replacements=['/\bkucuk\s+cekmece\b/'=>'kucukcekmece','/\bbuyuk\s+cekmece\b/'=>'buyukcekmece',
        '/\bkucukcekm[e]?ce(?:ce)?\b/'=>'kucukcekmece','/\bkucukcekmecece\b/'=>'kucukcekmece',
        '/\be\s+c\s+a\b/'=>'eca','/\bdemir\s+dokum\b/'=>'demirdokum'];
    return preg_replace(array_keys($replacements),array_values($replacements),$s);
}
function st_search(array $a): array {
    $query=st_text($a,'query',3,200);
    // Web paketindeki katalog, ayrı bir arama SQLite dosyası gerektirmez.
    $raw=@file_get_contents(__DIR__.'/assets/servis-katalog.json');
    $catalog=is_string($raw)?json_decode($raw,true):null;
    if(!is_array($catalog)||empty($catalog['devices']))throw new RuntimeException('Servis kataloğu okunamadı.');
    $preferred=$a['device']??'';
    if(!is_string($preferred)||!in_array($preferred,['','kombi','klima'],true))st_fail('Cihaz türünü kontrol edin.');
    return st_resolve_query($query,$preferred,$catalog);
}
function st_contains(string $q,string $term): bool {
    $term=st_normalize($term);return $term!==''&&strpos(' '.$q.' ',' '.$term.' ')!==false;
}
function st_best_match(string $q,array $entries): ?array {
    $best=null;$length=-1;
    foreach($entries as $entry)foreach($entry['terms']??[] as $term){
        $normalized=st_normalize($term);
        if(strlen($normalized)>$length&&st_contains($q,$normalized)){$best=$entry;$length=strlen($normalized);}
    }
    return $best;
}
function st_resolve_query(string $query,string $preferred,array $catalog,?array $legacy=null): array {
    $raw=@file_get_contents(__DIR__.'/assets/organic-catalog.json');
    $organic=is_string($raw)?json_decode($raw,true):[];
    if(!is_array($organic))$organic=[];
    $q=st_normalize($query);$explicit='';
    foreach(['klima','klimasi','klimaci'] as $term)if(st_contains($q,$term))$explicit='klima';
    if(!$explicit)foreach(['kombi','kombisi','kombici','komci'] as $term)if(st_contains($q,$term))$explicit='kombi';
    $brand_entries=[];$matched_devices=[];
    foreach($catalog['devices'] as $kind=>$item){
        $brand_entries[$kind]=[];
        foreach($item['brands'] as $brand)$brand_entries[$kind][]=['name'=>$brand,'terms'=>array_merge([$brand],$catalog['brand_aliases'][$brand]??[])];
        if(st_best_match($q,$brand_entries[$kind]))$matched_devices[]=$kind;
    }
    $inferred=[];
    if(function_exists('st_fault_infer'))foreach($catalog['devices'] as $type=>$item){
        $explicit_brand=st_best_match($q,$brand_entries[$type]);
        $candidate=st_fault_infer($query,$type,$explicit_brand['name']??'');
        if($candidate)$inferred[]=$candidate;
    }
    $unique_inferred=count($inferred)===1?$inferred[0]:null;
    $model_entries=array_values(array_filter($organic['models']??[],function($model)use($q){return st_contains($q,$model['brand']);}));
    $recognized_model=st_best_match($q,$model_entries);
    $kind=$explicit?:($unique_inferred['device']??($recognized_model['device']??''));
    if(!$kind)$kind=count($matched_devices)===1?$matched_devices[0]:(isset($catalog['devices'][$preferred])?$preferred:'kombi');
    $device=$catalog['devices'][$kind];$explicit_brand=st_best_match($q,$brand_entries[$kind]);
    $inferred_model=function_exists('st_fault_infer')?st_fault_infer($query,$kind,$explicit_brand['name']??''):null;
    $brand=$explicit_brand?:($inferred_model?['name'=>$inferred_model['brand']]:null);
    $district_entry=st_best_match($q,array_map(function($d){return ['name'=>$d,'terms'=>[$d]];},$catalog['districts']));
    $locality=st_best_match($q,array_map(function($s){return array_merge($s,['terms'=>[$s['name']]]);},$catalog['localities']));
    $district=$district_entry['name']??($locality['district']??'');$district_hits=[];
    foreach($catalog['districts'] as $d)if(st_contains($q,$d))$district_hits[]=$d;
    $groups=[];
    foreach($catalog['neighborhoods'] as $row){
        $key=st_normalize($row['name']);
        if(st_contains($q,$key))$groups[$key][]=$row;
    }
    uksort($groups,function($a,$b){return strlen($b)<=>strlen($a);});$neighborhood='';$ambiguous=false;
    foreach($groups as $candidates){
        $consistent=array_values(array_filter($candidates,function($r)use($district_hits,$q){
            return in_array($r['district'],$district_hits,true)
                &&((st_normalize($r['name'])!==st_normalize($r['district'])&&st_contains(st_normalize($r['name']),$r['district']))
                    ||st_contains(preg_replace('/\b'.st_normalize($r['district']).'\b/','',$q,1),$r['name']));
        }));
        if(count($consistent)===1){$district=$consistent[0]['district'];$neighborhood=$consistent[0]['name'];break;}
    }
    $geography=$district?preg_replace('/\b'.st_normalize($district).'\b/','',$q,1):$q;
    if(!$neighborhood)foreach($groups as $candidates){
        $narrowed=array_values(array_filter($candidates,function($r)use($district,$geography){return(!$district||$r['district']===$district)&&st_contains($geography,$r['name']);}));
        if(count($narrowed)===1){$neighborhood=$narrowed[0]['name'];$district=$narrowed[0]['district'];break;}
        if(count($narrowed)>1)$ambiguous=true;
    }
    if(($locality['name']??'')==='500 Evler'&&!$district_entry){$district='';$neighborhood='';$ambiguous=true;}
    $code_context=(bool)($explicit||$brand||$inferred_model);
    foreach(['hata','hatasi','hata kodu','ariza','arizasi','ariza kodu'] as $term)if(st_contains($q,$term))$code_context=true;
    preg_match_all('/\b[a-z]{1,2}\s*\d{1,3}\b/',$q,$code_matches);
    $fallback_code='';
    foreach($code_matches[0] as $value){
        $candidate=strtoupper(preg_replace('/\s+/','',$value));
        if(preg_match('/^(?:E|F|A|C|CH|H|J|L|P|U|EA|EC)\d{1,3}$/D',$candidate)){$fallback_code=$candidate;break;}
    }
    if(!$fallback_code&&preg_match('/\b(?:ea|ec)\b/',$q,$standalone))$fallback_code=strtoupper($standalone[0]);
    if(!$fallback_code&&preg_match('/\b(?:hata|ariza|kod|kodu)\s+(\d{2,4})\b/',$q,$numeric))$fallback_code=$numeric[1];
    $fault=function_exists('st_fault_lookup')?st_fault_lookup(['device'=>$kind,'brand'=>$brand['name']??'',
        'model_id'=>$inferred_model['id']??'','query'=>$query]):null;
    $error_code=$code_context?(!empty($fault['code'])?$fault['code']:$fallback_code):'';
    $model=$fault['model']['label']??'';
    if($model===''&&($recognized_model['device']??'')===$kind&&($recognized_model['brand']??'')===($brand['name']??''))$model=$recognized_model['name']??'';
    $matched_guide=null;
    foreach($organic['guides']??[] as $guide){
        if(($guide['status']??'')==='published'&&empty($guide['model_id'])&&$guide['device']===$kind&&$guide['brand']===($brand['name']??'')&&$guide['error_code']===$error_code
            &&(empty($guide['model'])||st_normalize($guide['model'])===st_normalize($model))){$matched_guide=$guide;break;}
    }
    $error_intent=$error_code!=='';
    foreach(['hata kodu','ariza kodu','hata kod','ariza kod'] as $term)if(st_contains($q,$term))$error_intent=true;
    $verified=!empty($fault['verified']);$definition=$verified?($fault['definition']??null):null;
    $fault_model_path=$fault['model']['path']??'';
    if(!preg_match('~^/[a-z0-9-]+\.html$~D',$fault_model_path))$fault_model_path='';
    $fault_anchor=!empty($definition['anchor'])?$definition['anchor']:($definition&&function_exists('st_fault_key')?'kod-'.strtolower(st_fault_key($definition['code'])):'');
    $verified_path=$verified&&$fault_model_path!==''?$fault_model_path.'#'.$fault_anchor:'';
    $symptom=st_best_match($q,$device['symptoms']);$service=st_best_match($q,array_slice($device['services'],1));
    $allowed=array_fill_keys($organic['published_routes']??[],true);
    $slug=function($value){return str_replace(' ','-',st_normalize($value));};
    $district_candidate=$district?'/'.$slug($district).'-'.$kind.'-servisi.html':'';
    $district_path=isset($allowed[$district_candidate])?$district_candidate:'';
    $locality_candidate=$locality?'/'.$slug($locality['name']).'-servisi.html':'';
    $locality_path=isset($allowed[$locality_candidate])?$locality_candidate:'';
    $brand_candidate=$brand?'/'.$slug($brand['name']).'-'.$kind.'-servisi.html':'';
    $brand_path=isset($allowed[$brand_candidate])?$brand_candidate:'';
    $error_path=$error_intent?($verified_path?:($fault_model_path?:($matched_guide['path']??($organic['general_error_paths'][$kind]??($kind==='klima'?'/klima-hata-kodu.html':'/kombi-calismiyor.html'))))):'';
    $found=(bool)($explicit||$brand||$district||$neighborhood||$locality||$symptom||$service||$error_intent);
    $path=$error_path?:($symptom['path']??($service['path']??($locality_path?:($district_path?:($brand_path?:$device['services'][0]['path'])))));
    $scope=false;foreach(['yetkili','ozel','satis','ikinci el','bayilik','temsilcilik'] as $term)if(st_contains($q,$term))$scope=true;
    return ['ok'=>true,'found'=>$found,'query'=>$query,'device'=>$kind,'device_label'=>$device['label'],
        'brand'=>$brand['name']??'','district'=>$district,'neighborhood'=>$neighborhood,'locality'=>$locality['name']??'',
        'path'=>$found?$path:'','symptom'=>$symptom['name']??'','service_path'=>$service['path']??$device['services'][0]['path'],
        'scope_check'=>$scope,'ambiguous_neighborhood'=>$ambiguous&&!$neighborhood,'model'=>$model,'error_code'=>$error_code,
        'error_guide_path'=>$error_path,'content_status'=>$verified?'verified-model-guide':($error_intent&&$fault_model_path!==''?'model-guide':($matched_guide?'published-guide':($error_intent?'general-guide':'published'))),
        'model_id'=>$fault['model']['id']??'','fault_status'=>$fault['status']??($error_intent?'needs-model':'not-requested'),
        'model_required'=>$error_intent&&!$verified,'needs_model'=>$error_intent&&!$verified,'code_definition_verified'=>$verified,
        'fault_meaning'=>$definition['meaning']??'','source_url'=>$verified?($definition['source_url']??($fault['model']['manual']['url']??'')):'',
        'source_locator'=>$verified?($definition['source_locator']??($fault['model']['manual']['locator']??'')):''];
}
function st_db(): PDO {
    static $db;
    if ($db) return $db;
    $db = new PDO('sqlite:'.st_private().'/site.sqlite', null, null, [PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC]);
    $db->exec('PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000; PRAGMA foreign_keys=ON;');
    $db->exec("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,author TEXT NOT NULL,district TEXT NOT NULL,service TEXT NOT NULL,cat TEXT NOT NULL,rating INTEGER NOT NULL,comment TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',nonce TEXT NOT NULL,created INTEGER NOT NULL,decided INTEGER,consent INTEGER NOT NULL,notification_sent INTEGER NOT NULL DEFAULT 0,telegram_message_id INTEGER);
        CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY,name TEXT NOT NULL,phone TEXT NOT NULL,district TEXT NOT NULL,device TEXT NOT NULL,issue TEXT NOT NULL,created INTEGER NOT NULL,notification_sent INTEGER NOT NULL DEFAULT 0,telegram_message_id INTEGER);
        CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY,payload TEXT NOT NULL,created INTEGER NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,due INTEGER NOT NULL,lease INTEGER NOT NULL DEFAULT 0,sent INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS idempotency(k TEXT PRIMARY KEY,hash TEXT NOT NULL,response TEXT NOT NULL,created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS rate(k TEXT NOT NULL,action TEXT NOT NULL,window INTEGER NOT NULL,n INTEGER NOT NULL,PRIMARY KEY(k,action,window));
        CREATE TABLE IF NOT EXISTS daily_stats(day TEXT NOT NULL,metric TEXT NOT NULL,val INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(day,metric));
        CREATE TABLE IF NOT EXISTS session_state(sid TEXT PRIMARY KEY,searched INTEGER NOT NULL DEFAULT 0,last_query TEXT NOT NULL DEFAULT '',ticket_sent INTEGER NOT NULL DEFAULT 0,updated INTEGER NOT NULL DEFAULT 0);");
    $db->exec('BEGIN IMMEDIATE');
    try{
        $columns=array_column($db->query('PRAGMA table_info(outbox)')->fetchAll(),'name');
        foreach(['last_error'=>"TEXT NOT NULL DEFAULT ''",'telegram_message_id'=>'INTEGER','delivered'=>'INTEGER'] as $name=>$declaration)if(!in_array($name,$columns,true))$db->exec('ALTER TABLE outbox ADD COLUMN '.$name.' '.$declaration);
        foreach(['reviews','tickets'] as $table){
            $columns=array_column($db->query('PRAGMA table_info('.$table.')')->fetchAll(),'name');
            foreach(['notification_sent'=>'INTEGER NOT NULL DEFAULT 0','telegram_message_id'=>'INTEGER'] as $name=>$declaration)if(!in_array($name,$columns,true))$db->exec('ALTER TABLE '.$table.' ADD COLUMN '.$name.' '.$declaration);
        }
        st_backfill_receipts($db);$db->exec('COMMIT');
    }catch(Throwable $e){$db->exec('ROLLBACK');throw $e;}
    $q=$db->prepare('INSERT OR IGNORE INTO meta(k,v) VALUES(?,?)'); $q->execute(['secret',bin2hex(random_bytes(32))]);
    $q->execute(['last_daily_report', date('Y-m-d')]);
    return $db;
}
function st_stat_inc(string $metric, int $amount=1): void {
    try {
        $db = st_db();
        $day = date('Y-m-d');
        $q = $db->prepare('INSERT INTO daily_stats(day,metric,val) VALUES(?,?,?) ON CONFLICT(day,metric) DO UPDATE SET val=val+excluded.val');
        $q->execute([$day, $metric, $amount]);
    } catch (Throwable $e) {}
}
function st_session_track(string $session, string $type, string $query=''): void {
    try {
        $db = st_db();
        $sid = hash_hmac('sha256', $session, st_secret());
        if ($type === 'search') {
            $q = $db->prepare("INSERT INTO session_state(sid,searched,last_query,updated) VALUES(?,1,?,?) ON CONFLICT(sid) DO UPDATE SET searched=1,last_query=excluded.last_query,updated=excluded.updated");
            $q->execute([$sid, $query, time()]);
        } elseif ($type === 'ticket') {
            $q = $db->prepare("INSERT INTO session_state(sid,ticket_sent,updated) VALUES(?,1,?) ON CONFLICT(sid) DO UPDATE SET ticket_sent=1,updated=excluded.updated");
            $q->execute([$sid, time()]);
        }
    } catch (Throwable $e) {}
}
function st_session_info(string $session): array {
    try {
        $db = st_db();
        $sid = hash_hmac('sha256', $session, st_secret());
        $q = $db->prepare("SELECT searched,last_query,ticket_sent FROM session_state WHERE sid=?");
        $q->execute([$sid]);
        $r = $q->fetch();
        if ($r) return ['searched'=>(int)$r['searched']>0, 'last_query'=>(string)$r['last_query'], 'ticket_sent'=>(int)$r['ticket_sent']>0];
    } catch (Throwable $e) {}
    return ['searched'=>false, 'last_query'=>'', 'ticket_sent'=>false];
}
function st_build_daily_report(string $day): string {
    $db = st_db();
    $q = $db->prepare('SELECT metric,val FROM daily_stats WHERE day=?');
    $q->execute([$day]);
    $stats = [];
    foreach ($q->fetchAll() as $row) {
        $stats[$row['metric']] = (int)$row['val'];
    }
    $visits = $stats['visits'] ?? 0;
    $s_found = $stats['search_found'] ?? 0;
    $s_not_found = $stats['search_not_found'] ?? 0;
    $s_total = $s_found + $s_not_found;
    $ai_count = $stats['ai_questions'] ?? 0;
    $tickets = $stats['tickets'] ?? 0;
    $reviews = $stats['reviews'] ?? 0;

    $formatted_date = date('d.m.Y', strtotime($day));
    $search_status = $s_total > 0
        ? "✅ Yapıldı (" . $s_total . " arama | 🎯 " . $s_found . " bulundu, ⚠️ " . $s_not_found . " bulunamadı)"
        : "❌ Siteden arama yapılmadı (0)";
    $ai_status = $ai_count > 0 ? "✅ " . $ai_count . " soru yanıtlandı" : "➖ Soru sorulmadı (0)";
    $ticket_status = $tickets > 0 ? "✅ " . $tickets . " servis talebi alındı" : "❌ Servis talebi oluşturulmadı (0)";
    $review_status = $reviews > 0 ? "✅ " . $reviews . " yeni yorum geldi" : "➖ Yeni yorum gelmedi (0)";

    return "📊 GÜNLÜK GENEL SİTE RAPORU (00:00)\n"
        . "📅 Rapor Tarihi: " . $formatted_date . "\n"
        . "🕒 Rapor Saati: " . date('H:i') . " (İstanbul)\n\n"
        . "👥 Toplam Site Ziyareti: " . $visits . "\n"
        . "🔍 Siteden Arama: " . $search_status . "\n"
        . "🤖 AI Usta Kullanımı: " . $ai_status . "\n"
        . "🛠 Servis Talepleri: " . $ticket_status . "\n"
        . "⭐ Müşteri Yorumları: " . $review_status;
}
function st_check_daily_report(bool $force_today=false): bool {
    try {
        if(!$force_today && !st_config()['daily_report'])return false;
        $db = st_db();
        $today = date('Y-m-d');
        if ($force_today) {
            $text = st_build_daily_report($today);
            $id = 'daily-test:' . $today . ':' . bin2hex(random_bytes(4));
            st_enqueue($db, $id, ['text' => $text]);
            return true;
        }
        $q = $db->prepare("SELECT v FROM meta WHERE k='last_daily_report'");
        $q->execute();
        $last = (string)$q->fetchColumn();
        if ($last === '') {
            $db->prepare("INSERT OR IGNORE INTO meta(k,v) VALUES('last_daily_report',?)")->execute([$today]);
            return false;
        }
        if ($last < $today) {
            $report_day = date('Y-m-d', strtotime('-1 day'));
            $db->prepare("UPDATE meta SET v=? WHERE k='last_daily_report'")->execute([$today]);
            $text = st_build_daily_report($report_day);
            $id = 'daily:' . $report_day;
            st_enqueue($db, $id, ['text' => $text]);
            return true;
        }
    } catch (Throwable $e) {}
    return false;
}

function st_secret(): string { return (string) st_db()->query("SELECT v FROM meta WHERE k='secret'")->fetchColumn(); }
function st_json(array $data, int $code=200): void {
    http_response_code($code); header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store'); header('X-Content-Type-Options: nosniff'); header('X-Robots-Tag: noindex, nofollow');
    echo json_encode($data, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_INVALID_UTF8_SUBSTITUTE); exit;
}
function st_fail(string $message,int $code=400): void { st_json(['ok'=>false,'error'=>$message],$code); }
function st_session(): string {
    $s = $_COOKIE['st_session'] ?? '';
    if (!preg_match('/^[a-f0-9]{48}$/D',$s)) {
        $s=bin2hex(random_bytes(24));
        $secure=parse_url(st_config()['site_url'],PHP_URL_SCHEME)==='https';
        if (PHP_VERSION_ID >= 70300) {
            setcookie('st_session',$s,['expires'=>time()+7200,'path'=>'/','secure'=>$secure,'httponly'=>true,'samesite'=>'Strict']);
        } else {
            setcookie('st_session',$s,time()+7200,'/; SameSite=Strict','',$secure,true);
        }
    }
    return $s;
}
function st_csrf(string $session,?int $stamp=null): string {
    $stamp=$stamp??time(); return $stamp.'.'.hash_hmac('sha256',$session.'.'.$stamp,st_secret());
}
function st_require_csrf(): string {
    $s=$_COOKIE['st_session']??''; $token=$_SERVER['HTTP_X_CSRF_TOKEN']??''; $bits=explode('.',$token);
    if (!preg_match('/^[a-f0-9]{48}$/D',$s) || count($bits)!==2 || !ctype_digit($bits[0]) || (int)$bits[0]>time()+60 || (int)$bits[0]<time()-7200 || !hash_equals(st_csrf($s,(int)$bits[0]),$token)) st_fail('Sayfayı yenileyip tekrar deneyin.',403);
    $origin=$_SERVER['HTTP_ORIGIN']??''; $expected=rtrim(st_config()['site_url'],'/');
    if ($origin!=='' && rtrim($origin,'/')!==$expected) st_fail('Başvuru kaynağı kabul edilmedi.',403);
    if (($_SERVER['HTTP_SEC_FETCH_SITE']??'')==='cross-site') st_fail('Başvuru kaynağı kabul edilmedi.',403);
    return $s;
}
function st_in_cidr(string $ip,string $cidr): bool {
    $parts=explode('/',$cidr); $a=@inet_pton($ip);$b=@inet_pton($parts[0]);
    if (!$a || !$b || strlen($a)!==strlen($b)) return false;
    $bits=isset($parts[1])?(int)$parts[1]:strlen($a)*8;
    if ($bits<0 || $bits>strlen($a)*8) return false;
    $full=intdiv($bits,8);$rem=$bits%8;
    if (substr($a,0,$full)!==substr($b,0,$full)) return false;
    return !$rem || ((ord($a[$full]) & (255<<(8-$rem)))===(ord($b[$full]) & (255<<(8-$rem))));
}
function st_ip(): string {
    $ip=$_SERVER['REMOTE_ADDR']??'unknown'; $trusted=false;
    $ranges=st_config()['trusted_proxy_cidrs'];
    if(!$ranges && is_file(__DIR__.'/assets/trusted-proxies.json')){$data=json_decode(file_get_contents(__DIR__.'/assets/trusted-proxies.json'),true);$ranges=is_array($data['ranges']??null)?$data['ranges']:[];}
    foreach($ranges as $cidr) if(st_in_cidr($ip,(string)$cidr)) {$trusted=true;break;}
    if($trusted && filter_var($_SERVER['HTTP_CF_CONNECTING_IP']??'',FILTER_VALIDATE_IP)) $ip=$_SERVER['HTTP_CF_CONNECTING_IP'];
    return $ip;
}
function st_location(): string {
    $path=st_config()['geoip_csv'];$ip=st_ip();
    if ($path && is_file($path) && ($f=fopen($path,'r'))) {
        while(($row=fgetcsv($f))!==false) if(count($row)>=4 && st_in_cidr($ip,$row[0])) {
            fclose($f);$parts=array_filter([trim($row[3]),trim($row[2]),trim($row[1])]);
            return implode(' / ',$parts).' (IP tahmini; ilçe/mahalle doğrulanmadı)';
        }
        fclose($f);
    }
    return st_config()['ip_location_lookup']?st_ip_lookup($ip):'Belirlenemedi (ilçe/mahalle alınmadı)';
}
function st_rate(string $action,int $limit,int $seconds=3600): void {
    $db=st_db();$k=hash_hmac('sha256',st_ip().'.'.date('Y-m-d'),st_secret());$window=intdiv(time(),$seconds);
    $q=$db->prepare('INSERT INTO rate(k,action,window,n) VALUES(?,?,?,1) ON CONFLICT(k,action,window) DO UPDATE SET n=n+1');$q->execute([$k,$action,$window]);
    $q=$db->prepare('SELECT n FROM rate WHERE k=? AND action=? AND window=?');$q->execute([$k,$action,$window]);
    if((int)$q->fetchColumn()>$limit) st_fail('Çok sık başvuru alındı. Biraz sonra tekrar deneyin veya telefonla ulaşın.',429);
}
function st_body(): array {
    if((int)($_SERVER['CONTENT_LENGTH']??0)>16384) st_fail('Başvuru çok uzun.',413);
    if(stripos($_SERVER['CONTENT_TYPE']??'','application/json')!==0) st_fail('JSON başvurusu gerekli.',415);
    $raw=file_get_contents('php://input',false,null,0,16385);
    if(strlen($raw)>16384) st_fail('Başvuru çok uzun.',413);
    $a=json_decode($raw,true);if(!is_array($a)) st_fail('Başvuru okunamadı.');return $a;
}
function st_text(array $a,string $key,int $min,int $max): string {
    $v=$a[$key]??null;if(!is_string($v)) st_fail('Lütfen tüm gerekli alanları doldurun.');
    $v=trim($v);$n=preg_match_all('/./us',$v,$m);
    if($n!==false)$n+=preg_match_all('/[\x{10000}-\x{10ffff}]/u',$v);
    if($n===false || $n<$min || $n>$max || preg_match('/[\x00-\x08\x0b\x0c\x0e-\x1f]/',$v)) st_fail('Alan uzunluklarını kontrol edin.');return $v;
}
function st_enqueue(PDO $db,string $id,array $payload): void {
    $q=$db->prepare('INSERT OR IGNORE INTO outbox(id,payload,created,due) VALUES(?,?,?,?)');
    foreach(st_notification_rows($id,$payload) as [$key,$message])$q->execute([$key,json_encode($message,JSON_UNESCAPED_UNICODE|JSON_INVALID_UTF8_SUBSTITUTE),time(),time()]);
}
class STTelegramError extends RuntimeException {
    public $retry_after;
    public function __construct(string $message,int $retry_after=0){parent::__construct($message);$this->retry_after=$retry_after;}
}
function st_telegram_error(int $code,string $description='',array $parameters=[]): STTelegramError {
    $message='Telegram’a ulaşılamadı; bildirim kuyrukta tutuluyor.';$d=strtolower($description);
    if($code===401)$message='Telegram bot anahtarı kabul edilmedi. TXT dosyasındaki anahtarı kontrol edin.';
    elseif($code===403)$message='Bot bu sohbete mesaj gönderemiyor. Botu başlatın, engeli kaldırın veya grup iznini kontrol edin.';
    elseif($code===400 && strpos($d,'chat not found')!==false)$message='Telegram chat ID bulunamadı. Botu başlatıp doğru sohbet ID bilgisini kaydedin.';
    elseif($code===409)$message='Telegram onay alıcısı çakışıyor; webhook veya başka bir getUpdates alıcısı bulunuyor.';
    elseif($code===429)$message='Telegram gönderim sınırına ulaşıldı; belirtilen sürenin sonunda yeniden denenecek.';
    return new STTelegramError($message,min(86400,max(0,(int)($parameters['retry_after']??0))));
}
function st_telegram(string $method,array $payload): array {
    $token=st_config()['telegram_token']; if(!$token)throw new STTelegramError('Telegram bot anahtarı ayarlanmadı.');
    if(!function_exists('curl_init'))throw new STTelegramError('PHP cURL uzantısı etkin değil; Telegram gönderimi yapılamıyor.');
    $ch=curl_init('https://api.telegram.org/bot'.$token.'/'.$method);
    $photo=$method==='sendPhoto';
    curl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_HTTPHEADER=>$photo?[]:['Content-Type: application/json'],CURLOPT_POSTFIELDS=>$photo?st_photo_fields($payload):json_encode($payload),CURLOPT_RETURNTRANSFER=>true,CURLOPT_CONNECTTIMEOUT=>3,CURLOPT_TIMEOUT=>8]);
    $raw=curl_exec($ch);$status=curl_getinfo($ch,CURLINFO_HTTP_CODE);curl_close($ch);
    $a=is_string($raw)?json_decode($raw,true):null;
    if($status!==200 || !is_array($a) || empty($a['ok']))throw st_telegram_error((int)($a['error_code']??$status),(string)($a['description']??''),is_array($a['parameters']??null)?$a['parameters']:[]);return $a;
}
function st_backfill_receipts(PDO $db): void {
    foreach(['reviews'=>'review','tickets'=>'ticket'] as $table=>$kind){
        $db->exec("UPDATE ".$table." SET notification_sent=1,telegram_message_id=COALESCE(telegram_message_id,(SELECT o.telegram_message_id FROM outbox o WHERE o.id='".$kind.":'||".$table.".id AND o.sent=1 AND o.telegram_message_id>0)) WHERE notification_sent=0 AND EXISTS(SELECT 1 FROM outbox o WHERE o.id='".$kind.":'||".$table.".id AND o.sent=1 AND o.telegram_message_id>0)");
    }
}
function st_delivery_receipt(PDO $db,string $event,int $message_id): void {
    if(!preg_match('/^(review|ticket):([a-f0-9]{24})$/D',$event,$m))return;
    $table=$m[1]==='review'?'reviews':'tickets';
    $db->prepare('UPDATE '.$table.' SET notification_sent=1,telegram_message_id=? WHERE id=?')->execute([$message_id,$m[2]]);
}
function st_cleanup(): void {
    $db=st_db();$cfg=st_config();
    $db->exec('BEGIN IMMEDIATE');
    try{
        st_backfill_receipts($db);
        $review_cutoff=time()-max(1,(int)$cfg['pending_retention_days'])*86400;
        $has_legacy=(bool)$db->query("SELECT 1 FROM sqlite_master WHERE type='table' AND name='legacy_review_imports'")->fetchColumn();
        $review_cleanup="DELETE FROM reviews WHERE status!='approved' AND created<?";
        if($has_legacy)$review_cleanup.=" AND NOT EXISTS(SELECT 1 FROM legacy_review_imports li WHERE li.review_id=reviews.id AND li.imported>=?)";
        $q=$db->prepare($review_cleanup);$q->execute($has_legacy?[$review_cutoff,$review_cutoff]:[$review_cutoff]);
        $q=$db->prepare('DELETE FROM tickets WHERE created<?');$q->execute([time()-max(1,(int)$cfg['ticket_retention_days'])*86400]);
        $db->exec('DELETE FROM rate WHERE window<'.(int)(intdiv(time(),3600)-48));
        $q=$db->prepare('DELETE FROM idempotency WHERE created<?');$q->execute([time()-86400*30]);
        $q=$db->prepare('DELETE FROM outbox WHERE (sent=1 AND created<?) OR (sent=0 AND created<?)');$q->execute([time()-86400*7,time()-86400*90]);
        $db->prepare('DELETE FROM session_state WHERE updated<?')->execute([time()-86400*2]);
        // Gunluk ziyaret sayim anahtarlari en fazla 32 gun saklanir.
        $db->prepare("DELETE FROM meta WHERE k LIKE 'visitor:%' AND substr(k,9,10) < ?")
            ->execute([date('Y-m-d',time()-86400*32)]);
        $db->exec('COMMIT');
    }catch(Throwable $e){$db->exec('ROLLBACK');throw $e;}
}
function st_worker(int $limit=20,?string $event_id=null,bool $on_request=false): array {
    $db=st_db();$cfg=st_config();
    if(!$on_request)st_cleanup();
    if(!$cfg['telegram_token'] || !$cfg['telegram_chat_id']) return ['sent'=>0,'configured'=>false];
    // Visitor requests must not install webhooks or run global cleanup.
    if(!$on_request){st_ensure_webhook(false);st_check_daily_report(false);}
    $sent=0;$failed=0;
    for($i=0;$i<$limit;$i++) {
        $db->exec('BEGIN IMMEDIATE');
        $filter=$event_id!==null?' AND (id=? OR id LIKE ?)':'';
        $q=$db->prepare('SELECT * FROM outbox WHERE sent=0 AND due<=? AND lease<?'.$filter.' ORDER BY due,id LIMIT 1');
        $q->execute(array_merge([time(),time()],$event_id!==null?[$event_id,$event_id.':%']:[]));$row=$q->fetch();
        if(!$row){$db->exec('COMMIT');break;}
        $q=$db->prepare('UPDATE outbox SET lease=? WHERE id=?');$q->execute([time()+30,$row['id']]);$db->exec('COMMIT');
        try {
            $payload=json_decode($row['payload'],true);$method=$payload['_method']??'sendMessage';unset($payload['_method']);
            if($method==='answerCallbackQuery' && (int)$row['created']<time()-30){$q=$db->prepare('UPDATE outbox SET sent=1,lease=0 WHERE id=?');$q->execute([$row['id']]);continue;}
            if(in_array($method,['sendMessage','sendPhoto'],true))$payload['chat_id']=$cfg['telegram_chat_id'];
            if($method==='sendPhoto'){
                $photo_name=(string)($payload['_photo']??'');
                $photo_path=__DIR__.'/assets/notifications/'.$photo_name;
                if(!in_array($photo_name,['visit.png','review.png','ticket.png'],true) || !is_file($photo_path) || !is_readable($photo_path)){
                    // Gorsel eksikse metin ve yorum onay butonlarini koruyarak bildir.
                    $text_payload=['chat_id'=>$cfg['telegram_chat_id'],'text'=>(string)($payload['caption']??'Saglam Teknik bildirimi')];
                    if(isset($payload['reply_markup']))$text_payload['reply_markup']=$payload['reply_markup'];
                    $payload=$text_payload;$method='sendMessage';
                }
            }
            $receipt=st_telegram($method,$payload);$message_id=$receipt['result']['message_id']??null;
            if(in_array($method,['sendMessage','sendPhoto'],true) && (!is_int($message_id) || $message_id<=0))throw new STTelegramError('Telegram teslim onayı alınamadı; bildirim kuyrukta.');
            $db->exec('BEGIN IMMEDIATE');
            try{
                $q=$db->prepare("UPDATE outbox SET sent=1,lease=0,last_error='',telegram_message_id=?,delivered=? WHERE id=?");$q->execute([in_array($method,['sendMessage','sendPhoto'],true)?$message_id:null,time(),$row['id']]);
                if(in_array($method,['sendMessage','sendPhoto'],true))st_delivery_receipt($db,$row['id'],$message_id);
                $db->exec('COMMIT');
            }catch(Throwable $e){$db->exec('ROLLBACK');throw $e;}
            $sent++;
        }catch(Throwable $e){$n=(int)$row['attempts']+1;$error=$e instanceof STTelegramError?$e->getMessage():'Telegram’a ulaşılamadı; bildirim kuyrukta.';$delay=max($e instanceof STTelegramError?$e->retry_after:0,min(3600,30*(2**min($n,7))));$q=$db->prepare('UPDATE outbox SET attempts=?,due=?,lease=0,last_error=? WHERE id=?');$q->execute([$n,time()+$delay,$error,$row['id']]);$failed++;}
    }
    return ['sent'=>$sent,'failed'=>$failed,'configured'=>true];
}
function st_deliver_now(string $event_id): void {
    // One event and its companion photo/AI chunks. Duplicates are claimed by outbox leases.
    // Network errors must never cause a saved customer request to fail.
    try{if(!st_db()->inTransaction())st_worker(12,$event_id,true);}catch(Throwable $e){
        @error_log('SaglamTeknik: anlik Telegram iletimi siraya alindi ('.get_class($e).').');
    }
}
function st_finish_record(array $response,string $action,int $code=200): void {
    $event_id=$action.':'.$response['id'];
    st_deliver_now($event_id);
    $q=st_db()->prepare('SELECT sent FROM outbox WHERE id=?');$q->execute([$event_id]);
    $delivered=$q->fetchColumn();
    if($delivered===false){$table=$action==='review'?'reviews':'tickets';$q=st_db()->prepare('SELECT notification_sent FROM '.$table.' WHERE id=?');$q->execute([$response['id']]);$delivered=$q->fetchColumn();}
    $response['delivery']=$delivered?'sent':'queued';st_json($response,$code);
}
function st_ai_error(string $message): void {
    st_db()->prepare("INSERT INTO meta(k,v) VALUES('ai_error',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v")->execute([$message]);
}
function st_guide(string $device,string $issue): array {
    $q=st_normalize($issue);$kind=strpos(st_normalize($device),'klima')!==false?'klima':'kombi';
    if(preg_match('/gaz\s*kok|dogal\s*gaz\s*(kok|kac)/',$q) || ($kind==='kombi' && preg_match('/gaz[i]?\s*kac/',$q)))return ['ok'=>true,'source'=>'emergency','emergency_phone'=>'187','text'=>'Gaz kokusu veya gaz kaçağı bildiriyorsanız elektrik düğmelerine dokunmayın. Ortamdan ayrılıp dışarıdan 187 Doğal Gaz Acil hattını arayın.'];
    if(preg_match('/yangin|alev\s*al|duman\s*cik|yaralan/',$q))return ['ok'=>true,'source'=>'emergency','emergency_phone'=>'112','text'=>'Yangın, duman veya yaralanma bildiriyorsanız ortamdan güvenli biçimde uzaklaşın ve 112 Acil Çağrı Merkezi’ni arayın. Cihaza müdahale etmeyin.'];
    $file=__DIR__.'/assets/diagnostic-data.json';$rows=is_file($file)?json_decode(file_get_contents($file),true):[];
    $best=null;$score=0;
    foreach($rows??[] as $row)if($row['device']===$kind)foreach($row['terms'] as $term)if(strpos($q,$term)!==false && strlen($term)>$score){$best=$row;$score=strlen($term);}
    $text=$best['text']??'Şikâyetinizi biraz daha tarif eder misiniz: cihaz hiç açılmıyor mu, su mu akıtıyor, ses mi yapıyor, ısıtma/soğutma mı yetersiz? Marka/modeli ve ekranda gördüğünüz kodu aynen yazın. Kodları modele göre değerlendirelim; kesin parça teşhisi için yerinde kontrol gerekir.';
    return ['ok'=>true,'source'=>'guide','text'=>$text.' Sağlam Teknik: 0534 622 5515; aynı bilgileri WhatsApp ile de iletebilirsiniz.','guide_path'=>$best['path']??'/ariza-rehberi.html'];
}
function st_device(string $ua): string {
    $device=stripos($ua,'tablet')!==false || stripos($ua,'ipad')!==false?'Tablet':(preg_match('/mobile|android|iphone/i',$ua)?'Telefon':'Bilgisayar');
    $os='Bilinmiyor';foreach(['Android','iPhone','iPad','Windows','Macintosh','Linux'] as $v)if(stripos($ua,$v)!==false){$os=$v;break;}
    $browser='Diğer';foreach(['Edg'=>'Edge','OPR'=>'Opera','Firefox'=>'Firefox','Chrome'=>'Chrome','Safari'=>'Safari'] as $k=>$v)if(stripos($ua,$k)!==false){$browser=$v;break;}
    return $device.' / '.$os.' / '.$browser;
}
function st_decide(array $query): string {
    $cfg=st_config();$from=(string)($query['from']['id']??'');$chat=(string)($query['message']['chat']['id']??'');
    $allowed_admins = array_map('strval', $cfg['telegram_admin_ids']);
    $allowed_admins[] = (string)$cfg['telegram_chat_id'];
    if(!in_array($from, $allowed_admins, true) || $chat!==(string)$cfg['telegram_chat_id']) throw new DomainException('Onay yetkisi yok.');
    $data=$query['data']??'';
    if(!preg_match('/^r:([ar]):([a-f0-9]{24}):([a-f0-9]{16})$/D',$data,$m)) throw new DomainException('Geçersiz onay.');
    $db=st_db();$q=$db->prepare('SELECT status,nonce FROM reviews WHERE id=?');$q->execute([$m[2]]);$r=$q->fetch();
    if(!$r || !hash_equals($r['nonce'],$m[3])) throw new DomainException('Geçersiz onay.');
    $status=$m[1]==='a'?'approved':'rejected';$q=$db->prepare("UPDATE reviews SET status=?,decided=? WHERE id=? AND status='pending'");$q->execute([$status,time(),$m[2]]);
    return $q->rowCount()>0?($status==='approved'?'✅ Yorum onaylandı ve sitede yayınlandı.':'❌ Yorum reddedildi.'):'Bu yorum daha önce işlendi.';
}
// A single wall-clock budget covers the whole owner-configured key pool.
// Quota, billing, authorization and request errors stop the pool immediately.
function st_gemini_execute(array $keys,array $payload,string $model,callable $transport,?callable $clock=null): array {
    $clock=$clock??static function(): float{return microtime(true);};
    $deadline=$clock()+10.5;$attempts=0;$lastCode=0;
    $keys=array_slice(array_values(array_unique(array_filter(array_map('trim',$keys),static function($key){return $key!=='';}))),0,4);
    foreach($keys as $key){
        $remaining=(int)floor(($deadline-$clock())*1000);
        if($remaining<250)break;
        $timeout=min(9000,$remaining);$connect=min(1200,$timeout);$attempts++;
        $response=$transport($key,$model,$payload,$timeout,$connect);
        $lastCode=(int)($response['status']??0);$body=$response['body']??null;
        if($lastCode===200 && is_array($body)){
            $texts=[];
            foreach($body['candidates'][0]['content']['parts']??[] as $part){
                if(empty($part['thought'])&&is_string($part['text']??null)&&trim($part['text'])!=='')$texts[]=trim($part['text']);
            }
            $text=implode("\n",$texts);
            if($text!=='')return ['text'=>$text,'status'=>200,'attempts'=>$attempts];
        }
        if(!in_array($lastCode,[0,408,500,502,503,504],true))break;
    }
    return ['text'=>'','status'=>$lastCode,'attempts'=>$attempts];
}
function st_gemini_transport(string $key,string $model,array $payload,int $timeoutMs,int $connectMs): array {
    $ch=curl_init('https://generativelanguage.googleapis.com/v1beta/models/'.rawurlencode($model).':generateContent');
    curl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_HTTPHEADER=>['Content-Type: application/json','x-goog-api-key: '.$key],CURLOPT_POSTFIELDS=>json_encode($payload),CURLOPT_RETURNTRANSFER=>true,CURLOPT_CONNECTTIMEOUT_MS=>$connectMs,CURLOPT_TIMEOUT_MS=>$timeoutMs]);
    $raw=curl_exec($ch);$status=(int)curl_getinfo($ch,CURLINFO_HTTP_CODE);curl_close($ch);
    return ['status'=>$status,'body'=>is_string($raw)&&strlen($raw)<=131072?json_decode($raw,true):null];
}
function st_ai(array $a): array {
    $device=st_text($a,'device',2,40);$issue=st_text($a,'issue',3,1200);
    $fallback=st_guide($device,$issue);if($fallback['source']==='emergency')return $fallback;
    $notice=st_fault_advisory($issue);if($notice)return $notice;
    $manual=st_fault_response(['device'=>stripos($device,'klima')!==false?'klima':'kombi','query'=>$issue,'model_id'=>is_string($a['model_id']??null)?$a['model_id']:'','code'=>is_string($a['code']??null)?substr($a['code'],0,64):'','scope_confirmed'=>($a['scope_confirmed']??false)===true]);
    if($manual)return $manual;
    // Model kilavuzu ile dogrulanmamis bir koda yapay zeka anlami atamaz.
    if(preg_match('/(?<![a-z0-9])((?:CH|EA|EC|E|F|A|C|H|J|L|P|U)[ .-]?[0-9]{1,3}|EA|EC)(?![a-z0-9])/i',$issue,$code)
        || preg_match('/\b(?:hata|ariza|kod|kodu)\s+([0-9]{2,3})\b/',st_normalize($issue),$code)) {
        $shown=strtoupper(preg_replace('/[ .-]/','',$code[1]));
        return ['ok'=>true,'source'=>'guide','text'=>$shown.' kodunu not ettik. Kodun anlamı tam model ve üretici kaydıyla doğrulanmalıdır. Önce tam kod aranır; E1/E01 veya F4/F04 gibi baştaki sıfır varyantları yalnız seçili modelde tek ve çelişkisiz bir kayda bağlanıyorsa eşleştirilir. Farklı modellerin kod açıklamaları birbirine aktarılmaz. Model adını, kodun ekrandaki tam yazımını ve hangi kullanımda oluştuğunu paylaşın. Kapağı açmayın, gaz veya elektrik aksamına müdahale etmeyin ve tekrarlayan uyarıda reseti sürekli denemeyin. Sağlam Teknik: 0534 622 5515.','guide_path'=>stripos($device,'klima')!==false?'/klima-hata-kodu.html':'/kombi-hata-kodu.html'];
    }
    
    // Up to four owner-configured slots, used only for transient availability failover.
    $cfg=st_config();
    $default_keys = [];
    $configured_keys = array_filter(array_map('trim', explode(',', (string)$cfg['gemini_key'])), function($x){ return $x !== ''; });
    $gemini_keys = array_values(array_unique(array_merge($configured_keys, $default_keys)));

    if(empty($gemini_keys)){st_ai_error('Gemini API anahtarı ayarlanmadı; belirti rehberi çalışıyor.');return $fallback;}
    if(!function_exists('curl_init')){st_ai_error('PHP cURL uzantısı etkin değil; belirti rehberi çalışıyor.');return $fallback;}
    
    $instruction='Sağlam Teknik için Türkçe, 3-4 cümlelik teknik ön değerlendirme yaz. Sadece bildirilen belirtiyle ilişkili olası nedenleri belirsizlik belirterek açıkla; kesin teşhis veya ölçüm sonucu uydurma. Gereksiz korku, patlama/yangın tehdidi ve garantili sonuç kullanma. İç parça, elektrik, gaz, soğutucu devre müdahalesi anlatma. Gaz kokusunda elektrik düğmelerine dokunmadan ortamdan ayrılıp dışarıdan 187; yangın veya yaralanmada 112 yönlendirmesi yap, ticari arama önceliği verme. Diğer durumlarda model ve hata kodu notunu iste. Üretici kaydıyla doğrulanmayan koda anlam verme ve başka modelin kod açıklamasını taşıma. Kod eşleşmesinde önce tam yazım esas alınır; baştaki sıfır varyantı yalnız seçili modelde tek ve çelişkisiz bir kayda bağlanıyorsa kullanılabilir. Yabancı belge varsa ülke ve kontrolcü bağlamını açıkla; model uyumunu varsayma ve rehberi göstermek için onay kutusu şartı koyma. Tekrarlayan sorun için 0534 622 5515 veya WhatsApp ile servis randevusu öner.';
    $generation=['maxOutputTokens'=>1024,'temperature'=>0.3];
    if(in_array($cfg['gemini_model'],['gemini-3-flash-preview','gemini-3.5-flash-lite','gemini-3.6-flash'],true))$generation['thinkingConfig']=['thinkingLevel'=>'minimal'];
    $payload=['contents'=>[['parts'=>[['text'=>'Cihaz: '.$device.'. Bildirilen belirti: '.$issue]]]],'systemInstruction'=>['parts'=>[['text'=>$instruction]]],'generationConfig'=>$generation];
    
    $result=st_gemini_execute($gemini_keys,$payload,$cfg['gemini_model'],'st_gemini_transport');
    if($result['text']!==''){
        st_ai_error('');
        return ['ok'=>true,'text'=>$result['text'],'source'=>'ai'];
    }
    $errors=[400=>'Gemini isteği kabul edilmedi. Anahtar ve model ayarını kontrol edin.',401=>'Gemini API anahtarı kabul edilmedi.',402=>'Gemini kredi/faturalandırma sınırına ulaşıldı.',403=>'Gemini proje erişimi reddedildi.',404=>'Gemini model adı bu hesapta bulunamadı.',429=>'Gemini kota sınırına ulaşıldı; belirti rehberi devrede.'];
    st_ai_error($errors[$result['status']]??'Gemini servisine ulaşılamadı; belirti rehberi devrede.');
    return $fallback;
}
function st_dispatch(): void {
    $action=$_GET['action']??'';$method=$_SERVER['REQUEST_METHOD']??'GET';
    if($action==='business-maps' && $method==='GET')st_json(st_business_maps());
    if(($action==='setup_webhook' || $action==='daily_report_test') && $method==='GET') {
        st_fail('Bu işlem yönetici arayüzünden yapılmalıdır.',404);
    }
    if($action==='webhook') {
        if($method!=='POST')st_fail('POST gerekli.',405);
        $secret=st_config()['telegram_webhook_secret'];
        $provided=$_SERVER['HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN'] ?? '';
        if(!preg_match('/^[A-Za-z0-9_-]{32,256}$/D',$secret) || !is_string($provided) || !hash_equals($secret,$provided))st_fail('Bildirim doğrulanamadı.',403);
        $raw=file_get_contents('php://input');
        $a=is_string($raw)?json_decode($raw,true):null;
        if(!is_array($a))st_json(['ok'=>true]);
        $query=$a['callback_query']??null;if(!is_array($query))st_json(['ok'=>true]);
        try{$message=st_decide($query);}catch(DomainException $e){st_fail('Onay yetkisi veya kayıt doğrulanamadı.',403);}
        if(!empty($query['id'])) {
            $p=['_method'=>'answerCallbackQuery','callback_query_id'=>(string)$query['id'],'text'=>$message,'show_alert'=>true];
            st_enqueue(st_db(),'ack:'.hash('sha256',(string)$query['id']),$p);
            try{
                $send=$p;unset($send['_method']);
                st_telegram('answerCallbackQuery',$send);
                $q=st_db()->prepare('UPDATE outbox SET sent=1 WHERE id=?');
                $q->execute(['ack:'.hash('sha256',(string)$query['id'])]);
                if(!empty($query['message']['chat']['id']) && !empty($query['message']['message_id'])) {
                    st_telegram('editMessageReplyMarkup', [
                        'chat_id' => $query['message']['chat']['id'],
                        'message_id' => (int)$query['message']['message_id'],
                        'reply_markup' => ['inline_keyboard' => []]
                    ]);
                }
            }catch(Throwable $e){}
        }
        st_json(['ok'=>true]);
    }
    if($action==='bootstrap' && $method==='GET'){
        // Daily reports are queued locally. Webhook setup and delivery belong to cron.
        st_check_daily_report(false);
        st_json(['ok'=>true,'csrf'=>st_csrf(st_session())]);
    }
    if($action==='reviews' && $method==='GET') {
        $rows=st_db()->query("SELECT id,author,district,service,cat,rating,comment,created FROM reviews WHERE status='approved' ORDER BY created DESC LIMIT 500")->fetchAll();
        foreach($rows as &$r){$r['rating']=(int)$r['rating'];$r['date']=date('d.m.Y',(int)$r['created']);if($r['district']!=='')$r['service'].=' ('.$r['district'].')';$r['source']='site';unset($r['district'],$r['created']);}
        st_json(['ok'=>true,'reviews'=>$rows]);
    }
    if($method!=='POST')st_fail('İşlem bulunamadı.',404);
    $session=st_require_csrf();$a=st_body();
    if($action==='activity'){
        // Compatibility: suppress repeated 404s. Activity measurements are not recorded in rollback mode.
        st_json(['ok'=>true,'recorded'=>false]);
    }
    if($action==='query'){
        st_rate('query',120);
        $res = st_search($a);
        $q_txt = $res['query'] ?? ($a['query'] ?? '');
        st_session_track($session, 'search', (string)$q_txt);
        st_stat_inc(!empty($res['found']) ? 'search_found' : 'search_not_found');
        try {
            $gps = st_gps_description($a);
            $found_icon = !empty($res['found']) ? '✅ Eşleşme Bulundu' : '❌ Eşleşme Bulunamadı';
            $target_info = array_filter([
                $res['device_label'] ?? '',
                $res['brand'] ?? '',
                $res['district'] ?? '',
                $res['neighborhood'] ?? '',
                $res['locality'] ?? ''
            ]);
            $search_id = 'search:' . hash_hmac('sha256', $session . ':' . $q_txt, st_secret()) . ':' . intdiv(time(), 60);
            $search_text = "🔍 SİTEDEN ARAMA YAPILDI\n"
                . "🕒 Tarih/Saat: " . date('d.m.Y H:i:s') . " (İstanbul)\n"
                . "⌨️ Aranan İfade: " . $q_txt . "\n"
                . "📊 Sonuç Durumu: " . $found_icon . "\n"
                . (!empty($target_info) ? "🎯 Tespit Edilen: " . implode(' / ', $target_info) . "\n" : "")
                . (!empty($res['path']) ? "📄 Yönlendirilen Sayfa: " . $res['path'] . "\n" : "")
                . "📱 Kullanılan Cihaz: " . st_device($_SERVER['HTTP_USER_AGENT'] ?? '') . "\n"
                . "📍 Konum: " . ($gps ?: st_location());
            st_enqueue(st_db(), $search_id, ['text' => $search_text]);
            st_deliver_now($search_id);
        } catch (Throwable $e) {}
        st_json($res);
    }
    if($action==='visit') {
        st_rate('visit',60);$page=st_text($a,'page',1,160);$page=explode('?',$page)[0];
        if(!preg_match('#^/[a-zA-Z0-9_./-]*$#D',$page)||strpos($page,'..')!==false)st_fail('Sayfa bilgisi geçersiz.');
        // Ziyaret bildirimi kapali olsa da gunluk sayac calisir. Bir oturum/gun = bir ziyaretci.
        $visit_day=date('Y-m-d');
        $visit_key='visitor:'.$visit_day.':'.hash_hmac('sha256',$session,st_secret());
        $visit_db=st_db();
        $visit_insert=$visit_db->prepare('INSERT OR IGNORE INTO meta(k,v) VALUES(?,?)');
        $visit_insert->execute([$visit_key,'1']);
        if($visit_insert->rowCount()===1)st_stat_inc('visits');
        if(!st_config()['visit_notifications'])st_json(['ok'=>true,'enabled'=>false]);
        $s_info = st_session_info($session);
        $search_line = $s_info['searched']
            ? "✅ Yapıldı (" . $s_info['last_query'] . ")"
            : "❌ Yapılmadı";
        $ticket_line = $s_info['ticket_sent']
            ? "✅ Servis talebi oluşturdu"
            : "➖ Henüz talep oluşturmadı";
        $gps=st_gps_description($a);
        $id=($gps?'visit-location:':'visit:').hash_hmac('sha256',$session,st_secret()).':'.intdiv(time(),300);
        $text="🌐 Site ziyareti\n"
            . "🕒 Tarih/saat: ".date('d.m.Y H:i:s')." (İstanbul)\n"
            . "📄 Sayfa: ".$page."\n"
            . "📱 Cihaz: ".st_device($_SERVER['HTTP_USER_AGENT']??'')."\n"
            . "📍 Konum: ".($gps?:st_location())."\n"
            . "🔍 Siteden Arama: ".$search_line."\n"
            . "🛠 Talep Durumu: ".$ticket_line;
        st_enqueue(st_db(),$id,['text'=>$text]);st_deliver_now($id);st_json(['ok'=>true,'enabled'=>true]);
    }
    if($action==='ai'){
        st_rate('ai',12);
        st_stat_inc('ai_questions');
        $res = st_ai($a);
        try {
            $device_txt = isset($a['device']) && is_string($a['device']) ? trim($a['device']) : 'Belirtilmedi';
            $issue_txt = isset($a['issue']) && is_string($a['issue']) ? trim($a['issue']) : 'Belirtilmedi';
            $ans_txt = $res['text'] ?? '';
            $src_label = ($res['source'] ?? '') === 'ai' ? '✨ Gemini AI' : (($res['source'] ?? '') === 'emergency' ? '🚨 Acil Durum Uyarı' : '📘 Belirti Rehberi');
            $s_info = st_session_info($session);
            $search_line = $s_info['searched'] ? "✅ Yapıldı (" . $s_info['last_query'] . ")" : "❌ Yapılmadı";
            $gps = st_gps_description($a);
            $ai_id = 'ai:' . bin2hex(random_bytes(12));
            $ai_text = "🤖 AI Usta Soru & Cevap\n"
                . "🕒 Tarih/saat: " . date('d.m.Y H:i:s') . " (İstanbul)\n"
                . "🔧 Cihaz: " . $device_txt . "\n"
                . "📡 Yanıt Kaynağı: " . $src_label . "\n\n"
                . "❓ Sorulan Soru:\n" . $issue_txt . "\n\n"
                . "💡 Verilen Cevap:\n" . $ans_txt . "\n\n"
                . "🔍 Siteden Arama: " . $search_line . "\n"
                . "📱 Ziyaretçi cihazı: " . st_device($_SERVER['HTTP_USER_AGENT'] ?? '') . "\n"
                . "📍 Konum: " . ($gps ?: 'Konum paylaşılmadı (AI yanıtı için IP konum servisi çağrılmaz).');
            st_enqueue(st_db(), $ai_id, ['text' => $ai_text]);
            st_deliver_now($ai_id);
        } catch (Throwable $e) {}
        st_json($res);
    }
    if(!in_array($action,['review','ticket'],true))st_fail('İşlem bulunamadı.',404);
    if(!empty($a['website']))st_fail('Başvuru doğrulanamadı.');
    $idempotency=$_SERVER['HTTP_IDEMPOTENCY_KEY']??'';
    if(!preg_match('/^[a-zA-Z0-9_-]{16,80}$/D',$idempotency))st_fail('Başvuru anahtarı eksik.');
    $key=hash_hmac('sha256',$action.'.'.$idempotency,st_secret());$hash=hash('sha256',json_encode($a));$db=st_db();
    $q=$db->prepare('SELECT hash,response FROM idempotency WHERE k=?');$q->execute([$key]);$old=$q->fetch();
    if($old){if(!hash_equals($old['hash'],$hash))st_fail('Aynı başvuru anahtarı farklı içerikle kullanılamaz.',409);st_finish_record(json_decode($old['response'],true),$action);}
    st_rate($action,$action==='review'?5:8);$id=bin2hex(random_bytes(12));$stamp=time();
    $s_info = st_session_info($session);
    $search_line = $s_info['searched'] ? "✅ Yapıldı (" . $s_info['last_query'] . ")" : "❌ Yapılmadı";
    if($action==='review') {
        $author=st_text($a,'author',2,80);$district=st_text($a,'district',2,80);$comment=st_text($a,'comment',10,2000);$service=st_text($a,'service',2,80);
        if(!in_array($service,['Kombi Bakımı / Onarımı','Klima Bakımı / Montajı','Makineli Petek Temizliği','Acil Servis Hizmeti'],true))st_fail('Hizmet türü geçersiz.');
        $rating=$a['rating']??0;if(!is_int($rating)||$rating<1||$rating>5)st_fail('Puan 1 ile 5 arasında olmalı.');
        if(($a['consent']??false)!==true)st_fail('Yayın onayını işaretleyin.');
        $cat=strpos($service,'Klima')!==false?'klima':(strpos($service,'Petek')!==false?'petek':'kombi');$nonce=bin2hex(random_bytes(8));
        $data=[$id,$author,$district,$service,$cat,$rating,$comment,$nonce,$stamp,1];
        $sql='INSERT INTO reviews(id,author,district,service,cat,rating,comment,nonce,created,consent) VALUES(?,?,?,?,?,?,?,?,?,?)';
        $text="⭐ Yorum onayı bekliyor\n🆔 Kayıt: $id\n🕒 Tarih: ".date('d.m.Y H:i:s',$stamp)." (İstanbul)\n👤 Ad: $author\n📍 İlçe: $district\n🔧 Hizmet: $service\n🌟 Puan: $rating/5\n\n💬 $comment";
        $payload=['text'=>$text,'reply_markup'=>['inline_keyboard'=>[[['text'=>'✅ Onayla','callback_data'=>'r:a:'.$id.':'.$nonce],['text'=>'❌ Reddet','callback_data'=>'r:r:'.$id.':'.$nonce]]]]];
        $response=['ok'=>true,'id'=>$id,'status'=>'pending','message'=>'Yorumunuz kaydedildi. Onay verilirse yayınlanacak.'];
    }else {
        $name=st_text($a,'name',2,80);$phone=st_text($a,'phone',10,25);$district=st_text($a,'district',2,120);$device=st_text($a,'device',2,40);$issue=st_text($a,'issue',5,2000);
        if(!preg_match('/^[+0-9 ()-]+$/D',$phone)||strlen(preg_replace('/\D/','',$phone))<10||strlen(preg_replace('/\D/','',$phone))>15)st_fail('Telefon numarasını kontrol edin.');
        if(!in_array($device,['Kombi','Klima','Petek'],true))st_fail('Cihaz türü geçersiz.');
        $sql='INSERT INTO tickets(id,name,phone,district,device,issue,created) VALUES(?,?,?,?,?,?,?)';$data=[$id,$name,$phone,$district,$device,$issue,$stamp];
        $payload=['text'=>"🛠 Servis talebi\n🆔 Kayıt: $id\n🕒 Tarih: ".date('d.m.Y H:i:s',$stamp)." (İstanbul)\n👤 Ad: $name\n📞 Telefon: $phone\n📍 Konum (müşterinin beyanı): $district\n🔧 Cihaz: $device\n\n📝 $issue"];
        $response=['ok'=>true,'id'=>$id,'message'=>'Talebiniz kaydedildi. Hızlı dönüş için arayabilir veya WhatsApp ile iletebilirsiniz.'];
    }
    $gps=st_gps_description($a);
    $payload['text'].="\n\n🔍 Siteden Arama: ".$search_line."\n📱 Ziyaretçi cihazı: ".st_device($_SERVER['HTTP_USER_AGENT']??'')."\n🗺 Konum: ".($gps?:st_location());
    $db->exec('BEGIN IMMEDIATE');
    try {
        $q=$db->prepare('SELECT hash,response FROM idempotency WHERE k=?');$q->execute([$key]);$old=$q->fetch();
        if($old){$db->exec('COMMIT');if(!hash_equals($old['hash'],$hash))st_fail('Başvuru anahtarı çakıştı.',409);st_finish_record(json_decode($old['response'],true),$action);}
        $db->prepare($sql)->execute($data);st_enqueue($db,$action.':'.$id,$payload);
        st_stat_inc($action==='review'?'reviews':'tickets');
        if($action==='ticket')st_session_track($session,'ticket');
        $db->prepare('INSERT INTO idempotency(k,hash,response,created) VALUES(?,?,?,?)')->execute([$key,$hash,json_encode($response,JSON_UNESCAPED_UNICODE),$stamp]);$db->exec('COMMIT');
    }catch(Throwable $e){$db->exec('ROLLBACK');throw $e;}
    st_finish_record($response,$action,201);
}
if(!defined('ST_LIBRARY_MODE')) {
    try{st_dispatch();}catch(Throwable $e){
        $safe=date('c').' | '.get_class($e).' | '.basename($e->getFile()).':'.$e->getLine().' | '.(int)$e->getCode()."\n";
        try { @file_put_contents(st_private().'/api-hata-guvenli.log',$safe,FILE_APPEND|LOCK_EX); } catch (Throwable $ignored) {}
        @error_log('SaglamTeknik API: '.trim($safe));
        st_json(['ok'=>false,'error'=>'İşlem tamamlanamadı. Daha sonra deneyin veya 0534 622 5515 üzerinden ulaşın.'],503);
    }
}
