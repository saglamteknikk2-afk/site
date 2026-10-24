/* Real DOM, intercepted local fixture requests only: no provider/account traffic. */
'use strict';
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path'), assert = require('assert/strict');
(async () => {
  const root = path.join(__dirname, '..');
  const environment = fs.readFileSync(path.join(root, 'overrides/assets/environment.js'), 'utf8');
  const site = fs.readFileSync(path.join(root, 'overrides/assets/site.js'), 'utf8');
  const executablePath = process.env.CHROMIUM_BIN || (fs.existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined);
  const browser = await chromium.launch({headless: true, executablePath, args: ['--no-sandbox']});
  let checks = 0; const reports = [];
  const equal = (actual, expected, message) => { checks++; assert.deepEqual(actual, expected, message); };
  try {
    async function scenario(url, mode = 'production', mount = '/') {
      const page = await browser.newPage();
      const requests = [], errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('**/*', async route => {
        const request = route.request(), target = new URL(request.url());
        if (target.href === url) return route.fulfill({contentType: 'text/html', body: `<!doctype html><html data-st-mode="${mode}"><head><meta charset="utf-8"><script>sessionStorage.setItem('st_visit_try','1')</script><script src="${mount}assets/environment.js"></script></head><body data-st-mode="${mode}"><div id="st-preview-banner">TEST ÖN İZLEMESİ</div><form id="send"><div class="st-honey"><label>Web sitesi<input name="website" value=""></label></div><button>Gönder</button></form><form id="local" data-preview-local="true" onsubmit="event.preventDefault();window.localSearchFired=true"><button>Ara</button></form><script src="${mount}assets/site.js"></script></body></html>`});
        if (target.pathname === mount + 'assets/environment.js') return route.fulfill({contentType: 'text/javascript', body: environment});
        if (target.pathname === mount + 'assets/site.js') return route.fulfill({contentType: 'text/javascript', body: site});
        requests.push({path: target.pathname, method: request.method(), action: target.searchParams.get('action')});
        if (target.pathname === mount + 'api.php') return route.fulfill({contentType: 'application/json', body: JSON.stringify(target.searchParams.get('action') === 'bootstrap' ? {ok: true, csrf: '1234567890.' + 'a'.repeat(64)} : {ok: true})});
        if (target.pathname === mount + 'data.json') return route.fulfill({contentType: 'application/json', body: '{"local":true}'});
        return route.abort();
      });
      await page.goto(url);
      await page.waitForFunction(() => typeof stSiteURL === 'function');
      equal(await page.locator('.st-honey').isHidden(), true, 'Honeypot remains outside visible layout');
      equal(await page.locator('input[name="website"]').getAttribute('tabindex'), '-1', 'Honeypot cannot receive tab focus');
      equal(await page.locator('.st-honey').getAttribute('aria-hidden'), 'true', 'Honeypot excluded from accessibility tree');
      await page.evaluate(() => { const wrap = document.createElement('label'); wrap.innerHTML = 'Web sitesi<input id="yorumWebsite">'; document.body.append(wrap); });
      await page.waitForFunction(() => document.getElementById('yorumWebsite').tabIndex === -1);
      equal(await page.locator('#yorumWebsite').isHidden(), true, 'Dynamically inserted honeypot is hidden');
      return {page, requests, errors};
    }
    for (const [url, mode, mount] of [
      ['https://saglamteknikk2-afk.github.io/site/', 'production', '/site/'],
      ['https://saglamkombiklima.com.tr/', 'preview', '/'],
    ]) {
      const fixture = await scenario(url, mode, mount), {page, requests, errors} = fixture;
      equal(await page.evaluate(() => STEnvironment.preview), true, 'Host or artifact flag enforces preview');
      equal(await page.locator('meta[name="robots"]').getAttribute('content'), 'noindex, nofollow', 'Preview is explicitly noindex/nofollow');
      equal(await page.evaluate(async () => { try { await stApi('ticket', {name: 'Fixture'}); return false; } catch (e) { return e.code === 'PREVIEW_DISABLED'; } }), true, 'API wrapper cannot send');
      equal(await page.evaluate(async () => { try { await fetch(STEnvironment.href('api.php?action=bootstrap')); return false; } catch (e) { return e.code === 'PREVIEW_DISABLED'; } }), true, 'Direct PHP fetch cannot bypass wrapper');
      equal(await page.evaluate(async () => { try { await fetch(STEnvironment.href('data.json'), {method: 'POST', body: 'fixture'}); return false; } catch (e) { return e.code === 'PREVIEW_DISABLED'; } }), true, 'POST blocked even to non-PHP endpoint');
      equal(await page.evaluate(async () => fetch(STEnvironment.href('data.json')).then(r => r.json())), {local: true}, 'Read-only local datasets remain usable');
      equal(await page.evaluate(() => { try { const request = new XMLHttpRequest(); request.open('POST', STEnvironment.href('api.php')); request.send('fixture'); return false; } catch (error) { return error.message.includes('kaydedilmedi'); } }), true, 'XHR cannot bypass host preview protection');
      equal(await page.evaluate(() => navigator.sendBeacon(STEnvironment.href('api.php'), 'fixture')), false, 'Beacon delivery is blocked');
      equal(await page.evaluate(() => { try { new WebSocket('wss://fixture.invalid'); return false; } catch (error) { return error.message.includes('kaydedilmedi'); } }), true, 'WebSocket delivery is blocked');
      equal(await page.evaluate(() => { try { new EventSource(STEnvironment.href('api.php')); return false; } catch (error) { return error.message.includes('kaydedilmedi'); } }), true, 'EventSource delivery is blocked');
      equal(await page.evaluate(() => new Promise(resolve => navigator.geolocation.getCurrentPosition(() => resolve(false), error => resolve(error.code === 1)))), true, 'Preview never asks for a real location');
      await page.locator('#send button').click();
      equal(await page.locator('[data-preview-status]').count(), 1, 'Submit shows truthful simulation state');
      await page.evaluate(() => document.getElementById('send').submit());
      equal(await page.locator('[data-preview-status]').count(), 1, 'Native submit also blocked');
      await page.locator('#local button').click();
      equal(await page.evaluate(() => window.localSearchFired), true, 'Local search forms remain functional');
      await page.evaluate(() => {
        window.localSearchFired = false;
        const button = document.querySelector('#local button');
        button.setAttribute('formmethod', 'POST'); button.setAttribute('formaction', STEnvironment.href('api.php'));
      });
      await page.locator('#local button').click();
      equal(await page.evaluate(() => window.localSearchFired), false, 'A submitter override cannot turn local search into a live POST');
      equal(requests.filter(r => r.path.endsWith('.php') || r.method !== 'GET').length, 0, 'No real API/write request escapes preview');
      equal(errors, [], 'No JavaScript errors');
      reports.push({url, mode, preview: true, requests}); await page.close();
    }
    for (const [url, mount] of [
      ['https://saglamkombiklima.com.tr/', '/'],
      ['https://www.saglamkombiklima.com.tr/assets/owner-admin.html', '/'],
      ['https://saglamkombiklima.com.tr/qa-preview/index.html', '/qa-preview/'],
    ]) {
      const {page, requests, errors} = await scenario(url, 'production', mount);
      equal(await page.evaluate(() => STEnvironment.officialProduction), true, 'Exact production hostname recognized');
      equal(await page.locator('#st-preview-banner').isHidden(), true, 'Production preview banner hidden');
      equal(await page.evaluate(() => stSiteURL('api.php')), new URL(mount + 'api.php', url).href, 'API mount resolves from local script including nested admin page');
      equal(await page.evaluate(async () => stApi('ticket', {name: 'Fixture'})), {ok: true}, 'Production API stays active');
      await page.evaluate(()=>stRecordVisit());
      equal(requests.map(r => [r.path, r.method, r.action]).sort((a,b)=>a.join().localeCompare(b.join())), [[mount+'api.php','GET','bootstrap'],[mount+'api.php','POST','ticket'],[mount+'api.php','POST','visit']].sort((a,b)=>a.join().localeCompare(b.join())), 'Only one synthetic same-mount bootstrap, automatic visit and explicit form write are exercised');
      equal(errors, [], 'No JavaScript errors');
      reports.push({url, preview: false, requests}); await page.close();
    }
    for (const url of ['https://github.io.evil.invalid/', 'https://saglamkombiklima.com.tr.evil.invalid/']) {
      const {page, requests, errors} = await scenario(url);
      equal(await page.evaluate(() => STEnvironment.officialProduction), false, 'Lookalike official host is not promoted');
      equal(await page.evaluate(() => STEnvironment.preview), false, 'Lookalike GitHub host does not match suffix');
      equal(await page.locator('#st-preview-banner').isVisible(), true, 'Lookalike host cannot hide preview notice');
      await page.evaluate(()=>stRecordVisit());
      equal(requests.map(r=>[r.path,r.action]).sort((a,b)=>a.join().localeCompare(b.join())), [['/api.php','bootstrap'],['/api.php','visit']], 'Copied production telemetry remains on its own fixture origin and never targets the official host'); equal(errors, [], 'No JavaScript errors'); await page.close();
    }
    const report = {passed: true, checks, reports, real_provider_requests: 0, actual_notification_requests: 0};
    const file = path.join(root, 'build/environment-report.json'); fs.mkdirSync(path.dirname(file), {recursive: true}); fs.writeFileSync(file, JSON.stringify(report, null, 2) + '\n');
    process.stdout.write(JSON.stringify({passed: true, checks, real_provider_requests: 0}) + '\n');
  } finally { await browser.close(); }
})().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
