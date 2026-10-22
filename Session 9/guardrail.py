"""Day 8 Lab 3 (Part A): deterministic, pre-execution policy guard on increase_processing_limit.

Policy: increases > 15% need the Risk Committee (agents may not submit them); watchlist merchants are never eligible.
Run:  python guardrail.py
"""
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage

from cost_ledger import CostLedger
from data import MERCHANTS
from meridian import ALL_TOOLS, SYSTEM_PROMPT, build_agent
from tools_sensitive import increase_processing_limit

BLOCK_LOG: list[dict] = []


def policy_violation(args: dict) -> str | None:
    m = MERCHANTS.get(str(args.get("merchant_id", "")).strip().upper())
    if m is None:
        return "unknown merchant"
    current = m["processing_limit"]["amount"]
    pct = (float(args["new_limit"]) - current) / current * 100
    if "Watchlist" in m["kyb_notes"]:
        return "merchant is on the chargeback watchlist (not eligible for increases)"
    if pct > 15:
        return f"increase of {pct:.1f}% exceeds 15%; requires Risk Committee"
    return None


@wrap_tool_call
def risk_policy_guard(request, handler):
    call = request.tool_call
    if call["name"] == "increase_processing_limit":
        reason = policy_violation(call["args"])
        if reason:
            BLOCK_LOG.append({"tool": call["name"], "args": call["args"], "reason": reason})
            return ToolMessage(f"BLOCKED by merchant risk policy guard: {reason}. Do not retry; escalate to a human.",
                               tool_call_id=call["id"], status="error")
    return handler(request)  # allowed -> execute normally (in production also behind the Day 4 HITL gate)


meridian_guarded = build_agent(tools=ALL_TOOLS + [increase_processing_limit], middleware=[risk_policy_guard])

if __name__ == "__main__":
    ledger = CostLedger(budget_usd=1.00)
    for q in ["Raise Bolt's processing limit to 9.9M USD for 3 days (flash sale).",     # ~4% -> allowed
              "Raise ACME's processing limit to 12M USD for 5 days.",                   # ~26% -> BLOCKED
              "Raise CRUX's processing limit by 2% for 3 days."]:                       # watchlist -> BLOCKED
        out = meridian_guarded.invoke({"messages": [("user", q + " Use the increase_processing_limit tool.")]},
                                      {"recursion_limit": 20, "callbacks": [ledger]})
        print(f"\nQ: {q}\nA: {out['messages'][-1].text[:300]}")
    print("\nBLOCK LOG:", BLOCK_LOG)
    ledger.print_report()
    # unit-level checks (no LLM)
    assert policy_violation({"merchant_id": "ACME", "new_limit": 12_000_000}) is not None
    assert policy_violation({"merchant_id": "CRUX", "new_limit": 816_000_000}) is not None
    assert policy_violation({"merchant_id": "ACME", "new_limit": 9_900_000}) is None
    print("policy unit checks passed")