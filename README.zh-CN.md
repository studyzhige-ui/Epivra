<p align="center"><img src="src/epivra/web/favicon.svg" width="72" alt="Epivra" /></p>
<h1 align="center">Epivra</h1>
<p align="center">自主研究工作台 · 从问题到洞见</p>
<p align="center"><a href="README.md">English</a> · <strong>简体中文</strong></p>

![Epivra 中文工作台](docs/images/home-zh-CN.png)

Epivra 是本地自主研究工作台，将问题与获授权的资料转化为附带来源引用的研究报告。它整合公开网络研究、本地文档、可选的数据分析和外部 MCP 工具。Web、终端与 MCP 接口共享同一个本地研究工作区。

## 研究方式

描述问题、用途与资料范围，阅读并批准初始研究路线。研究负责人调查问题，维护发现和待解冲突，整理写作依据，并持续修订共享稿件。负责人可以直接调查和写作，也可以按需将具体任务交给助手。

研究只需初次批准，之后在已授权范围内自主推进，不再要求重复审批。你可以通过工作台暂停、取消、补充资料或调整方向。保存草稿不等于发布结果：当前稿件必须经过独立审稿者认可才能发布，修改后的稿件需要重新审阅。报告没有默认字数上限。

来源、摘录、研究发现、报告和已记录用量保存在本地工作区。引用检查和独立审阅便于核查，但不保证研究结论正确。

## 快速开始

需要 **Python 3.11 或更高版本**，以及可用的模型供应商服务。在 Windows PowerShell 中克隆仓库并运行：

```powershell
git clone https://github.com/studyzhige-ui/Epivra.git
cd Epivra
python -m venv .venv
.venv/Scripts/python.exe -m pip install .
.venv/Scripts/epivra.exe --lang zh-CN web --port 0
```

打开“连接与设置”，选择供应商，输入 API 密钥并选择模型。新建研究、选择资料、生成路线，确认后开始研究。浏览器会自动打开；端口 `0` 表示选择可用端口。研究期间保持宿主运行。

运行工作台不需要 Node.js、前端构建或数据库服务器。macOS/Linux 的虚拟环境可执行文件位于 `.venv/bin/`。当前已验证的本地环境为 Windows，不声明已完成跨平台验收。

## 入口与能力

| 入口 | 用途 |
|---|---|
| `epivra --lang zh-CN web` | 浏览器工作台：配置连接、管理研究、核查来源、导出报告 |
| `epivra --lang zh-CN` | 交互式终端工作台 |
| `epivra --help` | 用于本地自动化的 JSON 命令 |
| `epivra-mcp --root <工作区绝对路径>` | 向其他客户端提供 MCP 接口；需要 MCP 扩展和已运行的宿主 |

Web 界面可切换简体中文与英文。报告语言请在研究需求中指定。报告可导出为 Markdown、Word 或独立 HTML；PDF 通过浏览器打印对话框导出。

- **模型连接：**通过官方供应商适配器连接 OpenAI、Claude、Gemini、Grok、DeepSeek、Qwen、Kimi、GLM、Doubao、MiniMax、Hunyuan 和 ERNIE。默认选择 DeepSeek / `deepseek-flash`，实际可用性取决于账户。
- **搜索与阅读：**支持 Tavily、Exa、Brave、Perplexity、Bocha、无需密钥的 DuckDuckGo 回退和 Jina 阅读。允许联网的研究还可使用 Crossref、PubMed、Europe PMC 和 World Bank 公共数据。
- **资料：**支持文本、CSV/TSV、文本 PDF 和电子表格；可选的文档扩展提供 Docling 解析与 OCR。资料访问遵守所选授权范围。
- **分析：**可选的 Python 计算与图表在禁止联网的 Docker Linux 容器中执行。
- **外部 MCP：**研究助手可使用明确授权的工具和资源。仅本地资料模式关闭内建网络研究，但仍可使用所选外部 MCP 服务。

供应商调用可能收费。Epivra 不设置研究总时长、token 或费用预算；记录的用量不是账单。

## 可选组件

使用虚拟环境中的 Python 安装：

```powershell
.venv/Scripts/python.exe -m pip install ".[documents]"  # 文档解析与 OCR
.venv/Scripts/python.exe -m pip install ".[mcp]"        # MCP 集成
```

解析模型的下载方法见[本地模型说明](models/README.md)。需要数据分析时，安装支持 Linux 容器的 Docker，运行 `docker build -t epivra-analysis:1 sandbox` 构建镜像，再在设置中启用分析。这些组件均为可选项。

## 工作区与仓库结构

| 路径 | 内容 |
|---|---|
| `src/epivra/` | 应用代码、Web 资源和界面翻译 |
| `tests/` | 离线回归测试 |
| `tools/` | 开发检查与本地诊断工具 |
| `sandbox/` | 隔离分析镜像与执行器 |
| `models/` | 解析模型说明及清单；模型权重保留在本地 |
| `docs/` | 中英文使用说明及 README 图片 |
| `eval/` | 参考资料 |
| `.epivra/` | 本地私有研究、导入资料、设置及恢复记录；不纳入 Git |
| `.env` | 本地供应商凭据；不纳入 Git |
| `mcp-servers.json` | 本地 MCP 连接与权限；不纳入 Git |

请从固定工作区启动，或明确指定 `--root`。升级前停止研究并备份完整的 `.epivra/` 目录。恢复时复用已保存响应；结果未知的调用不会自动重发。运行合同不兼容的研究仍可查阅和导出，但不能隐式恢复执行。

配置、资料、MCP、备份与故障排查见[使用说明](docs/USAGE.md)。

## 开发检查

```powershell
python -m pip install -e ".[mcp]" ruff mypy build
python -m unittest discover -s tests
python tools/check_architecture.py
ruff check src tests tools
mypy
python -m build --wheel
```

这些检查不调用模型或搜索 API。源码包含基于 Node 的 Web 回归测试；Node.js 仅用于运行这些测试，应用本身不依赖它。
