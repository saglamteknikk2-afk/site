<?php
declare(strict_types=1);
// Local, read-only installation inspection. Never opens a public diagnostics API.
if(PHP_SAPI!=='cli'){http_response_code(404);exit;}
require_once __DIR__.'/business-config.php';
if(is_file(__DIR__.'/storage.php'))require_once __DIR__.'/storage.php';

function st_installation_database_setting(string $private): ?string {
    $environment=getenv('SAGLAM_DATABASE_PATH');
    if(is_string($environment)&&$environment!=='')return $environment;
    $primary=$private.'/site_apileri,.txt';$legacy=$private.'/site_apileri.txt';
    $file=is_file($primary)?$primary:$legacy;
    if(!is_file($file)||!is_readable($file)||filesize($file)>65536)return null;
    $raw=file_get_contents($file);if(!is_string($raw))return null;
    // Only the database-path setting is inspected; API key values are not output.
    $path=null;
    foreach(preg_split('/\r\n|\n|\r/',preg_replace('/^\xEF\xBB\xBF/','',$raw)) as $line){
        if(!preg_match('/^\s*DATABASE_PATH\s*=(.*)$/i',$line,$match))continue;
        $value=trim($match[1]);
        if(strlen($value)>=2&&in_array($value[0],['"',"'"],true)&&substr($value,-1)===$value[0])$value=substr($value,1,-1);
        $path=$value!==''?$value:null;
    }
    return $path;
}

function st_installation_diagnostics(string $directory,?string $private=null): array {
    $root=realpath($directory);
    if(!$root||!is_dir($root))throw new RuntimeException('Yayın klasörü okunamadı.');
    $private=$private??(getenv('SAGLAM_PRIVATE_DIR')?:dirname($root).'/private/saglam-teknik');
    $privateReal=realpath($private);
    $private=$privateReal?:$private;
    $privateSafe=substr($private,0,1)==='/'&&!st_business_inside($private,$root);
    $infoFile=$root.'/build-info.json';
    $info=is_file($infoFile)&&filesize($infoFile)<262144?json_decode((string)file_get_contents($infoFile),true):null;
    $build=[];
    foreach(['schema_version','mode','base_path','visitor_pages','content_sha256','archive_sha256','archive_sha256_kind','production_deployed'] as $key)if(is_array($info)&&array_key_exists($key,$info))$build[$key]=$info[$key];
    $assets=[];$index=$root.'/index.html';
    if(is_file($index)&&filesize($index)<2097152){
        preg_match_all('/<(?:script|link)\b[^>]*\b(?:src|href)=["\']([^"\']+)["\'][^>]*>/i',(string)file_get_contents($index),$matches);
        foreach(array_slice(array_unique($matches[1]),0,100) as $reference){
            $url=parse_url(html_entity_decode($reference,ENT_QUOTES,'UTF-8'));
            if(!is_array($url)||isset($url['scheme'])||isset($url['host'])||!preg_match('/\.(?:js|css)$/i',$url['path']??''))continue;
            $name=rawurldecode(ltrim($url['path'],'/'));$file=realpath($root.'/'.$name);
            $exists=$file&&st_business_inside($file,$root)&&is_file($file)&&is_readable($file)&&filesize($file)<=8388608;
            parse_str($url['query']??'',$query);$version=$query['v']??null;
            $hash=$exists?hash_file('sha256',$file):null;
            $assets[]=['file'=>$name,'exists'=>(bool)$exists,'sha256'=>$hash,'declared_version'=>is_string($version)?$version:null,'version_matches'=>$version===null?null:($hash!==null&&is_string($version)&&preg_match('/^[a-f0-9]{10}$/D',$version)===1&&substr($hash,0,10)===$version)];
        }
    }
    $fingerprints=[];
    foreach(['api.php','worker.php','notification-dispatch.php','notification-support.php','analytics.php','storage.php','assets/site.js','assets/home.js','assets/premium-reviews.js','assets/fault-lookup.js'] as $name){
        $file=realpath($root.'/'.$name);
        $fingerprints[$name]=$file&&st_business_inside($file,$root)&&is_file($file)&&is_readable($file)&&filesize($file)<=8388608?hash_file('sha256',$file):null;
    }
    $configuration=[];
    foreach(['site_apileri,.txt','site_apileri.txt','haritalar.json','maps.json'] as $name)$configuration[$name]=['exists'=>$privateSafe&&is_file($private.'/'.$name),'readable'=>$privateSafe&&is_readable($private.'/'.$name)];
    $storage=['inspected'=>false];
    if($privateSafe&&is_dir($private)&&function_exists('st_storage_diagnostics')){
        try{$storage=st_storage_diagnostics($private,$root,st_installation_database_setting($private));}
        catch(Throwable $error){$storage=['inspected'=>false,'error_class'=>get_class($error),'error'=>'Veritabanı seçimi doğrulanamadı; storage-status çıktısını kontrol edin.'];}
    }
    $images=[];
    foreach(['visit.png','review.png','ticket.png'] as $name)$images[$name]=is_readable($root.'/assets/notifications/'.$name);
    $pdo=class_exists('PDO');$sqlite=$pdo&&in_array('sqlite',PDO::getAvailableDrivers(),true);
    $assetErrors=array_values(array_filter($assets,static function(array $asset):bool{return !$asset['exists']||$asset['version_matches']===false;}));
    return [
        'read_only'=>true,'network_requests'=>0,'database_created'=>false,
        'checked_at_istanbul'=>(new DateTimeImmutable('now',new DateTimeZone('Europe/Istanbul')))->format('Y-m-d H:i:s'),
        'runtime'=>['php'=>PHP_VERSION,'php_8_2_or_newer'=>version_compare(PHP_VERSION,'8.2','>='),'pdo_sqlite'=>$sqlite,'curl'=>function_exists('curl_init')],
        'application_directory'=>$root,'cli_document_root'=>$_SERVER['DOCUMENT_ROOT']??'',
        'vhost_binding_verified'=>false,'vhost_note'=>'Plesk Hosting Ayarları belge kökü bu CLI çıktısıyla bağımsız doğrulanmaz.',
        'build_info'=>$build,'build_info_readable'=>is_array($info),
        'private_directory'=>$private,'private_outside_webroot'=>$privateSafe,'private_exists'=>is_dir($private),'private_writable'=>$privateSafe&&is_dir($private)&&is_writable($private),
        'configuration_files'=>$configuration,'storage'=>$storage,'notification_images'=>$images,
        'asset_versions_match'=>$assets!==[]&&$assetErrors===[],'assets'=>$assets,'file_sha256'=>$fingerprints,
        'scope'=>'Yerel dosyalar incelendi; Cloudflare yanıtı, PHP-FPM belge kökü, Gemini veya Telegram teslimi test edilmedi. build_info özeti yayımlanmış bildirimi gösterir; bütün dizinin bağımsız hash doğrulaması değildir.'
    ];
}

if(!defined('ST_DIAGNOSTIC_LIBRARY_MODE')){
    try{echo json_encode(st_installation_diagnostics(__DIR__),JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_INVALID_UTF8_SUBSTITUTE)."\n";}
    catch(Throwable $error){fwrite(STDERR,'Kurulum kontrolü tamamlanamadı: '.get_class($error)."\n");exit(1);}
}
