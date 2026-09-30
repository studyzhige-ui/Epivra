# Execution ownership and offline validation

Epivra has one local Host event loop. Interface code requests changes; the
research service schedules work; the Harness crosses durable execution
boundaries; infrastructure supplies independent capabilities. The dependency
allow-list in `tools/check_architecture.py` is executable documentation.

## Responsibilities

| Owner | Responsibility | Must not own |
| --- | --- | --- |
| `Store` | Accepted control epochs, frozen work/requests, operation admission and settlement, immutable evidence and publication/review binding | Provider I/O or UI state |
| `ResearchService` | One driver per study, work scheduling, entry into a new control epoch, disposable work errors | Rewriting operation outcomes or resending unknown calls |
| `AgentRuntime` | Cross-study fair execution turns and observable execution phases | Provider quotas, retry policy, durable work |
| `Scheduler` | Shared provider concurrency, rolling rate/spacing windows, cooperative waiting and joint live-resource admission | Research authority, durable operation outcomes or provider requests |
| `Harness` | Frozen request construction, final authority check, durable admission before sending, settlement before epoch recheck, bounded recovery | User form state or HTTP transport decoding |
| `adapters` / `DirectReader` | HTTP transport, one content-decompression boundary, representation decoding and provider envelopes | Research decisions or UI recovery |
| `materials` | Bounded local-file acquisition and isolated parsing | Study controls or provider calls |
| `native_analysis` / `sandbox_windows` | Native job lifetime, monitored scratch/output validation, Windows LPAC and process/handle ownership | Research decisions or an unrestricted execution fallback |
| `Host` | Authenticated interface dispatch and composition of the shared services | Duplicated file-reading or rate-limit policies |
| Web app | Draft, pending-import and dialog lifetimes; rendering accepted Host state | Inferring successful writes from an uncertain response |
| `mcp_client` / `mcp_tools` | Owned session lifetime, frozen tool discovery and cancellable per-connection prepared turns | A second dispatch queue after durable admission |

The changes deliberately preserve the existing modules rather than adding a
parallel runtime or relocating unrelated business logic.

## Control and send invariants

1. An accepted `resume` advances the durable control epoch. `start()` only ensures
   a driver exists. The driver clears disposable blockers once when it enters
   the new epoch, after all older executions settle. Fast pause/resume and a
   restart after a settled pause therefore have the same recovery semantics. Every
   settled driver exit rechecks accepted control, including ordinary old-epoch
   failures, so an error cannot swallow a concurrent resume.
2. Queued, unsent work is cancellable. Both provider waits and Agent waits check
   current authority at most every 250 ms while the event loop is responsive.
   Withdrawal removes queue entries and releases live resources without creating
   an operation record. A different study's slow provider does not block this.
3. Provider readiness does not reserve rate allowance. If an Agent turn is also
   needed, acquire it only after initial provider readiness, then recheck quota
   and concurrency. If readiness changed, release the Agent turn and wait again.
   No provider slot is held while waiting for an Agent, and no Agent turn is held
   while waiting for rate capacity. FIFO provider tickets prevent new requests
   from overtaking existing waiters; tickets are released before waiting for an
   Agent turn, and release/cancellation notifications promptly wake the next
   eligible waiter.
4. Once both resources are ready, the event loop commits the rate/concurrency
   allowance without suspension. The Harness then persists admission and marks
   invocation before calling the adapter. Waiting time is never counted as a send.
   Restart restoration uses persisted invocation time when present, and falls
   back conservatively to admission time for older or uncertain records.
5. A sent request is different from a queued request. Pause stops new admissions
   but allows sent responses to settle. Cancellation/shutdown after sending
   preserves an unknown outcome. Resume/restart cannot automatically replay that
   paid request. Settled responses can be reused without another provider call.
6. Frozen request checks, evidence validation and exact manuscript/review binding
   remain unchanged. Clearing a runtime work error never erases these records.
7. MCP session setup, serialized-turn waiting and paginated definition refresh all
   precede joint Scheduler admission. The session owner opens/closes its SDK
   context; the turn holder sends directly after durable admission, with no
   downstream private queue. Pause/cancel can withdraw unsent preparation without
   creating an unknown operation. Once dispatched, an interrupted MCP read/write
   still preserves its unknown result and cannot automatically replay.

## Input boundaries

- `httpx.Response.aiter_bytes()` supplies decompressed bytes. The shared
  `decoded_response()` constructor removes original Content-Encoding and
  Content-Length before decoding those bytes again as a representation. It keeps
  Content-Type/charset, status and useful provider headers. Both JsonAPI and
  DirectReader use the same rule.
- `materials.read_file()` opens once, checks the opened handle is a regular file,
  rejects known oversized files before reading, reads at most the input cap plus
  one byte, then rejects oversized/grown/changed inputs. The parser keeps its own
  bytes-level check for other callers. POSIX nonblocking open prevents a replaced
  FIFO path from hanging the shared Host.
- CLI uploads and reconciliation response files use the same acquisition boundary
  with a smaller transport-specific cap. The Host client checks the encoded IPC
  frame before opening a connection, including JSON escaping expansion.
- Native analysis accepts ordinary files/directories, not hidden NTFS named data
  streams. The Windows adapter enumerates streams on both writable roots and
  every nested entry, rejecting named streams and unexpected enumeration errors.
  Both scratch and output are checked again after the worker is reaped, before a
  successful result is accepted. This remains periodic monitoring rather than a
  hard filesystem quota; transient writes between polls are not quota-enforced.

## Frontend lifetimes

- Creating research locks its complete draft controls across create, import and
  resume. Only acknowledged draft inputs are retired; later file-picker events
  or programmatic changes belong to the next draft and survive.
- After create is acknowledged, pending files belong to that study. Successful
  imports leave its pending list individually. Failure retains the remaining
  files in Supplement, where the user can retry or remove them. Retrying imports
  neither creates another study nor silently resumes research. This list is
  explicitly page-local, not a durable upload queue; the UI warns to import it
  before closing the page. Source files on disk are never deleted.
- Settings has one session in loading, editing or saving phase. Every asynchronous
  callback carries that session's ownership. Close/Escape invalidates it, so old
  settings, MCP, model-list and component responses cannot reopen the dialog,
  replace a newer edit or unlock fields during save. Save keeps existing partial
  credential/default-persistence disclosures and does not issue a paid test call.

## Run the public regressions

Use Python 3.11+ and Node.js 22+:

```sh
python -m pip install -e ".[mcp]" ruff mypy build
python tools/check_source.py --wheel-dir dist
```

The same entry point runs on pull requests, main pushes and desktop builds. It
checks architecture, Ruff, the configured mypy surface, Python `unittest`, every
bundled JavaScript file's syntax and Node's frontend tests. `--wheel-dir` adds an
isolated source-wheel build. PR jobs check out the exact head commit. The desktop
workflow also runs its native analysis and relocated-app smoke checks on same-repository PRs,
with publication disabled for PR events. Publishing remains limited to version
tag pushes or an explicit manual publish request.
Release publication verifies archive checksum and source provenance. Retries
never overwrite assets: existing uploaded digests must match exactly before any
missing files can be added or the verified release marked Latest.

Focused commands:

```sh
python -m unittest discover -s tests -v
node --test tests/frontend/lifecycle.test.cjs
```

- `test_execution_lifecycle.py` uses real Store, Harness, Scheduler, AgentRuntime,
  ResearchService and Host dispatch with controlled clocks/providers. It covers
  long queues, RPM/TPM, fair cancellation, pause/resume ordering, upload/reload
  after pause, frozen requests, settlement and unknown-result non-replay.
- `test_input_boundaries.py` uses real imports/parsers and HTTP MockTransport. It
  covers compressed/plain/Markdown/HTML bodies, character sets, fallback policy,
  bounded reads, growth races, sparse oversized inputs and the existing upload API.
- `tests/frontend/` loads the complete app and real handlers in a dependency-free
  DOM harness, with delayed/reordered API responses. Native browser focus/layout
  is a separate validation surface.
- Provider contract fixtures cover every configured model/search/public-source
  adapter without network calls. The complete research journey exercises source
  reading, evidence, findings, writing ownership, exact independent review,
  publication, export, restart and archive import with a deterministic model.
- Integrity tests reject stale evidence/bases/manuscripts, invalid citations,
  cross-work replay of unknown requests and unauthorized filesystem access, and
  verify additive legacy-schema migration. Web boundary tests run the real
  loopback Server/App/Host; MCP tests use the real SDK's in-process transport.
- Component/stream tests cover integrity manifests, process output/deadline
  bounds, credential stripping, Windows enumeration error handling and tiny
  real Windows named-stream fixtures. Native acceptance also probes running and
  fast-exit LPAC writes in root/nested output and scratch entries. Translation
  tests check literal Python templates and placeholder parity.
- MCP admission tests exercise the complete connect-tools/Harness/Store route
  across queued reads/writes, setup and discovery interruption, quota rechecks,
  definition rejection, real SDK session borrowing and owner-close unknowns.
  Interface tests share the Host distinction between a valid blocked status and
  an error-only failed read (for example, a study deleted by another client).

No API credentials, model/search calls or private evaluation materials are
required. These deterministic checks establish application contracts; they do
not establish model quality, live provider protocol compatibility, Windows LPAC
behavior, or OS-specific release correctness. Native platform smoke checks and
separately authorized provider evaluations remain necessary for those claims.

Native-browser smoke (all API responses mocked, loopback assets only):

```sh
npm install --no-save playwright@1.62.1
npx playwright install chromium
node tests/browser/lifecycle-smoke.cjs
```

Set `EPIVRA_CHROMIUM` (or `$env:EPIVRA_CHROMIUM` in PowerShell) to use an existing
Chromium executable instead. This check covers native Escape/modal behavior,
actual disabled form controls, retained File inputs, partial-import retry and
save dismissal. Source validation runs it in a separate read-only hosted Linux
job against the same exact head commit. Browser dependencies and screenshots are
kept outside the checkout; there are no provider calls or user credentials.
Local execution requires a runtime allowed to launch Chromium.
