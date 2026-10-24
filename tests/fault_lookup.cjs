/* Model-scoped matching regression; synthetic documents, no browser or network. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const repository=path.resolve(__dirname,'..');
const row=(code,meaning,extra={})=>({code,meaning,safe_observation:'Sentetik gözlem',anchor:'test-code',source_url:'https://manual.invalid/test',...extra});
const model=(id,codes,extra={})=>({id,device:'kombi',brand:'Fixture',label:id,model_names:[id],aliases:[],path:id+'.html',manual:{url:'https://manual.invalid/'+id,title:'Sentetik belge'},codes,...extra});
const models=[
 model('fixture-main',[row('E01','Ana model ateşleme'),row('E10','Ana model basınç'),row('F04','Ana model fan'),row('227','Sayısal kod')]),
 model('fixture-other',[row('E09','Yalnız diğer modelde'),row('E01','Diğer model açıklaması')]),
 model('fixture-brand',[row('E01','Başka marka açıklaması')],{brand:'Other'}),
 model('fixture-climate',[row('E01','Klima açıklaması')],{device:'klima'}),
 model('fixture-padding-conflict',[row('E1','Birinci açıklama'),row('E01','İkinci açıklama')]),
 model('fixture-source-conflict',[row('F04','Çelişkili kaynak',{source_conflict:true})]),
 model('fixture-foreign',[row('E01','Yabancı belge açıklaması')],{requires_scope_confirmation:true,market:'BR'}),
 model('fixture-controller',[row('F04','Seçilen kontrol belgesi açıklaması'),row('E02','Eşleştirilmeyen örüntü',{matchable:false})],{matchable:false,requires_document_match:true,requires_scope_confirmation:true,market:'TR'}),
 model('fixture-equivalent',[row('F04','Belgede açık eşdeğer',{equivalent_codes:['F4']})]),
];
const context={window:{ST_VERIFIED_FAULTS:{models,coverage:[]}}};vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(repository,'overrides/assets/fault-lookup.js'),'utf8'),context);
const api=context.window.STFaults;let checks=0;const results=[];
function check(name,test){checks++;assert(test,name);results.push({name,passed:true});}
const lookup=(code,model_id='fixture-main',extra={})=>api.lookup({device:'kombi',brand:'Fixture',model_id,code,...extra});
for(const input of ['E1','E01','E001']){const result=lookup(input);check(input+' resolves only inside selected model',result.verified&&result.code==='E01'&&result.definition.meaning==='Ana model ateşleme');check(input+' records exact/flexible provenance',result.code_match===(input==='E01'?'exact':'flexible'));}
for(const input of ['F4','F04','F004'])check(input+' zero-padding spelling resolves F04',lookup(input).verified&&lookup(input).code==='F04');
check('E10 does not collapse into E1',lookup('E10').definition.meaning==='Ana model basınç'&&api.flexKey('E10')!==api.flexKey('E1'));
check('Raw codeKey retains the display digits',api.codeKey('E1')!==api.codeKey('E01'));
check('flexKey folds only prefixed numeric leading zeros',api.flexKey('E1')===api.flexKey('E01')&&api.flexKey('F4')===api.flexKey('F04')&&api.flexKey('001')!==api.flexKey('1'));
check('Punctuation variant stays supported',lookup('F.04').verified&&lookup('F.04').code_match==='exact');
check('Exact E1 wins over competing padded spelling',lookup('E1','fixture-padding-conflict').definition.meaning==='Birinci açıklama');
check('Exact E01 wins over competing unpadded spelling',lookup('E01','fixture-padding-conflict').definition.meaning==='İkinci açıklama');
const ambiguous=lookup('E001','fixture-padding-conflict');check('Ambiguous flexible spelling does not pick a row',!ambiguous.verified&&ambiguous.status==='ambiguous-code'&&ambiguous.definition===null);
check('Source-conflicted row does not become a definition',lookup('F4','fixture-source-conflict').status==='source-conflict'&&lookup('F4','fixture-source-conflict').definition===null);
check('Other model meaning is never borrowed',lookup('E09').status==='code-not-covered'&&lookup('E09').definition===null);
check('Incompatible brand/model ID cannot infer another model',api.lookup({device:'kombi',brand:'Other',model_id:'fixture-main',query:'fixture-brand E01'}).status==='needs-model');
check('Incompatible device/model ID cannot infer another model',api.lookup({device:'klima',brand:'Fixture',model_id:'fixture-main',query:'fixture-climate E01'}).status==='needs-model');
check('Model-free code has no asserted definition',api.lookup({device:'kombi',brand:'Fixture',code:'E1'}).definition===null);
check('Foreign selected document answers without checkbox',lookup('E1','fixture-foreign').verified&&lookup('E1','fixture-foreign',{scope_confirmed:false}).verified);
check('Country warning remains nonblocking and explicit',lookup('E1','fixture-foreign').scope_warning.includes('BR')&&lookup('E1','fixture-foreign').scope_warning.includes('Türkiye varyantı doğrulaması değildir'));
check('Explicit controller/document selection answers without checkbox',lookup('F4','fixture-controller').verified&&lookup('F4','fixture-controller').scope_warning.length>0);
check('Generic controller label is never auto-inferred',api.infer('fixture-controller F4','kombi','Fixture')===null);
check('Unmatchable row remains excluded from selected document',lookup('E02','fixture-controller').status==='code-not-covered');
check('Explicit documented equivalent is exact before flexible fallback',lookup('F4','fixture-equivalent').verified&&lookup('F4','fixture-equivalent').code_match==='exact');
check('Extract preserves zero-padding fallback provenance',api.extract('hata kodu E1',models[0])==='E1'&&api.lookup({device:'kombi',brand:'Fixture',model_id:'fixture-main',query:'hata kodu E1'}).code_match==='flexible');
check('Extract keeps ambiguous spelling unresolved',api.lookup({device:'kombi',brand:'Fixture',model_id:'fixture-padding-conflict',query:'hata kodu E001'}).status==='ambiguous-code');
check('Bare temperature does not become numeric fault code',api.extract('sıcaklık 227 derece',models[0])==='');
check('Explicit numeric fault remains supported',api.extract('hata kodu 227',models[0])==='227');
vm.runInContext(fs.readFileSync(path.join(repository,'overrides/assets/diagnostic-guide.js'),'utf8'),context);
const guide=context.window.STDiagnosticGuide('Kombi','hata kodu E1',{brand:'Fixture',model_id:'fixture-foreign',code:'E1'});
check('Diagnostic result exposes selected foreign document immediately',guide.source==='manual'&&guide.code_match==='flexible'&&guide.scope_warning.includes('BR')&&guide.text.includes('Türkiye varyantı'));
const conflict=context.window.STDiagnosticGuide('Kombi','hata kodu E001',{brand:'Fixture',model_id:'fixture-padding-conflict',code:'E001'});
check('Ambiguous diagnostic asks for document review rather than selecting meaning',conflict.source==='guide'&&conflict.requires_document_review===true&&!conflict.text.includes('Birinci açıklama'));
check('Emergency priority still precedes manual matching',context.window.STDiagnosticGuide('Kombi','Gaz kokusu var',{brand:'Fixture',model_id:'fixture-main',code:'E1'}).emergency_phone==='187');
const missing=context.window.STDiagnosticGuide('Kombi','hata kodu E99',{brand:'Fixture',code:'E99'});
check('Missing model requests exact model without unrelated code examples',missing.requires_model===true&&missing.text.includes('E99')&&!missing.text.includes('E1/E01')&&!missing.code_definition_verified);
check('Explicit unknown model can finish with an honest guide',context.window.STDiagnosticGuide('Kombi','hata kodu E99',{brand:'Fixture',code:'E99',model_unknown:true}).requires_model===false);
const uncovered=context.window.STDiagnosticGuide('Kombi','hata kodu E99',{brand:'Fixture',model_id:'fixture-main',code:'E99'});
check('Unsupported selected-model code requires document review without borrowing another meaning',uncovered.requires_document_review===true&&uncovered.requires_model===false&&!uncovered.text.includes('Yalnız diğer modelde')&&!uncovered.code_definition_verified);
const report={passed:true,checks,results,provider_requests:0};const output=path.join(repository,'build/fault-lookup-report.json');fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:true,checks,provider_requests:0}));
