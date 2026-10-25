
    // Sadece müşteri adresi: mevcut API alanlarının adları korunur.
    async function stUpgradeAddress() {
      const old=document.getElementById('ticketDistrict');if(!old)return;
      const districts=['Arnavutköy','Avcılar','Bağcılar','Bahçelievler','Bakırköy','Başakşehir','Bayrampaşa','Beşiktaş','Beylikdüzü','Beyoğlu','Büyükçekmece','Çatalca','Esenler','Esenyurt','Eyüpsultan','Fatih','Gaziosmanpaşa','Güngören','Kağıthane','Küçükçekmece','Sarıyer','Silivri','Şişli','Sultangazi','Zeytinburnu'];
      const unknown='Bilmiyorum / Listede yok';
      const select=(id,placeholder)=>{const el=document.createElement('select');el.id=id;el.innerHTML='';el.add(new Option(placeholder,''));el.add(new Option(unknown,unknown));return el;};
      let district=old;
      if(old.tagName!=='SELECT'){
        district=select('ticketDistrict','İlçe seçin');
        for(const name of districts)district.add(new Option(name,name));
        district.required=true;old.replaceWith(district);
      }
      let hood=document.getElementById('ticketNeighborhood');
      if(!hood){const label=document.createElement('label');label.htmlFor='ticketNeighborhood';label.textContent='Mahalle (isteğe bağlı)';hood=select('ticketNeighborhood','Önce ilçe seçin');label.append(hood);district.closest('label')?.after(label);}
      let street=document.getElementById('ticketStreet');
      if(!street){const label=document.createElement('label');label.htmlFor='ticketStreet';label.textContent='Sokak / cadde (isteğe bağlı)';street=document.createElement('input');street.id='ticketStreet';street.maxLength=120;street.placeholder='Sokak/cadde adı veya bilmiyorum';label.append(street);hood.closest('label')?.after(label);}
      let catalog=null;
      try{
        const url=new URL('assets/servis-katalog.json',document.baseURI);
        const response=await fetch(url,{credentials:'same-origin'});
        if(response.ok)catalog=await response.json();
      }catch(_){}
      const list=Array.isArray(catalog?.neighborhoods)?catalog.neighborhoods:[];
      const render=()=>{
        if(hood.tagName!=='SELECT')return;
        const former=hood.value;hood.replaceChildren(new Option(district.value?'Mahalle seçin':'Önce ilçe seçin',''),new Option(unknown,unknown));
        for(const name of [...new Set(list.filter(x=>x.district===district.value).map(x=>x.name))].sort((a,b)=>a.localeCompare(b,'tr')))hood.add(new Option(name,name));
        if([...hood.options].some(x=>x.value===former))hood.value=former;
      };
      district.addEventListener('change',render);render();
      const ticket=document.getElementById('serviceTicketForm');
      ticket?.addEventListener('submit',()=>{
        const issue=document.getElementById('ticketIssue');if(!issue)return;
        const value=issue.value.replace(/\s*\|\s*Mahalle:.*$/,'');
        const extra=[hood.value&&'Mahalle: '+hood.value,street.value.trim()&&'Sokak: '+street.value.trim()].filter(Boolean).join(' | ');
        issue.value=(value+(extra?' | '+extra:'')).slice(0,2000);
      },true);
    }
    document.addEventListener('DOMContentLoaded',stUpgradeAddress);



    // 1. GEMINI AI USTA MOTORU
    let lastDiagnosedIssue = "";
    let aiRequestSerial = 0;

    document.addEventListener('DOMContentLoaded',()=>{
      document.getElementById('homeGuideSearch')?.addEventListener('submit',event=>{
        const query=document.getElementById('homeGuideQuery').value.trim();
        if(query.length<3)return;
        event.preventDefault();
        location.href='/servis-sec.html#'+new URLSearchParams({arama:query}).toString();
      });
    });

    function stDiagnosticGuideURL(value) {
      let home;
      try {
        const anchor=document.querySelector('.at-header .at-brand[href]');
        home=new URL(anchor?.getAttribute('href')||'./',location.href);
        if(home.origin!==location.origin)throw new Error('Unexpected home origin');
      } catch (_) { home=new URL('./',location.href); }
      home.pathname=home.pathname.replace(/\/index\.html$/i,'/');
      if(!home.pathname.endsWith('/'))home.pathname+='/';
      home.search='';home.hash='';
      const fallback=new URL('ariza-rehberi.html',home);
      const entry=path=>{
        if(typeof path!=='string'||!path)return null;
        try {
          const url=new URL(path,home);
          if(url.origin!==home.origin||url.username||url.password)return null;
          const file=url.pathname.startsWith(home.pathname)?url.pathname.slice(home.pathname.length):url.pathname.slice(1);
          if(!/^[a-z0-9-]+\.html$/.test(file)||url.hash&&!/^#[a-z0-9-]+$/.test(url.hash))return null;
          return {url,file};
        } catch (_) { return null; }
      };
      const published=new Set(['ariza-rehberi.html']);
      const paths=[...(window.ST_ORGANIC_CATALOG?.published_routes||[]),...(window.ST_DIAGNOSTIC_DATA||[]).map(row=>row.path),...(window.ST_VERIFIED_FAULTS?.models||[]).map(model=>model.path)];
      for(const path of paths){const known=entry(path);if(known)published.add(known.file);}
      const selected=entry(value);
      if(!selected||!published.has(selected.file))return fallback.pathname;
      const target=new URL(selected.file,home);
      target.search=selected.url.search;target.hash=selected.url.hash;
      return target.pathname+target.search+target.hash;
    }

    function renderDiagnostic(data, options={}) {
      if(data.requires_model){data={...data,requires_model:false,text:'Model bilinmiyorsa hata koduna kesin anlam veremeyiz. Arızayı tarif edin; yetkin usta kontrolü gerekir.'};}
      const box=document.getElementById('aiResultBox'),response=document.getElementById('aiResponseText');
      stAiContact(data.emergency_phone);
      const actions=document.querySelector('#aiResultBox .usta-result-actions');if(actions)actions.hidden=data.source==='advisory'||data.source==='emergency';
      const context=options.context||window.STUstaWizard?.getContext()||{},device=options.device||document.getElementById('deviceSelect').value;
      const issue=options.issue??document.getElementById('issueInput').value.trim();
      const match=data.source==='manual'?window.STFaults?.lookup({device:device.toLowerCase(),brand:context.brand||'',model_id:context.model_id||'',code:context.code||'',scope_confirmed:context.scope_confirmed===true}):null;
      const safe=value=>stEscape(value||'').replace(/\n/g,'<br>');
      if(data.source==='advisory'||data.source==='emergency'||data.source==='safety'){
        const phone=['187','112'].includes(data.emergency_phone)?data.emergency_phone:'';
        response.innerHTML='<section class="usta-result-alert" aria-label="Öncelikli bilgi"><p>'+safe(data.text)+'</p>'+(phone?'<a class="usta-emergency-call" href="tel:'+phone+'">'+phone+' acil hattını ara →</a>':'')+'</section>';
      }else{
        const text=match?.verified?match.definition.code+' · '+match.definition.meaning:(data.text||'Marka/model ve arıza belirtisini biraz daha tarif eder misiniz?');
        const observation=match?.verified?[match.definition.safe_observation,match.scope_warning].filter(Boolean).join(' '):'Ekrandaki tam kodu ve belirtinin hangi kullanım sırasında çıktığını, kapağı açmadan not edin.';
        const heading=match?.verified?'Üretici belgesindeki açıklama':data.source==='ai'?'AI ön değerlendirmesi':'İlk yönlendirme';
        response.innerHTML='<div class="usta-result-grid"><section class="usta-result-main" aria-label="'+safe(heading)+'"><p>'+safe(text)+'</p></section><section><h4>Güvenli gözlem</h4><p>'+safe(observation)+'</p></section><section><h4>Sonraki adım</h4><p>Belirti devam ediyorsa model ve gözlemlerinizi paylaşarak kontrolü planlayalım. Gaz, elektrik ve soğutucu devreye müdahale etmeyin.</p></section></div>';
      }
      const source=document.getElementById('aiSource');
      if(source)source.textContent=data.source==='advisory'?'Üreticinin modele özel duyurusu':data.source==='manual'?'Seçilen modelin üretici belgesi':data.source==='ai'?'AI teknik ön değerlendirme':data.source==='emergency'||data.source==='safety'?'Öncelikli güvenlik bilgisi':'Belirti rehberi';
      if(!response.querySelector('.st-call-technician')){const link=document.createElement('a');link.className='st-call-technician';link.href='tel:05346225515';link.textContent='Ustamızı ara';link.style.cssText='display:inline-block;margin-top:12px;padding:12px 18px;background:#164b3b;color:white;border-radius:8px';response.append(link);}
      box.classList.remove('hidden');
      const guide=document.getElementById('aiGuideLink');
      if(guide){
        const local=window.STDiagnosticGuide?.(device,issue,context);
        const path=data.guide_path||local?.guide_path||'';
        guide.href=stDiagnosticGuideURL(path);
        guide.hidden=data.source==='emergency'||data.source==='advisory';
      }
      const reference=document.getElementById('aiManualReference');
      if(reference){reference.replaceChildren();reference.hidden=!data.source_url;if(data.source_url&&/^https:\/\//.test(data.source_url)){const link=document.createElement('a');link.href=data.source_url;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Üretici kaynağını aç ↗';reference.append(link,document.createElement('br'),document.createTextNode(data.source_locator||''));}}
      if(options.record!==false&&typeof stRecordAIResult==='function'){
        stRecordAIResult({...data,device,brand:context.brand||'',model:context.model||'',model_id:context.model_id||'',district:context.district||'',neighborhood:context.neighborhood||'',code:context.code||'',issue,answer:response.innerText.trim()});
      }
    }

    function showFallbackDiagnostic(device, issue, options={}) {
      const data=window.STDiagnosticGuide?window.STDiagnosticGuide(device,issue,options.context||window.STUstaWizard?.getContext()||{}):{source:'guide',text:'Marka/modeli, hata kodunu ve sorunun ne zaman oluştuğunu paylaşın. İç parçalara müdahale etmeden Sağlam Teknik ile servis kontrolü planlayabilirsiniz: 0534 622 5515.'};
      renderDiagnostic(data,options);return data;
    }

    async function diagnoseIssue() {
      const device=document.getElementById('deviceSelect').value,issue=document.getElementById('issueInput').value.trim();
      if(issue.length<3){alert('Lütfen arıza belirtisini veya hata kodunu en az 3 karakterle yazın.');return;}
      if(issue.length>1200){alert('Arıza açıklamasını biraz kısaltın; en fazla 1200 karakter kullanabilirsiniz.');return;}
      const button=document.getElementById('askBtn');if(button.disabled)return;
      const requestKey=stId(),serial=++aiRequestSerial;
      const context={...(window.STUstaWizard?.getContext()||{})};
      const snapshot=JSON.stringify({device,issue,context});
      const isCurrent=()=>serial===aiRequestSerial&&snapshot===JSON.stringify({device:document.getElementById('deviceSelect').value,issue:document.getElementById('issueInput').value.trim(),context:window.STUstaWizard?.getContext()||{}});
      const renderOptions={context,device,issue};
      lastDiagnosedIssue=`${device}: ${issue}`;
      const initial=showFallbackDiagnostic(device,issue,{record:false});
      // Güvenlik yönlendirmesi ve belirti rehberi bağlantıyı beklemeden görünür.
      if(initial.requires_model&&!context.model_unknown){}
      if(initial.source==='emergency'||initial.source==='safety'||initial.source==='advisory'||initial.source==='manual'||initial.requires_document_review||initial.code_unverified){renderDiagnostic(initial);return;}
      button.disabled=true;document.getElementById('aiLoading').classList.remove('hidden');
      const source=document.getElementById('aiSource');if(source)source.textContent='Belirti rehberi · AI değerlendirmesi bekleniyor…';
      try {
        const data=await stApi('ai',{device,issue,model_id:context.model_id||'',code:context.code||'',model_unknown:context.model_unknown===true,scope_confirmed:context.scope_confirmed===true},requestKey);
        if(!isCurrent())return;
        if(data.text)renderDiagnostic(data,renderOptions);else showFallbackDiagnostic(device,issue,renderOptions);
      }catch(error){if(isCurrent()){showFallbackDiagnostic(device,issue,renderOptions);if(source)source.textContent='Belirti rehberi · AI bağlantısı kurulamadı';}}
      finally{if(serial===aiRequestSerial){button.disabled=false;button.classList.remove('hidden');document.getElementById('aiLoading').classList.add('hidden');}}
    }

    window.diagnoseIssue = diagnoseIssue;
    function sendToWhatsappFromAI() {
      const issue = document.getElementById('issueInput')?.value.trim() || lastDiagnosedIssue || 'Kombi / Klima arızası';
      const message = `Merhaba Sağlam Teknik, AI Usta üzerinden ön bilgi hazırladım.\n\nCihaz: ${document.getElementById('deviceSelect')?.value || ''}\n${issue}\n\nServis uygunluğunu görüşmek istiyorum.`;
      window.open('https://wa.me/905346225515?text='+encodeURIComponent(message), '_blank','noopener,noreferrer');
    }

    window.sendToWhatsappFromAI = sendToWhatsappFromAI;
    function selectDeviceAndFocus(device) {
      if(window.STUstaWizard){window.STUstaWizard.open(device);return;}
      const select = document.getElementById('deviceSelect');
      select.value = device;
      document.getElementById('issueInput').focus();
      document.getElementById('hero').scrollIntoView({ behavior: 'smooth' });
    }

    // 2. ARIZA KAYDI BIRAK
    let ticketReturnFocus=null;
    function toggleServiceTicketModal(show) {
      const modal = document.getElementById('serviceTicketModal');
      if(!modal)return false;
      if (show) {
        if(!modal.classList.contains('hidden'))return true;
        ticketReturnFocus=document.activeElement;
        document.getElementById('ticketSubmitBtn').classList.remove('hidden');
        document.getElementById('ticketSuccessMsg').classList.add('hidden');
        stError('ticketError','');
        document.getElementById('ticketQueueSummary')?.remove();
        const currentIssue = document.getElementById('issueInput')?.value.trim()||'';
        const currentDevice = document.getElementById('deviceSelect')?.value||'';
        if (currentIssue) {
          document.getElementById('ticketIssue').value = currentIssue;
        }
        if (currentDevice) {
          document.getElementById('ticketDevice').value = currentDevice;
        }
        window.STPriorityTicket?.setLevel(document.getElementById('serviceTicketForm'),'standard');
        modal.classList.remove('hidden');
        modal.setAttribute('aria-hidden','false');
        document.body.classList.add('ah-dialog-open');
        const card=modal.querySelector('.ah-modal-card');if(card)card.scrollTop=0;
        document.getElementById('ticketName').focus({preventScroll:true});
      } else {
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden','true');
        document.body.classList.remove('ah-dialog-open');
        ticketReturnFocus?.focus?.({preventScroll:true});
      }
      return true;
    }
    // Capture at the document so old inline HTML and premium.js do not open it twice.
    document.addEventListener('click',event=>{
      const prioritySubmit=event.target.closest?.('#ticketSubmitBtn');
      if(prioritySubmit&&window.ST_PREVIEW===true&&document.getElementById('ticketServiceLevel')?.value==='priority'&&window.STPriorityTicket){
        event.preventDefault();event.stopImmediatePropagation();
        if(document.getElementById('serviceTicketForm').reportValidity())submitServiceTicket();
        return;
      }
      const control=event.target.closest?.('[data-ticket-open],.usta-ticket,[data-ticket-close],#serviceTicketModal .ah-modal-close');
      if(!control||!document.getElementById('serviceTicketModal'))return;
      event.preventDefault();event.stopImmediatePropagation();
      toggleServiceTicketModal(!control.matches('[data-ticket-close],.ah-modal-close'));
      if(control.dataset.ticketDevice){
        document.getElementById('ticketDevice').value=control.dataset.ticketDevice;
        if(window.STUstaWizard?.getContext()?.device!==control.dataset.ticketDevice)document.getElementById('ticketIssue').value='';
      }
      if(control.dataset.ticketLevel)window.STPriorityTicket?.setLevel(document.getElementById('serviceTicketForm'),control.dataset.ticketLevel);
    },true);
    document.addEventListener('submit',event=>{
      if(event.target.id!=='serviceTicketForm')return;
      event.preventDefault();event.stopImmediatePropagation();submitServiceTicket(event);
    },true);
    document.addEventListener('keydown',event=>{const modal=document.getElementById('serviceTicketModal');if(!modal||modal.classList.contains('hidden'))return;if(event.key==='Escape'){event.preventDefault();toggleServiceTicketModal(false);return;}if(event.key==='Tab'){const items=[...modal.querySelectorAll('button,a[href],input,select,textarea')].filter(e=>e.offsetParent!==null&&!e.disabled&&e.tabIndex!==-1),first=items[0],last=items[items.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}}});

    async function submitServiceTicket(e) {
      if (e) e.preventDefault();

      const name = document.getElementById('ticketName')?.value?.trim() || '';
      const phone = document.getElementById('ticketPhone')?.value?.trim() || '';
      const district = document.getElementById('ticketDistrict')?.value?.trim() || '';
      const neighborhood = document.getElementById('ticketNeighborhood')?.value?.trim() || '';
      const street = document.getElementById('ticketStreet')?.value?.trim() || '';
      const device = document.getElementById('ticketDevice')?.value || 'Kombi';
      const issue = [document.getElementById('ticketIssue')?.value?.trim() || '',neighborhood?'Mahalle: '+neighborhood:'',street?'Sokak: '+street:''].filter(Boolean).join(' | ').slice(0,2000);

      if (!name || !phone || !district || !issue) {
        alert("Lütfen tüm alanları doldurunuz.");
        return false;
      }

      const submitBtn = document.getElementById('ticketSubmitBtn');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = 'Talebiniz iletiliyor…';
      }

      const waMessage = `*YENİ ARIZA KAYDI*%0A%0A*Müşteri:* ${encodeURIComponent(name)}%0A*Telefon:* ${encodeURIComponent(phone)}%0A*İlçe:* ${encodeURIComponent(district)}%0A*Cihaz:* ${encodeURIComponent(device)}%0A*Arıza:* ${encodeURIComponent(issue)}`;
      const waBtn = document.getElementById('ticketDirectWhatsappBtn');
      if (waBtn) {
        waBtn.href = `https://wa.me/905346225515?text=${waMessage}`;
      }

      const form = document.getElementById('serviceTicketForm');
      let payload = {name,phone,district,device,issue,website:document.getElementById('ticketWebsite').value};
      stError('ticketError','');document.getElementById('ticketSuccessMsg').classList.add('hidden');
      try {
        if(document.getElementById('ticketServiceLevel')?.value==='priority'&&!window.STPriorityTicket)throw Error('Öncelikli servis ücret onayı yüklenemedi. Sayfayı yenileyin veya uygunluğu telefonla görüşün.');
        if(window.STPriorityTicket){
          const confirmation=await STPriorityTicket.beforeSubmit(form,payload);
          if(!confirmation.ready)return false;
          payload=confirmation.payload;
        }
        const saved=await stApi('ticket',payload,stRequestKey(form,payload));
        const note=document.querySelector('#ticketSuccessMsg p');
        if(note)note.textContent=saved.delivery==='sent'?'Talebiniz kaydedildi ve ekibimize bildirildi. Randevu uygunluğunu birlikte netleştireceğiz.':'Talebiniz kaydedildi. Ekibimize bildirim bekliyor; acil destek için bizi arayabilir veya WhatsApp’tan ulaşabilirsiniz.';
        if(saved.queue&&typeof saved.queue.message==='string'){
          let summary=document.getElementById('ticketQueueSummary');
          if(!summary){summary=document.createElement('p');summary.id='ticketQueueSummary';summary.className='ticket-queue-summary';document.getElementById('ticketSuccessMsg').append(summary);}
          summary.textContent=saved.queue.message;
        }
        document.getElementById('ticketSuccessMsg').classList.remove('hidden');
        submitBtn.classList.add('hidden');
        delete form.dataset.requestKey; delete form.dataset.requestBody;
      } catch (err) {
        window.STPriorityTicket?.handleError(form,err);
        stError('ticketError',err.name==='AbortError'?'Bağlantı zaman aşımına uğradı. Aynı talebi tekrar gönderebilirsiniz.':err.message);
      } finally { submitBtn.disabled=false; submitBtn.textContent=window.STPriorityTicket?.submitLabel(form)||'Servis talebini gönder'; }
      return false;
    }

    function handleServiceCardClick(category) {
      filterByCat(category);
      const deviceMap = { kombi: 'Kombi', klima: 'Klima', petek: 'Petek' };
      selectDeviceAndFocus(deviceMap[category] || 'Kombi');
    }

    // 3. DOĞRULANMIŞ YORUMLAR VERİTABANI
    const allFileReviews = JSON.parse(document.getElementById('st-review-seeds')?.textContent || '[]');

    window.STPublishedReviewSeeds = allFileReviews.map(review => ({...review}));

    let currentFilterCat = 'all';

    function renderReviewsList(list) {
      const container=document.getElementById('reviewsContainer');
      if(!container)return;
      container.replaceChildren();
      if(!list||!list.length){
        container.innerHTML='<div class="ah-review-empty"><span aria-hidden="true">↗</span><h3>Deneyiminize yer var.</h3><p>Bu filtrede yayımlanmış yorum bulunmuyor. Hizmet aldıysanız deneyiminizi paylaşabilirsiniz.</p></div>';
        return;
      }
      list.forEach(r=>{
        const author=stEscape(r.author||r.ad||r.isim||'Müşteri');
        const comment=stEscape(r.comment||r.mesaj||r.yorum||'');
        const rating=Math.max(1,Math.min(5,parseInt(r.rating||r.puan||5,10)||5));
        const date=stEscape(r.date||r.tarih||'');
        const service=stEscape(r.service||r.hizmet||'Teknik servis');
        const source=r.source==='site'?'Yönetici onaylı':'Kaynak değerlendirmesi';
        const card=document.createElement('article');
        card.className='review-item ah-review';
        card.dataset.category=r.cat||'kombi';
        card.innerHTML='<div class="ah-review-head"><div><h4>'+author+'</h4><small>'+[date,service].filter(Boolean).join(' · ')+'</small></div><span class="ah-review-rating" aria-label="5 üzerinden '+rating+'">'+'★'.repeat(rating)+'<span aria-hidden="true">'+'☆'.repeat(5-rating)+'</span></span></div>'+(comment?'<p>“'+comment+'”</p>':'<p>Yazılı not eklenmemiş.</p>')+'<small>'+source+'</small>';
        container.appendChild(card);
      });
    }

    function filterByCat(category, ev) {
      currentFilterCat=category;
      const keys={all:'btnCatAll',kombi:'btnCatKombi',klima:'btnCatKlima',petek:'btnCatPetek'};
      Object.entries(keys).forEach(([key,id])=>{
        const button=document.getElementById(id);if(!button)return;
        button.className='cat-filter-btn'+(key===category?' is-active':'');
        button.setAttribute('aria-pressed',String(key===category));
      });
      applyAllFilters();
    }

    function filterBySearch() {
      applyAllFilters();
    }

    function applyAllFilters() {
      const input = document.getElementById('reviewSearchInput');
      const q = input ? input.value.toLowerCase().trim() : '';
      let list = allFileReviews;

      if (currentFilterCat !== 'all') {
        list = list.filter(r => r.cat === currentFilterCat);
      }

      if (q) {
        list = list.filter(r => {
          const author = (r.author || r.ad || r.isim || '').toLowerCase();
          const comment = (r.comment || r.mesaj || r.yorum || '').toLowerCase();
          const service = (r.service || r.hizmet || '').toLowerCase();
          return author.includes(q) || comment.includes(q) || service.includes(q);
        });
      }

      renderReviewsList(list);
    }


    async function loadApprovedReviews() {
      try { const r=await fetch('/api.php?action=reviews',{credentials:'same-origin'});if(r.ok){const a=await r.json();const ids=new Set(allFileReviews.map(r=>r.id).filter(Boolean));allFileReviews.unshift(...(a.reviews||[]).filter(r=>!ids.has(r.id)));} } catch(e) {}
      applyAllFilters();
    }
    async function yorumMailGonder(event) {
      event.preventDefault();
      const form=document.getElementById('musteriYorumFormu');
      const payload={author:document.getElementById('yorumIsim').value.trim(),district:document.getElementById('yorumIlce').value.trim(),service:document.getElementById('yorumHizmet').value,rating:parseInt(document.getElementById('yorumPuan').value,10),comment:document.getElementById('yorumMetni').value.trim(),consent:document.getElementById('yorumYayinOnayi').checked,website:document.getElementById('yorumWebsite').value};
      const btn=document.getElementById('yorumGonderBtn');btn.disabled=true;stError('yorumError','');document.getElementById('yorumOnayMsg').classList.add('hidden');btn.innerHTML='Yorumunuz kaydediliyor…';
      try{await stApi('review',payload,stRequestKey(form,payload));document.getElementById('yorumOnayMsg').classList.remove('hidden');form.reset();delete form.dataset.requestKey;delete form.dataset.requestBody;}
      catch(e){stError('yorumError',e.name==='AbortError'?'Bağlantı zaman aşımına uğradı. Aynı yorumu tekrar gönderebilirsiniz.':e.message);}
      finally{btn.disabled=false;btn.innerHTML='Yorumu onaya gönder <span aria-hidden="true">↗</span>';}
    }
    window.addEventListener('DOMContentLoaded',()=>{if(document.querySelector('[data-premium-reviews]'))return;renderReviewsList(allFileReviews);loadApprovedReviews();});
