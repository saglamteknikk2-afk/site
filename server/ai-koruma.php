<?php
/**
 * SAĞLAM TEKNİK — AI KORUMA, AKILLI KONUM VE TELEGRAM KONTROL SİSTEMİ
 * 
 * 1. Ziyaretçi Bildirim Kirliliği Engellendi: Boş ziyaretler yerine sadece iş getirecek gerçek bildirimler atılır.
 * 2. 2 Soru Sınırı & Usta Yönlendirmesi: 2 sorudan sonra ziyaretçiyi kovmaz; Arıza Rehberi ve "Ustayı Hemen Ara" butonunu sunar.
 * 3. Şüphe Ettirmeyen Akıllı Konum: En yakın servis aracının varış süresi için konum iznini doğal yolla aldırır.
 * 4. Gemini Hata & Kota Koruması: 429/401 anında Telegram'a bildirilir, site çökmeden yerel rehbere geçer.
 * 5. Akıllı Önbellek (Cache): Aynı soruları hafızadan vererek kotanızı ve cebinizi korur.
 */

// -----------------------------------------------------------------------------
// 1. TELEGRAM BİLDİRİM MOTORU (site_apileri,.txt dosyasını otomatik okur)
// -----------------------------------------------------------------------------
function st_telegram_gonder($mesaj) {
    // Mevcut Telegram API göndereni TLS sertifikasını doğrular; token TXT dışında bulunmaz.
    if (!function_exists('st_config') || !function_exists('st_telegram')) return false;
    $c=st_config();if(empty($c['telegram_token']) || empty($c['telegram_chat_id']))return false;
    try {
        $result=st_telegram('sendMessage',[
            'chat_id'=>$c['telegram_chat_id'],
            'text'=>(string)$mesaj,
            'parse_mode'=>'HTML',
            'disable_web_page_preview'=>true
        ]);
        return !empty($result['ok']);
    } catch (Throwable $e) { return false; }
}

// -----------------------------------------------------------------------------
// 2. 2 SORU SINIRI & MÜŞTERİYİ USTAYA BAĞLAYAN ARIZA REHBERİ
// -----------------------------------------------------------------------------
function st_ip_spam_engelle() {
    $ip = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
    $dizin = __DIR__ . '/../private/saglam-teknik';
    if (!is_dir($dizin)) $dizin = sys_get_temp_dir();
    $dosya = $dizin . '/ai_rate_limit.json';
    
    $suan = time();
    $veriler = file_exists($dosya) ? (json_decode(file_get_contents($dosya), true) ?: []) : [];
    
    // 1 saatten eski kayıtları temizle
    foreach ($veriler as $kayitli_ip => $zamanlar) {
        $veriler[$kayitli_ip] = array_filter($zamanlar, function($z) use ($suan) {
            return ($suan - $z) < 3600;
        });
        if (empty($veriler[$kayitli_ip])) unset($veriler[$kayitli_ip]);
    }
    
    $ip_gecmisi = $veriler[$ip] ?? [];
    
    // 2 SORU DOLDUĞUNDA ÇALIŞACAK BLOK:
    if (count($ip_gecmisi) >= 2) {
        // Telegram'a SADECE 1 KEZ bildirim at (aynı kişi için telefonunuzu zırt pırt çaldırmaz)
        if (count($ip_gecmisi) === 2) {
            $tarih = date('d.m.Y H:i:s');
            $uyari = "🔔 <b>Müşteri AI Soru Sınırına Ulaştı:</b>\n" .
                     "Bir ziyaretçi 2 soru sorma hakkını doldurdu ve telefonla usta desteğine yönlendirildi.\n" .
                     "📍 IP: <code>{$ip}</code>\n" .
                     "🕒 Zaman: {$tarih}";
            st_telegram_gonder($uyari);
            
            // Sayacı 3 yaparak bir sonraki tıklamalarda Telegram'ı sustur
            $ip_gecmisi[] = $suan;
            $veriler[$ip] = $ip_gecmisi;
            file_put_contents($dosya, json_encode($veriler), LOCK_EX);
        }
        
        $cevap_metni = "Ücretsiz yapay zekâ ön kontrol hakkınızı tamamladınız.\n\n" .
                       "⚠️ Kombi ve klimalarınızda elektrik, doğalgaz ve yüksek su basıncı hatları bulunduğu için bu aşamadan sonra cihaz kapağını açmadan MYK belgeli teknik ekibimizin müdahale etmesi can ve cihaz güvenliğiniz için gereklidir.\n\n" .
                       "📍 <b>Varış Planı:</b> Bölge, ekip uygunluğu ve trafik durumuna göre görüşmede netleştirilir.\n\n" .
                       "📞 <b>Ustayı Hemen Arayın:</b> <a href='tel:05346225515'><b>0534 622 5515</b></a>\n" .
                       "💬 <b>WhatsApp ile Arıza Fotoğrafı Gönderin:</b> <a href='https://wa.me/905346225515'><b>Hemen Mesaj Atın</b></a>\n" .
                       "📋 Veya aşağıdaki formu doldurarak nöbetçi servis kaydı oluşturabilirsiniz.";
                       
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode([
            'ok'          => true,
            'status'      => 'limit_ve_rehber',
            'badge'       => 'Arıza Rehberi & Usta Desteği',
            'title'       => 'Ücretsiz Soru Hakkınız Tamamlandı',
            'yanit'       => $cevap_metni,
            'text'        => $cevap_metni,
            'description' => $cevap_metni,
            'adımlar'     => [
                "Uygun soğuk tesisat basıncı aralığı tam modelin üretici kılavuzuna göre değerlendirilir; göstergedeki mevcut değeri not edin.",
                "Ekranda beliren arıza kodunu not edin.",
                "Garantili onarım için 0534 622 5515 numarasından servis kaydı oluşturun."
            ]
        ], JSON_UNESCAPED_UNICODE);
        exit;
    }
    
    // Sayacı 1 artır
    $ip_gecmisi[] = $suan;
    $veriler[$ip] = $ip_gecmisi;
    file_put_contents($dosya, json_encode($veriler), LOCK_EX);
}

// -----------------------------------------------------------------------------
// 3. ŞÜPHE ETTİRMEYEN AKILLI KONUM YAKALAYICI (Google Haritalar Linki Üretir)
// -----------------------------------------------------------------------------
function st_konum_takibi() {
    $lat = $_POST['lat'] ?? $_GET['lat'] ?? null;
    $lon = $_POST['lon'] ?? $_GET['lon'] ?? null;
    
    if ($lat && $lon) {
        $harita_linki = "https://www.google.com/maps?q={$lat},{$lon}";
        $bildirim = "📍 <b>Müşteri Kesin Konumunu Paylaştı:</b>\n" .
                    "🗺️ <a href='{$harita_linki}'>Google Haritalar'da Konumu Gör</a>\n" .
                    "🕒 Zaman: " . date('d.m.Y H:i:s');
        st_telegram_gonder($bildirim);
    }
}

// -----------------------------------------------------------------------------
// 4. GEMINI HATA, KOTA VE TELEGRAM UYARI TAKİBİ (429 / 401 / 500)
// -----------------------------------------------------------------------------
function st_gemini_hata_kontrol($http_kodu, $hata_detayi = '') {
    if ($http_kodu == 200) return;
    
    $tarih = date('d.m.Y H:i:s');
    
    if ($http_kodu == 429) {
        $mesaj = "⚠️ <b>AI Usta Uyarısı:</b>\n" .
                 "Google Gemini API kotası doldu (<b>Hata: 429 Rate Limit</b>).\n" .
                 "🕒 Zaman: {$tarih}\n" .
                 "ℹ️ Sistem ziyaretçiler için otomatik olarak 48 yerel belirti rehberine geçti. Site kesintisiz çalışıyor.";
        st_telegram_gonder($mesaj);
    } elseif ($http_kodu == 401 || $http_kodu == 403) {
        $mesaj = "⚠️ <b>AI Usta Uyarısı:</b>\n" .
                 "Gemini API anahtarı geçersiz veya yetkisiz (<b>Hata: {$http_kodu}</b>).\n" .
                 "🕒 Zaman: {$tarih}\n" .
                 "Lütfen yönetim panelinden API anahtarını kontrol edin.";
        st_telegram_gonder($mesaj);
    } elseif ($http_kodu >= 500) {
        $mesaj = "⚠️ <b>AI Usta Uyarısı:</b>\n" .
                 "Google sunucuları geçici olarak yanıt vermedi (<b>Hata: {$http_kodu}</b>).\n" .
                 "Ziyaretçi yerel belirti rehberine yönlendirildi.";
        st_telegram_gonder($mesaj);
    }
}

// -----------------------------------------------------------------------------
// 5. AKILLI ÖNBELLEK (Aynı Soruları Hafızadan Verir, Kotayı Korur)
// -----------------------------------------------------------------------------
function st_ai_onbellek_getir($soru) {
    $anahtar = md5(mb_strtolower(trim($soru), 'UTF-8'));
    $dizin = __DIR__ . '/../private/saglam-teknik/cache';
    $dosya = $dizin . '/' . $anahtar . '.json';
    
    if (file_exists($dosya) && (time() - filemtime($dosya) < 86400)) {
        $veri = json_decode(file_get_contents($dosya), true);
        if (!empty($veri)) return $veri;
    }
    return null;
}

function st_ai_onbellek_kaydet($soru, $cevap) {
    $dizin = __DIR__ . '/../private/saglam-teknik/cache';
    if (!is_dir($dizin)) @mkdir($dizin, 0775, true);
    $anahtar = md5(mb_strtolower(trim($soru), 'UTF-8'));
    $dosya = $dizin . '/' . $anahtar . '.json';
    file_put_contents($dosya, json_encode($cevap, JSON_UNESCAPED_UNICODE), LOCK_EX);
}

// -----------------------------------------------------------------------------
// 6. TETİKLEYİCİ: SADECE ARİZA SORUSU GELDİĞİNDE DEVREYE GİRER
// -----------------------------------------------------------------------------
$girdi = file_get_contents('php://input');
$json_veri = json_decode($girdi, true) ?: [];

// URL parametrelerinden konum bildirimi yapılmaz; müşteri rızası JSON formunda doğrulanır.

// Sadece gerçek arıza sorusu sorulduğunda 2 soru sınırını çalıştır
if (!empty($_POST['belirti']) || !empty($_POST['soru']) || !empty($_POST['ariza']) || !empty($json_veri['belirti']) || !empty($json_veri['soru']) || !empty($json_veri['prompt'])) {
    st_ip_spam_engelle();
}