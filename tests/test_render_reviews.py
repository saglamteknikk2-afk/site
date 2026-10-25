"""Static review ordering preserves persistent deletion identities."""
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('home_renderer',Path(__file__).resolve().parents[1]/'scripts/render_home.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
class ReviewRenderTests(unittest.TestCase):
    def test_newest_source_date_first_without_reindexing(self):
        result=renderer.render_reviews([{'author':'Old','date':'22 Haz 2016'},{'author':'New','date':'07 Nis 2026'}])
        self.assertLess(result.index('existing-1'),result.index('existing-0'))
        self.assertEqual(result.count('Müşteri yorumu'),2)
    def test_timestamp_and_invalid_dates_are_safe(self):
        self.assertGreater(renderer.review_time({'created':1700000000}),renderer.review_time({'date':'not a date'}))
        self.assertEqual(renderer.review_time({'date':'31 Şub 2026'}),0)
        result=renderer.render_reviews([{'author':'<script>','comment':'<img onerror=1>','date':'07 Nis 2026'}])
        self.assertNotIn('<script>',result)
        self.assertIn('&lt;img onerror=1&gt;',result)
    def test_numeric_turkish_dates_sort_with_iso_and_timestamps(self):
        self.assertEqual(renderer.review_time({'date':'25.10.2026'}),renderer.review_time({'date':'25 Eki 2026'}))
        self.assertEqual(renderer.review_time({'date':'25/10/2026'}),renderer.review_time({'date':'2026-10-25'}))
        self.assertEqual(renderer.review_time({'date':'31.02.2026'}),0)
        result=renderer.render_reviews([{'author':'Old','date':'24.10.2026'},{'author':'New','date':'25 Eki 2026'},{'author':'Invalid','date':'31.02.2026'}])
        self.assertLess(result.index('existing-1'),result.index('existing-0'))
        self.assertLess(result.index('existing-0'),result.index('existing-2'))
    def test_millisecond_timestamps_do_not_appear_in_the_future(self):
        self.assertEqual(renderer.review_time({'created':1792929600000}),renderer.review_time({'created':1792929600}))
        self.assertEqual(renderer.review_time({'created':True}),0)
