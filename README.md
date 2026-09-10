# Deep Research Agent

本分支正在重构为自研 Harness 与供应商无关的研究 Runtime。原目录保持不变；这里的旧执行链已移除，新实现正在按可验证切片建设。

**当前交付的是可测试的执行底座，还不是可供最终用户使用的完整研究产品。** 已具备统一 Agent 循环、策略审批、暂停/恢复/改向、持久调用回放、独立核查工作与版本化发布。模型和外部工具通过 Python 协议注入，目前的闭环验证使用离线替身。

已增加授权文本目录/上传、按范围读取、显式记忆及按需并发调查。网络/PDF 资料适配、真实模型协议、持续宿主与用户界面、规模化语义质量评测仍待完成；不能把离线测试理解成供应商联调通过。

- [唯一现行架构](docs/ARCHITECTURE.md)
- [研究与产品设计](docs/product-redesign/README.md)
- [实施进度与待完成项](docs/product-redesign/IMPLEMENTATION.md)
- [开发与验证](docs/GETTING-STARTED.md)

历史学习、面试和复盘文档描述旧实现，仅作为背景材料；不指导本分支的新架构。开发规则见 [AGENTS.md](AGENTS.md)。
