/* Exhaustive registered-row browser runtime audit. Local public data; no network. */
'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path');
const root=path.resolve(__dirname,'..');
const site=path.resolve(process.argv[2]||path.join(root,'build/production'));
const data=JSON.parse(fs.readFileSync(path.join(site,'assets/verified-faults.json'),'utf8'));
const context={window:{}};vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(site,'assets/verified-faults.js'),'utf8'),context);
for(const name of ['fault-lookup.js','diagnostic-guide.js'])vm.runInContext(fs.readFileSync(path.join(site,'assets',name),'utf8'),context);
const result=[];
for(const m of data.models)for(const c of m.codes)for(const code of [c.code,...c.equivalent_codes]){
 const input={device:m.device,brand:m.brand,model_id:m.id,code};
 const found=context.window.STFaults.lookup(input);
 const answer=context.window.STDiagnosticGuide(m.device==='klima'?'Klima':'Kombi','hata kodu '+code,input);
 result.push({model_id:m.id,input:code,status:found.status,code:found.code,meaning:found.definition?.meaning||null,source:answer?.source,source_url:answer?.source_url||null,text:answer?.text||null});
}
const scope=[];
for(const m of data.models){
 const code=m.codes.find(c=>c.matchable!==false&&!c.source_conflict)?.code||'E99';
 for(const [kind,input]of [
  ['missing-model',{device:m.device,brand:m.brand,code}],
  ['wrong-brand',{device:m.device,brand:'__unsupported_brand__',model_id:m.id,code}],
  ['wrong-device',{device:m.device==='klima'?'kombi':'klima',brand:m.brand,model_id:m.id,code}],
 ]){const r=context.window.STFaults.lookup(input);scope.push({model_id:m.id,kind,status:r.status,verified:r.verified,meaning:r.definition?.meaning||null});}
}
console.log(JSON.stringify({rows:result,scope}));
