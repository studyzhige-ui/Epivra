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
