'use strict';
// Exact model first; zero-padding is a spelling fallback inside that document only.
(() => {
  const norm = value => String(value ?? '').toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i').replace(/[^a-z0-9]+/g,' ').trim();
  const key = value => String(value ?? '').toUpperCase().replace(/[^A-Z0-9]/g,'');
  const flexKey = value => key(value).replace(/^([A-Z]+)0+(\d+)$/, '$1$2');
  const contains = (text, term) => !!norm(term) && (' '+norm(text)+' ').includes(' '+norm(term)+' ');
  const dataset = () => window.ST_VERIFIED_FAULTS || {models:[],coverage:[]};
  const models = (device,brand='') => dataset().models.filter(m => m.device===device && (!brand || norm(m.brand)===norm(brand)));
  function infer(query, device, brand='') {
    let length=0, candidates=[];
    for(const model of models(device,brand)) {
      if(model.matchable===false)continue;
      for(const term of [...(model.model_names||[]),...(model.aliases||[]),model.label]) {
        const n=norm(term);
        if(n.length<4 || !contains(query,n))continue;
        if(n.length>length){length=n.length;candidates=[model];}
        else if(n.length===length&&!candidates.some(m=>m.id===model.id))candidates.push(model);
      }
    }
    return candidates.length===1?candidates[0]:null;
  }
  const regexEscape = text => text.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  function appears(query,code) {
    const display=String(code).toUpperCase();
    if(!/^[A-Z0-9.\s-]+$/.test(display))return contains(query,code);
    const chars=key(display).split('').map(regexEscape).join('[.\\s-]*');
    return new RegExp('(^|[^A-Z0-9])'+chars+'(?=$|[^A-Z0-9])','i').test(String(query));
  }
  function extract(query, model=null) {
    // Strip the selected model label, so capacity/model numbers are not codes.
    let text=String(query);
    if(model)for(const name of [...(model.model_names||[]),...(model.aliases||[]),model.label].sort((a,b)=>b.length-a.length)) {
      text=text.replace(new RegExp(regexEscape(name),'ig'),' ');
    }
    const explicit=norm(text).match(/\b(?:hata kodu|ariza kodu|ekrandaki kod|kod|kodu)\s+([a-z0-9]+(?:\s+[0-9]{1,3}){0,3})/);
    const codeRows=model?model.codes:[];
    if(explicit){
      const candidate=explicit[1].toUpperCase();
      const exact=findRows(model,candidate);
      if(exact.rows.length)return exact.match==='exact'&&exact.rows.length===1?exact.rows[0].code:candidate;
      const first=candidate.split(' ')[0];
      if(findRows(model,first).rows.length)return first;
    }
    for(const row of [...codeRows].sort((a,b)=>key(b.code).length-key(a.code).length)) {
      if(row.matchable===false)continue;
      // A bare numeric value needs an explicit code label, not a temperature.
      if(/^\d+$/.test(key(row.code))&&!explicit)continue;
      if(appears(text,row.code))return row.code;
    }
    const generic=text.match(/\b((?:CH|EA|EC|E|F|A|C|H|J|L|P|U)[.\s-]?\d{1,3}(?:[.-]\d{1,3})*|EA|EC)\b/i);
    return generic?generic[1].toUpperCase().replace(/\s/g,''):explicit?explicit[1].toUpperCase():'';
  }
  function findRows(model, code) {
    const available=(model?.codes||[]).filter(row=>row.matchable!==false);
    const values=row=>[row.code,...(row.equivalent_codes||[])];
    const exact=available.filter(row=>values(row).some(value=>key(value)===key(code)));
    if(exact.length)return {rows:exact,match:'exact'};
    const flexible=available.filter(row=>values(row).some(value=>flexKey(value)===flexKey(code)));
    return {rows:flexible,match:flexible.length?'flexible':''};
  }
  function scopeWarning(model) {
    if(!model||!(model.requires_scope_confirmation||model.requires_document_match||model.matchable===false))return '';
    const market=model.market?'Belge pazarı / bölgesi: '+model.market+'. ':'';
    const foreign=model.market&&!/(?:^|[^a-z])tr(?:[^a-z]|$)|turkiye|turkce/.test(norm(model.market));
    return market+(foreign?'Bu pazar için yayımlanan belge Türkiye varyantı doğrulaması değildir. ':'')+'Açıklama seçtiğiniz üretici belgesine aittir; ülke/ürün son eki, kontrol birimi veya belge sürümü farklıysa anlam değişebilir.';
  }
  function lookup(input={}) {
    const device=input.device==='klima'?'klima':'kombi',brand=input.brand||'';
    const allowed=models(device,brand);
    let model=input.model_id?allowed.find(m=>m.id===input.model_id):null;
    // An explicit incompatible model ID never falls through to another model.
    if(!input.model_id)model=infer([brand,input.model,input.query].filter(Boolean).join(' '),device,brand);
    const code=input.code||extract(input.query||'',model);
    const base={verified:false,status:model?'model-known':'needs-model',model:model||null,code,definition:null,candidate_models:[],scope_warning:scopeWarning(model),code_match:''};
    if(model){
      if(!code)return base;
      const found=findRows(model,code),rows=found.rows;
      if(rows.length===0)return {...base,status:'code-not-covered'};
      if(rows.length>1)return {...base,status:found.match==='flexible'?'ambiguous-code':'source-conflict',code_match:found.match};
      if(rows[0].source_conflict)return {...base,status:'source-conflict',code_match:found.match};
      return {...base,status:'verified',verified:true,definition:rows[0],code:rows[0].code,code_match:found.match};
    }
    if(code&&!input.model_id)base.candidate_models=allowed.filter(m=>findRows(m,code).rows.length);
    return base;
  }
  window.STFaults={normalize:norm,codeKey:key,flexKey,models,infer,extract,lookup};
})();
