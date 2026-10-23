<?php
declare(strict_types=1);

// Only public business-map URLs are returned here. This helper never parses the
// API credential TXT file, makes HTTP requests, or accepts iframe/script markup.
function st_business_inside(string $path, string $root): bool {
    $root=rtrim(str_replace('\\','/',$root),'/');
    $path=rtrim(str_replace('\\','/',$path),'/');
    return $path===$root || strpos($path,$root.'/')===0;
}
function st_business_webroot(): string {
    $here=realpath(__DIR__)?:__DIR__;
    $document=isset($_SERVER['DOCUMENT_ROOT'])?realpath((string)$_SERVER['DOCUMENT_ROOT']):false;
    return $document && st_business_inside($here,$document)?$document:$here;
}
function st_business_private_directory(?string $configured=null, ?string $publicRoot=null): string {
    $root=realpath($publicRoot??st_business_webroot());
    if(!$root)throw new RuntimeException('Yayın kökü doğrulanamadı.');
    $p=$configured??(getenv('SAGLAM_PRIVATE_DIR')?:dirname($root).'/private/saglam-teknik');
    if($p==='' || strpos($p,"\0")!==false || strlen($p)>4096)throw new RuntimeException('Özel depolama yolu geçersiz.');
    if($p[0]!=='/' && !preg_match('~^[A-Za-z]:[\\\\/]~',$p))$p=getcwd().DIRECTORY_SEPARATOR.$p;
    $parts=[];
    foreach(explode('/',str_replace('\\','/',$p)) as $part){
        if($part===''||$part==='.')continue;
        if($part==='..'){array_pop($parts);continue;}
        $parts[]=$part;
    }
    $p=(DIRECTORY_SEPARATOR==='/'?'/':'').implode(DIRECTORY_SEPARATOR,$parts);
    if(st_business_inside($p,$root))throw new RuntimeException('Depolama web kökünün dışında olmalıdır.');
    $ancestor=$p;$suffix=[];
    while(!file_exists($ancestor)&&!is_link($ancestor)){
        $parent=dirname($ancestor);if($parent===$ancestor)throw new RuntimeException('Özel depolama yolu doğrulanamadı.');
        array_unshift($suffix,basename($ancestor));$ancestor=$parent;
    }
    $resolved=realpath($ancestor);
    if(!$resolved || st_business_inside($resolved.($suffix?DIRECTORY_SEPARATOR.implode(DIRECTORY_SEPARATOR,$suffix):''),$root))throw new RuntimeException('Depolama web kökünün dışında olmalıdır.');
    if(!is_dir($p)&&!@mkdir($p,0700,true)&&!is_dir($p))throw new RuntimeException('Depolama kullanılamıyor.');
    $real=realpath($p);
    if(!$real || st_business_inside($real,$root))throw new RuntimeException('Depolama web kökünün dışında olmalıdır.');
    return $real;
}
function st_business_map_url($value, string $provider, bool $embed=false): string {
    if(!is_string($value))return '';
    $value=trim($value);
    if($value===''||strlen($value)>4096||preg_match('/[\x00-\x20\x7f<>"\\\\]/',$value))return '';
    $url=parse_url($value);
    if(!is_array($url)||strtolower($url['scheme']??'')!=='https'||isset($url['user'])||isset($url['pass'])||isset($url['port'])&&$url['port']!==443)return '';
    $host=strtolower($url['host']??'');$path=$url['path']??'/';
    if($provider==='google'){
        if($embed)return in_array($host,['www.google.com','google.com','www.google.com.tr','google.com.tr'],true)&&$path==='/maps/embed'&&isset($url['query'])?$value:'';
        if(in_array($host,['maps.app.goo.gl','g.page'],true))return preg_match('~^/[A-Za-z0-9_/-]+$~D',$path)?$value:'';
        if($host==='goo.gl')return preg_match('~^/maps/[A-Za-z0-9_-]+/?$~D',$path)?$value:'';
        if(in_array($host,['www.google.com','google.com','www.google.com.tr','google.com.tr'],true))return preg_match('~^/maps(?:/|$)~',$path)?$value:'';
        if(in_array($host,['maps.google.com','maps.google.com.tr'],true))return $path==='/'||preg_match('~^/maps(?:/|$)~',$path)?$value:'';
    }
    if($provider==='yandex'&&in_array($host,['yandex.com','yandex.com.tr','yandex.ru','yandex.eu','www.yandex.com','www.yandex.com.tr','www.yandex.ru'],true)){
        if($embed)return preg_match('~^/map-widget/v1/?$~D',$path)&&isset($url['query'])?$value:'';
        return preg_match('~^/maps(?:/|$)~',$path)?$value:'';
    }
    return '';
}
function st_business_maps(?string $directory=null): array {
    $empty=['google'=>['url'=>'','embed_url'=>''],'yandex'=>['url'=>'','embed_url'=>'']];
    $directory=$directory??st_business_private_directory();
    $file=$directory.'/haritalar.json';
    if(!is_file($file))$file=$directory.'/maps.json';
    $size=is_file($file)?@filesize($file):false;
    if($size===false||$size>16384)return ['ok'=>true,'configured'=>false,'maps'=>$empty];
    $raw=@file_get_contents($file);
    $data=is_string($raw)?json_decode($raw,true):null;
    if(!is_array($data))return ['ok'=>true,'configured'=>false,'maps'=>$empty];
    foreach(['google','yandex'] as $provider){
        $empty[$provider]['url']=st_business_map_url($data[$provider.'_url']??'',$provider);
        // An embed is usable only alongside an independently validated share link.
        if($empty[$provider]['url']!=='')$empty[$provider]['embed_url']=st_business_map_url($data[$provider.'_embed_url']??'',$provider,true);
    }
    return ['ok'=>true,'configured'=>$empty['google']['url']!==''||$empty['yandex']['url']!=='','maps'=>$empty];
}
