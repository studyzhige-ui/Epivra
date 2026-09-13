"""Auditable arithmetic, without Python execution or research-method decisions."""

from __future__ import annotations

import ast
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction


def calculate(expression: str) -> dict:
    # Operational bounds for this arithmetic tool, not model/provider limits.
    if len(expression) > 2000:
        raise ValueError("arithmetic expression too long")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise ValueError("invalid arithmetic expression") from exc
    if sum(1 for _ in ast.walk(tree)) > 200:
        raise ValueError("arithmetic expression too complex")

    def number(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            raw = ast.get_source_segment(expression, node)
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
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)
        ):
            left, right = number(node.left), number(node.right)
            if isinstance(node.op, ast.Add):
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
                "only decimal numbers, parentheses and + - * / are supported"
            )
        if max(value.numerator.bit_length(), value.denominator.bit_length()) > 4096:
            raise ValueError("arithmetic result too large")
        return value

    value = number(tree.body)
    with localcontext() as context:
        context.prec = 50
        approximate = str(Decimal(value.numerator) / Decimal(value.denominator))
    return {
        "expression": expression,
        "exact": str(value),
        "decimal": approximate,
        "decimal_significant_digits": 50,
        "scope": "Arithmetic only; units, inputs and method assumptions require research validation.",
    }
