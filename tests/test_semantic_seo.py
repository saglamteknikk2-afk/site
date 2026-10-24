"""Behavior checks for final SEO reconciliation; no network or live account."""
import importlib.util
import json
from pathlib import Path
import re
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('semantic_seo', ROOT / 'scripts/semantic_seo.py')
seo = importlib.util.module_from_spec(spec); spec.loader.exec_module(seo)


def document(heading='Servis rehberi', body='', head='', preview=False):
    mode = ' data-st-mode="preview"' if preview else ''
    guard = '<meta name="robots" content="noindex,nofollow"><script src="assets/preview-guard.js"></script>' if preview else ''
    return ('<!doctype html><html><head><meta charset="UTF-8">' + guard + head + '<title>' + heading + '</title></head><body' + mode + '><main><h1>' + heading + '</h1>' + body + '</main></body></html>').encode()


def rows(data):
    parser = seo.parse(data.decode())
    return [row for doc in parser.schemas for row in seo.graph_rows(doc)]


class SemanticSeoTests(unittest.TestCase):
    def files(self, preview=False):
        return {
            'index.html': document('Sağlam Teknik', preview=preview),
            'kombi-servisi.html': document('Kombi servisi', preview=preview),
            'kucukcekmece-kombi-servisi.html': document('Küçükçekmece kombi servisi', preview=preview),
            'kombi-su-akitiyor.html': document('Kombi su akıtıyor', preview=preview),
            'model-ariza-kodlari.html': document('Model rehberleri', preview=preview),
            '404.html': document('Bulunamadı', head='<meta name="robots" content="noindex">', preview=preview),
            'servis-sec.html': document('Servis seçimi', head='<meta name="robots" content="noindex">', preview=preview),
            'assets/servis-katalog.json': json.dumps({'districts': ['Küçükçekmece', 'Avcılar']}).encode(),
            'assets/brand/logo-ribbon.png': b'fixture logo',
            'assets/owner-admin.html': document('Yönetim'),
            'api.php': b'<?php /* no execution */',
            'ai-koruma.php': b'<?php /* no execution */',
        }

    def test_replaces_conflicting_metadata_and_schemas_with_one_production_graph(self):
        files = self.files()
        legacy = '<link href="https://example.test/old" rel="canonical"><link rel="canonical" href="/duplicate"><meta property="og:url" content="https://old.test/"><meta property="og:image" content="/site/assets/brand/logo-ribbon.png"><script type="application/ld+json">{"@type":"Product","aggregateRating":{"ratingValue":4.8}}</script>'
        files['kombi-servisi.html'] = document('Kombi servisi', head=legacy)
        seo.enhance_files(files)
        text = files['kombi-servisi.html'].decode()
        self.assertEqual(text.count('rel="canonical"'), 1)
        self.assertIn('href="' + seo.ORIGIN + '/kombi-servisi.html"', text)
        self.assertEqual(text.count('property="og:url"'), 1)
        self.assertIn('content="' + seo.ORIGIN + '/assets/brand/logo-ribbon.png"', text)
        self.assertEqual(text.count('application/ld+json'), 1)
        graph = rows(files['kombi-servisi.html'])
        self.assertIn('HVACBusiness', {row['@type'] for row in graph})
        self.assertNotRegex(json.dumps(graph), r'aggregateRating|AggregateRating|MYK|warranty|hasCredential')

    def test_faq_uses_only_real_visible_expandable_questions_and_exact_inline_text(self):
        files = self.files()
        body = '<details><summary>E1 ve <a href="manual.pdf">E01</a> aynı mı?</summary><p>Hayır; <strong>E1</strong>, E01 ve F.28 farklıdır.</p></details><details><summary>Hizmet bölgeleri</summary><p>İlçe menüsü.</p></details><details hidden><summary>Gizli soru?</summary><p>Gizli cevap.</p></details><div aria-hidden="true"><details><summary>Gizli durum?</summary><p>Gizli.</p></details></div><form><details><summary>Form sorusu?</summary><p>Alan.</p></details></form>'
        files['kombi-su-akitiyor.html'] = document(body=body)
        seo.enhance_files(files)
        faq = [row for row in rows(files['kombi-su-akitiyor.html']) if row['@type'] == 'FAQPage']
        self.assertEqual(len(faq), 1)
        self.assertEqual(faq[0]['mainEntity'], [{'@type': 'Question', 'name': 'E1 ve E01 aynı mı?', 'acceptedAnswer': {'@type': 'Answer', 'text': 'Hayır; E1, E01 ve F.28 farklıdır.'}}])
        self.assertNotIn('FAQPage', {row['@type'] for row in rows(files['index.html'])})

    def test_model_article_preserves_visible_codes_and_exact_manufacturer_citation(self):
        files = self.files()
        name = 'ureticimodel-ariza-kodlari.html'
        manual = 'https://manufacturer.example/manual.pdf?rev=1&lang=tr'
        body = '<p>Yalnız belgelenen ürün: E01, E1, F.28 ve F28 birbirinden ayrıdır.</p><a href="https://manufacturer.example/manual.pdf?rev=1&amp;lang=tr">Resmî belge</a>'
        files[name] = document('Tam model kapsamı', body)
        files['assets/verified-faults.json'] = json.dumps({'models': [{'path': '/' + name, 'manual': {'official': True, 'url': manual, 'title': 'Üretici tam model kılavuzu', 'locator': 'Bölüm 8, sayfa 21'}}]}).encode()
        seo.enhance_files(files)
        self.assertIn(body, files[name].decode())
        article = next(row for row in rows(files[name]) if row['@type'] == 'TechArticle')
        self.assertEqual(article['citation'], [{'@type': 'CreativeWork', 'url': manual, 'name': 'Üretici tam model kılavuzu', 'description': 'Bölüm 8, sayfa 21'}])
        self.assertNotIn('Service', {row['@type'] for row in rows(files[name])})

    def test_visible_local_heading_faq_is_captured_once_without_changing_code_distinctions(self):
        files = self.files()
        pair = '<h3>E1, E01 ve F.28 aynı mı?</h3><p><strong>E1</strong>, E01 ve F.28 ayrı gösterimlerdir; F28 yazımını kendiliğinden eşitlemeyin.</p>'
        body = '<section id="yerel-sorular"><h2>Yerel sorular</h2><div class="local-faq-item">' + pair + '</div><div class="local-faq-item" hidden><h3>Gizli soru?</h3><p>Gizli cevap.</p></div></section><details><summary>E1, E01 ve F.28 aynı mı?</summary><p><strong>E1</strong>, E01 ve F.28 ayrı gösterimlerdir; F28 yazımını kendiliğinden eşitlemeyin.</p></details><div class="local-faq-item"><h3>Bölüm dışı menü?</h3><p>Menü metni.</p></div>'
        files['kucukcekmece-kombi-servisi.html'] = document('Yerel rehber', body)
        seo.enhance_files(files)
        self.assertIn(body, files['kucukcekmece-kombi-servisi.html'].decode())
        faq = next(row for row in rows(files['kucukcekmece-kombi-servisi.html']) if row['@type'] == 'FAQPage')
        self.assertEqual(len(faq['mainEntity']), 1)
        self.assertEqual(faq['mainEntity'][0]['name'], 'E1, E01 ve F.28 aynı mı?')
        self.assertEqual(faq['mainEntity'][0]['acceptedAnswer']['text'], 'E1, E01 ve F.28 ayrı gösterimlerdir; F28 yazımını kendiliğinden eşitlemeyin.')

    def test_business_logo_prefers_existing_lossless_webp_with_png_fallback(self):
        files = self.files(); seo.enhance_files(files)
        business = next(row for row in rows(files['index.html']) if row['@type'] == 'HVACBusiness')
        self.assertEqual(business['logo'], seo.ORIGIN + '/assets/brand/logo-ribbon.png')
        files['assets/brand/logo-ribbon.webp'] = b'lossless logo fixture'; seo.enhance_files(files)
        business = next(row for row in rows(files['index.html']) if row['@type'] == 'HVACBusiness')
        self.assertEqual(business['logo'], seo.ORIGIN + '/assets/brand/logo-ribbon.webp')

    def test_service_scope_and_technical_page_type_are_distinct(self):
        files = self.files(); seo.enhance_files(files)
        district = next(row for row in rows(files['kucukcekmece-kombi-servisi.html']) if row['@type'] == 'Service')
        self.assertEqual(district['areaServed']['name'], 'Küçükçekmece, İstanbul')
        technical = {row['@type'] for row in rows(files['kombi-su-akitiyor.html'])}
        self.assertIn('TechArticle', technical); self.assertNotIn('Service', technical)
        self.assertNotIn('TechArticle', {row['@type'] for row in rows(files['model-ariza-kodlari.html'])})
        self.assertTrue(all(any(row['@type'] == 'BreadcrumbList' for row in rows(data)) for name, data in files.items() if seo.visitor(name)))

    def test_sitemap_contains_only_actual_indexable_visitor_canonicals_once(self):
        files = self.files()
        files['google123.html'] = b'google-site-verification: actual-token'
        files['private-note.html'] = document('Geçici', head='<meta name="robots" content="noindex">')
        stats = seo.enhance_files(files)
        tree = ET.fromstring(files['sitemap.xml'])
        actual = [node.text for node in tree.findall('{*}url/{*}loc')]
        expected = {seo.ORIGIN + '/', seo.ORIGIN + '/kombi-servisi.html', seo.ORIGIN + '/kucukcekmece-kombi-servisi.html', seo.ORIGIN + '/kombi-su-akitiyor.html', seo.ORIGIN + '/model-ariza-kodlari.html'}
        self.assertEqual(set(actual), expected); self.assertEqual(len(actual), len(expected))
        self.assertEqual(stats['sitemap_urls'], len(expected))
        self.assertNotIn(b'lastmod', files['sitemap.xml'])
        self.assertEqual(files['google123.html'], b'google-site-verification: actual-token')

    def test_admin_noindex_and_production_api_disallows_do_not_deny_public_pages(self):
        files = self.files(); files['worker.php'] = b'<?php'; seo.enhance_files(files)
        robots = files['robots.txt'].decode()
        for path in ['/api.php', '/ai-koruma.php', '/worker.php', '/assets/owner-admin.html', '/owner-admin.html']:
            self.assertIn('Disallow: ' + path + '\n', robots)
        self.assertIn('Allow: /\n', robots)
        self.assertNotRegex(robots, r'Disallow: /\s*\n')
        self.assertIn(b'content="noindex,nofollow"', files['assets/owner-admin.html'])
        self.assertNotIn('owner-admin', files['sitemap.xml'].decode())

    def test_preview_keeps_first_guard_noindex_and_production_metadata_without_sitemap(self):
        files = self.files(preview=True); files['sitemap.xml'] = b'old sitemap'
        stats = seo.enhance_files(files)
        self.assertEqual(stats['mode'], 'preview'); self.assertNotIn('sitemap.xml', files)
        self.assertEqual(files['robots.txt'], b'User-agent: *\nAllow: /\n')
        for name, data in files.items():
            if not seo.visitor(name): continue
            text = data.decode(); self.assertIn('noindex', text)
            self.assertIn('href="' + seo.page_url(name) + '"', text)
            scripts = re.findall(r'<script\b[^>]*>', text)
            self.assertIn('preview-guard.js', scripts[0])

    def test_llms_lists_only_real_model_urls_and_available_district_routes(self):
        files = self.files()
        files['baymak-kombi-servisi.html'] = document('Baymak kombi servisi')
        name = 'gercek-model-ariza-kodlari.html'; files[name] = document('Gerçek model')
        files['assets/verified-faults.json'] = json.dumps({'models': [{'path': '/' + name}, {'path': '/olmayan-model.html'}]}).encode()
        seo.enhance_files(files); llms = files['llms.txt'].decode()
        self.assertIn('0534 622 55 15', llms); self.assertIn('Küçükçekmece', llms); self.assertIn('Avcılar', llms)
        self.assertIn(seo.ORIGIN + '/' + name, llms); self.assertNotIn('olmayan-model', llms)
        self.assertIn(seo.ORIGIN + '/baymak-kombi-servisi.html', llms)
        self.assertNotIn('/avcilar-kombi-servisi.html', llms)
        self.assertNotIn('owner-admin', llms); self.assertNotIn('404.html', llms)

    def test_llms_distinguishes_supplied_business_declarations_from_external_verification(self):
        files = self.files()
        files['isletme-bilgileri.json'] = json.dumps({'business_claims': {'qualification': {'status': 'business-declared', 'credential_number': 'YB0200/11UY0032-4/02/502'}, 'warranty': {'status': 'business-declared', 'duration': '1 yıl', 'scope': 'Servis fişinde belirtilen takılan parça ve uygulanan işçilik'}}}).encode()
        seo.enhance_files(files); llms = files['llms.txt'].decode()
        self.assertIn('İşletme sahibinin beyanına göre MYK belge numarası: YB0200/11UY0032-4/02/502', llms)
        self.assertIn('bağımsız doğrulanmış değildir', llms)
        self.assertIn('1 yıl parça ve işçilik', llms)
        self.assertIn('Servis fişinde belirtilen takılan parça ve uygulanan işçilik', llms)
        self.assertNotIn('MYK belge numarası', json.dumps(rows(files['index.html'])))

    def test_idempotent_and_preserves_unrelated_code_bytes(self):
        files = self.files(); files['assets/app.js'] = b'const code="E01";'
        first = seo.enhance_files(files); snapshot = dict(files)
        self.assertEqual(seo.enhance_files(files), first)
        self.assertEqual(files, snapshot)
        self.assertEqual(files['assets/app.js'], b'const code="E01";')


if __name__ == '__main__': unittest.main()
