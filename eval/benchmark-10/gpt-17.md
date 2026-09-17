[← 二十份研究目录](README.md)

# ChatGPT · ID 17 · 低代码开发的价值与挑战

[原研究窗口](https://chatgpt.com/g/g-p-6aa7b0cb61f48191bc4c4f582a8acef5/c/6aa7b4e7-652c-83ea-8642-507be08f9de5)

原文整理，不改写研究结论。旧页面记录采集于 2026-09-14；GPT Activity 于 2026-09-17 补采。保留页面公开展示的过程说明，不代表平台未公开的内部推理。 保留引用按钮编号，但旧来源摘录不保证完整呈现每个按钮内全部对应来源。图形布局及未载入图片不在文本摘录中；公式按页面现有文本保留，不推测补齐运算符。

## 评测原题

"“在当今软件开发行业中，低代码/无代码平台对传统开发流程的影响有多大？它们是否真正提高了开发效率，还是在特定场景下反而增加了维护成本？”
为什么这个问题有价值？
行业趋势：低代码/无代码开发近年来发展迅速，许多企业尝试采用它们来加快产品交付速度。
生产力 vs. 维护成本：这些工具宣称能降低开发门槛，但长期来看，它们是否真的能提高效率，还是在维护和扩展时带来了更多问题？
开发者视角 vs. 业务视角：企业管理者可能认为它们降低了成本，但开发者可能认为它们限制了可扩展性和灵活性。
未来发展预测：是否会有越来越多企业完全转向低代码/无代码，还是它们只适用于特定业务场景？"

## 对话及完成信息

Today 4:48 PM

##### You said:

Deep research

"“在当今软件开发行业中，低代码/无代码平台对传统开发流程的影响有多大？它们是否真正提高了开发效率，还是在特定场景下反而增加了维护成本？” 为什么这个问题有价值？ 行业趋势：低代码/无代码开发近年来发展迅速，许多企业尝试采用它们来加快产品交付速度。 生产力 vs. 维护成本：这些工具宣称能降低开发门槛，但长期来看，它们是否真的能提高效率，还是在维护和扩展时带来了更多问题？ 开发者视角 vs. 业务视角：企业管理者可能认为它们降低了成本，但开发者可能认为它们限制了可扩展性和灵活性。 未来发展预测：是否会有越来越多企业完全转向低代码/无代码，还是它们只适用于特定业务场景？"

Your message actions

##### ChatGPT said:

页面完成时长：8 分钟（页面取整值）；显示来源数：38。本窗口未见 Gemini 式独立审批方案，未从报告倒推补写。

## 最终研究报告

## 低代码/无代码平台对传统软件开发流程的影响：效率增益、维护成本与适用边界研究

### 执行摘要

**结论：低代码/无代码已显著改变企业软件交付，但并未普遍取代传统开发。**受控实验显示，在一个管理信息系统中，OutSystems 相比 Django 的总开发效率约高 3.2 倍、一次维护任务约高 2.5 倍；企业案例也普遍报告明显缩短交付周期。[1]但独立、跨平台、持续三年以上的 bug 率、迁移成本和 TCO 对照数据仍不足。最大收益集中在内部应用、CRUD/工作流、原型和自动化；复杂算法、极致性能、差异化用户体验及长寿命核心系统更适合传统或混合开发。[2]

### 研究边界与方法

用户给出的范围是“近 5 年（2019–至今）”。由于当前日期为**2026 年 9 月 14 日**，2019 年至今实际上已超过五个自然年；本报告以更明确的绝对时间范围**2019 年 1 月—2026 年 9 月**为准，以避免遗漏低代码从早期企业采用到生成式 AI/Agentic AI 阶段的演变。

本研究将“低代码”定义为以可视化模型、声明式逻辑、预制组件、连接器及自动生成代码/运行时为主要开发手段，同时允许专业开发者通过代码扩展的平台；“无代码”则更强调业务人员无需直接编程即可完成应用或自动化。现实市场中两者边界并不严格，学术研究也指出从业者对 low-code、no-code、zero-code 的使用存在明显重叠，因此本文多数场景以**LC/NC**统称，在涉及工程扩展能力时再区分。[3]

检索优先级依次为：中文官方/原始资料；Gartner、Forrester、IDC 等市场研究机构的原始页面；同行评审论文及作者公开稿；Microsoft、Mendix、OutSystems、Appian、Retool 等官方技术文档；企业官方/厂商客户案例；最后才是 Stack Overflow、Reddit 等开发者社区证据。社区意见没有被当作性能基准，而主要用来识别**维护、定制、学习、价格、锁定、调试等边界问题**。其中一项 2021 年 ESEM 实证研究系统分析了 73 条 Stack Overflow 帖子和 228 条 Reddit 帖子，比选择少量热门帖子更适合反映开发者经验。[2]

证据权重如下：

|  |  |  |  |
| --- | --- | --- | --- |
| 证据等级 | 本报告中的典型来源 | 用途 | 主要局限 |
| **A：较高** | 同行评审实证研究、厂商官方技术文档、IDC/Gartner/Forrester 原始研究 | 判断工程能力、市场方向、实测生产力 | 实验样本有时很小；分析师市场口径不同 |
| **B：中等** | 系统综述、结构化开发者社区研究、公开企业案例 | 判断场景适用性、实际组织影响 | 案例有选择偏差，失败项目不易公开 |
| **C：谨慎使用** | 厂商委托 ROI/TCO 研究、厂商营销案例 | 获取成本结构和大规模部署数据 | 资助关系、模型假设和客户筛选可能高估收益 |

尤其需要强调：Forrester 2024 年 Power Apps TEI 报告虽然采用标准化财务模型，但由 Microsoft 委托；Forrester 自身明确声明该研究不应用作竞争性分析，也不应假设其他企业能够获得相同 ROI，因此本文只把其中的数字视为\*\*“可实现收益的一种经风险调整的情景模型”\*\*，而不是行业平均值。[4]

学术证据本身也尚未成熟。2022 年发表于*Software and Systems Modeling*的多声部系统综述检索了数百篇学术与灰色文献，结论之一是低代码研究仍处于相对早期阶段，尤其在复杂性、性能、可扩展性和长期软件演化方面，需要更多实证研究。[5]

**因此，本报告最重要的方法论原则是：开发速度的证据明显强于长期 TCO 的证据。**对“低代码能不能更快”可以给出较高置信度回答；对“十年生命周期里一定更便宜吗”，现有公开证据不足以给出同等强度的结论。[5]

### 核心发现：效率提升是真实的，但复杂度更多是被转移而非消除

#### 市场采用已经从边缘工具进入企业主流

IDC 中国数据显示，2022 年中国低代码/零代码软件市场规模约**26.2 亿元人民币，同比增长 24.2%**；2023 年下半年市场规模约**19.0 亿元，同比增长 22.1%**，IDC 当时已观察到产品开始渗透企业关键系统应用。IDC 在 2024 年进一步预测，中国低代码/无代码软件市场到 2027 年将达到**106.3 亿元人民币，五年 CAGR 32.3%**。这些数字采用的统计周期并不完全一致，因此不能直接串成单一时间序列，但可以确认中国市场仍处于较快扩张阶段。[6]

全球市场的分析师口径差异更大。Forrester 将 low-code 与数字流程自动化合并估算，称 2023 年相关市场约**132 亿美元**，基准情形下到 2028 年接近**300 亿美元**；若 AI 显著强化低代码，则其上行情景接近**500 亿美元**。Forrester 同一研究称，87% 的企业开发者至少将部分工作放在低代码环境中。[7]Gartner 使用更宽的“Low-Code Development Technologies”口径，则预计到 2029 年市场达到**582 亿美元，2024–2029 CAGR 约 14.1%**，并将生成式/代理式 AI、Citizen Development 与运营效率列为主要增长驱动。由于 Gartner 与 Forrester 的分类范围不同，这两个绝对市场规模**不应被当作彼此验证的同一指标**。[8]

到 2026 年，Gartner 对 2025 年市场份额的分析已明确将**Agentic AI 嵌入开发环境**视为领先厂商扩大优势的重要因素。这意味着低代码正在从“拖拽式 UI 工具”转变为“模型驱动 + AI 生成 + 工作流编排 + 专业代码扩展”的综合软件工程环境。[9]

#### 开发速度：证据最明确的优势

目前质量较高、但规模有限的直接对照实验来自 Trigo、Varajão 与 Almeida 的研究。两名具有对应技术经验的开发者分别使用**OutSystems**和**Django/Python**实现同一个管理信息系统。包含测试和配置的总工作量约为**11.93 小时 vs. 38.37 小时**，即低代码一侧约**3.2 倍**效率；仅开发用例比较约为**8.4 vs. 22.8 小时，约 2.7 倍**。独立质量评价约为 85.79% 与 81.37%，没有出现“以明显降低质量换速度”的现象。[1]

但这项实验只有两名开发者，而且是相对典型的管理信息系统，而不是大型分布式系统。因此，它能证明“**在合适问题类型上，低代码的速度优势可以非常大**”，却不能证明任何企业应用都会获得 3 倍生产力。其外部有效性必须谨慎解释。[1]

Forrester 的 Power Apps TEI 模型得到相对温和的结果：其 30,000 人、200 名专业开发者和 1,800 名 Citizen Developers 的复合企业模型中，专业开发者应用开发时间下降**50%**。三年风险调整后，模型估算收益现值约**4,610 万美元**、成本约**1,510 万美元**、NPV**3,100 万美元**、ROI**206%**、回收期低于六个月。[4]

然而其成本结构也揭示了另一个关键事实：三年模型中仅**Power Apps 许可证就约 1,130 万美元**，另有约 190 万美元实施/培训和约 190 万美元持续管理成本。换句话说，低代码节省了大量编码劳动，并不代表软件交付成本趋近于零；相当一部分成本被转换成了**平台许可、治理、培训及持续平台管理支出**。[4]

#### 维护：短期往往更快，长期结论远弱于开发期

同一 OutSystems/Django 实验还包含一次需求变化后的维护任务：低代码约**3.88 小时**，传统开发约**9.55 小时**，约为**2.46 倍效率差**。这说明在平台抽象仍适配需求的情况下，模型驱动开发同样可以降低修改成本。[1]

但是，**本次检索未找到可比数据**：尚未找到一组独立研究能在控制系统规模、业务复杂度、团队成熟度等变量后，对多个主流平台与传统开发进行**3–5 年以上**连续跟踪，同时给出 bug 密度、故障率、升级工时、平台迁移成本及累计 TCO。因此不能严谨地说“低代码长期维护一定更便宜”。这个证据空缺会显著降低任何十年期 TCO 预测的置信度。现有系统综述及 Gartner 2026 年针对低代码技术债务的专门研究都说明，长期软件演化已经成为一个独立问题，而不是平台自动解决的问题。[5]

开发者社区研究给出了成本反转的机制。对 Stack Overflow 与 Reddit 帖子的结构化编码中，研究者发现高学习曲线、价格、缺乏定制能力、加载/发布速度、复杂需求仍需编码、无法访问源代码、供应商锁定、维护/调试困难和集成困难等问题；同一批开发者甚至会同时表达“开发快”和“复杂项目更难维护”这两个看似矛盾的观点。[2]

这实际上解释了低代码经济学的核心：

**低代码主要消灭的是重复性实现成本，并不会消灭业务复杂性、分布式系统复杂性、数据复杂性以及生命周期复杂性。**

当复杂度能够被平台的标准抽象覆盖时，收益巨大；一旦频繁“穿透抽象层”，大量自定义 JavaScript、Java、C#、SQL、API、插件、非标准组件开始出现，团队可能同时承担“平台知识 + 通用编程 + 平台扩展机制”三套复杂度。这个边界也与从业者社区研究观察到的“复杂问题最终仍需编码”“定制不足反而产生更多 workaround”一致。[2]

#### 各评价指标的总体判断

|  |  |  |
| --- | --- | --- |
| 指标 | 研究结论 | 证据强度 |
| **交付周期** | 在 CRUD、表单、流程、内部工具和标准集成中，通常明显缩短；实验可达到约 2.7–3.2 倍效率，企业案例中也常出现 40%–90% 的周期下降，但厂商案例存在选择偏差。[1] | **较高** |
| **功能点/人月** | **未找到可比数据**。直接实验主要使用 use-case points/工时，而主流公开企业案例很少公布标准 IFPUG 功能点/人月。 | **低** |
| **初始开发成本** | 通常因人员数量、前端/CRUD/部署样板代码减少而下降，但平台许可证可能成为新的大项。[4] | **中—高** |
| **长期维护成本** | 标准组件范围内往往降低；高度定制、长期生命周期和平台升级环境中可能反转。缺乏独立多年对照。[10] | **中—低** |
| **Bug 率** | **未找到可跨平台比较的生产环境 bug/KLOC 或 defect density 数据**。实验质量指标接近，但不能替代长期缺陷率。[1] | **低** |
| **升级/迁移成本** | **未找到可比行业均值**；专有模型、运行时和连接器会增加退出成本。Mendix 即使使用 Git，其专有模型文件也不能像普通源码一样依赖第三方 Git 工具完成合并。[11] | **中** |
| **可扩展性** | 主流企业平台提供云/Kubernetes、集群及企业运行时，但“使用低代码”本身不等于“天然可扩展”；数据量、查询复杂度、架构设计仍决定性能。Appian 官方文档也明确要求按实际负载进行性能测试。[12] | **中—高** |
| **可测试性** | 平台差距较大。Appian 原生支持单元、UI 和性能测试；Power Platform、Mendix、OutSystems 均有 ALM/测试体系，但测试工件更依赖各自平台。[13] | **中** |
| **可观测性** | 企业级 LCAP 已不等于“黑盒”：OutSystems 可输出 Logs/Traces/Analytics，并支持 OpenTelemetry；Mendix 提供日志、健康检查和告警；Retool 有日志与审计能力。[14] | **较高** |
| **安全/合规** | 中央 RBAC、审计、DLP、环境隔离有机会优于散乱自建工具，但 Citizen Development 若缺少治理也会扩大应用和数据访问面。Forrester 访谈同时观察到治理改善与 Shadow IT 风险。[4] | **中—高** |
| **供应商锁定** | 是结构性风险，不仅是商业风险：模型、运行时、连接器、身份体系、部署方式和测试资产均可能是平台专有的。[2] | **高** |
| **业务敏捷性** | 是最稳定的收益之一，特别是业务规则频繁变化且业务专家能参与建模时。[2] | **高** |
| **ROI/TCO** | ROI 可很高，但高度依赖采用规模、许可证、已有生态和是否真正减少工程瓶颈；没有可信的“全行业统一 ROI”。[4] | **中** |

### 平台与工程生命周期比较

主流平台如今的差异已经不只是“拖拽 UI 好不好用”，而在于它们分别把**应用、流程、数据、运行时、CI/CD、可观测性和治理**封装到了什么程度。这直接决定效率提升与锁定之间的交换关系。[15]

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| 平台 | 最适合的主要领域 | 工程化优势 | 主要局限与潜在维护成本 | 综合判断 |
| **Microsoft Power Platform** | Microsoft 365/Teams/SharePoint/Dataverse 环境中的内部应用、表单、审批、自动化 | 官方 ALM 支持 Solutions、环境迁移、源码管理及 CI/CD；与微软身份、Office 和 Power Automate 集成紧密。[16] | 大规模采用必须治理环境、连接器和权限；Dataverse、Premium Connector 及许可结构会进入 TCO。独立 TEI 模型三年许可成本本身已是主要成本项。[4] | **微软生态内部应用：强推荐**；跨云核心产品：条件式 |
| **Mendix** | 大中型企业业务应用、制造/ERP 延伸、移动和 Web 应用 | 支持 Mendix Cloud、Kubernetes、Azure 等部署方式；Team Server 使用 Git，适合规范化企业开发。[17] | Git 并不意味着完全等同于普通源码：官方文档指出某些专有`.mpr/.mxunit`模型文件不能使用普通 Git CLI/第三方工具正确合并，仍依赖 Studio Pro。[11] | **大型企业应用：强**；代码/工具链可移植性：中等偏弱 |
| **OutSystems** | 企业数字化、客户门户、移动应用、遗留系统现代化 | 提供运行时、发布、代码质量检测、性能与错误监控；ODC 支持日志、Trace、Analytics，并可通过 OpenTelemetry 向 Datadog、Dynatrace、Splunk、Elastic、New Relic 等输出遥测。[18] | 平台帮助发现技术债并不等于消除技术债；应用越深入使用专有运行时和组件，迁移成本越高。Gartner 已单独提出 LCAP 技术债治理问题。[10] | **企业级 LC 能力强**；需主动设计退出与扩展边界 |
| **Appian** | 流程、案件管理、保险/金融后台、跨系统业务编排 | 流程/数据模型是一等公民；官方支持 unit、UI、performance testing，Health Check 可发现设计和性能风险。[13] | 更适合“业务过程复杂”而非“算法/计算复杂”；高性能自定义计算仍宜放到外部服务。平台本身也要求性能验证，而非保证所有模型自动扩展。[19] | **流程密集型场景：强推荐** |
| **Retool** | 内部管理后台、客服/运营工具、数据操作工具、人工审核工作台 | 对专业开发者友好，可直接使用 SQL、JavaScript/Python/API；支持 GitHub/GitLab/Bitbucket/Azure Repos 等源码控制与 PR 工作流。[20] | 自托管虽然增加数据与基础设施控制，但官方文档明确指出 self-managed 模式具有更高运营负担，由客户承担更新、维护和基础设施运维。[21] | **内部工具：非常强**；通用公众产品平台：条件式 |

这里最容易产生一个误判：**“支持 Git”不等于“无供应商锁定”。**锁定至少有四层——业务模型格式、平台 API/组件、部署运行时以及许可/身份/数据生态。Retool 在源码工作流方面比纯模型驱动平台更接近专业开发习惯；Mendix 虽基于 Git 管理版本，但模型工件仍有专有语义；Power Platform 的 Solutions/Dataverse、OutSystems 与 Appian 的应用模型也属于各自平台的执行体系。[20]

同样，“平台化”也并不必然削弱运维能力。OutSystems 已支持 OpenTelemetry 输出，Mendix 有平台日志和健康检查，Appian 有 Monitor/Health Check，Retool 有审计和容器日志。这意味着今天的企业级 LCAP 可以纳入 SRE/安全体系；真正的问题变成了**平台暴露的遥测粒度是否足够，以及故障是否发生在用户无法控制的抽象层内部**。[22]

测试也是类似情况。低代码不会自动免除测试，只是把一部分错误从“语法/框架代码”转化成“模型、权限、连接器、流程状态和数据规则”错误。Appian 官方仍明确要求单元、UI、性能和验证测试；研究界也专门研究低代码测试框架，说明测试不是平台已彻底解决的问题。[13]

### 场景与利益相关者分析

下表的推荐等级不是厂商排名，而是根据本次证据综合得到的**架构适配度**。

|  |  |  |  |
| --- | --- | --- | --- |
| 场景 | 推荐程度 | 为什么可能更高效 | 什么时候维护成本会反转 |
| **内部企业应用：ERP/CRM 定制、审批、资产/库存、HR** | **强推荐：★★★★☆** | 数据表、权限、表单、CRUD、审批和通知高度标准化，正是预制组件与连接器最能消除重复编码的领域；Heathrow、Siemens、Retool 客户均有大规模案例。[23] | 当低代码应用逐步变成企业事实上的核心 ERP，出现大量自定义规则、复杂事务和跨系统耦合时，平台升级和许可成本会扩大。[2] |
| **面向客户的数字产品** | **条件推荐：★★★☆☆** | 门户、账户管理、简单交易流程、B2B 客户界面等可快速上线；部分平台已具有企业级部署与监控能力。[14] | 若产品竞争力来自独特 UI、动画、离线能力、极低延迟、复杂实时状态或快速试验底层技术，平台抽象可能成为约束。社区研究中的“缺少定制”“平台性能”“复杂功能需编码”尤为相关。[2] |
| **原型/MVP/快速迭代** | **最强推荐：★★★★★** | 可以快速验证需求、让业务人员直接参与，减少需求—设计—编码多轮翻译；系统综述和社区实证均把快速原型/开发速度列为主要价值。[5] | 最大风险是“原型意外成为十年生产系统”。进入产品化阶段前必须重新检查性能、可测试性、数据架构及退出方案。[10] |
| **数据集成/工作流/RPA/自动化** | **强推荐：★★★★☆** | 预制连接器、API、事件和流程引擎消除大量 glue code；社区研究发现 workflow/process automation 正是低代码最受欢迎的用途之一。[2] | 高吞吐流处理、复杂一致性、长事务、精细重试/幂等语义、数据工程管线不应简单用可视化工作流替代专门的数据/消息基础设施。 |
| **复杂业务逻辑/高性能核心系统** | **通常不推荐作为主体：★★☆☆☆** | 可用于后台管理、配置台和业务编排层。 | 算法密集、超低延迟、大吞吐、复杂并发、特殊数据库访问及高度定制架构会不断突破平台抽象；此时同时维护低代码模型与扩展代码可能比直接传统开发更复杂。[2] |

其中“数据集成/自动化”的边界尤其值得注意：低代码非常适合**编排**“调用哪些系统、谁审批、失败后通知谁”，但不一定适合承载“每秒处理几十万事件时的分区策略、背压、事务语义和内存管理”。这正是“业务复杂”与“计算机科学复杂”之间的区别。

不同利益相关者也会得出不同答案：

|  |  |  |  |
| --- | --- | --- | --- |
| 利益相关者 | 主要收益 | 主要担忧 | 最合理的评价 |
| **企业管理者/CIO** | backlog 减少、上市速度提高、更多小需求被数字化；可能得到较高 ROI。Forrester TEI 的复合企业模型就是典型例子。[4] | 许可证随用户/应用规模增长；应用泛滥、平台集中风险与未来迁移成本。 | 不应只问“能否更快”，而应问“5 年后每个活跃应用的 TCO 与退出成本是多少”。 |
| **专业开发者** | 少写 CRUD、认证、表单、部署样板代码，将精力投入领域逻辑；Retool 等平台仍能直接使用 SQL/JS/Python。[24] | 平台 DSL、专有调试方式和抽象泄漏；复杂功能最终又需要代码。社区研究明确观察到这种矛盾。[2] | 对专业开发者而言，最佳低代码是“减少低价值编码”，而不是“禁止编码”。 |
| **运维/安全团队** | 统一身份、权限、环境、日志、审计和发布链路，可以比各部门私搭应用更容易治理。[25] | Citizen Development 会迅速扩大资产数量；必须管理数据连接器、凭据、PII、环境和第三方组件。 | 没有 CoE/平台工程和资产清单时，不应大规模开放 Citizen Development。 |
| **业务人员** | 需求离实现更近，可自己试验、修改小流程；减少等待中央 IT。[4] | “无需写代码”并不等于“无需软件工程知识”；数据模型、权限、异常、测试仍需要训练。高学习曲线也是社区研究中最常见的挑战类别之一。[2] | Citizen Developer 最适合成为**受治理的领域开发者**，而不是替代专业工程师。 |

### 企业案例、风险与限制

真实案例最一致地证明的是“交付速度”和“业务流程效率”，而最少公开的是失败率、五年 TCO 与迁移成本。以下所有经济结果都应注意：除特别说明外，多来自平台厂商客户案例，因此存在成功案例选择偏差。

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| 企业与规模 | 行业 | 平台 | 公开收益 | 已知问题、代价或证据限制 |
| **Heathrow Airport** | 航空/机场 | Microsoft Power Apps | 2019 年 Microsoft 案例称员工开发约**30 个应用**，消除**75,000 页纸张**，减少接近**1,000 小时数据录入**。[23] | 这是非常适合 LC 的内部流程场景；公开案例**未披露多年许可证、bug 率和应用退役/升级成本**。 |
| **Siemens / Siemens Energy** | 工业制造、能源 | Mendix | Siemens 已将 Mendix 扩展至**1,000+ 应用、数千名参与员工**；单个 freight-claims 项目六周交付，厂商案例称开发速度约 4 倍、ROI 2,400%。[26] | Siemens Digital Industries Software 本身拥有 Mendix，利益关系显著；更重要的是 Siemens 为规模化采用建立了正式 Adoption Program、认证、DevOps meetup 和治理机制，说明低代码规模化并非“无需工程管理”。[27] |
| **Petrobras** | 石油能源 | OutSystems | OutSystems 案例称其 CoE 支撑**100+ 敏捷团队、500+ 开发人员**；8 个月交付 48 个应用、每月 400+ 次部署，新应用开发比此前流程快最高约 60%。[28] | 成果与**Center of Excellence**同时出现，难以把速度全部归因于工具；公开资料没有提供传统开发与低代码的完整许可证/TCO 对照。 |
| **Aon Reinsurance Solutions** | 保险/再保险，业务覆盖 120+ 国家和地区 | Appian | Aon 使用 Appian 在其“8-week guarantee”框架下交付新的 claims workflow，整合原有算法、理赔和计费逻辑，并报告理赔受理和开票处理明显加快。[29] | 这是“流程复杂但算法可继续留在原系统”的典型成功模式；**未公开量化的长期维护成本、许可证或迁移费用**。 |
| **DoorDash** | 互联网配送 | Retool | 团队称内部工具由过去每个约**1–2 个月缩短为 30–60 分钟**；已有**40+**个活跃运营工具，简单维护从不确定工期缩到数分钟。[30] | 极端效率增益来自典型“内部管理工具”，不能外推到 DoorDash 的核心配送算法和客户 App；长期许可/TCO 未公开。 |
| **Altrad Sparrows** | 能源工程服务 | OutSystems | 一名开发者在四年中实现**100+ 模块**，支撑**2,000+ 用户**；厂商称节约员工工时价值约**£600,000**。[31] | 单开发者体现生产力，也意味着可能出现**关键人员知识集中风险**——这是本报告根据团队规模作出的推论，而非案例直接报告的问题。厂商案例未给出独立审计。 |
| **Teachable** | 在线教育 SaaS | Retool | 将面向客户的分析 dashboard 在一个月内提供给前 100 名客户，次月扩展到 1,000 名；部分迭代由原来数天/数周压缩到约一小时，并使用 VPC 自托管、SSO、RBAC。[32] | 证明 LC 也能进入部分客户侧产品，但案例没有披露大规模长期性能和完整 TCO，因此不足以证明 Retool 适合所有公众产品。 |

这些案例共同揭示一个非常稳定的模式：**成功企业很少把低代码理解为“任何人随便拖几下就上线”，而是把它做成平台工程能力。**Siemens 和 Petrobras 都伴随正式治理或 CoE；Forrester 的 Power Apps 模型也计入了培训和持续管理成本。[27]

主要风险与限制可以归纳如下：

|  |  |  |  |
| --- | --- | --- | --- |
| 风险 | 何时最危险 | 影响 | 建议控制措施 |
| **供应商锁定/退出困难** | 预计使用 5–10 年以上、核心业务、大量专有组件 | 迁移重新实现、双栈运行成本 | 把核心领域逻辑置于平台外 API/service；每年进行 exit test；保存数据模式、接口契约和业务规则文档。Mendix 的专有模型合并限制说明仅有 Git 不足以保证可移植性。[11] |
| **许可证成本反转** | 用户/应用/自动化执行量快速上升 | OPEX 可能超过节省的人力成本 | TCO 模型必须至少包括许可证、Premium Connector、非生产环境、运维和培训；Power Apps TEI 即显示许可为显著成本项。[4] |
| **技术债被视觉化而非消除** | 大量复制流程、隐藏依赖、复杂 expression、自定义插件 | 修改影响范围不透明 | 建立架构审查、模块复用、静态/平台质量扫描和技术债预算；Gartner 已将 LCAP 技术债作为专门治理主题。[10] |
| **Shadow IT 变成“官方 Shadow IT”** | 任何员工都能创建生产应用，却无 owner/生命周期制度 | 孤儿应用、数据权限扩大、重复系统 | 建立应用目录、owner、数据分级、发布审批和自动过期机制。Forrester 同时观察到 LC 可以减少传统 Shadow IT，但前提是处于 IT 批准边界内。[4] |
| **抽象泄漏与调试困难** | 复杂事务、特殊 UI、边缘 API、异常并发 | 开发者需要同时理解平台和底层代码 | PoC 必须测试最困难的 10% 需求，而不是只实现最简单的 80%；社区研究明确报告复杂问题仍需编码及维护/调试困难。[2] |
| **性能/扩展误判** | 大数据量、N+1 查询、高并发、批处理 | 成本增加或 SLA 失效 | 上线前执行真实数据规模和峰值负载测试；Appian 官方也明确把数据量、查询复杂度和资源作为性能因素。[19] |
| **技能错配** | 把“少写代码”理解为“不需要工程技能” | 权限、数据、错误处理和测试缺陷 | Citizen Developer 与专业开发者 pairing；分级认证和 production 权限。社区研究发现“学习曲线高”和“仍需要编程基础”同时存在。[2] |
| **平台升级/产品路线依赖** | 长寿命核心系统、专有插件多 | 被迫适配版本和弃用 API | 建立兼容性测试环境；减少非官方组件；合同中关注生命周期/SLA；保持核心逻辑平台无关。 |
| **单厂商可用性风险** | 整个业务完全依赖平台 runtime | 平台故障影响大量应用 | 对核心链路设计降级/灾备；关键逻辑通过独立服务隔离。 |

需要特别指出三个数据缺口。

第一，**未找到可比数据：生产环境 bug 率。**公开研究通常报告“开发速度”“满意度”“质量评分”，极少按相同业务复杂度报告 defects/KLOC、每功能点生产事故等指标。[5]

第二，**未找到可比数据：跨平台长期迁移成本。**虽然技术上可以明确看到模型与运行时锁定，但没有足够公开样本能够回答“从 Mendix/OutSystems/Power Platform 迁移一个 50 万功能点系统平均花多少”。因此，本文只能确定方向性风险，无法给出可信行业均值。[11]

第三，**未找到可比数据：传统开发与 LC/NC 的五年以上全生命周期 TCO。**Forrester TEI 提供三年财务模型，但它是特定平台、厂商委托且基于复合企业；学术实验又太小。这是目前判断“长期一定更便宜”时最大的证据缺口。[33]

### 决策框架、实践建议与未来趋势

对于实际选型，比“低代码还是传统开发”更有效的问题是：

**哪一部分复杂性值得交给平台管理，哪一部分必须由组织自己拥有？**

以下矩阵是本报告基于上述证据提出的决策框架，并非某厂商或行业标准。

|  |  |  |  |
| --- | --- | --- | --- |
| 项目特征 | 低代码优先 | 混合架构优先 | 传统开发优先 |
| 业务主要是表单、CRUD、审批、工作流 | **是** |  |  |
| 需求变化快、需要频繁与业务人员共同迭代 | **是** |  |  |
| 已购买 Microsoft/其他平台生态且连接器覆盖高 | **是** |  |  |
| MVP/短生命周期部门工具 | **是** |  |  |
| 需要连接 ERP/CRM，但核心逻辑已存在 |  | **是：LC 做界面/编排** |  |
| 有一部分复杂算法或高吞吐处理 |  | **是：核心服务高代码化** |  |
| 对外产品但后台管理占较大比例 |  | **是** |  |
| 极强品牌化、差异化前端体验 |  | 可用于后台 | **是** |
| 超低延迟、高并发、实时计算 |  | 可用于控制面 | **是** |
| 特殊数据存储、复杂事务/一致性模型 |  | **通常是** | **核心部分是** |
| 预计十年以上生命周期且退出平台代价不可接受 |  | 可局部使用 | **是** |
| 无 CoE、无应用资产管理、无生产发布控制 | **暂不应规模化** |  |  |
| 监管严格但本质是案件/审批/审计流程 | **可采用企业 LCAP** | **常为最佳** | 视核心计算而定 |

综合证据表明，一个相对稳健的默认架构是：

**低代码 = 体验/流程/编排层；传统代码 = 差异化能力、复杂计算和长期核心资产层。**这种方式既利用预制 UI、流程、权限、集成和部署能力，也避免把无法替代的核心业务算法封死在单一平台中。Appian/Aon 的案例就是较典型的模式：新的低代码流程层继续调用已有算法、理赔和计费逻辑，而非一次性重写所有后台系统。[29]

否

是

是

否

否

是

否

是

否

是

是

否

新的软件需求

主要是表单、CRUD、工作流、集成吗？

存在极致性能、复杂算法或高度定制 UX 吗？

标准组件/连接器可覆盖大部分需求吗？

传统开发为主

混合架构：低代码界面/编排 + 高代码服务

可接受平台许可与供应商锁定吗？

已有 ALM、测试、安全、CoE 和资产治理吗？

先建立治理，再做受控 PoC

低代码优先实施

PoC 的性能、测试、TCO、退出测试达标吗？

进入生产并持续度量

实际 PoC 不应只测“Hello World”。最有效的试点方法是刻意选取项目中**最复杂的集成、权限、查询、批处理和 UI 定制需求**；如果这些需求仍能以清晰、可测试和可观测的方式实现，低代码才真正适配。这个做法直接针对社区研究观察到的“简单需求非常快、复杂需求突然跌出抽象层”的风险。[2]

上线后应持续测量，而不是以“应用数量”作为成功指标。推荐至少跟踪 Lead Time for Changes、每月生产故障、MTTR、每次发布人工工时、平台许可成本/活跃用户、每个活跃应用的维护工时、自定义代码比例、连接器数量、孤儿应用数量，以及“平台外核心服务”占比。这样才能判断最初的开发速度优势是否真正转化为五年 TCO 优势。

未来三到五年，即约**2027–2031 年**，本报告作出以下判断：

|  |  |  |
| --- | --- | --- |
| 趋势预测 | 置信度 | 依据 |
| **低代码将与 Agentic AI 深度融合，视觉拖拽不再是核心卖点** | **高** | Gartner 的 2025–2026 市场研究已经将 Agentic AI 视为市场增长和领先者扩大优势的重要因素，并预测低代码技术市场到 2029 年继续保持双位数增长。[34] |
| **“自然语言 → 应用/流程/代理”会继续降低首版开发成本，但不会同比例降低维护成本** | **中—高** | AI 能生成模型、逻辑和连接，但 Gartner 已同时强调低代码技术债管理；生成更多软件也意味着更多需要维护的软件资产。[10] |
| **Citizen Development 将从自由式民主化转向强治理模式** | **高** | Siemens、Petrobras 的大规模案例均依赖 Adoption Program/CoE；Forrester 企业访谈把治理、合规和减少 Shadow IT 作为正式价值，而不是附加功能。[27] |
| **低代码将越来越像“企业编排层”，而不是传统代码的全面替代品** | **高** | Appian 聚焦流程/数据编排，Power Platform 聚焦应用+自动化，Retool 聚焦内部操作界面，主流企业案例也主要集中在系统连接、工作流和操作层。[35] |
| **Pro-code 与 low-code 的边界继续模糊** | **高** | Retool 已把 Git、SQL、JS/Python/API 纳入开发体验；Mendix 使用 Git 并支持多种部署目标；OutSystems 可向标准 OpenTelemetry 生态输出可观测性数据。[20] |
| **供应商锁定不会因 AI 消失，甚至可能更难察觉** | **中—高** | 应用生成变快后，组织可能更迅速积累平台专有模型、连接器和自动化资产；Mendix 的模型文件限制及社区中的 vendor-lock-in 反馈显示锁定是架构属性，而非仅仅是编码量问题。[11] |
| **市场继续增长，但“低代码”这个分类本身会逐渐模糊** | **高（方向），中（规模）** | Forrester 的 2028 基准/AI 上行情景与 Gartner 2029 预测都指向增长，但两者市场口径和规模明显不同，说明低代码、DPA、AI AppGen、RPA、内部工具、业务编排正在融合。[36] |

因此，对用户提出的核心问题可以给出一个明确回答：

**低代码/无代码确实提高了开发效率，而且在合适场景中提升幅度可以很大；这不是纯营销叙事。**直接实验、结构化社区研究和大规模企业案例在这一点上方向高度一致。[1]

但更准确地说，它提高的是**被平台标准化的那一部分软件工程效率**。如果业务需求主要由表单、数据、权限、流程、连接器和标准 UI 构成，低代码往往同时降低初始开发和短期维护成本；如果系统的竞争优势来自平台无法抽象的复杂性，低代码就可能把原本的一层技术栈变成“平台 + 专有 DSL/模型 + 扩展代码 + 外部服务”的多层技术栈，长期成本反而上升。[2]

所以企业真正需要优化的目标，不是“低代码覆盖率”，而是：

**在不牺牲可移植性、可测试性、性能和长期所有权的前提下，最大限度减少没有差异化价值的手写代码。**

### 主要参考来源

|  |  |
| --- | --- |
| 类型 | 主要来源及本报告用途 |
| **Gartner** | *Forecast Analysis: Low-Code Development Technologies, Worldwide*，用于 2029 市场预测及增长驱动判断。[8]*Market Share Analysis: Low-Code Application Platforms, Worldwide, 2025*，用于 Agentic AI 趋势。[9]*5 Strategies to Reduce Technical Debt in Low-Code Development*，用于长期技术债风险。[10] |
| **Forrester** | 2024 低代码市场分析，用于 2023 市场规模、2028 基准/AI 情景与开发者采用率。[7]Microsoft Power Apps TEI 2024，用于开发时间、ROI、许可、培训和持续管理成本；明确按厂商委托研究降权。[4] |
| **IDC 中国** | 2022、2023 中国低代码/零代码软件市场跟踪及 2027 年预测，用于中国市场规模与趋势。[6] |
| **同行评审/学术研究** | Bucaioni、Cicchetti、Ciccozzi 的多声部系统综述，用于研究成熟度、证据缺口及工程问题。[5]Trigo、Varajão、Almeida 的低代码生产力对照研究，用于开发与维护效率。[1] |
| **开发者社区实证研究** | 武汉大学、Monash、UIUC 团队在 ESEM 2021 对 73 条 Stack Overflow 与 228 条 Reddit 低代码讨论的系统编码，用于学习、定制、维护、价格、锁定等风险判断。[2] |
| **Microsoft 官方资料** | Power Platform ALM 文档及 Heathrow 客户案例，用于 CI/CD、环境管理和 Citizen Development 实例。[37] |
| **Mendix 官方资料** | Deployment、Version Control 文档及 Siemens 案例，用于部署弹性、Git/专有模型约束及大规模企业治理。[38] |
| **OutSystems 官方资料** | 监控、OpenTelemetry、代码质量文档及 Petrobras/Altrad Sparrows 案例，用于可观测性、技术债和规模化交付。[18] |
| **Appian 官方资料** | 测试、Health Check、性能文档及 Aon 案例，用于流程型低代码、测试能力和复杂企业业务编排。[13] |
| **Retool 官方资料** | Source Control、自托管文档及 DoorDash、Teachable 等案例，用于内部工具效率、专业代码结合与 self-hosted 运维成本。[20] |

## 引用资料与扫描来源（保留原分组）

Citations · 38

[researchgate.net researchgate.net](https://www.researchgate.net/publication/365873896_Low-Code_Versus_Code-Based_Software_Development_Which_Wins_the_Productivity_Game?utm_source=chatgpt.com)  

**1** [(PDF) Low-Code Versus Code-Based Software Development](https://www.researchgate.net/publication/365873896_Low-Code_Versus_Code-Based_Software_Development_Which_Wins_the_Productivity_Game?utm_source=chatgpt.com)

[arxiv.org arxiv.org](https://arxiv.org/html/2107.07482v1)  

**2** [Characteristics and Challenges of Low-Code Development: The Practitioners’ Perspective](https://arxiv.org/html/2107.07482v1)

**3** [Characteristics and Challenges of Low-Code Development: The Practitioners’ Perspective](https://arxiv.org/html/2107.07482v1)

[tei.forrester.com tei.forrester.com](https://tei.forrester.com/go/microsoft/powerappstei/?lang=en-us)  

**4** [The Total Economic Impact™ Of Microsoft Power Apps](https://tei.forrester.com/go/microsoft/powerappstei/?lang=en-us)

**25** [The Total Economic Impact™ Of Microsoft Power Apps](https://tei.forrester.com/go/microsoft/powerappstei/?lang=en-us)

**33** [The Total Economic Impact™ Of Microsoft Power Apps](https://tei.forrester.com/go/microsoft/powerappstei/?lang=en-us)

[link.springer.com link.springer.com](https://link.springer.com/article/10.1007/s10270-021-00964-0)  

**5** [Modelling in low-code development: a multi-vocal systematic review | Software and Systems Modeling | Springer Nature Link](https://link.springer.com/article/10.1007/s10270-021-00964-0)

[idc.com idc.com](https://www.idc.com/resource-center/blog/press-release-type/insights/page/144/?utm_source=chatgpt.com)  

**6** [Insights Archives - Page 144 of 220 - IDC](https://www.idc.com/resource-center/blog/press-release-type/insights/page/144/?utm_source=chatgpt.com)

[forrester.com forrester.com](https://www.forrester.com/blogs/the-low-code-market-could-approach-50-billion-by-2028/?utm_source=chatgpt.com)  

**7** [The Low-Code Market Could Approach $50 Billion By 2028](https://www.forrester.com/blogs/the-low-code-market-could-approach-50-billion-by-2028/?utm_source=chatgpt.com)

**36** [The Low-Code Market Could Approach $50 Billion By 2028](https://www.forrester.com/blogs/the-low-code-market-could-approach-50-billion-by-2028/?utm_source=chatgpt.com)

[gartner.com gartner.com](https://www.gartner.com/en/documents/7146430?utm_source=chatgpt.com)  

**8** [Forecast Analysis: Low-Code Development Technologies, Worldwide](https://www.gartner.com/en/documents/7146430?utm_source=chatgpt.com)

**9** [Market Share Analysis: Low-Code Application Platforms, Worldwide, 2025](https://www.gartner.com/en/documents/7987137?utm_source=chatgpt.com)

**34** [Market Share Analysis: Low-Code Application Platforms, Worldwide, 2025](https://www.gartner.com/en/documents/7987137?utm_source=chatgpt.com)

**10** [5 Strategies to Reduce Technical Debt in Low-Code Development](https://www.gartner.com/en/documents/7378730?utm_source=chatgpt.com)

**15** [Best Enterprise Low-Code Application Platforms (Transitioning to AI ...](https://www.gartner.com/reviews/market/enterprise-low-code-application-platform?utm_source=chatgpt.com)

[docs.mendix.com docs.mendix.com](https://docs.mendix.com/refguide10/using-version-control-in-studio-pro/)  

**11** [Using Version Control in Studio Pro | Mendix Documentation](https://docs.mendix.com/refguide10/using-version-control-in-studio-pro/)

**12** [Deployment | Mendix Documentation](https://docs.mendix.com/developerportal/deploy/?utm_source=chatgpt.com)

**17** [Deployment | Mendix Documentation](https://docs.mendix.com/developerportal/deploy/?utm_source=chatgpt.com)

**38** [Deployment | Mendix Documentation](https://docs.mendix.com/developerportal/deploy/?utm_source=chatgpt.com)

[docs.appian.com docs.appian.com](https://docs.appian.com/suite/help/26.8/introduction-to-application-building.html?utm_source=chatgpt.com)  

**13** [Introduction to Application Building in Appian](https://docs.appian.com/suite/help/26.8/introduction-to-application-building.html?utm_source=chatgpt.com)

**19** [System Requirements [Administration]](https://docs.appian.com/suite/help/26.8/System_Requirements.html?utm_source=chatgpt.com)

[success.outsystems.com success.outsystems.com](https://success.outsystems.com/documentation/outsystems_developer_cloud/monitoring_and_troubleshooting_apps/?utm_source=chatgpt.com)  

**14** [Monitoring and troubleshooting apps - ODC Documentation](https://success.outsystems.com/documentation/outsystems_developer_cloud/monitoring_and_troubleshooting_apps/?utm_source=chatgpt.com)

**18** [Monitoring and troubleshooting apps](https://success.outsystems.com/documentation/11/monitoring_and_troubleshooting_apps/?utm_source=chatgpt.com)

**22** [Streaming observability data - ODC Documentation](https://success.outsystems.com/documentation/outsystems_developer_cloud/monitoring_and_troubleshooting_apps/streaming_observability_data/?utm_source=chatgpt.com)

[learn.microsoft.com learn.microsoft.com](https://learn.microsoft.com/en-us/power-platform/alm/overview-alm?utm_source=chatgpt.com)  

**16** [Application lifecycle management (ALM) with Microsoft Power Platform - Power Platform | Microsoft Learn](https://learn.microsoft.com/en-us/power-platform/alm/overview-alm?utm_source=chatgpt.com)

**37** [Application lifecycle management (ALM) with Microsoft Power Platform - Power Platform | Microsoft Learn](https://learn.microsoft.com/en-us/power-platform/alm/overview-alm?utm_source=chatgpt.com)

[docs.retool.com docs.retool.com](https://docs.retool.com/source-control/?utm_source=chatgpt.com)  

**20** [Source Control documentation](https://docs.retool.com/source-control/?utm_source=chatgpt.com)

**21** [Self-hosted deployments](https://docs.retool.com/self-hosted?utm_source=chatgpt.com)

[microsoft.com microsoft.com](https://www.microsoft.com/en/customers/story/766053-heathrow-airport-travel-transportation-power-apps?utm_source=chatgpt.com)  

**23** [Heathrow Airport inspires employee engagement with ...](https://www.microsoft.com/en/customers/story/766053-heathrow-airport-travel-transportation-power-apps?utm_source=chatgpt.com)

[retool.com retool.com](https://retool.com/customers/zeus?utm_source=chatgpt.com)  

**24** [Zeus](https://retool.com/customers/zeus?utm_source=chatgpt.com)

**30** [Doordash](https://retool.com/customers/doordash?utm_source=chatgpt.com)

**32** [Teachable](https://retool.com/customers/teachable-builds-reporting-and-analytics-dashboards?utm_source=chatgpt.com)

[mendix.com mendix.com](https://www.mendix.com/customer-stories/how-siemens-ag-is-unlocking-strategic-value-with-over-1000-mendix-applications/?utm_source=chatgpt.com)  

**26** [How Siemens AG is Unlocking Strategic Value with Over ...](https://www.mendix.com/customer-stories/how-siemens-ag-is-unlocking-strategic-value-with-over-1000-mendix-applications/?utm_source=chatgpt.com)

**27** [Siemens Enables Rapid Digitization in a 175-Year-Old ...](https://www.mendix.com/customer-stories/siemens-enables-rapid-digitization-in-a-175-year-old-enterprise/?utm_source=chatgpt.com)

[outsystems.com outsystems.com](https://www.outsystems.com/case-studies/petrobras-agile-development?utm_source=chatgpt.com)  

**28** [Petrobras Embraces Development at Scale with Low-Code](https://www.outsystems.com/case-studies/petrobras-agile-development?utm_source=chatgpt.com)

**31** [Altrad Sparrows Improves Employees' Efficiency and ...](https://www.outsystems.com/case-studies/sparrows-employee-efficiency?utm_source=chatgpt.com)

[appian.com appian.com](https://appian.com/about/explore/customers/all-customers/aon?utm_source=chatgpt.com)  

**29** [Aon](https://appian.com/about/explore/customers/all-customers/aon?utm_source=chatgpt.com)

**35** [About Appian | Enterprise AI Automation Platform](https://appian.com/about/explore/overview?utm_source=chatgpt.com)

Sources scanned · 531

[tei.forrester.com tei.forrester.com](https://tei.forrester.com/go/microsoft/powerappstei/?lang=en-us)  

The Total Economic Impact™ Of Microsoft Power Apps

Total lines: 538

[gartner.com gartner.com](https://www.gartner.com/en/documents/7987137)  

Market Share Analysis: Low-Code Application Platforms, Worldwide, 2025

https://www.gartner.com/en/documents/7987137

Forecast Analysis: Low-Code Development Technologies, Worldwide

The low-code development technologies market is projected to reach $58.2 billion by 2029, with a robust double-digit CAGR of 14.1%.

Best Enterprise Low-Code Application Platforms (Transitioning to AI ...

Gartner defines enterprise low-code application platforms (LCAPs) as software platforms for the accelerated development and maintenance of applications,

5 Strategies to Reduce Technical Debt in Low-Code Development

https://www.gartner.com/en/documents/7378730

Quick Answer: Assessing No-Code Development for Enterprise Applications

GARTNER INSIGHTS ABSTRACT QUICK ANSWER: ASSESSING NO-CODE DEVELOPMENT FOR ENTERPRISE APPLICATIONS Published: 29 January 2025 SUMMARY No-code development tools have gained popularity in recent yea...

Tool: When to Use Low-Code Application Development Versus Traditional Coding

GARTNER INSIGHTS ABSTRACT TOOL: WHEN TO USE LOW-CODE APPLICATION DEVELOPMENT VERSUS TRADITIONAL CODING Published: 18 June 2025 SUMMARY Low-code application development is an alternative to tradit...

Risk and Opportunity Index: Low-Code Application Platforms

GARTNER INSIGHTS ABSTRACT RISK AND OPPORTUNITY INDEX: LOW-CODE APPLICATION PLATFORMS Published: 24 May 2024 SUMMARY The market for low-code application platforms is growing rapidly but it is very...

When and How to Use Low Code for Software Modernization

GARTNER INSIGHTS ABSTRACT WHEN AND HOW TO USE LOW CODE FOR SOFTWARE MODERNIZATION Published: 05 August 2025 SUMMARY Software modernization is a major challenge for organizations that aim to deliv...

Gartner Hype Cycle Shows AI Practices and Platform Engineering Will Reach Mainstream Adoption in Software Engineering in Two to Five Years

STAMFORD, CONN., NOVEMBER 28, 2023 GARTNER HYPE CYCLE SHOWS AI PRACTICES AND PLATFORM ENGINEERING WILL REACH MAINSTREAM ADOPTION IN SOFTWARE ENGINEERING IN TWO TO FIVE YEARS BY 2027, 50% OF ENTERPR...

Market Share Analysis: Application Development Software, Worldwide, 2023

GARTNER INSIGHTS ABSTRACT MARKET SHARE ANALYSIS: APPLICATION DEVELOPMENT SOFTWARE, WORLDWIDE, 2023 Published: 19 September 2024 SUMMARY The application development software market grew 10.7% in 2...

Market Share: Application Development, Worldwide, 2023

GARTNER INSIGHTS ABSTRACT MARKET SHARE: APPLICATION DEVELOPMENT, WORLDWIDE, 2023 Published: 13 June 2024 SUMMARY AD grew by 10.7% in 2023, reaching $21.0 billion. Create continued to be the domin...

Gartner Says More Than 80% of Enterprises Will Have Used Generative AI APIs or Deployed Generative AI-Enabled Applications by 2026

STAMFORD, CT, OCTOBER 11, 2023 GARTNER SAYS MORE THAN 80% OF ENTERPRISES WILL HAVE USED GENERATIVE AI APIS OR DEPLOYED GENERATIVE AI-ENABLED APPLICATIONS BY 2026 ANALYSTS TO DISCUSS GENERATIVE AI T...

Journey Guide to Enterprise Low-Code Adoption

GARTNER INSIGHTS ABSTRACT JOURNEY GUIDE TO ENTERPRISE LOW-CODE ADOPTION Published: 17 February 2026 SUMMARY Strategic low-code adoption accelerates app delivery, yet most rush and experience wast...

Podcast: Low Code — What’s Beyond the Gartner Magic Quadrant?

GARTNER INSIGHTS ABSTRACT PODCAST: LOW CODE — WHAT’S BEYOND THE GARTNER MAGIC QUADRANT? Published: 17 January 2024 SUMMARY Low-code application platforms — or LCAPs — offer many benefits to solut...

[forrester.com forrester.com](https://www.forrester.com/blogs/the-low-code-market-could-approach-50-billion-by-2028/)  

The Low-Code Market Could Approach $50 Billion By 2028

https://www.forrester.com/blogs/the-low-code-market-could-approach-50-billion-by-2028/

The Partner Opportunity For Microsoft Power Platform

Total Economic Impact THE PARTNER OPPORTUNITY FOR MICROSOFT POWER PLATFORM A Total Economic Impact™ Partner Opportunity Analysis A FORRESTER TOTAL ECONOMIC IMPACT STUDY COMMISSIONED BY Microsoft,...

The State Of Low-Code, North America 2024 | Forrester

Data Overview Report THE STATE OF LOW-CODE, NORTH AMERICA 2024 LOW-CODE IS EVERYWHERE, BUT WE’RE STILL WRITING A LOT OF CODE John Bratincevic and four contributors Sep 3, 2024 SUMMARY In North...

OutSystems ROI Estimator

OutSystems ROI Estimator By answering the questions below, you will receive free access to a high-level estimate of the Total Economic Impact of OutSystems for your organization (registration is req...

Predictions 2024: Software Development

PREDICTIONS 2024: SOFTWARE DEVELOPMENT ADAPTS TO TURINGBOTS, AJAR SOURCE, AND BACKSTAGE Chris Gardner, VP, Research Director Oct 30 2023 A year ago, we predicted that citizen development would dom...

The Total Economic Impact™ Of Microsoft Azure Integration Services

\* Cost reduction from fewer application support requests. In an integrated environment, data entry errors occur much less frequently, resulting in a reduced number of support tickets for the composite...

The Total Economic Impact™ Of Microsoft Unified

COSTS BY CATEGORY Image: figure 40% Reduction in customer-facing downtime events “Our business’s largest segment had historically relied on legacy, on-premises servers for our proprietary systems....

[idc.com idc.com](https://www.idc.com/resource-center/blog/cloud-native-app-delivery-progress-is-made-but-optimization-is-hard/)  

Cloud Native App Delivery: Progress is Made, But Optimization Is Hard - IDC

October 19, 2023 5 min CLOUD NATIVE APP DELIVERY: PROGRESS IS MADE, BUT OPTIMIZATION IS HARD Image: Feature image WHAT IS CLOUD NATIVE? Before diving into the topic, we need to provide some conte...

Insights Archives - Page 144 of 220 - IDC

https://www.idc.com/resource-center/blog/press-release-type/insights/page/144/

Insights Archives - Page 49 of 220 - IDC

PRESS RELEASE TYPE: INSIGHTS Nov 25, 2024 IDC发布中国工业互联网平台2023年市场份额 北京，2024年11月26日——近日，国际数据公司（IDC）发布了《中国工业互联网平台企业侧：PaaS平台及应用解决方案市场份额，2023：平台应用分流》（Doc#50965024，2024年11月）及《中国工业互联网平台政府侧：区域平台及产业公共服务市场份额...

Asia Pacific Archives - Page 99 of 191 - IDC

RESOURCE REGIONS: ASIA PACIFIC May 11, 2024 IDC：市场小幅收缩——2023年中国IT安全服务市场同比下降0.5% 北京，2024年5月11日——IDC最新发布的《中国IT安全服务市场跟踪报告，2023H2》显示，2023年下半年中国IT安全服务市场厂商整体收入约为122.8亿人民币（约合17亿元美元），同比下降4.4%。结合全年数据，2023全...

Insights Archives - Page 74 of 220 - IDC

PRESS RELEASE TYPE: INSIGHTS Jul 18, 2024 A HIGH LEVEL OF SECURITY IS INSEPARABLE FROM MANAGED SECURITY SERVICES – THE IDC MARKETSCAPE: CHINA CLOUD MANAGED SECURITY SERVICE CAPABILITY 2024 VENDOR A...

IDC - China - Home

AI超级周期下的万亿棋局 中国创新如何重塑全球价值？ IDC Directions 2026：中国ICT市场趋势论坛 观看回放 全球领先企业信赖之选 \* Image: Anthropic \* Image: OpenAI \* Image: Nvidia \* Image: Google \* Image: Baidu \* Image: Puma \* Image: Expedia \* Image...

Insights Archives - Page 192 of 220 - IDC

PRESS RELEASE TYPE: INSIGHTS Jan 17, 2023 IDC FORECASTS STRONG GROWTH FOR LOW-CODE, NO-CODE, AND INTELLIGENT DEVELOPER TECHNOLOGIES A new IDC forecast shows worldwide low-code, no-code, and intell...

The IT Labor Shortage: Post-Pandemic Issue or Long-Term Problem?

target audience: TECH BUYER Publication date: Jun 2022 - Document type: IDC Perspective - Doc Document number: # US49093622 THE IT LABOR SHORTAGE: POST-PANDEMIC ISSUE OR LONG-TERM PROBLEM? By: D...

IDC - CPaaS Segment Is in Transition

June 5, 2023 6 min CPAAS SEGMENT IS IN TRANSITION Image: Feature image The communications-platform-as-a-service (CPaaS) segment is in transition. Over the past few years, companies in this segment...

IDC - Digital Transformation and Cloud Technology: Where Application Development Falls Short

June 6, 2022 6 min DIGITAL TRANSFORMATION AND CLOUD TECHNOLOGY: WHERE APPLICATION DEVELOPMENT FALLS SHORT Image: Feature image Digital Transformation can be regardad as a buzzword. However, IDC re...

IDC - Top 4 Effective Changes A Budget-Conscious IT Organization Can Make In 2023

January 12, 2023 5 min TOP 4 EFFECTIVE CHANGES A BUDGET-CONSCIOUS IT ORGANIZATION CAN MAKE IN 2023 Image: Feature image Are you one of those IT leaders who is facing the challenge of making change...

IDC - IDC FutureScape: Worldwide Future of Operations 2023 Predictions

December 14, 2022 3 min IDC FUTURESCAPE: WORLDWIDE FUTURE OF OPERATIONS 2023 PREDICTIONS Image: Feature image As business across many industries struggle with supply chain disruptions, rising ener...

IDC - IDC CIO Sentiment Survey 2022: The Future CIO Is Not the Same as Today's CIO

August 2, 2022 5 min IDC CIO SENTIMENT SURVEY 2022: THE FUTURE CIO IS NOT THE SAME AS TODAY’S CIO Image: Feature image To discover more strategies CIOs will need in order to plan for contingencies...

How Agile Development Teams Can Resolve Agile Measurement Challenges with Function Point Analysis - IDC

November 3, 2022 4 min HOW AGILE DEVELOPMENT TEAMS CAN RESOLVE AGILE MEASUREMENT CHALLENGES WITH FUNCTION POINT ANALYSIS Image: Feature image Agile development empowers teams with many benefits bu...

Singapore CIO Summit

PARTNERS Host Partner Strategic Partner Smart ICT Partner Innovation Partner Digital Work Platform Partner Summit Partner Summit Partner Summit Partner Platinum Partner Platinum Partner Pla...

IDC China - 研究产品

研究产品 发现机会并做出明智的决策 全球1,300多名专业分析师对全球、地区和本地技术趋势和购买行为提供及时、独特的见解。 Image 定义、评估和引导市场 实现您的目标和推动您的业务绩效是我们的首要任务。我们致力于为您业务旅程的每个阶段提供正确的信息。无论您处于技术路线图的哪个阶段，IDC都有您需要的基于真实数据和严格研究方法的研究。 Image IDC首席研究官（CRO）MER...

IDC China - 行业

基于数十年经验的行业研究 IDC的行业研究帮助商业和IT领导者在六个行业制定技术决策，这六个行业包括零售、政府、金融服务、制造、医疗和能源。 联系我们 Image IDC的行业研究可帮助企业和IT领导者: IDC的行业研究还帮助技术供应商为他们的垂直营销、销售和产品管理战略提供信息，以便他们更紧密地与特定行业的主要趋势和投资重点保持一致。 \* #### 利用成熟的行业洞察力优化IT战...

Insights Archives - Page 73 of 220 - IDC

PRESS RELEASE TYPE: INSIGHTS Jul 23, 2024 数据要素的坚实底座，中国数字政府一体化大数据平台2024年厂商评估结果发布 北京，2024年7月24日——建设数字中国，发展数字经济是推进中国式现代化的重要引擎。数字基础设施和数据资源体系是数字中国建设的“两大基础”，需要对数据资源规模和质量进行大幅提升。大数据平台作为数字基础设施的关键能力，支撑政务服务、...

China Archives - Page 12 of 16 - IDC

RESOURCE REGIONS: CHINA 从生成式 AI 到智能体，真正的变化是什么？ 过去两年，生成式 AI 在企业中的普及速度远超预期。但 IDC 指出，生成式 AI并不是终点。当 AI 只能生成内容时，它仍然是工具；而当 AI能够 感知环境、调用工具、执行任务并持续反馈结果，它才真正开始参与企业运行。 智能体正是在这一背景下出现。它不再局限于单点问答或流程辅助，而是以数字劳动力...

IDC China - 资源中心 - 新闻稿

具有市场洞察力的最新技术新闻 IDC的研究和数据产品提供全球、地区和本地的见解，为关键决策提供信息。 Showing Technology Trends Sep 9, 2026 Qijin Chen AI加速进入经营全链路，135亿元零售云市场迎来全新价值坐标—— IDC最新零售云报告发布 随着零售行业数字化进入深水区，云计算正在发生一次角色迁移：从承载业务系统的基础设施，逐步成为连接...

Asia Pacific Archives - Page 21 of 191 - IDC

RESOURCE REGIONS: ASIA PACIFIC 2025年中国腕戴设备市场出货量7,390万台，同比增长20.8%。国补政策与促销活动成为增长主引擎，这一趋势将延续至2026年。市场参与者如何应对政策驱动的新节奏？本文基于IDC最新数据，为您梳理市场变化与未来方向。 根据国际数据公司（IDC）最新发布的《中国可穿戴设备市场季度跟踪报告》，2025年中国腕戴设备市场出货量为7,3...

IDC China - 资源中心

资源中心 探索 IDC更多研究 IDC致力于通过及时的分析师洞察和庞大的数据帮助我们的客户做出明智的决策。 Image 发掘分析师的洞察力 \* ### 人工智能如何塑造未来的产业？ 独家了解人工智能如何改变零售、制造和政府部门的组织。 下载电子书 \* ### 人工智能在IT采购中的未来 阅读IDC最新的电子书，了解AI在IT采购和采购周期中当前和未来的使用，您的同行如何在其IT...

[kissflow.com kissflow.com](https://kissflow.com/low-code/gartner-forecasts-on-low-code-development-market/)  

Gartner Forecasts on the Future of Low-Code Development in 2026

According to Gartner's latest estimate, the global low-code development technologies industry will be worth $13.8 billion in 2023, up 22.6 ...

[ninox.com ninox.com](https://ninox.com/en/resources/blog/gartner-called-it-low-code-is-eating-software-development)  

Gartner called it: Low-code is eating software development

Gartner predicts 75% of new apps will be built with low-code by 2026. By 2024, 65% of all companies were already building with low-code. And ...

[facebook.com facebook.com](https://www.facebook.com/NATEKworkITwithUS/posts/gartner-predicts-70-of-new-applications-will-be-built-with-low-codeno-code-techn/1351434623693206/)  

Gartner predicts ~70% of new applications will be built with low ...

Market Growth: The global low-code market is expected to reach $187 billion by 2030, growing at a staggering rate of 31.1% CAGR!

My debut album 'The Wrong Side Of 25' is out at midnight. ...

10 Jul 2025 — The video shows a screen recording of her vocal test run in the Suno software, which she describes as a therapeutic experience.

Reliance Infosystems

At Heathrow airport, one security officer taught himself how to develop in Microsoft #PowerPlatform and created a suite of apps using #PowerBI, ...

[appbuilder.dev appbuilder.dev](https://www.appbuilder.dev/low-code-statistics/)  

Low-Code Statistics And Trends 2025 - App Builder

The global low-code application development platform market size was estimated at USD 24.83 billion in 2023 and is projected to grow at a compound annual growth ...

[blog.tooljet.com blog.tooljet.com](https://blog.tooljet.com/gartner-forecast-on-low-code-development-technologies/)  

Gartner Forecast on Enterprise Low-Code Development ...

Gartner's statistics show that the low-code market is expected to grow at a compound annual growth rate (CAGR) of 28.1% from 2023 to 2025. This ...

[grandviewresearch.com grandviewresearch.com](https://www.grandviewresearch.com/industry-analysis/low-code-application-development-platform-market)  

Low-Code Application Development Platform Market (2024 - 2030)

low-code application development platform market size was valued at $24.81 billion in 2023 and is projected to grow from $44.6 billion in 2026 to $101.686 ...

[quandarycg.com quandarycg.com](https://www.quandarycg.com/low-code-statistics)  

56+ Critical Low-Code Statistics to Review for 2024

The global market forecast for low-code is around 65 Billion U.S. by 2027. And it's expected to reach $187 Billion by 2030. That's a CAGR of ...

[searchlab.nl searchlab.nl](https://searchlab.nl/en/statistics/no-code-low-code-statistics-2026)  

No-Code & Low-Code Statistics 2026 | 50+ Data Points & Insights

The global no-code and low-code development platform market is valued at $65 billion in 2026, growing at a CAGR of 26.1%. Gartner projects it will reach $94 ...

[reuters.com reuters.com](https://www.reuters.com/technology/salesforce-challenger-creatio-raises-200-mln-becomes-unicorn-2024-06-26/)  

Salesforce challenger Creatio raises $200 mln, becomes 'unicorn'

Creatio, a low-code CRM software platform competing with Salesforce, has raised $200 million in a new funding round, achieving a valuation of $1.2 billion and earning "unicorn" status. The round was led by Sapphire Ventures, with participation from StepStone Group, Volition Capital, and Horizon Capital. Founded in 2014, Creatio has grown its revenue by 50% annually and now employs 700 people across seven offices globally, including in Poland and Ukraine. Its clients include major enterprises such as AMD, Coca-Cola, and MetLife. Although not yet profitable, the company plans to use the funding to expand product development, incorporating generative AI to enhance automation in marketing and sales tasks. Founder and CEO Katherine Kostereva emphasized that while they welcome investor support, strategic control remains with the founding team. Despite a general decline in investment for low-code and no-code platforms post-2021, Creatio has distinguished itself through a targeted focus on business process automation and a flexible backend architecture.

Apple loses top spot in China market with shipments down 6.6% in Q1, data shows

In the first quarter of 2024, Apple lost its position as the top smartphone vendor in China due to a 6.6% drop in shipments compared to the previous year, according to preliminary data from IDC. Honor and Huawei overtook Apple, each achieving around a 17% market share—Honor slightly ahead at 17.1%, with Huawei at 17%. Apple's market share fell to 15.6%, despite implementing price promotions, which IDC's Arthur Guo stated were insufficient against strong competition from Android brands. Meanwhile, China's overall smartphone shipments increased by 6.5% to 69.3 million units. Complementary data from Counterpoint Research also noted a sharper 19% decline in Apple's shipments, marking its weakest performance in China since 2020.

[en.wikipedia.org en.wikipedia.org](https://en.wikipedia.org/wiki/Microsoft_Power_Fx)  

Microsoft Power Fx

https://en.wikipedia.org/wiki/Microsoft\_Power\_Fx

Usage share of operating systems

https://en.wikipedia.org/wiki/Usage\_share\_of\_operating\_systems

Zapier

https://en.wikipedia.org/wiki/Zapier

OutSystems

https://en.wikipedia.org/wiki/OutSystems

Perspective (graphical) - Wikipedia

The most characteristic features of linear perspective are that objects appear smaller as their distance from the observer increases, and that they are ...

Control (video game) - Wikipedia

Control is a 2019 action-adventure game developed by Remedy Entertainment. It follows Jesse Faden, the new Director of the Federal Bureau of Control (FBC), ...

[wsj.com wsj.com](https://www.wsj.com/articles/marketing-budgets-as-a-share-of-revenue-fall-to-postpandemic-low-30d11fa1)  

Marketing Budgets as a Share of Revenue Fall to Postpandemic Low

In 2024, marketing budgets have declined to 7.7% of company revenue—down from an 11% pre-pandemic average and marking a post-pandemic low, according to a Gartner survey of nearly 400 marketing leaders. While 2021 had a lower budget share at 6.4%, it was heavily affected by the pandemic. Most surveyed companies have annual revenues over $1 billion, making even small percentage changes significant; for example, a drop from 11% to 8.2% represents a $14 million cut for a $500 million company. Despite the reduced budgets, 73% of marketers report increased pressure to deliver growth and profitability, while 64% say they lack sufficient budget for their strategies. Media budgets remain steady at around 2% of revenue, but costs in labor, agency work, and martech are being cut. Marketers are increasingly exploring AI to boost efficiency, although experts caution its immediate impact remains limited. Some industry leaders believe ad spending could rise later in the year as businesses attempt to recapture consumer attention despite economic pressures.

[expresscomputer.in expresscomputer.in](https://www.expresscomputer.in/news/gartner-says-ai-optimised-iaas-spending-to-reach-42-billion-in-2026/137564/)  

Gartner says AI-optimised IaaS spending to reach $42 billion in 2026

According to Gartner, global spending on AI-optimized infrastructure as a service (IaaS) is projected to reach $42.3 billion in 2026, marking a 96.4% increase from 2025. This growth is expected to continue, reaching $66.1 billion in 2027, driven primarily by the increasing demand for infrastructure that supports the training of large language models (LLMs) and the widespread deployment of AI across enterprise applications and workflows. A significant development in this trend is the shift in spending focus from training to inference. In 2026, AI inference is anticipated to surpass training in expenditure, with $23.3 billion expected to be spent on inference compared to $19 billion on training. Inference is forecasted to account for 55% of AI-optimized IaaS spending in 2026, increasing to 59% in 2027. This shift reflects the growing integration of fine-tuned and domain-specific models (DSMs) into real-time, customer-facing, and operational systems, necessitating continuous execution rather than periodic training.

[itpro.com itpro.com](https://www.itpro.com/business/business-strategy/ai-investment-increase-2026-gartner)  

Companies continue to splash out on AI, despite disillusionment with the technology

Despite widespread disillusionment with AI technology, global investment in AI is projected to surge, reaching $2.5 trillion in 2026—a 44% increase from 2025—and rising further to $3.3 trillion in 2027, according to Gartner. This growth comes even as many companies experience poor returns from AI projects, with a 2025 MIT study showing 95% of generative AI projects yielded zero ROI. Analysts note that AI is now typically integrated into existing software systems rather than launched as standalone initiatives. The bulk of 2026 investments will go into AI infrastructure ($1.3 billion), nearly half of the total increase, followed by AI services ($588.6 million) and software ($452.5 million). The boom in infrastructure spending already boosted semiconductor industry revenues by 21% in 2025, hitting $793 billion. Nvidia emerged as the revenue leader in AI semiconductors in 2025 with $125.7 million and a 15.8% market share, followed by Samsung and SK Hynix. Intel was the only top 10 vendor to see revenue decline. Analysts expect AI semiconductors to continue driving growth, potentially accounting for over one-third of semiconductor market sales as investment in AI infrastructure continues to soar.

Global IT spending set to exceed $6 trillion in 2026

Global IT spending is expected to exceed $6 trillion for the first time in 2026, reaching $6.08 trillion according to Gartner, marking a 9.8% increase from 2025. This major growth reflects a rebound from earlier market uncertainties, particularly seen in Q2 2025, with a resurgence in budgets anticipated by year-end. A major driver of this surge is data center systems, which grew by 46.8% in 2025 to $489 billion and are projected to reach $582 billion in 2026, a 19% gain. Software spending is also set to rise 15.2% to $143 billion. Mobile phone and AI device sales have further fueled this growth, with AI infrastructure demands significantly boosting data center server investments. This uptrend occurs despite the industry entering the "trough of disillusionment" in the Gartner Hype Cycle, where initial excitement around emerging technologies tends to taper off.

[link.springer.com link.springer.com](https://link.springer.com/article/10.1007/s10270-021-00964-0)  

Modelling in low-code development: a multi-vocal systematic review | Software and Systems Modeling | Springer Nature Link

Total lines: 755

A model and workflow-driven approach for engineering domain ...

OutSystems [40] is one of the most prominent low-code platforms. Application development takes place in Service Studio, its dedicated desktop ...

[ieeexplore.ieee.org ieeexplore.ieee.org](https://ieeexplore.ieee.org/document/10795358/)  

The Hidden Costs of Automation: An Empirical Study on GitHub Actions Workflow Maintenance | IEEE Conference Publication | IEEE Xplore

THE HIDDEN COSTS OF AUTOMATION: AN EMPIRICAL STUDY ON GITHUB ACTIONS WORKFLOW MAINTENANCE Publisher: IEEE Abstract Authors ABSTRACT: GitHub Actions (GA) is an orchestration platform that streaml...

Low-Code Versus Code-Based Software Development

by A Trigo · 2022 · Cited by 41 — Low-Code Versus Code-Based Software Development: Which Wins the Productivity Game? Abstract: Software is becoming increasingly larger and ...Read more

SegNet: A Deep Convolutional Encoder-Decoder Architecture for ...

We present a novel and practical deep fully convolutional neural network architecture for semantic pixel-wise segmentation termed SegNet.

Human3.6M: Large Scale Datasets and Predictive Methods for 3D ...

Abstract: We introduce a new dataset, Human3.6M, of 3.6 Million accurate 3D Human poses, acquired by recording the performance of 5 female ...

The discrete wavelet transform: wedding the a trous and Mallat ...

Abstract: Two separately motivated implementations of the wavelet transform are brought together. It is observed that these algorithms are ...

The JPEG still picture compression standard - IEEE Xplore

A joint ISO/CCITT committee known as JPEG (Joint Photographic Experts Group) has been working to establish the first international compression standard for

Quantum communication | IEEE Conference Publication - IEEE Xplore

Abstract: · Local Randomness for True Random Number generators · Non-local Randomness for distribution of Cryptographic Keys · Towards faster, ...

TSM: Temporal Shift Module for Efficient and Scalable Video ...

In this paper, we propose a generic and effective Temporal Shift Module (TSM) that enjoys both high efficiency and high performance.

MIMO Radar with Colocated Antennas | IEEE Journals & Magazine

Abstract: We have provided a review of some recent results on the emerging technology of MIMO radar with colocated antennas.

End-to-End Driving Via Conditional Imitation Learning - IEEE Xplore

We evaluate different architectures for conditional imitation learning in vision-based driving. We conduct experiments in realistic three-dimensional ...

LSD: A Fast Line Segment Detector with a False Detection Control

Abstract: We propose a linear-time line segment detector that gives accurate results, a controlled number of false detections, and requires ...

Unmanned Aerial Vehicles (UAVs): A Survey on Civil Applications ...

Abstract: The use of unmanned aerial vehicles (UAVs) is growing rapidly across many civil application domains, including real-time ...

Practitioners' Perceptions on the Adoption of Low Code ...

Practitioners' Perceptions on the Adoption of Low Code Development Platforms. Abstract: Organizations are under increasing pressure to ...

A Multiple Mini Case Study on the Adoption of Low Code ...

A Multiple Mini Case Study on the Adoption of Low Code Development Platforms in Work Systems ... Abstract: Although the adoption of Low Code ...

[computer.org computer.org](https://www.computer.org/publications/tech-news/research/low-code-vs-code)  

Low-Code vs. Code-Based Development | IEEE Computer Society

The Productivity Debate: Low-Code vs. Code-Based Software Development ... Use case points analysis (UCPA) was used to measure productivity ...

Low-Code Versus Code-Based Software Development

Low-Code Versus Code-Based Software Development: Which Wins the Productivity Game? Sept.-Oct. 2022, pp. 61-68, vol. 24. DOI Bookmark: 10.1109/MITP ...Read more

Quality of Low-Code/No-Code Development Platforms Through the ...

Wang, M. Shahin, and J. Zhan, “Characteristics and challenges of low-code development: The practitioners' perspective,” in Proc. 15th ACM/IEEE ...

[iscsitr.org iscsitr.org](https://iscsitr.org/index.php/ISCSITR-IJIT/article/view/ISCSITR-IJIT_2025_01_01_003)  

Empirical Study on the Impact of Low Code and No Code Development Platforms on Software Engineering Productivity and Long-Term Maintainability | ISCSITR- INTERNATIONAL JOURNAL OF INFORMATION TECHNOLOGY (ISCSITR-IJIT)

EMPIRICAL STUDY ON THE IMPACT OF LOW CODE AND NO CODE DEVELOPMENT PLATFORMS ON SOFTWARE ENGINEERING PRODUCTIVITY AND LONG-TERM MAINTAINABILITY AUTHORS \* Henry Amonoo Full-stack developer, USA Autho...

[github.com github.com](https://github.com/tillguthardt/Low-code-vs.-the-developer)  

GitHub - tillguthardt/Low-code-vs.-the-developer: This repository contains all raw data, scripts, and documents collected and used in the study "Low-code vs. the Developer: An Empirical Study on the Developer Experience and Efficiency of a No-Code Platform." · GitHub

tillguthardt / Low-code-vs.-the-developer Public \* Notifications You must be signed in to change notification settings \* Fork 0 \* Star \* Code \* Issues 0 \* Pull requests 0 \* Actions \* Projects \* Sec...

[doi.org doi.org](https://doi.org/10.1145/3786791)  

Understanding Self-Admitted Technical Debt in Test Code: An Empirical Study | ACM Transactions on Software Engineering and Methodology

research-article Open access UNDERSTANDING SELF-ADMITTED TECHNICAL DEBT IN TEST CODE: AN EMPIRICAL STUDY Authors: Ibuki Nakamura Image Ibuki Nakamura Nara Institute of Science and Technology Ik...

als ein Trend?: Wie Low-Code die digitale Transformation ...

by E Elshan · 2024 · Cited by 9 — ... Low-code versus code-based software development: which wins the productivity game? IT Prof 24(5):61–68. https://doi.org/10.1109/MITP ...Read more

[researchgate.net researchgate.net](https://www.researchgate.net/publication/376017565_Low-code_Development_Productivity_Is_winter_coming_for_code-based_technologies)  

(PDF) Low-code Development Productivity: "Is winter coming" for ...

The author used OutSystems as the Low Code Platform (LCP) and MongoDB, ExpressJS, ReactJS, NodeJS (MERN) in the Full Code approach. The results showed that ...

low code integration testing in outsystems personal environment

This paper presents a comprehensive study ... In this work, we study the test automation process on the OutSystems low-code development platform.

(PDF) Low-Code Versus Code-Based Software Development

1 Dec 2022 — Low-Code Versus Code-Based Software Development: Which Wins the Productivity Game? September 2022; IT Professional 24(5):61-68. DOI:10.1109 ...Read more

(PDF) Challenges & opportunities in low-code testing - ResearchGate

Challenges & Opportunities in Low-Code Testing. ACM/IEEE 23rd International Conference on Model Driven Engineering Languages and Systems. ( ...

(PDF) Practitioners' Perceptions on the Adoption of Low Code ...

Practitioners' Perceptions on the Adoption of Low Code Development Platforms. March 2023; IEEE Access 11:29009-29034. DOI:10.1109/ACCESS ...

(PDF) A Multiple Mini Case Study on the Adoption of Low Code ...

... A Multiple Mini Case Study on the Adoption of Low Code Development Platforms in Work Systems. January 2023; IEEE Access 11:118762-118786. DOI ...

(PDF) Characteristics and Challenges of Low-Code Development

Characteristics and Challenges of Low-Code Development: The Practitioners' Perspective. July 2021. Yajing Luo ...

(PDF) Designing Scalable Data Pipelines with Low-Code Platforms

exponentially, traditional manual coding (ETL) faces bottlenecks in speed and specialist availability. This study evaluates whether low-code solutions can maintain performance parity with traditiona...

(PDF) Scalable Microservices Integration Through Low-Code API Development Architectures

organizations to accelerate development timelines, democratize application creation, and maintain architectural consistency through model-driven approaches. The intersection of low-code development...

[outsystems.com outsystems.com](https://www.outsystems.com/low-code)  

What is Low-Code Development? A Guide for IT Leaders - OutSystems

Low-code is a software development approach that enables developers to create applications with minimal hand coding. It's designed for both ...

Dah Chong Hong Transforms Customer Experiences

The low-code platform enables us to customize our own process and connect systems across cloud platforms."

Altrad Sparrows Improves Employees' Efficiency and ...

Sparrows is using low-code to build custom solutions, including a critical risk management portal, and enhance its efficiency.

PLANgroep Modernizes SharePoint Legacy Solution

Low-code for Future-proof Development. These requirements led PLANgroep to use a low-code approach led by OutSystems delivery partner IG&H. The new core system ...

ISB Global Extends SAP with Mobile Application

ISB Global creates SAP mobile application allowing remote users to access real-time SAP information on any device, in just 2 months.

Nimbi Truly Masters DevOps With OutSystems

They chose OutSystems for a few key reasons: Game-changing speed and velocity of the low-code platform; Simplified development and application maintenance ...Read more

Georgia Tech IEN Develops Lab Management App

IEN tracks lab inventory and equipment, how users check availability and make reservations, as well as how departments are billed. Launch Your Low-Code Digital ...

Koopman Logistics Invest in Process Automation

OutSystems low-code platform enables Koopman to model applications visually and generate code, allowing IT to quickly develop applications that enhance ...Read more

Petrobras Embraces Development at Scale with Low-Code

Petrobras implemented a low-code Center of Excellence that supports 100+ agile teams and sped up app development by up to 90%. Read the full story.

Hospital Management System Deploys in Weeks

With a low-code platform, Advanced Technology Company developed a hospital management system that's easy to use and deploys in weeks (not years).

Custom-built CRM Using OutSystems

See how OutSystems is different. Schedule demoContact Sales. Low-code Platform. Platform OverviewPricingEvaluation GuideLow-Code BasicsApplication Templates ...Read more

From Development to Deployment with Low-Code | OutSystems

FROM DEV TO DEPLOY IN NO TIME Always say yes to requests for apps without worrying about lead times. With one-click deployment, built-in governance, application lifecycle management, and DevOps, the...

The Agentic Systems Platform for Enterprise AI | OutSystems

THE OPEN AGENTIC SYSTEMS PLATFORM BUILT FOR THE ENTERPRISE Move beyond fragmented AI tools, unpredictable costs, and growing security risks. With the OutSystems Agentic Systems Platform, your teams c...

Scale Agentic AI Systems with Agent Workbench | OutSystems

OUTSYSTEMS AGENT WORKBENCH ONE PLATFORM TO FAST TRACK AGENTIC AI INNOVATION Create custom AI agents that streamline operations, elevate experiences, and grow revenue, all on the AI development platf...

[arxiv.org arxiv.org](https://arxiv.org/pdf/2402.01156)  

[PDF] An Empirical Study on Low-Code Programming using Traditional vs ...

Traditional LCP tools, such as Power Apps [8] and. OutSystems [20], typically include a visual development inter- face for drag-and-drop development. They are ...

Improving the Developer Experience with a Low-Code Process Modelling Language

https://arxiv.org/abs/2508.06299

CHAMELEON: OutSystems Live Bidirectional Transformations

https://arxiv.org/abs/2305.03361

Towards a Polyglot Data Access Layer for a Low-Code Application Development Platform

https://arxiv.org/abs/2004.13495

Natural language to SQL in low-code platforms

https://arxiv.org/abs/2308.15239

Characteristics and Challenges of Low-Code Development: The Practitioners' Perspective

Characteristics and Challenges of Low-Code Development: The Practitioners' Perspective. Authors:Yajing Luo, Peng Liang, Chong Wang, Mojtaba ...

Characteristics and Challenges of Low-Code Development - arXiv

Characteristics and Challenges of Low-Code Development: The Practitioners' Perspective. Conference: ACM / IEEE International Symposium on ...

[queue.acm.org queue.acm.org](https://queue.acm.org/doi/full/10.1145/3631183)  

Low-code Development Productivity - ACM Queue

The underlying research question was: Do low-code technologies result in higher software-development productivity than code-based technologies ( ...

Low-code Development Productivity

27 Nov 2023 — Low-code versus code-based software development: Which wins the productivity game? IEEE IT Professional 24(5), 61–68; https://www.computer ...Read more

[ijsred.com ijsred.com](https://ijsred.com/volume8/issue5/IJSRED-V8I5P282.pdf)  

Comparative Study of Application Development - Low Code/No ...

[3] OutSystems, “The State of Application Development. Report: Low-Code 2021,” OutSystems Industry Report,. 2021. [4] P. Mohagheghi, S. Sæther, and T. Sta ...

[semanticscholar.org semanticscholar.org](https://www.semanticscholar.org/paper/Low-Code-Versus-Code-Based-Software-Development%3A-Trigo-Varaj%C3%A3o/0e04d7ba43d68098800636ce40cfb5d986419183)  

[PDF] Low-Code Versus Code-Based Software Development

The results show that the development and maintenance of software with low-code technology is significantly faster, thus supporting the high potential of ...

Practitioners' Perceptions on the Adoption of Low Code ...

Practitioners' Perceptions on the Adoption of Low Code Development Platforms · 36 Citations · 69 References.

challenges of low-code/no-code platforms in supporting ...

A Multiple Mini Case Study on the Adoption of Low Code Development Platforms in Work Systems · Computer Science. IEEE Access · 2023.

[PDF] Characteristics and Challenges of Low-Code Development

Characteristics and Challenges of Low-Code Development: The Practitioners' Perspective · Yajing Luo, Peng Liang, +2 authors. Jing Zhan · Published in ...

Challenges & opportunities in low-code testing - Semantic Scholar

Challenges & opportunities in low-code testing · F. Khorram, Jean-Marie Mottu, Gerson Sunyé; Published in · Published in ACM/IEEE International… 16 October ...

[academia.edu academia.edu](https://www.academia.edu/106193373/Low_Code_Versus_Code_Based_Software_Development_Which_Wins_the_Productivity_Game)  

(PDF) Low-Code Versus Code-Based Software Development ...

Low-code technology demonstrated productivity at least three times higher than code-based development in the experiment. ... OutSystems platform, use cases, ...

(PDF) The Rise of Low Code/No Code Software Development Models

Characteristics and challenges of low-code development: the practitioners' perspective. In Proceedings of the 15th ACM/IEEE international symposium on ...

[devoteam.com devoteam.com](https://www.devoteam.com/expert-view/outsystems-impact-on-developers/)  

Will OutSystems Make Developers Obsolete?

Learn how OutSystems impacts developers, transforming traditional coding roles into high-value, low-code application development for faster delivery.

[news.ycombinator.com news.ycombinator.com](https://news.ycombinator.com/item?id=46767440)  

RIP Low-Code 2014-2025 - Hacker News

So yeah, for folks doing generic low-code productivity apps, it's not great. ... I will say Low code is something like Outsystems. CountVonGuetzli 7 months ...

[youtube.com youtube.com](https://www.youtube.com/watch?v=tsGQ86xKc3o)  

Low-Code vs Traditional Development: Is OutSystems Worth It?

Low-Code is no longer just for prototypes. In 2026, platforms like OutSystems are running core enterprise systems. But as a developer, ...

Perspective projection in 5 minutes - YouTube

Equivalent to a 50 minute university lecture on perspective projection. Part 1 of 2. 0:00 - intro 0:28 - pin-hole camera 0:43 - room-sized ...

Perspective for Beginners - YouTube

This lesson is a beginner's guide to one-point perspective drawing. It breaks down the basics like the XYZ axes, horizon line, and vanishing ...

12 - Basic Responsive Web Development | Design & Code Series

In today's episode, we continue on with our project by Using some responsive web development techniques to make our site look great on all ...

The Truth About Perspective - YouTube

Marshall joins me for a conversation about how perspective relates to how we actually see the world. Perspective is a mix of invention and ...

Lightning Message Service & Code Builder - YouTube

Getting started with Lightning Web Components LWC · Lightning Web Components Best practices · Keynote: After the AI Hype – What's Real, and What's ...

Perspective for Drawing Anything - Marshall Vandruff's Course

Start learning perspective today! - https://proko.com/perspective In this course, you'll learn how to transform a flat surface into a deep, ...

8 - Design & Code a Responsive Landing Page from Start to Finish

9 - Design & Code a Responsive Landing Page from Start to Finish | Coding the Offer Section. Jesse Showalter · 7.4K views ; JavaScript Tutorial ...

Better Perspective Correction In Lightroom - YouTube

In this video, I'll show you a quick trick to fix perspective distortion in Lightroom that the default upright tool can't handle.

perspective hacks - YouTube

This video is all about perspective hacks. The first several minutes are some quick examples of traditional perspective, loosely drawn in, ...

How to Draw 3D Heads with Perspective - YouTube

This is a great exercise to improve your perspective skills, especially with organic forms like human heads. You're going to figure out the ...

How to Pronounce Perspective and Prospective - YouTube

You can do it! SpeechModification.com. How to Pronounce Perspective and Prospective. @SpeechModification116 likes4.4K views3 years ago more.

How to Fix Perspective in Affinity Photo - YouTube

Perspective in Affinity Photo Explained (Source vs Destination Finally Makes Sense). Learn Canva with Greg · 6.5K views ; Affinity Photo - ...

Conversations with Memory (explanation & code walkthrough)

Colab: [https://rli.to/UNseN](https://rli.to/UNseN) Creating Chat Agents that can manage their memory is a big advantage of LangChain.

Source to Sea down the River Thames WITHOUT Leaving it

27 Mar 2025 — Source to Sea down the River Thames WITHOUT Leaving it - Part 6 @EdPratt44K likes1.4M views1 year ago

25 Easy Family Dinners And More | Jamie Oliver

23 Jul 2025 — 25 Easy Family Dinners to cook at home! Jamie Oliver shows you how to cook 0:00 - British bolognese 4:01 - Farm house roast chicken 7:57 ...

deftones - infinite source [video]

21 Aug 2025 — ftones website: https://deftones.com … deftones - infinite source [video] @deftones91K likes4.4M views1 year ago

Top 25 Places To Visit in Scotland - Travel Guide

14 Sept 2025 — Scotland is one of the most magical places on earth! Enjoy this travel guide featuring some of my favorite places in Scotland.

NIKI DEMAR - 25 (Official Video)

10 Jun 2021 — 25 out now: https://unitedmasters.com/m/NIKIDEMAR25 25 is the most honest track I've put out so far. I'm so grateful to my team of ...

Top 25 Places To Visit in Slovenia - Travel Guide

18 May 2025 — Slovenia is one of Europe's hidden gems. Enjoy this travel guide featuring some of my favorite places in Slovenia.

Testing 100 Viral Food Hacks

30 Jul 2022 — Testing 100 Viral Food Hacks · Comments.Read more

Testing SCARY Mario Myths that are Unsolved…

6 Dec 2025 — Testing the SCARIEST Mario Myths ever found... · Testing Mario's Most SCARY Myths… · Trapped In Every Color For 24 Hours! · When LUIGI Goes GODMODE ...Read more

Testing SCARY Mario Myths that are actually TRUE…

26 Apr 2025 — Testing SCARY Mario Myths that are Unsolved… Manx Ninja Pig•18M ... Testing the SCARIEST Mario Myths ever found... Manx Ninja Pig. New.Read more

Testing If You Can Blow Your Own Sail

2 Mar 2024 — Testing If You Can Blow Your Own Sail. @MarkRober1.2M likes64M views2 ... Testing What Happens If You Jump On A Moving Train. Mark Rober ...Read more

Testing FREE VBUCKS Maps Until They Work!

26 Apr 2026 — Testing EVERY FREE VBUCKS Myth Until One WORKS! Item Shop Code: MMCS #UseCodeMMCS #fortnite Hit LIKE and ✓ Subscribe - Thank you!

Testing the Most Popular Home 3D Prints

22 May 2026 — Testing The Worlds Most Popular Home 3D Prints. Williams Workshop (Corey J. Williams) · 73K views ; 3D Prints You Will ACTUALLY Want To Make! - ...Read more

Testing What Happens If You Jump On A Moving Train

12 Apr 2025 — Testing What Happens If You Jump On A Moving Train. @MarkRober412K ... Testing If You Can Blow Your Own Sail. Mark Rober•64M views · 22:55.Read more

Software Testing Book Recommendations

29 Sept 2024 — In this video, I am talking about software testing and non software testing related books. In total, I am sharing 17 books I highly ...

LIVE: London Heathrow Airport - YouTube

HEATHROW AIRPORT LIVE From Heathrow's perimeter to airports around the world, Big Jet TV has built a reputation as the No1 destination for ...

10 Best Lower Back Stretches for Low Back Pain Relief - Ask Doctor Jo

These back stretches are for general lower back pain. If you have a specific injury or diagnosis, some of these might not be appropriate, ...

Time for a refurb? Thistle hotel, London Heathrow T5 - YouTube

As part of my 'think maintenance' series I've decided to have a look at the Thistle hotel at Terminal 5 of London Heathrow airport.

"Customer Obsession" Leadership Principle Explained by Amazon ...

CEO Andy Jassy explains how to apply the Leadership Principle “Customer Obsession” at Amazon.

How to Turn Low Poly Models into AAA Game Assets - Blender 5

In this tutorial, we're transforming a basic, flat-shaded stone pillar into a highly detailed, production-ready game asset using Blender's ...

Low - Disappearing (Official Video) - YouTube

"Disappearing" from Low's album HEY WHAT (Out September 10, 2021) Director/Producer/Editor: Dorian Wood. Low - Disappearing (Official Video) ...

How to Play Lazy Low Effort Golf and Beat Everyone - YouTube

How to Play Lazy Low Effort Golf and Beat. The Cheat Code Old Golfers Use (Young Players Refuse to Try)

LIVE: London Heathrow Airport - YouTube

HEATHROW AIRPORT LIVE From Heathrow's perimeter to airports around the world, Big Jet TV has built a reputation as the No1 destination for ...

‍♂️Client? or Customer? - a simple explanation - YouTube

Client? or Customer? These two words can easily be confused. Client = /ˈklaɪ.ənt/ Customer = /ˈkʌs.tə.mɚ/ A client pays for a service.

Foo Fighters - Low (Official HD Video) - YouTube

"Low" by Foo Fighters. Foo Fighters - Low (Official HD Video) 47K likes9.8M views16 years ago

Low - Days Like These (Official Video) - YouTube

"Days Like These" from Low's album HEY WHAT (Release Date: September 10, 2021) Low - Days Like These (Official Video) Low - Full Performance ( ...

LIVE: Storm Eunice at London Heathrow Airport - YouTube

#Heathrow #StormEunice #Storm Join us live from London Heathrow Airport as Storm Eunice hits the UK. Chat will be opened up to all ...

DEAR HEATHROW AIRPORT... #Heathrow #Shootfromthehip ...

#Heathrow #Shootfromthehip #Airport #Funnyreels #Comedy #Improv #Game · COMPLAINT to HEATHROW AIRPORT | The LETTERS Game (they can only ...

Chet Faker - Low (Official Music Video) - YouTube

"Low" by Chet Faker from the album Hotel Surrender – OUT NOW. Animation by Amanda Bonaiuto. Stream "LOW" here: - Low (Official Music Video) 3.9 ...

D-low - Poison Dagger (GBB26 Wildcard 1ST PLACE) - YouTube

D-low | Winner's Compilation | SBX KICKBACK BATTLE 2021. Swissbeatbox · 3.4M views ; KING INERTIA and TRC Brand new wildcards! · New. 33K views.

BRING THE NOISE! LIVE: London Heathrow Airport Arr into deps

HEATHROW AIRPORT LIVE From Heathrow's perimeter to airports around the world, Big Jet TV has built a reputation as the No1 destination for ...

Satya Nadella w London Heathrow Airport

Microsoft CEO Satya Nadella highlights how Heathrow airport's Samit Saini and Komal Tekchandani are utilizing Microsoft's Power Platform ...

Enterprise Sales | Startup School - YouTube

In this video, Pete breaks down the enterprise sales funnel and shares his top tips on how a technical founder can start closing real deals for ...

Building Megaobjects in Minecraft - YouTube

This is the beginning framework of the Enterprise - D in Minecraft. Minecraft Enterprise-D update!

How the USS Enterprise Was Battle Damaged in Star Trek! - YouTube

This time, we check out the massive close-up model of the USS Enterprise with incredibly detailed hull damage it sustained in Star Trek II ...

Adam Savage Unboxes Star Trek's USS Enterprise Refit Model!

Adam and Norm unbox and scrutinize Tomy's 1:350 USS Enterprise Refit model! From its heavy diecast parts to the clever illumination design,

Halsey - Control (Audio) - YouTube

Official Audio Video for “Control” by Halsey from the album : Heathens (from Suicide Squad: The Album) [OFFICIAL VIDEO]

Control - Official Gameplay Trailer - YouTube

Control is the next game from Remedy, releasing August 27 on PS4, Xbox One, and PC. CONTROL Walkthrough Gameplay Part 1 - INTRO (FULL GAME)

Control Review - YouTube

Jonathon Dornbush reviews Remedy Entertainment's Control ahead of its August 27 release on PC, PS4, and Xbox One.

Janet Jackson - Control - YouTube

Music video by Janet Jackson performing Control. (C) 1986 A&M Records Janet Jackson - Control @JanetJacksonVEVO139K 16M views17 years ago

Are we in control of our decisions? | Dan Ariely - YouTube

http://www.ted.com Behavioral economist Dan Ariely, the author of Predictably Irrational, uses classic visual illusions and his own ...

[mdpi.com mdpi.com](https://www.mdpi.com/2076-3417/12/19/9556)  

Combining Rigorous Requirements Specifications with Low-Code ...

Low-code platforms such as Quidgest Genio [8], OutSystems [9], or Mendix [10] can be particularly beneficial at the prototyping stages of the development ...

Evaluating Low-Code Development Platforms: A MULTIMOORA ...

... A multiple mini case study on the adoption of low code development platforms in work systems. IEEE Access 2023, 11, 118762–118786. [Google ...

Democratizing Digital Transformation: A Multisector Study of Low-Code Adoption Patterns, Limitations, and Emerging Paradigms

DEMOCRATIZING DIGITAL TRANSFORMATION: A MULTISECTOR STUDY OF LOW-CODE ADOPTION PATTERNS, LIMITATIONS, AND EMERGING PARADIGMS by Zhengwu Shi ImageZhengwu Shi SciProfiles Scilit Preprints.org Googl...

[dl.acm.org dl.acm.org](https://dl.acm.org/doi/pdf/10.1145/3783862.3783880)  

Software Rapid Application Development (RAD) for Web Application ...

Unlike existing low-code platforms such as OutSystems and. Mendix, which often restrict customization and lock users into proprietary ecosystems ...

Characteristics and Challenges of Low-Code Development

Characteristics and Challenges of Low-Code Development: The Practitioners' Perspective. Authors: Yajing Luo. Yajing Luo. School of Computer ...

Challenges & opportunities in low-code testing - ACM Digital Library

Challenges & opportunities in low-code testing. research-article. Free access. Share on. Challenges & opportunities in low-code testing. Authors: Faezeh Khorram.

An Investigation of Low-Code Development Adoption in a Finnish IT ...

Käss S, Strahringer S, and Westner M Practitioners' perceptions on the adoption of low code development platforms IEEE Access 2023 11 29009- ...

[ceur-ws.org ceur-ws.org](https://ceur-ws.org/Vol-3113/paper12.pdf)  

[PDF] A Use Case-based Investigation of Low-Code Development Platforms

We aim to investigate the promises of easy, rapid application development and deployment by evaluating to which extent this is possible with a ...

[reddit.com reddit.com](https://www.reddit.com/r/ExperiencedDevs/comments/18bs1n9/what_technology_or_approach_seems_easy_to_start/)  

What technology or approach seems easy to start with, but becomes ...

We're currently dealing with an Outsystems installation that's basically blocking us from going live. ... Also, large code-bases with low test ...

Reddit - The heart of the internet

Reddit is where millions of people gather for conversations about the things they care about, in over 100000 subreddit communities.

Control - (The Good, The Bad, The Ugly) : r/patientgamers - Reddit

Control is an action-adventure game developed by Remedy Entertainment. Control answers the question of what happens when a game doesn't answer ...

[pt.wikipedia.org pt.wikipedia.org](https://pt.wikipedia.org/wiki/OutSystems)  

OutSystems

https://pt.wikipedia.org/wiki/OutSystems

[fr.wikipedia.org fr.wikipedia.org](https://fr.wikipedia.org/wiki/OutSystems)  

OutSystems

https://fr.wikipedia.org/wiki/OutSystems

[ciencia.iscte-iul.pt ciencia.iscte-iul.pt](https://ciencia.iscte-iul.pt/publications/low-code-versus-code-based-software-development-which-wins-the-productivity-game/105359?lang=en)  

Low-Code Versus Code-Based Software Development: Which Wins ...

Low-Code Versus Code-Based Software Development: Which Wins the Productivity Game? António Trigo (Trigo, A.); Varajão, João (Varajão, João); Miguel Almeida ...

[portaberta.uminho.pt portaberta.uminho.pt](https://portaberta.uminho.pt/display/cv-t-793216001dcb3e6a9caa0b2db8c82c4e)  

Low-Code Versus Code-Based Software Development

Low-Code Versus Code-Based Software Development: Which Wins the Productivity Game? Artigo Académico uri icon.

[sciencedirect.com sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S0164121226001263)  

What does current research say about the viability of low- ...

by D Gao · 2026 — Low-code versus code-based software development: Which wins the productivity game? IT Prof., 24 (5) (2022), pp. 61-68. Google Scholar. Volioti et al., 2024. C ...Read more

A large-scale empirical study on the lifecycle of code smell co-occurrences - ScienceDirect

INFORMATION AND SOFTWARE TECHNOLOGY Volume 99, July 2018, Pages 1-10 A LARGE-SCALE EMPIRICAL STUDY ON THE LIFECYCLE OF CODE SMELL CO-OCCURRENCES https://doi.org/10.1016/j.infsof.2018.02.004Get rig...

[efpia.eu efpia.eu](https://www.efpia.eu/relationships-code/)  

Relationships & code - EFPIA

Collaboration with partners in healthcare is critical to advancing patient care. These relationships are built on transparency and a strong regulatory ...

[instagram.com instagram.com](https://www.instagram.com/reel/DdEuqbkCjmT/)  

I visited the trichology team at Philip Kingsley to get to the root cause ...

So many of you still ask me how I grew my relatively healthy hair back, and here is the answer: I visited the trichology team at Philip Kingsley ...

Kim Kardashian (@kimkardashian)

My name is Lonnie Hawkins. This is an Instagram post. Please comment if I posted it. Thank you Kim for helping me post. Is this going through?

Low Carb Love - Instagram

Lost 100 lbs • Kept it off 15+ years Low-carb recipes for real weight loss Simple, realistic & family-friendly Recipes,Ebooks & Guides.

[community.intersystems.com community.intersystems.com](https://community.intersystems.com/post/video-iris-ai-studio-detailed-functionality-code-walkthrough)  

[Video] IRIS AI Studio: A detailed Functionality & Code Walkthrough

This is a detailed, candid walkthrough of the IRIS AI Studio platform. I speak out loud on my thoughts while trying different examples, some of ...

[uk.linkedin.com uk.linkedin.com](https://uk.linkedin.com/in/drew-spencer)  

Drew Spencer - Software Technical Lead & Code Club Champion

Code Club Champion at the Cambridge @ Makespace. My key strengths are my drive, attention to detail, and ability to take initiative and communicate ideas well.

Jenny McLaughlin (she/her) - Senior Project Manager - LinkedIn

I have been lucky enough to have a varied career at Heathrow, and that is one of the beauties of working here. I started in 2007 in the Environment team, ...

[linkedin.com linkedin.com](https://www.linkedin.com/posts/meetsteveharris_%F0%9D%97%A6%F0%9D%98%82%F0%9D%97%BB%F0%9D%97%B1%F0%9D%97%AE%F0%9D%98%86-%F0%9D%97%96%F0%9D%97%BC%F0%9D%97%B3%F0%9D%97%B3%F0%9D%97%B2%F0%9D%97%B2-%F0%9D%97%96%F0%9D%97%BC%F0%9D%97%B1%F0%9D%97%B2-%F0%9D%97%A7%F0%9D%97%B2%F0%9D%97%AE%F0%9D%97%B0%F0%9D%97%B5%F0%9D%97%B6%F0%9D%97%BB%F0%9D%97%B4-activity-7499918362731474944-e_9z)  

Steve Harris' Post - LinkedIn

Sunday Coffee & Code: Teaching my phone to text back (LM Playground OpenAI ...

Microsoft Power Platform (Power BI, PowerApps, Flow)

Microsoft CEO Satya Nadella highlights how Heathrow airport's. Microsoft's Power Platform (PowerApps, Power BI & Flow) to save 11,000 sheets of ...

[chiefdelphi.com chiefdelphi.com](https://www.chiefdelphi.com/t/1778-2026-cad-code-release/521825)  

1778 2026 CAD & Code Release - Robot Showcase - Chief Delphi

Team 1778 Chill Out is excited to release the CAD and Code for our 2026 robot: HAILSTORM 2026 CAD 2026 Code.

[hal.science hal.science](https://hal.science/hal-02946812)  

Challenges & Opportunities in Low-Code Testing

Challenges & Opportunities in Low-Code Testing. Faezeh Khorram (1, 2 ... Challenges & Opportunities in Low-Code Testing. ACM/IEEE 23rd ...

[opus4.kobv.de opus4.kobv.de](https://opus4.kobv.de/opus4-oth-regensburg/frontdoor/deliver/index/docId/5917/file/Kaess_Strahringer_Westner_Practitioners.pdf)  

[PDF] Perceptions on the Adoption of Low Code Development Platforms

Käss et al.: Practitioners' Perceptions on the Adoption of Low Code Development Platforms adoption research also apply to the specific situation of LCDP.

A Multiple Mini Case Study on the Adoption of Low Code ... - OPUS 4

... A Multiple Mini Case Study on the Adoption of Low Code Development Platforms in Work Systems. Sebastian Käss, Susanne Strahringer, Markus Westner. Although ...

[scribd.com scribd.com](https://www.scribd.com/document/819360919/Challenges-opportunities-in-low-code-testing)  

Low-Code Testing: Challenges & Opportunities | PDF | Software ...

Challenges & opportunities in low-code testing - Free download as PDF File (.pdf), Text File (.txt) or read online for free.

Practitioners Perceptions On The Adoption of Low Code ... - Scribd

Practitioners Perceptions On The Adoption of Low Code Development Platforms. The document discusses the adoption of Low Code Development Platforms (LCDPs) by ...

Challenges of Low Code | PDF - Scribd

... Challenges & opportunities in low-code testing. In: Proceedings – 23rd ACM/IEEE International Conference on Model Driven Engineering Lan- guages and Systems ...

[faezeh-kh.github.io faezeh-kh.github.io](https://faezeh-kh.github.io/uploads/lowcode_presentation.pdf)  

[PDF] Challenges & Opportunities in Low-Code Testing - Faezeh Khorram

Challenges & Opportunities in Low-Code Testing. Faezeh Khorram, Jean-Marie Mottu, Gerson Sunyé. LS2N, Université de Nantes, IMT Atlantique, Nantes, France. ACM ...

[ekonbiz.ues.rs.ba ekonbiz.ues.rs.ba](https://www.ekonbiz.ues.rs.ba/ojs/article/view/330.html)  

LOW CODE/NO CODE DEVELOPMENT DRIVERS ASSESSED BY ...

Practitioners' Perceptions on the Adoption of Low Code Development Platforms. IEEE Access, 11, 29009–29034. https://doi.org/10.1109/ACCESS.2023.3258539. Luo ...

[pmc.ncbi.nlm.nih.gov pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC9643911/)  

Developer discussion topics on the adoption and barriers of low ...

... Challenges & opportunities in low-code testing. In: Proceedings of the 23rd ACM/IEEE international conference on model driven engineering languages and ...

[ouci.dntb.gov.ua ouci.dntb.gov.ua](https://ouci.dntb.gov.ua/en/works/7XavqEyr/)  

Low-Code Platforms Adoption: A Motivational Adoption Process ...

... Practitioners' perceptions on the adoption of low code development platforms. IEEE Access 11, 29009–29034 (2023) DOI: 10.1109/ACCESS.2023.3258539; Keller ...

Low Code/No Code software Development: Definition, drivers, and ...

... A Multiple Mini Case Study on the Adoption of Low Code Development Platforms in Work Systems. IEEE Access, 11, 118762-118786. Doi: https://doi.org/10.1109 ...

Challenges of Low-Code/No-Code Software Development - OUCI

... Challenges & opportunities in low-code testing. In: Proceedings – 23rd ACM/IEEE International Conference on Model Driven Engineering Languages and Systems ...

[diva-portal.org diva-portal.org](https://www.diva-portal.org/smash/get/diva2%3A1736580/FULLTEXT01.pdf)  

[PDF] Low-code platforms as an enabler for value creation - DiVA portal

Challenges & opportunities in low-code testing. In Proceedings of the 23rd ACM/IEEE International Conference on Model Driven Engineering.

[zendy.io zendy.io](https://zendy.io/pdf-viewer/PROCART-472100056)  

Characteristics and Challenges of Low-Code Development: The ...

Characteristics and Challenges of Low-Code Development: The Practitioners' Perspective ... The content you want is available to Zendy users.Already have an ...

[exaly.com exaly.com](https://exaly.com/article/161563529)  

Practitioners' Perceptions on the Adoption of Low Code ... - exaly.com

Scientometric profile and citation metrics for Practitioners' Perceptions on the Adoption of Low Code Development Platforms.

[ae.ef.unibl.org ae.ef.unibl.org](https://ae.ef.unibl.org/index.php/ae/article/view/582)  

A LITERATURE REVIEW AND CASE STUDY EVIDENCE

... A Multiple Mini Case Study on the Adoption of Low Code Development Platforms in Work Systems. IEEE Access, 11, 118762–118786. https://doi ...

[scholar.google.com scholar.google.com](https://scholar.google.com/citations?hl=en&user=MyCkzOUAAAAJ)  

‪Markus Westner‬ - ‪Google Scholar‬

... A Multiple Mini Case Study on the Adoption of Low Code Development Platforms in Work Systems. S Käss, S Strahringer, M Westner. IEEE Access 11, 118762-118786 ...

[docs.mendix.com docs.mendix.com](https://docs.mendix.com/developerportal/deploy/)  

Deployment | Mendix Documentation

https://docs.mendix.com/developerportal/deploy/

Using Version Control in Studio Pro | Mendix Documentation

Total lines: 4240

Alerts | Mendix Documentation

ALERTS Last modified: August 4, 2026 INTRODUCTION When your application has reached production status, it is important to keep track of its status and health. When you click Alerts in the Mendix P...

[learn.microsoft.com learn.microsoft.com](https://learn.microsoft.com/en-us/power-platform/alm/overview-alm)  

Application lifecycle management (ALM) with Microsoft Power Platform - Power Platform | Microsoft Learn

https://learn.microsoft.com/en-us/power-platform/alm/overview-alm

[success.outsystems.com success.outsystems.com](https://success.outsystems.com/documentation/11/monitoring_and_troubleshooting_apps/)  

Monitoring and troubleshooting apps

8 May 2025 — OutSystems 11 (O11) offers comprehensive monitoring and troubleshooting tools for application performance and user experience.

Use cases for monitoring OutSystems apps

8 May 2025 — Learn about sample best-practices paths toward optimal monitoring and analysis solutions. - OutSystems 11 Documentation.

Streaming observability data - ODC Documentation

6 Sept 2026 — Stream observability data in real-time from OutSystems Developer Cloud (ODC) to various APM tools using OpenTelemetry framework.

DevOps and ALM in OutSystems

3 Jul 2026 — Elastic is a powerful monitoring and observability tool that you can use to leverage OutSystems monitoring data and, if needed, even do real ...

Introduction to log streaming

3 Jul 2026 — Log streaming is the process of continuously collecting and streaming log data to your Application Performance Monitoring (APM) or analytics ...

Monitoring and troubleshooting apps - ODC Documentation

28 Jul 2026 — OutSystems Developer Cloud (ODC) offers comprehensive tools for monitoring and troubleshooting applications through logs and traces within ...

Streaming log data - OutSystems 11

7 Feb 2025 — Explore how OutSystems 11 (O11) supports streaming log data in OTLP format to various APM tools for enhanced monitoring and troubleshooting.

Change logs storage location at OutSystems Cloud

16 Jan 2025 — Improve your observability and monitoring capabilities by using appropriate tools that won't impact the ongoing performance of app environments.

Best practices for testing and debugging mobile apps

27 Jul 2026 — Apply these recommendations when testing and debugging mobile apps in OutSystems Developer Cloud to catch issues early and diagnose problems ...

Monitor assets with ODC Analytics

6 days ago — ODC Analytics dashboard monitors app performance, health scores, errors, response times, AI model usage, and agent metrics across stages.

[epa.gov epa.gov](https://www.epa.gov/ghgemissions/sources-greenhouse-gas-emissions)  

Sources of Greenhouse Gas Emissions

9 Jun 2026 — Sources of greenhouse gas emissions, inculding electricity production, tranportation, industry, agriculture, and forestry.

[docs.appian.com docs.appian.com](https://docs.appian.com/suite/help/26.8/appian-recommendations.html)  

Appian Design Guidance

Appian design guidance is made up of both warnings and recommendations. Applying these design patterns helps improve the performance of your applications ...Read more

Introduction to Application Building in Appian

Appian supports three types of testing in particular: unit testing, UI testing, and performance testing. You'll want to thoroughly test your application before ...

Understanding the Health Check Report

Health Check provides insights into application design patterns and performance risks in your environment. Consider running performance testing on a ...

Glossary

Performance Testing Testing an application and its processes to ensure that it will scale and behave as expected during peak usage or in-production scenarios.

Site Object

This page provides detailed information on how to configure and manage a site object. This section provides you with guidance and tips. Sites do not support ...

DevOps in Appian

Performance: Testing an application and its processes to ensure that it will scale and behave as expected during peak usage or in-production scenarios.

Monitor View

The Monitor view helps you keep an eye on health and activity indicators for your applications. It includes both runtime and design-time information, and ...

Process Model Object

Design guidance Appian design guidance reinforces best practice design patterns that should be implemented in your objects. Process model guidance

Interface Object

Appian design guidance reinforces best practice design patterns that you should use in your objects. You'll see design guidance for interfaces while editing ...Read more

System Requirements [Administration]

Performance testing: Query performance across all tiers depends on your record type data volume, query complexity, and available resources. While row limits ...Read more

[apps.apple.com apps.apple.com](https://apps.apple.com/us/app/threads/id6446901002)  

Threads - App Store - Apple

Discover new perspectives and connect through conversation on Threads. See what people are talking about right now—from niche interests to big moments.Read more

[hmiprisons.justiceinspectorates.gov.uk hmiprisons.justiceinspectorates.gov.uk](https://hmiprisons.justiceinspectorates.gov.uk/hmipris_reports/children-in-custody-2024-25/)  

Children in custody 2024–25

23 Sept 2025 — An analysis of 12–18-year-olds' perceptions of their experiences in secure training centres and young offender institutions. What we found (Back ...

[seattleschools.org seattleschools.org](https://www.seattleschools.org/student-portal/technology-supports-for-families/source/)  

The Source

The Source is Seattle Public Schools' online communication tool that allows parents, guardians and students access to schedules, attendance, assessment scores, ...Read more

[source-ev.com source-ev.com](https://source-ev.com/)  

Source | Powering Your Journey with Ultra-Reliable EV ...

Our mission is simple: to build the safest, most reliable, and accessible electric vehicle charging network across the UK and Ireland.

[gdpr-info.eu gdpr-info.eu](https://gdpr-info.eu/art-25-gdpr/)  

Art. 25 GDPR – Data protection by design and by default

The controller shall implement appropriate technical and organisational measures for ensuring that, by default, only personal data which are necessary for each ...

[sourceoutdoor.com sourceoutdoor.com](https://sourceoutdoor.com/?srsltid=AfmBOorI07kEZ97Pa9eH_GJewX5LVcAewa_0s8fsyxf28Q7q2thlx490)  

Source - Leaders in Hiking Sandals & Hydration Systems

SOURCE is a world leader in outdoor gear for 30 years, designing and manufacturing Water Bladders, Hydration Packs, Sandals, and more.

[docs.retool.com docs.retool.com](https://docs.retool.com/)  

Retool Docs

RETOOL DOCS BUILD ANYWHERE, DEPLOY IN RETOOL Create production-ready apps using Retool, your favorite coding agent, or imported React code. Whether you’re improving an app or starting from scratch,...

Source Control documentation

Source Control allows organizations to manage changes to apps, workflows, resources, and themes using pull requests on remote source control management ...Read more

View user audit logs

Cloud customers on a Business or an Enterprise plan can download audit logs directly from the Audit Logs page. Downloading audit logs.Read more

Self-hosted deployments

A self-hosted, Retool-managed deployment is a single-tenant instance with low operational overhead. Retool deploys a stable release instance on AWS and manages ...Read more

Configuring Source Control in Retool

This laboratory focuses on configuring Retool with Github, a Source Control Management (SCM) provider. Additional documentation is provided here.

Audit trail logged events

Reference information for audit logs. By default, Retool captures the following events in the audit log. Refer to the View user audit logs page for more ...Read more

Self-hosted, self-managed Retool quickstart

This guide serves as an introduction to self-hosted Retool. It covers many of the concepts and terminology you would come across when deploying and ...Read more

Configure Source Control with GitHub

You create a repository for Source Control to use, then configure a GitHub App for your Retool instance that commits, pushes, and pulls changes. Requirements.Read more

Monitor usage and logs

Audit logs. Learn how to view and query user audit logs. Redact tokens from ingress logs. Set up your network gateway to redact short-lived authentication ...Read more

Self-hosted, self-managed

A self-hosted, self-managed deployment is a single-tenant instance that you host, deploy, and manage. This option provides you with complete control and ...Read more

Use Source Control with apps

Source Control lets organizations manage changes using remote SCM providers GitHub, GitLab, AWS CodeCommit, Bitbucket, and Azure Repos.Read more

View audit logs across spaces

Organization admins in the admin space can now view audit logs from all spaces on the same instance directly from the Audit logs page.

Deploy self-hosted Retool on Kubernetes

Deploy self-hosted Retool on Kubernetes. Tutorials for initial installation of a production instance of Retool on Kubernetes. Retool provides Terraform ...Read more

Multi-instance releases for Source Control

27 Aug 2025 — Self-hosted organizations using Source Control to protect apps can opt into the public beta of multi-instance releases.

Administration reference

Logged events. Reference information for audit logs. MCP tools. The set of tools available for use through Retool's MCP.Read more

Scalability (Self-hosted)

The Retool Platform, when run in a self-hosted environment (e.g., AWS, Azure, Google) will rely on compute, storage, networking, and security infrastructure.Read more

Source Control how-to guides

Step-by-step instructions for common features and functionality of Source Control. Guidance for specific goals or functionality. These guides assume users are ...Read more

Send audit log events to Datadog

11 Mar 2024 — Connect audit logs to Datadog. ... Read the docs. Tags. Enterprise · Observability · Cloud · Self-hosted. Platform. Build · Launch · Scale ...Read more

Deploy self-hosted Retool with Docker

Deploy self-hosted Retool with Docker · 1. Download self-hosted Retool · 2. Install dependencies · 3. Back up encryption key · 4. Configure the instance · 5.Read more

Source Control quickstart

This guide serves as an introduction to Source Control. It covers many of the concepts and terminology you would come across when using version control to ...Read more

Container logs

To access logs for Retool product events, such as user creation, use the audit logs instead. Access container logs. Retool sends container logs to standard ...Read more

Set up Retool Database on Self-hosted deployments

On self-hosted deployments, you can use your own PostgreSQL database to host Retool Database. Your database automatically connects to the main Retool backend ...Read more

Source Control tutorials

Source Control tutorials. Hands-on guides for configuring Source Control ... Set your hosting type and Retool domain to personalize code examples, links, and ...Read more

Operations | Retool Docs

For cloud customers, these logs are found at /audit. Retool's audit logs capture events like query executions, page views, user logins, changes to resources, ...Read more

Self-hosted Retool glossary

Self-hosted, Retool-managed instance. A deployment offering in which a self-hosted instance is deployed by the customer and partially managed by Retool.Read more

Protect apps with Source Control

Use the following guide to protect your app by checking it into a remote source control repository. Prerequisite: Configure Source Control.Read more

Monitoring and alerting best practices

Retool stores a record of user actions in audit logs. Review audit logs periodically to identify anomalous behavior such as unexpected resource access, unusual ...Read more

Self-hosted Retool upgrade best practices

Learn about best practices for upgrading your self-hosted Retool deployment. ... This guide provides high-level recommendations and best practices for updating ...Read more

Source Control environment variables

Source Control environment variables available for use with self-hosted Retool deployments. You can also set these variables from the Source Control ...Read more

Advanced query options

Queries and their parameters are logged in the audit logs when they're run. You should hide sensitive parameters, such as API keys, from your audit logs.Read more

Self-hosted, Retool-managed deployments

A self-hosted, Retool-managed deployment is a single-tenant instance with low operational overhead. Retool deploys a stable release instance on AWS and ...Read more

[nhs.uk nhs.uk](https://www.nhs.uk/tests-and-treatments/covid-19-rapid-lateral-flow-test/)  

COVID-19 rapid lateral flow test

COVID-19 rapid lateral flow tests show the result on the testing device within a few minutes. ... NHS App · Find my NHS number · View your test results · About ...Read more

[michaelfeathers.silvrback.com michaelfeathers.silvrback.com](https://michaelfeathers.silvrback.com/characterization-testing)  

Characterization Testing - Michael Feathers - Silvrback

8 Aug 2016 — Characterization Testing - Writing tests to describe and fix existing code.

[caict.ac.cn caict.ac.cn](https://www.caict.ac.cn/kxyj/qwfb/bps/202601/P020260109784447548497.pdf)  

人工智能安全治理蓝皮书

代码安全层面,防范恶意攻击。通过对模型原生代码、依赖库代 码及部署脚本… 识别 SQL 注入、越权访问、API 未授权调用等漏洞。

云计算蓝皮书

云计算白皮书(2023 年)》全面分析了我国各行业上云水平参差不齐的现状,

软件定义存储发展与应用研究报告

整体来看，软件定义存储是分布式存储的一次新的进化,利. 用通用商用服务器促进了数据中心硬件形态的统一，降低TCO，同. 时实现跨供应商、跨型号存储产品互通，支持存储资源 ...

中国网络安全产业白皮书

6 Sept 2019 — 中国网络安全产业白皮书(2019) 中国信息通信安全风险,为区块链信息服务的提供、使用、管理等提供有效的法律依据。

人工智能基础设施发展态势报告

人工智能基础设施发展态势报告（2021）. 13. 算力占算力的比重则由2016 年的3%提升至2020 年41%，智能算力成. 为算力快速增长的驱动力3。 来源：《中国算力发展指数白皮书》 ...

全球Web3 技术产业生态发展报告

今年的白皮书在《全球Web3 技术产业生态发展报告（2022 年）》. 的基础上，重点对过去一年Web3 技术、数据、应用、监管的发展. 变化进行分析和阐述。技术层面，核心技术 ...

数据安全技术与产业发展研究报告

无代码SDK 集成提供人工智能数据保护服务,定期筛查人工智 能数据系统漏洞及风 险,及时报警并处理。

量子信息技术发展与应用研究报告

以量子计算、量子通信和量子精密测量为代表的量子信息技术，. 是量子科技的重要组成部分，有望带来重大技术范式变革和颠覆性. 创新应用，已成为培育新质生产力、打造 ...

工业和信息化部人工智能标准化技术委员会

人工智能标准行—工业和信息化部人工智能标准化技术委员会2025年度全体会议暨“标准周”活动在京举办. 2025人工智能产业及赋能新型工业化大会在京举办.Read more

[ndi.caict.ac.cn ndi.caict.ac.cn](https://ndi.caict.ac.cn/)  

数据基础设施开放平台

平台主要包括身份管理、标识管理、目录管理、实名认证、业务节点注册、审批中心、运行监测等基础功能。

[www-file.huawei.com www-file.huawei.com](https://www-file.huawei.com/admin/asset/v1/pro/view/41ff85b1f4314ef7b9a4d38e08aef72d.pdf)  

主机上云技术白皮书

同时，低代码平台支持快速迭代，当业务需求变更时，仅需调整组件配置或补充少量代码，即可完成功能. 优化，避免传统开发中“牵一发而动全身”的改造负担。 此外，低代码平台 ...Read more

云计算

针对全民开发者(即非专业开发者),需要提供一站式的低代码开发平台,帮 助用户通过可视化拖拽方式开发由用户界面、 业务逻辑、工作流和数据服务组成的应用程 序

工业数字化/智能化2030

《工业数字化/智能化2030白皮书》(以下简称《白皮书》) 低代码开发商业模式… 快速构建数据管理平台,低成本、高效率管理工业数据

迈向智能世界白皮书2023 — 数字金融

采用Low Code/No Code低代码/无代码积木式开发, 开发者仅需编写少量代码就可以实 现自己想要的应用系统,降低软件开发中的不确定性,大幅提升开发效率。 和低代码开发的RPA( ...

白皮书

白皮书. 12. 11. 持续开发的平台AIDO（敏捷Agile 、智能Intelligent、设计Design 和. 编排Orchestration ）. AIDO 平台负责业务模型的开发、测试和存储，包括以下主要功能 ...Read more

[gma.caict.ac.cn gma.caict.ac.cn](https://gma.caict.ac.cn/regulatory/HK)  

中国香港认证要求| OFCA

我们为欧盟和欧洲经济区市场的RED 提供认证机构(NB) 欧盟型式检验证书。我们获准在FCC 的TCB、ISED FCB 和欧盟CE 标志计划中提供最广泛的无线认证，以无与伦比的响应认证最 ...Read more

Domestic and International Testing and Certification ...

国内外检测认证资讯公共服务平台, 是中国信息通信研究院运营的公共服务平台，面向ICT产品的国内国际认证，欢迎查阅并可通过问答模块提出您感兴趣的问题，平台将指派专家与

ATT Certification of Bolivia认证资讯

2023年9月28日，玻利维亚电信和运输管理局(ATT) 发布了编号为ATT-DJ-RAR-TL LP 443/2023的关于电信设备认证证书注册和发放的新行政监管决议。认证要求的主要变化包括为缩短 ...Read more

[ictp.caict.ac.cn ictp.caict.ac.cn](https://ictp.caict.ac.cn/EN/abstract/abstract1110.shtml)  

Maturity model and assessment method of digital twin cities

by Z Jingtao · 2023 — 数字孪生城市白皮书(2022)[R]. 2022. [2], 张竞涛, 陈才, 崔颖, 等. 数字孪生城市框架与发展建议[J]. 信息通信技术与政策, 2022, 48(12):2-11. [3], MANKINS J C ...

信息通信技术与政策

基于中小企业资源匮乏、人才短缺及业务敏捷性要求高的实际痛点,提出一套轻量化数据安全治理体系构建方案。该方案通过虚拟化组织架构、归口统筹、分块负责的治理逻辑与风险 ...

[startup.aliyun.com startup.aliyun.com](https://startup.aliyun.com/info/1060983.html)  

低代码引擎技术白皮书

低代码引擎技术白皮书 &gt; &gt; 低代码引擎技术白皮书 邵磊 戊子 林熠 力皓 金禅 度城 荣彬 牧毅 承虎 胖丁 絮黎 游鹿 彼洋 2022-03-04 00:00:00 4533 “低代码”这个概念是在 2014 年由 Forrester Research 提出的，但早在“低代码”这个概念正 式提出之前，它的产品或者说低代码平台其实就已经在市场上出现。最早我有印象的低代码平台是 Drea...

Gartner 企业低代码平台魔力象限

GARTNER 企业低代码平台魔力象限 &gt; &gt; GARTNER 企业低代码平台魔力象限 阿里云创新中心 2023-07-25 00:00:00 4880 阿里巴巴进入2022年度Gartner《企业低代码平台魔力象限》，为首次入选的中国厂商之一。 &gt; 关键词：数字中国 &gt; 创作者：Gartner® &gt; 发布日期：2023年4月 报告介绍 近日，国际咨询机构Gartner®正式...

再受认可！蓝凌荣获“2023中国低代码推荐厂商”

再受认可！蓝凌荣获“2023中国低代码推荐厂商” &gt; &gt; 再受认可！蓝凌荣获“2023中国低代码推荐厂商” 蓝凌OA办公系统 2023-12-28 15:46:46 1267 蓝凌低代码xAI，随需搭建数字化应用 近日，甲子光年发布《2023中国企业低代码/无代码产品应用与实践研究》，同期对“低代码重点厂商”进行了分析。蓝凌低代码平台凭借敏捷、优质的产品特性，荣获“2023中国低代码推...

[miittc1.caict.ac.cn miittc1.caict.ac.cn](https://miittc1.caict.ac.cn/register/)  

工业和信息化部人工智能标准化技术委员会

工业和信息化部人工智能标准化技术委员会. 代码是否有相关标准化. WG4模型与平台工作组

[huawei.com huawei.com](https://www.huawei.com/cn/huaweitech/publication/202301/adn-high-level-network-autonomy)  

ADN铺就高阶自智网络之路- 华为

通过构建低代码开发体系,降低CT人员向数智化转型的门槛,帮助运维运营团队向DICT复合型人才转型。

华为云，驶入深水区

在佛山，Astro低代码开发平台已经在助力政务开发人员大幅降低应用上线时间，让应用使用的政府人员可以直接参与开发，通过积木式搭建、可视化编排快速构建新应用，释放软件 ...Read more

普惠AI，华为云与全球开发者共成长

华为云提供了Full code与低代码相结合的开发工具套件。以AI应用为例,ModelArts可以帮助开发者以低代码的方式完成数据标注、模型训练及模型发布。

赋能政企深度用云，跃升数字生产力

在佛山，Astro低代码开发平台帮助政务开发人员大幅降低应用上线时间，让应用使用人员也可以直接参与开发，通过积木式搭建、可视化编排快速构建新应用，跃升软件开发生产力 ...Read more

[aihub.caict.ac.cn aihub.caict.ac.cn](https://aihub.caict.ac.cn/docs/wsAciQ3mgRSY)  

共赴两周年之约，鲸智社区“鲸挑智选”生态伙伴征集启动

7 days ago — 2026年10月，鲸智社区将迎来正式上线两周年。两年来，鲸智社区与广大伙伴携手同行，围绕算力、模型、数据、工具、智能体、产业应用等各类场景，持续 ...Read more

人工智能辅助肺癌多学科精准诊疗决策平台 - 鲸智社区

鲸智社区·大模型公共服务平台立足于打造国家级人工智能开源生态，精选AI模型、数据集、开发工具、MCP、智能体、高水平论文、典型案例等优秀资源，构建高性能算力底座， ...

【具身智能】李飞飞团队发布低成本家用机器人BRS - 鲸智社区

李飞飞团队最新推出的低成本家用机器人BEHAVIOR Robot Suite (BRS)，堪称家庭自动化领域的革命性突破。BRS 专为解决日常家务任务而设计，具备强大的全身操作能力，能够 ...Read more

AIGC媒体创作系统 - 鲸智社区·大模型公共服务平台

该系统集成了数字人主播、智能剪辑、自动配音与风格模板等功能，为短视频创作者、自媒体用户和教育讲师提供了低门槛的创作平台。 ... 低噪点的超高清视听输出，为AI ...Read more

[carrier.huawei.com carrier.huawei.com](https://carrier.huawei.com/~/media/cnbgv2/download/adn/autonomous-driving-network-overview-cn.pdf)  

目录

平台提供了端到端高效的数据建模和低代码化数据编排工具，支撑数据探索和分析，并通过. API等多种形式实现数据的高质量和高效率开放，从而实现对多场景应用对数据分析和 ...Read more

[tech.china.com tech.china.com](https://tech.china.com/article/20240717/072024_1548738.html)  

IDC：2024年国内低代码厂商评估，钉钉宜搭综合实力第一\_中华网

IDC：2024年国内低代码厂商评估，钉钉宜搭综合实力第一 IDC：2024年国内低代码厂商评估，钉钉宜搭综合实力第一 2024-07-17 14:49:57 来源：实况网 今日，IT市场研究和咨询公司 IDC 发布了《生成式 AI+低代码：探索新一代开发范式》和《中国低代码开发平台技术评估，2024》。 IDC 预测，到 2027 年，中国低代码/无代码软件市场规模将达到 106.3...

[investopedia.com investopedia.com](https://www.investopedia.com/apple-leads-sales-in-china-smartphone-market-for-first-time-ever-8549724)  

Apple Leads Sales in China's Smartphone Market for First Time Ever

In 2023, Apple became the top smartphone seller in China for the first time, capturing 17.3% of the market, according to preliminary data from the International Data Corporation (IDC). Apple narrowly surpassed rivals Honor (17.1%), OPPO (16.7%), Vivo (16.5%), and Xiaomi (13.2%), while other brands made up 19.1% of the market. Despite a challenging year for China’s smartphone market—marked by its lowest sales volume in a decade and a 5% overall decline in shipments to 271.3 million units—Apple's strategic price promotions through third-party channels helped boost demand and secure its leadership. IDC noted that the fourth quarter of 2023 saw a 1.2% year-over-year increase in shipments, suggesting a possible market recovery. Apple's performance may alleviate investor concerns about declining iPhone sales and intensifying competition in China. As of late Thursday, Apple stock traded at $193.84, slightly down from earlier, but has risen over 36% in the past year.

[barrons.com barrons.com](https://www.barrons.com/articles/apple-fourth-smartphone-seller-china-idc-d8cc643a)  

Apple Drops to Fourth Place Smartphone Seller in China

Apple has dropped to fourth place in smartphone market share in China, according to new data from International Data Corp. (IDC), as it faces strong competition from domestic brands. In the first quarter of 2024, overall smartphone shipments in China rose by 6.5% compared to the previous year, showing continued market growth. Honor led the market with a 17.1% share, closely followed by Huawei at 17%, which saw a 110% surge in shipments driven by strong demand for its Mate 60 line. OPPO secured third place with 15.7%, while Apple fell to fourth, holding 15.6% of the market after a 6.6% year-over-year decline in shipments. Vivo rounded out the top five with 14.6%. IDC attributed Apple’s decline to fierce Android competition, enhanced by AI and foldable technologies, and noted that Apple's price cuts were insufficient to counter these dynamics. Apple is expected to release its quarterly earnings on May 2.

PC Sales Will Be Flat in 2024 Despite AI Models, IDC Says

According to a new forecast by International Data Corp (IDC), global PC sales will remain flat in 2024 at approximately 260.2 million units, despite the influx of new AI-capable personal computers expected in the second half of the year. Major chipmakers such as Intel, AMD, and Qualcomm have released AI-ready components, and hardware manufacturers like Dell, HP, Lenovo, Acer, and Asus are preparing to launch AI PCs. However, several factors—including elevated PC inventories and economic challenges in China—are hindering overall growth. Excluding China, global PC shipments are projected to rise 2.6% compared to 2023. Consumer PC sales are expected to decline by 1.1% globally, with a slight increase outside of China. High interest rates and competition from other devices such as smartphones contribute to this stagnation. While AI PCs are not forecasted to drive significant long-term shipment growth, they are expected to elevate average selling prices and gradually shift computing capabilities towards on-device AI use. IDC projects AI PCs will constitute over two-thirds of the market by 2028. Despite these trends, market reactions have been mixed, with Dell and HP shares declining amid this news.

[performance.gov performance.gov](https://www.performance.gov/cx/)  

Federal Customer Experience | CX - Performance.gov

You can easily track your case status, see accurate estimates of processing times, and provide customer feedback that's publicly shared by agencies for ...

[customer.io customer.io](https://customer.io/)  

Customer.io: AI-Powered Customer Engagement Platform

Customer.io is a customer engagement platform for creating personalized journeys and better business outcomes across email, push, SMS, and in-app messaging.

[tripadvisor.com tripadvisor.com](https://www.tripadvisor.com/Hotel_Feature-g528813-d13120977-zft9179-MOXY_London_Heathrow_Airport.html)  

Is there a breakfast at MOXY London Heathrow Airport ... - Tripadvisor

The Good: Close to airport; five minute bus ride from tube; free breakfast and coffee. The Bad: Honestly, I'm giving them a huge benefit of the doubt by ...

[merriam-webster.com merriam-webster.com](https://www.merriam-webster.com/dictionary/customer)  

CUSTOMER Definition & Meaning - Merriam-Webster

The meaning of CUSTOMER is one that purchases a commodity or service. How to use customer in a sentence.

CONTROL Definition & Meaning - Merriam-Webster

The meaning of CONTROL is to exercise restraining or directing influence over : regulate. How to use control in a sentence.

[support.google.com support.google.com](https://support.google.com/google-ads/answer/6379332?hl=en)  

About Customer Match - Google Ads Help

Use Data Manager or Data Manager API for your Customer Match workflows for an improved developer experience and access to additional features.

[lowes.com lowes.com](https://www.lowes.com/)  

Lowe's Home Improvement

Shop tools, appliances, building supplies, carpet, bathroom, lighting and more. Pros can take advantage of Pro offers, credit and business resources.

[ccacoalition.org ccacoalition.org](https://www.ccacoalition.org/content/low-methane)  

Lowering Organic Waste Methane (LOW-Methane)

The LOW-Methane Initiative works with jurisdictions to help them identify ambitious actions to reduce waste methane emissions and unlock implementation by ...

[federalregister.gov federalregister.gov](https://www.federalregister.gov/documents/2026/06/22/2026-12460/permitted-payment-stablecoin-issuer-customer-identification-program)  

Permitted Payment Stablecoin Issuer Customer Identification Program

Obligations under this proposal are comparable to existing CIP requirements for other financial institutions, such as banks, brokers-dealers, ...

[heathrow.com heathrow.com](https://www.heathrow.com/at-the-airport/airport-services/fast-track)  

Fast Track - Heathrow Airport

Heathrow offers Fast Track products for both departing (Security) and arriving (Passport Control) passengers to enhance your airport experience. Book Fast Track.

[alansparhawk.com alansparhawk.com](https://www.alansparhawk.com/)  

Alan Sparhawk + Low

The official website for Alan Sparhawk and Low.

[microsoft.com microsoft.com](https://www.microsoft.com/en/customers/story/766053-heathrow-airport-travel-transportation-power-apps)  

Heathrow Airport inspires employee engagement with ...

7 Nov 2019 — Through the low-code development of 30 apps, Heathrow employees have eliminated 75,000 helping the airport reduce its costs.

Overview of Dataverse Git integration - Power Platform | Microsoft Learn

OVERVIEW OF GIT INTEGRATION IN POWER PLATFORM Feedback Summarize this article for me IN THIS ARTICLE 1. ALM in the Power Platform and Dataverse 2. Benefits 3. Key concepts 4. Code-first developme...

ALM for developers in Power Platform - Power Platform | Microsoft Learn

ALM FOR DEVELOPERS Feedback Summarize this article for me IN THIS ARTICLE 1. Team development 2. Conflict management 3. Working with complex components The articles in this section describe how...

[mendix.com mendix.com](https://www.mendix.com/customer-stories/siemens-energy-promotes-innovation-and-process-efficiency-with-200-low-code-apps/)  

Siemens Energy Promotes Innovation and Process ...

Siemens Energy adopted the Mendix low-code development platform and has delivered over 200 applications that are replacing legacy systems, reducing manual work,

Siemens Rapidly Develops a Complex Ordering System ...

Utilizing the Mendix low-code platform, Siemens developed the Quick Order Processing (QOP) system. The new system includes: One-click ordering; Automated data ...Read more

Siemens Improves Data Collection and Collaboration with ...

By leveraging low-code, the department automated sampling and feedback collection for twice-yearly audits, significantly reducing the workload and accelerating ...

How Siemens AG is Unlocking Strategic Value with Over ...

Siemens has mobilized thousands of employees to contribute to software development projects with the Mendix low-code platform – resulting in more than 1,000 ...

Engineering Operations Center Transforms Project ...

Compared to traditional high-code development, which would require at least a year, low-code's agility saved approximately 40% of time. Initial feedback showed ...Read more

Mendix Enables Siemens Finance Teams to Develop Their ...

The finance department summarized the benefits of low-code development: Time Savings: Medium-scale applications can be developed in 40 days versus 3-4 months ...Read more

Siemens Dayu Platform Enables Business Department ...

Using big data, machine learning, cloud technology, and low-code development, the team builds a data analysis ecosystem rooted in Siemens' business practices. ...

Siemens Enables Rapid Digitization in a 175-Year-Old ...

8 Feb 2023 — Siemens adopted low-code in 2018 and has implemented proven development frameworks to deliver over 450 applications supporting all business ...

Siemens Global Business Services Democratizes App ...

Learn how Siemens created 2400% ROI and millions in savings by building an application to streamline freight claims using low-code.

Real-Time Data Visualization Dashboard Enables Smarter ...

Siemens Electric Drive Co., Ltd. SEDL uses Siemens low-code to develop a visual dashboard that updates data in real time to control production procedures ...

Deploying Apps | Mendix Documentation

DEPLOYING APPS Last modified: July 7, 2025 INTRODUCTION There are multiple ways to deploy a Mendix application. You can deploy to your local machine for development and testing. You can deploy to...

Deploying an App to Mendix Cloud | Mendix Documentation

DEPLOYING AN APP TO MENDIX CLOUD Last modified: August 4, 2026 INTRODUCTION This page describes how to deploy an app to Mendix Cloud. The method for deploying an app to Mendix Cloud differs depen...

Launching Your First App | Mendix Documentation

LAUNCHING YOUR FIRST APP Last modified: February 5, 2026 INTRODUCTION By the end of this section, you will be able to: \* Identify the different options available to test your app. \* Describe the...

Monitoring Your Mendix Apps with an APM Tool | Mendix Documentation

MONITORING YOUR MENDIX APPS WITH AN APM TOOL Last modified: September 1, 2026 INTRODUCTION There are several application performance monitoring (APM) tools for cloud applications available through...

Deploy API – Version 4 | Mendix Documentation

DEPLOY API – VERSION 4 Last modified: January 20, 2026 The Deploy API only works for apps that are deployed to Mendix Cloud. INTRODUCTION The Deploy API allows you to manage application environme...

Enabling Version Control for Your App | Mendix Documentation

ENABLING VERSION CONTROL FOR YOUR APP Last modified: July 16, 2026 INTRODUCTION Version control is enabled by default for Mendix apps. If the option was explicitly disabled during app creation, yo...

Version Control | Mendix Documentation

If you would like to upgrade to a newer long-term support version of Studio Pro, see Upgrading from Mendix Studio Pro 9 to 10. VERSION CONTROL Last modified: September 26, 2025 INTRODUCTION Versi...

Environments and Deployment | Mendix Documentation

ENVIRONMENTS AND DEPLOYMENT Last modified: September 7, 2026 INTRODUCTION You can use the Environments page to access information about your environments, deployment packages, manage certificates...

Workflow Versioning and Conflict Mitigation | Mendix Documentation

WORKFLOW VERSIONING AND CONFLICT MITIGATION Last modified: July 28, 2026 INTRODUCTION Workflows are processes that can potentially run for a long time. While a workflow is in progress, new version...

Versioning an App Deployed to the Cloud | Mendix Documentation

VERSIONING AN APP DEPLOYED TO THE CLOUD Last modified: March 4, 2026 INTRODUCTION While developing, you can deploy and run your app on your local machine by clicking the menu item Run &gt; Run Locall...

Operation Metrics | Mendix Documentation

OPERATION METRICS Last modified: July 30, 2026 INTRODUCTION The Metrics page contains detailed graphs about your app and its environment. You can use this page to monitor the performance and healt...

Deploy to the Cloud | Mendix Documentation

DEPLOY TO THE CLOUD Last modified: March 28, 2025 INTRODUCTION This menu option dialog creates a versioned deployment package and deploys it to your environment in Mendix Cloud. Image: Deploy to...

Mendix Cloud Release Notes | Mendix Documentation

MENDIX CLOUD RELEASE NOTES Last modified: September 7, 2026 These release notes cover changes to deployment to Mendix Cloud. There are separate release notes for other deployment targets; for more...

Deployment Options | Mendix Documentation

DEPLOYMENT OPTIONS Last modified: June 18, 2025 INTRODUCTION This document describes the supported deployment scenarios for the Application Test Suite (ATS). Every customer situation is different...

Testing | Mendix Documentation

TESTING Last modified: July 17, 2026 INTRODUCTION Testing is a vital component when creating a Mendix application. Finding and fixing bugs when your application is in production is more expensive...

Working with Git On-Premises Version Control Server | Mendix Documentation

WORKING WITH GIT ON-PREMISES VERSION CONTROL SERVER Last modified: September 26, 2025 INTRODUCTION When developing Mendix applications, changes to these applications are stored in a version contro...

Deployment Location | Mendix Documentation

DEPLOYMENT LOCATION Last modified: January 15, 2026 INTRODUCTION When you deploy your app outside Mendix Cloud, you can choose the URL that points to your app. However, there are some restrictions...

Configuring POST and GET Request Steps | Mendix Documentation

CONFIGURING POST AND GET REQUEST STEPS Last modified: August 10, 2026 INTRODUCTION POST and GET request steps let Mendix Pipelines call external systems over HTTPS to trigger actions, send data, o...

Version Control | Mendix Documentation

VERSION CONTROL Last modified: September 26, 2025 INTRODUCTION Version Control allows you to manage your app development in two ways: \* Firstly, it allows you to store (commit) the current revisi...

Troubleshooting Version Control | Mendix Documentation

TROUBLESHOOTING VERSION CONTROL Last modified: April 1, 2026 INTRODUCTION Mendix Studio Pro contains a version control system that supports collaborating with team members. This document describes...

[ryotokuro.gitbook.io ryotokuro.gitbook.io](https://ryotokuro.gitbook.io/microsoft/power-platform/power-platform-fundamentals/introduction-to-power-apps/case-study-heathrow-airport)  

Case study: Heathrow Airport | Microsoft - Readme - GitBook

24 Jun 2020 — Let's look at an example of a real world case of how a large infrastructure, Heathrow Airport has used the Power Platform to dramatically ...

[futuredotnow.uk futuredotnow.uk](https://futuredotnow.uk/samits-story-heathrow-airport/)  

Samit's story, Heathrow Airport

Heathrow embraced the potential of the platform and invited all staff to explore what it could offer, including the, 'Power Apps' programme, which allows for ...

[info.microsoft.com info.microsoft.com](https://info.microsoft.com/ww-landing-Turn-Your-Great-Ideas-into-Powerful-Apps.html?lcid=en-us)  

Power Apps Heathrow Webinar

Register for this webinar to learn how Heathrow Airport uses Power Apps to help achieve its vision of providing the best airport service in the world.

[valto.co.uk valto.co.uk](https://valto.co.uk/case-studies/city-of-london-case-study/)  

City of London Reduces Issue Reporting Time by 80 ... - Valto

We built The City of London a pilot version of a customised Microsoft Power App solution that was backed by Power Automate and SharePoint Online. A select group ...

[data-flair.training data-flair.training](https://data-flair.training/blogs/power-bi-case-study/)  

Power BI Case Study - How the tool reduced hassles ...

Heathrow group went with Microsoft Power BI as their business intelligence software and Microsoft Azure for cloud services. The airport has deployed Microsoft ...

[wired.com wired.com](https://www.wired.com/story/microsoft-power-apps-data-exposed)  

38M Records Were Exposed Online-Including Contact-Tracing Info

In 2021, researchers from UpGuard discovered that over 1,000 Microsoft Power Apps portals had been misconfigured, which unintentionally exposed 38 million records online. This included sensitive information like social security numbers, phone numbers, addresses, and COVID-19 vaccination data from organizations such as American Airlines, Ford, J.B. Hunt, several health departments, and public schools. The problem stemmed from Power Apps' design, which defaulted to making API data public unless manual privacy configurations were set. While no data theft was reported, the issue prompted Microsoft to change the default to private and release tools to help users audit configurations. The incident underscores the importance of secure default settings in cloud platforms, as widespread misconfigurations indicate systemic design flaws.

[investors.appian.com investors.appian.com](https://investors.appian.com/)  

Appian Corporation - IR site | Investor Relations | Investor Relations

Appian provides AI automation for mission-critical work. We automate complex processes in large enterprises and governments.

[enterprisecommunity.org enterprisecommunity.org](https://www.enterprisecommunity.org/about)  

About | Enterprise Community Partners

Enterprise Community Partners is a national nonprofit that exists to make a good home possible for the millions of families without one.

[academy.appian.com academy.appian.com](https://academy.appian.com/)  

Appian Academy

A full learning path in building intelligent, automated processes using Appian AI. Appian provides AI automation for mission-critical work. We automate complex ...

[dell.com dell.com](https://www.dell.com/support/contents/en-us/videos/videoplayer/openmanage-enterprise-offline-console-updates/6381463577112)  

OpenManage Enterprise Offline Console Updates | Dell US

Here how to update OpenManage Enterprise from an HTTP, HTTPS or NFS share on your local network.

[appmarket.appian.com appmarket.appian.com](https://appmarket.appian.com/listings/aquaman)  

AQuAMan - Appian AppMarket

This release augments the existing 'Code Complexity' report to include a report on any 'Magic Numbers' that the SAIL code might contain

PersonalizationUtilities - Appian AppMarket

Retrieve and act on Appian Groups and Users with a set of Smart Services and Custom Functions.

Snowflake - Appian AppMarket

Appian helps you get more from Snowflake by turning raw data into action through low-code applications and AI-powered automation.

[appian.com appian.com](https://appian.com/demo-request)  

Appian Demo - See Our AI Process Automation Platform in Action

On the Appian platform, customers build AI-powered processes that accelerate work, reduce cost, and manage risk. Case in Low-Code Report. Awarded $2.036 Billion

Transportation Operations Solutions & Applications - Appian

Learn how Appian's digital transformation software solutions are helping to enhance collaboration and optimize processes in the transportation sector.

Governance, Risk, & Compliance (GRC) Software & Solutions - Appian

Appian empowers insurers to improve agility for GRC requirements and deliver a unified view of risk data for your enterprise.

Streamlining Contracts with Appian's AI-Powered Automation

In this session, learn how Appian's Contract Lifecycle Management (CLM) solution can help your organization automate and optimize the entire contracting process ...

Aon

https://appian.com/about/explore/customers/all-customers/aon

Aon Transforms Reinsurance Claims Processing with Appian

PRESS RELEASE AON TRANSFORMS REINSURANCE CLAIMS PROCESSING WITH APPIAN October 10, 2023 Appian Contributor Aon achieves increased agility through scalable, secure, end-to-end process automation...

The Future of Insurance: Appian's Use Cases & Successful Partnerships

NAVIGATING THE FUTURE OF INSURANCE January 29, 2024 Vanna Maggi Partner Programs Content and Communications Appian A DEEP DIVE INTO APPIAN'S USE CASES AND STORIES FOR SUCCESSFUL PARTNERSHIPS Th...

About Appian | Enterprise AI Automation Platform

https://appian.com/about/explore/overview

Customer Experience

CUSTOMER EXPERIENCE ENHANCE CUSTOMER EXPERIENCE WITH AI-POWERED AUTOMATION Connect people, systems, data, and AI in a unified platform. Make every resolution faster, smarter, and compliant by desig...

Reinsurance Management Software - Platform to Automate Reinsurance

REINSURANCE AUTOMATE REINSURANCE PROCESSES Improve efficiency and risk management with AI-powered process automation. Contact Us TRUSTED BY LEADING INSURERS TOP BENEFITS STREAMLINE CEDENT ONBOA...

Appian Platform for AI Process Automation

THE APPIAN PLATFORM CONTROL YOUR PROCESS. OWN YOUR OPERATIONS. Unify people, systems, and AI with a single platform for AI automation. Join a Live Demo Image: Screenshot 2026 08 20 At 12 [Button...

Policy Underwriting & Service Operations: Insurance Solutions

POLICY UNDERWRITING AND SERVICE OPERATIONS. Enable connected underwriting and accelerated business. Read the Whitepaper LEADING INSURERS TRUST APPIAN. Efficient, connected underwriting, controlle...

Inspect the Deployment [Direct Deployments]

View this page in the latest version of Appian. INSPECT THE DEPLOYMENT On This Page The third step of a direct deployment using Compare and Deploy is the Inspect the Deployment step. Here, Appian...

Pre-Release Testing Program [Appian Cloud Administration]

PRE-RELEASE TESTING PROGRAM On This Page | This page applies to Appian Cloud only. It may not reflect the differences with Appian Government Cloud. OVERVIEW The Pre-Release Testing Program is a n...

Testing Applications [DevOps]

TESTING APPLICATIONS On This Page OVERVIEW This page is about the ways you can test and validate your Appian applications. Testing is an important part of the application life cycle—it’s how you c...

Web Administrator Guide

WEB ADMINISTRATOR GUIDE On This Page The Web Administrator is responsible for the configuration and monitoring of Appian which does not require direct access to the server. Common activities includ...

Insurance Process Automation for Better Business Outcomes

Insurance SMARTER UNDERWRITING and claims AI-powered insurance process automation. Explore the Platform Hear from leading insurers [Button: ×] Image: AI-powered insurance process automation In...

Aegon

AEGON: SIMPLIFYING INSURANCE FOR CUSTOMERS WITH DIGITAL INSURANCE SOLUTIONS & INTELLIGENT AUTOMATION Image: Logo Aegon New Aegon’s Dutch roots date back to 1844. Today, the company has operations i...

Appian DocCenter for Insurance

APPIAN DOCCENTER FOR INSURANCE Appian Resource Center Image Appian provides AI automation for mission-critical work. We automate complex processes in large enterprises and governments. Our platfor...

Appian Announces 2022 Excellence in Low-Code Award Winners

PRESS RELEASE APPIAN ANNOUNCES 2022 EXCELLENCE IN LOW-CODE AWARD WINNERS June 21, 2022 Appian Contributor McLean, VA – June 21, 2022 - Appian (NASDAQ: APPN) announced the winners of the 2022 Exce...

Our Customers

OUR CUSTOMERS APPIAN CUSTOMERS ARE REVOLUTIONIZING PRODUCTIVITY Discover how our customers use Appian to revolutionize their customer experience, transform their business operations, and master glo...

Aon: Achieving Operational Innovation with Appian

APPIAN WORLD 2025 AON: ACHIEVING OPERATIONAL INNOVATION WITH APPIAN Presenters: Kirsten Moore - Product Director, Aon Description: Learn how Aon scaled Appian for process automation across all sol...

DIA ITC Europe 2023

JOIN APPIAN AT DIA ITC EUROPE 28-29 June, 2023 FIRA GRAN VIA, North Access, Hall 8.1 Carrer del Foc, 37, Barcelona \* \* \* The future of insurance is here. Join Appian at DIA ITC Europe for the mo...

Aon transforma el procesamiento de reclamaciones de reaseguro con Appian | Appian

PRESS RELEASE AON TRANSFORMA EL PROCESAMIENTO DE RECLAMACIONES DE REASEGURO CON APPIAN October 10, 2023 Aon consigue una mayor agilidad a través de la automatización de procesos escalable, segura...

Enterprise Application Modernization Software

Enterprise Modernization MODERNIZE PROCESSES, NOT JUST SYSTEMS Effective modernization doesn't just rebuild systems. It reimagines processes and transforms how work gets done. With Appian, you can...

Life Insurance Software & Automation Solutions

LIFE INSURANCE DELIVER A CONNECTED LIFE INSURANCE EXPERIENCE Use AI-powered process automation to revitalize legacy systems, boost efficiency, and win customers. Contact Us TRUSTED BY LEADING INS...

ITC

ITC VEGAS RETURNS OCTOBER 2021 October 4 - 6, 2021 Mandalay Bay, Las Vegas The world’s largest gathering of insurance leaders and innovators. \* \* \* Don’t Miss Appian at ITC Vegas! Appian Boot...

[enterprisemobility.com enterprisemobility.com](https://www.enterprisemobility.com/)  

Introducing Enterprise Mobility

Enterprise Mobility marks the beginning of our next chapter, For more than 65 years we've been moving mobility forward. We began more than 65 years ago with a ...

[careers.appian.com careers.appian.com](https://careers.appian.com/)  

Appian Careers

On the Appian platform, customers build AI-powered processes that accelerate work, reduce cost, and manage risk.

[martinfowler.com martinfowler.com](https://martinfowler.com/books/)  

books - Martin Fowler

Each topic should be relevant to hands-on technical leaders, particularly in enterprise applications. The books should focus on long-lived fundamentals ...

[entethalliance.org entethalliance.org](https://entethalliance.org/)  

Enterprise Ethereum Alliance | Driving Ethereum Adoption in Business

The Enterprise Ethereum Alliance connects Fortune 500 enterprises, startups, and technology vendors to build enterprise blockchain solutions.

[coxenterprises.com coxenterprises.com](https://www.coxenterprises.com/)  

Cox Enterprises: Empower to Build

Empower to build. The story of Cox Enterprises is one of hard work, respect for employees, entrepreneurship and making bold decisions.

[retool.com retool.com](https://retool.com/customers/pump)  

How Pump saved 1600+ engineering hours with custom ...

Pump built 4 Retool apps to automate billing, onboarding, and cloud ops—saving 1600+ engineering hours and accelerating product velocity across teams.

Zeus

"Developing with Retool meant that 75–80% of the app was already built," said Justin Law, corporate planning engineer at Zeus. ... days to just four hours—a 92% ...Read more

How Segment uses real-time data in Retool for better support

And learn how teams build custom support tools and success dashboards in hours with Retool. Join industry leaders in changing the way you build custom ...Read more

Doordash

DoorDash builds tools in just hours with Retool ... Engineers were able to build their new tools in hours and more effectively support their operations teams ...Read more

Power Digital

Results with Retool: 50+ hours saved per month in contract review time; 90%+ accuracy in automated contract data extraction; 2x faster development cycles; 1,000 ...Read more

How Pernod Ricard scaled AI apps across 160 markets

Each went from concept to working prototype in days. Going from pilots to production on a platform built for global scale. What used to take a year to ...

Customers

Built for companies of all sizes. From startups to Fortune 500s, the world's most effective teams use Retool to build business software and operate better.Read more

Power MBA

How ThePowerMBA saves 40 hours per month reporting financial data using Retool.

Teachable

... days or weeks of engineering time. This shift allowed engineers to focus on ... We quickly built dashboards that were so effective, and some went straight into ...Read more

EquipmentShare | Retool

EquipmentShare, an equipment rental company that replaces the industry's manual and control over equipment usage, operating hours, billing, time tracking, ...

Finn

And he built it extremely quickly. For example, the “Compound Processes” tab that surfaced ETAs and other workflows took just two days to build. Building the ...Read more

Holland & Barrett

Holland & Barrett uses Retool to build internal business tools for their retail and digital operations teams, including dashboards for managing product data, ...

Plaid

Plaid uses Retool to build internal operations and customer support tools, companies like DoorDash, Snowflake, and Brex build custom support tools in hours ...

How Ramp operates 20% more efficiently and saved $8M ...

Ramp used Retool to build every important internal tool they've needed, saving them from purchasing expensive software or wasting engineering hours. Modern ...Read more

Remitly

Remitly is a digital remittance platform that makes it fast, affordable, and reliable for immigrants to send money to family in their home countries.Read more

Earnin

In the early days at Earnin, the engineering team built custom internal tooling for the customer service team that supported their basic needs. As they ...Read more

Descript scales operations with AI apps in Retool

Descript built 50+ AI apps in Retool, saving tens of thousands of dollars and automating hundreds of hours weekly without engineering resources.

How Westhill rebuilt operations to shift 60% of engineering ...

Engineering increased roadmap velocity as it shifted 30 full-time engineers away from internal tooling projects–over 60,000 engineering hours–to focus on other ...Read more

How Brex scaled 10x with Retool internal tools

Brex is a financial services company offering corporate cards, expense management, and business banking products built specifically for startups and fast- ...Read more

Komatsu built call center automation in Retool

Across the board, Eric estimates potential savings of over 22,000 hours of time annually. Enabling revenue growth. With Retool, Komatsu will be able to deliver ...Read more

How Harmonic Saved $20K Replacing a SaaS Tool with ...

33 internal apps built; $20,000+ saved by replacing an existing SaaS tool; 5 AI-generated tickets filed to every human ticket; 30+ million companies in their ...Read more

[engage.appian.com engage.appian.com](https://engage.appian.com/appian-for-insurance)  

Appian for Insurance

SMARTER PROCESS FOR INSURANCE MODERNIZATION The leading platform to boost productivity, reduce risk, and improve customer experiences. CONNECT PEOPLE, PROCESSES, AND DATA TO MODERNIZE OPERATIONS In...

[store.steampowered.com store.steampowered.com](https://store.steampowered.com/app/870780/CONTROL_Ultimate_Edition/)  

CONTROL Ultimate Edition on Steam

Winner of over 80 awards, CONTROL is a visually stunning third-person action-adventure that will keep you on the edge of your seat.

[remedygames.com remedygames.com](https://www.remedygames.com/games/control)  

Control - Remedy Entertaiment

After a secretive agency in New York is invaded by an otherworldly threat, you become the new Director struggling to regain Control.

[springer.com springer.com](https://link.springer.com/article/10.1007/s12599-021-00726-8)  

Low-Code Platform | Business & Information Systems Engineering | Springer Nature Link

LOW-CODE PLATFORM \* Catchword \* Open access \* Published: 15 November 2021 \* Volume 63, pages 733–740 (2021) \* Cite this article You have full access to this open access article Download PDF Save...

Analysing app reviews for software engineering: a systematic literature review | Empirical Software Engineering | Springer Nature Link

ANALYSING APP REVIEWS FOR SOFTWARE ENGINEERING: A SYSTEMATIC LITERATURE REVIEW \* Open access \* Published: 20 January 2022 \* Volume 27, article number 43 (2022) \* Cite this article You have full ac...

Low-code development and model-driven engineering: Two sides of the same coin? | Software and Systems Modeling | Springer Nature Link

LOW-CODE DEVELOPMENT AND MODEL-DRIVEN ENGINEERING: TWO SIDES OF THE SAME COIN? \* Expert Voice \* Open access \* Published: 11 January 2022 \* Volume 21, pages 437–446 (2022) \* Cite this article You h...

The democratization of software engineering: evolution, definition, and the future of low-code and no-code platforms | Management Review Quarterly | Springer Nature Link

However, the current lack of terminological consensus complicates the synthesis of research findings and obscures strategic decision-making in practice. This paper addresses this conceptual fragmentat...

Design of blockchain-based applications using model-driven engineering and low-code/no-code platforms: a structured literature review | Software and Systems Modeling | Springer Nature Link

DESIGN OF BLOCKCHAIN-BASED APPLICATIONS USING MODEL-DRIVEN ENGINEERING AND LOW-CODE/NO-CODE PLATFORMS: A STRUCTURED LITERATURE REVIEW \* Special Section Paper \* Open access \* Published: 11 June 2023...

Deep security analysis of program code | Empirical Software Engineering | Springer Nature Link

DEEP SECURITY ANALYSIS OF PROGRAM CODE A systematic literature review \* Open access \* Published: 21 October 2021 \* Volume 27, article number 2 (2022) \* Cite this article You have full access to t...

Model-driven development platform selection: four industry case studies | Software and Systems Modeling | Springer Nature Link

MODEL-DRIVEN DEVELOPMENT PLATFORM SELECTION: FOUR INDUSTRY CASE STUDIES \* Regular paper \* Open access \* Published: 15 January 2021 \* Volume 20, pages 1525–1551 (2021) \* Cite this article You have...

Claimed advantages and disadvantages of (dedicated) model transformation languages: a systematic literature review | Software and Systems Modeling | Springer Nature Link

3.1). As a first step, during the review we selected 58 publications from which to extract claims and evidence for advantages and disadvantages of model transformation languages. Afterwards, we catego...

Low Code Development Cycle Investigation | Springer Nature Link

It supports the way requirements are elicited, collected, analyzed, and processed into functionalities and non-functionalities in information systems. Technology enables end-users to create their own...

Industry practices and challenges for the evolvability assurance of microservices | Empirical Software Engineering | Springer Nature Link

INDUSTRY PRACTICES AND CHALLENGES FOR THE EVOLVABILITY ASSURANCE OF MICROSERVICES An interview study and systematic grey literature review \* Open access \* Published: 22 July 2021 \* Volume 26, arti...

Topic modeling in software engineering research | Empirical Software Engineering | Springer Nature Link

4 RESEARCH METHOD We conducted a literature survey to describe how topic modeling has been applied in software engineering research. To answer the research questions introduced in Section 1, we follo...

Effects of variability in models: a family of experiments | Empirical Software Engineering | Springer Nature Link

EFFECTS OF VARIABILITY IN MODELS: A FAMILY OF EXPERIMENTS \* Open access \* Published: 17 March 2022 \* Volume 27, article number 72 (2022) \* Cite this article You have full access to this open acces...

Recommender systems in model-driven engineering | Software and Systems Modeling | Springer Nature Link

RECOMMENDER SYSTEMS IN MODEL-DRIVEN ENGINEERING A systematic mapping review \* Regular Paper \* Open access \* Published: 26 July 2021 \* Volume 21, pages 249–280 (2022) \* Cite this article You have...

Agility, Innovation and Risk: A Systematic Literature Review on New Software Product Development and Organisational Capabilities | Archives of Computational Methods in Engineering | Springer Nature Link

\* 954 Accesses \* Explore all metrics ABSTRACT The aim of the study is to synthesise fragmented research streams to understand how organisational capabilities shape software development results suc...

Organizing the fragmented landscape of multidisciplinary product development: a mapping of approaches, processes, methods and tools from the scientific literature | Research in Engineering Design | Springer Nature Link

ORGANIZING THE FRAGMENTED LANDSCAPE OF MULTIDISCIPLINARY PRODUCT DEVELOPMENT: A MAPPING OF APPROACHES, PROCESSES, METHODS AND TOOLS FROM THE SCIENTIFIC LITERATURE \* Original Paper \* Open access \* Pu...

Measuring affective states from technical debt | Empirical Software Engineering | Springer Nature Link

MEASURING AFFECTIVE STATES FROM TECHNICAL DEBT A psychoempirical software engineering experiment \* Open access \* Published: 22 July 2021 \* Volume 26, article number 105 (2021) \* Cite this article...

[ieee.org ieee.org](https://ieeexplore.ieee.org/document/6405253/)  

An empirical analysis of the distribution of unit test smells and their impact on software maintenance | IEEE Conference Publication | IEEE Xplore

AN EMPIRICAL ANALYSIS OF THE DISTRIBUTION OF UNIT TEST SMELLS AND THEIR IMPACT ON SOFTWARE MAINTENANCE Publisher: IEEE PDF \* \* \* Abstract Authors \* Download PDF \* Download References \* Request...

Iteration Causes, Impact, and Timing in Software Development Lifecycle: An SLR | IEEE Journals & Magazine | IEEE Xplore

ITERATION CAUSES, IMPACT, AND TIMING IN SOFTWARE DEVELOPMENT LIFECYCLE: AN SLR Publisher: IEEE [Button: Cite This] PDF Under a Creative Commons License Abstract Authors Figures References C...

Cumulative code churn: Impact on maintainability | IEEE Conference Publication | IEEE Xplore

CUMULATIVE CODE CHURN: IMPACT ON MAINTAINABILITY Publisher: IEEE Abstract Authors Figures References \* Download PDF \* Download References \* Request Permissions \* Save to \* Alerts ABSTRACT: It...

Quantifying the Impact of Staged Rollout Policies on Software Process and Product Metrics | IEEE Conference Publication | IEEE Xplore

QUANTIFYING THE IMPACT OF STAGED ROLLOUT POLICIES ON SOFTWARE PROCESS AND PRODUCT METRICS ABSTRACT: Software processes define specific sequences of activities performed to effectively produce softw...

Quality Assurance in Low-Code/No-Code Development | IEEE Conference Publication | IEEE Xplore

QUALITY ASSURANCE IN LOW-CODE/NO-CODE DEVELOPMENT Publisher: IEEE ABSTRACT: Low-code and no-code development platforms have emerged as instrumental tools in expediting software development, cateri...

A controlled experiment in maintenance: comparing design patterns to simpler solutions | IEEE Journals & Magazine | IEEE Xplore

A CONTROLLED EXPERIMENT IN MAINTENANCE: COMPARING DESIGN PATTERNS TO SIMPLER SOLUTIONS Publisher: IEEE Abstract Authors ABSTRACT: Software design patterns package proven solutions to recurring d...

Uncovering the Benefits and Challenges of Continuous Integration Practices | IEEE Journals & Magazine | IEEE Xplore

UNCOVERING THE BENEFITS AND CHALLENGES OF CONTINUOUS INTEGRATION PRACTICES Publisher: IEEE Abstract Authors References Citations Keywords Metrics More Like This ABSTRACT: In 2006, Fowler an...

A Grounded Theory of Coordination in Remote-First and Hybrid Software Teams | IEEE Conference Publication | IEEE Xplore

A GROUNDED THEORY OF COORDINATION IN REMOTE-FIRST AND HYBRID SOFTWARE TEAMS Publisher: IEEE ABSTRACT: While the long-term effects of the COVID-19 pandemic on software professionals and organizatio...

[ssrn.com ssrn.com](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7036116)  

SOFTWARE MAINTAINABILITY: A COMPARATIVE STUDY BETWEEN LOW-CODE PLATFORMS AND TRADITIONAL FRAMEWORKS by Anastasios Chrysochoidis, Alexander Chatzigeorgiou, Apostolos Ampatzoglou :: SSRN

Download This Paper Open PDF in Browser SOFTWARE MAINTAINABILITY: A COMPARATIVE STUDY BETWEEN LOW-CODE PLATFORMS AND TRADITIONAL FRAMEWORKS 24 Pages Posted: 1 Jul 2026 See all articles by Anasta...

[china.com china.com](https://tech.china.com/article/20240903/092024_1570614.html)  

对话 IDC：一文带你了解低代码的技术趋势和平台选型\_中华网

对话 IDC：一文带你了解低代码的技术趋势和平台选型 对话 IDC：一文带你了解低代码的技术趋势和平台选型 2024-09-03 15:07:55 来源：看点时报 小 大 军事APP头条APP 近日，葡萄城的活字格企业级低代码开发平台入选《中国低代码开发平台技术评估，2024》技术代表厂商，并在可视化开发、集成能力、开放性和兼容性以及生态能力维度获得五星评价。这一荣誉见证了葡萄城在低代...

对话 IDC：一文带你了解低代码的技术趋势和平台选型\_中华网

高级分析师： 好的，目前低代码市场的发展情况可以从以下几个方面来看： 1）市场份额和市场空间的增长 首先，企业数字化转型正迅速发展成为一个重要趋势。在数字化进程中，企业业务数字化需求与 IT 供给之间的矛盾显著。因此，我们（IDC）观察到低代码平台正得到广泛采用。根据数据显示，2023 年，中国低代码与零代码市场规模约为 34 亿人民币，同比增长 31%。预计到 2027 年，市场规模将达到...

[utupub.fi utupub.fi](https://www.utupub.fi/items/3cf13bb3-6171-4aff-8045-11f50ecdc901/full)  

AI-Assisted and Low-Code Development in Practice: A Case Study of SocialMize on Developer Productivity, Code Quality, and Perceived Trust and Usability

AI-ASSISTED AND LOW-CODE DEVELOPMENT IN PRACTICE: A CASE STUDY OF SOCIALMIZE ON DEVELOPER PRODUCTIVITY, CODE QUALITY, AND PERCEIVED TRUST AND USABILITY dc.contributor.author | Uddin, Rafi | dc.con...

[kingdee.com kingdee.com](https://www.kingdee.com/resources/articles/1407059441823530977)  

金蝶五连冠！2024年中国低零代码软件市场排名出炉 - 金蝶软件官网

资源中心/金蝶五连冠！2024年中国低零代码软件市场排名出炉 金蝶AI苍穹数字化转型低代码开发 金蝶五连冠！2024年中国低零代码软件市场排名出炉 近日，国际数据公司IDC发布了《2024下半年中国低代码与零代码软件市场跟踪报告》（以下简称“报告”）。 2025-08-18 747 Image: 金蝶五连冠！2024年中国低零代码软件市场排名出炉 近日，国际数据公司IDC发布了《2...

aPaaS冠军！IDC：金蝶连续多年低零代码中国市场第一-金蝶官网

aPaaS冠军！IDC：金蝶连续多年低零代码中国市场第一 APAAS冠军！IDC：金蝶连续多年低零代码中国市场第一 2025/06/19 近日，国际数据公司IDC发布了《中国低代码和零代码软件市场跟踪研究报告（2024H1）》(PRC Low Code and No Code Software Market Tracker, 2024H1）。数据显示，金蝶在低代码和零代码的中国市场占有率蝉...

[ou.nl ou.nl](https://research.ou.nl/en/studentTheses/challenges-development-teams-face-in-low-code-development-process/)  

Challenges Development Teams Face in Low-code Development Process - Open Universiteit research portal

Challenges Development Teams Face in Low-code Development Process \* Z. Alyousef Student thesis: Master's Thesis ABSTRACT The low code programming paradigm has increased in popularity during the l...

[aliyun.com aliyun.com](https://developer.aliyun.com/article/1158294)  

OneCode开源低代码引擎白皮书-阿里云开发者社区

ONECODE开源低代码引擎白皮书 2023-02-11 1575 版权 版权声明： 本文内容由阿里云实名注册用户自发贡献，版权归原作者所有，阿里云开发者社区不拥有其著作权，亦不承担相应法律责任。具体规则请查看《 阿里云开发者社区用户服务协议》和 《阿里云开发者社区知识产权保护指引》。如果您发现本社区中有涉嫌抄袭的内容，填写 侵权投诉表单进行举报，一经查实，本社区将立刻删除涉嫌侵权内容。...

喜报！蓝凌连续两年上榜低代码企业TOP50

喜报！蓝凌连续两年上榜低代码企业TOP50 &gt; &gt; 喜报！蓝凌连续两年上榜低代码企业TOP50 蓝凌OA办公系统 2023-12-28 15:48:08 1775 蓝凌低代码xAI，让业务场景更智能更简单 近日，中国科学院主管、科学出版社主办的国家级核心期刊《互联网周刊》评选的《2023年度低代码企业TOP50》榜单正式公布。本次榜单从产品能力、用户口碑、市场占有率等多维度出发，对20...

2023温暖上云-生态权益会场

优秀伙伴 集合优质伙伴资源，全面助力创企成长 夺冠互动 河南夺冠互动网络科技有限公司成立于2015年，是国内首批小程序技术服务商，公司致力于运用小程序产品技术，为商家和企业提供“互联网营销+数字化经营”的一体化商业解决方案。 点赞热度：31800 已结束立即查看 蓝凌智能 深圳市蓝凌软件股份有限公司，生态OA引领者、数字化办公专家、深圳500强企业，为各类组织提供协同办公、PaaS...

赋能企业数字化转型 低代码创新创业潮起

赋能企业数字化转型 低代码创新创业潮起 &gt; &gt; 赋能企业数字化转型 低代码创新创业潮起 典名科技 2023-11-03 00:00:00 1587 一所从农田和废墟中诞生的小学，借助低代码开发，成为教育部评选的智慧教育优秀案例；短短两年，一家低代码服务商全年营收迅速翻了三番…… 记者了解到，低代码技术的不断创新和普及，正在加速数字化转型步伐。通过低代码开发，越来越多的企业实现降本增效，进...

2023年低碳科技白皮书——数字技术应用

2023年低碳科技白皮书——数字技术应用 &gt; &gt; 2023年低碳科技白皮书——数字技术应用 阿里云创新中心&前瞻产业研究院 2023-10-23 00:00:00 2342 阿里云创新中心及前瞻产业研究院推出《2023年低碳科技白皮书——数字技术应用》，助力“碳中和”产业绿色转型。 &gt; 关键词：能源，低碳科技 &gt; 创作者：阿里云创新中心&前瞻产业研究院 &gt; 发布日期：2022年10...

世界人工智能大会—阿里云主题论坛—以模型为中心的AI开发新范式

大会直播 大会议程 邀请好友 资料下载 大会直播 大会议程 MaaS：以模型为中心的AI开发新范式 7月7日14:00-16:30 日期 话题名称 嘉宾姓名 嘉宾职务 14:00-14:10 领导致辞 14:10-14:25 MaaS：以模型为中心的AI开发新范式 周靖人 阿里云首席技术官 14:25-14:45 Building RedPajama 张策...

钉钉总体经济影响™研究报告

钉钉总体经济影响™研究报告 &gt; &gt; 钉钉总体经济影响™研究报告 阿里云创新中心 2023-07-26 00:00:00 117587 Forrester 携手阿里云发布钉钉总体经济影响™研究报告，本白皮书聚焦数字化生产力工具市场趋势洞察与商业案例分析。调研显示，在数字化转型过程中，企业战略关注点是多方面的。其中最为关注的因素是提升企业运营效率。 &gt; 关键词：数字中国 &gt; 创作者：Fo...

云原生：新生产力的飞跃

云原生：新生产力的飞跃 &gt; &gt; 云原生：新生产力的飞跃 阿里云创新中心 2023-07-17 17:15:05 1817 企业如何通过云原生架构实现数字原生的飞跃？全社会数字化创新进程如何加速？阿里研究院、中国信息通信研究院、阿里云联合发布了云原生产业白皮书《云原生：新生产力的飞跃》 &gt; 关键词：云原生 &gt; 创作者：阿里研究院、中国信息通信研究院、阿里云联合发布 &gt; 发布日期：20...

企业数字化时代：低代码造浪，服务商“淘金”

企业数字化时代：低代码造浪，服务商“淘金” &gt; &gt; 企业数字化时代：低代码造浪，服务商“淘金” 典名科技 2023-11-05 00:00:00 1262 漫长的技术普惠征途中,属于低代码的机会才刚刚开始。 “低代码让我打开了新世界的大门。”从事低代码创业这两年,皓歌坦言让他感到兴奋的,不单单是把这条路跑通了,更重要的,是通过低代码接触到了各行各业的人,并且给他们的业务带来了肉眼可见的...

[cnblogs.com cnblogs.com](https://www.cnblogs.com/awaw/p/18257960)  

万字长文：十大低代码平台安利，2024低代码谁主沉浮 - aw\_wa - 博客园

万字长文：十大低代码平台安利，2024低代码谁主沉浮 低代码、快速开发工具、未来开发的生产力、常用低代码工具特点 低代码赛道持续“火爆”，开源、智能成为低代码演进“催化剂” 全球范围内数字化进程的迅猛推进，为各行业、领域带来巨大冲击，对应用、系统的需求爆炸式增长，这为低代码领域带来了巨大发展机遇，如今低代码作为推动数字化转型、加速创新和提高企业竞争力的关键工具，早已经成为一种趋势。低代码平...

IDC + 魔力象限：低代码市场与技术双维度选型指南 - 迈阿蜜 - 博客园

IDC + 魔力象限：低代码市场与技术双维度选型指南 &gt; 光看排名会被骗，不懂格局选错货。两本权威报告，一套选型逻辑，帮你避开低代码赛道那些看不到的坑。 “低代码不是技术问题，是格局问题。” 这句话是一个做技术选型的朋友跟我说的。他自己在两家公司踩过低代码的坑，教训很直接：第一次，光看名气选了某大厂平台，落地半年发现架构太臃肿，一个简单需求要绕好几层；第二次，被某个圈钱跑路的小平台...

2023年的低代码：数字化、人工智能、趋势及未来展望 - 葡萄城技术团队 - 博客园

\* \* \* \* \* \* # 2023年的低代码：数字化、人工智能、趋势及未来展望 &gt; 本文由葡萄城技术团队发布。转载请注明出处：葡萄城官网，葡萄城为开发者提供专业的开发工具、解决方案和服务，赋能开发者。 前言 正如许多专家预测的那样，低代码平台在2023年将展现更加强劲的势头。越来越多的企业正在纷纷转向低代码开发，他们希望能够快速开发内部应用程序，并在经济衰退可能出现的...

低代码技术与市场（Mendix与 OutSystems） - 吴建明wujianming - 博客园

微信视频号：sph0RgSyDYV47z6 快手号：4874645212 抖音号：dy0so323fq2w 小红书号：95619019828 B站1：UID:3546863642871878 B站2：UID: 3546955410049087 知乎1：https://www.zhihu.com/people/wujianming\_110117 知乎2：https://www.zhihu.com/p...

[rcaap.pt rcaap.pt](https://www.rcaap.pt/detail.jsp?id=oai%3Arepositorium.uminho.pt%3A1822%2F88695)  

RCAAP - Low-code development productivity

DOCUMENT DETAILS LOW-CODE DEVELOPMENT PRODUCTIVITY Author(s): Varajão, João ; Trigo, António ; Almeida, Miguel Date: 2023 Persistent ID: https://hdl.handle.net/1822/88695 Origin: RepositóriUM -...

[colab.ws colab.ws](https://colab.ws/articles/10.1109%2Ftr.2023.3295009)  

What's Wrong With Low-Code Development Platforms? An Empirical Study of Low-Code Development Platform Bugs | CoLab

, том 73 , издание 1 , страницы 695-709 WHAT'S WRONG WITH LOW-CODE DEVELOPMENT PLATFORMS? AN EMPIRICAL STUDY OF LOW-CODE DEVELOPMENT PLATFORM BUGS Тип публикации: Journal Article Дата публикаци...

[kingdee.com.hk kingdee.com.hk](https://www.kingdee.com.hk/news/kdnews/13283/)  

PaaS中國市場持續領先！ 金蝶再獲IDC低零代碼第一 - 金蝶

PAAS中國市場持續領先！ 金蝶再獲IDC低零代碼第一 \* 2024-05-10 近日，國際數據公司IDC最新發布《PRC Low Code and No Code Software Market Tracker, 2023H1》報告顯示，金蝶憑藉金蝶雲·蒼穹在中國低代碼與零代碼軟體市場佔有率第一！ 這是繼2020、2021、2022年登頂中國低零代碼市場之後，金蝶再次摘得此領域的2023年...

[amazon.in amazon.in](https://www.amazon.in/hz/contact-us)  

Contact Us - Amazon.in

https://www.amazon.in/hz/contact-us

[fazenda.gov.br fazenda.gov.br](https://normas.receita.fazenda.gov.br/sijut2consulta/link.action?idato=138279)  

Instrução Normativa - Normas - Receita Federal

https://normas.receita.fazenda.gov.br/sijut2consulta/link.action?idato=138279

[scopus.com scopus.com](https://www.scopus.com/sources.uri?origin=searchbasic&zone=TopNavBar)  

Scopus Indexed Journals

https://www.scopus.com/sources.uri?origin=searchbasic&zone=TopNavBar

Connector sources scanned

No connector sources scanned

## 公开 Activity（页面顺序）

Research activity

Planning a Chinese low-code research report

I’m preparing a deeply researched report in Chinese covering 2019–2026, while preserving the user’s requested sections, citations, and major-source coverage. I’m gathering evidence from analyst firms such as Gartner, Forrester, and IDC, alongside academic research, white papers, enterprise case studies, platform documentation, community discussions, and productivity or cost studies. I’ll also verify key market figures and forecasts rather than relying on unsupported summaries.

Searching 4 websites

[Open source tei.forrester.com](https://tei.forrester.com/go/microsoft/powerappstei/?lang=en-us)  
[Open source www.gartner.com](https://www.gartner.com/en/documents/7987137)  
[Open source www.forrester.com](https://www.forrester.com/blogs/the-low-code-market-could-approach-50-billion-by-2028/)  
[Open source www.idc.com](https://www.idc.com/resource-center/blog/cloud-native-app-delivery-progress-is-made-but-optimization-is-hard/)  

Searching

[Open source www.gartner.com](https://www.gartner.com/en/documents/7146430)  
[Open source kissflow.com](https://kissflow.com/low-code/gartner-forecasts-on-low-code-development-market/)  
[Open source ninox.com](https://ninox.com/en/resources/blog/gartner-called-it-low-code-is-eating-software-development)  
[Open source www.facebook.com](https://www.facebook.com/NATEKworkITwithUS/posts/gartner-predicts-70-of-new-applications-will-be-built-with-low-codeno-code-techn/1351434623693206/)  
[Open source www.appbuilder.dev](https://www.appbuilder.dev/low-code-statistics/)  
[Open source blog.tooljet.com](https://blog.tooljet.com/gartner-forecast-on-low-code-development-technologies/)  
[Open source www.grandviewresearch.com](https://www.grandviewresearch.com/industry-analysis/low-code-application-development-platform-market)  
[Open source www.quandarycg.com](https://www.quandarycg.com/low-code-statistics)  
[Open source searchlab.nl](https://searchlab.nl/en/statistics/no-code-low-code-statistics-2026)  
[Open source www.reuters.com](https://www.reuters.com/technology/salesforce-challenger-creatio-raises-200-mln-becomes-unicorn-2024-06-26/)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Microsoft_Power_Fx)  
[Open source www.wsj.com](https://www.wsj.com/articles/marketing-budgets-as-a-share-of-revenue-fall-to-postpandemic-low-30d11fa1)  
[Open source www.expresscomputer.in](https://www.expresscomputer.in/news/gartner-says-ai-optimised-iaas-spending-to-reach-42-billion-in-2026/137564/)  
[Open source www.itpro.com](https://www.itpro.com/business/business-strategy/ai-investment-increase-2026-gartner)  

Searching

[Open source www.gartner.com](https://www.gartner.com/en/documents/7146430)  
[Open source kissflow.com](https://kissflow.com/low-code/gartner-forecasts-on-low-code-development-market/)  
[Open source ninox.com](https://ninox.com/en/resources/blog/gartner-called-it-low-code-is-eating-software-development)  
[Open source www.facebook.com](https://www.facebook.com/NATEKworkITwithUS/posts/gartner-predicts-70-of-new-applications-will-be-built-with-low-codeno-code-techn/1351434623693206/)  
[Open source www.appbuilder.dev](https://www.appbuilder.dev/low-code-statistics/)  
[Open source blog.tooljet.com](https://blog.tooljet.com/gartner-forecast-on-low-code-development-technologies/)  
[Open source www.grandviewresearch.com](https://www.grandviewresearch.com/industry-analysis/low-code-application-development-platform-market)  
[Open source www.quandarycg.com](https://www.quandarycg.com/low-code-statistics)  
[Open source searchlab.nl](https://searchlab.nl/en/statistics/no-code-low-code-statistics-2026)  
[Open source www.reuters.com](https://www.reuters.com/technology/salesforce-challenger-creatio-raises-200-mln-becomes-unicorn-2024-06-26/)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Microsoft_Power_Fx)  
[Open source www.wsj.com](https://www.wsj.com/articles/marketing-budgets-as-a-share-of-revenue-fall-to-postpandemic-low-30d11fa1)  
[Open source www.expresscomputer.in](https://www.expresscomputer.in/news/gartner-says-ai-optimised-iaas-spending-to-reach-42-billion-in-2026/137564/)  

Searching

[Open source link.springer.com](https://link.springer.com/article/10.1007/s10270-021-00964-0)  
[Open source ieeexplore.ieee.org](https://ieeexplore.ieee.org/document/10795358/)  

Searching

[Open source www.computer.org](https://www.computer.org/publications/tech-news/research/low-code-vs-code)  
[Open source iscsitr.org](https://iscsitr.org/index.php/ISCSITR-IJIT/article/view/ISCSITR-IJIT_2025_01_01_003)  
[Open source www.gartner.com](https://www.gartner.com/en/documents/7378730)  
[Open source github.com](https://github.com/tillguthardt/Low-code-vs.-the-developer)  
[Open source doi.org](https://doi.org/10.1145/3786791)  

Searching

[Open source www.researchgate.net](https://www.researchgate.net/publication/376017565_Low-code_Development_Productivity_Is_winter_coming_for_code-based_technologies)  
[Open source www.computer.org](https://www.computer.org/publications/tech-news/research/low-code-vs-code)  
[Open source www.outsystems.com](https://www.outsystems.com/low-code)  
[Open source arxiv.org](https://arxiv.org/pdf/2402.01156)  
[Open source queue.acm.org](https://queue.acm.org/doi/full/10.1145/3631183)  
[Open source ijsred.com](https://ijsred.com/volume8/issue5/IJSRED-V8I5P282.pdf)  
[Open source www.semanticscholar.org](https://www.semanticscholar.org/paper/Low-Code-Versus-Code-Based-Software-Development%3A-Trigo-Varaj%C3%A3o/0e04d7ba43d68098800636ce40cfb5d986419183)  
[Open source www.academia.edu](https://www.academia.edu/106193373/Low_Code_Versus_Code_Based_Software_Development_Which_Wins_the_Productivity_Game)  
[Open source link.springer.com](https://link.springer.com/article/10.1007/s10270-025-01308-y)  
[Open source www.devoteam.com](https://www.devoteam.com/expert-view/outsystems-impact-on-developers/)  
[Open source news.ycombinator.com](https://news.ycombinator.com/item?id=46767440)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=tsGQ86xKc3o)  
[Open source www.mdpi.com](https://www.mdpi.com/2076-3417/12/19/9556)  
[Open source dl.acm.org](https://dl.acm.org/doi/pdf/10.1145/3783862.3783880)  
[Open source ceur-ws.org](https://ceur-ws.org/Vol-3113/paper12.pdf)  
[Open source www.reddit.com](https://www.reddit.com/r/ExperiencedDevs/comments/18bs1n9/what_technology_or_approach_seems_easy_to_start/)  
[Open source pt.wikipedia.org](https://pt.wikipedia.org/wiki/OutSystems)  
[Open source fr.wikipedia.org](https://fr.wikipedia.org/wiki/OutSystems)  

Searching

[Open source www.researchgate.net](https://www.researchgate.net/publication/376017565_Low-code_Development_Productivity_Is_winter_coming_for_code-based_technologies)  
[Open source www.computer.org](https://www.computer.org/publications/tech-news/research/low-code-vs-code)  
[Open source www.outsystems.com](https://www.outsystems.com/low-code)  
[Open source arxiv.org](https://arxiv.org/pdf/2402.01156)  
[Open source queue.acm.org](https://queue.acm.org/doi/full/10.1145/3631183)  
[Open source ijsred.com](https://ijsred.com/volume8/issue5/IJSRED-V8I5P282.pdf)  
[Open source www.semanticscholar.org](https://www.semanticscholar.org/paper/Low-Code-Versus-Code-Based-Software-Development%3A-Trigo-Varaj%C3%A3o/0e04d7ba43d68098800636ce40cfb5d986419183)  
[Open source www.academia.edu](https://www.academia.edu/106193373/Low_Code_Versus_Code_Based_Software_Development_Which_Wins_the_Productivity_Game)  
[Open source link.springer.com](https://link.springer.com/article/10.1007/s10270-025-01308-y)  
[Open source www.devoteam.com](https://www.devoteam.com/expert-view/outsystems-impact-on-developers/)  
[Open source news.ycombinator.com](https://news.ycombinator.com/item?id=46767440)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=tsGQ86xKc3o)  
[Open source www.mdpi.com](https://www.mdpi.com/2076-3417/12/19/9556)  
[Open source dl.acm.org](https://dl.acm.org/doi/pdf/10.1145/3783862.3783880)  
[Open source ceur-ws.org](https://ceur-ws.org/Vol-3113/paper12.pdf)  
[Open source www.reddit.com](https://www.reddit.com/r/ExperiencedDevs/comments/18bs1n9/what_technology_or_approach_seems_easy_to_start/)  

Searching

[Open source doi.org](https://doi.org/10.1365/s40702-024-01107-x?urlappend=%3Futm_source%3Dresearchgate.net%26utm_medium%3Darticle)  
[Open source www.researchgate.net](https://www.researchgate.net/publication/365873896_Low-Code_Versus_Code-Based_Software_Development_Which_Wins_the_Productivity_Game)  
[Open source ieeexplore.ieee.org](https://ieeexplore.ieee.org/document/9967415/)  
[Open source www.computer.org](https://www.computer.org/csdl/magazine/it/2022/05/09967415/1IIYACGLXnq)  
[Open source www.academia.edu](https://www.academia.edu/106193373/Low_Code_Versus_Code_Based_Software_Development_Which_Wins_the_Productivity_Game)  
[Open source www.semanticscholar.org](https://www.semanticscholar.org/paper/Low-Code-Versus-Code-Based-Software-Development%3A-Trigo-Varaj%C3%A3o/0e04d7ba43d68098800636ce40cfb5d986419183)  
[Open source queue.acm.org](https://queue.acm.org/detail.cfm?id=3631183)  
[Open source ciencia.iscte-iul.pt](https://ciencia.iscte-iul.pt/publications/low-code-versus-code-based-software-development-which-wins-the-productivity-game/105359?lang=en)  
[Open source portaberta.uminho.pt](https://portaberta.uminho.pt/display/cv-t-793216001dcb3e6a9caa0b2db8c82c4e)  
[Open source www.sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S0164121226001263)  

Searching

[Open source doi.org](https://doi.org/10.1365/s40702-024-01107-x?urlappend=%3Futm_source%3Dresearchgate.net%26utm_medium%3Darticle)  
[Open source www.researchgate.net](https://www.researchgate.net/publication/365873896_Low-Code_Versus_Code-Based_Software_Development_Which_Wins_the_Productivity_Game)  
[Open source ieeexplore.ieee.org](https://ieeexplore.ieee.org/document/9967415/)  
[Open source www.computer.org](https://www.computer.org/csdl/magazine/it/2022/05/09967415/1IIYACGLXnq)  
[Open source www.academia.edu](https://www.academia.edu/106193373/Low_Code_Versus_Code_Based_Software_Development_Which_Wins_the_Productivity_Game)  
[Open source www.semanticscholar.org](https://www.semanticscholar.org/paper/Low-Code-Versus-Code-Based-Software-Development%3A-Trigo-Varaj%C3%A3o/0e04d7ba43d68098800636ce40cfb5d986419183)  
[Open source queue.acm.org](https://queue.acm.org/detail.cfm?id=3631183)  
[Open source ciencia.iscte-iul.pt](https://ciencia.iscte-iul.pt/publications/low-code-versus-code-based-software-development-which-wins-the-productivity-game/105359?lang=en)  
[Open source portaberta.uminho.pt](https://portaberta.uminho.pt/display/cv-t-793216001dcb3e6a9caa0b2db8c82c4e)  

Searching

[Open source www.youtube.com](https://www.youtube.com/watch?v=F5WA26W4JaM)  
[Open source ieeexplore.ieee.org](https://ieeexplore.ieee.org/document/7803544/)  
[Open source www.efpia.eu](https://www.efpia.eu/relationships-code/)  
[Open source www.instagram.com](https://www.instagram.com/reel/DdEuqbkCjmT/)  
[Open source community.intersystems.com](https://community.intersystems.com/post/video-iris-ai-studio-detailed-functionality-code-walkthrough)  
[Open source uk.linkedin.com](https://uk.linkedin.com/in/drew-spencer)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Perspective_%28graphical%29)  
[Open source www.linkedin.com](https://www.linkedin.com/posts/meetsteveharris_%F0%9D%97%A6%F0%9D%98%82%F0%9D%97%BB%F0%9D%97%B1%F0%9D%97%AE%F0%9D%98%86-%F0%9D%97%96%F0%9D%97%BC%F0%9D%97%B3%F0%9D%97%B3%F0%9D%97%B2%F0%9D%97%B2-%F0%9D%97%96%F0%9D%97%BC%F0%9D%97%B1%F0%9D%97%B2-%F0%9D%97%A7%F0%9D%97%B2%F0%9D%97%AE%F0%9D%97%B0%F0%9D%97%B5%F0%9D%97%B6%F0%9D%97%BB%F0%9D%97%B4-activity-7499918362731474944-e_9z)  
[Open source www.chiefdelphi.com](https://www.chiefdelphi.com/t/1778-2026-cad-code-release/521825)  

Searching

[Open source www.youtube.com](https://www.youtube.com/watch?v=F5WA26W4JaM)  
[Open source ieeexplore.ieee.org](https://ieeexplore.ieee.org/document/7803544/)  
[Open source www.efpia.eu](https://www.efpia.eu/relationships-code/)  
[Open source www.instagram.com](https://www.instagram.com/reel/DdEuqbkCjmT/)  
[Open source community.intersystems.com](https://community.intersystems.com/post/video-iris-ai-studio-detailed-functionality-code-walkthrough)  
[Open source uk.linkedin.com](https://uk.linkedin.com/in/drew-spencer)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Perspective_%28graphical%29)  
[Open source www.linkedin.com](https://www.linkedin.com/posts/meetsteveharris_%F0%9D%97%A6%F0%9D%98%82%F0%9D%97%BB%F0%9D%97%B1%F0%9D%97%AE%F0%9D%98%86-%F0%9D%97%96%F0%9D%97%BC%F0%9D%97%B3%F0%9D%97%B3%F0%9D%97%B2%F0%9D%97%B2-%F0%9D%97%96%F0%9D%97%BC%F0%9D%97%B1%F0%9D%97%B2-%F0%9D%97%A7%F0%9D%97%B2%F0%9D%97%AE%F0%9D%97%B0%F0%9D%97%B5%F0%9D%97%B6%F0%9D%97%BB%F0%9D%97%B4-activity-7499918362731474944-e_9z)  

Searching

[Open source arxiv.org](https://arxiv.org/abs/2107.07482)  
[Open source ieeexplore.ieee.org](https://ieeexplore.ieee.org/document/10075454/)  
[Open source www.researchgate.net](https://www.researchgate.net/publication/347478419_Challenges_opportunities_in_low-code_testing)  
[Open source dl.acm.org](https://dl.acm.org/doi/10.1145/3475716.3475782)  
[Open source www.semanticscholar.org](https://www.semanticscholar.org/paper/Practitioners%E2%80%99-Perceptions-on-the-Adoption-of-Low-K%C3%A4ss-Strahringer/975be5b7461efc7f751438b136a882e079720df2)  
[Open source hal.science](https://hal.science/hal-02946812)  
[Open source opus4.kobv.de](https://opus4.kobv.de/opus4-oth-regensburg/frontdoor/deliver/index/docId/5917/file/Kaess_Strahringer_Westner_Practitioners.pdf)  
[Open source www.scribd.com](https://www.scribd.com/document/819360919/Challenges-opportunities-in-low-code-testing)  
[Open source www.sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S0164121226001263)  
[Open source faezeh-kh.github.io](https://faezeh-kh.github.io/uploads/lowcode_presentation.pdf)  
[Open source www.mdpi.com](https://www.mdpi.com/2673-4591/104/1/15)  
[Open source www.computer.org](https://www.computer.org/csdl/magazine/co/2025/03/10896927/24uGETds2Vq)  
[Open source www.ekonbiz.ues.rs.ba](https://www.ekonbiz.ues.rs.ba/ojs/article/view/330.html)  
[Open source pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC9643911/)  
[Open source www.academia.edu](https://www.academia.edu/164467828/The_Rise_of_Low_Code_No_Code_Software_Development_Models_Trends_and_Tools_by)  
[Open source ouci.dntb.gov.ua](https://ouci.dntb.gov.ua/en/works/7XavqEyr/)  
[Open source www.diva-portal.org](https://www.diva-portal.org/smash/get/diva2%3A1736580/FULLTEXT01.pdf)  
[Open source zendy.io](https://zendy.io/pdf-viewer/PROCART-472100056)  
[Open source exaly.com](https://exaly.com/article/161563529)  
[Open source ae.ef.unibl.org](https://ae.ef.unibl.org/index.php/ae/article/view/582)  
[Open source scholar.google.com](https://scholar.google.com/citations?hl=en&user=MyCkzOUAAAAJ)  

Searching

[Open source arxiv.org](https://arxiv.org/abs/2107.07482)  
[Open source ieeexplore.ieee.org](https://ieeexplore.ieee.org/document/10075454/)  
[Open source www.researchgate.net](https://www.researchgate.net/publication/347478419_Challenges_opportunities_in_low-code_testing)  
[Open source dl.acm.org](https://dl.acm.org/doi/10.1145/3475716.3475782)  
[Open source www.semanticscholar.org](https://www.semanticscholar.org/paper/Practitioners%E2%80%99-Perceptions-on-the-Adoption-of-Low-K%C3%A4ss-Strahringer/975be5b7461efc7f751438b136a882e079720df2)  
[Open source hal.science](https://hal.science/hal-02946812)  
[Open source opus4.kobv.de](https://opus4.kobv.de/opus4-oth-regensburg/frontdoor/deliver/index/docId/5917/file/Kaess_Strahringer_Westner_Practitioners.pdf)  
[Open source www.scribd.com](https://www.scribd.com/document/819360919/Challenges-opportunities-in-low-code-testing)  
[Open source www.sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S0164121226001263)  
[Open source faezeh-kh.github.io](https://faezeh-kh.github.io/uploads/lowcode_presentation.pdf)  
[Open source www.mdpi.com](https://www.mdpi.com/2673-4591/104/1/15)  
[Open source www.computer.org](https://www.computer.org/csdl/magazine/co/2025/03/10896927/24uGETds2Vq)  
[Open source www.ekonbiz.ues.rs.ba](https://www.ekonbiz.ues.rs.ba/ojs/article/view/330.html)  
[Open source pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC9643911/)  
[Open source www.academia.edu](https://www.academia.edu/164467828/The_Rise_of_Low_Code_No_Code_Software_Development_Models_Trends_and_Tools_by)  
[Open source ouci.dntb.gov.ua](https://ouci.dntb.gov.ua/en/works/7XavqEyr/)  
[Open source www.diva-portal.org](https://www.diva-portal.org/smash/get/diva2%3A1736580/FULLTEXT01.pdf)  
[Open source zendy.io](https://zendy.io/pdf-viewer/PROCART-472100056)  
[Open source exaly.com](https://exaly.com/article/161563529)  
[Open source ae.ef.unibl.org](https://ae.ef.unibl.org/index.php/ae/article/view/582)  

Searching

[Open source ieeexplore.ieee.org](https://ieeexplore.ieee.org/document/10075454/)  
[Open source arxiv.org](https://arxiv.org/html/2107.07482v1)  

Searching

[Open source docs.mendix.com](https://docs.mendix.com/developerportal/deploy/)  
[Open source learn.microsoft.com](https://learn.microsoft.com/en-us/power-platform/alm/overview-alm)  

Searching

[Open source success.outsystems.com](https://success.outsystems.com/documentation/11/monitoring_and_troubleshooting_apps/)  
[Open source www.epa.gov](https://www.epa.gov/ghgemissions/sources-greenhouse-gas-emissions)  
[Open source www.facebook.com](https://www.facebook.com/gracedaviesofficial/videos/my-debut-album-the-wrong-side-of-25-is-out-at-midnight-what-a-surreal-feeling-iv/661610833580651/)  
[Open source docs.appian.com](https://docs.appian.com/suite/help/26.8/appian-recommendations.html)  
[Open source apps.apple.com](https://apps.apple.com/us/app/threads/id6446901002)  
[Open source hmiprisons.justiceinspectorates.gov.uk](https://hmiprisons.justiceinspectorates.gov.uk/hmipris_reports/children-in-custody-2024-25/)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=yTnWP09K5WU)  
[Open source www.seattleschools.org](https://www.seattleschools.org/student-portal/technology-supports-for-families/source/)  
[Open source www.instagram.com](https://www.instagram.com/kimkardashian/?hl=en)  
[Open source www.reddit.com](https://www.reddit.com/)  
[Open source source-ev.com](https://source-ev.com/)  
[Open source gdpr-info.eu](https://gdpr-info.eu/art-25-gdpr/)  
[Open source sourceoutdoor.com](https://sourceoutdoor.com/?srsltid=AfmBOorI07kEZ97Pa9eH_GJewX5LVcAewa_0s8fsyxf28Q7q2thlx490)  

Searching

[Open source success.outsystems.com](https://success.outsystems.com/documentation/11/monitoring_and_troubleshooting_apps/)  
[Open source www.epa.gov](https://www.epa.gov/ghgemissions/sources-greenhouse-gas-emissions)  
[Open source www.facebook.com](https://www.facebook.com/gracedaviesofficial/videos/my-debut-album-the-wrong-side-of-25-is-out-at-midnight-what-a-surreal-feeling-iv/661610833580651/)  
[Open source docs.appian.com](https://docs.appian.com/suite/help/26.8/appian-recommendations.html)  
[Open source apps.apple.com](https://apps.apple.com/us/app/threads/id6446901002)  
[Open source hmiprisons.justiceinspectorates.gov.uk](https://hmiprisons.justiceinspectorates.gov.uk/hmipris_reports/children-in-custody-2024-25/)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=yTnWP09K5WU)  
[Open source www.seattleschools.org](https://www.seattleschools.org/student-portal/technology-supports-for-families/source/)  
[Open source www.instagram.com](https://www.instagram.com/kimkardashian/?hl=en)  
[Open source www.reddit.com](https://www.reddit.com/)  
[Open source source-ev.com](https://source-ev.com/)  
[Open source gdpr-info.eu](https://gdpr-info.eu/art-25-gdpr/)  

Searching

[Open source docs.retool.com](https://docs.retool.com/)  

Searching

[Open source docs.retool.com](https://docs.retool.com/source-control/)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=F_9PnhbCcUM)  
[Open source www.nhs.uk](https://www.nhs.uk/tests-and-treatments/covid-19-rapid-lateral-flow-test/)  
[Open source michaelfeathers.silvrback.com](https://michaelfeathers.silvrback.com/characterization-testing)  

Searching

[Open source www.caict.ac.cn](https://www.caict.ac.cn/kxyj/qwfb/bps/202601/P020260109784447548497.pdf)  
[Open source ndi.caict.ac.cn](https://ndi.caict.ac.cn/)  
[Open source www-file.huawei.com](https://www-file.huawei.com/admin/asset/v1/pro/view/41ff85b1f4314ef7b9a4d38e08aef72d.pdf)  
[Open source gma.caict.ac.cn](https://gma.caict.ac.cn/regulatory/HK)  
[Open source ictp.caict.ac.cn](https://ictp.caict.ac.cn/EN/abstract/abstract1110.shtml)  
[Open source startup.aliyun.com](https://startup.aliyun.com/info/1060983.html)  
[Open source miittc1.caict.ac.cn](https://miittc1.caict.ac.cn/register/)  
[Open source www.huawei.com](https://www.huawei.com/cn/huaweitech/publication/202301/adn-high-level-network-autonomy)  
[Open source aihub.caict.ac.cn](https://aihub.caict.ac.cn/docs/wsAciQ3mgRSY)  
[Open source carrier.huawei.com](https://carrier.huawei.com/~/media/cnbgv2/download/adn/autonomous-driving-network-overview-cn.pdf)  

Searching

[Open source www.idc.com](https://www.idc.com/resource-center/blog/press-release-type/insights/page/144/)  
[Open source tech.china.com](https://tech.china.com/article/20240717/072024_1548738.html)  
[Open source www.reuters.com](https://www.reuters.com/technology/apple-loses-top-spot-china-market-with-shipments-down-66-q1-data-shows-2024-04-25/)  
[Open source www.investopedia.com](https://www.investopedia.com/apple-leads-sales-in-china-smartphone-market-for-first-time-ever-8549724)  
[Open source www.barrons.com](https://www.barrons.com/articles/apple-fourth-smartphone-seller-china-idc-d8cc643a)  

Preparing a rigorous Chinese research report

I’m now assembling the final report in Chinese with a clear opening summary, a small number of analytical sections, citations for sourced claims, and a decision framework. I’m weighing analyst forecasts, academic evidence, vendor studies, enterprise examples, platform documentation, community signals, and cost metrics carefully. I’ll distinguish independent evidence from vendor-sponsored estimates and explicitly flag areas where comparable data is unavailable.

Searching

[Open source www.youtube.com](https://www.youtube.com/watch?v=_wQZYRPWGa8)  
[Open source www.performance.gov](https://www.performance.gov/cx/)  
[Open source customer.io](https://customer.io/)  
[Open source www.instagram.com](https://www.instagram.com/low.carb.love/)  
[Open source www.tripadvisor.com](https://www.tripadvisor.com/Hotel_Feature-g528813-d13120977-zft9179-MOXY_London_Heathrow_Airport.html)  
[Open source www.merriam-webster.com](https://www.merriam-webster.com/dictionary/customer)  
[Open source support.google.com](https://support.google.com/google-ads/answer/6379332?hl=en)  
[Open source www.lowes.com](https://www.lowes.com/)  
[Open source www.ccacoalition.org](https://www.ccacoalition.org/content/low-methane)  
[Open source uk.linkedin.com](https://uk.linkedin.com/in/jenny-mclaughlin-she-her-11935b20)  
[Open source www.federalregister.gov](https://www.federalregister.gov/documents/2026/06/22/2026-12460/permitted-payment-stablecoin-issuer-customer-identification-program)  
[Open source www.heathrow.com](https://www.heathrow.com/at-the-airport/airport-services/fast-track)  
[Open source www.alansparhawk.com](https://www.alansparhawk.com/)  

Searching

[Open source www.youtube.com](https://www.youtube.com/watch?v=_wQZYRPWGa8)  
[Open source www.performance.gov](https://www.performance.gov/cx/)  
[Open source customer.io](https://customer.io/)  
[Open source www.instagram.com](https://www.instagram.com/low.carb.love/)  
[Open source www.tripadvisor.com](https://www.tripadvisor.com/Hotel_Feature-g528813-d13120977-zft9179-MOXY_London_Heathrow_Airport.html)  
[Open source www.merriam-webster.com](https://www.merriam-webster.com/dictionary/customer)  
[Open source support.google.com](https://support.google.com/google-ads/answer/6379332?hl=en)  
[Open source www.lowes.com](https://www.lowes.com/)  
[Open source www.ccacoalition.org](https://www.ccacoalition.org/content/low-methane)  
[Open source uk.linkedin.com](https://uk.linkedin.com/in/jenny-mclaughlin-she-her-11935b20)  
[Open source www.federalregister.gov](https://www.federalregister.gov/documents/2026/06/22/2026-12460/permitted-payment-stablecoin-issuer-customer-identification-program)  

Searching

[Open source www.microsoft.com](https://www.microsoft.com/en/customers/story/766053-heathrow-airport-travel-transportation-power-apps)  
[Open source www.mendix.com](https://www.mendix.com/customer-stories/siemens-energy-promotes-innovation-and-process-efficiency-with-200-low-code-apps/)  
[Open source www.outsystems.com](https://www.outsystems.com/case-studies/dah-chong-hong)  
[Open source ryotokuro.gitbook.io](https://ryotokuro.gitbook.io/microsoft/power-platform/power-platform-fundamentals/introduction-to-power-apps/case-study-heathrow-airport)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=0F24U8tTtgg)  
[Open source futuredotnow.uk](https://futuredotnow.uk/samits-story-heathrow-airport/)  
[Open source info.microsoft.com](https://info.microsoft.com/ww-landing-Turn-Your-Great-Ideas-into-Powerful-Apps.html?lcid=en-us)  
[Open source www.linkedin.com](https://www.linkedin.com/pulse/microsoft-power-platform-bi-powerapps-flow-satya-nadella-panchal)  
[Open source valto.co.uk](https://valto.co.uk/case-studies/city-of-london-case-study/)  
[Open source www.facebook.com](https://www.facebook.com/relianceinfosystems/posts/at-heathrow-airport-one-security-officer-taught-himself-how-to-develop-in-micros/3579686672143841/)  
[Open source data-flair.training](https://data-flair.training/blogs/power-bi-case-study/)  
[Open source www.wired.com](https://www.wired.com/story/microsoft-power-apps-data-exposed)  

Searching

[Open source investors.appian.com](https://investors.appian.com/)  
[Open source www.enterprisecommunity.org](https://www.enterprisecommunity.org/about)  
[Open source academy.appian.com](https://academy.appian.com/)  
[Open source www.dell.com](https://www.dell.com/support/contents/en-us/videos/videoplayer/openmanage-enterprise-offline-console-updates/6381463577112)  
[Open source appmarket.appian.com](https://appmarket.appian.com/listings/aquaman)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=0fKYVl12VTA)  
[Open source appian.com](https://appian.com/demo-request)  
[Open source www.enterprisemobility.com](https://www.enterprisemobility.com/)  
[Open source careers.appian.com](https://careers.appian.com/)  
[Open source martinfowler.com](https://martinfowler.com/books/)  
[Open source entethalliance.org](https://entethalliance.org/)  
[Open source www.coxenterprises.com](https://www.coxenterprises.com/)  

Searching

[Open source investors.appian.com](https://investors.appian.com/)  
[Open source www.enterprisecommunity.org](https://www.enterprisecommunity.org/about)  
[Open source academy.appian.com](https://academy.appian.com/)  
[Open source www.dell.com](https://www.dell.com/support/contents/en-us/videos/videoplayer/openmanage-enterprise-offline-console-updates/6381463577112)  
[Open source appmarket.appian.com](https://appmarket.appian.com/listings/aquaman)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=0fKYVl12VTA)  
[Open source appian.com](https://appian.com/demo-request)  
[Open source www.enterprisemobility.com](https://www.enterprisemobility.com/)  
[Open source careers.appian.com](https://careers.appian.com/)  
[Open source martinfowler.com](https://martinfowler.com/books/)  

Searching

[Open source retool.com](https://retool.com/customers/pump)  

Searching

[Open source appian.com](https://appian.com/about/explore/customers/all-customers/aon)  
[Open source engage.appian.com](https://engage.appian.com/appian-for-insurance)  

Searching

[Open source www.youtube.com](https://www.youtube.com/watch?v=so8V5dAli-Q)  
[Open source store.steampowered.com](https://store.steampowered.com/app/870780/CONTROL_Ultimate_Edition/)  
[Open source www.reddit.com](https://www.reddit.com/r/patientgamers/comments/1gbc8et/control_the_good_the_bad_the_ugly/)  
[Open source www.remedygames.com](https://www.remedygames.com/games/control)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Control_%28video_game%29)  
[Open source www.merriam-webster.com](https://www.merriam-webster.com/dictionary/control)  

Searching

[Open source tei.forrester.com](https://tei.forrester.com/go/microsoft/powerappstei/?lang=en-us)  

Searching

[Open source ieeexplore.ieee.org](https://ieeexplore.ieee.org/document/9967415/)  
[Open source arxiv.org](https://arxiv.org/html/2107.07482v1)  
[Open source link.springer.com](https://link.springer.com/article/10.1007/s10270-021-00964-0)  
[Open source docs.mendix.com](https://docs.mendix.com/refguide10/using-version-control-in-studio-pro/)  

Worked for 8m 5s

Worked for 8m 5s

Done

Searching

[Open source forrester.com](https://tei.forrester.com/go/microsoft/powerappstei/?lang=en-us&utm_source=chatgpt.com)  
[Open source springer.com](https://link.springer.com/article/10.1007/s10270-021-00964-0?utm_source=chatgpt.com)  
[Open source computer.org](https://www.computer.org/publications/tech-news/research/low-code-vs-code?utm_source=chatgpt.com)  
[Open source researchgate.net](https://www.researchgate.net/publication/400810699_Designing_Scalable_Data_Pipelines_with_Low-Code_Platforms?utm_source=chatgpt.com)  
[Open source doi.org](https://doi.org/10.1145/3786791?utm_source=chatgpt.com)  
[Open source youtube.com](https://www.youtube.com/watch?v=tsGQ86xKc3o&utm_source=chatgpt.com)  
[Open source arxiv.org](https://arxiv.org/pdf/2402.01156?utm_source=chatgpt.com)  
[Open source retool.com](https://docs.retool.com/?utm_source=chatgpt.com)  
[Open source caict.ac.cn](https://www.caict.ac.cn/kxyj/qwfb/bps/202601/P020260109784447548497.pdf?utm_source=chatgpt.com)  
[Open source appian.com](https://docs.appian.com/suite/help/26.3/inspect-deployment.html?utm_source=chatgpt.com)  
[Open source kissflow.com](https://kissflow.com/low-code/gartner-forecasts-on-low-code-development-market/?utm_source=chatgpt.com)  
[Open source ieee.org](https://ieeexplore.ieee.org/document/10795358/?utm_source=chatgpt.com)  
[Open source iscsitr.org](https://iscsitr.org/index.php/ISCSITR-IJIT/article/view/ISCSITR-IJIT_2025_01_01_003?utm_source=chatgpt.com)  
[Open source epa.gov](https://www.epa.gov/ghgemissions/sources-greenhouse-gas-emissions?utm_source=chatgpt.com)  
[Open source idc.com](https://www.idc.com/resource-center/blog/cloud-native-app-delivery-progress-is-made-but-optimization-is-hard/?utm_source=chatgpt.com)  
[Open source performance.gov](https://www.performance.gov/cx/?utm_source=chatgpt.com)  
[Open source mendix.com](https://docs.mendix.com/refguide10/using-version-control-in-studio-pro/?utm_source=chatgpt.com)  
[Open source enterprisecommunity.org](https://www.enterprisecommunity.org/about?utm_source=chatgpt.com)  
[Open source steampowered.com](https://store.steampowered.com/app/870780/CONTROL_Ultimate_Edition/?utm_source=chatgpt.com)  
[Open source outsystems.com](https://www.outsystems.com/low-code?utm_source=chatgpt.com)  
[Open source efpia.eu](https://www.efpia.eu/relationships-code/?utm_source=chatgpt.com)  
[Open source facebook.com](https://www.facebook.com/NATEKworkITwithUS/posts/gartner-predicts-70-of-new-applications-will-be-built-with-low-codeno-code-techn/1351434623693206/?utm_source=chatgpt.com)  
[Open source huawei.com](https://www-file.huawei.com/admin/asset/v1/pro/view/41ff85b1f4314ef7b9a4d38e08aef72d.pdf?utm_source=chatgpt.com)  
[Open source reddit.com](https://www.reddit.com/r/ExperiencedDevs/comments/18bs1n9/what_technology_or_approach_seems_easy_to_start/?utm_source=chatgpt.com)  
[Open source ninox.com](https://ninox.com/en/resources/blog/gartner-called-it-low-code-is-eating-software-development?utm_source=chatgpt.com)  
[Open source github.com](https://github.com/tillguthardt/Low-code-vs.-the-developer?utm_source=chatgpt.com)  
[Open source gitbook.io](https://ryotokuro.gitbook.io/microsoft/power-platform/power-platform-fundamentals/introduction-to-power-apps/case-study-heathrow-airport?utm_source=chatgpt.com)  
[Open source dell.com](https://www.dell.com/support/contents/en-us/videos/videoplayer/openmanage-enterprise-offline-console-updates/6381463577112?utm_source=chatgpt.com)  
[Open source acm.org](https://queue.acm.org/doi/full/10.1145/3631183?utm_source=chatgpt.com)  
[Open source remedygames.com](https://www.remedygames.com/games/control?utm_source=chatgpt.com)  
[Open source gartner.com](https://www.gartner.com/en/documents/6130259?utm_source=chatgpt.com)  
[Open source appbuilder.dev](https://www.appbuilder.dev/low-code-statistics/?utm_source=chatgpt.com)  
[Open source ijsred.com](https://ijsred.com/volume8/issue5/IJSRED-V8I5P282.pdf?utm_source=chatgpt.com)  
[Open source apple.com](https://apps.apple.com/us/app/threads/id6446901002?utm_source=chatgpt.com)  
[Open source tooljet.com](https://blog.tooljet.com/gartner-forecast-on-low-code-development-technologies/?utm_source=chatgpt.com)  
[Open source ssrn.com](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7036116&utm_source=chatgpt.com)  
[Open source semanticscholar.org](https://www.semanticscholar.org/paper/Low-Code-Versus-Code-Based-Software-Development%3A-Trigo-Varaj%C3%A3o/0e04d7ba43d68098800636ce40cfb5d986419183?utm_source=chatgpt.com)  
[Open source microsoft.com](https://learn.microsoft.com/en-us/power-platform/alm/git-integration/overview?utm_source=chatgpt.com)  
[Open source justiceinspectorates.gov.uk](https://hmiprisons.justiceinspectorates.gov.uk/hmipris_reports/children-in-custody-2024-25/?utm_source=chatgpt.com)  
[Open source china.com](https://tech.china.com/article/20240717/072024_1548738.html?utm_source=chatgpt.com)  
[Open source grandviewresearch.com](https://www.grandviewresearch.com/industry-analysis/low-code-application-development-platform-market?utm_source=chatgpt.com)  
[Open source utupub.fi](https://www.utupub.fi/items/3cf13bb3-6171-4aff-8045-11f50ecdc901/full?utm_source=chatgpt.com)  
[Open source academia.edu](https://www.academia.edu/106193373/Low_Code_Versus_Code_Based_Software_Development_Which_Wins_the_Productivity_Game?utm_source=chatgpt.com)  
[Open source iscte-iul.pt](https://ciencia.iscte-iul.pt/publications/low-code-versus-code-based-software-development-which-wins-the-productivity-game/105359?lang=en&utm_source=chatgpt.com)  
[Open source www.nhs.uk](https://www.nhs.uk/tests-and-treatments/covid-19-rapid-lateral-flow-test/?utm_source=chatgpt.com)  
[Open source customer.io](https://customer.io/?utm_source=chatgpt.com)  
[Open source wikipedia.org](https://en.wikipedia.org/wiki/Perspective_%28graphical%29?utm_source=chatgpt.com)  
[Open source quandarycg.com](https://www.quandarycg.com/low-code-statistics?utm_source=chatgpt.com)  
[Open source uminho.pt](https://portaberta.uminho.pt/display/cv-t-793216001dcb3e6a9caa0b2db8c82c4e?utm_source=chatgpt.com)  
[Open source kingdee.com](https://www.kingdee.com/resources/articles/1407059441823530977?utm_source=chatgpt.com)  
[Open source searchlab.nl](https://searchlab.nl/en/statistics/no-code-low-code-statistics-2026?utm_source=chatgpt.com)  
[Open source ou.nl](https://research.ou.nl/en/studentTheses/challenges-development-teams-face-in-low-code-development-process/?utm_source=chatgpt.com)  
[Open source devoteam.com](https://www.devoteam.com/expert-view/outsystems-impact-on-developers/?utm_source=chatgpt.com)  
[Open source aliyun.com](https://startup.aliyun.com/info/1060983.html?utm_source=chatgpt.com)  
[Open source futuredotnow.uk](https://futuredotnow.uk/samits-story-heathrow-airport/?utm_source=chatgpt.com)  
[Open source merriam-webster.com](https://www.merriam-webster.com/dictionary/customer?utm_source=chatgpt.com)  
[Open source cnblogs.com](https://www.cnblogs.com/awaw/p/18257960?utm_source=chatgpt.com)  
[Open source sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S0164121226001263?utm_source=chatgpt.com)  
[Open source ycombinator.com](https://news.ycombinator.com/item?id=46767440&utm_source=chatgpt.com)  
[Open source rcaap.pt](https://www.rcaap.pt/detail.jsp?id=oai%3Arepositorium.uminho.pt%3A1822%2F88695&utm_source=chatgpt.com)  
[Open source hal.science](https://hal.science/hal-02946812?utm_source=chatgpt.com)  
[Open source instagram.com](https://www.instagram.com/reel/DdEuqbkCjmT/?utm_source=chatgpt.com)  
[Open source enterprisemobility.com](https://www.enterprisemobility.com/?utm_source=chatgpt.com)  
[Open source colab.ws](https://colab.ws/articles/10.1109%2Ftr.2023.3295009?utm_source=chatgpt.com)  
[Open source mdpi.com](https://www.mdpi.com/2076-3417/15/12/6481?utm_source=chatgpt.com)  
[Open source kobv.de](https://opus4.kobv.de/opus4-oth-regensburg/frontdoor/deliver/index/docId/5917/file/Kaess_Strahringer_Westner_Practitioners.pdf?utm_source=chatgpt.com)  
[Open source tripadvisor.com](https://www.tripadvisor.com/Hotel_Feature-g528813-d13120977-zft9179-MOXY_London_Heathrow_Airport.html?utm_source=chatgpt.com)  
[Open source martinfowler.com](https://martinfowler.com/books/?utm_source=chatgpt.com)  
[Open source ceur-ws.org](https://ceur-ws.org/Vol-3113/paper12.pdf?utm_source=chatgpt.com)  
[Open source scribd.com](https://www.scribd.com/document/819360919/Challenges-opportunities-in-low-code-testing?utm_source=chatgpt.com)  
[Open source linkedin.com](https://uk.linkedin.com/in/drew-spencer?utm_source=chatgpt.com)  
[Open source intersystems.com](https://community.intersystems.com/post/video-iris-ai-studio-detailed-functionality-code-walkthrough?utm_source=chatgpt.com)  
[Open source seattleschools.org](https://www.seattleschools.org/student-portal/technology-supports-for-families/source/?utm_source=chatgpt.com)  
[Open source google.com](https://scholar.google.com/citations?hl=en&user=MyCkzOUAAAAJ&utm_source=chatgpt.com)  
[Open source entethalliance.org](https://entethalliance.org/?utm_source=chatgpt.com)  
[Open source kingdee.com.hk](https://www.kingdee.com.hk/news/kdnews/13283/?utm_source=chatgpt.com)  
[Open source lowes.com](https://www.lowes.com/?utm_source=chatgpt.com)  
[Open source valto.co.uk](https://valto.co.uk/case-studies/city-of-london-case-study/?utm_source=chatgpt.com)  
[Open source faezeh-kh.github.io](https://faezeh-kh.github.io/uploads/lowcode_presentation.pdf?utm_source=chatgpt.com)  
[Open source coxenterprises.com](https://www.coxenterprises.com/?utm_source=chatgpt.com)  
[Open source amazon.in](https://www.amazon.in/hz/contact-us?utm_source=chatgpt.com)  
[Open source ccacoalition.org](https://www.ccacoalition.org/content/low-methane?utm_source=chatgpt.com)  
[Open source ues.rs.ba](https://www.ekonbiz.ues.rs.ba/ojs/article/view/330.html?utm_source=chatgpt.com)  
[Open source federalregister.gov](https://www.federalregister.gov/documents/2026/06/22/2026-12460/permitted-payment-stablecoin-issuer-customer-identification-program?utm_source=chatgpt.com)  
[Open source nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC9643911/?utm_source=chatgpt.com)  
[Open source data-flair.training](https://data-flair.training/blogs/power-bi-case-study/?utm_source=chatgpt.com)  
[Open source heathrow.com](https://www.heathrow.com/at-the-airport/airport-services/fast-track?utm_source=chatgpt.com)  
[Open source chiefdelphi.com](https://www.chiefdelphi.com/t/1778-2026-cad-code-release/521825?utm_source=chatgpt.com)  
[Open source dntb.gov.ua](https://ouci.dntb.gov.ua/en/works/7XavqEyr/?utm_source=chatgpt.com)  
[Open source fazenda.gov.br](https://normas.receita.fazenda.gov.br/sijut2consulta/link.action?idato=138279&utm_source=chatgpt.com)  
[Open source diva-portal.org](https://www.diva-portal.org/smash/get/diva2%3A1736580/FULLTEXT01.pdf?utm_source=chatgpt.com)  
[Open source alansparhawk.com](https://www.alansparhawk.com/?utm_source=chatgpt.com)  
[Open source zendy.io](https://zendy.io/pdf-viewer/PROCART-472100056?utm_source=chatgpt.com)  
[Open source source-ev.com](https://source-ev.com/?utm_source=chatgpt.com)  
[Open source exaly.com](https://exaly.com/article/161563529?utm_source=chatgpt.com)  
[Open source gdpr-info.eu](https://gdpr-info.eu/art-25-gdpr/?utm_source=chatgpt.com)  
[Open source unibl.org](https://ae.ef.unibl.org/index.php/ae/article/view/582?utm_source=chatgpt.com)  
[Open source sourceoutdoor.com](https://sourceoutdoor.com/?srsltid=AfmBOorI07kEZ97Pa9eH_GJewX5LVcAewa_0s8fsyxf28Q7q2thlx490&utm_source=chatgpt.com)  
[Open source silvrback.com](https://michaelfeathers.silvrback.com/characterization-testing?utm_source=chatgpt.com)  
[Open source scopus.com](https://www.scopus.com/sources.uri?origin=searchbasic&zone=TopNavBar&utm_source=chatgpt.com)  

Generated report on 低代码/无代码平台对传统软件开发流程的影响：效率增益、维护成本与适用边界研究

## 原始页面记录

完整原始摘录保存在[同名 HTML 档案](html/gpt-17.html)末尾的折叠附录中。Markdown 为便于检索的正文版，未重复嵌入原始结构。
