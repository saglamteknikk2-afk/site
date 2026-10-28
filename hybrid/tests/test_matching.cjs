'use strict';
// Execute the shipped browser helpers, without a DOM or provider/network calls.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=process.argv[2];if(!root)throw Error('Usage: node test_matching.cjs <webroot> [report.json]');
const ctx={window:{}};vm.createContext(ctx);
for(const n of ['assets/servis-verileri.js','assets/organic-catalog.js','assets/verified-faults.js','assets/fault-lookup.js','assets/servis-search.js','assets/diagnostic-guide.js'])vm.runInContext(fs.readFileSync(path.join(root,n),'utf8'),ctx,{filename:n});
const w=ctx.window,resolve=q=>w.STResolveQuery(w.ST_SERVICE_DATA,q,'');
const cases=[
 ['Küçükçekmece Baymak kombi servisi','kucukcekmece-kombi-servisi.html'],
 ['kombi servisi Baymak Küçükçekmece','kucukcekmece-kombi-servisi.html'],
 ['Küçükçekmcece Baymak kombi servisi','kucukcekmece-kombi-servisi.html'],
 ['Baymak kombi servisi','baymak-kombi-servisi.html'],
 ['Sefaköy kombi servisi','sefakoy-servisi.html'],
 ['Avcılar Bosch kombi sıcak su vermiyor','kombi-sicak-su.html'],
 ['Avcılar Bosch kombi vermiyor sıcak su','kombi-sicak-su.html'],
 ['Baymak kombi altından su geliyor','kombi-su-akitiyor.html'],
 ['Şişli Vaillant kombi ateşleme arızası','kombi-atesleme.html'],
 ['Küçükçekmece petek temizliği','petek-temizligi.html'],
 ['petek yıkama','petek-temizligi.html'],
 ['Vaillant ecoTEC pro VUW TR 236/5-3 F22 hata kodu','vaillant-kombi-ecotec-pro-236-286-5-3-ariza-kodlari.html#kod-f22'],
 ['Baymak Duotec 33 E1 hata kodu','baymak-kombi-duotec-33-42-45-ariza-kodlari.html#kod-e01'],
 ['Baymak Duotec 33 E01 hata kodu','baymak-kombi-duotec-33-42-45-ariza-kodlari.html#kod-e01'],
];
const results=[];
for(const [query,expected] of cases){const r=resolve(query);assert.equal(r.path,expected,query);const [file,anchor]=r.path.split('#');assert(fs.existsSync(path.join(root,file)));if(anchor)assert(new RegExp('id=["\']'+anchor+'["\']').test(fs.readFileSync(path.join(root,file),'utf8')));for(const mount of ['/','/site/','/custom/mount/'])assert.equal(new URL(r.path,'https://preview.example'+mount+'index.html').pathname,mount+file);results.push({query,path:r.path,district:r.district,neighborhood:r.neighborhood,brand:r.brand,ambiguous_neighborhood:r.ambiguous_neighborhood,verified:r.code_definition_verified});}
for(const query of ['Maltepe kombi servisi','Kadıköy İstanbul kombi','Cumhuriyet kombi servisi','500 Evler kombi']){const r=resolve(query);assert.equal(r.ambiguous_neighborhood,true,query);assert.equal(r.neighborhood,'',query);results.push({query,path:r.path,district:r.district,neighborhood:r.neighborhood,brand:r.brand,ambiguous_neighborhood:r.ambiguous_neighborhood,verified:r.code_definition_verified});}
for(const [query,district] of [['Beşiktaş Arnavutköy kombi','Beşiktaş'],['Silivri Kadıköy kombi','Silivri'],['Zeytinburnu Maltepe kombi','Zeytinburnu']])assert.equal(resolve(query).district,district,query);
assert.equal(resolve('Şişli vailant kombi servisi').brand,'Vaillant');
assert.equal(resolve('ekran bos kombi').brand,'','Do not mistake an empty display for the Bosch brand');
const e1=resolve('Baymak Duotec 33 E1 hata kodu'),e01=resolve('Baymak Duotec 33 E01 hata kodu'),e10=resolve('Baymak Duotec 33 E10 hata kodu');
assert.equal(e1.path,e01.path);assert.notEqual(e1.path,e10.path);assert.equal(resolve('ECA E99 kombi').code_definition_verified,false);assert.equal(resolve('ECA E99 kombi').fault_meaning,'');
const f4Model=w.ST_VERIFIED_FAULTS.models.find(m=>m.codes.some(c=>['F4','F04','F.04'].includes(c.code)&&!c.source_conflict&&c.matchable!==false));assert(f4Model);
const f4=w.STFaults.lookup({device:f4Model.device,brand:f4Model.brand,model_id:f4Model.id,code:'F4'}),f04=w.STFaults.lookup({device:f4Model.device,brand:f4Model.brand,model_id:f4Model.id,code:'F04'});assert.equal(f4.verified,true);assert.equal(f04.verified,true);assert.equal(f4.definition.meaning,f04.definition.meaning);
let districtCases=0;for(const d of w.ST_SERVICE_DATA.districts)for(const b of w.ST_SERVICE_DATA.devices.kombi.brands){const r=resolve(d+' '+b+' kombi servisi');assert.equal(r.district,d);assert.equal(r.brand,b);assert(fs.existsSync(path.join(root,r.path)));districtCases++;}
let neighborhoodCases=0;for(const n of w.ST_SERVICE_DATA.neighborhoods){const r=resolve(n.district+' '+n.name+' kombi servisi');assert.equal(r.district,n.district,JSON.stringify(n));assert.equal(r.neighborhood,n.name,JSON.stringify(n));neighborhoodCases++;}
const safety=w.STDiagnosticGuide('Kombi','kombi yanarken patlama yaparak yanıyor');assert.equal(safety.source,'safety');assert.match(safety.text,/resetlemeyin|resetlemeyin/i);assert.doesNotMatch(safety.text,/pompa/);
assert.equal(w.STDiagnosticGuide('Kombi','Baymak Duotec 33 E01 ve ilk yanışta patlama',{brand:'Baymak',model_id:'baymak-kombi-duotec-33-42-45',code:'E01'}).source,'safety');
assert.equal(w.STDiagnosticGuide('Kombi','gaz kokusu geliyor').emergency_phone,'187');assert.equal(w.STDiagnosticGuide('Kombi','duman çıkıyor').emergency_phone,'112');
const report={scope:'Actual shipped JS resolver and deterministic guides only; excludes Google/provider delivery',results,district_brand_cases:districtCases,neighborhood_cases:neighborhoodCases,status:'passed'};
if(process.argv[3])fs.writeFileSync(process.argv[3],JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,queries:results.length,district_brand_cases:districtCases,neighborhood_cases:neighborhoodCases}));
