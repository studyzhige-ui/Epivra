"""Reproducibility projections from existing records, without private reasoning."""

import platform
import sys
from importlib.metadata import distributions

from .domain import encode, identity
from .review import public_inputs


def environment():
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "gil_enabled": sys._is_gil_enabled()
        if hasattr(sys, "_is_gil_enabled")
        else True,
        "packages": dict(
            sorted(
                (d.metadata["Name"], d.version)
                for d in distributions()
                if d.metadata.get("Name")
            )
        ),
    }


def windows(store, study):
    for step in store.iter_artifacts(study, "step"):
        request = step.body["request"]
        entries, receipts = [], []
        for value in public_inputs(request):
            for item in value.get("context", []):
                entry = {
                    k: item[k]
                    for k in ("ref", "kind", "body_omitted", "characters")
                    if k in item
                }
                if "body" in item:
                    entry.update(
                        body_hash=identity(item["body"]),
                        characters=len(encode(item["body"])),
                    )
                entries.append(entry)
            if "observation_ref" in value:
                entry = {
                    "ref": value["observation_ref"],
                    "body_omitted": "result" not in value,
                }
                if "result" in value:
                    result = value["result"]
                    entry["result_hash"] = identity(result)
                    if isinstance(result, dict):
                        entry.update(
                            {
                                k: result[k]
                                for k in (
                                    "report",
                                    "ref",
                                    "offset",
                                    "end",
                                    "next_offset",
                                    "coverage",
                                )
                                if k in result
                            }
                        )
                        entry["report_units"] = [
                            x["unit"] for x in result.get("units", []) if "unit" in x
                        ]
                receipts.append(entry)
        yield {
            "step": step.ref,
            "work": step.parents[0],
            "provider": request.get("provider"),
            "current_date": request.get("current_date"),
            "window_mode": request.get("wire", {}).get("window_mode", "direct"),
            "estimated_input_tokens": request.get("wire", {}).get(
                "estimated_input_tokens"
            ),
            "omitted_count": request.get("omitted_count"),
            "context": entries,
            "tool_receipts": receipts,
            "tools": sorted(request.get("tools", {})),
            "input_revisions": request.get("input_revisions", {}),
            "operations": [
                dict(row)
                for row in store.db.execute(
                    "SELECT id,status,admission FROM operations WHERE study=? AND request_step=?",
                    (study, step.ref),
                )
            ],
        }
