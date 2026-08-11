# Deep Research Agent

一个由研究 Agent 主导、由确定性 Trust Plane 提供可信边界的通用深度研究项目。

模型负责规划、检索策略、证据判断、研究停止、跨来源综合与报告表达；代码负责安全执行、角色权限、来源保存、状态恢复和引用验证。项目不以固定查询、字段配额、来源数量或任务级预算代替研究判断。

内置运行时不为 Planner 或 Researcher 设置跨调用累计的任务级回合上限；防止失控循环统一依赖父 LangGraph 每次调用默认 512 且可配置的技术递归保护，命中后保存当前 Checkpoint 并返回可恢复暂停。Python 嵌入方仍可显式设置角色构造器的 `runtime_turn_limit` 作为主动选择的 fail-fast 保护，但它触发的是失败，不具有 `recoverable_pause` / `continue` 语义。这些技术保护都不代表研究完成、证据充分、预算耗尽或应当停止。

## 当前状态

v1 Agentic Core 已按批准架构实现，并通过不访问网络、不调用模型 API 的完整离线测试。真实 DeepSeek 与搜索供应商联调尚未执行；运行真实任务前仍需单独进行有成本的端到端验证。

权威设计文档只有两份：

- [架构决策](docs/ARCHITECTURE.md)：阶段治理、角色职责、研究产物、检索与停止、Guide、引用和上下文设计；
- [Prompt 规范](docs/PROMPTS.md)：八份独立角色 Prompt 与权限边界。

被新决策替代的描述会从当前文档删除，设计演变只由 Git 历史保存。`PROJECT_CHARTER.md` 只说明稳定使命和开发边界，不复制另一套架构。

## 架构

```text
Planner → 人工审批 → Supervisor
  → 并行 Researcher → Curator → Synthesizer
  → Writer → Independent Validator → Editor
  → Citation Renderer → 最终报告
```

- Planner 结合模型能力和公开只读预搜索形成 Research Contract，默认等待人工确认；
- Supervisor 持续判断实质缺口、信息增益、饱和与阶段质量，只有它能批准 L0、L1、L2 修订；
- Researcher 发现并保存来源，Curator 整理来源忠实的正式素材，Synthesizer 在写作前形成跨来源研究判断；
- Writer 只使用 Research Synthesis 与 Curated Material Library，不重新搜索或核验；
- Independent Validator 使用干净上下文只读核验，Editor 闭合意见并完成表达；
- Citation Renderer 确定性生成首次出现顺序正确、可复用且闭合的数字引用；
- 证据合理穷尽后仍不足可以成为合法结论，不为制造确定答案而无限搜索。

第一版内置 Tavily、Exa、Brave Search 与博查搜索适配器，以及受限的公开 HTTP/PDF 阅读器。Tavily/Exa 可直接返回正文；Brave/博查结果只作为发现线索，保存前必须读取原始页面。Agent 可以观察供应商状态，并使用 `auto`、`prefer`、`only` 或 `exclude` 路由。

## 安装与离线验证

项目支持普通 Python、venv、Conda 或 uv，不绑定环境管理器。Python 版本要求为 3.11 或更高。

```bash
python -m pip install -e .
python -m deep_research_agent doctor
python -m unittest discover -s tests -v
```

`doctor` 与测试套件不会调用模型或搜索 API。

## 配置与运行

内置真实运行时从环境变量读取凭据：

- `DEEPSEEK_API_KEY`：必需；
- `TAVILY_API_KEY`、`EXA_API_KEY`、`BRAVE_SEARCH_API_KEY`、`BOCHA_API_KEY`：至少配置一个。

创建任务会先执行公开只读预搜索并调用 Planner，然后停在人工审批点，因此会产生外部 API 请求与相应费用：

```bash
deep-research-agent run "研究问题"
deep-research-agent resume <thread-id> --approve
deep-research-agent status <thread-id>
deep-research-agent retry <thread-id>
deep-research-agent continue <thread-id>
```

也可以用 `--revise "修改意见"` 让 Planner 整体重做 Contract，或用 `--cancel` 取消。三种恢复操作互不替代：只有 LangGraph `interrupt()` 正在等待人工输入时使用 `resume`；只有 Checkpoint 明确记录失败步骤时使用 `retry`；进程中断或父图单次技术递归保护留下“无错误、无人工中断、仍有待执行节点”的 Checkpoint 时使用 `continue`。默认 Checkpoint 位于 `.deep-research-agent/checkpoints.sqlite3`；同一 `thread-id` 用于中断恢复，不能被另一个新任务复用。

父图技术递归保护可通过 Python API 的 `recursion_limit=` 或 CLI 的 `--recursion-limit` 调整；它作用于每次 `run`、`resume`、`retry` 和 `continue` 调用，不限制完整任务的研究深度。CLI 在 `retryable_failure`、`recoverable_pause` 或无法自动解释的 `paused` 状态返回退出码 `2`，在等待人工输入、完成或取消时返回 `0`，便于脚本区分“正常等待用户”和“需要运维动作”。

内置组合按当前 DeepSeek V4 的大上下文设置 `400,000` 字符的保守输入 envelope，并为输出保留空间；Python 组合可通过 `role_max_payload_chars=` 为其他模型显式调低。字符 envelope 只负责物理分批和防止请求被模型拒绝，不是 token 估算、研究预算或完成条件。

本地 SQLite 运行时强制单写者：同一数据库同一时刻只允许一个会修改任务的 CLI/Python 进程，第二个写入进程会在运行任何 Agent 前明确失败；图内部的并行 Researcher 不受影响。`status` 使用只读连接和同一父图拓扑重建 LangGraph 的公开 `next` 状态，不加载用户角色插件，也不执行任何角色。数据库记录运行时 schema 版本，不兼容版本会明确拒绝恢复，而不会猜测性反序列化旧任务。

v0.1 面向单机、中等规模研究。SQLite 会保存每个 LangGraph 步骤的历史，而 Planner/Researcher 的候选与来源全文当前仍在 Checkpoint state 中，因此数据库大小会随累计全文体量和工具回合数增长；本版不自动压缩或清理历史。大型任务应使用独立的 `--database`、预留并监控磁盘空间，并只在没有活动 writer 时整体归档或轮换数据库。后续高容量版本将把不可变正文移入内容寻址存储，Checkpoint 只保留 ID、有界预览和来源溯源。

自定义 Guide 可通过 `--guides <目录>` 加载；`--roles module:attribute` 只用于用户明确信任的本地 `RoleExecutors` 实现，因为该模块会以当前进程权限执行。

## 当前实现边界

已完成 LangGraph 父图与可持久化 Planner/Researcher 子图、默认人工审批、并行研究分支、八角色窄上下文与角色内有界分批、L0/L1/L2 治理、追加式独立验证审计、带版本和显式重试的 SQLite Checkpoint、透明 Search Broker、公开 HTTP/PDF 阅读、轻量 Domain/Capability Guides、稳定来源锚点和 Citation Renderer。

尚未完成的验证是：经用户明确允许后的真实 API 冒烟测试、多领域真实任务质量评测，以及闭环稳定后的薄 MCP 适配层。当前没有 GUI、多租户、向量 Context Engine，也不会迁移旧项目的确定性研究核心。
