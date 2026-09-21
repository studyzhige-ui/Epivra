/* Shared, offline report rendering. Content never supplies executable HTML. */
import { t } from "./i18n.js";

export function addMath(md) {
  const render = (tokens, i) => {
    try {
      return window.katex.renderToString(tokens[i].content, {
        output: "mathml", displayMode: tokens[i].block, trust: false,
        throwOnError: true, maxExpand: 1000, maxSize: 20,
      });
    } catch {
      return `<code>${md.utils.escapeHtml(tokens[i].content)}</code>`;
    }
  };
  md.inline.ruler.before("escape", "math_inline", (state, silent) => {
    const rest = state.src.slice(state.pos);
    const open = ["\\(", "\\[", "$$", "$"].find(x => rest.startsWith(x));
    if (!open || (open === "$" && /\s/.test(rest[1] || " "))) return false;
    const close = ({"\\(": "\\)", "\\[": "\\]"})[open] || open;
    const end = state.src.indexOf(close, state.pos + open.length);
    if (end < 0 || state.src.slice(state.pos, end).includes("\n")) return false;
    if (open === "$" && (/\s/.test(state.src[end - 1]) || /\d/.test(state.src[end + 1] || ""))) return false;
    if (!silent) state.push("math_inline", "math", 0).content = state.src.slice(state.pos + open.length, end);
    state.pos = end + close.length;
    return true;
  });
  md.block.ruler.before("fence", "math_block", (state, start, end, silent) => {
    const first = state.bMarks[start] + state.tShift[start];
    const line = state.src.slice(first, state.eMarks[start]);
    const open = line.startsWith("$$") ? "$$" : line.startsWith("\\[") ? "\\[" : null;
    if (!open) return false;
    const close = open === "$$" ? "$$" : "\\]";
    let last = start, text = line.slice(2);
    while (true) {
      const closing = text.indexOf(close);
      if (closing >= 0) {
        if (text.slice(closing + close.length).trim()) return false;
        break;
      }
      if (++last >= end) return false;
      text += "\n" + state.getLines(last, last + 1, state.blkIndent, false);
    }
    if (silent) return true;
    const token = state.push("math_block", "math", 0);
    token.block = true;
    token.content = text.trimEnd().slice(0, -2);
    token.map = [start, last + 1];
    state.line = last + 1;
    return true;
  });
  md.renderer.rules.math_inline = md.renderer.rules.math_block = render;
}

export function renderReport(md, target, toc, report, onCitation, onCopy) {
  const citations = new Map((report.citations || []).map(c => [c.number, c]));
  const prefix = "epivra-citation-" + crypto.randomUUID() + "-";
  const chars = Array.from(report.text), parts = [];
  let end = 0;
  for (const mark of report.citation_marks || []) {
    parts.push(chars.slice(end, mark.start).join(""), `[${prefix}${mark.number}]`);
    end = mark.end;
  }
  parts.push(chars.slice(end).join(""));
  if (!md.__epivraCitations) {
  md.__epivraCitations = true;
  md.inline.ruler.before("link", "bound_citation", (state, silent) => {
    const prefix = state.env.epivraCitationPrefix;
    if (!prefix || state.linkLevel) return false;
    const start = "[" + prefix;
    if (!state.src.startsWith(start, state.pos)) return false;
    const end = state.src.indexOf("]", state.pos + start.length);
    const number = state.src.slice(state.pos + start.length, end);
    if (end < 0 || !/^\d+$/.test(number)) return false;
    if (!silent) {
      const link = state.push("link_open", "a", 1);
      link.attrSet("href", "#" + prefix + number);
      state.push("text", "", 0).content = `[${number}]`;
      state.push("link_close", "a", -1);
    }
    state.pos = end + 1;
    return true;
  });
  }
  const tokens = md.parse(parts.join(""), {epivraCitationPrefix: prefix});
  let heading = 0;
  const headings = [];
  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];
    if (token.type === "heading_open") {
      const id = "report-section-" + ++heading;
      token.attrSet("id", id);
      headings.push({ id, level: token.tag, text: tokens[i + 1]?.content || "" });
    }

  }
  target.innerHTML = md.renderer.render(tokens, md.options, {});
  for (const link of target.querySelectorAll("a")) {
    link.target = "_blank"; link.rel = "noopener noreferrer";
  }
  for (const link of target.querySelectorAll(`a[href^="#${prefix}"]`)) {
    const number = Number(link.getAttribute("href").slice(prefix.length + 1));
    const button = document.createElement("button");
    button.className = "citation"; button.textContent = `[${number}]`;
    button.setAttribute("aria-label", t("查看引用 {0}", number));
    button.onclick = () => onCitation(citations.get(number));
    link.replaceWith(button);
  }
  toc.replaceChildren();
  for (const h of headings) {
    const link = document.createElement("a");
    link.href = "#" + h.id; link.textContent = target.querySelector("#" + h.id)?.textContent || h.text; link.className = h.level;
    link.onclick = event => {
      event.preventDefault();
      const section = document.getElementById(h.id);
      section.tabIndex = -1; section.focus({preventScroll: true}); section.scrollIntoView({block: "start"});
    };
    toc.append(link);
  }
  for (const table of target.querySelectorAll("table")) {
    const wrapper = document.createElement("div"); wrapper.className = "table-wrap";
    table.before(wrapper); wrapper.append(table);
    const copy = document.createElement("button");
    copy.className = "copy-table"; copy.textContent = t("复制表格");
    copy.onclick = () => onCopy(Array.from(table.rows, row => Array.from(row.cells, cell => cell.innerText.replace(/\t|\n/g, " ")).join("\t")).join("\n"));
    wrapper.prepend(copy);
  }
}

export function standalone(target, title, ref) {
  const copy = target.cloneNode(true);
  copy.querySelectorAll(".copy-table").forEach(e => e.remove());
  copy.querySelectorAll(".citation").forEach(e => e.replaceWith(document.createTextNode(e.textContent)));
  const escape = s => String(s).replace(/[&<>\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  return `<!doctype html><html lang="${document.documentElement.lang}"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="epivra-report" content="${escape(ref)}"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>${escape(title)}</title><style>body{max-width:880px;margin:40px auto;padding:0 24px;color:#26352e;font:16px/1.8 'Microsoft YaHei',serif}h1,h2,h3{line-height:1.35;break-after:avoid}h2{margin-top:2em}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #dce3da;padding:8px;overflow-wrap:anywhere}th{background:#edf3ec}a{color:#1d5545;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f1;padding:16px}blockquote{border-left:3px solid #91b2a0;margin-left:0;padding-left:20px}math[display=block]{overflow-x:auto;margin:1em 0}.align-right{text-align:right}.align-center{text-align:center}.align-left{text-align:left}@page{size:A4;margin:20mm}@media print{body{margin:0;padding:0;max-width:none}tr{break-inside:avoid}}</style><article>${copy.innerHTML}</article></html>`;
}
