<p align="center"><img src="src/epivra/web/favicon.svg" width="72" alt="Epivra" /></p>

## 连续研究架构（优化分支）

一次研究路线审批后，完整研究主体自主取证、按需调用调查/冲突核实助手，维护有原文支持的研究判断与写作依据，在共享文稿上持续局部修改；独立编辑核查精确版本后交付。保存初稿不结束作者工作，过期依据/稿件/核查不能用于发布。路线不提出假设或预定答案，批准后不再请示用户；用户仍可主动暂停、取消或调整问题。

本分支使用 `continuous-research-v2`；旧任务保持可读、可审计，不自动按新合同恢复未知调用。没有默认报告长度限制。实现与验收入口见 [研究工作台](docs/refactor/02_RESEARCH_WORKSPACE.md) 和 [源码/手册验收映射](docs/refactor/03_REFERENCE_AND_ACCEPTANCE.md)。重构的工程验证与真实质量结果分开报告，尚未授权合并 main 或发布。

<h1 align="center">Epivra</h1>
<p align="center">从问题到洞见 · 本地自主研究工作台</p>
<p align="center"><a href="README.md">English</a> · <strong>简体中文</strong></p>

![Epivra 简体中文工作台](docs/images/home-zh-CN.png)

Epivra 结合公开网络和你的资料开展研究。你确认初始策略后，Agent 自主调查、分析、综合、写作与核查，交付有来源依据的成果。研究过程中可以暂停、补充资料或调整方向。

## 为什么使用 Epivra

- **研究由你定方向**：先审批策略，再自主推进；支持暂停和改向。
- **网络与本地资料一起使用**：搜索网页、上传文件，或授权资料文件夹及 MCP 资源。
- **选择自己的模型**：支持 12 家官方模型厂商，以及多种搜索与网页读取服务。
- **三种使用入口**：简体中文与 English 的 Web、CLI 和 MCP；同一份本地研究记录。
- **有据可查的成果**：保留来源、研究产物和用量，支持 Markdown、Word、HTML 导出及浏览器 PDF/打印与可选数据分析。

## 研究如何推进

Epivra 从人类研究中的问题澄清、证据评价、方法选择、反证检查和修订机制出发，将它们落实为角色职责、工具与成果交接合同。它没有为每个主题预设固定研究步骤：负责人按证据决定调查、补查、综合或修订；调查成果已足够完整时，可以直接进入写作。

这里的“研究内核”指组织研究判断的方法、指令与材料合同，分布在角色指令、工具语义、上下文和原成果交接中，不是另一个模型。所有角色共用自研 Harness，由程序控制授权、调用账本、执行调度与恢复。内部多 Agent 协作使用持久工作与成果引用，不依赖 A2A；MCP 用于连接外部工具和客户端。

研究内核影响模型如何使用证据，但结果质量还取决于模型、资料、工具和实际上下文。独立审查及可追溯引用不能保证判断正确；需要同时检查最终结论、依据和核查理由。

## 快速开始

需要 **Python 3.11+**。在项目目录执行（Windows PowerShell）：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
.venv/Scripts/epivra.exe --lang zh-CN web
```

macOS / Linux 对应使用 `.venv/bin/python` 与 `.venv/bin/epivra`。当前主要验证平台为 Windows。

1. 打开“连接与设置”，选择厂商、填写密钥并选择模型。
2. 输入问题及用途，选择资料范围。
3. 生成并确认研究策略，随后等待研究成果。

Web 右上角可切换语言，输入内容不会清空。无需 Node.js、前端构建或数据库服务。

## 使用方式

以下命令假设已激活虚拟环境：

| 入口 | 命令 |
|---|---|
| Web 工作台 | `epivra --lang zh-CN web` |
| CLI 交互工作台 | `epivra --lang zh-CN` |
| MCP 服务 | 先 `epivra start`，再 `epivra-mcp --lang zh-CN` |

使用 `--lang en` 切换 English，或设置 `EPIVRA_LANG`。界面语言不自动翻译你的资料与报告；请在研究需求中指定成果语言。

## 连接与扩展

| 能力 | 支持范围 |
|---|---|
| 模型 | OpenAI、Claude、Gemini、Grok、DeepSeek、Qwen、Kimi、GLM、豆包、MiniMax、混元、文心 |
| 搜索 | Tavily、Exa、Brave、Perplexity、Bocha；DuckDuckGo 兜底 |
| 自带公共渠道 | Crossref、PubMed、Europe PMC、世界银行；这些渠道无需 API Key |
| 网页正文 | Jina、Tavily、Exa |
| 资料 | 文本、CSV/TSV、PDF 文本层、XLSX；可选 Docling 文档解析和 OCR |
| 分析 | 可选 Docker Python 沙箱，用于统计、数据处理与绘图 |
| MCP | 连接外部工具与资料，也可供其他客户端调用研究能力 |

```powershell
# 按需要安装扩展
python -m pip install -e ".[documents,mcp]"
# 可选数据分析
docker build -t epivra-analysis:1 sandbox
```

默认模型为 `deepseek-flash`。仅支持官方模型接口；不支持自定义中转站 URL。模型列表发现与真实账户联调的覆盖范围不同，未登记型号可能需要填写容量参数。

## 本地数据与隐私

研究记录保存在 `.epivra/`，密钥保存在 `.env`，本地解析模型位于 `models/docling/`。这些内容不进入 Git。Epivra 会保护本地用户的 `.epivra/` 私有状态目录，不会修改用户原资料目录的权限。图标及界面资源随应用打包。

本地运行不等于资料从不离开设备：在线模型、搜索服务及外部工具会接收任务所需的查询和资料。关闭界面不会结束后台研究，本机和宿主服务需保持运行。

## 帮助与当前状态

- [使用说明](docs/USAGE.md)：安装、配置、研究流程、MCP、备份和故障处理。
- [本地模型说明](models/README.md)：下载与目录结构。
- [验证工具说明](evals/README.md)：离线工程验证与研究评测的区别。

当前为开发版本。功能已集成，但并非所有供应商都完成真实账户联调，跨题材、长文档及规模化研究质量仍有待验证。工程测试通过不代表研究结论必然正确；OCR 也不等于复杂图表语义理解。
