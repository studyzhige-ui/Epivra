# Epivra user guide

**English** · [简体中文](USAGE.md)

Epivra is a local autonomous research workbench. Describe your question and approve a strategy; the agents gather materials, compare evidence, analyze, and write results. You can pause, add materials, or change direction.

## Interface language

Select **English** or **简体中文** in the Web header. Switching preserves your request and material selection. CLI and MCP accept `--lang en` / `--lang zh-CN`, or the `EPIVRA_LANG` environment variable. The CLI settings menu can also change the current session's language.

MCP tool names, parameters, and protocol states remain stable; descriptions use the selected language. Interface switching never rewrites user input, sources, or existing reports. Specify your preferred report language in the research request.

## 1. Install and start

Requires Python 3.11+. From the project directory in Windows PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
.venv/Scripts/epivra.exe --lang en web
```

The browser opens automatically. No Node.js, frontend build, or database server is required. If the port is occupied, use `epivra web --port 0`. Closing the browser does not stop research. Keep the computer and host running; system sleep interrupts execution.

For the terminal workbench, run `.venv/Scripts/epivra.exe --lang en`. On macOS/Linux use `.venv/bin/python` and `.venv/bin/epivra`; Windows is the primary platform validated so far. Commands below assume an activated virtual environment or the equivalent full executable path.

### Startup command and arguments

After installation, start from the project directory without reinstalling or activating the virtual environment:

```powershell
.\.venv\Scripts\epivra.exe --lang en web --port 0
```

| Part | Meaning |
|---|---|
| `.\.venv\Scripts\epivra.exe` | Run Epivra from this project's virtual environment. The old `deep-research.exe` command is retired. |
| `--lang en` | Select English; use `--lang zh-CN` for Simplified Chinese. When omitted, `EPIVRA_LANG` applies, falling back to Simplified Chinese. |
| `web` | Start the Web workbench and open the browser. Without this subcommand, Epivra opens the interactive CLI. |
| `--port 0` | Let the system choose an available port and print the actual URL. Omit it to use port `8765`, or specify a port such as `--port 8080`. |

Place the language option before `web` and Web options after it, as shown above. Port `0` requests an available port rather than listening on port zero. The selected port may change between launches; use the complete URL printed for the current launch. You can still switch languages in the Web header.

Append `--no-browser` to run without opening the browser automatically. To list Web options:

```powershell
.\.venv\Scripts\epivra.exe web --help
```

## 2. Configure connections

Open **Connections & settings**, choose a model provider and account region, enter an API key, then choose a model. The Web model picker fetches available models and filters by characters: for example, `gpt5` matches `gpt-5.5`. Manual model IDs are also accepted. Where an account-list endpoint has not been verified, the interface explicitly shows local presets. If a model has no capacity metadata, enter context and output limits from its official documentation.

The CLI supports provider, key, and model configuration; the searchable model picker is currently a Web feature.

Official adapters cover OpenAI, Claude, Gemini, Grok, DeepSeek, Qwen, Kimi, GLM, Doubao, MiniMax, Hunyuan, and ERNIE. The default is DeepSeek / `deepseek-flash`. Custom relay URLs are not supported. Model access and rate limits depend on your provider account.

Search providers: Tavily, Exa, Brave, Perplexity, and Bocha. DuckDuckGo provides a key-free fallback, with no availability guarantee. Web reading uses Jina, Tavily, or Exa. Configure only the services you use.

Keys are stored locally in `.env`; environment variables take precedence. Defaults live in `.epivra/cli-settings.json` and apply to new research. Usage displays recorded provider counters, not an invoice or prediction of your remaining balance.

## 3. Run research

1. Describe the question and intended use. Optionally specify dates, readers, and output format.
2. Choose public web, web plus local materials, or local materials and selected MCP connections only.
3. Select or upload files, or authorize a folder. A single-file import grants access to that file; folder authorization permits on-demand searches inside it.
4. Generate and read the initial strategy, then approve its scope and approach.
5. Use **My research** to view progress and results. Research proceeds autonomously; genuine blockers such as quota or credential problems are reported.

Strategy generation also calls the model. Use explicit pause and direction controls to change a task. When a revised strategy needs approval, review the current version. Do not edit the database or intermediate files to control research.


### Citations and repeated failures

Epivra validates citations and numbers sources in order of first appearance. Repeated citations of the same source reuse its number; the bibliography lists the sources actually cited. Passage citations also verify the original text location. Review and delivery use the same numbered manuscript. Zero-citation reports are allowed; valid citation formatting does not prove that evidence supports a conclusion.

After three consecutive rounds with the identical protocol error or invalid call and no successful operation or new research material, that work stops retrying automatically and retains its reason. The lead can change the method or obtain additional material. This type of block is reconsidered when new material arrives; you can also pause and resume after addressing the cause. Normal investigation, different operations, and necessary revisions have no fixed round limit. Paid calls with unknown outcomes are still never automatically resent.

## 4. Parsing and analysis

The base installation handles text, CSV/TSV, text-layer PDFs, and XLSX. Spreadsheet formulas are read but not recalculated. For scanned PDFs, image OCR, DOCX/PPTX, and other complex materials:

```powershell
python -m pip install -e ".[documents]"
```

Local models are automatically discovered in `models/docling/`. After a fresh clone, follow the [model guide](../models/README.en.md) to download them. Missing dependencies, incomplete models, and parser failures are reported. OCR does not interpret charts; important figures and complex layouts still need review.

Statistics, charts, and Python analysis require Docker running Linux containers. Build the image once:

```powershell
docker build -t epivra-analysis:1 sandbox
```

Enable analysis in settings. Containers have no network access and receive only the authorized inputs for that task, not credentials or the whole project. Docker is unnecessary when analysis is disabled.

## 5. Bidirectional MCP

```powershell
python -m pip install -e ".[mcp]"
epivra start
```

Other clients can use Epivra through `epivra-mcp --lang en --root <absolute-project-path>`. Start the research host independently first; it must not depend on the MCP client's process lifetime. Strategy approval through MCP is disabled by default.

Example client configuration; replace paths with your installation:

```json
{
  "mcpServers": {
    "Epivra": {
      "command": "D:/Projects/Python/Epivra/.venv/Scripts/epivra-mcp.exe",
      "args": ["--lang", "en", "--root", "D:/Projects/Python/Epivra"]
    }
  }
}
```

To connect Epivra to an external MCP server, define a named connection in local `mcp-servers.json`. HTTP example:

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

Public services may omit `token_env`. Keep tokens in the environment or `.env`. Run `epivra mcp-discover materials`, then explicitly allow the required tools and exact resource URIs. A tool entry looks like `"lookup": {"roles": ["investigator", "reviewer"], "write": false}`. Only connect trusted services; `write: true` is advance authorization for external writes.

To expose Epivra through local HTTP MCP, set a separate `EPIVRA_MCP_TOKEN` environment variable and run `epivra-mcp --lang en --transport http`. Clients use Bearer authentication. The service listens on loopback only; this product does not provide public multi-tenant hosting.

## 6. Files, backups, and upgrades

| Location | Purpose | Tracked by Git |
|---|---|---|
| `src/epivra/` | Code, Web interface, icons, translations | Yes |
| `models/docling/` | Local parsing models | No; instructions and manifest are tracked |
| `.env` | API credentials | No |
| `.epivra/` | Research database, materials, settings, recovery records | No |
| `mcp-servers.json` | Local external-tool connections | No |
| `.venv/` | Python environment | No; reinstall dependencies |

Before a backup, pause tasks and wait for in-flight work to finish. Run `epivra shutdown`, then copy the entire `.epivra/` directory. Back up credentials and MCP configuration separately and securely if needed. Do not copy only the database and omit material files. Stop the Web server separately in its terminal.

Epivra does not automatically import the old project's `.deep-research-agent/` data. Keep the old directory and use its previous installation to read historical research. Installation and research roots may differ; specify `--root` to avoid accidentally creating separate workspaces by launching from different directories.

## 7. Troubleshooting and current limits

- **Model discovery fails:** check the key, region, account permissions, and network. Listing and inference permissions may differ.
- **A new key has no effect:** check for an overriding environment variable. Reload credentials for paused tasks before resuming.
- **Scanned materials fail:** verify that the documents extension and complete local model directory are installed.
- **Analysis will not start:** check Docker and the `epivra-analysis:1` image.
- **Research is blocked:** follow the task's message, fix the cause, and resume instead of creating a duplicate task.

Features are integrated, but live provider verification and cross-topic/long-document evaluations still have coverage gaps. Research conclusions are not guaranteed correct; review important sources, limitations, and uncertainty. Engineering tests do not replace research quality evaluation.
