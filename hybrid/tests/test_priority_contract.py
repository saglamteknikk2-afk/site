"""Fee/consent boundaries for the actual packaged priority PHP, no providers."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'hybrid'))
from source import load_source

PHP=r'''<?php
require $argv[1];
$secret=str_repeat('isolated-qa-only-',4);$session='isolated-session';
$time=static fn($clock)=>(new DateTimeImmutable('2026-10-29 '.$clock,new DateTimeZone('Europe/Istanbul')))->getTimestamp();
$input=['name'=>'Test Müşteri','phone'=>'5555555555','district'=>'Esenler','device'=>'Kombi','issue'=>'Kombi sıcak su vermiyor. | Mahalle: Tuna','service_level'=>'priority'];
$fees=[];foreach(['00:00:00','07:59:59','08:00:00','20:59:59','21:00:00','23:59:59'] as $t)$fees[$t]=st_priority_quote($input,$session,$secret,$time($t))['fee_try'];
$q=st_priority_quote($input,$session,$secret,$time('12:00:00'));
$accepted=$input+['priority_quote'=>$q['priority_quote'],'priority_accepted'=>true,'priority_terms_version'=>$q['terms_version']];
$cases=[];$attempt=static function($value,$at)use(&$cases,$session,$secret){try{$a=st_priority_accept($value,$session,$secret,$at);return ['accepted'=>true,'fee'=>$a['fee_try']];}catch(STPriorityException $e){return ['accepted'=>false,'reason'=>$e->reason()];}};
$cases['valid']=$attempt($accepted,$time('12:00:01'));
$changed=$accepted;$changed['issue']='Kombi sıcak su vermiyor. | Mahalle: Birlik';$cases['changed_neighborhood']=$attempt($changed,$time('12:00:01'));
$changed=$accepted;$changed['priority_accepted']=false;$cases['unchecked']=$attempt($changed,$time('12:00:01'));
$changed=$accepted;$changed['priority_fee_try']=1;$cases['forged_amount']=$attempt($changed,$time('12:00:01'));
$cases['expired']=$attempt($accepted,$time('12:10:00'));
$changed=$accepted;$changed['location']=['consent'=>true,'latitude'=>41.04,'longitude'=>28.87];$cases['async_location']=$attempt($changed,$time('12:00:01'));
$boundary=st_priority_quote($input,$session,$secret,$time('20:59:55'));
$cases['tariff_boundary']=$attempt($input+['priority_quote'=>$boundary['priority_quote'],'priority_accepted'=>true,'priority_terms_version'=>$boundary['terms_version']],$time('21:00:00'));
echo json_encode(['fees'=>$fees,'cases'=>$cases,'provider_requests'=>0],JSON_UNESCAPED_UNICODE);
'''


class PriorityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        files,_=load_source(ROOT)
        current=ROOT/'hybrid/runtime/priority-service.php'
        source=current.read_bytes() if current.exists() else files['priority-service.php']
        php=shutil.which('php')
        if not php and Path('/workspace/work/qa/php82-cli').exists():php='/workspace/work/qa/php82-cli'
        if not php:raise unittest.SkipTest('PHP CLI required for signed fee contract')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'priority.php').write_bytes(source);(root/'test.php').write_text(PHP)
            result=subprocess.run([php,str(root/'test.php'),str(root/'priority.php')],capture_output=True,text=True,check=True)
            cls.result=json.loads(result.stdout)

    def test_istanbul_day_and_night_boundaries(self):
        self.assertEqual(self.result['fees'],{'00:00:00':4000,'07:59:59':4000,'08:00:00':2500,'20:59:59':2500,'21:00:00':4000,'23:59:59':4000})

    def test_neighborhood_context_is_bound_to_final_acceptance(self):
        self.assertEqual(self.result['cases']['valid'],{'accepted':True,'fee':2500})
        self.assertEqual(self.result['cases']['changed_neighborhood']['reason'],'contact_changed')

    def test_consent_amount_expiry_and_tariff_checks_remain_enforced(self):
        cases=self.result['cases']
        for name,reason in [('unchecked','consent_required'),('forged_amount','invalid_fee'),('expired','quote_expired'),('tariff_boundary','quote_expired')]:
            self.assertEqual(cases[name],{'accepted':False,'reason':reason})

    def test_async_location_does_not_change_the_reviewed_contact_fee(self):
        self.assertEqual(self.result['cases']['async_location'],{'accepted':True,'fee':2500})
        self.assertEqual(self.result['provider_requests'],0)


if __name__=='__main__':unittest.main()
