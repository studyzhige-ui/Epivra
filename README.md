<p align="center"><img src="src/epivra/web/favicon.svg" width="72" alt="Epivra" /></p>
<h1 align="center">Epivra</h1>
<p align="center">Autonomous research on your desktop</p>
<p align="center"><strong>English</strong> · <a href="README.zh-CN.md">简体中文</a></p>

![Epivra workbench](docs/images/home-en.png)

Epivra is a local research workbench that turns a question and authorized materials into a source-linked report. It combines public web research, local documents, optional data analysis, and external MCP tools. Web, terminal, and MCP interfaces share the same local research workspace.

## Download and open

**Desktop preview 0.3.0** — no separate Python, Git, Node.js or database installation.

| Your computer | Download |
|---|---|
| Windows 10/11, x64 | [Download Windows ZIP](https://github.com/studyzhige-ui/Epivra/releases/download/v0.3.0/Epivra-0.3.0-windows-x64.zip) |
| macOS 14+, Apple Silicon (M-series) | [Download macOS DMG](https://github.com/studyzhige-ui/Epivra/releases/download/v0.3.0/Epivra-0.3.0-macos-arm64.dmg) |

1. **Windows:** extract the entire ZIP and double-click **Epivra.exe**.
   **macOS:** open the DMG, drag **Epivra** into Applications, then open it.
2. Your browser opens automatically. On first launch, choose a provider, enter your own API key, select a model and save.
3. Enter a research question, select the material scope, generate the route and approve it.

Next time, open Epivra again. Repeated launches reopen the existing workbench.
Closing the browser keeps research running; use **Quit** in the Epivra control window to stop the background host.

These preview builds have **no Windows publisher certificate or Apple notarization**; your OS may show an unknown-developer warning. While this repository is private, downloads require an authorized GitHub account.
[Release notes and SHA-256](https://github.com/studyzhige-ui/Epivra/releases/tag/v0.3.0) · [User guide](docs/USAGE.en.md)

The base app supports text, text PDFs, spreadsheets and web research. Prepare
**OCR and Docker analysis independently in Settings**; no separate Epivra edition
is needed. Install and start Docker Desktop separately to use analysis.

## Research workflow

Describe the question, intended use, and material scope, then review and approve the initial research route. A research owner investigates the question, maintains findings and unresolved conflicts, prepares the writing basis, and revises a shared manuscript. It can investigate and write directly or delegate focused tasks to assistants when useful.

Approval is required once. Research continues within that authorization without further approval requests; you can pause, cancel, add materials, or adjust direction through the workbench. A saved draft is not a published result. An independent reviewer must accept the current manuscript before publication, and changes to the manuscript require another review. Reports have no default word limit.

Sources, excerpts, findings, reports, and recorded usage remain in the local workspace. Citation checks and independent review support inspection; they do not guarantee that conclusions are correct.

## Interfaces and capabilities

| Entry | Purpose |
|---|---|
| `epivra --lang en web` | Browser workbench: configure connections, manage research, inspect sources, and export reports |
| `epivra --lang en` | Interactive terminal workbench |
| `epivra --help` | JSON commands for local automation |
| `epivra-mcp --root <absolute-workspace-path>` | MCP access for another client; requires the MCP extra and a running host |

The Web interface switches between English and Simplified Chinese. Set the desired report language in the research request. Reports can be exported as Markdown, Word, or standalone HTML; PDF export uses the browser's print dialog.

- **Model connections:** OpenAI, Claude, Gemini, Grok, DeepSeek, Qwen, Kimi, GLM, Doubao, MiniMax, Hunyuan, and ERNIE through official provider adapters. The default selection is DeepSeek / `deepseek-flash`; account availability varies.
- **Search and reading:** Tavily, Exa, Brave, Perplexity, Bocha, a key-free DuckDuckGo fallback, and Jina reading. Network-enabled research can also use Crossref, PubMed, Europe PMC, and World Bank public data.
- **Materials:** text, CSV/TSV, text PDFs, and spreadsheets; the optional documents extra adds Docling parsing and OCR. Sources are accessed within the selected permissions.
- **Analysis:** optional Python calculations and charts in Docker Linux containers with no network access.
- **External MCP:** explicitly permitted tools and resources can be used by research assistants. Local-material mode disables built-in web research but may still use selected external MCP services.

Provider calls may incur charges. Epivra does not impose a total research time, token, or cost budget. Recorded usage is not a billing statement.

## Optional components

Open **Optional features** in Connections & settings:

- **OCR document parsing:** choose Install and wait for dependencies and models to download and validate. This enables scans, images and complex documents. Downloads can require several GB. Keep Epivra running; new studies use the prepared component automatically.
- **Docker data analysis:** install and start [Docker Desktop](https://www.docker.com/products/docker-desktop/), then choose Prepare Docker analysis. Once the image is ready, enable analysis. Image preparation needs a network connection; analysis containers run without network access.

Enable either, both or neither. Settings show preparation progress and errors.

## Run from source (developers)

Requires Python 3.11+ and Git. In Windows PowerShell:

```powershell
git clone https://github.com/studyzhige-ui/Epivra.git
cd Epivra
python -m venv .venv
.venv/Scripts/python.exe -m pip install ".[mcp]"
.venv/Scripts/epivra-desktop.exe
```

On macOS, use `.venv/bin/python` and `.venv/bin/epivra-desktop`.
Use `epivra-desktop --root <absolute-path>` for an existing source workspace;
data and keys are never silently migrated. [Build desktop releases](packaging/README.md).

## Workspace and repository

| Path | Contents |
|---|---|
| `src/epivra/` | Application code, Web assets, and interface translations |
| `tests/` | Offline regression tests |
| `tools/` | Development checks and local diagnostics |
| `sandbox/` | Isolated analysis image and runner |
| `models/` | Parsing-model instructions and manifest; weights stay local |
| `docs/` | English and Chinese user guides and README images |
| `eval/` | Reference materials |
| `.epivra/` | Private local research, imported materials, settings, and recovery records; excluded from Git |
| `.env` | Local provider credentials; excluded from Git |
| `mcp-servers.json` | Local MCP connections and permissions; excluded from Git |

Desktop data lives in `%LOCALAPPDATA%\Epivra` on Windows or `~/Library/Application Support/Epivra` on macOS. Open it from the control window. User files such as `.epivra/` and `.env` are inside this data folder, separate from the application. Quit Epivra and back up the complete data folder before replacing the app. Source CLI/Web commands still use the current workspace unless `--root` is specified. Saved responses are reused during recovery; calls with unknown outcomes are not automatically repeated. Studies created with incompatible runtime contracts remain available for inspection and export but cannot be silently resumed.

See the [user guide](docs/USAGE.en.md) for configuration, materials, MCP, backups, and troubleshooting.

## Development checks

```powershell
python -m pip install -e ".[mcp]" ruff mypy build
python -m unittest discover -s tests
python tools/check_architecture.py
ruff check src tests tools
mypy
python -m build --wheel
```

These checks run without model or search API calls. The source includes Node-based Web regression tests; Node.js is only needed to run those tests, not the application.
