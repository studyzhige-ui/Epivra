import unittest

import deep_research_agent


class PackageTest(unittest.TestCase):
    def test_version_is_exposed(self) -> None:
        self.assertEqual(deep_research_agent.__version__, "0.1.0")


if __name__ == "__main__":
    unittest.main()
