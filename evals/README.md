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
