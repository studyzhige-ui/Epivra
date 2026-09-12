/* The browser presents Host facts. It owns no research state machine. */
"use strict";
const $ = (id) => document.getElementById(id);
const labels = {
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
};
const coverageLabels = {
  text_extracted_not_reviewed: "已提取正文 · 尚未核查",
  text_extracted: "已提取正文",
  table_extracted_not_reviewed: "已提取表格 · 尚未核查",
  structure_extracted_not_reviewed: "已提取结构 · 尚未核查",
  partial_extraction: "部分提取，请留意缺失内容",
  needs_ocr_or_visual_review: "需要 OCR 或视觉解读",
  computed_not_reviewed: "计算产物 · 尚未核查",
  mcp_output_not_reviewed: "外部工具资料 · 尚未核查",
};
const roles = {
  lead: "研究负责人",
  investigator: "调查",
  synthesizer: "综合",
  writer: "写作",
  reviewer: "核查",
};
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
md.renderer.rules.image = (tokens, index) =>
  `<span class="muted">图示：${md.utils.escapeHtml(tokens[index].content || "图片")}（请查看对应资料原件）</span>`;
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
  close.setAttribute("aria-label", "关闭提示");
  close.onclick = () => {
    $("notice").hidden = true;
  };
  $("notice").append(close);
  $("notice").hidden = false;
}
async function api(path, data, raw = false) {
  const headers = { "X-Research-Token": token };
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
      "与本地工作台的连接中断。操作可能已被宿主接收，请刷新状态，不要重复创建或提交。",
    );
  }
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "操作未完成。");
  return result;
}
const call = (action, fields = {}) =>
  api("/api/command", { action, ...fields });
async function act(button, work, feedback) {
  if (mutating) return;
  mutating = true;
  if (button) button.disabled = true;
  try {
    await work();
  } catch (e) {
    notice(e.message);
    if (feedback) $(feedback).textContent = e.message;
  } finally {
    mutating = false;
    if (button) button.disabled = false;
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
  if (s.cancelled) return "已取消";
  if (s.published) return "已完成";
  if (s.error) return "需要处理";
  if (s.paused) return "已暂停";
  if (!s.approved) return s.plans?.length ? "策略待审批" : "正在准备策略";
  return s.running ? "研究中" : "等待接续";
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
    active,
    data.studies.map((s) => [s.study, s.request, stage(s)]),
  ]);
  if ($("studies").dataset.signature === signature) return;
  $("studies").dataset.signature = signature;
  $("studies").replaceChildren();
  if (!data.studies.length)
    $("studies").append(node("p", "还没有研究，从一个问题开始。", "muted"));
  for (const s of data.studies) {
    const button = node(
      "button",
      undefined,
      "study-link" + (s.study === active ? " selected" : ""),
    );
    button.append(node("strong", s.request), node("small", stage(s)));
    button.title = s.request;
    button.onclick = () => {
      if (!mutating) openStudy(s.study).catch((e) => notice(e.message));
    };
    $("studies").append(button);
  }
}
async function openStudy(id) {
  statusSerial++;
  active = id;
  status = report = null;
  sessionStorage.setItem("research-study", id);
  $("welcome").hidden = true;
  $("study-view").hidden = false;
  $("study-title").textContent = "正在读取研究…";
  $("breadcrumb").textContent = "工作台 / 我的研究";
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
  $("study-title").textContent = s.request;
  $("study-stage").textContent = stage(s);
  $("study-meta").textContent =
    `${labels[s.policy.provider] || s.policy.provider} / ${s.policy.model} · 资料 ${s.source_count} 份 · ${s.policy.network ? "允许联网" : "本地资料与授权工具"}`;
  $("blocker").hidden =
    !s.error && !s.analysis_cleanup_error && !s.unsettled_operations?.length;
  $("blocker").textContent = s.unsettled_operations?.length
    ? "存在返回结果未知的调用，系统不会自动重发。请暂停后通过 CLI 对账入口，依据供应商的真实结果处理。"
    : s.error
      ? `研究暂时阻断：${s.error}。可暂停后检查连接设置，更新密钥并重新载入。`
      : s.analysis_cleanup_error
        ? "分析容器清理需要处理，请检查 Docker 状态。"
        : "";
  $("approve").hidden = s.cancelled || s.approved || !s.plans?.length;
  $("pause-resume").hidden = s.cancelled || s.published;
  $("pause-resume").textContent = s.paused ? "继续研究" : "暂停研究";
  $("steer").hidden = $("cancel").hidden = s.cancelled;
  $("supplement").hidden = $("reload-keys").hidden =
    s.cancelled || !s.paused || s.running;
  let message = s.cancelled
    ? "研究已取消，已有资料与成果仍保留。"
    : s.published
      ? "研究已完成，报告与引用已保存。"
      : !s.approved && s.plans?.length
        ? s.paused
          ? "初始策略已准备好。研究当前暂停，审批后仍需选择继续研究。"
          : "初始策略已准备好。阅读并审批后，系统会继续研究并交付最终成果。"
        : s.paused
          ? "研究保持暂停。可补充资料或修改连接设置，再决定继续。"
          : "研究在独立宿主中运行。你可以离开页面，稍后回来查看结果。";
  $("progress-summary").replaceChildren(
    node("strong", stage(s)),
    node("p", message, "muted"),
  );
  const signature = JSON.stringify(s.work || []);
  if ($("work-list").dataset.signature !== signature) {
    $("work-list").dataset.signature = signature;
    $("work-list").replaceChildren(node("h3", "已分配的研究工作"));
    if (!s.work?.length)
      $("work-list").append(node("p", "尚未分配调查工作。", "muted"));
    for (const w of s.work || []) {
      const row = node("div", undefined, "work-item");
      row.append(
        node("span", roles[w.role] || w.role, "work-role"),
        node("p", w.task),
      );
      $("work-list").append(row);
    }
  }
  renderUsage(s.usage || []);
  if (
    !previous ||
    previous.control !== s.control ||
    previous.published !== s.published
  ) {
    report = null;
    $("download-report").hidden = true;
    $("report-text").replaceChildren(
      node("p", "当前方向尚无已发布报告。", "muted"),
    );
    $("report-sources").replaceChildren();
    if (s.published && !previous?.published) selectTab("report");
    else if (tab === "report") loadPanel().catch((e) => notice(e.message));
  }
}
async function refreshStudy() {
  const id = active,
    serial = ++statusSerial;
  if (!id) return;
  const s = await call("status", { study: id });
  if (active === id && serial === statusSerial) renderStatus(s);
}
function renderUsage(groups) {
  $("usage-list").replaceChildren();
  if (!groups.length)
    $("usage-list").append(node("p", "暂无调用用量。", "muted"));
  for (const g of groups) {
    const card = node("div", undefined, "card usage-card");
    card.append(
      node("strong", `${g.resource} / ${g.model || "搜索或工具"}`),
      node(
        "p",
        `${g.calls} 次调用 · ${g.unresolved_calls} 次未知结果`,
        "muted",
      ),
    );
    const metrics = node("div", undefined, "usage-metrics");
    for (const [key, label] of Object.entries({
      input_tokens: "输入 tokens",
      output_tokens: "输出 tokens",
      cache_read_tokens: "缓存命中 tokens",
      reasoning_tokens: "推理 tokens（子项）",
      search_credits: "搜索 credits",
    })) {
      const metric = node("div");
      const value = g.totals[key];
      metric.append(
        node("strong", value == null ? "—" : value.toLocaleString()),
        node("small", label),
      );
      metrics.append(metric);
    }
    card.append(metrics);
    $("usage-list").append(card);
  }
}
function sourceRows(target, sources, id) {
  target.replaceChildren();
  if (!sources.length) target.append(node("p", "暂无资料。", "muted"));
  for (const s of sources) {
    const row = node("div", undefined, "source-row"),
      detail = node("div");
    const origin =
      typeof s.origin === "string"
        ? s.origin
        : JSON.stringify(s.origin || s.name || s.ref);
    detail.append(
      node("div", s.name || origin),
      node("small", coverageLabels[s.coverage] || "资料原件", "muted"),
    );
    if (/^https?:\/\//i.test(origin)) {
      const link = node("a", "打开来源 ↗", "text-button");
      link.href = origin;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      detail.append(link);
    }
    const download = node("button", "下载原件 ↓");
    download.onclick = () =>
      act(download, () => downloadSource(id, s.ref, s.name || origin));
    row.append(detail, download);
    target.append(row);
  }
}
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
        markdown($("report-text"), result.text);
        $("download-report").hidden = false;
        sourceRows($("report-sources"), result.sources || [], id);
      } else
        $("report-text").textContent = "当前方向尚无已发布报告，请刷新状态。";
    }
    sourceRows(
      $("analysis-files"),
      (status.analyses || []).flatMap((a) => a.files || []),
      id,
    );
  } else if (selected === "materials") {
    const result = await call("sources", { study: id });
    if (id === active && control === status?.control && tab === selected)
      sourceRows($("source-list"), result.sources, id);
  }
}
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
    headers: { "X-Research-Token": token, "Content-Type": "application/json" },
    body: JSON.stringify({ study: id, source: ref }),
  });
  if (!response.ok)
    throw new Error((await response.json()).error || "资料下载失败。");
  const blob = await response.blob();
  let filename = String(name)
    .split(/[\\/]/)
    .pop()
    .split("?")[0]
    .replace(/[<>:"|?*\x00-\x1f]/g, "_");
  saveBlob(blob, filename || "研究资料.bin");
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
  if (active === id) await refreshStudy();
  await refreshList();
}

function renderMaterials() {
  $("selected-materials").replaceChildren();
  materials.forEach((m, i) => {
    const li = node("li"),
      remove = node("button", "移除", "text-button");
    li.append(
      node(
        "span",
        `${m.kind === "folder" ? "授权文件夹及子目录" : "导入文件"} · ${m.path || m.file.name}`,
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
        "此文件超过浏览器上传上限，请使用系统选择或本地路径导入。",
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
  return `已导入 · ${r.characters} 字符 · ${coverageLabels[r.coverage] || "资料已保存"}${r.issues?.length ? "；" + r.issues.join("；") : ""}`;
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
    if (!request) throw new Error("请填写研究需求。");
    const defaults = config.defaults;
    if (
      !config.providers.find((p) => p.id === (defaults.provider || "deepseek"))
        ?.configured
    )
      throw new Error("请先在连接与设置中保存研究模型密钥。");
    if (scope === "local" && !chosen.length && !defaults.mcp_servers?.length)
      throw new Error("请至少选择文件、授权文件夹或启用资料 MCP。");
    $("creation-hint").textContent = "正在创建暂停草稿…";
    // A lost create response is never automatically resent.
    let id;
    try {
      const created = await call("create", {
        ...defaults,
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
          "正在导入 " + (item.path || item.file.name);
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
          "研究已保留，请查看当前状态。若资料未全部导入，请在暂停草稿中补充后继续。" +
            error.message,
        );
      }
      await refreshList();
      throw error;
    } finally {
      $("creation-hint").textContent =
        "生成策略会调用模型；正式研究需另行审批。";
    }
  });
};
$("new-study").onclick = () => {
  if (mutating) return;
  statusSerial++;
  active = null;
  status = report = null;
  sessionStorage.removeItem("research-study");
  $("welcome").hidden = false;
  $("study-view").hidden = true;
  $("breadcrumb").textContent = "工作台 / 新建研究";
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
for (const button of document.querySelectorAll(".close-dialog"))
  button.onclick = () => button.closest("dialog").close();
$("approve").onclick = () => {
  if (!status?.plans?.length || mutating) return;
  const plan = status.plans.at(-1);
  approval = { id: active, expected: status.control, ref: plan.ref };
  markdown($("approval-text"), plan.body.text);
  if (plan.body.brief) {
    $("approval-text").append(node("h3", "研究范围与前提"));
    const names = {
      subject: "研究对象",
      given_context: "已知背景",
      questions: "研究问题",
      material_scope: "资料范围",
    };
    for (const [key, value] of Object.entries(plan.body.brief)) {
      const p = node("p");
      p.append(node("strong", (names[key] || key) + "："));
      const modes = {
        case_materials: "针对本案例的资料",
        library: "待检索的资料库",
        unspecified: "尚未指定",
      };
      const display =
        typeof value === "string"
          ? value
          : Array.isArray(value)
            ? value.join("；")
            : value?.mode
              ? `${modes[value.mode] || value.mode}；依据：${value.basis || ""}`
              : JSON.stringify(value);
      p.append(document.createTextNode(display));
      $("approval-text").append(p);
    }
  }
  $("approval-hint").textContent = status.paused
    ? "研究当前暂停。批准策略不会自动恢复；之后选择继续研究开始执行。"
    : "确认后将按此策略自主研究并交付成果；你仍可主动暂停或改向。";
  $("approval-dialog").showModal();
};
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
      notice("策略已批准，研究仍暂停。选择继续研究开始执行。");
  });
$("pause-resume").onclick = () =>
  act($("pause-resume"), async () => {
    const id = active,
      s = status;
    await control(id, s.control, s.paused ? "resume" : "pause");
    await afterControl(id);
  });
$("steer").onclick = () => {
  steering = { id: active, expected: status.control };
  $("steer-request").value = status.request;
  $("steer-dialog").showModal();
};
$("steer-form").onsubmit = (e) => {
  e.preventDefault();
  act(e.submitter, async () => {
    const shown = steering;
    const request = $("steer-request").value.trim();
    if (!request) throw new Error("请填写新的完整需求。");
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
    if (confirm("取消后不能恢复此研究。确定取消？")) {
      await control(id, expected, "cancel");
      await afterControl(id);
    }
  });
$("reload-keys").onclick = () =>
  act($("reload-keys"), async () => {
    await call("reload", { study: active });
    notice("已重新载入密钥。研究配置不变，可继续接续研究。");
  });
$("download-report").onclick = () => {
  if (report?.text)
    saveBlob(
      new Blob([report.text], { type: "text/markdown;charset=utf-8" }),
      "研究报告.md",
    );
};
let supplement = null;
$("supplement").onclick = () => {
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
  const p = config.providers.find(
    (p) => p.id === (config.defaults.provider || "deepseek"),
  );
  $("model-summary").textContent =
    `${labels[p.id]} / ${config.defaults.model || p.model}${p.configured ? "" : " · 未配置密钥"}`;
}
function capacityFields() {
  const p = config.providers.find((p) => p.id === $("provider").value);
  const custom = $("model").value.trim() !== p.model;
  $("custom-capacity").hidden = !custom;
  $("context-tokens").required = $("max-tokens").required = custom;
}
function providerFields() {
  const p = config.providers.find((p) => p.id === $("provider").value);
  $("model").value = p.model;
  options("region", p.regions, p.region, {});
  $("model-key").value = "";
  $("context-tokens").value = $("max-tokens").value = "";
  $("model-key-label").textContent = p.configured
    ? "API Key · 已配置，留空保留"
    : "API Key · 尚未配置";
  capacityFields();
}
function connectionFields() {
  const c = config.connections.find(
    (c) => c.id === $("connection-provider").value,
  );
  $("connection-key").value = "";
  $("connection-key").disabled = !c.credential;
  $("connection-key-label").textContent = !c.credential
    ? "无需密钥"
    : c.configured
      ? "API Key · 已配置"
      : "API Key · 尚未配置";
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
      $("mcp-options").append(node("p", "尚未配置 MCP 连接。", "muted"));
  } catch (e) {
    $("settings-feedback").textContent = e.message;
  }
  $("settings-dialog").showModal();
}
$("open-settings").onclick = $("change-model").onclick = () =>
  openSettings().catch((e) => notice(e.message));
$("provider").onchange = providerFields;
$("model").oninput = capacityFields;
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
      for (const [name, value] of [
        [p.credential, $("model-key").value.trim()],
        [
          config.connections.find(
            (c) => c.id === $("connection-provider").value,
          ).credential,
          $("connection-key").value.trim(),
        ],
      ]) {
        if (name && value)
          override =
            (await api("/api/key", { name, value })).environment_override ||
            override;
      }
      // Credentials and defaults have distinct persistence; partial saves are explicit.
      $("model-key").value = $("connection-key").value = "";
      try {
        await api("/api/settings", d);
      } catch (e) {
        throw new Error("默认设置未保存；本次已提交的密钥已保存。" + e.message);
      }
      await loadConfig();
      $("settings-dialog").close();
      notice(
        "设置已保存，仅用于新研究。没有发起付费连通测试。" +
          (override ? " 当前进程环境变量优先于文件中的密钥。" : ""),
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
    notice("请从终端输出的完整本地启动链接打开工作台。");
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
boot().catch((e) => notice(e.message));
