[← 二十份研究目录](README.md)

# ChatGPT · ID 14 · 量子计算与数学交叉研究评估

[原研究窗口](https://chatgpt.com/g/g-p-6aa7b0cb61f48191bc4c4f582a8acef5/c/6aa7b4dc-4954-83ea-a600-9d115d7edf23)

原文整理，不改写研究结论。旧页面记录采集于 2026-09-14；GPT Activity 于 2026-09-17 补采。保留页面公开展示的过程说明，不代表平台未公开的内部推理。 保留引用按钮编号，但旧来源摘录不保证完整呈现每个按钮内全部对应来源。图形布局及未载入图片不在文本摘录中；公式按页面现有文本保留，不推测补齐运算符。

## 评测原题

收集整理全球数学与量子计算交叉领域的主要研究团队及其成果，横向比较其研究方向、论文产出、国际合作、资金支持、工业界合作等维度，评估哪些团队最有可能在未来5-10年内推动量子计算技术的重大突破，并预测可能产生的关键性数学理论或应用技术

## 对话及完成信息

Today 4:48 PM

##### You said:

Deep research

收集整理全球数学与量子计算交叉领域的主要研究团队及其成果，横向比较其研究方向、论文产出、国际合作、资金支持、工业界合作等维度，评估哪些团队最有可能在未来5-10年内推动量子计算技术的重大突破，并预测可能产生的关键性数学理论或应用技术

Your message actions

##### ChatGPT said:

页面完成时长：11 分钟（页面取整值）；显示来源数：65。本窗口未见 Gemini 式独立审批方案，未从报告倒推补写。

## 最终研究报告

## 全球数学与量子计算交叉领域主要研究团队、成果与未来突破潜力

### 执行摘要

截至2026年9月，本报告基于原始论文、机构官网、资助公告及可核验文献计量，筛选全球15个具有代表性的数学—量子计算团队。综合判断：**IBM、Google Quantum AI、Quantinuum**最接近“数学纠错理论—逻辑量子比特—硬件”闭环；**Caltech、QuICS/RQS、MIT、QuSoft**最可能持续产生改变算法复杂度或容错资源量级的理论；**QMATH、ETH、Oxford、NUS**在量子信息数学、算子/熵理论、图与范畴方法方面具有高杠杆潜力。未来5–10年的核心变量是qLDPC纠错、解码数学、QSVT/信号处理、形式化编译、量子学习与认证，以及尚具较大不确定性的拓扑量子计算。[1]

### 研究口径与评估方法

本研究以**2016年9月至2026年9月**为主窗口；2016年前的成果仅在其仍直接塑造当前研究路线时作为历史背景。所谓“数学与量子计算交叉”，并不限于数学系，而是要求团队的核心工作实质依赖于代数、拓扑、图论、算子理论、信息论、概率与随机方法、数值分析、优化、复杂性理论、编码理论、张量网络或数学物理等工具，并对量子算法、量子纠错、量子模拟、验证、编译、通信或硬件架构产生直接影响。

团队边界按用户要求采用“**PI当前归属＋稳定联合中心＋代表作发表时机构归属**”划分。因此，像QuICS/RQS、MIT–IBM、QMATH及Quantinuum–Microsoft这样的跨机构结构，会保留合作关系而不强行合并。QuSoft创始人Harry Buhrman自2023年底转入Quantinuum，但仍是阿姆斯特丹大学教授，因此其成果在历史归因与当前合作网络中分别处理。[2]

文献引用数尤其需要谨慎。Google Scholar、OpenAlex、Crossref、出版商页面、Scopus的覆盖范围不同，同一论文可能相差数十个百分点。因此下文均注明口径；**引用数用于识别数量级，不用于精确排位**。例如Childs等人的Trotter误差论文，OSTI显示971次，而Google Scholar作者页快照约1,099次，正体现数据库差异。[3]h指数同样采用“来源＋快照”的方式，而不是将不同数据库的数字直接混合；Google Scholar本身也说明其指标依赖索引快照。[4]

对未来潜力的评价采用七个维度：**数学原创性25%、理论到硬件闭环20%、近十年高影响成果15%、人才梯队10%、合作网络10%、资金可持续性10%、软件/产业转化10%**。其中“高/中/低”和A+/A/B均为本报告依据公开证据形成的分析判断，不是外部官方排名。对于纯理论中心，缺少自有硬件并不等价于科学潜力低；因此另行区分“理论杠杆”和“工程成熟度”。

工程成熟度采用本报告内部尺度：M1=理论/定理阶段，M2=算法或软件原型，M3=在量子硬件上验证关键逻辑操作，M4=多逻辑比特、重复纠错和可扩展工程路线均已有明确验证。当前没有任何团队可以无争议地被视为完成通用大规模容错量子计算的M4终态；这一判断也与Google、IBM和Quantinuum目前仍把逻辑扩展、低开销纠错和容错算法列为后续里程碑相一致。[5]

### 全球主要团队详细盘点

下表先集中比较“机构—数学方向—成果—人员”。引用数为接近2026年9月的可公开查询快照；无法可靠统一核验的明确标为“未统一核验”。

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| 团队 / 机构 | 国家 / 城市 | 核心数学与量子方向 | 近十年代表性论文及引用 | 主要研究人员与影响力 |
| **Caltech IQIM** | 美国，Pasadena | 量子信息、QEC、拓扑量子计算、张量网络/全息编码、随机测量、量子学习、数学物理 | Huang–Kueng–Preskill,*Predicting Many Properties of a Quantum System from Very Few Measurements*,**Nature Physics**, 2020：提出classical shadows，以对数级样本预测大量观测量；第三方文献库快照约779引，且该方法已形成独立研究方向。[6] | John Preskill长期聚焦QEC、量子计算和量子信息，并创立Caltech早期IQI；Google Scholar快照h≈92。IQIM的学术谱系还包括Alexei Kitaev等，Preskill页面统计其体系已有约85名前博士后成为教职。[7] |
| **QuICS / NSF RQS，University of Maryland** | 美国，College Park | 量子算法、Hamiltonian simulation、查询复杂性、量子游走、代数算法、复杂性理论、QEC | Childs et al.,*Theory of Trotter Error with Commutator Scaling*,**Physical Review X**, 2021：用嵌套交换子结构获得更紧的乘积公式误差界；OSTI约971引，GS作者页约1,099引。[8] | Andrew Childs研究量子算法、模拟、query complexity和代数问题；GS快照h≈63。QuICS还通过Daniel Gottesman、Alexey Gorshkov等连接QEC和量子多体理论。[9] |
| **MIT Quantum Information Science / MIT–IBM** | 美国，Cambridge | 量子算法、复杂性、表示论、优化、量子信息、多体理论、算法资源理论 | Peng–Harrow–Ozols–Wu,*Simulating Large Quantum Circuits on a Small Quantum Computer*,**PRL**, 2020：以张量网络式cluster decomposition换取较少量子比特；APS页面约478引。[10] | Aram Harrow关注算法、信息、复杂性、表示论与优化，GS h≈55；MIT QIS还包括Isaac Chuang、Peter Shor、Anand Natarajan、Soonwon Choi等。[11] |
| **Institute for Quantum Computing, Waterloo** | 加拿大，Waterloo | 量子复杂性、QEC、密码与格问题、量子通信、算子/信息理论、量子模拟 | Bravyi–Gosset–König,*Quantum advantage with shallow circuits*,**Science**, 2018：以二次型/非局域性给出常深度量子电路相对于经典模型的无条件优势；OpenAlex约424引。[12] | David Gosset、Michele Mosca、John Watrous、Debbie Leung等覆盖复杂性、密码、量子信息；Watrous在2022–2025年曾任IBM量子教育技术负责人，2026起承担IQC教育培训领导职务。[13] |
| **QuSoft / CWI–UvA** | 荷兰，Amsterdam | 复杂性理论、量子算法、量子密码、线性代数、谱变换、量子软件 | Gilyén–Su–Low–Wiebe,*Quantum Singular Value Transformation and Beyond*,**STOC**, 2019：以多项式逼近、block encoding和奇异值变换统一大量Hamiltonian simulation、线性代数和QML原语；引用数不同数据库差异较大，本报告不强行给单一数字。[14] | Harry Buhrman是创始负责人之一、复杂性理论专家，当前兼任UvA教授和Quantinuum算法首席科学家，GS h≈51；生态还包括Ronald de Wolf、Christian Schaffner、Stacey Jeffery等。[15] |
| **QMATH，University of Copenhagen** | 丹麦，Copenhagen | 数学物理、算子与矩阵分析、图论、量子群、张量、量子信息、量子学习 | Mančinska–Roberson,*Quantum isomorphism is equivalent to equality of homomorphism counts from planar graphs*,**FOCS**, 2020：把量子图同构与平面图同态计数、量子群联系起来；IEEE检索约133引。[16] | Matthias Christandl、Jan Philip Solovej、Laura Mančinska、Daniel Stilck França等；Mančinska GS h≈22；Solovej获Henri Poincaré Prize等数学物理荣誉。[17] |
| **ETH Zürich Quantum Information Theory** | 瑞士，Zürich | 熵理论、算子与信息不等式、量子密码、随机性、热力学、量子基础 | Dupuis–Fawzi–Renner,*Entropy Accumulation*,**Communications in Mathematical Physics**, 2020：把非独立序列的不确定性化为逐轮条件熵累积，是device-independent crypto等的重要数学工具；Springer约302引。[18] | Renato Renner领导量子信息理论方向；GS抓取h≈84，研究涵盖量子密码、量子热力学与基础。ETH还可与本校超导量子硬件团队形成理论—实验闭环。[19] |
| **Oxford Quantum Group** | 英国，Oxford | 范畴论、ZX-calculus、图论、形式化验证、编译优化、容错电路 | Duncan–Kissinger–Perdrix–van de Wetering,*Graph-theoretic Simplification of Quantum Circuits with the ZX-calculus*,**Quantum**, 2020：把local complementation/pivoting与ZX重写结合；Quantum/Crossref页面约401引。[20] | Aleks Kissinger现为Oxford量子计算教授和Quantum Group联合负责人，研究编译、容错、验证及图示语言；团队开发PyZX、QuiZX、Chyp等工具。[21] |
| **NUS Centre for Quantum Technologies** | 新加坡 | 非渐近信息论、Rényi熵、复杂性、量子密码、通信、算法、随机性 | Coles–Berta–Tomamichel–Wehner,*Entropic uncertainty relations and their applications*,**RMP**, 2017：系统化熵不确定关系及其密码/信息应用；GS快照约811引。[22] | Marco Tomamichel研究有限资源量子信息、熵和密码，GS/公开指标h≈51；Rahul Jain研究量子/经典信息、算法、复杂性与密码；CQT还包括Miklós Santha等理论PI。[23] |
| **USTC / CAS Quantum Information Division** | 中国，合肥 | 量子信息、光子抽样、量子模拟、QEC、量子网络、超导计算、复杂采样问题 | Zhong et al.,*Quantum computational advantage using photons*,**Science**, 2020：Jiuzhang高斯玻色采样实验达到76 photon-click等规模；OpenAlex快照约2,205引。[24] | 潘建伟为核心创建者，陆朝阳等在光量子计算与多光子干涉方面长期活跃；该部门覆盖自由空间/光纤通信、存储、中继、光学与超导计算、冷原子模拟等平台。[25] |
| **RIKEN Center for Quantum Computing / Theory & Mathematical QI** | 日本，和光/东京圈 | QEC、量子算法、量子软件、数学量子信息、资源理论、量子机器学习、量子模拟 | Fujii等团队谱系的量子reservoir computing及后续工作把动力系统、统计学习和量子多体演化结合；例如*Boosting Computational Power through Spatial Multiplexing in Quantum Reservoir Computing*,**PR Applied**, 2019；统一引用数未核验。[26] | Center Director Yasunobu Nakamura负责硬件体系；Keisuke Fujii领导Quantum Computing Theory Research Team；RIKEN另设Mathematical Quantum Information Hakubi方向研究量子资源的结构与量化。[27] |
| **IBM Quantum** | 美国，Yorktown Heights等 | QEC、qLDPC、代数编码、图嵌入/拓扑、解码算法、编译、量子模拟 | Bravyi et al.,*High-threshold and low-overhead fault-tolerant quantum memory*,**Nature**, 2024：构造bivariate bicycle qLDPC码；Nature截至抓取约573引。论文给出的示例中，物理错误率0.1%时288物理比特可保护12逻辑比特近百万syndrome cycles，而相近目标的surface code需逾3,000物理比特。[1] | Sergey Bravyi、Andrew Cross、Jay Gambetta、Dmitri Maslov、Theodore Yoder等形成“编码数学—decoder—超导连接图—芯片”协同团队。相关设计已有专利申请。[1] |
| **Google Quantum AI** | 美国，Santa Barbara / California | surface code、统计解码、随机过程、量子模拟、算法、校准优化 | Acharya et al.,*Quantum error correction below the surface code threshold*,**Nature**, 2025：distance-7、101物理比特逻辑memory约0.143%/cycle，并展示随码距增加逻辑错误下降；Nature页面抓取约1,094引。[28] | Google QAI覆盖芯片、校准、decoder、算法和应用；Willow为105-qubit处理器，实验实现d=3→5→7随码距增加的错误抑制。[29] |
| **Microsoft Quantum** | 美国Redmond等；与欧洲器件团队深度合作 | 拓扑量子计算、Majorana、凝聚态拓扑、QEC、逻辑量子比特软件 | *Interferometric single-shot parity measurement in InAs–Al hybrid devices*,**Nature**, 2025：单次fermion-parity测量；Nature约171引。2026年Nature刊发Matters Arising，对用于判定拓扑相的transport protocol稳健性提出挑战，因此“已实现拓扑量子比特”不能视为无争议事实。[30] | Krysta Svore、Chetan Nayak等覆盖QEC/软件和拓扑路线。Microsoft 2025推出Majorana 1并给出拓扑核路线图，但外界质疑意味着其科研上限极高、同时验证风险也在本报告样本中最高。[31] |
| **Quantinuum** | 美国Broomfield / 英国London、Cambridge等 | 离子阱QEC、非局域qLDPC、编译、复杂性、算法、量子软件、范畴方法 | Paetznick et al.,*Demonstration of logical qubits and repeated error correction with better-than-physical error rates*, arXiv, 2024：在H2上以[[7,1,3]]、[[12,2,4]]码实现逻辑错误低于物理基线及重复纠错；另有[[25,4,3]]非局域qLDPC四逻辑比特GHZ实验。引用数未统一核验。[32] | David Hayes、Russell Stutz等负责容错/硬件；Harry Buhrman于2023年底加入Quantinuum担任量子算法与创新首席科学家。公司2025年披露员工逾500人，其中约370名科学家和工程师。[2] |

第二张表补齐用户要求的**合作网络、资金、产业转化、硬/软件资源、影响力与未来潜力**。金额若属于国家生态而非单个团队，已明确区分，避免把“国家量子计划总额”误写为PI预算。

|  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| 团队 | 主要合作网络 | 资金来源与公开规模 | 工业合作 / 技术转化 | 软硬件资源 | 影响力与人才梯队 | 本报告未来判断 |
| **Caltech IQIM** | AWS Center for Quantum Computing与Caltech同园区；IQIM形成庞大的全球校友网络。[33] | NSF 2023续期：**$13.8M/6年**；2011创建期约$12.6M/5年，另有基金会支持。[33] | AWS量子中心提供从理论到器件/QEC的工业接口。[33] | 原子、超导、量子材料等Caltech实验资源＋AWS邻接资源。 | Preskill h≈92；约85名前postdoc成长为faculty，人才扩散力极强。[34] | **A+理论 / A综合**。最可能贡献新的QEC、学习/认证和数学物理框架。 |
| **QuICS / RQS** | RQS由UMD、Duke、NCSU、Princeton、Yale、NIST组成；2026续期加入Harvard，形成美国最密集的量子软件/算法联盟之一。[35] | 2021 NSF初始\*\*$25M\*\*；后有$2.5M补充；2026续期预计\*\*$37.5M/5年\*\*。[35] | 与NIST及科技企业合著；Trotter代表作即包含Google、PNNL等机构。[8] | 重点是理论与软件，通过UMD/NIST/JQI生态连接实验。 | Childs h≈63；RQS具有跨校稳定博士后和博士培养网络。[36] | **A+算法理论 / A综合**；资金续期显著降低未来五年的组织风险。 |
| **MIT QIS** | MIT–IBM Watson AI Lab是重要工业接口；MIT内部物理、CS、EECS高度交叉。[37] | 联邦项目＋MIT/IBM等；单一“量子理论组总预算”未公开。 | IBM硬件/算法协同是最直接转化链之一。[37] | IBM量子系统、MIT HPC及本校实验生态。 | Harrow h≈55；Shor、Chuang等形成跨代学术谱系。[38] | **A+理论 / A综合**。复杂性、算法和量子多体之间仍有极强原创空间。 |
| **Waterloo IQC** | 加拿大政府、CSA、NRC、Calgary、Ciena、RBC、TELUS、Entrust等。[39] | IQC披露最近一个财年获得\*\*&gt;$25M**资金，过去五年**&gt;$150M\*\*；另有联邦SSF**$18.4M/5年**；QUINT项目$5M、抗量子密码项目$4.1M。[40] | 抗量子密码、量子通信、初创生态明显；2024年度回顾称活跃初创企业达23家。[40] | 自建通信、光子、离子阱等设施；Waterloo离子组2024已在Bloodstone系统捕获25个Yb离子。[41] | 截至2024，IQC支持成果累计\*\*&gt;3,000篇论文、&gt;100,000次引用\*\*；同期53名postdoc。[40] | **A**。优势是“数学理论＋密码＋通信＋实验＋创业”均衡，而非单点押注。 |
| **QuSoft** | CWI/UvA；历史上与Google、Microsoft、ID Quantique等合作；Buhrman转入Quantinuum后形成更直接产业通道。[42] | CWI/UvA结构性支持；Quantum Delta NL获国家增长基金\*\*€615M\*\*，后续阶段另有约\*\*€228M\*\*，但这是荷兰国家生态预算，**不能等同于QuSoft预算**。[43] | 算法、密码与软件转化极强；Quantinuum形成明显人才与理论迁移。 | 主要为软件/理论，通过荷兰量子生态和企业访问硬件。 | 2015成立时规划35–40人，2021报道约70名研究人员；Buhrman h≈51。[15] | **A+算法数学 / A综合**。QSVT式“统一算法框架”是最值得关注的高杠杆类型。 |
| **QMATH** | 与Niels Bohr Institute实验组、ETH Zürich、Microsoft Research建立明确合作；Christandl 2024又任QuSoft Turing Chair。[44] | VILLUM最初**DKK30M**；2025 Solovej获新的**DKK30M、2026–2031**投资；另有ERC、VILLUM Young Investigator等项目。[17] | 产业合作中等，但与Microsoft、QuSoft和丹麦国家量子生态接口明确。 | 以理论为主，借NBI/NQCP等实验生态完成验证。 | 当前约**16名PhD、19名postdoc**；人才密度在纯数学量子中心中突出。[17] | **A+数学 / A-综合**。最可能贡献结构性定理，而非首先交付硬件。 |
| **ETH QIT** | 与全球量子密码/信息团队长期共著；本校与超导量子器件组可直接合作。[19] | ETH、SNSF、ERC等；Entropy Accumulation论文即列出SNSF/ERC支持；组级年度规模未公开。[18] | 密码安全证明、随机性认证等具有标准/协议转化价值。 | 理论计算资源＋ETH超导器件接口。 | Renner GS h≈84；熵理论工具已被大量后续密码/随机性工作采用。[45] | **A+数学信息论 / A-综合**。未来突破更可能表现为“证明技术改变安全边界”。 |
| **Oxford Quantum Group** | Quantinuum及欧洲量子软件网络联系密切。[21] | UKRI/EPSRC、大学和产业项目；团队总规模未公开。 | **PyZX**等已把图论/ZX-calculus直接变成电路优化工具；学生与研究者持续流向CQC/Quantinuum。[21] | PyZX、QuiZX、Chyp，偏软件/形式化而非自有通用硬件。 | 代表性ZX论文Crossref约401引；社区软件效应强。[46] | **A+形式方法 / A-综合**。容错编译越复杂，其数学工具价值越上升。 |
| **NUS CQT** | NUS、A\*STAR及全球ETH/Delft/Cornell等信息论网络。Tomamichel公开合作网络覆盖Renner、Wehner、Wilde、Winter等。[47] | 2021 NUS称CQT外部资助项目累计\*\*&gt;S$40M\*\*；新加坡RIE2025为国家量子研究预留**S$295M**，但不是全部给CQT。[48] | 密码、通信、量子处理器与国家量子安全/工程计划接口强。 | CQT有通信、处理器、模拟等实验方向，并由国家量子战略提供更广平台。[49] | 2021已约2,000篇成果、训练逾60名PhD；Tomamichel h≈51。[48] | **A**。非渐近信息论和密码数学在全球具有稳定长期价值。 |
| **USTC/CAS** | 中国科学院及国内量子科技体系；论文层面保持广泛国际可见度。 | 国家/CAS/NSFC等多源支持，团队总体规模未公开；不以未经核实的项目总盘子替代团队预算。 | 光量子计算、超导处理器、量子通信形成较完整技术链。[50] | 自有光子、超导、冷原子、量子网络平台。[50] | Jiuzhang 2020论文OpenAlex约2,205引，是样本中近期实验论文影响力最高之一。[51] | **A+实验优势 / A综合**。数学突破更集中在采样复杂性、验证和纠错接口。 |
| **RIKEN RQC** | 与Fujitsu、Osaka等共同开展量子计算研究。[52] | RIKEN机构支持；具体Theory/Math QI团队年度金额未公开。 | RIKEN–Fujitsu联合研发具有直接工程转化通道。[52] | RIKEN称已开发/拥有日本国产超导量子计算机，并建设通用光量子计算平台。[27] | 同一中心并列Theory Research Team与Mathematical Quantum Information团队，利于理论—硬件共址。[53] | **A**。日本最值得关注的异构硬件＋理论协同中心之一。 |
| **IBM Quantum** | MIT、Rutgers、DOE C2QA等；qLDPC工作横跨数学编码和硬件布局。[54] | 企业R&D预算未按IBM Quantum数学团队拆分公开；部分研究获DOE C2QA等支持。[54] | qLDPC已有专利布局；代码、decoder、芯片连接架构与产品路线直接绑定。[1] | IBM超导处理器、HPC、实时decoder及完整软件栈；路线图以2029大规模FTQC为目标。[55] | 2024 qLDPC Nature论文约573引，且直接提出可验证的物理开销优势。[1] | **A+**。当前“数学纠错理论转成硬件架构”最完整的样本之一。 |
| **Google Quantum AI** | Google内部硬件、算法、控制与解码高度一体化。 | 企业内部预算未按团队公开。 | Willow、surface-code decoder和算法研发处于同一产品化体系。[29] | 自研105-qubit Willow及Santa Barbara fabrication能力。[29] | 2025 Nature QEC论文约1,094引；已实验证明码距增加时logical error下降。[28] | **A+**。近期证据最强；关键未知是从单/少数logical memory扩展到算法级多逻辑比特。 |
| **Microsoft Quantum** | 与Quantinuum的逻辑量子比特合作、与半导体/超导实验团队合作。[32] | 企业预算未拆分公开；Majorana计划进入DARPA US2QC相关阶段。[31] | Azure Quantum提供软件/云入口；若拓扑路线成立，硬件转化价值极高。 | Majorana器件、Azure逻辑/QEC软件；拓扑物理状态尚存在公开学术争议。[56] | Nature 2025 parity论文171引；但2026 Matters Arising显著提高证据门槛。[30] | **A\***高风险高回报。不能用普通A+/A排序理解：上行潜力极大，置信度明显较低。 |
| **Quantinuum** | Microsoft、QuSoft/Amsterdam、Oxford及大学理论团队。[57] | 企业内部预算未公开；2025披露员工规模&gt;500人。[58] | H系列离子阱硬件＋TKET/Nexus/Guppy等软件栈＋QEC实验形成强转化闭环。[58] | H2/后续离子阱系统具有灵活连通性、mid-circuit measurement等QEC关键能力。[32] | 已展示better-than-physical逻辑操作、重复QEC及非局域qLDPC实验。[32] | **A+**。在“高保真硬件利用复杂数学编码”这一赛道尤其突出。 |

从团队结构看，有三种明显模式。第一种是\*\*“数学理论—自有硬件闭环”**，代表为IBM、Google和Quantinuum；第二种是**“理论中心—跨机构硬件接口”**，代表为Caltech、QuICS、MIT、QuSoft、ETH和Oxford；第三种是**“国家级综合量子中心”\*\*，如Waterloo、CQT、USTC和RIKEN。QMATH则是少见的“以纯数学/数学物理为组织核心、向量子计算外溢”的中心。上述差异意味着单纯用论文数给团队排总榜并不科学。[40]

### 横向比较、分级与合作网络

以下“高/中”是相对于本报告所选全球头部样本，而不是与整个学术界相比。因此“中”仍可能代表世界一流，只是该维度不是该团队最强项。

|  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 团队 | 数学理论深度 | 近十年高影响产出 | 国际/跨机构合作 | 资金可持续性 | 工业合作与转化 | 软硬件闭环 | 五至十年综合潜力 |
| IBM Quantum | 高 | 高 | 高 | 高 | **极高** | **极高** | **A+** |
| Google Quantum AI | 高 | **极高** | 高 | 高 | **极高** | **极高** | **A+** |
| Quantinuum | 高 | 高 | **极高** | 高 | **极高** | **极高** | **A+** |
| Caltech IQIM | **极高** | **极高** | **极高** | 高 | 高 | 高 | **A+/A** |
| QuICS / RQS | **极高** | **极高** | 高 | **极高** | 中高 | 中 | **A** |
| MIT QIS | **极高** | **极高** | 高 | 高 | **极高** | 高 | **A** |
| QuSoft | **极高** | **极高** | **极高** | 高 | 高 | 中 | **A** |
| Waterloo IQC | 高 | 高 | **极高** | **极高** | **极高** | 高 | **A** |
| QMATH | **极高** | 高 | **极高** | 高 | 中 | 中 | **A（理论）** |
| ETH QIT | **极高** | 高 | **极高** | 高 | 中 | 中高 | **A（理论）** |
| Oxford Quantum Group | **极高** | 高 | 高 | 中高 | 高 | 中 | **A-/A** |
| NUS CQT | **极高** | 高 | **极高** | 高 | 中高 | 高 | **A** |
| USTC/CAS | 中高 | **极高** | 高 | 高\* | 中高 | **极高** | **A** |
| RIKEN RQC | 高 | 高 | 高 | 高\* | 高 | **极高** | **A** |
| Microsoft Quantum | **极高** | 高 | **极高** | 高 | **极高** | 中：路线待验证 | **A\*，高方差** |

\* USTC和RIKEN公开材料能确认持续的国家/机构级支持和大型平台，但并没有可与美国NSF中心预算直接比较的统一“团队年度金额”，因此资金等级反映可持续制度基础，而非声称已知精确金额。[50]

若按**研究方向而非机构总实力**排序，结构更加清楚：

|  |  |  |  |
| --- | --- | --- | --- |
| 方向 | 第一梯队 | 第二梯队 / 强项互补 | 判断依据 |
| **量子纠错数学、qLDPC与decoder** | IBM、Google、Quantinuum | Caltech、QuICS、Microsoft | IBM已经把qLDPC的代数/图结构转成具体连接图；Google有below-threshold surface-code实验；Quantinuum已实验非局域qLDPC与better-than-physical QEC。[1] |
| **量子算法与复杂性** | QuICS、QuSoft、MIT | Caltech、NUS、Quantinuum | Trotter理论、QSVT、复杂性/表示论分别代表三个高杠杆方向。[8] |
| **数学量子信息/熵/算子结构** | ETH、QMATH、NUS | Caltech、Waterloo | Entropy accumulation、量子图同构、Rényi/有限资源信息论具有明显数学核心。[59] |
| **图论、范畴论与形式化编译** | Oxford | QuSoft、QMATH | ZX-calculus已由抽象diagrammatic calculus发展成实际电路优化软件。[21] |
| **量子模拟数学** | QuICS、MIT | RIKEN、USTC、Caltech | Hamiltonian simulation的误差界、谱方法、张量网络和实际模拟平台高度互补。[8] |
| **可验证量子优势** | Google、USTC、Quantinuum | IBM、Waterloo | Google/USTC的实验优势证据与Quantinuum逻辑QEC分别对应随机线路/采样与可靠逻辑计算两类路线。[60] |
| **拓扑量子计算** | Microsoft（高不确定性）、Caltech | QMATH、其他数学物理团队 | 理论价值很高，但Microsoft实验解释在2026年仍有实质争议。[56] |

一个重要结论是：**未来重大突破越来越不可能只来自“纯硬件堆qubit”，也不太可能只来自孤立数学定理，而更可能发生在数学结构显著改变工程缩放律的地方。**IBM 2024 qLDPC论文就是典型案例：编码理论、有限群/循环结构、Tanner图和图的厚度直接决定连接布局和物理比特开销。Google的surface-code结果则把统计解码和阈值理论变成实际逻辑错误曲线。Quantinuum利用离子阱的长程连通性，使原本在二维局域硬件上昂贵的非局域码变得可实验。[1]

公开资料中可以较明确确认的主要合作关系如下。为可读性，图中只放“对研究路线有实质作用”的边，而不是所有论文共著关系。Caltech–AWS、MIT–IBM、RQS联盟、Waterloo产业联盟、QMATH–ETH/Microsoft、RIKEN–Fujitsu、Microsoft–Quantinuum等均有机构来源支持。[61]

Caltech IQIM

AWS Quantum

MIT QIS

IBM Quantum

QuICS / UMD

NSF RQS

NIST

Duke

Princeton

Yale

Harvard

Waterloo IQC

Ciena / CSA / NRC

RBC / TELUS / Entrust

QuSoft

Quantum Delta NL

Quantinuum

QMATH Copenhagen

ETH Zürich

Microsoft

Oxford Quantum Group

NUS CQT

A\*STAR / Singapore NQS

RIKEN RQC

Fujitsu

Osaka University

Rutgers / DOE C2QA

该图也揭示了一个值得关注的“**人才—数学工具迁移网络**”：Buhrman由QuSoft转向Quantinuum，Christandl由QMATH担任QuSoft Turing Chair，Oxford/CQC传统与Quantinuum软件栈相连，Watrous曾在IBM负责量子教育后回到Waterloo。这意味着未来理论突破的扩散速度可能比传统“大学论文→几年后企业采用”的模式快得多。[2]

### 未来五至十年的突破评估与关键数学预测

综合证据后，本报告认为最值得区分的是“**高概率平台突破**”和“**高杠杆理论突破**”。

在平台级突破上，**IBM、Google和Quantinuum处于第一组**，但理由不同。IBM的优势是qLDPC码已被具体化为数百物理比特量级、有限度连接的硬件问题，其Nature论文甚至明确列出第二层互连、长程coupler等工程障碍，因此未来进度可以被逐项验证，而不是只看远期路线图。[1]Google的优势是已经跨过surface-code below-threshold的重要实验门槛，接下来的关键问题从“逻辑误差能否随码距降低”转成“能否同时维持多个逻辑比特、逻辑门、magic-state等操作”。[29]Quantinuum的优势则是高保真离子阱、灵活连通性与QEC软件共同存在，使非局域高率码能比二维超导硬件更早接受实验检验。[32]

在理论级突破上，**QuICS/RQS、QuSoft、Caltech和MIT**是本报告置信度最高的四个节点。原因不是单纯的历史声誉，而是近十年的代表作恰好击中了未来容错计算最昂贵的几个数学瓶颈：Hamiltonian simulation误差边界、QSVT/多项式逼近、随机测量/学习、复杂性与资源论。一个定理如果能把门深从多项式中的高次幂降为近线性、把查询复杂度降一个数量级，或者把样本量从系统维度依赖变为对数依赖，其工程效果可能等价于数年的硬件改进。[8]

**QMATH、ETH、Oxford和NUS**更像“基础设施数学”团队：它们未必首先宣布“100个逻辑qubit”，但可能改变什么能够被证明、验证、编译或安全使用。Entropy accumulation已经证明这类工作的路径：一个信息论定理可以成为设备无关密码分析的通用工具；ZX-calculus则说明范畴/图示语言能够从抽象数学进入量子编译器。[59]

**Microsoft需要单列。**若可扩展、具有真正拓扑保护的Majorana qubit得到独立且重复的实验确认，拓扑编码将改变量子纠错的基础资源结构，Microsoft因此具有样本中最大的“上行尾部”。但截至2026年6月，Nature已正式发表针对其topological-gap判定协议稳健性的Matters Arising；所以在本报告基准情景下，它不是“最高概率第一名”，而是**最高收益、最高模型风险路线**。[56]

未来最值得追踪的数学—技术链如下。时间窗口是基于当前公开进展的情景估计，不是统计置信区间。

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| 关键问题 | 数学工具 | 逻辑链：问题 → 数学 → 技术影响 | 估计窗口 | 可观察里程碑 | 最相关团队 |
| **QEC物理比特开销过高** | qLDPC、有限群/群代数、expander、Tanner图、同调/拓扑编码、组合优化 | surface code编码率低 → 构造高率高距稀疏码并找到低深度syndrome circuit → 每逻辑比特物理开销下降一个量级 → 大规模FTQC成本曲线改变 | **2026–2031** | 数十至上百逻辑比特的qLDPC重复纠错；无重度postselection；实时decoder跟上syndrome速率 | IBM、Quantinuum、Caltech、QuICS |
| **逻辑算法门数仍过大** | QSVT/QSP、多项式/有理逼近、block encoding、谱理论、数值线性代数 | 算法主要成本来自函数/矩阵变换 → 用近最优多项式实现谱函数 → 减少T/Toffoli及查询次数 → 使化学、材料、线性代数第一次进入可承受logical budget | **2026–2033** | 在完整FT resource estimate中，QSVT类算法相对传统phase-estimation/Trotter路线出现持续数量级优势 | QuSoft、QuICS、MIT、Quantinuum |
| **量子模拟误差界过松** | Lie algebra、交换子展开、算子范数、Lieb–Robinson bounds、随机化、谱分析 | 最坏情形界远高于实际误差 → 利用局域性/交换结构给出紧界 → 减少Trotter steps及逻辑门 → 模拟成为早期FT应用 | **2026–2031** | 误差证明与真实器件误差在常数因子内吻合；资源估计不再被过松理论界支配 | QuICS、MIT、IBM |
| **大型量子系统无法完全表征** | classical shadows、浓缩不等式、随机矩阵、压缩感知、学习理论 | tomography指数增长 → 随机测量构造低维“影子” → 少量样本同时估计大量性质 → 校准、验证、VQE/QML实验显著降本 | **2026–2030** | 100–1000+ qubit体系上常规使用shadow类认证；与QEC syndrome/噪声学习融合 | Caltech、QMATH、Google |
| **容错电路过于复杂，人工优化失效** | ZX-calculus、范畴论、图重写、形式验证、SAT/SMT/组合优化 | millions/billions gates难人工推理 → 将电路化为可证明等价的图/diagram → 自动消除门、优化T-depth/布局 → compiler成为“数学定理执行器” | **2026–2032** | ZX/形式化IR进入主流FT compiler；优化结果附机器可验证等价证明 | Oxford、Quantinuum、QuSoft |
| **解码延迟成为QEC瓶颈** | 图算法、统计推断、概率模型、张量网络、机器学习、在线算法 | syndrome持续高速产生 → decoder必须低延迟估计最可能错误 → 数学/硬件协同decoder → 更高码距不被经典控制端拖垮 | **2026–2030** | decoder latency稳定低于syndrome周期；logical error改善可随distance持续扩展 | Google、IBM、Quantinuum |
| **非局域纠错码难映射到实际芯片** | 图嵌入、graph thickness、拓扑布局、网络流、调度优化 | 好码需要非局域连接 → 分解Tanner graph、加入少量长程coupler或利用离子全连接 → 保留高编码率 → qLDPC从纸上进入芯片 | **2026–2032** | IBM式双层连接或其他高率码布局在百至千物理qubit芯片实测 | IBM、Quantinuum、RIKEN |
| **拓扑qubit是否真能天然压低误差** | 拓扑不变量、braid/anyon理论、BdG谱理论、K-theory式分类、统计假设检验 | ordinary qubit需重QEC → 若非阿贝尔零模可非局域编码 → hardware-level保护减少active QEC → 架构发生根本变化 | **2028–2036+，高不确定** | 独立重复的拓扑gap/融合/braiding证据；logical operation展示随器件尺度增强的拓扑保护 | Microsoft、Caltech及凝聚态数学物理团队 |
| **量子优势难与经典算法进步区分** | 复杂性理论、通信复杂性、非局域游戏、随机线路理论、平均情形复杂性 | “经典目前跑不动”不等于严格优势 → 建立可证明分离或更稳健复杂性假设 → 设计更难被dequantization追上的任务 | **持续至2035+** | 从采样优势转向有验证器、具有应用语义的复杂性分离 | QuICS、QuSoft、MIT、Waterloo、USTC |

其中最值得强调的是第一项。IBM的2024结果显示，qLDPC不是只有渐近意义：在其模型中，[[144,12,12]]一类bivariate bicycle code已把编码率和阈值推到可能影响实际几百qubit设备的区域。与此同时，论文也清楚表明“数学上更好的码”会把问题转移到长程coupler、二维不可局域嵌入和decoder，因此**未来真正的突破标准不是出现更漂亮的码参数，而是码、连接图、syndrome circuit、decoder和芯片同时满足约束**。[1]

QSVT则代表第二种高杠杆路径。其价值并不只是一个新算法，而是把Hamiltonian simulation、矩阵逆、谱过滤、主成分问题等都归入“对block-encoded矩阵奇异值施加多项式变换”的统一语言。未来如果FTQC变得可用，这种框架很可能扮演类似经典数值计算中“线性代数基础库”的角色；但它的实际价值仍取决于state preparation、oracle构造和fault-tolerant gate成本，不能仅凭渐近复杂度宣称应用优势。[14]

本报告的基准情景下，未来5–10年“重大突破概率”的粗分组因此是：

**最高置信平台组：IBM、Google、Quantinuum。**三者都已有同行评议或可复现实验数据，把QEC从“物理比特更可靠”推进到“逻辑层真正获得收益”的方向。[1]

**最高置信理论组：QuICS/RQS、QuSoft、Caltech、MIT。**它们的优势是数学工具具有跨硬件平台复用性，一次理论突破可能同时影响超导、离子阱和光量子路线。[62]

**基础数学高杠杆组：QMATH、ETH、Oxford、NUS。**最可能的重大贡献是熵、图、算子、范畴、学习/验证等底层理论，而不是独立完成通用FTQC。[63]

**硬件—算法综合追赶/差异化组：USTC、RIKEN、Waterloo。**USTC具有光量子优势实验和多硬件平台，RIKEN把数学/理论团队与国产超导和光量子平台共址，Waterloo则兼具理论、通信、离子阱和商业化生态。[50]

**高方差路线：Microsoft。**成功时可能改变整个QEC成本模型；若拓扑证据不能经独立重复，则其长期优势将更多依赖Azure软件/QEC而非Majorana硬件。[56]

主要不确定性有四类。首先是**相关噪声**：很多阈值和decoder分析以近似局域或特定统计噪声模型为基础，实际器件中的泄漏、串扰、宇宙射线等可能改变缩放。IBM论文自己即把硬件连接和器件损耗列为核心障碍。[1]其次是**经典算法反攻**，量子优势实验经常会刺激更快的经典模拟，因此抽样难度的当前差距并不是永久常数。第三是**decoder和控制系统**，真正的FTQC需要经典反馈速度与qubit数量同步扩展。第四是**资本与供应链**：企业路线图属于计划而非定理，IBM的2029目标、Microsoft的拓扑路线均应被视为可验证假设，而非保证。[55]

### 数据可视化与主要参考来源

公开数据库并不存在一个完全统一、可直接比较这15个团队“每年论文数＋每年新增引用数”的权威接口，而且机构边界变化会造成严重归属误差。因此，为避免伪造精确性，下图采用一个**严格可追溯的代表作样本**：每个团队选取上表所述代表性论文，按发表年份统计“样本论文数”；引用图只计有明确公开数字的论文。它回答的是“这些头部代表成果在何时集中出现、当前累积影响多大”，**不是各机构全部bibliometric产出的替代品**。

代表作样本的发表年份分布为：2017年NUS一篇；2018年Waterloo一篇；2019年QuSoft与RIKEN谱系两篇；2020年Caltech、MIT、Oxford、QMATH、ETH、USTC六篇；2021年QuICS一篇；2024年IBM、Quantinuum两篇；2025年Google、Microsoft两篇。相应论文信息来自原始论文/出版页面。[22]

代表作样本：按发表年份统计的论文数量

2017

2018

2019

2020

2021

2022

2023

2024

2025

6

5.5

5

4.5

4

3.5

3

2.5

2

1.5

1

0.5

0

样本论文数

对具有公开且相对明确引用数字的子样本，截至接近2026年9月的累计引用为：2017年NUS代表作约811；2018年Waterloo约424；2020年六篇合计约4,298，其中USTC约2,205、Caltech约779、MIT约478、Oxford约401、ETH约302、QMATH约133；2021年QuICS论文用较保守的OSTI口径约971；2024年此图只计IBM的573，因Quantinuum代表预印本未取得同口径数字；2025年Google约1,094＋Microsoft约171=1,265。由于来源口径不同，这些数字应解释为“引用影响量级”，而不是精确加总的科学计量指标。[64]

可核验代表作子样本：截至2026年9月累计引用量，按发表年份

2017

2018

2020

2021

2024

2025

4500

4000

3500

3000

2500

2000

1500

1000

500

0

累计引用数（近似）

该图最值得注意的不是2020年的峰值本身，而是峰值来自**不同数学范式同时成熟**：classical shadows对应概率/学习理论，量子图同构对应图论/量子群，entropy accumulation对应熵与算子不等式，ZX对应图重写/范畴方法，MIT工作使用张量网络式电路分解，USTC则把复杂采样理论落实到光子实验。换言之，数学—量子计算交叉并没有收敛到一个单一数学分支，而是在多个数学语言之间形成“工具生态”。[6]

主要原始与机构来源如下，优先列出能直接支持本报告核心判断的材料：

|  |  |
| --- | --- |
| 来源类别 | 主要来源及用途 |
| Caltech / IQIM | IQIM与John Preskill官方资料用于研究方向、人才谱系；Caltech 2023公告用于NSF**$13.8M/6年**续期及AWS合作。[7] |
| UMD / QuICS / RQS | Andrew Childs官方页面用于算法方向；NSF RQS相关机构公告用于2021**$25M**启动及2026预计\*\*$37.5M/5年\*\*续期。[65] |
| Waterloo IQC | IQC年度回顾用于五年\*\*&gt;$150M\*\*资金、论文/引用、人才及创业指标；NSERC Alliance资料用于QUINT和抗量子密码产业合作。[40] |
| QuSoft / CWI | CWI 2015成立公告和后续资料用于中心规模、方向、企业合作及Buhrman迁移；QSVT采用CWI论文库及arXiv。[15] |
| QMATH / Copenhagen | QMATH官方About、Collaboration和News用于DKK资金、当前PhD/postdoc规模及ETH/Microsoft合作。[17] |
| ETH Zürich | ETH Research Collection及CMP原始论文用于Entropy Accumulation内容、基金和发表信息；Renner GS页面用于h指数快照。[18] |
| Oxford | Oxford官方Kissinger/Quantum Group资料用于研究方向、软件和Quantinuum联系；Quantum原始论文页用于ZX代表作和引用。[21] |
| NUS / Singapore NRF | CQT官方组页和PI资料用于研究方向；NUS/NRF用于CQT历史产出、外部资助和国家量子战略资金背景。[49] |
| USTC / CAS | USTC官方量子信息部门与潘建伟页面用于平台/人员；Science/arXiv和OpenAlex用于Jiuzhang论文及引用。[50] |
| RIKEN | RIKEN RQC、Theory Research Team、Mathematical QI和RIKEN–Fujitsu官方资料用于团队、硬件与合作。[27] |
| IBM Quantum | Nature 2024 qLDPC原始论文是本报告判断低开销纠错的重要依据；IBM路线图用于2026–2029工程目标。[1] |
| Google Quantum AI | Google Research/Quantum AI和Nature 2025论文用于Willow、surface-code below-threshold和logical-error数据。[29] |
| Microsoft Quantum | Microsoft Majorana 1资料、Nature 2025原始实验及Nature 2026 Matters Arising共同使用，避免只采用企业宣称。[31] |
| Quantinuum | 逻辑QEC及非局域qLDPC实验、Quantinuum软件栈/人员资料用于判断其QEC—硬件闭环。[32] |

整体上，**全球数学与量子计算的竞争中心正在从“谁提出了更多量子算法”转向“谁能找到改变资源缩放律的数学结构，并把它放进真实逻辑量子计算栈”**。过去十年的classical shadows、QSVT、entropy accumulation、ZX-calculus以及近年的qLDPC都符合这一模式：它们的共同特征不是单个benchmark变好，而是提供了一个可被其他团队反复复用的数学抽象。[6]在这一标准下，未来5–10年最值得持续跟踪的并非某一个“qubit数冠军”，而是**IBM/Google/Quantinuum的纠错闭环、QuICS/QuSoft/Caltech/MIT的算法与复杂性突破，以及QMATH/ETH/Oxford/NUS对证明、验证、编译和安全边界的重新定义**。

## 引用资料与扫描来源（保留原分组）

Citations · 65

[nature.com nature.com](https://www.nature.com/articles/s41586-024-07107-7)  

**1** <https://www.nature.com/articles/s41586-024-07107-7>

**30** <https://www.nature.com/articles/s41586-024-08445-2>

**56** <https://www.nature.com/articles/s41586-026-10567-8>

[cwi.nl cwi.nl](https://www.cwi.nl/en/news/famous-quantum-researcher-harry-buhrman-takes-on-new-position-in-londons-business-community/?utm_source=chatgpt.com)  

**2** [World-renowned quantum researcher Harry Buhrman takes on new ...](https://www.cwi.nl/en/news/famous-quantum-researcher-harry-buhrman-takes-on-new-position-in-londons-business-community/?utm_source=chatgpt.com)

**15** [QuSoft research center for quantum software launched](https://www.cwi.nl/en/news/qusoft-research-center-quantum-software-launch/?utm_source=chatgpt.com)

**42** [QuSoft research center for quantum software launched](https://www.cwi.nl/en/news/qusoft-research-center-quantum-software-launch/?utm_source=chatgpt.com)

[osti.gov osti.gov](https://www.osti.gov/biblio/1769799)  

**3** <https://www.osti.gov/biblio/1769799>

[scholar.google.com.sg scholar.google.com.sg](https://scholar.google.com.sg/intl/en/scholar/metrics.html)  

**4** <https://scholar.google.com.sg/intl/en/scholar/metrics.html>

[blog.google blog.google](https://blog.google/innovation-and-ai/technology/research/google-willow-quantum-chip/?utm_source=chatgpt.com)  

**5** [Meet Willow, our state-of-the-art quantum chip](https://blog.google/innovation-and-ai/technology/research/google-willow-quantum-chip/?utm_source=chatgpt.com)

[arxiv.org arxiv.org](https://arxiv.org/abs/2002.08953)  

**6** <https://arxiv.org/abs/2002.08953>

**10** <https://arxiv.org/abs/1904.00102>

**16** <https://arxiv.org/abs/1910.06958>

**20** <https://arxiv.org/abs/1902.03178>

**24** [Quantum computational advantage using photons](https://arxiv.org/abs/2012.01625?utm_source=chatgpt.com)

**60** [Quantum computational advantage using photons](https://arxiv.org/abs/2012.01625?utm_source=chatgpt.com)

[iqim.caltech.edu iqim.caltech.edu](https://iqim.caltech.edu/profile/john-preskill/?utm_source=chatgpt.com)  

**7** [John Preskill – IQIM](https://iqim.caltech.edu/profile/john-preskill/?utm_source=chatgpt.com)

[doi.org doi.org](https://doi.org/10.1103%2FPhysRevX.11.011020)  

**8** <https://doi.org/10.1103%2FPhysRevX.11.011020>

**62** <https://doi.org/10.1103%2FPhysRevX.11.011020>

**28** [Quantum error correction below the surface code threshold | Nature](https://doi.org/10.1038/s41586-024-08449-y?utm_source=chatgpt.com)

[quics.umd.edu quics.umd.edu](https://www.quics.umd.edu/people/andrew-childs?utm_source=chatgpt.com)  

**9** [Andrew Childs | Joint Center for Quantum Information and Computer Science (QuICS)](https://www.quics.umd.edu/people/andrew-childs?utm_source=chatgpt.com)

**65** [Andrew Childs | Joint Center for Quantum Information and Computer Science (QuICS)](https://www.quics.umd.edu/people/andrew-childs?utm_source=chatgpt.com)

[physics.mit.edu physics.mit.edu](https://physics.mit.edu/research-areas/quantum-information-science/?utm_source=chatgpt.com)  

**11** [Quantum Information Science - MIT Physics](https://physics.mit.edu/research-areas/quantum-information-science/?utm_source=chatgpt.com)

[openalex.org openalex.org](https://openalex.org/W2604467189)  

**12** <https://openalex.org/W2604467189>

[uwaterloo.ca uwaterloo.ca](https://uwaterloo.ca/institute-for-quantum-computing/profiles/john-watrous?utm_source=chatgpt.com)  

**13** [John Watrous | Institute for Quantum Computing | University of Waterloo](https://uwaterloo.ca/institute-for-quantum-computing/profiles/john-watrous?utm_source=chatgpt.com)

**39** <https://uwaterloo.ca/institute-for-quantum-computing/news/iqc-members-awarded-millions-nserc-quantum-alliance-funding>

**40** <https://uwaterloo.ca/institute-for-quantum-computing/news/2024-year-in-review>

[ir.cwi.nl ir.cwi.nl](https://ir.cwi.nl/pub/28780/)  

**14** <https://ir.cwi.nl/pub/28780/>

[qmath.ku.dk qmath.ku.dk](https://qmath.ku.dk/about/)  

**17** <https://qmath.ku.dk/about/>

**44** <https://qmath.ku.dk/about/collaboration/>

**63** <https://qmath.ku.dk/>

[research-collection.ethz.ch research-collection.ethz.ch](https://www.research-collection.ethz.ch/items/31ab361d-11ce-466b-aa35-86702fff0753)  

**18** <https://www.research-collection.ethz.ch/items/31ab361d-11ce-466b-aa35-86702fff0753>

[qit.ethz.ch qit.ethz.ch](https://qit.ethz.ch/?utm_source=chatgpt.com)  

**19** [Homepage – Quantum Information Theory | ETH Zurich](https://qit.ethz.ch/?utm_source=chatgpt.com)

[cs.ox.ac.uk cs.ox.ac.uk](https://www.cs.ox.ac.uk/people/aleks.kissinger/?utm_source=chatgpt.com)  

**21** [Aleks Kissinger | Department of Computer Science](https://www.cs.ox.ac.uk/people/aleks.kissinger/?utm_source=chatgpt.com)

[scholar.google.com scholar.google.com](https://scholar.google.com/citations?hl=en&user=PlDS_zYAAAAJ)  

**22** <https://scholar.google.com/citations?hl=en&user=PlDS_zYAAAAJ>

**64** <https://scholar.google.com/citations?hl=en&user=PlDS_zYAAAAJ>

**36** <https://scholar.google.com/citations?hl=en&user=7MOW-j4AAAAJ>

**38** <https://scholar.google.com/citations?hl=en&user=6WYsaqMAAAAJ>

**45** <https://scholar.google.com/citations?hl=en&user=OEBtlWgAAAAJ>

[cqt.sg cqt.sg](https://www.cqt.sg/groups/marco-tomamichel/)  

**23** <https://www.cqt.sg/groups/marco-tomamichel/>

**49** <https://www.cqt.sg/research-groups/>

[quantum.ustc.edu.cn quantum.ustc.edu.cn](https://quantum.ustc.edu.cn/web/en/node/32?utm_source=chatgpt.com)  

**25** [Jian-Wei Pan | Division of Quantum Physics and Quantum Information](https://quantum.ustc.edu.cn/web/en/node/32?utm_source=chatgpt.com)

**50** [首页 | Division of Quantum Physics and Quantum Information](https://quantum.ustc.edu.cn/web/en?utm_source=chatgpt.com)

[journals.aps.org journals.aps.org](https://journals.aps.org/prapplied/abstract/10.1103/PhysRevApplied.11.034021)  

**26** <https://journals.aps.org/prapplied/abstract/10.1103/PhysRevApplied.11.034021>

[riken.jp riken.jp](https://www.riken.jp/en/research/labs/rqc/)  

**27** <https://www.riken.jp/en/research/labs/rqc/>

**53** <https://www.riken.jp/en/research/labs/rqc/qtm_comput_theor/index.html>

[research.google research.google](https://research.google/blog/making-quantum-error-correction-work/?utm_source=chatgpt.com)  

**29** [Making quantum error correction work](https://research.google/blog/making-quantum-error-correction-work/?utm_source=chatgpt.com)

[azure.microsoft.com azure.microsoft.com](https://azure.microsoft.com/en-us/blog/quantum/2025/02/19/microsoft-unveils-majorana-1-the-worlds-first-quantum-processor-powered-by-topological-qubits/?msockid=2e18b3bd622f67ae04bda5fa63bd66b2&utm_source=chatgpt.com)  

**31** [Microsoft unveils Majorana 1, the world’s first quantum processor powered by topological qubits - Microsoft Azure Quantum Blog](https://azure.microsoft.com/en-us/blog/quantum/2025/02/19/microsoft-unveils-majorana-1-the-worlds-first-quantum-processor-powered-by-topological-qubits/?msockid=2e18b3bd622f67ae04bda5fa63bd66b2&utm_source=chatgpt.com)

[alphaxiv.org alphaxiv.org](https://www.alphaxiv.org/abs/2404.02280)  

**32** <https://www.alphaxiv.org/abs/2404.02280>

**57** <https://www.alphaxiv.org/abs/2404.02280>

[caltech.edu caltech.edu](https://www.caltech.edu/about/news/caltechs-institute-for-quantum-information-and-matter-iqim-receives-new-6-year-grant)  

**33** <https://www.caltech.edu/about/news/caltechs-institute-for-quantum-information-and-matter-iqim-receives-new-6-year-grant>

**61** <https://www.caltech.edu/about/news/caltechs-institute-for-quantum-information-and-matter-iqim-receives-new-6-year-grant>

[preskill.caltech.edu preskill.caltech.edu](https://preskill.caltech.edu/?utm_source=chatgpt.com)  

**34** [John Preskill](https://preskill.caltech.edu/?utm_source=chatgpt.com)

[qtc.umd.edu qtc.umd.edu](https://qtc.umd.edu/news/story/umd-leads-new-25m-nsf-quantum-leap-challenge-institute-for-robust-quantum-simulation?utm_source=chatgpt.com)  

**35** [UMD Leads New $25M NSF Quantum Leap Challenge Institute for ...](https://qtc.umd.edu/news/story/umd-leads-new-25m-nsf-quantum-leap-challenge-institute-for-robust-quantum-simulation?utm_source=chatgpt.com)

[mitibm.mit.edu mitibm.mit.edu](https://mitibm.mit.edu/people/aram-harrow/?utm_source=chatgpt.com)  

**37** [Aram Harrow - MIT-IBM Watson AI Lab](https://mitibm.mit.edu/people/aram-harrow/?utm_source=chatgpt.com)

[qiti.iqc.uwaterloo.ca qiti.iqc.uwaterloo.ca](https://qiti.iqc.uwaterloo.ca/news/)  

**41** <https://qiti.iqc.uwaterloo.ca/news/>

[qusoft.com qusoft.com](https://www.qusoft.com/about/?utm_source=chatgpt.com)  

**43** [About – QuSoft](https://www.qusoft.com/about/?utm_source=chatgpt.com)

[quantum-journal.org quantum-journal.org](https://quantum-journal.org/papers/q-2020-06-04-279/)  

**46** <https://quantum-journal.org/papers/q-2020-06-04-279/>

[nrf.gov.sg nrf.gov.sg](https://www.nrf.gov.sg/resources/quantum-research-coordination-between-astar-and-nus-and-combined-annual-funding/)  

**47** <https://www.nrf.gov.sg/resources/quantum-research-coordination-between-astar-and-nus-and-combined-annual-funding/>

[cde.nus.edu.sg cde.nus.edu.sg](https://cde.nus.edu.sg/mse/news/shaping-the-future-of-quantum-technology/)  

**48** <https://cde.nus.edu.sg/mse/news/shaping-the-future-of-quantum-technology/>

[explore.openalex.org explore.openalex.org](https://explore.openalex.org/works/w3107463944?utm_source=chatgpt.com)  

**51** [Quantum computational advantage using photons - OpenAlex](https://explore.openalex.org/works/w3107463944?utm_source=chatgpt.com)

[fujitsu.com fujitsu.com](https://www.fujitsu.com/global/about/resources/news/press-releases/2023/0324-01.html)  

**52** <https://www.fujitsu.com/global/about/resources/news/press-releases/2023/0324-01.html>

[ibm.com ibm.com](https://www.ibm.com/quantum/blog/qldpc-codes?utm_source=chatgpt.com)  

**54** [Computing with error-corrected quantum computers | IBM Quantum Computing Blog](https://www.ibm.com/quantum/blog/qldpc-codes?utm_source=chatgpt.com)

**55** [Quantum 2026 — IBM Technology Atlas](https://www.ibm.com/roadmaps/quantum/2026/?utm_source=chatgpt.com)

[quantinuum.com quantinuum.com](https://www.quantinuum.com/blog/built-for-all-introducing-our-new-software-stack?utm_source=chatgpt.com)  

**58** [Built for All: Introducing Our New Software Stack](https://www.quantinuum.com/blog/built-for-all-introducing-our-new-software-stack?utm_source=chatgpt.com)

[link.springer.com link.springer.com](https://link.springer.com/article/10.1007/s00220-020-03839-5)  

**59** <https://link.springer.com/article/10.1007/s00220-020-03839-5>

Sources scanned · 457

[iqim.caltech.edu iqim.caltech.edu](https://iqim.caltech.edu/profile/john-preskill/)  

John Preskill – IQIM

https://iqim.caltech.edu/profile/john-preskill/

IQIM – Institute for Quantum Information and Matter

Institute for Quantum Information and Matter, a National Science Foundation Physics Frontiers Center 4.14.25 Image: Caltech Science Exchange Quantum CALTECH SCIENCE Exchange brings insight and e...

[quics.umd.edu quics.umd.edu](https://www.quics.umd.edu/people/andrew-childs)  

Andrew Childs | Joint Center for Quantum Information and Computer Science (QuICS)

https://www.quics.umd.edu/people/andrew-childs

Simulating large quantum circuits on a small quantum computer

Simulating large quantum circuits on a small quantum computer. Abstract. Limited quantum memory is one of the most important constraints for near-term quantum ...Read more

[uwaterloo.ca uwaterloo.ca](https://uwaterloo.ca/institute-for-quantum-computing/profiles/john-watrous)  

John Watrous | Institute for Quantum Computing | University of Waterloo

https://uwaterloo.ca/institute-for-quantum-computing/profiles/john-watrous

Reflecting on a year of community, growth and milestones at the Institute for Quantum Computing | Institute for Quantum Computing | University of Waterloo

https://uwaterloo.ca/institute-for-quantum-computing/news/2024-year-in-review

Newsletters and reports | Institute for Quantum Computing | University of Waterloo

https://uwaterloo.ca/institute-for-quantum-computing-impact-report/forward?path=taxonomy%2Fterm%2F59

IQC members awarded millions in NSERC Quantum Alliance funding | Institute for Quantum Computing | University of Waterloo

https://uwaterloo.ca/institute-for-quantum-computing/news/iqc-members-awarded-millions-nserc-quantum-alliance-funding

IQC researchers recognized with NSERC awards | Institute for Quantum Computing | University of Waterloo

IQC RESEARCHERS RECOGNIZED WITH NSERC AWARDS Friday, June 27, 2014 Eight IQC researchers received Natural Sciences and Engineering Research Council (NSERC) awards‎ including a prestigious NSERC Dis...

[preskill.caltech.edu preskill.caltech.edu](https://preskill.caltech.edu/)  

John Preskill

https://preskill.caltech.edu/

John Preskill

CONTACT Caltech 305-16, Pasadena, CA 91125 Office: 206 Annenberg Phone: 626-395-6691 Email: preskill(at)caltech(dot)edu PAPERS AND TALKS My publications are on the arXiv and on Google Scholar. Here...

Publications

John Preskill — Home. Publications. See also the arXiv and Google Scholar. Cosmological Production of Superheavy Magnetic Monopoles, John P. Preskill ...Read more

[magazine.caltech.edu magazine.caltech.edu](https://magazine.caltech.edu/post/iqim-quantum-john-preskill)  

The Story of IQIM: Institute for Quantum Information and Matter — Caltech Magazine

QUANTUM'S HUB: THE INSTITUTE FOR QUANTUM INFORMATION AND MATTER (IQIM) Summer 2022 Jul 26 Written By Andrew Moseman Image: a cartwheel in front of Beckman Auditorium In quantum superposition, sub...

[cs.umd.edu cs.umd.edu](https://www.cs.umd.edu/~amchilds/)  

Andrew Childs

My research aims to better understand the power of quantum systems to process information. Teaching Fall 2026: Introduction to quantum information processing

[qc.uwaterloo.ca qc.uwaterloo.ca](https://qc.uwaterloo.ca/)  

Quantum Computing in the School of Computer Science

QUANTUM COMPUTING RESEARCH GROUP SCHOOL OF COMPUTER SCIENCE, UNIVERSITY OF WATERLOO Quantum information formulates the notion of information in a manner that accounts for the quantum mechanical beha...

[publications.uwaterloo.ca publications.uwaterloo.ca](https://publications.uwaterloo.ca/quantum-impact-2021/quantum-champions/)  

Quantum champions - IQC Impact Report 2021

Quantum champions \* Pages \* Editions QUANTUM CHAMPIONS Image: John Watrous JOHN WATROUS INTERIM EXECUTIVE DIRECTOR, INSTITUTE FOR QUANTUM COMPUTING PROFESSOR, DAVID R. CHERITON SCHOOL OF COMPUTER...

[its.caltech.edu its.caltech.edu](https://www.its.caltech.edu/~preskill/)  

John Preskill

John D. MacArthur Professor of Theoretical Physics Division of Physics, Mathematics, and Astronomy California Institute of Technology Curriculum Vitae and publication list. IMAGEHOME PAGE FOR PHYSI...

[en.wikipedia.org en.wikipedia.org](https://en.wikipedia.org/wiki/Renato_Renner)  

Renato Renner

Renato Renner (born 11 December 1974) is a Swiss professor for Theoretical Physics at the Swiss Federal Institute of Technology (ETH) in Zurich, ...Read more

Swiss Electromagnetics Research and Engineering Centre

https://en.wikipedia.org/wiki/Swiss\_Electromagnetics\_Research\_and\_Engineering\_Centre

Categorical quantum mechanics

https://en.wikipedia.org/wiki/Categorical\_quantum\_mechanics

Quantum Trajectory Theory

https://en.wikipedia.org/wiki/Quantum\_Trajectory\_Theory

Centre for Quantum Computation

https://en.wikipedia.org/wiki/Centre\_for\_Quantum\_Computation

NQIT

https://en.wikipedia.org/wiki/NQIT

Quantum group

https://en.wikipedia.org/wiki/Quantum\_group

Centre for Quantum Technologies

https://en.wikipedia.org/wiki/Centre\_for\_Quantum\_Technologies

Pan Jianwei - Wikipedia

Pan Jianwei is a Chinese academic administrator and quantum physicist. He is a university administrator and professor of physics at the University of ...

Jiuzhang (quantum computer)

https://en.wikipedia.org/wiki/Jiuzhang\_%28quantum\_computer%29

Yasunobu Nakamura

https://en.wikipedia.org/wiki/Yasunobu\_Nakamura

Institute for Interdisciplinary Information Sciences

https://en.wikipedia.org/wiki/Institute\_for\_Interdisciplinary\_Information\_Sciences

Seigo Tarucha

https://en.wikipedia.org/wiki/Seigo\_Tarucha

Aram Harrow

Aram Wettroth Harrow (born 1980) is an American quantum information scientist. He has been a professor at the Massachusetts Institute of Technology since ...

Seth Lloyd

https://en.wikipedia.org/wiki/Seth\_Lloyd

Isaac Chuang

https://en.wikipedia.org/wiki/Isaac\_Chuang

Dodd-Walls Centre

https://en.wikipedia.org/wiki/Dodd-Walls\_Centre

OpenAlex

https://en.wikipedia.org/wiki/OpenAlex

Shor code

https://en.wikipedia.org/wiki/Shor\_code

Harry Buhrman

Harry Buhrman (born 1966) is a Dutch computer scientist, currently Chief Scientist Quantum Algorithms & Innovation at Quantinuum.

Majorana 1

https://en.wikipedia.org/wiki/Majorana\_1

Quantum singular value transformation

https://en.wikipedia.org/wiki/Quantum\_singular\_value\_transformation

Andrew Childs

https://en.wikipedia.org/wiki/Andrew\_Childs

Harry Buhrman

Harry Buhrman (born 1966) is a Dutch computer scientist, currently Chief Scientist Quantum Algorithms & Innovation at Quantinuum . Read more

[de.wikipedia.org de.wikipedia.org](https://de.wikipedia.org/wiki/Renato_Renner)  

Renato Renner

https://de.wikipedia.org/wiki/Renato\_Renner

Renato Zenobi

https://de.wikipedia.org/wiki/Renato\_Zenobi

[arxiv.org arxiv.org](https://arxiv.org/abs/1412.8553)  

The ZX-calculus is complete for the single-qubit Clifford+T group

https://arxiv.org/abs/1412.8553

The ZX-calculus is complete for stabilizer quantum mechanics

https://arxiv.org/abs/1307.7025

A Complete Axiomatisation of the ZX-Calculus for Clifford+T Quantum Mechanics

https://arxiv.org/abs/1705.11151

ZX-Calculus: Cyclotomic Supplementarity and Incompleteness for Clifford+T quantum mechanics

https://arxiv.org/abs/1702.01945

Security of Quantum Key Distribution

https://arxiv.org/abs/quant-ph/0512258

Fundamental work cost of quantum processes

https://arxiv.org/abs/1709.00506

The black hole information puzzle and the quantum de Finetti theorem

https://arxiv.org/abs/2110.14653

An information-theoretic security proof for QKD protocols

https://arxiv.org/abs/quant-ph/0502064

Phase-Programmable Gaussian Boson Sampling Using Stimulated Squeezed Light

https://arxiv.org/abs/2106.15534

Applications of coherent classical communication and the Schur transform to quantum information theory

https://arxiv.org/abs/quant-ph/0512255

Quantum error correction below the surface code threshold - arXiv

In this work, we present two surface code memories operating below this threshold: a distance-7 code and a distance-5 code integrated with a ...

Quantum computational advantage using photons

https://arxiv.org/abs/2012.01625

Supplementary information for "Quantum supremacy using a programmable superconducting processor"

Supplementary information for "Quantum supremacy using a programmable superconducting processor". Authors:Frank Arute, Kunal Arya, Ryan Babbush, ...

Quantum singular value transformation and beyond: exponential improvements for quantum matrix arithmetics

https://arxiv.org/abs/1806.01838

Entangling four logical qubits beyond break-even in a nonlocal code

https://arxiv.org/abs/2406.02666

Towards Distributed Quantum Error Correction for Distributed Quantum Computing

https://arxiv.org/abs/2409.05244

Demonstration of logical qubits and repeated error correction with better-than-physical error rates

https://arxiv.org/abs/2404.02280

Realizing Repeated Quantum Error Correction in a Distance-Three Surface Code

https://arxiv.org/abs/2112.03708

Entropy accumulation

https://arxiv.org/abs/1607.01796

There and back again: A circuit extraction tale

https://arxiv.org/abs/2003.01664

Quantum isomorphism is equivalent to equality of homomorphism counts from planar graphs

https://arxiv.org/abs/1910.06958

Predicting Many Properties of a Quantum System from Very Few Measurements

https://arxiv.org/abs/2002.08953

Simulating Large Quantum Circuits on a Small Quantum Computer

https://arxiv.org/abs/1904.00102

Graph-theoretic Simplification of Quantum Circuits with the ZX-calculus

https://arxiv.org/abs/1902.03178

\OurScheme: Evaluating Large Quantum Circuits on Small ...

23 Mar 2025 — [37] Tianyi Peng, Aram W. Harrow, Maris Ozols, and Xiaodi Wu. Simulating large quantum circuits on a small quantum computer. volume 125, page ...Read more

Trotter error bounds and dynamic multi-product formulas for Hamiltonian simulation

https://arxiv.org/abs/2306.12569

Laura Mančinska's articles on arXiv

( 2026 ) Subjects: Quantum Physics (quant-ph) ( 2026 ) Subjects: Quantum Physics (quant-ph) Laura Mancinska , Subjects: Networking and Internet Architecture. ...

[livescience.com livescience.com](https://www.livescience.com/physics-mathematics/quantum-physics/physicists-achieve-perfect-randomness-for-the-first-time-ever)  

Physicists achieve 'perfect randomness' for the first time ever

Researchers at ETH Zurich have achieved a groundbreaking milestone by generating "perfect randomness" using entangled superconducting qubits. Unlike traditional random number generators that can carry subtle biases, this quantum-based method offers certifiably unbiased outputs, critical for fields like cryptography. Led by Professors Renato Renner and Andreas Wallraff, the team employed two superconducting chips cooled near absolute zero and linked by a 30-meter supercooled tube. This setup ensured quantum entanglement between the qubits, with enough distance to prevent any light-speed communication that could disrupt the randomness. An initial imperfect random input was used to determine how the qubits would be measured. Then, post-measurement, an algorithm enhanced the results to yield truly random binary sequences. Since all randomness originates directly from quantum measurements, the process is computationally inexpensive and secure against future advances in analysis. The ETH team likens the breakthrough to atomic clocks in its potential reliability and utility. Applications may span encrypted messaging, digital identities, lotteries, and blockchain systems, especially in networked environments where nodes require trusted randomness sources.

'This is easily the most powerful quantum computer on Earth': Scientists unveil Helios, a record-breaking quantum system

Quantinuum has unveiled Helios, the most powerful quantum computer to date, featuring a 98-qubit quantum processing unit (QPU) made from barium ions in a novel “junction ion trap” layout. This efficient design improves error detection and correction, enabling Helios to outperform all existing quantum systems in benchmark tests. Using 98 physical qubits, scientists created 48 logical qubits—with better than break-even performance using only a 2:1 physical-to-logical qubit ratio, far exceeding the industry norm. Helios also features a new real-time error correction control engine and utilizes Nvidia GPUs to minimize errors during computation. A new programming language, Guppy, based on Python, was developed to support future fault-tolerant applications. The system achieved groundbreaking qubit fidelity—99.921% for two-qubit operations and 99.9975% for single-qubit gates. Beyond computational benchmarks, Helios simulated superconducting materials, revealing novel electron behaviors that aren’t observable in physical lab settings. According to Quantinuum's director of computational design, David Hayes, this architecture offers a path to scaling quantum systems toward the millions of qubits required to surpass traditional supercomputers.

Japan launches its first homegrown quantum computer

Japan has launched its first fully domestically built quantum computer, marking a significant milestone in its technological advancement. The system, operational since July 28, 2025, is housed at the University of Osaka's Center for Quantum Information and Quantum Biology (QIQB). Unlike previous systems reliant on imported components, this computer uses only homegrown hardware and software, including the superconducting qubit-based quantum processing unit (QPU) developed by RIKEN and the Open Quantum Toolchain for Operators and Users (OQTOPUS), an open-source software suite. All structural elements, such as the chip package, magnetic shielding, filters, and cooling units like dilution and pulse tube refrigerators, were sourced from Japanese manufacturers. The system was publicly showcased at Expo 2025 in Osaka, where attendees could interact with it via cloud-based access and participate in demonstrations illustrating quantum principles like entanglement. Quantum computing holds the promise of solving complex problems in areas like medicine, logistics, and traffic systems. However, progress still faces hurdles like high error rates, making quantum error correction a crucial focus of ongoing research. Japan’s move underscores its commitment to advancing independent and cutting-edge quantum technologies.

[thetimes.co.uk thetimes.co.uk](https://www.thetimes.co.uk/article/uk-quantum-firm-oxford-ionics-sold-to-us-rival-ion-q-for-11bn-w55plxwrx)  

UK quantum firm Oxford Ionics sold to US rival Ion Q for $1.1bn

Oxford Ionics, a UK quantum computing start-up founded in 2019 by Oxford University PhD graduates Chris Ballance and Tom Harty, has been acquired by U.S.-based Ion Q in a deal valued at nearly $1.1 billion. The acquisition, primarily composed of shares, grants Ballance and Harty a combined $370 million stake. Despite the sale, both founders will remain with the company and plan to expand operations in Oxford, including establishing a new head office at a 30,000 sq ft science park and maintaining an office in Colorado. Oxford Ionics specializes in trapped ion qubit technology, known for its high-quality, low-error quantum processing capabilities. The company holds several world records in quantum performance and has sold computers to the UK's National Quantum Computing Centre and Germany's Cyberagentur. Key partners include AstraZeneca. Ion Q, led by CEO Niccolo de Masi, aims to create the "Nvidia of quantum" and grow to a $1 trillion company. The merger is seen as a strategic collaboration between UK and US firms to counter China’s quantum advancements. Oxford Ionics was backed by Oxford Science Enterprises and other major investors, raising $36 million in 2022.

[barrons.com barrons.com](https://www.barrons.com/articles/ionq-quantum-computing-oxford-ionics-a791d8a5)  

IonQ Stock Rises. It's Buying U.K. Quantum Computing Start-Up Oxford Ionics for $1.075 Billion

IonQ announced its acquisition of U.K.-based quantum computing startup Oxford Ionics for $1.075 billion, comprising $1.065 billion in common stock and $10 million in cash. Both companies specialize in trapped-ion quantum computing. This move follows IonQ's recent acquisition of Lightsynq and a controlling stake in ID Quantique, part of its global expansion strategy. Oxford Ionics, which also operates in Colorado, was selected earlier this year for the U.S. Defense Advanced Research Projects Agency’s Quantum Benchmarking Initiative. IonQ said the acquisition enhances U.S.-U.K. quantum technology collaboration and supports its goal of building fault-tolerant quantum computers with two million physical qubits and 80,000 logical qubits by 2030. Following the announcement, IonQ’s stock rose 2.9% to $40.16. Additionally, IonQ unveiled a collaborative research project with AstraZeneca, Amazon, and Nvidia, which significantly sped up chemical simulations using its Forte processor in a hybrid quantum-classical workflow. The demonstration reduced simulation time from months to days, with a 20x improvement in solution time. IonQ CEO Niccolo de Masi likened the evolution of quantum technology to recent advances in AI, suggesting the industry is nearing a tipping point toward broader commercial utility.

[ft.com ft.com](https://www.ft.com/content/dde7bac2-cacb-4deb-9223-5bcfe285db15)  

US quantum computing company IonQ to buy Oxford university start-up

IonQ, a leading US quantum computing company, announced a $1.1 billion all-stock acquisition of Oxford Ionics, a UK start-up spun out from the University of Oxford. This marks a significant move in the quantum computing sector, reflecting growing deal activity amid technological breakthroughs. Oxford Ionics, founded in 2019, is recognized for its highly accurate ion-trapped quantum technology, which integrates with standard semiconductor chips and experiences fewer random errors. The acquisition includes a $10 million cash payment and will grant Oxford Ionics’ investors between 7.3% and 11.9% of IonQ's common stock, dependent on stock performance before the deal closes later this year. IonQ aims to use Oxford Ionics' technology and team, including its 80 employees, to achieve its target of creating a fault-tolerant quantum computer with 80,000 logical and 2 million physical qubits by the end of the decade. This move positions it ahead of rivals like IBM, which plans to build a 100,000-qubit machine by 2033. IonQ CEO Niccolo de Masi stated the acquisition supports the company’s ambition to become "the Nvidia of quantum." IonQ, whose clients include the US Oak Ridge National Laboratory, AstraZeneca, and Airbus, has seen its shares quadruple since 2021 amid rising enthusiasm for quantum computing.

Quantum computing company raises a record $1bn

PsiQuantum, a US-based quantum computing start-up originally founded in the UK, has secured $1 billion in a record-breaking funding round, marking the industry's largest investment to date. The company aims to build a 1 million-qubit quantum computer by 2028, significantly outpacing current machines that operate with only hundreds of qubits. PsiQuantum uses photon-based qubits, which it claims are more scalable and easier to produce using existing semiconductor technologies, without the need for ultra-low temperatures required by competitors like Google and IBM. The funding round was led by BlackRock, Temasek, and Baillie Gifford, with participation from Nvidia’s venture arm, despite CEO Jensen Huang’s caution that practical quantum machines may still be decades away. The investment values PsiQuantum at $7 billion, a sharp increase from $3.2 billion in 2021. This surge of investor interest follows recent technological breakthroughs and growing optimism in the quantum sector, spurring competition among players like Quantinuum, IQM, IonQ, and Rigetti. While PsiQuantum has achieved key technical milestones, challenges remain, especially in error correction. The company plans to begin construction on its first full-scale site in Australia and has agreements for another in Chicago.

[cs.ox.ac.uk cs.ox.ac.uk](https://www.cs.ox.ac.uk/people/aleks.kissinger/)  

Aleks Kissinger | Department of Computer Science

https://www.cs.ox.ac.uk/people/aleks.kissinger/

[cwi.nl cwi.nl](https://www.cwi.nl/en/news/qusoft-research-center-quantum-software-launch/)  

QuSoft research center for quantum software launched

https://www.cwi.nl/en/news/qusoft-research-center-quantum-software-launch/

QuSoft

QUSOFT QuSoft is the Dutch research center for the development of software and technology for future quantum computers. It is a collaboration between CWI and the University of Amsterdam (UvA). Publ...

World-renowned quantum researcher Harry Buhrman takes on new ...

As of 15 December 2023, quantum researcher Harry Buhrman (CWI, QuSoft and UvA) will start a new position as Chief Scientist Quantum ...

The Quantum Leaps of Harry Buhrman

At the end of 2023, world-renowned quantum researcher Harry Buhrman moved from CWI's Algorithms and Complexity group to Quantinuum in London, ... Read more

QuSoft

QUSOFT QuSoft is het Nederlandse onderzoekscentrum voor kwantumsoftware. Het werd in 2015 opgericht als een samenwerkingsverband tussen de Universiteit van Amsterdam en het CWI. Deel deze pagina I...

QuSoft onderzoekscentrum voor kwantum-software gelanceerd

QUSOFT ONDERZOEKSCENTRUM VOOR KWANTUM-SOFTWARE GELANCEERD Donderdag 3 december 2015 wordt QuSoft, het eerste onderzoekscentrum dat zich specifiek richt op kwantum-software, gelanceerd. Het centrum i...

[qusoft.com qusoft.com](https://www.qusoft.com/about/)  

About – QuSoft

https://www.qusoft.com/about/

[oqi.web.ox.ac.uk oqi.web.ox.ac.uk](https://oqi.web.ox.ac.uk/people/aleks-kissinger)  

Aleks Kissinger | Oxford Quantum Institute

ALEKS KISSINGER Image: Aleks kissinger Associate Professor I am an Associate Professor of Quantum Computing at the University of Oxford, and the joint head of the Quantum Group in Oxford's Departm...

[qmath.ku.dk qmath.ku.dk](https://qmath.ku.dk/)  

Centre for the Mathematics of Quantum Theory – University of Copenhagen

This lecture presents a mathematical framework for proving that quantum agents can learn from exponentially fewer experiments than classical agents. We will ... Read more

QMath News – University of Copenhagen - Københavns Universitet

Professor Matthias Christandl from QMATH gives a Copenhagen Bioscience Lecture on "Artificially… Dynamics on Correlated Networks. 2021.03.20. Associate ...

Past Quantum Lunches – University of Copenhagen - QMATH

Matthias Christandl from QMATH · 10 Aug. 2016, 12:00-13:00. Quantum Lunch: An outsider's view on the mathematical foundations of machine ...

About the QMath Centre – University of Copenhagen

https://qmath.ku.dk/about/

Masterclass: Quantum Learning Theory – University of Copenhagen

https://qmath.ku.dk/events/quantum-learning-theory

Collaboration – University of Copenhagen

https://qmath.ku.dk/about/collaboration/

[qit.ethz.ch qit.ethz.ch](https://qit.ethz.ch/)  

Homepage – Quantum Information Theory | ETH Zurich

https://qit.ethz.ch/

[wired.com wired.com](https://www.wired.com/2017/05/happens-mix-thermodynamics-quantum-world-revolution)  

What Happens When You Mix Thermodynamics and the Quantum World? A Revolution

The article explores the rapidly evolving field of quantum thermodynamics, which seeks to reinterpret classical thermodynamics through the lens of quantum mechanics and quantum information theory. Traditionally, thermodynamics was rooted in 19th-century industrial applications like steam engines, where laws such as entropy increasing over time governed energy interactions. However, the theory always had an unusual, almost "magical" reputation due to its apparent subjectivity, especially regarding entropy and energy dissipation. Revolutionary progress in understanding thermodynamics now stems from quantum information theory, which treats information as a physical quantity. Researchers such as Sandu Popescu and Jonathan Oppenheim have tied entropy's behavior to the spread of quantum information and entanglement between particles. These insights suggest that entropy increase may reflect an observer’s limited knowledge rather than fundamental disorder. New quantum versions of thermodynamic laws have been developed, enabling novel understandings of phenomena such as Maxwell’s demon and the second law. Entropy is increasingly viewed as observer-dependent rather than an intrinsic property of systems. Researchers are also investigating how conserved quantities like angular momentum interact in quantum systems, and theorize a broader thermodynamic framework where information acts as currency. This could reshape interpretations of space-time and black hole physics. However, critics warn against overemphasizing information theory and call for clarity in definitions of work and entropy in quantum contexts. The field is vibrant yet disordered, as experts attempt to synthesize various findings into a coherent theory with both philosophical and practical implications for future technologies like quantum engines and computers.

New Quantum Theory Could Explain the Flow of Time

A new quantum theory proposes that the flow of time—commonly understood as the “arrow of time”—can be explained not by classical thermodynamics or human ignorance, but by quantum entanglement. Traditionally, thermodynamics explained the direction of time through statistical probabilities and increasing entropy, yet the underlying laws of physics are time-symmetric. Physicists such as Sandu Popescu and Tony Short argue that time’s arrow emerges from how particles become entangled during interactions: energy disperses, and systems reach equilibrium because information about their initial states spreads out through entanglement. Their theory builds on earlier work by Seth Lloyd, who in the 1980s suggested that entanglement, not ignorance, drives time forward. Although initially dismissed, the idea found support through advances in quantum information theory. Recent proofs show that most physical systems equilibrate over realistic time scales due to increasing entanglement. This quantum view maintains that while local entropy increases, global entropy remains zero, as the universe itself is in a pure state. However, the theory does not yet explain why the universe began far from equilibrium nor address the deeper nature of time itself. Nonetheless, it marks significant progress in understanding time's asymmetry and has potential implications for quantum computing, thermodynamics, and cosmology.

[quantum.ustc.edu.cn quantum.ustc.edu.cn](https://quantum.ustc.edu.cn/web/en/node/32)  

Jian-Wei Pan | Division of Quantum Physics and Quantum Information

Prof. Jian-Wei Pan, born in Mar, 1970, is a full professor of physics at the University of Science and Technology of China. He obtained his Ph.D. degree in ...

首页 | Division of Quantum Physics and Quantum Information

This division of quantum physics and quantum information was founded by Prof. Jian-Wei Pan in 2001. We work in the field of quantum optics and quantum ...

[youtube.com youtube.com](https://www.youtube.com/watch?v=Dc-RSPv9FT8)  

Quantum information processing with photons and atoms | Jian Wei ...

Quantum information processing with photons and atoms | Jian Wei Pan (USTC, China) · Comments.

What Will We Do With Quantum Computing? - Aram Harrow, MIT

Comments · Lunch & Learn: Quantum Computing · Quantum Information Science - Dr. · Quantum Computing 2026 Update · Zeros of the partition function ...

Aram Harrow: Hybrid Classical-Quantum Algorithms | QHack 2023

Comments · Electromagnetism as a Gauge Theory · MIT 6. · Ezequiel Chiacchio: Implementing Real-world Optimization Use Cases in Quantum Devices | ...

Quantum Supremacy Using a Programmable Superconducting ...

Sergio Boixo (Google Research) https://simons.berkeley.edu/talks/quantum-supremacy-using-programmable-superconducting-processor-i Quantum ...

"Below Threshold Quantum Error Correction", Alexandre Bourassa ...

"Below Threshold Quantum Error Correction", Alexandre Bourassa, Google Quantum, AI Abstract: Quantum error correction (QEC) is critical for ...

Q100: Keisuke Fujii - The Future of Quantum Computing

Meet Keisuke Fujii Deputy Director & Distinguished Professor, Center for Quantum Information and Quantum Biology, Graduate School of ...

[quantumzeitgeist.com quantumzeitgeist.com](https://quantumzeitgeist.com/pan-jianwei-the-chinese-quantum-pioneer/)  

Pan Jianwei, The Chinese Quantum Pioneer

Pan Jianwei built two quantum advantage machines, the photonic Jiuzhang and the superconducting Zuchongzhi. He has not won a Nobel Prize, yet ...

Quantum Simulators Advance With New $37.5M NSF Grant

A $37.5 million renewal award from the U.S. National Science Foundation builds on an initial $25 million investment from 2021. This sustained ...

John Preskill, The Physicist Who Named ...

1 Jul 2026 — John Preskill coined quantum supremacy and NISQ ・ 2026 by Futurist ・ as a senior scientist in 2026.

[facebook.com facebook.com](https://www.facebook.com/scmp/posts/the-breakthrough-establishes-a-core-element-required-for-general-purpose-quantum/1395934735915908/)  

The breakthrough establishes a core element required for general ...

Chinese researchers have achieved a monumental breakthrough in quantum computing with their prototype, Jiuzhang. By counting 76 photons through ...

Anhui, China - Facebook

Pan Jianwei, a member of the CPPCC National Committee, says Anhui is emerging as a key hub for quantum innovation in China.

NSF renews funding for Quantum Leap Challenge Institute - Facebook

The NSF Quantum Leap Challenge Institute for Robust Quantum Simulation has renewed its funding, totaling $37.5 million.

QuSoft | Amsterdam - Facebook

This evening co-director Harry Buhrman will give a Quantum Intermezzo at New Scientist NL's. Quantum Delta NL yesterday! Quantum Delta NL celebrate close ...

Centre for Quantum Technologies | Singapore ...

Marco Tomamichel was his main thesis advisor … quantum algorithms. Principal Investigator Rahul Jain and his thesis is on "Minimal Assumptions in Quantum ...

Erlangen Meeting of COST CA15220 "Quantum Technology in ...

The Wallenberg Centre for Quantum Technology invites to a free online workshop on quantum technology. ... Marco Tomamichel (NUS). Schloss Dagstuhl ...

[scholar.google.com scholar.google.com](https://scholar.google.com/citations?hl=zh-CN&user=RERrJ6UAAAAJ)  

‪Jian-Wei Pan‬ - ‪Google 学术搜索‬

Jian-Wei Pan. University of Science and Technology of China. 在 ustc.edu.cn 的电子邮件经过验证. quantum informationquantum physics. 文章引用次数 ...

‪aram harrow‬ - ‪Google Scholar‬

aram harrow Physics, MIT Verified - Homepage quantum information ArticlesCited. Quantum algorithm for linear systems of equations

Rahul Jain

Professor, Computer Science, NUS - iCentre for Quantum TechnologiesVerified. Marco Tomamichel Marco TomamichelProfessor at ECE/CDE and CQT, National University ...

Keisuke Fujii

i Keisuke Fujii Engineering Science, Osaka Univ. quantum physicsquantum computationquantum information. Theory, Physical Implementations, and Applications,

Laura Mančinska

Quantum isomorphism is equivalent to equality of homomorphism counts from planar graphs. L Mančinska, DE Roberson. 2020 IEEE 61st Annual Symposium on ...

Nathan Wiebe

Theory of trotter error with commutator scaling. AM Childs, Y Su, MC Tran, N Wiebe, S Zhu. Physical Review X 11 (1), 011020, 2021. 1099, 2021. Hartree-Fock on a ...Read more

John Preskill

h-index 92 72. John Preskill Richard P. Feynman Professor of Theoretical Physics, California Institute of Technology

Andrew Childs

Lecturer in Criminology, Griffith University. Citations 562 506 h-index 10. Journal of Criminology,

Renato Renner

Professor for Theoretical Physics, - ‪Quantum Information Theory‬ … 13909 h-index 84 60 i10-index 159

Andrew M. Childs

Quantum Information and Computer Science, University of Maryland … h-index 63 51. Childs Joint Center for Quantum Information and Computer Science, University ...

Renato Renner

Professor for Theoretical Physics, h-index 84 60 i10-index. Renner International Journal of Quantum Information. R Renner Nature Physics

Bharath Sambasivam

h-index 8 8 i10-index … aram harrow aram harrowPhysics, 2026 Quantum simulation of molecular excited-state manifolds and energies. A Quantum algorithm for real ...

Harry Buhrman

538 5830 h - index 51 29. Harry Buhrman Chief Scientist Q Algorithms @ Quantinuum, Professor Univ. of Amsterdam & Founding Director

Laura Classen

Institute for Solid State Research ・ 1083 h - index 22 20 i10- index ・ 32 articles articles available not available. Laura Classen Laura Classen

Marco Tomamichel

Professor at ECE/CDE and CQT, National University of Singapore - ‪‪ Cited by ‬‬ ... Entropic uncertainty relations and their applications . PJ Coles, M Berta, M ... Read more

Stephanie Wehner

Entropic uncertainty relations and their applications . PJ Coles, M Berta, M Tomamichel , S Wehner. Reviews of Modern Physics 89 (1), 015002, 2017. 811, 2017. Read more

Mario Berta

RWTH Aachen & Imperial College London - ‪‪ Cited by 10291‬‬ - ‪Quantum‬ ... Entropic uncertainty relations and their applications . PJ Coles, M Berta, M ... Read more

[app.thequantuminsider.com app.thequantuminsider.com](https://app.thequantuminsider.com/company/cbb4538e-06bc-4578-a67d-c1204c17874d/profile)  

Jiuzhang [Quantum Computer by USTC] - Company Overview

Jiuzhang is the first photonic quantum computer to claim quantum supremacy. Jiuzhang was developed by a team from University of Science and Technology of China ...

[fr.wikipedia.org fr.wikipedia.org](https://fr.wikipedia.org/wiki/Jiuzhang)  

Jiuzhang

https://fr.wikipedia.org/wiki/Jiuzhang

[reuters.com reuters.com](https://www.reuters.com/world/asia-pacific/china-likely-have-standards-post-quantum-crytography-3-years-expert-says-2026-03-19/)  

China likely to have standards for post-quantum cryptography in 3 years, expert says

China is expected to establish national standards for post-quantum cryptography within the next three years, driven by heavy investment and strategic emphasis in its latest five-year plan. This initiative reflects global efforts to safeguard data against powerful future quantum computers that could break current encryption methods. China has prioritized quantum technology alongside emerging industries like embodied AI and brain-computer interfaces, and aims to develop a scalable quantum computer. While the U.S. finalized its first post-quantum cryptography standards in 2024 and targets industry-wide adoption by 2035, China has taken a unique approach by focusing on "structureless lattice" algorithms such as S-Cloud+, which are considered more secure than algebraic-lattice-based international standards. Financial and energy sectors are identified as migration priorities due to their data sensitivity. Tsinghua University professor Wang Xiaoyun forecasts a surge in the industry’s growth within the next three to five years. China also recently released an open-source operating system for quantum computers. Countries like South Korea are also planning phased transitions to post-quantum cryptography by 2035, emphasizing its increasingly global strategic importance.

IBM says key quantum computing error correction algorithm can run on conventional AMD chips

IBM announced that it successfully ran a key quantum error correction algorithm on standard AMD field-programmable gate array (FPGA) chips, marking a significant step toward commercializing quantum computing. The correction algorithm, vital for managing the error-prone nature of quantum bits (qubits), was initially introduced by IBM in June. While quantum computers are touted for solving problems conventional computers would take millennia to crack, they remain challenged by high error rates. Jay Gambetta, Director of IBM Research, emphasized that the algorithm not only operates effectively on non-specialized, affordable AMD chips but also executes in real time, performing ten times faster than required. This breakthrough supports IBM’s roadmap to build a quantum computer named Starling by 2029, with this milestone achieved a year ahead of schedule. IBM is in a competitive race with Microsoft and Google in advancing quantum technology.

EU turns to private funding to boost quantum technology ambition

The European Union is shifting its focus towards securing private investment to bolster its position in quantum technology by 2030, aiming to reduce reliance on the U.S. and China. According to EU tech chief Henna Virkkunen, while public funding is already strong—with over €11 billion ($13 billion) invested over the past five years—Europe currently accounts for only 5% of global private quantum investments. The newly unveiled EU Quantum Strategy seeks to enhance private sector involvement and promote collaboration in research, infrastructure, and start-up development, particularly in the fields of security and defense. Virkkunen emphasized the vulnerability of European quantum start-ups to foreign acquisition or relocation due to limited funding, stressing the need for protective and supportive measures. To this end, the European Commission plans to introduce a "Quantum Act" in 2026 to support and implement the strategy. The quantum sector is projected to grow significantly and may be worth trillions of dollars within the next decade.

Canada to tighten foreign investment rules in AI, space technology sectors, Bloomberg reports

Canada is set to tighten its foreign investment regulations in sectors such as artificial intelligence (AI), quantum computing, and space technology, according to a Bloomberg report citing Innovation Minister François-Philippe Champagne. Under the new policy, foreign companies will be required to notify the government in advance of planned investments or acquisitions in these areas. This measure is intended to allow for national security reviews before deals progress too far, limiting investors' access to sensitive data during the process. The stricter rules will also cover critical minerals and could extend to other sectors. The move aligns with a previously announced crackdown on foreign involvement in Canada's interactive digital media industry to prevent threats from state-sponsored actors. The Innovation, Science and Economic Development ministry has not yet commented.

Novo Nordisk owner to invest $200 million in quantum computing startups

Novo Holdings, the investment arm of the Novo Nordisk Foundation and majority voting shareholder in Danish pharmaceutical giant Novo Nordisk, has announced plans to invest around $200 million in quantum computing startups. This move aims to support the development of quantum computing technologies, particularly in life sciences, with a focus on Nordic-based companies. Quantum computing is regarded by experts as a transformative technology capable of accelerating tasks like drug development and processing complex biological data. Soren Moller, a managing partner at Novo Holdings, highlighted potential applications such as modeling drug-protein interactions and analyzing large-scale biological systems. Though practical quantum computers are still in development, Novo Holdings sees this as a strategic time to invest and help shape the emerging quantum ecosystem in the life sciences sector.

[physics.mit.edu physics.mit.edu](https://physics.mit.edu/faculty/aram-harrow/)  

Aram Harrow '01 PhD '05 - MIT Physics

His research focuses on quantum information and computing, and best known for co-developing the HHL algorithm in 2008. Research Areas. Quantum Information ...

Quantum Information Science - MIT Physics

MIT Center for Theoretical Physics — a Leinweber Institute (CTP-LI) faculty involved are: Soonwon Choi and Aram Harrow, and the larger group at MIT includes ...

[mitibm.mit.edu mitibm.mit.edu](https://mitibm.mit.edu/people/aram-harrow/)  

Aram Harrow - MIT-IBM Watson AI Lab

Aram Harrow is the MIT quantum lead of the MIT-IBM Computing Research Lab and a professor in MIT's Department of Physics. He studies theoretical quantum ...

[english.elpais.com english.elpais.com](https://english.elpais.com/technology/2026-06-05/aram-harrow-quantum-researcher-these-computers-wont-take-10-years-theyll-arrive-sooner.html)  

Aram Harrow, quantum researcher: 'These computers won't take 10 ...

Aram Harrow has spent 25 of his 46 years working in quantum computing. He is a researcher at the Massachusetts Institute of Technology (MIT)

[theoryofcomputing.org theoryofcomputing.org](https://theoryofcomputing.org/articles/v010a003/about.html)  

Aram W. Harrow - Theory of Computing

His research focuses mainly on quantum computing, quantum information and connections between these fields and other areas of math, physics and computer science ...

[icmat.es icmat.es](https://www.icmat.es/news/07-04-26-en/)  

Aram Harrow, creator of one of the most influential quantum ... - ICMAT

Aram Harrow (1980, Michigan, USA) is a theoretical physicist and computer scientist specializing in quantum information and quantum algorithms.

[zh.wikipedia.org zh.wikipedia.org](https://zh.wikipedia.org/wiki/%E9%98%BF%E6%8B%89%E5%A7%86%C2%B7%E5%93%88%E7%BE%85)  

阿拉姆·哈羅

https://zh.wikipedia.org/wiki/%E9%98%BF%E6%8B%89%E5%A7%86%C2%B7%E5%93%88%E7%BE%85

物理量子比特与逻辑量子比特

https://zh.wikipedia.org/wiki/%E7%89%A9%E7%90%86%E9%87%8F%E5%AD%90%E6%AF%94%E7%89%B9%E4%B8%8E%E9%80%BB%E8%BE%91%E9%87%8F%E5%AD%90%E6%AF%94%E7%89%B9

[research.google research.google](https://research.google/blog/making-quantum-error-correction-work/)  

Making quantum error correction work

https://research.google/blog/making-quantum-error-correction-work/

Quantum Supremacy Using a Programmable Superconducting ...

This experiment, referred to as a quantum supremacy experiment, provided direction for our team to overcome the many technical challenges inherent in quantum ...

The vast world of quantum advantage

by R Huang · 2025 · Cited by 77 — The vast world of quantum advantage. Robert Huang. Jarrod McClean. John Preskill. Soonwon Choi. arXiv (2025). Download Google Scholar. Copy Bibtex. Abstract.Read more

Dynamic surface codes open new avenues for quantum error correction

Image: Dynamic surface codes open new avenues for quantum error correction DYNAMIC SURFACE CODES OPEN NEW AVENUES FOR QUANTUM ERROR CORRECTION January 13, 2026 Alec Eickbusch and Alexis Morvan, Re...

A colorful quantum future

Image: A colorful quantum future A COLORFUL QUANTUM FUTURE June 23, 2025 Alexandre Bourassa and Kevin Satzinger, Research Scientists, Google Research, Google Quantum AI team We present results sh...

[blog.google blog.google](https://blog.google/innovation-and-ai/technology/research/google-willow-quantum-chip/)  

Meet Willow, our state-of-the-art quantum chip

https://blog.google/innovation-and-ai/technology/research/google-willow-quantum-chip/

Go inside the Google Quantum AI lab

GO INSIDE THE GOOGLE QUANTUM AI LAB TO LEARN ABOUT HOW QUANTUM COMPUTING WORKS Dec 09, 2024 | We’re taking you inside our Quantum AI lab, and demystifying six essential quantum computing terms. \*...

[ibm.com ibm.com](https://www.ibm.com/roadmaps/quantum/2026/)  

Quantum 2026 — IBM Technology Atlas

https://www.ibm.com/roadmaps/quantum/2026/

Computing with error-corrected quantum computers | IBM Quantum Computing Blog

https://www.ibm.com/quantum/blog/qldpc-codes

Scaling for quantum advantage and beyond | IBM Quantum Computing Blog

SCALING FOR QUANTUM ADVANTAGE AND BEYOND At Quantum Developer Conference 2025, IBM® lays out the groundbreaking advances in algorithms, hardware, and software that will empower our community to achi...

IBM roadmap to quantum-centric supercomputers (Updated 2024) | IBM Quantum Computing Blog

EXPANDING THE IBM QUANTUM ROADMAP TO ANTICIPATE THE FUTURE OF QUANTUM-CENTRIC SUPERCOMPUTING We are explorers. We’re working to explore the limits of computing, chart the course of a technology that...

IBM Commits More Than $10 Billion to Quantum Computing, Funding Its Roadmap from Today's Leading Systems to the World's First Fault-Tolerant Quantum Computers

ALL PRESS RELEASES IBM COMMITS MORE THAN $10 BILLION TO QUANTUM COMPUTING, FUNDING ITS ROADMAP FROM TODAY'S LEADING SYSTEMS TO THE WORLD'S FIRST FAULT-TOLERANT QUANTUM COMPUTERS Five-year investmen...

Introducing Relay-BP | IBM Quantum Computing Blog

RELAY-BP: THE WORLD’S FASTEST, MOST ACCURATE DECODER FOR QLDPC ERROR CORRECTION CODES After months of collaboration—and one happy accident—a team of IBM® researchers has devised the fastest, most ac...

Error correcting codes for near-term quantum computers | IBM Quantum Computing Blog

ERROR CORRECTING CODES FOR NEAR-TERM QUANTUM COMPUTERS At IBM Quantum, we recognize that fault-tolerant universal quantum computers won’t roll off a manufacturing line tomorrow. Rather, we expect th...

Flag-Proxy Networks: Overcoming the Architectural, Scheduling and Decoding Obstacles of Quantum LDPC Codes for MICRO 2024 - IBM Research

MICRO 2024 Conference paper 02 Nov 2024 FLAG-PROXY NETWORKS: OVERCOMING THE ARCHITECTURAL, SCHEDULING AND DECODING OBSTACLES OF QUANTUM LDPC CODES ABSTRACT Quantum error correction is necessary f...

High-threshold and low-overhead fault-tolerant quantum memory for QIP 2024 - IBM Research

Keynote 13 Jan 2024 HIGH-THRESHOLD AND LOW-OVERHEAD FAULT-TOLERANT QUANTUM MEMORY ABSTRACT Quantum error correction becomes a practical possibility only if the physical error rate is below a thre...

HetEC: Architectures for Heterogeneous Quantum Error Correction Codes for ASPLOS 2025 - IBM Research

Conference paper 30 Mar 2025 HETEC: ARCHITECTURES FOR HETEROGENEOUS QUANTUM ERROR CORRECTION CODES View publication ABSTRACT Quantum Error Correction (QEC) is essential for future quantum comput...

Building the future of quantum error correction | IBM Quantum Computing Blog

BUILDING THE FUTURE OF QUANTUM ERROR CORRECTION Last week’s IEEE Quantum Week conference put the spotlight on the latest research in error correction — and a glimpse of what quantum computing’s futu...

IBM Sets the Course to Build World's First Large-Scale, Fault-Tolerant Quantum Computer at New IBM Quantum Data Center - Jun 10, 2025

ALL PRESS RELEASES IBM SETS THE COURSE TO BUILD WORLD'S FIRST LARGE-SCALE, FAULT-TOLERANT QUANTUM COMPUTER AT NEW IBM QUANTUM DATA CENTER Jun 10, 2025 \* \* \* \* \* IBM Quantum roadmap, proces...

Landmark IBM error correction paper on Nature cover | IBM Quantum Computing Blog

LANDMARK IBM ERROR CORRECTION PAPER PUBLISHED ON THE COVER OF NATURE IBM has created a quantum error-correcting code about 10 times more efficient than prior methods — a milestone in quantum computi...

Tour de gross: A modular quantum computer based on bivariate bicycle codes for Quantum Summer Cluster Workshop 2025 - IBM Research

Quantum Summer Cluster Workshop 2025 Conference paper 07 Jul 2025 TOUR DE GROSS: A MODULAR QUANTUM COMPUTER BASED ON BIVARIATE BICYCLE CODES Download paper ABSTRACT We present the bicycle archit...

Codesign of quantum error-correcting codes and modular chiplets in the presence of defects for ASPLOS 2024 - IBM Research

ASPLOS 2024 Conference paper 27 Apr 2024 CODESIGN OF QUANTUM ERROR-CORRECTING CODES AND MODULAR CHIPLETS IN THE PRESENCE OF DEFECTS View publication ABSTRACT Fabrication errors pose a significan...

[doi.org doi.org](https://doi.org/10.1038/s41586-024-08449-y)  

Quantum error correction below the surface code threshold | Nature

https://doi.org/10.1038/s41586-024-08449-y

Theory of Trotter Error with Commutator Scaling | Phys. Rev. X

https://doi.org/10.1103%2FPhysRevX.11.011020

[tomshardware.com tomshardware.com](https://www.tomshardware.com/tech-industry/artificial-intelligence/nvidia-releases-ising-open-ai-models)  

Nvidia releases open AI models for quantum computing tasks - 'Ising' said to be 2.5x faster and 3x more accurate than existing tools for decoding

Nvidia has released a suite of open-source AI models called Ising, designed to enhance quantum computing through improved processor calibration and error correction decoding. Built for integration with Nvidia’s proprietary CUDA-Q software platform and NVQLink interconnect, Ising includes two major components: Ising Calibration, a 35-billion-parameter vision-language model that reduces calibration time from days to hours; and Ising Decoding, a pair of 3D convolutional neural networks offering significant performance gains—2.5x faster and 3x more accurate than the commonly used pyMatching decoder, while using ten times less training data. Although the Ising models are open-source and available on GitHub, Hugging Face, and build.nvidia.com, they are tightly integrated with Nvidia's proprietary infrastructure, driving GPU dependency. The models are not hardware-agnostic, requiring NVQLink’s low-latency interconnect and CUDA-Q to operate. This approach mirrors Nvidia’s strategy with previous AI tools like Nemotron and Cosmos, allowing it to maintain relevance in quantum computing without manufacturing its own quantum hardware. Major institutions such as Fermilab, Harvard, and IonQ have adopted the Ising models, with IonQ using the calibration model in its quantum systems.

[lemonde.fr lemonde.fr](https://www.lemonde.fr/sciences/article/2025/02/21/ordinateurs-quantiques-microsoft-jette-un-pave-dans-la-mare_6557701_1650684.html)  

Ordinateurs quantiques : Microsoft dit être en mesure de les commercialiser d'ici à quelques années

Microsoft a récemment annoncé un bond technologique majeur dans le domaine des ordinateurs quantiques : la commercialisation possible, d’ici quelques années, d’un ordinateur quantique basé sur des qubits topologiques, avancée qui arrivait plusieurs décennies plus tôt que prévu. La société affirme avoir fabriqué une première puce, appelée « Majorana One », utilisant un matériau topoconducteur qui encapsule des particules de Majorana — ces dernières étant hypothétiquement plus stables car elles seraient leur propre antiparticule. Cette puce contient huit qubits topologiques et pourrait, à terme, en contenir jusqu’à un million dans un format compact. Cependant, des incertitudes demeurent : l’existence expérimentale des particules de Majorana n’est toujours pas définitivement confirmée, bien que les mesures enregistrées par Microsoft soient compatibles avec cette hypothèse. L'annonce est saluée prudemment dans la communauté scientifique, certains chercheurs appelant à une validation plus rigoureuse. Malgré les doutes, Microsoft dévoile une feuille de route ambitieuse visant une architecture quantique tolérante aux pannes reposant sur ces qubits, misant sur une commercialisation industrielle dans un avenir proche.

Calcul quantique : l'inévitable besoin de corriger les erreurs

L'article traite du défi majeur que représente la correction d’erreurs dans le calcul quantique. Les qubits, éléments fondamentaux des ordinateurs quantiques, sont extrêmement sensibles aux perturbations, provoquant fréquemment des erreurs de calcul. Contrairement aux ordinateurs classiques, où les erreurs sont rarissimes, les ordinateurs quantiques actuels génèrent une erreur toutes les 100 à 1 000 opérations, rendant la correction indispensable. Historiquement, Peter Shor a proposé un code correcteur en 1995, suivi du « code de surface » des Russes Kitaev et Bravyi, qui a dominé pendant deux décennies. Depuis quelques années, des avancées notables ont vu le jour, notamment les travaux de Panteleev, Kalachev, Leverrier et Zémor, qui ont augmenté l’efficacité des codes correcteurs et accéléré leur détection d’erreurs. Côté expérimental, Google, Harvard-Quera, IBM et Microsoft ont démontré des progrès significatifs, même si les taux d’erreur restent élevés. Un défi persistant est l’impact des rayons cosmiques et gamma, qui peuvent affecter plusieurs qubits simultanément, échappant aux méthodes actuelles. Malgré les progrès, la correction d’erreurs reste un obstacle majeur pour le calcul quantique à grande échelle.

[elpais.com elpais.com](https://elpais.com/tecnologia/2025-02-20/microsoft-asegura-haber-hallado-un-nuevo-estado-de-la-materia-para-desarrollar-ordenadores-cuanticos-en-pocos-anos.html)  

Microsoft asegura haber hallado un nuevo estado de la materia para desarrollar ordenadores cuánticos en pocos años

Microsoft ha anunciado un avance clave en su objetivo de desarrollar una computadora cuántica funcional y comercializable en pocos años, gracias al hallazgo de un nuevo estado de la materia conocido como "superconductividad topológica". Basado en fermiones de Majorana, partículas teóricas con propiedades cuánticas especiales, la compañía ha creado un procesador llamado Majorana 1 que opera a temperaturas cercanas al cero absoluto y que permite generar cúbits topológicos más estables y resistentes a errores. Este logro representa un hito técnico significativo en la computación cuántica, según investigadores, aunque aún no se ha demostrado inequívocamente la viabilidad completa del cúbit topológico. La partícula de Majorana, predicha hace 88 años, es clave para mantener la coherencia cuántica, uno de los principales desafíos del sector. Microsoft también ha implementado técnicas no destructivas de medición de paridad para validar la funcionalidad de sus cúbits. Sin embargo, expertos del ámbito científico llaman a la cautela, destacando que aunque el avance es prometedor, todavía es temprano para confirmar que esta tecnología pueda integrarse a corto plazo en aplicaciones prácticas.

Aram Harrow, investigador cuántico: "No quedan 10 años para estos ordenadores, llegarán antes"

Aram Harrow, investigador del MIT y pionero en computación cuántica, expresa en una entrevista que los avances recientes indican que los ordenadores cuánticos interesantes, con miles de cúbits, podrían llegar antes de lo previsto. Identifica como clave la mejora de la corrección de errores y la reducción del ruido por cúbit, algo que se compara con una "ley de mejora anual", similar a la Ley de Moore. Harrow destaca el potencial de estos ordenadores en la simulación de moléculas y materiales, así como en la ruptura de cifrados, aunque considera que su impacto será más limitado que el de la inteligencia artificial. Aun así, insiste en que el verdadero valor de la computación cuántica radica en su capacidad de procesar información de formas totalmente nuevas. También apunta posibles aplicaciones indirectas, como en el desarrollo de superconductores que podrían avanzar la energía de fusión. Aunque reconoce que la IA ha desviado atención e inversión, asegura que la computación cuántica sigue creciendo y podría ser clave en problemas científicos muy específicos.

[huffingtonpost.es huffingtonpost.es](https://www.huffingtonpost.es/tecnologia/willow-nuevo-chip-cuantico-google-potencia-calculo-extraordinaria.html)  

Willow, el nuevo chip cuántico de Google con una potencia de cálculo "extraordinaria"

Google ha presentado su nuevo chip cuántico, llamado Willow, el cual representa un importante progreso en el camino hacia la computación cuántica práctica y a gran escala. Willow destaca por su "extraordinaria" potencia de cálculo y su capacidad para corregir errores cuánticos, gracias a una arquitectura que permite reducir exponencialmente los errores conforme se utilizan más cúbits. Este avance es descrito por Google como estar "por debajo del umbral", un hito clave en la corrección cuántica de errores que se intentaba alcanzar desde hace tres décadas. Willow, con 105 cúbits (aunque las pruebas fueron con 101), logró ejecutar en cinco minutos una tarea que a uno de los superordenadores más rápidos del mundo le llevaría un tiempo inconmensurable. El chip también superó las pruebas más exigentes de la computación cuántica, incluyendo el muestreo aleatorio de circuitos, ligado a la llamada "supremacía cuántica". Sin embargo, expertos como Carlos Sabín advierten que, aunque los errores se han reducido significativamente, aún se está lejos de lograr un ordenador cuántico útil, ya que se necesitarían millones de cúbits físicos para realizar cálculos prácticos con miles de cúbits lógicos.

[azure.microsoft.com azure.microsoft.com](https://azure.microsoft.com/en-us/blog/quantum/2025/02/19/microsoft-unveils-majorana-1-the-worlds-first-quantum-processor-powered-by-topological-qubits/?msockid=2e18b3bd622f67ae04bda5fa63bd66b2)  

Microsoft unveils Majorana 1, the world’s first quantum processor powered by topological qubits - Microsoft Azure Quantum Blog

https://azure.microsoft.com/en-us/blog/quantum/2025/02/19/microsoft-unveils-majorana-1-the-worlds-first-quantum-processor-powered-by-topological-qubits/?msockid=2e18b3bd622f67ae04bda5fa63bd66b2

Microsoft unveils Majorana 1, the world’s first quantum processor powered by topological qubits - Microsoft Azure Quantum Blog

February 19, 2025 7 min read MICROSOFT UNVEILS MAJORANA 1, THE WORLD’S FIRST QUANTUM PROCESSOR POWERED BY TOPOLOGICAL QUBITS By Chetan Nayak, Technical Fellow and Corporate Vice President of Quantu...

[quantinuum.com quantinuum.com](https://www.quantinuum.com/blog/built-for-all-introducing-our-new-software-stack)  

Built for All: Introducing Our New Software Stack

https://www.quantinuum.com/blog/built-for-all-introducing-our-new-software-stack

Introducing Helios: The Most Accurate Quantum Computer in the World

INTRODUCING HELIOS: THE MOST ACCURATE QUANTUM COMPUTER IN THE WORLD November 5, 2025 View the presentation Image: A large room with a large rectangular objectAI-generated content may be incorrect....

Helios | Quantinuum's Quantum Computers

INTRODUCING QUANTINUUM HELIOS WHERE LIMITS END AND POSSIBILITIES DAWN Access Now Access Now A MASSIVE LEAP IN OUR WORLD-LEADING QUANTINUUM SYSTEMS Image Quantinuum Helios, Powered by Honeywell,...

Quantinuum and Microsoft achieve breakthrough that unlocks a new era of reliable quantum computing

QUANTINUUM AND MICROSOFT ACHIEVE BREAKTHROUGH THAT UNLOCKS A NEW ERA OF RELIABLE QUANTUM COMPUTING QUANTINUUM’S SYSTEM MODEL H2 ENABLED MICROSOFT’S QUBIT-VIRTUALIZATION SYSTEM TO GENERATE THE MOST R...

Quantinuum | Blog

BLOG ‍ DISCOVER HOW WE ARE PUSHING THE BOUNDARIES IN THE WORLD OF QUANTUM COMPUTING [Input: Search our blog] [Input]corporate [Input]partnership [Input]technical [Input]events technical All...

Technical perspective: By the end of the decade, we will deliver universal, fully fault-tolerant quantum computing

TECHNICAL PERSPECTIVE: BY THE END OF THE DECADE, WE WILL DELIVER UNIVERSAL, FULLY FAULT-TOLERANT QUANTUM COMPUTING September 17, 2024 View the presentation By Dr. Harry Buhrman, Chief Scientist fo...

Quantinuum | Quantum Error Correction

Back to glossary QUANTUM ERROR CORRECTION Quantum error correction (QEC) is a set of techniques used to protect quantum information from errors due to decoherence and other sources of noise. Quantum...

Quantinuum | Quantum Error Correcting Code

QUANTUM ERROR CORRECTING CODE We take the original definition: “A quantum error-correcting code is defined to be a unitary mapping (encoding) of k qubits (2-state quantum systems) into a subspace of...

Real Time Error Correction at Increased Scale

REAL TIME ERROR CORRECTION AT INCREASED SCALE March 16, 2026 View the presentation As quantum computing power grows, so does the difficulty of error correction. Meeting that demand requires tight...

Helios Operation - Quantinuum Systems

HELIOS OPERATION¶ QCCD OPERATION¶ The Helios QPU is a transport-based quantum processor with spatially separate qubit storage regions (memory and cache) and quantum logic regions [1]. The storage z...

Quantinuum Helios - Quantinuum Systems

QUANTINUUM HELIOS¶ DEFAULT NOISE MODEL PARAMETERS¶ [Input] Helios-1E Helios-1E emulators from 2025-11-18¶ Default Settings | Helios-1E General | Qubits (Statevector) | 32 Qubits (Stabilizer) |...

Quantinuum | Blog

In addition to providing a full pipeline for solving this problem, a major aspect of this work was to use the fact that the Jones polynomial is an invariant to introduce a benchmark for noisy quantum...

[explore.openalex.org explore.openalex.org](https://explore.openalex.org/works/w3107463944)  

Quantum computational advantage using photons - OpenAlex

Quantum computational advantage or supremacy is a long-anticipated milestone toward practical quantum computers. 178.7 Cites: 40 Cited by: 2,205 Related to: ...

[sciencedirect.com sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S2352340926006967)  

A dataset of publications and patents on quantum error correction ...

Google Quantum AI and Collaborators. Quantum error correction below the surface code threshold. Nature, 638 (8052) (2025), pp. 920-926, 10.1038/s41586-024 ...

Error estimates and higher order Trotter product formulas in ...

by S Chehade · 2025 · Cited by 5 — Childs, et al. Theory of Trotter error with commutator scaling. Phys. Rev. X, 11 (1) (2021), Article 011020. View in Scopus Google Scholar. [6]. G. Escolano, A ...Read more

[pubmed.ncbi.nlm.nih.gov pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/31645734/)  

Quantum supremacy using a programmable superconducting ...

Quantum supremacy using a programmable superconducting processor. Nature. 2019 Oct;574(7779):505-510. doi: 10.1038/s41586-019-1666-5. Epub ...

Quantum computational advantage using photons - PubMed

Quantum computational advantage using photons. Science. 2020 Dec 18;370(6523):1460-1463. doi: 10.1126/science.abe8770. Epub 2020 Dec 3 ...

[inspirehep.net inspirehep.net](https://inspirehep.net/literature/2821840)  

Quantum error correction below the surface code threshold - INSPIRE

1,269 citations Citations per year. Our system maintains below-threshold performance when decoding in real time, achieving an average decoder ...

Quantum computational advantage using photons - Inspire HEP

1,966 citations Citations per year. Quantum computational advantage or supremacy is a long-anticipated milestone toward practical quantum ...

Generalised Entropy Accumulation

12 Oct 2024 — reference search 26 citations. Citations per year ... This is a generalisation of the entropy accumulation theorem (EAT) (Dupuis et al.Read more

flow-preserving rewriting that ignores the interpretation - Inspire HEP

There and back again: A circuit extraction tale · Miriam Backens(. Birmingham U. ) ,. Hector Miller-Bakewell(. Oxford U. ) ,. Giovanni de Felice ...

Graph-theoretic Simplification of Quantum Circuits with the ...

Graph-theoretic Simplification of Quantum Circuits with the ZX-calculus. Ross Duncan(. Strathclyde U. and; Cambridge U. (main). ) ,. Aleks Kissinger(. Oxford U ...Read more

Renato Renner

25 Nov 2024 — Renato Renner( Zurich, ETH. Renato.Renner.1 PhD Advisor: Ueli Maurer #1 Jef Pauwels , Jul 28, 2026) e-Print: 2607.25838 (May 27, 2026) ...

[reddit.com reddit.com](https://www.reddit.com/r/Physics/comments/d7s3ov/quantum_supremacy_using_a_programmable/)  

Quantum Supremacy Using a Programmable Superconducting ...

In this write-up, however, they push the idea that the device can demonstrate quantum supremacy using a sampling problem as a benchmark. The ...

Quantum error correction below the surface code threshold - Reddit

It's a small step on the way. They've demonstrated that scaling up physical qubits reduces the error threshold for the logical layer.

[collaborate.princeton.edu collaborate.princeton.edu](https://collaborate.princeton.edu/en/publications/quantum-error-correction-below-the-surface-code-threshold/)  

Quantum error correction below the surface code threshold

Google Quantum AI and Collaborators. / Quantum error correction below the surface code threshold. In: Nature. 2025 ; Vol. 638, No. 8052. pp. 920 ...

[datadryad.org datadryad.org](https://datadryad.org/dataset/doi%3A10.5061/dryad.k6t1rj8)  

Data: Quantum supremacy using a programmable superconducting ...

Here, we report using a processor with programmable superconducting qubits to create quantum states on 53 qubits, corresponding to a computational state-space ...

[insti.physics.sunysb.edu insti.physics.sunysb.edu](https://insti.physics.sunysb.edu/~korepin/Teaching/Spring2020/science.abe8770.pdf)  

[PDF] Quantum computational advantage using photons

Cite as: H.-S. Zhong et al., Science. 10.1126/science.abe8770 (2020). REPORTS. First release: 3 December 2020 www.sciencemag.org. (Page numbers ...

[whocitedit.com whocitedit.com](https://whocitedit.com/w/W3107463944/)  

Quantum computational advantage using photons — Who Cited It

Quantum computational advantage using photons (2020) — 2285 citations, its references and the papers citing it, drawn as a graph.

[osti.gov osti.gov](https://www.osti.gov/biblio/1607005)  

Quantum supremacy using a programmable superconducting ... - OSTI

Cited By (71) ; Quantum supremacy using a programmable superconducting processor. Martinis, John; Boixo, Sergio; Neven, Hartmut; Dryad https:// ...

Theory of Trotter Error with Commutator Scaling

by AM Childs · 2021 · Cited by 971 — Citation Formats · Childs, Andrew M., Su, Yuan, Tran, Minh, Wiebe, Nathan O., and Zhu, Suschen. Theory of Trotter Error with Commutator Scaling.Read more

[researchgate.net researchgate.net](https://www.researchgate.net/publication/348231548_Quantum_computational_advantage_using_photons)  

Quantum computational advantage using photons | Request PDF

Evaluation covers eleven IEEE systems from 9 to 300 buses using IBM quantum computing resources, with Gurobi and monolithic QAOA as references.

(PDF) A Theory of Trotter Error

https://www.researchgate.net/publication/338064975\_A\_Theory\_of\_Trotter\_Error

(PDF) Quantum singular value transformation and beyond

7 Jun 2018 — Quantum singular value transformation and beyond: exponential improvements for quantum matrix arithmetics. June 2018. DOI:10.48550/arXiv ...Read more

Quantum isomorphism is equivalent to equality of ...

Quantum isomorphism is equivalent to equality of homomorphism counts from planar graphs. November 2020. DOI:10.1109/FOCS46700.2020.00067. Conference: 2020 IEEE ...

Renato Renner's research works | ETH Zurich, Zürich ...

Our proof relies on a recently developed information-theoretic tool called generalised entropy accumulation and can handle generic prepare-and-measure protocols ...Read more

Predicting Many Properties of a Quantum System from Very ...

Predicting Many Properties of a Quantum System from Very Few Measurements. February 2020. DOI:10.48550/arXiv.2002.08953. Authors: Hsin-Yuan ...Read more

Graph-theoretic Simplification of Quantum Circuits with the ...

Graph-theoretic Simplification of Quantum Circuits with the ZX-calculus. June 2020; Quantum 4:279. DOI:10.22331/q-2020-06-04-279. License; CC BY 4.0. Authors ...Read more

(PDF) CutQC: Using Small Quantum Computers for Large ...

... Simulating Large Quantum Circuits on a Small Quantum Computer. Article. Oct 2020; PHYS REV LETT. Tianyi Peng · Aram Harrow · Maris Ozols ...Read more

Andrew M. Childs Professor at University of Maryland ...

Andrew CHILDS, Professor | Cited by 21408 | of University of Maryland, College Park, College Park (UMD, UMCP, University of Maryland College Park) | Read ...

Number of publications, citations and h-index according to ...

The objective of this work is to identify the set of highly cited documents in Google Scholar and define their core characteristics: their languages, their file ... Read more

[pmc.ncbi.nlm.nih.gov pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC11864966/)  

Quantum error correction below the surface code threshold - PMC

Here we present two below-threshold surface code memories. This section collects any data citations, data availability statements, or supplementary materials ...

[digicoll.lib.berkeley.edu digicoll.lib.berkeley.edu](https://digicoll.lib.berkeley.edu/record/140693)  

Quantum Supremacy using a Programmable Superconducting ...

The promise of quantum computers is that certain computational tasks might be executed exponentially faster on a quantum processor than on a ...

[quantumcomputing.stackexchange.com quantumcomputing.stackexchange.com](https://quantumcomputing.stackexchange.com/questions/75/which-quantum-error-correction-code-has-the-highest-threshold-as-proven-at-the)  

Which quantum error correction code has the highest threshold (as ...

With an assumption of all elements failing with equal probability (and doing so in a certain way) it has a threshold of around 1%. Note that the ...

Understanding Google's “Quantum supremacy using a ...

I was recently going through the paper titled "Quantum supremacy using a programmable superconducting processor" by NASA Ames Research Centre ...

[alphaxiv.org alphaxiv.org](https://www.alphaxiv.org/abs/1910.11333)  

Supplementary information for "Quantum supremacy using a ...

This citation provides the crucial complexity theory argument that sampling from the output of random quantum circuits is a classically hard problem.

Quantum error correction below the surface code threshold | alphaXiv

This citation details a specific implementation of the surface code, which is a key element enabling below-threshold error correction in the main paper.

Quantum computational advantage using photons - alphaXiv

Quantum computational advantage using photons ; HW. Hui Wang ; YD. Yu-Hao Deng ; MC. Ming-Cheng Chen ; LP. Li-Chao Peng ; YL. Yi-Han Luo.

Demonstration of logical qubits and repeated error correction with better-than-physical error rates | alphaXiv

https://www.alphaxiv.org/abs/2404.02280

Simulating Large Quantum Circuits on a Small ...

Simulating Large Quantum Circuits on a Small Quantum Computer. University of ... This cited work is a foundational paper on classical simulation using ...Read more

Predicting Many Properties of a Quantum System from Very Few ...

Predicting Many Properties of a Quantum System from Very Few Measurements · Quantum Fidelity Estimation · Local Properties · Entanglement Entropy · Variational ...

Marco Tomamichel | alphaXiv

https://www.alphaxiv.org/%40marco-tomamichel

[link.aps.org link.aps.org](https://link.aps.org/doi/10.1103/PhysRevLett.131.150601)  

Gaussian Boson Sampling with Pseudo-Photon-Number-Resolving ...

In the quantum computational advantage regime, we use Bayesian tests and correlation function analysis to validate the samples against all current classical ...

Generalized Rényi Entropy Accumulation Theorem and ...

by A Arqand · Cited by 31 — References (113). F. Dupuis, O. Fawzi, and R. Renner, Entropy accumulation, Commun. Math. Phys. 379, 867 (2020). F. Dupuis and O. Fawzi ...Read more

Trotter error with commutator scaling for the Fermi-Hubbard ...

by A Schubert · 2023 · Cited by 27 — Zhu, Theory of Trotter error with commutator scaling, Phys. Rev. X 11, 011020 (2021). Y. Su, H.-Y. Huang, and E. T. Campbell, Nearly tight ...Read more

Simulating Large Quantum Circuits on a Small ... - APS Journals

by T Peng · 2020 · Cited by 478 — Simulating Large Quantum Circuits on a Small Quantum Computer. Tianyi Peng1,†, Aram W. Harrow2, Maris Ozols3, and Xiaodi Wu ...Read more

Trotter error timescaling separation via commutant ...

by YH Chen · 2025 · Cited by 5 — Zhu, Theory of Trotter error with commutator scaling, Phys. Rev. X 11, 011020 (2021). A. M. Childs and Y. Su, Nearly optimal lattice ...Read more

[research-collection.ethz.ch research-collection.ethz.ch](https://www.research-collection.ethz.ch/bitstreams/ff784bf1-6f08-48b5-a9c6-c61d13aba053/download)  

[PDF] Quantum error correction below the surface code threshold

Here we present two below-threshold surface code memories on our newest generation of superconducting processors, Willow: a distance-7 code and ...

Entropy Accumulation

by F Dupuis · 2020 · Cited by 289 — Here we show that entropy accumulation occurs more generally, i.e., without an independence assumption, provided one quantifies the uncertainty about the ...Read more

[kth.se kth.se](https://www.kth.se/social/files/605a065cb6c2ee8b567f2a79/quantum-computation-advantage.pdf)  

[PDF] Quantum computational advantage using photons - KTH

The photonic quantum computer, Jiuzhang, generates up to 76 output photon clicks, which yields an output state- space dimension of 1030 and a ...

[qusoft.org qusoft.org](https://qusoft.org/2023/12/14/the-end-of-2023-marks-the-end-of-harry-buhrmans-leadership-at-qusoft/)  

The end of 2023 marks the end of Harry Buhrman's leadership at ...

As of 15 December 2023, director of QuSoft and famous quantum researcher Harry Buhrman will start a new position. After leaving his position ...

Sitemap - Qusoft

Harry Buhrman in podcast episode. Delta NL awarded 615 million euro from Netherlands' National Growth Fund to accelerate quantum technology

Qusoft – Research center for Quantum software & technology

This research was carried out in CWI's Algorithms and Complexity group, headed by Prof. Harry Buhrman. Other specialised research on quantum condensed matter ...

[PDF] QuSoft Annual Report 2023

Harry Buhrman also left his directorship and departed from CWI to join Quantinuum as the Chief Scientist for Algorithms and Innovation, based in London.

[cmns.umd.edu cmns.umd.edu](https://cmns.umd.edu/news-events/news/nsf-maryland-quantum-simulation-institute-funding)  

NSF Renews Maryland-Led Quantum Simulation Institute's Funding

Established in 2021 with a $25 million federal award, NSF RQS has developed novel ways to verify quantum systems, reduce errors and ...

[quantum-journal.org quantum-journal.org](https://quantum-journal.org/papers/q-2022-11-28-862/)  

On contraction coefficients, partial orders and approximation of ...

In this work, we revisit the notion of contraction coefficients of quantum channels, which provide sharper and specialized versions of the data ...

There and back again: A circuit extraction tale - Quantum Journal

There and back again: A circuit extraction tale. Miriam Backens1 ... The above citations are from Crossref's cited-by service (last ...

NPA Hierarchy for Quantum Isomorphism and ...

by PN Kar · 2026 · Cited by 14 — ``Quantum isomorphism is equivalent to equality of homomorphism counts from planar graphs''. ... The above citations are from SAO/NASA ADS ...

Graph-theoretic Simplification of Quantum Circuits with the ...

by R Duncan · 2020 · Cited by 401 — Graph-theoretic Simplification of Quantum Circuits with the ZX-calculus ... The above citations are from Crossref's cited-by service (last ...Read more

Quantum now fully recognized by Google Scholar

12 Mar 2018 — For older articles, the information will be updated when Google Scholar rebuilds their index in (northern) summer. ... Aram Harrow; Khabat Heshami ...

Quantum now fully recognized by Google Scholar

12 Mar 2018 — For older articles, the information will be updated when Google Scholar rebuilds their index in (northern) summer. ... Harry Buhrman ; Daniel ... Read more

[math.ku.dk math.ku.dk](https://www.math.ku.dk/english/research/qa/news/)  

QA section news – University of Copenhagen

... (QMATH) under the mentorship of Matthias Christandl. Appointment. 2024.09.18. Matthias Christandl appointed Turing Chair. Professor Matthias Christandl has been ...

Guests – University of Copenhagen - Københavns Universitet

Marius Junge (University of Illinois at Urbana-Champaign) , 28.05.2024 ... Matthias Christandl , 21.12.2013 - 07.01.2014; Steffen Lauritzen , 16.12.2013 ...

Nyheder - Institut for Matematiske Fag - Københavns Universitet

Lukas Junge startede som ph.d.-studerende ved QMATH-centeret 1. ... Roberto er tilknyttet forskningsgruppen QMath og vil blive vejledt af Matthias Christandl.

[nsf.gov nsf.gov](https://www.nsf.gov/mps/quantum-leap-challenge-institutes)  

NSF Quantum Leap Challenge Institutes

NSF FTQSAA investigates new methods to make quantum technologies more robust and resistant to the inherent fragility of quantum information.

[tqc.iaqi.org tqc.iaqi.org](https://tqc.iaqi.org/2025/tqc2023/index.html)  

TQC 2023 | TQC Conference 2025

You are always welcome to contact center leader Matthias Cristandl for information about upcoming positions. Come join QMATH Masterclass 2023 from 21st-25th of ...

[mcqst.de mcqst.de](https://www.mcqst.de/MCQST-MEDIA/qip2021/BookletofAbstractsFeb2.pdf)  

[PDF] Booklet of abstracts

Alexander Müller-Hermes and Matthias Christandl. Claude Bernard University of Lyon 1 | University of Copenhagen. Fault-tolerant coding for quantum communication.

[pratt.duke.edu pratt.duke.edu](https://pratt.duke.edu/news/nsf-quantum-simulation-institute/)  

NSF Renews $37.5M Quantum Simulation Institute

The National Science Foundation has renewed the NSF Quantum Leap Challenge Institute for Robust Quantum Simulation (RQS) with a five-year ...

[qtc.umd.edu qtc.umd.edu](https://qtc.umd.edu/news/story/umd-leads-new-25m-nsf-quantum-leap-challenge-institute-for-robust-quantum-simulation)  

UMD Leads New $25M NSF Quantum Leap Challenge Institute for ...

Funded by a $25 million award from NSF, researchers in the UMD-led institute will develop theoretical concepts, design innovative hardware, and ...

[x.com x.com](https://x.com/quantumlight)  

Harry Buhrman (@quantumlight) / X

Honored to have president Macron visit QuSoft, UvA, and Quantum Delta NL! ⁦Good for the European cooperation and the European Quantum Software Institute (EQSI).

Joint Quantum Institute (@JQInews) on X

The NSF Quantum Leap Challenge Institute for Robust Quantum Simulation has renewed its funding, totaling $37.5 million.

Post

... Predicting many properties of a quantum system from very few measurements" https://t.co/YEIn4kokcX reaches 1000 citations. #topcites.

[linkedin.com linkedin.com](https://www.linkedin.com/company/institute-for-robust-quantum-simulation-rqs)  

Institute for Robust Quantum Simulation (RQS) - LinkedIn

... quantum heat engines, and computer science. Supported by a $25 million NSF award, RQS brings together researchers from the University of Maryland, Duke ...

[openresearch.amsterdam openresearch.amsterdam](https://openresearch.amsterdam/en/page/67124/qusoft-celebrates-five-years-of-cutting-edge-quantum-algorithm-and)  

QuSoft celebrates five years of cutting-edge quantum algorithm and ...

Buhrman, co-founder and director of QuSoft, who was recently installed as a member of the Royal Netherlands Academy of Arts and Sciences (KNAW).

[rqs.umd.edu rqs.umd.edu](https://rqs.umd.edu/news/new-ideas-quantum-simulation-bring-additional-federal-funding)  

New Ideas in Quantum Simulation Bring Additional Federal Funding

A $2.5 million supplemental NSF award will jumpstart several new research thrusts in RQS and an undergraduate research program.

[entangledfuture.com entangledfuture.com](https://entangledfuture.com/company/qusoft/)  

QuSoft | Quantum Research

Senior researchers include Harry Buhrman, Ronald de Wolf, Stacey Jeffery, Kareljan Schoutens and Michael Walter. The Amsterdam effort traces ...

[instagram.com instagram.com](https://www.instagram.com/p/Dc1FYdskfr0/)  

nsfgov (NSF) has renewed funding for the @univofmaryland-led ...

@nsfgov (NSF) has renewed funding for the @univofmaryland-led Institute for Robust Quantum Simulation with a five-year award expected to total ...

[caltech.edu caltech.edu](https://www.caltech.edu/about/news/caltechs-institute-for-quantum-information-and-matter-iqim-receives-new-6-year-grant)  

Caltech's Institute for Quantum Information and Matter (IQIM) Receives New 6-Year Grant - www.caltech.edu

https://www.caltech.edu/about/news/caltechs-institute-for-quantum-information-and-matter-iqim-receives-new-6-year-grant

Caltech Awarded $12.6 Million for New Institute for Quantum Information and Matter - www.caltech.edu

https://www.caltech.edu/about/news/caltech-awarded-126-million-new-institute-quantum-information-and-matter-1730

Research – IQIM

RESEARCH The IQIM is driven by the belief that there is a rare convergence of theoretical insights and experimental capabilities that offers remarkable opportunities for discoveries of new principle...

[canada.ca canada.ca](https://www.canada.ca/en/innovation-science-economic-development/news/2023/01/government-of-canada-launches-national-quantum-strategy-to-create-jobs-and-advance-quantum-technologies.html?trk=article-ssr-frontend-pulse_little-text-block)  

Government of Canada launches National Quantum Strategy to create jobs and advance quantum technologies - Canada.ca

https://www.canada.ca/en/innovation-science-economic-development/news/2023/01/government-of-canada-launches-national-quantum-strategy-to-create-jobs-and-advance-quantum-technologies.html?trk=article-ssr-frontend-pulse\_little-text-block

[riken.jp riken.jp](https://www.riken.jp/en/research/labs/rqc/)  

RIKEN Center for Quantum Computing (RQC)

The RIKEN Center for Quantum Computing (RQC) is an internationally unique research organization that develops and owns actual quantum computers. Keisuke Fujii ...

Quantum Computing Theory Research Team | RIKEN

Director: Keisuke Fujii (Ph.D. (Eng.)) We focus on quantum software engineering science, for the realization of quantum computers. Email: keisuke.fujii.ay@ ...

Quantum Information Physics Theory Research Team

Our research group performs interdisciplinary studies at the interface between nanoscience, quantum computing, quantum information processing,

Quantum Computer System Design Research Team | RIKEN

Our laboratory aims to design faster and more scalable quantum computers. Keisuke Fujii, and Yuuki Tokunaga. Quantum Computing Eras"

Mathematical Quantum Information RIKEN Hakubi ...

Our group studies the mathematical underpinnings of quantum information theory, with a particular focus on the investigation of the mathematical structure ...Read more

[cqt.sg cqt.sg](https://www.cqt.sg/people/rahul-jain/)  

Rahul Jain - CQT

Rahul Jain is a CQT Principal Investigator and Associate Professor in the Computer Science Department, National University of Singapore.

Marco Tomamichel - CQT - Centre for Quantum Technologies

https://www.cqt.sg/groups/marco-tomamichel/

Research Groups - CQT

Marco Tomamichel Principal Investigator. Rahul Jain Principal Investigator Research Areas: Basic Science, Quantum Communication & Security, Quantum Processors, ...

[comp.nus.edu.sg comp.nus.edu.sg](https://www.comp.nus.edu.sg/~rahul/allfiles/CV.pdf)  

Rahul Jain

Research Interests Quantum Algorithms, Information Theory, Associate Professor, Department of Computer Science, and Principal Investigator, Centre for Quantum ...

https://www.comp.nus.edu.sg/~rahul/

https://www.comp.nus.edu.sg/~rahul/

[fujitsu.com fujitsu.com](https://www.fujitsu.com/global/about/resources/news/press-releases/2023/0324-01.html)  

Japanese joint research group launches quantum ...

24 Mar 2023 — Keisuke Fujii, Ph.D., Deputy Director and Professor. Leader, Quantum Computing Theory Research Team, RIKEN Center for Quantum Computing)

[rqc.riken.jp rqc.riken.jp](https://rqc.riken.jp/en/)  

RIKEN QUANTUM COMPUTING

The RIKEN Center for Quantum Computing (RQC) explores the frontier of quantum technologies through the research and development of quantum computers as ...

[scholar.google.co.jp scholar.google.co.jp](https://scholar.google.co.jp/citations?hl=ja&user=CS6HdE0AAAAJ)  

Keisuke Fujii

Quantum reservoir computing: a reservoir approach toward quantum machine learning on near-term quantum devices. K Fujii, K Nakajima. Reservoir Computing ...Read more

[nature.com nature.com](https://www.nature.com/articles/d42473-023-00091-y)  

Fast tracking quantum-computing tech

Keisuke Fujii, deputy director of the Center for Quantum Information and Quantum Biology (QIQB) at Osaka University in Japan. making it the largest quantum ...

Spectral analysis of product formulas for quantum simulation

by C Yi · 2022 · Cited by 45 — Theory of trotter error with commutator scaling. Phys. Rev. X 11, 011020 (2021). Google Scholar. Childs, A. M. & Su, Y. Nearly optimal lattice ...Read more

Parallel quantum simulation of large systems on small ...

by F Barratt · 2021 · Cited by 127 — Peng, T., Harrow, A. W., Ozols, M. & Wu, X. Simulating large quantum circuits on a small quantum computer. Phys. Rev. Lett. 125, 150504 (2020).Read more

Efficient learning for linear properties of bounded-gate ...

by Y Du · 2025 · Cited by 22 — -Y., Kueng, R. & Preskill, J. Predicting many properties of a quantum system from very few measurements . Nat. Phys. 16, 1050–1057 (2020). Read more

Spin signature of majorana fermions in topological nodal-point superconductors | npj Quantum Materials

Spin signature of majorana fermions in topological nodal-point superconductors Download PDF Download PDF \* Article \* Open access \* Published: 15 May 2025 SPIN SIGNATURE OF MAJORANA FERMIONS IN TO...

Enhanced Majorana stability in a three-site Kitaev chain | Nature Nanotechnology

Enhanced Majorana stability in a three-site Kitaev chain Download PDF Download PDF \* Article \* Open access \* Published: 31 March 2025 ENHANCED MAJORANA STABILITY IN A THREE-SITE KITAEV CHAIN \* A...

Solving the Bernstein-Vazirani problem using Majorana-based topological quantum algorithms | npj Quantum Information

Solving the Bernstein-Vazirani problem using Majorana-based topological quantum algorithms \* Article \* Open access \* Published: 19 November 2025 SOLVING THE BERNSTEIN-VAZIRANI PROBLEM USING MAJORAN...

Topological prethermal strong zero modes on superconducting processors | Nature

Topological prethermal strong zero modes on superconducting processors Download PDF Download PDF \* Article \* Open access \* Published: 27 August 2025 TOPOLOGICAL PRETHERMAL STRONG ZERO MODES ON SU...

On the robustness of topological gap detection via transport | Nature

\* Matters Arising \* Published: 24 June 2026 ON THE ROBUSTNESS OF TOPOLOGICAL GAP DETECTION VIA TRANSPORT \* Henry F. Legg ORCID: orcid.org/0000-0003-0400-5370^{1,2} Nature volume 654, pages E22–E2...

[majulab.cnrs.fr majulab.cnrs.fr](https://majulab.cnrs.fr/quantum-information-computation/)  

Quantum Information & Computation

Rahul JAIN, Professor at NUS and Principal Investigator. Centre for Quantum Technologies, National University Singapore & Director … hosted by CQT, Centre for ...

[nrf.gov.sg nrf.gov.sg](https://www.nrf.gov.sg/resources/quantum-research-coordination-between-astar-and-nus-and-combined-annual-funding/)  

Quantum Research coordination between ASTAR and NUS and Combined Annual Funding | National Research Foundation, Singapore (NRF)

https://www.nrf.gov.sg/resources/quantum-research-coordination-between-astar-and-nus-and-combined-annual-funding/

[qiqb.osaka-u.ac.jp qiqb.osaka-u.ac.jp](https://qiqb.osaka-u.ac.jp/en/members/article/K_Fujii)  

FUJII Keisuke | QIQB: Center for Quantum Information and ...

I am involved in both theoretical and software research on quantum computing. My interests include designing and evaluating methodologies and algorithms to ...Read more

[nqo.sg nqo.sg](https://nqo.sg/programmes/qep/projects/)  

QEP R&D Projects

Lead PI: Marco Tomamichel, NUS. We aim to advance spin-based qubits as a basic quantum computing resource through materials engineering in semiconductors. ...

[eeas.europa.eu eeas.europa.eu](https://www.eeas.europa.eu/sites/default/files/11_27_kohei_itoh_keio_univ.pdf)  

Quantum Computing in Japan - EEAS

Program Director : K. ITOH. ➢ Superconducting Quantum Computers : Prof. Y. NAKAMURA et.al. ➢ Quantum AI : Prof. K. FUJII et.Read more

[quantumsg.org quantumsg.org](https://quantumsg.org/category/quantum-information/)  

Quantum Information

CQT, MSE, & Dept. of Physics, NUS. Read More · Marco Tomamichel · Marco Tomamichel. By Evon Tan|2020-04-09T13:08:30+08:00August 2nd, 2019|. CQT & ECE, NUS. Read ...Read more

[physics.nus.edu.sg physics.nus.edu.sg](https://www.physics.nus.edu.sg/fundamental-quantum-physics-and-quantum-technologies/)  

Fundamental Quantum Physics and Quantum Technologies | NUS Physics

https://www.physics.nus.edu.sg/fundamental-quantum-physics-and-quantum-technologies/

[cde.nus.edu.sg cde.nus.edu.sg](https://cde.nus.edu.sg/mse/news/shaping-the-future-of-quantum-technology/)  

Shaping the future of quantum technology – Materials Science and Engineering

https://cde.nus.edu.sg/mse/news/shaping-the-future-of-quantum-technology/

[theguardian.com theguardian.com](https://www.theguardian.com/technology/2025/feb/19/topoconductor-chip-quantum-computing-topological-qubits-microsoft)  

Microsoft unveils chip it says could bring quantum computing within years

Microsoft has announced a significant breakthrough in quantum computing with the development of a new chip powered by the world’s first "topoconductor." This innovation potentially brings the construction of reliable quantum computers within years rather than decades. The topoconductor enables the creation of topological qubits, using a new state of matter distinct from solid, liquid, or gas, which may lead to more compact and reliable quantum systems. This could allow quantum computers to scale to millions of qubits, vastly enhancing their power to tackle complex problems, including environmental cleanup, advanced materials, logistics, and encryption. The breakthrough has been documented in a peer-reviewed paper published in Nature and has garnered cautious optimism from experts, who acknowledge its technical promise but emphasize the challenges ahead. Microsoft’s approach involves Majorana fermions — elusive particles that facilitate more robust qubit designs — but constructing such systems remains complex. The U.S. defense research agency DARPA has selected Microsoft’s topoconductor approach as one of two main routes it is exploring to build usable quantum computers by 2033. Experts note Microsoft’s long-term strategy may provide a more resilient platform compared to its competitors, such as Google and PsiQuantum, who use different technological paths.

[businessinsider.com businessinsider.com](https://www.businessinsider.com/amazon-exec-casts-doubt-microsoft-quantum-claims-2025-3)  

'BS and hype': Amazon execs cast doubt on Microsoft's quantum-computing claims in private discussions

Amazon executives have privately criticized Microsoft's recent claims of a significant quantum computing breakthrough, calling them exaggerated and unsubstantiated. Microsoft unveiled a new quantum processor, "Majorana 1," asserting it could lead to high-performance quantum computing using topological qubits. However, in internal communications, Amazon’s head of quantum technologies, Simone Severini, and others expressed skepticism, arguing the supporting scientific paper lacks evidence of such a breakthrough and only provides potential directions for future experiments. Amazon executives pointed out Microsoft's history of retracted research and categorized the company's announcement as "next level" hype. Notably, Amazon's quantum hardware lead Oskar Painter, compared Microsoft's efforts unfavorably to those of Google and IBM, describing the announcement as marketing-driven rather than scientifically significant. Experts from academia echoed this sentiment, labeling Microsoft’s claim as overhyped and not yet peer-validated. Meanwhile, Amazon and Microsoft continue to diverge on expectations for quantum computing’s viability, with Microsoft predicting utility-scale applications within years, while Amazon anticipates commercial usefulness could still be decades away. Overall, while the increasing activity in quantum computing signals growing interest, some warn the hype could outpace actual technological progress.

[theverge.com theverge.com](https://www.theverge.com/tech/956450/nature-microsoft-quantum-computing-majorana-1-claims)  

A new paper argues Microsoft exaggerated its quantum claims a year ago

A recent article in \*Nature\* critiques Microsoft's claims about its quantum computing technology, specifically the Majorana 1 chip introduced in February 2025. The chip is based on a newly touted innovation: topological qubits, theoretically built on Majorana particles, which Microsoft says are foundational for their future quantum computers. However, Henry Legg, a physicist at the University of St Andrews, challenges this claim, arguing that Microsoft's data does not conclusively prove the existence of Majorana particles and instead may reflect signatures from quantum dots, which do not support quantum computing. Legg originally posted his critique on March 11, 2025, and it took over a year to be peer-reviewed and published. Microsoft disputes Legg's interpretation, standing by their results and commitment to scientific rigor. Despite the criticism, Microsoft has already launched a follow-up chip, Majorana 2, in June 2026, reaffirming its roadmap to build a scalable quantum computer by 2029. Legg maintains that the same fundamental issues persist in the newer device. The debate highlights ongoing skepticism in the scientific community about Microsoft’s approach amid broader uncertainties surrounding practical quantum computing breakthroughs.

[as.com as.com](https://as.com/meristation/betech/el-dispositivo-que-cabe-en-la-palma-de-la-mano-puede-resolver-un-problema-que-ningun-ordenador-puede-asi-es-el-chip-de-computacion-cuantica-n/)  

El dispositivo que cabe en la palma de la mano puede resolver un problema que ningún ordenador puede: así es el chip de computación cuántica

Microsoft ha presentado el chip cuántico Majorana 1, un dispositivo revolucionario basado en la arquitectura “Topological Core” que utiliza un innovador material llamado topoconductor. Este chip, que cabe en la palma de la mano, emplea partículas conocidas como Majoranas para crear qubits más estables y potencialmente escalables, abordando así uno de los principales retos de la computación cuántica: la inestabilidad de los qubits. La compañía asegura que esta nueva tecnología podría escalar hasta un millón de qubits, el umbral necesario para aplicaciones prácticas a gran escala. Este avance podría transformar múltiples industrias, desde la medicina hasta la sostenibilidad ambiental. Sin embargo, existen dudas dentro de la comunidad científica. Investigadores como Vincent Mourik muestran escepticismo ante el enfoque de Microsoft, citando la falta de pruebas computacionales tangibles y recordando fallos previos, como la retirada de un estudio en 2018. Mientras tanto, los expertos instan a la cautela hasta que se validen experimentalmente los avances anunciados.

[pt.wikipedia.org pt.wikipedia.org](https://pt.wikipedia.org/wiki/Majorana_1)  

Majorana 1

https://pt.wikipedia.org/wiki/Majorana\_1

[ru.wikipedia.org ru.wikipedia.org](https://ru.wikipedia.org/wiki/Majorana_1)  

Majorana 1

https://ru.wikipedia.org/wiki/Majorana\_1

[es.wikipedia.org es.wikipedia.org](https://es.wikipedia.org/wiki/Majorana_1)  

Majorana 1

https://es.wikipedia.org/wiki/Majorana\_1

[it.wikipedia.org it.wikipedia.org](https://it.wikipedia.org/wiki/Majorana_1)  

Majorana 1

https://it.wikipedia.org/wiki/Majorana\_1

[openalex.org openalex.org](https://openalex.org/W2604467189)  

Quantum advantage with shallow circuits

https://openalex.org/W2604467189

Quantum Algorithms for Fidelity Susceptibility: From Quantum Criticality to Metrology

https://openalex.org/W7127622095

Holographic codes from hyperinvariant tensor networks

https://openalex.org/W4388593305

[dtic.minsky.ai dtic.minsky.ai](https://dtic.minsky.ai/index/10.1103%2Fphysrevx.11.011020)  

Theory of Trotter Error with Commutator Scaling 10.1103/physrevx.11.011020 - Minsky DTIC

https://dtic.minsky.ai/index/10.1103%2Fphysrevx.11.011020

[hpcwire.com hpcwire.com](https://www.hpcwire.com/2024/07/02/quantinuum-cu-succeed-implementing-non-local-qlpds-correction-code/)  

HPCwire - Since 1987 – Covering the Fastest Computers in the World and the People Who Run Them

https://www.hpcwire.com/2024/07/02/quantinuum-cu-succeed-implementing-non-local-qlpds-correction-code/

[emergentmind.com emergentmind.com](https://www.emergentmind.com/papers/2406.02666)  

Entangling four logical qubits beyond break-even in a nonlocal code

https://www.emergentmind.com/papers/2406.02666

Quantum Singular Value Transformation

14 Aug 2025 — Quantum singular value transformation and beyond: exponential improvements for quantum matrix arithmetics (2018). 4. Hamiltonian simulation ...Read more

[hacker-linner.com hacker-linner.com](https://www.hacker-linner.com/events/logical-qubits-error-correction-better-than-physical/)  

Demonstration of logical qubits and repeated error correction with better-than-physical error rates：逻辑量子比特与重复纠错实验突破物理错误率基线 · 黑客下午茶

https://www.hacker-linner.com/events/logical-qubits-error-correction-better-than-physical/

[phys.org phys.org](https://phys.org/news/2024-04-quantinuum-quantum-microsoft-logical-bits.html)  

Quantinuum quantum computer using Microsoft's 'logical quantum bits' runs 14,000 experiments with no errors

https://phys.org/news/2024-04-quantinuum-quantum-microsoft-logical-bits.html

[ir.cwi.nl ir.cwi.nl](https://ir.cwi.nl/pub/28780/)  

Centrum Wiskunde & Informatica: Quantum singular value transformation and beyond: Exponential improvements for quantum matrix arithmetics

https://ir.cwi.nl/pub/28780/

[journals.aps.org journals.aps.org](https://journals.aps.org/prapplied/abstract/10.1103/PhysRevApplied.11.034021)  

Boosting Computational Power through Spatial Multiplexing in Quantum Reservoir Computing | Phys. Rev. Applied

https://journals.aps.org/prapplied/abstract/10.1103/PhysRevApplied.11.034021

[semanticscholar.org semanticscholar.org](https://www.semanticscholar.org/paper/Quantum-singular-value-transformation-and-beyond%3A-Gily%C3%A9n-Su/fa00b2c3d2fe8326470c47a3e5f5d1e716e58cb3)  

[PDF] Quantum singular value transformation and beyond

Quantum singular value transformation and beyond: exponential improvements for quantum matrix arithmetics · András Gilyén, Yuan Su, +1 author. N. Wiebe ...Read more

Hector Miller-Bakewell | Semantic Scholar

Hector Miller-Bakewell ; There and back again: A circuit extraction tale · Miriam Backens · Quantum ; Finite Verification of Infinite Families of Diagram Equations.

Predicting many properties of a quantum system from very ...

Predicting many properties of a quantum system from very few measurements · Hsin-Yuan Huang, R. Kueng, J. Preskill · Published in Nature Physics 18 February 2020 ...Read more

Graph-theoretic Simplification of Quantum Circuits with the ...

Graph-theoretic Simplification of Quantum Circuits with the ZX-calculus ... 255 Citations. Filters. Sort by Relevance, Sort by Most Influenced Papers, Sort by ...Read more

J. Preskill

Semantic Scholar profile for J. Preskill, with 2500 highly influential citations and 224 scientific research papers. h-index 75 Citations43,865 Highly ...

Andrew M. Childs

Semantic Scholar profile for Andrew M. Childs, with 1112 highly influential citations and 129 scientific research papers. Publications129 h-index 55 Citations ...

[link.springer.com link.springer.com](https://link.springer.com/article/10.1007/s00220-020-03839-5)  

Entropy Accumulation | Communications in Mathematical ...

by F Dupuis · 2020 · Cited by 302 — Entropy Accumulation. Open access; Published: 23 September 2020. Volume 379, pages 867–913 (2020); Cite this article. You have full access to ...Read more

[ieeexplore.ieee.org ieeexplore.ieee.org](https://ieeexplore.ieee.org/abstract/document/9317964/)  

Quantum isomorphism is equivalent to equality of ...

by L Mančinska · 2020 · Cited by 133 — Quantum isomorphism is equivalent to equality of homomorphism counts from planar graphs. Abstract: Over 50 years ago, Lovász proved that two ...

[pennylane.ai pennylane.ai](https://pennylane.ai/demos/tutorial_intro_qsvt)  

Intro to QSVT | PennyLane Demos

22 May 2023 — References. [1]. András Gilyén, Yuan Su, Guang Hao Low, Nathan Wiebe, “Quantum singular value transformation and beyond: exponential ...Read more

ZX-Calculus Intermediate Representation - PennyLane

[3] "There and back again: A circuit extraction tale", Miriam Backens, Hector Miller-Bakewell, Giovanni de Felice, Leo Lobski, John van de Wetering, arXiv ...

Introduction to the ZX-calculus | PennyLane Demos

5 Jun 2023 — “Graph-theoretic Simplification of Quantum Circuits with the ZX-calculus.” Quantum Journal. [9]. Aleks Kissinger and John van de Wetering ...Read more

Classical shadows | PennyLane Demos

13 Jun 2021 — Huang, Hsin-Yuan, Richard Kueng, and John Preskill, “Predicting many properties of a quantum system from very few measurements”, Nature ...Read more

[repository.ubn.ru.nl repository.ubn.ru.nl](https://repository.ubn.ru.nl/handle/2066/232803)  

There and back again: A circuit extraction tale - Radboud Repository

There and back again: A circuit extraction tale. Find Full text. Publication year. 2021. Author(s). Backens, Miriam · Miller-Bakewell, Hector · Felice, Giovanni ...

[math.uwaterloo.ca math.uwaterloo.ca](https://www.math.uwaterloo.ca/~cgodsil/quagmire/qmorphs/pdfs/qplanar_focs_final.pdf)  

Quantum isomorphism is equivalent to equality of ...

by L Mancinska · Cited by 133 — Abstract—Over 50 years ago, Lovász proved that two graphs are isomorphic if and only if they admit the same number of homomorphisms from any graph.

[leolob.ski leolob.ski](https://leolob.ski/files/zx-gflow.pdf)  

[PDF] There and back again: A circuit extraction tale - Leo Lobski

There and back again: A circuit extraction tale. Miriam Backens, Hector Miller-Bakewell, Giovanni de Felice,. Leo Lobski and John van de Wetering. QPL 2020. 1 ...

[orbit.dtu.dk orbit.dtu.dk](https://orbit.dtu.dk/en/publications/quantum-isomorphism-is-equivalent-to-equality-of-homomorphism-cou/)  

Quantum isomorphism is equivalent to equality of ...

Mancinska, Laura ; Roberson, David E. / Quantum isomorphism is equivalent to equality of homomorphism counts from planar graphs. Proceedings of IEEE 61st Annual ...

[dl.acm.org dl.acm.org](https://dl.acm.org/doi/10.1145/3313276.3316366)  

Quantum singular value transformation and beyond

23 Jun 2019 — Quantum singular value transformation and beyond: exponential improvements for quantum matrix arithmetics. Authors: András Gilyén. András ...Read more

CutQC: using small Quantum computers for large ...

Simulating large quantum circuits on a small quantum computer. Physical Review Letters 125, 15 ( 2020 ), 150504. Crossref · Google Scholar. [37]. Charles E ...Read more

[scholar.google.nl scholar.google.nl](https://scholar.google.nl/citations?hl=en&user=4gdnMJYAAAAJ)  

András Gilyén

Quantum singular value transformation and beyond: exponential improvements for quantum matrix arithmetics. A Gilyén, Y Su, GH Low, N Wiebe. Proceedings of the ...Read more

World-Renowned Researcher Harry Buhrman Joins ...

Harry Buhrman , Ph.D., a renowned and distinguished complexity theorist and quantum computing scientist, has joined its team as Chief Scientist for Algorithms ...

[scholar.google.com.sg scholar.google.com.sg](https://scholar.google.com.sg/citations?hl=th&user=yDlqLwsAAAAJ)  

‪Miriam Backens‬ - ‪Google Scholar‬

There and back again: A circuit extraction tale. M Backens, H Miller-Bakewell, G de Felice, L Lobski, J van de Wetering. Quantum 5, 421, 2021. 159, 2021.

John Preskill

John Preskill Richard P. Feynman Professor of Theoretical Physics, California Institute of Technology … quantum computingquantum informationtheoretical ...

Marco Tomamichel

Professor at ECE/CDE and CQT, National University of Singapore … h-index 51 42. Renato Renner Renato RennerProfessor for Theoretical Physics, Marco Tomamichel ...

Google Scholar Metrics Help

https://scholar.google.com.sg/intl/en/scholar/metrics.html

[hal.science hal.science](https://hal.science/hal-05038521v1)  

Generalised entropy accumulation

This is a generalisation of the entropy accumulation theorem (EAT), which deals with a more restrictive model of side information: there, past side information ...

[tseppelt.github.io tseppelt.github.io](https://tseppelt.github.io/homind-database/)  

Homomorphism Indistinguishability Zoo

Mančinska and Roberson (2020): L. Mančinska and D. E. Roberson, 'Quantum isomorphism is equivalent to equality of homomorphism counts from planar graphs', in ...

[pureportal.strath.ac.uk pureportal.strath.ac.uk](https://pureportal.strath.ac.uk/en/publications/graph-theoretic-simplification-of-quantum-circuits-with-the-zx-ca/persons/)  

Graph-theoretic simplification of quantum circuits with the ZX- ...

Graph-theoretic simplification of quantum circuits with the ZX-calculus. Ross Duncan, Aleks Kissinger, Simon Perdrix, John van de Wetering.

[scispace.com scispace.com](https://scispace.com/papers/predicting-many-properties-of-a-quantum-system-from-very-few-34o7c4w7n4)  

Predicting many properties of a quantum system from very few ...

Predicting many properties of a quantum system from very few measurements ; Elements of information theory · Thomas M. Cover, · 31 Dec 1990 ; Quantum Computation ...

Renato Renner | ETH Zurich | 297 Publications

Renato Renner is an academic researcher from ETH Zurich. The author has an hindex of 73, co-authored 284 publications. Previous affiliations of Renato Renner ...

[pubs.rsc.org pubs.rsc.org](https://pubs.rsc.org/dd/article/4/12/3540/889079/Estimating-Trotter-approximation-errors-to)  

Estimating Trotter approximation errors to optimize ...

by SG Mehendale · 2025 · Cited by 12 — Google Scholar. 6. A. M.. Childs. ,. Y. Su. ,. M. C.. Tran. ,. N. Wiebe. and. S. Zhu. ,. Theory of trotter error with commutator scaling. ,.Read more

[pure.uva.nl pure.uva.nl](https://pure.uva.nl/ws/files/178706749/1904.00102v2.pdf)  

UvA-DARE (Digital Academic Repository)

by T Peng · Cited by 478 — Simulating large quantum circuits on a small quantum computer. Peng, T.; Harrow, A.W.; Ozols, M.; Wu, X. DOI. 10.48550/arXiv.1904.00102 · 10.1103/PhysRevLett ...Read more

[mindat.org mindat.org](https://www.mindat.org/reference.php?id=13939560)  

Huang, Hsin-Yuan, Kueng, Richard, Preskill, John (2020) ...

Huang, Hsin-Yuan, Kueng, Richard, Preskill, John (2020) Predicting many properties of a quantum system from very few measurements. Nature Physics, 16 (10) 1050- ...

[drops.dagstuhl.de drops.dagstuhl.de](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ICALP.2022.119)  

Circuit Extraction for ZX-Diagrams Can Be #P-Hard - DROPS

28 Jun 2022 — Graph-theoretic Simplification of Quantum Circuits with the ZX-calculus. Quantum, 4:279, June 2020. URL: https://doi.org/10.22331/q-2020-06 ...Read more

[scholar.google.com.au scholar.google.com.au](https://scholar.google.com.au/citations?hl=th&user=yEGt2NAAAAAJ)  

Yuan Su

Theory of trotter error with commutator scaling. AM Childs, Y Su, MC Tran, N Wiebe, S Zhu. Physical Review X 11 (1), 011020, 2021. 985, 2021 ; Toward the first ...

[scribd.com scribd.com](https://www.scribd.com/document/990281048/s41567-020-0932-7)  

Predicting many properties of a quantum system

Predicting Many Properties of A Quantum System From Very Few Measurements ... Any methods, additional references, Nature Research report- 2171–2180 (2004).Read more

[ouci.dntb.gov.ua ouci.dntb.gov.ua](https://ouci.dntb.gov.ua/en/works/4z1RPZK7/)  

Hybrid Quantum-Classical Circuit Simplification with the ZX ...

... Graph-theoretic simplification of quantum circuits with the ZX-calculus. Quantum 4, 279 (2020) DOI: 10.22331/q-2020-06-04-279; Duncan, R., Lucas, M ...

[qiti.iqc.uwaterloo.ca qiti.iqc.uwaterloo.ca](https://qiti.iqc.uwaterloo.ca/publications/)  

Publications | QUANTUM INFORMATION WITH TRAPPED IONS

https://qiti.iqc.uwaterloo.ca/publications/

Towards Large Scale Quantum Simulations with Trapped Ions: Programmable XY model, Precise Light Sensing, and Extreme High Vacuum | QUANTUM INFORMATION WITH TRAPPED IONS

https://qiti.iqc.uwaterloo.ca/publications/2024-nikhil-kotibhaskar-phd-thesis/

News | QUANTUM INFORMATION WITH TRAPPED IONS

https://qiti.iqc.uwaterloo.ca/news/

[research.com research.com](https://research.com/u/aram-w-harrow)  

2026 Aram W. Harrow - Computer Science

2026 research profile of Aram W. Harrow, a leading Computer Science researcher. Explore H-index, citation metrics, awards, key publications, and academic ...

2026 Andrew M. Childs: Computer Science Researcher

Childs, a leading Computer Science researcher. Explore H-index, citation metrics, awards, key publications, and academic impact based on Research.com data.

2026 Renato Renner - Computer Science

2026 research profile of Renato Renner, a leading Computer Science researcher. Explore H-index, citation metrics, awards, key publications, and academic ...

2026 John Preskill - Physics

2026 research profile of John Preskill, a leading Physics researcher. Explore H-index, citation metrics, awards, key publications, and academic impact based ...

2026 Marco Tomamichel: Mathematics Researcher – H-Index, Publications & Awards | Research.com

https://research.com/u/marco-tomamichel

Best Mathematics Scientists 2026

Compare the best scientists in Mathematics for 2026 . Discover Research.com annual Best Mathematics Scientists.

[citationmap.com citationmap.com](https://citationmap.com/profile/OEBtlWgAAAAJ)  

Renato Renner — h-index 82, 28K citations | CitationMap

Renato Renner's h-index is 82 (157 i10-index, 27,727+ total citations across 270+ publications) according to Google Scholar as of July 2026.

[scholar.google.com.br scholar.google.com.br](https://scholar.google.com.br/citations?hl=th&user=7MOW-j4AAAAJ)  

Andrew M. Childs

Joint Center for Quantum Information and Computer Science, University of Maryland - ‪‪อ้างอิงโดย 23680 รายการ‬‬ … ดัชนี h 63 50

[scholar.google.es scholar.google.es](https://scholar.google.es/citations?hl=ja&user=6WYsaqMAAAAJ)  

aram harrow

h 指標 55 43 … aram harrow aram harrow Physics, Quantum supremacy through the quantum approximate optimization algorithm

[web.mit.edu web.mit.edu](https://web.mit.edu/aram/www/)  

Aram Harrow

Aram Harrow ; 2027 PhD applications: I hope to recruit one new grad student starting in Fall 2027. ; research interests: quantum algorithms, information and ...

[scholar.google.com.hk scholar.google.com.hk](https://scholar.google.com.hk/citations?hl=vi&user=K2BMBtcAAAAJ)  

John Preskill

Feynman Professor of Theoretical Physics, California Institute of Technology … h-index 92 72 i10-index. J Preskill Physical review letters 85. Preskill Journal ...

[scholar.google.co.th scholar.google.co.th](https://scholar.google.co.th/citations?hl=th&user=wlOytxsAAAAJ)  

‪Harry Buhrman‬ - ‪Google Scholar‬

Harry Buhrman Chief Scientist Q Algorithms @ Quantinuum, Professor Univ. of Amsterdam & Founding Director. Quantum ComputingComplexity TheoryKolmogorov

[scholar.google.pt scholar.google.pt](https://scholar.google.pt/citations?hl=fil&user=6hjdwrsAAAAJ)  

Laura Mančinska

Associate Professor at QMATH, University of Copenhagen - 2440 h - index 22 16 i10- index 35 26. L Mancinska , T Islam,

[adscientificindex.com adscientificindex.com](https://adscientificindex.com/scientist/marco-tomamichel/413233/)  

Marco Tomamichel – Natural Sciences / Physics | AD Scientific Index

https://adscientificindex.com/scientist/marco-tomamichel/413233/

[scholarlyindex.com scholarlyindex.com](https://scholarlyindex.com/)  

Harry Buhrman | Top1000 Scholar

H - index . 86i10-index. 41Best World rank. Top 0.47%Best statistical percentile. 30 ... Scholarly Index Top1000 Scholar · 2026 Edition · Public BetaMethodology. Read more

[sites.google.com sites.google.com](https://sites.google.com/site/justincsong/publications)  

Quantum Materials Theory - Publications & Pre-prints

Quantum Materials Theory and Mesoscopics ; 2026. Kramers Dichroism in PT Symmetric Magnets. Oles Matsyshyn, Ying Xiong, Justin CW Song\*, ; Physical Review ... Read more

[linhuli.com linhuli.com](https://linhuli.com/)  

Publications - LLH @ quantumsc

Non-Academic Publications ( 2026 -02-28. Control of Bulk non-Hermitian Systems, 174205 ( 2026 ).

[aiche.org aiche.org](https://www.aiche.org/)  

Harry Buhrman

Harry Buhrman is chief scientist quantum algorithms & innovation at Quantinuum . He is also professor of algorithms, complexity theory, and quantum computing ...

[quantumsystemsaccelerator.org quantumsystemsaccelerator.org](https://quantumsystemsaccelerator.org/)  

Publications – QSA

The publications below highlight a small selection of the most recent 2025– 2026 papers led by QSA. SEARCH PUBLICATIONS ON GOOGLE SCHOLAR . 2026 . Parity-doublet ... Read more

[purigroup.research.yale.edu purigroup.research.yale.edu](https://purigroup.research.yale.edu/)  

Publications | Puri Group - Yale University

(2016). Google Scholar Link. Google Scholar - Shruti Puri(Link is external). Patents. Quantum Information Processing with an asymmetric error channel, WO2020 ... Read more

[ox.ac.uk ox.ac.uk](https://dbonto.cs.ox.ac.uk/quantum/)  

Quantum Group

QUANTUM GROUP We are a group focused on quantum computation and the foundations of quantum theory. The group is led by Professor Jonathan Barrett and Professor Aleks Kissinger. Other faculty in the...

Aleks Kissinger – Department of Computer Science, University of Oxford

ALEKS KISSINGER ASSOCIATE PROFESSOR OF QUANTUM COMPUTING, UNIVERSITY OF OXFORD Image He has ten years of research experience and over 50 publications in quantum computation, automated reasoning, g...

[nih.gov nih.gov](https://pubmed.ncbi.nlm.nih.gov/39653125/)  

Quantum error correction below the surface code threshold - PubMed

QUANTUM ERROR CORRECTION BELOW THE SURFACE CODE THRESHOLD Google Quantum AI and Collaborators. Nature. 2025 Feb. AUTHOR Google Quantum AI and Collaborators COLLABORATORS \* Google Quantum AI and C...

[microsoft.com microsoft.com](https://www.microsoft.com/en-us/research/publication/roadmap-to-fault-tolerant-quantum-computation-using-topological-qubit-arrays/?lang=ko-kr)  

Roadmap to fault tolerant quantum computation using topological qubit arrays - Microsoft Research

ROADMAP TO FAULT TOLERANT QUANTUM COMPUTATION USING TOPOLOGICAL QUBIT ARRAYS \* David Aasen , February 2025 BibTex 다운로드 We describe a concrete device roadmap towards a fault-tolerant quantum compu...

Ideas: Quantum computing redefined with Chetan Nayak - Microsoft Research

IDEAS IDEAS: QUANTUM COMPUTING REDEFINED WITH CHETAN NAYAK Published February 19, 2025 By Gretchen Huizinga , Host of the Microsoft Research Podcast Dr. Chetan Nayak , Technical Fellow Image: Out...

Microsoft unveils Majorana 1, the world’s first quantum processor powered by topological qubits - Microsoft Azure Quantum Blog

REVOLUTIONIZING QUANTUM CONTROL THROUGH DIGITAL PRECISION This readout technique enables a fundamentally different approach to quantum computing in which measurements are used to perform calculations...

Microsoft Quantum | Topological qubits

Topological qubits \* Fundamentals \* Hardware A quantum machine capable of solving challenging scientific and commercial problems will ultimately require at least one million stable qubits that can...

Microsoft’s Majorana 1 chip carves new path for quantum computing - Source

MICROSOFT’S MAJORANA 1 CHIP CARVES NEW PATH FOR QUANTUM COMPUTING \* Image WRITTEN BY \* Catherine Bolgar PUBLISHED February 19, 2025 Microsoft today introduced Majorana 1, the world’s first quan...

Microsoft’s Majorana 1 chip carves new path for quantum computing - Source

DESIGNING QUANTUM MATERIALS ATOM BY ATOM Microsoft’s topological qubit architecture has aluminum nanowires joined together to form an H. Each H has four controllable Majoranas and makes one qubit. Th...

The quantum quest at Microsoft - Microsoft Research

MICROSOFT RESEARCH BLOG THE QUANTUM QUEST AT MICROSOFT Published July 6, 2015 Quantum computing has the potential to utterly overturn what it means to compute. At Microsoft, we have been studying...

In a historic milestone, Azure Quantum demonstrates formerly elusive physics needed to build scalable topological qubits - Source

\* Category: Innovation March 14, 2022 IN A HISTORIC MILESTONE, AZURE QUANTUM DEMONSTRATES FORMERLY ELUSIVE PHYSICS NEEDED TO BUILD SCALABLE TOPOLOGICAL QUBITS BY \* Jennifer Langston Image Micros...

Chip Majorana 1 dari Microsoft Membuka Jalan Baru bagi Komputasi Kuantum - Source Asia

Image: Picture of Microsoft's newest chip CHIP MAJORANA 1 DARI MICROSOFT MEMBUKA JALAN BARU BAGI KOMPUTASI KUANTUM PUBLISHED 20 Februari 2025 KATEGORI \* AI TAG: \* AI \* Product development \* Te...

Issues Archive | Signal Magazine

Source Signal Magazine Learn more about Signal magazine ISSUE 05 Welcome to issue five of Signal magazine Every edition of Signal magazine is packed with stories of innovation, and issue five is...

Microsoft stellt Majorana 1 vor – den weltweit ersten Quantenprozessor mit topologischen Qubits - Source EMEA

19\. Feber 2025 \* Kategorie: Company News MICROSOFT STELLT MAJORANA 1 VOR – DEN WELTWEIT ERSTEN QUANTENPROZESSOR MIT TOPOLOGISCHEN QUBITS Image Gebaut mit einer neuen Materialklasse namens Topocon...

Microsoft presenta Majorana 1, el primer procesador cuántico del mundo impulsado por qubits topológicos - Source LATAM

\* Categoría: Noticias de Microsoft febrero 19, 2025 MICROSOFT PRESENTA MAJORANA 1, EL PRIMER PROCESADOR CUÁNTICO DEL MUNDO IMPULSADO POR QUBITS TOPOLÓGICOS CONSTRUIDO CON UNA CLASE INNOVADORA DE MA...

[quantumai.google quantumai.google](https://quantumai.google/qecmilestone)  

Milestone 2 | Google Quantum AI

OUR QUANTUM ERROR CORRECTION MILESTONE The Google Quantum AI team has made an important step towards the development of a large-scale useful quantum computer. This breakthrough is the first demonstr...

[googleblog.com googleblog.com](https://developers.googleblog.com/unlocking-the-potential-of-quantum-computing-a-developers-guide-to-error-correction/)  

Unlocking the Potential of Quantum Computing - Google Developers Blog

UNLOCKING THE POTENTIAL OF QUANTUM COMPUTING DEC. 9, 2024 Austin Fowler Research Scientist Google Quantum AI A DEVELOPER’S GUIDE TO ERROR CORRECTION Manipulating quantum states on a superconducti...

Connector sources scanned

No connector sources scanned

## 公开 Activity（页面顺序）

Research activity

Planning a broad quantum-computing review

I’m organizing a deep, current review of major mathematical quantum-computing teams, prioritizing primary sources and defining a practical set of roughly 15–20 prominent groups rather than attempting every team worldwide. I’m also considering how to report citation metrics responsibly: Google Scholar is preferred, but where direct counts aren’t available, I may need to label alternative databases as approximate and state the date clearly.

Searching

[Open source iqim.caltech.edu](https://iqim.caltech.edu/profile/john-preskill/)  
[Open source www.quics.umd.edu](https://www.quics.umd.edu/people/andrew-childs)  
[Open source uwaterloo.ca](https://uwaterloo.ca/institute-for-quantum-computing/profiles/john-watrous)  
[Open source preskill.caltech.edu](https://preskill.caltech.edu/)  
[Open source magazine.caltech.edu](https://magazine.caltech.edu/post/iqim-quantum-john-preskill)  
[Open source www.cs.umd.edu](https://www.cs.umd.edu/~amchilds/)  
[Open source qc.uwaterloo.ca](https://qc.uwaterloo.ca/)  
[Open source publications.uwaterloo.ca](https://publications.uwaterloo.ca/quantum-impact-2021/quantum-champions/)  
[Open source www.its.caltech.edu](https://www.its.caltech.edu/~preskill/)  

Searching

[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Renato_Renner)  
[Open source de.wikipedia.org](https://de.wikipedia.org/wiki/Renato_Renner)  
[Open source arxiv.org](https://arxiv.org/abs/1412.8553)  
[Open source www.livescience.com](https://www.livescience.com/physics-mathematics/quantum-physics/physicists-achieve-perfect-randomness-for-the-first-time-ever)  

Searching

[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Renato_Renner)  
[Open source www.thetimes.co.uk](https://www.thetimes.co.uk/article/uk-quantum-firm-oxford-ionics-sold-to-us-rival-ion-q-for-11bn-w55plxwrx)  
[Open source www.livescience.com](https://www.livescience.com/physics-mathematics/quantum-physics/physicists-achieve-perfect-randomness-for-the-first-time-ever)  
[Open source www.barrons.com](https://www.barrons.com/articles/ionq-quantum-computing-oxford-ionics-a791d8a5)  
[Open source www.ft.com](https://www.ft.com/content/dde7bac2-cacb-4deb-9223-5bcfe285db15)  
[Open source de.wikipedia.org](https://de.wikipedia.org/wiki/Renato_Renner)  
[Open source arxiv.org](https://arxiv.org/abs/quant-ph/0512258)  

Searching

[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Renato_Renner)  
[Open source www.thetimes.co.uk](https://www.thetimes.co.uk/article/uk-quantum-firm-oxford-ionics-sold-to-us-rival-ion-q-for-11bn-w55plxwrx)  
[Open source www.livescience.com](https://www.livescience.com/physics-mathematics/quantum-physics/physicists-achieve-perfect-randomness-for-the-first-time-ever)  
[Open source www.barrons.com](https://www.barrons.com/articles/ionq-quantum-computing-oxford-ionics-a791d8a5)  
[Open source www.ft.com](https://www.ft.com/content/dde7bac2-cacb-4deb-9223-5bcfe285db15)  
[Open source de.wikipedia.org](https://de.wikipedia.org/wiki/Renato_Renner)  

Searching

[Open source www.cs.ox.ac.uk](https://www.cs.ox.ac.uk/people/aleks.kissinger/)  
[Open source www.cwi.nl](https://www.cwi.nl/en/news/qusoft-research-center-quantum-software-launch/)  
[Open source www.qusoft.com](https://www.qusoft.com/about/)  
[Open source oqi.web.ox.ac.uk](https://oqi.web.ox.ac.uk/people/aleks-kissinger)  
[Open source qmath.ku.dk](https://qmath.ku.dk/)  
[Open source qit.ethz.ch](https://qit.ethz.ch/)  
[Open source www.livescience.com](https://www.livescience.com/physics-mathematics/quantum-physics/physicists-achieve-perfect-randomness-for-the-first-time-ever)  
[Open source www.wired.com](https://www.wired.com/2017/05/happens-mix-thermodynamics-quantum-world-revolution)  
[Open source www.ft.com](https://www.ft.com/content/dde7bac2-cacb-4deb-9223-5bcfe285db15)  

Searching

[Open source quantum.ustc.edu.cn](https://quantum.ustc.edu.cn/web/en/node/32)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=Dc-RSPv9FT8)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Pan_Jianwei)  
[Open source quantumzeitgeist.com](https://quantumzeitgeist.com/pan-jianwei-the-chinese-quantum-pioneer/)  
[Open source www.facebook.com](https://www.facebook.com/scmp/posts/the-breakthrough-establishes-a-core-element-required-for-general-purpose-quantum/1395934735915908/)  
[Open source scholar.google.com](https://scholar.google.com/citations?hl=zh-CN&user=RERrJ6UAAAAJ)  
[Open source app.thequantuminsider.com](https://app.thequantuminsider.com/company/cbb4538e-06bc-4578-a67d-c1204c17874d/profile)  
[Open source fr.wikipedia.org](https://fr.wikipedia.org/wiki/Jiuzhang)  
[Open source www.reuters.com](https://www.reuters.com/world/asia-pacific/china-likely-have-standards-post-quantum-crytography-3-years-expert-says-2026-03-19/)  
[Open source arxiv.org](https://arxiv.org/abs/2106.15534)  

Searching

[Open source quantum.ustc.edu.cn](https://quantum.ustc.edu.cn/web/en/node/32)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=Dc-RSPv9FT8)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Pan_Jianwei)  
[Open source quantumzeitgeist.com](https://quantumzeitgeist.com/pan-jianwei-the-chinese-quantum-pioneer/)  
[Open source www.facebook.com](https://www.facebook.com/scmp/posts/the-breakthrough-establishes-a-core-element-required-for-general-purpose-quantum/1395934735915908/)  
[Open source scholar.google.com](https://scholar.google.com/citations?hl=zh-CN&user=RERrJ6UAAAAJ)  
[Open source app.thequantuminsider.com](https://app.thequantuminsider.com/company/cbb4538e-06bc-4578-a67d-c1204c17874d/profile)  
[Open source fr.wikipedia.org](https://fr.wikipedia.org/wiki/Jiuzhang)  
[Open source www.reuters.com](https://www.reuters.com/world/asia-pacific/china-likely-have-standards-post-quantum-crytography-3-years-expert-says-2026-03-19/)  

Searching

[Open source physics.mit.edu](https://physics.mit.edu/faculty/aram-harrow/)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=dU8_wSDhIFU)  
[Open source mitibm.mit.edu](https://mitibm.mit.edu/people/aram-harrow/)  
[Open source english.elpais.com](https://english.elpais.com/technology/2026-06-05/aram-harrow-quantum-researcher-these-computers-wont-take-10-years-theyll-arrive-sooner.html)  
[Open source theoryofcomputing.org](https://theoryofcomputing.org/articles/v010a003/about.html)  
[Open source scholar.google.com](https://scholar.google.com/citations?hl=en&user=6WYsaqMAAAAJ)  
[Open source www.icmat.es](https://www.icmat.es/news/07-04-26-en/)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Aram_Harrow)  
[Open source zh.wikipedia.org](https://zh.wikipedia.org/wiki/%E9%98%BF%E6%8B%89%E5%A7%86%C2%B7%E5%93%88%E7%BE%85)  
[Open source arxiv.org](https://arxiv.org/abs/quant-ph/0512255)  

Searching

[Open source physics.mit.edu](https://physics.mit.edu/faculty/aram-harrow/)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=dU8_wSDhIFU)  
[Open source mitibm.mit.edu](https://mitibm.mit.edu/people/aram-harrow/)  
[Open source english.elpais.com](https://english.elpais.com/technology/2026-06-05/aram-harrow-quantum-researcher-these-computers-wont-take-10-years-theyll-arrive-sooner.html)  
[Open source theoryofcomputing.org](https://theoryofcomputing.org/articles/v010a003/about.html)  
[Open source scholar.google.com](https://scholar.google.com/citations?hl=en&user=6WYsaqMAAAAJ)  
[Open source www.icmat.es](https://www.icmat.es/news/07-04-26-en/)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Aram_Harrow)  
[Open source zh.wikipedia.org](https://zh.wikipedia.org/wiki/%E9%98%BF%E6%8B%89%E5%A7%86%C2%B7%E5%93%88%E7%BE%85)  

Searching

[Open source research.google](https://research.google/blog/making-quantum-error-correction-work/)  
[Open source blog.google](https://blog.google/innovation-and-ai/technology/research/google-willow-quantum-chip/)  
[Open source www.ibm.com](https://www.ibm.com/roadmaps/quantum/2026/)  
[Open source doi.org](https://doi.org/10.1038/s41586-024-08449-y)  
[Open source www.reuters.com](https://www.reuters.com/business/ibm-says-key-quantum-computing-algorithm-can-run-conventional-amd-chips-2025-10-24/)  
[Open source www.livescience.com](https://www.livescience.com/technology/computing/this-is-easily-the-most-powerful-quantum-computer-on-earth-scientists-unveil-helios-a-record-breaking-quantum-system)  
[Open source www.tomshardware.com](https://www.tomshardware.com/tech-industry/artificial-intelligence/nvidia-releases-ising-open-ai-models)  
[Open source www.lemonde.fr](https://www.lemonde.fr/sciences/article/2025/02/21/ordinateurs-quantiques-microsoft-jette-un-pave-dans-la-mare_6557701_1650684.html)  
[Open source elpais.com](https://elpais.com/tecnologia/2025-02-20/microsoft-asegura-haber-hallado-un-nuevo-estado-de-la-materia-para-desarrollar-ordenadores-cuanticos-en-pocos-anos.html)  
[Open source www.huffingtonpost.es](https://www.huffingtonpost.es/tecnologia/willow-nuevo-chip-cuantico-google-potencia-calculo-extraordinaria.html)  

Searching

[Open source www.ibm.com](https://www.ibm.com/quantum/blog/qldpc-codes)  
[Open source azure.microsoft.com](https://azure.microsoft.com/en-us/blog/quantum/2025/02/19/microsoft-unveils-majorana-1-the-worlds-first-quantum-processor-powered-by-topological-qubits/?msockid=2e18b3bd622f67ae04bda5fa63bd66b2)  
[Open source www.quantinuum.com](https://www.quantinuum.com/blog/built-for-all-introducing-our-new-software-stack)  

Searching

[Open source arxiv.org](https://arxiv.org/abs/2408.13687)  
[Open source research.google](https://research.google/blog/quantum-supremacy-using-a-programmable-superconducting-processor/)  
[Open source explore.openalex.org](https://explore.openalex.org/works/w3107463944)  
[Open source www.sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S2352340926006967)  
[Open source pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/31645734/)  
[Open source inspirehep.net](https://inspirehep.net/literature/2821840)  
[Open source www.reddit.com](https://www.reddit.com/r/Physics/comments/d7s3ov/quantum_supremacy_using_a_programmable/)  
[Open source collaborate.princeton.edu](https://collaborate.princeton.edu/en/publications/quantum-error-correction-below-the-surface-code-threshold/)  
[Open source datadryad.org](https://datadryad.org/dataset/doi%3A10.5061/dryad.k6t1rj8)  
[Open source insti.physics.sunysb.edu](https://insti.physics.sunysb.edu/~korepin/Teaching/Spring2020/science.abe8770.pdf)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=o7knWfVC4J4)  
[Open source whocitedit.com](https://whocitedit.com/w/W3107463944/)  
[Open source www.osti.gov](https://www.osti.gov/biblio/1607005)  
[Open source www.researchgate.net](https://www.researchgate.net/publication/348231548_Quantum_computational_advantage_using_photons)  
[Open source pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC11864966/)  
[Open source digicoll.lib.berkeley.edu](https://digicoll.lib.berkeley.edu/record/140693)  
[Open source quantumcomputing.stackexchange.com](https://quantumcomputing.stackexchange.com/questions/75/which-quantum-error-correction-code-has-the-highest-threshold-as-proven-at-the)  
[Open source www.alphaxiv.org](https://www.alphaxiv.org/abs/1910.11333)  
[Open source link.aps.org](https://link.aps.org/doi/10.1103/PhysRevLett.131.150601)  
[Open source www.research-collection.ethz.ch](https://www.research-collection.ethz.ch/bitstreams/ff784bf1-6f08-48b5-a9c6-c61d13aba053/download)  
[Open source www.kth.se](https://www.kth.se/social/files/605a065cb6c2ee8b567f2a79/quantum-computation-advantage.pdf)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/OpenAlex)  

Searching

[Open source arxiv.org](https://arxiv.org/abs/2408.13687)  
[Open source research.google](https://research.google/blog/quantum-supremacy-using-a-programmable-superconducting-processor/)  
[Open source explore.openalex.org](https://explore.openalex.org/works/w3107463944)  
[Open source www.sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S2352340926006967)  
[Open source pubmed.ncbi.nlm.nih.gov](https://pubmed.ncbi.nlm.nih.gov/31645734/)  
[Open source inspirehep.net](https://inspirehep.net/literature/2821840)  
[Open source www.reddit.com](https://www.reddit.com/r/Physics/comments/d7s3ov/quantum_supremacy_using_a_programmable/)  
[Open source collaborate.princeton.edu](https://collaborate.princeton.edu/en/publications/quantum-error-correction-below-the-surface-code-threshold/)  
[Open source datadryad.org](https://datadryad.org/dataset/doi%3A10.5061/dryad.k6t1rj8)  
[Open source insti.physics.sunysb.edu](https://insti.physics.sunysb.edu/~korepin/Teaching/Spring2020/science.abe8770.pdf)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=o7knWfVC4J4)  
[Open source whocitedit.com](https://whocitedit.com/w/W3107463944/)  
[Open source www.osti.gov](https://www.osti.gov/biblio/1607005)  
[Open source www.researchgate.net](https://www.researchgate.net/publication/348231548_Quantum_computational_advantage_using_photons)  
[Open source pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC11864966/)  
[Open source digicoll.lib.berkeley.edu](https://digicoll.lib.berkeley.edu/record/140693)  
[Open source quantumcomputing.stackexchange.com](https://quantumcomputing.stackexchange.com/questions/75/which-quantum-error-correction-code-has-the-highest-threshold-as-proven-at-the)  
[Open source www.alphaxiv.org](https://www.alphaxiv.org/abs/1910.11333)  
[Open source link.aps.org](https://link.aps.org/doi/10.1103/PhysRevLett.131.150601)  

Searching

[Open source qmath.ku.dk](https://qmath.ku.dk/about/news/)  
[Open source qusoft.org](https://qusoft.org/2023/12/14/the-end-of-2023-marks-the-end-of-harry-buhrmans-leadership-at-qusoft/)  
[Open source cmns.umd.edu](https://cmns.umd.edu/news-events/news/nsf-maryland-quantum-simulation-institute-funding)  
[Open source quantum-journal.org](https://quantum-journal.org/papers/q-2022-11-28-862/)  
[Open source quantumzeitgeist.com](https://quantumzeitgeist.com/quantum-simulators-advance-375m-nsf/)  
[Open source www.math.ku.dk](https://www.math.ku.dk/english/research/qa/news/)  
[Open source www.cwi.nl](https://www.cwi.nl/en/news/famous-quantum-researcher-harry-buhrman-takes-on-new-position-in-londons-business-community/)  
[Open source www.nsf.gov](https://www.nsf.gov/mps/quantum-leap-challenge-institutes)  
[Open source tqc.iaqi.org](https://tqc.iaqi.org/2025/tqc2023/index.html)  
[Open source www.facebook.com](https://www.facebook.com/JQInews/posts/the-nsf-quantum-leap-challenge-institute-for-robust-quantum-simulation-has-renew/1697575739044508/)  
[Open source www.mcqst.de](https://www.mcqst.de/MCQST-MEDIA/qip2021/BookletofAbstractsFeb2.pdf)  
[Open source pratt.duke.edu](https://pratt.duke.edu/news/nsf-quantum-simulation-institute/)  
[Open source qtc.umd.edu](https://qtc.umd.edu/news/story/umd-leads-new-25m-nsf-quantum-leap-challenge-institute-for-robust-quantum-simulation)  
[Open source x.com](https://x.com/quantumlight)  
[Open source www.linkedin.com](https://www.linkedin.com/company/institute-for-robust-quantum-simulation-rqs)  
[Open source openresearch.amsterdam](https://openresearch.amsterdam/en/page/67124/qusoft-celebrates-five-years-of-cutting-edge-quantum-algorithm-and)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Harry_Buhrman)  
[Open source rqs.umd.edu](https://rqs.umd.edu/news/new-ideas-quantum-simulation-bring-additional-federal-funding)  
[Open source entangledfuture.com](https://entangledfuture.com/company/qusoft/)  
[Open source www.instagram.com](https://www.instagram.com/p/Dc1FYdskfr0/)  

Searching

[Open source qmath.ku.dk](https://qmath.ku.dk/about/news/)  
[Open source qusoft.org](https://qusoft.org/2023/12/14/the-end-of-2023-marks-the-end-of-harry-buhrmans-leadership-at-qusoft/)  
[Open source cmns.umd.edu](https://cmns.umd.edu/news-events/news/nsf-maryland-quantum-simulation-institute-funding)  
[Open source quantum-journal.org](https://quantum-journal.org/papers/q-2022-11-28-862/)  
[Open source quantumzeitgeist.com](https://quantumzeitgeist.com/quantum-simulators-advance-375m-nsf/)  
[Open source www.math.ku.dk](https://www.math.ku.dk/english/research/qa/news/)  
[Open source www.cwi.nl](https://www.cwi.nl/en/news/famous-quantum-researcher-harry-buhrman-takes-on-new-position-in-londons-business-community/)  
[Open source www.nsf.gov](https://www.nsf.gov/mps/quantum-leap-challenge-institutes)  
[Open source tqc.iaqi.org](https://tqc.iaqi.org/2025/tqc2023/index.html)  
[Open source www.facebook.com](https://www.facebook.com/JQInews/posts/the-nsf-quantum-leap-challenge-institute-for-robust-quantum-simulation-has-renew/1697575739044508/)  
[Open source www.mcqst.de](https://www.mcqst.de/MCQST-MEDIA/qip2021/BookletofAbstractsFeb2.pdf)  
[Open source pratt.duke.edu](https://pratt.duke.edu/news/nsf-quantum-simulation-institute/)  
[Open source qtc.umd.edu](https://qtc.umd.edu/news/story/umd-leads-new-25m-nsf-quantum-leap-challenge-institute-for-robust-quantum-simulation)  
[Open source x.com](https://x.com/quantumlight)  
[Open source www.linkedin.com](https://www.linkedin.com/company/institute-for-robust-quantum-simulation-rqs)  
[Open source openresearch.amsterdam](https://openresearch.amsterdam/en/page/67124/qusoft-celebrates-five-years-of-cutting-edge-quantum-algorithm-and)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Harry_Buhrman)  
[Open source rqs.umd.edu](https://rqs.umd.edu/news/new-ideas-quantum-simulation-bring-additional-federal-funding)  

Searching

[Open source uwaterloo.ca](https://uwaterloo.ca/institute-for-quantum-computing/news/2024-year-in-review)  
[Open source www.caltech.edu](https://www.caltech.edu/about/news/caltechs-institute-for-quantum-information-and-matter-iqim-receives-new-6-year-grant)  
[Open source www.canada.ca](https://www.canada.ca/en/innovation-science-economic-development/news/2023/01/government-of-canada-launches-national-quantum-strategy-to-create-jobs-and-advance-quantum-technologies.html?trk=article-ssr-frontend-pulse_little-text-block)  
[Open source www.reuters.com](https://www.reuters.com/business/eu-turns-private-funding-boost-quantum-technology-ambition-2025-07-02/)  
[Open source www.ft.com](https://www.ft.com/content/0a16281f-6bb4-4e60-a6f0-3a9d6f8d764a)  

Searching

[Open source www.riken.jp](https://www.riken.jp/en/research/labs/rqc/)  
[Open source www.cqt.sg](https://www.cqt.sg/people/rahul-jain/)  
[Open source www.comp.nus.edu.sg](https://www.comp.nus.edu.sg/~rahul/allfiles/CV.pdf)  
[Open source www.fujitsu.com](https://www.fujitsu.com/global/about/resources/news/press-releases/2023/0324-01.html)  
[Open source scholar.google.com](https://scholar.google.com/citations?hl=en&user=zzHzz7wAAAAJ)  
[Open source rqc.riken.jp](https://rqc.riken.jp/en/)  
[Open source scholar.google.co.jp](https://scholar.google.co.jp/citations?hl=ja&user=CS6HdE0AAAAJ)  
[Open source www.nature.com](https://www.nature.com/articles/d42473-023-00091-y)  
[Open source www.facebook.com](https://www.facebook.com/quantumlah/?locale=fr_FR)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=5T561IxrSm8)  
[Open source majulab.cnrs.fr](https://majulab.cnrs.fr/quantum-information-computation/)  
[Open source www.nrf.gov.sg](https://www.nrf.gov.sg/resources/quantum-research-coordination-between-astar-and-nus-and-combined-annual-funding/)  
[Open source qiqb.osaka-u.ac.jp](https://qiqb.osaka-u.ac.jp/en/members/article/K_Fujii)  
[Open source nqo.sg](https://nqo.sg/programmes/qep/projects/)  
[Open source www.eeas.europa.eu](https://www.eeas.europa.eu/sites/default/files/11_27_kohei_itoh_keio_univ.pdf)  
[Open source quantumsg.org](https://quantumsg.org/category/quantum-information/)  
[Open source www.physics.nus.edu.sg](https://www.physics.nus.edu.sg/fundamental-quantum-physics-and-quantum-technologies/)  
[Open source cde.nus.edu.sg](https://cde.nus.edu.sg/mse/news/shaping-the-future-of-quantum-technology/)  
[Open source www.livescience.com](https://www.livescience.com/technology/computing/japan-launches-its-first-homegrown-quantum-computer)  

Searching

[Open source www.riken.jp](https://www.riken.jp/en/research/labs/rqc/)  
[Open source www.cqt.sg](https://www.cqt.sg/people/rahul-jain/)  
[Open source www.comp.nus.edu.sg](https://www.comp.nus.edu.sg/~rahul/allfiles/CV.pdf)  
[Open source www.fujitsu.com](https://www.fujitsu.com/global/about/resources/news/press-releases/2023/0324-01.html)  
[Open source scholar.google.com](https://scholar.google.com/citations?hl=en&user=zzHzz7wAAAAJ)  
[Open source rqc.riken.jp](https://rqc.riken.jp/en/)  
[Open source scholar.google.co.jp](https://scholar.google.co.jp/citations?hl=ja&user=CS6HdE0AAAAJ)  
[Open source www.nature.com](https://www.nature.com/articles/d42473-023-00091-y)  
[Open source www.facebook.com](https://www.facebook.com/quantumlah/?locale=fr_FR)  
[Open source www.youtube.com](https://www.youtube.com/watch?v=5T561IxrSm8)  
[Open source majulab.cnrs.fr](https://majulab.cnrs.fr/quantum-information-computation/)  
[Open source www.nrf.gov.sg](https://www.nrf.gov.sg/resources/quantum-research-coordination-between-astar-and-nus-and-combined-annual-funding/)  
[Open source qiqb.osaka-u.ac.jp](https://qiqb.osaka-u.ac.jp/en/members/article/K_Fujii)  
[Open source nqo.sg](https://nqo.sg/programmes/qep/projects/)  
[Open source www.eeas.europa.eu](https://www.eeas.europa.eu/sites/default/files/11_27_kohei_itoh_keio_univ.pdf)  
[Open source quantumsg.org](https://quantumsg.org/category/quantum-information/)  
[Open source www.physics.nus.edu.sg](https://www.physics.nus.edu.sg/fundamental-quantum-physics-and-quantum-technologies/)  
[Open source cde.nus.edu.sg](https://cde.nus.edu.sg/mse/news/shaping-the-future-of-quantum-technology/)  

Searching

[Open source arxiv.org](https://arxiv.org/abs/2406.02666)  
[Open source www.theguardian.com](https://www.theguardian.com/technology/2025/feb/19/topoconductor-chip-quantum-computing-topological-qubits-microsoft)  
[Open source www.businessinsider.com](https://www.businessinsider.com/amazon-exec-casts-doubt-microsoft-quantum-claims-2025-3)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Majorana_1)  
[Open source www.theverge.com](https://www.theverge.com/tech/956450/nature-microsoft-quantum-computing-majorana-1-claims)  
[Open source www.lemonde.fr](https://www.lemonde.fr/sciences/article/2024/04/22/calcul-quantique-l-inevitable-besoin-de-corriger-les-erreurs_6229240_1650684.html)  
[Open source as.com](https://as.com/meristation/betech/el-dispositivo-que-cabe-en-la-palma-de-la-mano-puede-resolver-un-problema-que-ningun-ordenador-puede-asi-es-el-chip-de-computacion-cuantica-n/)  
[Open source pt.wikipedia.org](https://pt.wikipedia.org/wiki/Majorana_1)  
[Open source ru.wikipedia.org](https://ru.wikipedia.org/wiki/Majorana_1)  
[Open source zh.wikipedia.org](https://zh.wikipedia.org/wiki/%E7%89%A9%E7%90%86%E9%87%8F%E5%AD%90%E6%AF%94%E7%89%B9%E4%B8%8E%E9%80%BB%E8%BE%91%E9%87%8F%E5%AD%90%E6%AF%94%E7%89%B9)  
[Open source es.wikipedia.org](https://es.wikipedia.org/wiki/Majorana_1)  
[Open source elpais.com](https://elpais.com/tecnologia/2025-02-20/microsoft-asegura-haber-hallado-un-nuevo-estado-de-la-materia-para-desarrollar-ordenadores-cuanticos-en-pocos-anos.html)  
[Open source it.wikipedia.org](https://it.wikipedia.org/wiki/Majorana_1)  

Searching

[Open source arxiv.org](https://arxiv.org/abs/2406.02666)  
[Open source www.theguardian.com](https://www.theguardian.com/technology/2025/feb/19/topoconductor-chip-quantum-computing-topological-qubits-microsoft)  
[Open source www.businessinsider.com](https://www.businessinsider.com/amazon-exec-casts-doubt-microsoft-quantum-claims-2025-3)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Majorana_1)  
[Open source www.theverge.com](https://www.theverge.com/tech/956450/nature-microsoft-quantum-computing-majorana-1-claims)  
[Open source www.lemonde.fr](https://www.lemonde.fr/sciences/article/2024/04/22/calcul-quantique-l-inevitable-besoin-de-corriger-les-erreurs_6229240_1650684.html)  
[Open source as.com](https://as.com/meristation/betech/el-dispositivo-que-cabe-en-la-palma-de-la-mano-puede-resolver-un-problema-que-ningun-ordenador-puede-asi-es-el-chip-de-computacion-cuantica-n/)  
[Open source pt.wikipedia.org](https://pt.wikipedia.org/wiki/Majorana_1)  
[Open source ru.wikipedia.org](https://ru.wikipedia.org/wiki/Majorana_1)  
[Open source zh.wikipedia.org](https://zh.wikipedia.org/wiki/%E7%89%A9%E7%90%86%E9%87%8F%E5%AD%90%E6%AF%94%E7%89%B9%E4%B8%8E%E9%80%BB%E8%BE%91%E9%87%8F%E5%AD%90%E6%AF%94%E7%89%B9)  
[Open source es.wikipedia.org](https://es.wikipedia.org/wiki/Majorana_1)  

Searching

[Open source openalex.org](https://openalex.org/W2604467189)  

Searching

[Open source www.research-collection.ethz.ch](https://www.research-collection.ethz.ch/items/31ab361d-11ce-466b-aa35-86702fff0753)  
[Open source doi.org](https://doi.org/10.1103%2FPhysRevX.11.011020)  
[Open source openalex.org](https://openalex.org/W4388593305)  
[Open source www.researchgate.net](https://www.researchgate.net/publication/338064975_A_Theory_of_Trotter_Error)  
[Open source dtic.minsky.ai](https://dtic.minsky.ai/index/10.1103%2Fphysrevx.11.011020)  

Searching

[Open source www.alphaxiv.org](https://www.alphaxiv.org/abs/2404.02280)  
[Open source www.hpcwire.com](https://www.hpcwire.com/2024/07/02/quantinuum-cu-succeed-implementing-non-local-qlpds-correction-code/)  
[Open source www.emergentmind.com](https://www.emergentmind.com/papers/2406.02666)  
[Open source www.hacker-linner.com](https://www.hacker-linner.com/events/logical-qubits-error-correction-better-than-physical/)  
[Open source phys.org](https://phys.org/news/2024-04-quantinuum-quantum-microsoft-logical-bits.html)  
[Open source ir.cwi.nl](https://ir.cwi.nl/pub/28780/)  
[Open source journals.aps.org](https://journals.aps.org/prapplied/abstract/10.1103/PhysRevApplied.11.034021)  

Searching

[Open source arxiv.org](https://arxiv.org/abs/1806.01838)  
[Open source www.semanticscholar.org](https://www.semanticscholar.org/paper/Quantum-singular-value-transformation-and-beyond%3A-Gily%C3%A9n-Su/fa00b2c3d2fe8326470c47a3e5f5d1e716e58cb3)  
[Open source link.springer.com](https://link.springer.com/article/10.1007/s00220-020-03839-5)  
[Open source quantum-journal.org](https://quantum-journal.org/papers/q-2021-03-25-421/)  
[Open source ieeexplore.ieee.org](https://ieeexplore.ieee.org/abstract/document/9317964/)  
[Open source pennylane.ai](https://pennylane.ai/demos/tutorial_intro_qsvt)  
[Open source inspirehep.net](https://inspirehep.net/literature/2852843)  
[Open source repository.ubn.ru.nl](https://repository.ubn.ru.nl/handle/2066/232803)  
[Open source www.math.uwaterloo.ca](https://www.math.uwaterloo.ca/~cgodsil/quagmire/qmorphs/pdfs/qplanar_focs_final.pdf)  
[Open source www.researchgate.net](https://www.researchgate.net/publication/325592400_Quantum_singular_value_transformation_and_beyond_exponential_improvements_for_quantum_matrix_arithmetics)  
[Open source www.research-collection.ethz.ch](https://www.research-collection.ethz.ch/items/31ab361d-11ce-466b-aa35-86702fff0753)  
[Open source leolob.ski](https://leolob.ski/files/zx-gflow.pdf)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Quantum_singular_value_transformation)  
[Open source link.aps.org](https://link.aps.org/doi/10.1103/pgrn-mz9j)  
[Open source orbit.dtu.dk](https://orbit.dtu.dk/en/publications/quantum-isomorphism-is-equivalent-to-equality-of-homomorphism-cou/)  
[Open source dl.acm.org](https://dl.acm.org/doi/10.1145/3313276.3316366)  
[Open source scholar.google.nl](https://scholar.google.nl/citations?hl=en&user=4gdnMJYAAAAJ)  
[Open source scholar.google.com.sg](https://scholar.google.com.sg/citations?hl=th&user=yDlqLwsAAAAJ)  
[Open source scholar.google.com](https://scholar.google.com/citations?hl=en&user=6hjdwrsAAAAJ)  
[Open source www.emergentmind.com](https://www.emergentmind.com/topics/quantum-singular-value-transformation-qsvt)  
[Open source hal.science](https://hal.science/hal-05038521v1)  
[Open source tseppelt.github.io](https://tseppelt.github.io/homind-database/)  

Searching

[Open source arxiv.org](https://arxiv.org/abs/2002.08953)  
[Open source link.aps.org](https://link.aps.org/doi/10.1103/PhysRevB.108.195105)  
[Open source www.semanticscholar.org](https://www.semanticscholar.org/paper/Predicting-many-properties-of-a-quantum-system-from-Huang-Kueng/3986bbdcf8784101bf7a0389948cda48f71ac5f3)  
[Open source www.osti.gov](https://www.osti.gov/biblio/1769799)  
[Open source quics.umd.edu](https://quics.umd.edu/publications/simulating-large-quantum-circuits-small-quantum-computer)  
[Open source quantum-journal.org](https://quantum-journal.org/papers/q-2020-06-04-279/)  
[Open source www.researchgate.net](https://www.researchgate.net/publication/339399534_Predicting_Many_Properties_of_a_Quantum_System_from_Very_Few_Measurements)  
[Open source scholar.google.com](https://scholar.google.com/citations?hl=en&user=DSgKHOQAAAAJ)  
[Open source pennylane.ai](https://pennylane.ai/demos/tutorial_zx_calculus)  
[Open source x.com](https://x.com/inspirehep/status/1864709221515657662)  
[Open source www.nature.com](https://www.nature.com/articles/s41534-022-00548-w)  
[Open source www.alphaxiv.org](https://www.alphaxiv.org/overview/1904.00102v2)  
[Open source pureportal.strath.ac.uk](https://pureportal.strath.ac.uk/en/publications/graph-theoretic-simplification-of-quantum-circuits-with-the-zx-ca/persons/)  
[Open source scispace.com](https://scispace.com/papers/predicting-many-properties-of-a-quantum-system-from-very-few-34o7c4w7n4)  
[Open source pubs.rsc.org](https://pubs.rsc.org/dd/article/4/12/3540/889079/Estimating-Trotter-approximation-errors-to)  
[Open source pure.uva.nl](https://pure.uva.nl/ws/files/178706749/1904.00102v2.pdf)  
[Open source inspirehep.net](https://inspirehep.net/literature/2728412)  
[Open source www.mindat.org](https://www.mindat.org/reference.php?id=13939560)  
[Open source www.sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S0024379525004458)  
[Open source dl.acm.org](https://dl.acm.org/doi/10.1145/3445814.3446758)  
[Open source drops.dagstuhl.de](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ICALP.2022.119)  
[Open source scholar.google.com.au](https://scholar.google.com.au/citations?hl=th&user=yEGt2NAAAAAJ)  
[Open source www.scribd.com](https://www.scribd.com/document/990281048/s41567-020-0932-7)  
[Open source ouci.dntb.gov.ua](https://ouci.dntb.gov.ua/en/works/4z1RPZK7/)  

Searching

[Open source arxiv.org](https://arxiv.org/abs/2002.08953)  
[Open source link.aps.org](https://link.aps.org/doi/10.1103/PhysRevB.108.195105)  
[Open source www.semanticscholar.org](https://www.semanticscholar.org/paper/Predicting-many-properties-of-a-quantum-system-from-Huang-Kueng/3986bbdcf8784101bf7a0389948cda48f71ac5f3)  
[Open source www.osti.gov](https://www.osti.gov/biblio/1769799)  
[Open source quics.umd.edu](https://quics.umd.edu/publications/simulating-large-quantum-circuits-small-quantum-computer)  
[Open source quantum-journal.org](https://quantum-journal.org/papers/q-2020-06-04-279/)  
[Open source www.researchgate.net](https://www.researchgate.net/publication/339399534_Predicting_Many_Properties_of_a_Quantum_System_from_Very_Few_Measurements)  
[Open source scholar.google.com](https://scholar.google.com/citations?hl=en&user=DSgKHOQAAAAJ)  
[Open source pennylane.ai](https://pennylane.ai/demos/tutorial_zx_calculus)  
[Open source x.com](https://x.com/inspirehep/status/1864709221515657662)  
[Open source www.nature.com](https://www.nature.com/articles/s41534-022-00548-w)  
[Open source www.alphaxiv.org](https://www.alphaxiv.org/overview/1904.00102v2)  
[Open source pureportal.strath.ac.uk](https://pureportal.strath.ac.uk/en/publications/graph-theoretic-simplification-of-quantum-circuits-with-the-zx-ca/persons/)  
[Open source scispace.com](https://scispace.com/papers/predicting-many-properties-of-a-quantum-system-from-very-few-34o7c4w7n4)  
[Open source pubs.rsc.org](https://pubs.rsc.org/dd/article/4/12/3540/889079/Estimating-Trotter-approximation-errors-to)  
[Open source pure.uva.nl](https://pure.uva.nl/ws/files/178706749/1904.00102v2.pdf)  
[Open source inspirehep.net](https://inspirehep.net/literature/2728412)  
[Open source www.mindat.org](https://www.mindat.org/reference.php?id=13939560)  
[Open source www.sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S0024379525004458)  
[Open source dl.acm.org](https://dl.acm.org/doi/10.1145/3445814.3446758)  
[Open source drops.dagstuhl.de](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ICALP.2022.119)  

Searching

[Open source www.nature.com](https://www.nature.com/)  

Searching

[Open source qmath.ku.dk](https://qmath.ku.dk/)  
[Open source qiti.iqc.uwaterloo.ca](https://qiti.iqc.uwaterloo.ca/publications/)  

Searching

[Open source scholar.google.com](https://scholar.google.com/citations?hl=en&user=K2BMBtcAAAAJ)  
[Open source scholar.google.com.sg](https://scholar.google.com.sg/citations?hl=th&user=K2BMBtcAAAAJ)  
[Open source research.com](https://research.com/u/aram-w-harrow)  
[Open source citationmap.com](https://citationmap.com/profile/OEBtlWgAAAAJ)  
[Open source www.preskill.caltech.edu](https://www.preskill.caltech.edu/pub.html)  
[Open source scholar.google.com.br](https://scholar.google.com.br/citations?hl=th&user=7MOW-j4AAAAJ)  
[Open source scholar.google.es](https://scholar.google.es/citations?hl=ja&user=6WYsaqMAAAAJ)  
[Open source research.google](https://research.google/pubs/the-vast-world-of-quantum-advantage-4/)  
[Open source web.mit.edu](https://web.mit.edu/aram/www/)  
[Open source scholar.google.com.hk](https://scholar.google.com.hk/citations?hl=vi&user=K2BMBtcAAAAJ)  
[Open source www.cs.umd.edu](https://www.cs.umd.edu/~amchilds/)  
[Open source quantum-journal.org](https://quantum-journal.org/quantum-now-fully-recognized-by-google-scholar/)  
[Open source www.semanticscholar.org](https://www.semanticscholar.org/author/J.-Preskill/2313130)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Renato_Renner)  
[Open source www.researchgate.net](https://www.researchgate.net/profile/Andrew-Childs)  
[Open source inspirehep.net](https://inspirehep.net/authors/1029747)  
[Open source quantumzeitgeist.com](https://quantumzeitgeist.com/john-preskill/)  
[Open source english.elpais.com](https://english.elpais.com/technology/2026-06-05/aram-harrow-quantum-researcher-these-computers-wont-take-10-years-theyll-arrive-sooner.html)  
[Open source scispace.com](https://scispace.com/authors/renato-renner-3dr20qmr47?papers_page=25)  
[Open source elpais.com](https://elpais.com/tecnologia/2026-06-05/aram-harrow-investigador-cuantico-no-quedan-10-anos-para-estos-ordenadores-llegaran-antes.html)  

Searching

[Open source scholar.google.com](https://scholar.google.com/citations?hl=en&user=K2BMBtcAAAAJ)  
[Open source scholar.google.com.sg](https://scholar.google.com.sg/citations?hl=th&user=K2BMBtcAAAAJ)  
[Open source research.com](https://research.com/u/aram-w-harrow)  
[Open source citationmap.com](https://citationmap.com/profile/OEBtlWgAAAAJ)  
[Open source www.preskill.caltech.edu](https://www.preskill.caltech.edu/pub.html)  
[Open source scholar.google.com.br](https://scholar.google.com.br/citations?hl=th&user=7MOW-j4AAAAJ)  
[Open source scholar.google.es](https://scholar.google.es/citations?hl=ja&user=6WYsaqMAAAAJ)  
[Open source research.google](https://research.google/pubs/the-vast-world-of-quantum-advantage-4/)  
[Open source web.mit.edu](https://web.mit.edu/aram/www/)  
[Open source scholar.google.com.hk](https://scholar.google.com.hk/citations?hl=vi&user=K2BMBtcAAAAJ)  
[Open source www.cs.umd.edu](https://www.cs.umd.edu/~amchilds/)  
[Open source quantum-journal.org](https://quantum-journal.org/quantum-now-fully-recognized-by-google-scholar/)  
[Open source www.semanticscholar.org](https://www.semanticscholar.org/author/J.-Preskill/2313130)  
[Open source en.wikipedia.org](https://en.wikipedia.org/wiki/Renato_Renner)  
[Open source www.researchgate.net](https://www.researchgate.net/profile/Andrew-Childs)  
[Open source inspirehep.net](https://inspirehep.net/authors/1029747)  
[Open source quantumzeitgeist.com](https://quantumzeitgeist.com/john-preskill/)  
[Open source english.elpais.com](https://english.elpais.com/technology/2026-06-05/aram-harrow-quantum-researcher-these-computers-wont-take-10-years-theyll-arrive-sooner.html)  
[Open source scispace.com](https://scispace.com/authors/renato-renner-3dr20qmr47?papers_page=25)  

Searching

[Open source scholar.google.com](https://scholar.google.com/citations?hl=en&user=wlOytxsAAAAJ)  
[Open source scholar.google.co.th](https://scholar.google.co.th/citations?hl=th&user=wlOytxsAAAAJ)  
[Open source scholar.google.pt](https://scholar.google.pt/citations?hl=fil&user=6hjdwrsAAAAJ)  
[Open source quantum-journal.org](https://quantum-journal.org/)  
[Open source adscientificindex.com](https://adscientificindex.com/scientist/marco-tomamichel/413233/)  
[Open source scholarlyindex.com](https://scholarlyindex.com/)  
[Open source sites.google.com](https://sites.google.com/site/justincsong/publications)  
[Open source scholar.google.nl](https://scholar.google.nl/citations?hl=it&user=wlOytxsAAAAJ)  
[Open source www.researchgate.net](https://www.researchgate.net/)  
[Open source research.com](https://research.com/u/marco-tomamichel)  
[Open source en.wikipedia.org](https://en.wikipedia.org/)  
[Open source arxiv.org](https://arxiv.org/)  
[Open source www.cwi.nl](https://www.cwi.nl/)  
[Open source linhuli.com](https://linhuli.com/)  
[Open source www.alphaxiv.org](https://www.alphaxiv.org/%40marco-tomamichel)  
[Open source www.aiche.org](https://www.aiche.org/)  
[Open source quantumsystemsaccelerator.org](https://quantumsystemsaccelerator.org/)  
[Open source purigroup.research.yale.edu](https://purigroup.research.yale.edu/)  
[Open source scholar.google.com.sg](https://scholar.google.com.sg/intl/en/scholar/metrics.html)  

Searching

[Open source scholar.google.com](https://scholar.google.com/citations?hl=en&user=t11U6_sAAAAJ)  

Worked for 11m 51s

Worked for 11m 51s

Done

Searching

[Open source mit.edu](https://physics.mit.edu/faculty/aram-harrow/?utm_source=chatgpt.com)  
[Open source arxiv.org](https://arxiv.org/abs/2408.13687?utm_source=chatgpt.com)  
[Open source ku.dk](https://qmath.ku.dk/?utm_source=chatgpt.com)  
[Open source youtube.com](https://www.youtube.com/watch?v=Dc-RSPv9FT8&utm_source=chatgpt.com)  
[Open source research.google](https://research.google/blog/dynamic-surface-codes-open-new-avenues-for-quantum-error-correction/?utm_source=chatgpt.com)  
[Open source qusoft.org](https://qusoft.org/?utm_source=chatgpt.com)  
[Open source wikipedia.org](https://en.wikipedia.org/wiki/Pan_Jianwei?utm_source=chatgpt.com)  
[Open source umd.edu](https://www.cs.umd.edu/~amchilds/?utm_source=chatgpt.com)  
[Open source cwi.nl](https://www.cwi.nl/en/stories/qusoft/?utm_source=chatgpt.com)  
[Open source quantumzeitgeist.com](https://quantumzeitgeist.com/pan-jianwei-the-chinese-quantum-pioneer/?utm_source=chatgpt.com)  
[Open source sciencedirect.com](https://www.sciencedirect.com/science/article/pii/S2352340926006967?utm_source=chatgpt.com)  
[Open source quantum-journal.org](https://quantum-journal.org/papers/q-2022-11-28-862/?utm_source=chatgpt.com)  
[Open source caltech.edu](https://magazine.caltech.edu/post/iqim-quantum-john-preskill?utm_source=chatgpt.com)  
[Open source ox.ac.uk](https://oqi.web.ox.ac.uk/people/aleks-kissinger?utm_source=chatgpt.com)  
[Open source facebook.com](https://www.facebook.com/scmp/posts/the-breakthrough-establishes-a-core-element-required-for-general-purpose-quantum/1395934735915908/?utm_source=chatgpt.com)  
[Open source elpais.com](https://english.elpais.com/technology/2026-06-05/aram-harrow-quantum-researcher-these-computers-wont-take-10-years-theyll-arrive-sooner.html?utm_source=chatgpt.com)  
[Open source ibm.com](https://www.ibm.com/quantum/blog/qdc-2025?utm_source=chatgpt.com)  
[Open source nih.gov](https://pubmed.ncbi.nlm.nih.gov/39653125/?utm_source=chatgpt.com)  
[Open source google.com](https://scholar.google.com/citations?hl=zh-CN&user=RERrJ6UAAAAJ&utm_source=chatgpt.com)  
[Open source theoryofcomputing.org](https://theoryofcomputing.org/articles/v010a003/about.html?utm_source=chatgpt.com)  
[Open source microsoft.com](https://azure.microsoft.com/en-us/blog/quantum/2025/02/19/microsoft-unveils-majorana-1-the-worlds-first-quantum-processor-powered-by-topological-qubits/?utm_source=chatgpt.com)  
[Open source quantinuum.com](https://www.quantinuum.com/blog/introducing-helios-the-most-accurate-quantum-computer-in-the-world?utm_source=chatgpt.com)  
[Open source inspirehep.net](https://inspirehep.net/literature/2821840?utm_source=chatgpt.com)  
[Open source uwaterloo.ca](https://qc.uwaterloo.ca/?utm_source=chatgpt.com)  
[Open source thequantuminsider.com](https://app.thequantuminsider.com/company/cbb4538e-06bc-4578-a67d-c1204c17874d/profile?utm_source=chatgpt.com)  
[Open source icmat.es](https://www.icmat.es/news/07-04-26-en/?utm_source=chatgpt.com)  
[Open source quantumai.google](https://quantumai.google/qecmilestone?utm_source=chatgpt.com)  
[Open source reddit.com](https://www.reddit.com/r/Physics/comments/d7s3ov/quantum_supremacy_using_a_programmable/?utm_source=chatgpt.com)  
[Open source nsf.gov](https://www.nsf.gov/mps/quantum-leap-challenge-institutes?utm_source=chatgpt.com)  
[Open source blog.google](https://blog.google/innovation-and-ai/technology/research/behind-the-scenes-google-quantum-ai-lab/?utm_source=chatgpt.com)  
[Open source princeton.edu](https://collaborate.princeton.edu/en/publications/quantum-error-correction-below-the-surface-code-threshold/?utm_source=chatgpt.com)  
[Open source iaqi.org](https://tqc.iaqi.org/2025/tqc2023/index.html?utm_source=chatgpt.com)  
[Open source googleblog.com](https://developers.googleblog.com/unlocking-the-potential-of-quantum-computing-a-developers-guide-to-error-correction/?utm_source=chatgpt.com)  
[Open source nature.com](https://www.nature.com/articles/s41535-025-00768-1?utm_source=chatgpt.com)  
[Open source datadryad.org](https://datadryad.org/dataset/doi%3A10.5061/dryad.k6t1rj8?utm_source=chatgpt.com)  
[Open source sunysb.edu](https://insti.physics.sunysb.edu/~korepin/Teaching/Spring2020/science.abe8770.pdf?utm_source=chatgpt.com)  
[Open source mcqst.de](https://www.mcqst.de/MCQST-MEDIA/qip2021/BookletofAbstractsFeb2.pdf?utm_source=chatgpt.com)  
[Open source whocitedit.com](https://whocitedit.com/w/W3107463944/?utm_source=chatgpt.com)  
[Open source duke.edu](https://pratt.duke.edu/news/nsf-quantum-simulation-institute/?utm_source=chatgpt.com)  
[Open source osti.gov](https://www.osti.gov/biblio/1607005?utm_source=chatgpt.com)  
[Open source researchgate.net](https://www.researchgate.net/publication/348231548_Quantum_computational_advantage_using_photons?utm_source=chatgpt.com)  
[Open source berkeley.edu](https://digicoll.lib.berkeley.edu/record/140693?utm_source=chatgpt.com)  
[Open source x.com](https://x.com/quantumlight?utm_source=chatgpt.com)  
[Open source linkedin.com](https://www.linkedin.com/company/institute-for-robust-quantum-simulation-rqs?utm_source=chatgpt.com)  
[Open source stackexchange.com](https://quantumcomputing.stackexchange.com/questions/75/which-quantum-error-correction-code-has-the-highest-threshold-as-proven-at-the?utm_source=chatgpt.com)  
[Open source alphaxiv.org](https://www.alphaxiv.org/abs/1910.11333?utm_source=chatgpt.com)  
[Open source openresearch.amsterdam](https://openresearch.amsterdam/en/page/67124/qusoft-celebrates-five-years-of-cutting-edge-quantum-algorithm-and?utm_source=chatgpt.com)  
[Open source aps.org](https://link.aps.org/doi/10.1103/PhysRevLett.131.150601?utm_source=chatgpt.com)  
[Open source entangledfuture.com](https://entangledfuture.com/company/qusoft/?utm_source=chatgpt.com)  
[Open source ethz.ch](https://www.research-collection.ethz.ch/bitstreams/ff784bf1-6f08-48b5-a9c6-c61d13aba053/download?utm_source=chatgpt.com)  
[Open source instagram.com](https://www.instagram.com/p/Dc1FYdskfr0/?utm_source=chatgpt.com)  
[Open source kth.se](https://www.kth.se/social/files/605a065cb6c2ee8b567f2a79/quantum-computation-advantage.pdf?utm_source=chatgpt.com)  

Generated report on 全球数学与量子计算交叉领域主要研究团队、成果与未来突破潜力

## 原始页面记录

完整原始摘录保存在[同名 HTML 档案](html/gpt-14.html)末尾的折叠附录中。Markdown 为便于检索的正文版，未重复嵌入原始结构。
