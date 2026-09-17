import unittest

from epivra.calculation import calculate


class CalculationTests(unittest.TestCase):
    def test_fractional_power_growth_discount_and_real_domain(self):
        for expression, expected in (
            ("(1.4641)^(1/4)-1", 0.1),
            ("100/(1.05**2)", 90.70294785),
            ("9^0.5", 3),
        ):
            result = calculate(expression)
            self.assertAlmostEqual(float(result["decimal"]), expected, places=5)
        self.assertIsNone(calculate("2^(1/2)")["exact"])
        self.assertEqual("-8", calculate("(-2)^3")["exact"])
        for expression in ("(-2)^0.5", "0^0", "0^-1", "10^1000000"):
            with self.assertRaises(ValueError):
                calculate(expression)

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
