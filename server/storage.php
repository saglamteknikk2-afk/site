<?php
declare(strict_types=1);

// Resolve existing storage before PDO can silently create a second empty file.
// No customer row or credential is returned by these diagnostics.
function st_storage_safe_path(string $path,string $webroot,bool $existing=false): string {
    if($path===''||strlen($path)>4096||strpos($path,"\0")!==false||!preg_match('~^(?:/|[A-Za-z]:[\\\\/])~',$path))throw new RuntimeException('Veritabanı yolu mutlak bir dosya yolu olmalıdır.');
    $root=realpath($webroot);if(!$root)throw new RuntimeException('Yayın kökü doğrulanamadı.');
    $resolved=realpath($path);
    if($resolved===false){
        if($existing)throw new RuntimeException('Seçilen mevcut veritabanı bulunamadı; boş dosya oluşturulmadı.');
        $parent=realpath(dirname($path));
        if(!$parent)throw new RuntimeException('Veritabanı klasörü bulunamadı.');
        $resolved=$parent.DIRECTORY_SEPARATOR.basename($path);
    }
    if(st_business_inside($resolved,$root))throw new RuntimeException('Veritabanı web kökünün dışında olmalıdır.');
    if(file_exists($resolved)&&!is_file($resolved))throw new RuntimeException('Veritabanı yolu normal bir dosya olmalıdır.');
    return $resolved;
}
function st_storage_candidates(string $private,string $webroot): array {
    $paths=[$private.'/site.sqlite'];
    if(basename($private)==='saglam-teknik')$paths[]=dirname($private).'/site.sqlite';
    else $paths[]=$private.'/saglam-teknik/site.sqlite';
    $domain=dirname($webroot);
    $paths[]=$domain.'/private/saglam-teknik/site.sqlite';
    $paths[]=$domain.'/private/site.sqlite';
    $found=[];$identities=[];
    foreach(array_unique($paths) as $path){
        if(!file_exists($path)&&!is_link($path))continue;
        $safe=st_storage_safe_path($path,$webroot,true);
        $stat=stat($safe);$identity=$stat!==false?$stat['dev'].':'.$stat['ino']:$safe;
        if(isset($identities[$identity]))continue;
        $identities[$identity]=true;$found[]=$safe;
    }
    return $found;
}
function st_storage_inspect(string $path): array {
    if(!is_file($path)||!is_readable($path))throw new RuntimeException('Mevcut veritabanı okunamıyor; yeni dosya oluşturulmadı.');
    $handle=fopen($path,'rb');
    if(!$handle)throw new RuntimeException('Mevcut veritabanı okunamıyor.');
    try{$header=fread($handle,16);}finally{fclose($handle);}
    if($header!=="SQLite format 3\0")throw new RuntimeException('Mevcut veritabanı SQLite biçiminde değil; dosya değiştirilmedi.');
    $base=['path'=>$path,'bytes'=>filesize($path),'readable'=>true,'writable'=>is_writable($path),'wal_present'=>is_file($path.'-wal'),'counts'=>[]];
    // A read-only SQLite connection can still create/update a WAL shm file.
    // Diagnostics never open an active WAL database; the actual API connection
    // reads the complete WAL after the owner has selected this existing file.
    if($base['wal_present'])return $base+['inspection'=>'SQLite başlığı doğrulandı; aktif WAL nedeniyle satır sayısı okunmadı.'];
    $options=[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC,PDO::SQLITE_ATTR_OPEN_FLAGS=>PDO::SQLITE_OPEN_READONLY];
    $uri='file:'.str_replace(['%','?','#'],['%25','%3F','%23'],$path).'?mode=ro&immutable=1';
    $db=new PDO('sqlite:'.$uri,null,null,$options);$db->exec('PRAGMA query_only=ON;');
    $tables=array_column($db->query("SELECT name FROM sqlite_master WHERE type='table'")->fetchAll(),'name');
    $counts=[];
    foreach(['reviews','tickets','outbox'] as $table)if(in_array($table,$tables,true))$counts[$table]=(int)$db->query('SELECT COUNT(*) FROM '.$table)->fetchColumn();
    if(in_array('reviews',$tables,true)){
        $columns=array_column($db->query('PRAGMA table_info(reviews)')->fetchAll(),'name');
        foreach(['id','author','comment','status','created'] as $required)if(!in_array($required,$columns,true))throw new RuntimeException('Mevcut yorum şeması farklı; yedekli aktarım gerekir, dosya değiştirilmedi.');
        $counts['approved_reviews']=(int)$db->query("SELECT COUNT(*) FROM reviews WHERE status='approved'")->fetchColumn();
    }
    if(!$tables)throw new RuntimeException('Mevcut SQLite dosyasında site tablosu yok; doğru dosyayı açıkça seçin.');
    if(!array_intersect(['reviews','tickets','outbox','meta'],$tables))throw new RuntimeException('Seçilen SQLite dosyası tanınan site veritabanı değil.');
    $base['counts']=$counts;return $base+['inspection'=>'Salt okunur ana dosya şeması ve sayımları doğrulandı.'];
}
function st_storage_database_path(string $private,string $webroot,?string $configured=null): string {
    $explicit=getenv('SAGLAM_DATABASE_PATH');
    if($explicit===false||trim($explicit)==='')$explicit=$configured;
    if(is_string($explicit)&&trim($explicit)!==''){
        $selected=st_storage_safe_path(trim($explicit),$webroot,true);st_storage_inspect($selected);return $selected;
    }
    $candidates=st_storage_candidates($private,$webroot);
    if(count($candidates)>1)throw new RuntimeException('Birden fazla site.sqlite bulundu. DATABASE_PATH ile mevcut doğru dosyayı seçin; dosyalar birleştirilmedi veya sıfırlanmadı.');
    if($candidates){st_storage_inspect($candidates[0]);return $candidates[0];}
    return st_storage_safe_path($private.'/site.sqlite',$webroot);
}
function st_storage_diagnostics(string $private,string $webroot,?string $configured=null): array {
    $result=['ok'=>false,'selected_path'=>'','selected_existing'=>false,'candidates'=>[],'error'=>''];
    try{
        foreach(st_storage_candidates($private,$webroot) as $path){
            try{$result['candidates'][]=st_storage_inspect($path);}catch(Throwable $e){$result['candidates'][]=['path'=>$path,'error'=>$e->getMessage()];}
        }
        $selected=st_storage_database_path($private,$webroot,$configured);
        $result['selected_path']=$selected;$result['selected_existing']=is_file($selected);$result['ok']=true;
    }catch(Throwable $e){$result['error']=$e->getMessage();}
    return $result;
}
function st_storage_backup(PDO $db,string $directory): string {
    if($db->inTransaction())throw new RuntimeException('Veritabanı işlemi sürerken yedek alınamaz.');
    $webroot=st_business_webroot();
    if(is_link($directory))throw new RuntimeException('Yedek klasörü sembolik bağlantı olamaz.');
    $parent=realpath(dirname($directory));
    if(!$parent||st_business_inside($parent.DIRECTORY_SEPARATOR.basename($directory),$webroot))throw new RuntimeException('Yedek klasörü mevcut özel dizinin altında ve web kökünün dışında olmalıdır.');
    if(!is_dir($directory)&&!mkdir($directory,0700)&&!is_dir($directory))throw new RuntimeException('Yedek klasörü oluşturulamadı.');
    $real=realpath($directory);if(!$real||st_business_inside($real,$webroot))throw new RuntimeException('Yedek klasörü web kökünün dışında olmalıdır.');
    if(!chmod($real,0700))throw new RuntimeException('Yedek klasörü izinleri ayarlanamadı.');
    $path=$real.'/site-'.date('Ymd-His').'-'.bin2hex(random_bytes(6)).'.sqlite';
    if(file_exists($path))throw new RuntimeException('Yedek hedefi zaten var; üzerine yazılmadı.');
    try{
        $db->exec('VACUUM INTO '.$db->quote($path));
        if(!chmod($path,0600))throw new RuntimeException('Yedek dosyası izinleri ayarlanamadı.');
        st_storage_inspect($path);
    }catch(Throwable $e){if(is_file($path))unlink($path);throw $e;}
    return $path;
}
