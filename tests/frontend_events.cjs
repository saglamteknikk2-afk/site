/* Focused browser-runtime contracts. Fetch is synthetic; no provider or DB claim. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const source=fs.readFileSync(path.join(__dirname,'../overrides/assets/site.js'),'utf8');
const checks=[];
function check(name,condition){assert(condition,name);checks.push({name,passed:true});}
function runtime(options={}){
 const events={window:{},document:{}},requests=[],failures={};
 const add=(target,type,handler)=>(events[target][type]||=([])).push(handler);
 const context={URL,URLSearchParams,AbortController,Intl,Date,Promise,Map,JSON,String,Object,Error,crypto,
  location:{protocol:options.preview?'https:':'http:',href:'http://localhost/index.html?arama=Baymak+E1&phone=private',pathname:'/index.html',search:'?arama=Baymak+E1&phone=private',hostname:'localhost'},
  document:{currentScript:{src:'http://localhost/assets/site.js'},referrer:'https://www.google.com/search?q=boiler',visibilityState:'visible',addEventListener:(type,handler)=>add('document',type,handler)},
  ST_PREVIEW:!!options.preview,STEnvironment:{preview:!!options.preview,href:value=>new URL(value,'http://localhost/').href},
  addEventListener:(type,handler)=>add('window',type,handler),
  setTimeout:(handler,delay)=>delay===1000?setTimeout(handler,0):setTimeout(handler,delay),clearTimeout,
  sessionStorage:{getItem(){throw Error('A forever session-storage flag must not suppress visits');}},
  fetch:async(url,request={})=>{
   const action=new URL(url).searchParams.get('action');requests.push({action,headers:request.headers,body:request.body?JSON.parse(request.body):null});
   if(options.failOnce===action&&!failures[action]){failures[action]=true;throw Error('Synthetic connection failure');}
   return {ok:true,json:async()=>action==='bootstrap'?{ok:true,csrf:'1700000000.'+'a'.repeat(64)}:{ok:true,recorded:true}};
  }
 };
 context.window=context;context.globalThis=context;vm.createContext(context);vm.runInContext(source,context);
 return {context,requests,events};
}
(async()=>{
 const main=runtime(),c=main.context;
 const result={device:'Kombi',brand:'Baymak',model:'Lambert LPY',model_id:'model-1',issue:'E1 uyarısı var',answer:'E01 · Ateşleme\nGüvenli gözlem\nEtiketi okuyun.',source:'manual',code:'E1'};
 await c.stRecordAIResult(result);await c.stRecordAIResult({...result});
 let recorded=main.requests.filter(r=>r.action==='activity');
 check('An unchanged completed answer is recorded once',recorded.length===1);
 check('The displayed multiline answer is sent without replacing it with a generic guide',recorded[0].body.answer===result.answer);
 check('Model, source and entered code are preserved',recorded[0].body.model_id==='model-1'&&recorded[0].body.source==='manual'&&recorded[0].body.code==='E1');
 check('Activity body and idempotency header use the same stable event key',recorded[0].body.event_id===recorded[0].headers['Idempotency-Key']);
 await c.stRecordAIResult({...result,activity_recorded:true,answer:'Server already recorded this answer'});
 check('An answer already saved by the AI endpoint does not generate a second event',main.requests.filter(r=>r.action==='activity').length===1);
 await c.stRecordAIResult({...result,source:'guide',answer:'Yerel belirti rehberi'});
 check('A new local guide has its own event and keeps the guide source',main.requests.filter(r=>r.action==='activity').at(-1).body.source==='guide'&&main.requests.filter(r=>r.action==='activity').length===2);
 await c.stRecordAIResult({...result,source:'unrecognized',answer:'Unknown'});
 check('Unsupported source labels are not sent as verified AI activity',main.requests.filter(r=>r.action==='activity').length===2);
 await c.stRecordAIResult({...result,source:'ai',activity_id:'ai:synthetic-receipt',activity_token:'synthetic-signed-token',answer:'Son ekranda gösterilen sunucu cevabı ve sonraki adım.'});
 const acknowledged=main.requests.filter(r=>r.action==='activity').at(-1).body;
 check('A final server answer retains its signed generation receipt',acknowledged.server_activity_id==='ai:synthetic-receipt'&&acknowledged.server_activity_token==='synthetic-signed-token');
 check('The display acknowledgement retains the entire rendered text',acknowledged.answer==='Son ekranda gösterilen sunucu cevabı ve sonraki adım.');
 const retry=runtime({failOnce:'activity'});await retry.context.stRecordAIResult(result);
 const attempts=retry.requests.filter(r=>r.action==='activity');
 check('A temporary connection error gets one bounded retry',attempts.length===2);
 check('Retries reuse both the event ID and the exact answer payload',JSON.stringify(attempts[0])===JSON.stringify(attempts[1]));
 const visits=runtime();await visits.context.stRecordVisit();await visits.context.stRecordVisit();
 let rows=visits.requests.filter(r=>r.action==='visit');
 check('One document sends one page-view event even if initialization runs again',rows.length===1);
 check('A visit includes its entering page and referrer class',rows[0].body.page==='/index.html'&&rows[0].body.source==='google');
 check('Only a recognized site search is copied, not arbitrary URL parameters',rows[0].body.query==='Baymak E1'&&!JSON.stringify(rows[0].body).includes('private'));
 const firstID=rows[0].body.event_id;await visits.context.stRecordVisit(true);rows=visits.requests.filter(r=>r.action==='visit');
 check('A genuine return creates a new total-visit event',rows.length===2&&rows[1].body.event_id!==firstID);
 for(const handler of visits.events.window.pageshow||[])handler({persisted:true});await visits.context.stRecordVisit();
 check('Restoring a page from browser history records a return visit',visits.requests.filter(r=>r.action==='visit').length===3);
 const nextDocument=runtime();await nextDocument.context.stRecordVisit();
 check('Reloading the document produces a new event rather than a lifetime session flag',nextDocument.requests.find(r=>r.action==='visit').body.event_id!==firstID);
 const preview=runtime({preview:true});await preview.context.stRecordVisit();await preview.context.stRecordAIResult(result);
 check('Preview makes zero bootstrap, activity or visit requests',preview.requests.length===0);
 const local=runtime();local.context.location.protocol='file:';await local.context.stRecordVisit();await local.context.stRecordAIResult(result);
 check('Opening files locally cannot record activity or visits',local.requests.length===0);
 const report={passed:true,checks:checks.length,cases:checks,provider_requests:0,policy:'Synthetic fetch only; not a real Telegram/API delivery test.'};
 const output=path.join(__dirname,'../build/frontend-events-report.json');fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:true,checks:checks.length,provider_requests:0}));
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
