/* Private customer view. Refresh data only; never reload the document. */
(() => {
  'use strict';
  const code=new URLSearchParams(location.search).get('kod')||'';
  const load=document.getElementById('load'),detail=document.getElementById('detail');
  if(!/^[a-f0-9]{32}$/.test(code)){load.textContent='Takip bağlantısı geçersiz.';return;}
  const POLL_MS=3000,REQUEST_TIMEOUT_MS=12000;
  let first=true,busy=false,timer=0,controller=null,stopped=false;
  const clear=()=>{if(timer){clearTimeout(timer);timer=0;}};
  const schedule=()=>{clear();if(!stopped&&!document.hidden)timer=setTimeout(render,POLL_MS);};
  const telegramLink=value=>{
    try{const u=new URL(value);return u.protocol==='https:'&&u.hostname==='t.me'&&/^\/[A-Za-z0-9_]{5,32}$/.test(u.pathname)?u.href:'';}catch(_){return '';}
  };
  async function render(){
    clear();if(busy||stopped||document.hidden)return;
    busy=true;controller=new AbortController();
    const deadline=setTimeout(()=>controller?.abort(),REQUEST_TIMEOUT_MS);
    try{
      const res=await fetch('api.php?action=service-status&kod='+encodeURIComponent(code),{
        cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',
        signal:controller.signal,headers:{Accept:'application/json'}
      });
      const data=await res.json();
      if(!res.ok||!data.ok)throw Error('Takip bağlantısı bulunamadı.');
      load.classList.add('hidden');detail.classList.remove('hidden');
      const kind=document.getElementById('kind');
      kind.textContent=data.service_level==='priority'?'✦ VIP Servis':'Normal Servis';
      kind.classList.toggle('vip',data.service_level==='priority');
      document.getElementById('status').textContent=data.status_label;
      document.getElementById('recordRef').textContent=/^[a-f0-9]{8}$/.test(data.record_ref||'')?'Servis kayıt no: '+data.record_ref:'';
      document.getElementById('eta').textContent=data.eta_minutes?'Son bildirilen tahmini varış: '+data.eta_minutes+' dakika.':'Varış süresi henüz paylaşılmadı.';
      const history=document.getElementById('history');history.replaceChildren();
      if(!data.updates?.length){const p=document.createElement('p');p.textContent='Servis talebiniz alındı. Yeni bilgiler burada gösterilecek.';history.append(p);}
      else for(const item of data.updates){
        const box=document.createElement('div');box.className='update';
        const time=document.createElement('time');time.textContent=new Date(item.created*1000).toLocaleString('tr-TR',{dateStyle:'medium',timeStyle:'short'});
        const text=document.createElement('p');text.textContent=item.body;box.append(time,text);history.append(box);
      }
      const bot=document.getElementById('bot'),telegram=telegramLink(data.telegram_url);
      bot.classList.toggle('hidden',!telegram);
      if(telegram)bot.href=telegram;else bot.removeAttribute('href');
      document.getElementById('telegramNote').textContent=data.telegram_subscribed?'Telegram bildirimleri etkin.':'Telegram bildirimi için botu başlatmalısınız. Bot bağlantısı görünmüyorsa doğrudan bu ekrandan takip edebilirsiniz.';
      document.getElementById('liveStatus').textContent='🟢 Canlı takip açık · Son kontrol: '+new Date().toLocaleTimeString('tr-TR')+' · 3 saniyede bir güncellenir.';
      first=false;
    }catch(error){
      if(!stopped&&!document.hidden){
        if(first)load.textContent='Servis bilgisine ulaşılamadı. Bağlantı yeniden denenecek; destek için 0534 622 5515 numarasını arayabilirsiniz.';
        else document.getElementById('liveStatus').textContent='Bağlantı şu anda yenilenemedi. Son bilgiler korunuyor; yeniden denenecek.';
      }
    }finally{
      clearTimeout(deadline);controller=null;busy=false;schedule();
    }
  }
  document.addEventListener('visibilitychange',()=>{
    clear();if(document.hidden)controller?.abort();else render();
  });
  window.addEventListener('pagehide',()=>{stopped=true;clear();controller?.abort();});
  window.addEventListener('pageshow',()=>{stopped=false;render();});
  render();
})();
