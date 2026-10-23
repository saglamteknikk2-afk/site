'use strict';
(() => {
  const data=window.ST_BRAND_REGISTRY||{brands:[]};
  const norm=s=>String(s||'').toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i').replace(/[^a-z0-9]+/g,' ').trim();
  const list=device=>(data.brands||[]).filter(b=>!device||b.devices.includes(String(device).toLowerCase())).map(b=>({...b,verified_model_ids:device?(b.guides_by_device?.[String(device).toLowerCase()]||[]):Object.values(b.guides_by_device||{}).flat(),guide_count:device?(b.guides_by_device?.[String(device).toLowerCase()]||[]).length:Object.values(b.guides_by_device||{}).flat().length}));
  const find=(name,device)=>list(device).find(b=>[b.name,...(b.aliases||[])].some(v=>norm(v)===norm(name)))||null;
  window.STBrands=Object.freeze({list,names:device=>list(device).map(b=>b.name),find,normalize:norm});
})();
