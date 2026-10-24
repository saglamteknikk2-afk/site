<?php
declare(strict_types=1);
// Isolated synthetic fixtures; no production private directory, provider request,
// Telegram dispatch, webhook setup or notification worker is executed.
define('ST_LIBRARY_MODE',true);
$root=dirname(__DIR__);$base=sys_get_temp_dir().'/st-business-runtime-'.bin2hex(random_bytes(6));
mkdir($base,0700);mkdir($base.'/httpdocs',0700);mkdir($base.'/private',0700);
putenv('SAGLAM_PRIVATE_DIR='.$base.'/private');
require $root.'/server/api.php';
$checks=0;$assert=static function(bool $ok,string $name)use(&$checks):void{$checks++;if(!$ok)throw new RuntimeException($name);};
$remove=function(string $path)use(&$remove):void{if(is_link($path)||!is_dir($path)){unlink($path);return;}foreach(scandir($path) as $part)if($part!=='.'&&$part!=='..')$remove($path.'/'.$part);rmdir($path);};
try{
    $originalRoot=$_SERVER['DOCUMENT_ROOT']??null;$originalCwd=getcwd();
    try{
        chdir('/');$_SERVER['DOCUMENT_ROOT']='';
        $assert(st_business_webroot()===realpath($root.'/server'),'Empty CLI document root never resolves to current directory');
        unset($_SERVER['DOCUMENT_ROOT']);
        $assert(st_business_webroot()===realpath($root.'/server'),'Missing CLI document root uses the API directory');
    }finally{chdir($originalCwd);if($originalRoot===null)unset($_SERVER['DOCUMENT_ROOT']);else $_SERVER['DOCUMENT_ROOT']=$originalRoot;}
    foreach([
        ['https://maps.app.goo.gl/UnitTestLink','google',false,true],
        ['https://www.google.com/maps/place/unit-test/','google',false,true],
        ['https://www.google.com/maps/embed?pb=unit-test','google',true,true],
        ['https://yandex.com.tr/maps/org/unit-test/1','yandex',false,true],
        ['https://yandex.ru/map-widget/v1/?um=unit-test','yandex',true,true],
        ['https://google.com.evil.invalid/maps/place/1','google',false,false],
        ['https://evil.invalid/?url=https://google.com/maps','google',false,false],
        ['http://www.google.com/maps/place/1','google',false,false],
        ['javascript:alert(1)','google',false,false],
        ['https://user:pass@www.google.com/maps/place/1','google',false,false],
        ['https://www.google.com:444/maps/place/1','google',false,false],
        ['https://www.google.com/search?q=maps','google',false,false],
        ['https://yandex.com/search/?text=maps','yandex',false,false],
        ['<iframe src="https://www.google.com/maps/embed?pb=test"></iframe>','google',true,false],
        ['https://www.google.com/maps/embed?pb=test" onload="alert(1)','google',true,false],
        ['https://yandex.com/maps/org/unit/1','yandex',true,false],
    ] as [$url,$provider,$embed,$expected])$assert((st_business_map_url($url,$provider,$embed)!=='')===$expected,'URL allowlist case');
    $maps=st_business_maps($base.'/private');$assert(!$maps['configured']&&$maps['maps']['google']['url']==='','Missing config is empty');
    file_put_contents($base.'/private/haritalar.json',json_encode(['google_url'=>'https://maps.app.goo.gl/UnitTestLink','yandex_url'=>'https://yandex.com/maps/org/unit/1','google_embed_url'=>'https://www.google.com/maps/embed?pb=unit-test','telegram_token'=>'SYNTHETIC_NEVER_PUBLIC']));
    $maps=st_business_maps($base.'/private');$assert($maps['configured']&&$maps['maps']['google']['embed_url']!=='','Valid maps returned');
    $assert(strpos(json_encode($maps),'SYNTHETIC_NEVER_PUBLIC')===false&&count($maps['maps'])===2,'Only public allowlisted map fields returned');
    file_put_contents($base.'/private/haritalar.json',json_encode(['google_url'=>'https://evil.invalid/maps','google_embed_url'=>'https://www.google.com/maps/embed?pb=test']));
    $assert(st_business_maps($base.'/private')['maps']['google']['embed_url']==='','No iframe without valid share URL');
    file_put_contents($base.'/private/haritalar.json','{broken');$assert(!st_business_maps($base.'/private')['configured'],'Malformed JSON stays empty');
    file_put_contents($base.'/private/haritalar.json',str_repeat(' ',16385));$assert(!st_business_maps($base.'/private')['configured'],'Oversized config stays empty');
    $safe=st_business_private_directory($base.'/new-private',$base.'/httpdocs');$assert(is_dir($safe),'Outside-root private directory created');
    foreach([$base.'/httpdocs/private',$base.'/new-private/../httpdocs/private'] as $bad){
        $rejected=false;try{st_business_private_directory($bad,$base.'/httpdocs');}catch(RuntimeException $e){$rejected=true;}
        $assert($rejected&&!is_dir($base.'/httpdocs/private'),'Inside-root storage rejected before creation');
    }
    if(function_exists('symlink')&&symlink($base.'/httpdocs',$base.'/root-link')){
        $rejected=false;try{st_business_private_directory($base.'/root-link/private',$base.'/httpdocs');}catch(RuntimeException $e){$rejected=true;}
        $assert($rejected,'Symlink into webroot rejected');
    }
    $legacy="GEMINI_API_KEY_1=unit-test-slot-one\nGEMINI_API_KEY_2=unit-test-slot-two\nGEMINI_API_KEY_3=unit-test-slot-three\nGEMINI_API_KEY_4=unit-test-slot-four\n";
    file_put_contents($base.'/private/site_apileri.txt',$legacy);
    $assert(count(explode(',',st_config(true)['gemini_key']))===4,'Four legacy filename slots retained');
    file_put_contents($base.'/private/site_apileri,.txt',"GEMINI_API_KEY_1=unit-test-primary-slot\n");
    $before=hash_file('sha256',$base.'/private/site_apileri,.txt');
    $assert(st_config(true)['gemini_key']==='unit-test-primary-slot','Exact comma filename takes precedence');
    $assert(hash_file('sha256',$base.'/private/site_apileri,.txt')===$before,'Existing credential file not modified');
    $time=100.0;$windows=[];
    $clock=static function()use(&$time):float{return $time;};
    $transport=static function($key,$model,$payload,$timeout,$connect)use(&$time,&$windows):array{$windows[]=[$timeout,$connect];$time+=$timeout/1000;return ['status'=>0,'body'=>null];};
    $r=st_gemini_execute(['one','two','three','four'],[],'unit-test-model',$transport,$clock);
    $assert($time<=110.501&&array_sum(array_column($windows,0))<=10500,'Whole pool respects 10.5 second network budget');
    $assert(count($windows)<=4&&max(array_column($windows,1))<=1200,'Connection windows bounded');
    foreach([429,402,401,403,400,404] as $status){
        $calls=0;$r=st_gemini_execute(['one','two','three','four'],[],'unit-test-model',static function()use(&$calls,$status):array{$calls++;return ['status'=>$status,'body'=>null];});
        $assert($calls===1&&$r['text']==='','No key rotation on quota/billing/auth/request error');
    }
    $calls=0;$r=st_gemini_execute(['one','two'],[],'unit-test-model',static function()use(&$calls):array{$calls++;return $calls===1?['status'=>503,'body'=>null]:['status'=>200,'body'=>['candidates'=>[['content'=>['parts'=>[['thought'=>true,'text'=>'not public'],['text'=>'Synthetic safe response']]]]]]];});
    $assert($calls===2&&$r['text']==='Synthetic safe response','Transient failover succeeds and excludes thought parts');
    $r=st_gemini_execute(['one'],[],'unit-test-model',static function():array{return ['status'=>200,'body'=>['candidates'=>[['content'=>['parts'=>[['thought'=>true,'text'=>'Synthetic hidden reasoning only']]]]]]];});
    $assert($r['text']==='','Thought-only provider response is never a public answer');
    $r=st_gemini_execute(['one'],[],'unit-test-model',static function():array{return ['status'=>200,'body'=>null];});
    $assert($r['text']==='','Malformed successful provider body preserves fallback');
    $calls=0;st_gemini_execute(['one','two','three','four','five'],[],'unit-test-model',static function()use(&$calls):array{$calls++;return ['status'=>503,'body'=>null];});
    $assert($calls===4,'No more than four owner slots');
    st_enqueue(st_db(),'ai:unit-test',['text'=>'Synthetic queued notification']);
    $row=st_db()->query("SELECT sent,attempts FROM outbox WHERE id='ai:unit-test'")->fetch();
    $assert((int)$row['sent']===0&&(int)$row['attempts']===0,'Notification is durable and unsent until cron');
    $emergency=st_ai(['device'=>'Kombi','issue'=>'gaz kokusu var']);
    $assert($emergency['source']==='emergency'&&$emergency['emergency_phone']==='187','Emergency precedence preserved');
    echo json_encode(['checks'=>$checks,'errors'=>0,'network_requests'=>0,'production_private_read'=>false])."\n";
}finally{$remove($base);putenv('SAGLAM_PRIVATE_DIR');}
