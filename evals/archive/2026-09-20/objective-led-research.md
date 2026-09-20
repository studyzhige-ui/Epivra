# 归档实验：Objective-led Lead（2026-09-20）

状态：**实验结束，不进入默认优化主线。** 本文件只保存实验事实和否决理由，不恢复实验 prompt。

- 实验分支：`experiment/objective-led-research-20260920`
- 分支删除前 head：`b0302503eefb6d9b25d8e715739b54a23dcbb0c2`
- 实际 Lead-only 候选代码：`e089910a27ca92f3f5ba944d718396ed5ec7b515`
- 对照基线：`94ffd531d5faaf16adb56562239b63ef32bf9f75`
- 严格离线验证：run `35495698714`，artifact `10600409102`，SHA-256 `87d2730b775bf84e9b602290cf03a4419696c5e46de355072de2fdf0c5f7417d`
- 完整真实任务：run `35495879387` / job `106038595762`，artifact `10600539532`，SHA-256 `a9507e67e19428d32ebf28e61382bbd270dae790ec8b1ea290ce373de5d43f18`

## 结果

在相同 SQLite 官方快照、相同模型策略和相同完整 ResearchService 任务上：

| 指标 | 旧读取修复版 | Objective-led Lead |
|---|---:|---:|
| publication | 否 | 是 |
| 成功完成时间 | 未取得；15分钟保护后停止 | 654.533秒 |
| 模型调用 | 89 | 68 |
| 总 token | 4,050,617 | 2,500,193 |
| 输入 token | 3,808,703 | 2,366,106 |
| 输出 token | 241,914 | 134,087 |
| unknown | 0 | 0 |
| 独立质量验收 | 未通过 | **未通过** |

角色调用变化：Lead 20→20、Investigator 31→13、Synthesizer 5→0、Writer 11→14、Reviewer 22→21。外部调用区间并非所有角色都下降，且不同角色区间会重叠，不能相加为端到端耗时。

## 为什么不进入主线

发布报告虽完成，但独立复核发现实质证据强度问题：
1. 将受条件限制的 checkpoint 进展与“完成/重置”过度合并；
2. 把“下一次调用继续”强化为特定写事务“一次性消化积压”，并进一步声称开销与积压量成正比，快照并未支持这种必然性和定量关系。

第一次 final review 虽 accepted=true，但 comments 中包含会影响模式选择的实质问题；Lead 的返工不能简单视为浪费。第二次 final review 仍 accepted=true，却漏过上述过强结论。因此本实验说明“减少 Lead 制造的下游工作”具有值得继续研究的效率信号，但这个具体 Lead prompt **没有满足质量门槛**。

保留决策：只归档结果；实验代码和分支删除。后续若重新研究 Lead，应从新的通用机制重新验证，不复用本 prompt 作为默认答案。
