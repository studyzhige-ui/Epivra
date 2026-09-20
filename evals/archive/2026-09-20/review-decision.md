# 归档实验：Reviewer decision（2026-09-20）

状态：**实验结束，不进入默认优化主线。** 本文件保存真实 paired reviewer 结果和否决理由。

- 实验分支：`experiment/review-decision-20260920`
- 删除前 head / reviewer 候选：`cbba57dab549e4bb5b009452f8cc2056e1f198bd`
- reviewer 基线代码：`e089910a27ca92f3f5ba944d718396ed5ec7b515`
- 严格离线验证：run `35496878945`，通过 455 项中的 453 项、2 skip，以及 pip check / architecture / Ruff / 配置内 mypy / wheel 构建
- paired 真实 reviewer：run `35497100613`
- baseline artifact：`10600971403`，SHA-256 `2a7a9971f9b4b5f0aef4af39ea64a18a50d1a97fb6afd6926c671e61c0715a78`
- candidate artifact：`10601346945`，SHA-256 `476d4553a3ef7cc12bf9bb416c3c9ee48402f412afe2fc943986c4545f052248`

## 用量

| 指标 | baseline reviewer | candidate reviewer |
|---|---:|---:|
| DeepSeek 调用 | 17 | 13 |
| 输入 token | 345,696 | 246,978 |
| 输出 token | 28,898 | 43,453 |
| 总 token | 374,594 | 290,431 |
| cache read（已含在输入） | 305,664 | 204,672 |
| reasoning（已含在输出） | 25,303 | 40,018 |
| unknown | 0 | 0 |

三个固定 reviewer 输入都完整结束，但 workflow 按语义验收保持 failure，不用“execution completed”冒充质量通过。

## 三个对照结果

1. **真实 SQLite 报告**：baseline 与 candidate 都 accepted=true。candidate 虽减少 comments，但仍没有阻断独立复核已经确认的关键过强表述，因此没有解决主问题。
2. **cost_inference 负向控制**：baseline accepted=true，只把“维护费确定未计入 / 门槛必须高于4万元”放在 comments；candidate accepted=false，并把“材料省略不能推出事实否定、预计成本不能升级为下限、可能不能升级为必然”正确提升为 defect。
3. **cost_qualified 正向控制**：两边都 accepted=true；candidate 没有误伤合理限定答案。

## 为什么不进入主线

候选 reviewer 在“评论 vs 实质缺陷”的一类控制案例上明显改善，而且调用更少；但它仍然漏过真正 SQLite 成品中的关键证据强度问题。因此只能说明一个局部方向有价值，不能证明 reviewer 核心已经可靠。

保留决策：归档 paired 结果和失败边界；不把候选 reviewer prompt 合入默认优化代码；删除实验分支。未来 reviewer 优化必须再次经过不同领域、相反方向控制和完整任务验证。
