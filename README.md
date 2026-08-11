# Deep Research Agent

一个由研究 Agent 主导、由确定性 Trust Plane 提供可信边界的通用深度研究项目。

模型负责规划、检索策略、证据判断、研究停止与报告论证；代码负责安全执行、来源保存、状态恢复和引用验证。项目不以静态字段、数量阈值、固定查询队列或任务级预算代替研究判断。

## 当前状态

项目正在先完成整体架构、研究质量治理和八个模型角色的 Prompt 设计，尚未批准进入正式实现。仓库中的早期代码只作为行为原型，不能代表当前架构，也不会在讨论期间继续扩展。

两份权威设计文档是：

- [架构决策](docs/ARCHITECTURE.md)：保存当前有效的阶段治理、角色职责、研究产物、检索与停止、领域能力指南、引用和上下文设计；
- [Prompt 规范](docs/PROMPTS.md)：保存与当前架构一致的八份独立角色 Prompt 和权限边界。

被新决策替代的描述会从当前文档中删除；设计演变由 Git 历史保存。`PROJECT_CHARTER.md` 只说明稳定的项目使命和开发边界，不重复另一套架构。

## 已确定的方向

- 研究计划结合模型能力与公开只读预搜索，默认由用户确认；
- Supervisor 持续判断实时缺口、信息增益和阶段质量，只由它批准 L0、L1、L2 跨阶段修订；
- 并行 Researcher 发现来源，Curator 整理来源忠实的正式素材，Synthesizer 在写作前形成研究判断；
- Writer 只使用 Research Synthesis 与 Curated Material Library 写作，Independent Validator 独立核验，Editor 负责闭合意见和表达；
- 研究以语义充分性与信息饱和停止，不设置会截断正常研究的任务级预算；
- 证据合理穷尽后仍不足可以成为合法结论，不为制造确定答案而无限搜索；
- Universal Research Core 可组合少量 Domain Guides 与 Capability Guides，提供领域方法和顶层报告指导，不硬编码研究路径；
- 最终由轻量 Citation Renderer 生成顺序正确的数字引用并检查引用闭包；
- 数据结构保持最小，先修正架构、责任和 Prompt，不累积补丁式例外逻辑。

## 本地验证

当前行为原型可使用普通 Python、venv、Conda 或 uv 验证：

```bash
python -m pip install -e .
python -m unittest discover -s tests
```

这些测试只说明原型自身可运行，不代表最终架构已经实现或验收。
