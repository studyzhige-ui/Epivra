"""Model discovery contract tests: official-shaped responses, no network."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from epivra import cli_settings
from epivra.model_catalog import OFFICIAL_PROVIDERS, resolve_endpoint
from epivra.model_discovery import DISCOVERY, DiscoveryError, discover
from epivra.webui import App


class DiscoveryTests(unittest.TestCase):
    def test_official_urls_auth_and_no_generation(self):
        for name in DISCOVERY:
            with self.subTest(provider=name):
                provider = OFFICIAL_PROVIDERS[name]

                def handler(request):
                    self.assertEqual("GET", request.method)
                    suffix = "/language-models" if name == "grok" else "/models"
                    self.assertEqual(resolve_endpoint(name) + suffix, str(request.url))
                    self.assertEqual(
                        provider.auth_prefix + "secret",
                        request.headers[provider.auth_header],
                    )
                    self.assertNotIn("secret", str(request.url))
                    if name == "gemini":
                        body = {
                            "models": [
                                {
                                    "name": "models/gemini-example",
                                    "supportedGenerationMethods": ["generateContent"],
                                },
                                {
                                    "name": "models/embedding",
                                    "supportedGenerationMethods": ["embedContent"],
                                },
                            ]
                        }
                    else:
                        body = {
                            "models" if name == "grok" else "data": [
                                {"id": provider.default_model.id}
                            ]
                        }
                    return httpx.Response(200, json=body)

                result = discover(
                    name, None, "secret", transport=httpx.MockTransport(handler)
                )
                self.assertEqual("account", result["source"])
                self.assertEqual(1, len(result["models"]))
                self.assertNotIn("secret", str(result))

    def test_pagination_and_capacities(self):
        for name in ("claude", "gemini"):
            calls = []

            def handler(request):
                calls.append(request)
                first = len(calls) == 1
                if name == "claude":
                    body = {
                        "data": [
                            {
                                "id": "one" if first else "two",
                                "max_input_tokens": 100000,
                                "max_tokens": 8000,
                            }
                        ],
                        "has_more": first,
                        "last_id": "one" if first else "two",
                    }
                else:
                    body = {
                        "models": [
                            {
                                "name": "models/one" if first else "models/two",
                                "supportedGenerationMethods": ["generateContent"],
                                "inputTokenLimit": 100000,
                                "outputTokenLimit": 8000,
                            }
                        ]
                    }
                    if first:
                        body["nextPageToken"] = "cursor"
                return httpx.Response(200, json=body)

            result = discover(
                name, None, "secret", transport=httpx.MockTransport(handler)
            )
            self.assertEqual(2, len(result["models"]))
            self.assertEqual(8000, result["models"][0]["max_tokens"])
            self.assertEqual(1, len(calls[1].url.params))

    def test_errors_are_sanitized_and_redirect_not_followed(self):
        for status in (401, 403, 429, 302, 500):
            calls = []

            def handler(request):
                calls.append(request)
                return httpx.Response(
                    status, text="secret", headers={"Location": "https://evil.invalid/"}
                )

            with self.assertRaises(DiscoveryError) as raised:
                discover(
                    "deepseek", None, "secret", transport=httpx.MockTransport(handler)
                )
            self.assertNotIn("secret", str(raised.exception))
            self.assertEqual(1, len(calls))
        with self.assertRaises(DiscoveryError):
            discover(
                "deepseek",
                None,
                "secret",
                transport=httpx.MockTransport(
                    lambda r: httpx.Response(200, text="not json")
                ),
            )

    def test_empty_list_loop_missing_key_and_preset(self):
        result = discover(
            "openai",
            None,
            "secret",
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json={"data": []})
            ),
        )
        self.assertEqual([], result["models"])
        with self.assertRaises(DiscoveryError):
            discover(
                "claude",
                None,
                "secret",
                transport=httpx.MockTransport(
                    lambda r: httpx.Response(
                        200, json={"data": [], "has_more": True, "last_id": "same"}
                    )
                ),
            )
        with self.assertRaises(DiscoveryError):
            discover("deepseek", None, "")
        result = discover(
            "qwen",
            None,
            "secret",
            transport=httpx.MockTransport(
                lambda r: self.fail("must not guess endpoint")
            ),
        )
        self.assertEqual("preset", result["source"])

    def test_effective_key_and_ephemeral_override(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict("os.environ", {}, clear=True),
        ):
            root = Path(directory)
            cli_settings.save_key(root, "DEEPSEEK_API_KEY", "saved")
            with patch(
                "epivra.webui.discover",
                return_value={"models": [], "source": "account"},
            ) as mock:
                App(root).discover_models({"provider": "deepseek", "key": "entered"})
                self.assertEqual("entered", mock.call_args.args[2])
                self.assertEqual("saved", cli_settings.model_key(root, "deepseek"))
            with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "environment"}):
                self.assertEqual(
                    "environment", cli_settings.model_key(root, "deepseek")
                )
                with self.assertRaises(ValueError):
                    cli_settings.model_key(root, "deepseek", "different")

            with patch.dict("os.environ", {"DEEPSEEK_API_KEY": ""}):
                with self.assertRaises(ValueError):
                    cli_settings.model_key(root, "deepseek", "different")
