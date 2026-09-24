# Epivra user guide

**English** · [简体中文](USAGE.md)

Epivra is a local autonomous research workbench. Describe your question and approve a strategy; the agents gather materials, compare evidence, analyze, and write results. You can pause, add materials, or change direction.

## Interface language

Select **English** or **简体中文** in the Web header. Switching preserves your request and material selection. CLI and MCP accept `--lang en` / `--lang zh-CN`, or the `EPIVRA_LANG` environment variable. The CLI settings menu can also change the current session's language.

MCP tool names, parameters, and protocol states remain stable; descriptions use the selected language. Interface switching never rewrites user input, sources, or existing reports. Specify your preferred report language in the research request.

## 1. Download, open, and quit

Desktop downloads include Python and require no Git, Node.js, or database installation. Choose a package from the [GitHub Release](https://github.com/studyzhige-ui/Epivra/releases/tag/v0.3.0):

| Platform | Steps |
|---|---|
| Windows 10/11 x64 | Download the Windows ZIP, extract the complete folder, and open **Epivra.exe**. |

This is an unsigned desktop preview. Windows may report an unknown publisher. macOS is no longer a build or verification target. Downloads require an authorized GitHub account while the repository is private.


Your browser opens automatically, showing connection settings on first launch. Opening Epivra again reuses the running workbench. Closing the browser keeps research running; use **Quit** in the Epivra control window to stop the background service. Wait for component installation to finish before quitting. Computer sleep interrupts execution.

### Data and upgrades

The control window opens your **Data folder**:
- Windows: `%LOCALAPPDATA%\Epivra`

Paths such as `.env`, `.epivra/`, `.epivra-components/`, and `mcp-servers.json` in this guide are relative to that folder. Before upgrading, quit Epivra and back up the entire data folder, then replace the application. Keep credentials and research out of the installation folder. Use `epivra-desktop --root <absolute-path>` to open an existing source workspace; existing data is never migrated automatically.

### Run from source (developers)

Requires Python 3.11+. From the project directory on Windows:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install ".[mcp]"
.venv/Scripts/epivra-desktop.exe
```

Source Web/CLI commands default to the current directory; the desktop entry defaults to the user data folder above. Pass `--root` explicitly to use the same workspace.

For manual server operation use `epivra --root <path> --lang en web --port 0`; see `epivra --help` for automation. CLI commands below assume a source installation and an activated virtual environment.

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

Generating the initial route calls the model. The route describes the question, material scope, methods, and deliverables without prescribing an answer. Approval is required once; the research owner then works within the approved permissions. Adjusting direction does not require another approval. Pause and wait for active execution to settle before adding materials or reloading credentials. Do not edit the database or intermediate files to control research.

The owner can investigate original sources, record findings and conflicts, prepare a writing basis, and revise the manuscript directly. It may delegate focused investigation, synthesis, or writing tasks when useful; roles are not a mandatory pipeline. External MCP capabilities are used through authorized assistants.

Investigators return evidence and suggestions without editing the manuscript. Delegating a writer hands over the current manuscript exclusively; the owner resumes editing after completion or cancellation. Cancellation preserves saved work and is displayed separately from delivery.

Drafts are saved and revised continuously but are not published reports. An independent reviewer must accept the exact current manuscript before publication. Defects return to revision or further investigation, and changed manuscripts require another review. Reports have no default word limit. Local-material mode disables built-in web channels; selected external MCP services may still access the network.


### Citations and repeated failures

Epivra validates citations and numbers sources in order of first appearance. Repeated citations of the same source reuse its number; the bibliography lists the sources actually cited. Passage citations also verify the original text location. Review and delivery use the same numbered manuscript. Zero-citation reports are allowed; valid citation formatting does not prove that evidence supports a conclusion.

After three consecutive rounds with no tool action, or the same protocol error or complete sequence of failed calls, and no successful operation or new research material, that work stops retrying automatically and retains its reason. The lead can change the method or obtain additional material. This type of block is reconsidered when new material arrives; you can also pause and resume after addressing the cause. Normal investigation, different operations, and necessary revisions have no fixed round limit. Paid calls with unknown outcomes are still never automatically resent.

Normal research has no total call, token, cost, or elapsed-time cap. Explicit provider rejections have a separate recovery guard: one operation can be recovered at most five times within one control epoch. After that guard is reached, pause and resume explicitly before trying the operation again; this protects resources without limiting research depth.

## 4. Parsing and analysis

Text and CSV/TSV default to UTF-8. Select `gb18030` when creating a study for older Chinese files, or pass `create --text-encoding gb18030` in the JSON CLI. Encoding is fixed per study; original bytes are retained and decoding errors are reported without replacement characters. Automatic PDF fallback converts only pages with visual content but no extracted text, preserving original page numbers.

Set `EPIVRA_CONTACT_EMAIL` in the host process environment to supply a real contact email to PubMed (email) and Crossref (mailto). Without it, public access remains available.

The base installation handles text, CSV/TSV, text-layer PDFs, and XLSX. Spreadsheet formulas are read but not recalculated. For scanned PDFs, image OCR, DOCX/PPTX, and other complex materials, desktop users choose **Connections & settings → Optional features → Install OCR**. Wait for packages and models to finish downloading. New research then uses them automatically, without a manual model path. Downloads can require several GB; keep Epivra running during setup.

For a source installation, install dependencies manually:

```powershell
python -m pip install ".[documents]"
```

In a source installation, local models are automatically discovered in `models/docling/`. After a fresh clone, follow the [model guide](../models/README.en.md) to download them. Missing dependencies, incomplete models, and parser failures are reported. OCR does not interpret charts; important figures and complex layouts still need review.

A single material is limited to 256 MiB, parser output to 64 MiB, and an authorized directory snapshot to 100,000 entries. These are resource-protection limits, not research source-count limits; use smaller roots or split oversized materials when necessary.

Python analysis runs in the built-in Windows x64 sandbox. In Settings choose
**Prepare built-in Python analysis**, wait for local extraction and verification,
then enable it. No Docker or separately installed Python is required.

The bundled runtime includes scientific, statistical, ML, chart and Excel/Parquet
libraries. Scripts receive only staged authorized inputs and cannot use the
network or arbitrary local files. Process/memory/CPU restrictions and timeouts
apply; output/scratch size limits use monitoring, not hard disk quotas.

Source developers first run `python tools/build_analysis_bundle.py`. This build
downloads and verifies the pinned runtime, compiler and wheels; downloaded desktop
users do not run it. The published 0.3.0 package predates this feature.

## 5. Bidirectional MCP

Desktop packages include MCP dependencies; opening Epivra starts its host. External MCP servers may still need their own commands or runtimes, which Epivra does not install. The following commands are for source installations:

```powershell
python -m pip install ".[mcp]"
epivra start
```

Other clients can use Epivra through `epivra-mcp --lang en --root <absolute-project-path>`. Start the research host independently first; it must not depend on the MCP client's process lifetime. Strategy approval through MCP is disabled by default; add `--allow-approval` when explicitly authorizing the connected client to approve routes.

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

MCP creates a paused research draft. Upload materials, resume to generate a route, and approve it through Web/CLI or an authorized MCP client. Control requests require the current control version and a unique command ID; approval also requires the exact route reference.

External connections are fixed when a study is created. Editing the configuration does not add permissions to existing studies. Tool roles may be `investigator`, `synthesizer`, `writer`, or `reviewer`; `lead` is not accepted.

To expose Epivra through local HTTP MCP, set a separate `EPIVRA_MCP_TOKEN` environment variable and run `epivra-mcp --lang en --transport http`. Clients use Bearer authentication. This HTTP token is read from the process environment, not `.env`. The service listens on loopback only; this product does not provide public multi-tenant hosting.

## 6. Files, backups, and upgrades

| Location | Purpose | Tracked by Git |
|---|---|---|
| `src/epivra/` | Code, Web interface, icons, translations | Yes |
| `models/docling/` | Local parsing models | No; instructions and manifest are tracked |
| `.env` | API credentials | No |
| `.epivra/` | Private research database, materials, settings, recovery records | No |
| `mcp-servers.json` | Local external-tool connections | No |
| `.venv/` | Python environment | No; reinstall dependencies |

Before a backup, pause tasks and wait for in-flight work to finish. Run `epivra shutdown`, then copy the entire `.epivra/` directory. Epivra protects this directory for the local owner; it does not change permissions on user source folders. Back up credentials and MCP configuration separately and securely if needed. Do not copy only the database and omit material files. Stop the Web server separately in its terminal.

Installation and research roots may differ. Specify `--root` to avoid creating separate workspaces by launching from different directories. Before upgrading, back up the complete workspace and retain a rollback version of the application. Studies with incompatible runtime contracts remain available for inspection and export, but cannot resume implicitly; create a new study with the required materials to continue investigation. Data directories are not migrated automatically. Completed studies can be imported explicitly with the `import_study` command listed by `epivra --help`.

## 7. Troubleshooting and current limits

### Long tasks and recovery

Growing directories and large materials enter the model window through bounded pages, with the original request and current approved scope retained first. Memory and evidence anchors are checked against the full context allowance before saving. Oversized working sets from older versions retain their originals and expose references for paged recovery. Retrievable material is not proof that the model has read or understood it.

Pause or redirect stops new calls from the previous control epoch; already sent requests still need to settle. Recovery reuses saved responses. Unknown outcomes block automatic resubmission: resolve the reported issue before resuming instead of creating a duplicate study. Incompatible model or tool contracts may prevent continuing old work; back up the workspace before upgrading.

Provider caching is an optimization, not a recovery dependency. Usage reports show provider-reported cache counters; missing values are not zero. Explicit caching is not enabled for every interface.

- **Model discovery fails:** check the key, region, account permissions, and network. Listing and inference permissions may differ.
- **A new key has no effect:** check for an overriding environment variable. Reload credentials for paused tasks before resuming.
- **Scanned materials fail:** verify that the documents extension and complete local model directory are installed.
- **Analysis will not start:** prepare the built-in component in Settings. If verification fails, inspect .epivra-components/setup.log; do not disable sandbox restrictions.
- **Research is blocked:** follow the task's message, fix the cause, and resume instead of creating a duplicate task.

Research conclusions are not guaranteed correct; review important sources, limitations, and uncertainty. Engineering tests do not replace research quality evaluation.

## Included public sources and research strategy

New network-enabled studies automatically offer Crossref (publication metadata), PubMed (biomedical discovery and records/abstracts), Europe PMC (life-science literature and available abstracts), and World Bank (indicator definitions and observations). These four channels require no API keys. Models and paid search services still use their own credentials. Local-only studies do not access these channels; existing studies retain their original tool bindings.

Investigators choose channels for the question rather than searching every service. Metadata and abstracts are not full text, and missing indicator values are not zero. Original records, dates and provenance are preserved. World Bank data queries require indicator codes; agents can browse the catalogue or verify a definition first. Public services can throttle or fail; errors remain explicit so agents can revise their approach.

Tavily supports structured domain and publication/update-date filters; these options are rejected for providers without that support. Initial strategies briefly propose focus, time scope, methods and deliverables. With no specified genre, writers organize findings freely. For an explicit genre they can read short writing guides; user templates take precedence. Strategies and guides do not guarantee correct conclusions: evidence-based research and review remain necessary.

### Research elapsed time

The Web study header, CLI study details and MCP status response expose elapsed time from first strategy approval to publication of the current result. This includes pauses, provider waiting and offline time. Cancellation stops the clock; changing direction retains the original start. It is neither compute time nor an estimated completion time. Older studies without complete timestamps show “Not recorded”; file modification times are not used to reconstruct a duration.

### Cancel and delete

Cancel stops research while keeping its records. Completed studies offer “Adjust direction” and “Delete study”; ongoing studies also offer “Stop and delete”. Web and CLI require confirmation. MCP delete_research requires explicit user authorization, the observed control version and confirmed=true.

Deletion stops study agents, parsing tasks and dedicated tool connections, cleans its analysis containers/staging, then removes report, source-copy, usage and execution records. Cleanup failure retains the deletion intent for retry; host restart continues cleanup. User originals, exported copies, shared models/settings and other studies are retained. Already submitted external calls cannot be recalled or unbilled. Export anything you wish to retain before deleting.

### Usage by function

Usage is grouped by provider, model and function (for example, Tavily search versus extraction). Only reported metrics are displayed: zero is retained and missing data is not treated as zero. Partial reporting includes the number of covered calls. Jina Reader tokens are separate from LLM input/output; literature endpoints without metering show call counts only. Exa dollar amounts are provider references, not settled invoices. HTTP errors and unknown outcomes are separate; call counts do not imply successfully retrieved sources.


The Web workbench keeps the research plan available and offers expandable public findings, a report outline, expanded reading, citation excerpts and saved source text. Export supports Markdown, Word, standalone HTML and PDF/Print (Save as PDF in the browser). Word preserves original formula notation. Export does not rerun research.


## When research is ready for writing

The owner assesses each original question against its required answer, evidence, meaningful remaining gaps and stopping reasons. Expand progress to see further investigation, readiness or a limited answer. These are model judgments, not completeness certificates. Reflection uses normal research turns; there is no mandatory search-round or source-count target.

New retrieval results, sources or research handoffs must be considered before an existing writing basis can authorize delivery. Repeated reads do not repeatedly reopen research. Identical successful web requests reuse the current direction's snapshot; the researcher can explicitly refresh when newly acquired data is needed. Publication still requires independent editorial review.

After this research-contract upgrade, earlier studies remain readable and exportable; start a new study for execution. Finish existing work and restart an already running service to load the updated code.

Context is managed against the selected model window for each role, reserving its configured output allowance. Reads fit the remaining capacity of the complete request instead of fixed 48,000-character context or 12,000-character result ceilings. Explicit smaller read limits are honored. Window checks retain the adapters’ local estimates and reported usage calibration; they neither fill every request nor guarantee exact use of every advertised token.
