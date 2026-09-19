"""Two small mechanism probes. Outcomes never enter model requests.

Not a general research benchmark: these test source navigation and substantive
revision with preserved evidence, including a contrasting valid deployment.
"""

CASES = {
    "source-conditions": {
        "task": "根据给定原始资料判断 AZ-4 是否适合无人值守室外部署；说明已验证能力与适用限制。",
        "sources": [
            {
                "origin": "az4-manual.txt",
                "text": "# AZ-4使用手册\n\n"
                + ("日常维护：定期核对铭牌并记录巡检日期。\n" * 2100)
                + "\n适用限制：本型号仅限有人值守的干燥室内使用；未认证室外或无人值守部署。\n",
            },
            {
                "origin": "az4-test.txt",
                "text": "AZ-4在有人工监控的干燥室内连续运行12小时，测量误差保持标称范围。未进行淋雨、湿热或无人值守故障测试。",
            },
        ],
    },
    "source-valid": {
        "task": "根据给定原始资料判断 BX-2 是否满足用于无人值守室外部署的已列要求；说明适用范围。",
        "sources": [
            {
                "origin": "bx2-manual.txt",
                "text": "# BX-2使用手册\n\n"
                + ("维护记录：记录例行检测并核对设备标识。\n" * 2100)
                + "\n适用范围：本型号获准无人值守室外部署，适用环境温度0至35摄氏度；必须按季度检查密封件。\n",
            },
            {
                "origin": "bx2-test.txt",
                "text": "BX-2完成0至35摄氏度下连续30天无人值守室外测试，故障率满足给定验收要求；超出这一环境范围未测试。",
            },
        ],
    },
    "revise-outcome": {
        "task": "根据新取得的原始表注修订所附报告：纠正所有受影响的成效判断，保留仍成立的执行安排与费用信息，交付修订稿。",
        "sources": [
            {
                "origin": "campaign-register.txt",
                "text": "本月登记120人，上月100人，登记人数增加20%。表注：未测量活动效果，不能由登记变化推定成效变化。执行安排为下月三场，每场预算3000元，总预算9000元。",
            }
        ],
    },
}


def request_cases(request):
    if (
        not isinstance(request, dict)
        or set(request) != {"version", "request_id", "cases"}
        or type(request["version"]) is not int
        or request["version"] != 1
    ):
        raise ValueError("invalid capability request")
    if (
        not isinstance(request["request_id"], str)
        or not request["request_id"].replace("-", "").replace("_", "").isalnum()
    ):
        raise ValueError("invalid request identity")
    cases = request["cases"]
    if (
        not isinstance(cases, list)
        or not 1 <= len(cases) <= 3
        or any(not isinstance(c, str) or c not in CASES for c in cases)
        or len(set(cases)) != len(cases)
    ):
        raise ValueError(
            "select at most the three fixed capability probes; no large benchmarks"
        )
    return cases
