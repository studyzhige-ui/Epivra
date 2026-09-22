// Exercise actual UI functions with controlled asynchronous responses.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const read=p=>fs.readFileSync(p,'utf8');
const app=read('src/epivra/web/app.js'),pending=[],rows=[];
const p=vm.createContext({active:'a',status:{control:'c',source_count:1},tab:'materials',language:'en',call:()=>new Promise(resolve=>pending.push(resolve)),sourceRows:(_,sources)=>rows.push(sources),$:()=>({})});
vm.runInContext(app.slice(app.indexOf('let materialsPending'),app.indexOf('function renderPlan(')),p);
(async()=>{let old=p.loadPanel();p.status.source_count=2;let recent=p.loadPanel();pending[1]({sources:['new1','new2']});await recent;pending[0]({sources:['old1']});await old;assert.deepEqual(rows,[['new1','new2']]);console.log('materials: newer count response survives old response finishing last');
const elements={'request':{value:'research'},scope:{value:'local'},'text-encoding':{value:'gb18030'}};const commands=[],imports=[];let action;
const f=vm.createContext({$:id=>elements[id]||=( {}),materials:[{kind:'file',path:'sample.txt'}],config:{defaults:{provider:'deepseek',text_encoding:'utf-8-sig'},providers:[{id:'deepseek',configured:true}]},t:s=>s,act:(_,fn)=>(action=fn()),call:async(action,args)=>{commands.push({action,args});return action==='create'?{study:'s'}:{control:'c'}},importMaterial:async(...args)=>{imports.push(args);return{}},control:async()=>{},renderMaterials(){},openStudy:async()=>{},refreshList:async()=>{},notice(){}});
vm.runInContext(app.slice(app.indexOf('$("create-form").onsubmit'),app.indexOf('$("new-study").onclick')),f);elements['create-form'].onsubmit({preventDefault(){}});await action;assert.equal(commands[0].action,'create');assert.equal(commands[0].args.text_encoding,'gb18030');assert.equal(imports.length,1);console.log('create: selected GB18030 overrides UTF8 defaults before file import');
})().catch(e=>{console.error(e);process.exitCode=1});

// Render a terminal cancellation through the actual progress function.
const badges = [];
const element = () => ({dataset:{}, children:[], querySelectorAll:()=>[],
  append(...children){this.children.push(...children);}, replaceChildren(){this.children=[];}});
const workList = element();
const cancelledProgress = vm.createContext({active:'s',status:{direction:'d'},tab:'progress',language:'en',roles:{writer:'Writer'},
  call:async()=>({work:[{ref:'w',role:'writer',task:'Revise',state:'cancelled'}]}),
  t:s=>s, $:()=>workList,
  node:(tag,text,style)=>{if(style==='badge')badges.push(text);return element();}});
vm.runInContext(app.slice(app.indexOf('let progressPending'),app.indexOf('function setReader(')),cancelledProgress);
cancelledProgress.loadProgress().then(()=>{
  assert.deepEqual(badges,['已取消']);
  console.log('progress: cancelled work is not presented as delivered');
}).catch(e=>{console.error(e);process.exitCode=1;});
