[← 二十份研究目录](README.md)

# ChatGPT · ID 28 · 大模型模拟药物影响评估展望

[原研究窗口](https://chatgpt.com/g/g-p-6aa7b0cb61f48191bc4c4f582a8acef5/c/6aa7b53a-394c-83e9-bcce-7b2d2e317670)

原文整理，不改写研究结论。旧页面记录采集于 2026-09-14；GPT Activity 于 2026-09-17 补采。保留页面公开展示的过程说明，不代表平台未公开的内部推理。 保留引用按钮编号，但旧来源摘录不保证完整呈现每个按钮内全部对应来源。图形布局及未载入图片不在文本摘录中；公式按页面现有文本保留，不推测补齐运算符。

## 评测原题

传统的药物研究，即便是从多组学角度出发也难以系统地，宏观地解析药物对机体产生的影响。而且个人异质性会造成其他的影响，因之，请为我调研现阶段大模型是否能模拟药物产生影响来系统性评估药物，这个方向未来会如何发展呢

## 对话及完成信息

Today 4:49 PM

##### You said:

Deep research

传统的药物研究，即便是从多组学角度出发也难以系统地，宏观地解析药物对机体产生的影响。而且个人异质性会造成其他的影响，因之，请为我调研现阶段大模型是否能模拟药物产生影响来系统性评估药物，这个方向未来会如何发展呢

Your message actions

##### ChatGPT said:

页面完成时长：7 分钟（页面取整值）；显示来源数：41。本窗口未见 Gemini 式独立审批方案，未从报告倒推补写。

## 最终研究报告

## 现阶段大模型能否模拟药物影响并进行系统性药物评估：能力边界、验证证据与未来五至十年路线图

### 执行摘要

**核心结论：截至 2026 年，大模型已经能够“模拟药物作用链条中的若干局部环节”，但还不能可靠地端到端模拟“给某个具体患者一种药 → 分子结合 → 细胞与组织响应 → 器官暴露与毒性 → 临床疗效/不良反应”的完整因果过程。**当前最成熟的是分子结构、蛋白—配体相互作用、分子性质和部分靶点/药物排序；最活跃的突破点是单细胞转录组层面的扰动响应；器官、全身及个体层面的可靠模拟仍主要依赖 PBPK、PK/PD、QSP 等机制模型，再辅以机器学习，而不是单独依赖 GPT、LLaMA、scGPT 等大模型。AlphaFold 3 已能联合预测蛋白、核酸、小分子、离子等复合物结构，但结构预测并不等同于结合自由能、剂量—效应、药代动力学或临床疗效模拟，而且后续基准研究显示其对训练分布之外配体的泛化仍受训练集相似性影响。[1]

从“药物产生影响”的角度看，**细胞级扰动模型是目前最接近真正“模拟干预后状态”的基础模型方向**。PRnet 等模型已经能够根据未处理细胞状态、化合物结构和剂量预测新的转录状态；GEARS 可预测未见过的基因扰动组合；scGPT、scFoundation、Geneformer 则提供大规模细胞表征与迁移学习能力。[2]但独立评测给出了重要警告：2025 年针对 Geneformer/scGPT 的零样本评估发现，它们在多个任务上不能稳定超过 HVG、scVI、Harmony 等简单或较小模型；Arc Institute 2025 Virtual Cell Challenge 同样发现，扰动模型尚不能在所有指标上稳定胜过朴素基线。[3]因此，现阶段不应把“单细胞 foundation model”直接等同于“细胞数字孪生”。

**多组学能够显著改善问题定义和上下文条件，但尚未解决因果性。**GLUE、scGPT 等方法可把转录组、表观染色质等异构数据映射到共同潜空间；AlphaGenome 类模型进一步把基因组变异连接到调控效应；药物研发实践中，PandaOmics/Chemistry42 将多组学和文献知识用于靶点发现与化合物生成，最终产生 TNIK 抑制剂 rentosertib（原 INS018\_055）。该项目已完成体外、动物、Ⅰ期人体验证，并在 2025 年报告了随机双盲Ⅱa期试验结果，是目前“AI 药物研发链条得到人体临床检验”的代表案例之一。[4]但这一成功证明的是 AI 可辅助发现靶点和药物，并**不证明已有模型能够事先准确模拟每名患者的疗效**。

**个体层面仍是最大的能力缺口。**遗传药理学可以利用药物基因组学和 PRS 估计治疗反应异质性；例如 PRS-PGx 在 IMPROVE-IT 数据中优于传统疾病 PRS。[5]但更大规模现实世界研究显示，某些药物反应 PRS 所解释的方差仍低于 2%，说明遗传背景只是个体药效差异的一部分。[6]共病、年龄、器官功能、既往用药、DDI、免疫状态、微生物组、依从性和环境因素必须同时建模，而目前几乎没有基础模型拥有覆盖这些变量且带有高质量剂量—时间—结局标签的数据。

因此，本报告建议把未来系统定义为\*\*“多尺度混合药物数字孪生”而非单一大模型\*\*：

分子/蛋白基础模型 + 单细胞扰动模型 + 多组学表征 + 知识图谱/因果模型 + PBPK/QSP + 个体临床数据 + 不确定性量化 + 实验反馈闭环。

监管趋势也支持这种“特定用途、可验证模型”而非“万能模型”的路线。中国 CDE 已发布模型引导的创新药物剂量探索与优化指导原则；国家药监局 2026 年《“人工智能+药品监管”实施意见》明确提出建设高质量数据集、垂直大模型、智能体以及模型验证标准。[7]FDA 则采取基于 context of use 和风险的模型可信度思路，并于 2025 年首次资格认定 AI 药物开发工具 AIM-NASH；ICH M15 进一步为 MIDD 的证据和监管使用形成国际框架。[8]

**未来五至十年的关键里程碑不会是“出现一个能模拟人体所有药物的大模型”，而更可能是：先在特定疾病、特定药物类别、特定终点中形成经实验和前瞻性临床验证的多尺度模型；之后才逐步形成可更新的患者级数字孪生。**当前最值得投入的研究不是继续单纯扩大参数量，而是建立严格隔离训练集的扰动基准、获得纵向剂量—时间—多组学数据、加入机制约束和因果结构、量化模型不确定性，并把湿实验与临床反馈真正纳入模型训练循环。[9]

### 分层模拟能力：从分子、细胞到器官与个体

**结论要点。**“大模型能否模拟药物影响”不能用单一的“能/不能”回答，因为当前所谓“大模型”至少包括四类完全不同的系统：通用文本 LLM、分子/蛋白基础模型、细胞/组学基础模型，以及图神经网络和机制—机器学习混合模型。它们预测的对象、所学概率分布及验证标准并不相同。当前只有把这些模型组合起来，才有希望覆盖完整的药物作用链条。[1]

本报告对截至 2026 年的成熟度判断如下；这里的等级是对文献证据的综合评价，而不是某篇论文给出的评分：

|  |  |  |  |
| --- | --- | --- | --- |
| 生物尺度 | 当前可实现的“模拟” | 本报告成熟度判断 | 能否独立支持系统性药物评估 |
| 分子/靶点 | 结构、口袋、对接姿态、部分亲和力/性质、靶点关联 | **较高，任务级成熟** | **不能**；缺少完整动力学、ADME/Tox 和生理环境 |
| 细胞/通路 | 转录组扰动、部分遗传/化学 perturbation、细胞状态转换 | **中等，快速发展** | **有限**；OOD 泛化及因果性不足 |
| 组织/器官 | 部分影像、组织状态、局部 QSP/数字孪生 | **中低** | **必须依赖机制模型和实测参数** |
| 全身系统 | PK/PD、PBPK、DDI、疾病 QSP | **机制模型较成熟，大模型较弱** | **可用于特定问题，非纯大模型方案** |
| 个体患者 | PGx、部分风险/疗效预测、数字孪生原型 | **较低** | **尚不能通用、前瞻性地替代临床试验** |

#### 分子层面：预测结构已经很强，但“知道怎么结合”不等于“知道会产生什么药效”

AlphaFold 3 的重大进展是把结构预测从蛋白质扩展至蛋白—核酸—小分子—离子等联合体系，使药物研发第一次拥有非常通用的生物分子复合体结构先验。[1]DynamicBind、DiffDock、Uni-Mol、MoLFormer 等则分别探索蛋白构象适应、扩散式对接、三维分子表示及超大规模分子语言预训练。MoLFormer 的预训练规模达到约 11 亿个未标记分子；Uni-Mol 以大规模三维分子和蛋白口袋构象进行预训练。[10]

这些方法适合回答：

**“这个分子可能结合哪里？”、“可能采用什么构象？”、“它像不像活性化合物？”、“某类理化性质可能是多少？”**

却不能直接回答：

**“100 mg 口服后肝、肺、脑中暴露是多少？”、“在特定 CYP 基因型和合并用药下会不会产生毒性？”、“三个月后这个患者的 FEV1/FVC 会改善多少？”**

原因是结构模型通常没有显式表示吸收、分布、代谢、排泄、动态构象分布、组织微环境、剂量和时间等变量。对全原子模型的最新比较也显示，对未见配体的性能仍与训练集相似性有关，提示结构模型可能部分受记忆和分布外泛化限制。[11]

因此，**分子层面已经达到“高价值虚拟筛选与结构假设生成”，但距离“药效数字孪生”仍有本质差距。**

#### 细胞与通路层面：目前最接近真正的药物“反事实模拟”

这一区域是近三年进步最快的方向。PRnet 明确将问题定义为：给定未处理转录组状态、化合物结构和剂量，预测药物处理后的转录状态，并针对实验中未处理过的新化合物进行泛化。[2]这已经接近一个可计算的反事实：

[ P(X\_{t+\Delta t}\mid X\_t,\ \text{drug},\ \text{dose},\ \text{context}) ]

其中 (X) 是细胞分子状态。

GEARS 则通过图增强建模预测未见过的单基因及组合基因 perturbation；原论文在部分任务上相对于已有方法报告约 30%–50% 的均方误差改善，并强调其对未测组合扰动的预测能力。[12]但 GEARS 是**遗传干预模型**，不能直接把 CRISPR knockout 的效果等同于小分子药物，因为小分子存在部分抑制、剂量效应、结合多靶点、代谢物及时间动态等差异。

scFoundation 在超过 5,000 万个人类单细胞表达谱上预训练约 1 亿参数模型，并展示组织药物反应预测、单细胞药物响应分类、扰动预测等下游任务。[13]scGPT 则以生成式 Transformer 建模约数千万单细胞数据，覆盖细胞类型、批次整合、多组学以及 perturbation 等任务。[14]Geneformer 通过大规模单细胞表达预训练和 in-silico perturbation，将细胞网络状态作为迁移学习对象，并开展了疾病靶点的实验验证。[15]

然而，**独立基准大幅降低了我们对“虚拟细胞已经成熟”的判断**。2025 年零样本研究发现 Geneformer 和 scGPT 在多套数据的细胞聚类和批次处理上不能稳定超过 HVG、Harmony 或 scVI；研究甚至观察到某些预训练任务只略胜或不胜简单平均预测。[3]Arc Institute 2025 Virtual Cell Challenge 使用约 30 万单细胞、300 个 CRISPRi perturbations，结论同样是扰动模型还不能在全部指标上一致超过朴素基线，而获胜方法往往结合深度学习与经典统计特征。[16]

这说明目前真正的瓶颈并非参数量，而是**能否从统计共现升级为可迁移的干预规律**。

#### 器官与系统层面：机制模型目前比 foundation model 更可信

一旦从细胞进入器官和全身，问题发生质变，需要处理血流、屏障、器官体积、蛋白结合、代谢酶、清除、跨器官反馈、免疫系统和疾病进程等连续动力学。FDA 长期接受 PBPK 用于药物研发和申报；当前 MIDD 框架也明确把暴露、疾病、生物学及统计模型整合用于药物开发。[17]

因此最现实的体系不是：

“用一个 Transformer 从 SMILES 直接预测临床结局”

而是：

**结构/组学模型提供参数或先验 → PBPK 计算体内暴露 → QSP 建模靶点占有和生物网络 → ML 校正复杂残差 → 临床数据更新个体参数。**

QSP 已进一步发展为“虚拟患者群体”乃至数字孪生。例如免疫肿瘤学研究正在探索用机制型 QSP 建立患者状态和干预反应，但相关综述同时强调从 virtual patient 到真正实时更新的 patient digital twin 尚需要纵向患者数据和临床验证。[18]

2025 年一个三阴性乳腺癌研究利用 ARTEMIS 试验中 105 名患者构建 MRI 驱动数字孪生，用于预测新辅助化疗反应，是器官尺度个体化模型的代表性 proof-of-concept；但这种疾病专用模型与“任意药物—任意患者数字孪生”仍有很大距离。[19]

#### 个体层面：已有“个体条件化预测”，尚无可靠通用患者模拟器

PGx 是最成熟的个体化入口之一。PRS-PGx 将治疗组和对照组信息共同纳入遗传风险建模，在 IMPROVE-IT 等随机试验数据中提高了药物反应预测和患者分层能力。[5]但真实世界大规模 EHR/biobank 研究显示，一些药物反应 PRS 的解释方差仍不足 2%，说明多数个体药效变异并不能仅靠遗传信息解释。[6]

年龄、性别、肝肾功能、共病、既往治疗、合并用药、饮食、依从性、免疫状态以及微生物组都会改变药效或药物代谢；微生物组本身还高度动态，受药物、饮食及环境暴露影响。[20]当前数据通常只覆盖这些因素中的少数几个，因此即使模型在内部测试集有高 AUC/Pearson correlation，也不等于对跨医院、跨族群和新药具有可靠外推能力。

**未解决问题。**真正缺失的是一个能同时保持以下守恒关系的模型：分子物理合理性、细胞因果一致性、器官动力学一致性、患者临床现实一致性。目前几乎没有单模型能同时满足四点。[9]

### 多组学融合与个体异质性

**结论要点。**多组学不是简单地“给模型更多 feature”。真正有价值的设计是让不同组学承担不同因果角色：

[ \text{遗传/表观遗传背景} \rightarrow \text{基线细胞状态} \rightarrow \text{药物靶点扰动} \rightarrow \text{转录/蛋白/代谢变化} \rightarrow \text{组织表型} \rightarrow \text{临床结局} ]

现有基础模型已经能够处理其中多个节点，却很少拥有足够数据同时学习整条时间链。[4]

|  |  |  |  |
| --- | --- | --- | --- |
| 数据层 | 最适合作用 | 与大模型的典型结合方式 | 当前主要问题 |
| 基因组 | 固定遗传背景、PGx、靶点变异 | 序列 foundation model、variant embedding、PRS | 人群偏差、效应小、罕见变异 |
| 表观组 | 调控潜能、细胞状态约束 | ATAC/甲基化 token、调控图 | 数据稀疏、批次效应 |
| 转录组 | 药物扰动的高通量 readout | Transformer/VAE/扰动生成模型 | RNA ≠ 蛋白活性，时间点有限 |
| 蛋白组 | 靶点丰度、磷酸化、信号通路 | 图网络、多模态 embedding | 覆盖度和大规模训练集不足 |
| 代谢组 | 药物与表型之间的末端状态 | latent-space fusion/QSP conditioning | 标准化和定量一致性差 |
| 单细胞数据 | 细胞类型、异质性、状态分布 | cell foundation model | donor 数远小于 cell 数 |
| 临床/EHR | 最终疗效、安全性和长期状态 | 时序模型、因果模型、数字孪生更新 | 缺失、混杂、标签偏差 |

**成功案例之一是 GLUE。**GLUE 通过知识图连接不同特征空间，把未配对的单细胞多组学映射到统一表征，并可进一步推断调控关系，代表了“知识先验 + 表征学习”而不是简单拼接矩阵的路线。[4]scGPT 则进一步表明，大规模预训练模型可承担单细胞多组学整合及迁移学习任务。[14]

**另一个值得重视的方向是把基因组模型作为药物模型的“患者背景条件”。**AlphaGenome 在 2026 年正式发表的工作中直接预测调控序列及变异效应，在多个基因组轨道和 variant-effect benchmark 上达到很强性能。[21]它自身不是药物模拟器，但可以提供类似：

[ P(\text{drug response}\mid \text{variant-regulatory state}, \text{cell state}, \text{drug}) ]

中的第一部分患者背景先验。

**最具药物研发实证意义的多模态案例之一是 TNIK/rentosertib。**PandaOmics 利用组学数据与文本模型选择纤维化相关靶点，Chemistry42 再以多个生成模型产生和优化化合物。INS018\_055 随后在细胞实验、IPF 患者原代成纤维细胞、多个动物纤维化模型中验证，并进入人体Ⅰ期。论文指出从靶点发现到候选药物提名约为 18 个月。[22]2025 年发表的随机双盲Ⅱa期试验纳入约 71 名 IPF 患者；在 60 mg 每日一次组中，12 周平均 FVC 变化为 +98.4 ml，而安慰剂组为 −20.3 ml，但样本量小、疗程短，作者本人也指出需要更大、更长期试验确认。[23]

这一案例非常重要，同时也说明应避免概念扩大：**AI 成功提出靶点和化合物，并不意味着 AI 已经准确模拟了临床药效。**临床结果仍必须通过随机试验获得。

**失败模式和挑战。**

第一，**cell 数不等于患者数**。五千万个单细胞可能只来自相对有限的组织、donor、疾病和测序平台；扩大单细胞数量并不能自动获得同等规模的个体异质性。scGPT/Geneformer 的零样本评估表明，更大的预训练数据量也不必然转化为更好的跨数据集泛化。[3]

第二，**不同组学存在不同时间常数**。DNA 基本固定，RNA 可以在分钟至小时变化，蛋白和磷酸化有自己的动力学，代谢物又更快；把同一患者不同时间采集的数据简单融合可能生成不存在的“伪同步状态”。

第三，**药物训练数据严重缺少 dose × time × tissue × genotype 的完整笛卡尔积**。PRnet 的意义正在于显式加入 compound structure 和 dose；未来模型还必须进一步加入时间、组织、患者及联合用药。[2]

第四，**转录相关性不是药理因果链。**某基因在给药后改变，可能是药效机制、补偿反应、细胞死亡结果或纯粹批次效应。由此得到的注意力权重或 embedding 相似性不能直接解释为 pathway mechanism。独立 foundation-model benchmark 正是对此提出警告。[3]

**个体异质性的推荐建模形式**因而应是：

```
[ \hat Y_i(d,t)
```

f\_\theta ( \underbrace{G\_i,E\_i}*{遗传/表观}, \underbrace{C\_i}*{细胞状态}, \underbrace{P\_i,M\_i}*{蛋白/代谢}, \underbrace{D\_i}*{疾病}, \underbrace{H\_i}*{病史/共病}, \underbrace{Rx\_i}*{既往与合并用药}, \underbrace{\mu\_i}\_{微生物组}, d,\text{dose},t ) ]

同时输出预测分布而不是单点：

[ p(Y\_i\mid X\_i,d),\quad \mathrm{CI/PI},\quad P(\text{OOD}\mid X\_i) ]

即必须明确告诉研究者：**模型预测什么，以及它有多不确定。**

**未解决问题。**对真正个体化药物评估而言，最缺的不是模型架构，而是同一患者上的纵向、多组织、剂量明确、治疗前后多组学及长期临床结局数据。未来如果这一类数据不增加，仅靠把模型从数亿扩展到数百亿参数，很难跨越患者级模拟瓶颈。这个判断与目前 foundation model 的零样本结果以及数字孪生领域对纵向校准数据的需求一致。[9]

### 可解释性、可验证性与临床转化

**结论要点。**对药物研究而言，“可解释”真正有用的定义不是“模型能生成一段听起来合理的机制说明”，而是：

**模型必须产生一个可以被实验推翻的生物学预测。**

因此最好把解释拆成四层。

**结构解释**回答“药物可能在哪里、以什么构象结合”；AlphaFold 3、DiffDock、DynamicBind 属于这一层。[1]

**网络解释**回答“哪些基因/通路/细胞类型介导预测”。TxGNN 的优势之一是能够给出知识图谱中的多跳路径，而不是只输出 drug–disease score。TxGNN 在 17,080 种疾病的零样本药物再利用任务中，相对比较方法报告了显著性能提高，但这仍主要属于计算验证和知识图谱解释，而非前瞻性治疗试验证明。[24]

**反事实解释**回答“若改变靶点、剂量、时间或细胞状态，结果是否按模型预测改变”。GEARS、PRnet 等 perturbation 模型更接近这一层，因为可以把预测转化为新的 CRISPR 或药物实验。[25]

**机制解释**则要求预测符合 PK、受体占有、酶动力学和已知生物网络约束，这也是 QSP/PBPK 与 foundation model 结合的核心价值。[17]

一个适合科研实践的验证梯度应是：

**计算留出验证 → 生化实验 → 细胞/原代细胞 → 类器官或组织 → 动物 → 人体 PK/安全性 → 随机临床疗效 → 前瞻性“模型指导治疗”试验。**

其中前三层只能证明模型捕获了部分生物规律；只有后两层才逐渐接近证明“模型在临床决策中有增量价值”。

**代表性验证案例：Geneformer。**Geneformer 并不只做分类，而是使用 in-silico perturbation 推断基因网络和潜在治疗靶点，并在心肌病相关模型中通过实验系统对部分模型预测进行验证。这类“模型提出靶点 → 实验 perturbation 验证”是单细胞基础模型当前最合理的验证范式。[15]

**代表性验证案例：rentosertib。**这是更完整的链条：AI 靶点识别 → 生成化学 → 酶和细胞实验 → IPF 患者来源原代细胞 → 小鼠/大鼠纤维化模型 → 健康志愿者Ⅰ期 PK/安全性 → IPF 患者Ⅱa期随机对照。[22]这一案例说明 AI 模型输出可以最终转化为可临床验证的假设，但也恰恰说明**体内真实结果依然需要实验和临床试验，而不能用模型输出替代。**

**监管层面的验证案例：AIM-NASH。**FDA 于 2025 年 12 月资格认定 AIM-NASH，允许 AI 辅助病理学工具用于 MASH 临床试验中的组织学评估。这是 FDA 首个获得资格认定的 AI drug development tool。工具输出仍由病理医师最终审核，资格认定基于其与专家共识比较的验证结果。[26]它不是药效模拟器，但给出了一个非常重要的监管模板：

**明确 Context of Use → 锁定模型 → 预先定义性能指标 → 与专家/实验金标准比较 → 保持人类监督。**

这比“模型总体 benchmark 很高”更接近未来药物模拟模型所需的监管证据。

**通用 GPT/LLaMA/BioGPT 的角色也应在这里明确。**BioGPT 是在大规模 PubMed 生物医学文本上预训练的生成式模型，展示了生物医学关系抽取、药物—靶点/药物—药物关系及问答能力。[27]GPT/LLaMA 类通用 LLM 同样非常适合文献检索、证据整合、代码生成、工具调用和实验设计。然而，这些文本模型本身没有保存质量守恒、化学势、血流动力学、药物清除或基因调控因果结构，因此更合理的定位是**scientific copilot/agent 与模型编排器，而不是直接充当药物数字孪生的“物理引擎”**。WHO 对医疗大型多模态模型的指导也明确指出其可能产生错误、不完整和带偏差的结果，并强调独立审计和持续评估。[28]

**未解决问题。**当前绝大多数论文验证的是模型预测准确性，而不是**模型指导决策是否改善实验成功率或患者结局**。未来真正高价值的终点应从 Pearson (r)、AUROC 和 reconstruction error，逐步转向：

[ \Delta \text{实验成功率},\quad \Delta \text{候选药淘汰率},\quad \Delta \text{临床试验富集效率},\quad \Delta \text{患者获益} ]

这将是“AI benchmark”走向“药物研发证据”的关键转变。

### 监管、伦理、隐私与现实障碍

**结论要点。**未来监管机构大概率不会审批一个笼统声明“可以模拟人体药物反应的大模型”；监管对象会是一个明确限定用途的模型，例如“预测特定人群中某药某剂量的暴露”“辅助某种临床试验终点”“为某适应症患者分层”。FDA、ICH 和中国 CDE 的最新方向均强调 context of use、模型证据、验证和生命周期管理。[29]

在中国，CDE 于 2024 年发布并实施《模型引导的创新药物剂量探索和优化技术指导原则》，说明基于模型的剂量探索已进入正式监管框架。[7]2026 年国家药监局进一步提出建设“人工智能+药品监管”体系，到 2030 年形成高质量数据集、垂直大模型和智能体，并特别提出训练/微调数据和知识库的合法来源、准确性、可追溯性，以及算法透明度和模型验证标准。[30]

美国方面，FDA 已形成风险导向的 AI 药物开发监管思路，MIDD 又通过 ICH M15 向标准化证据框架推进；AIM-NASH 的资格认定显示，AI 可以正式进入临床药物开发流程，但前提是用途边界和验证证据足够清晰。[8]

欧盟方面，EMA 已发布药品全生命周期使用 AI 的 reflection paper，而 EU AI Act 对作为受监管产品安全组件的高风险 AI 设置了风险管理、数据治理、透明度和人工监督等要求。[31]

**风险与伦理清单：**

**训练数据泄漏与 benchmark 污染。**

预训练集极大时，测试化合物、细胞系或研究数据可能已被模型见过，产生虚假的“零样本”能力；single-cell foundation model 评估已经观察到训练数据与 benchmark 部分重叠。

[3]**族群和疾病谱偏差。**

单细胞库、PGx、EHR 和生物库中的族裔、年龄及地区分布不均，会把人群结构误认为药物生物学规律。

[6]**错误因果解释。**

attention、embedding similarity 和 feature attribution 均不能自动证明机制因果，需要 perturbation 验证。

[3]**幻觉与知识过时。**

通用 LLM 可能生成不存在的机制、靶点、文献或剂量信息，因此不应直接用于无监督临床处方决策。WHO 明确把虚假、不准确、不完整和偏差输出列为大型多模态医疗模型风险。

[28]**基因和健康隐私。**

中国《个人信息保护法》将医疗健康等信息纳入敏感个人信息范畴，要求具有特定目的、充分必要性和严格保护措施；相关处理还涉及单独同意以及自动化决策透明度等义务。

[32]**跨境多组学数据限制。**

人类遗传资源与临床数据国际合作及跨境共享需要符合相应监管要求，直接集中训练全球患者模型存在法律和治理障碍。

[33]**自动化偏见。**

医师或研究者可能因为模型“语言流畅”而过度相信预测，WHO 特别警告 automation bias，并要求人类监督和部署后监测。

[28]**责任归属。**

当基础模型、PBPK 软件、数据提供方、医院和医生共同组成系统时，必须明确哪一个版本、数据、参数和人为决策产生最终结论；NMPA 2026 意见已特别强调全过程可追溯与人机协同。

[34]**双重用途。**

能准确预测靶点、毒性和分子设计的模型也可能被用于优化有害化合物；越接近“完整药理模拟器”，模型访问控制和危险能力评估越重要。

**模型漂移。**

新药、变异株、治疗指南、患者群体及检测技术变化都会改变数据分布，因此一次性验证不能代表永久有效；应建立版本化、漂移监测和再验证制度，这与生命周期式 AI 监管思路一致。

[31]

现实临床路径因此应采用**递增风险模型**：首先用于候选排序和实验设计；之后用于试验患者富集和终点辅助；再经过前瞻性研究后进入模型辅助剂量或治疗选择；只有经过严格临床效用验证后才考虑更高程度的自动化。

### 技术瓶颈与研究实践建议

**结论要点。**目前限制该领域发展的首要因素已经不再只是“模型参数太少”。核心瓶颈依次是**因果干预数据、跨尺度对齐、分布外泛化、不确定性以及临床验证**。单纯 scale-up 很可能带来递减收益。2025 年零样本评测发现，更大的 single-cell 预训练集合没有稳定转化为更优表现；Virtual Cell Challenge 同样显示 end-to-end 深度模型仍没有解决全部 perturbation prediction 问题。[3]

|  |  |  |
| --- | --- | --- |
| 瓶颈 | 为什么严重 | 优先解决方案 |
| 干预标签稀缺 | 大量 omics 是观察数据而非药物干预 | 大规模 Perturb-seq、药物×剂量×时间矩阵 |
| 多尺度数据断裂 | 分子、细胞、动物、临床来自不同实验 | 建立同一化合物跨尺度数据 lineage |
| OOD 泛化 | 新药、新组织、新患者才是实际应用场景 | scaffold split、time split、unseen donor/site benchmark |
| 因果识别不足 | 共表达容易冒充药物机制 | CRISPR、药物 rescue、因果图、随机化数据 |
| 蛋白/代谢数据不足 | RNA 不是功能终点 | 强化 proteomics、phosphoproteomics、metabolomics |
| 动态数据不足 | 单一终点无法学习药理时间过程 | dense longitudinal sampling + neural ODE/QSP |
| 个体标签不足 | 数千万 cells 往往只有有限 donors | 把 donor 数和纵向随访作为主要 scaling axis |
| 不确定性欠缺 | 高置信错误在药物开发中代价巨大 | ensemble、conformal prediction、OOD detection |
| 计算昂贵 | 全原子+单细胞+患者联合模拟不可直接暴力求解 | 多保真度模型、surrogate、模块化 simulation |
| 临床验证慢 | retrospective accuracy 不等于 clinical utility | silent deployment → prospective validation → RCT |

**最值得建设的数据不是另一个静态单细胞 atlas，而是干预型 atlas。**Tahoe-100M 是这一转变的代表：其规模约一亿单细胞，覆盖约 1,100 种小分子和约 50 个癌细胞系，为模型学习 drug × cell-context interaction 提供了远大于传统单细胞药物数据的训练环境。[35]但其主体仍是癌细胞系，所以不能简单外推至患者组织和复杂慢性病。

针对一个研究团队，本报告建议构建四层 benchmark：

**第一层：药物完全未见。**以 scaffold 或 target family 做严格拆分，阻止同骨架近邻泄漏。

**第二层：生物环境未见。**留出完整 cell type、tissue 或 donor，而非随机留出 cells。Arc 的 Virtual Cell Challenge 特意使用与典型训练数据分布不同的 H1 人胚胎干细胞，以检验真正的 generalization。[16]

**第三层：时间外推。**只用早期时间点训练，预测晚期状态，以区分动态规律和简单插值。

**第四层：实验前瞻验证。**在模型冻结后选择 Top-K 与随机/传统方法候选，同时进行实验，比较 hit rate，而不是再从实验结果反向调模型。

药物作用模型的一个推荐工程架构为：

text

```
化合物结构/蛋白结构 │ ▼ 3D foundation model ──► affinity / target / off-target │ ▼ 细胞扰动 foundation model │ ├── genome / epigenome ├── transcriptome ├── proteome / phosphoproteome └── metabolome │ ▼ 因果通路 / QSP │ ▼ PBPK → 器官暴露 → PK/PD │ ▼ 患者条件化层 PGx + 年龄 + 肝肾功能 + 共病 + 合并用药 + 微生物组 + EHR │ ▼ 疗效分布 / AE分布 / dose-response │ ▼ 不确定性 + OOD报警 + 可验证机制假设
```

这里最重要的设计原则是**不要让单一神经网络承担所有物理和生物约束**。FDA 对 PBPK/MIDD 的持续使用，以及 QSP 数字孪生文献的发展，都支持让明确的机制模型保留那些已经被药理学理解的结构，让机器学习负责目前无法完整参数化的复杂部分。[17]

对于实验验证，最有效的设计不是验证“模型预测表达谱相关系数很高”，而是同时验证：靶点 engagement、关键 pathway readout、表型 rescue、剂量曲线、时间曲线和至少两个未用于训练的 donor。对进入转化阶段的候选，还应继续验证 PK/PD bridge 与安全窗口。

**未解决问题。**目前尚没有公认的“CASP for drug-effect simulation”。结构领域曾因盲测 benchmark 获得巨大推动，而药物作用模拟仍缺少长期保密、真正未见过的新药—新细胞—新患者组合。2025 年 single-cell benchmark 已明确建议建设永久保留、不进入未来预训练集的独立评估数据。[3]这是未来三年最值得由产业、医院和监管机构联合建立的基础设施之一。

### 未来五至十年路线图

**结论要点。**以下是基于当前技术状态和监管方向做出的研究预测，而不是已确定的产业时间表。最可能的演化路径是从“单尺度预测器”变成“模块化多尺度模型”，随后才出现经前瞻性验证的疾病专用数字孪生；一个可以可靠模拟所有疾病、药物和患者的“通用人体 foundation model”在未来十年内仍不应作为基线假设。当前 virtual-cell 泛化结果、QSP 数字孪生的发展状态及监管对 context-specific validation 的要求都支持这一判断。[9]

2026–2029

建立严格OOD药物扰动基准

结构+剂量+时间+细胞上下文联合foundationmodel

Tahoe级化学扰动图谱扩展至原代细胞/类器官

foundationmodel与PBPK/QSP深度融合

不确定性和OOD检测成为标准输出

AI开发工具出现更多限定用途监管资格

2029–2031

RNA+蛋白+表观+代谢纵向多组学联合预测

多组织类器官及器官芯片进入模型训练闭环

患者级模型用临床纵向数据持续校准

多中心前瞻性模型验证成为高水平证据

特定适应症数字孪生用于试验富集和剂量优化

2031–2036

若干疾病形成经过临床验证的患者数字孪生

模型参与自适应临床试验设计

药物组合和长期毒性实现概率化模拟

联邦式跨机构学习成为重要基础设施

监管接受部分模型作为正式MIDD证据

通用人体模拟仍需真实实验持续校准

药物作用大模型与数字孪生的可能发展路线

**短期一至三年：从“预测表达”转向“预测干预”。**

研究优先级应首先放在 chemical perturbation foundation model，而不是继续堆积普通未处理单细胞数据。模型输入至少应同时包括 drug structure、dose、time、cell type 和 baseline state。PRnet 已展示其中前三者结合的可行性，Tahoe-100M 则提供了训练规模；Virtual Cell Challenge 暴露出的泛化问题会迫使领域更重视真正的 OOD benchmark。[2]

这一阶段最可能首先产业化的是“**virtual screening 2.0**”：不是只预测 binding，而是依次预测 binding → cell response → pathway → basic PK/Tox，从而大幅减少真正进入湿实验的候选数量。监管端中国 NMPA 已明确提出开发高质量数据集、垂直大模型和智能体，并推动 AI 在药品全生命周期中规范使用，说明产业基础设施与监管能力会同步发展。[34]

**中期三至五年：疾病专用数字孪生开始形成。**

更可信的系统会是 disease-specific 而非 universal，例如某一癌种、IPF、炎症性疾病或特定免疫治疗场景。这些模型可把患者影像、PGx、多组学和 serial biomarkers 与 QSP/PBPK 联合，实时更新个体参数。当前 TNBC MRI digital twin 和免疫肿瘤 QSP 已经展示了这种方向的原型。[19]

最关键的里程碑将不是 benchmark，而是**多中心 prospective validation**：在治疗前冻结模型，对患者疗效/毒性作出预注册预测，再与真实结果比较。

同时，模型需具备类似：

[ \text{Prediction} \pm \text{Uncertainty} + \text{Mechanistic rationale} + \text{Applicable domain} ]

的标准输出，而不能只给一个数字。

**长期五至十年：限定疾病中的可更新 patient twin。**

真正意义上的药物数字孪生应做到患者每次新检测后更新状态：

```
[ S_{t+1}
```

F( S\_t, \text{drug}*{t}, \text{dose}*{t}, \text{new omics}, \text{labs}, \text{imaging}, \text{clinical events} ) ]

并同时模拟“不给药”“药 A”“药 B”“A+B”“不同剂量”等反事实轨迹。

这种体系可能首先用于高成本、治疗窗口狭窄、机制相对明确且存在频繁生物标志物的疾病。其用途更可能是**决策支持、剂量优化和试验设计**，而不是完全代替临床医师或人体试验。FDA AIM-NASH 目前仍将最终解释责任保留给人类病理学家；中国 NMPA 2026 政策同样强调“数据智能赋能、人工审查、全流程可追溯”的人机协作。[26]

从产业投资角度，本报告认为未来价值链最可能由四类资产决定：

**第一是独占性干预数据，而非纯算法；第二是能够跨尺度连接的数据标准；第三是经过实验和临床验证的特定用途模型；第四是能够留下完整审计轨迹的模型治理系统。**纯模型参数规模的壁垒反而可能下降。

### 代表性模型比较与关键参考来源

下表把经常被统称为“大模型/AI药物模型”的技术拆开。一个重要观察是：**没有任何一行能够独立覆盖所有输入和输出，这本身就是当前无法端到端模拟药物作用的最直接证据。**

|  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| 代表模型/方法 | 输入数据 | 主要输出能力 | 验证状态 | 优点 | 主要限制 | 关键文献 |
| GPT/LLaMA 类通用 LLM | 文献、文本、结构化知识、工具输出 | 文献推理、信息抽取、代码、agent orchestration | 大量通用/医疗任务；非药效数字孪生验证 | 知识整合和人机交互强 | 无内建药代/物理/因果约束，存在幻觉 | WHO LMM 医疗指南[28] |
| **BioGPT** | PubMed 生物医学文本 | DTI/DDI关系抽取、QA、文本生成 | NLP benchmark | 医药语言领域适应 | 本质为文本模型，不模拟真实生物状态 | Luo et al., 2022 [英文][27] |
| **AlphaFold 3** | 生物大分子、小分子、离子序列/组成 | 复合物三维结构 | 大规模结构 benchmark | 分子相互作用结构能力强 | 非动力学、非PK/PD；OOD ligand 风险 | Abramson et al., Nature 2024 [英文][1] |
| **Uni-Mol / MoLFormer** | 3D构象或 SMILES | 分子表示、性质、3D任务 | 多分子 benchmark | 大规模预训练、迁移性强 | 对真实人体药效仍是间接 proxy | [36] |
| **DiffDock / DynamicBind** | 蛋白结构、配体 | docking pose、部分构象调整 | PDBBind 等 benchmark | 对接速度快，可建模构象变化 | 对接正确 ≠ potency/efficacy | [37] |
| **TxGNN** | 药物—疾病—基因知识图 | 零样本药物再利用、机制路径 | retrospective/KG benchmark | 适合罕见疾病、可输出路径解释 | 关联/排序不是动态药效模拟 | Huang et al., Nat Med 2024 [英文][24] |
| **GraphDRP / DeepCDR 类** | 分子图 + 肿瘤多组学 | 癌细胞系 drug response | GDSC/CCLE 等 | 能联合药物结构与患者/细胞分子背景 | 主要为癌症细胞系；临床 transfer 有限 | [38] |
| **Geneformer** | 单细胞 RNA | cell embedding、in-silico perturbation、网络预测 | 部分实验验证 | 可产生可实验检验的靶点假设 | zero-shot 泛化不稳定 | Theodoris et al., Nature 2023 [英文][15] |
| **scGPT** | 大规模单细胞/多组学 | annotation、integration、perturbation 等 | 多 downstream benchmark | 可统一多个 single-cell 任务 | 独立 zero-shot benchmark 表现不稳定 | Cui et al., Nat Methods 2024 [英文][14] |
| **scFoundation** | &gt;5,000万单细胞表达谱 | 表达恢复、drug-response/perturbation 等 | downstream benchmark | 约1亿参数，大规模 transcriptome pretraining | 主要仍是 RNA；患者级验证不足 | Hao et al., Nat Methods 2024 [英文][13] |
| **GEARS** | 基线表达、基因关系、CRISPR perturbation | 未见单/组合基因扰动后表达 | Perturb-seq benchmark | 图先验有利于组合外推 | 基因 knockout 不等于药物作用 | Roohani et al., Nat Biotechnol [英文][12] |
| **PRnet** | 基线 RNA + 化合物结构 + 剂量 | 新化合物处理后的转录响应 | bulk + single-cell benchmark | 与“药物模拟”问题最直接相关 | 主要终点仍是 transcriptome | Qi et al., Nat Commun 2024 [英文][2] |
| **GLUE** | RNA、ATAC 等未配对单细胞多组学 | 共同表征、调控关系 | 多组学 benchmark | 可把知识图作为跨组学桥梁 | 不直接预测药物临床结果 | Cao & Gao, Nat Biotechnol 2022 [英文][4] |
| **AlphaGenome** | 长 DNA 序列、遗传变异 | 调控轨道和 variant effect | 大规模 genomic benchmark | 可作为患者遗传条件编码器 | 自身不是药物响应模型 | Nature 2026 [英文][21] |
| **PBPK / PK-PD / QSP** | 生理参数、药物参数、机制网络、临床数据 | 暴露、剂量—效应、DDI、虚拟患者 | 已进入监管/MIDD | 因果结构明确、可审查 | 校准成本高，未知生物过程难建模 | FDA/MIDD/QSP[17] |
| **PandaOmics + Chemistry42 / rentosertib** | omics、文献、疾病数据、结构/化学空间 | 靶点优选 + 生成药化 | 细胞→动物→Ⅰ期→Ⅱa期 | 临床转化证据链最完整之一 | 不是患者级端到端 simulator | Nature Biotech + Phase IIa [英文][22] |

**综合判断可以压缩成一句话：**

**截至 2026 年，大模型已经可以成为“药物作用模拟系统”的核心组成部分，但还不能成为整个系统本身。**

最可信的技术目标不是追求一个从 SMILES 直接生成患者结局的黑箱，而是构造可以逐层校验的：

[ \boxed{ \text{Molecular FM} \rightarrow \text{Cell Perturbation FM} \rightarrow \text{Causal/QSP} \rightarrow \text{PBPK} \rightarrow \text{Patient-conditioned Twin} } ]

并在每一级配置真实实验观测作为锚点。当前结构模型的高性能、细胞 foundation model 的独立 benchmark 结果、机制 MIDD 已经进入监管实践这一事实，共同支持这一判断。[1]

**研究项目的优先数据集与实验组合。**若以“通用药物影响模拟”为科研目标，近期最有价值的起点是以 Tahoe-100M/大规模化学扰动数据作为预训练，以独立药物和 donor 的单细胞 perturbation 作为 OOD 测试，再增加药物结构、剂量、时间、蛋白/磷酸化和代谢数据；对候选机制用 CRISPR/药物 rescue 做因果检验，之后接入 PBPK/QSP。Tahoe-100M 的规模和 Virtual Cell Challenge 的盲式 OOD 设计提供了互补的数据与评价范式。[35]

对临床阶段，最值得建设的并不是单纯更多 EHR，而是**治疗前基线 + 明确药物/剂量 + 多个治疗后时间点 + PK + 多组学 + 结局 + AE**的一体化纵向队列，因为这类数据才能直接估计个体反事实药物响应。当前数字孪生与 QSP 研究反复指出临床校准和纵向验证是从 virtual patient 走向 patient twin 的核心条件。[18]

**关键参考来源（中文/官方优先，其余标记为英文）：**

**国家药监局药审中心（CDE），2024，《模型引导的创新药物剂量探索和优化技术指导原则》**

。中国 MIDD 和剂量优化的重要正式监管依据。

[7]**国家药品监督管理局，2026，《关于“人工智能+药品监管”的实施意见》**

。明确高质量数据集、垂直大模型、智能体、模型验证及数据可追溯要求。

[30]**《中华人民共和国个人信息保护法》相关官方文本**

。医疗健康信息、敏感个人信息、自动化决策及数据处理的隐私基础。

[32]**FDA，Physiologically Based Pharmacokinetic Analyses Guidance**

[英文，官方]。PBPK 在药物开发和监管提交中的框架。

[17]**FDA / ICH M15，2026，General Principles for Model-Informed Drug Development**

[英文，官方]。最新 MIDD 国际原则框架。

[39]**FDA，2025，AIM-NASH qualification**

[英文，官方]。FDA 首个获得资格认定的 AI drug-development tool。

[26]**EMA，Reflection paper on the use of AI in the medicinal product lifecycle**

[英文，官方]。药品全生命周期 AI 使用的欧洲监管框架。

[31]**WHO，2024，Ethics and governance of artificial intelligence for health: guidance on large multi-modal models**

[英文，官方]。大型模型医疗风险、人类监督及审计框架。

[28]**Abramson et al., Nature, 2024, AlphaFold 3**

[英文，原始论文]。多类型生物分子复合体结构基础模型的重要里程碑。

[1]**Huang et al., Nature Medicine, 2024, TxGNN**

[英文，原始论文]。知识图谱 foundation model 与零样本药物再利用。

[24]**Theodoris et al., Nature, 2023, Geneformer**

[英文，原始论文]。单细胞 foundation model、网络 perturbation 与实验验证。

[15]**Cui et al., Nature Methods, 2024, scGPT**

[英文，原始论文]。生成式单细胞多组学基础模型。

[14]**Hao et al., Nature Methods, 2024, scFoundation**

[英文，原始论文]。约 1 亿参数、超过 5,000 万单细胞表达谱预训练。

[13]**Roohani et al., GEARS, Nature Biotechnology**

[英文，原始论文]。面向未见基因组合 perturbation 的图增强预测模型。

[12]**Qi et al., Nature Communications, 2024, PRnet**

[英文，原始论文]。直接根据药物结构、剂量与基线表达预测新的化学 perturbation。

[2]**Cao & Gao, Nature Biotechnology, 2022, GLUE**

[英文，原始论文]。单细胞未配对多组学整合和调控推断。

[4]**Kedzierska et al., Genome Biology, 2025**

[英文，独立评测]。Geneformer/scGPT 零样本性能和泛化限制的重要反证。

[3]**Arc Institute, Virtual Cell Challenge 2025**

[英文，机构 benchmark]。约 30 万细胞、300 个 CRISPRi perturbations，显示现有模型尚不能一致超过简单基线。

[16]**Tahoe-100M, 2025**

[英文，预印本/开放数据项目]。约一亿单细胞、约 1,100 种小分子和约 50 癌细胞系的大规模药物扰动数据资源。

[35]**Wang et al., npj Digital Medicine, 2024**

[英文]。从 QSP virtual patients 向免疫肿瘤 digital twins 演进的机制框架与现实限制。

[18]**Wu et al., npj Digital Medicine, 2025**

[英文，原始研究]。105 名 TNBC 患者 MRI 驱动治疗数字孪生案例。

[19]**Zhai et al., Nature Communications, 2022, PRS-PGx**

[英文，原始论文]。将遗传背景用于个体药物反应预测。

[5]**Sadler et al., Nature Communications, 2025**

[英文，原始研究]。大规模 biobank/EHR 中 PGx/PRS 泛化能力及有限解释度的实证。

[6]**Ren et al., Nature Biotechnology, 2024/2025, INS018\_055/rentosertib**

[英文，原始论文]。AI 靶点发现和生成化学经体外、动物、Ⅰ期验证的完整案例。

[22]**Rentosertib randomized phase IIa trial, 2025**

[英文，临床原始论文]。生成式 AI 发现药物进入随机双盲Ⅱa期人体疗效验证的重要案例。

[23]**Luo et al., Briefings in Bioinformatics, 2022, BioGPT**

[英文，原始论文]。生物医学文本生成与关系抽取基础模型。

[27]**MoLFormer, Nature Machine Intelligence, 2022**

[英文，原始论文]。超大规模分子语言模型和分子性质迁移学习。

[40]**DynamicBind, Nature Communications, 2024**

[英文，原始论文]。考虑 ligand-specific protein conformation 的蛋白—配体预测。

[10]**AlphaGenome, Nature, 2026**

[英文，原始论文]。面向长基因组上下文和调控变异效应的 foundation model，可作为未来患者遗传背景建模模块。

[21]**EU 1+ Million Genomes / Genomic Data Infrastructure**

[英文，欧盟官方]。说明大规模个体基因组—临床模型未来更可能依赖安全、联邦式数据基础设施，而非把所有患者数据集中到一个模型中。

[41]

## 引用资料与扫描来源（保留原分组）

Citations · 41

[nature.com nature.com](https://www.nature.com/articles/s41586-024-07487-w?utm_source=chatgpt.com)  

**1** [Accurate structure prediction of biomolecular interactions ...](https://www.nature.com/articles/s41586-024-07487-w?utm_source=chatgpt.com)

**2** [Predicting transcriptional responses to novel chemical ...](https://www.nature.com/articles/s41467-024-53457-1?utm_source=chatgpt.com)

**4** [Multi-omics single-cell data integration and regulatory ...](https://www.nature.com/articles/s41587-022-01284-4?utm_source=chatgpt.com)

**5** [Pharmacogenomics polygenic risk score for drug response ...](https://www.nature.com/articles/s41467-022-32407-9?utm_source=chatgpt.com)

**6** [Leveraging large-scale biobank EHRs to enhance ...](https://www.nature.com/articles/s41467-025-58152-3?utm_source=chatgpt.com)

**10** [DynamicBind: predicting ligand-specific protein ...](https://www.nature.com/articles/s41467-024-45461-2?utm_source=chatgpt.com)

**11** [Benchmarking all-atom biomolecular structure prediction ...](https://www.nature.com/articles/s41467-025-67127-3?utm_source=chatgpt.com)

**12** [Predicting transcriptional outcomes of novel multigene perturbations with GEARS | Nature Biotechnology](https://www.nature.com/articles/s41587-023-01905-6?utm_source=chatgpt.com)

**25** [Predicting transcriptional outcomes of novel multigene perturbations with GEARS | Nature Biotechnology](https://www.nature.com/articles/s41587-023-01905-6?utm_source=chatgpt.com)

**13** [Large-scale foundation model on single-cell transcriptomics](https://www.nature.com/articles/s41592-024-02305-7?utm_source=chatgpt.com)

**14** [CellFM: a large-scale foundation model pre-trained on ...](https://www.nature.com/articles/s41467-025-59926-5?utm_source=chatgpt.com)

**15** [Transfer learning enables predictions in network biology | Nature](https://www.nature.com/articles/s41586-023-06139-9?utm_source=chatgpt.com)

**18** [From virtual patients to digital twins in immuno-oncology](https://www.nature.com/articles/s41746-024-01188-4?utm_source=chatgpt.com)

**19** [MRI-based digital twins to improve treatment response of ...](https://www.nature.com/articles/s41746-025-01579-1?utm_source=chatgpt.com)

**21** [Advancing regulatory variant effect prediction with ...](https://www.nature.com/articles/s41586-025-10014-0?utm_source=chatgpt.com)

**22** [A small-molecule TNIK inhibitor targets fibrosis in preclinical and clinical models | Nature Biotechnology](https://www.nature.com/articles/s41587-024-02143-0?utm_source=chatgpt.com)

**24** [A foundation model for clinician-centered drug repurposing](https://www.nature.com/articles/s41591-024-03233-x?utm_source=chatgpt.com)

**40** [Large-scale chemical language representations capture molecular structure and properties | Nature Machine Intelligence](https://www.nature.com/articles/s42256-022-00580-7?utm_source=chatgpt.com)

[link.springer.com link.springer.com](https://link.springer.com/article/10.1186/s13059-025-03574-x)  

**3** [Zero-shot evaluation reveals limitations of single-cell foundation models | Genome Biology | Springer Nature Link](https://link.springer.com/article/10.1186/s13059-025-03574-x)

**9** [Zero-shot evaluation reveals limitations of single-cell foundation models | Genome Biology | Springer Nature Link](https://link.springer.com/article/10.1186/s13059-025-03574-x)

[cde.org.cn cde.org.cn](https://www.cde.org.cn/main/news/viewInfoCommon/3a55263f274e0525c1172a37f5b04a8e?utm_source=chatgpt.com)  

**7** [国家药监局药审中心关于发布《模型引导的创新药物剂量探索和优化技术指导原则》的通告（2024年第53号）](https://www.cde.org.cn/main/news/viewInfoCommon/3a55263f274e0525c1172a37f5b04a8e?utm_source=chatgpt.com)

[fda.gov fda.gov](https://www.fda.gov/drugs/drug-safety-and-availability/fda-qualifies-first-ai-drug-development-tool-will-be-used-mash-clinical-trials?utm_source=chatgpt.com)  

**8** [FDA Qualifies First AI Drug Development Tool, Will Be Used in 'MASH' Clinical Trials | FDA](https://www.fda.gov/drugs/drug-safety-and-availability/fda-qualifies-first-ai-drug-development-tool-will-be-used-mash-clinical-trials?utm_source=chatgpt.com)

**26** [FDA Qualifies First AI Drug Development Tool, Will Be Used in 'MASH' Clinical Trials | FDA](https://www.fda.gov/drugs/drug-safety-and-availability/fda-qualifies-first-ai-drug-development-tool-will-be-used-mash-clinical-trials?utm_source=chatgpt.com)

**17** [The Use of Physiologically Based Pharmacokinetic ...](https://www.fda.gov/?utm_source=chatgpt.com)

**29** [Considerations for the Use of Artificial Intelligence](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/considerations-use-artificial-intelligence-support-regulatory-decision-making-drug-and-biological?utm_source=chatgpt.com)

**39** [M15 General Principles for Model-Informed Drug ...](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/m15-general-principles-model-informed-drug-development?utm_source=chatgpt.com)

[arcinstitute.org arcinstitute.org](https://arcinstitute.org/news/virtual-cell-challenge-2025-wrap-up)  

**16** [Virtual Cell Challenge 2025 Wrap-Up: Winners and Reflections | Arc Institute](https://arcinstitute.org/news/virtual-cell-challenge-2025-wrap-up)

[genome.gov genome.gov](https://www.genome.gov/genetics-glossary/Microbiome?utm_source=chatgpt.com)  

**20** [Microbiome](https://www.genome.gov/genetics-glossary/Microbiome?utm_source=chatgpt.com)

[pubmed.ncbi.nlm.nih.gov pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/?term=NCT05938920&utm_source=chatgpt.com)  

**23** [A generative AI-discovered TNIK inhibitor for idiopathic pulmonary fibrosis: a randomized phase 2a trial - PubMed](https://pubmed.ncbi.nlm.nih.gov/?term=NCT05938920&utm_source=chatgpt.com)

**38** [Graph Convolutional Networks for Drug Response Prediction - PubMed](https://pubmed.ncbi.nlm.nih.gov/33606633/?utm_source=chatgpt.com)

[academic.oup.com academic.oup.com](https://academic.oup.com/bib/article/23/6/bbac409/6713511?utm_source=chatgpt.com)  

**27** [BioGPT: generative pre-trained transformer for biomedical text generation and mining | Briefings in Bioinformatics | Oxford Academic](https://academic.oup.com/bib/article/23/6/bbac409/6713511?utm_source=chatgpt.com)

[who.int who.int](https://www.who.int/news/item/18-01-2024-who-releases-ai-ethics-and-governance-guidance-for-large-multi-modal-models?utm_source=chatgpt.com)  

**28** [WHO releases AI ethics and governance guidance for large multi-modal models](https://www.who.int/news/item/18-01-2024-who-releases-ai-ethics-and-governance-guidance-for-large-multi-modal-models?utm_source=chatgpt.com)

[english.nmpa.gov.cn english.nmpa.gov.cn](https://english.nmpa.gov.cn/2026-08/20/c_1210673.htm?utm_source=chatgpt.com)  

**30** [Implementation Opinions on "Artificial Intelligence + Drug Regulation" issued by NMPA](https://english.nmpa.gov.cn/2026-08/20/c_1210673.htm?utm_source=chatgpt.com)

**34** [Implementation Opinions of NMPA on "Artificial Intelligence + Drug Regulation"](https://english.nmpa.gov.cn/2026-08/20/c_1210674.htm?utm_source=chatgpt.com)

[ema.europa.eu ema.europa.eu](https://www.ema.europa.eu/en/use-artificial-intelligence-ai-medicinal-product-lifecycle-scientific-guideline?utm_source=chatgpt.com)  

**31** [Use of Artificial Intelligence (AI) in the medicinal product lifecycle](https://www.ema.europa.eu/en/use-artificial-intelligence-ai-medicinal-product-lifecycle-scientific-guideline?utm_source=chatgpt.com)

[samr.gov.cn samr.gov.cn](https://www.samr.gov.cn/wljys/gzzd/art/2023/art_3ef1e889c1e644d4b65b5f5c7f432386.html?utm_source=chatgpt.com)  

**32** [中华人民共和国个人信息保护法](https://www.samr.gov.cn/wljys/gzzd/art/2023/art_3ef1e889c1e644d4b65b5f5c7f432386.html?utm_source=chatgpt.com)

[wjw.wuxi.gov.cn wjw.wuxi.gov.cn](https://wjw.wuxi.gov.cn/doc/2024/06/04/4323063.shtml?utm_source=chatgpt.com)  

**33** [中华人民共和国人类遗传资源管理条例（2024修订）](https://wjw.wuxi.gov.cn/doc/2024/06/04/4323063.shtml?utm_source=chatgpt.com)

[biorxiv.org biorxiv.org](https://www.biorxiv.org/content/10.1101/2025.02.20.639398v1?utm_source=chatgpt.com)  

**35** [Tahoe-100M: A Giga-Scale Single-Cell Perturbation Atlas for Context-Dependent Gene Function and Cellular Modeling | bioRxiv](https://www.biorxiv.org/content/10.1101/2025.02.20.639398v1?utm_source=chatgpt.com)

[mlanthology.org mlanthology.org](https://mlanthology.org/iclr/2023/zhou2023iclr-unimol/?utm_source=chatgpt.com)  

**36** [Uni-Mol: A Universal 3D Molecular Representation Learning Framework | ML Anthology](https://mlanthology.org/iclr/2023/zhou2023iclr-unimol/?utm_source=chatgpt.com)

**37** [DiffDock: Diffusion Steps, Twists, and Turns for Molecular Docking | ML Anthology](https://mlanthology.org/iclr/2023/corso2023iclr-diffdock/?utm_source=chatgpt.com)

[digital-strategy.ec.europa.eu digital-strategy.ec.europa.eu](https://digital-strategy.ec.europa.eu/en/policies/1-million-genomes?utm_source=chatgpt.com)  

**41** [European '1+ Million Genomes' initiative](https://digital-strategy.ec.europa.eu/en/policies/1-million-genomes?utm_source=chatgpt.com)

Sources scanned · 564

[nature.com nature.com](https://www.nature.com/articles/s41586-024-07487-w)  

Accurate structure prediction of biomolecular interactions ...

by J Abramson · 2024 · Cited by 19075 — Here we describe our AlphaFold 3 model with a substantially updated diffusion-based architecture that is capable of predicting the joint ...Read more

A foundation model for clinician-centered drug repurposing

by K Huang · 2024 · Cited by 345 — TxGNN uses a graph neural network and metric learning module to rank drugs as potential indications and contraindications for 17,080 diseases.

Investigating whether deep learning models for co-folding ...

by MR Masters · 2025 · Cited by 113 — AlphaFold3, and others have shown high-quality results on predicting the structures of proteins interacting with small-molecules, nucleic-acids ...

Enhancing link prediction in biomedical knowledge graphs ...

by EY Hu · 2026 · Cited by 11 — TxGNN is a state-of-the-art graph neural network model designed to predict drug–disease relationships in zero-shot scenarios, which builds ...Read more

Assessing the potential of deep learning for protein–ligand ...

by A Morehead · 2026 · Cited by 23 — Accurate structure prediction of biomolecular interactions with AlphaFold 3. Nature 630, 493–500 (2024).

leveraging large language model to prioritize Alzheimer's ...

by M Li · 2026 · Cited by 1 — TxGNN is a graph model designed for zero-shot drug repurposing, enabling the identification of potential therapeutic candidates even for ...Read more

DynamicBind: predicting ligand-specific protein ...

by W Lu · 2024 · Cited by 305 — AlphaFold, which leads the way in the prediction of nearly all structures in the human proteome, however, typically generates only a few ...Read more

Inferring molecular inhibition potency with AlphaFold ...

by PF Oliveira · 2024 · Cited by 9 — This model captures the relationship between ligand properties and the unique structural features of various target proteins, enabling ...Read more

Benchmarking all-atom biomolecular structure prediction ...

by S Xu · 2025 · Cited by 58 — As similarity increases, the model's ability to accurately model ligands also improves, with AlphaFold 3 showing a slight performance advantage.Read more

The influence of ligands on AlphaFold3 prediction of cryptic ...

by M Lazou · 2026 · Cited by 1 — Herein we examine the use of AlphaFold 3 (AF3) for generating realistic conformational ensembles that include known cryptic pockets. We find ...Read more

Artificial Intelligence Methodology in Structural Biology

AlphaFold3 generates protein-ligand structural ensembles … in cryptic-site. AlphaFold 3 represents a breakthrough in predicting the 3D structures of complexes ...

3D molecular generative framework for interaction-guided ...

by W Zhung · 2024 · Cited by 104 — To address these issues, we propose an interaction-aware 3D molecular generative framework that enables interaction-guided drug design inside ...Read more

Accurate structure prediction of biomolecular interactions ...

by J Abramson · 2024 · Cited by 19075 — In this paper, we describe our AlphaFold 3 model with a substantially. 29 updated diffusion-based architecture, which is capable of joint ...Read more

scGPT: toward building a foundation model for single-cell multi ...

Through further adaptation of transfer learning, scGPT can be optimized to achieve superior performance across diverse downstream applications.

Large-scale foundation model on single-cell transcriptomics

by M Hao · 2024 · Cited by 959 — Here we developed a large pretrained model scFoundation, also named 'xTrimoscFoundationα', with 100 million parameters covering about 20,000 ...Read more

CellFM: a large-scale foundation model pre-trained on ...

by Y Zeng · 2025 · Cited by 135 — Large-scale foundation model on single-cell transcriptomics. Nat. methods 21, 1481–1491 (2024). Article CAS PubMed Google Scholar. Yang, X ...Read more

scLong: a billion-parameter foundation model for capturing ...

by D Bai · 2026 · Cited by 17 — Foundation models have shown great promise in analyzing single-cell transcriptomics data. Pretrained on large-scale single-cell RNA sequencing ( ...Read more

Transfer learning enables predictions in network biology | Nature

https://www.nature.com/articles/s41586-023-06139-9

Predicting transcriptional outcomes of novel multigene perturbations with GEARS | Nature Biotechnology

https://www.nature.com/articles/s41587-023-01905-6

Predicting the effects of multigene perturbations | Nature Reviews Genetics

\* Research Highlight \* Published: 19 September 2023 Genetic screens PREDICTING THE EFFECTS OF MULTIGENE PERTURBATIONS \* Henry Ertl^{1} Nature Reviews Genetics volume 24, page 736 (2023) Large-s...

Benchmarking algorithms for generalizable single-cell perturbation response prediction | Nature Methods

ABSTRACT Single-cell perturbation technologies enable systematic investigation of gene functions and regulatory networks with single-cell resolution. However, performing large-scale and combinatorial...

Predicting transcriptional responses to novel chemical perturbations using deep generative model for drug discovery | Nature Communications

by X Qi · 2024 · Cited by 109 — Here we present PRnet, which is a flexible and scalable perturbation-conditioned deep generative model for predicting transcriptional responses ...Read more

Pharmacogenomics polygenic risk score for drug response prediction using PRS-PGx methods | Nature Communications

by S Zhai · 2022 · Cited by 69 — We propose a shift from disease PRS to PGx PRS approaches by simultaneously modeling both the prognostic and predictive effects and further make ...Read more

Advancing regulatory variant effect prediction with ...

by Ž Avsec · 2026 · Cited by 361 — AlphaGenome achieved SOTA performance on 22 of 24 genome track prediction tasks and 25 of 26 variant effect prediction tasks.

DeepMind's new genome 'atlas' charts effects of all nine ...

6 days ago — AlphaGenome forecasts the consequences of altering every single DNA letter in the human genome. 2026 DeepMind's new genome 'atlas' charts ...

Advancing regulatory variant effect prediction with ...

28 Jan 2026 — Advancing regulatory variant effect prediction with AlphaGenome ; Journal: Nature ; Published: 2026-01-28 ; DOI · 10.1038/s41586-025-10014-0.Read more

Decoding immune signaling landscapes

by OF Fagbohun · 2026 — AlphaGenome as a unified, multimodal framework that can predict thousands of functional genomic tracks and variant effects up to single-base- ...

The AlphaGenome deep learning model predicts effects of ...

by D Gankin · 2026 — study published in Nature, DeepMind released AlphaGenome1, a deep learning model that aims to predict the effects of variants on regulation.Read more

Predicting non-coding variant effects with AlphaGenome

by AE Murphy · 2026 — AlphaGenome is a recently developed sequence-to-function model that leverages megabase-scale genomic context to predict diverse regulatory activities and ...

How DeepMind's genome AI could help solve rare-disease ...

30 Jan 2026 — Hackathons using AlphaGenome and other AI models are hunting down the genetic causes of devastating conditions that have evaded diagnosis.

Large-scale chemical language representations capture molecular structure and properties | Nature Machine Intelligence

https://www.nature.com/articles/s42256-022-00580-7

Generation of 3D molecules in pockets via a language model | Nature Machine Intelligence

Generation of 3D molecules in pockets via a language model Download PDF Download PDF \* Article \* Open access \* Published: 15 January 2024 GENERATION OF 3D MOLECULES IN POCKETS VIA A LANGUAGE MODE...

Improving de novo molecular design with curriculum learning | Nature Machine Intelligence

\* Article \* Published: 22 June 2022 IMPROVING DE NOVO MOLECULAR DESIGN WITH CURRICULUM LEARNING \* Jeff Guo ORCID: orcid.org/0000-0002-4633-3199^{1}^{ na1}, \* Vendy Fialková^{1}^{ na1}, \* Juan Dieg...

Multi-omics single-cell data integration and regulatory ...

by ZJ Cao · 2022 · Cited by 720 — Hereby, we introduce GLUE (graph-linked unified embedding), a modular framework for integrating unpaired single-cell multi-omics data and ...Read more

From virtual patients to digital twins in immuno-oncology

by H Wang · 2024 · Cited by 121 — From virtual patients to digital twins in immuno-oncology: lessons learned from mechanistic quantitative systems pharmacology modeling.Read more

The GLUE that holds omics layers together

by L Koch · 2022 — A new study presents GLUE (graph-linked unified embedding), a generalizable computational framework for integrating unpaired single-cell ...

Digital Twin models to address long-term treatment ...

by I Elsayed · 2026 — Digital Twins, harnesses recent advances in computational modelling to predict and eventually manage treatment toxicities via a personalised ...

Mosaic integration and knowledge transfer of single-cell ...

by Z He · 2024 · Cited by 98 — Multi-omics single-cell data integration and regulatory inference with graph-linked embedding. Nat. Biotechnol. 40, 1458–1466 (2022).Read more

Immune digital twins for complex human pathologies

by A Niarakis · 2024 · Cited by 112 — clinical validation will allow for the iterative improvement of human immune system models.

Interpretable modality-aware mapping of gene regulation ...

by Y Wang · 2026 · Cited by 2 — Multi-omics single-cell data integration and regulatory inference with graph-linked embedding. Nat. Biotechnol. 40, 1458–1466 (2022).Read more

Multi-omics and artificial intelligence for precision drug ...

by Y Liu · 2026 · Cited by 21 — This review offers an in-depth analysis of multiomics applications across the drug development pipeline, covering target deconvolution, drug ...

A unified computational framework for single-cell data ...

by K Cao · 2022 · Cited by 126 — Multi-omics single-cell data integration and regulatory inference with graph-linked embedding. Nat. Biotechnol. 40, 1458–1466 (2022).Read more

Large language models forecast patient health trajectories ...

by N Makarov · 2025 · Cited by 67 — Generative artificial intelligence empowers digital twins in drug discovery and clinical trials. Expert Opin. Drug Discov. 19, 33–42 (2024).Read more

Modal-nexus auto-encoder for multi-modality cellular data ...

by Z Tang · 2024 · Cited by 45 — Multi-omics single-cell data integration and regulatory inference with graph-linked embedding. Nat. Biotechnol. 40, 1458–1466 (2022).Read more

AI-driven virtual cell models in preclinical research

by C Ma · 2025 · Cited by 44 — Generative artificial intelligence empowers digital twins in drug discovery and clinical trials. mechanistic quantitative systems pharmacology ...

OmicVerse: a framework for bridging and deepening ...

by Z Zeng · 2024 · Cited by 115 — Multi-omics single-cell data integration and regulatory inference with graph-linked embedding. Nature Biotechnology 40, 1458–1466 (2022).Read more

MRI-based digital twins to improve treatment response of ...

by C Wu · 2025 · Cited by 36 — We developed a practical framework to construct digital twins for predicting and optimizing triple-negative breast cancer (TNBC) response to ...

ARTICLE IN PRESS

by JM Choi · 2026 · Cited by 1 — Multi-omics single-cell data integration and regulatory inference with graph-linked embedding. Nat. Biotechnol. 40, 1458–1466 (2022).

Design specifications for biomedical virtual twins in ...

by U Weirauch · 2025 · Cited by 12 — In healthcare, digital twins (DTs) and virtual twins (VTs) are computer-based models that digitally represent interacting biological systems ...Read more

Knowledge-based inductive bias and domain adaptation ...

by Z Tang · 2024 · Cited by 12 — Multi-omics single-cell data integration and regulatory inference with graph-linked embedding. Nat. Biotechnol. 40, 1458–1466 (2022).Read more

The effectiveness of digital twins in promoting precision ...

by M Shen · 2024 · Cited by 82 — American researchers developed a quantitative systems pharmacology model using digital twins to identify the optimal dosing for aggressive non- ...Read more

A multimodal cross-species comparison of pancreas ...

by K Yang · 2025 · Cited by 13 — Multi-omics single-cell data integration and regulatory inference with graph-linked embedding. Nat. Biotechnol. 40, 1458–1466 (2022).Read more

Advancing the frontier of rare disease modeling: a critical ...

by F Pistollato · 2025 · Cited by 5 — Quantitative systems pharmacology for rare disease drug development. J. Pharm. Sci. 112, 2313–2320 (2023). Article CAS PubMed Google Scholar.Read more

A small-molecule TNIK inhibitor targets fibrosis in preclinical and clinical models | Nature Biotechnology

https://www.nature.com/articles/s41587-024-02143-0

Pharmacogenomics | Nature Communications

Pharmacogenomics polygenic risk score for drug response prediction using PRS-PGx methods. To try to predict an individual's drug response using genetic data ...Read more

Improving polygenic risk score based drug response ...

by Y Cheng · 2025 · Cited by 2 — Pharmacogenomics polygenic risk score for drug response prediction using PRS-PGx methods. Nat. Commun. 13, 5278 (2022). Article CAS PubMed ...Read more

Predictive medicine articles within Nature Communications

Pharmacogenomics polygenic risk score for drug response prediction using PRS-PGx methods. To try to predict an individual's drug response using genetic data ...Read more

Leveraging large-scale biobank EHRs to enhance ...

by MC Sadler · 2025 · Cited by 34 — We also found polygenic risk scores to predict drug response, though they explained less than 2% of the variance. pharmacogenetics (PGx) ...

Maternal influences on infant gut microbiome and health

by T Sinha · 2026 · Cited by 2 — We observe that the maternal gut microbiome undergoes only subtle changes during pregnancy and postpartum, influenced by diet, infections and ...

Articles in 2022 | Nature Communications

... 2022. Pharmacogenomics polygenic risk score for drug response prediction using PRS-PGx methods. To try to predict an individual's drug response using genetic ...

The Estonian Biobank's journey from ...

by L Milani · 2025 · Cited by 97 — PRS—polygenic risk scores for CVD (cardiovascular disease) or breast cancer, PGx—pharmacogenetics—novel predicted LoF (loss-of-function) ...

Drug discovery articles within Nature Communications

Pharmacogenomics polygenic risk score for drug response prediction using PRS-PGx methods. To try to predict an individual's drug response using genetic data ...

Protective alleles and precision healthcare in crewed ...

by LA Rutter · 2024 · Cited by 15 — Spaceflight pharmacogenomics (SPGx) is the study of gene variants that influence the regulation of drug metabolism in space operations. The drug ...Read more

Genomes in clinical care | npj Genomic Medicine

by O Riess · 2024 · Cited by 35 — Using the sequenced genome as a platform for pharmacogenomic (PGx) testing in clinical practice to understand how variations in the genome ...Read more

RegFormer: a single-cell foundation model powered by ...

by L Hu · 2026 · Cited by 8 — RegFormer is a foundation model for single-cell transcriptomics that integrates gene regulatory network (GRN) priors with a state space ...Read more

Machine-learning model makes predictions about network biology | Nature

\* RESEARCH BRIEFINGS \* 31 May 2023 MACHINE-LEARNING MODEL MAKES PREDICTIONS ABOUT NETWORK BIOLOGY A deep-learning model called Geneformer has been developed and pretrained using about 30 million si...

Single-cell foundation models: bringing artificial ...

by S Baek · 2025 · Cited by 75 — a large-scale deep learning model. Large-scale foundation model on single-cell transcriptomics. Nat. Methods 21, 1481–1491 (2024).

AI identifies gene interactions to speed up search for treatment targets | Nature

TRANSCRIPT Benjamin Thompson Welcome back to the Nature Podcast. This week, the AI that identifies gene interactions... Nick Petrić Howe ...and assessing the impact of rocket noise on wildlife. I'...

Scaling and quantization of large-scale foundation model enables resource-efficient predictions in network biology | Nature Computational Science

Scaling and quantization of large-scale foundation model enables resource-efficient predictions in network biology Download PDF Download PDF \* Article \* Open access \* Published: 27 March 2026 SCA...

scPML: pathway-based multi-view learning for cell type annotation from single-cell RNA-seq data | Communications Biology

scPML: pathway-based multi-view learning for cell type annotation from single-cell RNA-seq data Download PDF Download PDF \* Article \* Open access \* Published: 14 December 2023 SCPML: PATHWAY-BASE...

Biologically informed deep learning to query gene programs in single-cell atlases | Nature Cell Biology

Biologically informed deep learning to query gene programs in single-cell atlases \* Technical Report \* Open access \* Published: 02 February 2023 BIOLOGICALLY INFORMED DEEP LEARNING TO QUERY GENE PR...

Single-cell biological network inference using a heterogeneous graph transformer | Nature Communications

Single-cell biological network inference using a heterogeneous graph transformer Download PDF Download PDF \* Article \* Open access \* Published: 21 February 2023 SINGLE-CELL BIOLOGICAL NETWORK INF...

A self-supervised deep learning method for data-efficient training in genomics | Communications Biology

A self-supervised deep learning method for data-efficient training in genomics Download PDF Download PDF \* Article \* Open access \* Published: 11 September 2023 A SELF-SUPERVISED DEEP LEARNING MET...

Discovery of candidate therapeutic targets with Geneformer | Nature Protocols

\* Protocol \* Published: 23 April 2026 DISCOVERY OF CANDIDATE THERAPEUTIC TARGETS WITH GENEFORMER \* Yujie Zhang (张毓杰) ORCID: orcid.org/0000-0002-1017-0316^{1,2,3}, \* Madhavan S. Venkatesh^{1,2,4}...

De novo design of protein interactions with learned surface fingerprints | Nature

De novo design of protein interactions with learned surface fingerprints Download PDF Download PDF \* Article \* Open access \* Published: 26 April 2023 DE NOVO DESIGN OF PROTEIN INTERACTIONS WITH L...

A generalizable Cas9/sgRNA prediction model using machine transfer learning with small high-quality datasets | Nature Communications

A generalizable Cas9/sgRNA prediction model using machine transfer learning with small high-quality datasets Download PDF Download PDF \* Article \* Open access \* Published: 07 September 2023 A GEN...

Language models for biological research: a primer | Nature Methods

REFERENCES 1. Thirunavukarasu, A. J. et al. Large language models in medicine. Nat. Med. 29, 1930–1940 (2023). 2. OpenAI et al. GPT-4 technical report. Preprint at https://doi.org/10.48550/arXiv.230...

A knowledge-driven framework for predicting single-cell responses for unprofiled drugs | Nature Machine Intelligence

\* … \* Weidi Xie ORCID: orcid.org/0009-0002-8609-6826^{1,2} Show authors Nature Machine Intelligence (2026) Save article View saved research \* 12k Accesses \* 24 Altmetric \* Metrics details ABST...

Modelling drug-induced cellular perturbation responses with a biologically informed dual-branch transformer | Nature Machine Intelligence

Modelling drug-induced cellular perturbation responses with a biologically informed dual-branch transformer Download PDF Download PDF \* Article \* Open access \* Published: 26 January 2026 MODELLIN...

DeepInsight-3D architecture for anti-cancer drug response prediction with deep-learning on multi-omics | Scientific Reports

DeepInsight-3D architecture for anti-cancer drug response prediction with deep-learning on multi-omics Download PDF Download PDF \* Article \* Open access \* Published: 11 February 2023 DEEPINSIGHT-...

scDrugMap: benchmarking large foundation models for drug response prediction | Nature Communications

scDrugMap: benchmarking large foundation models for drug response prediction \* Article \* Open access \* Published: 11 December 2025 SCDRUGMAP: BENCHMARKING LARGE FOUNDATION MODELS FOR DRUG RESPONSE...

An interpretable deep learning framework for genome-informed precision oncology | Nature Machine Intelligence

To this end, we developed a computational framework consisting of two components: (1) a representation-learning component, which learns a representation of the cellular signalling systems when perturb...

Discovery of drug–omics associations in type 2 diabetes with generative deep-learning models | Nature Biotechnology

ABSTRACT The application of multiple omics technologies in biomedical cohorts has the potential to reveal patient-level disease characteristics and individualized response to treatment. However, the...

Genomics

AlphaGenome forecasts the consequences of altering every single DNA letter in the human genome. is shown to be a scalable and flexible tool for genetic variant ...

Pre-training genomic language model with variants for ...

by T Liu · 2026 · Cited by 8 — Advancing regulatory variant effect prediction with AlphaGenome. Nature 649, 1206–1218 (2026). Article Google Scholar. François, A. et al ...Read more

DeepMind's new AlphaGenome AI tackles the 'dark matter' ...

by E Callaway · 2025 · Cited by 16 — Tool aims to solve the mystery of non-coding sequences — but is still in its infancy.

ResGen is a pocket-aware 3D molecular generation model based on parallel multiscale modelling | Nature Machine Intelligence

\* Published: 07 September 2023 RESGEN IS A POCKET-AWARE 3D MOLECULAR GENERATION MODEL BASED ON PARALLEL MULTISCALE MODELLING \* Odin Zhang^{1,2}, \* Jintu Zhang^{1}, \* Jieyu Jin^{1}, \* Xujun Zhang^{1}...

Structure-inducing pre-training | Nature Machine Intelligence

Structure-inducing pre-training \* Article \* Open access \* Published: 01 June 2023 STRUCTURE-INDUCING PRE-TRAINING \* Matthew B. A. McDermott ORCID: orcid.org/0000-0001-6048-9707^{1,2}, \* Brendan Y...

A multilevel generative framework with hierarchical self-contrasting for bias control and transparency in structure-based ligand design | Nature Machine Intelligence

\* Article \* Published: 05 December 2022 A MULTILEVEL GENERATIVE FRAMEWORK WITH HIERARCHICAL SELF-CONTRASTING FOR BIAS CONTROL AND TRANSPARENCY IN STRUCTURE-BASED LIGAND DESIGN \* Lucian Chan^{1}, \*...

Large language model for molecular chemistry | Nature Computational Science

\* Research Highlight \* Published: 23 January 2023 Cheminformatics LARGE LANGUAGE MODEL FOR MOLECULAR CHEMISTRY \* Jie Pan^{1} Nature Computational Science volume 3, page 5 (2023) Save article Vi...

Language models can learn complex molecular distributions | Nature Communications

Language models can learn complex molecular distributions Download PDF Download PDF \* Article \* Open access \* Published: 07 June 2022 LANGUAGE MODELS CAN LEARN COMPLEX MOLECULAR DISTRIBUTIONS \*...

Optimizing molecules using efficient queries from property evaluations | Nature Machine Intelligence

Optimizing molecules using efficient queries from property evaluations Download PDF Download PDF \* Article \* Published: 30 December 2021 OPTIMIZING MOLECULES USING EFFICIENT QUERIES FROM PROPERTY...

Accurate prediction of molecular properties and drug targets using a self-supervised image representation learning framework | Nature Machine Intelligence

Accurate prediction of molecular properties and drug targets using a self-supervised image representation learning framework Download PDF Download PDF \* Article \* Published: 17 November 2022 ACCU...

Multitask joint strategies of self-supervised representation learning on biomedical networks for drug discovery | Nature Machine Intelligence

Multitask joint strategies of self-supervised representation learning on biomedical networks for drug discovery Download PDF Download PDF \* Article \* Open access \* Published: 24 April 2023 MULTIT...

Leveraging large language models for predictive chemistry | Nature Machine Intelligence

Leveraging large language models for predictive chemistry Download PDF Download PDF \* Article \* Open access \* Published: 06 February 2024 LEVERAGING LARGE LANGUAGE MODELS FOR PREDICTIVE CHEMISTRY...

A generalized-template-based graph neural network for accurate organic reactivity prediction | Nature Machine Intelligence

\* Published: 15 September 2022 A GENERALIZED-TEMPLATE-BASED GRAPH NEURAL NETWORK FOR ACCURATE ORGANIC REACTIVITY PREDICTION \* Shuan Chen ORCID: orcid.org/0000-0002-5528-5272^{1} & \* Yousung Jung O...

AI serves up target and inhibitor for lung fibrosis | Nature Reviews Drug Discovery

\* RESEARCH HIGHLIGHT \* 20 March 2024 AI SERVES UP TARGET AND INHIBITOR FOR LUNG FIBROSIS By \* Katie Kingwell Idiopathic pulmonary fibrosis (IPF) is a progressive and usually fatal lung disease f...

Precision oncology in the age of AI: lessons from AI-driven drug discovery and clinical translation | BJC Reports

Precision oncology in the age of AI: lessons from AI-driven drug discovery and clinical translation Download PDF Download PDF \* Perspective \* Open access \* Published: 15 April 2026 PRECISION ONCO...

2024: research in review | Nature Biotechnology

2024: research in review \* Editorial \* Published: 04 December 2024 2024: RESEARCH IN REVIEW Nature Biotechnology volume 42, pages 1755–1756 (2024) Nature Biotechnology editors pick their favorite...

[single-market-economy.ec.europa.eu single-market-economy.ec.europa.eu](https://single-market-economy.ec.europa.eu/single-market_en)  

Single market

The new single market strategy is the European Commission's plan to make the single market simpler, seamless and strong – unlocking its full potential for ...Read more

[youtube.com youtube.com](https://www.youtube.com/watch?v=xvyxEaoSd1s)  

David Gilmour - A Single Spark (Official Audio)

Apr 18, 2025 — David Gilmour - A Single Spark (Official Audio) on vinyl, CD and digital. 146K views1 year ago

Best Palworld 1.0 Single Player World Settings to Enjoy ...

Jul 11, 2026 — This is a video guide on the best Palworld 1.0 single player world settings to enjoy and beat the game. Useful Links: Best Pals Breeding ...

Fousheé - single af (Official Video)

12 Feb 2021 — Fousheé - "single af" out now!: https://smarturl.it/xsingleaf Check it out: https://www.fousheesingleaf.com Follow Fousheé: Tik Tok: ...

What is the single best thing we can do for our health?

2 Dec 2011 — A Doctor-Professor answers the old question "What is the single best thing we can do for our health" in a completely new way.

How Not to Feel Too Bad About Being Single

Dec 17, 2025 — I feel like it's different when you've been single your entire life. It just grates and grates and grates at you. every year just gets harder ...

Selena Gomez - Single Soon (Official Music Video)

24 Aug 2023 — Music video by Selena Gomez performing Single Soon. (Official Music Video) Official Music Video 2023

Fiona Apple - Every Single Night (Official Video)

11 Jun 2012 — Fiona Apple's official music video for "Every Single Night” Listen to Fiona Apple: https://FionaApple.lnk.to/listenYD Subscribe to the ...

mgk - twin flame (Official Lyric Video) - YouTube

Stream twin flame from 'mainstream sellout (life in pink deluxe)' available now: https://mgk.lnk.to/MSDeluxe Follow MGK: ...

Getting Started With Trauma-Informed Practices - YouTube

When teachers use strategies tailored to children who have experienced trauma, all students reap the emotional and academic benefits.

(Do It On My) Twin Bed - SNL - YouTube

When you're home for the holidays, sometimes you've got to get busy on your childhood twin bed. [Season 39, 2013] #SNL Subscribe to SNL ...

Reid Hoffman meets his AI twin - Full - YouTube

I recently created an AI version of myself—REID AI—and recorded a Q&A to see how this digital twin might challenge me in new ways.

Informed Consent for Research: What to Expect - YouTube

This video provides basic information about informed consent and what to information you'll get to help you decide whether to volunteer for ...

twin - YouTube

Provided to YouTube by OA Entertainment/Columbia twin · JENNIE Ruby ℗ 2025 Columbia Records, a Division of Sony Music Entertainment, ...

Aphex Twin - T69 Collapse - YouTube

WARNING: CONTAINS STROBING. Taken from Aphex Twin's 'Collapse' EP out now on Warp. Video by Weirdcore. Order 'Collapse' EP: ...

The Front Bottoms "Twin Size Mattress" Official Music Video - YouTube

Check out our new video for "Twin Size Mattress", from our new album TALON OF THE HAWK, out now! Purchase Talon of the Hawk below - iTunes: ...

What is a Digital Twin? - YouTube

... digital twins, where virtual replicas of physical objects and systems are used to make better decisions. From component twins to system twins ...

Physiologically-based Pharmacokinetic Modeling (32of35) ...

2 Apr 2020 — Physiologically-based Pharmacokinetic Modeling (32of35) Complex Generics – Sep. ... PBPK to Guide Study Design and Product Development for ... Read more

US FDA Draft Guidance 2025: Artificial Intelligence in Pharma ...

In this video, we simplify the FDA's draft guidance on the use of AI to support regulatory decision-making for drugs and biologics. This ...

Massive Attack - Protection ft. Tracey Thorn - YouTube

Official video of Massive Attack performing Protection from the album Protection. Massive Attack Protection (Remastered 2006)

What are Deep Agents?

31 Jul 2025 — Managed Deep Agents explained in 20 minutes · What Are Deep Agents? (And Why They're Better Than Regular Agents) · Hierarchical multi-agent ...Read more

Gradient descent, how neural networks learn

16 Oct 2017 — Gradient descent, how neural networks learn | Deep Learning Chapter 2 ... 1: Introduction to Neural Networks and Deep Learning; Training Deep NNs.Read more

Introduction to Deep Research

2 Feb 2025 — Mark Chen, Josh Tobin, Neel Ajjarapu, and Isa Fulford introduce and demo deep research from Tokyo.

What is Multimodal RAG? Unlocking LLMs with Vector ...

16 Feb 2026 — Can AI handle text, images, and more? Multimodal RAG, where LLMs and vector databases work together to transform AI retrieval. Discover hybrid ...

The Hungry Microbiome: why resistant starch is good for you

9 Apr 2014 — This animation shows how resistant starch moves through the intestine, feeds the healthy bacteria of the gut Microbiome and helps prevent ...

What is the gut microbiome?

30 Oct 2021 — Share your videos with friends, family, and the world.

2025 — Year in Search

8 Dec 2025 — This year, we searched for ways to rediscover, reinvent, and rethink what's possible. See how people reimagined their worlds in 2025.

The Gut Microbiome Explained: Why It's a Big Deal in ...

5 Feb 2026 — Emerging studies suggest the microbiome may influence cancer risk, immune function, treatment response, and side effects from therapies like ...

THE GAME AWARDS 2025: Official 4K60FPS Livestream

11 Dec 2025 — Celebrate the best and see what's next in video games at The Game Awards 2025, live from Peacock Theater in Los Angeles.

The Invisible Universe Of The Human Microbiome

5 Nov 2013 — There are 10 times more cells from microorganisms like bacteria and fungi in and on our bodies than there are human cells. artist Ben Arthur to ...

Every Hole of the 2025 Final Round with Masters ...

3 Apr 2026 — The strategy, the decisions and the emotions. Relive every hole of Rory McIlroy's 2025 final round, as told by the Masters champion himself.

What is a microbiome?

9 May 2017 — A microbiome is the community of micro-organisms living together in a particular habitat. Humans, animals and plants have their own unique ...

2025

9 Jan 2026 — It's the 31st of December and im thinking about the past year, watching back the show we filmed in Dublin, and a whole bunch of other stuff ...

How Bacteria Rule Over Your Body – The Microbiome

5 Oct 2017 — I literally was eating pizza while watching this and decided to put it away to show my bacteria im still in charge.Read more

FULL MATCH: 2025 Men's Royal Rumble Match

21 Jan 2026 — John Cena competes in his last Royal Rumble Match, with Superstars like Jey Uso, Roman Reigns, Penta, Jacob Fatu, CM Punk, Seth Rollins and ...

Introducing Meta - YouTube

Meta is helping build a future where people have more ways to play and connect in the metaverse. Welcome to the next chapter of social ...

Katie Melua - Nine Million Bicycles - YouTube

Katie Melua's Music Video for 'Nine Million Bicycles' taken from the album 'Piece By Piece'. Amazon: http://amzn.to/AiyHPc iTunes: ...

Bastille - Million Pieces ft. The Chamber Orchestra Of London (Live)

#DoomDays Music video by Bastille performing Million Pieces. © 2019 Virgin Records Limited. Bastille - Million Pieces ft. The Chamber ...

Design Ticketmaster w/ a Ex-Meta Staff Engineer - YouTube

System Design Interview: Design Ticketmaster w/ a Ex-Meta Staff Engineer · Comments.

Million Dollar Baby (2004) Official Trailer - Hilary Swank ... - YouTube

Million Dollar Baby (2004) Official Trailer - Hilary Swank, Clint Eastwood Movie HD.

Exclusive: We tried Meta's AR glasses with Mark Zuckerberg

Project Orion is Meta's first pair of true AR glasses. They project hologram onto the world and are controlled with a neural wristband.

They Spent $10 Million Perfecting This Fried Chicken... and I Stole It.

... 100% gluten free. In this video I'm breaking down everything that makes it work. Proper whole bird butchery, a brined and double fried ...

Tommy Richman - MILLION DOLLAR BABY (Official Music Video)

Official Music Video for “MILLION DOLLAR BABY” by Tommy Richman - available everywhere now: https://tommyrichman.ffm.to/MILLIONDOLLARBABY ...

is VR finally good now? - YouTube

The thing is, while the Steam Frame is gonna trash the Quest, the AI Bros that breathe RAM just might trash the Frame.

We aren't ready for Meta glasses - YouTube

Zuckerberg got tired of stealing your privacy himself, so he invented Meta glasses so your friends could help him do it too.

Mark Rober's $60 Million Science Experiment | TED - YouTube

Mark Rober (@MarkRober) spent years trying to land a rover on Mars. Now, the former NASA engineer turned science YouTuber with millions of ...

Learning Adaptive Perturbation-Conditioned Contexts for ...

Predicting high-dimensional transcriptional responses to genetic perturbations. AdaPert consistently outperforms existing baselines and ...

A Million Dreams (from The Greatest Showman - P!nk - YouTube

The official audio of "A Million Dreams" by P!nk from the album 'The Greatest Showman: Reimagined'. The Greatest Showman: Reimagined ...

[srb.europa.eu srb.europa.eu](https://www.srb.europa.eu/en/node/1)  

Single Resolution Board (SRB) - European Union

The SRB tries to ensure an orderly resolution of failing banks with minimum impact on the real economy, the financial system, and the public finances

[cultofpedagogy.com cultofpedagogy.com](https://www.cultofpedagogy.com/single-point-rubric/)  

Meet the Single Point Rubric

4 Feb 2015 — The practice of using single point rubrics is slowly but surely catching on. Try one for yourself and let us see it!

[enisa.europa.eu enisa.europa.eu](https://www.enisa.europa.eu/topics/product-security/single-reporting-platform-srp)  

Single Reporting Platform (SRP) | ENISA - European Union

3 days ago — Designed to simplify EU reporting obligations, the SRP allows users to report once through a single platform and communicate the relevant ...Read more

[play.google.com play.google.com](https://play.google.com/store/apps/details?hl=en_US&id=com.single.dating)  

Single - Apps on Google Play

Aug 25, 2026 — Single is a dating app designed to help people meet and connect through smart matching. Users create a profile, explore potential matches ...Read more

[jamesclear.com jamesclear.com](https://jamesclear.com/great-speeches/the-danger-of-a-single-story-by-chimamanda-ngozi-adichie)  

"The Danger of a Single Story" by Chimamanda Ngozi ...

I would like to tell you a few personal stories about what I like to call “the danger of the single story.” In this single story, there was no possibility of ...

[unodc.org unodc.org](https://www.unodc.org/pdf/convention_1961_en.pdf)  

Single Convention on Narcotic Drugs, 1961

The United Nations Conference for the Adoption of a Single Convention on Narcotic Drugs met at United Nations Headquarters from 24 January to 25 March 1961. 3.Read more

[github.com github.com](https://github.com/bowang-lab/scgpt)  

bowang-lab/scGPT - GitHub

This is the official codebase for scGPT: Towards Building a Foundation Model for Single-Cell Multi-omics Using Generative AI.

GitHub - bm2-lab/scPerturBench: Single-cell perturbation effects ...

In the perturbation generalization scenario, we assess the ability of models to predict the effects of previously unobserved perturbations within a specific ...

GitHub - kimmo1019/DeepCDR: Cancer Drug Response Prediction via a Hybrid Graph Convolutional Network · GitHub

DEEPCDR Cancer Drug Response Prediction via a Hybrid Graph Convolutional Network This work has been accepted to ECCB2020(slides) and was also published in the journal Bioinformatics. DeepCDR is a...

PRnet: Predicting transcriptional responses to novel ...

PRnet is a flexible and scalable perturbation-conditioned generative model predicting transcriptional responses to unseen complex perturbations at bulk and ...

Awesome Foundation Models for Single-Cell

[2024 Nature Methods] scFoundation: Large Scale Foundation Model on Single-cell Transcriptomics [paper]; [2024 Nature Methods] SATURN: Toward universal cell ...Read more

GitHub - deepmodeling/Uni-Mol: Official Repository for the Uni-Mol Series Methods · GitHub

UNI-MOL2: EXPLORING MOLECULAR PRETRAINING MODEL AT SCALE We present Uni-Mol2 , an innovative molecular pretraining model that leverages a two-track transformer to effectively integrate features at th...

[virtualcellmodels.cziscience.com virtualcellmodels.cziscience.com](https://virtualcellmodels.cziscience.com/model/scgpt)  

scGPT | v1.0 - Virtual Cells Platform - Chan Zuckerberg Initiative

scGPT is a foundation model designed to integrate and analyze large-scale single-cell multi-omics data using a generative pre-trained ...

[biorxiv.org biorxiv.org](https://www.biorxiv.org/content/10.64898/2026.04.01.714123v1.full-text)  

CellBench-LS: Benchmark Evaluation of Single-cell Foundation ...

(Wu et al., 2025) offer early insights into the zero-shot performance of Geneformer and scGPT, showing that classical approaches can still ...

A unified framework enables accessible deployment and ... - bioRxiv

In this study, we provide a systematic and reproducible evaluation of single-cell foundation models (scFMs) across diverse analytical scenarios.

Benchmarking zero-shot single-cell foundation model embeddings ...

We find that zero-shot scFM embeddings underperform the HVG baseline across diverse biological systems, particularly in recovering the ...

Benchmarking AI Models for In Silico Gene Perturbation of Cells

For the DEG\_PCC metric, single-cell foundation models, including scFoundation and scGPT, outperformed all other methods, indicating their ...

Tahoe-100M: A Giga-Scale Single-Cell Perturbation Atlas for Context-Dependent Gene Function and Cellular Modeling | bioRxiv

https://www.biorxiv.org/content/10.1101/2025.02.20.639398v1

Tahoe-100M: A Giga-Scale Single-Cell Perturbation Atlas for Context-Dependent Gene Function and Cellular Modeling | bioRxiv

TAHOE-100M: A GIGA-SCALE SINGLE-CELL PERTURBATION ATLAS FOR CONTEXT-DEPENDENT GENE FUNCTION AND CELLULAR MODELING Jesse Zhang, Airol A Ubas, Richard de Borja, Valentine Svensson, Nicole Thomas, Neha...

Tahoe-100M: A Giga-Scale Single-Cell Perturbation Atlas for Context-Dependent Gene Function and Cellular Modeling | bioRxiv

TAHOE-100M: A GIGA-SCALE SINGLE-CELL PERTURBATION ATLAS FOR CONTEXT-DEPENDENT GENE FUNCTION AND CELLULAR MODELING Jesse Zhang, Airol A Ubas, Richard de Borja, Valentine Svensson, Nicole Thomas, Neha...

Large Scale Foundation Model on Single-cell ...

2 Jun 2023 — Large Scale Foundation Model on Single-cell Transcriptomics. View ... We developed a large-scale pretrained model scFoundation with 100M ...Read more

PerturbNet predicts single-cell responses to unseen ...

by H Yu · 2022 · Cited by 77 — We present PerturbNet, a deep generative model for predicting the distribution of cell states induced by unseen chemical or genetic ...

scGPT: Towards Building a Foundation Model for Single-Cell Multi ...

We demonstrate that the generative pre-trained transformer, scGPT, effectively captures meaningful biological insights into genes and cells.

scGPT: Towards Building a Foundation Model for Single-Cell Multi ...

We introduce scGPT as the generative pre-trained foundation model in the single-cell domain. The core model has stacked transformer layers with ...

Tahoe-x1: Scaling Perturbation-Trained Single-Cell Foundation Models to 3 Billion Parameters | bioRxiv

TAHOE-X1: SCALING PERTURBATION-TRAINED SINGLE-CELL FOUNDATION MODELS TO 3 BILLION PARAMETERS View ORCID ProfileShreshth Gandhi, View ORCID ProfileFarnoosh Javadi, View ORCID ProfileValentine Svensso...

Tahoe-100M: A Giga-Scale Single-Cell Perturbation Atlas for Context-Dependent Gene Function and Cellular Modeling | bioRxiv

DISCUSSION In this study, we present Tahoe-100M, a large-scale single-cell perturbation atlas that far surpasses previous datasets in both breadth and depth, encompassing over 100 million single-cell...

SCALE: Scalable Conditional Atlas-Level Endpoint transport for virtual cell perturbation prediction | bioRxiv

SCALE: SCALABLE CONDITIONAL ATLAS-LEVEL ENDPOINT TRANSPORT FOR VIRTUAL CELL PERTURBATION PREDICTION Shuizhou Chen, Lang Yu, Xueqin Lin, Xinjie Mao, Songming Zhang, Xinyu Gu, Hao Wu, Sheng Xu, Kedu J...

SCALE: Scalable Conditional Atlas-Level Endpoint transport for virtual cell perturbation prediction | bioRxiv

SCALE: SCALABLE CONDITIONAL ATLAS-LEVEL ENDPOINT TRANSPORT FOR VIRTUAL CELL PERTURBATION PREDICTION Shuizhou Chen, Lang Yu, Kedu Jin, Songming Zhang, Hao Wu, Wenxuan Huang, Sheng Xu, Quan Qian, Qin...

PIANO: Probabilistic Inference Autoencoder Networks for multi-Omics enables robust generative modeling of gene expression and scales single-cell integration to 100 million cells | bioRxiv

PIANO ENABLES MODELING DRUG PERTURBATIONS OVER 100 MILLION CANCER CELLS Single-cell transcriptomics data can measure changes in gene expression induced by drug perturbations. The Tahoe-100M dataset p...

Predicting cellular responses to perturbation across diverse contexts with State | bioRxiv

Overall, the performance and flexibility of S tate sets the stage for scaling the development of virtual cell models. 1. INTRODUCTION Therapeutic discovery relies on accurately predicting the impact...

Integrating single-cell and bulk transcriptomic perturbation resources reveals complementary therapeutic spaces for drug repurposing | bioRxiv

ABSTRACT Transcriptome-based drug repurposing can accelerate therapeutic discovery, but is limited by fragmented resources, inconsistent quality control, and reliance on single perturbation databases...

Virtual-cell verification enables self-auditing AI discovery for immune rejuvenation | bioRxiv

2 The RVQ–LLM framework and cross-modal alignment. a, Schematic of the RVQ– LLM pipeline. More than 10^{8} single cells are encoded into continuous latent vectors and quantized through residual vecto...

Inferring virtual cell environments using multi-agent reinforcement learning | bioRxiv

Recent sequencing techniques measure single-cell-level gene expression under specific conditions, either temporally or spatially. Using these datasets, emerging works, such as virtual cells, can learn...

[link.springer.com link.springer.com](https://link.springer.com/article/10.1186/s13059-025-03574-x)  

Zero-shot evaluation reveals limitations of single-cell foundation ...

We propose two hypotheses as to why Geneformer and scGPT underperform zero-shot compared to the tested baselines. First, it could be that the ...

GPDRP: a multimodal framework for drug response prediction with graph transformer | BMC Bioinformatics | Springer Nature Link

GPDRP: A MULTIMODAL FRAMEWORK FOR DRUG RESPONSE PREDICTION WITH GRAPH TRANSFORMER \* Research \* Open access \* Published: 17 December 2023 \* Volume 24, article number 484 (2023) \* Cite this article...

[bm2-lab.github.io bm2-lab.github.io](https://bm2-lab.github.io/scPerturBench-reproducibility/)  

Benchmarking algorithms for generalizable single-cell perturbation ...

linearModel, Perturbation, bioRxiv, 2024, Deep learning-based predictions of gene perturbation effects do not yet outperform simple linear methods ; scGPT ...

[reddit.com reddit.com](https://www.reddit.com/r/bioinformatics/comments/1qu1i1p/where_do_foundation_models_like_geneformer_fit/)  

Where do foundation models like Geneformer fit into scRNA-seq ...

This is where you can get the most accurate predictions, whether it is cell type or gene perturbation. ... Tool to compare single cell foundation ...

[x.com x.com](https://x.com/BiologyAIDaily/status/1923972504059556201)  

Biology+AI Daily on X: "Evaluating Foundation Models for In-Silico ...

Evaluating Foundation Models for In-Silico Perturbation 1．This work introduces scISP, a benchmarking framework for evaluating in-silico ...

[odsc.medium.com odsc.medium.com](https://odsc.medium.com/in-silico-perturbation-meets-single-cell-foundation-models-from-zero-shot-potential-to-fine-tuned-0f1b4da054c4)  

In-Silico Perturbation Meets Single-Cell Foundation Models - Medium

The gating analysis reveals that many perturbations fail before scoring because separability is weak in the model's representation space.

[arxiv.org arxiv.org](https://arxiv.org/abs/2603.02952)  

Sparse autoencoders reveal organized biological knowledge but minimal regulatory logic in single-cell foundation models: a comparative atlas of Geneformer and scGPT

https://arxiv.org/abs/2603.02952

Systematic Evaluation of Single-Cell Foundation Model Interpretability Reveals Attention Captures Co-Expression Rather Than Unique Regulatory Signal

https://arxiv.org/abs/2602.17532

Nephrobase Cell+: Multimodal Single-Cell Foundation Model for Decoding Kidney Biology

https://arxiv.org/abs/2509.26223

Causal Circuit Tracing Reveals Distinct Computational Architectures in Single-Cell Foundation Models: Inhibitory Dominance, Biological Coherence, and Cross-Model Convergence

https://arxiv.org/abs/2603.01752

ChromFound: Towards A Universal Foundation Model for Single-Cell Chromatin Accessibility Data

https://arxiv.org/abs/2505.12638

[en.wikipedia.org en.wikipedia.org](https://en.wikipedia.org/wiki/AlphaGenome)  

AlphaGenome

https://en.wikipedia.org/wiki/AlphaGenome

AlphaFold

https://en.wikipedia.org/wiki/AlphaFold

Trajectory inference

https://en.wikipedia.org/wiki/Trajectory\_inference

Perturb-seq

https://en.wikipedia.org/wiki/Perturb-seq

Critical Assessment of Function Annotation

https://en.wikipedia.org/wiki/Critical\_Assessment\_of\_Function\_Annotation

DNA large language model

https://en.wikipedia.org/wiki/DNA\_large\_language\_model

Physiologically based pharmacokinetic modelling

Physiologically based pharmacokinetic (PBPK) modeling is a mathematical modeling technique for predicting the absorption, distribution, metabolism and ... Read more

[deepmind.google deepmind.google](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/)  

AlphaGenome: AI for better understanding the genome

25 Jun 2025 — Update January 2026: This research has been published in Nature. You can read the full paper here and access the model here. The genome is our ...

Publications

Explore a selection of our recent research on some of the most complex and interesting challenges in AI. 263 publications. 1 September 2026: Designing ...Read more

Co-Scientist: A multi-agent AI partner to accelerate research

19 May 2026 — Introducing a collaborative AI partner for researchers to develop new hypotheses in life sciences and beyond.Read more

New AI Tools for the Future of Science

The ERA and Co-Scientist research papers are published today in Nature. AlphaFold Database, AlphaGenome API and InterPro. 2026 Here's a look at everything we ...

Google DeepMind Accelerator — AI for the Planet, APAC

A three-month program for AI-focused startups, research teams, and non-profits across Asia Pacific (APAC) that are tackling environmental challenges.Read more

Science

AlphaGenome: Using AI to understand the human genome. AlphaGenome Predict how single variants or mutations in human DNA sequences impact the biological ...

AI model achieves breakthrough in forecasting cyclones

6 Aug 2026 — our WeatherNext AI model achieved state-of-the-art accuracy in predicting a cyclone's track, intensity, and wind structure.

AlphaFold — Google DeepMind

AlphaFold has revealed millions of intricate 3D protein structures, and is helping scientists understand how all of life's molecules interact.

AlphaEvolve: A Gemini-powered coding agent for ...

14 May 2025 — New AI agent evolves algorithms for math and practical applications in computing by combining the creativity of large language models with ...

Science Needs AI Data Stocktakes: A Proof-of-Concept for ...

Can AI accelerate fusion energy? This essay explores the data challenges facing fusion research and proposes "AI data stocktakes" to unlock scientific ...

[arcinstitute.org arcinstitute.org](https://arcinstitute.org/news/arc-vevo)  

Tahoe Open Sources Tahoe-100M, the World's Largest ...

25 Feb 2025 — Tahoe-100M, is the world's largest single-cell dataset, 50x larger than all public drug-perturbed data combined. It includes 100 million cells ...

Arc Virtual Cell Atlas

First released in February 2025, the Atlas includes Tahoe's Tahoe-100M ... It contains 100m cells from ~60,000 drug perturbation experiments, mapping the ...Read more

Tahoe Therapeutics, Arc Institute, and Biohub Partner to ...

12 Jan 2026 — Released in 2025 on Arc Virtual Cell Atlas, Tahoe-100M rapidly became one of the most influential datasets in computational biology, with ...Read more

Arc Institute's first virtual cell model: State

23 Jun 2025 — During benchmarking on Tahoe-100M, State demonstrated a 50 percent improvement in distinguishing perturbation effects and achieved twice the ...Read more

Arc's Virtual Cell Initiative

Additional contributions include the Tahoe-100M dataset from Tahoe Therapeutics and the Virtual Cell Challenge's perturbation benchmark datasets.

Virtual Cell Challenge 2025 Wrap-Up: Winners and ...

6 Dec 2025 — We have an ambitious goal of predicting cellular response to perturbation, a challenging and impactful task with wide implications for biology.Read more

Arc Virtual Cell Atlas launches, combining data from over ...

25 Feb 2025 — The first is a new, open source, perturbation dataset called Tahoe-100M, created by Tahoe comprising 100 million cells and mapping 60,000 drug- ...

Yusuf Roohani, Arc's Associate Director of Machine Learning

13 Aug 2025 — In our recent paper, for example, we pre-trained the model on the Tahoe 100M drug perturbation dataset and then adapted it to a different ...Read more

[academic.oup.com academic.oup.com](https://academic.oup.com/bib/article/23/6/bbac409/6713511)  

BioGPT: generative pre-trained transformer for biomedical text generation and mining | Briefings in Bioinformatics | Oxford Academic

https://academic.oup.com/bib/article/23/6/bbac409/6713511

GeneGPT: augmenting large language models with domain tools for improved access to biomedical information | Bioinformatics | Oxford Academic

1 INTRODUCTION Large language models (LLMs) such as PaLM (Chowdhery et al. 2022) and GPT-4 (OpenAI 2023) have shown great success on a wide range of general-domain Natural Language Processing (NLP) t...

[pubmed.ncbi.nlm.nih.gov pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/33381841/)  

DeepCDR: a hybrid graph convolutional network for predicting cancer drug response - PubMed

. 2020 Dec 30;36(Suppl\_2):i911-i918. doi: 10.1093/bioinformatics/btaa822. DEEPCDR: A HYBRID GRAPH CONVOLUTIONAL NETWORK FOR PREDICTING CANCER DRUG RESPONSE Qiao Liu^{ 1 2 }, Zhiqiang Hu^{ 2...

Graph Convolutional Networks for Drug Response Prediction - PubMed

https://pubmed.ncbi.nlm.nih.gov/33606633/

towards a biology-informed framework for mental disorders - PubMed

In clinical research and drug development, diagnostic categories are used as enrollment criteria for clinical trials and to inform prescribing information ...

Increased Access to Professional Interpreters in the ... - PubMed

A bedside interpreter phone system intervention to increase rapid access to professional interpreters was associated with improvements in patient-reported ...

Interventions to improve research participants' understanding in ...

Objective: To review research on interventions to improve research participants' understanding of information disclosed in the informed consent process. Data ...

A Physiologically-Based Pharmacokinetic Model for the ...

by HM Jones · 2019 · Cited by 55 — A Physiologically-Based Pharmacokinetic Model for the Prediction of Monoclonal Antibody Pharmacokinetics From In Vitro Data. CPT Pharmacometrics Syst ... Read more

Current Use of Physiologically Based Pharmacokinetic ...

by P Paul · 2025 · Cited by 33 — Advice on the data expected to allow qualification of a PBPK model or platform is provided in the EMA Guideline on the reporting of PBPK modeling and simulation ...Read more

Multimodal strategies for the implementation of infection ...

by A Sonpar · 2025 · Cited by 49 — Most studies demonstrate a significant effect on HAI prevention improvement after applying a multimodal strategy.

AI-based differential diagnosis of dementia etiologies on ...

by C Xue · 2024 · Cited by 240 — Here, we present an artificial intelligence (AI) model that harnesses a broad array of data, including demographics, individual and family medical history, ...Read more

Multimodal multicentre investigation of diagnostic and ...

by D Manasova · 2026 · Cited by 15 — Multimodal multicentre investigation of diagnostic and prognostic markers in disorders of consciousness.Read more

Sensitivity and specificity of multimodal and ... - PubMed

by U Menon · 2009 · Cited by 1132 — The sensitivity of the MMS and USS screening strategies is encouraging. Specificity was higher in the MMS than in the USS group, resulting in lower rates of ...

Effects of a multimodal management strategy for acute ...

by O Corcos · 2013 · Cited by 201 — A multidisciplinary and multimodal management approach might increase survival of patients with AMI and prevent intestinal failure.

Multimodal prehabilitation in colorectal cancer patients to ...

by S van Rooijen · 2019 · Cited by 475 — This study will determine the impact of multimodal prehabilitation on patients' functional capacity and postoperative complications.

Multimodal Patient Blood Management Program Based on ...

by FC Althoff · 2019 · Cited by 451 — Overall, a comprehensive PBM program addressing all 3 PBM pillars is associated with reduced transfusion need of red blood cell units, lower complication and

A generative AI-discovered TNIK inhibitor for idiopathic pulmonary fibrosis: a randomized phase 2a trial - PubMed

https://pubmed.ncbi.nlm.nih.gov/?term=NCT05938920

Large-scale foundation model on single-cell transcriptomics

by M Hao · 2024 · Cited by 959 — Large-scale foundation model on single-cell transcriptomics. Nat Methods. 2024 Aug;21(8):1481-1491. doi: 10.1038/s41592-024-02305-7. Epub 2024 Jun 6. Authors.Read more

Predicting transcriptional responses to novel chemical ...

by X Qi · 2024 · Cited by 108 — PRnet, a perturbation-conditioned deep generative model that predicts transcriptional responses to novel chemical perturbations that have never ...

[mlanthology.org mlanthology.org](https://mlanthology.org/iclr/2023/corso2023iclr-diffdock/)  

DiffDock: Diffusion Steps, Twists, and Turns for Molecular Docking | ML Anthology

https://mlanthology.org/iclr/2023/corso2023iclr-diffdock/

Uni-Mol: A Universal 3D Molecular Representation Learning Framework | ML Anthology

https://mlanthology.org/iclr/2023/zhou2023iclr-unimol/

[dblp.org dblp.org](https://dblp.org/rec/conf/iclr/CorsoSJBJ23.html)  

dblp: DiffDock: Diffusion Steps, Twists, and Turns for Molecular Docking.

"DIFFDOCK: DIFFUSION STEPS, TWISTS, AND TURNS FOR MOLECULAR DOCKING." \* help us \* How can I correct errors in dblp? \* contact dblp Gabriele Corso et al. (2023) \* \* Image: use mirror server Dag...

[merriam-webster.com merriam-webster.com](https://www.merriam-webster.com/dictionary/informed)  

INFORMED Definition & Meaning - Merriam-Webster

The meaning of INFORMED is having information. How to use informed in a sentence.

PROTECTION Definition & Meaning - Merriam-Webster

The meaning of PROTECTION is the act of protecting : the state of being protected. How to use protection in a sentence.

[clinicaldata.ema.europa.eu clinicaldata.ema.europa.eu](https://clinicaldata.ema.europa.eu/)  

Home - Clinical Data Publication

This website provides access to clinical data published under the European Medicines Agency (EMA) policy on the publication of clinical data.

[catalogues.ema.europa.eu catalogues.ema.europa.eu](https://catalogues.ema.europa.eu/)  

Homepage | HMA-EMA Catalogues of real-world data sources and ...

The HMA-EMA Real-World Data (RWD) Catalogues provide a centralised and global repository of information on real-world data sources and studies. Their purpose is ...

[ascpt.onlinelibrary.wiley.com ascpt.onlinelibrary.wiley.com](https://ascpt.onlinelibrary.wiley.com/)  

Leveraging In Silico and Artificial Intelligence Models to ...

by K Yang · 2025 · Cited by 16 — Machine learning (ML) and AI provide powerful tools to integrate and analyze large datasets and identify key physiological determinants of drug ... Read more

Current Use of Physiologically Based Pharmacokinetic ...

2 Jan 2025 — The 2018 EMA Guideline on the reporting of physiologically based pharmacokinetic (PBPK) modeling and simulation (the EMA PBPK Guideline) ...Read more

Considerations for Industry—Preparing for the FDA Model ...

22 Mar 2024 — In 2018, the FDA established the MIDD Paired Meeting Pilot Program to facilitate the use of modeling and simulation in drug development and ...Read more

[register.ema.europa.eu register.ema.europa.eu](https://register.ema.europa.eu/)  

Home · EMA Account Management

The EMA Account Management platform guides you through accessing EMA applications facilitating interactions between the EMA and their users.

[rcog.org.uk rcog.org.uk](https://www.rcog.org.uk/guidance/browse-all-guidance/green-top-guidelines/management-of-monochorionic-twin-pregnancy-green-top-guideline-no-51/)  

Monochorionic Twin Pregnancy, Management - RCOG

This guideline provides clinicians with up-to-date evidence-based information regarding the management of monochorionic twin pregnancy.

[reaganlibrary.gov reaganlibrary.gov](https://www.reaganlibrary.gov/archives/speech/farewell-address-nation)  

Farewell Address to the Nation | Ronald Reagan

An informed patriotism is what we want. And are we doing a good enough job teaching our children what America is and what she represents in ...

[iris.ema.europa.eu iris.ema.europa.eu](https://iris.ema.europa.eu/)  

Home · IRIS

A secure online platform for handling product-related scientific and regulatory procedures with EMA Sign In. Quick links. Access & submission.

[instagram.com instagram.com](https://www.instagram.com/twin_music_/?hl=ar)  

TWIN (@twin\_music\_) • Instagram photos and videos

Our new single \*Hey, It's OK\* is live! Go listen! And go watch the video! Now! Link in bio This song means a lot to us. Thank you for listening.

The Deep (@thedeeeep) • Instagram photos and videos

65K followers · 267 following · 19 posts · @thedeeeep.Read more

Mark Zuckerberg (@zuck) • Instagram photos and videos

The original and classic design. Now with 2X more battery life. I wear them all day, and they never run out of battery. Meta Horizon Studio. Over the last ...

Meta One. - Instagram

The app connects directly to Instagram and Facebook professional accounts, giving creators and business owners real-time access to their ...

Taylor Swift (@taylorswift) • Instagram photos and videos

Just a few Opalite memories to celebrate the Hot 100 #1 you guys just got this song!!

Kylie (@kyliejenner) • Instagram photos and videos

381M followers · 155 following · 7390 posts · @kyliejenner: “@kyliecosmetics @khy”

Taylor Swift (@taylorswift) • Instagram photos and videos

273M followers · 0 following · 708 posts · @taylorswift: “Original song "I Knew It, I Knew You," for Toy Story 5, out now! ☁️”

Kim Kardashian (@kimkardashian) • Instagram photos and videos

Seven years of loving you and learning from you every single day. I'm so proud of how kind, smart, and special you are, and I hope your birthday is filled with ...

[eudragmdp.ema.europa.eu eudragmdp.ema.europa.eu](https://eudragmdp.ema.europa.eu/)  

Eudra GMP - Public Layout

Manufacturing Practice (GMP) certificates. Registration of manufacturers, importers and distributors of active substances for human use

[esubmission.ema.europa.eu esubmission.ema.europa.eu](https://esubmission.ema.europa.eu/)  

eSubmission: Projects

Familiarise themselves with the PLM web-based eAF and available guidance materials. Practice creating submissions in the PLM portal. Draft forms can be ...

[pmc.ncbi.nlm.nih.gov pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC5851387/)  

Trauma-informed care: Better care for everyone - PMC

The principles of trauma-informed care provide guidance for physicians who might be unsure of how to approach the difficult topics of ACEs that are central to a ...

Industrial Perspective on the Benefits Realized From ... - PMC

by GR Galluppi · 2021 · Cited by 31 — The US Food and Drug Administration (FDA) Model‐Informed Drug Development (MIDD) Paired Meeting Pilot Program was created to facilitate the application of MIDD ...

[careers.ema.europa.eu careers.ema.europa.eu](https://careers.ema.europa.eu/)  

Careers at EMA

Apply online for jobs at EMA. You work at the heart of medicines evaluation and regulation within Europe, opportunities for professional growth and development.

[magellanhealthcare.com magellanhealthcare.com](https://www.magellanhealthcare.com/health-plans/informed/)  

inforMED Pharmacy Program - Magellan Healthcare

Magellan's clinical outreach program, inforMED, provides physicians with unbiased, evidence-based info about medicines and other therapeutic interventions..

[esmp.ema.europa.eu esmp.ema.europa.eu](https://esmp.ema.europa.eu/)  

ESMP: Home

ESMP enables information exchange for prevention, identification, and management of shortages to ensure medicines are available for patients in the EU and EEA.

[spor.ema.europa.eu spor.ema.europa.eu](https://spor.ema.europa.eu/)  

SPOR Web UI

The SPOR portal currently offers guest access to query, browse and export OMS, RMS and SMS data. As of 1 October 2025 change requests should be submitted ...

[justicecenter.ny.gov justicecenter.ny.gov](https://www.justicecenter.ny.gov/ep-10-understanding-trauma-and-trauma-informed-approach)  

Ep 10: Understanding Trauma and the Trauma-Informed Approach

We discuss why a trauma-informed approach is critical for anyone who works with people in vulnerable situations.

[eudract.ema.europa.eu eudract.ema.europa.eu](https://eudract.ema.europa.eu/)  

EudraCT Public website - Home page

Welcome to the EudraCT public home page. EudraCT (European Union Drug Regulating Authorities Clinical Trials Database) is the database for all ...

[theguardian.com theguardian.com](https://www.theguardian.com/lifeandstyle/2026/may/02/rare-twins-different-dads-the-gift-bbc-radio-4)  

meet the twins who have different dads | Family | The Guardian

When DNA test results shattered everything Lavinia and Michelle thought they knew about their family history, they also revealed something ...

[pubs.acs.org pubs.acs.org](https://pubs.acs.org/)  

Meta-Analysis of Nanoparticle Delivery to Tumors Using a ...

by YH Cheng · 2020 · Cited by 393 — In this study, we used physiologically based pharmacokinetic (PBPK) models to analyze 376 data sets covering a wide range of nanomedicines ... Read more

[fda.gov fda.gov](https://www.fda.gov/)  

The Use of Physiologically Based Pharmacokinetic ...

29 Sept 2020 — This guidance provides general recommendations regarding the development, evaluation, and use of physiologically based pharmacokinetic ... Read more

Considerations for the Use of Artificial Intelligence

6 Jan 2025 — GUIDANCE DOCUMENT. Considerations for the Use of Artificial Intelligence To Support Regulatory Decision-Making for Drug and Biological ...Read more

Model-Informed Drug Development Paired Meeting Program

7 Jul 2026 — FDA is conducting a MIDD Pilot Program to facilitate the development and application of exposure-based, biological, and statistical models ...

Considerations for the Use of Artificial Intelligence To ...

Regulatory Decision-Making for Drug and Biological Products. 2. Guidance for Industry1 and Other Interested Parties. 3. 4. This draft guidance, when finalized ...Read more

M15 General Principles for Model-Informed Drug ...

3 Jun 2026 — This guideline is intended to facilitate a multidisciplinary understanding of MIDD and associated evidence generation. The guidance finalizes ...Read more

Artificial Intelligence for Drug Development

1 May 2026 — FDA published a draft guidance in 2025 ... Artificial Intelligence to Support Regulatory Decision Making for Drug and Biological Products.Read more

MIDD Paired Meeting Program Frequently Asked Questions

25 Aug 2026 — FDA is encouraging early meeting discussions to provide advice on how specific, proposed MIDD approaches can be used in a specific drug ...Read more

FDA Qualifies First AI Drug Development Tool, Will Be Used in 'MASH' Clinical Trials | FDA

https://www.fda.gov/drugs/drug-safety-and-availability/fda-qualifies-first-ai-drug-development-tool-will-be-used-mash-clinical-trials

Clinical Outcome Assessment (COA) Qualification Program | FDA

CLINICAL OUTCOME ASSESSMENT (COA) QUALIFICATION PROGRAM CDER & CBER’S DDT QUALIFICATION PROJECT SEARCH DATABASE Locate a project or a qualified Clinical Outcome Assessment on CDER & CBER’s DDT Qual...

FDA Launches Agency-Wide AI Tool to Optimize Performance for the American People | FDA

FDA News Release FDA LAUNCHES AGENCY-WIDE AI TOOL TO OPTIMIZE PERFORMANCE FOR THE AMERICAN PEOPLE For Immediate Release: June 02, 2025 iframe The U.S. Food and Drug Administration (FDA) today l...

FDA Expands Artificial Intelligence Capabilities with Agentic AI Deployment | FDA

FDA News Release FDA EXPANDS ARTIFICIAL INTELLIGENCE CAPABILITIES WITH AGENTIC AI DEPLOYMENT For Immediate Release: December 01, 2025 The U.S. Food and Drug Administration today announced the depl...

FDA Announces Completion of First AI-Assisted Scientific Review Pilot and Aggressive Agency-Wide AI Rollout Timeline | FDA

FDA News Release FDA ANNOUNCES COMPLETION OF FIRST AI-ASSISTED SCIENTIFIC REVIEW PILOT AND AGGRESSIVE AGENCY-WIDE AI ROLLOUT TIMELINE For Immediate Release: May 08, 2025 In a historic first for th...

Guiding Principles of Good AI Practice in Drug Development | FDA

GUIDING PRINCIPLES OF GOOD AI PRACTICE IN DRUG DEVELOPMENT Image: Cover image of Guiding Principles og Good AI Practice in Drug Development Download PDF CDER and CBER have collaborated with the Eu...

Medical Device Development Tools (MDDT) | FDA

MEDICAL DEVICE DEVELOPMENT TOOLS (MDDT) Image: Medical Device Development Tools (MDDT) Program Update - November 19, 2024 The FDA is announcing qualification of the WOUND-Q instrument, a new pat...

Artificial Intelligence for Drug Development | FDA

\* Artificial Intelligence for Drug Development \* Guiding Principles of Good AI Practice in Drug Development \* External Engagements with FDA for Artificial Intelligence in Drug Development ARTIFICIA...

FDA Announces Plan to Phase Out Animal Testing Requirement for Monoclonal Antibodies and Other Drugs | FDA

FDA News Release FDA ANNOUNCES PLAN TO PHASE OUT ANIMAL TESTING REQUIREMENT FOR MONOCLONAL ANTIBODIES AND OTHER DRUGS For Immediate Release: April 10, 2025 Today, the U.S. Food and Drug Administra...

External Engagements with FDA for Artificial Intelligence in Drug Development | FDA

EXTERNAL ENGAGEMENTS WITH FDA FOR ARTIFICIAL INTELLIGENCE IN DRUG DEVELOPMENT FDA encourages sponsors and other interested parties to engage early with FDA. There are various options for engagement...

New Approach Methodologies (NAMs) | FDA

NEW APPROACH METHODOLOGIES (NAMS) Introduction | Definitions | FDA’s NAMs Activities Selected Guidance | Other Resources | Contact Information FDA ACHIEVES YEAR 1 GOALS IN REDUCING ANIMAL TESTING I...

SmartCore Technology: Using AI and Patient Tissue to Identify Potential Cancer Therapies for Ultra-rare Cancers | FDA

SMARTCORE TECHNOLOGY: USING AI AND PATIENT TISSUE TO IDENTIFY POTENTIAL CANCER THERAPIES FOR ULTRA-RARE CANCERS External Institution: Fred Hutchinson Cancer Research Center External Collaborators:...

Biomarker Guidances and Reference Materials | FDA

BIOMARKER GUIDANCES AND REFERENCE MATERIALS On this page: \* Guidance Documents \* Recent FDA-Cosponsored Workshops and Events \* Biomarker Materials and Informational Websites \* Biomarker Survey GUI...

[ema.europa.eu ema.europa.eu](https://www.ema.europa.eu/system/files/documents/scientific-guideline/reflection-paper-use-artificial-intelligence-ai-medicinal-product-lifecycle-en.pdf)  

Reflection paper on the use of Artificial Intelligence (AI) in the ...

Sep 9, 2024 — This reflection paper focuses only on the use of AI in the medicinal product lifecycle and any references to qualification of novel ...Read more

Reporting of physiologically based pharmacokinetic (PBPK ...

The aim of this guideline is to describe the expected content of physiologically based pharmacokinetic (PBPK) modelling and simulation reports included in ...Read more

Use of Artificial Intelligence (AI) in the medicinal product lifecycle

Jul 19, 2023 — EMA is seeking stakeholder feedback on the draft reflection paper on the use of Artificial Intelligence (AI) in the medicinal product lifecycle ...Read more

Guideline on the reporting of physiologically based ...

13 Dec 2018 — Guideline on the reporting of physiologically based pharmacokinetic (PBPK) modelling and simulation. EMA/CHMP/458101/2016. Page 2/16. Guideline ...Read more

[goodwinlaw.com goodwinlaw.com](https://www.goodwinlaw.com/en/insights/publications/2025/01/alerts-lifesciences-aiml-fda-publishes-its-first-draft-guidance)  

FDA Publishes Its First Draft Guidance On Use of Artificial ...

28 Jan 2025 — FDA issues its first AI draft guidance for drug and biologics development, outlining a risk-based framework for regulatory decision-making.

[benzifoundation.org benzifoundation.org](https://benzifoundation.org/reflection-paper-ai-medicinal-products-lifecycle/)  

EMA's final reflection paper on AI in medicinal products ...

Oct 17, 2024 — This paper explores the potential applications and regulatory considerations for AI across the lifecycle of medicinal products, from drug ...Read more

[onlinelibrary.wiley.com onlinelibrary.wiley.com](https://onlinelibrary.wiley.com/doi/10.1155/joch/5202999)  

A Critical Review of the FDA's Draft Guidance on Artificial ...

by SK Niazi · 2026 · Cited by 16 — In January 2025, the FDA issued its first definitive guideline, “Considerations for the Use of AI to Support Regulatory Decision-Making for Drug ...Read more

[certara.com certara.com](https://www.certara.com/blog/how-the-us-fda-midd-paired-pilot-program-helps-sponsors/)  

How the US FDA MIDD paired pilot program helps sponsors

28 Feb 2025 — The FDA MIDD paired pilot program integrates quantitative tools in drug development to improve efficiency and inform regulatory decisions.

[ec.europa.eu ec.europa.eu](https://ec.europa.eu/newsroom/ema/redirection/item/850303/en/3679)  

EMA - Reflection paper on the use of AI in the medicinal ...

It provides considerations on the use of AI in the lifecycle of medicinal products and describes the current experience of the EU medicines regulators while ...Read more

[page-meeting.org page-meeting.org](https://www.page-meeting.org/Abstracts/the-new-draft-ema-guidance-on-pbpk-the-qualification-of-the-intended-use-concept/)  

The new draft EMA Guidance on PBPK – The qualification ...

Available EMA guidance covers the principles and the general approach to the use of PBPK analysis.

[dlapiper.com dlapiper.com](https://www.dlapiper.com/en/insights/publications/2025/01/fda-releases-draft-guidance-on-use-of-ai)  

Key takeaways from FDA's draft guidance on use of AI ...

23 Jan 2025 — This draft guidance provides recommendations for the use of AI in the product life cycle of drugs and biologics, where the specific objective of ...Read more

[propharmagroup.com propharmagroup.com](https://www.propharmagroup.com/thought-leadership/faq-model-informed-drug-development-midd-modeling-simulation-ms)  

FAQs: Model Informed Drug Development (MIDD) & ...

18 Mar 2025 — According to FDA, "MIDD approaches use a variety of quantitative methods to help balance the risks and benefits of drug products in development.Read more

[biotalk.twobirds.com biotalk.twobirds.com](https://biotalk.twobirds.com/post/102juyw/emas-finalised-reflection-paper-on-the-use-of-ai)  

EMA's finalised reflection paper on the use of AI - BioTalk

Jan 22, 2025 — On 9 September 2024 the European Medicines Agency (“EMA”) issued its final reflection paper on the use of AI in the medicinal product lifecycle.Read more

[tga.gov.au tga.gov.au](https://www.tga.gov.au/resources/resources/international-scientific-guidelines-adopted-australia/guideline-reporting-physiologically-based-pharmacokinetic-pbpk-modelling-and-simulation)  

Guideline on the reporting of physiologically based ...

2 Jan 2025 — Guideline on the reporting of physiologically based pharmacokinetic (PBPK) modelling and simulation line - EMA/CHMP/458101/2016

[facebook.com facebook.com](https://www.facebook.com/insife/posts/grip-news-ema-releases-reflection-paper-on-ai-and-machine-learning-in-medicinal-/1053748976536856/)  

[GRIP NEWS] EMA Releases Reflection Paper on AI and ...

This paper discusses principles relevant to the application of AI and machine learning (ML) at every stage of a medicine's lifecycle, from drug ...Read more

My conducting the orchestra video just hit 4 million views!! I'm ever ...

This video captures a powerful and emotional performance of the opera "The Phantom of the Opera." It features a full orchestra, led by a ...

[casrai.org casrai.org](https://casrai.org/guides/fda-ai-guidance)  

FDA AI Guidance: Drugs & Medical Devices

18 Jul 2026 — January 6-7, 2025 — draft guidance: “Considerations for the Use of Artificial Intelligence to Support Regulatory Decision-Making for Drug and ...Read more

[scirp.org scirp.org](https://www.scirp.org/reference/referencespapers?referenceid=3997588)  

European Medicines Agency (EMA) (2024) Reflection ...

European Medicines Agency (EMA) (2024) Reflection Paper on the Use of Artificial Intelligence (AI) in the Medicinal Product Lifecycle. https://www.ema.europa.eu.Read more

[scilifelab.se scilifelab.se](https://www.scilifelab.se/wp-content/uploads/2021/06/Luzon-et-al-CPT-2017.pdf)  

Physiologically based pharmacokinetic modeling in ...

by E Luzon · 2017 · Cited by 163 — This work reviews the use and impact of such modeling in selected regulatory procedures submitted to the European Medicines Agency (EMA) before the end of 2015, ...Read more

[c-path.org c-path.org](https://c-path.org/training/model-informed-drug-development-training-course/)  

Model-Informed Drug Development Training Course

Learn more about the Model-Informed Drug Development Training Course and what can you learn from it by visiting our page and applying for it.

[nsf.org nsf.org](https://www.nsf.org/life-science-regulatory-news/ema-reflection-paper-on-ai-in-the-medicinal-product-lifecycle)  

EMA Reflection Paper on AI in the Medicinal Product ...

Sep 30, 2024 — On September 30, 2024, the EMA published a 'Reflection paper on the use of Artificial Intelligence (AI) in the medicinal product lifecycle'.Read more

[linkedin.com linkedin.com](https://www.linkedin.com/pulse/ema-provides-guidelines-pediatric-pbpk-modeling-lynda-graham-mba)  

EMA Provides Guidelines for Pediatric PBPK Modeling

The European Medicines Agency (EMA) unveiled its first-ever draft guideline focused on the use of physiologically-based pharmacokinetic (PBPK) ...

Genetics and Genomic Medicine Research Team Roles

Modeling all 28,000 genes at once: a foundation model for single-cell transcriptomics Every cell in your body carries the same genome, yet a neuron looks ...

[sternekessler.com sternekessler.com](https://www.sternekessler.com/news-insights/client-alerts/fda-issues-draft-guidance-documents-on-artificial-intelligence-for-medical-devices-drugs-and-biological-products/)  

FDA Issues Draft Guidance Documents on Artificial ...

14 Jan 2025 — 1. Drug & Biological Products Guidance: Considerations for the Use of Artificial Intelligence to Support Regulatory Decision-Making for Drug and ...Read more

[gabionline.net gabionline.net](https://gabionline.net/switchlanguage/to/gabi_online_es/guidelines/european-position-paper-on-ai-in-medicinal-product-lifecycle)  

European position paper on AI in medicinal product lifecycle

At the end of 2024, the European Medicine's agency (EMA) published a reflection paper on 'The use of Artificial Intelligence (AI) in the medicinal product ...Read more

[researchgate.net researchgate.net](https://www.researchgate.net/publication/311992013_Report_from_EMA_Workshop_on_Qualification_and_Reporting_of_Physiologically-based_Pharmacokinetic_PBPK_Modelling_and_Simulation)  

(PDF) Report from EMA Workshop on Qualification and ...

22 May 2026 — Physiologically-Based Pharmacokinetic (PBPK) modelling is a valuable tool in drug development and regulatory assessment, as it offers the ...Read more

Large Scale Foundation Model on Single-cell ...

1 May 2026 — Experiments showed that scFoundation can serve as a foundation model for single-cell transcriptomics and can achieve state-of-the-art ...Read more

Predicting Cellular Responses to Novel Drug Perturbations ...

20 Apr 2026 — PRnet [13] is a perturbation-conditioned generative model that targets novel compounds directly, ably Predicting Chemical Perturbation via ...

Large-scale foundation model on single-cell transcriptomics

6 Jun 2024 — Experiments showed that scFoundation can serve as a foundation model for single-cell transcriptomics and can achieve state-of-the-art ...Read more

(PDF) Zero-shot evaluation reveals limitations of single-cell ...

9 Apr 2025 — Experiments showed that scFoundation can serve as a foundation model for single-cell transcriptomics and can achieve state-of-the-art ...Read more

[reuters.com reuters.com](https://www.reuters.com/world/us/us-fda-phase-out-animal-testing-drug-development-2025-04-10/)  

US FDA to phase out animal testing in drug development

The U.S. Food and Drug Administration (FDA) announced a major change in drug development practices, planning to phase out animal testing in favor of "human-relevant methods" such as AI-based models and lab-developed human organ-like structures. This initiative, described by FDA Commissioner Martin Makary as a “paradigm shift,” aims to enhance drug safety, cut research and development costs, reduce drug prices, and minimize animal use. Under this new framework, animal testing requirements may be reduced, refined, or replaced with New Approach Methodologies (NAMs) for drug evaluation. The FDA will begin immediate implementation, encouraging the use of NAMs data in clinical trial applications. Drug companies providing robust non-animal safety data may benefit from faster regulatory reviews, which could promote investment in modern testing platforms. Over the coming year, the FDA will also pilot a non-animal testing program with select developers of monoclonal antibody therapies, using results to inform future policy and regulatory updates.

US FDA qualifies first AI tool to help speed liver disease drug development

The U.S. Food and Drug Administration (FDA) has officially qualified the first AI tool, AIM-NASH, to aid in drug development for a serious liver condition known as metabolic dysfunction-associated steatohepatitis (MASH). This cloud-based tool uses artificial intelligence to analyze liver tissue images, identifying signs such as fat accumulation, inflammation, and fibrosis. AIM-NASH is expected to streamline clinical trials by standardizing the evaluation process, reducing reliance on multiple human experts, and speeding up assessments. The FDA confirmed that the tool’s analysis is comparable to expert reviews, supporting its use in clinical trial settings. Importantly, AIM-NASH will now be publicly accessible for use in drug development programs. Experts believe such AI tools could significantly shorten drug development timelines and reduce costs over the next few years.

[apnews.com apnews.com](https://apnews.com/article/a5aaa5501ae15f264bbd20d0dffa4dc4)  

FDA will drop two-study requirement for new drug approvals, aiming to speed access

The U.S. Food and Drug Administration (FDA) announced a major shift in its drug approval process by dropping its longstanding requirement for two rigorous clinical trials. Under the new policy spearheaded by FDA Commissioner Dr. Marty Makary and Deputy Dr. Vinay Prasad, the standard will now be to approve new drugs based on a single well-controlled study, supported by additional evidence. This aims to accelerate drug development and reduce bureaucratic hurdles, with officials citing modern scientific advancements that make repeated trials less necessary. The change comes as part of broader reforms introduced by Makary since his 2025 appointment, which include integrating artificial intelligence and offering expedited one-month drug assessments for medications deemed in the "national interest." While the FDA has already accepted single trials for rare or fatal diseases, the new policy expands that flexibility to treatments for more common conditions. Former FDA drug director Dr. Janet Woodcock supports the move, noting it's consistent with the agency's evolving approach. However, the FDA's inconsistent stance on other products like vaccines and gene therapies—highlighted by recent reversals on Moderna’s mRNA flu vaccine—has led to confusion within the industry about the agency’s standards and future direction.

FDA proposes new system for approving customized drugs and therapies for rare diseases

The U.S. Food and Drug Administration (FDA) has proposed a new approval system aimed at accelerating the development of customized treatments for rare and hard-to-treat diseases, including gene-editing therapies for rare genetic conditions. Announced by FDA Commissioner Marty Makary, the plan introduces a draft framework for approving bespoke therapies that may only be tested in small patient groups due to the rarity of the conditions. This initiative is part of a broader trend of policy changes under Makary’s leadership, including the recent elimination of the longstanding requirement for two clinical trials in standard drug review. The new “plausible mechanism” pathway would allow commercialization of experimental drugs that show a scientifically reasonable basis for treating specific biological or genetic illnesses, provided researchers demonstrate that the therapy targets the correct disease mechanism. The proposal addresses limitations of the current “compassionate use” system, which is hard to navigate and prohibits profits. The plan also acknowledges the financial disincentives faced by pharmaceutical companies in developing treatments for small patient populations. The FDA will collect public comments on the draft guidelines for 60 days before moving toward finalization. The effort reflects growing interest from researchers and patients in expanding access to innovative, personalized medical interventions.

[washingtonpost.com washingtonpost.com](https://www.washingtonpost.com/wp-intelligence/health-brief/2025/10/29/biosimilars-obamacare-premiums-opiods/)  

Slashing the red tape for biosimilars

The October 29, 2025, issue of Health Brief focuses on the Trump administration's initiative to reduce drug costs by streamlining the approval process for biosimilars—less expensive versions of biologic drugs. The FDA, led by Commissioner Marty Makary, plans to eliminate the requirement for comparative studies in favor of analytical testing, potentially cutting several years off the development timeline. This move is seen as a major win for manufacturers like Sandoz, Teva, Pfizer, and Amgen. Biologics, which originate from living organisms, represent only 5% of prescriptions but 51% of total drug spending. Industry leaders believe the new regulatory direction could increase U.S. investments in biosimilars. Critics argue that prior lobbying efforts by brand-name pharmaceutical firms created excessive barriers to approval. Health officials worry about a "biosimilar void," with only a fraction of upcoming patent-expired biologics having alternatives in development. The newsletter also discusses the Affordable Care Act’s (ACA) tax credit uncertainty, which could drive premium spikes during open enrollment. Meanwhile, a legal shift reinstates opioid distributors' liability for their role in West Virginia’s opioid crisis. Drug pricing and Medicaid exposure remain key issues for companies like GSK and Gilead, especially under Trump-era pricing policies.

[investors.com investors.com](https://www.investors.com/news/technology/genedx-stock-fda-ai-draft-guidance/)  

IBD 50's GeneDx Adds To Nearly 2,700% Sprint With FDA Guide On AI

GeneDx, a company featured on the IBD 50 list, experienced another surge in its stock price following new draft guidance from the FDA regarding the use of artificial intelligence (AI) in medical device development. The proposed guidelines address the use of AI across the entire product lifecycle, potentially benefiting companies like GeneDx that employ AI in genomics-based diagnostic testing. In 2024, GeneDx stock soared nearly 2,700% as the firm improved its financial outlook. On January 6, 2025, GeneDx shares jumped another 13.2%, closing at $89.61 and breaking out of a consolidation at a buy point of $89.11. GeneDx specializes in whole genome and exome sequencing, primarily for diagnosing rare diseases in children. The company focuses only on diseases with available solutions, emphasizing early testing to prevent lengthy diagnostic processes. GeneDx’s continued growth has earned it the No. 40 spot on the IBD 50 list of top-performing growth stocks. The FDA's draft guidance may further support the company's role in AI-driven healthcare innovations.

[cde.org.cn cde.org.cn](https://www.cde.org.cn/main/news/viewInfoCommon/3a55263f274e0525c1172a37f5b04a8e)  

国家药监局药审中心关于发布《模型引导的创新药物剂量探索和优化技术指导原则》的通告（2024年第53号）

https://www.cde.org.cn/main/news/viewInfoCommon/3a55263f274e0525c1172a37f5b04a8e

指导原则专栏

国家药品监督管理局药品审评中心 指导原则专栏 Image: site 当前位置 : 国内药品技术指导原则 &gt;&gt; 详细内容 发布时间 | 20150228 发布通告 | 名称 | 生物类似药研发与评价技术指导原则（试行） 适用范围 | 生物制品 专业分类 | 药学 版本状态 | 颁布 关键词 | 附件 1 | 生物类似药研发与评价技术指导原则（试行）.doc 意见留言 |...

药品注册管理办法

国家药品监督管理局药品审评中心 CENTER FOR DRUG EVALUATION, NMPA Image: site 当前位置：法律法规&gt;&gt;详细内容 药品注册管理办法 颁布日期：20200330 药品注册管理办法 （2020年1月22日国家市场监督管理总局令第27号公布） 第一章 总 则 第一条 为规范药品注册行为，保证药品的安全、有效和质量可控，根据《中华人民共和国药品管...

https://www.cde.org.cn/ichWeb/guideIch/toGuideIch/2/0

Title Image: ICH工作办公室 ICH指导原则 \* 指导原则概况 \* 质量(Q) \* 安全性(S) \* Image S1A - S1C Carcinogenicity Studies/致癌性研究 \* Image S2 Genotoxicity Studies/基因毒性研究 \* Image S3A - S3B Toxicokinetics and Pharmacokineti...

关于公开征求ICH《M10：生物分析方法验证及样品分析》指导原则实施建议和中文版的通知

关于公开征求ICH《M10：生物分析方法验证及样品分析》指导原则实施建议和中文版的通知 发布日期：20220817 为推动ICH三级指导原则在国内的平稳落地实施，我中心拟定了《M10：生物分析方法验证及样品分析》实施建议，同时组织翻译中文版。现对M10实施建议和中文版公开征求意见，为期1个月。 如有修改意见，请反馈至联系人电子邮箱：gkzhqyj@cde.org.cn。 附件：1.M10...

药物临床试验方案提交与审评工作规范

国家药品监督管理局药品审评中心 CENTER FOR DRUG EVALUATION, NMPA Image: site 当前位置：中心制度&gt;&gt;详细内容 药物临床试验方案提交与审评工作规范 颁布日期：20231013 内容分类: 业务 相关附件 序号 | 附件名称 --- | --- 1 | 《药物临床试验方案提交与审评工作规范》.pdf

国家药品监督管理局药品审评中心

办事服务 Image: site 当前位置 : 办事服务 ＞＞ 办事指南 一、药品注册申请的受理 药品注册申请人（以下简称申请人）依照《药品注册管理办法》等相关要求向国家药品监督管理局（以下简称药监局）提出以下类型药品注册申请，包括药物临床试验申请、药品上市许可申请、补充申请和境外生产药品再注册申请等。 申请人按照《药品注册管理办法》、《药品注册申报资料格式体例与整理规范》等相关规定填...

关于上线注册服务平台的通知

国家药品监督管理局药品审评中心 CENTER FOR DRUG EVALUATION, NMPA 关于上线注册服务平台的通知 发布日期：20260330 为贯彻国务院关于持续优化政务服务的决策部署，进一步提高“互联网+政务服务”水平，我中心将“行政受理服务专栏”升级为“注册服务平台”。该平台致力于为医药企业提供药品注册全程指导，为社会大众提供药品注册科普介绍，具体内容如下： 一、注册指...

国家药品监督管理局药品审评中心

国家药品监督管理局药品审评中心 CENTER FOR DRUG EVALUATION, NMPA Image: 搜索 [Input: 请输入关键词] [Button: 搜索] 首页 机构职能 \* 领导介绍 \* 组织机构 \* 中心职能 \* 发展历程 新闻中心 \* 政务新闻 \* 要闻导读 \* 图片新闻 \* 工作动态 政策法规 \* 法律法规 \* 指导原则 \* 政策解读 党建工作 \*...

https://www.cde.org.cn/ichWeb/news/getNewsDetail/2/fd1a2e7f52a8593c404592ba7eea5200/3

关于公开征求ICH《E6（R3）：药物临床试验质量管理规范（GCP）》指导原则及附件1草案的通知 2023-05-29 ICH《E6（R3）：药物临床试验质量管理规范（GCP）》指导原则及附件1现进入第3阶段区域公开征求意见阶段。按照ICH相关章程要求，ICH的监管机构成员需收集本地区关于第2b阶段指导原则草案的意见并反馈ICH。 E6（R3）指导原则及附件1英文原文和中文译文见附件，现就该...

视频回放 | ICH《Q2（R2）/Q14：分析方法验证和开发》指导原则培训

国家药品监督管理局药品审评中心 CENTER FOR DRUG EVALUATION, NMPA 视频回放 | ICH《Q2（R2）/Q14：分析方法验证和开发》指导原则培训 发布日期：2024-09-05 8月28日，由国家药品监督管理局ICH工作办公室和药品审评中心主办的ICH《Q2（R2）：分析方法验证》和《Q14：分析方法开发》指导原则宣贯活动在北京举办。 本场培训邀请ICH...

关于公开征求《罕见疾病药物临床研发中应用去中心化临床试验的技术指导原则》意见的通知

国家药品监督管理局药品审评中心 CENTER FOR DRUG EVALUATION, NMPA Image: site 当前位置：新闻中心&gt;&gt;工作动态&gt;&gt;通知公告&gt;&gt;新闻正文 关于公开征求《罕见疾病药物临床研发中应用去中心化临床试验的技术指导原则》意见的通知 发布日期：20231124 罕见疾病药物临床研发存在诸多挑战，探索更有利于患者参与的临床试验新模式将有助于提高罕见疾病药物研...

孔繁圃：科学审评精准发力突破性治疗药物密集上市

国家药品监督管理局药品审评中心 CENTER FOR DRUG EVALUATION, NMPA Image: site 当前位置：新闻中心&gt;&gt;政务新闻&gt;&gt;新闻正文 孔繁圃：科学审评精准发力突破性治疗药物密集上市 发布日期：20220808 Image: 1.jpg 近年来，随着我国药品审评审批制度改革加速深化推进，鼓励药品创新政策红利不断加码，审评能力与效率进一步提升，审评资源重...

[english.nmpa.gov.cn english.nmpa.gov.cn](https://english.nmpa.gov.cn/2026-08/20/c_1210674.htm)  

Implementation Opinions of NMPA on "Artificial Intelligence + Drug Regulation"

https://english.nmpa.gov.cn/2026-08/20/c\_1210674.htm

Implementation Opinions on "Artificial Intelligence + Drug Regulation" issued by NMPA

https://english.nmpa.gov.cn/2026-08/20/c\_1210673.htm

[wjw.wuxi.gov.cn wjw.wuxi.gov.cn](https://wjw.wuxi.gov.cn/doc/2024/06/04/4323063.shtml)  

中华人民共和国人类遗传资源管理条例（2024修订）

https://wjw.wuxi.gov.cn/doc/2024/06/04/4323063.shtml

[xzfg.moj.gov.cn xzfg.moj.gov.cn](https://xzfg.moj.gov.cn/mobile/law/detail?LawID=1714)  

国家行政法规库

中华人民共和国人类遗传资源管理条例 Image 下载Word Image 下载PDF Image 历史沿革 中华人民共和国人类遗传资源管理条例 2019-05-28 中华人民共和国人类遗传资源管理条例 2024-03-10 中华人民共和国人类遗传资源管理条例 (2019年5月28日中华人民共和国国务院令第717号公布 根据2024年3月10日《国务院关于修改和废止部分行政法规的...

[cac.gov.cn cac.gov.cn](https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm)  

生成式人工智能服务管理暂行办法\_中央网络安全和信息化委员会办公室

生成式人工智能服务管理暂行办法 2023年07月13日 15:00 来源： 中国网信网 国家互联网信息办公室 中华人民共和国国家发展和改革委员会 中华人民共和国教育部 中华人民共和国科学技术部 中华人民共和国工业和信息化部 中华人民共和国公安部 国家广播电视总局 令 第15号 《生成式人工智能服务管理暂行办法》已经2023年5月23日国家互联网信息办公室2023年第12次室...

国家互联网信息办公室关于《生成式人工智能服务管理办法（征求意见稿）》公开征求意见的通知\_中央网络安全和信息化委员会办公室

国家互联网信息办公室关于《生成式人工智能服务管理办法（征求意见稿）》公开征求意见的通知 2023年04月11日 12:51 来源： 中国网信网 〖打印〗〖纠错〗 为促进生成式人工智能技术健康发展和规范应用，根据《中华人民共和国网络安全法》等法律法规，国家互联网信息办公室起草了《生成式人工智能服务管理办法（征求意见稿）》，现向社会公开征求意见。公众可通过以下途径和方式提出反馈意见： 1.登...

规范生成式智能服务，充分释放技术红利\_中央网络安全和信息化委员会办公室

规范生成式智能服务，充分释放技术红利 2023年04月17日 15:51 来源： 光明日报 〖打印〗〖纠错〗 近日，国家网信办发布《生成式人工智能服务管理办法（征求意见稿）》（以下简称《办法》），向社会公开征求意见。自去年以来，生成式人工智能快速走红，席卷文本、图像、音频、视频等各类媒介场景，成为全社会关注的焦点。 生成式人工智能服务以其优异的知识表现、流畅的语言交互和媒介输出，引发了各...

个人信息保护政策法规问答（2026年1月）\_中央网络安全和信息化委员会办公室

个人信息保护政策法规问答（2026年1月） 2026年01月09日 16:30 来源： 中国网信网 〖打印〗〖纠错〗 国家互联网信息办公室持续加强个人信息保护相关政策法规宣贯，指导帮助个人信息处理者规范开展个人信息处理活动，保护个人信息权益。现将一些具有代表性的问题和答复公布如下。 1.什么是个人信息？ 个人信息是以电子或者其他方式记录的与已识别或者可识别的自然人有关的各种信息，不包括...

部门规章\_中央网络安全和信息化委员会办公室

当前位置： 首页 &gt; 网信政务 &gt; 政策法规 &gt; 部门规章 政策法规 \* 法律 \* 行政法规 \* 部门规章 \* 司法解释 \* 规范性文件 \* 政策文件 \* 政策解读 \* ##### 小型个人信息处理者个人信息保护简化措施规定 2026-07-24 \* ##### 网络数据安全风险评估办法 2026-06-18 \* ##### 互联网信息内容多渠道分发服务管理规定 2026-05-...

专家解读｜坚持创新引领促进生成式人工智能健康发展\_中央网络安全和信息化委员会办公室

专家解读｜坚持创新引领 促进生成式人工智能健康发展 2023年08月29日 11:30 来源： 中国网信网 〖打印〗〖纠错〗 为促进生成式人工智能健康发展和规范应用，国家互联网信息办公室等部门公布《生成式人工智能服务管理暂行办法》（以下简称《办法》），充分表明支持生成式人工智能健康发展的态度，针对生成式人工智能发展的数据安全、个人隐私、虚假信息、知识产权等关键问题作出制度安排，是贯彻落实党...

专家解读｜以安全助发展以治理促创新\_中央网络安全和信息化委员会办公室

专家解读｜以安全助发展 以治理促创新 2023年08月29日 11:30 来源： 中国网信网 〖打印〗〖纠错〗 近日，国家网信办联合国家发展改革委、教育部、科技部、工业和信息化部、公安部、广电总局公布《生成式人工智能服务管理暂行办法》（以下称《办法》），这充分体现了国家对生成式人工智能发展和应用的高度重视，也标志着我国生成式人工智能治理迈出了坚实的一步。《办法》坚持发展与安全并重、促进创新...

我国网络安全保障体系和能力持续构建\_中央网络安全和信息化委员会办公室

我国网络安全保障体系和能力持续构建 2023年08月31日 11:50 来源： 人民网 〖打印〗〖纠错〗 在8月31日举行的“2023年国家网络安全宣传周新闻发布会”上，中央网信办网络安全协调局局长高林表示，党的十八大以来，以习近平同志为核心的党中央高度重视网络安全工作，为更好维护网络安全指明了前进方向、提供了根本遵循。 近年来，各地区各部门在党中央的坚强领导下，切实履行网络安全工作责任...

专家解读｜制度与技术同频共振：生成式人工智能治理的中国方案\_中央网络安全和信息化委员会办公室

专家解读｜制度与技术同频共振：生成式人工智能治理的中国方案 2023年07月13日 20:09 来源： 中国网信网 〖打印〗〖纠错〗 以ChatGPT为代表的生成式人工智能正在引发新一轮人工智能革命。生成式人工智能改变了信息和知识的生产方式，重塑了人类与技术的交互模式，并开启了我们对于通用人工智能的无穷想象。可以预见，生成式人工智能将对医疗、教育、零售、金融、咨询、媒体和游戏等行业产生重大...

专家解读｜坚持多方共治为生成式人工智能健康发展提供制度保障\_中央网络安全和信息化委员会办公室

专家解读｜坚持多方共治 为生成式人工智能健康发展提供制度保障 2023年07月13日 20:14 来源： 中国网信网 〖打印〗〖纠错〗 生成式人工智能是人类科学技术发展的重要成果，为引领和带动新一轮产业变革提供了可能。近年来，生成式人工智能技术不断成熟，展现出全方位提升人类生产生活效率的重要潜力，揭开人类社会智能化演进的趋势。然而，生成式人工智能也在网络安全方面带来新挑战、新风险。如何发...

《人工智能生成合成内容标识办法》答记者问\_中央网络安全和信息化委员会办公室

《人工智能生成合成内容标识办法》答记者问 2025年03月14日 17:05 来源： 中国网信网 近日，国家互联网信息办公室、工业和信息化部、公安部、国家广播电视总局联合发布《人工智能生成合成内容标识办法》（以下简称《标识办法》），自2025年9月1日起施行。日前，国家互联网信息办公室有关负责人就《标识办法》有关问题回答了记者提问。 一、问：请介绍一下《标识办法》的出台背景？ 答：近年来...

政务领域人工智能大模型部署应用指引\_中央网络安全和信息化委员会办公室

政务领域人工智能大模型部署应用指引 2025年10月10日 19:53 来源： 中国网信网 〖打印〗〖纠错〗 为深入贯彻落实党中央、国务院决策部署，规范和引导人工智能大模型在政务领域的发展与应用，提升政务数字化智能化治理和服务水平，制定本指引。本指引主要为各级政务部门提供人工智能大模型部署应用的工作导向和基本参照，将根据实践进展，结合人工智能大模型发展和应用的新形势、新要求，进行动态调整。...

[samr.gov.cn samr.gov.cn](https://www.samr.gov.cn/wljys/gzzd/art/2023/art_3ef1e889c1e644d4b65b5f5c7f432386.html)  

中华人民共和国个人信息保护法

https://www.samr.gov.cn/wljys/gzzd/art/2023/art\_3ef1e889c1e644d4b65b5f5c7f432386.html

中华人民共和国数据安全法

\* 标题： \* 中华人民共和国数据安全法 \* 索引号： \* 2021-1636078625011 | \* 主题分类： \* 总局涉及职能的法律 \* 文号： \* 无 | \* 公布日期： \* 2021年06月10日 \* 中华人民共和国数据安全法 \* 发布时间：2021-11-05 10:22 \* \* \* 中华人民共和国数据安全法 （2021年6月10日第十三届全国人民代表大会常务委员...

[hhs.gov hhs.gov](https://www.hhs.gov/ohrp/regulations-and-policy/guidance/index.html)  

Guidance | HHS.gov

OHRP has published a variety of guidance documents to assist the research community in conducting ethical research that is in compliance ...

[bis.gov bis.gov](https://www.bis.gov/media/documents/bis-guidance-may-31-2026.pdf)  

[PDF] BIS Guidance — May 31, 2026 (PDF)

In January 2025, the AI Diffusion Rule transferred the requirement for these “.a” items from § 744.23(a) into § 742.6 as part of a new worldwide.

[epa.gov epa.gov](https://www.epa.gov/home)  

U.S. Environmental Protection Agency | US EPA

Website of the U.S. Environmental Protection Agency (EPA). EPA's mission is to protect human health and the environment.

[justice.gov justice.gov](https://www.justice.gov/ag/media/1409486/dl)  

[PDF] Guidance for Recipients of Federal Funding Regarding Unlawful ...

This guidance clarifies the application of federal antidiscrimination laws to programs or initiatives that may involve discriminatory practices,

[consumerfinance.gov consumerfinance.gov](https://www.consumerfinance.gov/)  

Consumer Financial Protection Bureau

The CFPB enforces federal consumer financial laws consistently to promote compliance and ensure that markets, products, and services are fair, ...

[cms.gov cms.gov](https://www.cms.gov/priorities/innovation/innovation-models/guide)  

GUIDE (Guiding an Improved Dementia Experience) Model - CMS

The model's interventions help people with dementia to remain in their homes and communities while supporting caregiver health and wellbeing.

[usa.gov usa.gov](https://www.usa.gov/state-consumer)  

State consumer protection offices | USAGov

Find your state's consumer protection office. They can help with complaints against businesses, investigating scams and fraud, and more.

[federalregister.gov federalregister.gov](https://www.federalregister.gov/documents/2024/02/13/2024-02623/inventorship-guidance-for-ai-assisted-inventions)  

Inventorship Guidance for AI-Assisted Inventions - Federal Register

The guidance provides clarity for USPTO stakeholders and personnel, including the Central Reexamination Unit and the Patent Trial and Appeal ...

[sba.gov sba.gov](https://www.sba.gov/loans/covid-era-programs/)  

COVID-era programs - Small Business Administration - SBA

The COVID-19 EIDL program provided loans and advances to help businesses recover from the economic impacts of the pandemic. Learn about COVID-19 EIDL. Paycheck ...

[ico.org.uk ico.org.uk](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/biometric-data-guidance-biometric-recognition/)  

Biometric data guidance: Biometric recognition | ICO

About this guidance · Why have you produced this guidance? Who is it for? What does it cover? What doesn't it cover? How should we use this guidance?

[ghgprotocol.org ghgprotocol.org](https://ghgprotocol.org/land-sector-and-removals-guidance)  

Land Sector and Removals Guidance - GHG Protocol

Alongside the Land Sector and Removals Standard v1.1, the LSR Guidance explains how companies account for and report the following activities in their ...

[whistleblowers.gov whistleblowers.gov](https://www.whistleblowers.gov/)  

The Whistleblower Protection Programs | Whistleblower Protection ...

Before sharing sensitive information, make sure you're on a federal government site. any information you provide is encrypted and transmitted securely. Data ...

[roll20.net roll20.net](https://roll20.net/compendium/dnd5e/Guidance)  

Guidance | D&D 5th Edition on Roll20 Compendium

You touch one willing creature. Once before the spell ends, the target can roll a d4 and add the number rolled to one ability check of its choice.

[edpb.europa.eu edpb.europa.eu](https://www.edpb.europa.eu/home_en)  

European Data Protection Board: Home

We ensure that everyone in Europe benefits from equal data protection rights by providing clear guidance and consistent enforcement.

[aap.org aap.org](https://www.aap.org/ImmunizationSchedule?srsltid=AfmBOooq2PmtzoYEYisEck9BY0mE1tcQTvGWk4tH3xzYVgMn3Z1ov5x-)  

vaccine schedule from the American Academy of Pediatrics - AAP

https://www.aap.org/ImmunizationSchedule?srsltid=AfmBOooq2PmtzoYEYisEck9BY0mE1tcQTvGWk4tH3xzYVgMn3Z1ov5x-

[fisheries.noaa.gov fisheries.noaa.gov](https://www.fisheries.noaa.gov/topic/marine-mammal-protection)  

Marine Mammal Protection | NOAA Fisheries

NOAA Fisheries works to help all marine mammals protected under the Marine Mammal Protection Act, Endangered Species Act, and other laws and policies.

[whitehouse.gov whitehouse.gov](https://www.whitehouse.gov/wp-content/uploads/2025/03/OSTP-Guidance-for-GSS-June-2025.pdf)  

[PDF] Guidance for Gold Standard Science - The White House

This Guidance establishes a proactive approach to ensure science generated and utilized by agencies withstands scrutiny, fosters cross disciplinary ...

[imdb.com imdb.com](https://www.imdb.com/title/tt28698590/)  

Protection (TV Mini Series 2024) - IMDb

Follows a witness protection officer who finds herself at the center of a breach; compromised by an extramarital romance with a coworker; but resolute in her ...

[who.int who.int](https://www.who.int/news/item/18-01-2024-who-releases-ai-ethics-and-governance-guidance-for-large-multi-modal-models)  

WHO releases AI ethics and governance guidance for large multi-modal models

https://www.who.int/news/item/18-01-2024-who-releases-ai-ethics-and-governance-guidance-for-large-multi-modal-models

Ethics and governance of artificial intelligence for health: large multi-modal models. WHO guidance

DIGITAL PUBLICATIONS This page and linked pages display WHO publications in various digital formats, over and above what is available on Publications. This publication page will eventually replace...

Ethics and governance of artificial intelligence for health

ETHICS AND GOVERNANCE OF ARTIFICIAL INTELLIGENCE FOR HEALTH WHO guidance 28 June 2021 | Guideline Image: Ethics and governance of artificial intelligence for health Download (1.9 MB) OVERVIEW...

Ethics and governance of artificial intelligence for health

DIGITAL PUBLICATIONS This page and linked pages display WHO publications in various digital formats, over and above what is available on Publications. This publication page will eventually replace...

Ethics and governance of artificial intelligence for health

Image: Ethics and governance of artificial intelligence for health ETHICS AND GOVERNANCE OF ARTIFICIAL INTELLIGENCE FOR HEALTH WHO guidance. Executive summary \* Publication date: 2021 \* Health top...

WHO consultation towards the development of guidance on ethics and governance of artificial intelligence for health

DIGITAL PUBLICATIONS This page and linked pages display WHO publications in various digital formats, over and above what is available on Publications. This publication page will eventually replace...

WHO Consultation towards the development of guidance on ethics and governance of artificial intelligence for health

WHO CONSULTATION TOWARDS THE DEVELOPMENT OF GUIDANCE ON ETHICS AND GOVERNANCE OF ARTIFICIAL INTELLIGENCE FOR HEALTH Meeting report 7 March 2021 | Meeting report Image: WHO Consultation towards th...

Health Ethics & Governance

Health Ethics & Governance We provide a focal point for the examination of ethical issues raised by activities throughout the Organization and foster discussion and debate on diverse topics in globa...

WHO issues first global report on Artificial Intelligence (AI) in health and six guiding principles for its design and use

WHO ISSUES FIRST GLOBAL REPORT ON ARTIFICIAL INTELLIGENCE (AI) IN HEALTH AND SIX GUIDING PRINCIPLES FOR ITS DESIGN AND USE GROWING USE OF AI FOR HEALTH PRESENTS GOVERNMENTS, PROVIDERS, AND COMMUNITI...

Ensuring ethical standards and procedures for research with human beings

ENSURING ETHICAL STANDARDS AND PROCEDURES FOR RESEARCH WITH HUMAN BEINGS Research ethics govern the standards of conduct for scientific researchers. It is important to adhere to ethical principles i...

Health Ethics & Governance

Health Ethics & Governance We provide a focal point for the examination of ethical issues raised by activities throughout the Organization and foster discussion and debate on diverse topics in globa...

Harnessing artificial intelligence for health

Harnessing Artificial Intelligence for Health WHO / Danielle Alakija © Credits &gt; "AI is already playing a role in diagnosis and clinical care, drug development, disease surveillance, outbreak resp...

WHO | News releases

NEWS RELEASES WHO / Nazik Armenakyan © Credits LATEST 18 January 2024 News release WHO releases AI ethics and governance guidance for large multi-modal models 16 January 2024 News release Tobacc...

Social Determinants of Health - Global

Health Determinants, Promotion and Prevention We advance health for all by working with governments and partners to address the social determinants of health and the major risk factors for noncommun...

WHO releases AI ethics and governance guidance for large multi-modal models

WHO RELEASES AI ETHICS AND GOVERNANCE GUIDANCE FOR LARGE MULTI-MODAL MODELS 18 January 2024 News release Media Contacts WHO Media Team World Health Organization Email: mediainquiries@who.int R...

[eur-lex.europa.eu eur-lex.europa.eu](https://eur-lex.europa.eu/eli/reg/2024/1689/2026-07-27/eng)  

EUR-Lex - 02024R1689-20260727 - DE - EUR-Lex

laying down harmonised rules on artificial intelligence and amending Regulations (EC) No 300/2008, (EU) No 167/2013, (EU) No 168/2013, (EU) 2018/858, (EU) 2018/1139 and (EU) 2019/2144 and Directives 2...

[multimodal.org.uk multimodal.org.uk](https://www.multimodal.org.uk/)  

Multimodal - NEC Birmingham - 29 June - 1 July 2027

Multimodal has been the UK's leading logistics event, bringing together shippers, retailers, manufacturers, wholesalers, importers, exporters and the suppliers

[gigamon.com gigamon.com](https://www.gigamon.com/products/deep-observability-pipeline.html)  

Deep Observability Pipeline

Deliver real-time network-derived telemetry across your hybrid cloud to improve security, performance, compliance, and AI-driven operations.

[deeplearning.ai deeplearning.ai](https://www.deeplearning.ai/courses/vibe-coding-101-with-replit)  

Vibe Coding 101 with Replit

Learn the principles of agentic code development and skills to effectively build, host, and share your apps with Replit coding agents and assistants.

Claude Code: A Highly Agentic Coding Assistant

In this course, you'll learn best practices for using Claude Code to improve your coding workflow. You'll learn key tips on how to provide Claude Code with ...Read more

[nea.gov.sg nea.gov.sg](https://www.nea.gov.sg/our-services/public-cleanliness/toilets-management/coffeeshop-toilet-grants/ctcg)  

Coffeeshop Toilet Deep Cleaning Grant (CTCG)

The CTCG is intended to help coffeeshop operators maintain higher toilet cleanliness standards through regular deep cleaning, for removal of deep and ...Read more

[deepl.com deepl.com](https://www.deepl.com/en/translator)  

World's Most Accurate Translator

Translate texts & full document files instantly. Accurate translations for individuals and Teams. Millions translate with DeepL every day.

[tc.columbia.edu tc.columbia.edu](https://www.tc.columbia.edu/digitalfuturesinstitute/multimodal-toolkit/video-what-is-multimodal/)  

Video: what is multimodal? | Digital Futures Institute (DFI)

This explainer video breaks down the word and concept "multimodal" for all members of the academy--from graduate students to faculty--interested in ...Read more

[gma.caict.ac.cn gma.caict.ac.cn](https://gma.caict.ac.cn/plat/news/full-collection-of-blue-books-published-by-caict-in-2024)  

中国信通院2024年蓝皮书合集 | 业内新闻

中国信通院2024年蓝皮书合集 作者：CTTL-T 发布时间：2024-11-03 最后更新：2024-12-30 \* \* \* 最后更新：2024-12 出版时间 | 白皮书名称（单击下载） --- | --- 2024年12月 | 人工智能治理蓝皮书（2024年） 2024年12月 | 新一代智能终端蓝皮书（2024年） 2024年12月 | 数字消费者权益保护蓝皮书（2024...

[aihub.caict.ac.cn aihub.caict.ac.cn](https://aihub.caict.ac.cn/docs/qzNUc4Ssvduc)  

国家药监局关于“人工智能+药品监管”的实施意见 - 鲸智社区·大模型公共服务平台

鲸智社区·大模型公共服务平台 Image: Community Logo 项目来源：工业与信息化部-2023年产业技术基础公共服务平台-面向人工智能大模型工程化技术及应用的产业公共服务平台

[cell.com cell.com](https://www.cell.com/iscience/fulltext/S2589-0042%2826%2900657-7)  

Profiling biological effects of microbiome metabolites via ...

by HA Chung · 2026 · Cited by 2 — Our findings demonstrate the potential power of machine learning to accelerate the functional annotations of microbiome-derived metabolites, ...Read more

Metabolism and gene expression models for the ...

by JD Tibocha-Bonilla · 2026 · Cited by 6 — Predicting metabolic responses to dietary changes with ME-models. Next, we investigated metabolic profiles of the complex gut microbiota using ...Read more

Discovery of antimicrobial peptides in the global ...

by CD Santos-Júnior · 2024 · Cited by 460 — We present a machine-learning-based approach to predict antimicrobial peptides (AMPs) within the global microbiome and leverage a vast dataset ...Read more

Interindividual variability in gut microbiome mediates the ...

by X Long · 2025 · Cited by 22 — The gut microbiota-based machine learning models have demonstrated robust predictive capability for treatment response.64

From microbiome to metabolism: Bridging a two-decade ...

by M Van Hul · 2026 · Cited by 39 — Unlike drugs with defined molecular targets, these interventions engage with a dynamic and personalized ecosystem.

Artificial intelligence for microbiology and microbiome ...

This review provides a comprehensive overview of AI-driven approaches tailored for microbiology and microbiome studies, emphasizing both technical advancements ...

New approach methodologies for drug discovery

by W Liu · 2026 · Cited by 28 — Mapping human microbiome drug metabolism by gut bacteria and their genes Nature. Idiosyncratic drug reactions and toxicities. Biotechnology ...

Chemotherapy modulation by a cancer-associated ...

by D Martinez-Martinez · 2025 · Cited by 6 — Understanding how the microbiota produces regulatory metabolites is of significance for cancer and cancer therapy.Read more

Integrating multi-omics to unravel host-microbiome ...

by Y Zhang · 2024 · Cited by 92 — This review highlights the significance of multi-omics data in IBD research and provides an overview of state-of-the-art systems biology ...Read more

A novel perspective on gut microbiota-host interactions

by X Liu — ∙ Li, H. Microbial-host-isozyme: a new territory for understanding personalized responses towards drug therapy. Chin. J. Nat. Med. 2023; ...Read more

[internal-displacement.org internal-displacement.org](https://www.internal-displacement.org/global-report/grid2025/)  

2025 Global Report on Internal Displacement (GRID) | IDMC

The 2024 Global Report on Internal Displacement (GRID) report presents the data and analysis behind the 75.9 million people living in internal displacement ...

[healthline.com healthline.com](https://www.healthline.com/nutrition/gut-microbiome-and-health)  

How Does Your Gut Microbiome Affect Your Health?

1 Oct 2025 — A 2022 review suggests a bidirectional relationship, where psychological stress actually changes the gut microbiome itself.

[hepi.ac.uk hepi.ac.uk](https://www.hepi.ac.uk/reports/student-generative-ai-survey-2025/)  

Student Generative AI Survey 2025 - HEPI

26 Feb 2025 — On 26 February 2025, HEPI and Kortext will publish the Student Generative AI Survey 2025 by Josh Freeman, with a Foreword by Professor Janice ...Read more

[epo.org epo.org](https://www.epo.org/en/about-us/statistics/technology-dashboard-2025)  

EPO Technology Dashboard 2025

Filings to the EPO exceeded 200 000 for the first time, up +1.4% on 2024. Growth was driven by technologies such as AI, quantum technologies, batteries and ...Read more

[genome.gov genome.gov](https://www.genome.gov/genetics-glossary/Microbiome)  

Microbiome

These groups of microorganisms are dynamic and change in response to a host of environmental factors, such as exercise, diet, medication and other exposures.Read more

[uist.acm.org uist.acm.org](https://uist.acm.org/2026/)  

UIST 2026 - Home

The ACM Symposium on User Interface Software and Technology (UIST) is the premier forum for innovations in human-computer interfaces.

[ntu.edu.sg ntu.edu.sg](https://www.ntu.edu.sg/medicine/CMM)  

Centre for Microbiome Medicine (CMM)

Research into the diet-microbiome interactions in Asians can lead to diagnostic and therapeutic solutions for cancer and other chronic conditions.Read more

[unep.org unep.org](https://www.unep.org/resources/emissions-gap-report-2025)  

Emissions Gap Report 2025

4 Nov 2025 — The report finds that this overshoot must be limited through faster and bigger reductions in greenhouse gas emissions to minimize climate risks ...Read more

UNEP - UN Environment Programme

The global authority for the environment with programmes focusing on climate, nature, pollution, sustainable development and more.

[academy.openai.com academy.openai.com](https://academy.openai.com/public/videos/introduction-to-codex-2026-03-02)  

Introduction to Codex - Video | OpenAI Academy

A replay of our February 27 webinar, Introduction to Codex.

OpenAI Academy

Unlock the new opportunities of the AI era by equipping yourself with the knowledge and skills to harness artificial intelligence effectively.

Introduction to Prompt Engineering - Video - OpenAI Academy

Unlock the new opportunities of the AI era by equipping yourself with the knowledge and skills to harness artificial intelligence effectively.

Mastering Prompts: The Key to Getting What You Need from ChatGPT

Unlock the new opportunities of the AI era by equipping yourself with the knowledge and skills to harness artificial intelligence effectively.

[go.nature.com go.nature.com](https://go.nature.com/ykfvNW)  

IDSA Home

The Infectious Diseases Society of America (IDSA) provides clinical guidelines, research, education and resources for infectious diseases professionals.

IAEG-SDGs — SDG Indicators - UN Statistics Division

The IAEG-SDGs was tasked to develop and implement the global indicator framework for the Goals and targets of the 2030 Agenda. The global indicator framework ...

Why Animal Research?

NABR is dedicated to raising awareness of the role animals play in biomedical research. Find out more about the role the organization plays in devising ...

AR6 Synthesis Report: Climate Change 2023

AR6 Synthesis Report. Climate Change 2023. Summary for. Policymakers ▽ · Longer Report ▽ · SYR (Full volume)▽ · Figures ▻ · Headline Statements ▽.

Powers of Ten™ (1977) - YouTube

Powers of Ten takes us on an adventure in magnitudes. Starting at a picnic by the lakeside in Chicago, this famous film transports us to the ...

[worldbank.org worldbank.org](https://www.worldbank.org/en/news/press-release/2020/10/07/covid-19-to-add-as-many-as-150-million-extreme-poor-by-2021)  

COVID-19 to Add as Many as 150 Million Extreme Poor by 2021

We will be deploying up to $160 billion in financial support over 15 months to help more than 100 countries protect the poor and vulnerable, ...

[deploymentsafety.openai.com deploymentsafety.openai.com](https://deploymentsafety.openai.com/)  

OpenAI Deployment Safety Hub: System cards & other updates

Review OpenAI system cards and other safety updates for deployed AI systems. See how systems are evaluated, monitored, and improved over time.

[partnerships.nature.com partnerships.nature.com](https://partnerships.nature.com/)  

Nature Partnerships

Innovative solutions that connect academic institutions, research-led organizations and suppliers with the scientific community.

[meta.com meta.com](https://www.meta.com/meta-verified/?srsltid=AfmBOoolBdyfUN1-OJITxsuE0_X18xdHb2q97A7Zv-UGa0cQ8j4tYioC)  

Meta Verified: Get the verified badge on Instagram & Facebook

Get the verified badge for impersonation protection, direct support & exclusive features. Protect your brand & build confidence with new audiences.

About Meta | Social Technology, VR, AR, and Innovation

Learn more about Meta and stay updated on our role in social technology, virtual reality, augmented reality, and the future of human connection.

Meta: Shop AI Glasses, Meta Glasses & Quest Headsets

Meet the all-new Meta Glasses. Bold colors. Signature styles. Powerful AI. Starting at $299. Shop · Learn more. Explore the Meta Store.

[arabicedition.nature.com arabicedition.nature.com](https://arabicedition.nature.com/)  

Nature Middle East - Nature Asia

Nature Middle East is your one stop portal for science news, features, and information on the latest scientific and medical research in the Arab world in ...

[sugarspunrun.com sugarspunrun.com](https://sugarspunrun.com/million-dollar-deviled-eggs/)  

Million Dollar Deviled Eggs - Sugar Spun Run

There are deviled eggs, and then there are these Million Dollar Deviled Eggs -- the best recipe that includes a secret ingredient!

[openai.com openai.com](https://openai.com/foundation/)  

OpenAI Foundation

Using AI to accelerate breakthroughs so everyone can benefit from better diagnostics, treatments, and cures. Read the latest. OpenAI employees working. AI ...

OpenAI News

Stay up to speed on the rapid advancement of AI technology and the benefits it offers to humanity.

[forum.openai.com forum.openai.com](https://forum.openai.com/public/videos/event-replay-from-terminal-to-turnaround-how-gitlabs-co-founder-leveraged-chatgpt-in-his-cancer-fight-2026-03-18)  

Event Replay: From Terminal to Turnaround: How GitLab's Co ...

Event Replay: From Terminal to Turnaround: How GitLab's Co-Founder Leveraged ChatGPT in His Cancer Fight. Posted Mar 18, 2026 | Views 18.4K. # ...

[prism.openai.com prism.openai.com](https://prism.openai.com/)  

Prism - AI LaTeX Editor

An AI powered LaTeX editor that runs in your browser.

[communities.nature.com communities.nature.com](https://communities.nature.com/)  

A community for those interested in all areas of ... - Springer Nature

Research Communities by Springer Nature provide a forum for all those interested in research to share the latest discoveries, news, and opinions.

[conferences.nature.com conferences.nature.com](https://conferences.nature.com/)  

Nature Conferences

Nature Conferences are multi-day events designed for the international scientific community, with the goal of fostering communication and collaboration. These ...

[chat.openai.com chat.openai.com](https://chat.openai.com/)  

ChatGPT: Chat, Work, Create & Code with AI

Use ChatGPT to answer questions, write, create images, complete work, and code—all in one place. Get started for free or download the app.

[openreview.net openreview.net](https://openreview.net/forum?id=Vk2sfKAdeu&noteId=omI9iBAAHr)  

Tabula: A Tabular Self-Supervised Foundation Model for ...

This paper introduces TABULA, a foundation model for single-cell transcriptomics that proposes two primary innovations over existing models: a novel self ...Read more

Predicting Cellular Responses to Novel Drug Perturbations ...

by L Hetzel · 2022 · Cited by 163 — We present a model for counterfactual modelling of perturbation responses for unseen drugs and evaluate a transfer learning scheme for ...

Venues | OpenReview

2025 (41 VENUES) \* ICLR 2025 Conference \* ICLR 2025 Workshop Proposals \* ICLR 2025 BlogPosts \* ICLR 2025 Workshop World Models \* ICLR 2025 Workshop FPI \* ICLR 2025 Workshop ICBINB \* ICLR 2025 Worksho...

Search | OpenReview

Soft Injection of Task Embeddings Outperforms Prompt-Based In-Context Learning ICLR 2026 Conference Submission2081 Reviewer DTRG \* 29 Oct 2025 (modified: 12 Nov 2025) \* ICLR 2026 Conference Submissi...

[medium.com medium.com](https://medium.com/%40anatolybuchin/predicting-donor-age-from-nk-cells-using-geneformer-987430d07aca)  

🧬 Predicting Donor Age from NK Cells Using Geneformer

Theodoris, C. et al. (2023). Geneformer: A Foundation Model for Single-Cell Transcriptomics. bioRxiv. https://doi.org/10.1101/2023.03 ...Read more

[scispace.com scispace.com](https://scispace.com/papers/large-scale-foundation-model-on-single-cell-transcriptomics-zlar8c88)  

Large Scale Foundation Model on Single-cell ...

Experiments showed that scFoundation can serve as a foundation model for single-cell transcriptomics and achieve state-of-the-art performances in a diverse ...Read more

[experiments.springernature.com experiments.springernature.com](https://experiments.springernature.com/articles/10.1038/s41592-024-02305-7)  

Large-scale foundation model on single-cell transcriptomics

Nat Methods (2024).https://doi ... 14, 128 (2013). Hao, M. scFoundation: large scale foundation model on single-cell transcriptomics - processed datasets.Read more

[computer.org computer.org](https://www.computer.org/csdl/proceedings-article/bibm/2025/11356145/2e1jlN0FaDe)  

Synthesizing Disparate Models to Enhance Single-Cell ...

A Foundation Model for Single-Cell Transcriptomics in Alzheimer's Disease 2025 IEEE 25th International Conference on Bioinformatics and Bioengineering (BIBE) ...Read more

[scribd.com scribd.com](https://www.scribd.com/document/871939988/Large-scale-Foundation-Model-on-Single-cell-Transcriptomics)  

scFoundation: A Large-Scale Model for Single-Cell ...

Large-scale Foundation Model on Single-cell Transcriptomics - Free download ... Nature Methods | Volume 21 | August 2024 | 1481–1491 1481. Content ...Read more

[d2j16w31g89z0j.cloudfront.net d2j16w31g89z0j.cloudfront.net](https://d2j16w31g89z0j.cloudfront.net/site/biml2026/lecture2/on33.pdf)  

Single Cell, Pre-training, and Foundation Model - Cloudfront.net

Large-scale foundation model on single-cell transcriptomics. Nat Methods 21, 1481–1491 (2024). scFoundation Pretraining. • Expression enhancement for low-depth.Read more

[xqiu625.github.io xqiu625.github.io](https://xqiu625.github.io/ai4bio-concepts/single-cell-analysis/perturbation-prediction_modeling.html)  

Single-Cell Perturbation Modeling & Prediction

A comprehensive guide to state-of-the-art approaches combining single-cell transcriptomics, CRISPR screens, and machine learning to predict how cells respond ...

[huggingface.co huggingface.co](https://huggingface.co/perturblab/scfoundation-cell)  

perturblab/scfoundation-cell

Original Repository: biomap-research/scFoundation · Paper: Large Scale Foundation Model on Single-cell Transcriptomics (Nature Methods, 2024) ...Read more

tdc/scGPT - Hugging Face

scGPT is A foundation model for single-cell biology based on a generative pre trained transformer across a repository of over 33 million cells.

[iea.org iea.org](https://www.iea.org/news/iea-member-countries-to-carry-out-largest-ever-oil-stock-release-amid-market-disruptions-from-middle-east-conflict)  

IEA Member countries to carry out largest ever oil stock release amid ...

An average of 20 million barrels per day of crude oil and oil products transited the Strait of Hormuz in 2025, or around 25% of the world's ...

[digital-strategy.ec.europa.eu digital-strategy.ec.europa.eu](https://digital-strategy.ec.europa.eu/en/policies/1-million-genomes)  

European '1+ Million Genomes' initiative

The 1+ Million Genomes (1+MG) initiative has the potential to improve disease prevention, allow for more personalised treatments and support groundbreaking ...

[stackoverflow.blog stackoverflow.blog](https://stackoverflow.blog/2017/05/23/stack-overflow-helping-one-million-developers-exit-vim/)  

Stack Overflow: Helping One Million Developers Exit Vim

I think there are two reasons it's easy to forget how to exit Vim: developers are often dropped into Vim from a git command or another situation ...

[nih.gov nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC12191839/)  

A Comprehensive Review of Deep Learning Applications with Multi-Omics Data in Cancer Research - PMC

To address the limitations of prior models based on handcrafted drug features or single-omics data, DeepCDR [166] proposes a hybrid framework that combines graph-based drug representations with multi-...

Optimized models and deep learning methods for drug response prediction in cancer treatments: a review - PMC

Liu et al. (2020) developed DeepCDR, which utilizes a hybrid graph convolutional network for DRP. This network includes a uniform graph convolutional network and multiple sub-networks. It automaticall...

Artificial intelligence in the development of Rentosertib: A novel TNIK inhibitor for idiopathic pulmonary fibrosis - A letter to editor.

ARTIFICIAL INTELLIGENCE IN THE DEVELOPMENT OF RENTOSERTIB: A NOVEL TNIK INHIBITOR FOR IDIOPATHIC PULMONARY FIBROSIS - A LETTER TO EDITOR. Pulmonary pharmacology & therapeutics PMID: 41475169 Public...

AI-Driven Robotics Laboratory Identifies Pharmacological TNIK Inhibition as a Potent Senomorphic Agent - PubMed

. 2025 Feb 13;17(1):432-451. doi: 10.14336/AD.2024.1492. AI-DRIVEN ROBOTICS LABORATORY IDENTIFIES PHARMACOLOGICAL TNIK INHIBITION AS A POTENT SENOMORPHIC AGENT Qiuqiong Tang^{ 1 2 3 }, Deyong...

SAR156597 in idiopathic pulmonary fibrosis: a phase 2 placebo-controlled study (DRI11772) - PubMed

. 2018 Dec 13;52(6):1801130. doi: 10.1183/13993003.01130-2018. Print 2018 Dec. SAR156597 IN IDIOPATHIC PULMONARY FIBROSIS: A PHASE 2 PLACEBO-CONTROLLED STUDY (DRI11772) Ganesh Raghu^{ 1 }, Luca R...

Safety, tolerability, pharmacokinetics, and pharmacodynamics of GLPG1690, a novel autotaxin inhibitor, to treat idiopathic pulmonary fibrosis (FLORA): a phase 2a randomised placebo-controlled trial.

SAFETY, TOLERABILITY, PHARMACOKINETICS, AND PHARMACODYNAMICS OF GLPG1690, A NOVEL AUTOTAXIN INHIBITOR, TO TREAT IDIOPATHIC PULMONARY FIBROSIS (FLORA): A PHASE 2A RANDOMISED PLACEBO-CONTROLLED TRIAL....

[acs.org acs.org](https://pubs.acs.org/doi/10.1021/acs.jcim.3c01060)  

Improving Anticancer Drug Selection and Prioritization via Neural Learning to Rank | Journal of Chemical Information and Modeling | ACS Publications

4.2. BASELINES In order to illustrate the efficacy of our proposed methods, we use two strong baseline methods: pLETORg (26) and DeepCDR. (52) 4.2.1. PLETORG pLETORg learns the drug and cell line e...

[springer.com springer.com](https://link.springer.com/article/10.1186/s13059-025-03781-6)  

Biology-driven insights into the power of single-cell foundation ...

by J Wu · 2025 · Cited by 42 — Large-scale foundation model on single-cell transcriptomics. Nat Methods Nature Publishing Group. 2024;21:1481–91. Article CAS Google Scholar.Read more

[caict.ac.cn caict.ac.cn](https://ictp.caict.ac.cn/EN/abstract/abstract1254.shtml)  

Research on development trend of key technologies and industry of intelligent computing

RESEARCH ON DEVELOPMENT TREND OF KEY TECHNOLOGIES AND INDUSTRY OF INTELLIGENT COMPUTING ZHANG Qian^{1}, HUANG Huang^{1}, MIAO Zicong^{2} 1. 1. Informatization and Industrialization Integration Rese...

Bottlenecks of digital transformation in China’s biopharmaceutical industry and corresponding suggestions

BOTTLENECKS OF DIGITAL TRANSFORMATION IN CHINA’S BIOPHARMACEUTICAL INDUSTRY AND CORRESPONDING SUGGESTIONS WANG Xiaoling 1. Informatization and Industrialization Integration Research Institute, Chin...

大模型智算基础设施夯实新型工业化赋能底座

信息通信技术与政策 ›› 2024, Vol. 50 ›› Issue (12): 2-6.doi: 10.12267/j.issn.2096-5931.2024.12.001 专题:人工智能赋能新型工业化 上一篇 下一篇 大模型智算基础设施夯实新型工业化赋能底座 LARGE MODEL INTELLIGENT COMPUTING INFRASTRUCTURE REINFORCES...

信息通信技术与政策

过刊 本期目录 \* 2024年 第50卷 第6期 刊出日期：2024-06-25 上一期 下一期 专题:先进计算 \* 专题导读:先进计算 \* 黄伟 \* 大模型算力基础设施技术趋势、关键挑战与发展路径 \* 张政, 冯少飞 \* 信息通信技术与政策. 2024, 50(6): 2-9. DOI:10.12267/j.issn.2096-5931.2024.06.001 \* 摘要 ( 1374...

政务大模型的技术应用路径及发展建议

政务大模型的技术应用路径及发展建议 THE TECHNICAL APPLICATION PATH AND DEVELOPMENT SUGGESTIONS OF LARGE LANGUAGE MODEL FOR DIGITAL GOVERNMENT 李帅峥^{1}, 钱正^{1}, 董正浩^{2}, 史翔^{1} 1. 1.中电信数智科技有限公司,北京 100035 2.中国联通智能城市研究...

信息通信技术与政策

过刊 本期目录 \* 2024年 第50卷 第12期 刊出日期：2024-12-25 上一期 下一期 专题:人工智能赋能新型工业化 \* 人工智能赋能新型工业化 \* 魏凯 \* 信息通信技术与政策. 2024, 50(12): 1-1. \* 摘要 ( 8029 ) HTML ( 1254 ) \* \* 参考文献 | 相关文章 | 计量指标 \* 大模型智算基础设施夯实新型工业化赋能底...

百度AI系列白皮书

精品案例 百度AI系列白皮书 收藏 [Input] [Input] [Input] [Input] [Input] 与我国人工智能头部企业深度合作，发布百度AI系列白皮书，包括《飞桨凝聚创新，开源共创产业新机》开源框架报告、《构筑智能化基座，驱动全行业创新升级》AI中台白皮书等，聚焦人工智能产业热点领域，探讨产业现状、分析产业生态发展机遇及未来方向，促进人工智能产业繁荣发展，重点内容如...

中国信通院启动2024年端侧通用智能创新应用优秀案例征集 | 泰尔终端

中国信通院启动2024年端侧通用智能创新应用优秀案例征集 作者：CTTL-T 发布时间：2024-01-18 最后更新：2024-03-14 \* \* \* 当前全球人工智能已进入新一轮发展热潮，以大规模预训练模型、智能体、具身智能等路径演进的通用人工智能技术发展带来了巨大的历史机遇。伴随模型轻量化技术突破和终端算力水平提升，通用智能技术正从云端向终端侧加速渗透，并不断涌现出新模式、新形态、新...

信息通信技术与政策

Image: 信息通信技术与政策 过刊 本期目录 \* 2021年 第47卷 第4期 刊出日期：2021-04-15 上一期 下一期 \* 人工智能数据中心研究 \* 杨明川, 刘倩, 赵继壮 \* 信息通信技术与政策. 2021, 47(4): 1-7. DOI:10.12267/j.issn.2096-5931.2021.04.001 \* 摘要 ( 1601 ) \* 通过对信息化与数字化技术演...

[oup.com oup.com](https://academic.oup.com/bioinformatics/article/39/9/btad557/7264174)  

extensive benchmark study on biomedical text generation and mining with ChatGPT | Bioinformatics | Oxford Academic

ABSTRACT Motivation In recent years, the development of natural language process (NLP) technologies and deep learning hardware has led to significant improvement in large language models (LLMs). The...

BioVAE: a pre-trained latent variable language model for biomedical text mining | Bioinformatics | Oxford Academic

Journal Article BIOVAE: A PRE-TRAINED LATENT VARIABLE LANGUAGE MODEL FOR BIOMEDICAL TEXT MINING Hai-Long Trieu , Hai-Long Trieu Artificial Intelligence Research Center (AIRC), National Institute...

Figure 2. Dual-pipeline architecture of... | Oxford Academic

Figure 2. Dual-pipeline architecture of the TBEP Assistant for generating context-aware, reference-supported biomedical responses. (A) Schematic overview of the TBEP Assistant, which integrates two...

On the effectiveness of compact biomedical transformers | Bioinformatics | Oxford Academic

1 INTRODUCTION There has been an ever-increasing abundance of medical texts in recent years, both in private and public domains, which provide researchers with the opportunity to automatically proces...

GraphCDR: a graph neural network method with contrastive learning for cancer drug response prediction | Briefings in Bioinformatics | Oxford Academic

2 DATASETS Multi-omics data for cancer cell lines. CCLE [2] provides genomic, transcriptomic and epigenomic profiles for more than 1000 cancer cell lines. Following DeepCDR [20], we downloaded genomi...

[cziscience.com cziscience.com](https://virtualcellmodels.cziscience.com/quickstart/scgpt-quickstart)  

scGPT Quickstart - Virtual Cells Platform

This quickstart will guide you through using the scGPT model, trained on 33 million cells (including data from the CZ CELLxGENE Census), to generate embeddings ...

[moj.gov.cn moj.gov.cn](https://xzfg.moj.gov.cn/law/detail?LawID=446)  

国家行政法规库

Image 下载Word Image 下载PDF 扫码下载 中华人民共和国人类遗传资源管理条例 Image 历史沿革 收起 暂无历史沿革

国家行政法规库

标题检索 [Input] [Input] [Input: 在现行有效605部行政法规中搜索] 高级检索 根据《行政法规制定程序条例》汇编国家正式版本并动态更新，中国政府网与中国政府法制信息网(司法部官网)同步公布 [Input] 时 效 性 现行有效 \* 现行有效 公布文号 [Input] 公布日期 [Input: 请选择开始时间] [Input: 请选择结束时间] 施行日...

国家行政法规库

网络数据安全管理条例 Image 历史沿革 网络数据安全管理条例 (2024年8月30日国务院第40次常务会议通过 2024年9月24日中华人民共和国国务院令第790号公布 自2025年1月1日起施行) 第一章 总 则 第一条 为了规范网络数据处理活动，保障网络数据安全，促进网络数据依法合理有效利用，保护个人、组织的合法权益，维护国家安全和公共利益，根据《中华人民共和国网络安全法...

[nmpa.gov.cn nmpa.gov.cn](https://english.nmpa.gov.cn/2026-08/20/c_1210675.htm)  

Policy Interpretation of the Implementation Opinions of the NMPA on "Artificial Intelligence + Drug Regulation"

POLICY INTERPRETATION OF THE IMPLEMENTATION OPINIONS OF THE NMPA ON "ARTIFICIAL INTELLIGENCE + DRUG REGULATION" CCFDIE| Updated: 2026-08-20 In order to thoroughly implement the Opinions of the Stat...

NMPA Announcement on Guidance for the Classification Defining of AI-Based Medical Software Products

Home&gt; Regulatory Information NMPA ANNOUNCEMENT ON GUIDANCE FOR THE CLASSIFICATION DEFINING OF AI-BASED MEDICAL SOFTWARE PRODUCTS CCFDIE| Updated: 2021-07-08 In order to strengthen the supervision...

Opinions issued on integrated development of AI and drug regulation

OPINIONS ISSUED ON INTEGRATED DEVELOPMENT OF AI AND DRUG REGULATION Updated: 2026-06-29 Image: 1782723987381061838.jpg

Opinions of the General Office of the State Council on Comprehensively Deepening the Reform of Regulation of Drugs and Medical Devices to Promote the High-Quality Development of the Pharmaceutical Industry

OPINIONS OF THE GENERAL OFFICE OF THE STATE COUNCIL ON COMPREHENSIVELY DEEPENING THE REFORM OF REGULATION OF DRUGS AND MEDICAL DEVICES TO PROMOTE THE HIGH-QUALITY DEVELOPMENT OF THE PHARMACEUTICAL IN...

Announcement of the National Medical Products Administration on Issuing Measures to Optimize Whole Life-Cycle Regulation in Support of the Innovative Development of High-End Medical Devices ([2025 ]No. 63)

Home&gt; Medical Devices ANNOUNCEMENT OF THE NATIONAL MEDICAL PRODUCTS ADMINISTRATION ON ISSUING MEASURES TO OPTIMIZE WHOLE LIFE-CYCLE REGULATION IN SUPPORT OF THE INNOVATIVE DEVELOPMENT OF HIGH-END ME...

Drug Administration Law of the People's Republic of China

DRUG ADMINISTRATION LAW OF THE PEOPLE'S REPUBLIC OF CHINA en.npc.gov.cn.cdurl.cn| Updated: 2019-09-26 Order of the President of the People's Republic of China No. 31 The Drug Administration Law o...

Announcement of NMPA on Recommended Application of 4 ICH Guidelines Including Q8 (R2): Pharmaceutical Development

Home&gt; Regulatory Information ANNOUNCEMENT OF NMPA ON RECOMMENDED APPLICATION OF 4 ICH GUIDELINES INCLUDING Q8 (R2): PHARMACEUTICAL DEVELOPMENT CCFDIE| Updated: 2020-01-22 On January 21, 2020, NMPA...

Drugs

Home&gt; Drugs \* ### Policy Interpretation of the Announcement on Optimizing of the Review and Approval Process for Clinical Trials of Innovative Drugs 2025-10-14 This announcement further refines re...

Provisions for Drug Registration

Home&gt; Laws and Regulations PROVISIONS FOR DRUG REGISTRATION Updated: 2022-06-30 Chapter II General Systems and Requirements Article 8 The conduct of drug R&D and registration shall comply with ap...

Policies Interpretation

\* ### Opinions issued on integrated development of AI and drug regulation 2026-06-29 \* ### Procedure for Information Sharing Between Regulatory Agencies 2026-05-14 \* ### Policy measures to advanc...

NMPA to enhance drug regulation under revised rules — committed to a people-centered healthy policy and strengthen high-effect regulation

NMPA TO ENHANCE DRUG REGULATION UNDER REVISED RULES — COMMITTED TO A PEOPLE-CENTERED HEALTHY POLICY AND STRENGTHEN HIGH-EFFECT REGULATION Updated: 2026-01-08 On Dec 31, 2025, the State Council exec...

China updates drug clinical trial guideline to enhance biotech innovation

CHINA UPDATES DRUG CLINICAL TRIAL GUIDELINE TO ENHANCE BIOTECH INNOVATION chinadaily.com.cn| Updated: 2026-06-12 China has recently released a new edition of the Good Clinical Practice for Drugs —...

China revises drug administration regulations to spur innovation, tighten oversight

CHINA REVISES DRUG ADMINISTRATION REGULATIONS TO SPUR INNOVATION, TIGHTEN OVERSIGHT Xinhua| Updated: 2026-01-28 BEIJING -- China has revised regulations concerning drug administration in a bid to p...

国家药监局 国家卫生健康委 国家医保局关于做好后续品种实施医疗器械唯一标识工作的公告（2026年第21号）

国家药监局 国家卫生健康委 国家医保局关于做好后续品种实施医疗器械唯一标识工作的公告（2026年第21号） 为进一步贯彻落实《医疗器械监督管理条例》《国务院办公厅关于全面深化药品医疗器械监管改革促进医药产业高质量发展的意见》和国务院深化医药卫生体制改革有关重点工作任务，在所有第三类医疗器械（含体外诊断试剂）和103种第二类医疗器械实施医疗器械唯一标识基础上，现就后续品种实施医疗器械唯一标识有关...

国家药监局政务服务门户首页

Image: 国家药品监督管理局 国家政务服务平台 | 国家药品监督管理局 \* 首页 \* 法人服务 \* \* 行政权力 \* 公共服务 \* 其他服务 \* 联系我们 登录 搜索 热点服务 更多&gt; \* Image 药物临床试验登记 \* Image 境内生产药品上市许可 \* Image 境内生产药品补充申请许可 \* Image 药物临床试验审批 \* Image 药物临床试验机构备案 政务服...

[npc.gov.cn npc.gov.cn](https://www.npc.gov.cn/npc/c2/c30834/202108/t20210820_313088.html)  

中华人民共和国个人信息保护法\_中国人大网

中华人民共和国个人信息保护法 （2021年8月20日第十三届全国人民代表大会常务委员会第三十次会议通过） 来源： 中国人大网 浏览字号： 大 中 小 2021年08月20日 16:53 目 录 第一章 总 则 第二章 个人信息处理规则 第一节 一般规定 第二节 敏感个人信息的处理规则 第三节 国家机关处理个人信息的特别规定 第三章 个人信息跨境提供的规则 第四章 个人在...

[bypc.gov.cn bypc.gov.cn](https://www.bypc.gov.cn/zfxxgk/bmdwxzjd/bmdw/qkjj/fdzdgknr/lzyj/zcfg/art/2024/art_0fe5c379248b4f28964b4d67bb35103e.html)  

人类遗传资源管理条例实施细则

索 引 号： | 11620403013912770D/2024-00010 | 生成日期： | 2024-05-27 文 号： | | 关键字： | 人类,遗传,资源,科技部,行政 所属机构： | 平川区政府办 | 发布机构： | 人类遗传资源管理条例实施细则 信息来源：平川区人民政府 发布时间：2024-05-27 10:54 浏览次数： 人类遗传资源管理条...

[nvidia.com nvidia.com](https://build.nvidia.com/mit/diffdock/modelcard)  

diffdock Model by MIT | NVIDIA NIM

DIFFDOCK Downloadable Predicts the 3D structure of how a molecule interacts with a protein. MODEL OVERVIEW DESCRIPTION: DiffDock is a generative diffusion model for drug discovery in molecular b...

[gsjn.gov.cn gsjn.gov.cn](https://www.gsjn.gov.cn/zfxxgk/zfbmxxgk/gxj/zcwj/art/2025/art_84af6e2d2e974d17a70a79d1d79fc7d8.html)  

工业和信息化部等七部门关于印发《医药工业数智化转型实施方案（2025—2030年）》的通知

到2027年，医药工业数智化转型取得重要进展，以数智技术驱动的医药全产业链竞争力和全生命周期质量管理水平显著提升。在数智化发展基础建设方面，突破一批医药工业数智化关键技术，制修订30项以上医药工业数智技术标准，在智能制药设备、检测仪器和制药工业软件等领域研发推广100款以上高性能产品；在数智化转型推广方面，打造100个以上医药工业数智技术应用典型场景，建成100个以上数智药械工厂，建设50家以上具...

[rna-seqblog.com rna-seqblog.com](https://www.rna-seqblog.com/scgpt-towards-building-a-foundation-model-for-single-cell-multi-omics-using-generative-ai/)  

scGPT – towards building a foundation model for single-cell multi ...

scGPT, a generative pre-trained transformer, effectively distills critical biological insights concerning genes and cells.

[sciencedirect.com sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S095070512601659X)  

DeepTraCDR: Prediction of Cancer Drug Response Using Multimodal Deep Learning with Transformers - ScienceDirect

Date: Available online 22 August 2026 Article: 116933 In Press, Journal Pre-proof PUBLISHED BY: ELSEVIER Research article Get rights and content DEEPTRACDR: PREDICTION OF CANCER DRUG RESPONSE U...

DRN-CDR: A cancer drug response prediction model using multi-omics and drug features - ScienceDirect

COMPUTATIONAL BIOLOGY AND CHEMISTRY Date: October 2024 Article: 108175 Volume: Volume 112 PUBLISHED BY: ELSEVIER PUBLISHED BY Show more Research article Get rights and content DRN-CDR: A CAN...

Prediction of drug response in multilayer networks based on fusion of multiomics data - ScienceDirect

METHODS Volume 192, August 2021, Pages 85-92 PREDICTION OF DRUG RESPONSE IN MULTILAYER NETWORKS BASED ON FUSION OF MULTIOMICS DATA https://doi.org/10.1016/j.ymeth.2020.08.006Get rights and content...

Prediction of cancer drug response based on heterogeneous graph neural networks and multi-omics data - ScienceDirect

NEURAL NETWORKS Date: January 2026 Article: 108001 Volume: Volume 193 PUBLISHED BY: ELSEVIER Full Length Article Prediction of cancer drug response based on heterogeneous graph neural networks...

[miit.gov.cn miit.gov.cn](https://www.miit.gov.cn/jgsj/zfs/fl/art/2022/art_515a4b20c12f430eab54bb4f56d89f56.html)  

中华人民共和国个人信息保护法

中华人民共和国个人信息保护法 发布时间：2022-01-29 10:30 来源：产业政策与法规司 （2021年8月20日第十三届全国人民代表大会常务委员会第三十次会议通过） 目 录 第一章 总则 第二章 个人信息处理规则 第一节 一般规定 第二节 敏感个人信息的处理规则 第三节 国家机关处理个人信息的特别规定 第三章 个人信息跨境提供的规则 第四章 个人在个人信息处理活动中...

[scgpt.readthedocs.io scgpt.readthedocs.io](https://scgpt.readthedocs.io/en/latest/introduction.html)  

Introduction — scGPT 0.2.1 documentation

scGPT, a Python package for single-cell multi-omic data analysis using pretrained foundation models. provides a set of functions for data preprocessing, ...

[hyper.ai hyper.ai](https://hyper.ai/en/news/32623)  

A Cell Model With 100 Million Parameters Is ...

In June 2024, a research paper titled "Large-scale foundation model on single-cell transcriptomics" was published in Nature Methods. The paper introduces a ...Read more

[nsfc.gov.cn nsfc.gov.cn](https://www.nsfc.gov.cn/p1/3381/2824/66768.html)  

关于发布可解释、可通用的下一代人工智能方法&lt;br&gt;重大研究计划2025年度项目指南的通告

项目指南 关于发布可解释、可通用的下一代人工智能方法 重大研究计划2025年度项目指南的通告 日期：2025-01-26 国科金发计〔2025〕12号 国家自然科学基金委员会现发布可解释、可通用的下一代人工智能方法重大研究计划2025年度项目指南，请申请人及依托单位按项目指南所述要求和注意事项申请。 国家自然科学基金委员会 2025年1月24日 可解释、可通用的下一代人工智...

[ln.gov.cn ln.gov.cn](https://wsjk.ln.gov.cn/wsjk/zfxxgk/fdzdgknr/lzyj/xzfg/2025103112592010583/)  

中华人民共和国人类遗传资源管理条例

当前位置： 首页 &gt; 政府信息公开 &gt; 法定主动公开内容 &gt; 履职依据 &gt; 行政法规 中华人民共和国人类遗传资源管理条例 发布时间：2025-10-31 编辑：辽宁省卫生健康委管理员 来源：国务院 附件下载： 35.中华人民共和国人类遗传资源管理条例（2024）.pdf

[vizgen.com vizgen.com](https://vizgen.com/resources/scgpt-spatial-continual-pretraining-of-single-cell-foundation-model-for-spatial-transcriptomics/)  

scGPT-spatial: Continual Pretraining of Single-Cell Foundation ...

We introduce scGPT-spatial, a specialized foundation model for spatial transcriptomics continually pretrained on our previously published scGPT scRNA-seq ...

[beijing.gov.cn beijing.gov.cn](https://invest.beijing.gov.cn/zwgk/sqgzdt/202512/t20251215_4342747.html)  

GHDDI自研“AI孔明”制药平台在京发布，以AI全流程设计引领新药研发新范式\_市区工作动态\_北京市投资促进服务局

GHDDI自研“AI孔明”制药平台在京发布，以AI全流程设计引领新药研发新范式 时间： 2025-12-15 15:04 来源：全球健康药物研发中心 2025年12月11日，北京 — 全球健康药物研发中心（GHDDI）在京成功举办“‘AI孔明’智驭新药未来”主题活动，正式发布由中国自主研发的、率先实现药物研发全流程智能设计的AI平台—“AI孔明”。该平台的问世，标志着中国在利用人工智能...

北京市持续激发创新医药发展活力

北京市持续激发创新医药发展活力 \* 发布日期：2025-04-10 \* 来源：中国科技网 \* Image: 文字变小 Image: 恢复文字大小 Image: 文字变大 \* 4月7日，北京市医保局等九部门联合推出《北京市支持创新医药高质量发展若干措施（2025年）》。4月8日，北京市卫生健康委（以下简称市卫健委）表示，北京将聚焦临床试验提质增效、促进创新药械入院应用和人工智能赋能创新医药发展...

解读：《北京市加快推动“人工智能+医药健康”创新发展行动计划（2025-2027年）》\_政策解读\_北京市科学技术委员会、中关村科技园区管理委员会

解读：《北京市加快推动“人工智能+医药健康”创新发展行动计划（2025-2027年）》 日期：2025-07-03 21:31 来源：北京市科学技术委员会、中关村科技园区管理委员会 《北京市加快推动“人工智能+医药健康”创新发展行动计划（2025-2027年）》（以下简称《行动计划》）已正式印发。现将有关内容解读如下： 一、出台背景 作为新一轮科技革命和产业变革的重要驱动力量，以人工智能...

[lifesciencesaihandbook.com lifesciencesaihandbook.com](https://lifesciencesaihandbook.com/cells/single-cell-models.html)  

Single-Cell Foundation Models - The Life Sciences AI Handbook

by B Tegomoh · 2026 — Single-cell biology produced its foundation-model wave between 2022 and 2024. scGPT, Geneformer, scFoundation, scBERT, UCE ( Nature Rosen et ...Read more

[cq.gov.cn cq.gov.cn](https://kjj.cq.gov.cn/zwgk_176/fdzdgknr/zcwj/gwybmgz/202405/t20240529_13247994.html)  

国务院部门规章\_重庆市科学技术局门户网站

[ 索引号 ] | 11500000MB15895317/2024-00028 | [ 发文字号 ] | [ 主题分类 ] | 科技 | [ 体裁分类 ] | 部门规章 [ 发布机构 ] | 市科技局 [ 成文日期 ] | 2024-05-29 | [ 发布日期 ] | 2024-05-29 [ 索引号 ] | 11500000MB15895317/2024-00028 [...

[shanghai.gov.cn shanghai.gov.cn](https://www.shanghai.gov.cn/nw4411/20250117/c656f4eafa214956a0b30f4ff6e86aa4.html)  

人工智能生物医药融合 如何实现数据共享共用 代表委员建议 加快探索标准化机制 构建统一平台

人工智能生物医药融合 如何实现数据共享共用 代表委员建议 加快探索标准化机制 构建统一平台 2025-01-17 来源：解放日报 字号： 大 中 小 记者 邬林桦 周程祎 人工智能和生物医药，都是上海重点发展的先导产业，两者融合、彼此赋能，正逐渐成为产业变革的重要力量。代表委员们认为，建设“人工智能+生物医药”创新高地，上海已走在全国前列，但仍有些问题亟待解决。 市工商联调研民营企业时...

[zibo.gov.cn zibo.gov.cn](https://www.zibo.gov.cn/art/2025/5/13/art_18394_2914823.html)  

淄博市人民政府 投资政策 〖山东·产业相关〗关于加快人工智能赋能重点领域高质量发展的推进方案

〖山东·产业相关〗关于加快人工智能赋能重点领域高质量发展的推进方案 发布日期： 2025-05-13 10:41:10 浏览次数： 字体：[ 大 中 小 ] 山东省人民政府办公厅印发《关于加快人工智能赋能重点领域高质量发展的推进方案》的通知鲁政办字〔2025〕48号 各市人民政府，各县（市、区）人民政府，省政府各部门、各直属机构，各大企业，各高等院校：《关于加快人工智能赋能重点领域高质量发展...

[fushun.gov.cn fushun.gov.cn](https://fskjj.fushun.gov.cn/006/006001/006001002/20240612/edf064cd-09c2-454c-a279-d05dba676073.html)  

《人类遗传资源管理条例实施细则》政策解读\_抚顺科技局

《人类遗传资源管理条例实施细则》政策解读 〖信息时间：2024-06-12 阅读次数：〗 〖我要打印〗 〖〗 为深入落实《中华人民共和国人类遗传资源管理条例》（以下简称《条例》），进一步提高我国人类遗传资源管理规范化水平，科技部印发了《人类遗传资源管理条例实施细则》（以下简称《实施细则》）。针对《实施细则》公众关心的有关问题，解读如下： 问题1：《实施细则》制定的背景和过程？ 答：为加...

[ndrc.gov.cn ndrc.gov.cn](https://www.ndrc.gov.cn/xxgk/jd/jd/202508/t20250826_1400077.html)  

〖以技术持续创新支撑“人工智能+”行动加速落地〗-国家发展和改革委员会

以技术持续创新支撑“人工智能+”行动加速落地 发布时间：2025/08/26 来源：高技术司 人工智能是引领新一轮科技革命和产业变革的具有“头雁”效应的战略性技术。近期，国务院印发《关于深入实施“人工智能+”行动的意见》（以下简称《意见》），要求大力推进人工智能规模化商业化应用，充分发挥我国产业体系完备、市场规模大、应用场景丰富等优势，推动人工智能在经济社会发展各领域加快普及、深度融合，形...

Connector sources scanned

No connector sources scanned

## 公开 Activity（页面顺序）

Research activity

Planning a current biomedical research review

I’m organizing the review around model capabilities, multi-omics and patient heterogeneity, interpretability, clinical translation, regulation, risks, bottlenecks, and future research priorities. I’m prioritizing authoritative primary studies and recent sources, while comparing representative models such as AlphaFold, docking systems, molecular language models, and biomedical large language models. I’ll also distinguish genuine simulation from prediction, generation, and clinical text processing.

Searching

[Open source www.nature.com](https://www.nature.com/articles/s41586-024-07487-w)  
[Open source single-market-economy.ec.europa.eu](https://single-market-economy.ec.europa.eu/single-market_en)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=xvyxEaoSd1s)  
[Open source www.srb.europa.eu](https://www.srb.europa.eu/en/node/1)  
[Open source www.cultofpedagogy.com](https://www.cultofpedagogy.com/single-point-rubric/)  
[Open source www.enisa.europa.eu](https://www.enisa.europa.eu/topics/product-security/single-reporting-platform-srp)  
[Open source play.google.com](https://play.google.com/store/apps/details?hl=en_US&id=com.single.dating)  
[Open source jamesclear.com](https://jamesclear.com/great-speeches/the-danger-of-a-single-story-by-chimamanda-ngozi-adichie)  
[Open source www.unodc.org](https://www.unodc.org/pdf/convention_1961_en.pdf)  

Searching 8 websites

[Open source www.nature.com](https://www.nature.com/articles/s41586-024-07487-w)  
[Open source single-market-economy.ec.europa.eu](https://single-market-economy.ec.europa.eu/single-market_en)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=xvyxEaoSd1s)  
[Open source www.srb.europa.eu](https://www.srb.europa.eu/en/node/1)  
[Open source www.cultofpedagogy.com](https://www.cultofpedagogy.com/single-point-rubric/)  
[Open source www.enisa.europa.eu](https://www.enisa.europa.eu/topics/product-security/single-reporting-platform-srp)  
[Open source play.google.com](https://play.google.com/store/apps/details?hl=en_US&id=com.single.dating)  
[Open source jamesclear.com](https://jamesclear.com/great-speeches/the-danger-of-a-single-story-by-chimamanda-ngozi-adichie)  

Searching

[Open source www.nature.com](https://www.nature.com/articles/s41592-024-02201-0)  
[Open source github.com](https://github.com/bowang-lab/scgpt)  
[Open source virtualcellmodels.cziscience.com](https://virtualcellmodels.cziscience.com/model/scgpt)  

Searching

[Open source www.nature.com](https://www.nature.com/articles/s41587-023-01905-6)  

Searching

[Open source www.biorxiv.org](https://www.biorxiv.org/content/10.64898/2026.04.01.714123v1.full-text)  
[Open source link.springer.com](https://link.springer.com/article/10.1186/s13059-025-03574-x)  
[Open source bm2-lab.github.io](https://bm2-lab.github.io/scPerturBench-reproducibility/)  
[Open source www.reddit.com](https://www.reddit.com/r/bioinformatics/comments/1qu1i1p/where_do_foundation_models_like_geneformer_fit/)  
[Open source x.com](https://x.com/BiologyAIDaily/status/1923972504059556201)  
[Open source odsc.medium.com](https://odsc.medium.com/in-silico-perturbation-meets-single-cell-foundation-models-from-zero-shot-potential-to-fine-tuned-0f1b4da054c4)  
[Open source github.com](https://github.com/bm2-lab/scPerturBench)  
[Open source arxiv.org](https://arxiv.org/abs/2603.02952)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/AlphaGenome)  

Searching

[Open source www.biorxiv.org](https://www.biorxiv.org/content/10.64898/2026.04.01.714123v1.full-text)  
[Open source link.springer.com](https://link.springer.com/article/10.1186/s13059-025-03574-x)  
[Open source bm2-lab.github.io](https://bm2-lab.github.io/scPerturBench-reproducibility/)  
[Open source www.reddit.com](https://www.reddit.com/r/bioinformatics/comments/1qu1i1p/where_do_foundation_models_like_geneformer_fit/)  
[Open source x.com](https://x.com/BiologyAIDaily/status/1923972504059556201)  
[Open source odsc.medium.com](https://odsc.medium.com/in-silico-perturbation-meets-single-cell-foundation-models-from-zero-shot-potential-to-fine-tuned-0f1b4da054c4)  
[Open source github.com](https://github.com/bm2-lab/scPerturBench)  
[Open source arxiv.org](https://arxiv.org/abs/2603.02952)  

Searching

[Open source www.nature.com](https://www.nature.com/articles/s41586-025-10014-0)  
[Open source deepmind.google](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/)  
[Open source arcinstitute.org](https://arcinstitute.org/news/arc-vevo)  
[Open source www.biorxiv.org](https://www.biorxiv.org/content/10.1101/2025.02.20.639398v1)  

Searching

[Open source www.nature.com](https://www.nature.com/articles/s42256-022-00580-7)  
[Open source academic.oup.com](https://academic.oup.com/bib/article/23/6/bbac409/6713511)  

Searching

[Open source pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/33381841/)  
[Open source mlanthology.org](https://mlanthology.org/iclr/2023/corso2023iclr-diffdock/)  
[Open source dblp.org](https://dblp.org/rec/conf/iclr/CorsoSJBJ23.html)  
[Open source github.com](https://github.com/kimmo1019/DeepCDR)  
[Open source link.springer.com](https://link.springer.com/article/10.1186/s12859-023-05618-0)  

Searching

[Open source www.merriam-webster.com](https://www.merriam-webster.com/dictionary/informed)  
[Open source clinicaldata.ema.europa.eu](https://clinicaldata.ema.europa.eu/)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=SQJVDwk3QFI)  
[Open source catalogues.ema.europa.eu](https://catalogues.ema.europa.eu/)  
[Open source ascpt.onlinelibrary.wiley.com](https://ascpt.onlinelibrary.wiley.com/)  
[Open source pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/40533548/)  
[Open source register.ema.europa.eu](https://register.ema.europa.eu/)  
[Open source www.rcog.org.uk](https://www.rcog.org.uk/guidance/browse-all-guidance/green-top-guidelines/management-of-monochorionic-twin-pregnancy-green-top-guideline-no-51/)  
[Open source www.reaganlibrary.gov](https://www.reaganlibrary.gov/archives/speech/farewell-address-nation)  
[Open source iris.ema.europa.eu](https://iris.ema.europa.eu/)  
[Open source www.instagram.com](https://www.instagram.com/twin_music_/?hl=ar)  
[Open source eudragmdp.ema.europa.eu](https://eudragmdp.ema.europa.eu/)  
[Open source esubmission.ema.europa.eu](https://esubmission.ema.europa.eu/)  
[Open source pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC5851387/)  
[Open source careers.ema.europa.eu](https://careers.ema.europa.eu/)  
[Open source www.magellanhealthcare.com](https://www.magellanhealthcare.com/health-plans/informed/)  
[Open source esmp.ema.europa.eu](https://esmp.ema.europa.eu/)  
[Open source spor.ema.europa.eu](https://spor.ema.europa.eu/)  
[Open source www.justicecenter.ny.gov](https://www.justicecenter.ny.gov/ep-10-understanding-trauma-and-trauma-informed-approach)  
[Open source eudract.ema.europa.eu](https://eudract.ema.europa.eu/)  
[Open source www.theguardian.com](https://www.theguardian.com/lifeandstyle/2026/may/02/rare-twins-different-dads-the-gift-bbc-radio-4)  

Searching

[Open source www.merriam-webster.com](https://www.merriam-webster.com/dictionary/informed)  
[Open source clinicaldata.ema.europa.eu](https://clinicaldata.ema.europa.eu/)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=SQJVDwk3QFI)  
[Open source catalogues.ema.europa.eu](https://catalogues.ema.europa.eu/)  
[Open source ascpt.onlinelibrary.wiley.com](https://ascpt.onlinelibrary.wiley.com/)  
[Open source pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/40533548/)  
[Open source register.ema.europa.eu](https://register.ema.europa.eu/)  
[Open source www.rcog.org.uk](https://www.rcog.org.uk/guidance/browse-all-guidance/green-top-guidelines/management-of-monochorionic-twin-pregnancy-green-top-guideline-no-51/)  
[Open source www.reaganlibrary.gov](https://www.reaganlibrary.gov/archives/speech/farewell-address-nation)  
[Open source iris.ema.europa.eu](https://iris.ema.europa.eu/)  
[Open source www.instagram.com](https://www.instagram.com/twin_music_/?hl=ar)  
[Open source eudragmdp.ema.europa.eu](https://eudragmdp.ema.europa.eu/)  
[Open source esubmission.ema.europa.eu](https://esubmission.ema.europa.eu/)  
[Open source pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC5851387/)  
[Open source careers.ema.europa.eu](https://careers.ema.europa.eu/)  
[Open source www.magellanhealthcare.com](https://www.magellanhealthcare.com/health-plans/informed/)  
[Open source esmp.ema.europa.eu](https://esmp.ema.europa.eu/)  
[Open source spor.ema.europa.eu](https://spor.ema.europa.eu/)  

Searching

[Open source pubs.acs.org](https://pubs.acs.org/)  
[Open source www.fda.gov](https://www.fda.gov/)  
[Open source pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/)  
[Open source www.youtube.com](https://www.youtube.com/)  
[Open source en.wikipedia.org](https://en.wikipedia.org/)  

Searching

[Open source www.fda.gov](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/considerations-use-artificial-intelligence-support-regulatory-decision-making-drug-and-biological)  
[Open source www.ema.europa.eu](https://www.ema.europa.eu/system/files/documents/scientific-guideline/reflection-paper-use-artificial-intelligence-ai-medicinal-product-lifecycle-en.pdf)  
[Open source pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC8596613/)  
[Open source www.goodwinlaw.com](https://www.goodwinlaw.com/en/insights/publications/2025/01/alerts-lifesciences-aiml-fda-publishes-its-first-draft-guidance)  
[Open source benzifoundation.org](https://benzifoundation.org/reflection-paper-ai-medicinal-products-lifecycle/)  
[Open source pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/39748538/)  
[Open source onlinelibrary.wiley.com](https://onlinelibrary.wiley.com/doi/10.1155/joch/5202999)  
[Open source www.certara.com](https://www.certara.com/blog/how-the-us-fda-midd-paired-pilot-program-helps-sponsors/)  
[Open source ec.europa.eu](https://ec.europa.eu/newsroom/ema/redirection/item/850303/en/3679)  
[Open source www.page-meeting.org](https://www.page-meeting.org/Abstracts/the-new-draft-ema-guidance-on-pbpk-the-qualification-of-the-intended-use-concept/)  
[Open source www.dlapiper.com](https://www.dlapiper.com/en/insights/publications/2025/01/fda-releases-draft-guidance-on-use-of-ai)  
[Open source www.propharmagroup.com](https://www.propharmagroup.com/thought-leadership/faq-model-informed-drug-development-midd-modeling-simulation-ms)  
[Open source biotalk.twobirds.com](https://biotalk.twobirds.com/post/102juyw/emas-finalised-reflection-paper-on-the-use-of-ai)  
[Open source www.tga.gov.au](https://www.tga.gov.au/resources/resources/international-scientific-guidelines-adopted-australia/guideline-reporting-physiologically-based-pharmacokinetic-pbpk-modelling-and-simulation)  
[Open source www.facebook.com](https://www.facebook.com/insife/posts/grip-news-ema-releases-reflection-paper-on-ai-and-machine-learning-in-medicinal-/1053748976536856/)  
[Open source ascpt.onlinelibrary.wiley.com](https://ascpt.onlinelibrary.wiley.com/doi/10.1002/cpt.3525?af=R)  
[Open source casrai.org](https://casrai.org/guides/fda-ai-guidance)  
[Open source www.scirp.org](https://www.scirp.org/reference/referencespapers?referenceid=3997588)  
[Open source www.scilifelab.se](https://www.scilifelab.se/wp-content/uploads/2021/06/Luzon-et-al-CPT-2017.pdf)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=pGB89H-feNU)  
[Open source c-path.org](https://c-path.org/training/model-informed-drug-development-training-course/)  
[Open source www.nsf.org](https://www.nsf.org/life-science-regulatory-news/ema-reflection-paper-on-ai-in-the-medicinal-product-lifecycle)  
[Open source www.linkedin.com](https://www.linkedin.com/pulse/ema-provides-guidelines-pediatric-pbpk-modeling-lynda-graham-mba)  
[Open source www.sternekessler.com](https://www.sternekessler.com/news-insights/client-alerts/fda-issues-draft-guidance-documents-on-artificial-intelligence-for-medical-devices-drugs-and-biological-products/)  
[Open source gabionline.net](https://gabionline.net/switchlanguage/to/gabi_online_es/guidelines/european-position-paper-on-ai-in-medicinal-product-lifecycle)  
[Open source www.researchgate.net](https://www.researchgate.net/publication/311992013_Report_from_EMA_Workshop_on_Qualification_and_Reporting_of_Physiologically-based_Pharmacokinetic_PBPK_Modelling_and_Simulation)  
[Open source www.reuters.com](https://www.reuters.com/world/us/us-fda-phase-out-animal-testing-drug-development-2025-04-10/)  
[Open source apnews.com](https://apnews.com/article/a5aaa5501ae15f264bbd20d0dffa4dc4)  
[Open source www.washingtonpost.com](https://www.washingtonpost.com/wp-intelligence/health-brief/2025/10/29/biosimilars-obamacare-premiums-opiods/)  
[Open source www.investors.com](https://www.investors.com/news/technology/genedx-stock-fda-ai-draft-guidance/)  

Searching

[Open source www.fda.gov](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/considerations-use-artificial-intelligence-support-regulatory-decision-making-drug-and-biological)  
[Open source www.ema.europa.eu](https://www.ema.europa.eu/system/files/documents/scientific-guideline/reflection-paper-use-artificial-intelligence-ai-medicinal-product-lifecycle-en.pdf)  
[Open source pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC8596613/)  
[Open source www.goodwinlaw.com](https://www.goodwinlaw.com/en/insights/publications/2025/01/alerts-lifesciences-aiml-fda-publishes-its-first-draft-guidance)  
[Open source benzifoundation.org](https://benzifoundation.org/reflection-paper-ai-medicinal-products-lifecycle/)  
[Open source pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/39748538/)  
[Open source onlinelibrary.wiley.com](https://onlinelibrary.wiley.com/doi/10.1155/joch/5202999)  
[Open source www.certara.com](https://www.certara.com/blog/how-the-us-fda-midd-paired-pilot-program-helps-sponsors/)  
[Open source ec.europa.eu](https://ec.europa.eu/newsroom/ema/redirection/item/850303/en/3679)  
[Open source www.page-meeting.org](https://www.page-meeting.org/Abstracts/the-new-draft-ema-guidance-on-pbpk-the-qualification-of-the-intended-use-concept/)  
[Open source www.dlapiper.com](https://www.dlapiper.com/en/insights/publications/2025/01/fda-releases-draft-guidance-on-use-of-ai)  
[Open source www.propharmagroup.com](https://www.propharmagroup.com/thought-leadership/faq-model-informed-drug-development-midd-modeling-simulation-ms)  
[Open source biotalk.twobirds.com](https://biotalk.twobirds.com/post/102juyw/emas-finalised-reflection-paper-on-the-use-of-ai)  
[Open source www.tga.gov.au](https://www.tga.gov.au/resources/resources/international-scientific-guidelines-adopted-australia/guideline-reporting-physiologically-based-pharmacokinetic-pbpk-modelling-and-simulation)  
[Open source www.facebook.com](https://www.facebook.com/insife/posts/grip-news-ema-releases-reflection-paper-on-ai-and-machine-learning-in-medicinal-/1053748976536856/)  
[Open source ascpt.onlinelibrary.wiley.com](https://ascpt.onlinelibrary.wiley.com/doi/10.1002/cpt.3525?af=R)  
[Open source casrai.org](https://casrai.org/guides/fda-ai-guidance)  
[Open source www.scirp.org](https://www.scirp.org/reference/referencespapers?referenceid=3997588)  
[Open source www.scilifelab.se](https://www.scilifelab.se/wp-content/uploads/2021/06/Luzon-et-al-CPT-2017.pdf)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=pGB89H-feNU)  
[Open source c-path.org](https://c-path.org/training/model-informed-drug-development-training-course/)  
[Open source www.nsf.org](https://www.nsf.org/life-science-regulatory-news/ema-reflection-paper-on-ai-in-the-medicinal-product-lifecycle)  
[Open source www.linkedin.com](https://www.linkedin.com/pulse/ema-provides-guidelines-pediatric-pbpk-modeling-lynda-graham-mba)  
[Open source www.sternekessler.com](https://www.sternekessler.com/news-insights/client-alerts/fda-issues-draft-guidance-documents-on-artificial-intelligence-for-medical-devices-drugs-and-biological-products/)  
[Open source gabionline.net](https://gabionline.net/switchlanguage/to/gabi_online_es/guidelines/european-position-paper-on-ai-in-medicinal-product-lifecycle)  
[Open source www.researchgate.net](https://www.researchgate.net/publication/311992013_Report_from_EMA_Workshop_on_Qualification_and_Reporting_of_Physiologically-based_Pharmacokinetic_PBPK_Modelling_and_Simulation)  

Searching

[Open source www.cde.org.cn](https://www.cde.org.cn/main/news/viewInfoCommon/3a55263f274e0525c1172a37f5b04a8e)  
[Open source english.nmpa.gov.cn](https://english.nmpa.gov.cn/2026-08/20/c_1210674.htm)  
[Open source wjw.wuxi.gov.cn](https://wjw.wuxi.gov.cn/doc/2024/06/04/4323063.shtml)  
[Open source xzfg.moj.gov.cn](https://xzfg.moj.gov.cn/mobile/law/detail?LawID=1714)  

Searching

[Open source www.cac.gov.cn](https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm)  
[Open source www.samr.gov.cn](https://www.samr.gov.cn/wljys/gzzd/art/2023/art_3ef1e889c1e644d4b65b5f5c7f432386.html)  

Searching

[Open source www.hhs.gov](https://www.hhs.gov/ohrp/regulations-and-policy/guidance/index.html)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=Epgo8ixX6Wo)  
[Open source www.bis.gov](https://www.bis.gov/media/documents/bis-guidance-may-31-2026.pdf)  
[Open source www.epa.gov](https://www.epa.gov/home)  
[Open source www.justice.gov](https://www.justice.gov/ag/media/1409486/dl)  
[Open source www.consumerfinance.gov](https://www.consumerfinance.gov/)  
[Open source www.cms.gov](https://www.cms.gov/priorities/innovation/innovation-models/guide)  
[Open source www.usa.gov](https://www.usa.gov/state-consumer)  
[Open source www.federalregister.gov](https://www.federalregister.gov/documents/2024/02/13/2024-02623/inventorship-guidance-for-ai-assisted-inventions)  
[Open source www.sba.gov](https://www.sba.gov/loans/covid-era-programs/)  
[Open source ico.org.uk](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/biometric-data-guidance-biometric-recognition/)  
[Open source www.merriam-webster.com](https://www.merriam-webster.com/dictionary/protection)  
[Open source ghgprotocol.org](https://ghgprotocol.org/land-sector-and-removals-guidance)  
[Open source www.whistleblowers.gov](https://www.whistleblowers.gov/)  
[Open source roll20.net](https://roll20.net/compendium/dnd5e/Guidance)  
[Open source www.edpb.europa.eu](https://www.edpb.europa.eu/home_en)  
[Open source www.aap.org](https://www.aap.org/ImmunizationSchedule?srsltid=AfmBOooq2PmtzoYEYisEck9BY0mE1tcQTvGWk4tH3xzYVgMn3Z1ov5x-)  
[Open source www.fisheries.noaa.gov](https://www.fisheries.noaa.gov/topic/marine-mammal-protection)  
[Open source www.whitehouse.gov](https://www.whitehouse.gov/wp-content/uploads/2025/03/OSTP-Guidance-for-GSS-June-2025.pdf)  
[Open source www.imdb.com](https://www.imdb.com/title/tt28698590/)  

Searching

[Open source www.hhs.gov](https://www.hhs.gov/ohrp/regulations-and-policy/guidance/index.html)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=Epgo8ixX6Wo)  
[Open source www.bis.gov](https://www.bis.gov/media/documents/bis-guidance-may-31-2026.pdf)  
[Open source www.epa.gov](https://www.epa.gov/home)  
[Open source www.justice.gov](https://www.justice.gov/ag/media/1409486/dl)  
[Open source www.consumerfinance.gov](https://www.consumerfinance.gov/)  
[Open source www.cms.gov](https://www.cms.gov/priorities/innovation/innovation-models/guide)  
[Open source www.usa.gov](https://www.usa.gov/state-consumer)  
[Open source www.federalregister.gov](https://www.federalregister.gov/documents/2024/02/13/2024-02623/inventorship-guidance-for-ai-assisted-inventions)  
[Open source www.sba.gov](https://www.sba.gov/loans/covid-era-programs/)  
[Open source ico.org.uk](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/biometric-data-guidance-biometric-recognition/)  
[Open source www.merriam-webster.com](https://www.merriam-webster.com/dictionary/protection)  
[Open source ghgprotocol.org](https://ghgprotocol.org/land-sector-and-removals-guidance)  
[Open source www.whistleblowers.gov](https://www.whistleblowers.gov/)  
[Open source roll20.net](https://roll20.net/compendium/dnd5e/Guidance)  
[Open source www.edpb.europa.eu](https://www.edpb.europa.eu/home_en)  
[Open source www.aap.org](https://www.aap.org/ImmunizationSchedule?srsltid=AfmBOooq2PmtzoYEYisEck9BY0mE1tcQTvGWk4tH3xzYVgMn3Z1ov5x-)  
[Open source www.fisheries.noaa.gov](https://www.fisheries.noaa.gov/topic/marine-mammal-protection)  

Searching

[Open source www.who.int](https://www.who.int/news/item/18-01-2024-who-releases-ai-ethics-and-governance-guidance-for-large-multi-modal-models)  
[Open source eur-lex.europa.eu](https://eur-lex.europa.eu/eli/reg/2024/1689/2026-07-27/eng)  

Refining the research report’s central argument

I’m framing the report around a key distinction: today’s models are strong at specialized tasks such as molecular structure, docking, property prediction, and some cellular perturbation forecasts, but they cannot yet provide reliable, causal, end-to-end simulations from drug binding through individual clinical outcomes. I’m also covering multi-omics, heterogeneity, interpretability, validation, regulation, hybrid mechanistic approaches, and a five-to-ten-year roadmap.

Searching

[Open source www.nature.com](https://www.nature.com/articles/s41587-022-01284-4)  
[Open source pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/39863071/)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=433SmtTc0TA)  
[Open source www.multimodal.org.uk](https://www.multimodal.org.uk/)  
[Open source www.gigamon.com](https://www.gigamon.com/products/deep-observability-pipeline.html)  
[Open source www.deeplearning.ai](https://www.deeplearning.ai/courses/vibe-coding-101-with-replit)  
[Open source www.nea.gov.sg](https://www.nea.gov.sg/our-services/public-cleanliness/toilets-management/coffeeshop-toilet-grants/ctcg)  
[Open source www.deepl.com](https://www.deepl.com/en/translator)  
[Open source www.tc.columbia.edu](https://www.tc.columbia.edu/digitalfuturesinstitute/multimodal-toolkit/video-what-is-multimodal/)  
[Open source www.instagram.com](https://www.instagram.com/thedeeeep/?hl=en)  

Searching

[Open source www.fda.gov](https://www.fda.gov/drugs/drug-safety-and-availability/fda-qualifies-first-ai-drug-development-tool-will-be-used-mash-clinical-trials)  
[Open source pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/?term=NCT05938920)  
[Open source www.nature.com](https://www.nature.com/articles/s41587-024-02143-0)  

Searching

[Open source english.nmpa.gov.cn](https://english.nmpa.gov.cn/2026-08/20/c_1210673.htm)  
[Open source www.cde.org.cn](https://www.cde.org.cn/main/news/viewInfoCommon/3a55263f274e0525c1172a37f5b04a8e)  
[Open source gma.caict.ac.cn](https://gma.caict.ac.cn/plat/news/full-collection-of-blue-books-published-by-caict-in-2024)  
[Open source aihub.caict.ac.cn](https://aihub.caict.ac.cn/docs/qzNUc4Ssvduc)  

Searching

[Open source www.youtube.com](https://www.youtube.com/watch?v=NI3KtR3LoqM)  
[Open source www.cell.com](https://www.cell.com/iscience/fulltext/S2589-0042%2826%2900657-7)  
[Open source www.nature.com](https://www.nature.com/articles/s41467-022-32407-9)  
[Open source www.internal-displacement.org](https://www.internal-displacement.org/global-report/grid2025/)  
[Open source www.healthline.com](https://www.healthline.com/nutrition/gut-microbiome-and-health)  
[Open source www.hepi.ac.uk](https://www.hepi.ac.uk/reports/student-generative-ai-survey-2025/)  
[Open source www.epo.org](https://www.epo.org/en/about-us/statistics/technology-dashboard-2025)  
[Open source www.genome.gov](https://www.genome.gov/genetics-glossary/Microbiome)  
[Open source uist.acm.org](https://uist.acm.org/2026/)  
[Open source www.ntu.edu.sg](https://www.ntu.edu.sg/medicine/CMM)  
[Open source www.unep.org](https://www.unep.org/resources/emissions-gap-report-2025)  

Searching

[Open source link.springer.com](https://link.springer.com/article/10.1186/s13059-025-03574-x)  
[Open source arcinstitute.org](https://arcinstitute.org/news/virtual-cell-challenge-2025-wrap-up)  

Searching

[Open source academy.openai.com](https://academy.openai.com/public/videos/introduction-to-codex-2026-03-02)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=pjNI9K1D_xo)  
[Open source go.nature.com](https://go.nature.com/ykfvNW)  
[Open source www.worldbank.org](https://www.worldbank.org/en/news/press-release/2020/10/07/covid-19-to-add-as-many-as-150-million-extreme-poor-by-2021)  
[Open source deploymentsafety.openai.com](https://deploymentsafety.openai.com/)  
[Open source www.instagram.com](https://www.instagram.com/zuck/)  
[Open source partnerships.nature.com](https://partnerships.nature.com/)  
[Open source www.meta.com](https://www.meta.com/meta-verified/?srsltid=AfmBOoolBdyfUN1-OJITxsuE0_X18xdHb2q97A7Zv-UGa0cQ8j4tYioC)  
[Open source arabicedition.nature.com](https://arabicedition.nature.com/)  
[Open source sugarspunrun.com](https://sugarspunrun.com/million-dollar-deviled-eggs/)  
[Open source openai.com](https://openai.com/foundation/)  
[Open source forum.openai.com](https://forum.openai.com/public/videos/event-replay-from-terminal-to-turnaround-how-gitlabs-co-founder-leveraged-chatgpt-in-his-cancer-fight-2026-03-18)  
[Open source prism.openai.com](https://prism.openai.com/)  
[Open source communities.nature.com](https://communities.nature.com/)  
[Open source conferences.nature.com](https://conferences.nature.com/)  
[Open source www.unep.org](https://www.unep.org/node)  
[Open source www.facebook.com](https://www.facebook.com/JCollierMusic/videos/my-conducting-the-orchestra-video-just-hit-4-million-views-im-ever-so-grateful-t/664665456504414/)  
[Open source chat.openai.com](https://chat.openai.com/)  

Searching

[Open source academy.openai.com](https://academy.openai.com/public/videos/introduction-to-codex-2026-03-02)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=pjNI9K1D_xo)  
[Open source go.nature.com](https://go.nature.com/ykfvNW)  
[Open source www.worldbank.org](https://www.worldbank.org/en/news/press-release/2020/10/07/covid-19-to-add-as-many-as-150-million-extreme-poor-by-2021)  
[Open source deploymentsafety.openai.com](https://deploymentsafety.openai.com/)  
[Open source www.instagram.com](https://www.instagram.com/zuck/)  
[Open source partnerships.nature.com](https://partnerships.nature.com/)  
[Open source www.meta.com](https://www.meta.com/meta-verified/?srsltid=AfmBOoolBdyfUN1-OJITxsuE0_X18xdHb2q97A7Zv-UGa0cQ8j4tYioC)  
[Open source arabicedition.nature.com](https://arabicedition.nature.com/)  
[Open source sugarspunrun.com](https://sugarspunrun.com/million-dollar-deviled-eggs/)  
[Open source openai.com](https://openai.com/foundation/)  
[Open source forum.openai.com](https://forum.openai.com/public/videos/event-replay-from-terminal-to-turnaround-how-gitlabs-co-founder-leveraged-chatgpt-in-his-cancer-fight-2026-03-18)  
[Open source prism.openai.com](https://prism.openai.com/)  
[Open source communities.nature.com](https://communities.nature.com/)  
[Open source conferences.nature.com](https://conferences.nature.com/)  

Searching

[Open source www.nature.com](https://www.nature.com/articles/s41467-026-72198-x)  
[Open source www.researchgate.net](https://www.researchgate.net/publication/371204614_Large_Scale_Foundation_Model_on_Single-cell_Transcriptomics)  
[Open source pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/38844628/)  
[Open source openreview.net](https://openreview.net/forum?id=Vk2sfKAdeu&noteId=omI9iBAAHr)  
[Open source www.biorxiv.org](https://www.biorxiv.org/content/10.1101/2023.05.29.542705v2)  
[Open source github.com](https://github.com/Perturbation-Response-Prediction/PRnet)  
[Open source medium.com](https://medium.com/%40anatolybuchin/predicting-donor-age-from-nk-cells-using-geneformer-987430d07aca)  
[Open source scispace.com](https://scispace.com/papers/large-scale-foundation-model-on-single-cell-transcriptomics-zlar8c88)  
[Open source experiments.springernature.com](https://experiments.springernature.com/articles/10.1038/s41592-024-02305-7)  
[Open source www.computer.org](https://www.computer.org/csdl/proceedings-article/bibm/2025/11356145/2e1jlN0FaDe)  
[Open source www.scribd.com](https://www.scribd.com/document/871939988/Large-scale-Foundation-Model-on-Single-cell-Transcriptomics)  
[Open source d2j16w31g89z0j.cloudfront.net](https://d2j16w31g89z0j.cloudfront.net/site/biml2026/lecture2/on33.pdf)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=VXCfNxNKjmk)  
[Open source www.linkedin.com](https://www.linkedin.com/posts/shukrala-shifa-bsc-mph-00794b285_multi-disciplinary-team-genetics-and-genomic-activity-7416459594518028288-URlo)  
[Open source xqiu625.github.io](https://xqiu625.github.io/ai4bio-concepts/single-cell-analysis/perturbation-prediction_modeling.html)  
[Open source huggingface.co](https://huggingface.co/perturblab/scfoundation-cell)  
[Open source arxiv.org](https://arxiv.org/abs/2505.12638)  

Searching

[Open source www.nature.com](https://www.nature.com/articles/s41467-026-72198-x)  
[Open source www.researchgate.net](https://www.researchgate.net/publication/371204614_Large_Scale_Foundation_Model_on_Single-cell_Transcriptomics)  
[Open source pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/38844628/)  
[Open source openreview.net](https://openreview.net/forum?id=Vk2sfKAdeu&noteId=omI9iBAAHr)  
[Open source www.biorxiv.org](https://www.biorxiv.org/content/10.1101/2023.05.29.542705v2)  
[Open source github.com](https://github.com/Perturbation-Response-Prediction/PRnet)  
[Open source medium.com](https://medium.com/%40anatolybuchin/predicting-donor-age-from-nk-cells-using-geneformer-987430d07aca)  
[Open source scispace.com](https://scispace.com/papers/large-scale-foundation-model-on-single-cell-transcriptomics-zlar8c88)  
[Open source experiments.springernature.com](https://experiments.springernature.com/articles/10.1038/s41592-024-02305-7)  
[Open source www.computer.org](https://www.computer.org/csdl/proceedings-article/bibm/2025/11356145/2e1jlN0FaDe)  
[Open source www.scribd.com](https://www.scribd.com/document/871939988/Large-scale-Foundation-Model-on-Single-cell-Transcriptomics)  
[Open source d2j16w31g89z0j.cloudfront.net](https://d2j16w31g89z0j.cloudfront.net/site/biml2026/lecture2/on33.pdf)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=VXCfNxNKjmk)  
[Open source www.linkedin.com](https://www.linkedin.com/posts/shukrala-shifa-bsc-mph-00794b285_multi-disciplinary-team-genetics-and-genomic-activity-7416459594518028288-URlo)  
[Open source xqiu625.github.io](https://xqiu625.github.io/ai4bio-concepts/single-cell-analysis/perturbation-prediction_modeling.html)  

Searching

[Open source www.instagram.com](https://www.instagram.com/kyliejenner/?hl=ar)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=TJ9GYswlzsI)  
[Open source www.iea.org](https://www.iea.org/news/iea-member-countries-to-carry-out-largest-ever-oil-stock-release-amid-market-disruptions-from-middle-east-conflict)  
[Open source www.facebook.com](https://www.facebook.com/JCollierMusic/videos/my-conducting-the-orchestra-video-just-hit-4-million-views-im-ever-so-grateful-t/664665456504414/)  
[Open source digital-strategy.ec.europa.eu](https://digital-strategy.ec.europa.eu/en/policies/1-million-genomes)  
[Open source stackoverflow.blog](https://stackoverflow.blog/2017/05/23/stack-overflow-helping-one-million-developers-exit-vim/)  

Worked for 7m 40s

Worked for 7m 40s

Done

Searching

[Open source nature.com](https://www.nature.com/articles/s41467-025-63947-5?utm_source=chatgpt.com)  
[Open source biorxiv.org](https://www.biorxiv.org/content/10.1101/2023.04.30.538439v1?utm_source=chatgpt.com)  
[Open source nih.gov](https://pubmed.ncbi.nlm.nih.gov/38844628/?utm_source=chatgpt.com)  
[Open source merriam-webster.com](https://www.merriam-webster.com/dictionary/informed?utm_source=chatgpt.com)  
[Open source acs.org](https://pubs.acs.org/doi/10.1021/acs.jcim.3c01060?utm_source=chatgpt.com)  
[Open source cac.gov.cn](https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm?utm_source=chatgpt.com)  
[Open source hhs.gov](https://www.hhs.gov/ohrp/regulations-and-policy/guidance/index.html?utm_source=chatgpt.com)  
[Open source youtube.com](https://www.youtube.com/watch?v=xvyxEaoSd1s&utm_source=chatgpt.com)  
[Open source openai.com](https://academy.openai.com/public/videos/introduction-to-codex-2026-03-02?utm_source=chatgpt.com)  
[Open source instagram.com](https://www.instagram.com/twin_music_/?hl=ar&utm_source=chatgpt.com)  
[Open source europa.eu](https://single-market-economy.ec.europa.eu/single-market_en?utm_source=chatgpt.com)  
[Open source deepmind.google](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/?utm_source=chatgpt.com)  
[Open source fda.gov](https://www.fda.gov/drugs/development-resources/model-informed-drug-development-paired-meeting-program?utm_source=chatgpt.com)  
[Open source who.int](https://www.who.int/publications/b/70584?utm_source=chatgpt.com)  
[Open source cell.com](https://www.cell.com/iscience/fulltext/S2589-0042%2826%2900657-7?utm_source=chatgpt.com)  
[Open source github.com](https://github.com/bowang-lab/scgpt?utm_source=chatgpt.com)  
[Open source springer.com](https://link.springer.com/article/10.1186/s13059-025-03781-6?utm_source=chatgpt.com)  
[Open source arcinstitute.org](https://arcinstitute.org/news/arc-vevo?utm_source=chatgpt.com)  
[Open source bis.gov](https://www.bis.gov/media/documents/bis-guidance-may-31-2026.pdf?utm_source=chatgpt.com)  
[Open source caict.ac.cn](https://gma.caict.ac.cn/plat/news/full-collection-of-blue-books-published-by-caict-in-2024?utm_source=chatgpt.com)  
[Open source oup.com](https://academic.oup.com/bioinformatics/article/40/2/btae075/7606338?utm_source=chatgpt.com)  
[Open source epa.gov](https://www.epa.gov/home?utm_source=chatgpt.com)  
[Open source internal-displacement.org](https://www.internal-displacement.org/global-report/grid2025/?utm_source=chatgpt.com)  
[Open source worldbank.org](https://www.worldbank.org/en/news/press-release/2020/10/07/covid-19-to-add-as-many-as-150-million-extreme-poor-by-2021?utm_source=chatgpt.com)  
[Open source researchgate.net](https://www.researchgate.net/publication/311992013_Report_from_EMA_Workshop_on_Qualification_and_Reporting_of_Physiologically-based_Pharmacokinetic_PBPK_Modelling_and_Simulation?utm_source=chatgpt.com)  
[Open source cziscience.com](https://virtualcellmodels.cziscience.com/model/scgpt?utm_source=chatgpt.com)  
[Open source bm2-lab.github.io](https://bm2-lab.github.io/scPerturBench-reproducibility/?utm_source=chatgpt.com)  
[Open source dblp.org](https://dblp.org/rec/conf/iclr/CorsoSJBJ23.html?utm_source=chatgpt.com)  
[Open source wikipedia.org](https://en.wikipedia.org/?utm_source=chatgpt.com)  
[Open source cde.org.cn](https://www.cde.org.cn/zdyz/domesticinfopage?zdyzIdCODE=f044cdf4b7d7286aa12ffb85fc81a74c&utm_source=chatgpt.com)  
[Open source justice.gov](https://www.justice.gov/ag/media/1409486/dl?utm_source=chatgpt.com)  
[Open source healthline.com](https://www.healthline.com/nutrition/gut-microbiome-and-health?utm_source=chatgpt.com)  
[Open source iea.org](https://www.iea.org/news/iea-member-countries-to-carry-out-largest-ever-oil-stock-release-amid-market-disruptions-from-middle-east-conflict?utm_source=chatgpt.com)  
[Open source reddit.com](https://www.reddit.com/r/bioinformatics/comments/1qu1i1p/where_do_foundation_models_like_geneformer_fit/?utm_source=chatgpt.com)  
[Open source moj.gov.cn](https://xzfg.moj.gov.cn/mobile/law/detail?LawID=1714&utm_source=chatgpt.com)  
[Open source consumerfinance.gov](https://www.consumerfinance.gov/?utm_source=chatgpt.com)  
[Open source multimodal.org.uk](https://www.multimodal.org.uk/?utm_source=chatgpt.com)  
[Open source x.com](https://x.com/BiologyAIDaily/status/1923972504059556201?utm_source=chatgpt.com)  
[Open source wiley.com](https://ascpt.onlinelibrary.wiley.com/?utm_source=chatgpt.com)  
[Open source nmpa.gov.cn](https://english.nmpa.gov.cn/2026-08/20/c_1210675.htm?utm_source=chatgpt.com)  
[Open source npc.gov.cn](https://www.npc.gov.cn/npc/c2/c30834/202108/t20210820_313088.html?utm_source=chatgpt.com)  
[Open source cms.gov](https://www.cms.gov/priorities/innovation/innovation-models/guide?utm_source=chatgpt.com)  
[Open source openreview.net](https://openreview.net/venue?id=ICLR.cc&utm_source=chatgpt.com)  
[Open source usa.gov](https://www.usa.gov/state-consumer?utm_source=chatgpt.com)  
[Open source hepi.ac.uk](https://www.hepi.ac.uk/reports/student-generative-ai-survey-2025/?utm_source=chatgpt.com)  
[Open source medium.com](https://odsc.medium.com/in-silico-perturbation-meets-single-cell-foundation-models-from-zero-shot-potential-to-fine-tuned-0f1b4da054c4?utm_source=chatgpt.com)  
[Open source goodwinlaw.com](https://www.goodwinlaw.com/en/insights/publications/2025/01/alerts-lifesciences-aiml-fda-publishes-its-first-draft-guidance?utm_source=chatgpt.com)  
[Open source bypc.gov.cn](https://www.bypc.gov.cn/zfxxgk/bmdwxzjd/bmdw/qkjj/fdzdgknr/lzyj/zcfg/art/2024/art_0fe5c379248b4f28964b4d67bb35103e.html?utm_source=chatgpt.com)  
[Open source federalregister.gov](https://www.federalregister.gov/documents/2024/02/13/2024-02623/inventorship-guidance-for-ai-assisted-inventions?utm_source=chatgpt.com)  
[Open source huggingface.co](https://huggingface.co/tdc/scGPT?utm_source=chatgpt.com)  
[Open source rcog.org.uk](https://www.rcog.org.uk/guidance/browse-all-guidance/green-top-guidelines/management-of-monochorionic-twin-pregnancy-green-top-guideline-no-51/?utm_source=chatgpt.com)  
[Open source sba.gov](https://www.sba.gov/loans/covid-era-programs/?utm_source=chatgpt.com)  
[Open source meta.com](https://www.meta.com/meta-verified/?srsltid=AfmBOoolBdyfUN1-OJITxsuE0_X18xdHb2q97A7Zv-UGa0cQ8j4tYioC&utm_source=chatgpt.com)  
[Open source stackoverflow.blog](https://stackoverflow.blog/2017/05/23/stack-overflow-helping-one-million-developers-exit-vim/?utm_source=chatgpt.com)  
[Open source nvidia.com](https://build.nvidia.com/mit/diffdock/modelcard?utm_source=chatgpt.com)  
[Open source reaganlibrary.gov](https://www.reaganlibrary.gov/archives/speech/farewell-address-nation?utm_source=chatgpt.com)  
[Open source benzifoundation.org](https://benzifoundation.org/reflection-paper-ai-medicinal-products-lifecycle/?utm_source=chatgpt.com)  
[Open source ico.org.uk](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/biometric-data-guidance-biometric-recognition/?utm_source=chatgpt.com)  
[Open source gsjn.gov.cn](https://www.gsjn.gov.cn/zfxxgk/zfbmxxgk/gxj/zcwj/art/2025/art_84af6e2d2e974d17a70a79d1d79fc7d8.html?utm_source=chatgpt.com)  
[Open source sugarspunrun.com](https://sugarspunrun.com/million-dollar-deviled-eggs/?utm_source=chatgpt.com)  
[Open source rna-seqblog.com](https://www.rna-seqblog.com/scgpt-towards-building-a-foundation-model-for-single-cell-multi-omics-using-generative-ai/?utm_source=chatgpt.com)  
[Open source sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S095070512601659X?utm_source=chatgpt.com)  
[Open source ghgprotocol.org](https://ghgprotocol.org/land-sector-and-removals-guidance?utm_source=chatgpt.com)  
[Open source scispace.com](https://scispace.com/papers/large-scale-foundation-model-on-single-cell-transcriptomics-zlar8c88?utm_source=chatgpt.com)  
[Open source cultofpedagogy.com](https://www.cultofpedagogy.com/single-point-rubric/?utm_source=chatgpt.com)  
[Open source certara.com](https://www.certara.com/blog/how-the-us-fda-midd-paired-pilot-program-helps-sponsors/?utm_source=chatgpt.com)  
[Open source miit.gov.cn](https://www.miit.gov.cn/jgsj/zfs/fl/art/2022/art_515a4b20c12f430eab54bb4f56d89f56.html?utm_source=chatgpt.com)  
[Open source whistleblowers.gov](https://www.whistleblowers.gov/?utm_source=chatgpt.com)  
[Open source springernature.com](https://experiments.springernature.com/articles/10.1038/s41592-024-02305-7?utm_source=chatgpt.com)  
[Open source scgpt.readthedocs.io](https://scgpt.readthedocs.io/en/latest/introduction.html?utm_source=chatgpt.com)  
[Open source roll20.net](https://roll20.net/compendium/dnd5e/Guidance?utm_source=chatgpt.com)  
[Open source gigamon.com](https://www.gigamon.com/products/deep-observability-pipeline.html?utm_source=chatgpt.com)  
[Open source hyper.ai](https://hyper.ai/en/news/32623?utm_source=chatgpt.com)  
[Open source page-meeting.org](https://www.page-meeting.org/Abstracts/the-new-draft-ema-guidance-on-pbpk-the-qualification-of-the-intended-use-concept/?utm_source=chatgpt.com)  
[Open source samr.gov.cn](https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bgt/art/2023/art_33654085364e45e2a878c70a06934414.html?utm_source=chatgpt.com)  
[Open source nsfc.gov.cn](https://www.nsfc.gov.cn/p1/3381/2824/66768.html?utm_source=chatgpt.com)  
[Open source computer.org](https://www.computer.org/csdl/proceedings-article/bibm/2025/11356145/2e1jlN0FaDe?utm_source=chatgpt.com)  
[Open source dlapiper.com](https://www.dlapiper.com/en/insights/publications/2025/01/fda-releases-draft-guidance-on-use-of-ai?utm_source=chatgpt.com)  
[Open source aap.org](https://www.aap.org/ImmunizationSchedule?srsltid=AfmBOooq2PmtzoYEYisEck9BY0mE1tcQTvGWk4tH3xzYVgMn3Z1ov5x-&utm_source=chatgpt.com)  
[Open source propharmagroup.com](https://www.propharmagroup.com/thought-leadership/faq-model-informed-drug-development-midd-modeling-simulation-ms?utm_source=chatgpt.com)  
[Open source ln.gov.cn](https://wsjk.ln.gov.cn/wsjk/zfxxgk/fdzdgknr/lzyj/xzfg/2025103112592010583/?utm_source=chatgpt.com)  
[Open source noaa.gov](https://www.fisheries.noaa.gov/topic/marine-mammal-protection?utm_source=chatgpt.com)  
[Open source scribd.com](https://www.scribd.com/document/871939988/Large-scale-Foundation-Model-on-Single-cell-Transcriptomics?utm_source=chatgpt.com)  
[Open source twobirds.com](https://biotalk.twobirds.com/post/102juyw/emas-finalised-reflection-paper-on-the-use-of-ai?utm_source=chatgpt.com)  
[Open source whitehouse.gov](https://www.whitehouse.gov/wp-content/uploads/2025/03/OSTP-Guidance-for-GSS-June-2025.pdf?utm_source=chatgpt.com)  
[Open source deeplearning.ai](https://www.deeplearning.ai/courses/vibe-coding-101-with-replit?utm_source=chatgpt.com)  
[Open source vizgen.com](https://vizgen.com/resources/scgpt-spatial-continual-pretraining-of-single-cell-foundation-model-for-spatial-transcriptomics/?utm_source=chatgpt.com)  
[Open source tga.gov.au](https://www.tga.gov.au/resources/resources/international-scientific-guidelines-adopted-australia/guideline-reporting-physiologically-based-pharmacokinetic-pbpk-modelling-and-simulation?utm_source=chatgpt.com)  
[Open source imdb.com](https://www.imdb.com/title/tt28698590/?utm_source=chatgpt.com)  
[Open source beijing.gov.cn](https://invest.beijing.gov.cn/zwgk/sqgzdt/202512/t20251215_4342747.html?utm_source=chatgpt.com)  
[Open source epo.org](https://www.epo.org/en/about-us/statistics/technology-dashboard-2025?utm_source=chatgpt.com)  
[Open source d2j16w31g89z0j.cloudfront.net](https://d2j16w31g89z0j.cloudfront.net/site/biml2026/lecture2/on33.pdf?utm_source=chatgpt.com)  
[Open source lifesciencesaihandbook.com](https://lifesciencesaihandbook.com/cells/single-cell-models.html?utm_source=chatgpt.com)  
[Open source cq.gov.cn](https://kjj.cq.gov.cn/zwgk_176/fdzdgknr/zcwj/gwybmgz/202405/t20240529_13247994.html?utm_source=chatgpt.com)  
[Open source linkedin.com](https://www.linkedin.com/pulse/ema-provides-guidelines-pediatric-pbpk-modeling-lynda-graham-mba?utm_source=chatgpt.com)  
[Open source google.com](https://play.google.com/store/apps/details?hl=en_US&id=com.single.dating&utm_source=chatgpt.com)  
[Open source magellanhealthcare.com](https://www.magellanhealthcare.com/health-plans/informed/?utm_source=chatgpt.com)  
[Open source facebook.com](https://www.facebook.com/insife/posts/grip-news-ema-releases-reflection-paper-on-ai-and-machine-learning-in-medicinal-/1053748976536856/?utm_source=chatgpt.com)  
[Open source shanghai.gov.cn](https://www.shanghai.gov.cn/nw4411/20250117/c656f4eafa214956a0b30f4ff6e86aa4.html?utm_source=chatgpt.com)  
[Open source xqiu625.github.io](https://xqiu625.github.io/ai4bio-concepts/single-cell-analysis/perturbation-prediction_modeling.html?utm_source=chatgpt.com)  
[Open source jamesclear.com](https://jamesclear.com/great-speeches/the-danger-of-a-single-story-by-chimamanda-ngozi-adichie?utm_source=chatgpt.com)  
[Open source casrai.org](https://casrai.org/guides/fda-ai-guidance?utm_source=chatgpt.com)  
[Open source scirp.org](https://www.scirp.org/reference/referencespapers?referenceid=3997588&utm_source=chatgpt.com)  
[Open source unodc.org](https://www.unodc.org/pdf/convention_1961_en.pdf?utm_source=chatgpt.com)  
[Open source scilifelab.se](https://www.scilifelab.se/wp-content/uploads/2021/06/Luzon-et-al-CPT-2017.pdf?utm_source=chatgpt.com)  
[Open source acm.org](https://uist.acm.org/2026/?utm_source=chatgpt.com)  
[Open source ny.gov](https://www.justicecenter.ny.gov/ep-10-understanding-trauma-and-trauma-informed-approach?utm_source=chatgpt.com)  
[Open source c-path.org](https://c-path.org/training/model-informed-drug-development-training-course/?utm_source=chatgpt.com)  
[Open source zibo.gov.cn](https://www.zibo.gov.cn/art/2025/5/13/art_18394_2914823.html?utm_source=chatgpt.com)  
[Open source theguardian.com](https://www.theguardian.com/lifeandstyle/2026/may/02/rare-twins-different-dads-the-gift-bbc-radio-4?utm_source=chatgpt.com)  
[Open source nsf.org](https://www.nsf.org/life-science-regulatory-news/ema-reflection-paper-on-ai-in-the-medicinal-product-lifecycle?utm_source=chatgpt.com)  
[Open source nea.gov.sg](https://www.nea.gov.sg/our-services/public-cleanliness/toilets-management/coffeeshop-toilet-grants/ctcg?utm_source=chatgpt.com)  
[Open source unep.org](https://www.unep.org/resources/emissions-gap-report-2025?utm_source=chatgpt.com)  
[Open source fushun.gov.cn](https://fskjj.fushun.gov.cn/006/006001/006001002/20240612/edf064cd-09c2-454c-a279-d05dba676073.html?utm_source=chatgpt.com)  
[Open source ndrc.gov.cn](https://www.ndrc.gov.cn/xxgk/jd/jd/202508/t20250826_1400077.html?utm_source=chatgpt.com)  
[Open source sternekessler.com](https://www.sternekessler.com/news-insights/client-alerts/fda-issues-draft-guidance-documents-on-artificial-intelligence-for-medical-devices-drugs-and-biological-products/?utm_source=chatgpt.com)  
[Open source gabionline.net](https://gabionline.net/switchlanguage/to/gabi_online_es/guidelines/european-position-paper-on-ai-in-medicinal-product-lifecycle?utm_source=chatgpt.com)  
[Open source deepl.com](https://www.deepl.com/en/translator?utm_source=chatgpt.com)  
[Open source ntu.edu.sg](https://www.ntu.edu.sg/medicine/CMM?utm_source=chatgpt.com)  
[Open source columbia.edu](https://www.tc.columbia.edu/digitalfuturesinstitute/multimodal-toolkit/video-what-is-multimodal/?utm_source=chatgpt.com)  

Generated report on 现阶段大模型能否模拟药物影响并进行系统性药物评估：能力边界、验证证据与未来五至十年路线图

## 原始页面记录

完整原始摘录保存在[同名 HTML 档案](html/gpt-28.html)末尾的折叠附录中。Markdown 为便于检索的正文版，未重复嵌入原始结构。
