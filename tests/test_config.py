from __future__ import annotations

import unittest

from deep_research_agent.config import (
    DEFAULT_ROLE_TIERS,
    ROLES,
    ConfigError,
    load_config,
)
from deep_research_agent.providers.llm import (
    LLM_PROVIDERS,
    configured_llm_providers,
    resolve_llm_provider,
)

DEEPSEEK = {"DEEPSEEK_API_KEY": "ds-key"}


class LlmRegistryTest(unittest.TestCase):
    def test_every_vendor_declares_both_tiers_and_a_credential(self) -> None:
        for spec in LLM_PROVIDERS:
            with self.subTest(provider=spec.name):
                self.assertTrue(spec.api_base.startswith("https://"))
                self.assertTrue(spec.key_env_var.isupper())
                self.assertNotEqual(spec.reasoning_model, spec.fast_model)
                self.assertEqual(spec.reasoning_model, spec.default_model("reasoning"))
                self.assertEqual(spec.fast_model, spec.default_model("fast"))

    def test_vendor_names_are_unique(self) -> None:
        names = [spec.name for spec in LLM_PROVIDERS]
        self.assertEqual(len(names), len(set(names)))

    def test_an_unknown_vendor_lists_the_supported_set(self) -> None:
        with self.assertRaises(ValueError) as caught:
            resolve_llm_provider("not-a-vendor")
        self.assertIn("deepseek", str(caught.exception))

    def test_only_credentialed_vendors_are_reported_as_configured(self) -> None:
        configured = configured_llm_providers({"ANTHROPIC_API_KEY": "sk-x"})
        self.assertEqual(("anthropic",), tuple(s.name for s in configured))
        self.assertEqual((), configured_llm_providers({}))


class RoleModelTest(unittest.TestCase):
    def test_investigator_is_cheap_and_judgment_roles_are_not(self) -> None:
        config = load_config(DEEPSEEK)

        self.assertEqual("fast", config.model_for("investigator").tier)
        for role in ("architect", "lead", "curator", "analyst", "author", "reviewer"):
            with self.subTest(role=role):
                self.assertEqual("reasoning", config.model_for(role).tier)

    def test_every_role_resolves_to_a_model(self) -> None:
        config = load_config(DEEPSEEK)

        self.assertEqual(set(ROLES), set(config.role_models))
        self.assertEqual(set(ROLES), set(DEFAULT_ROLE_TIERS))
        for role in ROLES:
            self.assertTrue(config.model_for(role).model_id)

    def test_a_role_tier_can_be_overridden(self) -> None:
        config = load_config({**DEEPSEEK, "DEEP_RESEARCH_CURATOR_TIER": "fast"})

        self.assertEqual("fast", config.model_for("curator").tier)
        self.assertEqual("deepseek-v4-flash", config.model_for("curator").model_id)

    def test_an_exact_model_beats_the_tier_default(self) -> None:
        config = load_config(
            {**DEEPSEEK, "DEEP_RESEARCH_AUTHOR_MODEL": "deepseek-v4-pro-preview"}
        )

        self.assertEqual("deepseek-v4-pro-preview", config.model_for("author").model_id)
        self.assertEqual("deepseek-v4-pro", config.model_for("analyst").model_id)

    def test_a_tier_override_applies_to_every_role_in_that_tier(self) -> None:
        config = load_config({**DEEPSEEK, "DEEP_RESEARCH_FAST_MODEL": "cheap-model"})

        self.assertEqual("cheap-model", config.model_for("investigator").model_id)
        self.assertEqual("deepseek-v4-pro", config.model_for("author").model_id)

    def test_roles_can_run_against_different_vendors(self) -> None:
        config = load_config(
            {
                **DEEPSEEK,
                "ANTHROPIC_API_KEY": "sk-x",
                "DEEP_RESEARCH_AUTHOR_PROVIDER": "anthropic",
            }
        )

        self.assertEqual("anthropic", config.model_for("author").provider.name)
        self.assertEqual("claude-opus-5", config.model_for("author").model_id)
        self.assertEqual("deepseek", config.model_for("analyst").provider.name)

    def test_the_default_profile_uses_exactly_two_models(self) -> None:
        self.assertEqual(
            ("deepseek-v4-flash", "deepseek-v4-pro"),
            load_config(DEEPSEEK).distinct_models,
        )

    def test_a_missing_credential_is_reported_against_its_role(self) -> None:
        config = load_config({})
        with self.assertRaisesRegex(ConfigError, "DEEPSEEK_API_KEY"):
            config.model_for("author").api_key({})

    def test_an_invalid_tier_name_is_refused(self) -> None:
        with self.assertRaisesRegex(ConfigError, "reasoning"):
            load_config({**DEEPSEEK, "DEEP_RESEARCH_LEAD_TIER": "cheapest"})


class SearchSelectionTest(unittest.TestCase):
    def test_the_keyless_fallback_is_appended_by_default(self) -> None:
        config = load_config(DEEPSEEK)
        self.assertEqual(("tavily", "duckduckgo"), config.search_providers)

    def test_an_operator_chooses_the_provider_set(self) -> None:
        config = load_config(
            {**DEEPSEEK, "DEEP_RESEARCH_SEARCH_PROVIDERS": "exa, brave"}
        )
        self.assertEqual(("exa", "brave", "duckduckgo"), config.search_providers)

    def test_the_fallback_can_be_switched_off(self) -> None:
        config = load_config(
            {**DEEPSEEK, "DEEP_RESEARCH_DUCKDUCKGO_FALLBACK": "0"}
        )
        self.assertEqual(("tavily",), config.search_providers)

    def test_the_fallback_is_never_listed_twice(self) -> None:
        config = load_config(
            {**DEEPSEEK, "DEEP_RESEARCH_SEARCH_PROVIDERS": "duckduckgo"}
        )
        self.assertEqual(("duckduckgo",), config.search_providers)

    def test_an_unknown_provider_lists_the_supported_set(self) -> None:
        with self.assertRaisesRegex(ConfigError, "unknown search providers"):
            load_config({**DEEPSEEK, "DEEP_RESEARCH_SEARCH_PROVIDERS": "google"})

    def test_keyless_academic_search_is_on_by_default(self) -> None:
        self.assertEqual(
            ("arxiv", "crossref", "pubmed"), load_config(DEEPSEEK).academic_providers
        )

    def test_academic_providers_are_individually_switchable(self) -> None:
        config = load_config({**DEEPSEEK, "DEEP_RESEARCH_PUBMED_SEARCH": "no"})
        self.assertEqual(("arxiv", "crossref"), config.academic_providers)

    def test_a_non_boolean_flag_is_refused(self) -> None:
        with self.assertRaisesRegex(ConfigError, "boolean"):
            load_config({**DEEPSEEK, "DEEP_RESEARCH_ARXIV_SEARCH": "sometimes"})


if __name__ == "__main__":
    unittest.main()
