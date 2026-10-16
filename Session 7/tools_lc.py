# tools_lc.py: Meridian's tools as LangChain @tool functions (schema comes from type hints + docstring)
import ast
import operator
from typing import Literal

from langchain_core.tools import tool

from data import MERCHANTS, fx_rate

Currency = Literal["USD", "EUR", "GBP", "INR", "JPY", "CHF"]
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def _calc(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_calc(node.left), _calc(node.right))
    raise ValueError("only numbers and + - * / are allowed")


@tool
def calculator(expression: str) -> float:
    """Evaluate an arithmetic expression (+ - * / parentheses). Use for ALL arithmetic."""
    return round(_calc(ast.parse(expression, mode="eval").body), 4)


@tool
def lookup_merchant(merchant_id: str) -> dict:
    """Look up a merchant file: monthly processing limit (amount + currency), risk tier, chargeback ratio
    and this month's settlement batches (amount + currency)."""
    m = MERCHANTS.get(merchant_id.strip().upper())
    if m is None:
        raise ValueError(f"unknown merchant; valid ids: {sorted(MERCHANTS)}")
    return m


@tool
def get_fx_rate(base: Currency, quote: Currency) -> float:
    """Spot FX rate converting 1 unit of `base` into `quote`. Use for ANY currency conversion; never guess rates."""
    return fx_rate(base, quote)


TOOLS = [calculator, lookup_merchant, get_fx_rate]