<?php
declare(strict_types=1);
/** Pure lookup regression suite. Synthetic public records; no API, secrets or network.
 * php tests/fault-catalog.php [--parity]
 * --parity returns public fixtures/vectors for the JavaScript implementation.
 */
$root=dirname(__DIR__);
$data=json_decode(file_get_contents($root.'/overrides/assets/verified-faults.json'),true,512,JSON_THROW_ON_ERROR);
$row=static function(string $code,string $meaning,array $extra=[]):array{return array_replace(['code'=>$code,'meaning'=>$meaning,'equivalent_codes'=>[],'source_locator'=>'Synthetic QA table, row '.$code,'safe_observation'=>'Ekrandaki kodun tam yazımını kaydedin.','anchor'=>'kod-'.strtolower(preg_replace('/[^A-Z0-9]/','',$code))],$extra);};
$model=static function(string $id,string $name,array $codes,array $extra=[]):array{return array_replace(['id'=>$id,'device'=>'kombi','brand'=>'QA Fixture','label'=>$name,'model_names'=>[$name],'aliases'=>[],'manual'=>['url'=>'https://manufacturer.invalid/qa.pdf','title'=>'Synthetic QA only','locator'=>'Synthetic table','official'=>false],'path'=>'/'.$id.'.html','codes'=>$codes],$extra);};
$scope=$model('qa-scope','QA Scope Boiler 24',[
 $row('E01','First scoped meaning'),$row('F04','Second scoped meaning'),$row('E10','Unrelated tenth code'),
 $row('H.01.00','Multipart meaning'),$row('6A227','Combined code meaning'),$row('101','Numeric meaning'),
 $row('M03','Documented alias meaning',['equivalent_codes'=>['M3']]),
 $row('E02','Excluded row',['matchable'=>false,'equivalent_codes'=>['E2']]),
 $row('F12','Conflicted source',['source_conflict'=>true]),
],['requires_scope_confirmation'=>true,'market'=>'UK']);
$split=$model('qa-split','QA Split Boiler 30',[$row('E1','Exact E1 meaning'),$row('E01','Different exact E01 meaning')]);
$collision=$model('qa-collision','QA Collision Boiler',[$row('F.04','First exact meaning'),$row('F04','Conflicting exact meaning')]);
$document=$model('qa-document','9000 BTU/H QA Document',[$row('E01','Document-family meaning')],['device'=>'klima','matchable'=>false,'requires_document_match'=>true,'market'=>'TR']);
$other=$model('qa-other','QA Other Boiler',[$row('E99','Other brand only'),$row('E1','Other brand meaning')],['brand'=>'Other QA']);
$data['models']=array_merge($data['models'],[$scope,$split,$collision,$document,$other]);
$vectors=[
 ['name'=>'Unpadded E1 uses only the selected model E01 row','input'=>['model_id'=>'qa-scope','code'=>'E1'],'status'=>'verified','code'=>'E01','match'=>'flexible','meaning'=>'First scoped meaning'],
 ['name'=>'Padded E01 keeps exact priority','input'=>['model_id'=>'qa-scope','code'=>'E01'],'status'=>'verified','code'=>'E01','match'=>'exact'],
 ['name'=>'Unpadded F4 resolves F04 inside one model','input'=>['model_id'=>'qa-scope','code'=>'F4'],'status'=>'verified','code'=>'F04','match'=>'flexible'],
 ['name'=>'E10 is not E1','input'=>['model_id'=>'qa-scope','code'=>'E10'],'status'=>'verified','code'=>'E10','meaning'=>'Unrelated tenth code'],
 ['name'=>'Explicit E1 wins over differently defined E01','input'=>['model_id'=>'qa-split','code'=>'E1'],'status'=>'verified','code'=>'E1','match'=>'exact','meaning'=>'Exact E1 meaning'],
 ['name'=>'Explicit E01 retains its different definition','input'=>['model_id'=>'qa-split','code'=>'E01'],'status'=>'verified','code'=>'E01','match'=>'exact','meaning'=>'Different exact E01 meaning'],
 ['name'=>'Ambiguous zero fallback never picks the first meaning','input'=>['model_id'=>'qa-split','code'=>'E001'],'status'=>'ambiguous-code','code'=>'E001','match'=>'flexible'],
 ['name'=>'Punctuation collision has no selected definition','input'=>['model_id'=>'qa-collision','code'=>'F04'],'status'=>'source-conflict','code'=>'F04','match'=>'exact'],
 ['name'=>'Source conflict remains blocked','input'=>['model_id'=>'qa-scope','code'=>'F12'],'status'=>'source-conflict','code'=>'F12','match'=>'exact'],
 ['name'=>'Explicitly selected document family needs no checkbox','input'=>['device'=>'klima','model_id'=>'qa-document','code'=>'E1','scope_confirmed'=>false],'status'=>'verified','code'=>'E01','match'=>'flexible','warning'=>true],
 ['name'=>'Document family cannot be inferred from capacity','input'=>['device'=>'klima','query'=>'9000 BTU/H QA Document hata kodu E1'],'status'=>'needs-model','code'=>'E1'],
 ['name'=>'No model means no definition','input'=>['brand'=>'QA Fixture','code'=>'E1'],'status'=>'needs-model','code'=>'E1'],
 ['name'=>'Invalid explicit model never infers another model','input'=>['model_id'=>'not-a-model','query'=>'QA Scope Boiler 24 hata kodu E1'],'status'=>'needs-model','code'=>'E1','no_candidates'=>true],
 ['name'=>'Wrong device selection never leaks another model','input'=>['device'=>'klima','model_id'=>'qa-scope','query'=>'QA Scope Boiler 24 hata kodu E1'],'status'=>'needs-model','code'=>'E1','no_candidates'=>true],
 ['name'=>'Wrong brand selection never leaks another model','input'=>['brand'=>'Other QA','model_id'=>'qa-scope','query'=>'QA Scope Boiler 24 hata kodu E1'],'status'=>'needs-model','code'=>'E1','no_candidates'=>true],
 ['name'=>'A different brand cannot supply the missing code','input'=>['model_id'=>'qa-scope','code'=>'E99'],'status'=>'code-not-covered','code'=>'E99'],
 ['name'=>'Excluded canonical code cannot verify','input'=>['model_id'=>'qa-scope','code'=>'E02'],'status'=>'code-not-covered','code'=>'E02'],
 ['name'=>'Excluded flexible alias cannot verify','input'=>['model_id'=>'qa-scope','code'=>'E2'],'status'=>'code-not-covered','code'=>'E2'],
 ['name'=>'Documented alias has exact priority','input'=>['model_id'=>'qa-scope','query'=>'hata kodu M3'],'status'=>'verified','code'=>'M03','match'=>'exact'],
 ['name'=>'Multipart code retains every zero','input'=>['model_id'=>'qa-scope','query'=>'hata kodu H.01.00'],'status'=>'verified','code'=>'H.01.00','match'=>'exact'],
 ['name'=>'Multipart group zeros are not stripped','input'=>['model_id'=>'qa-scope','code'=>'H.1.0'],'status'=>'code-not-covered','code'=>'H.1.0'],
 ['name'=>'Combined code is preserved','input'=>['model_id'=>'qa-scope','query'=>'hata kodu 6A 227'],'status'=>'verified','code'=>'6A227'],
 ['name'=>'Numeric code requires explicit context','input'=>['model_id'=>'qa-scope','query'=>'hata kodu 101'],'status'=>'verified','code'=>'101'],
 ['name'=>'A bare temperature is not a numeric code','input'=>['model_id'=>'qa-scope','query'=>'Sıcaklık 101 derece'],'status'=>'model-known','code'=>''],
 ['name'=>'Selected scope warning is present without a code','input'=>['model_id'=>'qa-scope'],'status'=>'model-known','code'=>'','warning'=>true],
 ['name'=>'Query flex extraction preserves ambiguity','input'=>['model_id'=>'qa-split','query'=>'hata kodu E001'],'status'=>'ambiguous-code','code'=>'E001','match'=>'flexible'],
 ['name'=>'Exact complete model can still be recognized','input'=>['brand'=>'QA Fixture','query'=>'QA Scope Boiler 24 hata kodu E1'],'status'=>'verified','code'=>'E01','match'=>'flexible'],
];
$directory=sys_get_temp_dir().'/st-fault-qa-'.bin2hex(random_bytes(6));
mkdir($directory,0700);mkdir($directory.'/assets',0700);
try{
 copy($root.'/server/fault-catalog.php',$directory.'/fault-catalog.php');
 copy($root.'/server/fault-advisories.php',$directory.'/fault-advisories.php');
 file_put_contents($directory.'/assets/verified-faults.json',json_encode($data,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR));
 require $directory.'/fault-catalog.php';require $directory.'/fault-advisories.php';
 $checks=0;$assert=static function(bool $condition,string $name)use(&$checks):void{$checks++;if(!$condition)throw new RuntimeException($name);};
 foreach($vectors as $vector){
  $found=st_fault_lookup($vector['input']);$name=$vector['name'];
  $assert($found['status']===$vector['status'],$name.' status: '.$found['status']);
  $assert($found['code']===$vector['code'],$name.' code: '.$found['code']);
  $assert($found['verified']===($vector['status']==='verified'),$name.' verification');
  if(isset($vector['match']))$assert($found['code_match']===$vector['match'],$name.' match type');
  if(isset($vector['meaning']))$assert(($found['definition']['meaning']??'')===$vector['meaning'],$name.' selected meaning');
  if(!empty($vector['warning']))$assert($found['scope_warning']!=='',$name.' scope provenance');
  if(!empty($vector['no_candidates']))$assert($found['candidate_models']===[],$name.' no fallback candidates');
  if(!$found['verified'])$assert($found['definition']===null,$name.' no unverified definition');
 }
 $verified=st_fault_response(['model_id'=>'qa-scope','code'=>'E1','scope_confirmed'=>false]);
 $assert($verified['source']==='manual'&&$verified['code_definition_verified']===true,'Selected foreign manual is usable without confirmation');
 $assert($verified['scope_warning']!==''&&strpos($verified['text'],$verified['scope_warning'])!==false,'Country warning remains visible in the response');
 $assert($verified['source_url']===$scope['manual']['url']&&$verified['source_locator']===$scope['codes'][0]['source_locator'],'Every selected meaning retains its source locator');
 foreach(['qa-split'=>'E001','qa-collision'=>'F04','qa-scope'=>'F12'] as $id=>$code){$answer=st_fault_response(['model_id'=>$id,'code'=>$code]);$assert($answer['source']==='guide'&&($answer['requires_document_review']??false)===true&&empty($answer['code_definition_verified']),'Conflicting rows require document review: '.$id);}
 $missing=st_fault_response(['code'=>'E99']);
 $assert($missing['requires_model']===true&&empty($missing['code_definition_verified'])&&strpos($missing['text'],'E1/E01')===false,'Missing model asks for model without unrelated code examples');
 $unknown=st_fault_response(['code'=>'E99','model_unknown'=>true]);
 $assert($unknown['requires_model']===false&&$unknown['source']==='guide','Explicit unknown model can finish safely');
 $uncovered=st_fault_response(['model_id'=>'qa-scope','code'=>'E99']);
 $assert($uncovered['requires_document_review']===true&&$uncovered['requires_model']===false&&empty($uncovered['code_definition_verified']),'Uncovered selected-model code requires document review');
 $assert(st_fault_flex_key('E01')===st_fault_flex_key('E1')&&st_fault_key('E01')!==st_fault_key('E1'),'Exact key stays distinct while flex normalizes zero padding');
 $assert(st_fault_flex_key('E10')!==st_fault_flex_key('E1')&&st_fault_flex_key('H.01.00')!==st_fault_flex_key('H.1.0'),'Unrelated and multipart codes remain separate');
 $assert(st_fault_advisory('Baymak Güneş Premix 35 kW')===null,'Recall advisory cannot cross Baykan/Baymak brands');
 if(in_array('--parity',$argv,true))echo json_encode(['data'=>$data,'vectors'=>$vectors,'results'=>array_map(static function($vector){return st_fault_lookup($vector['input']);},$vectors)],JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR)."\n";
 else echo json_encode(['passed'=>true,'checks'=>$checks,'vectors'=>count($vectors),'network_requests'=>0,'private_config_read'=>false],JSON_UNESCAPED_SLASHES)."\n";
}finally{
 @unlink($directory.'/assets/verified-faults.json');@rmdir($directory.'/assets');
 @unlink($directory.'/fault-catalog.php');@unlink($directory.'/fault-advisories.php');@rmdir($directory);
}
