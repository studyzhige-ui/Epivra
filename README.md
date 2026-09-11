# Deep Research Agent

本分支正在重构为自研 Harness 与供应商无关的研究 Runtime。原目录保持不变；这里的旧执行链已移除，新实现正在按可验证切片建设。

**当前可通过本地 CLI 完成真实在线研究，尚未达到完整产品验收标准。** 已接入 DeepSeek 与 Tavily，具备统一 Agent 循环、策略审批、暂停/恢复/改向、持久调用回放、独立调查与核查、版本化发布。研究在常驻宿主中运行，关闭客户端不会结束任务。

已实现授权资料目录与 CLI/宿主上传、PDF 文本层与 CSV/TSV/XLSX 解析、按范围读取、显式记忆与固定证据引用、并发调查、安全工具并发、供应商共享容量及限流冷却、流式完整性校验、凭据重载、明确拒绝恢复和未知调用人工对账。后续新任务默认使用 deepseek-flash。真实在线技术研究已经过策略审批、搜索、原文提取、写作和独立核查并发布；Flash 流式工具协议另有真实联调。扫描页 OCR、复杂版式/表格语义、更多供应商、用户界面和规模化研究质量评测仍待完成。未知付费调用不自动重发。

- [唯一现行架构](docs/ARCHITECTURE.md)
- [研究与产品设计](docs/product-redesign/README.md)
- [实施进度与待完成项](docs/product-redesign/IMPLEMENTATION.md)
- [开发与验证](docs/GETTING-STARTED.md)

历史学习、面试和复盘文档描述旧实现，仅作为背景材料；不指导本分支的新架构。开发规则见 [AGENTS.md](AGENTS.md)。
