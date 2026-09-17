// Deterministic response ordering: no browser, account, or research calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/epivra/web/app.js', 'utf8');
const controls = source.slice(source.indexOf('  $("approve").hidden'), source.indexOf('  $("supplement").hidden'));
for (const [state, cancelHidden, deleteText] of [
  [{published:true}, true, '删除研究'],
  [{running:true}, false, '终止并删除'],
  [{cancelled:true}, true, '删除研究'],
  [{cancelled:true, deleting:true}, true, '重试删除'],
]) {
  const elements = {};
  vm.runInNewContext(controls, {s:state, t:x=>x, $:id => elements[id] ||= {}});
  assert.equal(Boolean(elements.cancel.hidden), cancelHidden);
  assert.equal(elements['delete-study'].textContent, deleteText);
}
const code = source.slice(source.indexOf('const statusReads ='), source.indexOf('function renderUsage'));
const pending = [], rendered = [];
const context = vm.createContext({
  active: 'a', statusSerial: 0,
  call: (_action, fields) => new Promise(resolve => pending.push({id: fields.study, resolve})),
  renderStatus: value => rendered.push(value),
});
vm.runInContext(code, context);
(async () => {
  const old = vm.runInContext('refreshStudy()', context);
  const duplicate = vm.runInContext('refreshStudy()', context);
  assert.equal(pending.length, 1);
  const fresh = vm.runInContext('refreshStudy(true)', context);
  assert.equal(pending.length, 2);
  pending[0].resolve('before-control');
  await Promise.all([old, duplicate]);
  assert.deepEqual(rendered, []);
  const freshDuplicate = vm.runInContext('refreshStudy()', context);
  assert.equal(pending.length, 2); // Old completion must not erase the new read.
  pending[1].resolve('after-control');
  await Promise.all([fresh, freshDuplicate]);
  assert.deepEqual(rendered, ['after-control']);
  const a = vm.runInContext('refreshStudy()', context);
  context.active = 'b';
  const b = vm.runInContext('refreshStudy()', context);
  pending[3].resolve('study-b');
  await b;
  pending[2].resolve('late-study-a');
  await a;
  assert.deepEqual(rendered, ['after-control', 'study-b']);
  console.log('status deduplication, fresh control reads, and switching: OK');
})().catch(error => { console.error(error); process.exitCode = 1; });
