import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('performance', ROOT/'performance.py')
performance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(performance)


class PerformanceTests(unittest.TestCase):
    def fixture(self):
        return {
            'index.html': (b'<html><head><link rel="stylesheet" href="assets/fonts.css">'
                           b'<script src="assets/environment.js"></script></head><body>'
                           b'<img src="assets/logo.svg" width="38" height="42">'
                           b'<img class="p-hero-photo" src="assets/hero.svg" loading="lazy" fetchpriority="high">'
                           b'<img src="assets/card.svg"><img src="assets/logo.svg" width="38" height="42">'
                           b'</body></html>'),
            'assets/logo.svg': b'<svg width="38" height="42"></svg>',
            'assets/hero.svg': b'<svg viewBox="0 0 1400 933"></svg>',
            'assets/card.svg': b'<svg width="800" height="520"></svg>',
            'assets/environment.js': b'window.ST_PREVIEW=false;',
            'assets/fonts.css': b'@font-face{font-display:swap}',
            'assets/fonts/d8c30647abfe.woff2': b'latin',
            'assets/fonts/94d65887a83f.woff2': b'turkish',
            'unused.css': b'body{color:black}',
            'assets/unused.css': b'body{color:black}',
            'different.css': b'old',
            'assets/different.css': b'new',
        }

    def test_critical_images_not_lazy_and_below_fold_is_lazy(self):
        files=self.fixture(); report=performance.apply_performance(files)
        tags=performance.IMG.findall(files['index.html'].decode())
        self.assertIn('loading="eager"',tags[0]); self.assertIn('fetchpriority="high"',tags[0])
        self.assertIn('loading="eager"',tags[1]); self.assertIn('width="1400"',tags[1])
        self.assertIn('height="933"',tags[1]); self.assertIn('loading="lazy"',tags[2])
        self.assertIn('loading="lazy"',tags[3]); self.assertEqual(report['after']['missing_dimensions'],0)

    def test_exact_two_local_fonts_preload_no_extra_script_deferral(self):
        files=self.fixture();performance.apply_performance(files);source=files['index.html'].decode()
        self.assertEqual(source.count('rel="preload"'),2)
        self.assertIn('<script src="assets/environment.js"></script>',source)
        self.assertNotIn('fonts/22bd9b393960.woff2',source)

    def test_only_unreferenced_byte_identical_duplicates_removed(self):
        files=self.fixture();performance.apply_performance(files)
        self.assertNotIn('unused.css',files); self.assertIn('assets/unused.css',files)
        self.assertIn('different.css',files)
        files=self.fixture();files['page.html']=b'<link href="unused.css" rel="stylesheet">'
        performance.apply_performance(files);self.assertIn('unused.css',files)

    def test_reapplication_does_not_duplicate_preloads_or_change_files(self):
        files=self.fixture();performance.apply_performance(files);once=dict(files)
        report=performance.apply_performance(files)
        self.assertEqual(files,once);self.assertEqual(report['pages_changed'],0)

    def test_dimension_reading_does_not_invent_missing_metadata(self):
        self.assertIsNone(performance._dimensions(b'bad file','photo.webp'))
        self.assertEqual(performance._dimensions(b'<svg viewBox="0 0 800 520"/>','art.svg'),(800,520))

    def test_only_home_data_only_scripts_lazy_loaded_and_consumers_retained(self):
        files=self.fixture()
        sources=['assets/verified-faults.js?v=1','assets/organic-catalog.js?v=2','assets/model-directory.js?v=3']
        chain=''.join('<script src="'+value+'" defer></script>' for value in sources)
        chain+='<script src="assets/fault-lookup.js" defer></script><script src="assets/ai-usta.js" defer></script>'
        files['index.html']=('<html><head>'+chain+'</head><body><section id="aiUstaWizard"></section></body></html>').encode()
        files['brand.html']=files['index.html']
        for value in sources: files[value.split('?')[0]]=b'window.fixture=true;'
        report=performance.apply_performance(files)
        text=files['index.html'].decode()
        self.assertIn('src="assets/diagnostics-loader.js"',text)
        self.assertNotIn('src="assets/verified-faults.js?v=1"',text)
        self.assertIn('src="assets/fault-lookup.js" defer',text)
        self.assertIn('src="assets/ai-usta.js" defer',text)
        self.assertIn('src="assets/verified-faults.js?v=1"',files['brand.html'].decode())
        self.assertEqual(report['diagnostic_data_loading']['bytes_removed_from_initial_script_chain'],60)

    def test_icon_subset_preserves_base_fontface_aliases_and_used_dynamic_literals(self):
        files=self.fixture()
        files['assets/icons.css']=(b'/*! Font license */.fa{font-family:icons}@font-face{font-family:icons;src:url(fonts/x.woff2)}'
                                  b'.fa-phone:before,.fa-phone-alt:before{content:"\\f095"}'
                                  b'.fa-unused:before{content:"\\ffff"}.fa-spin{animation:spin 1s}'
                                  b'@keyframes spin{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}')
        files['assets/consumer.js']=b'const icon="fa-phone";'
        performance.apply_performance(files);css=files['assets/icons.css'].decode()
        self.assertIn('/*! Font license */',css);self.assertIn('@font-face{',css)
        self.assertIn('.fa-phone-alt:before',css);self.assertNotIn('.fa-unused:before',css)
        self.assertIn('@keyframes spin',css);self.assertIn('.fa-spin{',css)

    def test_icon_purge_refuses_unbounded_dynamic_names(self):
        files=self.fixture();original=b'/*license*/.fa-dynamic:before{content:"x"}'
        files['assets/icons.css']=original;files['assets/a.js']=b'const icon="fa-"+userInput;'
        report=performance.apply_performance(files)
        self.assertEqual(files['assets/icons.css'],original)
        self.assertFalse(report['icon_stylesheet']['applied'])


if __name__=='__main__':unittest.main()
