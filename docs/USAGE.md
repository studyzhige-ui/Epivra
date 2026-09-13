# Epivra 使用说明

[English](USAGE.en.md) · **简体中文**

Epivra 是在本机运行的自主研究工作台。提出问题、确认策略后，Agent 自主搜集资料、比较证据、分析并撰写成果；你可以随时暂停、补充资料和调整方向。

## 界面语言

Web 右上角可选择简体中文或 English；切换不会清空正在填写的需求或资料选择。CLI 与 MCP 使用 `--lang zh-CN` / `--lang en`，或设置 `EPIVRA_LANG`；CLI 的连接设置中也可切换当前会话语言。MCP 工具名称、参数和协议状态不翻译，工具说明按所选语言呈现。界面切换不改写用户输入、来源和已有报告；成果语言请在研究需求中指定。

## 1. 安装和启动

需要 Python 3.11 或更高版本。以下为 Windows PowerShell，在 Epivra 项目目录执行：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
.venv/Scripts/epivra.exe web
```

浏览器会自动打开。无需 Node.js、前端构建或数据库服务。端口占用时使用 `epivra web --port 0`。关闭浏览器不结束后台研究；研究时本机及宿主服务需要保持运行，系统休眠会中断执行。

偏好终端交互时运行 `.venv/Scripts/epivra.exe`，无参数进入工作台。macOS/Linux 对应使用 `.venv/bin/python` 与 `.venv/bin/epivra`；本轮主要验证平台为 Windows。

下文命令假设已激活虚拟环境，或把 `epivra` 替换为上述完整路径。

## 2. 配置连接

在“连接与设置”中选择模型厂商和账户地区，填写 API Key，再选择模型。Web 会获取可用模型，支持字符筛选（例如 `gpt5` 匹配 `gpt-5.5`）及手动输入。部分厂商暂无已核实的列表接口，会明确显示预设列表；未知型号如缺少容量元数据，需按厂商文档填写上下文和输出容量。终端也支持配置厂商、密钥及型号，模型列表搜索目前在 Web 提供。

支持 OpenAI、Claude、Gemini、Grok、DeepSeek、Qwen、Kimi、GLM、豆包、MiniMax、腾讯混元和百度文心官方接口。默认 DeepSeek / deepseek-flash。不支持自定义中转站 URL。不同账户的模型权限与速率额度由厂商决定。

搜索可选 Tavily、Exa、Brave、Perplexity、Bocha；DuckDuckGo 作为无需密钥的兜底，不保证随时可用。网页正文可通过 Jina、Tavily、Exa 获取。按实际启用的服务配置密钥即可。

密钥保存在本地 `.env`，环境变量优先于文件。设置保存在 `.epivra/cli-settings.json`，修改默认配置只影响新研究。用量面板记录接口返回的用量，不代表供应商账单；不能预知账户余额。

## 3. 开展研究

1. 输入希望弄清的问题及用途；可补充时间范围、读者和成果格式。
2. 选择公开网络、网络与本地资料，或仅本地资料与已选 MCP。
3. 如有资料，选择文件、上传文件或授权资料文件夹。选择单个文件只导入该文件；授权文件夹允许按需检索其内容。
4. 生成并阅读初始研究策略，确认范围与方法后批准。
5. 在“我的研究”查看进度和成果。正常过程自主推进，遇到额度、凭据等阻断会说明原因。

生成初始策略也会调用模型。需要改变方向时使用暂停与改向操作；修改后的策略如需审批，应阅读当前版本再确认。不要通过直接编辑数据库或中间文件控制研究。

## 4. 资料解析与数据分析

基础安装支持文本、CSV/TSV、PDF 文本层和 XLSX。公式可读取但不重新计算。扫描 PDF、图片 OCR、DOCX/PPTX 等复杂资料安装可选依赖：

```powershell
python -m pip install -e ".[documents]"
```

本项目的模型放在 `models/docling/`，运行时自动发现；新克隆项目按[模型说明](../models/README.md)下载。缺少依赖、模型或解析失败会明确反馈；OCR 不等于理解图表，重要图表和复杂排版仍应核查。

统计、绘图及 Python 分析需要 Docker Linux 容器环境。安装并启动 Docker 后构建一次：

```powershell
docker build -t epivra-analysis:1 sandbox
```

在设置中启用数据分析。执行容器禁止联网，只接收本次授权输入，不挂载密钥或整个项目。无需分析时无需 Docker。

## 5. MCP 双向接入

```powershell
python -m pip install -e ".[mcp]"
epivra start
```

外部 MCP 工具在本地 `mcp-servers.json` 配置；通过设置启用，并明确允许的工具、资料与角色。其他 MCP 客户端调用 Epivra 时，使用 `epivra-mcp --root <项目绝对路径>`。宿主须先独立启动，不能依赖 MCP 客户端的生命周期。默认不允许外部客户端批准研究策略。

例如在外部客户端的 MCP 设置中配置（路径替换为实际安装目录）：

```json
{
  "mcpServers": {
    "Epivra": {
      "command": "D:/Projects/Python/Epivra/.venv/Scripts/epivra-mcp.exe",
      "args": ["--root", "D:/Projects/Python/Epivra"]
    }
  }
}
```

Epivra 连接外部服务时，在本地 `mcp-servers.json` 配置命名连接。HTTP 示例：

```json
{
  "materials": {
    "transport": "http",
    "url": "https://your-service.example/mcp",
    "token_env": "MATERIALS_MCP_TOKEN",
    "tools": {},
    "resources": []
  }
}
```

公开服务可省略 token_env；其他服务的令牌只保存在本地环境或 `.env`。先运行 `epivra mcp-discover materials` 查看工具与资源，再为需要的工具指定 `roles` 和 `write`，如 `"lookup": {"roles": ["investigator", "reviewer"], "write": false}`；resources 填精确资源 URI。只添加信任的服务，外部写工具的 `write: true` 表示用户预先授权写操作。

Epivra 对外提供 HTTP MCP 时，设置独立环境变量 `EPIVRA_MCP_TOKEN`，再运行 `epivra-mcp --transport http`；客户端使用 Bearer 认证。该服务仅监听本机，本产品不提供公网多租户服务。

## 6. 文件、备份与升级

| 位置 | 用途 | 纳入 Git |
|---|---|---|
| `src/epivra/` | 代码、网页、图标 | 是 |
| `models/docling/` | 本地解析模型 | 否，保留下载说明与清单 |
| `.env` | API 密钥 | 否 |
| `.epivra/` | 研究数据库、资料、配置与恢复记录 | 否 |
| `mcp-servers.json` | 本地外部工具连接配置 | 否 |
| `.venv/` | Python 环境 | 否，按依赖重新安装 |

备份研究前先暂停任务，等待当前执行结束，然后使用 `epivra shutdown` 关闭宿主，再复制整个 `.epivra/`；如需保留连接，单独安全备份 `.env` 和 MCP 配置。不要只复制数据库而遗漏资料文件。Web 服务另行在其终端退出。

Epivra 是新的独立项目，不自动导入旧项目 `.deep-research-agent/` 数据。旧目录保持原样，历史研究继续使用旧安装读取。安装位置与研究根目录可不同，用 `--root` 显式指定，避免从不同目录启动产生两份本地工作区。

## 7. 常见问题与当前边界

- **模型列表获取失败：**检查密钥、地区、账户权限及网络；列表接口与推理接口权限可能不同。
- **配置新密钥仍无效：**检查同名环境变量是否覆盖 `.env`，已暂停任务通过重载连接接续。
- **无法解析扫描件：**确认安装 documents 扩展，且模型目录完整。
- **无法启动分析：**确认 Docker 正在运行且已构建 `epivra-analysis:1`。
- **研究被阻断：**依据任务提示处理，再恢复。不要重复新建任务来替代恢复。

当前功能已集成，供应商真实账户联调、跨题材与长文档研究评测仍有未覆盖范围。报告不是必然正确的结论，重要使用场景应回看来源、条件和不确定性。工程测试通过不等于研究质量验收通过。
