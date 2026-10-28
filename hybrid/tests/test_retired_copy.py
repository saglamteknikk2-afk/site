import importlib.util
from pathlib import Path
import unittest

PATH=Path(__file__).resolve().parents[1]/'retired_copy.py'
spec=importlib.util.spec_from_file_location('retired_copy',PATH)
copy=importlib.util.module_from_spec(spec);spec.loader.exec_module(copy)

class RetiredCopyTests(unittest.TestCase):
    def test_backwards_compatible_review_value_and_history(self):
        review='<article class="review"><p>Geçen yıl klima montajı yapıldı; son bakımda memnun kaldım.</p></article>'
        files={'index.html':('<p>Soğutma, ısıtma, bakım ve montaj ihtiyaçları. İç ve dış ünite belirtilerinden doğru yerden başlayın.</p>'
                            '<option value="Klima Bakımı / Montajı">Klima bakımı / montajı</option>'+review).encode()}
        copy.correct_retired_copy(files);text=files['index.html'].decode()
        self.assertIn('value="Klima Bakımı / Montajı">Klima bakımı / onarımı',text)
        self.assertIn(review,text)
        self.assertNotIn('bakım ve montaj ihtiyaçları',text)

    def test_technical_table_and_manual_title_are_unchanged(self):
        table='<table><tr><td>Baymak Elegant Air Montaj ve Kullanma Kılavuzu</td><td>E1: üretici tanımı</td></tr></table>'
        history='<p>Son montaj/bakım tarihini de paylaşın. Elektrikli bölümlere su ulaşıyorsa kullanımı sürdürmeyin.</p>'
        offer='<p>Kombi tamiri veya bakımı; klima bakım, onarım, montaj ve yer değişimi için bulunduğunuz bölgeyi ve cihazınızın markasını birlikte belirtin.</p>'
        files={'servis-sec.html':(table+history+offer).encode()}
        copy.correct_retired_copy(files);text=files['servis-sec.html'].decode()
        self.assertIn(table,text);self.assertIn(history,text)
        self.assertIn('klima bakım ve onarımı için',text)
        snapshot=dict(files);copy.correct_retired_copy(files);self.assertEqual(snapshot,files)

if __name__=='__main__':unittest.main()
