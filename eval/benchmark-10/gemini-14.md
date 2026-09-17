[← 二十份研究目录](README.md)

# Gemini · ID 14 · 量子计算与数学交叉研究评估

[原研究窗口](https://gemini.google.com/app/826564c20b27059a)

原文整理，不改写研究结论。旧页面记录采集于 2026-09-14；GPT Activity 于 2026-09-17 补采。保留页面公开展示的过程说明，不代表平台未公开的内部推理。 报告由 2026-09-17 页面结构补采；空上标保留其页面 DOM 提供的来源索引，标为“[页内索引 N]”，未据此猜配来源列表。公式保留页面 data-math 中的原始 TeX；其余来源及 Thoughts 依旧归档照录。

## 评测原题

收集整理全球数学与量子计算交叉领域的主要研究团队及其成果，横向比较其研究方向、论文产出、国际合作、资金支持、工业界合作等维度，评估哪些团队最有可能在未来5-10年内推动量子计算技术的重大突破，并预测可能产生的关键性数学理论或应用技术

## 对话与研究方案（原文顺序）

## Conversation with Gemini

###### You said 收集整理全球数学与量子计算交叉领域的主要研究团队及其成果，横向比较其研究方向、论文产出、国际合作、资金支持、工业界合作等维度，评估哪些团队最有可能在未来5-10年内推动量子计算技术的重大突破，并预测可…

收集整理全球数学与量子计算交叉领域的主要研究团队及其成果，横向比较其研究方向、论文产出、国际合作、资金支持、工业界合作等维度，评估哪些团队最有可能在未来5-10年内推动量子计算技术的重大突破，并预测可能产生的关键性数学理论或应用技术

###### Gemini said

这是我拟定的方案。如果你需要进行任何改动，请在我开始研究前告诉我。

#### Quantum Mathematics Research Evaluation

The plan has 3 steps, 1st step

研究网站

(1) 检索全球在数学与量子计算交叉领域（如量子纠错码、拓扑量子计算、量子复杂性理论及量子算法等）处于领先地位的高校、国家实验室及跨学科研究机构。 (2) 搜集各核心团队的学术带头人、代表性学者以及近年发表的高影响力论文与标志性理论突破。 (3) 针对各重点团队，系统调研以下维度的具体数据与现状： (a) 核心研究方向与细分理论路线 (b) 论文产出数量、顶刊发表及学术引用表现 (c) 跨国学术网络与国际联合攻坚项目 (d) 政府基金、国家重大科研计划等资金支持力度 (e) 与量子科技企业的联合实验室、技术转化及产业合作模式 (4) 构建多维横向对比体系，综合分析各团队在理论创新深度、资源禀赋与工程实现结合度等方面的竞争格局。 (5) 基于现有技术成熟度、团队梯队与资源支撑，评估并遴选出未来5-10年内最有望取得颠覆性突破的核心团队。 (6) 结合数学与量子计算前沿瓶颈，推演未来可能诞生的关键数学理论（如新型容错拓扑结构、高效纠错架构或高维量子算法）及其衍生应用技术。

2nd step

分析结果

3rd-step

生成报告

estimated time

只需要几分钟就可以准备好

###### You said 开始研究

开始研究

###### Gemini said

I've completed your research. Feel free to ask me follow-up questions or request changes.

Gemini is AI and can make mistakes.

travel\_explore

### Quantum Mathematics Research Evaluation

## 最终研究报告

# 全球数学与量子计算交叉前沿的研发布局、多维竞争格局与颠覆性突破预测

量子信息科学正处于从嘈杂中等规模量子（NISQ）阶段向可扩展容错量子计算（FTQC）跨越的关键历史节点。在这一范式跃迁中，数学已超越传统物理建模工具的从属角色，深度演进为重构纠错拓扑结构、破解算法计算复杂度下界以及定义通用算力物理边界的核心动力。无论是利用高维膨胀图同调代数构建渐近优异量子纠错码，利用李代数与算子逼近论创立通用量子算法框架，抑或是通过非阿贝尔张量范畴探索内禀拓扑容错，数学与量子计算的交叉前沿已成为全球科技大国、顶级学术机构与跨国产业巨头战略竞争的主阵地。

## 理论范式变迁与数理基座演进

现代量子计算的理论突破越来越依赖于深刻的纯粹数学理论。过去数年间，拓扑学、微分几何、代数几何、数论与复杂性理论的交融，推动了量子信息底层逻辑的根本性重塑。

### 量子低密度奇偶校验码与同调代数

传统的二维表面码（Surface Code）长期受制于二维欧氏空间的局部几何约束，其编码率随物理比特规模 `N` 增长而急剧衰减至零（即 `K/N \to 0`），导致构建数千个逻辑量子比特往往需要耗费数百万个物理比特的极端硬件冗余[页内索引 1]。破解这一瓶颈的关键在于同调代数与图拓扑的引入。在 Calderbank-Shor-Steane（CSS）量子纠错体系下，量子稳定子码被形式化表征为链复形（Chain Complex）：

```
C_2 \xrightarrow{\partial_2} C_1 \xrightarrow{\partial_1} C_0
```

其中物理量子比特映射为 1-胞腔（1-cells），`X` 型与 `Z` 型校验算子分别对应于边界映射 `\partial_2` 与上边界映射 `\delta_0 = \partial_1^\dagger`。对偶正交条件 `\partial_1 \partial_2 = 0` 自然满足稳定子对易约束，而码空间则由同调群 `H_1 = \ker(\partial_1) / \mathrm{im}(\partial_2)` 精确给出[页内索引 3]。通过引入凯莱复形（Cayley Complex）、平衡积（Balanced Product）及提升积（Lifted Product），数学家构建出具备常数编码率与线性相对最小距离的“渐近优异（Asymptotically Good）”量子低密度奇偶校验（qLDPC）码，彻底打破了长达二十年的平方根距离理论界限[页内索引 3]。

### 量子哈密顿量复杂度与局部可检验理论

量子计算复杂性理论的终极问题之一在于探索多体微观物理相互作用的计算极限。经典计算机科学中的 PCP（概率可检验明证明）定理确立了近似约束满足问题的 NP 困难度，而量子 PCP（qPCP）猜想则断言：对局部哈密顿量基态能量密度的常数级微扰近似依然保持在 QMA-完全（Quantum Merlin-Arthur Complete）的硬度阶数[页内索引 7]。作为迈向量子 PCP 猜想的决定性阶梯，无低能平凡态（NLTS）定理的攻克表明，存在特定局域非挫折哈密顿量，其所有低能激发态都无法通过浅层（常数深度）量子线路从平凡直积态制备[页内索引 7]。这一体系将高维复形上的上同调膨胀（Coboundary Expansion）概念从经典图论拓宽至张量纠缠分析，为量子局部可检验码（qLTC）提供了严格的泛函与代数判据[页内索引 4]。

### 算子逼近论与量子奇异值变换

在量子算法领域，量子奇异值变换（QSVT）与量子信号处理（QSP）确立了通用矩阵线性代数运算的统一范式[页内索引 14]。QSVT 依赖于抽象代数与调和分析中的约当引理（Jordan's Lemma），将高维希尔伯特空间中任意线性算子的交替酉反射解耦为一系列互不相交的二维不变子空间[页内索引 14]。在这些子空间内，交替相位旋转能够精确模拟李群 `\mathrm{SU}(2)` 中的单量子比特几何进动，从而利用切比雪夫多项式逼近实现对非正规算子奇异值的多项式函数变换[页内索引 14]。这一机制不仅统一并优化了哈密顿量模拟、量子相位估计与 HHL 线性方程组求解，更推动算法研究由经验性线路启发迈向以多变量多项式代数与非线性傅里叶分析为依托的严谨数学优化时代[页内索引 14]。

### 范畴学、非阿贝尔任意子与谱隙可判定性

拓扑量子计算致力于利用物理体系的非局域拓扑自由度提供内禀硬件容错，其数学基座根植于幺正模块张量范畴（UMTC）[页内索引 19]。非阿贝尔任意子系统的辫群表示（`R`-矩阵）与融合代数（`F`-符号）定义了受拓扑不变量保护的通用量子门算符[页内索引 20]。与此同时，针对宏观连续统中多体自旋晶格的谱隙（Spectral Gap）研究证实，判定一个宏观哈密顿量在热力学极限下是否存在激发能隙在数学上是严格图灵不可判定的（Undecidable），将停机问题映射至连续相变分析中，直接催生了利用矩阵积态（MPS）、投影纠缠对态（PEPS）与半正定规划（SDP）松弛层级严格逼近宏观纠缠极限的研究新维度[页内索引 22]。

## 全球主要研究阵营及其标志性成果分析

全球数学与量子计算交叉研究力量呈现出鲜明的区域特色与学术渊源，涵盖由理论物理衍生的高维拓扑阵营、理论计算机驱动的复杂性前沿，以及专注于算法逼近理论的应用数学集团。

### 北美领军机构与跨界联合体

北美阵营以跨学科深度嵌入与理论到工程的极短转化周期见长。IBM Quantum 理论实验室由 Sergey Bravyi、Andrew Cross、Jay Gambetta、Patrick Rall 及 Theodore Yoder 等学者组成[页内索引 26]。Bravyi 作为超图积纠错码的先驱，带领团队在 2024 年于《自然》（*Nature*）发表了双变量双环码（Bivariate Bicycle Codes, BB 码）架构[页内索引 26]。该理论基于交换群代数 `\mathbb{F}_2[x, y] / \langle x^r - 1, y^m - 1 \rangle` 的多项式环结构，在标准电路级噪声模型下实现了 0.8% 的高容错阈值，追平了二维表面码并降低物理比特冗余近一个数量级，直接奠定了工业界设计小规模逻辑量子存储器的数学骨干[页内索引 27]。依托 IBM 全球规模最大的超导硬件研发管线，该团队持续推动代数编码向芯片布线几何的端到端编译[页内索引 26]。

哈佛大学、麻省理工学院（MIT）与光镊原子计算先驱 QuEra 构筑了学术策源与产业孵化的高效闭环。哈佛物理学与应用数学团队由 Mikhail Lukin 与 Dolev Bluvstein 领衔，计算机科学理论学者 Anurag Anshu 及凝聚态物理学家 Ashvin Vishwanath 协同攻关[页内索引 7]。2023 年，Anshu 联合 Nikolas Breuckmann 与 Chinmay Nirkhe，利用优异 qLDPC 码的代数复形性质证明了理论计算机科学界悬置十余年的 NLTS 猜想，摘得 ACM STOC 最佳论文奖[页内索引 7]。在硬件层面，Lukin 与 Bluvstein 团队将三维超立方体同调色码理论应用于动态重构的中性原子阵列，借助声光偏转器实现了跨越几何邻近限制的长程原子穿梭，在国际上首次演示了 48 个纠错保护的逻辑量子比特并行操作与算法级采样，展现了高维代数结构在全互联硬件上的物理兼容性[页内索引 31]。

加州理工学院量子信息与物质研究所（IQIM）由理论物理学家 John Preskill 掌舵，聚合了 Fernando Brandão、Thomas Vidick 等学者[页内索引 1]。IQIM 是全球量子信息数学物理的学术摇篮。Preskill 团队在 2024 至 2025 年间提出了“分层量子纠错码（Hierarchical Codes）”，通过将恒定速率优异 qLDPC 码与底层二维表面码在胞腔复形上进行代数级联，证明在受限的严格二维欧氏物理平面上依然能够实现 `K = \Omega(N/\log^2 N)` 的高编码容量与恒定容错阈值，系统回答了受限空间内高维拓扑码的物理映射机制[页内索引 1]。此前，Vidick 与合作者基于量子纠缠多证明者交互式证明系统彻底证明了 `\mathrm{MIP}^* = \mathrm{RE}`，作为推论一举否定了算子代数领域的百年难题“康尼斯嵌入猜想（Connes Embedding Conjecture）”与量子物理中的“齐尔森问题”，在理论计算机科学、无限维 `C^*`-代数与微观非定域纠缠之间架设了统一的数学桥梁[页内索引 34]。

加州大学伯克利分校与劳伦斯伯克利国家实验室（LBNL）形成了以应用数学家 Lin Lin（林霖）、理论计算机科学家 Venkatesan Guruswami 及量子算法先锋 Umesh Vazirani 为代表的研究轴心[页内索引 12]。林霖及其团队专注于矩阵块编码（Block-encoding）与多变量量子信号处理（Multivariate QSP）的理论构建，系统解析了非对易算子多项式展开在非线性偏微分方程求解及多体能量泛函演化中的代数优化极限[页内索引 14]。与此同时，Guruswami 与 Louis Golowich 提出了基于链复形迭代同调积的准线性距离量子纠错码，利用子系统约束在规避传统同调积码平方根障碍的同时维持了局域稀疏度，为代数拓扑编码提供了全新的构造性工具[页内索引 12]。

### 欧洲数理基础与前沿算法重镇

欧洲的研究力量植根于深厚的代数几何、泛函分析与图论传统，在抽象理论与判定性研究中占据主导地位。

法国国家信息与自动化研究所（Inria）巴黎中心与波尔多数学研究所（IMB）的联合攻关极具代表性。核心学者 Anthony Leverrier 与 Gilles Zémor 在俄罗斯学者突破线性距离 qLDPC 码后，于 2022 年在 IEEE FOCS 提出了更为明晰的“量子坦纳码（Quantum Tanner Codes）”[页内索引 5]。该理论通过在四维左-右凯莱复形（Left-Right Cayley Complex）的二维面上配置经典坦纳小码，利用群膨胀图的局部-全局拓扑关联，首次给出了兼具常数编码率与严格线性最小距离的显式量子纠错码构造，成为 NLTS 定理攻克的基础数学工具[页内索引 5]。随后，团队相继攻克了优异 qLDPC 码在对数时间内的并行译码器与线性复杂度经典译码算法，化解了优异同调码在后处理延时上的潜在瓶颈[页内索引 38]。团队作为核心主力承接了法国“France 2030”国家战略规划下 1.5 亿欧元的 PEPR 专项（NISQ2LSQ 项目），并与欧洲中性原子领军企业 Pasqal 展开深层次物理映射开发[页内索引 37]。

荷兰量子软件联盟（QuSoft）依托阿姆斯特丹大学、荷兰数学与计算机科学国家研究所（CWI）及代尔夫特理工大学建立，汇聚了哥德尔奖得主 Ronald de Wolf、Harry Buhrman、Christian Schaffner 等理论学者[页内索引 40]。该联盟是全球利用纯数学工具界定量子加速边界的代表性基地。De Wolf 等人开创并系统完善了多项式方法与对抗性矩阵分析法在量子查询复杂度中的应用，确立了一系列不可逾越的经典与量子算力分离下界[页内索引 41]。团队承担了荷兰国家科研组织（NWO）“引力计划”近 1900 万欧元的长周期资助，并作为核心枢纽深度嵌入投资额达 6 亿欧元的 Quantum Delta NL 体系，其下设的量子应用实验室（QAL）与欧洲工业界（如丰田欧洲研发中心）建立了从底层理论到交通流与金融优化的代数应用通道[页内索引 41]。

德国马克斯·普朗克量子光学研究所（MPQ）与慕尼黑量子科技中心（MCQST）由沃尔夫物理奖得主 J. Ignacio Cirac 与 Norbert Schuch 领军，并长期与西班牙马德里康普顿斯大学的 David Pérez-García 紧密合作[页内索引 22]。该团队将张量网络发展为严格刻画量子多体物理局域纠缠结构的现代数学语言[页内索引 22]。Cirac 团队深入研究对称性保护拓扑（SPT）相与 PEPS 映射的边界对偶理论，并提出基于半正定规划（SDP）松弛层级直接判定无挫折自旋系统谱隙的严格外推数学框架，显著超越了传统有限尺寸判据（如 Knabe 界限），为量子哈密顿量的基态拓扑认证提供了纯代数工具[页内索引 23]。

英国伦敦大学学院（UCL）与布里斯托大学理论团队由 Toby Cubitt、Nikolas Breuckmann 及 Ashley Montanaro 构成[页内索引 7]。Cubitt 团队在《自然》（*Nature*）发表的长文彻底证明了晶格相互作用哈密顿量在热力学极限下微观谱隙的存在性属于不可判定问题，将离散计算图灵停机逻辑与连续微观量子多体体系融为一体[页内索引 24]。Breuckmann 则在双曲几何流形与同调积纠错码的设计中持续产出原创成果[页内索引 11]。为了将高深数理结构转化为算力收益，团队联合成立了深度算法初创企业 Phasecraft，专注于在紧凑量子线路内重构费米子映射算子，为固态物理与强关联材料模拟提供严格数学保障。

### 中国高水平数学与物理交叉研发阵营

中国在数学与量子计算的交叉布局上呈现出基础数学理论与宏观工程验证两翼齐驱的发展态势。

北京雁栖湖应用数学研究院（BIMSA）与清华大学丘成桐数学科学中心（YMSC）在菲尔兹奖得主丘成桐与清华大学教授刘正伟的带领下，主攻算子代数、子因子理论（Subfactor Theory）、量子拓扑以及非交换调和分析[页内索引 19]。刘正伟团队提出了基于张量网络与代数拓扑的“Alterfold 理论”，并创立了图形化数学工具“Quon 语言”，将其成功应用于非交换纠缠熵度量与量子通信保真度边界的解析表征[页内索引 19]。此外，该团队近期从泡利路径积分与可观测量反向传播（OBPPP）入手，从数学上严格证明了一大类含噪变分量子算法（VQA）在经典计算环境下的多项式复杂度可模拟性，为厘清 NISQ 线路表达力极限与确立真实量子优越性边界提供了纯数学依据[页内索引 52]。

中国科学技术大学与合肥国家实验室构筑了立足大科学工程的软硬件交叉重镇。由潘建伟、陆朝阳、朱晓波、龚明及袁骁等组成的攻坚团队，在接连刷新光量子“九章”与超导“祖冲之”系列量子计算原型机性能的同时，深度推进容错量子纠错的数理验证[页内索引 53]。团队在超导物理芯片上实验构建了最小完美五量子比特纠错码 `[[5, 1, 3]]`，验证了任意单比特物理错误的无破坏探测与逻辑门隐形传态[页内索引 55]。在连续变量玻色子编码体系中，团队针对非马尔可夫噪声信道与高斯热噪声漂移，提出了非对称 GKP 码与 XZZX 表面码的级联代数优化方案，将容错阈值大幅提升，为超导腔体与原子谐振体系中的低开销逻辑保护提供了坚实的理论支撑[页内索引 58]。

## 多维横向对比与全球竞争格局

为了系统评估全球数学与量子计算交叉团队的综合科研效能与资源转化能力，下表从研究主攻方向、标志性成果、学术影响力、产学研协同以及资金保障等多重维度展开横向比对：

| 团队 / 机构名称 | 学术带头人 | 核心数学与量子交叉方向 | 代表性理论突破成果 | 代表性发表与学术影响力 | 主要资金支持来源 | 工业协同与落地转化模式 |
| --- | --- | --- | --- | --- | --- | --- |
| **IBM Quantum 理论攻关组** (美国) | Sergey Bravyi, Andrew Cross, Jay Gambetta | 群代数、二元环多项式、超图积码、有限尺寸 qLDPC | 创立双变量双环码（BB Codes），在 0.8% 电路级噪声阈值下减少 90% 物理开销[页内索引 26] | *Nature*, *PRX*, *IEEE TIT*；引领当前工业级 FTQC 硬件路线设计[页内索引 26] | 企业战略科研预算（年均数亿美元规模），集成国家协同项目 | 垂直全栈整合：自研群代数编码直接编译至 Heron/Flamingo 超导硬件平台[页内索引 26] |
| **哈佛 / MIT / QuEra 联合体系** (美国) | Mikhail Lukin, Anurag Anshu, Dolev Bluvstein | 拓扑复形、高维上同调、动力学原子图、复杂性下界 | 严格证明 NLTS 猜想[页内索引 7]；利用原子重排物理实现 48 逻辑量子比特纠错算法[页内索引 31] | *Nature*, *Science*, STOC（最佳论文）, FOCS；跨物理与计算机顶尖峰值[页内索引 31] | 美国 NSF QLCI 挑战所专项、DOE 重点实验室、顶尖风投资本（QuEra） | 产学研深度一体化：孵化 QuEra，并在 AWS Braket 与自有云端平台落地运行[页内索引 31] |
| **加州理工学院 (Caltech) / IQIM** (美国) | John Preskill, Fernando Brandão, Thomas Vidick | 算子代数、交互式证明系统、分层复形纠错码 | 证明 `\mathrm{MIP}^*=\mathrm{RE}` 破解康尼斯猜想[页内索引 34]；提出常数阈值分层 qLDPC 表面码[页内索引 1] | *Annals of Math.*, *CACM*, *Quantum*, FOCS/STOC；数学物理最高声誉[页内索引 1] | DARPA、NSF 物理前沿中心、Simons 基金会超亿美元长期资助[页内索引 32] | 与亚马逊 AWS 量子计算中心（落户 Caltech 校园）深度协同与人才双向流动 |
| **法国 Inria / 波尔多数学所 (IMB)** (法国) | Anthony Leverrier, Gilles Zémor, Jean-Pierre Tillich | 图同调、左-右凯莱复形、局部可测性、对数步译码 | 提出量子坦纳码（Quantum Tanner Codes）体系与优异码并行对数步译码算法[页内索引 37] | *IEEE TIT*, *FOCS*, *STOC*, *SODA*；奠定量子图纠错数学基础[页内索引 37] | 法国 Plan France 2030 (PEPR NISQ2LSQ，1.5 亿欧元)、欧盟 ERC/QuantERA[页内索引 37] | 支撑欧洲中性原子领军企业 Pasqal 理论设计，对接法国国防与核能科研机构[页内索引 38] |
| **荷兰 QuSoft / CWI / 阿姆斯特丹大学** (荷兰) | Ronald de Wolf, Harry Buhrman, Christian Schaffner | 多项式法、矩阵分析、量子查询复杂度、后量子代数边界 | 系统确立量子查询多项式度数界限；厘清量子交互证明系统非局域信息下界[页内索引 41] | 斩获计算机理论哥德尔奖；*J. ACM*, *STOC/FOCS*, *PRL*  [cite: 42, 52] | 荷兰 NWO “引力计划”（1880 万欧元专项）、Quantum Delta NL 国家基金[页内索引 41] | 设立量子应用实验室（QAL），与丰田欧洲汽车、Quix Quantum 合作推进算法共研[页内索引 42] |
| **加州大学伯克利分校 / LBNL** (美国) | Lin Lin, Venkatesan Guruswami, Umesh Vazirani | 多变量量子信号处理、迭代同调积码、块编码优化 | 创立偏微分方程与算子动力学的多变量 QSP 逼近论[页内索引 14]；构造高维同调积拓扑码[页内索引 12] | *SIAM Rev.*, *PRX*, *ACM STOC*, *Math. Comp.*；应用数学与理论计算双峰[页内索引 12] | 美国能源部（DOE-ASCR）先导计算专项、NSF 计算数学、Simons 研究所专项[页内索引 12] | 与劳伦斯伯克利国家实验室深度绑定，向高能物理与新型材料模拟项目注入工具 |
| **马普量子光学所 (MPQ) / MCQST** (德国) | J. Ignacio Cirac, Norbert Schuch, David Pérez-García | 张量网络表征理论、连续对称性相变、谱隙 SDP 判定 | 建立 PEPS/MPS 连续统拓扑相分类定理[页内索引 44]；提出无挫折哈密顿量谱隙 SDP 严密认证[页内索引 23] | *Rev. Mod. Phys.*, *CMP*, *Nature Phys.*, *Quantum*；数理严密性标杆[页内索引 23] | 德国联邦研究部（BMBF）、巴伐利亚高科技转型计划、欧盟 ERC 旗舰资助 | 作为欧洲量子多体模拟理论中枢，协同慕尼黑工业大学产业化创新集群与初创企业 |
| **英国 UCL / 布里斯托大学 / Phasecraft** (英国) | Toby Cubitt, Nikolas Breuckmann, Ashley Montanaro | 双曲几何、哈密顿量复杂度、晶格谱隙不可判定性 | 证明宏观多体谱隙存在性不可判定[页内索引 24]；构建紧凑双曲量子拓扑流形纠错架构[页内索引 11] | *Nature*, *Forum of Math. Pi*, *STOC*, *CMP*；擅长跨界难题解决[页内索引 24] | 英国 EPSRC、欧洲 ERC 重点项目资助、顶级风投资本机构支持 | 深度孵化 Phasecraft，直接联合 Rigetti、Oxford Ionics 探索极小线路深度材料算法 |
| **北京雁栖湖研究院 (BIMSA) / 清华 YMSC** (中国) | 丘成桐, 刘正伟, Artan Sheshmani | 子因子理论、非交换几何、量子对称性、可微线路复杂度 | 创立 Quon 图形拓扑语言[页内索引 19]；证明经典多项式算法可高效模拟宽类含噪变分量子线路[页内索引 52] | *Adv. Math.*, *PRL*, *CMP*, *Lett. Math. Phys.*；深耕基础纯数学土壤[页内索引 49] | 中国国家自然科学基金重点专项、北京市前沿应用数学长周期定向支持 | 发展纯数学开源理论工具集，与国内顶尖科技企业实验室及北京量子院技术互通[页内索引 66] |
| **中科大 / 合肥国家实验室** (中国) | 潘建伟, 陆朝阳, 龚明, 袁骁 | 连续变量玻色码、纠缠门隐形传态、凸优化纠错译码 | 实验实现五比特完美纠错码 `[[5, 1, 3]]`[页内索引 55]；确立非对称 GKP-表面码级联高容错阈值理论[页内索引 58] | *Nature*, *Science*, *PRL*, *PNAS*；硬件测试指标与工程实现领跑全球[页内索引 55] | 中国国家实验室重大科研平台专项预算、中国科学院战略性先导专项支持[页内索引 54] | 举国体制重器：科研成果无缝导入“九章”光量子与“祖冲之”超导量子计算工程[页内索引 54] |

### 地缘竞性格局与创新生态机理

深入审视全球数学与量子计算交叉创新的内在动能，不同区域因学术传统、资金机制与产业环境的差异，形成了各具特色的创新范式。

北美体系展现出高密度的产业资本驱动与软硬件双向穿梭机制。无论是 IBM 将纯粹的二元多项式环代数直接转化为芯片上的跨层微波布线，还是哈佛与 MIT 团队将高维胞腔复形通过中性原子光镊阵列进行动力学几何实现，均表明理论构想能够在数月至一年内获得硬件级的工程反馈[页内索引 26]。这种“从高深代数同调到微纳加工执行”的敏捷闭环，构成了北美阵营在容错技术落地上的核心壁垒。

欧洲阵营则展现出对基础概念体系与深层数学定理的极致追求。以法国 Inria、波尔多数学所、荷兰 QuSoft 及德国马普所为代表的研究中心，其核心资助来自于国家战略与泛欧长期科研专项（如法国 PEPR 计划、荷兰 Gravitation 专项及 ERC 基金）[页内索引 37]。欧洲学者往往不急于对标短期硬件指标，而是致力于从本质上重构学科大厦的底层框架，例如攻克渐近优异同调码的全局代数复形、解决谱隙不可判定性、确立算子逼近论极值等[页内索引 5]。这种深邃的基础研究储备一旦突破，便会成为全球产业界竞相采用的技术底层范式。

中国阵营正在形成“以顶格工程物理装置为牵引，纯数学基础理论迅速补强”的纵深架构。依托合肥国家实验室与中科大，中国拥有国际顶尖的超导与光量子工程平台，能够率先在物理体系中完成复杂纠错码与隐形传态协议的实验闭环[页内索引 54]。与此同时，以清华丘成桐数学科学中心和北京雁栖湖应用数学研究院为代表的新兴纯数学力量，正在算子代数、子因子理论及张量范畴等纯数学深水区迅速建立国际话语权，为本土乃至全球量子纠错与线路复杂度提供全新判定准则，逐步填补以往在理论计算复杂性与纯代数抽象架构上的积累差距[页内索引 19]。

## 未来5至10年颠覆性突破的核心团队综合评估

结合过去数年各团队的数理突破爆发力、与前沿量子硬件工程的耦合度、关键资源持续供给能力以及中青年学术梯队储备，未来 5 至 10 年最有可能推动颠覆性跨越的团队可划分为三个核心梯队。

### 工业级容错量子计算架构的绝对领跑者

IBM Quantum 理论实验室（Sergey Bravyi 团队）展现出最高的突破确定性。Bravyi 团队提出的双变量双环码（BB Codes）已经彻底重构了硬件团队对 FTQC 路线图的构想[页内索引 27]。相较于表面码数以万计的物理开销，BB 码使工程界看到了利用数百个物理比特即实现数十个逻辑比特的曙光[页内索引 27]。在未来 5 至 10 年内，伴随超导多芯片倒装焊技术与低温同轴布线的高密度集成，该团队最有望率先在全栈硬件上突破纠错损益平衡点（Break-even Point），攻克高维循环群代数在准局部引线交错下的串扰抑制难题，确立全球首个商用级 qLDPC 纠错处理器。

哈佛大学 / MIT / QuEra 联合体系（Mikhail Lukin / Anurag Anshu / Dolev Bluvstein 集团）构成了中性原子体系下的领军集群。中性原子光镊阵列天然具备的长程穿梭能力，彻底消除了平面局部物理相互作用的拓扑桎梏，与高维同调复形码形成了完美的数理适配[页内索引 31]。随着双量子比特里德堡逻辑门保真度跨越 99.5% 的关键物理阈值，加上 Anshu 在量子多体复杂性与纠错态代数拓扑领域的深刻洞见，该团队极有可能在未来 5 年内率先实现百个逻辑量子比特规模下的容错量子算法连续执行，并在特定强关联量子化学与拓扑物态模拟中取得兼具容错性与实用性的决定性计算优势[页内索引 7]。

### 拓扑新范式与高维纠错数学的策源地

Quantinuum 与哈佛 / 芝加哥大学拓扑物理网络（Henrik Dreyer / Ashvin Vishwanath / Ruben Verresen）在拓扑量子计算赛道上展现出颠覆传统的爆发力。2024 至 2026 年，该团队依托 Quantinuum 的 H2 离子阱系统，接连完成了非阿贝尔拓扑序（`D_4` 群及 `S_3` 量子双重模型）的波函数受控合成，更在国际上首次演示了通过非阿贝尔任意子编织（Braiding）与融合（Fusion）测量的通用拓扑量子门集合[页内索引 21]。该方案从纯数学原理上绕过了传统稳定子码架构中极其耗费物理资源的“魔态蒸馏”过程[页内索引 21]。未来 5 至 10 年，该联合网络有望推动拓扑量子计算从依赖脆弱固态材料纳米线的“材料路线”彻底转向通过数字线路合成拓扑序的“内禀纠错新赛道”[页内索引 69]。

法国 Inria 巴黎 / 波尔多数学所联合中心（Anthony Leverrier / Gilles Zémor 团队）作为现代量子图纠错码的奠基者，未来数年将在更高维几何复形与张量层（Sheaves）的数学机制上取得持续产出[页内索引 3]。作为最透彻掌握图同调膨胀理论的数理学者，他们最有可能在兼具高编码率、大距离的优异 qLDPC 码上，突破 Eastin-Knill 定理的传统束缚，构造出天然兼容高阶容错非 Clifford 逻辑门（如横向 `CCZ` 门或 `T` 门）的代数结构，从纯数学层面解决表面码计算逻辑门编译成本畸高的根本难题[页内索引 3]。

### 算法数学革新与复杂性界限拓展者

加州大学伯克利分校 / 劳伦斯伯克利实验室算法体系（Lin Lin / Venkatesan Guruswami）将继续引领量子算法理论的高阶演进。林霖团队建立的多变量矩阵块编码与量子信号处理范式，正逐步打破量子动力学演化仅能针对特定薛定谔方程的局限[页内索引 14]。在未来 5 至 10 年内，该团队有望在流体力学纳维-斯托克斯方程、偏微分动力学特征值估计等高维科学计算难题中，构建出具有严格误差收敛证明的多变量 QSVT 量子算法体系，为量子超级计算（Q-HPC）奠定通用数值数学基础[页内索引 16]。

## 关键性数学理论演进与前沿应用技术预测

随着代数拓扑、高维膨胀图、非交换几何以及现代算子逼近论的加速渗透，未来 5 至 10 年内全球数学与量子计算交叉前沿预期将催生以下颠覆性理论与应用成果。

### 基于高维上同调膨胀的完全量子PCP定理证明

在 NLTS 定理获得完全证明的坚实基础上，理论计算机科学界的终极焦点已全面转向量子 PCP 猜想的证明[页内索引 7]。经典 PCP 定理的核心在于通过谱膨胀图与局部可测码放大约束冲突率，而量子体系的非定域纠缠与非对易算子代数使得冲突放大过程面临严重的纠缠退化与正交性破坏[页内索引 9]。未来 5 至 8 年，数学家将借助拉马努金四维复形、格拉斯曼复形上的上同调收缩性（Cosystolic Expansion）以及张量对偶空间的强鲁棒性理论，构建出具有常数健全性（Soundness）与线性距离的高维量子局部可检验码（qLTCs）[页内索引 4]。这一纯数学突破将为量子 PCP 猜想画上圆满句号，彻底终结关于多体量子基态能量密度近似复杂度的长期争论，并从数学形式上奠定宏观拓扑纠缠在微扰热力学环境下的不可经典模拟性[页内索引 10]。

### 基于拓扑层上同调杯积的无蒸馏通用横向门体系

依据 Eastin-Knill 定理，任何物理局域量子纠错码都不可能拥有通用且完全横向的逻辑门集合，这导致容错架构不得不通过开销巨大的“魔态蒸馏与隐形传态注入”来实现非 Clifford 门，该过程往往占据容错量子计算机整机 80% 以上的时空物理资源[页内索引 21]。未来 5 至 10 年，代数几何中的拓扑层（Sheaf Theory）与胞腔复形上的杯积（Cup Product）运算将实现工程转化[页内索引 3]。通过在流形复形的三维胞腔截面上定义多层张量结构，物理上可将作用在上同调类之间的双线性映射：

```
\smile : H^i(X, \mathcal{F}_1) \times H^j(X, \mathcal{F}_2) \to H^{i+j}(X, \mathcal{F}_1 \otimes \mathcal{F}_2)
```

直接转化为多比特逻辑态上的高阶相互作用[页内索引 3]。结合 Artin 原根猜想在有限域上的代数提升，理论物理学家将实现在大类优异 qLDPC 码中直接以常数深度线路并行施加 `\tilde{\Theta}(N)` 个完全横向的 `CCZ` 门与 `T` 门[页内索引 4]。这一进展将从理论底层彻底淘汰资源耗费严重的魔态蒸馏工厂，使容错量子处理器的物理硬件规模门槛实现两个数量级以上的断崖式下降。

### 多元非线性调和分析与多变量QSVT算法架构

当前成熟的量子信号处理（QSP）与量子奇异值变换（QSVT）本质上属于单变量多项式代数范畴，即仅能对单一矩阵算子的奇异值进行孤立的多项式函数调制[页内索引 14]。然而，真实世界的绝大多数前沿科学问题——包括强关联电子多体哈密顿量、非对易微分方程以及多体分子非绝热跃迁动力学，均由多个互不对易的算子集合 `\{A_1, A_2, \dots, A_m\}` 共同驱动[页内索引 14]。未来 5 年内，基于李代数紧致表示论、多复变函数论与非阿贝尔群上多变量非线性傅里叶变换的重大突破，将确立“多变量量子信号处理与奇异值变换（Multivariate QSP/QSVT）”的形式化解析体系[页内索引 16]。该理论将使得非线性偏微分方程与多维积分变换能够直接通过块编码酉算子的高维交替反射实现多项式近似，将量子动力学模拟能力从简单的薛定谔演化大幅扩展至非线性偏微分方程领域，确立下一代量子科学计算的核心数值库标准[页内索引 16]。

### 测量诱导非阿贝尔任意子态与拓扑量子存储技术

受限于材料科学微观界面的杂质缺陷、晶格无序及能隙微弱，传统依赖固态半导体-超导纳米线的马约拉纳零能模（MZMs）实用化进程面临严峻挑战[页内索引 69]。相对而言，利用离散非阿贝尔群（如 `D_4` 或 `S_3`）的量子双重模型已成功在高质量物理量子处理器上完成高保真度波函数合成[页内索引 20]。未来 8 至 10 年，结合“仅基于测量的拓扑量子计算（Measurement-Only Topological Quantum Computation）”与自适应带状算子（Ribbon Operators）投影技术，研究者将无须在物理空间中实际穿梭准粒子，而是通过时间轴上严格编排的拓扑荷隐形传态式投影测量，实现等效的非阿贝尔任意子多重编织与态合成[页内索引 20]。由此催生的新型拓扑量子存储器件将兼具非阿贝尔拓扑基底的内禀抗噪性与数字量子处理器的全可控性，推动容错量子计算在物理体系上开辟除传统纯超导与表面码之外的全新工业化路径[页内索引 21]。

## 结论

全球数学与量子计算交叉领域的演化轨迹表明，量子信息科学的技术重心正在发生决定性的范式重构。研发阵营的关注点已经从早期的物理比特堆叠与中等规模含噪演示，全面转向以同调代数为骨架、以代数几何编码为基座、以多变量算子分析为驱动的深度数理攻坚。在未来 5 至 10 年的窗口期内，北美依托产学研一体化飞轮效应在全栈容错工程化推进上保持领跑，欧洲凭借深邃的数理传统在底层定理确立与理论范式策源中发挥着主导功能，而中国则在完备的物理工程平台保障与纯数学前沿理论的快速蓄力中加速构建战略支点。伴随高维上同调膨胀推动量子 PCP 猜想的破题、层理论杯积赋予非 Clifford 门的横向突破，以及多变量 QSVT 体系的成熟，现代数学将不仅为量子计算构筑抵御宏观环境退相干的容错屏障，更将从计算复杂度与非交换拓扑的物理极限维度，重构人类认识和利用微观量子世界的底层科学坐标[页内索引 3]。

## 报告引用与阅读来源

### Sources used in the report

[preskill.caltech.edu Simulating quantum LDPC codes with local gates - John Preskill](https://www.preskill.caltech.edu/pubs/preskill-2025-hierarchical.pdf)  
[researchgate.net Quantum LDPC Codes With Positive Rate and Minimum Distance](https://www.researchgate.net/publication/260711243_Quantum_LDPC_Codes_With_Positive_Rate_and_Minimum_Distance_Proportional_to_the_Square_Root_of_the_Blocklength)  
[arxiv.org Transversal non-Clifford gates for quantum LDPC codes on sheaves](https://arxiv.org/pdf/2410.14631)  
[arxiv.org Theory of (Co)homological Invariants on Quantum LDPC Codes](https://arxiv.org/pdf/2603.25831)  
[eccc.weizmann.ac.il Quantum Tanner codes](https://eccc.weizmann.ac.il/report/2022/029/revision/1/download)  
[arxiv.org Small quantum Tanner codes from left–right Cayley complexes - arXiv](https://arxiv.org/html/2512.20532v1)  
[arxiv.org Fermionic Hamiltonians without trivial low-energy states - arXiv](https://arxiv.org/html/2307.13730v1)  
[escholarship.org Lower bounds on the complexity of quantum proofs - UC Berkeley](https://escholarship.org/content/qt5tb9r54c/qt5tb9r54c.pdf)  
[sanchayandutta.cs.ucdavis.edu SoS Lower Bounds, SS-HDX and NLTS - Sanchayan Dutta](https://sanchayandutta.cs.ucdavis.edu/files/Slides_SoS_Lower_Bounds__SS_HDX_and_NLTS.pdf)  
[en.wikipedia.org NLTS conjecture - Wikipedia](https://en.wikipedia.org/wiki/NLTS_conjecture)  
[blog.simons.berkeley.edu The Blind Men and the Quantum Elephants | Calvin Café](https://blog.simons.berkeley.edu/2022/08/the-blind-men-and-the-quantum-elephants/)  
[drops.dagstuhl.de Quantum LDPC Codes of Almost Linear Distance via ... - DROPS](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CCC.2025.25)  
[arxiv.org NLTS Hamiltonians and Strongly-Explicit SoS Lower Bounds ... - arXiv](https://arxiv.org/pdf/2311.09503)  
[arxiv.org Quantum signal processing with continuous variables - arXiv](https://arxiv.org/html/2304.14383v1)  
[quantum-journal.org An adversary bound for quantum signal processing](https://quantum-journal.org/papers/q-2026-03-13-2025/)  
[pubs.aip.org A perspective from block-encodings and polynomial transformations](https://pubs.aip.org/aip/aco/article/2/1/010901/3378659/Scalable-quantum-computational-science-A)  
[publications.mfo.de Quantum Signal Processing and Nonlinear Fourier Analysis](https://publications.mfo.de/bitstream/handle/mfo/4262/OWR_2024_46.pdf?sequence=1&isAllowed=y)  
[semanticscholar.org On variants of multivariate quantum signal processing and their](https://www.semanticscholar.org/paper/On-variants-of-multivariate-quantum-signal-and-N%27emeth-K%C3%B6v%C3%A9r/82c630b2e39b92d6372cc2695ced2ec3b2c3273f)  
[bimsa.cn BIMSA &gt; Quantum Symmetry](https://www.bimsa.cn/groups/quantum-symmetry.html)  
[assets-eu.researchsquare.com Reconstructing non-Abelian braiding and fusion without anyon](https://assets-eu.researchsquare.com/files/rs-10607154/v1_covered_78c709d3-c3c6-4e64-a022-9311ce9828c6.pdf)  
[quantumcomputingreport.com Quantinuum and Academic Partners Demonstrate First Universal](https://quantumcomputingreport.com/quantinuum-and-academic-partners-demonstrate-first-universal-topological-gate-set-via-non-abelian-anyons/)  
[mcqst.de Ignacio Cirac - Munich Center for Quantum Science and Technology](https://www.mcqst.de/about/members/ignacio-cirac.html)  
[quantum-journal.org A Hierarchy of Spectral Gap Certificates for Frustration-Free Spin](https://quantum-journal.org/papers/q-2026-04-13-2065/)  
[arxiv.org Spectral gap of Lee-Yang Hamiltonians - arXiv](https://arxiv.org/pdf/2607.10765)  
[researchgate.net (PDF) The Undecidability of the Spectral Gap: An Expository](https://www.researchgate.net/publication/411800951_The_Undecidability_of_the_Spectral_Gap_An_Expository_Account_of_a_Fundamental_Limitation_in_Quantum_Many-Body_Physics)  
[postquantum.com Quantum Low-Density Parity-Check (qLDPC) Codes](https://postquantum.com/quantum-computing/quantum-low-density-parity-check-qldpc-codes/)  
[arxiv.org High-threshold and low-overhead fault-tolerant quantum memory](https://arxiv.org/abs/2308.07915)  
[researchgate.net High-threshold and low-overhead fault-tolerant quantum memory](https://www.researchgate.net/publication/379336526_High-threshold_and_low-overhead_fault-tolerant_quantum_memory)  
[ibm.com IBM lays out clear path to fault-tolerant quantum computing](https://www.ibm.com/quantum/blog/large-scale-ftqc)  
[anthonywest.co.uk Fault-tolerant quantum computing: IBM (2025) | Anthony West](https://anthonywest.co.uk/explainers/folders/quantum-computing/2026-04-29_ibm_fault-tolerant-quantum-roadmap_explainer)  
[researchgate.net Shuttling arrives for silicon quantum computers - ResearchGate](https://www.researchgate.net/publication/392540454_Shuttling_arrives_for_silicon_quantum_computers)  
[simonsfoundation.org Quantum Effects Go Macro: Collaboration Unravels the Ultra](https://www.simonsfoundation.org/2026/08/03/quantum-effects-go-macro-collaboration-unravels-the-ultra-quantum-realm/)  
[researchgate.net Performance of the spin qubit shuttling architecture for a surface](https://www.researchgate.net/publication/389821189_Performance_of_the_spin_qubit_shuttling_architecture_for_a_surface_code_implementation)  
[gilkalai.wordpress.com Amazing: Zhengfeng Ji, Anand Natarajan, Thomas Vidick, John](https://gilkalai.wordpress.com/2020/01/17/amazing-zhengfeng-ji-anand-natarajan-thomas-vidick-john-wright-and-henry-yuen-proved-that-mip-re-and-thus-disproved-connes-1976-embedding-conjecture-and-provided-a-negative-answer-to-tsirelso/)  
[arxiv.org A Noncommutative Nullstellensatz for Perfect Two-Answer ... - arXiv](https://www.arxiv.org/pdf/2501.11826v1)  
[jst.go.jp 2.7.5 計算理論 - 科学技術振興機構（JST）](https://www.jst.go.jp/crds/pdf/2024/FR/CRDS-FY2024-FR-03/CRDS-FY2024-FR-03_20705.pdf)  
[ieee-focs.org Quantum Tanner codes](https://ieee-focs.org/FOCS-2022-Papers/pdfs/FOCS2022-4Bu7jGV9xIcveUWYj3oWoi/551900a872/551900a872.pdf)  
[inria.fr Theory of error-correcting codes: fundamental results to go towards](https://www.inria.fr/en/error-correcting-codes-fundamental-results-quantum-computer)  
[researchgate.net (PDF) A parallel decoder for good quantum LDPC codes](https://www.researchgate.net/publication/362643510_A_parallel_decoder_for_good_quantum_LDPC_codes)  
[uva.nl Quantum Technology - University of Amsterdam](https://www.uva.nl/en/news-events/press-office/uva-experts/quantum-technology/quantum-technology.html)  
[cwi.nl Quantum Software Consortium receives 18.8 million euro in the](https://www.cwi.nl/en/news/quantum-software-consortium-receives-18-8-million-euro-in-the-gravitation-programme/)  
[qusoft.org QuSoft Annual Report 2023](https://qusoft.org/?jet_download=7667f1b95d33d9323e1debde644cb67bc8d6f290)  
[alphaxiv.org David Pérez-García | alphaXiv](https://www.alphaxiv.org/@david-perez-garcia)  
[arxiv.org arXiv:2011.12127v2 [quant-ph] 9 Aug 2021](https://arxiv.org/pdf/2011.12127)  
[edoc.ub.uni-muenchen.de Tensor Network Methods in Many-body physics](https://edoc.ub.uni-muenchen.de/24118/1/Molnar_Andras.pdf)  
[qis.mit.edu seminars - quantum information science @ mit](http://qis.mit.edu/seminars.php?q=past)  
[repositories.lib.utexas.edu Dissertation by Justin Yirka - The University of Texas at Austin](https://repositories.lib.utexas.edu/bitstreams/dd3e1ca6-e569-4f0e-9c04-3b4181b79b5a/download)  
[researchgate.net Uncomputability of phase diagrams - ResearchGate](https://www.researchgate.net/publication/348601108_Uncomputability_of_phase_diagrams)  
[bimsa.net Zhengwei Liu - BIMSA](https://bimsa.net/people/zwliu/)  
[bimsa.net Shing-Tung Yau - BIMSA](https://bimsa.net/people/yau/)  
[qzc.tsinghua.edu.cn 刘正伟团队提出经典模拟变分量子算法的多项式新途径](https://qzc.tsinghua.edu.cn/info/1040/6441.htm)  
[bimsa.cn New and efficient approach to classical simulations of variational](https://www.bimsa.cn/news/info/1235.html)  
[events.polyu.edu.hk Plenary and Keynote Speakers - PolyU](https://events.polyu.edu.hk/IEEE_qCCL2025/plenaryspeakers)  
[cdotimes.com Top 25 Institutions Leading Quantum Computing Research in 2026](https://cdotimes.com/2026/07/17/top-25-institutions-leading-quantum-computing-research-in-2026-the-quantum-insider/)  
[academic.oup.com Experimental exploration of five-qubit quantum error-correcting code](https://academic.oup.com/nsr/article-abstract/9/1/nwab011/6105301)  
[en.baqis.ac.cn ABOUT QPQIS-2024](http://en.baqis.ac.cn/upload/file/20241031/b5f6170cf3b64a06b3b7ef1373cedb34.pdf)  
[pnas.org Quantum teleportation of physical qubits into logical code spaces](https://www.pnas.org/doi/10.1073/pnas.2026250118)  
[arxiv.org Concatenation of the Gottesman-Kitaev-Preskill code with the XZZX](https://arxiv.org/html/2207.04383v3)  
[scholar.google.lt ‪Sergey Bravyi‬ - ‪Google Scholar‬](https://scholar.google.lt/citations?user=DaHYX8sAAAAJ&hl=iw)  
[alphaxiv.org Continuous operation of a coherent 3,000-qubit system | alphaXiv](https://www.alphaxiv.org/abs/2506.20660v1)  
[radar.inria.fr COSMIQ - 2025 - Rapport annuel d'activité - Inria](https://radar.inria.fr/report/2025/cosmiq)  
[mediatum.ub.tum.de Applications of tensor networks to open problems in many-body](https://mediatum.ub.tum.de/doc/1686021/1686021.pdf)  
[quarc.csic.es Publications of Álvaro M. Alhambra](https://quarc.csic.es/database/publications-of-alvaro-m-alhambra/)  
[epubs.siam.org The Complexity of the Local Hamiltonian Problem | SIAM Journal on](https://epubs.siam.org/doi/abs/10.1137/S0097539704445226?mobileUi=0)  
[scholar.google.com ‪Zhengwei Liu‬ - ‪Google 学术搜索‬](https://scholar.google.com/citations?user=Nld6mJQAAAAJ&hl=zh-CN)  
[bimsa.cn BIMSA &gt; Quantum Theory and Operator Theory](https://www.bimsa.cn/research_detail/QTOT2024.html)  
[pubmed.ncbi.nlm.nih.gov Non-Abelian topological order and anyons on a trapped-ion processor](https://pubmed.ncbi.nlm.nih.gov/38356069/)  
[pme.uchicago.edu Braided, exotic particles could build reliable, universal quantum](https://pme.uchicago.edu/news-events/news/braided-exotic-particles-could-build-reliable-universal-quantum-computers)  
[postquantum.com First Universal Topological Gates Run on Quantinuum H2](https://postquantum.com/industry-news/universal-topological-gates-anyons/)  
[arxiv.org Expansion of higher-dimensional cubical complexes with ... - arXiv](https://arxiv.org/html/2402.07476v1)  
[arxiv.org Emulating quantum teleportation of a Majorana zero mode qubit](https://arxiv.org/html/2009.07590v2)  
[arxiv.org Universal Gates from Braiding and Fusing Anyons on Quantum](https://arxiv.org/html/2601.20956v2)  

### Sources read but not used in the report

[arxiv.orgQuantum Tanner codes - arXivOpens in a new window](https://arxiv.org/html/2202.13641v3)  
[arxiv.org[2202.13641] Quantum Tanner codes - arXivOpens in a new window](https://arxiv.org/abs/2202.13641)  
[scispace.comarXiv:2406.02666v2 [quant-ph] 5 Aug 2024 - SciSpaceOpens in a new window](https://scispace.com/pdf/entangling-four-logical-qubits-beyond-break-even-in-a-3mnprd0liyws.pdf)  
[pennylane.aiQSVT in Practice | PennyLane DemosOpens in a new window](https://pennylane.ai/demos/tutorial_apply_qsvt)  
[homes.cs.washington.eduMaking the leap to quantum PCPsOpens in a new window](https://homes.cs.washington.edu/~nirkhe/talks/leap_to_qpcps.pdf)  
[dash.harvard.eduFermionic Hamiltonians without trivial low-energy statesOpens in a new window](https://dash.harvard.edu/bitstreams/4ba91896-aa4f-477d-bec3-b1d3603c56af/download)  
[epubs.siam.orgNLTS Hamiltonians from Good Quantum Codes | SIAM Journal onOpens in a new window](https://epubs.siam.org/doi/10.1137/23M1608045)  
[researchgate.net(PDF) Fermionic Hamiltonians without trivial low-energy statesOpens in a new window](https://www.researchgate.net/publication/372654950_Fermionic_Hamiltonians_without_trivial_low-energy_states)  
[arxiv.org[2307.13730] Fermionic Hamiltonians without trivial low-energy statesOpens in a new window](https://arxiv.org/abs/2307.13730)  
[nolanjcoble.comNolan J. Coble Joint work with Matthew Coudron, Jon Nelson, andOpens in a new window](https://nolanjcoble.com/assets/files/Cob24_NLACS_IQC_Presentation.pdf)  
[research.iaifi.orgMachine Learning Decoding of Circuit-Level Noise for BivariateOpens in a new window](https://research.iaifi.org/posts/machine-learning-decoding-of-circuit-level-noise-for-bivariate-bicycle-codes/)  
[baqis.ac.cnIBM的量子跃迁：迈向容错量子计算新纪元Opens in a new window](https://www.baqis.ac.cn/news/detail/?cid=2288)  
[researchgate.netZhengwei LIU | Professor (Full) | Doctor of Philosophy - ResearchGateOpens in a new window](https://www.researchgate.net/profile/Zhengwei-Liu)  
[bimsa.cnBIMSA &gt; 2025 China Annual Review of MathematicsOpens in a new window](https://www.bimsa.cn/research_detail/AnnRevMathCN.html)  
[scholar.google.cat‪Zhengwei Liu‬ - ‪Google Scholar‬Opens in a new window](https://scholar.google.cat/citations?user=Nld6mJQAAAAJ&hl=ja)  
[bimsa.cnBIMSA Team Publishes Two Major Achievements in TopOpens in a new window](https://www.bimsa.cn/news/info/Artan-post.html)  
[arxiv.orgNon-Abelian Topological Order and Anyons on a Trapped-IonOpens in a new window](https://arxiv.org/abs/2305.03766)  
[project.inria.frMembers – From NISQ to LSQ: Bosonic and LDPC codes - InriaOpens in a new window](https://project.inria.fr/nisq2lsq/members/)  
[radar.inria.frCOSMIQ - 2023 - Rapport annuel d'activité - InriaOpens in a new window](https://radar.inria.fr/report/2023/cosmiq)  
[arxiv.orgModerate-length lifted quantum Tanner codes - arXivOpens in a new window](https://arxiv.org/html/2502.20297v1)  
[researchgate.netQuantum Tanner codes | Request PDF - ResearchGateOpens in a new window](https://www.researchgate.net/publication/366666198_Quantum_Tanner_codes)  
[arxiv.orgTransversal non-Clifford gates on almost-good quantum LDPC andOpens in a new window](https://arxiv.org/pdf/2604.01874)  
[arxiv.orgPoincaré Duality and Multiplicative Structures on Quantum CodesOpens in a new window](https://arxiv.org/pdf/2512.21922)  
[drops.dagstuhl.de41st Computational Complexity Conference (CCC 2026) - DROPSOpens in a new window](https://drops.dagstuhl.de/entities/volume/LIPIcs-volume-383)  
[researchgate.net(PDF) Quantum state preparation for multivariate functionsOpens in a new window](https://www.researchgate.net/publication/390634704_Quantum_state_preparation_for_multivariate_functions)  
[arxiv.orgMathematical open problems in Projected Entangled Pair StatesOpens in a new window](https://arxiv.org/html/1903.09439v2)  
[researchgate.netTensor Network States and Geometry - ResearchGateOpens in a new window](https://www.researchgate.net/publication/51910203_Tensor_Network_States_and_Geometry)  
[jtura.catPublications — Jordi TuraOpens in a new window](https://jtura.cat/index.php?page=pub)  
[arxiv.orgA Note on the Second Spectral Gap Incompleteness Theorem - arXivOpens in a new window](https://arxiv.org/pdf/2105.09854)  
[arxiv.orgDissipative ground state preparation and the Dissipative QuantumOpens in a new window](https://arxiv.org/pdf/2303.11962)  
[quantumai.googleResearch Publications | Google Quantum AIOpens in a new window](https://quantumai.google/research)  
[arxiv.orgUncomputability of Phase Diagrams - arXivOpens in a new window](https://arxiv.org/pdf/1910.01631)  
[researchgate.netHamiltonian complexity - ResearchGateOpens in a new window](https://www.researchgate.net/publication/229081389_Hamiltonian_complexity)  
[qzc.tsinghua.edu.cn研究方向概况 - 清华大学求真书院Opens in a new window](https://qzc.tsinghua.edu.cn/syjx/yjfx/bjyxhyysxyjy/lzxxhlzjs/yjfxgk.htm)  
[venetian777.com研究方向概况-威尼斯人娱乐场官网Opens in a new window](https://www.venetian777.com/syjx/yjfx/bjyxhyysxyjy/lzxxhlzjs/yjfxgk.htm)  
[academic.oup.comExperimental exploration of five-qubit quantum error-correcting codeOpens in a new window](https://academic.oup.com/nsr/article/9/1/nwab011/6105301)  
[wuli.ac.cn超导量子计算系统中的容错技术Opens in a new window](http://www.wuli.ac.cn/cn/article/doi/10.7693/wl20231103)  
[arxiv.orgOptimal control with flag qubits - arXivOpens in a new window](https://arxiv.org/html/2603.12162)  
[instituteforexoticscience.caS. Bravyi, A. W. Cross, J. M. Gambetta, D. Maslov, P. Rall and T. J.Opens in a new window](https://instituteforexoticscience.ca/citations/s-bravyi-a-w-cross-j-m-gambetta-d-maslov-p-rall-and-t-j-yode-ae8fea26.html)  
[econpapers.repec.orgHigh-threshold and low-overhead fault-tolerant quantum memoryOpens in a new window](https://econpapers.repec.org/RePEc:nat:nature:v:627:y:2024:i:8005:d:10.1038_s41586-024-07107-7)  
[studioglobal.aiUniversal Topological Gates from Braiding and Fusing Anyons onOpens in a new window](https://www.studioglobal.ai/discover/answers/search-6a59957c2408d940d300457f)  
[supercomputing.newsQuantinuum Runs a Universal Anyon Gate Set on Trapped IonsOpens in a new window](https://www.supercomputing.news/quantum/quantinuum-universal-anyon-gate-set-trapped-ions)  
[digiconasia.netUniversal quantum gates achieved — by braiding and fusing anyonsOpens in a new window](https://digiconasia.net/news/universal-quantum-gates-achieved-by-braiding-and-fusing-anyons)  
[zenodo.orgQuantum-State Homeostasis: A Source–Sink Architecture for FaultOpens in a new window](https://zenodo.org/records/20178857)

## 公开 Thoughts（页面顺序）

---

全球顶尖研究力量分布梳理

正在系统梳理全球在数学与量子计算交叉领域的核心研究机构与学术网络。初步归纳出北美（如加州理工学院IQIM、麻省理工学院、普林斯顿高等研究院）、欧洲（法国Inria、德国马克斯·普朗克量子光学研究所、荷兰QuTech/QuSoft）、中国（中国科学技术大学、清华大学交叉信息院、北京雁栖湖应用数学研究院）以及加拿大圆周理论物理研究所等领先团队的阵营分布，明确了各机构在拓扑量子、量子纠错码及算法理论方面的分布格局。

---

标志性理论突破与关键领域锁定

深入解析了近年来数学与量子计算结合的颠覆性成果，包括渐近优良量子LDPC码的建立、解决康尼斯嵌入猜想与齐尔森问题的MIP\*=RE证明、基于多项式逼近统一量子算法的量子奇异值转换（QSVT）框架，以及谱隙不可判定性等哈密顿复杂性理论。这些突破展示了算子代数、代数拓扑和高维扩展图等纯数学工具在量子信息中的深刻应用。

---

多维对比调研与后续推进计划

接下来将针对遴选出的核心团队，多维度收集具体数据，涵盖顶级期刊与会议（如Annals of Mathematics, Nature/Science, STOC/FOCS, QIP等）的产出表现、国家级重大项目资金支持、跨国联合研究计划以及与领先量子科技企业（如IBM、Google、Microsoft、Quantinuum等）的产业合作与联合实验室建设。进而构建横向对比矩阵，评估未来5-10年内最有潜力取得重大颠覆的团队并推演潜在的关键数学理论。

---

[eccc.weizmann.ac.il Quantum Tanner codes](https://eccc.weizmann.ac.il/report/2022/029/revision/1/download)  
[arxiv.org Quantum Tanner codes - arXiv](https://arxiv.org/html/2202.13641v3)  
[arxiv.org [2202.13641] Quantum Tanner codes - arXiv](https://arxiv.org/abs/2202.13641)  
[researchgate.net Quantum Tanner codes | Request PDF - ResearchGate](https://www.researchgate.net/publication/366666198_Quantum_Tanner_codes)  
[preskill.caltech.edu Simulating quantum LDPC codes with local gates - John Preskill](https://www.preskill.caltech.edu/pubs/preskill-2025-hierarchical.pdf)  
[arxiv.org Small quantum Tanner codes from left–right Cayley complexes - arXiv](https://arxiv.org/html/2512.20532v1)  
[researchgate.net (PDF) A parallel decoder for good quantum LDPC codes](https://www.researchgate.net/publication/362643510_A_parallel_decoder_for_good_quantum_LDPC_codes)  
[scispace.com arXiv:2406.02666v2 [quant-ph] 5 Aug 2024 - SciSpace](https://scispace.com/pdf/entangling-four-logical-qubits-beyond-break-even-in-a-3mnprd0liyws.pdf)  
[ieee-focs.org Quantum Tanner codes](https://ieee-focs.org/FOCS-2022-Papers/pdfs/FOCS2022-4Bu7jGV9xIcveUWYj3oWoi/551900a872/551900a872.pdf)  
[drops.dagstuhl.de Quantum LDPC Codes of Almost Linear Distance via ... - DROPS](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CCC.2025.25)  
[gilkalai.wordpress.com Amazing: Zhengfeng Ji, Anand Natarajan, Thomas Vidick, John](https://gilkalai.wordpress.com/2020/01/17/amazing-zhengfeng-ji-anand-natarajan-thomas-vidick-john-wright-and-henry-yuen-proved-that-mip-re-and-thus-disproved-connes-1976-embedding-conjecture-and-provided-a-negative-answer-to-tsirelso/)  
[pennylane.ai QSVT in Practice | PennyLane Demos](https://pennylane.ai/demos/tutorial_apply_qsvt)  
[arxiv.org Quantum signal processing with continuous variables - arXiv](https://arxiv.org/html/2304.14383v1)  
[quantum-journal.org An adversary bound for quantum signal processing](https://quantum-journal.org/papers/q-2026-03-13-2025/)  

---

量子纠错码的拓扑与代数突破

通过对近期文献与研究进展的梳理，我发现量子渐进好码（Asymptotically Good qLDPC Codes）已成为数学与量子计算交叉领域的核心阵地。法国Inria/Bordeaux团队（Leverrier与Zémor）利用左-右凯莱复形（Left-Right Cayley Complexes）与Tanner码构建了具有常数码率和线性码距的量子纠错码，简化了此前Panteleev与Kalachev的突破性成果。同时，麻省理工学院与哈佛大学团队（Guruswami与Golowich）提出通过重复同调积（Iterated Homological Products）构建近线性码距的子系统码，成功突破了此前同调积码在距离上限上的瓶颈。这些基于同调代数与高维扩张图（High-Dimensional Expanders）的数学构筑，正直接推动硬件架构从传统二维平面表面码向高维拓扑纠错迈型。

---

量子算法与复杂性理论的数学统一

在量子算法与复杂性理论方向，我观察到两大标志性理论进展。其一是量子单值变换（QSVT）与量子信号处理（QSP）框架的演进，加州大学伯克利分校（Lin Lin等）与QuSoft/匈牙利科学院（Gilyén等）将代数多项式逼近与SU(2)表示论相结合，成功将哈密顿量模拟、相位估计和矩阵求逆等传统算法统一于单一的线性代数多项式变换体系中。其二是复杂性理论中$MIP^\*=RE$定理的证明彻底解决了算子代数领域的康奈斯嵌入猜想（Connes' Embedding Conjecture），展示出非交换几何、算子代数与量子纠缠复杂性之间的深刻关联。

---

下一步对全球主要团队与维度的系统调研

接下来，我将针对全球几大核心研究梯队（如北美IQIM/CQA、欧洲Inria/MPQ/QuSoft、微软Station Q以及中国清华BIMSA/中科大/中科院等）展开系统化梳理。重点聚焦于各团队在学术产出、国际合作网络、国家级资金扶持以及与量子硬件龙头企业（如QuEra、IBM、Quantinuum等）的联合实验室与产业转化模式，进而构建多维横向对比体系，推演未来5-10年最可能带来颠覆性突破的数学理论与关键技术路径。

---

[homes.cs.washington.edu Making the leap to quantum PCPs](https://homes.cs.washington.edu/~nirkhe/talks/leap_to_qpcps.pdf)  
[dash.harvard.edu Fermionic Hamiltonians without trivial low-energy states](https://dash.harvard.edu/bitstreams/4ba91896-aa4f-477d-bec3-b1d3603c56af/download)  
[arxiv.org Fermionic Hamiltonians without trivial low-energy states - arXiv](https://arxiv.org/html/2307.13730v1)  
[epubs.siam.org NLTS Hamiltonians from Good Quantum Codes | SIAM Journal on](https://epubs.siam.org/doi/10.1137/23M1608045)  
[en.wikipedia.org NLTS conjecture - Wikipedia](https://en.wikipedia.org/wiki/NLTS_conjecture)  
[researchgate.net (PDF) Fermionic Hamiltonians without trivial low-energy states](https://www.researchgate.net/publication/372654950_Fermionic_Hamiltonians_without_trivial_low-energy_states)  
[blog.simons.berkeley.edu The Blind Men and the Quantum Elephants | Calvin Café](https://blog.simons.berkeley.edu/2022/08/the-blind-men-and-the-quantum-elephants/)  
[escholarship.org Lower bounds on the complexity of quantum proofs - UC Berkeley](https://escholarship.org/content/qt5tb9r54c/qt5tb9r54c.pdf)  
[arxiv.org [2307.13730] Fermionic Hamiltonians without trivial low-energy states](https://arxiv.org/abs/2307.13730)  
[nolanjcoble.com Nolan J. Coble Joint work with Matthew Coudron, Jon Nelson, and](https://nolanjcoble.com/assets/files/Cob24_NLACS_IQC_Presentation.pdf)  
[postquantum.com Quantum Low-Density Parity-Check (qLDPC) Codes](https://postquantum.com/quantum-computing/quantum-low-density-parity-check-qldpc-codes/)  
[ibm.com IBM lays out clear path to fault-tolerant quantum computing](https://www.ibm.com/quantum/blog/large-scale-ftqc)  
[anthonywest.co.uk Fault-tolerant quantum computing: IBM (2025) | Anthony West](https://anthonywest.co.uk/explainers/folders/quantum-computing/2026-04-29_ibm_fault-tolerant-quantum-roadmap_explainer)  
[researchgate.net High-threshold and low-overhead fault-tolerant quantum memory](https://www.researchgate.net/publication/379336526_High-threshold_and_low-overhead_fault-tolerant_quantum_memory)  
[research.iaifi.org Machine Learning Decoding of Circuit-Level Noise for Bivariate](https://research.iaifi.org/posts/machine-learning-decoding-of-circuit-level-noise-for-bivariate-bicycle-codes/)  
[baqis.ac.cn IBM的量子跃迁：迈向容错量子计算新纪元](https://www.baqis.ac.cn/news/detail/?cid=2288)  
[bimsa.cn BIMSA &gt; Quantum Symmetry](https://www.bimsa.cn/groups/quantum-symmetry.html)  
[researchgate.net Zhengwei LIU | Professor (Full) | Doctor of Philosophy - ResearchGate](https://www.researchgate.net/profile/Zhengwei-Liu)  
[bimsa.net Shing-Tung Yau - BIMSA](https://bimsa.net/people/yau/)  
[bimsa.cn BIMSA &gt; Quantum Theory and Operator Theory](https://www.bimsa.cn/research_detail/QTOT2024.html)  
[bimsa.cn New and efficient approach to classical simulations of variational](https://www.bimsa.cn/news/info/1235.html)  
[bimsa.net Zhengwei Liu - BIMSA](https://bimsa.net/people/zwliu/)  
[bimsa.cn BIMSA &gt; 2025 China Annual Review of Mathematics](https://www.bimsa.cn/research_detail/AnnRevMathCN.html)  
[scholar.google.cat ‪Zhengwei Liu‬ - ‪Google Scholar‬](https://scholar.google.cat/citations?user=Nld6mJQAAAAJ&hl=ja)  
[scholar.google.com ‪Zhengwei Liu‬ - ‪Google 学术搜索‬](https://scholar.google.com/citations?user=Nld6mJQAAAAJ&hl=zh-CN)  
[bimsa.cn BIMSA Team Publishes Two Major Achievements in Top](https://www.bimsa.cn/news/info/Artan-post.html)  
[arxiv.org Non-Abelian Topological Order and Anyons on a Trapped-Ion](https://arxiv.org/abs/2305.03766)  
[pubmed.ncbi.nlm.nih.gov Non-Abelian topological order and anyons on a trapped-ion processor](https://pubmed.ncbi.nlm.nih.gov/38356069/)  

---

量子复杂性与纠错理论新进展

深入分析了无低能平凡态（NLTS）定理及其在费米子哈密顿量中的最新拓展，证实了量子纠错码与量子哈密顿复杂性之间的深层联系。同时，梳理了基于双变量单车码（Bivariate Bicycle Codes）的低开销容错量子内存突破，以及非阿贝尔拓扑序在量子硬件上的最新实验验证，展现了代数拓扑与高维几何理论在逻辑量子比特构建中的核心作用。

---

全球研究资助与产学研合作格局

进一步梳理了全球主要国家与地区的重大量子科研计划，如美国的量子飞跃挑战研究所（QLCI）与能源部量子信息科学研究中心、欧洲的量子旗舰计划与ERC资助体系、中国的科技创新2030-“量子通信与量子计算机”重大项目等。同时，分析了顶尖学术机构与量子科技巨头（如IBM、Quantinuum、QuEra等）在容错量子计算与中性原子架构方面的深层合作模式。

---

下一步调研与对比分析计划

下一步将重点聚焦中国在数学与量子计算交叉领域的顶尖团队（如清华大学交叉信息研究院、北京雁栖湖应用数学研究院、中国科学院数学与系统科学研究院及中国科学技术大学等），补充其学术带头人与最新理论产出。随后，将整合前述所有数据，构建多维横向对比矩阵，推演未来5-10年内最有希望取得颠覆性突破的团队与关键数学理论。

---

量子拓扑与图示化数学新范式

在深入梳理各阵营的数学理论工具时，我关注到北京雁栖湖应用数学研究院（BIMSA）与清华大学团队在量子对称性与算子代数领域的系统性理论建树。刘正伟教授等提出的Alterfold理论与Quon图示化语言，将算子代数、量子拓扑与张量网络深度结合，构建了统一的数学图示化框架；同时，其团队发展的变分量子算法经典模拟方法（OBPPP）证明了特定有限深度变分量子线路的多项式复杂度界限，为理解量子噪声与经典可模拟性边界提供了严格的数学工具。

---

硬件可实现非阿贝尔拓扑序的实验与理论拟合

在拓扑量子计算与非阿贝尔任意子领域，工业界与学术界交叉研究展现出重要突破。Quantinuum团队（Henrik Dreyer等）在Nature发表的突破性成果，成功在27个离子阱量子比特上利用自适应线路构建了$D\_4$非阿贝尔拓扑序基态，并实现了任意子的编织与控制。这表明结合高维代数拓扑与自适应测量技术，能够将原本停留在纯数学推演中的非阿贝尔拓扑状态转化为可编程的量子硬件架构。

---

全球核心团队多维对比数据采集计划

下一步，我将针对加州理工学院IQIM、法国Inria/PCQC、阿姆斯特丹QuSoft、加州大学伯克利分校应用数学团队以及IBM/Microsoft理论部门等重点机构，展开深度的多维数据搜集。重点整理各团队在顶级期刊（如Nature/Science、PRL、Annals of Mathematics）及算法顶级会议（STOC/FOCS、QIP）的产出表现、国家级资金扶持（如美国NSF/DOE、欧盟Horizon Europe、ANR PEPR等）以及与硬件巨头的联合转化模式，为最终的横向比较矩阵与未来5-10年突破预测提供支撑。

---

[ieee-focs.org Quantum Tanner codes](https://ieee-focs.org/FOCS-2022-Papers/pdfs/FOCS2022-4Bu7jGV9xIcveUWYj3oWoi/551900a872/551900a872.pdf)  
[inria.fr Theory of error-correcting codes: fundamental results to go towards](https://www.inria.fr/en/error-correcting-codes-fundamental-results-quantum-computer)  
[radar.inria.fr COSMIQ - 2025 - Rapport annuel d'activité - Inria](https://radar.inria.fr/report/2025/cosmiq)  
[project.inria.fr Members – From NISQ to LSQ: Bosonic and LDPC codes - Inria](https://project.inria.fr/nisq2lsq/members/)  
[radar.inria.fr COSMIQ - 2023 - Rapport annuel d'activité - Inria](https://radar.inria.fr/report/2023/cosmiq)  
[arxiv.org Moderate-length lifted quantum Tanner codes - arXiv](https://arxiv.org/html/2502.20297v1)  
[uva.nl Quantum Technology - University of Amsterdam](https://www.uva.nl/en/news-events/press-office/uva-experts/quantum-technology/quantum-technology.html)  
[cwi.nl Quantum Software Consortium receives 18.8 million euro in the](https://www.cwi.nl/en/news/quantum-software-consortium-receives-18-8-million-euro-in-the-gravitation-programme/)  
[qusoft.org QuSoft Annual Report 2023](https://qusoft.org/?jet_download=7667f1b95d33d9323e1debde644cb67bc8d6f290)  

---

顶尖团队资金与产学研模式明晰

通过对法国Inria/Bordeaux团队与荷兰QuSoft/CWI等机构的深入梳理，我掌握了欧洲顶尖交叉团队的具体资助与产业合作细节。Inria团队主要依赖法国国家量子战略中的PEPR专项（如NISQ2LSQ项目，拨款1.5亿欧元）以及EU QuantERA计划，并与Alice & Bob等量子初创公司紧密合作推行Cat Qubit与LDPC码结合；荷兰QuSoft则依靠NWO Gravitation Grant（量子软件财团1880万欧元）及Quantum Delta NL（6.15亿欧元），并通过量子应用实验室（QAL）与丰田等工业巨头开展技术转化。这些明确的资金支持与产学研布局构筑了其高浓度的理论研究与工程转化生态。

---

理论突破与工程路线的深度融合

在分析量子纠错码与算法框架的过程中，我观察到前沿纯数学工具正在加速向硬件路线图渗透。例如Inria提出的量子Tanner码不仅在数学上解开了NLTS猜想，其线性时间解码算法更被直接引入容错架构设计；而IBM的双变量单车码与加州理工-AWS联合团队的量子LDPC研究，正在促使工业界量子路线图从传统的二维平面表面码向高维拓扑与代数纠错码全面转向，大幅降低了容错量子计算所需的物理比特开销。

---

下一步横向对比与颠覆性理论推演

接下来，我将综合前述收集到的全球各大核心团队（包括北美IQIM/MIT/Harvard、欧洲Inria/MPQ/QuSoft、微软Station Q以及中国清华BIMSA/中科大/中科院等）的数据，构建涵盖理论创新深度、资金体量、产学研结合度等多维度的横向对比矩阵。基于此，我将遴选出未来5-10年最有望取得重大突破的梯队，并对高维扩展图纠错码、非阿贝尔拓扑相分类及多变量量子奇异值变换等关键数学理论与衍生技术路线进行深度推演。

---

[arxiv.org Transversal non-Clifford gates for quantum LDPC codes on sheaves](https://arxiv.org/pdf/2410.14631)  
[arxiv.org Expansion of higher-dimensional cubical complexes with ... - arXiv](https://arxiv.org/html/2402.07476v1)  
[researchgate.net Quantum Tanner codes | Request PDF - ResearchGate](https://www.researchgate.net/publication/366666198_Quantum_Tanner_codes)  
[arxiv.org NLTS Hamiltonians and Strongly-Explicit SoS Lower Bounds ... - arXiv](https://arxiv.org/pdf/2311.09503)  
[sanchayandutta.cs.ucdavis.edu SoS Lower Bounds, SS-HDX and NLTS - Sanchayan Dutta](https://sanchayandutta.cs.ucdavis.edu/files/Slides_SoS_Lower_Bounds__SS_HDX_and_NLTS.pdf)  
[arxiv.org Transversal non-Clifford gates on almost-good quantum LDPC and](https://arxiv.org/pdf/2604.01874)  
[arxiv.org Theory of (Co)homological Invariants on Quantum LDPC Codes](https://arxiv.org/pdf/2603.25831)  
[arxiv.org Poincaré Duality and Multiplicative Structures on Quantum Codes](https://arxiv.org/pdf/2512.21922)  
[researchgate.net Quantum LDPC Codes With Positive Rate and Minimum Distance](https://www.researchgate.net/publication/260711243_Quantum_LDPC_Codes_With_Positive_Rate_and_Minimum_Distance_Proportional_to_the_Square_Root_of_the_Blocklength)  
[drops.dagstuhl.de 41st Computational Complexity Conference (CCC 2026) - DROPS](https://drops.dagstuhl.de/entities/volume/LIPIcs-volume-383)  
[pubs.aip.org A perspective from block-encodings and polynomial transformations](https://pubs.aip.org/aip/aco/article/2/1/010901/3378659/Scalable-quantum-computational-science-A)  
[publications.mfo.de Quantum Signal Processing and Nonlinear Fourier Analysis](https://publications.mfo.de/bitstream/handle/mfo/4262/OWR_2024_46.pdf?sequence=1&isAllowed=y)  
[semanticscholar.org On variants of multivariate quantum signal processing and their](https://www.semanticscholar.org/paper/On-variants-of-multivariate-quantum-signal-and-N%27emeth-K%C3%B6v%C3%A9r/82c630b2e39b92d6372cc2695ced2ec3b2c3273f)  
[researchgate.net (PDF) Quantum state preparation for multivariate functions](https://www.researchgate.net/publication/390634704_Quantum_state_preparation_for_multivariate_functions)  

---

量子复杂性与拓扑同调纠错理论的新融通

通过对量子PCP猜想、无低能平凡态（NLTS）定理及量子局部可测试码（qLTC）最新理论进展的梳理，我观察到代数拓扑中的上同调积（Cup Product）与束论（Sheaf Theory）正成为构建容错量子计算的关键数学工具。利用高维立方复形与代数几何中的余边界扩展（Coboundary Expansion），研究团队在量子LDPC码上成功实现了横向非克利福德门（Transversal non-Clifford Gates），解决了长久以来容错量子计算中高码率与逻辑门实现不可兼得的难题。同时，将量子码表示为链复形的几何拓扑结构，为证明量子复杂性理论中的硬度界限提供了全新范式。

---

多元量子信号处理与谐波分析的理论统一

在量子算法的数学基础方面，多元量子信号处理（Multivariate QSP）与多元量子奇异值变换（Multivariate QSVT）取得了突破性进展。该框架将复杂量子算法映射为非线性傅里叶分析（Nonlinear Fourier Analysis）与SU(2)群表示论中的多项式逼近问题。这一理论上的统一不仅简化了多变量函数量子态准备的复杂度，更为设计非算术线路依赖的高效量子线性代数算法奠定了严格的数学基础。

---

欧洲与中国学术阵营的深层次调配与下一步预测

接下来，我将针对欧洲顶尖研究机构（如马克斯·普朗克量子光学研究所、伦敦大学学院、柏林自由大学）以及中国本土核心团队（中国科学院数学与系统科学研究院、清华大学、中国科学技术大学等）展开专项补充调研。重点评估各团队在量子谱隙不可判定性、哈密顿量复杂性及算子代数领域的深厚底蕴，随后将综合全球所有核心团队的数据，构建多维横向对比矩阵，推演未来5-10年内最有望取得重大颠覆的团队并预测关键数学突破。

---

[mcqst.de Ignacio Cirac - Munich Center for Quantum Science and Technology](https://www.mcqst.de/about/members/ignacio-cirac.html)  
[edoc.ub.uni-muenchen.de Tensor Network Methods in Many-body physics](https://edoc.ub.uni-muenchen.de/24118/1/Molnar_Andras.pdf)  
[mediatum.ub.tum.de Applications of tensor networks to open problems in many-body](https://mediatum.ub.tum.de/doc/1686021/1686021.pdf)  
[quantum-journal.org A Hierarchy of Spectral Gap Certificates for Frustration-Free Spin](https://quantum-journal.org/papers/q-2026-04-13-2065/)  
[alphaxiv.org David Pérez-García | alphaXiv](https://www.alphaxiv.org/@david-perez-garcia)  
[arxiv.org Mathematical open problems in Projected Entangled Pair States](https://arxiv.org/html/1903.09439v2)  
[quarc.csic.es Publications of Álvaro M. Alhambra](https://quarc.csic.es/database/publications-of-alvaro-m-alhambra/)  
[arxiv.org arXiv:2011.12127v2 [quant-ph] 9 Aug 2021](https://arxiv.org/pdf/2011.12127)  
[researchgate.net Tensor Network States and Geometry - ResearchGate](https://www.researchgate.net/publication/51910203_Tensor_Network_States_and_Geometry)  
[jtura.cat Publications — Jordi Tura](https://jtura.cat/index.php?page=pub)  
[arxiv.org Spectral gap of Lee-Yang Hamiltonians - arXiv](https://arxiv.org/pdf/2607.10765)  
[arxiv.org A Note on the Second Spectral Gap Incompleteness Theorem - arXiv](https://arxiv.org/pdf/2105.09854)  
[qis.mit.edu seminars - quantum information science @ mit](http://qis.mit.edu/seminars.php?q=past)  
[researchgate.net (PDF) The Undecidability of the Spectral Gap: An Expository](https://www.researchgate.net/publication/411800951_The_Undecidability_of_the_Spectral_Gap_An_Expository_Account_of_a_Fundamental_Limitation_in_Quantum_Many-Body_Physics)  
[researchgate.net Uncomputability of phase diagrams - ResearchGate](https://www.researchgate.net/publication/348601108_Uncomputability_of_phase_diagrams)  
[epubs.siam.org The Complexity of the Local Hamiltonian Problem | SIAM Journal on](https://epubs.siam.org/doi/abs/10.1137/S0097539704445226?mobileUi=0)  
[arxiv.org Dissipative ground state preparation and the Dissipative Quantum](https://arxiv.org/pdf/2303.11962)  
[repositories.lib.utexas.edu Dissertation by Justin Yirka - The University of Texas at Austin](https://repositories.lib.utexas.edu/bitstreams/dd3e1ca6-e569-4f0e-9c04-3b4181b79b5a/download)  
[quantumai.google Research Publications | Google Quantum AI](https://quantumai.google/research)  
[arxiv.org Uncomputability of Phase Diagrams - arXiv](https://arxiv.org/pdf/1910.01631)  
[researchgate.net Hamiltonian complexity - ResearchGate](https://www.researchgate.net/publication/229081389_Hamiltonian_complexity)  

---

量子张量网络与谱隙不可判定性

通过对马克斯·普朗克量子光学研究所（MPQ）Ignacio Cirac团队与伦敦大学学院（UCL）Toby Cubitt团队成果的深入剖析，我梳理了张量网络（PEPS/MPS）在量子多体系统与量子复杂性中的深刻数学表达。特别是在谱隙不可判定性（Undecidability of Spectral Gap）以及基于半正定规划（SDP）的谱隙下界认证层级结构方面，说明了无穷维算子代数与连续代数结构在判断多体哈密顿量基态性质中的基本限制与判定方法。

---

国内外交叉团队资助与布局梳理

在整合全球顶尖研究机构的资助背景时，我进一步理清了中国团队（如清华交叉信息院、BIMSA、中国科学院数研院及中科大）在科技创新2030-“量子通信与量子计算机”重大项目与国家自然科学基金重点项目中的布局，以及北美（MIT、Caltech、Harvard）与欧洲（Inria、MPQ、QuSoft）在NSF/DOE、ERC等重大专项支持下的理论攻坚格局，完成了对全球核心团队资金支撑与产学研模式的数据补全。

---

构建横向对比矩阵与未来突破推演

接下来，我将把收集到的全球各大核心团队（涵盖理论创新深度、论文顶刊产出、国际合作网络、国家级资金体量及工业界合作等五大维度）进行综合量化与横向对比，构建多维竞争格局矩阵。基于此评估出未来5-10年最可能取得颠覆性突破的梯队，并对高维扩展图（HDX）纠错码、非阿贝尔拓扑序硬件化、多变量量子奇异值变换（QSVT）及 Type III von Neumann 代数在量子纠错中的应用做出前瞻性推演。

---

[qzc.tsinghua.edu.cn 研究方向概况 - 清华大学求真书院](https://qzc.tsinghua.edu.cn/syjx/yjfx/bjyxhyysxyjy/lzxxhlzjs/yjfxgk.htm)  
[venetian777.com 研究方向概况-威尼斯人娱乐场官网](https://www.venetian777.com/syjx/yjfx/bjyxhyysxyjy/lzxxhlzjs/yjfxgk.htm)  
[qzc.tsinghua.edu.cn 刘正伟团队提出经典模拟变分量子算法的多项式新途径](https://qzc.tsinghua.edu.cn/info/1040/6441.htm)  
[pnas.org Quantum teleportation of physical qubits into logical code spaces](https://www.pnas.org/doi/10.1073/pnas.2026250118)  
[academic.oup.com Experimental exploration of five-qubit quantum error-correcting code](https://academic.oup.com/nsr/article/9/1/nwab011/6105301)  
[academic.oup.com Experimental exploration of five-qubit quantum error-correcting code](https://academic.oup.com/nsr/article-abstract/9/1/nwab011/6105301)  
[arxiv.org Emulating quantum teleportation of a Majorana zero mode qubit](https://arxiv.org/html/2009.07590v2)  
[en.baqis.ac.cn ABOUT QPQIS-2024](http://en.baqis.ac.cn/upload/file/20241031/b5f6170cf3b64a06b3b7ef1373cedb34.pdf)  
[cdotimes.com Top 25 Institutions Leading Quantum Computing Research in 2026](https://cdotimes.com/2026/07/17/top-25-institutions-leading-quantum-computing-research-in-2026-the-quantum-insider/)  
[arxiv.org Concatenation of the Gottesman-Kitaev-Preskill code with the XZZX](https://arxiv.org/html/2207.04383v3)  
[wuli.ac.cn 超导量子计算系统中的容错技术](http://www.wuli.ac.cn/cn/article/doi/10.7693/wl20231103)  
[arxiv.org Optimal control with flag qubits - arXiv](https://arxiv.org/html/2603.12162)  
[events.polyu.edu.hk Plenary and Keynote Speakers - PolyU](https://events.polyu.edu.hk/IEEE_qCCL2025/plenaryspeakers)  
[scholar.google.lt ‪Sergey Bravyi‬ - ‪Google Scholar‬](https://scholar.google.lt/citations?user=DaHYX8sAAAAJ&hl=iw)  
[instituteforexoticscience.ca S. Bravyi, A. W. Cross, J. M. Gambetta, D. Maslov, P. Rall and T. J.](https://instituteforexoticscience.ca/citations/s-bravyi-a-w-cross-j-m-gambetta-d-maslov-p-rall-and-t-j-yode-ae8fea26.html)  
[ibm.com IBM lays out clear path to fault-tolerant quantum computing](https://www.ibm.com/quantum/blog/large-scale-ftqc)  
[arxiv.org High-threshold and low-overhead fault-tolerant quantum memory](https://arxiv.org/abs/2308.07915)  
[econpapers.repec.org High-threshold and low-overhead fault-tolerant quantum memory](https://econpapers.repec.org/RePEc:nat:nature:v:627:y:2024:i:8005:d:10.1038_s41586-024-07107-7)  

---

中国研究团队在量子纠错与拓扑数学的突破

通过对中国科研力量的系统检索，我梳理了清华大学丘成桐数学科学中心、北京雁栖湖应用数学研究院（BIMSA）以及中国科学技术大学/合肥国家实验室在数学与量子计算交叉领域的深厚积淀。清华与BIMSA团队基于量子拓扑、量子代数与图形化语言（Quon），成功建立了量子信息与纠错码的图示化数学框架；而中科大/合肥国家实验室则在[5,1,3]最小完美量子纠错码的实验验证、玻色码（GKP码与XZZX表面码级联）以及基于Flag-GRAPE算法的测量辅助量子控制等方向取得了重要进展，展示出强劲的理论与工程结合能力。

---

高门槛与低开销量子内存理论的印证

在量子纠错码的工程落地方面，我关注到IBM Quantum团队在《Nature》上发表的量子内存突破。该成果利用双变量单车码（Bivariate Bicycle LDPC Codes）构建了具备0.8%高容错门槛及低物理比特开销的量子内存协议，在容错门槛上达到了与传统二维表面码持平的水准，但在物理比特冗余度上实现了数量级的优化。这进一步印证了代数图论与有限域线性代数在突破硬件资源瓶颈中的绝对核心地位。

---

整合全景数据与撰写多维对比评估报告

接下来，我将把全球各大核心团队（包括北美Harvard/MIT/Caltech、欧洲Inria/QuSoft/MPQ、工业界IBM/Microsoft/Quantinuum以及中国Tsinghua/USTC/CAS等）在论文产出、国际合作、科研资金与产业化落地等维度的具体数据进行全面汇总，构建横向对比矩阵。基于此，我将评估未来5-10年最有望实现颠覆性突破的重点阵营，并对高维扩张图、代数拓扑余边界扩展及多元量子奇异值变换等关键数学理论与应用技术作出前瞻预测。

---

[researchgate.net Shuttling arrives for silicon quantum computers - ResearchGate](https://www.researchgate.net/publication/392540454_Shuttling_arrives_for_silicon_quantum_computers)  
[researchgate.net Performance of the spin qubit shuttling architecture for a surface](https://www.researchgate.net/publication/389821189_Performance_of_the_spin_qubit_shuttling_architecture_for_a_surface_code_implementation)  
[studioglobal.ai Universal Topological Gates from Braiding and Fusing Anyons on](https://www.studioglobal.ai/discover/answers/search-6a59957c2408d940d300457f)  
[supercomputing.news Quantinuum Runs a Universal Anyon Gate Set on Trapped Ions](https://www.supercomputing.news/quantum/quantinuum-universal-anyon-gate-set-trapped-ions)  
[simonsfoundation.org Quantum Effects Go Macro: Collaboration Unravels the Ultra](https://www.simonsfoundation.org/2026/08/03/quantum-effects-go-macro-collaboration-unravels-the-ultra-quantum-realm/)  
[digiconasia.net Universal quantum gates achieved — by braiding and fusing anyons](https://digiconasia.net/news/universal-quantum-gates-achieved-by-braiding-and-fusing-anyons)  
[quantumcomputingreport.com Quantinuum and Academic Partners Demonstrate First Universal](https://quantumcomputingreport.com/quantinuum-and-academic-partners-demonstrate-first-universal-topological-gate-set-via-non-abelian-anyons/)  
[pubmed.ncbi.nlm.nih.gov Non-Abelian topological order and anyons on a trapped-ion processor](https://pubmed.ncbi.nlm.nih.gov/38356069/)  
[arxiv.org Universal Gates from Braiding and Fusing Anyons on Quantum](https://arxiv.org/html/2601.20956v2)  
[postquantum.com First Universal Topological Gates Run on Quantinuum H2](https://postquantum.com/industry-news/universal-topological-gates-anyons/)  
[pme.uchicago.edu Braided, exotic particles could build reliable, universal quantum](https://pme.uchicago.edu/news-events/news/braided-exotic-particles-could-build-reliable-universal-quantum-computers)  
[assets-eu.researchsquare.com Reconstructing non-Abelian braiding and fusion without anyon](https://assets-eu.researchsquare.com/files/rs-10607154/v1_covered_78c709d3-c3c6-4e64-a022-9311ce9828c6.pdf)  
[arxiv.org A Noncommutative Nullstellensatz for Perfect Two-Answer ... - arXiv](https://www.arxiv.org/pdf/2501.11826v1)  
[jst.go.jp 2.7.5 計算理論 - 科学技術振興機構（JST）](https://www.jst.go.jp/crds/pdf/2024/FR/CRDS-FY2024-FR-03/CRDS-FY2024-FR-03_20705.pdf)  

---

中性原子与离子阱硬件上的拓扑量子突破

通过对哈佛大学/QuEra与Quantinuum/芝加哥大学最新实验与理论成果的对比分析，我观察到高维代数拓扑与非阿贝尔对称性已成功在硬件层面得到验证。哈佛-QuEra团队利用中性原子阵列与移动量子比特（Shuttling Qubits），在48个以上逻辑比特上实现了基于三维同调码的逻辑采样线路与横向门操作；而Quantinuum与哈佛/加州理工联合团队则在54量子比特的离子阱处理器上准备了$S\_3$与$D\_4$非阿贝尔拓扑序基态，并通过编织（Braiding）与融合（Fusion）实现了免去魔态蒸馏（Magic State Distillation）的全拓扑通用门集合。这标志着纯数学中的模张量范畴（Modular Tensor Categories）与量子双代数（Quantum Doubles）正在从理论抽象走向硬件原生实现。

---

算子代数与量子算法框架的交叉融合

在数学基础理论方面，我梳理了算子代数与非交换几何在复杂性理论中的深远影响。季铮锋等学者通过$MIP^\*=RE$定理证明了非局部游戏与无限维算子代数的等价性，彻底消解了康尼斯嵌入猜想（Connes' Embedding Conjecture）与齐尔森问题（Tsirelson's Problem）。同时，量子奇异值变换（QSVT）向多变量（Multivariate QSVT）与SU(1,1)非紧致群表示论的拓展，正为非线性微分方程模拟与非酉量子动力学提供统一的多项式逼近代数工具。

---

多维对比体系构建与未来5-10年推演

接下来，我将把收集到的全球顶尖阵营（北美哈佛/MIT/加州理工-AWS、欧洲Inria/MPQ/QuSoft、微软Station Q以及中国清华BIMSA/中科大/中科院等）在理论深度、顶刊发表（Nature/Science, Annals of Math, STOC/FOCS/QIP）、国家级资金（NSF/DOE, ERC, 科技创新2030）及产业转化等五大维度进行全面量化横向对比。在此基础上，遴选未来5-10年最可能取得重大突破的梯队，并对高维扩张图（HDX）余边界扩展、束上同调（Sheaf Cohomology）非克利福德门合成、连续变量量子纠错中的III型冯·诺依曼代数等前瞻数学理论与千级逻辑比特容错架构做出系统推演。

---

[alphaxiv.org Continuous operation of a coherent 3,000-qubit system | alphaXiv](https://www.alphaxiv.org/abs/2506.20660v1)  
[zenodo.org Quantum-State Homeostasis: A Source–Sink Architecture for Fault](https://zenodo.org/records/20178857)  
[researchgate.net Shuttling arrives for silicon quantum computers - ResearchGate](https://www.researchgate.net/publication/392540454_Shuttling_arrives_for_silicon_quantum_computers)  
[researchgate.net Performance of the spin qubit shuttling architecture for a surface](https://www.researchgate.net/publication/389821189_Performance_of_the_spin_qubit_shuttling_architecture_for_a_surface_code_implementation)  

---

量子中性原子与硅基自旋架构的新验证

通过对近期硬件架构文献的梳理，我深入分析了中性原子阵列与硅基自旋量子比特在容错量子计算中的最新工程与理论进展。特别是在中性原子平台（如哈佛大学与QuEra团队）利用动态 shuttle 技术的448原子处理器展示，以及硅基自旋量子比特借助单线态-三线态编码与漏失检测协议提高纠错门槛的突破。这些进展表明，代数图论、高维拓扑纠错码与自适应控制理论正在加速融通，并被直接应用到可扩展量子硬件的设计之中。

---

全球理论阵营与五大数学理论路线的全景整理

我已经全面完成了对全球十大顶尖交叉研究团队（包括北美加州理工IQIM、麻省理工/哈佛、IBM Quantum，欧洲法国Inria、荷比卢QuSoft、德国马普所，以及中国清华BIMSA、中科大/合肥国家实验室等）的系统调研。归纳出当前推动量子计算突破的五大核心数学方向：高维扩展图与代数拓扑（qLDPC码）、范畴论与TQFT（拓扑量子计算）、算子代数与非交换几何（复杂性理论与MIP\*=RE）、多项式逼近与谐波分析（QSVT/QSP算法）以及多体纠缠与张量网络理论。

---

撰写多维对比评估报告与突破预测

在完成了所有核心维度的数据采集与理论梳理后，我将不再发起额外的检索，转入最终报告的撰写。我将构建涵盖理论深度、论文产出、国际合作、科研资金及产业结合度等多维度的横向对比矩阵，深入评估未来5-10年内最有希望驱动颠覆性突破的核心梯队，并对高维余边界扩展纠错码、非阿贝尔任意子编织以及多元量子信号处理等前沿数学理论与衍生技术路径做出详细推演。

---

初步研究收集了大量信息。我正在整理和组织这些信息，以确保整个项目流程顺畅，并涵盖您要求的所有关键点。

---

就是这样！我要把所有东西都整合起来。记下我最后的想法，润色一切，确保给你我最好的作品。

---

---

Hide thoughts

## 原始页面记录

完整原始摘录保存在[同名 HTML 档案](html/gemini-14.html)末尾的折叠附录中。Markdown 为便于检索的正文版，未重复嵌入原始结构。
