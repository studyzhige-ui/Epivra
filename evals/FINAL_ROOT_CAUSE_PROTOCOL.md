# 最后一轮根因审查：冻结设计与归因边界

基线 afa3fc3fc1f62b5c326fa8c6f392ae101c96ad04；仅 improve/epivra-optimization，src 不改、不新建分支、不发布。

## 首先更正 R1 的起源定位

完整旧轨迹35491396644/candidate中，“长读事务只能经checkpoint无法完成这一间接路径影响提交”的表述更早存在于调查者 note seq631/ref5b4f0562f41c，以及其 work_result seq901/ref1adc56191d1f 的 findings[2]（status=inference）。综合 seq1529 是继续传播并强化认识状态，不是最早起源。R1的传播链从综合开始因而不完整，不能据此把综合者判为唯一发生点。

## 实现审查（独立于真实试验）

已按 Git blob SHA 核对当前 application/harness/storage/prompts/context/adapters/models/scheduling。审查：每个角色可用能力、Store.work输入前置条件、任务创建权、check与final触发、报告与核查版本门、共享前提和职责交接。重点区分代码强制、prompt建议、运行中实际选择，不把长/多角色本身判成错误。

来源包括已保存的 Python、FDA、SQLite 完整/中断运行及R1八格公开产物。按首次出现、交接后变化、复核、返工逐步追踪，而不是只评最后稿件。旧成绩与核查文本不是事实金标。

## 固定24次单轮输入对照

全部使用现有DeepSeek官方适配器、同模型deepseek-flash/high、同65,536输出能力和1M上下文能力；没有报告字数限制。调用通过一致的直接回复通道，无工具/历史；这使模型输入因子能比较，但不冒充原Harness逐步重放、完整产品或单Agent产品验收。

A. 8次短材料生成：成本估计/固定实际成本，以及仍可同步的活跃读取/必须等全部读取结束的规则，两组正反条件，各比较最小研究说明与生产writer说明。来源、原始用户问题一致，生成输入不含待审陈述或金标。它检查基础前提理解是否在无多角色链时仍失效，以及角色说明的局部影响。

B. 8次旧真实资料重建：以同一三份完整SQLite官方快照、原用户问题、真实调查成果及综合委派为基础，4臂×2次，第二次倒序：
- original：原生产综合者说明＋原委派＋原两份调查成果＋完整来源；
- neutral_task：只用中性问题委派替换原委派；
- corrected_upstream：原委派保留，仅在调查成果findings[2]把“只能”改成非穷尽的一条可能路径，分配新投影ref，不伪装旧不可变记录；其余来源/输入不改；
- direct_sources：移除角色化说明和上游摘要，以原问题＋相同来源直接回答。这个臂同时改多个输入因素，只是简化组合的对照，不能单独归因于去掉综合者。

原ZIP固定SHA256 d4c547b7fa318a970906285c18565a4e8d0bc12d61fde6885c6d31d2882ffed9，内部manifest逐个核验。corrected_upstream是已标明的诊断用oracle干预，不是拟采用的SQLite产品规则。

C. 8次聚焦核查：上述四份短材料和正反报告陈述，分别用最小核查说明、生产reviewer说明，要求accepted与理由。若短范围都错，支持基础推断/指令问题；若能正确判定而原长任务放行，说明不是完全缺少判断能力，应定位注意力分配、继承性意见及作用范围，但不能仅凭此分离三者的比例。

## 判别方式与停止

对所有输出独立阅读全文，以相同资料核查关键内容、必要限制、额外无依据强断言和用户用途；不把字符串没出现自动等同正确。主要旧命题：排他“只能”、同步完成与日志重置的条件混淆、COMMIT语义范围、模式返回及代价、建议是否超过来源。区分缺陷、支持充分的内容及条件说清后的合理推断。

最小输入改善不自动证明整个单Agent架构已通过；oracle纠正有效说明对错误前提的敏感性，不证明生产能自动发现它；中性任务有效才支持原委派有害；若原臂无法复现，明确承认反事实未重现。每臂最多2次，不能推断稳定总体成功率。保留所有结果，不换措辞跑到绿色。

本轮最多24个实际模型请求（无工具循环），总20分钟主动诊断窗口只保护试验；不进入产品。已发送请求等待结算，unknown立即停、不重发。无Tavily、无十题或同等大批研究。完成后移除活动workflow/request，提交逐项证据、明确根因及仍未分离的因素；没有已验证的产品修改则不强行落入src。

## 方法依据（非效果保证）

OpenAI A practical guide to building agents 建议先最大化单Agent，按具体复杂性再分拆；Anthropic Demystifying evals for AI agents 要求检查轨迹、分开终态和对过程的解释、使用正反控制并校准评审。这里优先使用这些原则，不照搬产品角色。
https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/
https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
