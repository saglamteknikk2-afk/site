"""Publish the actual old/new narrative for all changed pages, separately from service pages."""
from html import escape
from pathlib import Path
import json

def add_content_review(files,repo,metrics):
    from regions import load_editorial
    from service_editorial import load_services
    pages=load_editorial()
    before=json.loads((repo/'hybrid/data/editorial-before.json').read_text())['pages']
    pages.update(load_services())
    before.update(json.loads((repo/'hybrid/data/service-editorial-before.json').read_text())['pages'])
    total=len(pages)
    rows=[]
    for i,(route,page) in enumerate(sorted(pages.items()),1):
        after='<p class="lead">'+escape(page['lead'])+'</p>'
        for section in page['sections']:
            after+='<h4>'+escape(section['heading'])+'</h4>'+''.join('<p>'+escape(p)+'</p>' for p in section['paragraphs'])
            if section.get('bullets'):after+='<ul>'+''.join('<li>'+escape(p)+'</li>' for p in section['bullets'])+'</ul>'
        after+='<h4>Soru ve cevaplar</h4>'
        for question in page['faqs']:after+='<p><strong>'+escape(question['question'])+'</strong><br>'+escape(question['answer'])+'</p>'
        label=route.removesuffix('.html').replace('-',' ')
        rows.append('<details class="review-row" data-review-row data-search="'+escape(label+' '+page['headline']+' '+page.get('focus',''),quote=True)+'"><summary><span>'+str(i)+'. '+escape(label)+'</span><small>'+escape(page['headline'])+'</small></summary>'
                    '<p><a href="'+route+'" target="_blank" rel="noopener">Yayımlanan sayfayı aç ↗</a></p>'
                    '<div class="comparison"><section class="before"><h3>Çıkarılan eski anlatım</h3><p>'+escape(before[route])+'</p></section>'
                    '<section class="after"><h3>Yeni ana içerik</h3>'+after+'</section></div></details>')
    checks=metrics.get('combined_editorial',metrics['editorial'])
    review=('<!doctype html><html lang="tr" data-st-mode="production"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,follow"><title>'+str(total)+' Sayfa — Eski ve Yeni İçerik | Sağlam Teknik</title>'
            '<link rel="canonical" href="https://saglamkombiklima.com.tr/icerik-inceleme.html">'
            '<style>body{margin:0;background:#f4f1e8;color:#173b32;font:16px/1.75 system-ui,sans-serif}main{max-width:1260px;margin:auto;padding:24px 18px 70px}a{color:#174d40;text-underline-offset:4px}h1{font-size:clamp(28px,5vw,42px);line-height:1.2}h2,h3,h4{line-height:1.4}input{box-sizing:border-box;display:block;width:100%;font:inherit;padding:14px;background:#fffdf8;border:1px solid #aebca3;border-radius:6px}label{font-weight:650}.review-row{margin:14px 0;padding:18px;background:#fffdf8;border:1px solid #c4d0b7;border-radius:10px}.review-row>summary{cursor:pointer;min-height:48px;font-weight:700}.review-row>summary span,.review-row>summary small{display:block}.review-row>summary small{font-size:14px;font-weight:450;color:#53664d;margin-top:4px}.comparison{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:24px}.comparison section{min-width:0;padding:18px;overflow-wrap:anywhere}.before{background:#eee8dd;color:#5f574b}.after{background:#edf3e5}p,li{overflow-wrap:anywhere}small{font-size:13px}.notice{padding:14px 18px;border-left:4px solid #375e41;background:#e5ecd9}button{font:inherit;min-height:44px;padding:8px 14px;cursor:pointer;border:1px solid #315f47;border-radius:5px;color:#fff;background:#315f47;margin:12px 8px 0 0}nav{display:flex;flex-wrap:wrap;gap:12px}nav a{min-height:44px;padding:7px 0}@media(max-width:760px){.comparison{grid-template-columns:1fr}.review-row{padding:14px}.comparison section{padding:14px}}</style></head><body><main>'
            '<a href="index.html">← Siteyi aç</a><h1>'+str(total)+' sayfanın eski ve yeni ana içeriği</h1>'
            '<p>Her başlığı açarak kaldırılan ortak özeti ve yeni yazılan gövdeyi yan yana okuyabilirsiniz. Menü, logo, iletişim ve doğru teknik bilgiler ortak kalabilir; karşılaştırma burada sayfaların ana anlatımını gösterir.</p>'
            '<p class="notice">50 ilçe, 5 semt, 16 marka ve 13 arıza/hizmet gövdesi ayrı yazıldı. Yer ve marka adları karşılaştırmadan çıkarılarak uzun paragraf, cümle ve yakın kopya denetimi yapıldı. Bu denetim Google’ın bir özgünlük puanı veya dizine alma garantisi değildir.</p>'
            '<nav><a href="kucukcekmece-kombi-servisi.html">Küçükçekmece kombi</a><a href="avcilar-kombi-servisi.html">Avcılar kombi</a><a href="fatih-kombi-servisi.html">Fatih kombi</a><a href="teknik-rapor.html">Teknik rapor</a></nav>'
            '<label for="reviewSearch">İlçe, semt veya konu ara</label><input id="reviewSearch" type="search" placeholder="Örn. Küçükçekmece, sıcak su, Kilyos" autocomplete="off">'
            '<p id="reviewCount" role="status" aria-live="polite">'+str(total)+' sayfa</p><button type="button" id="reviewOpen">Görünenleri aç</button><button type="button" id="reviewClose">Kapat</button>'
            +''.join(rows)+'<footer><p>Bölge karşılaştırma kaynağı e5a51a6; marka ve arıza karşılaştırma kaynağı yüklediğin a1.zip. Yeni anlatım 29 Ekim 2026 tarihinde kontrol edildi. Bu inceleme arama dizinine kapalıdır.</p></footer>'
            '<script>(()=>{const rows=[...document.querySelectorAll("[data-review-row]")],q=document.getElementById("reviewSearch");const norm=s=>s.normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").replace(/ı/g,"i").toLocaleLowerCase("tr");q.addEventListener("input",()=>{const query=norm(q.value.trim());let count=0;for(const row of rows){row.hidden=!!query&&!norm(row.dataset.search).includes(query);if(!row.hidden)count++;}document.getElementById("reviewCount").textContent=count+" sayfa";});document.getElementById("reviewOpen").onclick=()=>rows.filter(r=>!r.hidden).forEach(r=>r.open=true);document.getElementById("reviewClose").onclick=()=>rows.forEach(r=>r.open=false);})();</script>'
            '</main></body></html>')
    files['icerik-inceleme.html']=review.encode()
    files['assets/editorial-content-audit.json']=(json.dumps(checks,ensure_ascii=False,indent=2)+'\n').encode()
