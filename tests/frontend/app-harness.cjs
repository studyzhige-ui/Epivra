// Dependency-free DOM test double. Load the complete app, not copied handlers.
// This tests event ownership/API ordering; native focus/layout remain E2E work.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const web = path.resolve(__dirname, '../../src/epivra/web');
class Element {
  constructor(tag) {
    this.tagName = tag; this.children = []; this.attributes = {}; this.listeners = {};
    this.value = ''; this.className = ''; this.dataset = {}; this.disabled = false;
    this.hidden = false; this.open = false; this.checked = false;
    this.classList = {
      contains: name => this.className.split(/\s+/).includes(name),
      toggle: (name, enabled) => {
        const names = new Set(this.className.split(/\s+/).filter(Boolean));
        if (enabled ?? !names.has(name)) names.add(name); else names.delete(name);
        this.className = [...names].join(' ');
      },
    };
  }
  set textContent(value) {
    this.children = [];
    if (value) this.append(Object.assign(new Element('#text'), {data: value}));
  }
  get textContent() { return this.data || this.children.map(c => c.textContent).join(''); }
  get firstChild() { return this.children[0]; }
  get isConnected() { return !!this.parentElement?.isConnected; }
  append(...children) {
    for (let child of children) {
      if (typeof child === 'string') child = Object.assign(new Element('#text'), {data: child});
      if (child.parentElement) child.remove();
      child.parentElement = this; this.children.push(child);
      if (this.tagName === 'select' && this.children.length === 1) this.value = child.value;
    }
  }
  replaceChildren(...children) {
    for (const child of this.children) child.parentElement = null;
    this.children = []; this.append(...children);
  }
  remove() {
    this.parentElement.children = this.parentElement.children.filter(c => c !== this);
    this.parentElement = null;
  }
  setAttribute(name, value) {
    this.attributes[name] = String(value);
    if (name === 'class') this.className = value;
    else if (name === 'id' || name === 'value' || name === 'type') this[name] = value;
    else if (['disabled', 'hidden', 'open', 'checked'].includes(name)) this[name] = true;
    else if (name.startsWith('data-')) this.dataset[name.slice(5)] = value;
  }
  getAttribute(name) { return this.attributes[name] ?? null; }
  removeAttribute(name) { delete this.attributes[name]; }
  matches(selector) {
    const checked = selector.endsWith(':checked');
    if (checked) selector = selector.slice(0, -8);
    if (checked && !this.checked) return false;
    const attr = selector.match(/\[([^=\]]+)(?:=["']?([^"'\]]+)["']?)?\]$/);
    if (attr) {
      selector = selector.slice(0, attr.index);
      const value = this[attr[1]] ?? this.getAttribute(attr[1]);
      if (attr[2] === undefined ? value === null || value === false : String(value) !== attr[2]) return false;
    }
    if (!selector) return true;
    if (selector.startsWith('#')) return this.id === selector.slice(1);
    if (selector.startsWith('.')) return this.classList.contains(selector.slice(1));
    return this.tagName === selector;
  }
  querySelectorAll(selector) {
    const selectors = selector.split(',').map(s => s.trim());
    const result = [];
    const walk = root => { for (const child of root.children) {
      if (selectors.some(s => child.matches(s))) result.push(child);
      walk(child);
    } };
    walk(this); return result;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  closest(selector) { return this.matches(selector) ? this : this.parentElement?.closest(selector); }
  addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
  dispatch(name, event = {}) {
    for (const callback of this.listeners[name] || []) callback(event);
    return this['on' + name]?.({target: this, preventDefault() {}, ...event});
  }
  click() { if (!this.disabled) return this.dispatch('click'); }
  focus() {}
  showModal() { this.open = true; this.shows = (this.shows || 0) + 1; }
  close() { this.open = false; this.dispatch('close'); }
}
function documentFromHtml() {
  const root = new Element('document');
  Object.defineProperty(root, 'isConnected', {value: true});
  const stack = [root];
  const html = fs.readFileSync(path.join(web, 'index.html'), 'utf8');
  for (const token of html.match(/<!--[^]*?-->|<[^>]+>|[^<]+/g)) {
    if (token.startsWith('<!')) continue;
    if (token.startsWith('</')) { stack.pop(); continue; }
    if (!token.startsWith('<')) { stack.at(-1).append(token); continue; }
    const tag = token.match(/^<([\w-]+)/)[1];
    const element = new Element(tag);
    for (const [, name, quoted, bare] of token.slice(tag.length + 1, -1).matchAll(/([\w-]+)(?:\s*=\s*(?:"([^"]*)"|([^\s>]+)))?/g))
      element.setAttribute(name, quoted ?? bare ?? '');
    stack.at(-1).append(element);
    if (!['meta', 'link', 'img', 'input', 'br', 'hr'].includes(tag)) stack.push(element);
  }
  root.getElementById = id => root.querySelector('#' + id);
  const query = root.querySelector.bind(root);
  root.querySelector = selector => {
    const parts = selector.split(/\s+/);
    return parts.length > 1 ? query(parts[0])?.querySelector(parts.slice(1).join(' ')) : query(selector);
  };
  root.createElement = tag => new Element(tag);
  root.createTextNode = text => Object.assign(new Element('#text'), {data: text});
  root.body = query('body');
  return root;
}
const settings = () => ({defaults: {provider: 'deepseek', model: 'saved-model'},
  providers: [{id: 'deepseek', configured: true, model: 'saved-model', credential: 'MODEL_KEY', regions: ['global'], region: 'global'}],
  connections: [{id: 'tavily', credential: 'SEARCH_KEY', configured: false}],
  search: ['duckduckgo', 'tavily'], max_upload: 10000});
function createApp(route = () => undefined) {
  const document = documentFromHtml(), requests = [], timers = new Map();
  let timerId = 0;
  const context = vm.createContext({document, URLSearchParams, Map, Set, console,
    location: {hash: '', pathname: '/'}, sessionStorage: {getItem: () => '', setItem() {}, removeItem() {}},
    history: {}, crypto: {randomUUID: () => 'uuid'}, navigator: {},
    window: {addEventListener() {}, markdownit: () => ({renderer: {rules: {}}, utils: {}, render: () => ''})},
    localized: x => x, t: (text, ...args) => text.replace(/\{(\d+)\}/g, (_, i) => args[i]),
    language: 'en', setLanguage() {}, addMath() {}, renderReport() {}, standalone() {}, markdownReport() {},
    setTimeout: (callback, ms) => { const id = ++timerId; timers.set(id, {callback, ms}); return id; },
    clearTimeout: id => timers.delete(id),
    fetch: async (url, options) => {
      const data = options.body && typeof options.body === 'string' ? JSON.parse(options.body) : options.body;
      const request = {url, data, method: options.method}; requests.push(request);
      let result = await route(request);
      if (result === undefined) {
        if (url === '/api/settings') result = settings();
        else if (url === '/api/components') result = {job: {state: 'idle'}, documents: false, analysis: false};
        else if (url === '/api/models') result = {models: [], source: 'local', message: ''};
        else if (data?.action === 'mcp_connections') result = {servers: []};
        else if (data?.action === 'status') result = {control: 'control-S', paused: true};
        else throw Error('Unhandled API ' + JSON.stringify(request));
      }
      return {ok: !result.error, json: async () => result};
    },
  });
  const source = fs.readFileSync(path.join(web, 'app.js'), 'utf8')
    .replace(/^import .*;\n/gm, '')
    .replace('boot().catch((e) => notice(e.message));', '');
  vm.runInContext(source + `\nconfig = ${JSON.stringify(settings())};
    globalThis.testApp = {openSettings, loadConfig, addMaterial, fetchModels, refreshComponents,
      get materials() { return materials; }, get pending() { return pendingMaterials; },
      get session() { return settingsSession; }, get config() { return config; },
      get mutating() { return mutating; }, get editors() { return roleModelEditors; },
      opened: [], refreshes: 0};
    openStudy = async id => { active = id; status = {control: 'control-' + id, paused: true}; testApp.opened.push(id); };
    refreshList = async () => { testApp.refreshes++; };
    afterControl = async () => {};
  `, context, {filename: 'app.js'});
  return {app: context.testApp, document, el: id => document.getElementById(id), requests, timers};
}
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => {resolve=a;reject=b;}); return {promise,resolve,reject}; };
const flush = () => new Promise(resolve => setImmediate(resolve));
module.exports = {createApp, deferred, flush, settings};
