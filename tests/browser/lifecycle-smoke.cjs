/* Optional real-browser check: npm install --no-save playwright, then
 * npx playwright install chromium; node tests/browser/lifecycle-smoke.cjs
 * Set EPIVRA_CHROMIUM to use an existing Chromium executable instead.
 * Serves the shipped web assets; every API is mocked on loopback. No providers.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const http = require('node:http');
const path = require('node:path');
const {chromium} = require('playwright');
const web = path.resolve(__dirname, '../../src/epivra/web');
const deferred = () => {let resolve; const promise = new Promise(r => {resolve = r;}); return {promise, resolve};};
const types = {'.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.json':'application/json', '.svg':'image/svg+xml'};
const server = http.createServer(async (req, res) => {
  const name = new URL(req.url, 'http://localhost').pathname;
  if (name !== '/' && !/^\/[\w.-]+$/.test(name)) {res.writeHead(404); res.end(); return;}
  try {
    const data = await fs.readFile(path.join(web, name === '/' ? 'index.html' : name.slice(1)));
    res.setHeader('Content-Type', types[path.extname(name)] || (name === '/' ? 'text/html' : 'application/octet-stream'));
    res.end(data);
  } catch {res.writeHead(404); res.end();}
});
(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser, page;
  try {
    browser = await chromium.launch({headless:true, executablePath:process.env.EPIVRA_CHROMIUM, args:['--no-sandbox']});
    page = await browser.newPage();
    const errors = [], calls = [];
    page.on('pageerror', error => errors.push(error.message));
    const config = {defaults:{provider:'deepseek', model:'saved-model'},
      providers:[{id:'deepseek', configured:true, model:'saved-model', credential:'MODEL_KEY', regions:['global'], region:'global'}],
      connections:[{id:'tavily', credential:'SEARCH_KEY', configured:false}], search:['duckduckgo','tavily'], max_upload:10000};
    let delayedSettings = null, delayedSave = null, delayedCreate = null, delayedResume = null;
    let created = false, paused = true, failSecond = true, oldSettingsDone = false;
    const status = () => ({study:'S', request:'Original request', control:'control-S', direction:'direction-S',
      policy:{provider:'deepseek',model:'saved-model',network:true}, paused, source_count:1, running:false, plans:[]});
    await page.route('**/api/**', async route => {
      const req = route.request(), url = new URL(req.url()), data = req.postDataJSON();
      calls.push({path:url.pathname, data});
      let result, code = 200;
      if (url.pathname === '/api/settings') {
        if (req.method() === 'POST') {
          if (delayedSave) {const gate = delayedSave; delayedSave = null; await gate.promise;}
          config.defaults = data; result = {saved:true};
        } else {
          if (delayedSettings) {const gate = delayedSettings; delayedSettings = null; await gate.promise; oldSettingsDone = true;}
          result = config;
        }
      } else if (url.pathname === '/api/models') result = {models:[], source:'local', message:''};
      else if (url.pathname === '/api/components') result = {job:{state:'idle'},documents:false,analysis:false};
      else if (url.pathname === '/api/command') {
        switch (data.action) {
          case 'overview': result = {studies:created ? [status()] : []}; break;
          case 'mcp_connections': result = {servers:['test-server']}; break;
          case 'status': result = status(); break;
          case 'progress': result = {work:[]}; break;
          case 'create':
            if (delayedCreate) await delayedCreate.promise;
            created = true; result = {study:'S'}; break;
          case 'import_file':
            if (data.path === 'second.txt' && failSecond) {code = 400; result = {error:'parse failed'};}
            else result = {characters:10};
            break;
          case 'control':
            if (delayedResume) await delayedResume.promise;
            paused = false; result = {}; break;
          default: throw Error('Unhandled command ' + data.action);
        }
      } else throw Error('Unhandled API ' + url.pathname);
      await route.fulfill({status:code, contentType:'application/json', body:JSON.stringify(result)});
    });
    await page.goto(`http://127.0.0.1:${server.address().port}/#token=browser-test&lang=en`);
    await page.waitForFunction(() => document.getElementById('model-summary').textContent.includes('saved-model'));

    // Native modal cancellation while its config fetch is pending.
    const firstSettings = deferred(); delayedSettings = firstSettings;
    await page.click('#open-settings');
    await page.waitForFunction(() => document.getElementById('settings-dialog').open);
    assert.equal(await page.locator('#settings-form button[type=submit]').isDisabled(), true);
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => !document.getElementById('settings-dialog').open);
    await page.click('#open-settings');
    await page.waitForFunction(() => !document.querySelector('#settings-dialog .settings-body').hidden);
    await page.fill('#model', 'Unsaved newer edit');
    const staleResponse = page.waitForResponse(response => response.url().endsWith('/api/settings'));
    firstSettings.resolve();
    await staleResponse;
    assert.equal(oldSettingsDone, true);
    assert.equal(await page.inputValue('#model'), 'Unsaved newer edit');
    assert.equal(await page.locator('#settings-dialog').evaluate(el => el.open), true);
    await page.click('#settings-dialog .close-dialog');

    // Create must disable every actual form control, including hidden uploads
    // and dynamically added remove buttons, then preserve queued change events.
    await page.fill('#request', 'Original request');
    await page.selectOption('#scope', 'both');
    for (const name of ['first.txt', 'second.txt']) {
      await page.fill('#material-path', name); await page.click('#add-path');
    }
    delayedCreate = deferred();
    await page.click('#create-button');
    await page.waitForFunction(() => document.getElementById('request').disabled);
    assert.equal(await page.locator('#create-form').evaluate(el =>
      [...el.querySelectorAll('input,select,textarea,button')].every(input => input.disabled)), true);
    await page.evaluate(() => {
      document.getElementById('request').value = 'Late request';
      const transfer = new DataTransfer(); transfer.items.add(new File(['late'], 'late.txt', {type:'text/plain'}));
      const upload = document.getElementById('upload-files');
      upload.files = transfer.files; upload.dispatchEvent(new Event('change', {bubbles:true}));
    });
    delayedCreate.resolve();
    await page.waitForFunction(() => !document.getElementById('study-view').hidden && !document.getElementById('supplement').disabled);
    await page.click('#supplement');
    assert.match(await page.locator('#pending-materials').textContent(), /second.txt/);
    assert.doesNotMatch(await page.locator('#pending-materials').textContent(), /first.txt/);
    assert.match(await page.locator('#pending-materials-hint').textContent(), /this page/);
    await page.keyboard.press('Escape');
    await page.click('#supplement');
    failSecond = false;
    await page.click('#retry-materials');
    await page.waitForFunction(() => document.getElementById('retry-materials').hidden);
    await page.click('#supplement-dialog .close-dialog');
    delayedResume = deferred();
    await page.click('#pause-resume');
    await page.waitForFunction(() => document.getElementById('pause-resume').disabled);
    assert.equal(await page.locator('#request').isDisabled(), true);
    delayedResume.resolve();
    await page.waitForFunction(() => !document.getElementById('pause-resume').disabled);
    await page.click('#new-study');
    assert.equal(await page.inputValue('#request'), 'Late request');
    assert.match(await page.locator('#selected-materials').textContent(), /late.txt/);
    const imports = calls.filter(call => call.data?.action === 'import_file').map(call => call.data.path);
    assert.deepEqual(imports, ['first.txt', 'second.txt', 'second.txt']);
    assert.equal(calls.filter(call => call.data?.action === 'create').length, 1);

    // Saving remains one operation even if the native dialog is dismissed.
    await page.click('#open-settings');
    await page.waitForFunction(() => !document.querySelector('#settings-dialog .settings-body').hidden);
    const save = deferred(); delayedSave = save;
    await page.click('#settings-form button[type=submit]');
    await page.waitForFunction(() => document.getElementById('model').disabled);
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => !document.getElementById('settings-dialog').open);
    save.resolve();
    await page.waitForFunction(() => document.getElementById('notice').textContent.includes('Settings saved'));
    assert.equal(await page.locator('#settings-dialog').evaluate(el => el.open), false);
    assert.deepEqual(errors, []);
    console.log('Browser lifecycle smoke passed: Escape/stale settings, full creation locks, partial-import retry, retained draft/File inputs, save dismissal');
    if (process.env.EPIVRA_BROWSER_ARTIFACTS) {
      await fs.mkdir(process.env.EPIVRA_BROWSER_ARTIFACTS, {recursive:true});
      await page.screenshot({path:path.join(process.env.EPIVRA_BROWSER_ARTIFACTS, 'lifecycle-passed.png'), fullPage:true});
    }
  } catch (error) {
    if (page && process.env.EPIVRA_BROWSER_ARTIFACTS) {
      await fs.mkdir(process.env.EPIVRA_BROWSER_ARTIFACTS, {recursive:true});
      await page.screenshot({path:path.join(process.env.EPIVRA_BROWSER_ARTIFACTS, 'lifecycle-failed.png'), fullPage:true}).catch(() => {});
    }
    throw error;
  } finally {
    await browser?.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
