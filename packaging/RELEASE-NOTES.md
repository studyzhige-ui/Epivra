# Epivra 0.3.6 · Windows x64

## 本次更新

- 整理研究上下文顺序，优先保留原需求、当前研究状态、工作记忆和最近取得的内容。
- 长任务接近模型窗口容量时，先将可重新读取的较旧工具正文换成回读入口，再按需保存进度摘要并继续。原始资料和正式研究记录保留，可按需回读；最近读取与显式交接资料仍受保护。
- 工作摘要通过现有执行账本持久化，暂停、重启和中断后继续时复用已结算响应，避免重新购买摘要。未知结果、无效摘要和超大记忆不会覆盖原窗口。
- 澄清调查、核实、写作和编辑的指令与工具边界；写作者复用负责人当前问题评估，定点检查与整稿接受使用各自的交付合同。
- 区分目录、原文、研究记录和文稿的读取，以及进度记忆、解释笔记、精确证据和正式判断；加入按当前角色与阶段选择的少量操作示例。
- 更新工具顶层说明文字后，仍可回放原已结算响应。工具参数、权限、绑定或运行合同变化时，现有保护继续生效。

## 使用与升级

先退出旧程序并备份整个数据目录，再完整解压 ZIP，打开 Epivra.exe。现有工作区不会自动迁移；历史报告仍可查看和导出，不兼容运行合同的未完成研究需要新建。

长任务的进度摘要使用该任务配置的模型，可能产生模型调用费用；它是工作记忆，不替代原始资料。重要结论仍应结合引用核对。此版本没有改变默认模型、搜索供应商或研究费用策略。

Windows 10/11 x64，未签名。内置受限 Python 数据分析，OCR 仍为可选下载。

工程验收：127 项离线测试，123 项通过、4 项平台跳过；架构检查、Ruff、类型检查及独立审查通过。离线工程验证不证明真实模型的研究质量、摘要保真度或 token/费用收益。

## Changes

- Order research context around the original request, current state, working memory and recent results.
- When long-running work approaches its model window, replace retrievable older tool bodies with read-back handles before saving a progress summary and continuing. Original sources and canonical records remain available; recent reads and explicit handoff references remain protected.
- Persist summaries through the existing execution ledger. Pause, restart and interrupt/continue reuse settled responses. Unknown outcomes, invalid summaries and oversized memory do not replace the previous window.
- Align investigation, writing and review instructions with their granted tools. Writers reuse current owner assessments; scoped checks and complete-report acceptance have separate delivery contracts.
- Clarify directory, source, record and manuscript reads, plus memory, notes, exact evidence and findings. Select a few operational examples for each actual role and phase.
- Preserve settled-response replay after edits to top-level tool guidance. Parameter, permission, binding and runtime-contract changes remain subject to existing checks.

Quit the old app and back up the entire data folder before upgrading. Extract the complete ZIP and open Epivra.exe. Workspaces are not migrated automatically. Historical reports remain readable and exportable; unfinished studies with incompatible runtime contracts require a new study.

Progress summaries use the configured model for that task and may incur model charges. They do not replace original sources; check important conclusions against citations. Default models, search providers and research cost policies are unchanged.

Windows 10/11 x64 only, unsigned. Restricted Python analysis is bundled; OCR remains optional.

Engineering validation: 127 offline tests, 123 passed and 4 platform skips; architecture, Ruff, type checks and independent review passed. Offline checks do not establish live research quality, summary fidelity or token/cost savings.
