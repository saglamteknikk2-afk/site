/* Region selection enhances existing content; no new URL permutations or provider requests. */
(() => {
  'use strict';
  const roots=[...document.querySelectorAll('[data-hybrid-matrix]')];
  if(!roots.length)return;
  const script=document.currentScript?.src;
  const dataURL=new URL('hybrid-matrix-data.json',script||new URL('assets/',location.href));
  const norm=value=>String(value||'').replace(/[çğıöşüÇĞİÖŞÜ]/g,c=>({ç:'c',ğ:'g',ı:'i',ö:'o',ş:'s',ü:'u',Ç:'c',Ğ:'g',İ:'i',Ö:'o',Ş:'s',Ü:'u'}[c])).toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  const slug=value=>norm(value).replace(/ /g,'-');
  const key=value=>String(value||'').toUpperCase().replace(/[^A-Z0-9]/g,'').replace(/^([A-Z]+)0+(\d+)$/,'$1$2');
  const option=(value,label)=>{const item=document.createElement('option');item.value=value;item.textContent=label;return item;};
  fetch(dataURL).then(response=>{if(!response.ok)throw new Error('Catalogue unavailable');return response.json();}).then(data=>{
    const routes=new Set(data.routes);
    roots.forEach(root=>{
      const fields=Object.fromEntries([...root.querySelectorAll('[data-field]')].map(el=>[el.dataset.field,el]));
      const controls=root.querySelector('[data-matrix-controls]'),result=root.querySelector('[data-matrix-result]');
      const device=()=>data.devices[fields.device.value]||data.devices.kombi;
      function fillNeighborhoods(){
        const district=data.districts.find(row=>row.name===fields.district.value);
        fields.neighborhood.replaceChildren(option('','Mahallemi bilmiyorum / listede yok'),...(district?.neighborhoods||[]).map(n=>option(n,n)));
      }
      function fillModels(){
        const names=(data.model_names||[]).filter(m=>m.device===fields.device.value&&norm(m.brand)===norm(fields.brand.value));
        const models=data.models.filter(m=>m.device===fields.device.value&&m.brand===fields.brand.value);
        fields.model.replaceChildren(option('','Modeli bilmiyorum'),...(names.length?names.map(m=>option(m.id,m.name)):models.map(m=>option(m.id,m.label))),option('__custom','Modelim listede yok; yazmak istiyorum'));
        fields.customModel.value='';root.querySelector('[data-custom-model-label]').hidden=true;
      }
      function fillDevice(){
        const d=device();
        fields.brand.replaceChildren(option('','Markayı bilmiyorum'),...d.brands.map(b=>option(b,b)));
        const seen=new Set();const needs=d.needs.filter(n=>{const id=n.name+'|'+n.path;if(seen.has(id))return false;seen.add(id);return true;});
        fields.need.replaceChildren(option('','Servis bilgilerini göster'),...needs.map(n=>option(n.name,n.name)));
        fillModels();
      }
      function initialize(){
        fields.device.value=data.devices[root.dataset.device]?root.dataset.device:'kombi';
        fields.district.replaceChildren(option('','İlçeyi bilmiyorum / listede yok'),...data.districts.map(d=>option(d.name,d.name)));
        fields.district.value=root.dataset.district||'';fillDevice();fillNeighborhoods();
        const initialBrand=[...fields.brand.options].find(item=>item.value&&norm(item.value)===norm(root.dataset.brand));
        if(initialBrand){fields.brand.value=initialBrand.value;fillModels();}
        const initialNeed=device().needs.find(item=>item.path===root.dataset.needPath);
        if(initialNeed)fields.need.value=initialNeed.name;
        const neighborhood=decodeURIComponent(location.hash).replace(/^#mahalle-/,'');
        for(const item of fields.neighborhood.options)if(slug(item.value)===neighborhood&&item.value)fields.neighborhood.value=item.value;
        fields.code.value='';result.replaceChildren();result.hidden=true;
        root.querySelectorAll('details').forEach(el=>el.open=false);
      }
      function selectHashNeighborhood(){
        let selected='';
        try{selected=decodeURIComponent(location.hash).replace(/^#mahalle-/,'');}catch(_){return;}
        const match=[...fields.neighborhood.options].find(item=>item.value&&slug(item.value)===selected);
        if(match){fields.neighborhood.value=match.value;result.hidden=true;}
      }
      function localLink(path,label){
        const target=path.split(/[?#]/)[0];if(!routes.has(target))return null;
        const link=document.createElement('a');link.href=path;link.textContent=label;return link;
      }
      function show(){
        const kind=fields.device.value,brand=fields.brand.value,district=fields.district.value,neighborhood=fields.neighborhood.value;
        const named=(data.model_names||[]).find(m=>m.id===fields.model.value&&m.device===kind&&norm(m.brand)===norm(brand));
        const model=data.models.find(m=>m.id===(named?.verified_model_id||fields.model.value)&&m.device===kind&&norm(m.brand)===norm(brand));
        const custom=fields.model.value==='__custom'?fields.customModel.value.trim():'';
        const chosenName=named?.name||model?.label||custom;
        const code=fields.code.value.trim(),need=device().needs.find(n=>n.name===fields.need.value);
        let target=need?.path||data.brand_routes.find(b=>b.brand===brand&&b.device===kind)?.path||kind+'-servisi.html';
        if(district&&!need)target=slug(district)+'-'+kind+'-servisi.html'+(neighborhood?'#mahalle-'+slug(neighborhood):'#bolge-rehberi');
        const statement=document.createElement('p');
        if(model&&code){
          const definition=model.codes.find(c=>key(c.code)===key(code));
          if(definition){target=model.path+'#'+definition.anchor;statement.textContent=definition.code+': '+definition.meaning+'. Bu açıklama yalnız seçtiğiniz model belgesinin kapsamındadır.';}
          else {target=model.path+'#kodlar';statement.textContent='Bu kodu seçtiğiniz model tablosunda doğrulayamadık. Kodun ne zaman çıktığını ve eşlik eden belirtiyi not edin; ustamızla birlikte değerlendirelim.';}
        }else if(model){target=model.path+'#kodlar';statement.textContent='Seçtiğiniz modelin belge kapsamını ve kod tablosunu açabilirsiniz.';}
        else if(code){statement.textContent=named?'Seçtiğiniz model adını ve kodu aldık. Bu model için eşleşmiş bir kod belgesi kayıtlı değil. Cihazda ne olduğunu da tarif ederek ustamıza sorabilirsiniz; başka modelin kod açıklamasını kullanmıyoruz.':'Kodu not ettik. Kod anlamını kesinleştirmek için tam model gerekir. Cihazda ne olduğunu da tarif ederek ustamıza sorabilirsiniz; başka modelin kod açıklamasını kullanmıyoruz.';}
        else {statement.textContent='Seçiminize uygun servis bilgilerini ve güvenli gözlem notlarını açın. Yerinde kontrol gerektiren durumları ustamızla değerlendirebilirsiniz.';}
        const title=document.createElement('h3');title.textContent=[district,neighborhood,brand,chosenName,fields.need.value].filter(Boolean).join(' · ')||device().label+' servis bilgileri';
        const actions=document.createElement('div');actions.className='hybrid-actions';
        const guide=localLink(target,model?'Model ve arıza rehberini aç →':'İlgili servis rehberini aç →');if(guide)actions.append(guide);
        const call=document.createElement('a');call.href='tel:05346225515';call.textContent='Ustamızı ara';call.dataset.contactIntent='call';actions.append(call);
        const params=new URLSearchParams({cihaz:kind});for(const [k,v] of Object.entries({ilce:district,mahalle:neighborhood,marka:brand,model:chosenName,ariza:fields.need.value,kod:code}))if(v)params.set(k,v);
        const ticket=document.createElement('a');ticket.href='servis-sec.html#'+params;ticket.textContent='Bu bilgilerle servis talebi bırak';
        result.replaceChildren(title,statement,actions,ticket);result.hidden=false;
        result.scrollIntoView({block:'nearest',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
      }
      fields.device.addEventListener('change',()=>{fillDevice();fields.code.value='';result.hidden=true;});
      fields.brand.addEventListener('change',()=>{fillModels();result.hidden=true;});
      fields.district.addEventListener('change',()=>{fillNeighborhoods();result.hidden=true;});
      fields.model.addEventListener('change',()=>{root.querySelector('[data-custom-model-label]').hidden=fields.model.value!=='__custom';result.hidden=true;});
      root.querySelector('[data-matrix-show]').addEventListener('click',show);
      root.querySelector('[data-matrix-reset]').addEventListener('click',()=>{initialize();fields.brand.focus({preventScroll:true});});
      initialize();controls.hidden=false;
      window.addEventListener('hashchange',selectHashNeighborhood);
    });
  }).catch(()=>{/* Static region, brand and symptom links remain usable. */});
})();
