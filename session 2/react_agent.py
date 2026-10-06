"""Day 2 - Lab 1: a ReAct agent from scratch. No framework: just a loop.

Run:  python lab1_react_agent.py
      python lab1_react_agent.py "Is BOLT over its processing limit?"
"""
import ast
import json
import operator
import sys
from typing import Literal

from pydantic import BaseModel, Field

from llm import MODEL, client   # Claude via OpenRouter (see llm.py)

# ---------------- 1. Data (fictional) ----------------
MERCHANTS = {
    "ACME": {"limit": 9_500_000, "limit_currency": "USD",
             "batches": [(4_200_000, "EUR"), (3_100_000, "USD"), (2_000_000, "EUR")]},
    "BOLT": {"limit": 5_000_000, "limit_currency": "GBP",
             "batches": [(1_500_000, "USD"), (2_000_000, "GBP")]},
    "CRUX": {"limit": 800_000_000, "limit_currency": "INR",
             "batches": [(650_000_000, "INR"), (2_000_000, "USD")]},
}
FX = {("EUR", "USD"): 1.10, ("GBP", "USD"): 1.30, ("USD", "INR"): 85.0}


# ---------------- 2. Tool schemas (pydantic -> JSON schema the model reads) ----------------
class MerchantInput(BaseModel):
    """Look up a merchant: monthly processing limit and this month's settlement batches (amount, currency)."""
    merchant_id: str = Field(description="e.g. ACME")


class FxInput(BaseModel):
    """Get the FX rate to convert 1 unit of `base` into `quote`. Use it for EVERY currency conversion."""
    base: Literal["USD", "EUR", "GBP", "INR"]
    quote: Literal["USD", "EUR", "GBP", "INR"]


class CalcInput(BaseModel):
    """Calculate an arithmetic expression, e.g. '(4200000+2000000)*1.10'. Use it for ALL maths."""
    expression: str


# ---------------- 3. Tool implementations (plain Python) ----------------
def lookup_merchant(merchant_id: str) -> dict:
    if merchant_id.upper() not in MERCHANTS:
        raise ValueError(f"unknown merchant. Valid ids: {list(MERCHANTS)}")
    return MERCHANTS[merchant_id.upper()]


def get_fx_rate(base: str, quote: str) -> float:
    if base == quote:
        return 1.0
    if (base, quote) in FX:
        return FX[(base, quote)]
    if (quote, base) in FX:
        return round(1 / FX[(quote, base)], 6)       # inverse rate
    raise ValueError(f"no rate for {base}/{quote}, convert via USD")


OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def calculator(expression: str) -> float:
    """Safe maths: numbers and + - * / only. Never use eval()!"""
    def ev(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.left), ev(node.right))
        raise ValueError("only numbers and + - * / are allowed")
    return round(ev(ast.parse(expression, mode="eval").body), 4)


TOOLS = [
    {"name": "lookup_merchant", "description": MerchantInput.__doc__, "input_schema": MerchantInput.model_json_schema()},
    {"name": "get_fx_rate", "description": FxInput.__doc__, "input_schema": FxInput.model_json_schema()},
    {"name": "calculator", "description": CalcInput.__doc__, "input_schema": CalcInput.model_json_schema()},
]
FUNCTIONS = {"lookup_merchant": lookup_merchant, "get_fx_rate": get_fx_rate, "calculator": calculator}


def run_tool(name: str, args: dict) -> tuple[str, bool]:
    """Run a tool. Errors are returned to the model (is_error=True) so it can recover."""
    try:
        return json.dumps(FUNCTIONS[name](**args)), False
    except Exception as e:
        return f"Error: {e}", True


# ---------------- 4. The ReAct loop ----------------
SYSTEM = """You are a merchant-risk analyst at Northstar Pay (a payment processor).
Use ONLY the tools. Convert every amount into the limit's currency before comparing.
Finish with one line: OVER_LIMIT / NEAR_LIMIT (above 90%) / OK, and the utilisation %."""
MAX_TURNS = 10


def run_agent(question: str, system: str = SYSTEM, tools: list = TOOLS) -> str:
    messages = [{"role": "user", "content": question}]

    for turn in range(1, MAX_TURNS + 1):
        response = client.messages.create(model=MODEL, max_tokens=4000, system=system,
                                          tools=tools, messages=messages)
        messages.append({"role": "assistant", "content": response.content})   # keep the FULL reply

        if response.stop_reason != "tool_use":                                # THINK done -> answer
            return "".join(b.text for b in response.content if b.type == "text")

        results = []
        for block in response.content:
            if block.type == "tool_use":                                       # ACT
                output, is_error = run_tool(block.name, block.input)
                print(f"[turn {turn}] {block.name}({block.input}) -> {output}")  # OBSERVE
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": output, "is_error": is_error})
        messages.append({"role": "user", "content": results})                  # all results in ONE message

    return f"Stopped after {MAX_TURNS} turns."


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Is ACME over its processing limit?"
    print("\nANSWER:", run_agent(question))