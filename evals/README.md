# 研究质量评测

`research_case.py` 生成 30/100 份合成中文材料：大量同源转载、一份成本材料、一份独立随机试验。问题不泄漏关键文件位置。自动检查只判断正文读取覆盖和关键引用，不判定语义正确。

真实评测会调用模型 API 并产生费用：

```powershell
.venv/Scripts/python.exe tools/run_research_eval.py --sources 30 --run-id baseline
```

仅重算已有结果，不调用 API：

```powershell
.venv/Scripts/python.exe tools/run_research_eval.py --sources 30 --run-id baseline --assess-only
```

不同版本使用新 run-id，保留旧数据库与实际请求。产物在被忽略的 `.deep-research-agent/eval-{sources}-{run-id}/`，包含语料、SQLite 账本、最终报告和 result.json。夹具自动批准策略仅用于测试，产品任务仍由用户审批。

30 来源基线已完成，但人工质量验收未通过；先修正和复测，再扩大到 100。见 [实测记录](../docs/product-redesign/RESEARCH_EVAL.md) 和 [渐进验收](../docs/product-redesign/PARSING_AND_EVALUATION.md)。短文本夹具不能代表真实长文档研究质量。旧版脚本与数据保存在基线快照。


小型语义回归（8 个案例，含正确报告与跨场景错误；会调用模型）：

```powershell
.venv/Scripts/python.exe tools/run_review_eval.py --run-id version-name
```

直接核查已知失败的完整报告，复制数据库至独立评测目录，保留原报告和来源引用，原目录不修改：

```powershell
.venv/Scripts/python.exe tools/run_review_eval.py --run-id report-version --report-db .deep-research-agent/eval-30-coverage/research.db
```

使用已拒绝的独立审查驱动真实修订与再次核查，复用保存的来源（此夹具自行发出改向命令）：

```powershell
.venv/Scripts/python.exe tools/run_repair_eval.py --run-id repair-version --source-db .deep-research-agent/review-report-version/research.db
```

所有语义结果仍需检查理由是否正确；拒绝坏报告但给出错误理由，也不能判定通过。不同代码版本使用不同 run-id，未完成请求不能跨工具契约或模型绑定静默迁移。评测脚本不属于产品阶段控制器。
