"""Auditable arithmetic, without Python execution or research-method decisions."""

from __future__ import annotations

import ast
from decimal import Decimal, DecimalException, InvalidOperation, localcontext
from fractions import Fraction


def calculate(expression: str) -> dict:
    # Operational bounds for this arithmetic tool, not model/provider limits.
    if len(expression) > 2000:
        raise ValueError("arithmetic expression too long")
    # This is an arithmetic language, not Python: ^ and ** both denote power.
    parsed_expression = expression.replace("^", "**")
    try:
        tree = ast.parse(parsed_expression, mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise ValueError("invalid arithmetic expression") from exc
    if sum(1 for _ in ast.walk(tree)) > 200:
        raise ValueError("arithmetic expression too complex")

    def number(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            raw = ast.get_source_segment(parsed_expression, node)
            try:
                decimal = Decimal(raw)
            except InvalidOperation as exc:
                raise ValueError("only decimal numeric literals are supported") from exc
            if not decimal.is_finite() or abs(decimal.adjusted()) > 300:
                raise ValueError("numeric literal outside supported range")
            value = Fraction(decimal)
        elif isinstance(node, ast.UnaryOp) and isinstance(
            node.op, (ast.UAdd, ast.USub)
        ):
            value = number(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
        ):
            left, right = number(node.left), number(node.right)
            if isinstance(node.op, ast.Pow):
                if abs(right) > 1000:
                    raise ValueError("power exponent outside supported range")
                if left == 0 and right <= 0:
                    raise ValueError("zero requires a positive exponent")
                if right.denominator == 1:
                    # Check the size before allocating an enormous integer.
                    if (
                        max(left.numerator.bit_length(), left.denominator.bit_length())
                        * abs(right.numerator)
                        > 4096
                    ):
                        raise ValueError("arithmetic result too large")
                    value = left**right.numerator
                else:
                    if left < 0:
                        raise ValueError("fractional powers require a nonnegative base")
                    approximate_power[0] = True
                    with localcontext() as ctx:
                        ctx.prec = 60
                        ctx.Emax, ctx.Emin = 1000, -1000
                        try:
                            result = (
                                Decimal(left.numerator) / Decimal(left.denominator)
                            ) ** (Decimal(right.numerator) / Decimal(right.denominator))
                        except DecimalException as exc:
                            raise ValueError(
                                "power outside supported real range"
                            ) from exc
                        value = Fraction(result)
            elif isinstance(node.op, ast.Add):
                value = left + right
            elif isinstance(node.op, ast.Sub):
                value = left - right
            elif isinstance(node.op, ast.Mult):
                value = left * right
            else:
                if not right:
                    raise ValueError("division by zero")
                value = left / right
        else:
            raise ValueError(
                "only decimal numbers, parentheses and + - * / ** ^ are supported"
            )
        if max(value.numerator.bit_length(), value.denominator.bit_length()) > 4096:
            raise ValueError("arithmetic result too large")
        return value

    approximate_power = [False]
    value = number(tree.body)
    with localcontext() as context:
        context.prec = 50
        approximate = str(Decimal(value.numerator) / Decimal(value.denominator))
    return {
        "expression": expression,
        "exact": None if approximate_power[0] else str(value),
        "decimal": approximate,
        "decimal_significant_digits": 50,
        "scope": "Arithmetic only; units, inputs and method assumptions require research validation.",
    }
