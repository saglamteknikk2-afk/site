"""A pending business statement must not be advertised as a verified guarantee."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('home_renderer',ROOT/'scripts/render_home.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)

class ServicePromisesTests(unittest.TestCase):
    def item(self,status):
        return {'id':'arrival','status':status,'declared_title':'40 dk varış','title':'Varış planı','detail':'Süreyi görüşün','conditions':'Trafiğe göre değişir.'}
    def test_unconfirmed_statement_is_not_a_public_promise(self):
        cards,notes=renderer.render_assurances({'items':[self.item('pending')]})
        self.assertNotIn('40 dk',cards+notes);self.assertIn('Varış planı',cards)
    def test_confirmed_promise_keeps_visible_conditions(self):
        cards,notes=renderer.render_assurances({'items':[self.item('verified')]})
        self.assertIn('40 dk',cards);self.assertIn('Trafiğe göre değişir.',notes)
    def test_public_copy_is_escaped(self):
        item=self.item('pending');item['title']='<script>bad</script>'
        cards,notes=renderer.render_assurances({'items':[item]})
        self.assertNotIn('<script>',cards+notes)

if __name__=='__main__':unittest.main()
