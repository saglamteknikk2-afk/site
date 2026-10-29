"""Exercise private-view refresh lifecycle and keep the script extraction bounded."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from interface_repairs import apply_interface_repairs
from source import load_source

HARNESS=r'''
const vm=require('node:vm'),fs=require('node:fs');
const elements=new Map(),timers=new Map(),events={},windowEvents={};let seq=0,calls=[],requests=[];
class Element{
 constructor(){this.children=[];this.textContent='';this.href='';this.attrs={};this.classes=new Set();this.classList={add:x=>this.classes.add(x),remove:x=>this.classes.delete(x),toggle:(x,v)=>v?this.classes.add(x):this.classes.delete(x)};}
 append(...nodes){this.children.push(...nodes)}replaceChildren(...nodes){this.children=nodes}removeAttribute(name){delete this.attrs[name];if(name==='href')this.href='';}
}
const el=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id)};
const document={hidden:false,getElementById:el,createElement:()=>new Element(),addEventListener:(event,fn)=>events[event]=fn};
const ctx={URL,URLSearchParams,Date,AbortController,location:{search:process.argv[2]||'?kod='+('a'.repeat(32))},document,
 window:{addEventListener:(event,fn)=>windowEvents[event]=fn},setTimeout:(fn,ms)=>{const id=++seq;timers.set(id,{fn,ms});return id},clearTimeout:id=>timers.delete(id),
 fetch:(url,options)=>{calls.push({url,cache:options.cache,credentials:options.credentials,referrerPolicy:options.referrerPolicy});return new Promise((resolve,reject)=>{const row={resolve,reject,options};requests.push(row);options.signal.addEventListener('abort',()=>reject(new Error('AbortError')));});}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),ctx);
const flush=async()=>{for(let i=0;i<8;i++)await Promise.resolve()};
const result={ok:true,service_level:'standard',status_label:'Talep alındı',record_ref:'1234abcd',eta_minutes:null,telegram_url:'https://t.me/SaglamTeknikBot?start=test',updates:[]};
const respond=async(index,patch={})=>{requests[index].resolve({ok:true,json:async()=>({...result,...patch})});await flush()};
const next=async(ms)=>{const entry=[...timers].find(([id,row])=>row.ms===ms);if(!entry)throw Error('Missing scheduled interval '+ms);timers.delete(entry[0]);entry[1].fn();await flush()};
(async()=>{
 if(!requests.length){process.stdout.write(JSON.stringify({calls:calls.length,timers:timers.size,error:el('load').textContent}));return;}
 await respond(0);const afterFirst={calls:calls.length,poll:[...timers.values()].map(v=>v.ms),status:el('status').textContent};
 await next(3000);events.visibilitychange();await flush();const overlapping=calls.length;
 await respond(1,{status_label:'Yoldayım',eta_minutes:20,updates:[{created:1,body:'20 dakika içinde gelmeyi planlıyorum.'}]});
 const afterUpdate={status:el('status').textContent,eta:el('eta').textContent,message:el('history').children[0]?.children[1]?.textContent,live:el('liveStatus').textContent};
 document.hidden=true;events.visibilitychange();await flush();const hiddenTimers=timers.size;
 document.hidden=false;events.visibilitychange();await flush();const resumed=calls.length;
 document.hidden=true;events.visibilitychange();await flush();const aborted=requests[2].options.signal.aborted;
 document.hidden=false;events.visibilitychange();await flush();await respond(3,{status_label:'Mesajınız var',telegram_url:'javascript:alert(1)',updates:[{created:2,body:'<img src=x onerror=alert(1)>'}]});
 const plainText=el('history').children[0]?.children[1]?.textContent;
 const unsafeTelegramHidden=el('bot').classes.has('hidden')&&!el('bot').href;
 windowEvents.pagehide();await flush();const stopped=timers.size;
 process.stdout.write(JSON.stringify({afterFirst,overlapping,afterUpdate,hiddenTimers,resumed,aborted,plainText,unsafeTelegramHidden,stopped,calls}));
})().catch(e=>{console.error(e);process.exit(1)});
'''


class InterfaceRepairsTests(unittest.TestCase):
    def run_tracking(self,query=None):
        path=ROOT/'runtime/assets/customer-tracking.js'
        args=['node','-e',HARNESS,str(path)]
        if query is not None:args.append(query)
        return json.loads(subprocess.check_output(args,text=True))

    def test_three_second_partial_refresh_preserves_messages_and_has_no_overlapping_fetch(self):
        result=self.run_tracking()
        self.assertEqual(result['afterFirst']['poll'],[3000])
        self.assertEqual(result['overlapping'],2)
        self.assertEqual(result['afterUpdate']['status'],'Yoldayım')
        self.assertIn('20 dakika',result['afterUpdate']['eta'])
        self.assertIn('20 dakika',result['afterUpdate']['message'])
        self.assertIn('3 saniyede',result['afterUpdate']['live'])
        self.assertNotIn('reload', (ROOT/'runtime/assets/customer-tracking.js').read_text().replace('never reload','never refresh'))
        for call in result['calls']:
            self.assertEqual(call['cache'],'no-store')
            self.assertEqual(call['credentials'],'omit')
            self.assertEqual(call['referrerPolicy'],'no-referrer')

    def test_hidden_and_bfcache_lifecycle_and_untrusted_text(self):
        result=self.run_tracking()
        self.assertEqual(result['hiddenTimers'],0)
        self.assertEqual(result['resumed'],3)
        self.assertTrue(result['aborted'])
        self.assertEqual(result['plainText'],'<img src=x onerror=alert(1)>')
        self.assertTrue(result['unsafeTelegramHidden'])
        self.assertEqual(result['stopped'],0)

    def test_invalid_tracking_token_does_not_poll(self):
        result=self.run_tracking('?kod=not-a-token')
        self.assertEqual(result['calls'],0)
        self.assertEqual(result['timers'],0)
        self.assertIn('geçersiz',result['error'])

    def test_build_replaces_only_the_private_tracking_script_and_is_idempotent(self):
        source,_=load_source(ROOT.parent)
        files={name:data for name,data in source.items() if name in {'servis-takip.html','index.html'}}
        stats=apply_interface_repairs(files)
        self.assertEqual(stats['tracking_poll_ms'],3000)
        self.assertIn(b'assets/customer-tracking.js',files['servis-takip.html'])
        self.assertNotIn(b'15000',files['servis-takip.html'])
        self.assertIn(b'name="referrer" content="no-referrer"',files['servis-takip.html'])
        self.assertIn(b'name="robots" content="noindex,nofollow"',files['servis-takip.html'])
        before=dict(files);apply_interface_repairs(files);self.assertEqual(files,before)


if __name__=='__main__':unittest.main()
