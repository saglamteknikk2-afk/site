/* Sağlam Teknik | GitHub Pages görsel test katmanı. PHP/Gemini/Telegram içermez. */
(() => {
  'use strict';
  const p = location.pathname.split('/').pop();
  if (p !== 'eca-kombi-proteus-premix-hm-tr-ariza-kodlari.html') return;

  const titleText = 'ECA Proteus Premix HM — Kombi hata kodları';
  const h1 = document.querySelector('.at-page-hero h1');
  if (!h1) return;
  h1.textContent = titleText;
  document.title = titleText + ' | Sağlam Teknik';
  document.querySelectorAll('.at-breadcrumb > span:last-child').forEach(el => { el.textContent = 'Proteus Premix HM'; });
  const metaTitle = document.querySelector('meta[property="og:title"]');
  if (metaTitle) metaTitle.setAttribute('content',document.title);

  const scope = document.querySelector('.fault-scope');
  const tableSection = document.querySelector('.fault-table-section');
  if (!scope || !tableSection) return;
  const scopeTitle = scope.querySelector('h2');
  if (scopeTitle) scopeTitle.textContent = 'Model ve üretici belge kapsamı';
  // Eski sayı listesi yerine tam ticari model adları.
  const names = [14,20,24,28,30,35,42,45].map(size => 'E.C.A. Proteus Premix ' + size + ' HM');
  const namedModels = scope.querySelector('p');
  if (namedModels) namedModels.innerHTML = '<strong>Modelinizi seçin:</strong> Aşağıdaki listede tam model adları yer alır. Model etiketini kontrol edin.';
  const lead = document.querySelector('.at-page-hero .at-lead');
  if (lead) lead.textContent = 'Cihaz etiketindeki tam modeli seçin. Hata kodlarını yalnızca kaynağın o modele ait olduğunu doğrulayabildiğimizde gösteriyoruz.';

  // Mevcut tabloda yalnız 14 HM'nin kaynak kapsamı açıkça belgelenmiş.
  const box = document.createElement('section');
  box.className = 'st-model-picker';
  box.setAttribute('aria-labelledby','st-model-title');
  const heading = document.createElement('h2');
  heading.id = 'st-model-title';
  heading.textContent = 'Cihazınızın tam modelini seçin';
  const label = document.createElement('label');
  label.htmlFor = 'st-model-select';
  label.textContent = 'Kombi modeli';
  const select = document.createElement('select');
  select.id = 'st-model-select';
  select.name = 'model';
  select.innerHTML = '<option value="">Modelinizi seçin…</option>';
  names.forEach((name, index) => {
    const option = document.createElement('option');
    option.value = index === 0 ? 'documented' : 'unverified';
    option.textContent = name;
    option.dataset.model = name;
    select.append(option);
  });
  const status = document.createElement('p');
  status.id = 'st-model-status';
  status.setAttribute('role','status');
  status.setAttribute('aria-live','polite');
  const source = document.createElement('p');
  source.className = 'st-model-source';
  source.textContent = 'Yalnızca üretici belgesinde eşleştirilebilen kodlar gösterilir. E01 ve E1 farklı kodlar olarak korunur.';
  box.append(heading,label,select,status,source);
  scope.parentNode.insertBefore(box,scope);
  // Kullanıcı modeli seçmeden kod listesini gösterme.
  tableSection.hidden = true;

  const update = () => {
    const chosen = select.selectedOptions[0];
    tableSection.hidden = true;
    if (!select.value) {
      status.className = 'st-model-status st-model-wait';
      status.textContent = 'Başlamak için cihazınızın tam model adını seçin.';
      return;
    }
    if (select.value !== 'documented') {
      status.className = 'st-model-status st-model-warning';
      status.textContent = chosen.textContent + ' için mevcut test arşivinde modele özel doğrulanmış hata kodu tablosu yok. Başka modele ait kodları göstermiyoruz; üretici belgesini kontrol edin veya cihazın ekranındaki kodu not edin.';
      return;
    }
    status.className = 'st-model-status st-model-ok';
    status.textContent = 'E.C.A. Proteus Premix 14 HM için üretici kılavuzuyla eşleştirilen kodlar aşağıda. Kod, kesin parça teşhisi değildir.';
    tableSection.hidden = false;
  };
  select.addEventListener('change',update);
  update();

  // Üreticiye dair teknik notların tamamı kaybolmaz; isteyen açarak inceler.
  const paras=[...scope.querySelectorAll('p')];
  const technical = paras.find(x => /49\.205\.876|görüntü dönüştürme|metin sınırını/.test(x.textContent));
  if (technical) {
    const details=document.createElement('details');
    details.className='st-source-notes';
    const summary=document.createElement('summary');
    summary.textContent='Kaynak ve belge kapsamı hakkında ayrıntılı not';
    details.append(summary);
    technical.replaceWith(details);
    details.append(technical);
  }
})();
