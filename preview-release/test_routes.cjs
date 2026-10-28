'use strict';
// Offline regression of the browser-loaded helpers. No DOM/provider requests.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = process.argv[2];
if (!root) throw new Error('Usage: node test_routes.cjs <preview-webroot> [report.json]');
const sandbox = {window:{}};
vm.createContext(sandbox);
const chain = ['assets/servis-verileri.js','assets/organic-catalog.js','assets/verified-faults.js','assets/fault-lookup.js','assets/servis-search.js'];
for (const name of chain) vm.runInContext(fs.readFileSync(path.join(root,name),'utf8'),sandbox,{filename:name,timeout:1000});
const w = sandbox.window;
const cases = [
  ['Küçükçekmece Baymak kombi servisi','kucukcekmece-kombi-servisi.html'],
  ['kombi servisi Baymak Küçükçekmece','kucukcekmece-kombi-servisi.html'],
  ['Küçükçekmcece Baymak kombi servisi','kucukcekmece-kombi-servisi.html'],
  ['Avcılar Bosch kombi servisi','avcilar-kombi-servisi.html'],
  ['Baymak kombi servisi','baymak-kombi-servisi.html'],
  ['Sefaköy kombi servisi','sefakoy-servisi.html'],
  ['Avcılar Bosch kombi sıcak su vermiyor','kombi-sicak-su.html'],
  ['Vaillant ecoTEC pro VUW TR 236/5-3 F22 hata kodu','vaillant-kombi-ecotec-pro-236-286-5-3-ariza-kodlari.html#kod-f22'],
  ['Baymak Duotec 33 E1 hata kodu','baymak-kombi-duotec-33-42-45-ariza-kodlari.html#kod-e01'],
  ['Baymak Duotec 33 E01 hata kodu','baymak-kombi-duotec-33-42-45-ariza-kodlari.html#kod-e01'],
];
const results = [];
for (const [query,expected] of cases) {
  const r = w.STResolveQuery(w.ST_SERVICE_DATA,query,'');
  assert.equal(r.path,expected,query);
  assert(!r.path.startsWith('/'),query+' must be document-relative');
  const file = r.path.split(/[?#]/)[0];
  assert(fs.existsSync(path.join(root,file)),query+' target must exist');
  const anchor = r.path.split('#')[1];
  if (anchor) assert(new RegExp('id=["\']'+anchor+'["\']').test(fs.readFileSync(path.join(root,file),'utf8')),query+' anchor must exist');
  for (const mount of ['/', '/site/', '/custom/mount/']) {
    const url = new URL(r.path,'https://preview.example'+mount+'index.html');
    assert.equal(url.pathname,mount+file,query+' mount '+mount);
  }
  results.push({query,path:r.path,verified:r.code_definition_verified,model_id:r.model_id,error_code:r.error_code});
}
const e1 = w.STResolveQuery(w.ST_SERVICE_DATA,'Baymak Duotec 33 E1 hata kodu','');
const e01 = w.STResolveQuery(w.ST_SERVICE_DATA,'Baymak Duotec 33 E01 hata kodu','');
const e10 = w.STResolveQuery(w.ST_SERVICE_DATA,'Baymak Duotec 33 E10 hata kodu','');
assert.equal(e1.fault_meaning,e01.fault_meaning);
assert.notEqual(e1.path,e10.path,'E10 must remain a different scoped fault');
const unknown = w.STResolveQuery(w.ST_SERVICE_DATA,'ECA e99 kombi hatası','');
assert.equal(unknown.code_definition_verified,false,'Unknown model must not invent E99 meaning');
assert.equal(unknown.fault_meaning,'');
// Catalogue with rooted spellings is equivalent to the actual relative archive.
const original = w.ST_ORGANIC_CATALOG.published_routes;
w.ST_ORGANIC_CATALOG.published_routes = original.map(p => '/'+p.replace(/^\//,''));
assert.equal(w.STResolveQuery(w.ST_SERVICE_DATA,'Küçükçekmece Baymak kombi servisi','').path,cases[0][1]);
w.ST_ORGANIC_CATALOG.published_routes = original;
const report = {scope:'Offline execution of actual browser helpers; excludes live browser, Google, PHP, Gemini, Telegram delivery.',route_cases:results,mounts:['/','/site/','/custom/mount/'],safety_regressions:['E1/E01 same scoped fact','E10 remains distinct','unknown model E99 remains unverified'],status:'passed'};
if (process.argv[3]) fs.writeFileSync(process.argv[3],JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
