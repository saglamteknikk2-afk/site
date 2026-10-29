<?php
declare(strict_types=1);
/** Local, operator-confirmed service operations. No maps, GPS or ETA is inferred. */
function st_operations_districts(): array {
    return ['Arnavutköy','Avcılar','Bağcılar','Bahçelievler','Bakırköy','Başakşehir','Bayrampaşa','Beşiktaş','Beylikdüzü','Beyoğlu','Büyükçekmece','Çatalca','Esenler','Esenyurt','Eyüpsultan','Fatih','Gaziosmanpaşa','Güngören','Kağıthane','Küçükçekmece','Sarıyer','Silivri','Şişli','Sultangazi','Zeytinburnu'];
}
function st_operations_normalize(string $value): string {
    $value=strtr($value,['İ'=>'i','I'=>'i','ı'=>'i','Ş'=>'s','ş'=>'s','Ğ'=>'g','ğ'=>'g','Ü'=>'u','ü'=>'u','Ö'=>'o','ö'=>'o','Ç'=>'c','ç'=>'c','Â'=>'a','â'=>'a']);
    return trim((string)preg_replace('/[^a-z0-9]+/',' ',strtolower($value)));
}
function st_operations_district(string $input): array {
    $needle=' '.st_operations_normalize($input).' ';$matches=[];
    foreach(st_operations_districts() as $label){$key=st_operations_normalize($label);if(strpos($needle,' '.$key.' ')!==false)$matches[$key]=$label;}
    if(count($matches)!==1)return ['key'=>'','label'=>'Bölge görüşülecek'];
    foreach($matches as $key=>$label)return ['key'=>(string)$key,'label'=>(string)$label];
}
function st_operations_schema(PDO $db): void {
    $db->exec("CREATE TABLE IF NOT EXISTS ticket_operations(ticket_id TEXT PRIMARY KEY REFERENCES tickets(id) ON DELETE CASCADE,status TEXT NOT NULL DEFAULT 'received',service_level TEXT NOT NULL DEFAULT 'standard',district_key TEXT NOT NULL,district_label TEXT NOT NULL,routing_confirmed INTEGER NOT NULL DEFAULT 0,nonce TEXT NOT NULL,created INTEGER NOT NULL,updated INTEGER NOT NULL,operator TEXT NOT NULL DEFAULT '');
        CREATE INDEX IF NOT EXISTS ticket_operations_active ON ticket_operations(status,routing_confirmed,district_key,created);
        CREATE TABLE IF NOT EXISTS ticket_operation_events(id INTEGER PRIMARY KEY AUTOINCREMENT,ticket_id TEXT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,from_status TEXT NOT NULL,to_status TEXT NOT NULL,operator TEXT NOT NULL,created INTEGER NOT NULL);");
    // Old requests have no known completion state. Keep them visible to the owner,
    // but never invent a current queue from historical records.
    $rows=$db->query('SELECT t.id,t.district,t.created,p.ticket_id AS priority_id FROM tickets t LEFT JOIN ticket_operations o ON o.ticket_id=t.id LEFT JOIN priority_service_acceptances p ON p.ticket_id=t.id WHERE o.ticket_id IS NULL')->fetchAll(PDO::FETCH_ASSOC);
    $q=$db->prepare("INSERT OR IGNORE INTO ticket_operations(ticket_id,status,service_level,district_key,district_label,routing_confirmed,nonce,created,updated) VALUES(?,'received',?,?,?,0,?,?,?)");
    foreach($rows as $row){$district=st_operations_district((string)$row['district']);$q->execute([$row['id'],$row['priority_id']?'priority':'standard',$district['key'],$district['label'],bin2hex(random_bytes(8)),(int)$row['created'],(int)$row['created']]);}
}
function st_operations_labels(): array {return ['received'=>'Talep alındı','accepted'=>'Ekip kabul etti','en_route'=>'Yolda','completed'=>'Tamamlandı','cancelled'=>'İptal edildi'];}
function st_operations_row(PDO $db,string $id): ?array {
    if(!preg_match('/^[a-f0-9]{24}$/D',$id))throw new DomainException('Servis kayıt kimliği geçersiz.');
    $q=$db->prepare('SELECT o.*,t.device,t.district FROM ticket_operations o JOIN tickets t ON t.id=o.ticket_id WHERE o.ticket_id=?');$q->execute([$id]);$row=$q->fetch(PDO::FETCH_ASSOC);return $row?:null;
}
function st_operations_active(PDO $db): array {
    return $db->query("SELECT ticket_id,status,service_level,district_key,district_label,created,updated FROM ticket_operations WHERE routing_confirmed=1 AND status IN ('received','accepted','en_route') ORDER BY CASE WHEN status='en_route' THEN 0 WHEN status='accepted' AND service_level='priority' THEN 1 ELSE 2 END,created,rowid")->fetchAll(PDO::FETCH_ASSOC);
}
function st_operations_route(array $rows): array {
    $groups=[];
    foreach($rows as $row){$key=(string)$row['district_key'];if($key==='')continue;if(!isset($groups[$key]))$groups[$key]=['district'=>(string)$row['district_label'],'requests'=>0,'accepted'=>0,'en_route'=>0];$groups[$key]['requests']++;if($row['status']==='accepted')$groups[$key]['accepted']++;if($row['status']==='en_route')$groups[$key]['en_route']++;}
    return array_values($groups);
}
function st_operations_public_summary(PDO $db,string $id): array {
    $current=st_operations_row($db,$id);if(!$current)throw new DomainException('Servis kaydı bulunamadı.');
    $active=st_operations_active($db);$ahead=0;$found=false;
    foreach($active as $row){if($row['ticket_id']===$id){$found=true;break;}if($current['district_key']!==''&&$row['district_key']===$current['district_key'])$ahead++;}
    $pending=in_array($current['status'],['received','accepted','en_route'],true);
    $known=$found&&$current['district_key']!==''&&$pending;
    $message=$known?$current['district_label'].' bölgesinde önünüzde '.$ahead.' aktif kayıt bulunuyor. Sıra, ekibin kabulü ve güncel saha durumuyla değişebilir.':'Talebiniz ekip tarafından değerlendirilecek; bölge ve servis uygunluğu görüşülerek netleştirilir.';
    if(!$pending)$message=st_operations_labels()[$current['status']].'.';
    return ['district'=>$current['district_label'],'ahead'=>$known?$ahead:null,'status'=>$current['status'],'status_label'=>st_operations_labels()[$current['status']],'service_level'=>$current['service_level'],'priority_confirmed'=>$current['service_level']==='priority'&&in_array($current['status'],['accepted','en_route'],true),'route_districts'=>array_column(st_operations_route($active),'district'),'route_kind'=>'district-grouping-not-live-navigation','message'=>$message,'tracking_url'=>st_customer_tracking_url($db,$id)];
}
function st_operations_ticket_created(PDO $db,string $ticketId,array $ticketData,?array $acceptedPriority=null): array {
    if(!$db->inTransaction())throw new LogicException('Service operation must share the ticket transaction.');
    if(!preg_match('/^[a-f0-9]{24}$/D',$ticketId))throw new LogicException('Invalid service record identity.');
    $q=$db->prepare('SELECT district,created FROM tickets WHERE id=?');$q->execute([$ticketId]);$ticket=$q->fetch(PDO::FETCH_ASSOC);if(!$ticket)throw new LogicException('Service operation needs a persisted ticket.');
    $district=st_operations_district((string)$ticket['district']);
    $q=$db->prepare("INSERT INTO ticket_operations(ticket_id,status,service_level,district_key,district_label,routing_confirmed,nonce,created,updated) VALUES(?,'received',?,?,?,1,?,?,?) ON CONFLICT(ticket_id) DO NOTHING");
    $q->execute([$ticketId,$acceptedPriority?'priority':'standard',$district['key'],$district['label'],bin2hex(random_bytes(8)),(int)$ticket['created'],time()]);
    // Create the unguessable tracking link in the *same* transaction as the ticket.
    $q=$db->prepare("UPDATE ticket_operations SET customer_token=? WHERE ticket_id=? AND customer_token=''");
    $q->execute([bin2hex(random_bytes(16)),$ticketId]);
    return st_operations_public_summary($db,$ticketId);
}
function st_operations_keyboard(PDO $db,string $id): array {
    $row=st_operations_row($db,$id);if(!$row)return ['inline_keyboard'=>[]];$buttons=[];
    $allowed=['received'=>[['a','✅ Aldım'],['i','İptal']],'accepted'=>[['y','🚗 Yoldayım'],['t','✅ Tamamlandı'],['i','İptal']],'en_route'=>[['t','✅ Tamamlandı'],['i','İptal']]];
    foreach($allowed[$row['status']]??[] as [$code,$label])$buttons[]=['text'=>$label,'callback_data'=>'t:'.$code.':'.$id.':'.$row['nonce']];
    $rows=[];if($buttons)$rows[]=$buttons;
    $customer=[['text'=>'💬 Müşteriye yaz','callback_data'=>'cu:m:'.$id.':'.$row['nonce']],['text'=>'⏱ Varış süresi','callback_data'=>'cu:e:'.$id.':'.$row['nonce']]];
    if($row['service_level']==='priority'&&in_array($row['status'],['accepted','en_route'],true))$customer[]=['text'=>'✨ VIP bilgilendir','callback_data'=>'cu:v:'.$id.':'.$row['nonce']];
    if(!in_array($row['status'],['completed','cancelled'],true))$rows[]=$customer;
    return ['inline_keyboard'=>$rows];
}
function st_operations_set_status(PDO $db,string $id,string $status,string $operator='owner'): array {
    if(!isset(st_operations_labels()[$status]))throw new DomainException('Servis durumu geçersiz.');
    $owns=!$db->inTransaction();if($owns){if(function_exists('st_transaction_begin'))st_transaction_begin($db);else $db->beginTransaction();}
    try{
        $row=st_operations_row($db,$id);if(!$row)throw new DomainException('Servis kaydı bulunamadı.');
        $changed=$row['status']!==$status;
        if($changed){
            $transitions=['received'=>['accepted','cancelled'],'accepted'=>['en_route','completed','cancelled'],'en_route'=>['completed','cancelled'],'completed'=>[],'cancelled'=>[]];
            if(!in_array($status,$transitions[$row['status']]??[],true))throw new DomainException('Bu servis kaydı için durum geçişi uygun değil. Güncel durumu yenileyin.');
            // This is the operator's explicit update for this ticket. An older
            // open trip or another team must not silently block customer news.
            $stamp=time();$operator=substr($operator,0,80);
            $db->prepare('UPDATE ticket_operations SET status=?,routing_confirmed=1,operator=?,updated=? WHERE ticket_id=?')->execute([$status,$operator,$stamp,$id]);
            $db->prepare('INSERT INTO ticket_operation_events(ticket_id,from_status,to_status,operator,created) VALUES(?,?,?,?,?)')->execute([$id,$row['status'],$status,$operator,$stamp]);
            st_customer_update($db,$id,st_customer_status_text($row,$status),'status');
            if(function_exists('st_enqueue'))st_enqueue($db,'ticket-state:'.$id.':'.$status,['text'=>"🛠 Servis durumu güncellendi\nKayıt: ".$id."\nBölge: ".$row['district_label']."\nDurum: ".st_operations_labels()[$status],'reply_markup'=>st_operations_keyboard($db,$id)]);
        }
        $result=['ok'=>true,'changed'=>$changed,'ticket_id'=>$id,'status'=>$status,'message'=>$changed?st_operations_labels()[$status].'.':'Kayıt zaten bu durumda.','reply_markup'=>st_operations_keyboard($db,$id),'queue'=>st_operations_public_summary($db,$id)];
        if($owns){$db->commit();st_customer_deliver($db,$id);}return $result;
    }catch(Throwable $error){if($owns&&$db->inTransaction())$db->rollBack();throw $error;}
}
function st_operations_callback(PDO $db,array $query,array $cfg): ?array {
    $data=$query['data']??'';if(!is_string($data)||strncmp($data,'t:',2)!==0)return null;
    $from=(string)($query['from']['id']??'');$chat=(string)($query['message']['chat']['id']??'');
    $admins=array_map('strval',$cfg['telegram_admin_ids']??[]);$configured=(string)($cfg['telegram_chat_id']??'');if(ctype_digit($configured))$admins[]=$configured;
    if($configured===''||$chat!==$configured||!in_array($from,$admins,true))throw new DomainException('Bu servis kaydını yönetme yetkiniz yok.');
    if(!preg_match('/^t:([ayti]):([a-f0-9]{24}):([a-f0-9]{16})$/D',$data,$parts))throw new DomainException('Servis düğmesi geçersiz.');
    $row=st_operations_row($db,$parts[2]);if(!$row||!hash_equals($row['nonce'],$parts[3]))throw new DomainException('Servis düğmesi doğrulanamadı.');
    $states=['a'=>'accepted','y'=>'en_route','t'=>'completed','i'=>'cancelled'];
    return st_operations_set_status($db,$parts[2],$states[$parts[1]],'telegram:'.$from);
}
function st_operations_enrich_tickets(PDO $db,array $tickets): array {
    if(!$tickets)return [];$ids=array_column($tickets,'id');$q=$db->prepare('SELECT o.*,p.fee_try,p.currency FROM ticket_operations o LEFT JOIN priority_service_acceptances p ON p.ticket_id=o.ticket_id WHERE o.ticket_id IN ('.implode(',',array_fill(0,count($ids),'?')).')');$q->execute($ids);$lookup=[];
    foreach($q->fetchAll(PDO::FETCH_ASSOC) as $row)$lookup[$row['ticket_id']]=$row;
    foreach($tickets as &$ticket){$row=$lookup[$ticket['id']]??null;if(!$row)continue;$ticket['operation']=['status'=>$row['status'],'status_label'=>st_operations_labels()[$row['status']],'service_level'=>$row['service_level'],'district'=>$row['district_label'],'routing_confirmed'=>(bool)$row['routing_confirmed'],'fee_try'=>$row['fee_try']===null?null:(int)$row['fee_try'],'currency'=>$row['currency']??null];}unset($ticket);return $tickets;
}
function st_operations_owner_snapshot(PDO $db): array {
    $rows=st_operations_active($db);$counts=['received'=>0,'accepted'=>0,'en_route'=>0];foreach($rows as $row)$counts[$row['status']]++;
    return ['active'=>count($rows),'counts'=>$counts,'districts'=>st_operations_route($rows),'route_kind'=>'district-grouping-not-live-navigation','message'=>'Gerçek açık kayıtlar ilçelere göre gruplanır. Canlı araç konumu, sürüş süresi veya kesin varış saati hesaplanmaz.'];
}
