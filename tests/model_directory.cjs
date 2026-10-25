/* Model names may expand identification, never fault-code scope. No network. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),context={window:{},console};vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root,'overrides/assets/model-directory.js'),'utf8'),context);
const api=context.window.STModelDirectory;let checks=0;const check=(condition,message)=>{assert(condition,message);checks++;};
const vaillant=api.list('Kombi','Vaillant');
check(vaillant.length>=25,'Vaillant catalogue is no longer limited to two names');
check(api.list('klima','Vaillant').length>=10,'Vaillant klima model identification is available');
check(api.list('klima','Daikin').length>=10,'Daikin includes product series and exact catalogue names');
check(api.list('kombi','not-a-brand').length===0,'Unknown brand does not borrow another brand models');
check(api.list('petek','Vaillant').length===0,'Unsupported device does not borrow kombi data');
const pro=vaillant.find(row=>row.name==='VUW TR 236/5-3');check(!!pro?.verified_model_id,'Exact existing manual name retains its scope');
const intro=vaillant.find(row=>row.name==='ecoTEC intro VUW 24/24 AS/2-1 (H-TR)');check(intro&&!intro.verified_model_id,'Catalogue-only model cannot resolve to the pro manual');
vaillant[0].name='tampered';check(api.list('kombi','Vaillant')[0].name!=='tampered','Callers cannot mutate directory storage');
const coverage=api.coverage();coverage.gaps.length=0;check(api.coverage().gaps.length>0,'Coverage metadata is copied and honestly exposes gaps');
check(api.policy.complete_market_inventory===false&&api.policy.new_fault_definitions===0,'No unsupported universal completeness or added fault-code claim');
console.log(JSON.stringify({passed:true,checks,catalogue_entries:api.coverage().entries,vaillant_kombi_names:api.list('kombi','Vaillant').length,provider_requests:0}));
