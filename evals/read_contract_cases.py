"""Small interface experiments, not report-quality or generalization benchmarks.

Both arms use the same tasks and originals. Selection probes stop after ONE real
model turn and do not claim completed research. Final-review probes run normally.
Expected decisions are evaluation-only; no outcome labels enter model requests.
"""

SOURCE_CASES = {
    "registry": {
        "task": "核对所给登记资料中报名与实际到场的区别，回答该次活动的实际到场人数。",
        "source": "登记表：报名23人，实际到场19人。报名人数不等于到场人数。",
        "origin": "attendance-register.txt",
    },
    "service": {
        "task": "Check the supplied service log and determine the duration of the recorded interruption, preserving what the log does and does not establish about its cause.",
        "source": "Service log: unavailable from 10:04 to 10:11 UTC. Cause remains under investigation; a restart was observed at 10:06 UTC.",
        "origin": "service-log.txt",
    },
}

REPORT_CASES = {
    "length-within": {
        "template": "# 采样记录\n\n采样于周一完成，共取得12份样本@CITE0@。\n\n| 项目 | 数量 |\n|---|---|\n| 样本 | 12 |",
        "source": "采样记录：周一完成采样，共取得12份样本。",
        "origin": "sampling-register.txt",
        "title": "The complete original sampling register, including provenance and recording details",
        "allowance": 1,
        "accept": True,
    },
    "length-over": {
        "template": "# Device check\n\nThe check covered 14 devices. Two required replacement; the remaining 12 passed@CITE0@.",
        "source": "Device check record: 14 checked, 2 requiring replacement, 12 passed.",
        "origin": "device-register.txt",
        "title": "Original device check register and its detailed recording provenance",
        "allowance": -1,
        "accept": False,
    },
}

CASE_IDS = tuple(
    f"{role}-{case}" for role in ("lead", "investigator") for case in SOURCE_CASES
) + tuple(REPORT_CASES)


def selection(value: object) -> list[str]:
    if not isinstance(value, dict) or set(value) != {"version", "request_id", "cases"}:
        raise ValueError("unexpected read-contract request")
    if type(value["version"]) is not int or value["version"] != 1:
        raise ValueError("unsupported request version")
    if not isinstance(value["request_id"], str) or not value["request_id"].isascii() or not value["request_id"].replace("-", "").replace("_", "").isalnum() or len(value["request_id"]) > 64:
        raise ValueError("invalid request ID")
    cases = value["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= len(CASE_IDS) or any(not isinstance(c, str) for c in cases):
        raise ValueError("select existing small interface cases")
    if len(set(cases)) != len(cases) or not set(cases) <= set(CASE_IDS):
        raise ValueError("invalid/large case selection; no benchmarks in this runner")
    return cases
