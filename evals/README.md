# 研究质量评测

评测定位更新：公开基准作为产品质量比较的主要依据；本目录已有合成案例用于具体回归。公开基准尚未接入或运行，版本、选型和实施方案见[公开评测](../docs/product-redesign/PUBLIC_EVALUATION.md)。报告、角色行为、评审理由和工程结果分别解释。

`research_case.py` 生成 30/100 份合成中文材料：大量同源转载、一份成本材料、一份独立随机试验。问题不泄漏关键文件位置。自动检查只判断正文读取覆盖和关键引用，不判定语义正确。

真实评测会调用模型 API 并产生费用：

```powershell
.venv/Scripts/python.exe tools/run_research_eval.py --sources 30 --run-id baseline
```

仅重算已有结果，不调用 API：

```powershell
.venv/Scripts/python.exe tools/run_research_eval.py --sources 30 --run-id baseline --assess-only
```

不同版本使用新 run-id，保留旧数据库与实际请求。产物在被忽略的 `.epivra/eval-{sources}-{run-id}/`，包含语料、SQLite 账本、最终报告和 result.json。夹具自动批准策略仅用于测试，产品任务仍由用户审批。

30 来源基线已完成，但人工质量验收未通过；先修正和复测，再扩大到 100。见 [实测记录](../docs/product-redesign/RESEARCH_EVAL.md) 和 [渐进验收](../docs/product-redesign/PARSING_AND_EVALUATION.md)。短文本夹具不能代表真实长文档研究质量。旧版脚本与数据保存在基线快照。


小型语义回归（8 个案例，含正确报告与跨场景错误；会调用模型）：

```powershell
.venv/Scripts/python.exe tools/run_review_eval.py --run-id version-name
```

直接核查已知失败的完整报告，复制数据库至独立评测目录，保留原报告和来源引用，原目录不修改：

```powershell
.venv/Scripts/python.exe tools/run_review_eval.py --run-id report-version --report-db .epivra/eval-30-coverage/research.db
```

使用已拒绝的独立审查驱动真实修订与再次核查，复用保存的来源（此夹具自行发出改向命令）：

```powershell
.venv/Scripts/python.exe tools/run_repair_eval.py --run-id repair-version --source-db .epivra/review-report-version/research.db
```

所有语义结果仍需检查理由是否正确；拒绝坏报告但给出错误理由，也不能判定通过。不同代码版本使用不同 run-id，未完成请求不能跨工具契约或模型绑定静默迁移。评测脚本不属于产品阶段控制器。

18项机制的正反例在 `mechanism_cases.py`。36份短报告用于核查校准，不证明模型实际完成了探索、改向、协作或重启；每项还必须检查执行轨迹。例子经主评审修正，不直接采用辅助模型输出作为真值。

```powershell
.venv/Scripts/python.exe tools/run_review_eval.py --run-id mechanisms-v1 --mechanisms
.venv/Scripts/python.exe tools/run_review_eval.py --run-id selected-version --mechanisms --only M02-positive M13-positive
```

少量完整研究任务（每项4份合成资料，不使用网络）在 `closed_loop_cases.json`，由真实产品服务运行策略、研究、审查与修订。判据保存在评测侧，不注入 Agent。

```powershell
.venv/Scripts/python.exe tools/run_closed_loop_eval.py --case archive --run-id version-name
.venv/Scripts/python.exe tools/run_closed_loop_eval.py --case decision --run-id version-name
.venv/Scripts/python.exe tools/run_closed_loop_eval.py --case measurement --run-id version-name
```

`--assess-only` 只重新导出已有运行，输出 `trace.json`、`result.json` 和已发布的 `report.md`；语义验收另记，不由脚本自动判分。`running=true` 时未结算操作可能仍在传输，不能把它直接称为阻断。评测目录受忽略，保存模型私有协议的数据库不作为辅助模型输入。当前新运行绑定夹具、模型和实现指纹，修改后应使用新run-id；历史运行按其保存请求解释。


## 判分合同与外推边界

closed_loop_cases属于封闭资料的小型语义与流程回归。candidate_mechanisms只是候选检查项，不是已覆盖能力；未发生改向、失败、重启的任务，不为相应机制判通过或失败。全套短报告校准不能替代开放检索、长文阅读、改向补查或真实文档研究。

每项主审判断分别记录：报告原句及单元、对应来源/逻辑反例、具体错误、严重度、涉及维度；行为结论必须有工作/成果/调用轨迹定位，核查理由必须定位review原文。缺证据记未验证，不用一份失败报告推定18项均失败。报告拒绝允许依据预先明确的通用正确性要求，但新出现的专门要求必须说明并独立校准，不能悄悄改变真值。

判据允许合理的表达、假设与方法差异，不要求固定最终答案或唯一行动。必须区分算术正确、方法适用、主张支持、交付适用和风格；不因风格偏好拒绝，也不因主结论方向相同而豁免实质误述。长度口径应在新测试启动前说明，不能在收到报告后选择更严格算法。未来基准需同时含足够证据正例、不足证据、反证和合理替代方法，并保留未参与调试的任务。

此次独立测试复核、可计算反例与分层实验设计见[职责与根因审计](../docs/product-redesign/ROLE_DESIGN_REVIEW.md#分层根因审计先隔离失败再改变实现2026-09-11)。合成案例可检查特定逻辑，但主审也可能错，争议点须保留并核准，不能把AI自评作为真值。


仅隔离调查者的委派文字（固定measurement题、同一原计划/资料/模型；每侧独立目录）：

```powershell
.venv/Scripts/python.exe tools/run_role_diagnostic.py --run-id delegation-v3 --trace .epivra/closed-measurement-domain-v11/trace.json --variant direct
.venv/Scripts/python.exe tools/run_role_diagnostic.py --run-id delegation-v3 --trace .epivra/closed-measurement-domain-v11/trace.json --variant delegated
```

该工具刻意不运行完整研究；没有publication是正常的角色级诊断，不是失败。result中的semantic_acceptance仍须主审。首次请求仅task不同，后续采样可不同；一次每侧不能证明因果或成功率。源目录与祖先身份、资料一致性均在调用前检查，结束后复核磁盘文件集合和正文；改变工具/角色/资料配置须新run-id。


作者隔离使用 `--variant writer-reference` / `writer-actual`，两者都传 `--reference evals/role_calibration.json`；其余参数与上例相同。两臂使用同一任务、计划、来源和角色，分别注入经校准的文本与真实调查文本。这是仅保留来源的文本重新交接，不是完整旧调查图恢复；使用前检查答案没有不可回查的旧笔记引用。参考成果已接近成品，不能把该实验当作开放写作验收。

`role_calibration.json` 同时提供 `measurement_role_positive` / `measurement_role_negative` 两份核查输入，后者仅追加一个错误断言。它也产生文内矛盾，因此拒绝可能来自矛盾识别；必须核对具体反驳理由。原始标签和判分依据不进入模型上下文。`run_review_eval.py --effort high` / `--effort max` 可隔离提供方思考参数，每个新实验使用独立run-id，不重复发送旧账本调用。
