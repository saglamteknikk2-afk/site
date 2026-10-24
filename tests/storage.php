<?php
declare(strict_types=1);
// Isolated synthetic SQLite fixtures; never touches the production private tree.
require dirname(__DIR__).'/server/business-config.php';
require dirname(__DIR__).'/server/storage.php';
$base=sys_get_temp_dir().'/st-storage-'.bin2hex(random_bytes(7));
mkdir($base,0700);mkdir($base.'/httpdocs',0700);mkdir($base.'/private',0700);mkdir($base.'/private/saglam-teknik',0700);
$root=$base.'/httpdocs';$private=$base.'/private/saglam-teknik';$checks=[];
$check=static function(bool $ok,string $name)use(&$checks):void{$checks[]=['name'=>$name,'passed'=>$ok];if(!$ok)throw new RuntimeException($name);};
$reject=static function(callable $operation,string $name)use($check):void{$caught=false;try{$operation();}catch(RuntimeException $e){$caught=true;}$check($caught,$name);};
$remove=function(string $path)use(&$remove):void{if(is_link($path)||!is_dir($path)){if(file_exists($path)||is_link($path))unlink($path);return;}foreach(scandir($path) as $name)if($name!=='.'&&$name!=='..')$remove($path.'/'.$name);rmdir($path);};
$fixture=static function(string $file,string $comment='SYNTHETIC_STORAGE_REVIEW'):void{
    $db=new PDO('sqlite:'.$file);$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);
    $db->exec("CREATE TABLE reviews(id TEXT PRIMARY KEY,author TEXT,comment TEXT,status TEXT,created INTEGER); CREATE TABLE tickets(id TEXT PRIMARY KEY,name TEXT); CREATE TABLE meta(k TEXT PRIMARY KEY,v TEXT);");
    $q=$db->prepare('INSERT INTO reviews VALUES(?,?,?,?,?)');$q->execute(['synthetic','Unit Test',$comment,'approved',1700000000]);
    $db->exec("INSERT INTO tickets VALUES('ticket','Synthetic customer')");
};
try{
    putenv('SAGLAM_DATABASE_PATH');
    $canonical=$private.'/site.sqlite';$legacy=$base.'/private/site.sqlite';
    $check(st_storage_database_path($private,$root)===$canonical&&!file_exists($canonical),'Fresh resolution returns only canonical path without creating any database');
    $diagnostic=st_storage_diagnostics($private,$root);$check($diagnostic['ok']&&!$diagnostic['selected_existing']&&!file_exists($canonical),'Fresh diagnostics are read-only');
    $fixture($legacy);$original=hash_file('sha256',$legacy);
    $check(st_storage_database_path($private,$root)===$legacy,'One existing legacy private/site.sqlite is reused');
    $check(!file_exists($canonical),'Legacy reuse does not silently create a new empty canonical file');
    $diagnostic=st_storage_diagnostics($private,$root);
    $check($diagnostic['ok']&&$diagnostic['selected_existing']&&$diagnostic['candidates'][0]['counts']['approved_reviews']===1,'Read-only diagnostics report the existing approved count');
    $check(strpos(json_encode($diagnostic),'SYNTHETIC_STORAGE_REVIEW')===false&&strpos(json_encode($diagnostic),'Synthetic customer')===false,'Diagnostics disclose no review or customer field contents');
    $check(hash_file('sha256',$legacy)===$original&&!file_exists($legacy.'-wal')&&!file_exists($legacy.'-shm'),'Read-only diagnostics do not modify the main file or create WAL sidecars');
    $fixture($canonical,'SYNTHETIC_SECOND_DB');$canonicalHash=hash_file('sha256',$canonical);
    $reject(static function()use($private,$root){st_storage_database_path($private,$root);},'Multiple distinct existing databases require explicit owner selection');
    $diagnostic=st_storage_diagnostics($private,$root);
    $check(!$diagnostic['ok']&&count($diagnostic['candidates'])===2&&$diagnostic['error']!=='','Ambiguous diagnostics return a safe actionable failure');
    $check(hash_file('sha256',$legacy)===$original&&hash_file('sha256',$canonical)===$canonicalHash,'Ambiguous detection never merges, truncates, or overwrites either database');
    $check(st_storage_database_path($private,$root,$legacy)===$legacy,'DATABASE_PATH chooses the explicit existing legacy file');
    putenv('SAGLAM_DATABASE_PATH='.$canonical);
    $check(st_storage_database_path($private,$root,$legacy)===$canonical,'Plesk environment override takes precedence over TXT configuration');
    putenv('SAGLAM_DATABASE_PATH');
    $missing=$private.'/does-not-exist.sqlite';
    $reject(static function()use($private,$root,$missing){st_storage_database_path($private,$root,$missing);},'A mistyped explicit path fails before SQLite can create an empty replacement');
    $check(!file_exists($missing),'Mistyped explicit database remains absent');
    $reject(static function()use($private,$root){st_storage_database_path($private,$root,'relative/site.sqlite');},'Relative explicit database paths are rejected');
    $fixture($root.'/site.sqlite');
    $reject(static function()use($private,$root){st_storage_database_path($private,$root,$root.'/site.sqlite');},'Database inside public webroot is rejected');
    if(function_exists('symlink')&&symlink($root.'/site.sqlite',$private.'/public-link.sqlite')){
        $reject(static function()use($private,$root){st_storage_database_path($private,$root,$private.'/public-link.sqlite');},'Symlink into public webroot is rejected');
    }
    unlink($canonical);
    if(function_exists('symlink')&&symlink($legacy,$canonical)){
        $check(st_storage_database_path($private,$root)===realpath($legacy),'Symlink aliases of the same database are deduplicated');unlink($canonical);
    }
    $corrupt=$private.'/corrupt.sqlite';file_put_contents($corrupt,'SYNTHETIC-NOT-SQLITE');$corruptHash=hash_file('sha256',$corrupt);
    $reject(static function()use($private,$root,$corrupt){st_storage_database_path($private,$root,$corrupt);},'Non-SQLite explicit file is rejected');
    $check(hash_file('sha256',$corrupt)===$corruptHash,'Corrupt file is not rewritten');
    $unknown=$private.'/unknown.sqlite';$db=new PDO('sqlite:'.$unknown);$db->exec('CREATE TABLE unrelated(x INTEGER)');$db=null;
    $reject(static function()use($private,$root,$unknown){st_storage_database_path($private,$root,$unknown);},'Unrelated SQLite schema is not silently initialized as an empty site database');
    // Active WAL data is inspected through the real writer connection only.
    // Path diagnostics must not open it and create an SHM file.
    $db=new PDO('sqlite:'.$legacy);$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);$db->exec('PRAGMA journal_mode=WAL; PRAGMA wal_autocheckpoint=0;');
    $q=$db->prepare('INSERT INTO reviews VALUES(?,?,?,?,?)');$q->execute(['wal-review','Unit WAL','SYNTHETIC_WAL_DATA','approved',1700000010]);
    $mainBefore=hash_file('sha256',$legacy);$walBefore=hash_file('sha256',$legacy.'-wal');$shmPath=$legacy.'-shm';$shmBefore=is_file($shmPath)?hash_file('sha256',$shmPath):null;
    $info=st_storage_inspect($legacy);
    $check($info['wal_present']&&$info['counts']===[],'Active-WAL diagnostics explicitly avoid potentially stale row counts');
    $check(hash_file('sha256',$legacy)===$mainBefore&&hash_file('sha256',$legacy.'-wal')===$walBefore&&(!is_file($shmPath)||hash_file('sha256',$shmPath)===$shmBefore),'Active WAL diagnostics leave all SQLite file bytes untouched');
    $backup=st_storage_backup($db,$private.'/backups');
    $copy=new PDO('sqlite:'.$backup);$copy->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);
    $check((int)$copy->query('SELECT COUNT(*) FROM reviews')->fetchColumn()===2&&$copy->query("SELECT comment FROM reviews WHERE id='wal-review'")->fetchColumn()==='SYNTHETIC_WAL_DATA','Consistent backup includes recently written WAL rows');
    $check((fileperms($backup)&0777)===0600&&(fileperms(dirname($backup))&0777)===0700,'Backups and directory have private permissions');
    $again=st_storage_backup($db,$private.'/backups');
    $check($again!==$backup&&is_file($backup)&&is_file($again),'Repeated backups create unique files without overwriting the prior backup');
    $check((int)$db->query('SELECT COUNT(*) FROM reviews')->fetchColumn()===2,'Backup preserves the source rows');
    $copy=null;$db=null;
    $reject(static function()use($legacy){$db=new PDO('sqlite:'.$legacy);st_storage_backup($db,dirname(__DIR__).'/server/storage-forbidden-test');},'Public-root backup target is rejected before directory creation');
    $check(!is_dir(dirname(__DIR__).'/server/storage-forbidden-test'),'Rejected backup leaves public root unchanged');
    echo json_encode(['passed'=>true,'checks'=>count($checks),'cases'=>$checks,'production_private_read'=>false,'network_requests'=>0],JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES)."\n";
}finally{putenv('SAGLAM_DATABASE_PATH');$remove($base);}
