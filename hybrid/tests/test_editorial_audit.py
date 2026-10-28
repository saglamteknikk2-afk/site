import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from editorial_audit import audit_pages,verify_rendered

SOURCE={'districts':[], 'localities':[{'name':'Birinci Yer','slug':'birinci-yer'}, {'name':'İkinci Yer','slug':'ikinci-yer'}]}

def page(place,slug,seed):
    # Deliberately disjoint paragraphs make a clear negative control.
    pieces=[]
    for i in range(3):
        pieces.append({'id':'s'+str(i), 'heading':seed+' '+str(i)+' kontrol açıklaması',
                       'paragraphs':[' '.join(seed+str(i)+'kelime'+str(j) for j in range(65))],
                       'links':[{'path':'kombi-servisi.html','label':'Servis'}]})
    return {'route':slug+'-servisi.html','headline':place+' talebi', 'focus':seed,
            'lead':' '.join(seed+'giris'+str(j) for j in range(30)), 'sections':pieces,
            'faqs':[{'question':seed+' birinci soru açıklaması nedir?', 'answer':' '.join(seed+'yanit'+str(j) for j in range(30))},
                    {'question':seed+' ikinci kontrol ne zaman yapılır?', 'answer':' '.join(seed+'diger'+str(j) for j in range(30))}],
            'neighborhood_intro':seed+' adres bilgisi', 'cta':{'text':seed+' iletişim'}}

def fixture():return [page('Birinci Yer','birinci-yer','alfa'),page('İkinci Yer','ikinci-yer','beta')]

class EditorialAuditTests(unittest.TestCase):
    def test_distinct_authored_bodies_pass(self):
        result=audit_pages(fixture(),SOURCE,{'kombi-servisi.html':b''})
        self.assertEqual(result['status'],'passed');self.assertEqual(result['expected_pages'],2)
    def test_entity_name_swap_is_detected(self):
        rows=fixture();rows[0]['sections'][0]['paragraphs']=['Birinci Yer adresinde '+ ' '.join('ortakmetin'+str(j) for j in range(50))]
        rows[1]['sections'][0]['paragraphs']=[rows[0]['sections'][0]['paragraphs'][0].replace('Birinci Yer','İkinci Yer')]
        result=audit_pages(rows,SOURCE,{'kombi-servisi.html':b''},strict=False)
        self.assertIn('repeated_editorial_paragraph_after_location_mask',{e['kind'] for e in result['errors']})
    def test_missing_route_and_bad_link_fail(self):
        rows=fixture()[:1];rows[0]['sections'][0]['links'][0]['path']='missing.html'
        result=audit_pages(rows,SOURCE,{'kombi-servisi.html':b''},strict=False)
        kinds={e['kind'] for e in result['errors']}
        self.assertIn('missing_editorial_routes',kinds);self.assertIn('missing_editorial_link',kinds)
    def test_near_copy_with_added_words_is_detected(self):
        rows=fixture();common=' '.join('denetim'+str(i) for i in range(60))
        rows[0]['sections'][0]['paragraphs']=[common+' ilk son sözcük']
        rows[1]['sections'][0]['paragraphs']=[common+' farklı eklenen sözcük']
        result=audit_pages(rows,SOURCE,{'kombi-servisi.html':b''},strict=False)
        self.assertTrue(any(e['kind']=='near_duplicate_editorial_paragraph' for e in result['errors']))
    def test_short_shared_safety_fact_is_not_a_copy_failure(self):
        rows=fixture()
        for row in rows:row['sections'][0]['bullets']=['Gaz kokusunda güvenli alana geçip 187’yi arayın.']
        result=audit_pages(rows,SOURCE,{'kombi-servisi.html':b''})
        self.assertEqual(result['status'],'passed')
    def test_strict_mode_rejects_duplicate_body(self):
        rows=fixture();rows[1]['sections'][0]['paragraphs']=copy.deepcopy(rows[0]['sections'][0]['paragraphs'])
        with self.assertRaises(ValueError):audit_pages(rows,SOURCE,{'kombi-servisi.html':b''})
    def test_reused_substantive_question_is_detected(self):
        rows=fixture()
        for row in rows:row['faqs'][0]['question']='Cihaz için hangi bilgileri önceden hazırlamam gerekir?'
        report=audit_pages(rows,SOURCE,{'kombi-servisi.html':b''},strict=False)
        self.assertTrue(any(e['kind']=='repeated_substantive_heading_after_location_mask' for e in report['errors']))
    def test_refusal_of_diagnosis_is_not_a_promise_but_positive_claim_is_flagged(self):
        rows=fixture();rows[0]['sections'][0]['paragraphs'].append('Görüşmede kesin teşhis konulamaz.')
        report=audit_pages(rows,SOURCE,{'kombi-servisi.html':b''})
        self.assertEqual(report['warnings'],[])
        self.assertEqual(len(report['explicit_claim_disclaimers']),1)
        rows[0]['sections'][0]['paragraphs'].append('Bu işlem için kesin çözüm sözü veriyoruz.')
        report=audit_pages(rows,SOURCE,{'kombi-servisi.html':b''})
        self.assertTrue(any(w['kind']=='unsubstantiated_promise' for w in report['warnings']))
    def test_missing_visible_body_and_retained_old_template_are_detected(self):
        row=fixture()[0]
        body='<section data-editorial-route="'+row['route']+'"><article class="editorial-body">'
        for section in row['sections']:
            body+='<h2>'+section['heading']+'</h2>'
            body+=''.join('<p>'+p+'</p>' for p in section['paragraphs'])
        for faq in row['faqs']:body+='<details><summary>'+faq['question']+'</summary><p>'+faq['answer']+'</p></details>'
        body+='</article></section>'
        report=verify_rendered([row],{row['route']:body.encode()})
        self.assertEqual(report['errors'],[])
        bad=body.replace(row['sections'][0]['paragraphs'][0],'hidden replacement')+'<div class="at-summary">Old copied body</div>'
        report=verify_rendered([row],{row['route']:bad.encode()})
        kinds={e['kind'] for e in report['errors']}
        self.assertIn('authored_paragraph_not_rendered',kinds)
        self.assertIn('old_recycled_region_block_retained',kinds)

if __name__=='__main__':unittest.main()
