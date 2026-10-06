import ast
import json
import operator
import sys
from typing import Literal
from pydantic import BaseModel, Field

from llm import client, MODEL  # Claude via OpenRouter (see llm.py)

MERCHANTS = {
    "ACME": {"limit": 9_500_000, "limit_currency": "USD",
             "batches": [(4_200_000, "EUR"), (3_100_000, "USD"), (2_000_000, "EUR")]},
    "BOLT": {"limit": 5_000_000, "limit_currency": "GBP",
             "batches": [(1_500_000, "USD"), (2_000_000, "GBP")]},
    "CRUX": {"limit": 800_000_000, "limit_currency": "INR",
             "batches": [(650_000_000, "INR"), (2_000_000, "USD")]},
}
FX = {("EUR", "USD"): 1.10, ("GBP", "USD"): 1.30, ("USD", "INR"): 85.0}



class CalcInput(BaseModel):
    """Calculate an arithmetic expression, e.g. '(4200000+2000000)*1.10'. Use it for ALL maths."""
    expression: str


# ---------------- 3. Tool implementations (plain Python) ----------------
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
    {
        "name": "calculator", "description": CalcInput.__doc__, "input_schema": CalcInput.model_json_schema()
    }
]
FUNCTIONS = {"calculator" : calculator}


def run_tool(name: str, args: dict) -> tuple[str, bool]:
    try:
        return json.dumps(FUNCTIONS[name](**args)), False
    except Exception as e:
            return f"Error: {e}", True


SYSTEM = """You are a merchant-risk analyst at Northstar Pay (a payment processor).
Use ONLY the tools. Convert every amount into the limit's currency before comparing.
Finish with one line: OVER_LIMIT / NEAR_LIMIT (above 90%) / OK, and the utilisation %."""
MAX_TURNS = 10

def run_agent(question: str, system: str = SYSTEM, tools: list = TOOLS) -> str:

    messages = [{"role": "user", "content": question}]

    for turn in range(1, MAX_TURNS + 1)
        response = client.message.create(model=MODEL, max_token=4000, system=system, tools=tools, messages=messages)

        messages.append({ "role": "assistant", "content" : response.content })

        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text") # THINK done -> answer

        results = []
        for block in response.content:
            if block.type == "tool_use": # ACT
                output, is_error = run_tool(block.name, block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": output, "is_error": is_error})

                messages.append({"role": "user", "content": results})

        return f"Stopped after {MAX_TURNS} turns."

    if __name__ == "__main__":
        question = " ".join(sys.argv[1:]) or "Is ACME over its processing limit?"
    print("\nANSWER:", run_agent(question))

