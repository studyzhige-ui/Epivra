/* Only known interface templates are translated. Research content is never scanned. */
const response = await fetch("/messages.json", { cache: "no-store" });
if (!response.ok) throw new Error("Could not load interface translations");
const originalMessages = await response.json();
const normalize = text => text.trim().replace(/\s+/g, " ");
const messages = Object.create(null);
for (const [key, value] of Object.entries(originalMessages)) {
  const normalized = normalize(key);
  if (Object.hasOwn(messages, normalized) && messages[normalized] !== value)
    throw new Error("Conflicting interface translations: " + normalized);
  messages[normalized] = value;
}
const explicit = new URLSearchParams(location.hash.slice(1)).get("lang");
let saved;
try { saved = localStorage.getItem("epivra-language"); } catch { /* Private browser storage may be disabled. */ }
export let language = ["zh-CN", "en"].includes(explicit) ? explicit
  : ["zh-CN", "en"].includes(saved) ? saved
  : navigator.language.startsWith("zh") ? "zh-CN" : "en";
export function t(message, ...values) {
  const text = language === "en" ? messages[normalize(message)] ?? message : message;
  return values.length ? text.replace(/\{(\d+)\}/g, (_, n) => String(values[n])) : text;
}
export const localized = (values) => new Proxy(values, {
  get: (target, key) => typeof target[key] === "string" ? t(target[key]) : target[key],
});
const bindings = [];
const walker = document.createTreeWalker(document.documentElement, NodeFilter.SHOW_TEXT);
while (walker.nextNode()) {
  const node = walker.currentNode;
  const source = node.data.trim();
  if (Object.hasOwn(messages, normalize(source))) {
    const leading = node.data.match(/^\s*/)[0], trailing = node.data.match(/\s*$/)[0];
    bindings.push({ node, source, read: () => node.data, write: (s) => { node.data = s; }, wrap: (s) => leading + s + trailing });
  }
}
for (const node of document.querySelectorAll("*")) {
  for (const attr of ["placeholder", "aria-label", "title", "content"]) {
    const source = node.getAttribute(attr);
    if (source && Object.hasOwn(messages, normalize(source)))
      bindings.push({ node, source, read: () => node.getAttribute(attr), write: (s) => node.setAttribute(attr, s), wrap: (s) => s });
  }
}
export function renderLanguage() {
  document.documentElement.lang = language;
  for (let i = bindings.length - 1; i >= 0; i--) {
    const binding = bindings[i];
    // A later renderer may replace a static placeholder with user content.
    if (!binding.node.isConnected || (binding.previous !== undefined && binding.read() !== binding.previous)) { bindings.splice(i, 1); continue; }
    binding.previous = binding.wrap(t(binding.source));
    binding.write(binding.previous);
  }
  document.getElementById("language").value = language;
}
export function setLanguage(value) {
  if (!["zh-CN", "en"].includes(value)) return;
  language = value;
  try { localStorage.setItem("epivra-language", value); } catch { /* Session still works without storage. */ }
  renderLanguage();
}
renderLanguage();
