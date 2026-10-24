<?php
declare(strict_types=1);
/* Completed UI answers are acknowledged separately from generation, so the
 * notification contains the text actually displayed, not an earlier fallback. */
function st_activity_schema(PDO $db): void {
    $db->exec("CREATE TABLE IF NOT EXISTS ai_events(id TEXT PRIMARY KEY,sid TEXT NOT NULL,device TEXT NOT NULL,brand TEXT NOT NULL DEFAULT '',model TEXT NOT NULL DEFAULT '',model_id TEXT NOT NULL DEFAULT '',issue TEXT NOT NULL,answer TEXT NOT NULL,source TEXT NOT NULL,page TEXT NOT NULL DEFAULT '',created INTEGER NOT NULL,displayed INTEGER NOT NULL DEFAULT 0);
        CREATE INDEX IF NOT EXISTS ai_events_created ON ai_events(created);
        CREATE TABLE IF NOT EXISTS activity_replays(k TEXT PRIMARY KEY,hash TEXT NOT NULL,event_id TEXT NOT NULL,created INTEGER NOT NULL);");
}
function st_activity_optional(array $input,string $key,int $maximum=160): string {
    if(!isset($input[$key])||$input[$key]==='')return '';
    return st_text($input,$key,0,$maximum);
}
function st_activity_source_label(string $source,bool $client): string {
    $labels=['ai'=>'Gemini AI','manual'=>'Üretici belgesi','guide'=>'Yerel belirti rehberi','emergency'=>'Acil güvenlik yönlendirmesi','advisory'=>'Üretici duyurusu'];
    return ($labels[$source]??'Yerel rehber').($client?' (tarayıcıda gösterilen kaynak)':'');
}
function st_activity_finish(PDO $db,array $row,array $input): void {
    $source=$row['source'];$gps=st_gps_description($input);
    $text="🤖 AI USTA — SORU VE CEVAP\n🕒 Tarih/saat: ".date('d.m.Y H:i:s')." (İstanbul)\n🔧 Cihaz: ".$row['device']
        ."\n🏷️ Marka / model: ".(trim($row['brand'].' '.$row['model'])?:'Belirtilmedi')
        ."\n🧠 Yanıt kaynağı: ".st_activity_source_label($source,empty($input['server_activity_id']))
        ."\n\n❓ Kullanıcının sorusu / belirtisi:\n".$row['issue']
        ."\n\n💡 Ekranda gösterilen cevap:\n".$row['answer']
        ."\n\n📄 Sayfa: ".$row['page']."\n📱 Ziyaretçi cihazı: ".st_device($_SERVER['HTTP_USER_AGENT']??'')
        ."\n📍 Konum: ".($gps?:'Konum paylaşılmadı; ilçe/mahalle varsayılmadı.');
    st_enqueue($db,$row['id'],['text'=>$text]);
    st_analytics_increment($db,'ai_questions');
    st_analytics_increment($db,'ai_source_'.($source==='ai'?'gemini':($source==='advisory'?'manual':$source)));
}
function st_activity_generated(string $session,array $input,array $response): array {
    $db=st_db();$id='ai:'.bin2hex(random_bytes(12));$sid=hash_hmac('sha256',$session,st_secret());
    $device=st_text($input,'device',2,40);$issue=st_text($input,'issue',3,1200);
    $brand=st_activity_optional($input,'brand');$model=st_activity_optional($input,'model');
    $modelId=st_activity_optional($input,'model_id');
    $selected=st_fault_lookup(['device'=>$device==='Klima'?'klima':'kombi','model_id'=>$modelId]);
    if($selected['model']){$brand=$selected['model']['brand'];$model=$selected['model']['label'];}
    $q=$db->prepare('INSERT INTO ai_events(id,sid,device,brand,model,model_id,issue,answer,source,page,created,displayed) VALUES(?,?,?,?,?,?,?,?,?,?,?,0)');
    $q->execute([$id,$sid,$device,$brand,$model,$modelId,$issue,(string)$response['text'],(string)$response['source'],'',time()]);
    return ['activity_recorded'=>false,'activity_id'=>$id,'activity_token'=>hash_hmac('sha256',$sid.'|'.$id,st_secret())];
}
function st_activity_record(string $session,array $input,bool $legacy=false): array {
    $device=st_text($input,'device',2,40);
    if(!in_array($device,['Kombi','Klima','Petek'],true))st_fail('Cihaz türü geçersiz.');
    $issue=st_text($input,'issue',3,1200);$answer=st_text($input,'answer',3,10000);
    $source=$legacy?'guide':($input['source']??'');
    if(!is_string($source)||!in_array($source,['guide','manual','emergency','advisory','ai'],true))st_fail('Yanıt kaynağı geçersiz.');
    $db=st_db();$sid=hash_hmac('sha256',$session,st_secret());$serverId=st_activity_optional($input,'server_activity_id',80);
    $row=null;
    if($serverId!==''){
        $token=st_activity_optional($input,'server_activity_token',64);
        if(!preg_match('/^ai:[a-f0-9]{24}$/D',$serverId)||!hash_equals(hash_hmac('sha256',$sid.'|'.$serverId,st_secret()),$token))st_fail('Yanıt kaydı doğrulanamadı.',403);
        $q=$db->prepare('SELECT * FROM ai_events WHERE id=? AND sid=?');$q->execute([$serverId,$sid]);$row=$q->fetch();
        if(!$row||$row['device']!==$device||$row['issue']!==$issue)st_fail('Yanıt kaydı eşleşmedi.',409);
        $source=$row['source'];$id=$serverId;
    }else{
        if($source==='ai')st_fail('Gemini yanıtı sunucu kaydıyla doğrulanmalıdır.');
        if($legacy)$event=hash('sha256',$device.'|'.$issue.'|'.intdiv(time(),600));
        else{
            if(($input['type']??'')!=='ai_result')st_fail('Etkinlik türü geçersiz.');
            $event=st_text($input,'event_id',16,100);
            if(!preg_match('/^[A-Za-z0-9_-]+$/D',$event))st_fail('Etkinlik anahtarı geçersiz.');
        }
        $id='ai:'.($legacy?'local:':'').hash_hmac('sha256',$sid.'|'.$event,st_secret());
    }
    $brand=$row?$row['brand']:st_activity_optional($input,'brand');$model=$row?$row['model']:st_activity_optional($input,'model');
    $modelId=$row?$row['model_id']:st_activity_optional($input,'model_id');$page=st_activity_optional($input,'page',200);
    if($page!==''&&(!preg_match('~^/[A-Za-z0-9_./-]*$~D',$page)||strpos($page,'..')!==false))st_fail('Sayfa bilgisi geçersiz.');
    $hash=hash('sha256',json_encode([$device,$issue,$answer,$source,$brand,$model,$modelId,$page]));
    $db->exec('BEGIN IMMEDIATE');
    try{
        $replay=$db->prepare('SELECT hash FROM activity_replays WHERE k=?');$replay->execute([$id]);$old=$replay->fetchColumn();
        if($old!==false){$db->exec('COMMIT');if(!hash_equals($old,$hash))st_fail('Etkinlik anahtarı farklı içerikle kullanılamaz.',409);st_delivery_attempt($id);return ['ok'=>true,'recorded'=>true,'duplicate'=>true,'activity_id'=>$id];}
        if($serverId!=='')$db->prepare('UPDATE ai_events SET answer=?,page=?,displayed=1 WHERE id=? AND sid=?')->execute([$answer,$page,$id,$sid]);
        else $db->prepare('INSERT INTO ai_events(id,sid,device,brand,model,model_id,issue,answer,source,page,created,displayed) VALUES(?,?,?,?,?,?,?,?,?,?,?,1)')->execute([$id,$sid,$device,$brand,$model,$modelId,$issue,$answer,$source,$page,time()]);
        $eventRow=['id'=>$id,'device'=>$device,'brand'=>$brand,'model'=>$model,'issue'=>$issue,'answer'=>$answer,'source'=>$source,'page'=>$page];
        st_activity_finish($db,$eventRow,$input);
        $db->prepare('INSERT INTO activity_replays(k,hash,event_id,created) VALUES(?,?,?,?)')->execute([$id,$hash,$id,time()]);
        $db->exec('COMMIT');
    }catch(Throwable $error){if($db->inTransaction())$db->exec('ROLLBACK');throw $error;}
    st_delivery_attempt($id);
    return ['ok'=>true,'recorded'=>true,'duplicate'=>false,'activity_id'=>$id];
}
