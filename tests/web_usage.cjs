const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function node(tag, text) {
  return {tag, text, children: [],
    append(...items) { this.children.push(...items); },
    replaceChildren(...items) { this.children = items; },
    get childElementCount() { return this.children.length; }};
}
const list = node('div');
const source = fs.readFileSync('src/epivra/web/app.js', 'utf8');
const context = vm.createContext({node, labels: {}, $: () => list,
  t: (s, ...args) => s.replace(/\{(\d+)\}/g, (_, i) => args[i])});
vm.runInContext(source.slice(source.indexOf('function renderUsage'), source.indexOf('function sourceRows')), context);
context.groups = [
  {resource:'tavily', tool:'fetch_web', calls:2, totals:{search_credits:0, input_tokens:null}, reported_calls:{search_credits:1}},
  {resource:'jina', tool:'fetch_web', calls:4, totals:{reader_tokens:40684}, reported_calls:{reader_tokens:4}},
  {resource:'public:pubmed', tool:'search_pubmed', calls:1, totals:{input_tokens:null}},
  {resource:'model', calls:1, totals:{total_tokens:100}, reported_calls:{total_tokens:1}},
  {resource:'tavily', tool:'web_search', calls:76, totals:{search_credits:76}, reported_calls:{search_credits:76}},
  {resource:'public:pubmed', tool:'read_pubmed', calls:3, totals:{}},
];
vm.runInContext('renderUsage(groups)', context);
const text = JSON.stringify(list);
assert.ok(text.includes('网页搜索 credits'));
assert.ok(text.includes('读取 tokens'));
assert.ok(text.includes('已返回用量：1/2 次调用'));
assert.ok(text.includes('文献检索次数'));
assert.ok(!text.includes('输入 tokens'));
assert.ok(!text.includes('—'));
assert.ok(text.includes('总 tokens'));
assert.equal(list.children.length, 4);
// Exactly one flat metric grid per card, with no stacked function sections.
assert.equal(list.children[0].children.length, 3);
assert.equal(list.children[0].children[2].children.length, 4);
assert.equal(list.children[0].children[2].className, 'usage-metrics usage-paired');
assert.equal(list.children[2].children[2].className, 'usage-metrics usage-compact');
assert.equal(list.children[2].children[2].children.length, 2);
assert.ok(JSON.stringify(list.children[0]).includes('78 次调用'));
assert.ok(JSON.stringify(list.children[0]).includes('网页搜索'));
assert.ok(JSON.stringify(list.children[0]).includes('网页提取'));
assert.ok(JSON.stringify(list.children[2]).includes('4 次调用'));
vm.runInContext('renderUsage(groups)', context);
assert.equal(list.children.length, 4); // Polling replaces, never appends duplicate cards.
console.log('usage rendering: functional metrics, zero, missing and partial coverage OK');
