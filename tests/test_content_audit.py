"""Editorial audit fixtures distinguish body duplication from necessary modules."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('content_auditor',ROOT/'scripts/audit_content.py')
auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
PROSE='Servis öncesinde cihazın tam modelini ve belirtinin hangi kullanım sırasında başladığını kaydedin. Sorunun ilk kez görülmesiyle işlem sonrasında tekrarlaması farklı bilgiler sağlar; kontrol sırasında bu ayrıntıları birlikte değerlendirmek gerekir.'

class ContentAuditTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
    def page(self,name,main):
        (self.root/name).write_text('<html><head><title>'+name+'</title></head><body><header><p>'+PROSE+'</p></header><main>'+main+'</main><footer><p>'+PROSE+'</p></footer></body></html>')
    def test_navigation_footer_tables_and_forms_do_not_create_body_duplicates(self):
        main='<nav><p>'+PROSE+'</p></nav><table><tr><td>'+PROSE+'</td></tr></table><form><p>'+PROSE+'</p></form><p>Bu sayfada kısa ve ayrı bir açıklama var.</p>'
        self.page('a.html',main);self.page('b.html',main)
        report=auditor.audit(self.root)
        self.assertEqual(report['exact_duplicate_groups'],[])
        self.assertTrue(all(p['body_substantive_paragraphs']==0 for p in report['pages']))
    def test_real_body_repeat_and_within_page_repeat_are_reported(self):
        self.page('a.html','<p>'+PROSE+'</p><p>'+PROSE+'</p>');self.page('b.html','<p>'+PROSE+'</p>')
        report=auditor.audit(self.root)
        group=report['exact_duplicate_groups'][0]
        self.assertEqual(group['classification'],'editorial_review');self.assertEqual(len(group['occurrences']),3)
        self.assertTrue(group['cross_page']);self.assertEqual(report['pages'][0]['unique_body_substantive_paragraphs'],0)
    def test_source_and_model_scope_repetition_is_documented_context(self):
        assets=self.root/'assets';assets.mkdir()
        (assets/'verified-faults.json').write_text(json.dumps({'models':[{'path':'/a.html','manual':{'url':'https://manufacturer.invalid/manual.pdf'}},{'path':'/b.html','manual':{'url':'https://manufacturer.invalid/manual.pdf'}}]}))
        for name in ['a.html','b.html']:self.page(name,'<section class="fault-scope"><p>'+PROSE+'</p><a href="https://manufacturer.invalid/manual.pdf">Kaynak</a></section><table><tr><td>E1 ortak belge kaydı</td></tr></table>')
        report=auditor.audit(self.root)
        self.assertEqual(report['summary']['editorial_duplicate_groups'],0)
        self.assertEqual(report['summary']['missing_manual_link_pages'],0)
        self.assertTrue(all(p['kind']=='model_guide' for p in report['pages']))
    def test_entity_swapped_body_is_a_near_repeat_signal(self):
        assets=self.root/'assets';assets.mkdir()
        (assets/'servis-katalog.json').write_text(json.dumps({'districts':[{'name':'Avcılar'},{'name':'Bakırköy'}]}))
        text=('BÖLGE içinde servis kaydı açarken BÖLGE ilçe bilginizi ve BÖLGE mahallenizi ayrı belirtin. BÖLGE adresindeki cihazın modelini BÖLGE randevusundan önce kaydedin. BÖLGE için istenen işlemle BÖLGE konumunu birlikte görüşelim. '+PROSE)
        self.page('a.html','<p>'+text.replace('BÖLGE','Avcılar')+'</p>');self.page('b.html','<p>'+text.replace('BÖLGE','Bakırköy')+'</p>')
        pairs=auditor.audit(self.root)['near_repeat_pairs']
        self.assertEqual(len(pairs),1);self.assertEqual(pairs[0]['entity_masked_5word_jaccard'],1)
    def test_main_faq_mismatch_and_missing_manual_are_reviewable(self):
        assets=self.root/'assets';assets.mkdir();(assets/'verified-faults.json').write_text(json.dumps({'models':[{'path':'/a.html','manual':{'url':'https://manufacturer.invalid/manual.pdf'}}]}))
        self.page('a.html','<h1>Belge rehberi</h1><p>'+PROSE+'</p><script type="application/ld+json">'+json.dumps({'@type':'FAQPage','mainEntity':[{'@type':'Question','name':'Görünmeyen soru','acceptedAnswer':{'@type':'Answer','text':'Görünmeyen cevap'}}]})+'</script>')
        row=auditor.audit(self.root)['pages'][0]
        self.assertEqual(len(row['missing_manual_links']),1);self.assertEqual(len(row['faq_visible_mismatches']),2)
        reasons={v['reason'] for v in auditor.audit(self.root)['strict_violations']}
        self.assertEqual(reasons,{'missing_manual_link','faq_visible_mismatch'})
    def test_strict_flags_a_full_editorial_clone_not_just_a_repeated_paragraph(self):
        self.page('a.html','<p>'+PROSE+'</p>');self.page('b.html','<p>'+PROSE+'</p>')
        self.assertEqual(auditor.audit(self.root)['strict_violations'],[])
        long_body=' '.join([PROSE]*3)
        self.page('a.html','<p>'+long_body+'</p>');self.page('b.html','<p>'+long_body+'</p>')
        reasons={v['reason'] for v in auditor.audit(self.root)['strict_violations']}
        self.assertEqual(reasons,{'exact_editorial_body_clone'})
    def test_directory_teaser_can_quote_an_editorial_summary(self):
        self.page('hizmetler.html','<p>'+PROSE+'</p>');self.page('a.html','<p>'+PROSE+'</p>')
        report=auditor.audit(self.root)
        self.assertEqual(report['summary']['editorial_duplicate_groups'],0)
        self.assertEqual(report['strict_violations'],[])
    def test_strict_cli_fails_integrity_violation_but_report_mode_succeeds(self):
        (self.root/'a.html').write_text('<html><body><h1>MAIN bölümü eksik</h1></body></html>')
        command=[sys.executable,str(ROOT/'scripts/audit_content.py'),str(self.root)]
        report=subprocess.run(command,capture_output=True,text=True,check=False)
        strict=subprocess.run(command+['--strict'],capture_output=True,text=True,check=False)
        self.assertEqual(report.returncode,0);self.assertEqual(strict.returncode,1)
        self.assertEqual(json.loads(strict.stdout)['strict_violations'][0]['reason'],'missing_main')
    def test_empty_directory_cannot_pass_as_an_audited_release(self):
        self.assertEqual(auditor.audit(self.root)['strict_violations'],[{'reason':'no_visitor_pages'}])
    def test_inline_faq_links_do_not_invent_punctuation_mismatches(self):
        question='Hangi bilgiyi paylaşmalıyım?';answer='Cihazın tam modeli, marka/model bilgisi ve E01 ile F.28 kodlarını iletin.'
        schema={'@type':'FAQPage','mainEntity':[{'@type':'Question','name':question,'acceptedAnswer':{'@type':'Answer','text':answer}}]}
        self.page('a.html','<h2>'+question+'</h2><p>Cihazın <a href="/model.html">tam modeli</a>, marka/<a href="/model.html">model</a> bilgisi ve E01 ile F.28 kodlarını iletin.</p><script type="application/ld+json">'+json.dumps(schema)+'</script>')
        self.assertEqual(auditor.audit(self.root)['pages'][0]['faq_visible_mismatches'],[])
        for before,after in [('E01','E1'),('F.28','F28')]:
            self.page('a.html','<h2>'+question+'</h2><p>'+answer.replace(before,after)+'</p><script type="application/ld+json">'+json.dumps(schema)+'</script>')
            self.assertEqual(len(auditor.audit(self.root)['pages'][0]['faq_visible_mismatches']),1)

if __name__=='__main__':unittest.main()
