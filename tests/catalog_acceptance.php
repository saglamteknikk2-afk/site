<?php
declare(strict_types=1);
// Exhaustive registered-row server runtime audit. No dispatcher, credentials or network.
$site=realpath($argv[1]??dirname(__DIR__).'/build/production');
if($site===false)throw new RuntimeException('Production build missing');
require $site.'/fault-catalog.php';
$result=[];
foreach(st_fault_data()['models'] as $m)foreach($m['codes'] as $c)foreach(array_merge([$c['code']],$c['equivalent_codes']) as $code){
 $input=['device'=>$m['device'],'brand'=>$m['brand'],'model_id'=>$m['id'],'code'=>$code];$found=st_fault_lookup($input);$answer=st_fault_response($input);
 $result[]=['model_id'=>$m['id'],'input'=>$code,'status'=>$found['status'],'code'=>$found['code'],'meaning'=>$found['definition']['meaning']??null,'source'=>$answer['source']??null,'source_url'=>$answer['source_url']??null,'text'=>$answer['text']??null];
}
$scope=[];
foreach(st_fault_data()['models'] as $m){
 $code='E99';foreach($m['codes'] as $c)if(($c['matchable']??true)!==false&&empty($c['source_conflict'])){$code=$c['code'];break;}
 foreach([
  ['missing-model',['device'=>$m['device'],'brand'=>$m['brand'],'code'=>$code]],
  ['wrong-brand',['device'=>$m['device'],'brand'=>'__unsupported_brand__','model_id'=>$m['id'],'code'=>$code]],
  ['wrong-device',['device'=>$m['device']==='klima'?'kombi':'klima','brand'=>$m['brand'],'model_id'=>$m['id'],'code'=>$code]],
 ] as [$kind,$input]){$r=st_fault_lookup($input);$scope[]=['model_id'=>$m['id'],'kind'=>$kind,'status'=>$r['status'],'verified'=>$r['verified'],'meaning'=>$r['definition']['meaning']??null];}
}
echo json_encode(['rows'=>$result,'scope'=>$scope],JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR)."\n";
