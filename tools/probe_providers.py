"""Opt-in paid integration probe; never imported by the offline test suite."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from deep_research_agent.adapters import DeepSeek, JsonAPI, Tavily, credentials
from deep_research_agent.domain import identity
from deep_research_agent.storage import Store


async def run(root: Path, stream: bool = False) -> dict:
    keys = credentials(root / ".env")
    store = Store(root / ".deep-research-agent" / "provider-probe.db")
    clients = [
        JsonAPI("https://api.deepseek.com", keys["DEEPSEEK_API_KEY"]),
        JsonAPI("https://api.tavily.com", keys["TAVILY_API_KEY"]),
    ]
    try:
        try:
            c = store.control("probe")
        except ValueError:
            c = store.create("probe", "Authorized provider integration test", {})
            plan = store.put(
                "probe",
                "plan",
                {"text": "Probe tool protocol and public search only"},
                (c.direction,),
            )
            c = store.command(
                "probe", "approve-probe", c.ref, "approve", {"plan": plan.ref}
            )
        work = store.work(
            "probe", c.ref, "researcher", "Provider protocol verification"
        )

        async def paid(label, request, invoke):
            key = identity("probe", label, request)
            result = store.admit("probe", work.ref, c.epoch, key, request)
            if result is None:
                result = await invoke()
                store.settle(key, result)
            return result

        model = DeepSeek(clients[0], model="deepseek-v4-pro", max_tokens=2048, stream=stream)
        context = {
            "system": "You are a protocol test. Use the echo tool exactly once with value 'verified'. After its result, say verified.",
            "tools": {
                "echo": {
                    "description": "Echo a value",
                    "parameters": {
                        "type": "object",
                        "properties": {"value": {"type": "string"}},
                        "required": ["value"],
                        "additionalProperties": False,
                    },
                }
            },
            "task": "Call echo now.",
            "context": [],
        }
        wire = model.prepare(context, None)
        first = await paid("model-first", wire, lambda: model.complete({"wire": wire}))
        outcome = {"deepseek_http": first.get("http_status")}
        if first.get("http_status") == 200:
            decoded = model.decode(first)
            outcome["deepseek_tool_calls"] = len(decoded["calls"])
            outcome["deepseek_complete"] = decoded["complete"]
            outcome["deepseek_usage"] = first.get("data", {}).get("usage", {})
            if decoded["complete"] and decoded["calls"]:
                observations = [
                    {
                        "index": i,
                        "result": {"value": "verified"},
                        "_ref": "probe-fixture",
                    }
                    for i in range(len(decoded["calls"]))
                ]
                next_context = {
                    **context,
                    "task": "The echo test has finished. Say verified without further tools.",
                }
                wire2 = model.prepare(
                    next_context,
                    {
                        "request": wire["payload"],
                        "response": first,
                        "observations": observations,
                    },
                )
                second = await paid(
                    "model-followup", wire2, lambda: model.complete({"wire": wire2})
                )
                outcome["deepseek_followup_http"] = second.get("http_status")
                if second.get("http_status") == 200:
                    outcome["deepseek_followup_complete"] = model.decode(second)[
                        "complete"
                    ]
        tavily = Tavily(clients[1])
        query = {"query": "site:api-docs.deepseek.com tool calls"}
        search = await paid("search", query, lambda: tavily.search(query))
        outcome["tavily_search_http"] = search.get("http_status")
        results = search.get("data", {}).get("results", [])
        outcome["tavily_result_count"] = len(results)
        if results:
            args = {"url": results[0]["url"]}
            extracted = await paid("extract", args, lambda: tavily.extract(args))
            outcome["tavily_extract_http"] = extracted.get("http_status")
            outcome["tavily_extracted_pages"] = len(
                extracted.get("data", {}).get("results", [])
            )
        return outcome
    finally:
        for client in clients:
            await client.close()
        store.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args()
    try:
        result = asyncio.run(run(Path(__file__).resolve().parents[1], stream=args.stream))
    except Exception as exc:
        result = {"error_type": type(exc).__name__}
    print(json.dumps(result, ensure_ascii=False, indent=2))
