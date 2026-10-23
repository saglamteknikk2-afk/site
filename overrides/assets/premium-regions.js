/* Local region navigation: existing district, locality and neighborhood routes only. */
(() => {
  'use strict';
  const form=document.getElementById('regionFinder');
  if(!form)return;
  const input=document.getElementById('regionQuery');
  const results=document.getElementById('regionResults');
  const status=document.getElementById('regionLiveStatus');
  const clear=document.getElementById('regionClear');
  const directory=document.getElementById('regionDirectory');
  const localities=document.getElementById('regionLocalities');
  const norm=value=>String(value||'').replace(/[çğıöşüÇĞİÖŞÜ]/g,c=>({ç:'c',ğ:'g',ı:'i',ö:'o',ş:'s',ü:'u',Ç:'c',Ğ:'g',İ:'i',Ö:'o',Ş:'s',Ü:'u'}[c])).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,' ').trim().replace(/\bkucuk\s+cekmece\b/g,'kucukcekmece').replace(/\bkucukcekm(?:e)?ce(?:ce)?\b/g,'kucukcekmece');
  const ignored=new Set(['mahalle','mahallesi','mah','ilce','ilcesi','istanbul','avrupa','yakasi','servis','servisi','kombi','klima','ve']);
  const normalizedQuery=value=>norm(value).split(' ').filter(word=>!ignored.has(word)).join(' ');
  const aliases={Sefaköy:['Sefaköy','Sefakoy','Sefa köy'],'500 Evler':['500 Evler','500evler','Beşyüzevler'],Merter:['Merter'],Bahçeşehir:['Bahçeşehir'],Kilyos:['Kilyos','Kumköy']};
  const records=[];
  document.querySelectorAll('[data-region-district]').forEach(card=>{
    const name=card.dataset.regionDistrict;
    const combi=card.querySelector('[data-region-device="kombi"]');
    const climate=card.querySelector('[data-region-device="klima"]');
    if(combi)records.push({type:'district',name,parent:'',aliases:[name],href:combi.getAttribute('href'),climate:climate?.getAttribute('href')});
  });
  document.querySelectorAll('[data-region-locality]').forEach(link=>{
    const name=link.dataset.regionLocality;
    records.push({type:'locality',name,parent:link.dataset.regionParent,aliases:aliases[name]||[name],href:link.getAttribute('href')});
  });
  document.querySelectorAll('[data-region-neighborhood]').forEach(link=>records.push({type:'neighborhood',name:link.dataset.regionNeighborhood,parent:link.dataset.regionParent,aliases:[link.dataset.regionNeighborhood],href:link.getAttribute('href')}));
  records.forEach(record=>{record.own=record.aliases.map(norm);record.parentNorm=norm(record.parent);record.combined=norm([record.name,record.parent,...record.aliases].join(' '));});
  const collator=new Intl.Collator('tr',{sensitivity:'base'});
  let matches=[],shown=[],selected=-1;
  function find(query){
    const q=normalizedQuery(query),compact=q.replace(/\s/g,''),tokens=q.split(' ').filter(Boolean);
    if(!q)return [];
    return records.map(record=>{
      const ownExact=record.own.some(name=>name===q||name.replace(/\s/g,'')===compact);
      const composite=norm(record.parent+' '+record.name)===q||norm(record.name+' '+record.parent)===q;
      const ownMatch=record.own.some(name=>name.includes(q)||name.replace(/\s/g,'').includes(compact));
      const combinedMatch=tokens.every(word=>record.combined.includes(word));
      const specific=tokens.some(word=>!record.parentNorm.includes(word)&&record.own.some(name=>name.includes(word)));
      if(!ownMatch&&!(combinedMatch&&specific))return null;
      const rank=composite?110:ownExact?(record.type==='district'?100:record.type==='locality'?95:90):ownMatch?(record.type==='district'?75:record.type==='locality'?70:60):40;
      return {...record,rank,exact:ownExact||composite};
    }).filter(Boolean).sort((a,b)=>b.rank-a.rank||collator.compare(a.name,b.name)||collator.compare(a.parent,b.parent));
  }
  function hrefFor(record){
    const climate=/\bklima\b/.test(norm(input.value));
    if(climate&&record.climate)return record.climate;
    if(climate&&record.type==='neighborhood'){
      const [path,fragment='']=record.href.split('#');
      const fields=new URLSearchParams(fragment);fields.set('cihaz','klima');return path+'#'+fields;
    }
    return record.href;
  }
  function automatic(){
    const districts=shown.filter(record=>record.type==='district'&&record.exact);
    if(districts.length===1)return shown.indexOf(districts[0]);
    const exact=shown.filter(record=>record.exact);
    if(exact.length===1)return shown.indexOf(exact[0]);
    return matches.length===1?0:-1;
  }
  function select(index){
    selected=index;
    [...results.querySelectorAll('[role="option"]')].forEach((link,i)=>link.setAttribute('aria-selected',String(i===selected)));
    const option=results.querySelectorAll('[role="option"]')[selected];
    if(option){input.setAttribute('aria-activedescendant',option.id);option.scrollIntoView({block:'nearest'});}
    else input.removeAttribute('aria-activedescendant');
  }
  function render(){
    const raw=input.value.trim(),q=normalizedQuery(raw);
    results.replaceChildren();clear.hidden=!raw;
    input.removeAttribute('aria-activedescendant');selected=-1;
    directory.hidden=!!raw;localities.hidden=!!raw;
    if(!raw){results.hidden=true;input.setAttribute('aria-expanded','false');status.textContent='25 ilçe · 599 mahalle';matches=[];shown=[];return;}
    matches=find(raw);shown=matches.slice(0,8);
    if(!q){results.hidden=true;input.setAttribute('aria-expanded','false');status.textContent='İlçe, mahalle veya semt adını yazın.';return;}
    shown.forEach((record,i)=>{
      const li=document.createElement('li');li.setAttribute('role','presentation');
      const link=document.createElement('a');link.href=hrefFor(record);link.id='region-option-'+i;link.setAttribute('role','option');link.setAttribute('aria-selected','false');link.tabIndex=-1;
      const title=document.createElement('strong');title.textContent=record.name;
      const meta=document.createElement('span');meta.className='pr-result-meta';meta.textContent=record.type==='district'?'İlçe · Kombi ve klima servisi':record.type==='locality'?'Semt · '+record.parent:'Mahalle · '+record.parent;
      const arrow=document.createElement('span');arrow.className='pr-result-arrow';arrow.setAttribute('aria-hidden','true');arrow.textContent='↗';
      const copy=document.createElement('span');copy.append(title,meta);link.append(copy,arrow);li.append(link);results.append(li);
      link.addEventListener('focus',()=>select(i));
    });
    results.hidden=!shown.length;input.setAttribute('aria-expanded',String(!!shown.length));
    const auto=automatic();if(auto>=0)select(auto);
    status.textContent=!matches.length?'Bu adla eşleşme bulunamadı. İlçe adını veya başka bir yazımı deneyin.':auto>=0?'İlgili bölgeyi açmak için Enter’a basın.':matches.length+' eşleşme'+(matches.length>shown.length?' · İlk '+shown.length+' sonuç gösteriliyor.':'')+' İlçeyi de yazın veya bir sonuç seçin.';
  }
  function navigate(record){
    if(!record)return;
    const url=new URL(hrefFor(record),location.href);
    if(url.origin===location.origin)location.assign(url.href);
  }
  form.addEventListener('submit',event=>{
    event.preventDefault();
    if(!input.value.trim()){input.focus();status.textContent='Önce ilçe, mahalle veya semt adını yazın.';return;}
    if(results.hidden)render();
    if(selected>=0)navigate(shown[selected]);
    else{status.textContent=matches.length?'Aynı adla birden fazla yer var. İlçeyi ekleyin veya ok tuşlarıyla bir sonuç seçin.':'Eşleşme bulunamadı. İlçe adını kontrol edin.';input.focus();}
  });
  input.addEventListener('input',render);
  input.addEventListener('keydown',event=>{
    if(event.key==='ArrowDown'||event.key==='ArrowUp'){
      if(results.hidden)render();if(!shown.length)return;
      event.preventDefault();select(event.key==='ArrowDown'?(selected+1)%shown.length:(selected<0?shown.length-1:(selected-1+shown.length)%shown.length));
    }else if(event.key==='Escape'){
      results.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');directory.hidden=false;localities.hidden=false;selected=-1;status.textContent='25 ilçe · 599 mahalle';
    }
  });
  clear.addEventListener('click',()=>{input.value='';render();input.focus();});
  const initial=new URLSearchParams(location.search).get('bolge');if(initial){input.value=initial.slice(0,120);render();}
})();
