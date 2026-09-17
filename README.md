<p align="center"><img src="src/epivra/web/favicon.svg" width="72" alt="Epivra" /></p>
<h1 align="center">Epivra</h1>
<p align="center">From questions to insight · Autonomous research on your desktop</p>
<p align="center"><strong>English</strong> · <a href="README.zh-CN.md">简体中文</a></p>

![Epivra English workbench](docs/images/home-en.png)

Epivra researches questions using the public web and your materials. Approve the initial strategy, then let the agents investigate, analyze, synthesize, write, and review findings with traceable sources. Pause, add materials, or change direction as needed.

## What you can do

- **Set the direction** — approve a strategy before research starts; pause or redirect it later.
- **Combine web and local materials** — search the web, upload files, or authorize folders and MCP resources.
- **Choose your providers** — use 12 official model providers and multiple search and reading services.
- **Work through Web, CLI, or MCP** — English and Simplified Chinese interfaces share the same local research records.
- **Keep the evidence** — retain sources, research artifacts, and usage records; export Markdown, Word, or HTML, use browser PDF/printing, and run optional data analysis.

## How research proceeds

Epivra draws on human research practices such as clarifying questions, evaluating evidence, selecting methods, checking counterevidence, and revising conclusions. These inform role responsibilities, tools, and artifact handoffs. The research path adapts to findings: the lead decides what to investigate, revisit, synthesize, or revise. Complete investigation results can go directly to writing.

The research kernel is the set of methods, instructions, and material contracts that organize research judgment. It spans role instructions, tool semantics, context, and original artifact handoffs; it is not another model. All roles share a custom Harness, with authorization, the call ledger, scheduling, and recovery enforced by code. Internal agents collaborate through persistent work and artifact references, without A2A; MCP connects external tools and clients.

The kernel influences how the model uses evidence, but quality also depends on the model, materials, tools, and actual context. Independent review and traceable citations do not guarantee correct judgments. Evaluate the conclusions, supporting evidence, and review reasoning together.

## Quick start

Requires **Python 3.11+**. Run from the project directory (Windows PowerShell):

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
.venv/Scripts/epivra.exe --lang en web
```

On macOS / Linux, use `.venv/bin/python` and `.venv/bin/epivra`. Windows is the primary platform validated so far.

1. Open **Connections & settings**, choose a provider, enter its API key, and select a model.
2. Describe your question and intended use, then choose the material scope.
3. Generate and approve the strategy. Epivra then proceeds with the research.

Switch languages in the Web header without losing your input. No Node.js, frontend build, or database server is required.

## Three ways to work

The commands below assume your virtual environment is activated:

| Interface | Command |
|---|---|
| Web workbench | `epivra --lang en web` |
| Interactive CLI | `epivra --lang en` |
| MCP server | Run `epivra start`, then `epivra-mcp --lang en` |

Use `--lang zh-CN` for Simplified Chinese, or set `EPIVRA_LANG`. Interface language does not translate source materials or reports; specify your preferred output language in the research request.

## Providers and extensions

| Capability | Supported options |
|---|---|
| Models | OpenAI, Claude, Gemini, Grok, DeepSeek, Qwen, Kimi, GLM, Doubao, MiniMax, Hunyuan, ERNIE |
| Search | Tavily, Exa, Brave, Perplexity, Bocha; DuckDuckGo fallback |
| Included public sources | Crossref, PubMed, Europe PMC, World Bank; no API keys required for these channels |
| Web reading | Jina, Tavily, Exa |
| Materials | Text, CSV/TSV, text-layer PDFs, XLSX; optional Docling document parsing and OCR |
| Analysis | Optional Docker Python sandbox for statistics, data processing, and charts |
| MCP | Connect external tools and resources, or expose research to other clients |

```powershell
# Install extensions as needed
python -m pip install -e ".[documents,mcp]"
# Optional data analysis
docker build -t epivra-analysis:1 sandbox
```

The default model is `deepseek-flash`. Only official model endpoints are supported; custom relay URLs are not. Model discovery and live account verification have different coverage. Unregistered models may need explicit capacity settings.

## Local data and privacy

Research records live in `.epivra/`, credentials in `.env`, and local parsing models in `models/docling/`. These are excluded from Git. Icons and interface assets are packaged with the application.

Local operation does not mean all data stays offline: online models, search services, and external tools receive the queries and materials needed for the task. Closing an interface does not stop background research; keep the computer and research host running.

## Help and project status

- [User guide](docs/USAGE.en.md): setup, configuration, research, MCP, backups, and troubleshooting.
- [Local models](models/README.en.md): downloads and directory layout.
- [Validation tools](evals/README.en.md): engineering checks versus research quality evaluation.

This is a development release. Features are integrated, but not all providers have been tested with live accounts. Cross-topic, long-document, and larger-scale research quality still needs validation. Passing engineering tests does not guarantee correct research conclusions; OCR is not semantic understanding of complex charts.
