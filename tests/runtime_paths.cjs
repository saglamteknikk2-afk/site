/* No browser or network: exercise diagnostic href assignment and compiled-source paths. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),source=fs.readFileSync(path.join(root,'overrides/assets/home.js'),'utf8');
const checks=[];
function diagnostic(prefix,script=source){
  const base=prefix+'/',origin='https://preview.example',documentURL=origin+base+'index.html';
  const resolved=value=>new URL(value,documentURL).href;
  const elements={aiResultBox:{classList:{remove(){}}},aiResponseText:{},deviceSelect:{value:'Klima'},issueInput:{value:'klima soğutmuyor'},aiSource:{},aiGuideLink:{href:''}};
  const context={window:{addEventListener(){},ST_ORGANIC_CATALOG:{published_routes:[base+'klima-sogutmuyor.html',base+'model-ariza-kodlari.html']},ST_DIAGNOSTIC_DATA:[{path:base+'kombi-sicak-su.html'}],ST_VERIFIED_FAULTS:{models:[{path:base+'bosch-kombi-condens-2300i-w-ariza-kodlari.html'}]}},document:{baseURI:documentURL,addEventListener(){},getElementById:id=>elements[id]||null,querySelector:selector=>selector==='.at-header .at-brand[href]'?{getAttribute:()=>base}:null},location:{origin,href:documentURL,pathname:base+'index.html'},URL,stAiContact(){},stEscape:String};
  vm.createContext(context);vm.runInContext(script,context);
  const valid=[
    ['/klima-sogutmuyor.html',base+'klima-sogutmuyor.html'],
    ['klima-sogutmuyor.html',base+'klima-sogutmuyor.html'],
    [base+'klima-sogutmuyor.html',base+'klima-sogutmuyor.html'],
    [origin+base+'klima-sogutmuyor.html',base+'klima-sogutmuyor.html'],
    ['/kombi-sicak-su.html',base+'kombi-sicak-su.html'],
    [base+'bosch-kombi-condens-2300i-w-ariza-kodlari.html#kod-227',base+'bosch-kombi-condens-2300i-w-ariza-kodlari.html#kod-227'],
    [base+'model-ariza-kodlari.html?device=klima',base+'model-ariza-kodlari.html?device=klima']
  ];
  for(const [input,expected] of valid){context.renderDiagnostic({source:'guide',guide_path:input,text:'Test'});assert.equal(resolved(elements.aiGuideLink.href),resolved(expected),input);}
  for(const input of ['https://outside.example/klima-sogutmuyor.html','//outside.example/klima-sogutmuyor.html','javascript:alert(1)','/unpublished-guide.html',base+'missing/model.html',base+'klima-sogutmuyor.html#bad%20anchor','https://user:password@preview.example'+base+'klima-sogutmuyor.html'])assert.equal(resolved(context.stDiagnosticGuideURL(input)),resolved(base+'ariza-rehberi.html'),input);
  context.renderDiagnostic({source:'guide',text:'No guide'});assert.equal(resolved(elements.aiGuideLink.href),resolved(base+'ariza-rehberi.html'));
  checks.push({base,diagnostic_cases:valid.length+8,published_guides_retained:true,unknown_or_external_rejected:true});
}
for(const prefix of ['', '/site','/preview/v2'])diagnostic(prefix);
// Optional generated tree exercises the exact JS shipped by the builder too.
if(process.argv[2]){
  const built=path.resolve(process.argv[2]),prefix=(process.argv[3]||'').replace(/\/$/,'');
  diagnostic(prefix,fs.readFileSync(path.join(built,'assets/home.js'),'utf8'));
  const atelier=fs.readFileSync(path.join(built,'assets/atelier.js'),'utf8');
  const helper=atelier.match(/function normalizedPath\(path\)\s*\{[^}]*\}/);
  assert.ok(helper,'Built atelier path helper exists');
  const context={};vm.createContext(context);vm.runInContext(helper[0],context);
  for(const base of ['/',prefix+'/',prefix+'/nested/'])assert.equal(context.normalizedPath(base),context.normalizedPath(base+'index.html'),base);
  checks.push({built,prefix,atelier_index_and_directory_equivalent:true});
}
console.log(JSON.stringify({passed:checks.length,checks},null,2));
