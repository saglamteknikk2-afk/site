<?php
declare(strict_types=1);
// Manufacturer advisory lookup only. Never loads the API dispatcher or sends messages.
function st_fault_advisory(string $query): ?array {
    $fold=static function(string $value): string {
        $value=strtolower(strtr($value,['Ç'=>'c','ç'=>'c','Ğ'=>'g','ğ'=>'g','İ'=>'i','ı'=>'i','Ö'=>'o','ö'=>'o','Ş'=>'s','ş'=>'s','Ü'=>'u','ü'=>'u']));
        $value=preg_replace('/\p{Mn}+/u','',$value);
        $value=preg_replace('/([a-z])([0-9])/','$1 $2',$value);
        $value=preg_replace('/([0-9])([a-z])/','$1 $2',$value);
        return trim(preg_replace('/\s+/',' ',preg_replace('/[^a-z0-9.,]+/',' ',$value)));
    };
    $text=$fold($query);
    if(!preg_match('/\bbaykan\b/',$text)||preg_match('/\bbaymak\b/',$text))return null;
    if(!preg_match('/\bgunes\s*premix\b/',$text)||preg_match('/\b(?:saturn|lena|luxury)\b/',$text))return null;
    preg_match_all('/(?:^|[^a-z0-9.,])(\d+(?:[.,]\d+)?)\s*(?:kw|kilovat(?:t)?|kilowatt)(?=$|[^a-z0-9])/',$text,$matches);
    if(!$matches[1])return null;
    foreach($matches[1] as $capacity)if((float)str_replace(',','.',$capacity)!==35.0)return null;
    if(function_exists('st_fault_data'))$data=st_fault_data();
    else {
        $raw=@file_get_contents(__DIR__.'/assets/verified-faults.json');
        $data=is_string($raw)?json_decode($raw,true):null;
    }
    if(!is_array($data))return null;
    foreach($data['coverage']??[] as $brand){
        if(($brand['device']??'')!=='kombi'||$fold((string)($brand['brand']??''))!=='baykan')continue;
        foreach($brand['advisories']??[] as $notice){
            if(($notice['kind']??'')!=='recall'||!is_array($notice['exact_model_names']??null))continue;
            $exact=false;
            foreach($notice['exact_model_names'] as $name)if(preg_match('/^gunes\s*premix\s+35\s+kw$/',$fold((string)$name)))$exact=true;
            if(!$exact||!preg_match('~^https://(?:www\.)?baykankombi\.com(?:/|$)~',(string)($notice['url']??''))||!is_string($notice['message']??null)||trim($notice['message'])===''||empty($notice['source_locator']))continue;
            return ['ok'=>true,'source'=>'advisory','manufacturer_advisory'=>true,'text'=>$notice['message'],
                'source_url'=>$notice['url'],'source_locator'=>$notice['source_locator'],'guide_path'=>'/model-ariza-kodlari.html'];
        }
    }
    return null;
}
