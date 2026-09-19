# 研究验证工具

[English](README.en.md) · **简体中文**

这里的合成案例用于诊断与回归，不是公开基准成绩；公开研究基准尚未接入。报告质量、角色行为、核查理由和工程故障必须分别解释。

```powershell
# 工程检查：不调用模型或搜索
python -m unittest discover -s tests
python tools/check_architecture.py
ruff check src tests tools evals
# 可选：前端确定性回归需要 Node.js，应用运行本身不需要
node tests/web_reader.cjs
node tests/web_status.cjs
node tests/web_usage.cjs
```

GitHub Actions 还会在支持的 Python/操作系统矩阵上运行已配置的 mypy 检查并构建 wheel。Python 3.13 的基础安装任务另外在检出目录之外创建全新虚拟环境，安装所构建 wheel、检查依赖、导入位置、打包资产和 CLI 入口。这验证基础 wheel 与本次解析到的依赖，不是所有依赖最低版本或所有扩展的安装证明。

## 在线诊断

以下命令调用模型 API 并消耗供应商额度。模型、工具合同、样例或实现改变时，使用新的 run ID。已成功的调用回放已有记录，不重发旧账本操作；模型原始协议记录保存在被忽略的本地目录。

```powershell
# 小型报告核查案例
python tools/run_review_eval.py --run-id review-version
# 机制正反例
python tools/run_review_eval.py --run-id mechanisms-version --mechanisms
# 指定机制
python tools/run_review_eval.py --run-id selected-version --mechanisms --only M02-positive M13-positive
# 基于给定资料的小型完整任务
python tools/run_closed_loop_eval.py --case archive --run-id archive-version
python tools/run_closed_loop_eval.py --case decision --run-id decision-version
python tools/run_closed_loop_eval.py --case measurement --run-id measurement-version
```

闭环工具的 `--assess-only` 导出已有 `trace.json`、`result.json` 和已发布的 `report.md`，不自动判定语义质量。测试夹具可能自动审批策略，产品正常使用仍由用户审批。

## 复用报告与隔离角色

```powershell
python tools/run_review_eval.py --run-id report-version --report-db .epivra/prior-run/research.db
python tools/run_repair_eval.py --run-id repair-version --source-db .epivra/review-report-version/research.db
python tools/run_role_diagnostic.py --run-id delegation-version --trace .epivra/prior-run/trace.json --variant direct
python tools/run_role_diagnostic.py --run-id delegation-control --trace .epivra/prior-run/trace.json --variant delegated
```

角色诊断刻意不运行完整研究，没有发布不是失败。作者对照使用 `--variant writer-reference` / `writer-actual`，并传入 `--reference evals/role_calibration.json`。工具检查来源身份、样例指纹与资料一致性；每组一次运行不能证明因果关系或成功率。

## 样例能验证什么

`mechanism_cases.py` 提供18项机制的36份短报告正反例，用于核查校准，不证明探索、改向、协作或恢复实际发生。`closed_loop_cases.json` 提供每项4份合成资料的小型完整任务。`research_scenarios/` 分开保存输入语料和评估数据，判分标签不进入 Agent 上下文。

`research_case.py` 可生成30或100份来源，包含同源转载和关键独立证据。这些是已有夹具规模，不是产品的来源数量上限。自动覆盖检查不能证明语义正确或长文理解能力。

`tools/run_benchmark10.py` 是 Windows 批量诊断工具，按正常题内并发、题间顺序运行。题单由调用者通过 `--queries path/to/cases.jsonl` 提供，不随工具上传；每行包含整数 `id` 和字符串 `prompt`。启动命令为 `python tools/run_benchmark10.py --run-id batch-version --queries path/to/cases.jsonl`，查看原运行状态使用 `--run-id batch-version --status`。启动会消耗模型/搜索额度并自动批准生成策略，只应用于明确授权的诊断题单。代码和输入进入冻结身份，不能用同一 run ID 静默切换版本。这不是公开榜单成绩，发布成功也不代表质量通过。

先检查决定性结论和证据，再看风格。拒绝报告但理由错误不能算核查成功；没有发生的行为应标为未验证，不自动判通过或失败。保留争议判断以供人工复核，留出不参与调试的任务，不把模型自评当作真值。

[分析样例](analysis/README.zh-CN.md)说明用于确定性计算与产物交接测试的小型公开 Iris 数据集。

## 小规模 GitHub 真实测试

`Small live evaluation` 复用上面的 Harness 核查工具和四材料闭环，不创建第二套研究流程。修改 `evals/live-request.json` 并提交到指定开发分支或 `eval/**` 分支才会触发付费运行；普通代码/文档提交、PR 的离线验证不触发它。也可以手动启动工作流。仅在实际调用步骤注入 `DEEPSEEK_API_KEY`、`TAVILY_API_KEY`，后者可为逗号分隔的合法密钥池。

请求模式为 `providers`、`review`（1–4 个已有核查样例）或 `closed`（一个已有小型四材料案例）。`probe_providers` 会额外调用一次极短模型生成，并通过现有 Tavily 连接逐槽搜索；探测用量与研究账本用量分别记录。凭据已经验证后无需每轮重复探测。

截至 2026-09-19 的维护授权：普通小规模真实测试可以消耗额度；十题和同等规模高消耗评测须经负责人再次明确批准，不能通过拆分请求规避审批。本入口不提供 benchmark 模式。这里的案例数量和 GitHub 作业期限只限制该诊断作业，不改变普通产品研究的总调用、token、费用或时长政策。

工作流禁止直接重新运行已有的付费 attempt。先检查旧日志和产物，再提交明确的新请求；新请求不是旧研究的恢复，不自动重发旧账本中的 unknown。临时 Runner 不保留研究数据库，尚不承诺跨 Runner 的原操作恢复。作业被平台强制中止时产物可能不完整，不能将其算作通过。

Artifacts 只上传显式脱敏的领域成果、来源、公开核查理由、usage 和实际窗口回执，不上传 `.env`、研究 DB、HTTP headers 或模型私有协议正文。窗口回执与原成果可联合诊断，但不是完整原生会话的导出。当前入口只用于已有合成语料，不能把真实敏感材料直接当普通公共测试上传。

`execution_pass` 仅代表选定路径完成；核查案例的 `decision_gate` 只比较现有标签；`semantic_acceptance` 保持待独立核验。缺结果、错误、unknown 或标签不符返回非零，不能因底层脚本正常退出而假绿。标签不符先检查题目、语料、稿件、核查范围和理由；一个合理的下一步研究动作不自动等于可接受的最终报告。争议标签不能通过修改生产 prompt 或悄悄重标来消除。

## 通用研究质量标准与变更约定

以下是 Epivra 的**评估约定**，不是生产 prompt，也不是 DeepResearch Bench 官方评分。它适用于不同题材，但每项判断必须落在本题用途与原始证据上。

| 维度 | 检查内容 |
|---|---|
| 任务与覆盖 | 回答用户核心问题、用途和明确要求；主要分支没有被容易获取的旁支替代 |
| 事实与数值 | 关键实体、日期、数值、单位、计算与来源一致；事实、来源说法与推断可区分 |
| 证据支持 | 来源内容确实支持相邻断言，定位可回查；转载不当作独立证据；不可访问不等于不支持 |
| 分析与综合 | 方法适合问题，比较口径可比，解释与推论有依据；不以摘要拼接、材料数量代替洞见 |
| 条件与校准 | 反证、适用条件和版本变化影响结论；既不夸大，也不以一概“证据不足”回避已有充分答案 |
| 可用性与表达 | 读者能找到答案和依据，详略适合用途；没有格式、固定字数、引用数量或冗长奖励 |

每个维度可记录 0–4：0 为核心结果无效；1 为存在重大缺陷；2 为部分可用但仍需实质修订；3 为满足任务且仅有轻微问题；4 为在满足任务之外有证据支持的高价值分析。未检查或无法判断记为 `not_evaluated`，不填 0 或 4。每一项都附具体稿件位置、来源位置和影响说明；分数是可校准的评估尺度，不是数学证明，不默认折算总分。

另列决定性错误：足以改变主要结论/建议的错误事实、伪造依据、无支撑的因果或外推、失效前提仍被使用，以及在证据充分时无依据拒绝回答。必须说明实际影响，不能把每个措辞瑕疵升级为阻断项；排版分也不能抵消实质错误。评审者判断错误、误拒正确稿件与报告自身错误分别记录；自动判分须以独立人工校准为目标，本轮 AI 复核不能冒充人工验收。

**工程变更**可以针对可复现的协议、取消、恢复、容量或安全边界缺陷修复，附常规路径与反例回归。**研究内核、角色和 prompt 变更**不能因为单篇报告表现差就定制流程：先记录公开输入→工具结果→交接→成品→核查的失败链，提出不含题目专名的机制解释；再固定模型/工具/材料/版本，在不同情境以及结论方向相反的控制样例上对照，保留不参与调优的任务。单次改善不是稳定收益；未获得泛化依据时保留诊断，不增加主题分支、固定 critic 或同义禁令。

修改 prompt 前优先查官方文档，写明所采纳的具体原则、适用条件和验证结果。官方建议是设计依据，不是迁移到本项目模型后有效的保证。已有代码机制与用户产品边界优先于“参考项目也有这个功能”的推导。

## 权威依据与参考边界

- [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)：将目标、数据、指标与对照分开，结合人工校准，并检查判分顺序和冗长偏差。
- [OpenAI prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering)：参考明确指令、上下文与可验证迭代；具体模型行为仍须实测。
- [Anthropic success criteria and evaluations](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests)：成功条件要具体、可测量且与用途相关；评估本身也可能存在歧义。
- [Google prompt design strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies)：上下文与例子需清楚，例子过多可能使回答贴合示例而非泛化。不要把单题答案加入通用 prompt。
- [DeepResearch Bench，固定版本](https://github.com/Ayanami0730/deep_research_bench/blob/469cce54ea7f6a63c163d3d9fec879cf289ec484/README.md)：RACE 按任务评估 comprehensiveness、insight/depth、instruction-following、readability；FACT 分开验证引用支持，统计 citation accuracy 与 effective citations。引用支持数量不等于论证质量，参考报告不是不可质疑的真值。未运行对应官方流程时，不标称官方分数；不同 judge/版本不可直接合并。
- [Codex 工具执行快照](https://github.com/openai/codex/blob/e269f2164cbb9f499e4f22301c393500e2a831f3/codex-rs/core/src/tools/parallel.rs)：参考调用现场、记录与执行生命周期，不因此迁移语言或框架。
- [用户提供的 Claude 工具结果快照](https://github.com/studyzhige-ui/claude-code-source-private/blob/58231dcce408f805c645cfbc352d2876b517223b/utils/toolResultStorage.ts)：参考有界读取与原件外置不形成循环；该快照不是当前官方产品全部实现。
- [DeerFlow](https://github.com/bytedance/deer-flow)：读取时主线为重写后的 2.0 通用 harness，原研究框架在 `main-1.x`。选择具体机制时注明分支/提交；不照搬固定报告章节、强制字数或领域风格模板。

以上资料核对日期为 2026-09-19。工程检查、模型行为、成品语义、官方基准和发布承诺是不同证据层，不相互替代。
