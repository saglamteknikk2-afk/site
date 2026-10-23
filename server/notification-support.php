<?php
declare(strict_types=1);
function st_notification_text(string $kind,string $text): string {
    $events=['visit'=>'👤','visit-location'=>'👤','review'=>'⭐','ticket'=>'🛠️','ai'=>'🤖','summary'=>'📊'];
    if(!isset($events[$kind])||$text==='')return $text;
    $fields=['Tarih/saat:'=>'⏰','Tarih:'=>'⏰','Konum:'=>'📍','Konum (müşterinin beyanı):'=>'📍','Ziyaretçi cihazı:'=>'📱','Cihaz:'=>'📱','Soru:'=>'❓','Yanıt:'=>'💡','Ad:'=>'👤','Telefon:'=>'☎️','Puan:'=>'⭐'];
    $decorate=static function(string $header)use($fields):string{
        $lines=explode("\n",$header);
        foreach($lines as &$line)foreach($fields as $label=>$icon)if(str_starts_with($line,$label)){$line=$icon.' '.$line;break;}
        unset($line);return implode("\n",$lines);
    };
    $parts=explode("\n\n",$text,2);$header=$decorate($parts[0]);
    if(!preg_match('/^[\x{1F000}-\x{1FAFF}\x{2600}-\x{27BF}\x{2B50}]/u',$header))$header=$events[$kind].' '.$header;
    if(count($parts)===1)return $header;
    $body=$parts[1];
    if(in_array($kind,['review','ticket'],true)){
        $marker="\n\nZiyaretçi cihazı:";$position=strrpos($body,$marker);
        if($position!==false)$body=substr($body,0,$position)."\n\n".$decorate('Ziyaretçi cihazı:'.substr($body,$position+strlen($marker)));
    }
    return $header."\n\n".$body;
}
function st_ai_notification_rows(string $id,array $payload): array {
    $text=$payload['text'];$count=preg_match_all('/./us',$text,$matches);
    if($count===false)throw new RuntimeException('AI bildirim metni geçersiz.');
    $length=$count+preg_match_all('/[\x{10000}-\x{10ffff}]/u',$text);
    unset($payload['parse_mode']);
    if($length<=3500)return [[$id,$payload]];
    $total=2;
    do{
        $capacity=3500-(2*strlen((string)$total)+4);$chunks=[];$chunk='';$units=0;
        foreach($matches[0] as $char){
            $width=strlen($char)===4?2:1;
            if($units+$width>$capacity){$chunks[]=$chunk;$chunk='';$units=0;}
            $chunk.=$char;$units+=$width;
        }
        if($chunk!=='')$chunks[]=$chunk;
        $previous=$total;$total=count($chunks);
    }while($total!==$previous);
    $rows=[];
    foreach($chunks as $index=>$chunk){$part=$payload;$part['text']='['.($index+1).'/'.$total.'] '.$chunk;$rows[]=[$index===0?$id:$id.':part:'.($index+1),$part];}
    return $rows;
}
function st_notification_rows(string $id,array $payload): array {
    $assets=['visit'=>'visit.png','visit-location'=>'visit.png','review'=>'review.png','ticket'=>'ticket.png'];
    $kind=explode(':',$id,2)[0];
    if(!isset($payload['_method'])&&is_string($payload['text']??null))$payload['text']=st_notification_text($kind,$payload['text']);
    if($kind==='ai'&&!isset($payload['_method']))return st_ai_notification_rows($id,$payload);
    if(!isset($assets[$kind])||isset($payload['_method']))return [[$id,$payload]];
    $text=$payload['text'];$n=preg_match_all('/./us',$text);$n+=preg_match_all('/[\x{10000}-\x{10ffff}]/u',$text);
    $photo=['_method'=>'sendPhoto','_photo'=>$assets[$kind]];
    if($n<=1024){$photo['caption']=$text;if(isset($payload['reply_markup']))$photo['reply_markup']=$payload['reply_markup'];return [[$id,$photo]];}
    preg_match('/^.{0,100}/us',explode("\n",$text,2)[0],$m);$photo['caption']='Sağlam Teknik · '.($m[0]??'Bildirim');
    return [[$id,$payload],[$id.':photo',$photo]];
}
function st_photo_fields(array $payload): array {
    $name=$payload['_photo']??'';if(!in_array($name,['visit.png','review.png','ticket.png'],true))throw new RuntimeException('Bildirim görseli geçersiz.');
    $path=__DIR__.'/assets/notifications/'.$name;
    if(!is_file($path)||filesize($path)>2000000||file_get_contents($path,false,null,0,8)!=="\x89PNG\r\n\x1a\n")throw new RuntimeException('Bildirim görseli okunamadı.');
    unset($payload['_photo']);$payload['photo']=new CURLFile($path,'image/png',$name);
    if(isset($payload['reply_markup']))$payload['reply_markup']=json_encode($payload['reply_markup'],JSON_UNESCAPED_UNICODE);
    return $payload;
}
function st_gps_description(array $data): string {
    $loc=$data['location']??null;if(!is_array($loc)||($loc['consent']??false)!==true)return '';
    foreach(['latitude','longitude','accuracy'] as $k)if(!isset($loc[$k])||(!is_int($loc[$k])&&!is_float($loc[$k]))||!is_finite((float)$loc[$k]))return '';
    $lat=$loc['latitude'];$lon=$loc['longitude'];$acc=$loc['accuracy'];
    if($lat< -90||$lat>90||$lon< -180||$lon>180||$acc<0||$acc>100000)return '';
    return sprintf("Müşterinin izniyle paylaşılan konum: %.6f, %.6f (±%.0f m)\nHarita: https://www.google.com/maps?q=%.6f,%.6f",$lat,$lon,$acc,$lat,$lon);
}
function st_ip_lookup(string $ip): string {
    if(!filter_var($ip,FILTER_VALIDATE_IP,FILTER_FLAG_NO_PRIV_RANGE|FILTER_FLAG_NO_RES_RANGE)||st_in_cidr($ip,'100.64.0.0/10'))return 'PC / yerel ağ (ilçe ve mahalle belirlenemez)';
    $key='geo:'.hash_hmac('sha256',$ip.'.'.date('Y-m-d'),st_secret());$db=st_db();
    $q=$db->prepare('SELECT v FROM meta WHERE k=?');$q->execute([$key]);$cached=json_decode($q->fetchColumn()?:'null',true);
    if(is_array($cached)&&($cached['until']??0)>time())return $cached['text'];
    $text='Belirlenemedi (ilçe/mahalle doğrulanmadı)';$success=false;
    if(function_exists('curl_init')){
        $ch=curl_init('https://ipwho.is/'.rawurlencode($ip).'?fields=success,city,region,country');
        curl_setopt_array($ch,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_CONNECTTIMEOUT=>1,CURLOPT_TIMEOUT=>2]);
        $raw=curl_exec($ch);$code=curl_getinfo($ch,CURLINFO_HTTP_CODE);curl_close($ch);
        $a=is_string($raw)&&strlen($raw)<=16384?json_decode($raw,true):null;
        if($code===200&&is_array($a)&&($a['success']??false)===true){$parts=[];foreach(['city','region','country'] as $k)if(is_string($a[$k]??null))$parts[]=substr(preg_replace('/[\x00-\x1f]/',' ',trim($a[$k])),0,80);$text=implode(' / ',array_filter($parts)).' (IP tahmini; kesin ilçe/mahalle bilinmiyor)';$success=true;}
    }
    $db->prepare('INSERT INTO meta(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v')->execute([$key,json_encode(['until'=>time()+($success?21600:300),'text'=>$text])]);
    return $text;
}
