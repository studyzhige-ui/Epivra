import unittest

import deep_research_agent


class PackageTest(unittest.TestCase):
    def test_version_is_exposed(self) -> None:
        self.assertEqual(deep_research_agent.__version__, "0.1.0")

    def test_public_api_is_the_product_boundary(self) -> None:
        self.assertEqual(
            {
                "__version__",
                "Event",
                "ResearchService",
                "Task",
                "TaskAction",
                "TaskState",
            },
            set(deep_research_agent.__all__),
        )
        for internal in (
            "ArtifactStore",
            "SqliteArtifactStore",
            "SqliteContentStore",
            "SqliteOperationLedger",
            "OperationRequest",
            "run_once",
        ):
            with self.subTest(internal=internal):
                self.assertFalse(hasattr(deep_research_agent, internal))


if __name__ == "__main__":
    unittest.main()
