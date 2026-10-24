<?php
declare(strict_types=1);
// Pure model-scoped lookup. No dispatcher, credentials, network or notifications.
function st_fault_data(): array {
    static $data;
    if($data===null){$raw=@file_get_contents(__DIR__.'/assets/verified-faults.json');$parsed=is_string($raw)?json_decode($raw,true):null;$data=is_array($parsed)?$parsed:['models'=>[],'coverage'=>[]];}
    return $data;
}
function st_fault_key(string $value): string {return preg_replace('/[^A-Z0-9]/','',strtoupper($value));}
function st_fault_flex_key(string $value): string {return preg_replace('/^([A-Z]+)0+(\d+)$/','$1$2',st_fault_key($value));}
function st_fault_norm(string $value): string {
    $value=strtr($value,['ç'=>'c','ğ'=>'g','ı'=>'i','ö'=>'o','ş'=>'s','ü'=>'u','Ç'=>'C','Ğ'=>'G','İ'=>'I','Ö'=>'O','Ş'=>'S','Ü'=>'U']);
    return trim(preg_replace('/[^a-z0-9]+/',' ',strtolower($value)));
}
function st_fault_contains(string $query,string $term): bool {$q=st_fault_norm($query);$t=st_fault_norm($term);return $t!==''&&strpos(' '.$q.' ',' '.$t.' ')!==false;}
function st_fault_models(string $device,string $brand=''): array {return array_values(array_filter(st_fault_data()['models'],function($m)use($device,$brand){return $m['device']===$device&&($brand===''||st_fault_norm($m['brand'])===st_fault_norm($brand));}));}
function st_fault_infer(string $query,string $device,string $brand=''): ?array {
    $length=0;$candidates=[];
    foreach(array_filter(st_fault_models($device,$brand),function($m){return($m['matchable']??true)!==false;}) as $model)foreach(array_merge($model['model_names'],$model['aliases']??[],[$model['label']]) as $term){
        $n=st_fault_norm($term);if(strlen($n)<4||!st_fault_contains($query,$n))continue;
        if(strlen($n)>$length){$length=strlen($n);$candidates=[$model['id']=>$model];}
        elseif(strlen($n)===$length)$candidates[$model['id']]=$model;
    }
    return count($candidates)===1?array_values($candidates)[0]:null;
}
function st_fault_extract(string $query,?array $model=null): string {
    $text=$query;
    if($model){$names=array_merge($model['model_names'],$model['aliases']??[],[$model['label']]);usort($names,function($a,$b){return strlen($b)<=>strlen($a);});foreach($names as $name)$text=preg_replace('/'.preg_quote($name,'/').'/iu',' ',$text);}
    $explicit=[];preg_match('/\b(?:hata kodu|ariza kodu|ekrandaki kod|kod|kodu)\s+([a-z0-9]+(?:\s+[0-9]{1,3}){0,3})/',st_fault_norm($text),$explicit);
    $rows=array_values(array_filter($model['codes']??[],function($row){return($row['matchable']??true)!==false;}));
    if($explicit){
        $candidate=strtoupper($explicit[1]);$exact=$model?st_fault_matching_rows($model,$candidate):[];
        if($exact)return count($exact)===1?$exact[0]['code']:$candidate;
        if($model&&st_fault_matching_rows($model,$candidate,true))return $candidate;
        $first=explode(' ',$candidate)[0];
        if($model&&(st_fault_matching_rows($model,$first)||st_fault_matching_rows($model,$first,true)))return $first;
    }
    usort($rows,function($a,$b){return strlen(st_fault_key($b['code']))<=>strlen(st_fault_key($a['code']));});
    foreach($rows as $row){
        if(($row['matchable']??true)===false)continue;
        $key=st_fault_key($row['code']);if(ctype_digit($key)&&!$explicit)continue;
        $chars=str_split($key);$pattern=implode('[.\s-]*',array_map(function($c){return preg_quote($c,'/');},$chars));
        if(preg_match('/(^|[^A-Z0-9])'.$pattern.'(?=$|[^A-Z0-9])/i',$text))return $row['code'];
    }
    if(preg_match('/\b((?:CH|EA|EC|E|F|A|C|H|J|L|P|U)[.\s-]?[0-9]{1,3}(?:[.-][0-9]{1,3})*|EA|EC)\b/i',$text,$generic))return strtoupper(preg_replace('/\s/','',$generic[1]));
    return $explicit?strtoupper($explicit[1]):'';
}
function st_fault_scope_warning(?array $model): string {
    if(!$model||((empty($model['requires_scope_confirmation'])&&empty($model['requires_document_match']))&&($model['matchable']??true)!==false))return '';
    $market=(string)($model['market']??'');
    $foreign=$market!==''&&!preg_match('/(?:^|[^a-z])tr(?:[^a-z]|$)|turkiye|turkce/',st_fault_norm($market));
    return($market!==''?'Belge pazarı / bölgesi: '.$market.'. ':'').($foreign?'Bu pazar için yayımlanan belge Türkiye varyantı doğrulaması değildir. ':'').'Açıklama seçtiğiniz üretici belgesine aittir; ülke/ürün son eki, kontrol birimi veya belge sürümü farklıysa anlam değişebilir.';
}
function st_fault_matching_rows(array $model,string $code,bool $flexible=false): array {
    $rows=[];$key=$flexible?st_fault_flex_key($code):st_fault_key($code);
    if($key==='')return [];
    foreach($model['codes']??[] as $row){
        if(($row['matchable']??true)===false)continue;
        foreach(array_merge([$row['code']],$row['equivalent_codes']??[]) as $alias){
            $candidate=$flexible?st_fault_flex_key((string)$alias):st_fault_key((string)$alias);
            if($candidate===$key){$rows[]=$row;break;}
        }
    }
    return $rows;
}
function st_fault_lookup(array $input): array {
    $device=($input['device']??'')==='klima'?'klima':'kombi';$brand=(string)($input['brand']??'');$models=st_fault_models($device,$brand);$model=null;
    $requested_id=(string)($input['model_id']??'');
    if($requested_id!=='')foreach($models as $candidate)if($candidate['id']===$requested_id){$model=$candidate;break;}
    if(!$model&&$requested_id==='')$model=st_fault_infer(implode(' ',[$brand,(string)($input['model']??''),(string)($input['query']??'')]),$device,$brand);
    $code=(string)($input['code']??'');if($code==='')$code=st_fault_extract((string)($input['query']??''),$model);
    $base=['verified'=>false,'status'=>$model?'model-known':'needs-model','model'=>$model,'code'=>$code,'definition'=>null,'candidate_models'=>[],'scope_warning'=>st_fault_scope_warning($model),'code_match'=>''];
    if($model){
        if($code==='')return $base;
        $rows=st_fault_matching_rows($model,$code);$match='exact';
        if(!$rows){$rows=st_fault_matching_rows($model,$code,true);$match='flexible';}
        if(!$rows){$base['status']='code-not-covered';return $base;}
        $base['code_match']=$match;
        if(count($rows)>1){$base['status']=$match==='exact'?'source-conflict':'ambiguous-code';return $base;}
        if(!empty($rows[0]['source_conflict'])){$base['status']='source-conflict';return $base;}
        $base['definition']=$rows[0];$base['status']='verified';$base['verified']=true;$base['code']=$rows[0]['code'];return $base;
    }
    if($code!==''&&$requested_id==='')foreach($models as $candidate)if(st_fault_matching_rows($candidate,$code)||st_fault_matching_rows($candidate,$code,true))$base['candidate_models'][]=$candidate;
    return $base;
}
function st_fault_response(array $input): ?array {
    $found=st_fault_lookup($input);$model=$found['model'];$code=$found['code'];
    if($found['verified']){
        $row=$found['definition'];$manual=$model['manual'];
        return ['ok'=>true,'source'=>'manual','text'=>$model['brand'].' '.$model['label'].' için üretici belgesindeki '.$row['code'].' açıklaması: '.$row['meaning'].'. '.$row['safe_observation'].' Bu açıklama kesin parça teşhisi değildir. Kapağı açmayın; gaz, elektrik ve soğutucu devreye müdahale etmeyin.'.($found['scope_warning']!==''?' '.$found['scope_warning']:''),'guide_path'=>$model['path'].'#'.$row['anchor'],'source_url'=>$row['source_url']??$manual['url'],'source_locator'=>$row['source_locator'],'model_id'=>$model['id'],'code_definition_verified'=>true,'scope_warning'=>$found['scope_warning'],'code_match'=>$found['code_match']];
    }
    if($found['status']==='source-conflict')return ['ok'=>true,'source'=>'guide','text'=>$code.' için üretici kaynağında çelişkili veya birden fazla açıklama bulunuyor. Otomatik bir anlam seçilmedi. Tam belge, ürün kodu ve cihaz varyantı teknik olarak kontrol edilmeli.','guide_path'=>$model['path'],'scope_warning'=>$found['scope_warning'],'code_match'=>$found['code_match'],'requires_document_review'=>true];
    if($found['status']==='ambiguous-code')return ['ok'=>true,'source'=>'guide','text'=>$code.' yazımı seçilen modelin tablosunda birden fazla kodla eşleşiyor. Otomatik bir açıklama seçilmedi; kodu ekrandaki tam yazımıyla kaydedin ve modelin kendi tablosundan karşılaştırın.','guide_path'=>$model['path'],'scope_warning'=>$found['scope_warning'],'code_match'=>$found['code_match'],'requires_document_review'=>true];
    if($code!=='')return ['ok'=>true,'source'=>'guide','text'=>$code.' kodunu kaydettik. '.($model?'Seçilen modelin incelenen belgesinde bu kod için doğrulanmış bir eşleşme yok.':'Marka adı tek başına yeterli değildir; cihaz etiketindeki tam modelle ilerleyin.').' Kodun ekrandaki yazımını koruyun; eşleştirme yalnız seçilen modelin tablosunda yapılır. Kodu ve oluştuğu kullanım koşulunu paylaşın; kapağı açmayın ve tekrarlayan uyarıda reseti sürekli denemeyin.','guide_path'=>$model['path']??'/model-ariza-kodlari.html','scope_warning'=>$found['scope_warning'],'code_match'=>$found['code_match']];
    return null;
}
