# Agent 自主取证与精确修订能力优化

本批改进 Agent 可使用的行动能力，不改成固定后端流水线。模型仍决定问题、取证关键词、证据解释、分工、是否继续研究以及怎样修订。正常研究无总调用/token/时长硬限额，报告无默认字数或章节数量限制。

## 实现

- `search_sources`：由模型选择字面词/短语，在本研究已保存的原始资料中定位多个原文片段，返回精确位置、前后文、来源与selection。无新网络请求，不作模型摘要、不声称语义召回齐全；无命中不等于事实不存在，仍可读完整原文。调查者、综合者、作者和reviewer可用；lead已有权限不变。
- `read_manuscript` / `revise_report`：作者读取保留原始引用标记的原稿，自主选择精确替换内容，生成新不可变报告版本。未改变内容直接保留，不要求重新生成全文。歧义、重叠、错误引用在保存前失败。旧稿和旧review不覆盖，新稿仍需独立绑定核查；整体重写仍可选择draft_report。
- draft与revision共同使用原子报告/成果提交；成果回执失败不能留下半份报告。

没有增加主题专用prompt、固定额外critic、自动接受/自动发布或强制首回合动作。除了新工具说明和writer可选编辑说明，各角色的研究判断标准与ResearchService不变。

## 严格回归

新增10项确定性测试涉及搜索原文范围、真实引用与同work选择身份、角色/研究隔离、相反资料条件、Unicode/代码/Markdown引用往返、精确多处修改和原子回滚。

严格执行暴露了旧测试中的语法错误、settle失败注入mock没有接收新timing关键字，以及一个import顺序错误。仅修测试兼容性/语法，不移除断言。此前PowerShell多条native命令可能被最后成功命令掩盖退出码，本批逐条传播失败。不能用旧workflow绿色状态替代实际测试日志。

阶段验证35463659467保留1项mock错误；修复后35463945399执行448项测试，446通过、2跳过，架构检查通过，但随后发现旧import排序问题。该排序也已修复；最终提交的Ruff/mypy/build以新CI为准。没有将未执行步骤标通过。

## 真实模型对照设计

固定基线6bcd5a2588cab7c4952525902e438ab78df5f7c0与候选使用同一DeepSeek模型/配置、相同原始任务和材料，经真正Harness执行。两个取证题结论方向相反；修订题要求撤回无依据的成效判断，保留有效预算和执行记录。不给模型指定工具序列、预期结论或主题补丁。

每个角色探针观察最多6个已完成决策，是小型诊断范围而非生产预算。完成、质量、延迟、调用/token及未完成状态分别保存。它不是全链路联网质量基准，也不外推为所有报告耗时已解决。运行后附原始证据与独立复核；失败不改标签。

## 官方依据

Anthropic Writing effective tools for agents：用Agent可自主选择的相关内容检索替代逐页枚举，并实测工具使用、错误、成本与结果，避免规定唯一策略。
https://www.anthropic.com/engineering/writing-tools-for-agents

OpenAI Function calling：明确工具参数、适用边界，代码执行确定性操作，Agent保留判断。
https://developers.openai.com/api/docs/guides/function-calling

GitHub workflow syntax：检查PowerShell native命令退出码；测试失败不能被后续成功掩盖。
https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax

上述是设计依据，不是对本项目模型效果的保证。主线不合并，不运行十题。
