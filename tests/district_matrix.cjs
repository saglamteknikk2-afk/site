/* Reviewed model/document-scoped matrix cells plus original district metadata.
 * The supplied PHP was parsed as text, never executed; unsafe generic code
 * equivalences were replaced with the reviewed source-scoped thirteen rows.
 * APIs/external requests are aborted. No hosting, provider or message requests.
 */
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {startServer,publicNames}=require('./interaction_http.cjs');
const repository=path.resolve(__dirname,'..');
const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/master-request.json'),'utf8'));
const output=path.resolve(process.env.MATRIX_OUTPUT||path.join(repository,'build/qa-master-matrix'));
const matrix=process.env.MATRIX_CASES?JSON.parse(process.env.MATRIX_CASES):[
 {label:'preview',directory:path.join(repository,'_site'),base:'/site'},
 {label:'production',directory:path.join(repository,'build/production'),base:''}
];
const norm=value=>String(value).replace(/\s+/g,' ').trim();
const fill=(text,district,neighborhoods)=>text.replaceAll('{$ilce}',district).replaceAll('{$mahalleMetni}',neighborhoods);
async function run(browser,entry){
 const directory=path.resolve(entry.directory),base=entry.base.replace(/\/$/,''),start=JSON.parse(fs.readFileSync(path.join(directory,'build-info.json'),'utf8'));
 const catalog=JSON.parse(fs.readFileSync(path.join(directory,'assets/verified-faults.json'),'utf8'));
 const modelsByPath=new Map();for(const model of catalog.models){const key=model.path.split('/').pop();if(!modelsByPath.has(key))modelsByPath.set(key,[]);modelsByPath.get(key).push(model);}
 const names=publicNames(directory),districts=names.filter(name=>/\bdata-page-kind=["']district["']/.test(fs.readFileSync(path.join(directory,name),'utf8')));
 assert.deepEqual(districts,fixture.district_routes,'All fifty established district routes must remain district pages');
 assert.equal(names.filter(name=>fs.readFileSync(path.join(directory,name),'utf8').includes('data-st-master-matrix=')).length,50,'Only the fifty intended district pages receive this matrix');
 const server=await startServer(directory,base),records=[],errors=[],pageErrors=[],httpErrors=[],blockedAPI=[],blockedExternal=[];let cursor=0;
 try{
  async function worker(){
   const ctx=await browser.newContext({viewport:{width:320,height:900},reducedMotion:'reduce',serviceWorkers:'block'});
   await ctx.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin!==server.origin){blockedExternal.push(u.href);return route.abort();}if(/\.php(?:$|\/)/i.test(u.pathname)){blockedAPI.push(u.pathname);return route.abort();}return route.continue();});
   const page=await ctx.newPage();page.on('pageerror',e=>pageErrors.push({route:page.url(),error:e.message}));page.on('response',r=>{if(r.status()>=400)httpErrors.push({url:r.url(),status:r.status()});});
   try{while(cursor<districts.length){const name=districts[cursor++];try{
    const response=await page.goto(server.origin+base+'/'+name,{waitUntil:'load'});assert.equal(response.status(),200);await page.evaluate(()=>document.fonts.ready);
    const result=await page.evaluate(()=>{
     const norm=v=>String(v||'').replace(/\s+/g,' ').trim(),heading=norm(document.querySelector('h1')?.textContent),match=heading.match(/^(.*?)\s+(kombi|klima)\s+servisi$/i);
     if(!match)throw Error('Unexpected district heading: '+heading);
     const district=match[1],device=match[2].toLowerCase(),summary=document.querySelector('[data-st-master-matrix]'),tables=summary?.querySelectorAll('table'),table=tables?.[0];if(!table)throw Error('District matrix is missing');
     const wrapper=table.parentElement,rect=wrapper.getBoundingClientRect(),tr=table.getBoundingClientRect(),cells=[...table.querySelectorAll('th,td')];
     const neighborhoods=[...new Set([...document.querySelectorAll('a[href*="mahalle="]')].map(a=>norm(a.textContent)).filter(Boolean))];
     return {district,device,matrix_device:summary.dataset.stMasterMatrix,title:document.title,description:document.querySelector('meta[name=description]')?.content,og_title:document.querySelector('meta[property="og:title"]')?.content,og_description:document.querySelector('meta[property="og:description"]')?.content,lead:norm(document.querySelector('.at-page-hero .at-lead')?.textContent),neighborhoods:neighborhoods.slice(0,6),table_count:tables.length,headers:[...table.querySelectorAll('thead th')].map(c=>norm(c.textContent)),rows:[...table.querySelectorAll('tbody tr')].map(row=>[...row.querySelectorAll('td')].map(c=>norm(c.textContent))),links:[...table.querySelectorAll('tbody tr td:first-child a[href]')].map(a=>({path:new URL(a.href).pathname.split('/').pop(),text:norm(a.textContent)})),source_links:[...table.querySelectorAll('tbody tr')].map(row=>[...row.querySelectorAll('td:last-child a[href]')].map(a=>{const url=new URL(a.href);return {href:url.href,path:url.pathname.split('/').pop(),hash:url.hash,external:url.origin!==location.origin,text:norm(a.textContent)};})),layout:{viewport:innerWidth,document_width:document.documentElement.scrollWidth,wrapper_width:wrapper.clientWidth,wrapper_scroll_width:wrapper.scrollWidth,wrapper_left:rect.left,wrapper_right:rect.right,overflow_x:getComputedStyle(wrapper).overflowX,table_width:tr.width,cell_count:cells.length,cell_overflow:cells.map((c,index)=>({index,client:c.clientWidth,scroll:c.scrollWidth})).filter(c=>c.scroll>c.client+1).map(c=>({index:c.index,client:c.client,scroll:c.scroll})),hidden_cells:cells.filter(c=>!c.getClientRects().length||getComputedStyle(c).visibility==='hidden'||getComputedStyle(c).display==='none').length}};
    });
    const expected=fixture.matrices[result.device],neighborhoods=result.neighborhoods.length?result.neighborhoods.join(', '):result.district+' merkez',meta=fixture.district_metadata[result.device];
    assert(expected);assert.equal(result.matrix_device,result.device);assert.equal(result.table_count,1);assert.deepEqual(result.headers,expected.headers.map(h=>fill(h,result.district,neighborhoods)));assert.deepEqual(result.rows,expected.rows,'Every reviewed source-scoped body cell remains exact');assert.deepEqual(result.links.map(l=>l.path),expected.links,'Matrix brand links retain their requested targets');
    let sourcePairs=0;
    for(const links of result.source_links){
     assert(links.length>=2,'Each reviewed matrix row must link its model and its manufacturer source');let selected=null;
     for(const link of links){
      if(!link.external){assert.equal(selected,null,'Each model link needs its own following manufacturer source');selected=modelsByPath.get(link.path)?.filter(model=>model.device===result.device);assert(selected?.length,'Model detail link must exist for this device in this build catalog: '+link.path);assert.equal(link.hash,'#kodlar','Model detail anchor must open its own code table');}
      else{assert(selected,'A manufacturer link must follow the model document it supports');assert(selected.some(model=>new URL(link.href).href===new URL(model.manual.url).href),'Manufacturer link must match an exact model document at this page path, not another brand/model');selected=null;sourcePairs++;}
     }
     assert.equal(selected,null,'Model link must retain a corresponding manufacturer source');
    }
    assert.equal(sourcePairs,8,'Every device matrix keeps all eight distinct model/source pairs');result.source_pairs=sourcePairs;
    assert.equal(result.title,fill(meta.title,result.district,neighborhoods));assert.equal(result.description,fill(meta.description,result.district,neighborhoods));assert.equal(result.og_title,result.title);assert.equal(result.og_description,result.description);assert.equal(result.lead,norm(fill(meta.lead,result.district,neighborhoods)));
    const layout=result.layout;assert.equal(layout.viewport,320);assert(layout.document_width<=321,'District content must not overflow the viewport');assert(['auto','scroll'].includes(layout.overflow_x),'The matrix owns horizontal scrolling');assert(layout.wrapper_width>0&&layout.wrapper_left>=-1&&layout.wrapper_right<=321,'Scrollable wrapper remains inside the viewport');assert.equal(layout.cell_count,4*(expected.rows.length+1));assert.deepEqual(layout.cell_overflow,[],'Cell text must fit its own cell; table-wide scrolling is allowed');assert.equal(layout.hidden_cells,0);
    if(name==='kucukcekmece-kombi-servisi.html'||name==='kucukcekmece-klima-servisi.html'){
     const target=page.locator('[data-st-master-matrix] table');await target.scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'screenshots',entry.label+'-'+name.replace('.html','')+'-320.jpg'),type:'jpeg',quality:75,animations:'disabled'});
    }
    records.push({route:name,passed:true,width:320,...result});
   }catch(e){errors.push({route:name,error:e.stack});}}}finally{await ctx.close();}
  }
  await Promise.all(Array.from({length:Number(process.env.MATRIX_WORKERS||3)},worker));
 }finally{await server.close();}
 const end=JSON.parse(fs.readFileSync(path.join(directory,'build-info.json'),'utf8'));
 return {label:entry.label,passed:records.length===50&&!errors.length&&!pageErrors.length&&!httpErrors.length&&!blockedExternal.length&&start.content_sha256===end.content_sha256,build_start:start,build_end:end,documents:records.length,rows:records.reduce((n,r)=>n+r.rows.length,0),body_cells:records.reduce((n,r)=>n+r.rows.reduce((total,row)=>total+row.length,0),0),header_cells:records.reduce((n,r)=>n+r.headers.length,0),source_pairs:records.reduce((n,r)=>n+r.source_pairs,0),wrap_only_scrolling:records.filter(r=>r.layout.wrapper_scroll_width>r.layout.wrapper_width+1).length,errors,page_errors:pageErrors,http_errors:httpErrors,blocked_api_requests:blockedAPI,blocked_external_requests:blockedExternal,records};
}
(async()=>{
 fs.mkdirSync(path.join(output,'screenshots'),{recursive:true});const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||'/usr/bin/chromium',args:['--no-sandbox']}),reports=[];
 try{for(const entry of matrix){const result=await run(browser,entry);reports.push(result);fs.writeFileSync(path.join(output,'matrix-'+entry.label+'.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({label:entry.label,passed:result.passed,documents:result.documents,rows:result.rows,body_cells:result.body_cells,header_cells:result.header_cells,wrap_only_scrolling:result.wrap_only_scrolling,errors:result.errors,page_errors:result.page_errors,http_errors:result.http_errors}));}}finally{await browser.close();}
 const report={passed:reports.length===matrix.length&&reports.every(r=>r.passed),source_fixture_sha256:fixture.source_sha256,policy:'Reviewed model/document-scoped matrix cells and original district metadata fixtures; real local HTTP; viewport320; APIs and external requests aborted.',reports};fs.writeFileSync(path.join(output,'matrix-final.json'),JSON.stringify(report,null,2)+'\n');if(!report.passed)process.exitCode=1;
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
