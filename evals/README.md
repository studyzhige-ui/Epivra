# 研究质量评测

`research_case.py` 生成 30/100/1000 份合成中文材料：大量同源转载、一份成本材料、一份独立随机试验。问题不泄漏关键文件位置。自动检查只判断正文读取覆盖和关键引用，不判定语义正确。

真实评测会调用模型 API 并产生费用：

```powershell
.venv/Scripts/python.exe tools/run_research_eval.py --sources 30 --run-id baseline
```

仅重算已有结果，不调用 API：

```powershell
.venv/Scripts/python.exe tools/run_research_eval.py --sources 30 --run-id baseline --assess-only
```

不同版本使用新 run-id，保留旧数据库与实际请求。产物在被忽略的 `.deep-research-agent/eval-{sources}-{run-id}/`，包含语料、SQLite 账本、最终报告和 result.json。夹具自动批准策略仅用于测试，产品任务仍由用户审批。

30 来源基线已完成，但人工质量验收未通过；先修正和复测，再扩大到 100/1000。见 [实测记录](../docs/product-redesign/RESEARCH_EVAL.md) 和 [渐进验收](../docs/product-redesign/PARSING_AND_EVALUATION.md)。短文本夹具不能代表真实长文档研究质量。旧版脚本与数据保存在基线快照。
