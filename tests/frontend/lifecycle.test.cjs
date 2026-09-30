const test = require('node:test');
const assert = require('node:assert/strict');
const {createApp, deferred, flush, settings} = require('./app-harness.cjs');
const submit = el => el.dispatch('submit', {submitter: el.querySelector('button[type=submit]')});
const names = items => Array.from(items, item => item.path || item.file.name);
const commands = ui => ui.requests.filter(r => r.data?.action).map(r => r.data.action);
function draft(ui) {
  ui.el('request').value = 'Original request';
  ui.el('scope').value = 'both';
  ui.el('text-encoding').value = 'utf-8-sig';
  ui.app.addMaterial({kind: 'file', path: 'first.txt'});
  ui.app.addMaterial({kind: 'file', path: 'second.txt'});
}
function assertCreateLocked(ui, expected) {
  for (const control of ui.el('create-form').querySelectorAll('input, select, textarea, button'))
    assert.equal(control.disabled, expected, control.id || control.tagName);
}
test('create, each import and resume own the complete draft lock; late inputs survive', async () => {
  const gates = [deferred(), deferred(), deferred(), deferred()];
  let step = 0;
  const ui = createApp(async ({data}) => {
    if (data?.action === 'create') return gates[step++].promise;
    if (data?.action === 'import_file' || data?.action === 'control') return gates[step++].promise;
  });
  draft(ui);
  const run = submit(ui.el('create-form'));
  assertCreateLocked(ui, true);
  await submit(ui.el('create-form'));
  assert.equal(commands(ui).filter(x => x === 'create').length, 1);
  // Simulate a queued native file-change/programmatic edit, even though native
  // user edits are disabled. Only the exact submitted snapshot may be retired.
  ui.el('request').value = 'Late request';
  ui.el('upload-files').dispatch('change', {target: {files: [{name: 'late.txt'}], value: ''}});
  ui.el('add-path').value = 'ignored';
  gates[0].resolve({study: 'S'}); await flush();
  assertCreateLocked(ui, true);
  gates[1].resolve({characters: 1}); await flush();
  assertCreateLocked(ui, true);
  gates[2].resolve({characters: 2}); await flush();
  assertCreateLocked(ui, true);
  gates[3].resolve({}); await run;
  assertCreateLocked(ui, false);
  assert.deepEqual(names(ui.app.materials), ['late.txt']);
  assert.equal(ui.el('request').value, 'Late request');
  assert.equal(ui.app.pending.has('S'), false);
  assert.deepEqual(Array.from(ui.app.opened), ['S']);
});
test('web-only submission retains unused local material choices', async () => {
  const ui = createApp(({data}) => data?.action === 'create' ? {study: 'S'} : data?.action === 'control' ? {} : undefined);
  draft(ui); ui.el('scope').value = 'web';
  await submit(ui.el('create-form'));
  assert.deepEqual(names(ui.app.materials), ['first.txt', 'second.txt']);
  assert.equal(ui.el('request').value, '');
  assert.ok(!commands(ui).includes('import_file'));
});
test('failed create retains the entire draft and never automatically repeats an unknown result', async () => {
  const ui = createApp(({data}) => { if (data?.action === 'create') throw Error('lost response'); });
  draft(ui); await submit(ui.el('create-form'));
  assertCreateLocked(ui, false);
  assert.equal(ui.el('request').value, 'Original request');
  assert.deepEqual(names(ui.app.materials), ['first.txt', 'second.txt']);
  assert.deepEqual(commands(ui), ['create']);
  assert.equal(ui.app.pending.size, 0);
  assert.match(ui.el('notice').textContent, /不要重复/);
});
test('partial imports stay with the created study and retry only unacknowledged files', async () => {
  let fail = true;
  const ui = createApp(({data}) => {
    if (data?.action === 'create') return {study: 'S'};
    if (data?.action === 'import_file') return data.path === 'second.txt' && fail ? {error: 'parse failed'} : {characters: 5};
    if (data?.action === 'control') return {};
  });
  draft(ui); await submit(ui.el('create-form'));
  assert.deepEqual(names(ui.app.pending.get('S')), ['second.txt']);
  assert.equal(ui.app.materials.length, 0);
  assert.equal(ui.el('request').value, '');
  assertCreateLocked(ui, false);
  assert.ok(!commands(ui).includes('control'));
  ui.el('supplement').click();
  assert.match(ui.el('pending-materials').textContent, /second.txt/);
  ui.el('supplement-dialog').close();
  ui.el('supplement').click();
  await ui.el('retry-materials').click();
  assert.deepEqual(names(ui.app.pending.get('S')), ['second.txt']);
  fail = false; await ui.el('retry-materials').click();
  assert.equal(ui.app.pending.has('S'), false);
  const imported = ui.requests.filter(r => r.data?.action === 'import_file').map(r => r.data.path);
  assert.deepEqual(imported, ['first.txt', 'second.txt', 'second.txt', 'second.txt']);
  assert.equal(commands(ui).filter(x => x === 'create').length, 1);
  assert.ok(!commands(ui).includes('control'), 'retry does not silently resume paid work');
  await ui.el('pause-resume').click();
  assert.equal(commands(ui).at(-1), 'control');
});
test('status/resume failure keeps the accepted study without making another create', async () => {
  for (const stage of ['status', 'control']) {
    const ui = createApp(({data}) => {
      if (data?.action === 'create') return {study: 'S'};
      if (data?.action === stage) return {error: 'temporary failure'};
      if (data?.action === 'import_file') return {characters: 5};
    });
    draft(ui); await submit(ui.el('create-form'));
    assert.equal(commands(ui).filter(x => x === 'create').length, 1);
    assert.equal(ui.el('request').value, '');
    assert.equal(ui.app.pending.get('S')?.length || 0, stage === 'status' ? 2 : 0);
    assert.deepEqual(Array.from(ui.app.opened), ['S']);
    assertCreateLocked(ui, false);
  }
});
test('native picker locks submission and preserves its selected file on completion', async () => {
  const gate = deferred();
  const ui = createApp(({url}) => url === '/api/pick' ? gate.promise : undefined);
  draft(ui); const picked = ui.el('pick-file').click();
  assertCreateLocked(ui, true);
  await submit(ui.el('create-form'));
  gate.resolve({path: 'picked.txt'}); await picked;
  assert.deepEqual(names(ui.app.materials), ['first.txt', 'second.txt', 'picked.txt']);
  assertCreateLocked(ui, false);
  assert.ok(!commands(ui).includes('create'));
});
test('files selected during another import stay queued after the current batch', async () => {
  const ui = createApp(({data}) => {
    if (data?.action === 'create') return {study: 'S'};
    if (data?.action === 'import_file') return {error: 'retry later'};
  });
  draft(ui); await submit(ui.el('create-form'));
  ui.el('supplement').click();
  // Existing importer is pending; a browser chooser can still deliver a change.
  const pending = ui.el('retry-materials').click();
  ui.el('supplement-upload').dispatch('change', {target: {files: [{name: 'late.txt'}], value: ''}});
  await pending;
  assert.deepEqual(names(ui.app.pending.get('S')), ['first.txt', 'second.txt', 'late.txt']);
});
test('settings opening is single-flight and already-open settings preserve edits', async () => {
  const load = deferred(), mcp = deferred();
  const ui = createApp(({url, data}) => url === '/api/settings' ? load.promise : data?.action === 'mcp_connections' ? mcp.promise : undefined);
  const first = ui.app.openSettings();
  await ui.app.openSettings();
  assert.equal(ui.requests.filter(r => r.url === '/api/settings').length, 1);
  assert.equal(ui.el('settings-dialog').open, true);
  assert.equal(ui.el('settings-form').querySelector('button[type=submit]').disabled, true);
  load.resolve(settings()); await flush();
  assert.equal(ui.app.session.phase, 'loading');
  mcp.resolve({servers: ['test-server']}); await first;
  ui.el('model').value = 'Unsaved edit';
  await ui.app.openSettings();
  assert.equal(ui.el('model').value, 'Unsaved edit');
  assert.equal(ui.el('settings-dialog').shows, 1);
});
test('closing during config load invalidates older responses after another open', async () => {
  const loads = [deferred(), deferred()]; let count = 0;
  const ui = createApp(({url}) => url === '/api/settings' ? loads[count++].promise : undefined);
  const first = ui.app.openSettings();
  ui.el('settings-dialog').close();
  const second = ui.app.openSettings();
  const newer = settings(); newer.defaults.model = 'new-saved-model';
  loads[1].resolve(newer); await second;
  ui.el('model').value = 'New user edit';
  loads[0].resolve(settings()); await first;
  assert.equal(ui.el('model').value, 'New user edit');
  assert.equal(ui.app.config.defaults.model, 'new-saved-model');
  assert.equal(ui.el('settings-dialog').shows, 2);
});
test('late MCP response and error cannot reopen a dismissed dialog or replace newer fields', async () => {
  for (const reject of [false, true]) {
    const mcp = deferred(); let count = 0;
    const ui = createApp(({data}) => data?.action === 'mcp_connections' ? (++count === 1 ? mcp.promise : {servers: ['new-server']}) : undefined);
    const first = ui.app.openSettings(); await flush();
    ui.el('settings-dialog').dispatch('cancel'); ui.el('settings-dialog').close();
    const second = ui.app.openSettings(); await second;
    ui.el('model').value = 'Keep me';
    if (reject) mcp.reject(Error('old failure')); else mcp.resolve({servers: ['old-server']});
    await first;
    assert.equal(ui.el('model').value, 'Keep me');
    assert.match(ui.el('mcp-options').textContent, /new-server/);
    assert.doesNotMatch(ui.el('mcp-options').textContent, /old-server/);
    assert.doesNotMatch(ui.el('settings-feedback').textContent, /old failure/);
    ui.el('settings-dialog').close();
    assert.equal(ui.el('settings-dialog').open, false);
  }
});
test('save freezes settings and stale read callbacks cannot reenable or replace them', async () => {
  const model = deferred(), components = deferred(), save = deferred();
  const ui = createApp(({url, method}) => {
    if (url === '/api/models') return model.promise;
    if (url === '/api/components') return components.promise;
    if (url === '/api/settings' && method === 'POST') return save.promise;
  });
  await ui.app.openSettings();
  ui.el('model').value = 'new-model'; ui.el('context-tokens').value = '1000'; ui.el('max-tokens').value = '100';
  const saving = submit(ui.el('settings-form'));
  assert.equal(ui.app.session.phase, 'saving');
  for (const el of ui.el('settings-form').querySelectorAll('input, select, textarea, button'))
    assert.equal(el.disabled, !el.classList.contains('close-dialog'), el.id || el.tagName);
  model.resolve({models: [{id: 'stale-model'}], source: 'local', message: 'stale'});
  components.resolve({job: {state: 'idle'}, documents: false, analysis: false}); await flush();
  assert.equal(ui.el('install-analysis').disabled, true);
  assert.equal(ui.el('fetch-models').disabled, true);
  assert.equal(ui.el('model').value, 'new-model');
  ui.el('settings-dialog').close();
  await ui.app.openSettings();
  assert.equal(ui.el('settings-dialog').open, false, 'cannot open a new editor while saving');
  save.resolve({}); await saving;
  assert.equal(ui.el('settings-dialog').open, false);
  assert.equal(ui.app.mutating, false);
  assert.match(ui.el('notice').textContent, /设置已保存/);
});
test('failed settings save retains edits and restores the editor for retry', async () => {
  let fail = true;
  const ui = createApp(({url, method}) => url === '/api/settings' && method === 'POST' ? (fail ? {error: 'write failed'} : {}) : undefined);
  await ui.app.openSettings();
  ui.el('model').value = 'custom';
  await submit(ui.el('settings-form'));
  assert.equal(ui.el('settings-dialog').open, true);
  assert.equal(ui.el('model').value, 'custom');
  assert.equal(ui.el('model').disabled, false);
  assert.equal(ui.app.session.phase, 'editing');
  assert.match(ui.el('settings-feedback').textContent, /write failed/);
  fail = false; await submit(ui.el('settings-form'));
  assert.equal(ui.el('settings-dialog').open, false);
});
test('old component responses and role-model responses cannot affect a reopened editor', async () => {
  const oldComponents = deferred(), oldModels = deferred(); let componentCalls = 0, modelCalls = 0;
  const ui = createApp(({url}) => {
    if (url === '/api/components' && ++componentCalls === 1) return oldComponents.promise;
    if (url === '/api/models' && ++modelCalls === 2) return oldModels.promise;
  });
  await ui.app.openSettings();
  const oldEditor = ui.app.editors[0];
  const oldButton = oldEditor.controls.model.parentElement.parentElement.querySelector('button');
  const fetching = oldButton.click();
  ui.el('settings-dialog').close();
  await ui.app.openSettings(); await flush();
  oldComponents.resolve({job: {state: 'running', component: 'analysis', phase: 'complete'}, documents: true, analysis: true});
  oldModels.resolve({models: [{id: 'old-result'}], source: 'local', message: ''}); await fetching; await flush();
  assert.equal(ui.el('analysis-state').textContent, '未就绪');
  assert.equal(ui.el('install-analysis').disabled, false);
  assert.equal(ui.el('role-model-fields').textContent.includes('old-result'), false);
});
test('pending files block resume until explicitly imported or removed', async () => {
  const ui = createApp(({data}) => {
    if (data?.action === 'create') return {study:'S'};
    if (data?.action === 'import_file') return {error:'bad file'};
    if (data?.action === 'control') return {};
  });
  draft(ui); await submit(ui.el('create-form'));
  await ui.el('pause-resume').click();
  assert.ok(!commands(ui).includes('control'));
  ui.el('supplement').click();
  while (ui.el('pending-materials').querySelector('button'))
    ui.el('pending-materials').querySelector('button').click();
  assert.equal(ui.app.pending.has('S'), false);
  await ui.el('pause-resume').click();
  assert.equal(commands(ui).at(-1), 'control');
});
test('settings refresh preserves a manually edited draft encoding', async () => {
  const next = settings(); next.defaults.text_encoding = 'utf-16';
  const ui = createApp(({url}) => url === '/api/settings' ? next : undefined);
  ui.el('text-encoding').value = 'gb18030';
  await ui.app.openSettings();
  assert.equal(ui.el('text-encoding').value, 'gb18030');
});
test('queued native close event cannot invalidate an already reopened settings session', async () => {
  const ui = createApp(); await ui.app.openSettings();
  // Explicit dismiss synchronously invalidates the old session, but the native
  // close event itself can be dispatched on a later browser task.
  ui.el('settings-dialog').querySelector('.close-dialog').click();
  await ui.app.openSettings();
  const session = ui.app.session;
  ui.el('settings-dialog').dispatch('close');
  assert.equal(ui.app.session, session);
  assert.equal(ui.el('settings-dialog').open, true);
});
test('failed save invalidates an in-flight role lookup without leaving its button locked', async () => {
  const models = deferred(); let modelCalls = 0;
  const ui = createApp(({url, method}) => {
    if (url === '/api/models' && ++modelCalls === 2) return models.promise;
    if (url === '/api/settings' && method === 'POST') return {error:'write failed'};
  });
  await ui.app.openSettings();
  const editor = ui.app.editors[0], button = editor.controls.model.parentElement.parentElement.querySelector('button');
  const lookup = button.click();
  assert.equal(button.disabled, true);
  await submit(ui.el('settings-form'));
  assert.equal(button.disabled, false);
  models.resolve({models:[{id:'old'}],source:'local',message:''}); await lookup;
  assert.equal(button.disabled, false);
  assert.equal(ui.app.session.phase, 'editing');
});
test('overlapping background config reads cannot strand a settings editor in loading', async () => {
  const gates = [deferred(), deferred()]; let count = 0;
  const ui = createApp(({url}) => url === '/api/settings' ? gates[count++].promise : undefined);
  const opening = ui.app.openSettings();
  const background = ui.app.loadConfig();
  gates[0].resolve(settings()); await opening;
  assert.equal(ui.app.session.phase, 'editing');
  ui.el('model').value = 'User draft';
  gates[1].resolve(settings()); await background;
  assert.equal(ui.el('model').value, 'User draft');
});
