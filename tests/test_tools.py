from __future__ import annotations

import asyncio
import unittest

from deep_research_agent.tools import (
    ProviderInfo,
    ProviderResult,
    SearchRequest,
    SearchRouting,
    TransparentSearchBroker,
)


class AuthenticationError(RuntimeError):
    pass


class FakeProvider:
    def __init__(
        self,
        provider_id: str,
        *,
        results: tuple[ProviderResult, ...] = (),
        failures: tuple[BaseException, ...] = (),
        health: str = "healthy",
        call_log: list[str] | None = None,
    ) -> None:
        self.info = ProviderInfo(
            provider_id=provider_id,
            capabilities=("search",),
            health=health,  # type: ignore[arg-type]
        )
        self.results = results
        self.failures = list(failures)
        self.call_log = call_log
        self.describe_calls = 0
        self.search_calls = 0
        self.requests: list[tuple[str, str, str]] = []

    async def describe(self) -> ProviderInfo:
        self.describe_calls += 1
        return self.info

    async def search(self, *, query: str, intent: str, source_kind: str):
        self.search_calls += 1
        self.requests.append((query, intent, source_kind))
        if self.call_log is not None:
            self.call_log.append(self.info.provider_id)
        if self.failures:
            raise self.failures.pop(0)
        return self.results


class DescribeFailureProvider(FakeProvider):
    provider_id = "broken-catalog"

    async def describe(self) -> ProviderInfo:
        self.describe_calls += 1
        raise RuntimeError("secret catalog failure")


class SlowDescribeProvider(FakeProvider):
    provider_id = "slow-catalog"

    async def describe(self) -> ProviderInfo:
        await asyncio.sleep(60)
        return self.info


class TransparentSearchBrokerTest(unittest.IsolatedAsyncioTestCase):
    async def test_lists_provider_metadata_without_searching(self) -> None:
        first = FakeProvider("alpha")
        second = FakeProvider("beta", health="degraded")
        broker = TransparentSearchBroker([first, second])

        providers = await broker.list_providers()

        self.assertEqual(
            providers,
            (
                ProviderInfo("alpha", ("search",), "healthy"),
                ProviderInfo("beta", ("search",), "degraded"),
            ),
        )
        self.assertEqual((first.describe_calls, second.describe_calls), (1, 1))
        self.assertEqual((first.search_calls, second.search_calls), (0, 0))

    async def test_provider_description_failure_becomes_transparent_unavailable(self) -> None:
        broken = DescribeFailureProvider("ignored")
        healthy = FakeProvider("healthy")
        broker = TransparentSearchBroker([broken, healthy])

        providers = await broker.list_providers()
        response = await broker.search(SearchRequest("evidence", "discover"))

        self.assertEqual(
            ProviderInfo("broken-catalog", (), "unavailable"), providers[0]
        )
        self.assertIn(
            ("broken-catalog", "skipped", "provider_unavailable"),
            [
                (item.provider_id, item.status, item.error_type)
                for item in response.attempts
            ],
        )
        self.assertEqual(1, healthy.search_calls)

    async def test_provider_description_timeout_isolated_from_healthy_provider(self) -> None:
        slow = SlowDescribeProvider("ignored")
        healthy = FakeProvider("healthy")
        providers = await TransparentSearchBroker(
            [slow, healthy], provider_timeout_seconds=0.01
        ).list_providers()

        self.assertEqual("unavailable", providers[0].health)
        self.assertEqual("healthy", providers[1].provider_id)

    async def test_malformed_provider_url_is_filtered_without_breaking_search(self) -> None:
        provider = FakeProvider(
            "malformed",
            results=(
                ProviderResult("bad", "http://example.test:not-a-port/result"),
                ProviderResult("good", "https://example.test/result"),
            ),
        )

        response = await TransparentSearchBroker([provider]).search(
            SearchRequest("evidence", "discover")
        )

        self.assertEqual(1, len(response.results))
        self.assertEqual("good", response.results[0].title)

    async def test_merges_normalized_duplicate_urls_and_all_provider_provenance(
        self,
    ) -> None:
        first = FakeProvider(
            "alpha",
            results=(
                ProviderResult(
                    title="Primary title",
                    url="HTTPS://Example.COM:443/report/",
                    snippet="alpha snippet",
                ),
            ),
        )
        second = FakeProvider(
            "beta",
            results=(
                ProviderResult(
                    title="Alternate title",
                    url="https://example.com/report#results",
                    snippet="beta snippet",
                    content="full text from beta",
                ),
            ),
        )

        response = await TransparentSearchBroker([first, second]).search(
            SearchRequest(query="  evidence  ", intent="  discover  ")
        )

        self.assertEqual(len(response.results), 1)
        result = response.results[0]
        self.assertEqual(result.title, "Primary title")
        self.assertEqual(result.url, "HTTPS://Example.COM:443/report/")
        self.assertEqual(result.snippet, "alpha snippet")
        self.assertEqual(result.content, "full text from beta")
        self.assertEqual(result.provider_ids, ("alpha", "beta"))
        self.assertEqual(result.content_provider_ids, ("beta",))
        self.assertEqual(
            [(attempt.provider_id, attempt.status) for attempt in response.attempts],
            [("alpha", "success"), ("beta", "success")],
        )
        self.assertEqual(first.requests, [("evidence", "discover", "web")])
        self.assertEqual(second.requests, [("evidence", "discover", "web")])

    async def test_identical_full_content_unions_discovery_and_content_provenance(
        self,
    ) -> None:
        content = "the same complete provider body"
        response = await TransparentSearchBroker(
            [
                FakeProvider(
                    "alpha",
                    results=(
                        ProviderResult(
                            "First", "https://example.test/report", content=content
                        ),
                    ),
                ),
                FakeProvider(
                    "beta",
                    results=(
                        ProviderResult(
                            "Second", "https://example.test/report#section", content=content
                        ),
                    ),
                ),
            ]
        ).search(SearchRequest("evidence", "discover"))

        self.assertEqual(1, len(response.results))
        self.assertEqual(("alpha", "beta"), response.results[0].provider_ids)
        self.assertEqual(
            ("alpha", "beta"), response.results[0].content_provider_ids
        )

    async def test_different_full_content_at_same_url_remains_distinct(self) -> None:
        response = await TransparentSearchBroker(
            [
                FakeProvider(
                    "alpha",
                    results=(
                        ProviderResult(
                            "First",
                            "https://example.test/report",
                            content="body returned by alpha",
                        ),
                    ),
                ),
                FakeProvider(
                    "beta",
                    results=(
                        ProviderResult(
                            "Second",
                            "https://example.test/report#section",
                            content="body returned by beta",
                        ),
                    ),
                ),
            ]
        ).search(SearchRequest("evidence", "discover"))

        self.assertEqual(
            ["body returned by alpha", "body returned by beta"],
            [result.content for result in response.results],
        )
        self.assertEqual(
            [("alpha", "beta"), ("alpha", "beta")],
            [result.provider_ids for result in response.results],
        )
        self.assertEqual(
            [("alpha",), ("beta",)],
            [result.content_provider_ids for result in response.results],
        )

    async def test_explicit_source_kind_is_forwarded_without_parsing_intent(self) -> None:
        provider = FakeProvider("alpha")
        await TransparentSearchBroker([provider]).search(
            SearchRequest(
                query="event",
                intent="find current coverage without magic keywords",
                source_kind="news",
            )
        )

        self.assertEqual(
            [("event", "find current coverage without magic keywords", "news")],
            provider.requests,
        )

    async def test_provider_without_news_capability_is_transparently_skipped(self) -> None:
        provider = FakeProvider("web-only")
        provider.info = ProviderInfo("web-only", ("web",))

        response = await TransparentSearchBroker([provider]).search(
            SearchRequest("event", "find coverage", source_kind="news")
        )

        self.assertEqual(0, provider.search_calls)
        self.assertEqual("unsupported_source_kind", response.attempts[0].error_type)

    def test_source_kind_rejects_schema_growth(self) -> None:
        with self.assertRaises(ValueError):
            SearchRequest(
                "evidence",
                "discover",
                source_kind="academic",  # type: ignore[arg-type]
            )

    async def test_failed_attempt_is_transparent_but_never_exposes_error_details(
        self,
    ) -> None:
        secret = "credential-that-must-not-leak"
        failing = FakeProvider(
            "private-provider",
            failures=(AuthenticationError(f"401 unauthorized token={secret}"),),
        )

        response = await TransparentSearchBroker(
            [failing], transient_retries=3
        ).search(SearchRequest(query="evidence", intent="discover"))

        self.assertEqual(response.results, ())
        self.assertEqual(len(response.attempts), 1)
        attempt = response.attempts[0]
        self.assertEqual(attempt.provider_id, "private-provider")
        self.assertEqual(attempt.status, "failed")
        self.assertEqual(attempt.error_type, "auth_failed")
        self.assertNotIn(secret, repr(response))
        self.assertNotIn("token=", repr(response))

    async def test_only_and_exclude_route_to_exact_provider_sets(self) -> None:
        only_log: list[str] = []
        only_providers = [
            FakeProvider("alpha", call_log=only_log),
            FakeProvider("beta", call_log=only_log),
            FakeProvider("gamma", call_log=only_log),
        ]
        await TransparentSearchBroker(only_providers).search(
            SearchRequest(
                query="evidence",
                intent="discover",
                routing=SearchRouting(mode="only", providers=("beta",)),
            )
        )
        self.assertEqual(only_log, ["beta"])

        exclude_log: list[str] = []
        exclude_providers = [
            FakeProvider("alpha", call_log=exclude_log),
            FakeProvider("beta", call_log=exclude_log),
            FakeProvider("gamma", call_log=exclude_log),
        ]
        await TransparentSearchBroker(exclude_providers).search(
            SearchRequest(
                query="evidence",
                intent="discover",
                routing=SearchRouting(mode="exclude", providers=("beta",)),
            )
        )
        self.assertEqual(exclude_log, ["alpha", "gamma"])

    async def test_prefer_does_not_call_fallback_when_preferred_provider_succeeds(
        self,
    ) -> None:
        call_log: list[str] = []
        preferred = FakeProvider(
            "preferred",
            results=(ProviderResult("Preferred", "https://preferred.test/result"),),
            call_log=call_log,
        )
        fallback = FakeProvider(
            "fallback",
            results=(ProviderResult("Fallback", "https://fallback.test/result"),),
            call_log=call_log,
        )

        response = await TransparentSearchBroker([preferred, fallback]).search(
            SearchRequest(
                query="evidence",
                intent="discover",
                routing=SearchRouting(mode="prefer", providers=("preferred",)),
            )
        )

        self.assertEqual(call_log, ["preferred"])
        self.assertEqual(fallback.search_calls, 0)
        self.assertEqual(
            [result.provider_ids for result in response.results], [("preferred",)]
        )
        self.assertEqual(
            [(attempt.provider_id, attempt.status) for attempt in response.attempts],
            [("preferred", "success")],
        )

    async def test_prefer_calls_fallback_only_after_preferred_provider_fails(
        self,
    ) -> None:
        call_log: list[str] = []
        preferred = FakeProvider(
            "preferred",
            failures=(RuntimeError("permanent provider failure"),),
            call_log=call_log,
        )
        fallback = FakeProvider(
            "fallback",
            results=(ProviderResult("Fallback", "https://fallback.test/result"),),
            call_log=call_log,
        )

        response = await TransparentSearchBroker(
            [preferred, fallback], transient_retries=0
        ).search(
            SearchRequest(
                query="evidence",
                intent="discover",
                routing=SearchRouting(mode="prefer", providers=("preferred",)),
            )
        )

        self.assertEqual(call_log, ["preferred", "fallback"])
        self.assertEqual(
            [(attempt.provider_id, attempt.status) for attempt in response.attempts],
            [("preferred", "failed"), ("fallback", "success")],
        )
        self.assertEqual(len(response.results), 1)
        self.assertEqual(response.results[0].provider_ids, ("fallback",))

    async def test_transient_errors_retry_only_up_to_the_configured_limit(
        self,
    ) -> None:
        recovering = FakeProvider(
            "recovering",
            results=(ProviderResult("Recovered", "https://example.test/recovered"),),
            failures=(TimeoutError("first timeout"), TimeoutError("second timeout")),
        )
        recovered = await TransparentSearchBroker(
            [recovering], transient_retries=2
        ).search(SearchRequest(query="evidence", intent="discover"))

        self.assertEqual(recovering.search_calls, 3)
        self.assertEqual(
            [(attempt.status, attempt.error_type) for attempt in recovered.attempts],
            [("failed", "timeout"), ("failed", "timeout"), ("success", "")],
        )
        self.assertEqual(len(recovered.results), 1)

        exhausted = FakeProvider(
            "exhausted",
            failures=(
                TimeoutError("first timeout"),
                TimeoutError("second timeout"),
                TimeoutError("third timeout"),
                TimeoutError("must not be attempted"),
            ),
        )
        failed = await TransparentSearchBroker(
            [exhausted], transient_retries=2
        ).search(SearchRequest(query="evidence", intent="discover"))

        self.assertEqual(exhausted.search_calls, 3)
        self.assertEqual(len(failed.attempts), 3)
        self.assertTrue(
            all(
                attempt.status == "failed" and attempt.error_type == "timeout"
                for attempt in failed.attempts
            )
        )
        self.assertEqual(failed.results, ())


if __name__ == "__main__":
    unittest.main()
