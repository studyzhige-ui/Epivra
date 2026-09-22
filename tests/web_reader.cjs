// Uses the shipped Markdown and math parsers, with minimal output containers.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const markdownit = require('../src/epivra/web/markdown-it.min.js');
const katex = require('../src/epivra/web/katex.min.js');
const code = fs.readFileSync('src/epivra/web/reader.js','utf8')
  .replace(/^import .*;$/m, '').replaceAll('export function', 'function');
const context = vm.createContext({window:{katex}, crypto:{randomUUID:()=> 'test'}, t:(s,...v)=>s.replace(/\{(\d+)\}/g,(_,n)=>v[n]), document:{createElement:()=>({})}});
vm.runInContext(code,context);
const md = markdownit({html:false});
context.addMath(md);
const text = 'Literal \\[1], emoji 🦉 actual [1]. Code `[1]`.\n\n\\(x^2\\)\n\n$$\n\\frac{1}{2}\n$$';
const start = Array.from(text.slice(0,text.indexOf('actual')+7)).length;
const report = {text, citations:[{number:1,source:'s'}],citation_marks:[{start,end:start+3,number:1}]};
const target={innerHTML:'',querySelectorAll:()=>[]},toc={replaceChildren(){},append(){}};
context.renderReport(md,target,toc,report,()=>{},()=>{});
assert.equal((target.innerHTML.match(/href="#epivra-citation-test-1"/g)||[]).length,1);
assert.match(target.innerHTML,/Literal \[1\]/);
assert.match(target.innerHTML,/<code>\[1\]<\/code>/);
assert.equal((target.innerHTML.match(/<math/g)||[]).length,2);
const unsafe = md.render('\\(\\href{javascript:alert(1)}{x}\\)\n\n<script>alert(1)</script>');
assert.ok(!unsafe.includes('href="javascript:'));
assert.ok(!unsafe.includes('<script>'));
const labels=[];
const headingTarget={innerHTML:'',querySelectorAll:()=>[],querySelector:()=>({textContent:'标题 [1]'})};
context.renderReport(md,headingTarget,{replaceChildren(){},append(link){labels.push(link.textContent);}},
  {text:'# 标题 [1]',citations:[{number:1,source:'s'}],citation_marks:[{start:5,end:8,number:1}]},()=>{},()=>{});
assert.deepEqual(labels,['标题 [1]']);
assert.ok(!labels[0].includes('epivra-citation'));
console.log('Reader: exact citations, Unicode offsets, escaped/code literals, MathML and untrusted content OK');

for (let i=0; i<100; i++) context.renderReport(md,target,toc,report,()=>{},()=>{});
assert.equal(md.inline.ruler.__rules__.filter(r=>r.name==='bound_citation').length,1);
assert.ok(!md.render('[epivra-citation-test-1]').includes('href="#epivra-citation'));
for (const old of ['formula $x[1]$', '[label [1]](https://example.com)']) {
  context.renderReport(md,target,toc,{text:old,citation_marks:[],citations:[{number:1}]},()=>{},()=>{});
  assert.ok(!target.innerHTML.includes('epivra-citation'));
  if (old.startsWith('[label')) assert.match(target.innerHTML, /href="https:\/\/example.com"/);
}
assert.equal((md.render('$$x$$ after\n\nnext\n\n$$y$$').match(/<math/g)||[]).length,2);
assert.match(md.render('$$\n x\n\n  y\n$$'), /<math/);
assert.ok(!md.render('Price $5 to $10').includes('<math'));

for (const item of JSON.parse(fs.readFileSync('tests/fixtures/markdown_contracts.json', 'utf8'))) {
  const source = item.text.replace('@CITE@', '[1]');
  const offset = Array.from(source.slice(0, source.indexOf('[1]'))).length;
  context.renderReport(md, target, toc, {text: source, citations: [{number:1}],
    citation_marks: [{start:offset,end:offset+3,number:1}]}, ()=>{}, ()=>{});
  assert.equal((target.innerHTML.match(/href="#epivra-citation-test-1"/g)||[]).length, 1);
  assert.equal(md.parse(source, {}).filter(t=>t.type==='math_block').length, item.math_blocks);
  assert.ok(!md.parse(source, {}).some(t=>t.type==='math_block' && t.content.includes('Outside')));
}
const linkedText = '🦉 See [1]. Claim [1].\n\n[1]: https://author.example';
const linkedOffset = Array.from(linkedText.slice(0, linkedText.indexOf('Claim') + 6)).length;
const linkedReport = {text:linkedText, citations:[{number:1}],citation_marks:[{start:linkedOffset,end:linkedOffset+3,number:1}]};
context.renderReport(md,target,toc,linkedReport,()=>{},()=>{});
assert.equal((target.innerHTML.match(/href="https:\/\/author.example"/g)||[]).length,1);
assert.equal((target.innerHTML.match(/href="#epivra-citation-test-1"/g)||[]).length,1);
const exported = md.render(context.markdownReport(linkedReport));
assert.equal((exported.match(/href="https:\/\/author.example"/g)||[]).length,1);
assert.match(exported,/Claim \[1\]\./);
console.log('Shared Markdown contracts: list/quote boundaries and numeric link/citation identity preserved in reader and Markdown export');
