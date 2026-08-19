# Deep Research Agent

一个由研究 Agent 主导、由确定性 Trust Plane 提供可信边界的通用深度研究项目。

模型负责规划、检索策略、证据判断、研究停止、跨来源综合与报告表达；代码负责安全执行、
角色权限、来源保存、状态恢复和引用验证。项目不以固定查询、字段配额、来源数量或任务级
预算代替研究判断。

## 权威文档

**架构只维护在 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。** 本文件刻意不复述角色
拓扑、产物模型、运行时边界或阶段计划——上一版 README 复述过，然后在重构中变成了一份
描述已删除架构的文档：整条角色链、一套已废弃的修订协议、一个从未存在的 CLI，全都写得
像是当前事实。那比没有文档更糟。需要知道系统怎么运作，读权威文档。

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) —— 唯一权威架构
- [docs/PHASE-1E-CALIBRATION.md](docs/PHASE-1E-CALIBRATION.md) —— 零包全矩阵压测结果与
  逐条判定
- [PROJECT_CHARTER.md](PROJECT_CHARTER.md) —— 稳定使命与开发边界
- [docs/design-input/](docs/design-input/) —— 历史设计输入，**不具权威地位**

## 当前状态

零包（不启用任何能力包）基线已在八条对抗性 fixture 上跑通并校准完成：七份发布报告，
`ambiguous-scope` 正确停在澄清点，没有一条出现"结论强度超出证据"。真实 DeepSeek +
Tavily 端到端运行已多次执行。详见 `docs/PHASE-1E-CALIBRATION.md`。

尚未开始：统一 judge（Phase 2）、能力包内容（Phase 3）、故障注入与恢复矩阵（Phase 4）、
Orientation Scan / Protocol Assurer / VisualSpec / MCP（Phase 5）。目前没有 CLI、没有
GUI、没有多租户。

## 环境与验证

Python 3.11+。测试与静态门都不调用模型或搜索 API。

```bash
python -m pip install -e .
```

```bash
python -m unittest discover -s tests
```

```bash
python tools/check_architecture.py
```

静态门检查依赖方向、分层完整性、被禁的遗留符号与能力包边界，每次提交都要通过。

## 真实运行（会产生外部 API 费用）

凭据从 `.env` 读取：`DEEPSEEK_API_KEY` 必需；搜索 provider（`TAVILY_API_KEY`、
`EXA_API_KEY`、`BRAVE_SEARCH_API_KEY`、`BOCHA_API_KEY`）至少配置一个，缺失的 provider
跳过而不是失败。DuckDuckGo 与 arXiv / Crossref / PubMed 无需密钥。

跑一条压测 fixture 的完整路径（委托 → 合同 → 审批 → Wave → 写作 → 审查 → 发布）：

```bash
python tools/run_research.py --list
```

```bash
python tools/run_research.py --fixture sparse-evidence --database .deep-research-agent/run.sqlite3 --approve
```

不传 `--approve` 会停在审批卡，只花一次 Architect 调用。运行状态全部由 artifact heads
与 operation ledger 推导，所以中断后**对同一个数据库重跑即可继续**——已完成的付费调用
只回放不重发，已提交的产物不会重做。
