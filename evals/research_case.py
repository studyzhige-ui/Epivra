"""Synthetic research fixture and provenance checks, never production policy."""

from __future__ import annotations

from pathlib import Path

from deep_research_agent.domain import encode


def corpus(directory: Path, size: int) -> dict:
    if size not in {30, 100, 1000}:
        raise ValueError("supported corpus sizes: 30, 100, 1000")
    directory.mkdir(parents=True, exist_ok=True)
    for i in range(size):
        text = (
            f"资料编号 {i}。以下是虚构产品 Lumina 的内部资料，用于研究评测，非现实事实。\n"
            "这份资料转载供应商通稿 PR-01：供应商称试点组处理工单速度提升 35%。"
            "没有随机分组，样本为 12 名自愿参加员工，测量期 2 周。"
            "本篇没有新增样本或独立观察，不能当作新的独立研究。\n"
        )
        if i == size // 2:
            text = (
                "虚构资料：财务核算备忘录 FIN-02。全公司部署预计首年成本 48 万元，"
                "其中软件 30 万、集成 12 万、培训 6 万。收益尚未经过随机对照验证。"
                "只有每月节省至少 4 万元才能在首年实现名义收支平衡，未计算资金时间价值。\n"
            )
        if i == size - 1:
            text = (
                "虚构资料：独立随机对照试验 RCT-03，120 名员工，随机分为两组，随访 8 周。"
                "预注册主要终点为每小时完成的有效工单数量。相对改善估计 2%，95% 置信区间 [-4%, 8%]，"
                "不足以证明主要终点改善，也不能证明效果严格为零。"
                "新员工子组事后分析显示 18% 改善，但未经多重比较校正，不能作为确认性结论。"
                "随访短、单一部门，长期效果和跨部门推广均不确定。\n"
            )
        path = directory / f"record-{i:04d}.md"
        if path.exists() and path.read_text(encoding="utf-8") != text:
            raise ValueError("fixture differs from existing run; use a new run ID")
        path.write_text(text, encoding="utf-8")
    return {
        "critical_origins": [f"record-{size // 2:04d}.md", f"record-{size - 1:04d}.md"],
        "size": size,
    }


QUESTION = (
    "仅依据授权目录中的虚构 Lumina 资料，研究我们是否应当全公司部署这个工单辅助产品。"
    "请先辨明资料独立性和不同研究设计的证据力度，审阅成本、反证和不确定性，"
    "再提交中文报告，包含可回查的来源引用、关键数字、适用限制和可执行建议。"
    "不能使用网络或外部事实补全缺失结论。研究方法与分工由你决定。"
)


def assess(store, study: str, gold: dict) -> dict:
    direction = store.control(study).direction
    publications = [
        a for a in store.list(study, "publication") if direction in a.parents
    ]
    result = {
        "published": bool(publications),
        "unknown": len(store.unsettled(study)),
        "sources": len(store.list(study, "source")),
        "steps": len(store.list(study, "step")),
        "window_rebuilds": sum(
            a.body["request"].get("wire", {}).get("window_mode") == "rebuilt"
            for a in store.list(study, "step")
        ),
        "investigators": sum(
            a.body["role"] == "investigator" for a in store.list(study, "work")
        ),
        "critical_sources_cited": False,
        "critical_sources_read": False,
        "semantic_review": "manual_required",
        "tool_errors": sum(
            "error" in a.body.get("result", {})
            for a in store.list(study, "observation")
        ),
        "blocked_work": [
            a.body["blocked"]
            for a in store.list(study, "observation")
            if "blocked" in a.body
        ],
    }
    if not publications:
        return result
    report = store.get(study, publications[-1].body["report"])
    cited = {store.get(study, ref).body["origin"] for ref in report.body["evidence"]}
    ranges = {}
    read = set()
    sources = {s.ref: s for s in store.list(study, "source")}
    bodies = {encode(s.body): s.body["origin"] for s in sources.values()}
    for observation in store.list(study, "observation"):
        tool = observation.body.get("tool")
        value = observation.body.get("result", {})
        if tool == "read_artifact" and value.get("kind") == "source":
            origin = bodies.get(encode(value["body"]))
            if origin:
                read.add(origin)
        if (
            tool in {"read_source", "read_artifact_range"}
            and value.get("text", "").strip()
            and value.get("ref") in sources
        ):
            ranges.setdefault((value["ref"], tool), []).append(
                (value["offset"], value["end"])
            )
    for (ref, tool), intervals in ranges.items():
        end = 0
        for start, stop in sorted(intervals):
            if start > end:
                break
            end = max(end, stop)
        source = store.get(study, ref)
        length = (
            len(source.body["text"])
            if tool == "read_source"
            else len(encode(source.body))
        )
        if end >= length:
            read.add(source.body["origin"])
    required = set(gold["critical_origins"])
    result.update(
        critical_sources_cited=required <= cited,
        critical_sources_read=required <= read,
        sources_fully_read=len(read),
        report_ref=report.ref,
    )
    return result
