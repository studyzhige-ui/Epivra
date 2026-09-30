"""Offline wire, decode and normalization checks; no live provider requests."""

import json
import unittest

import httpx

from epivra.adapters import JsonAPI
from epivra.jev import MODEL, Jev
from epivra.model_catalog import OFFICIAL_PROVIDERS
from epivra.model_discovery import discover
from epivra.models import create_model, freeze_model_settings
from epivra.public_sources import TOOLS, PublicSource
from epivra.usage import counters
from epivra.web_providers import SEARCH, connect

context = {
    "system": "Test only",
    "role": "lead",
    "context": [],
    "tools": {
        "calculate": {
            "description": "compute",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
                "additionalProperties": False,
            },
        }
    },
}


class ProviderContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_configured_provider_contracts(self):
        counts = {}
        for name, spec in OFFICIAL_PROVIDERS.items():
            reqs = []
            if spec.protocol == "chat":
                response = {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "",
                                "reasoning_content": "private wire continuity",
                                "tool_calls": [
                                    {
                                        "id": "c1",
                                        "type": "function",
                                        "function": {
                                            "name": "calculate",
                                            "arguments": '{"expression":"1+1"}',
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 10},
                }
            elif spec.protocol == "anthropic":
                response = {
                    "content": [
                        {
                            "type": "thinking",
                            "thinking": "private wire continuity",
                            "signature": "sig",
                        },
                        {
                            "type": "tool_use",
                            "id": "c1",
                            "name": "calculate",
                            "input": {"expression": "1+1"},
                        },
                    ],
                    "stop_reason": "tool_use",
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 10,
                        "cache_read_input_tokens": 5,
                    },
                }
            else:
                response = {
                    "candidates": [
                        {
                            "content": {
                                "role": "model",
                                "parts": [
                                    {
                                        "functionCall": {
                                            "name": "calculate",
                                            "args": {"expression": "1+1"},
                                            "id": "c1",
                                        },
                                        "thoughtSignature": "sig",
                                    }
                                ],
                            },
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {
                        "promptTokenCount": 100,
                        "candidatesTokenCount": 10,
                        "thoughtsTokenCount": 4,
                    },
                }

            def respond(req):
                reqs.append(req)
                return httpx.Response(200, json=response)

            async with httpx.AsyncClient(
                transport=httpx.MockTransport(respond)
            ) as client:
                policy = freeze_model_settings(
                    {"provider": name, "stream_model": False}
                )
                model, api = create_model(
                    policy, {spec.credential_env: "offline-test-only"}, client=client
                )
                wire = model.prepare(context, None)
                raw = await model.complete({"wire": wire})
                decoded = model.decode(raw)
                assert decoded["complete"] and decoded["calls"] == [
                    {"name": "calculate", "arguments": {"expression": "1+1"}}
                ], name
                previous = {
                    "request": wire["payload"],
                    "response": raw,
                    "observations": [
                        {"index": 0, "_ref": "observation", "result": {"exact": "2"}}
                    ],
                }
                continued = model.prepare(context, previous)
                assert continued["window_mode"] == "continued", name
                assert (
                    "private wire continuity" in json.dumps(continued)
                    if spec.protocol != "gemini"
                    else "thoughtSignature" in json.dumps(continued)
                ), name
                assert (
                    len(reqs) == 1
                    and reqs[0].headers[spec.auth_header]
                    == spec.auth_prefix + "offline-test-only"
                ), name
                assert all(
                    "offline-test-only" not in json.dumps(x)
                    for x in [wire, raw, continued]
                ), name
                counts[name] = "request/decode/continuation PASS"
        searchdata = {
            "tavily": {
                "results": [
                    {
                        "url": "https://example.com/a",
                        "title": "A",
                        "content": "lead",
                        "raw_content": "original text",
                    }
                ]
            },
            "exa": {
                "results": [
                    {
                        "url": "https://example.com/a",
                        "title": "A",
                        "text": "original text",
                        "highlights": ["quoted passage"],
                    }
                ]
            },
            "brave": {
                "grounding": {
                    "generic": [
                        {
                            "url": "https://example.com/a",
                            "title": "A",
                            "snippets": ["quoted passage"],
                        }
                    ]
                }
            },
            "perplexity": {
                "results": [
                    {
                        "url": "https://example.com/a",
                        "title": "A",
                        "snippet": "selected excerpt",
                    }
                ]
            },
            "bocha": {
                "code": 200,
                "data": {
                    "webPages": {
                        "value": [
                            {
                                "url": "https://example.com/a",
                                "name": "A",
                                "snippet": "lead",
                                "summary": "vendor summary",
                            }
                        ]
                    }
                },
            },
            "duckduckgo": '<a class="result__a" href="https://example.com/a">A</a><a class="result__snippet">lead</a>',
        }
        for name in SEARCH:
            calls = []

            def reply(req):
                calls.append(req)
                return (
                    httpx.Response(200, text=searchdata[name])
                    if name == "duckduckgo"
                    else httpx.Response(200, json=searchdata[name])
                )

            async with httpx.AsyncClient(
                transport=httpx.MockTransport(reply)
            ) as client:
                from epivra.web_providers import CONNECTIONS

                provider = connect(
                    name, {CONNECTIONS[name][1]: "offline-test-only"}, client
                )
                raw = await provider.search({"query": "question"})
                out = provider.decode_search(raw)
                assert len(calls) == 1 and len(out["results"]) == 1
                assert bool(out["sources"]) == (name not in {"bocha", "duckduckgo"})
                if name == "bocha":
                    assert out["results"][0]["summary_type"] == "provider_summary"
        publicdata = {
            "search_crossref": {
                "status": "ok",
                "message": {
                    "items": [{"DOI": "x", "title": ["A"]}],
                    "total-results": 1,
                },
            },
            "search_pubmed": {"esearchresult": {"count": "1", "idlist": ["123"]}},
            "read_pubmed": "<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><ArticleTitle>Title</ArticleTitle><Abstract><AbstractText>Abstract</AbstractText></Abstract></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>",
            "search_europe_pmc": {
                "hitCount": 1,
                "nextCursorMark": "next",
                "resultList": {"result": [{"id": "123"}]},
            },
            "world_bank_indicators": [
                {"page": 1, "pages": 1},
                [{"id": "SP.POP.TOTL", "name": "Population"}],
            ],
            "query_world_bank": [
                {"page": 1, "pages": 1, "lastupdated": "2026-01-01"},
                [{"value": None, "date": "2025"}],
            ],
        }
        args = {
            "search_crossref": {"query": "x"},
            "search_pubmed": {"query": "x"},
            "read_pubmed": {"ids": ["123"]},
            "search_europe_pmc": {"query": "x"},
            "world_bank_indicators": {},
            "query_world_bank": {
                "indicator": "SP.POP.TOTL",
                "country": "CN",
                "start_year": 2025,
                "end_year": 2025,
            },
        }
        for tool, (name, *_) in TOOLS.items():
            calls = []

            def reply(req):
                calls.append(req)
                return (
                    httpx.Response(200, text=publicdata[tool])
                    if tool == "read_pubmed"
                    else httpx.Response(200, json=publicdata[tool])
                )

            async with httpx.AsyncClient(
                transport=httpx.MockTransport(reply)
            ) as client:
                p = PublicSource(name, client)
                out = p.decode(await p.invoke(tool, args[tool]))
                assert len(calls) == 1 and out["sources"]
                if tool == "query_world_bank":
                    assert out["records"][0]["value"] is None
        pages = []

        def discovery_reply(req):
            pages.append(req)
            return httpx.Response(
                200,
                json={
                    "data": [{"id": "m" + str(len(pages))}],
                    "has_more": len(pages) < 2,
                    "last_id": "next",
                },
            )

        found = discover(
            "claude",
            "global",
            "offline",
            transport=httpx.MockTransport(discovery_reply),
        )
        assert len(found["models"]) == 2 and pages[1].url.params["after_id"] == "next"
        events = [
            {
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": "ok"},
                        "finish_reason": None,
                    }
                ]
            },
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
            {"choices": [], "usage": {"prompt_tokens": 3, "completion_tokens": 1}},
        ]
        stream = (
            "".join("data: " + json.dumps(x) + "\n\n" for x in events)
            + "data: [DONE]\n\n"
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, text=stream))
        ) as client:
            raw = await JsonAPI("https://example.com", "offline", client).chat_stream(
                "/chat", {}
            )
            assert (
                raw["data"]["choices"][0]["message"]["content"] == "ok"
                and raw["data"]["usage"]["prompt_tokens"] == 3
            )
        seen = []

        def redirected(req):
            seen.append(req)
            return httpx.Response(
                302, headers={"location": "https://other.example/private"}
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(redirected)
        ) as client:
            raw = await JsonAPI("https://example.com", "offline", client).post("/x", {})
            assert raw == {"http_status": 302} and len(seen) == 1
        questions = {"q": {"type": "choice", "criteria": {"yes": "yes", "no": "no"}}}
        Jev.decode(
            {
                "http_status": 200,
                "data": {
                    "model": MODEL,
                    "answers": {
                        "q": {
                            "type": "choice",
                            "choice": "yes",
                            "confidence": 0.8,
                            "probabilities": {"yes": 0.8, "no": 0.2},
                        }
                    },
                },
            },
            questions,
        )
        assert (
            counters(
                {
                    "data": {
                        "usage": {
                            "input_tokens": 100,
                            "output_tokens": 10,
                            "cache_read_input_tokens": 20,
                        }
                    }
                }
            )["total_tokens"]
            == 130
        )
        print(
            json.dumps(
                {
                    "model_adapters": counts,
                    "search_providers": len(SEARCH),
                    "public_source_tools": len(TOOLS),
                    "extra": [
                        "paginated discovery",
                        "SSE usage",
                        "redirect no-forward",
                        "Jev typed answer",
                        "cache token accounting",
                    ],
                    "result": "PASS",
                    "real_network_calls": 0,
                }
            )
        )
