/* Existing published reviews plus newest approved production reviews on first load. */
(() => {
  'use strict';
  const script = document.currentScript;
  const siteBase = script?.src ? new URL('../', script.src) : new URL('./', document.baseURI);
  const services = ['Kombi Bakımı / Onarımı', 'Klima Bakımı / Montajı', 'Makineli Petek Temizliği', 'Acil Servis Hizmeti'];
  const normalize = value => String(value || '').toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ı/g, 'i');
  function init() {
    const root = document.querySelector('[data-premium-reviews]');
    if (!root || root.dataset.reviewsReady) return;
    root.dataset.reviewsReady = 'true';
    const byId = id => root.querySelector(`#${id}`);
    const container = byId('reviewsContainer');
    const form = byId('musteriYorumFormu');
    if (!container || !form) return;
    const preview = window.ST_PREVIEW === true || document.body.dataset.stMode === 'preview' || location.protocol === 'file:' || /(^|\.)github\.io$/i.test(location.hostname);
    const seeds = Array.isArray(window.STPublishedReviewSeeds) ? window.STPublishedReviewSeeds.map((review, index) => ({...review, id: `existing-${index}`, source: 'existing'})) : [];
    const deletedIds = new Set();
    let reviews = [...seeds].sort((a,b)=>reviewTime(b)-reviewTime(a));
    let category = 'all';
    let limit = 6;
    let submitting = false;
    let requestKey = '';
    let requestBody = '';
    let csrf = '';
    let liveLoad = null;
    let liveLoaded = preview;
    const filters = [...root.querySelectorAll('[data-review-category]')];
    const status = byId('premiumReviewStatus');
    const count = byId('premiumReviewCount');
    const more = byId('premiumReviewsMore');
    const submit = byId('yorumGonderBtn');
    const error = byId('yorumError');
    const success = byId('yorumOnayMsg');

    function element(tag, className, content) {
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (content !== undefined) node.textContent = content;
      return node;
    }
    function setMessage(node, message) {
      node.textContent = message;
      node.hidden = !message;
      node.classList.toggle('hidden', !message);
    }
    function reviewTime(review) {
      const created = Number(review.created);
      if (Number.isFinite(created) && created > 0) {
        const timestamp = created >= 1e12 ? created : created * 1000;
        if (Number.isFinite(new Date(timestamp).getTime())) return timestamp;
      }
      const calendarTime = (year, month, day) => {
        const timestamp = Date.UTC(year, month, day);
        const result = new Date(timestamp);
        // Date.UTC otherwise silently changes 31 February into a March date.
        return result.getUTCFullYear() === year && result.getUTCMonth() === month && result.getUTCDate() === day ? timestamp : 0;
      };
      const date = normalize(review.date).trim();
      const numeric = date.match(/^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$/);
      if (numeric) return calendarTime(Number(numeric[3]), Number(numeric[2]) - 1, Number(numeric[1]));
      const months = {oca: 0, sub: 1, mar: 2, nis: 3, may: 4, haz: 5, tem: 6, agu: 7, eyl: 8, eki: 9, kas: 10, ara: 11};
      const turkish = date.match(/^(\d{1,2})\s+([a-z]+)\s+(\d{4})$/);
      if (turkish && months[turkish[2].slice(0, 3)] !== undefined) return calendarTime(Number(turkish[3]), months[turkish[2].slice(0, 3)], Number(turkish[1]));
      const iso = date.match(/^(\d{4})-(\d{2})-(\d{2})(?:t.*)?$/);
      if (iso) {
        const calendar = calendarTime(Number(iso[1]), Number(iso[2]) - 1, Number(iso[3]));
        if (!calendar) return 0;
        const timestamp = Date.parse(date);
        return Number.isFinite(timestamp) ? timestamp : 0;
      }
      return 0;
    }
    function mergeApproved(approved) {
      const contentKey = review => {
        const author = normalize(review.author).replace(/[^a-z0-9]+/g, ' ').trim();
        const comment = normalize(review.comment).replace(/[^a-z0-9]+/g, ' ').trim();
        return author && comment ? `${author}\u0000${comment}` : '';
      };
      const identifiers = new Set();
      const content = new Set();
      // A live copy wins over its build-time copy, without changing stored rows.
      const merged = [...approved].sort((a, b) => reviewTime(b) - reviewTime(a)).concat(seeds).filter(review => {
        const id = String(review.id);
        const identity = contentKey(review);
        const rawId=id.startsWith('site-')?id.slice(5):id;
        if (deletedIds.has(id)||deletedIds.has(rawId)||identifiers.has(id) || (identity && content.has(identity))) return false;
        identifiers.add(id);
        if (identity) content.add(identity);
        return true;
      });
      return merged.sort((a, b) => reviewTime(b) - reviewTime(a));
    }
    function render({append = false, preserveStatic = false} = {}) {
      const query = normalize(byId('reviewSearchInput')?.value.trim());
      const filtered = reviews.filter(review => (category === 'all' || review.cat === category) && (!query || normalize([review.author, review.comment, review.service, review.district].join(' ')).includes(query)));
      const visible = filtered.slice(0, limit);
      const fragment = document.createDocumentFragment();
      const current = [...container.querySelectorAll(':scope > .pr-review')];
      const samePrefix = current.length <= visible.length && current.every((card, index) => card.dataset.reviewId === String(visible[index].id));
      // The first six cards are rendered into HTML at build time. Keep those
      // nodes intact; More appends the next batch instead of recreating them.
      const retain = (append || preserveStatic) && samePrefix && current.length > 0;
      (retain ? visible.slice(current.length) : visible).forEach(review => {
        const rating = Math.max(1, Math.min(5, Number.parseInt(review.rating, 10) || 5));
        const card = element('article', 'pr-review');
        card.dataset.reviewId = String(review.id);
        const head = element('div', 'pr-review-head');
        const identity = element('div', 'pr-review-identity');
        const author = String(review.author || 'Müşteri');
        const avatar = element('span', 'pr-review-avatar', author.replace(/\*/g, '').trim().charAt(0).toLocaleUpperCase('tr-TR') || 'S');
        avatar.setAttribute('aria-hidden', 'true');
        identity.append(element('h3', '', author), element('p', 'pr-review-meta', [review.date, review.service].filter(Boolean).join(' · ')));
        head.append(avatar, identity);
        const stars = element('span', 'pr-review-rating', '★'.repeat(rating) + '☆'.repeat(5 - rating));
        stars.setAttribute('role', 'img');
        stars.setAttribute('aria-label', `5 üzerinden ${rating} puan`);
        card.append(head, stars);
        const quote = element('blockquote', '', review.comment ? String(review.comment) : 'Bu değerlendirmeye yazılı not eklenmemiş.');
        const origin=element('p','pr-review-origin','Müşteri yorumu');
        if(review.source==='site'){
          const verified=review.service_verified===true;
          const badge=element('span','pr-review-badge'+(verified?' is-service-verified':''),verified?'✓ Hizmet doğrulandı':'✓ Yayın onaylı');
          badge.title=verified?'Hizmet kaydıyla eşleşen değerlendirme':'Yorumun yayımlanması yönetici tarafından onaylandı.';
          origin.append(badge);
        }
        card.append(quote,origin);
        fragment.append(card);
      });
      if (!visible.length) {
        const empty = element('div', 'pr-empty');
        empty.append(element('h3', '', 'Bu aramada yorum bulunamadı.'), element('p', '', 'Başka bir sözcük deneyin veya tüm hizmetleri seçin.'));
        fragment.append(empty);
      }
      if (retain && visible.length) container.append(fragment);
      else container.replaceChildren(fragment);
      const text = `${filtered.length} değerlendirme${filtered.length ? ` · ${visible.length} gösteriliyor` : ''}`;
      if (count) count.textContent = text;
      if (more) more.hidden = filtered.length <= visible.length && liveLoaded;
      filters.forEach(button => {
        const active = button.dataset.reviewCategory === category;
        button.classList.toggle('is-active', active);
        button.setAttribute('aria-pressed', String(active));
      });
    }
    filters.forEach(button => button.addEventListener('click', () => { category = button.dataset.reviewCategory; limit = 6; render(); }));
    byId('reviewSearchInput')?.addEventListener('input', () => { limit = 6; render(); });
    more?.addEventListener('click', () => {
      const previous = container.querySelectorAll('.pr-review').length;
      limit += 6;
      render({append: true});
      const next = container.querySelectorAll('.pr-review')[previous];
      if (next) { next.tabIndex = -1; next.focus({preventScroll: true}); }
      loadApprovedReviews();
    });
    root.querySelector('[data-review-privacy]')?.setAttribute('href', new URL('aydinlatma.html', siteBase).href);
    root.querySelector('[data-review-live-site]')?.setAttribute('href', 'https://saglamkombiklima.com.tr/#yorumFormKutusu');

    async function request(action, options = {}) {
      if (preview) throw new Error('Bu ön izlemede yorum gönderimi kapalıdır.');
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 15000);
      try {
        const url = new URL('api.php', siteBase);
        url.searchParams.set('action', action);
        const response = await fetch(url, {credentials: 'same-origin', cache: 'no-store', ...options, signal: controller.signal});
        let data;
        try { data = await response.json(); } catch (_) { throw new Error('Yorum sunucusuna ulaşılamadı. Lütfen daha sonra yeniden deneyin.'); }
        if (!response.ok || !data || data.ok !== true) {
          const failure = new Error(data?.error || 'İşlem tamamlanamadı.');
          failure.status = response.status;
          throw failure;
        }
        return data;
      } finally { clearTimeout(timeout); }
    }
    function loadApprovedReviews(force=false) {
      if (preview || liveLoad || (liveLoaded&&!force)) return;
      liveLoad = request('reviews').then(data => {
        if (!Array.isArray(data.reviews)) throw new Error('Yorum listesi doğrulanamadı.');
        for(const id of [...(Array.isArray(data.deleted_ids)?data.deleted_ids:[]),...(Array.isArray(data.deleted_seed_ids)?data.deleted_seed_ids:[])])deletedIds.add(String(id));
        const seen = new Set();
        const approved = data.reviews.filter(review => {
          if (!review || typeof review !== 'object' || !review.id || typeof review.author !== 'string' || typeof review.comment !== 'string' || (review.status && review.status !== 'approved') || seen.has(String(review.id))) return false;
          seen.add(String(review.id));
          return true;
        }).map(review => ({...review, id: `site-${review.id}`, source: 'site'}));
        reviews = mergeApproved(approved);
        liveLoaded = true;
        if (status) status.textContent = 'Müşteri yorumları · En yeniden eskiye.';
      }).catch(() => {
        if (status) status.textContent = 'Yeni yorumlar şu anda yüklenemedi. Görünen yorumlarda arama yapabilirsiniz.';
      }).finally(() => {
        liveLoad = null;
        render({append: true});
      });
    }
    async function postReview(payload, key) {
      for (let attempt = 0; attempt < 2; attempt++) {
        if (!csrf) {
          const data = await request('bootstrap');
          if (typeof data.csrf !== 'string' || !/^\d+\.[a-f0-9]{64}$/.test(data.csrf)) throw new Error('Form bağlantısı doğrulanamadı. Sayfayı yenileyip yeniden deneyin.');
          csrf = data.csrf;
        }
        try {
          return await request('review', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf, 'Idempotency-Key': key}, body: JSON.stringify(payload)});
        } catch (failure) {
          if (attempt === 0 && failure.status === 403 && failure.message === 'Sayfayı yenileyip tekrar deneyin.') { csrf = ''; continue; }
          throw failure;
        }
      }
    }
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (preview) { setMessage(error, 'Bu ön izlemede yorum gönderimi kapalıdır. Yorumunuz kaydedilmedi.'); return; }
      if (submitting || !form.reportValidity()) return;
      const payload = {author: byId('yorumIsim').value.trim(), district: byId('yorumIlce').value.trim(), service: byId('yorumHizmet').value, rating: Number.parseInt(byId('yorumPuan').value, 10), comment: byId('yorumMetni').value.trim(), consent: byId('yorumYayinOnayi').checked, website: byId('yorumWebsite').value};
      const length = value => Array.from(value).length;
      if (length(payload.author) < 2 || length(payload.author) > 80 || length(payload.district) < 2 || length(payload.district) > 80 || length(payload.comment) < 10 || length(payload.comment) > 2000 || !services.includes(payload.service) || !Number.isInteger(payload.rating) || payload.rating < 1 || payload.rating > 5 || !payload.consent || payload.website) {
        setMessage(error, 'Ad/rumuz, ilçe, hizmet, puan ve yorumunuzu kontrol edin; yayın onayını işaretleyin.');
        return;
      }
      const encoded = JSON.stringify(payload);
      if (requestBody !== encoded || !requestKey) {
        requestBody = encoded;
        requestKey = crypto.randomUUID ? crypto.randomUUID() : Array.from(crypto.getRandomValues(new Uint8Array(24)), byte => byte.toString(16).padStart(2, '0')).join('');
      }
      submitting = true;
      submit.disabled = true;
      submit.textContent = 'Yorumunuz iletiliyor…';
      form.setAttribute('aria-busy', 'true');
      setMessage(error, '');
      setMessage(success, '');
      try {
        const result = await postReview(payload, requestKey);
        if (result.status !== 'pending' || !result.id) throw new Error('Yorumun alındığı doğrulanamadı. Lütfen daha sonra yeniden deneyin.');
        setMessage(success, 'Teşekkür ederiz. Yorumunuz incelemeye iletildi; yönetici onayından sonra yayımlanabilir.');
        form.reset();
        requestKey = '';
        requestBody = '';
      } catch (failure) {
        setMessage(error, failure.name === 'AbortError' ? 'Bağlantı zaman aşımına uğradı. Aynı yorumu yeniden gönderebilirsiniz.' : failure.message);
      } finally {
        submitting = false;
        submit.disabled = false;
        submit.textContent = 'Yorumu onaya gönder ↗';
        form.removeAttribute('aria-busy');
      }
    });
    render({preserveStatic: true});
    if (preview) {
      root.classList.add('is-preview');
      submit.disabled = true;
      submit.textContent = 'Ön izlemede gönderim kapalı';
      root.querySelectorAll('[data-review-preview-note]').forEach(note => { note.hidden = false; });
      if (status) status.textContent = 'Müşteri yorumları · En yeniden eskiye. Ön izlemede yeni yorum gönderilemez.';
    } else {
      if (status) status.textContent = 'Müşteri yorumları yükleniyor…';
      loadApprovedReviews();
      window.addEventListener('focus',()=>loadApprovedReviews(true));
      document.addEventListener('visibilitychange',()=>{if(!document.hidden)loadApprovedReviews(true);});
      setInterval(()=>{if(!document.hidden)loadApprovedReviews(true);},60000);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once: true});
  else init();
})();
