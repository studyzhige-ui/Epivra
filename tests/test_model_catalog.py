"""Offline catalogue contract checks; these do not certify live model availability."""

import unittest
from dataclasses import FrozenInstanceError
from urllib.parse import urlsplit

from epivra.model_catalog import (
    OFFICIAL_PROVIDERS,
    get_provider,
    resolve_endpoint,
)


class ModelCatalogTests(unittest.TestCase):
    def test_official_catalog_is_explicit_and_self_consistent(self):
        self.assertEqual(
            set(OFFICIAL_PROVIDERS),
            {
                "openai",
                "claude",
                "gemini",
                "grok",
                "deepseek",
                "qwen",
                "kimi",
                "glm",
                "doubao",
                "minimax",
                "hunyuan",
                "ernie",
            },
        )
        for name, provider in OFFICIAL_PROVIDERS.items():
            with self.subTest(provider=name):
                self.assertEqual(provider.id, name)
                self.assertIn(provider.protocol, {"chat", "anthropic", "gemini"})
                self.assertTrue(provider.credential_env.endswith("_API_KEY"))
                self.assertEqual(len(dict(provider.endpoints)), len(provider.endpoints))
                self.assertEqual(
                    resolve_endpoint(name),
                    dict(provider.endpoints)[provider.default_region],
                )
                self.assertTrue(provider.default_model.sources)
                for _, endpoint in provider.endpoints:
                    parsed = urlsplit(endpoint)
                    self.assertEqual(parsed.scheme, "https")
                    self.assertTrue(parsed.hostname)
                    self.assertIsNone(parsed.username)
                    self.assertFalse(parsed.query)
                model = provider.default_model
                for capacity in (
                    model.context_tokens,
                    model.max_output_tokens,
                    model.default_output_tokens,
                    model.recommended_output_tokens,
                ):
                    if capacity is not None:
                        self.assertIs(type(capacity), int)
                        self.assertGreater(capacity, 0)
                if (
                    model.default_output_tokens is not None
                    and model.max_output_tokens is not None
                ):
                    self.assertLessEqual(
                        model.default_output_tokens, model.max_output_tokens
                    )

    def test_identity_and_region_never_fall_back_to_another_host(self):
        for name in ("relay", "https://api.openai.com/v1", "OpenAI", ""):
            with self.assertRaises(ValueError):
                get_provider(name)
        for region in ("", "singapore", "https://example.com"):
            with self.assertRaises(ValueError):
                resolve_endpoint("qwen", region)
        self.assertEqual(
            resolve_endpoint("hunyuan", "singapore"),
            "https://tokenhub-intl.tencentmaas.com/v1",
        )

    def test_native_auth_and_output_parameter_contracts(self):
        claude = get_provider("claude")
        self.assertEqual((claude.auth_header, claude.auth_prefix), ("x-api-key", ""))
        self.assertEqual(dict(claude.headers)["anthropic-version"], "2023-06-01")
        gemini = get_provider("gemini")
        self.assertEqual(
            (gemini.auth_header, gemini.auth_prefix), ("x-goog-api-key", "")
        )
        self.assertEqual(gemini.default_model.output_parameter, "maxOutputTokens")
        self.assertEqual(
            get_provider("openai").default_model.output_parameter,
            "max_completion_tokens",
        )

    def test_unknown_capacity_is_not_replaced_with_a_fictional_default(self):
        grok = get_provider("grok").default_model
        self.assertIsNone(grok.max_output_tokens)
        self.assertEqual(grok.default_output_tokens, 128_000)
        deepseek = get_provider("deepseek").default_model
        self.assertEqual(deepseek.default_output_tokens, 65_536)
        self.assertEqual(deepseek.max_output_tokens, 393_216)
        self.assertLess(deepseek.default_output_tokens, deepseek.max_output_tokens)

    def test_unverified_streaming_is_disabled_and_presets_are_frozen(self):
        minimax = get_provider("minimax").default_model
        self.assertFalse(minimax.supports_stream)
        self.assertIsNone(minimax.default_output_tokens)
        self.assertEqual(minimax.recommended_output_tokens, 131_072)
        self.assertTrue(dict(minimax.request_fields)["reasoning_split"])
        with self.assertRaises(FrozenInstanceError):
            minimax.id = "other"


if __name__ == "__main__":
    unittest.main()
