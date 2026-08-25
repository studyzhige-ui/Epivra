# Deep Research Agent

Deep Research Agent 是一个面向单人本地使用的 Agent-first 研究系统。用户给出开放问题，
Agent 在用户确认的研究方向内完成规划、检索、阅读、证据整理、综合、写作与独立审查，最终
交付可追溯来源的 Markdown 报告。

当前产品入口是 `deep-research` 交互式工作区，以及供 Codex、Claude Code 等本地 Agent
host 使用的 `deep-research-mcp` STDIO 服务。Python 接入只通过公开的 `ResearchService`
边界；存储、artifact 与 operation ledger 实现不属于包的公开 API。

## 文档

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)：当前实现的唯一权威架构说明
- [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md)：安装、配置与完整使用流程
- [PROJECT_CHARTER.md](PROJECT_CHARTER.md)：稳定的产品使命与开发边界

仓库不保留历史架构副本、未来实施蓝图或阶段性进度文档。实现改变时，直接更新上述当前
文档并删除被替代描述。

## 安装

需要 Python 3.11 或更高版本。

```bash
python -m pip install -e .
```

可以复制示例配置，也可以第一次进入工作区后按引导完成配置：

```bash
copy .env.example .env
```

## 使用

```bash
deep-research
```

首页会直接提示输入研究主题或问题；按 `Esc` 可以进入设置、查看已有研究或退出。提交主题后，
系统先生成一份简洁的研究方向，用户选择「开始研究」后才进入正式检索。生成研究方向本身会
调用模型，因此可能产生模型 API 费用。

诊断命令：

```bash
deep-research doctor
deep-research doctor --live
deep-research --version
deep-research --help
deep-research-mcp --help
```

`doctor --live` 会真实访问已配置的厂商；搜索厂商的验证会消耗查询额度。
Codex 与 Claude Code 的 MCP 接入步骤见
[docs/GETTING-STARTED.md](docs/GETTING-STARTED.md#10-通过-mcp-交给其他-agent)。

## 核心边界

- artifact lineage 与 operation ledger 保存持久事实；任务状态和可执行动作由事实投影。
- Research Contract 同时是用户看到的研究方向和 Agent 的执行依据，不维护第二份摘要模型。
- 已完成的相同外部调用从 ledger 回放；结果未知的调用停止并要求显式对账，不自动重试。
- `research_memory` 只保存会影响 Lead 后续决策的信息，不保存逐步运行日志。
- 系统没有持久任务状态字段、通用流程引擎、后台事务实体或主题专用持久模型。

完整边界见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 验证

测试和静态门不会调用模型或搜索 API：

```bash
python -m unittest discover -s tests
ruff check src tests tools evals
python tools/check_architecture.py
```
