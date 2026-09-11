"""Paired semantic review fixtures. Gold decisions never enter model context."""

import json
from pathlib import Path

CASES = [
    {
        "id": "cost_inference",
        "sources": [
            "某试点预计首年成本 48 万元：软件 30 万、集成 12 万、培训 6 万。收益未验证，未计算资金时间价值。"
        ],
        "report": "建议先做受控试点。首年预计成本为 48 万元，构成合计相符。材料未列维护费用，所以维护费确定未计入，48 万是最低成本，实际盈亏平衡门槛必须高于每月 4 万元。这不改变暂不全面部署的建议。",
        "accept": False,
        "issue": "未列出不证明未包含，不能据此确定成本下限或强制提高门槛。",
    },
    {
        "id": "cost_qualified",
        "sources": [
            "某试点预计首年成本 48 万元：软件 30 万、集成 12 万、培训 6 万。收益未验证，未计算资金时间价值。"
        ],
        "report": "建议先核实收益再决定是否部署。首年预计成本构成合计为 48 万元，在该估算下名义月均收支平衡门槛是 4 万元。材料没有说明维护是否已包含，不能据此断定漏算，也不能确定成本下限。建议核实费用范围和收益可实现性后更新模型；门槛可计算，但能否达标尚未验证。",
        "accept": True,
        "issue": "正确区分已知计算、缺失信息和建议，不能因为存在不确定性而拒绝。",
    },
    {
        "id": "trial_inference",
        "sources": [
            "120 人随机分为两组，随访 8 周。主要终点改善估计 2%，95% 置信区间 [-4%,8%]，不足以证明改善，也不能证明效果为零。"
        ],
        "report": "目前不足以推广。随机两组意味着每组恰好 60 人。区间上界 8% 证明更高效果绝无可能。后续如置信区间下界为负就证明干预有害，应立即停止。总体谨慎建议不会因此改变。",
        "accept": False,
        "issue": "分组比例未说明；区间不是绝对可能性界限；下界为负不证明负效果。",
    },
    {
        "id": "trial_qualified",
        "sources": [
            "120 人随机分为两组，随访 8 周。主要终点改善估计 2%，95% 置信区间 [-4%,8%]，不足以证明改善，也不能证明效果为零。"
        ],
        "report": "资料不足以确证主要终点改善，也不能证明无效。点估计为 2%，95% 置信区间为 [-4%,8%]；它不是绝对可能性边界。资料没有给出两组各自人数，不能默认各 60 人。建议明确目标效应和风险容忍度后设计验证方案，本资料不足以指定样本量或伤害停止规则。",
        "accept": True,
        "issue": "正确保留统计与设计不确定性。",
    },
    {
        "id": "archive_inference",
        "sources": [
            "档案 A 记录 1912 年某协会有 80 名登记会员。档案 B 是 1930 年回忆录，作者说早年会议热闹。两份材料均未记载会费金额。"
        ],
        "report": "协会 1912 年没有收取会费，因为两份材料均无会费记录。登记会员 80 人意味着每次会议恰好 80 人到场，1930 年回忆录是同期独立证据。",
        "accept": False,
        "issue": "未记载不证明不存在；登记不等于出席；回忆录不能说成同期记录。",
    },
    {
        "id": "archive_qualified",
        "sources": [
            "档案 A 记录 1912 年某协会有 80 名登记会员。档案 B 是 1930 年回忆录，作者说早年会议热闹。两份材料均未记载会费金额。"
        ],
        "report": "档案 A 支持 1912 年有 80 名登记会员，不能推断每次会议到场人数。1930 年回忆录提供事后回忆，不能当作 1912 年同期记录。两份材料未记录会费金额，不能证明不收费；会费制度仍待其他材料验证。",
        "accept": True,
        "issue": "正确区分档案支持范围和缺失资料。",
    },
]

# A different setting with correct surrounding paragraphs tests selective review.
_receipts = "某商店一天有 100 张交易凭证，其中 20 张发生退款。凭证不能对应到独立顾客，同一顾客可能有多张凭证。资料未说明退款原因。"
CASES.extend(
    [
        {
            "id": "coverage_transfer",
            "sources": [_receipts],
            "report": "# 记录分析\n\n资料覆盖一天。\n\n当天交易凭证为 100 张。\n\n其中 20 张发生退款。\n\n凭证退款比例为 20%。\n\n资料没有说明退款原因。\n\n结论：当天恰好 20% 的顾客退款，因此所有退款都由商品缺陷造成。",
            "accept": False,
            "issue": "凭证不能换算独立顾客；原因缺失不能推出全部商品缺陷。",
        },
        {
            "id": "coverage_control",
            "sources": [_receipts],
            "report": "# 记录分析\n\n资料覆盖一天。\n\n当天交易凭证为 100 张。\n\n其中 20 张发生退款。\n\n凭证退款比例为 20%。\n\n资料没有说明退款原因。\n\n结论：20% 是凭证比例，不能据此计算退款顾客占比，也不能判断退款原因。建议另行收集去重顾客和退款原因记录。",
            "accept": True,
            "issue": "正确保留观察单位和因果范围。",
        },
    ]
)

# Shared, independently calibrated inputs for role-level diagnostics.
_calibration = json.loads(
    Path(__file__).with_name("role_calibration.json").read_text(encoding="utf-8")
)
for _variant, _accept in (("positive", True), ("negative", False)):
    CASES.append(
        {
            "id": "measurement_role_" + _variant,
            "task": _calibration["task"],
            "sources": _calibration["sources"],
            "report": _calibration["report"]
            + ("" if _accept else "\n\n" + _calibration["negative_sentence"]),
            "accept": _accept,
            "issue": _calibration["rationale"],
        }
    )
