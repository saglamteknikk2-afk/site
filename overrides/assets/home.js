

    // 1. GEMINI AI USTA MOTORU
    let lastDiagnosedIssue = "";

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

    function renderDiagnostic(data) {
      const box=document.getElementById('aiResultBox'),response=document.getElementById('aiResponseText');
      stAiContact(data.emergency_phone);
      const actions=document.querySelector('#aiResultBox .usta-result-actions');if(actions)actions.hidden=data.source==='advisory'||data.source==='emergency';
      const context=window.STUstaWizard?.getContext()||{},device=document.getElementById('deviceSelect').value;
      const match=data.source==='manual'?window.STFaults?.lookup({device:device.toLowerCase(),brand:context.brand||'',model_id:context.model_id||'',code:context.code||'',scope_confirmed:context.scope_confirmed===true}):null;
      const safe=value=>stEscape(value||'').replace(/\n/g,'<br>');
      if(data.source==='advisory'||data.source==='emergency'){
        const phone=['187','112'].includes(data.emergency_phone)?data.emergency_phone:'';
        response.innerHTML='<section class="usta-result-alert" aria-label="Öncelikli bilgi"><p>'+safe(data.text)+'</p>'+(phone?'<a class="usta-emergency-call" href="tel:'+phone+'">'+phone+' acil hattını ara →</a>':'')+'</section>';
      }else{
        const text=match?.verified?match.definition.code+' · '+match.definition.meaning:(data.text||'Marka/model ve arıza belirtisini biraz daha tarif eder misiniz?');
        const observation=match?.verified?[match.definition.safe_observation,match.scope_warning].filter(Boolean).join(' '):'Ekrandaki tam kodu ve belirtinin hangi kullanım sırasında çıktığını, kapağı açmadan not edin.';
        const heading=match?.verified?'Üretici belgesindeki açıklama':data.source==='ai'?'AI ön değerlendirmesi':'İlk yönlendirme';
        response.innerHTML='<div class="usta-result-grid"><section class="usta-result-main" aria-label="'+safe(heading)+'"><p>'+safe(text)+'</p></section><section><h4>Güvenli gözlem</h4><p>'+safe(observation)+'</p></section><section><h4>Sonraki adım</h4><p>Belirti devam ediyorsa model ve gözlemlerinizi paylaşarak kontrolü planlayalım. Gaz, elektrik ve soğutucu devreye müdahale etmeyin.</p></section></div>';
      }
      const source=document.getElementById('aiSource');
      if(source)source.textContent=data.source==='advisory'?'Üreticinin modele özel duyurusu':data.source==='manual'?'Seçilen modelin üretici belgesi':data.source==='ai'?'AI teknik ön değerlendirme':data.source==='emergency'?'Öncelikli güvenlik bilgisi':'Belirti rehberi';
      box.classList.remove('hidden');
      const guide=document.getElementById('aiGuideLink');
      if(guide){
        const local=window.STDiagnosticGuide?.(document.getElementById('deviceSelect').value,document.getElementById('issueInput').value);
        const path=data.guide_path||local?.guide_path||'';
        guide.href=stDiagnosticGuideURL(path);
        guide.hidden=data.source==='emergency'||data.source==='advisory';
      }
      const reference=document.getElementById('aiManualReference');
      if(reference){reference.replaceChildren();reference.hidden=!data.source_url;if(data.source_url&&/^https:\/\//.test(data.source_url)){const link=document.createElement('a');link.href=data.source_url;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Üretici kaynağını aç ↗';reference.append(link,document.createElement('br'),document.createTextNode(data.source_locator||''));}}
    }

    function showFallbackDiagnostic(device, issue) {
      const data=window.STDiagnosticGuide?window.STDiagnosticGuide(device,issue,window.STUstaWizard?.getContext()||{}):{source:'guide',text:'Marka/modeli, hata kodunu ve sorunun ne zaman oluştuğunu paylaşın. İç parçalara müdahale etmeden Sağlam Teknik ile servis kontrolü planlayabilirsiniz: 0534 622 5515.'};
      renderDiagnostic(data);return data;
    }

    async function diagnoseIssue() {
      const device=document.getElementById('deviceSelect').value,issue=document.getElementById('issueInput').value.trim();
      if(issue.length<3){alert('Lütfen arıza belirtisini veya hata kodunu en az 3 karakterle yazın.');return;}
      if(issue.length>1200){alert('Arıza açıklamasını biraz kısaltın; en fazla 1200 karakter kullanabilirsiniz.');return;}
      const button=document.getElementById('askBtn');if(button.disabled)return;
      const requestKey=stId();
      lastDiagnosedIssue=`${device}: ${issue}`;
      const initial=showFallbackDiagnostic(device,issue);
      // Güvenlik yönlendirmesi ve belirti rehberi bağlantıyı beklemeden görünür.
      if(initial.source==='emergency'||initial.source==='advisory'||initial.source==='manual'||initial.requires_document_review)return;
      button.disabled=true;document.getElementById('aiLoading').classList.remove('hidden');
      const source=document.getElementById('aiSource');if(source)source.textContent='Belirti rehberi · AI değerlendirmesi bekleniyor…';
      try {
        const context=window.STUstaWizard?.getContext()||{};
        const data=await stApi('ai',{device,issue,model_id:context.model_id||'',code:context.code||'',scope_confirmed:context.scope_confirmed===true},requestKey);
        if(data.text)renderDiagnostic(data);else showFallbackDiagnostic(device,issue);
      }catch(error){showFallbackDiagnostic(device,issue);if(source)source.textContent='Belirti rehberi · AI bağlantısı kurulamadı';}
      finally{button.disabled=false;button.classList.remove('hidden');document.getElementById('aiLoading').classList.add('hidden');}
    }

    function sendToWhatsappFromAI() {
      const issue = document.getElementById('issueInput')?.value.trim() || lastDiagnosedIssue || 'Kombi / Klima arızası';
      const message = `Merhaba Sağlam Teknik, AI Usta üzerinden ön bilgi hazırladım.\n\nCihaz: ${document.getElementById('deviceSelect')?.value || ''}\n${issue}\n\nServis uygunluğunu görüşmek istiyorum.`;
      window.open('https://wa.me/905346225515?text='+encodeURIComponent(message), '_blank','noopener,noreferrer');
    }

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
      if (show) {
        ticketReturnFocus=document.activeElement;
        document.getElementById('ticketSubmitBtn').classList.remove('hidden');
        document.getElementById('ticketSuccessMsg').classList.add('hidden');
        stError('ticketError','');
        const currentIssue = document.getElementById('issueInput').value.trim();
        const currentDevice = document.getElementById('deviceSelect').value;
        if (currentIssue) {
          document.getElementById('ticketIssue').value = currentIssue;
        }
        if (currentDevice) {
          document.getElementById('ticketDevice').value = currentDevice;
        }
        modal.classList.remove('hidden');
        document.body.classList.add('ah-dialog-open');
        document.getElementById('ticketName').focus({preventScroll:true});
      } else {
        modal.classList.add('hidden');
        document.body.classList.remove('ah-dialog-open');
        ticketReturnFocus?.focus?.({preventScroll:true});
      }
    }
    document.addEventListener('keydown',event=>{const modal=document.getElementById('serviceTicketModal');if(!modal||modal.classList.contains('hidden'))return;if(event.key==='Escape'){event.preventDefault();toggleServiceTicketModal(false);return;}if(event.key==='Tab'){const items=[...modal.querySelectorAll('button,a[href],input,select,textarea')].filter(e=>e.offsetParent!==null&&!e.disabled&&e.tabIndex!==-1),first=items[0],last=items[items.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}}});

    async function submitServiceTicket(e) {
      if (e) e.preventDefault();

      const name = document.getElementById('ticketName')?.value?.trim() || '';
      const phone = document.getElementById('ticketPhone')?.value?.trim() || '';
      const district = document.getElementById('ticketDistrict')?.value?.trim() || '';
      const device = document.getElementById('ticketDevice')?.value || 'Kombi';
      const issue = document.getElementById('ticketIssue')?.value?.trim() || '';

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
      const payload = {name,phone,district,device,issue,website:document.getElementById('ticketWebsite').value};
      stError('ticketError','');document.getElementById('ticketSuccessMsg').classList.add('hidden');
      try {
        await stApi('ticket',payload,stRequestKey(form,payload));
        document.getElementById('ticketSuccessMsg').classList.remove('hidden');
        submitBtn.classList.add('hidden');
        delete form.dataset.requestKey; delete form.dataset.requestBody;
      } catch (err) {
        stError('ticketError',err.name==='AbortError'?'Bağlantı zaman aşımına uğradı. Aynı talebi tekrar gönderebilirsiniz.':err.message);
      } finally { submitBtn.disabled=false; submitBtn.innerHTML='Servis talebini gönder <span aria-hidden="true">↗</span>'; }
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
