<?php
declare(strict_types=1);
// Evaluate only the named pure helpers, never the application dispatcher/config.
$root=realpath($argv[1]??'');if(!$root)throw new RuntimeException('Usage: php test_matching.php <webroot> [js-report.json]');
$api=file_get_contents($root.'/api.php');
$wanted=['st_normalize','st_contains','st_best_match','st_resolve_query','st_guide','st_ai'];
$tokens=token_get_all($api);$functions=[];
for($i=0;$i<count($tokens);$i++){
    if(!is_array($tokens[$i])||$tokens[$i][0]!==T_FUNCTION)continue;
    $j=$i+1;while(isset($tokens[$j])&&is_array($tokens[$j])&&$tokens[$j][0]===T_WHITESPACE)$j++;
    if(!isset($tokens[$j])||!is_array($tokens[$j])||$tokens[$j][0]!==T_STRING)continue;
    $name=$tokens[$j][1];if(!in_array($name,$wanted,true))continue;
    $code='';$depth=0;$opened=false;
    for($k=$i;$k<count($tokens);$k++){
        $token=$tokens[$k];$text=is_array($token)?$token[1]:$token;
        if(is_array($token)&&$token[0]===T_DIR)$text=var_export($root,true);
        $code.=$text;
        if($token==='{'){$depth++;$opened=true;}elseif($token==='}'&&$opened&&--$depth===0)break;
    }
    $functions[$name]=$code;
}
foreach($wanted as $name){if(!isset($functions[$name]))throw new RuntimeException('Missing pure helper '.$name);eval($functions[$name]);}
require $root.'/fault-catalog.php';
function st_text(array $a,string $k,int $min,int $max):string{$v=(string)($a[$k]??'');if(strlen($v)<$min||strlen($v)>$max)throw new RuntimeException('Invalid test input');return $v;}
function st_fault_advisory(string $issue){throw new RuntimeException('Safety must return before any later provider/manual path');}
function ensure(bool $value,string $message):void{if(!$value)throw new RuntimeException($message);}
$catalog=json_decode(file_get_contents($root.'/assets/servis-katalog.json'),true,512,JSON_THROW_ON_ERROR);
$vectors=[
 ['Küçükçekmece Baymak kombi servisi','kucukcekmece-kombi-servisi.html'],
 ['Avcılar Bosch kombi vermiyor sıcak su','kombi-sicak-su.html'],
 ['Baymak kombi altından su geliyor','kombi-su-akitiyor.html'],
 ['Şişli Vaillant kombi ateşleme arızası','kombi-atesleme.html'],
 ['Küçükçekmece petek temizliği','petek-temizligi.html'],
 ['Vaillant ecoTEC pro VUW TR 236/5-3 F22 hata kodu','vaillant-kombi-ecotec-pro-236-286-5-3-ariza-kodlari.html#kod-f22'],
 ['Baymak Duotec 33 E1 hata kodu','baymak-kombi-duotec-33-42-45-ariza-kodlari.html#kod-e01'],
];
foreach($vectors as [$query,$expected])ensure(st_resolve_query($query,'',$catalog)['path']===$expected,$query);
foreach(['Maltepe kombi servisi','Kadıköy İstanbul kombi'] as $query){$r=st_resolve_query($query,'',$catalog);ensure($r['district']===''&&$r['neighborhood']===''&&$r['ambiguous_neighborhood'],$query);}
ensure(st_resolve_query('ECA E99 kombi','',$catalog)['code_definition_verified']===false,'Unknown model E99 must remain unverified');
$f4model=null;foreach(st_fault_data()['models'] as $model)foreach($model['codes'] as $row)if(in_array($row['code'],['F4','F04','F.04'],true)&&empty($row['source_conflict'])&&($row['matchable']??true)!==false){$f4model=$model;break 2;}
ensure($f4model!==null,'F4 source fixture exists');$f4=st_fault_lookup(['device'=>$f4model['device'],'brand'=>$f4model['brand'],'model_id'=>$f4model['id'],'code'=>'F4']);$f04=st_fault_lookup(['device'=>$f4model['device'],'brand'=>$f4model['brand'],'model_id'=>$f4model['id'],'code'=>'F04']);ensure($f4['verified']&&$f04['verified']&&$f4['definition']['meaning']===$f04['definition']['meaning'],'F4/F04 only within selected model');
$safety=st_ai(['device'=>'Kombi','issue'=>'kombi yanarken patlama yaparak yanıyor']);ensure($safety['source']==='safety','Ignition safety must precede providers');ensure(strpos($safety['text'],'resetlemeyin')!==false,'No repeated reset advice');
ensure(st_ai(['device'=>'Kombi','issue'=>'Baymak Duotec 33 E01 ve ilk yanışta patlama','model_id'=>'baymak-kombi-duotec-33-42-45','code'=>'E01'])['source']==='safety','Safety precedes even verified model/code output');
ensure(st_guide('Kombi','gaz kokusu geliyor')['emergency_phone']==='187','Gas emergency');
ensure(st_guide('Kombi','duman çıkıyor')['emergency_phone']==='112','Fire emergency');
$parity=0;
if(isset($argv[2]))foreach(json_decode(file_get_contents($argv[2]),true)['results'] as $row){
    $php=st_resolve_query($row['query'],'',$catalog);
    foreach(['path','district','neighborhood','brand','ambiguous_neighborhood'] as $key)ensure($php[$key]===$row[$key],'JS/PHP parity '.$key.' '.$row['query']);
    ensure($php['code_definition_verified']===$row['verified'],'Verified scope parity');$parity++;
}
echo json_encode(['status'=>'passed','php_vectors'=>count($vectors),'js_php_parity_queries'=>$parity,'safety'=>'No network/config executed'],JSON_UNESCAPED_UNICODE)."\n";
