import { t, localized, language, setLanguage } from "./i18n.js";
import { addMath, renderReport, standalone, markdownReport } from "./reader.js";
/* The browser presents Host facts. It owns no research state machine. */
"use strict";
const $ = (id) => document.getElementById(id);
const labels = localized({
  openai: "OpenAI",
  claude: "Claude",
  gemini: "Gemini",
  grok: "Grok",
  deepseek: "DeepSeek",
  qwen: "通义千问",
  kimi: "Kimi",
  glm: "智谱 GLM",
  doubao: "豆包",
  minimax: "MiniMax",
  hunyuan: "腾讯混元",
  ernie: "百度文心",
  tavily: "Tavily",
  exa: "Exa",
  brave: "Brave",
  perplexity: "Perplexity",
  bocha: "博查",
  duckduckgo: "DuckDuckGo",
  jina: "Jina Reader",
  pubmed: "PubMed",
  crossref: "Crossref",
  europe_pmc: "Europe PMC",
  world_bank: "World Bank",
});
const coverageLabels = localized({
  text_extracted_not_reviewed: "已提取正文 · 尚未核查",
  text_extracted: "已提取正文",
  table_extracted_not_reviewed: "已提取表格 · 尚未核查",
  structure_extracted_not_reviewed: "已提取结构 · 尚未核查",
  partial_extraction: "部分提取，请留意缺失内容",
  needs_ocr_or_visual_review: "需要 OCR 或视觉解读",
  computed_not_reviewed: "计算产物 · 尚未核查",
  mcp_output_not_reviewed: "外部工具资料 · 尚未核查",
});
const roles = localized({
  lead: "研究主体",
  investigator: "调查",
  synthesizer: "冲突核实",
  writer: "写作",
  reviewer: "编辑核查",
});
const fragment = new URLSearchParams(location.hash.slice(1));
if (fragment.has("token")) {
  sessionStorage.setItem("research-token", fragment.get("token"));
  history.replaceState(null, "", location.pathname);
}
const token = sessionStorage.getItem("research-token") || "";
window.addEventListener("hashchange", () => {
  if (new URLSearchParams(location.hash.slice(1)).has("token"))
    location.reload();
});
const md = window.markdownit({
  html: false,
  linkify: false,
  typographer: false,
});
addMath(md);
// Emit classes rather than inline styles so strict CSP also preserves alignment.
for (const tag of ["th_open", "td_open"]) {
  md.renderer.rules[tag] = (tokens, index, options, env, renderer) => {
    const cell = tokens[index],
      style = cell.attrGet("style") || "";
    cell.attrs = (cell.attrs || []).filter(([name]) => name !== "style");
    const match = /^text-align:(left|right|center)$/.exec(style);
    if (match) cell.attrSet("class", "align-" + match[1]);
    return renderer.renderToken(tokens, index, options);
  };
}
md.renderer.rules.image = (tokens, index) => {
  const image = tokens[index], alt = md.utils.escapeHtml(image.content || t("图片"));
  const src = md.utils.escapeHtml(image.attrGet("src") || "");
  return `<span class="muted">${alt} — ${src}</span>`;
};
let mcpLoaded = false;
let config,
  active = null,
  status = null,
  tab = "progress",
  report = null;
let materials = [],
  approval = null,
  steering = null,
  mutating = false,
  listSerial = 0,
  statusSerial = 0;

function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}
function notice(text) {
  $("notice").replaceChildren(node("span", text));
  const close = node("button", "×", "icon");
  close.setAttribute("aria-label", t("关闭提示"));
  close.onclick = () => {
    $("notice").hidden = true;
  };
  $("notice").append(close);
  $("notice").hidden = false;
}
async function api(path, data, raw = false) {
  const headers = { "X-Research-Token": token, "X-Epivra-Language": language };
  if (data !== undefined && !raw) headers["Content-Type"] = "application/json";
  let response;
  try {
    response = await fetch(path, {
      method: data === undefined ? "GET" : "POST",
      headers,
      body: data === undefined ? undefined : raw ? data : JSON.stringify(data),
      cache: "no-store",
    });
  } catch {
    throw new Error(
      t("与本地工作台的连接中断。操作可能已被宿主接收，请刷新状态，不要重复创建或提交。"),
    );
  }
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || t("操作未完成。"));
  return result;
}
const call = (action, fields = {}) =>
  api("/api/command", { action, ...fields });
const studyActions = new Set(["approve", "plan-approve", "pause-resume", "steer", "cancel", "delete-study", "supplement", "reload-keys"]);
function renderActions() {
  for (const id of studyActions) {
    const button = $(id);
    if (button) button.disabled = mutating || !active || !status?.control;
  }
}
async function act(button, work, feedback) {
  if (mutating || (studyActions.has(button?.id) && (!active || !status?.control))) return;
  mutating = true;
  renderActions();
  if (button) button.disabled = true;
  try {
    await work();
  } catch (e) {
    notice(e.message);
    if (feedback) $(feedback).textContent = e.message;
  } finally {
    mutating = false;
    if (button) button.disabled = false;
    renderActions();
  }
}
function markdown(target, text) {
  target.innerHTML = md.render(text || "");
  for (const link of target.querySelectorAll("a")) {
    link.rel = "noopener noreferrer";
    link.target = "_blank";
  }
}
function stage(s) {
  if (s.deleting) return t("正在删除");
  if (s.cancelled) return t("已取消");
  if (s.published) return t("已完成");
  if (s.error) return t("需要处理");
  if (s.paused) return t("已暂停");
  if (!s.approved) return s.plans?.length ? t("策略待审批") : t("正在准备策略");
  return s.running ? t("研究中") : t("等待接续");
}
function options(id, values, selected, names = labels) {
  $(id).replaceChildren(
    ...values.map((v) => {
      const o = node("option", names[v] || v);
      o.value = v;
      return o;
    }),
  );
  if (selected && values.includes(selected)) $(id).value = selected;
}
function selectTab(name) {
  if (name !== "report") setReader(false);
  tab = name;
  for (const button of document.querySelectorAll("[data-tab]")) {
    const selected = button.dataset.tab === name;
    button.setAttribute("aria-selected", String(selected));
    $(`${button.dataset.tab}-panel`).hidden = !selected;
  }
  if (active) loadPanel().catch((e) => notice(e.message));
}
async function refreshList() {
  const serial = ++listSerial;
  const data = await call("overview");
  if (serial !== listSerial) return;
  const signature = JSON.stringify([
    language,
    active,
    data.studies.map((s) => [s.study, s.request, stage(s)]),
  ]);
  if ($("studies").dataset.signature === signature) return;
  $("studies").dataset.signature = signature;
  $("studies").replaceChildren();
  if (!data.studies.length) $("studies").append(node("p", t("暂无研究"), "muted"));
  for (const s of data.studies) {
    const button = node(
      "button",
      undefined,
      "study-link" + (s.study === active ? " selected" : ""),
    );
    button.append(node("strong", s.request), node("small", stage(s)));
    button.title = s.request;
    button.dataset.study = s.study;
    button.onclick = () => {
      if (!mutating) openStudy(s.study).catch((e) => notice(e.message));
    };
    $("studies").append(button);
  }
}
async function openStudy(id) {
  setReader(false);
  $("source-dialog").close();
  sourceRead++;
  statusSerial++;
  active = id;
  for (const button of document.querySelectorAll(".study-link")) {
    button.classList.toggle("selected", button.dataset.study === id);
  }
  status = report = null;
  renderActions();
  materialsKey = "";
  sessionStorage.setItem("research-study", id);
  $("welcome").hidden = true;
  $("study-view").hidden = false;
  $("study-title").textContent = t("正在读取研究…");
  $("breadcrumb").textContent = t("工作台 / 我的研究");
  $("report-text").replaceChildren();
  $("report-sources").replaceChildren();
  $("source-list").replaceChildren();
  selectTab("progress");
  await refreshStudy();
  await refreshList();
}
function renderStatus(s) {
  const previous = status;
  status = s;
  renderActions();
  if (previous?.direction !== s.direction) {
    sourceRead++;
    $("source-dialog").close();
    $("work-list").replaceChildren();
    $("work-list").dataset.signature = "";
  }
  renderPlan(s);
  $("study-title").textContent = s.request;
  $("study-stage").textContent = stage(s);
  $("study-meta").textContent =
    t("{0} / {1} · 资料 {2} 份 · {3}", labels[s.policy.provider] || s.policy.provider, s.policy.model, s.source_count, s.policy.network ? t("允许联网") : t("本地资料与授权工具"));
  const elapsed = s.timing?.elapsed_seconds;
  if (s.approved) {
    const duration = typeof elapsed === "number"
      ? t("{0}小时 {1}分 {2}秒", Math.floor(elapsed / 3600), Math.floor(elapsed / 60) % 60, Math.floor(elapsed) % 60)
      : t("未记录");
    $("study-meta").textContent += " · " + t("研究耗时：{0}", duration);
    $("study-meta").title = t("从首次批准策略到交付的总经过时间，包含暂停、等待与离线时间。");
  } else $("study-meta").title = "";
  $("blocker").hidden =
    !s.error && !s.analysis_cleanup_error && !s.unsettled_operations?.length;
  $("blocker").textContent = s.unsettled_operations?.length
    ? t("存在返回结果未知的调用，系统不会自动重发。请暂停后通过 CLI 对账入口，依据供应商的真实结果处理。")
    : s.error === "RepeatedFailure"
      ? t("连续重复相同错误且没有进展，已停止自动尝试。请检查失败步骤，调整方法或补充资料后再恢复。")
    : s.error
      ? t("研究暂时阻断：{0}。可暂停后检查连接设置，更新密钥并重新载入。", s.error)
      : s.analysis_cleanup_error
        ? t("分析容器清理需要处理，请检查 Docker 状态。")
        : "";
  $("approve").hidden = s.cancelled || s.approved || !s.plans?.length;
  $("pause-resume").hidden = s.cancelled || s.published;
  $("pause-resume").textContent = s.paused ? t("继续研究") : t("暂停研究");
  $("steer").hidden = s.cancelled;
  $("cancel").hidden = s.cancelled || s.published;
  $("delete-study").textContent = s.deleting ? t("重试删除")
    : s.published || s.cancelled ? t("删除研究") : t("终止并删除");
  $("supplement").hidden = $("reload-keys").hidden =
    s.cancelled || !s.paused || s.running;
  let message = s.cancelled
    ? t("研究已取消，已有资料与成果仍保留。")
    : s.published
      ? t("研究已完成，报告与引用已保存。")
      : !s.approved && s.plans?.length
        ? s.paused
          ? t("初始策略已准备好。研究当前暂停，审批后仍需选择继续研究。")
          : t("初始策略已准备好。阅读并审批后，Epivra 会自主研究并交付最终成果。")
        : s.paused
          ? t("研究保持暂停。可补充资料或修改连接设置，再决定继续。")
          : t("Epivra 正在后台研究。可以关闭页面，保持本机运行，稍后回来查看成果；也可以主动暂停或调整方向。");
  $("progress-summary").replaceChildren(
    node("strong", stage(s)),
    node("p", message, "muted"),
  );
  if (tab === "progress") loadProgress().catch(e => notice(e.message));
  renderUsage(s.usage || []);
  if (tab === "materials") loadPanel().catch(e => notice(e.message));
  if (
    !previous ||
    previous.control !== s.control ||
    previous.published !== s.published
  ) {
    report = null;
    $("report-tools").hidden = true;
    $("report-toc").replaceChildren();
    $("report-source-panel").hidden = true;
    $("report-text").replaceChildren(
      node("p", t("当前方向尚无已发布报告。"), "muted"),
    );
    $("report-sources").replaceChildren();
    if (s.published && !previous?.published) selectTab("report");
    else if (tab === "report") loadPanel().catch((e) => notice(e.message));
  }
}
const statusReads = new Map();
async function refreshStudy(fresh = false) {
  const id = active,
    serial = ++statusSerial;
  if (!id) return;
  if (fresh || !statusReads.has(id)) {
    const pending = call("status", { study: id }).finally(() => {
      if (statusReads.get(id) === pending) statusReads.delete(id);
    });
    statusReads.set(id, pending);
  }
  let s;
  try {
    s = await statusReads.get(id);
  } catch (error) {
    if (active !== id || serial !== statusSerial) return;
    throw error;
  }
  if (active === id && serial === statusSerial) renderStatus(s);
}
function renderUsage(groups) {
  const signature = JSON.stringify([language, groups]);
  if ($("usage-list").dataset.signature === signature) return;
  $("usage-list").dataset.signature = signature;
  $("usage-list").replaceChildren();
  if (!groups.length)
    $("usage-list").append(node("p", t("暂无调用用量。"), "muted"));
  const providers = new Map();
  for (const group of groups) {
    if (!providers.has(group.resource)) providers.set(group.resource, []);
    providers.get(group.resource).push(group);
  }
  for (const entries of providers.values()) {
    const functions = {
      web_search: t("网页搜索"), fetch_web: t("网页提取"),
      search_pubmed: t("文献检索"), read_pubmed: t("文献读取"),
      search_crossref: t("文献检索"), search_europe_pmc: t("文献检索"),
      world_bank_indicators: t("指标查询"), query_world_bank: t("数据查询"),
    };
    const provider = entries[0].resource.replace(/^public:/, "");
    const card = node("div", undefined, "card usage-card");
    const total = (key) => entries.reduce((sum, g) => sum + (g[key] || 0), 0);
    const counts = [t("{0} 次调用", total("calls"))];
    if (total("unresolved_calls")) counts.push(t("{0} 次未知结果", total("unresolved_calls")));
    if (total("http_error_calls")) counts.push(t("{0} 次 HTTP 错误", total("http_error_calls")));
    card.append(
      node("strong", (labels[provider] || provider) + (entries.length === 1 && entries[0].model ? " / " + entries[0].model : "")),
      node("p", counts.join(" · "), "muted"),
    );
    const metrics = node("div", undefined, "usage-metrics");
    const groupSizes = [];
    for (const g of entries) {
      const before = metrics.childElementCount;
      const name = g.model || functions[g.tool] || g.tool || t("工具调用");
      if (entries.length > 1 || (!g.model && !Object.values(g.totals).some(v => v != null))) {
        const count = node("div");
        count.append(node("strong", g.calls.toLocaleString()), node("small", t("{0}次数", name)));
        metrics.append(count);
      }
      for (const [key, label] of Object.entries({
        input_tokens: t("输入 tokens"),
        output_tokens: t("输出 tokens"),
        total_tokens: t("总 tokens"),
        cache_read_tokens: t("缓存命中 tokens"),
        cache_write_tokens: t("缓存写入 tokens"),
        reasoning_tokens: t("推理 tokens（子项）"),
        search_credits: t("服务 credits"),
        reader_tokens: t("读取 tokens"),
        cost_usd: t("供应商费用参考（USD）"),
      })) {
        const value = g.totals[key];
        if (value == null) continue;
        if (key === "total_tokens" && (g.totals.input_tokens != null || g.totals.output_tokens != null)) continue;
        const metric = node("div");
        metric.append(
          node("strong", value.toLocaleString(undefined, {maximumFractionDigits: 8})),
          node("small", entries.length > 1
            ? (key === "search_credits" ? name + " credits" : name + " · " + label)
            : label),
        );
        const reported = g.reported_calls?.[key];
        if (reported != null && reported < g.calls)
          metric.append(node("small", t("已返回用量：{0}/{1} 次调用", reported, g.calls), "muted"));
        metrics.append(metric);
      }
      groupSizes.push(metrics.childElementCount - before);
    }
    if (entries.every(g => !g.model)) {
      if (groupSizes.length === 2 && groupSizes.every(size => size === 2))
        metrics.className = "usage-metrics usage-paired";
      else if (metrics.childElementCount <= 2)
        metrics.className = "usage-metrics usage-compact";
    }
    if (metrics.childElementCount) card.append(metrics);
    else card.append(node("p", t("此接口未返回计量数据，仅记录调用次数。"), "muted"));
    $("usage-list").append(card);
  }
}
function sourceRows(target, sources, id, previewable = true) {
  target.replaceChildren();
  if (!sources.length) target.append(node("p", t("暂无资料。"), "muted"));
  for (const [index, s] of sources.entries()) {
    const row = node("div", undefined, "source-row"),
      detail = node("div");
    const origin =
      typeof s.origin === "string"
        ? s.origin
        : JSON.stringify(s.origin || s.name || s.ref);
    detail.append(
      node("div", target.id === "source-list" ? `${index + 1}. ${s.title || s.name || origin}` : s.title || s.name || origin),
      node("small", coverageLabels[s.coverage] || t("资料原件"), "muted"),
    );
    if (/^https?:\/\//i.test(origin)) {
      const link = node("a", t("打开来源 ↗"), "text-button");
      link.href = origin;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      detail.append(link);
    }
    const download = node("button", t("下载原件 ↓"));
    download.onclick = () =>
      act(download, () => downloadSource(id, s.ref, s.name || origin));
    const preview = node("button", t("查看正文"));
    preview.onclick = () => showSource(id, s).catch(e => notice(e.message));
    const actions = node("div", undefined, "button-row");
    if (previewable) actions.append(preview);
    actions.append(download);
    row.append(detail, actions);
    target.append(row);
  }
}
let materialsPending = null, materialsKey = "";
async function loadPanel() {
  const id = active,
    control = status?.control,
    selected = tab;
  if (!id || !control) return;
  if (selected === "report") {
    if (!report && status.published) {
      const result = await call("report", { study: id });
      if (id !== active || control !== status?.control || tab !== selected)
        return;
      report = result;
      if (result.text) {
        renderReader();
      } else
        $("report-text").textContent = t("当前方向尚无已发布报告，请刷新状态。");
    }
    sourceRows(
      $("analysis-files"),
      (status.analyses || []).flatMap((a) => a.files || []),
      id,
    );
  } else if (selected === "materials") {
    const key = JSON.stringify([id, control, status.source_count, language]);
    if (materialsKey === key) return;
    if (materialsPending?.key === key) return materialsPending.promise;
    const promise = (async () => {
      const result = await call("sources", { study: id });
      if (key === JSON.stringify([active, status?.control, status?.source_count, language]) && tab === selected) {
        sourceRows($("source-list"), result.sources, id);
        materialsKey = key;
      }
    })().finally(() => { if (materialsPending?.promise === promise) materialsPending = null; });
    materialsPending = {key, promise};
    return promise;
  } else if (selected === "progress") {
    await loadProgress();
  }
}

function renderPlan(s) {
  const signature = JSON.stringify([language, s.direction, s.approved, s.plans]);
  if ($("plan-text").dataset.signature === signature) return;
  $("plan-text").dataset.signature = signature;
  const plan = s.plans?.find(p => p.ref === s.approved_plan) || s.plans?.at(-1);
  $("plan-state").textContent = !plan ? t("当前方向的方案") : s.approved ? t("已批准的研究方案") : t("待审批的研究方案");
  $("plan-approve").hidden = !plan || s.approved || s.cancelled;
  if (plan) renderPlanBody($("plan-text"), plan);
  else $("plan-text").replaceChildren(node("p", s.approved
    ? t("当前方向尚未保存新方案；已批准的研究授权继续有效。")
    : t("方案生成后将保留在这里，研究期间与完成后均可查看。"), "muted"));
}
let progressPending = null, progressRead = 0, sourceRead = 0;
async function loadProgress() {
  const id = active, direction = status?.direction;
  if (!id || !status || tab !== "progress") return;
  const key = id + direction;
  if (progressPending?.key === key) return progressPending.promise;
  const serial = ++progressRead;
  const promise = (async () => {
    let result;
    try { result = await call("progress", {study: id}); }
    catch (error) {
      if (serial === progressRead && id === active && direction === status?.direction && tab === "progress") {
        $("work-list").dataset.signature = "";
        $("work-list").replaceChildren(node("p", t("进度读取失败，请刷新重试。若刚更新程序，请确认后台研究宿主也已更新。"), "alert"));
      }
      throw error;
    }
    if (serial !== progressRead || id !== active || direction !== status?.direction || tab !== "progress") return;
    const signature = JSON.stringify([language, id, result]);
    if ($("work-list").dataset.signature === signature) return;
    const existing = new Map(Array.from($("work-list").querySelectorAll("details"), el => [el.dataset.ref, el]));
    const opened = new Set(Array.from(existing.values()).filter(el => el.open).map(el => el.dataset.ref));
    $("work-list").dataset.signature = signature;
    $("work-list").replaceChildren();
    const states = {cancelled:t("已取消"), delivered:t("已交付"), blocked:t("需要处理"), clarification:t("等待负责人澄清"), waiting:t("等待依赖成果"), pending:t("已安排，尚未交付")};
    if (result.research) {
      const panel = node("section", undefined, "work-card card"), research = result.research;
      panel.append(node("strong", t("研究依据与文稿")));
      panel.append(node("p", t("当前记录：{0} 项研究判断，{1} 项分歧核实。", research.findings.length, research.conflicts.length), "muted"));
      if (research.pending_inputs?.length) panel.append(node("p", t("有 {0} 批新输入待评估。", research.pending_inputs.length), "muted"));
      for (const question of research.questions || []) {
        const entry = node("details", "", "research-question");
        const state = {continue: t("待继续"), ready: t("可以写作"), limited: t("有明确限制")}[question.decision] || t("尚未评估");
        entry.append(node("summary", `${question.question} — ${state}`));
        if (question.answer_target) entry.append(node("p", question.answer_target));
        if (question.reason) entry.append(node("p", question.reason));
        for (const gap of question.remaining || []) entry.append(node("p", `${gap.question}: ${gap.reason}`));
        panel.append(entry);
      }
      panel.append(node("p", t("调查状态由研究主体评估，不代表资料完整性认证。"), "muted"));
      const basisText = !research.basis ? t("仍在形成写作依据")
        : research.basis.stale ? t("依据已变化，需要重新评估写作准备")
        : t("研究主体已记录写作准备判断；这不是自动正确性认证");
      panel.append(node("p", basisText));
      if (result.manuscript) panel.append(node("small", result.manuscript.state === "published"
        ? t("当前文稿已交付") : t("当前稿件持续编辑中，尚未交付"), "muted"));
      $("work-list").append(panel);
    }
    if (!result.work.length) $("work-list").append(node("p", t("尚未分配调查工作。"), "muted"));
    for (const w of result.work) {
      const signature = JSON.stringify([language, w]);
      const prior = existing.get(w.ref);
      if (prior?.dataset.signature === signature) { $("work-list").append(prior); continue; }
      const row = node("details", undefined, "work-card card"), summary = node("summary");
      row.dataset.ref = w.ref;
      row.dataset.signature = signature;
      summary.append(node("span", roles[w.role] || w.role, "work-role"), node("strong", w.task), node("small", states[w.state], "badge"));
      const body = node("div", undefined, "work-body markdown");
      row.append(summary, body);
      let loaded = false;
      row.ontoggle = async () => {
        if (!row.open || loaded) return;
        loaded = true;
        body.replaceChildren(node("p", t("正在读取阶段成果…"), "muted"));
        try {
          const detail = await call("work_detail", {study: id, work: w.ref});
          if (id !== active || direction !== status?.direction || !row.isConnected) return;
          body.replaceChildren();
          if (w.question) body.append(node("p", w.question, "alert"));
          if (w.error) body.append(node("p", w.error, "alert"));
          if (!detail.entries.length) body.append(node("p", t("尚无公开阶段成果；交付后可在这里查看。"), "muted"));
          for (const entry of detail.entries) {
            const section = node("section");
            markdown(section, entry.text);
            if (entry.answer_target) section.append(node("p", entry.answer_target));
            for (const check of entry.checks || []) section.append(node("p", `${check.angle}: ${check.reason}`));
            for (const gap of entry.remaining || []) section.append(node("p", `${gap.question}: ${gap.reason}`));
            if (entry.quote) section.append(node("blockquote", entry.quote));
            for (const condition of entry.conditions || []) section.append(node("p", t("成立条件：{0}", condition), "muted"));
            for (const limit of entry.limits || []) section.append(node("p", t("资料限制：{0}", limit), "muted"));
            if (typeof entry.accepted === "boolean") section.prepend(node("strong", entry.accepted ? t("该版本核查通过") : t("该版本需要修订")));
            if (entry.report) section.append(node("small", t("对应报告：{0}", entry.report), "muted"));
            for (const issue of entry.defects || []) section.append(node("p", issue, "alert"));
            for (const comment of entry.comments || []) section.append(node("p", comment));
            body.append(section);
          }
        } catch (e) { loaded = false; body.textContent = e.message; }
      };
      $("work-list").append(row);
      row.open = opened.has(w.ref);
    }
  })().finally(() => { if (progressPending?.promise === promise) progressPending = null; });
  progressPending = {key, promise};
  return promise;
}

function setReader(expanded) {
  document.body.classList.toggle("reading", expanded);
  $("reader-toggle").textContent = expanded ? t("退出展开阅读") : t("展开阅读");
  $("reader-toggle").setAttribute("aria-pressed", String(expanded));
}
function renderReader() {
  renderReport(md, $("report-text"), $("report-toc"), report, citation => {
    const source = report.sources.find(s => s.ref === citation.source);
    if (source) showSource(active, source, citation).catch(e => notice(e.message));
  }, copyText);
  $("report-text").append(node("p", "Epivra · " + report.ref, "print-provenance"));
  $("report-tools").hidden = false;
  const sources = (report.sources || []).map(s => {
    const citation = report.citations?.find(c => c.source === s.ref);
    return {...s, title: citation ? `[${citation.number}] ${s.title || s.name || s.origin || t("资料原件")}` : s.title};
  });
  sourceRows($("report-sources"), sources, active);
}
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); notice(t("已复制。")); }
  catch { notice(t("复制失败，请选择正文后手动复制。")); }
}
async function showSource(id, source, citation = null) {
  const serial = ++sourceRead, direction = status?.direction;
  const target = $("source-detail");
  $("source-title").textContent = citation ? t("引用 {0}", citation.number) : t("来源详情");
  target.replaceChildren(node("p", t("正在读取资料…"), "muted"));
  if (!$("source-dialog").open) $("source-dialog").showModal();
  const start = Math.max(0, (citation?.quotes?.[0]?.offset || 0) - 300);
  let pageRead = 0;
  async function page(offset) {
    const pageSerial = ++pageRead;
    const data = await call("source_text", {study:id, source:source.ref, offset});
    if (pageSerial !== pageRead || serial !== sourceRead || id !== active || direction !== status?.direction || !$("source-dialog").open) return;
    target.replaceChildren();
    const rows = node("div"); sourceRows(rows, [source], id, false);
    target.append(rows, node("p", coverageLabels[data.coverage] || data.coverage || t("资料原件"), "muted"));
    for (const quote of citation?.quotes || []) target.append(node("blockquote", quote.text, "source-quote"));
    target.append(node("p", t("提取正文 · 字符 {0}–{1} / {2}", data.offset, data.next_offset, data.total), "muted"));
    const text = node("pre", data.text || t("未保存可预览正文，请下载原件。"), "source-text");
    target.append(text);
    const nav = node("div", undefined, "button-row");
    for (const [label, offset, disabled] of [[t("上一页"), Math.max(0, data.offset-12000), data.offset===0], [t("下一页"), data.next_offset, data.next_offset>=data.total]]) {
      const button = node("button", label); button.disabled = disabled;
      button.onclick = () => page(offset).catch(e => notice(e.message)); nav.append(button);
    }
    target.append(nav);
  }
  await page(start);
}
$("reader-toggle").onclick = () => setReader(!document.body.classList.contains("reading"));
document.addEventListener("keydown", e => { if (e.key === "Escape" && !document.querySelector("dialog[open]")) setReader(false); });
$("sources-toggle").onclick = () => {
  $("report-source-panel").hidden = !$("report-source-panel").hidden;
  $("sources-toggle").setAttribute("aria-expanded", String(!$("report-source-panel").hidden));
};
$("copy-report").onclick = () => { if (report) copyText(report.text); };
$("refresh-progress").onclick = () => loadProgress().catch(e => notice(e.message));
$("plan-approve").onclick = () => $("approve").click();
function saveBlob(blob, name) {
  const url = URL.createObjectURL(blob),
    link = node("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
async function downloadSource(id, ref, name) {
  const response = await fetch("/api/file", {
    method: "POST",
    headers: { "X-Research-Token": token, "X-Epivra-Language": language, "Content-Type": "application/json" },
    body: JSON.stringify({ study: id, source: ref }),
  });
  if (!response.ok)
    throw new Error((await response.json()).error || t("资料下载失败。"));
  const blob = await response.blob();
  let filename = String(name)
    .split(/[\\/]/)
    .pop()
    .split("?")[0]
    .replace(/[<>:"|?*\x00-\x1f]/g, "_");
  saveBlob(blob, filename || t("研究资料.bin"));
}
const control = (id, expected, command, payload = {}) =>
  call("control", {
    study: id,
    expected,
    command,
    payload,
    command_id: crypto.randomUUID(),
  });
async function afterControl(id) {
  if (active === id) await refreshStudy(true);
  await refreshList();
}

function renderMaterials() {
  $("selected-materials").replaceChildren();
  materials.forEach((m, i) => {
    const li = node("li"),
      remove = node("button", t("移除"), "text-button");
    li.append(
      node(
        "span",
        `${m.kind === "folder" ? t("授权文件夹及子目录") : t("导入文件")} · ${m.path || m.file.name}`,
      ),
    );
    remove.type = "button";
    remove.onclick = () => {
      materials.splice(i, 1);
      renderMaterials();
    };
    li.append(remove);
    $("selected-materials").append(li);
  });
}
function addMaterial(item) {
  if (
    !materials.some((m) =>
      item.path
        ? m.path === item.path && m.kind === item.kind
        : m.file === item.file,
    )
  )
    materials.push(item);
  renderMaterials();
}
async function importMaterial(id, expected, item) {
  if (item.file) {
    if (item.file.size > config.max_upload)
      throw new Error(
        t("此文件超过浏览器上传上限，请使用系统选择或本地路径导入。"),
      );
    const params = new URLSearchParams({
      study: id,
      expected,
      name: item.file.name,
    });
    return api("/api/upload?" + params, item.file, true);
  }
  return call("import_file", { study: id, expected, path: item.path });
}
function importResult(r) {
  return t("已导入 · {0} 字符 · {1}{2}", r.characters, coverageLabels[r.coverage] || t("资料已保存"), r.issues?.length ? "；" + r.issues.join("；") : "");
}
$("scope").onchange = () => {
  $("material-panel").hidden = $("scope").value === "web";
};
for (const kind of ["file", "folder"])
  $("pick-" + kind).onclick = () =>
    act($("pick-" + kind), async () => {
      const result = await api("/api/pick", { kind });
      if (result.path) addMaterial({ kind, path: result.path });
    });
$("add-path").onclick = () => {
  const path = $("material-path").value.trim().replace(/^"|"$/g, "");
  if (path) {
    addMaterial({ kind: $("path-kind").value, path });
    $("material-path").value = "";
  }
};
$("upload-files").onchange = (e) => {
  for (const file of e.target.files) addMaterial({ kind: "file", file });
  e.target.value = "";
};
$("create-form").onsubmit = (e) => {
  e.preventDefault();
  act($("create-button"), async () => {
    const request = $("request").value.trim(),
      scope = $("scope").value;
    const chosen = scope === "web" ? [] : [...materials];
    if (!request) throw new Error(t("请填写研究需求。"));
    const defaults = config.defaults;
    if (
      !config.providers.find((p) => p.id === (defaults.provider || "deepseek"))
        ?.configured
    )
      throw new Error(t("请先在连接与设置中保存研究模型密钥。"));
    if (scope === "local" && !chosen.length && !defaults.mcp_servers?.length)
      throw new Error(t("请至少选择文件、授权文件夹或启用资料 MCP。"));
    $("creation-hint").textContent = t("正在准备研究与资料…");
    // A lost create response is never automatically resent.
    let id;
    try {
      const created = await call("create", {
        ...defaults,
        text_encoding: $("text-encoding").value,
        request,
        web: scope !== "local",
        local_roots: chosen
          .filter((m) => m.kind === "folder")
          .map((m) => m.path),
      });
      id = created.study;
      const s = await call("status", { study: id });
      for (const item of chosen.filter((m) => m.kind === "file")) {
        $("creation-hint").textContent =
          t("正在导入 ") + (item.path || item.file.name);
        const result = await importMaterial(id, s.control, item);
        if (result.issues?.length) notice(importResult(result));
      }
      await control(id, s.control, "resume");
      materials = [];
      renderMaterials();
      $("request").value = "";
      await openStudy(id);
    } catch (error) {
      if (id) {
        await openStudy(id);
        throw new Error(
          t("研究已保留，请查看当前状态。若资料未全部导入，请在暂停草稿中补充后继续。") +
            error.message,
        );
      }
      await refreshList();
      throw error;
    } finally {
      $("creation-hint").textContent = t("生成策略会使用模型额度");
    }
  });
};
$("new-study").onclick = () => {
  if (mutating) return;
  setReader(false);
  sourceRead++;
  $("source-dialog").close();
  statusSerial++;
  active = null;
  status = report = null;
  sessionStorage.removeItem("research-study");
  $("welcome").hidden = false;
  $("study-view").hidden = true;
  $("breadcrumb").textContent = t("工作台 / 新建研究");
  refreshList().catch((e) => notice(e.message));
  $("request").focus();
};
$("refresh-list").onclick = () => refreshList().catch((e) => notice(e.message));
document.querySelector(".brand").onclick = (e) => {
  e.preventDefault();
  $("new-study").click();
};
for (const button of document.querySelectorAll("[data-tab]"))
  button.onclick = () => selectTab(button.dataset.tab);
$("open-help").onclick = () => $("help-dialog").showModal();
for (const button of document.querySelectorAll(".close-dialog"))
  button.onclick = () => button.closest("dialog").close();
$("approve").onclick = () => {
  if (!status?.plans?.length || mutating) return;
  const plan = status.plans.at(-1);
  approval = { id: active, expected: status.control, ref: plan.ref };
  renderPlanBody($("approval-text"), plan);
  $("approval-hint").textContent = status.paused
    ? t("研究当前暂停。批准策略不会自动恢复；之后选择继续研究开始执行。")
    : t("确认后，Epivra 将按此策略自主研究并交付成果，无需逐步确认。你仍可主动暂停或调整方向；若遇到额度不足等阻断，会提示你处理。");
  $("approval-dialog").showModal();
};
function renderPlanBody(target, plan) {
  markdown(target, plan.body.text);
  if (plan.body.brief) {
    target.append(node("h3", t("研究范围与问题")));
    const names = {
      subject: t("研究对象"),
      given_context: t("已知背景"),
      questions: t("研究问题"),
      material_scope: t("资料范围"),
    };
    for (const [key, value] of Object.entries(plan.body.brief)) {
      const p = node("p");
      p.append(node("strong", (names[key] || key) + "："));
      const modes = {
        case_materials: t("针对本案例的资料"),
        library: t("待检索的资料库"),
        unspecified: t("尚未指定"),
      };
      const display =
        typeof value === "string"
          ? value
          : Array.isArray(value)
            ? value.join("；")
            : value?.mode
              ? t("{0}；依据：{1}", modes[value.mode] || value.mode, value.basis || "")
              : JSON.stringify(value);
      p.append(document.createTextNode(display));
      target.append(p);
    }
  }
}
$("confirm-approval").onclick = () =>
  act($("confirm-approval"), async () => {
    const shown = approval;
    try {
      await control(shown.id, shown.expected, "approve", { plan: shown.ref });
    } finally {
      $("approval-dialog").close();
      await afterControl(shown.id);
    }
    if (status?.paused)
      notice(t("策略已批准，研究仍暂停。选择继续研究开始执行。"));
  });
$("pause-resume").onclick = () =>
  act($("pause-resume"), async () => {
    const id = active,
      s = status;
    await control(id, s.control, s.paused ? "resume" : "pause");
    await afterControl(id);
  });
$("steer").onclick = () => {
  if (!active || !status?.control || mutating) return;
  steering = { id: active, expected: status.control };
  $("steer-request").value = status.request;
  $("steer-dialog").showModal();
};
$("steer-form").onsubmit = (e) => {
  e.preventDefault();
  act(e.submitter, async () => {
    const shown = steering;
    const request = $("steer-request").value.trim();
    if (!request) throw new Error(t("请填写新的完整需求。"));
    try {
      await control(shown.id, shown.expected, "steer", { request });
    } finally {
      $("steer-dialog").close();
      await afterControl(shown.id);
    }
  });
};
$("cancel").onclick = () =>
  act($("cancel"), async () => {
    const id = active,
      expected = status.control;
    if (confirm(t("取消后不能恢复此研究。确定取消？"))) {
      await control(id, expected, "cancel");
      await afterControl(id);
    }
  });
$("delete-study").onclick = () =>
  act($("delete-study"), async () => {
    const id = active, expected = status.control;
    if (!confirm(t("删除将终止此研究并永久清除其报告、资料副本和过程记录。用户原文件、已导出文件及其他研究不受影响。已提交的外部调用可能仍产生费用。确认删除？"))) return;
    try {
      await call("delete", {study: id, expected, confirmed: true});
    } catch (error) {
      if (active === id) await refreshStudy(true).catch(() => {});
      throw error;
    }
    if (active === id) {
      statusSerial++;
      active = null;
      status = report = null;
      sessionStorage.removeItem("research-study");
      $("welcome").hidden = false;
      $("study-view").hidden = true;
      $("breadcrumb").textContent = t("工作台 / 新建研究");
    }
    await refreshList();
  });
$("reload-keys").onclick = () =>
  act($("reload-keys"), async () => {
    await call("reload", { study: active });
    notice(t("已重新载入密钥。研究配置不变，可继续接续研究。"));
  });
$("download-report").onclick = () => act($("download-report"), async () => {
  if (!report?.text) return;
  const saved = report, id = active, format = $("export-format").value;
  // Recheck the precise publication before exporting, including a control change
  // made by another client since the last background status refresh.
  await call("report", {study:id, expected:saved.ref});
  if (id !== active || report?.ref !== saved.ref) return;
  const name = t("研究报告") + "-" + saved.ref.slice(-8);
  if (format === "pdf") {
    window.print();
  } else if (format === "docx") {
    const response = await fetch("/api/report-export", {
      method:"POST", headers:{"X-Research-Token":token, "X-Epivra-Language":language, "Content-Type":"application/json"},
      body:JSON.stringify({study:id, expected:saved.ref}),
    });
    if (!response.ok) throw new Error((await response.json()).error || t("导出失败。"));
    saveBlob(await response.blob(), name + ".docx");
  } else {
    const text = format === "html" ? standalone($("report-text"), status.request, saved.ref) : markdownReport(saved);
    saveBlob(new Blob([text], {type:format === "html" ? "text/html;charset=utf-8" : "text/markdown;charset=utf-8"}), name + "." + format);
  }
});
let supplement = null;
$("supplement").onclick = () => {
  if (!active || !status?.control || mutating) return;
  supplement = { id: active, expected: status.control };
  $("supplement-feedback").textContent = "";
  $("supplement-dialog").showModal();
};
async function supplementFiles(items) {
  const selected = supplement;
  for (const item of items) {
    const result = await importMaterial(selected.id, selected.expected, item);
    $("supplement-feedback").textContent += importResult(result) + "\n";
  }
  await afterControl(selected.id);
}
$("supplement-native").onclick = () =>
  act(
    $("supplement-native"),
    async () => {
      const result = await api("/api/pick", { kind: "file" });
      if (result.path) await supplementFiles([{ path: result.path }]);
    },
    "supplement-feedback",
  );
$("supplement-import").onclick = () =>
  act(
    $("supplement-import"),
    () =>
      supplementFiles([
        { path: $("supplement-path").value.trim().replace(/^"|"$/g, "") },
      ]),
    "supplement-feedback",
  );
$("supplement-upload").onchange = (e) => {
  const items = Array.from(e.target.files, (file) => ({ file }));
  e.target.value = "";
  act(null, () => supplementFiles(items), "supplement-feedback");
};

async function loadConfig() {
  config = await api("/api/settings");
  $("text-encoding").value = config.defaults.text_encoding || "utf-8-sig";
  const p = config.providers.find(
    (p) => p.id === (config.defaults.provider || "deepseek"),
  );
  $("model-summary").textContent =
    `${labels[p.id]} / ${config.defaults.model || p.model}${p.configured ? "" : t(" · 未配置密钥")}`;
}
let modelCandidates = [],
  modelListSerial = 0,
  modelOptionIndex = -1;
function closeModels() {
  $("model-options").hidden = true;
  $("model").setAttribute("aria-expanded", "false");
  $("model").removeAttribute("aria-activedescendant");
}
function invalidateModels() {
  modelListSerial++;
  modelCandidates = [];
  closeModels();
  $("fetch-models").disabled = false;
  $("model-list-status").textContent =
    t("填写密钥后获取模型列表，也可手动输入完整型号。");
}
const modelMatch = (value) =>
  value.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
function renderModels(showAll = false) {
  const query = showAll ? "" : modelMatch($("model").value);
  const matches = modelCandidates.filter((m) =>
    modelMatch(m.id).includes(query),
  );
  $("model-options").replaceChildren();
  modelOptionIndex = -1;
  $("model").removeAttribute("aria-activedescendant");
  for (const [index, model] of matches.entries()) {
    const option = node("button", model.id, "model-option");
    option.type = "button";
    option.id = `model-option-${index}`;
    option.tabIndex = -1;
    option.setAttribute("role", "option");
    option.setAttribute("aria-selected", "false");
    option.onmousedown = (e) => e.preventDefault();
    option.onclick = () => {
      $("model").value = model.id;
      $("context-tokens").value = model.context_tokens || "";
      $("max-tokens").value = model.max_tokens || "";
      capacityFields();
      closeModels();
      $("model").focus();
      closeModels();
    };
    $("model-options").append(option);
  }
  if (!matches.length)
    $("model-options").append(
      node("p", t("没有匹配项，可输入完整型号。"), "muted"),
    );
  $("model-options").hidden = false;
  $("model").setAttribute("aria-expanded", "true");
}
async function fetchModels() {
  const serial = ++modelListSerial;
  modelCandidates = [];
  closeModels();
  $("fetch-models").disabled = true;
  $("model-list-status").textContent = t("正在获取模型列表…");
  try {
    const result = await api("/api/models", {
      provider: $("provider").value,
      region: $("region").value,
      key: $("model-key").value.trim(),
    });
    if (serial !== modelListSerial || !$("settings-dialog").open) return;
    modelCandidates = result.models;
    $("model-list-status").textContent =
      t("{0} {1} 个模型。{2}", result.source === "account" ? t("接口返回") : t("本地预设"), result.models.length, result.message);
    if (document.activeElement === $("model")) renderModels();
  } catch (error) {
    if (serial === modelListSerial)
      $("model-list-status").textContent = error.message;
  } finally {
    if (serial === modelListSerial) $("fetch-models").disabled = false;
  }
}
function capacityFields() {
  const p = config.providers.find((p) => p.id === $("provider").value);
  const custom = $("model").value.trim() !== p.model;
  const discovered = modelCandidates.find(
    (m) => m.id === $("model").value.trim(),
  );
  const supplied = discovered?.context_tokens && discovered?.max_tokens;
  if (custom && supplied) {
    $("context-tokens").value = discovered.context_tokens;
    $("max-tokens").value = discovered.max_tokens;
  }
  $("custom-capacity").hidden = !custom || !!supplied;
  $("model-capacity-note").hidden = !custom || !!supplied;
  $("context-tokens").required = $("max-tokens").required = custom && !supplied;
}
function providerFields() {
  invalidateModels();
  const p = config.providers.find((p) => p.id === $("provider").value);
  $("model").value = p.model;
  options("region", p.regions, p.region, {});
  $("model-key").value = "";
  $("context-tokens").value = $("max-tokens").value = "";
  $("model-key-label").textContent = p.configured
    ? t("API Key · 已配置，留空保留")
    : t("API Key · 尚未配置");
  capacityFields();
}
function connectionFields() {
  const c = config.connections.find(
    (c) => c.id === $("connection-provider").value,
  );
  $("connection-key").value = "";
  $("connection-key").disabled = !c.credential;
  $("connection-key-label").textContent = !c.credential
    ? t("无需密钥")
    : c.configured
      ? t("API Key · 已配置")
      : t("API Key · 尚未配置");
}
const subagentRoles = {investigator: "调查", synthesizer: "冲突核实", writer: "写作", reviewer: "编辑核查"};
let roleModelEditors = [];
function renderRoleModels(saved) {
  $("role-model-fields").replaceChildren();
  roleModelEditors = Object.entries(subagentRoles).map(([role, title]) => {
    const box = node("fieldset"), legend = node("legend", t(title));
    const enabled = node("input");
    enabled.type = "checkbox";
    enabled.checked = !!saved[role];
    const toggle = node("label", undefined, "checkbox");
    toggle.append(enabled, document.createTextNode(t("使用独立模型")));
    const fields = node("div");
    const controls = {};
    function field(name, label, type = "input") {
      const wrapper = node("label", t(label)), input = node(type);
      input.id = `role-${role}-${name}`;
      wrapper.append(input);
      fields.append(wrapper);
      input.addEventListener("invalid", () => { $("role-model-settings").open = true; });
      controls[name] = input;
      return input;
    }
    const provider = field("provider", "厂商", "select");
    for (const p of config.providers) {
      const option = node("option", labels[p.id] || p.id);
      option.value = p.id;
      provider.append(option);
    }
    const region = field("region", "区域", "select");
    const model = field("model", "模型");
    const list = node("datalist");
    list.id = `role-${role}-models`;
    model.setAttribute("list", list.id);
    fields.append(list);
    const fetchButton = node("button", t("获取模型列表"), "secondary");
    fetchButton.type = "button";
    fields.append(fetchButton);
    const capacity = node("div", undefined, "form-row");
    const context = field("context_tokens", "上下文容量 tokens");
    const output = field("max_tokens", "输出额度 tokens");
    for (const input of [context, output]) {
      input.type = "number";
      input.min = "1";
      capacity.append(input.parentElement);
    }
    fields.append(capacity);
    const key = field("key", "API Key · 已配置，留空保留");
    key.type = "password";
    key.autocomplete = "new-password";
    const status = node("p", "", "muted");
    fields.append(node("p", t("同一厂商的所有角色共享 API Key。"), "muted"), status);
    let candidates = [], serial = 0;
    const spec = () => config.providers.find(p => p.id === provider.value);
    function updateCapacity() {
      const custom = model.value.trim() !== spec().model;
      capacity.hidden = !custom;
      context.required = output.required = enabled.checked && custom;
      model.required = enabled.checked;
    }
    function resetProvider() {
      serial++;
      candidates = [];
      list.replaceChildren();
      fetchButton.disabled = false;
      region.replaceChildren();
      for (const value of spec().regions) {
        const option = node("option", value);
        option.value = value;
        region.append(option);
      }
      region.value = spec().region;
      model.value = spec().model;
      context.value = output.value = key.value = "";
      key.parentElement.firstChild.textContent = t(spec().configured
        ? "API Key · 已配置，留空保留" : "API Key · 尚未配置");
      status.textContent = "";
      updateCapacity();
    }
    provider.value = saved[role]?.provider || $("provider").value;
    resetProvider();
    for (const name of ["region", "model", "context_tokens", "max_tokens"])
      if (saved[role]?.[name] != null) controls[name].value = saved[role][name];
    function toggleFields() {
      fields.hidden = !enabled.checked;
      for (const input of Object.values(controls)) input.disabled = !enabled.checked;
      updateCapacity();
    }
    toggleFields();
    enabled.onchange = toggleFields;
    provider.onchange = resetProvider;
    function invalidate() {
      serial++;
      candidates = [];
      list.replaceChildren();
      fetchButton.disabled = false;
      status.textContent = "";
    }
    region.onchange = key.oninput = invalidate;
    model.oninput = () => {
      const found = candidates.find(m => m.id === model.value.trim());
      context.value = found?.context_tokens || "";
      output.value = found?.max_tokens || "";
      updateCapacity();
    };
    fetchButton.onclick = async () => {
      const current = ++serial;
      fetchButton.disabled = true;
      status.textContent = t("正在获取模型列表…");
      try {
        const result = await api("/api/models", {provider: provider.value,
          region: region.value, key: key.value.trim()});
        if (current !== serial || !box.isConnected) return;
        candidates = result.models;
        list.replaceChildren(...candidates.map(m => {
          const option = node("option"); option.value = m.id; return option;
        }));
        status.textContent = t("{0} {1} 个模型。{2}", result.source === "account"
          ? t("接口返回") : t("本地预设"), candidates.length, result.message);
      } catch (error) {
        if (current === serial) status.textContent = error.message;
      } finally {
        if (current === serial) fetchButton.disabled = false;
      }
    };
    box.append(legend, toggle, fields);
    $("role-model-fields").append(box);
    return {role, enabled, controls, spec};
  });
}
function selectedRoleModels() {
  const result = {};
  for (const {role, enabled, controls, spec} of roleModelEditors) {
    if (!enabled.checked) continue;
    const value = {provider: controls.provider.value, model: controls.model.value.trim(),
      region: controls.region.value};
    if (value.model !== spec().model) {
      value.context_tokens = Number(controls.context_tokens.value);
      value.max_tokens = Number(controls.max_tokens.value);
    }
    result[role] = value;
  }
  return result;
}
async function openSettings() {
  if (mutating) return;
  await loadConfig();
  const d = config.defaults;
  options(
    "provider",
    config.providers.map((p) => p.id),
    d.provider || "deepseek",
  );
  providerFields();
  $("model").value = d.model || $("model").value;
  if (d.region) $("region").value = d.region;
  $("context-tokens").value = d.context_tokens || "";
  $("max-tokens").value = d.max_tokens || "";
  capacityFields();
  $("role-model-settings").open = false;
  renderRoleModels(d.role_models || {});
  options(
    "search-provider",
    config.search,
    d.search_provider ||
      (config.connections.find((c) => c.id === "tavily")?.configured
        ? "tavily"
        : "duckduckgo"),
  );
  options("reader-provider", config.readers, d.reader_provider || "jina");
  options(
    "connection-provider",
    config.connections.map((c) => c.id),
    d.search_provider || "tavily",
  );
  connectionFields();
  $("parser").value = d.parser || "auto";
  $("docling-models").value = d.docling_models || "";
  $("analysis").checked = !!d.analysis;
  $("settings-feedback").textContent = "";
  $("mcp-options").replaceChildren();
  mcpLoaded = false;
  try {
    const { servers } = await call("mcp_connections");
    mcpLoaded = true;
    for (const name of servers) {
      const label = node("label", undefined, "checkbox"),
        input = node("input");
      input.type = "checkbox";
      input.value = name;
      input.checked = !!d.mcp_servers?.includes(name);
      label.append(input, document.createTextNode(name));
      $("mcp-options").append(label);
    }
    if (!servers.length)
      $("mcp-options").append(node("p", t("尚未配置 MCP 连接。"), "muted"));
  } catch (e) {
    $("settings-feedback").textContent = e.message;
  }
  $("settings-dialog").showModal();
  if (config.providers.find((p) => p.id === $("provider").value).configured)
    fetchModels();
}
$("open-settings").onclick = $("change-model").onclick = () =>
  openSettings().catch((e) => notice(e.message));
$("provider").onchange = () => {
  providerFields();
  if (config.providers.find((p) => p.id === $("provider").value).configured)
    fetchModels();
};
$("region").onchange = () => {
  invalidateModels();
  if (
    $("model-key").value ||
    config.providers.find((p) => p.id === $("provider").value).configured
  )
    fetchModels();
};
$("model-key").oninput = invalidateModels;
$("model-key").onchange = fetchModels;
$("fetch-models").onclick = fetchModels;
$("model").oninput = () => {
  $("context-tokens").value = $("max-tokens").value = "";
  capacityFields();
  renderModels();
};
$("model").onfocus = () => renderModels(true);
$("model").onblur = closeModels;
$("model").onkeydown = (e) => {
  if (e.key === "Escape" && !$("model-options").hidden) {
    e.preventDefault();
    e.stopPropagation();
    closeModels();
    return;
  }
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    if ($("model-options").hidden) renderModels();
    const items = Array.from($("model-options").querySelectorAll("button"));
    if (!items.length) return;
    modelOptionIndex = Math.max(
      0,
      Math.min(
        items.length - 1,
        modelOptionIndex + (e.key === "ArrowDown" ? 1 : -1),
      ),
    );
    items.forEach((item, i) =>
      item.setAttribute("aria-selected", String(i === modelOptionIndex)),
    );
    $("model").setAttribute(
      "aria-activedescendant",
      items[modelOptionIndex].id,
    );
    items[modelOptionIndex].scrollIntoView({ block: "nearest" });
  } else if (e.key === "Enter" && !$("model-options").hidden) {
    e.preventDefault();
    const items = $("model-options").querySelectorAll("button");
    if (modelOptionIndex >= 0 && items[modelOptionIndex])
      items[modelOptionIndex].click();
    else closeModels();
  }
};
$("settings-dialog").addEventListener("close", invalidateModels);
$("connection-provider").onchange = connectionFields;
$("settings-form").onsubmit = (e) => {
  e.preventDefault();
  act(
    e.submitter,
    async () => {
      const p = config.providers.find((p) => p.id === $("provider").value);
      const d = {
        ...config.defaults,
        provider: p.id,
        model: $("model").value.trim(),
        role_models: selectedRoleModels(),
        region: $("region").value,
        search_provider: $("search-provider").value,
        reader_provider: $("reader-provider").value,
        parser: $("parser").value,
        analysis: $("analysis").checked,
        mcp_servers: mcpLoaded
          ? Array.from(
              $("mcp-options").querySelectorAll("input:checked"),
              (el) => el.value,
            )
          : config.defaults.mcp_servers || [],
      };
      delete d.context_tokens;
      delete d.max_tokens;
      delete d.docling_models;
      if (d.model !== p.model) {
        d.context_tokens = Number($("context-tokens").value);
        d.max_tokens = Number($("max-tokens").value);
      }
      if ($("docling-models").value.trim())
        d.docling_models = $("docling-models").value.trim();
      let override = false;
      const credentials = new Map();
      for (const [name, value] of [
        [p.credential, $("model-key").value.trim()],
        ...roleModelEditors.filter(e => e.enabled.checked).map(e =>
          [e.spec().credential, e.controls.key.value.trim()]),
        [
          config.connections.find(
            (c) => c.id === $("connection-provider").value,
          ).credential,
          $("connection-key").value.trim(),
        ],
      ]) {
        if (!name || !value) continue;
        if (credentials.has(name) && credentials.get(name) !== value)
          throw new Error(t("同一厂商填写了不同的 API Key，请统一后保存。"));
        credentials.set(name, value);
      }
      for (const [name, value] of credentials) {
          override =
            (await api("/api/key", { name, value })).environment_override ||
            override;
      }
      // Credentials and defaults have distinct persistence; partial saves are explicit.
      $("model-key").value = $("connection-key").value = "";
      for (const editor of roleModelEditors) editor.controls.key.value = "";
      try {
        await api("/api/settings", d);
      } catch (e) {
        throw new Error(t("默认设置未保存；本次已提交的密钥已保存。") + e.message);
      }
      await loadConfig();
      $("settings-dialog").close();
      notice(
        t("设置已保存，仅用于新研究。没有发起付费连通测试。") +
          (override ? t(" 当前进程环境变量优先于文件中的密钥。") : ""),
      );
    },
    "settings-feedback",
  );
};
async function poll() {
  try {
    if (!document.hidden && !mutating) {
      await refreshStudy();
      await refreshList();
    }
  } catch (e) {
    notice(e.message);
  } finally {
    setTimeout(poll, 3000);
  }
}
async function boot() {
  if (!token) {
    notice(t("请从终端输出的完整本地启动链接打开工作台。"));
    return;
  }
  await loadConfig();
  await refreshList();
  const prior = sessionStorage.getItem("research-study");
  if (prior) {
    try {
      await openStudy(prior);
    } catch (e) {
      $("new-study").click();
      notice(e.message);
    }
  }
  setTimeout(poll, 3000);
}
$("language").onchange = async (event) => {
  setLanguage(event.target.value);
  $("breadcrumb").textContent = active ? t("工作台 / 我的研究") : t("工作台 / 新建研究");
  renderMaterials();
  if (status) renderStatus(status);
  if (report?.text) {
    renderReader();
  } else if (status && !status.published) {
    $("report-text").replaceChildren(node("p", t("当前方向尚无已发布报告。"), "muted"));
  }
  if (token) {
    try {
      await loadConfig();
      await refreshList();
      if (active) await loadPanel();
    } catch (error) { notice(error.message); }
  }
};
boot().catch((e) => notice(e.message));
