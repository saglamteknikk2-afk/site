<?php
declare(strict_types=1);
define('ST_DIAGNOSTIC_LIBRARY_MODE',true);
require __DIR__.'/../server/kurulum-kontrol.php';
$checks=0;
function installation_check(bool $value,string $name): void {global $checks;$checks++;if(!$value)throw new RuntimeException($name);}
function installation_files(string $root): array {
    $result=[];
    foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS)) as $file)if($file->isFile())$result[$file->getPathname()]=hash_file('sha256',$file->getPathname());
    ksort($result);return $result;
}
function installation_remove(string $path): void {
    if(is_dir($path)&&!is_link($path)){foreach(scandir($path) as $name)if($name!=='.'&&$name!=='..')installation_remove($path.'/'.$name);rmdir($path);}else unlink($path);
}
$base=sys_get_temp_dir().'/st-installation-'.bin2hex(random_bytes(8));
$root=$base.'/httpdocs';$private=$base.'/private/saglam-teknik';
mkdir($root.'/assets',0700,true);
$oldDatabase=getenv('SAGLAM_DATABASE_PATH');putenv('SAGLAM_DATABASE_PATH');
try{
    $script="console.log('installation fixture');\n";
    file_put_contents($root.'/assets/site.js',$script);
    $version=substr(hash('sha256',$script),0,10);
    file_put_contents($root.'/index.html','<!doctype html><script src="assets/site.js?v='.$version.'"></script>');
    file_put_contents($root.'/build-info.json',json_encode(['mode'=>'production','base_path'=>'/','content_sha256'=>str_repeat('a',64),'archive_sha256'=>str_repeat('b',64),'production_deployed'=>false]));
    $before=installation_files($base);$report=st_installation_diagnostics($root,$private);
    installation_check($report['read_only']&&$report['network_requests']===0&&!$report['database_created'],'Read-only/no-provider contract');
    installation_check(!is_dir($private),'Missing private directory must not be created');
    installation_check($before===installation_files($base),'Diagnostics must leave all file bytes unchanged');
    installation_check($report['asset_versions_match'],'Matching served asset hash is accepted');
    installation_check($report['build_info']['content_sha256']===str_repeat('a',64),'Published build identity is shown unchanged');
    installation_check($report['file_sha256']['assets/site.js']===hash('sha256',$script),'Actual asset fingerprint is independent of manifest declaration');
    installation_check(!$report['vhost_binding_verified'],'CLI must not claim Plesk vhost verification');
    installation_check($report['private_outside_webroot'],'External private path accepted');
    file_put_contents($root.'/assets/site.js',$script.'// stale-page/new-file mismatch');
    $mismatch=st_installation_diagnostics($root,$private);
    installation_check(!$mismatch['asset_versions_match']&&$mismatch['assets'][0]['version_matches']===false,'Mixed HTML/JS deployment is detected');
    mkdir($private,0700,true);
    $pdo=new PDO('sqlite:'.$private.'/site.sqlite');
    $pdo->exec("CREATE TABLE reviews(id TEXT PRIMARY KEY,author TEXT,comment TEXT,status TEXT,created INTEGER); INSERT INTO reviews VALUES('1','PRIVATE CUSTOMER FIXTURE','Private fixture comment','approved',1);");
    unset($pdo);
    file_put_contents($private.'/site_apileri,.txt',"TELEGRAM_BOT_TOKEN=PRIVATE_SECRET_SENTINEL\nDATABASE_PATH=\"".$private."/site.sqlite\"\n");
    $before=installation_files($base);$report=st_installation_diagnostics($root,$private);$encoded=json_encode($report);
    installation_check($before===installation_files($base),'Existing SQLite/config inspection leaves bytes unchanged');
    installation_check(!is_file($private.'/site.sqlite-wal')&&!is_file($private.'/site.sqlite-shm'),'Read-only inspection creates no SQLite sidecars');
    installation_check($report['storage']['ok']&&$report['storage']['selected_existing'],'Existing database selected without creating another');
    installation_check($report['storage']['candidates'][0]['counts']['approved_reviews']===1,'Only aggregate approved-review count is exposed');
    installation_check(strpos($encoded,'PRIVATE_SECRET_SENTINEL')===false,'Secret value absent from diagnostic output');
    installation_check(strpos($encoded,'PRIVATE CUSTOMER FIXTURE')===false&&strpos($encoded,'Private fixture comment')===false,'Customer content absent from diagnostic output');
    installation_check($report['configuration_files']['site_apileri,.txt']['exists'],'Existing primary config presence reported');
    $unsafe=st_installation_diagnostics($root,$root.'/private');
    installation_check(!$unsafe['private_outside_webroot']&&$unsafe['storage']['inspected']===false,'Public private directory is never inspected');
    symlink($private.'/site.sqlite',$root.'/assets/outside.js');
    file_put_contents($root.'/index.html','<script src="assets/outside.js?v=0000000000"></script>');
    $outside=st_installation_diagnostics($root,$private);
    installation_check(!$outside['assets'][0]['exists']&&$outside['assets'][0]['sha256']===null,'Symlink asset cannot expose private file fingerprint');
    echo json_encode(['passed'=>true,'checks'=>$checks,'network_requests'=>0,'private_customer_data_used'=>false])."\n";
}finally{
    if($oldDatabase===false)putenv('SAGLAM_DATABASE_PATH');else putenv('SAGLAM_DATABASE_PATH='.$oldDatabase);
    installation_remove($base);
}
