# Read-tool contract experiment / 读取工具合同实验

## Scope and preregistered interpretation

This batch changes model-visible tool contracts and deterministic report measurements, not research role instructions or permission policy. `COMMON`, `ROLES`, and `WRITING_GUIDES` are unchanged. The earlier paid baselines and their failures remain visible in PR #2; no grading labels are relabeled here.

1. Both generic artifact readers already reject source bodies for lead and reject execution/private record kinds. Advertise those restrictions before a call and share the same rejection helper between handlers. Do not grant new permissions or prescribe a new research workflow.
2. Reuse one exact `report_metrics` function for rendered `measure_text` and `read_report`. Preserve existing full and page metrics. The body boundary is the stored start of host-generated references, not an inferred semantic body: author titles, headings, notes, tables, Markdown and inline citation markers still count. Missing legacy boundaries produce null body metrics. Malformed boundaries fail explicitly. No new length-compliance or semantic publication gate is added.

The hypothesis is that clearer tool capabilities can reduce preventable invalid calls, and shared deterministic receipts can avoid inconsistent count bases. A successful example is not proof of a general prompt or research-quality improvement. Both no-improvement outcomes and counterexamples must be recorded.

## Small paired live probe

`read-contract-eval.yml` checks out candidate and fixed baseline `96968e399832aea53e016434841fa9be52d48fb5`. Separate processes import the chosen implementation via explicit PYTHONPATH; the runner verifies that import path. Both arms execute the identical case code with the same DeepSeek configuration. Source-code, evaluation-input, environment, role-instruction and output fingerprints are recorded. Provider-side variation and order/cache effects are not eliminated by this one pair.

Four probes inspect only the first real model turn: lead/investigator each receive a Chinese attendance register or English service log. Lead should arrange investigation without forbidden source reads; investigator should still be able to read originals. These are interface-selection probes, not complete research, memory, cancellation or collaborative-quality tests.

Two short final-review probes put a report just within or just above an explicitly defined non-whitespace Unicode-code-point limit. Both have a host-generated bibliography and inline citations. The expected count comes independently from the author template with canonical citation markers, and expected decisions remain outside Agent input. The user constraint itself is explicit about scope; this does not claim to solve ambiguous human notions of word count or substantive body.

Reports are reviewed through normal Harness execution. A clarification or missing review is incomplete, never auto-accepted. All review reasons must still be independently checked against the exact report and source. Scripted unit tests separately exercise Unicode, whitespace, tables, manual headings, absent and invalid legacy boundaries, paging, reopen and native wire descriptions.

This fixed six-case experiment is authorized ordinary small live testing. It is not Benchmark-10, a replacement for held-out tasks or a leaderboard result. Job runtime and case selection constraints apply only to this test; normal research total budgets remain unchanged. Do not add many requests to bypass owner approval for a comparably expensive evaluation.

## Reproduction and evidence boundaries

Run only via a fresh request/run identity. A repeated Actions attempt is refused rather than silently repeating paid calls. Raw DB/provider protocol and private reasoning are not uploaded. Export uses the existing public projection, secret scrubbing and SHA-256 manifest. The temporary runner cannot provide cross-runner recovery after termination; incomplete or unknown outcomes remain failures.

Results belong in the PR evidence comment with exact commits, run/artifact IDs, usage and source-based adjudication. Keep original failed results. Do not change a role prompt merely to make these probes green.

## Primary references consulted (2026-09-19)

- OpenAI, Function calling: https://developers.openai.com/api/docs/guides/function-calling — describe tools, parameters and when they should or should not be used; move deterministic work to code where appropriate.
- Anthropic, Writing effective tools for agents: https://www.anthropic.com/engineering/writing-tools-for-agents — clear, useful tool contracts and responses; validate tool design against agent behavior.
- Google, Function calling: https://ai.google.dev/gemini-api/docs/function-calling — clear function/parameter descriptions and explicit implementation of tool calls.

These are design references, not evidence that a particular description changes DeepSeek behavior. No external product code or report-specific instructions are copied.

## 中文摘要

这次只让模型提前知道现有读取权限，并让作者和核查者使用相同、可解释的确定性报告计数。正文范围仅按已经保存的自动参考资料边界划分，不擅自删除作者标题、字数注记或引用，也不自动决定用户是否满意。研究角色、权限和常规研究预算政策不变。

六个微型场景对照同一基线和候选实现。lead/investigator 场景仅测第一回合的工具选择，两个核查场景测明确范围下的长度判定及其理由；不冒充完整研究或泛化测试。新离线用例同时覆盖相反方向：避免 lead 越权，又不阻止 investigator 读取；检测超限，又不把自动参考文献误算成正文而拒绝合格稿。
