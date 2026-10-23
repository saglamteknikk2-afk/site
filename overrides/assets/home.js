

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
        const observation=match?.verified?match.definition.safe_observation:'Ekrandaki tam kodu ve belirtinin hangi kullanım sırasında çıktığını, kapağı açmadan not edin.';
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
      if(initial.source==='emergency'||initial.source==='advisory'||initial.source==='manual')return;
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
    const allFileReviews = [
      { author: "Soner U.", date: "07 Nis 2026", service: "Kombi Tamiri", cat: "kombi", rating: 5, comment: "Bilgi ve tecrübesiyle hızlı çözüme ulaştım teşekkürler." },
      { author: "Muharrem T.", date: "07 Nis 2026", service: "Kombi Tamiri", cat: "kombi", rating: 5, comment: "Zamanında geldi, sorunu hemen tespit edip çözdü. İşinin ehli bir usta." },
      { author: "Sezgin E.", date: "08 Tem 2025", service: "Kombi Su Akıtıyor", cat: "kombi", rating: 5, comment: "Kombi su akıtıyordu, basınç kontrolü yapılarak sorun giderildi. Eline sağlık." },
      { author: "Mehmet Ali Ö.", date: "31 Mar 2023", service: "Klima Soğutmuyor", cat: "klima", rating: 5, comment: "Klima soğutmuyordu, kaçak testi ve gaz dolumu yapıldı. Çok memnun kaldım." },
      { author: "Hüsnü S.", date: "01 Eki 2022", service: "Kombi Su Akıtıyor", cat: "kombi", rating: 5, comment: "Çok teşekkür ederiz." },
      { author: "Baris C.", date: "16 Tem 2022", service: "Kombi Su Akıtıyor", cat: "kombi", rating: 5, comment: "İyi işçilik." },
      { author: "Alper A.", date: "06 Kas 2021", service: "Kombi Bakım", cat: "kombi", rating: 5, comment: "Yıllık bakım ve temizlik yapıldı. Çok dürüst ve temiz çalışan bir usta." },
      { author: "Egemen C.", date: "21 Kas 2020", service: "Kombi Tamiri", cat: "kombi", rating: 5, comment: "Sorunu hemen çözdü, güvenilir esnaf." },
      { author: "m ****", date: "10 Kas 2020", service: "Kombi Tamiri", cat: "kombi", rating: 5, comment: "Mustafa arkadaşa çok teşekkür ederim tavsiye ederim." },
      { author: "Sefa A.", date: "09 Kas 2020", service: "Kombi Tamiri", cat: "kombi", rating: 5, comment: "2 saat önce teklif verdi geldi hemen destek aldım, sorunu çözdü ustam. eline emeğine sağlık." },
      { author: "Oğuz S.", date: "19 Oca 2018", service: "Kombi Tamiri", cat: "kombi", rating: 5, comment: "Teşekkürler eline sağlık." },
      { author: "Talha A.", date: "06 Oca 2018", service: "Kombi Tamiri", cat: "kombi", rating: 4, comment: "" },
      { author: "e ****", date: "30 Ara 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "" },
      { author: "Ersin S.", date: "27 Ara 2017", service: "Kombi Su Akıtıyor", cat: "kombi", rating: 5, comment: "Bilgi vererek ve açıklayarak işi çözdü sağolsun.eline sağlık usta." },
      { author: "s ****", date: "27 Ara 2017", service: "Kombi Tamiri", cat: "kombi", rating: 5, comment: "Güvenilir ve harika işçilik.." },
      { author: "a ****", date: "27 Ara 2017", service: "Kombi Tamiri", cat: "kombi", rating: 5, comment: "Eline koluna sağlık usta..." },
      { author: "Fevzi E.", date: "23 Ara 2017", service: "Kombi Tamiri", cat: "kombi", rating: 5, comment: "Hızlı ve temiz iş. Kombinin yanmış 2 parçası değişti. Uygun fiyatlıydı." },
      { author: "Fadime A.", date: "23 Ara 2017", service: "Kombi Tamiri", cat: "kombi", rating: 5, comment: "Teşekkür ederiz gayet ilgiliydi ve sorunumuzu çözdü." },
      { author: "Enes T.", date: "23 Ara 2017", service: "Kombi Tamiri", cat: "kombi", rating: 5, comment: "İlgili ve hızlıydı." },
      { author: "Ayla E.", date: "19 Ara 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Zamanında geldi ve işini ustalıkla yaptı." },
      { author: "Belgin B.", date: "10 Ara 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Aldığımız hizmetten son derece memnun kaldık." },
      { author: "Adnan Ş.", date: "10 Ara 2017", service: "Kombi Servisi", cat: "kombi", rating: 4, comment: "Ustalık iyi, işimizi gördü." },
      { author: "Ozan Ç.", date: "29 Kas 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Daha önce de çağırmıştım motor dediler, Mustafa Bey kısa sürede hesaplı çözdü." },
      { author: "Oğuzhan Ö.", date: "17 Kas 2017", service: "Kombi Bakım", cat: "kombi", rating: 5, comment: "Profesyonel ve düzgün hizmet." },
      { author: "Kemal A.", date: "15 Kas 2017", service: "Kombi Servisi", cat: "kombi", rating: 4, comment: "Servis hızlıydı." },
      { author: "Kadir Eren S.", date: "10 Kas 2017", service: "Kombi Bakım", cat: "kombi", rating: 5, comment: "Kombi bakımı ve peteklerin temizliği yapıldı. Sorunsuz çalışıyor." },
      { author: "Muhammed A.", date: "10 Kas 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Kiracımın kombisi bozulmuştu, Mustafa bey gitti çok memnun kalmışlar." },
      { author: "Mert can E.", date: "07 Kas 2017", service: "Kombi Tamiri", cat: "kombi", rating: 5, comment: "Çok temiz iş yaptı kesinlikle tavsiye ediyorum." },
      { author: "Meray A.", date: "06 Kas 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Çok temiz bir iş çıkardı. Aynı gün parça değişimi yaptı." },
      { author: "İbrahim T.", date: "04 Kas 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Basınçlı temizlik ve bakım yaptırdım. İşinin ehli bir arkadaş." },
      { author: "Serkan B.", date: "01 Kas 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Pratik ve temiz çalışan biri. Çok memnun kaldım." },
      { author: "Ahmet Ö.", date: "30 Eki 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Kısa sürede yaptı tavsiye ederim." },
      { author: "Mert S.", date: "06 Eki 2017", service: "Kombi Bakım", cat: "kombi", rating: 5, comment: "Vaktinde gelen ve işinde başarılı usta." },
      { author: "Murat T.", date: "03 Eki 2017", service: "Kombi Tamiri", cat: "kombi", rating: 5, comment: "Pazar günü beni kurtararak süper servis sağladı." },
      { author: "Bülent K.", date: "09 Eyl 2017", service: "Makineli Petek Yıkama", cat: "petek", rating: 5, comment: "Hızlı ve dürüst usta. Kombi ve petek tavsiyeleri için teşekkürler." },
      { author: "Ilker B.", date: "07 Eyl 2017", service: "Klima Bakımı", cat: "klima", rating: 5, comment: "Uygun fiyata hızlı ve temiz iş oldu teşekkürler." },
      { author: "Seher T.", date: "05 Eyl 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Aynı gün içinde kombi arızası giderildi. Teşekkürler." },
      { author: "Fatih M.", date: "03 Eyl 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Yetkili servisin bozuk dediği kartı kurtardı problemi çözdü." },
      { author: "Murat A.", date: "28 Ağu 2017", service: "Klima Servisi", cat: "klima", rating: 5, comment: "İşinin hakkını veren birisi, gayet memnun kaldım." },
      { author: "**** ****", date: "24 Ağu 2017", service: "Klima Servisi", cat: "klima", rating: 5, comment: "Beklediğimden iyi hizmet, temiz çalıştı." },
      { author: "Benim A.", date: "11 Ağu 2017", service: "Klima Servisi", cat: "klima", rating: 5, comment: "Gaz dolumu süper hizmet sağol ustam." },
      { author: "Sabri Ö.", date: "07 Ağu 2017", service: "Makineli Petek Yıkama", cat: "petek", rating: 5, comment: "Sıkıntısız bir şekilde petek temizliği ve kombi bakımını yaptı." },
      { author: "Hasan A.", date: "05 Ağu 2017", service: "Klima Servisi", cat: "klima", rating: 5, comment: "Hızlı ve dürüst esnaf." },
      { author: "Mesut D.", date: "27 Tem 2017", service: "Klima Tamiri", cat: "klima", rating: 5, comment: "Söz verdiği saatte geldi, klima ilk günkü gibi soğutuyor." },
      { author: "Fatih A.", date: "26 Tem 2017", service: "Klima Bakımı", cat: "klima", rating: 5, comment: "Açık konuşan, güven veren usta." },
      { author: "Özgür Ş.", date: "26 Tem 2017", service: "Klima Gaz Dolumu", cat: "klima", rating: 4, comment: "İşimizi güzelce halletti." },
      { author: "Lvent Ş.", date: "19 Tem 2017", service: "Klima Tamiri", cat: "klima", rating: 5, comment: "Söz verdiği zamanda geldi, anlaştığımız fiyatta kaldı." },
      { author: "Abdullah A.", date: "17 Tem 2017", service: "Klima Tamiri", cat: "klima", rating: 5, comment: "Telefonda yapmam gerekeni anlatıp halletti, Allah razı olsun." },
      { author: "Metin T.", date: "09 Tem 2017", service: "Klima Tamiri", cat: "klima", rating: 5, comment: "Kaliteli servis herkese tavsiye ederim." },
      { author: "Alparslan Ç.", date: "06 Tem 2017", service: "Klima Servisi", cat: "klima", rating: 5, comment: "10 numara 5 yıldız dürüst bir arkadaş." },
      { author: "Cenk S.", date: "05 Tem 2017", service: "Klima Bakım", cat: "klima", rating: 5, comment: "İşinin ehli, uygun ücretle yaptı." },
      { author: "Dicle Can A.", date: "05 Tem 2017", service: "Klima Servisi", cat: "klima", rating: 5, comment: "Hızlı servis aldık teşekkürler." },
      { author: "Ersin C.", date: "03 Tem 2017", service: "Klima Servisi", cat: "klima", rating: 5, comment: "Sıcaktan kurtulduk eline sağlık." },
      { author: "**** ****", date: "02 Tem 2017", service: "Klima Servisi", cat: "klima", rating: 5, comment: "10 dakika içinde gelerek problemi halletti." },
      { author: "Nurdan T.", date: "04 Haz 2017", service: "Makineli Petek Yıkama", cat: "petek", rating: 5, comment: "Sözüne sadık, titiz çalışan bir usta." },
      { author: "Lutfi F.", date: "22 Nis 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Jet hızıyla gelip sorunu çözdü. Teşekkürler." },
      { author: "Pelin G.", date: "26 Mar 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Gönül rahatlığıyla tavsiye ederim." },
      { author: "İpek A.", date: "11 Şub 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Saygılı beyefendi, işini hakkıyla yaptı." },
      { author: "Serap T.", date: "24 Oca 2017", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Allah razı olsun Mustafa Bey sorunumuzu hemen çözdün." },
      { author: "Şenay Ç.", date: "23 Eyl 2016", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "İlk defa bir servis tam vaktinde kapımdaydı." },
      { author: "Ahmet K.", date: "08 Ağu 2016", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Çok uygun fiyata yaptı, eline sağlık ustam." },
      { author: "Uğur Ş.", date: "22 Haz 2016", service: "Kombi Servisi", cat: "kombi", rating: 5, comment: "Sanki kendi evinin eksiğini yapıyor gibi titiz çalıştı." }
    ];

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
