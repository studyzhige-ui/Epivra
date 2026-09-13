import unittest

from epivra.calculation import calculate


class CalculationTests(unittest.TestCase):
    def test_decimal_inputs_are_exact_and_repeating_results_are_labeled(self):
        self.assertEqual("3/10", calculate("0.1 + 0.2")["exact"])
        self.assertEqual("22", calculate("(20+22+24)/3")["exact"])
        self.assertEqual("3/7", calculate("1/0.7-1")["exact"])
        self.assertEqual("-50", calculate("-1e2 / +2")["exact"])
        result = calculate("1/3")
        self.assertEqual("1/3", result["exact"])
        self.assertEqual(50, result["decimal_significant_digits"])

    def test_no_code_execution_and_bounded_arithmetic(self):
        for expression in (
            "0xFF",
            "__import__('os')",
            "True+1",
            "x+1",
            "1/0",
            "2**1000000",
            "[1,2]",
            "1e301",
            "+".join(["1"] * 100),
            "1" * 2001,
        ):
            with (
                self.subTest(expression=expression[:30]),
                self.assertRaises(ValueError),
            ):
                calculate(expression)
