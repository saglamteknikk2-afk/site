"""Keep browser and PHP search in agreement without loosening model/code scope."""
from __future__ import annotations

import json
import re

OUTSIDE_DISTRICTS = ['Adalar','Ataşehir','Beykoz','Çekmeköy','Kadıköy','Kartal','Maltepe','Pendik','Sancaktepe','Sultanbeyli','Şile','Tuzla','Ümraniye','Üsküdar']


def _replace(text: str, before: str, after: str, *, name: str) -> str:
    if text.count(before) != 1:
        raise ValueError(f'Unexpected matching source in {name}; refusing an unverified patch')
    return text.replace(before, after, 1)


def apply_matching(files: dict[str, bytes]) -> dict:
    if b'// HYBRID-MATCHING:v1' in files['assets/servis-search.js']:
        return {'status':'already-applied'}
    # Only existing local HTML targets can be returned. No query creates a URL.
    routes = sorted(n for n in files if re.fullmatch(r'[a-z0-9-]+\.html', n)
                    and n not in {'owner-admin.html','404.html','servis-takip.html'}
                    and not n.startswith(('google','yandex')))
    files['assets/hybrid-routes.json'] = json.dumps(routes, ensure_ascii=False, separators=(',',':')).encode()
    data = json.loads(files['assets/servis-katalog.json'])
    aliases = data.setdefault('brand_aliases', {})
    for name, terms in {'Vaillant':['vailant','vaylant'], 'Bosch':['bosh','boch']}.items():
        aliases[name] = list(dict.fromkeys(aliases.get(name, []) + terms))
    additions = {
        'kombi-su-akitiyor.html':['altından su geliyor','kombi altından su geliyor','su sızdırıyor'],
        'kombi-atesleme.html':['ateşleme arızası','ateşleme hatası','ateş almıyor'],
    }
    for row in data['devices']['kombi']['symptoms']:
        if row['path'] in additions:
            row['terms'] = list(dict.fromkeys(row.get('terms', []) + additions[row['path']]))
    for name in ['assets/servis-katalog.json']:
        files[name] = json.dumps(data, ensure_ascii=False, separators=(',',':')).encode()
    service_js = ('window.ST_SERVICE_DATA=' + json.dumps(data, ensure_ascii=False, separators=(',',':')) + ';\n').encode()
    files['assets/servis-verileri.js'] = service_js
    if 'servis-verileri.js' in files:
        files['servis-verileri.js'] = service_js

    name = 'assets/servis-search.js'
    js = files[name].decode()
    if 'const routeKey =' not in js:
        raise ValueError('Apply preview-release/route_correction.py before hybrid matching')
    js = js.replace("'use strict';", "'use strict';\n// HYBRID-MATCHING:v1", 1)
    js = _replace(js, '  const best = entries => {', '  const best = (entries, unordered = false) => {\n    const words = new Set(q.split(/\\s+/));', name=name)
    js = _replace(js,
        '      if (n.length > length && has(n)) { chosen = entry; length = n.length; }',
        '      const tokens = n.split(/\\s+/);\n      const tokenMatch = unordered && tokens.length > 1 && tokens.every(word => words.has(word));\n      if (n.length > length && (has(n) || tokenMatch)) { chosen = entry; length = n.length; }', name=name)
    js = _replace(js,
        "  if (locality?.name === '500 Evler' && !districtEntry) { district = ''; neighborhood = ''; ambiguous = true; }",
        "  if (locality?.name === '500 Evler' && !districtEntry) { district = ''; neighborhood = ''; ambiguous = true; }\n"
        '  // These are also Istanbul districts outside our service area; do not silently treat them as a European neighborhood.\n'
        '  const outsideDistrict = ' + json.dumps(OUTSIDE_DISTRICTS, ensure_ascii=False) + '.some(has);\n'
        "  if (outsideDistrict && !districtEntry) { district = ''; neighborhood = ''; ambiguous = true; }", name=name)
    js = _replace(js, '  const symptom = best(device.symptoms), service = best(device.services.slice(1));',
        "  const symptom = best(device.symptoms, true), service = best(device.services.slice(1), true);\n"
        "  const petekIntent = kind === 'kombi' && ['petek temizligi','petek yikama','radyator temizligi'].some(has);\n"
        "  const petekPath = petekIntent ? 'petek-temizligi.html' : '';", name=name)
    js = _replace(js,
        "  const path = found ? errorPath || symptom?.path || service?.path || localityPath || districtPath\n    || brandPath || device.services[0].path : '';",
        '  const available = new Set(' + json.dumps(routes, ensure_ascii=False, separators=(',',':')) + ');\n'
        "  const safePath = value => { const file = routeKey(String(value || '').split(/[?#]/)[0]); return file && available.has(file) ? file + String(value || '').slice(String(value || '').split(/[?#]/)[0].length) : ''; };\n"
        "  const candidate = found ? errorPath || petekPath || symptom?.path || service?.path || localityPath || districtPath\n    || brandPath || device.services[0].path : '';\n"
        "  const path = safePath(candidate) || (found ? safePath(device.services[0].path) : '');", name=name)
    js = _replace(js, 'symptom:symptom?.name || \'\', service_path:service?.path || device.services[0].path,',
        "symptom:symptom?.name || '', service_path:safePath(petekPath || service?.path || device.services[0].path),", name=name)
    js = _replace(js, '    error_guide_path:errorPath,', '    error_guide_path:safePath(errorPath),', name=name)
    js = _replace(js, 'const found = !!(explicit || brand || district || neighborhood || locality || symptom || service || errorIntent);',
        'const found = !!(explicit || brand || district || neighborhood || locality || symptom || service || petekIntent || errorIntent);', name=name)
    files[name] = js.encode()

    name = 'api.php'; php = files[name].decode()
    php = _replace(php, 'function st_best_match(string $q,array $entries): ?array {\n    $best=null;$length=-1;',
        'function st_best_match(string $q,array $entries,bool $unordered=false): ?array {\n    $best=null;$length=-1;$words=array_fill_keys(preg_split(\'/\\s+/\',$q),true);', name=name)
    php = _replace(php,
        '        if(strlen($normalized)>$length&&st_contains($q,$normalized)){$best=$entry;$length=strlen($normalized);}',
        "        $tokens=preg_split('/\\s+/',$normalized);$token_match=$unordered&&count($tokens)>1;\n"
        "        if($token_match)foreach($tokens as $word)if(!isset($words[$word])){$token_match=false;break;}\n"
        '        if(strlen($normalized)>$length&&(st_contains($q,$normalized)||$token_match)){$best=$entry;$length=strlen($normalized);}', name=name)
    php = _replace(php,
        "    if(($locality['name']??'')==='500 Evler'&&!$district_entry){$district='';$neighborhood='';$ambiguous=true;}",
        "    if(($locality['name']??'')==='500 Evler'&&!$district_entry){$district='';$neighborhood='';$ambiguous=true;}\n"
        '    $outside_district=false;foreach(json_decode(\'' + json.dumps(OUTSIDE_DISTRICTS, ensure_ascii=False) + "',true) as $outside)if(st_contains($q,$outside))$outside_district=true;\n"
        "    if($outside_district&&!$district_entry){$district='';$neighborhood='';$ambiguous=true;}", name=name)
    php = _replace(php,
        "    $fault_model_path=$fault['model']['path']??'';\n    if(!preg_match('~^/[a-z0-9-]+\\.html$~D',$fault_model_path))$fault_model_path='';",
        "    $route_key=static function($value){$path=preg_replace('~^(?:\\./|/)~','',(string)$value);return preg_match('~^[a-z0-9-]+\\.html$~D',$path)?$path:'';};\n"
        "    $fault_model_path=$route_key($fault['model']['path']??'');", name=name)
    php = _replace(php,
        "    $symptom=st_best_match($q,$device['symptoms']);$service=st_best_match($q,array_slice($device['services'],1));\n    $allowed=array_fill_keys($organic['published_routes']??[],true);",
        "    $symptom=st_best_match($q,$device['symptoms'],true);$service=st_best_match($q,array_slice($device['services'],1),true);\n"
        "    $petek_intent=$kind==='kombi'&&(st_contains($q,'petek temizligi')||st_contains($q,'petek yikama')||st_contains($q,'radyator temizligi'));\n"
        "    $petek_path=$petek_intent?'petek-temizligi.html':'';\n"
        "    $allowed=array_fill_keys(array_filter(array_map($route_key,$organic['published_routes']??[])),true);", name=name)
    for kind in ['district','locality','brand']:
        php = _replace(php, f"${kind}_path=isset($allowed[${kind}_candidate])?${kind}_candidate:'';",
            f"${kind}_path=isset($allowed[$route_key(${kind}_candidate)])?$route_key(${kind}_candidate):'';", name=name)
    php = _replace(php,
        "    $path=$error_path?:($symptom['path']??($service['path']??($locality_path?:($district_path?:($brand_path?:$device['services'][0]['path'])))));",
        "    $candidate=$error_path?:($petek_path?:($symptom['path']??($service['path']??($locality_path?:($district_path?:($brand_path?:$device['services'][0]['path']))))));\n"
        "    $available_raw=@file_get_contents(__DIR__.'/assets/hybrid-routes.json');$available=json_decode(is_string($available_raw)?$available_raw:'[]',true);\n"
        "    $available=array_fill_keys(is_array($available)?$available:[],true);\n"
        "    $safe_path=static function($value)use($route_key,$available){$raw=preg_split('/[?#]/',(string)$value)[0];$file=$route_key($raw);return $file!==''&&isset($available[$file])?$file.substr((string)$value,strlen($raw)):'';};\n"
        "    $path=$safe_path($candidate)?:$safe_path($device['services'][0]['path']);", name=name)
    php = _replace(php, "'service_path'=>$service['path']??$device['services'][0]['path'],",
        "'service_path'=>$safe_path($petek_path?:($service['path']??$device['services'][0]['path'])),", name=name)
    php = _replace(php, "'error_guide_path'=>$error_path,", "'error_guide_path'=>$safe_path($error_path),", name=name)
    php = _replace(php, '$found=(bool)($explicit||$brand||$district||$neighborhood||$locality||$symptom||$service||$error_intent);',
        '$found=(bool)($explicit||$brand||$district||$neighborhood||$locality||$symptom||$service||$petek_intent||$error_intent);', name=name)
    files[name] = php.encode()

    for name in ['assets/servis-sec.js', 'servis-sec.js']:
        if name not in files: continue
        text = files[name].decode()
        text = text.replace('Aynı adlı birden fazla mahalle var. İlçenizi seçip konumu tamamlayın.',
                            'Bu konum birden fazla bölgeyi ifade edebilir. Avrupa Yakası ilçenizi seçerek konumu netleştirin.')
        text = text.replace('Tam modeli kontrol edin; E1 ve E01 gibi farklı kodlar birleştirilmez.',
                            'Anlam seçilen modelin belgesine göre belirlenir; E1/E01 gibi yazımlar yalnız aynı modelde tek ve çelişkisiz kayda karşılık gelirse eşleştirilir.')
        files[name] = text.encode()
    return {'status':'applied','files':['assets/servis-search.js','api.php','assets/servis-katalog.json','assets/servis-verileri.js','assets/servis-sec.js','assets/hybrid-routes.json'],
            'actual_html_route_gate':len(routes),'unordered_matching':'symptom/service phrases only; not model inference',
            'preserved':['model-scoped fault definitions','flexKey E1/E01 F4/F04','unknown-model code refusal','deterministic gas/fire/explosive-ignition handling'],
            'limits':['bounded phrase synonyms are not a Google ranking guarantee','short ambiguous brand typos such as bos are not guessed']}
