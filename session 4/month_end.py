# month_end.py — review every merchant IN PARALLEL, then merge the results into one report.
# No API key needed: the review is deterministic. Run:  python month_end.py
import operator
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

MERCHANTS = {
    "ACME": {"limit": 9_500_000, "currency": "USD", "batches": [(4_200_000, "EUR"), (3_100_000, "USD"), (2_000_000, "EUR")]},
    "BOLT": {"limit": 5_000_000, "currency": "GBP", "batches": [(1_500_000, "USD"), (2_000_000, "GBP")]},
    "CRUX": {"limit": 800_000_000, "currency": "INR", "batches": [(650_000_000, "INR"), (2_000_000, "USD")]},
}
FX = {("EUR", "USD"): 1.10, ("GBP", "USD"): 1.30, ("USD", "INR"): 85.0}

def rate(src: str, dst: str) -> float:
    if src == dst:
        return 1.0
    if (src, dst) in FX:
        return FX[(src, dst)]
    return 1 / FX[(dst, src)]                      # e.g. USD -> GBP from the GBP -> USD rate

class MonthEnd(TypedDict):
    merchants: list[str]
    # Reducer: each parallel branch RETURNS a one-item list; operator.add concatenates them.
    # Without it, branches would overwrite each other's results.
    reviews: Annotated[list[dict], operator.add]
    report: str

class ReviewInput(TypedDict):                      # what each parallel branch receives
    merchant_id: str

def fan_out(state: MonthEnd):
    """One Send per merchant: LangGraph runs these branches in parallel (a 'map')."""
    return [Send("review_merchant", {"merchant_id": m}) for m in state["merchants"]]

def review_merchant(task: ReviewInput):
    write = get_stream_writer()                    # custom progress events for a UI
    m_id = task["merchant_id"]
    m = MERCHANTS[m_id]
    write({"progress": f"reviewing {m_id}"})
    volume = sum(amount * rate(cur, m["currency"]) for amount, cur in m["batches"])
    pct = volume / m["limit"] * 100
    verdict = "OVER_LIMIT" if pct > 100 else "NEAR_LIMIT" if pct > 90 else "OK"
    write({"progress": f"{m_id} done: {verdict}"})
    return {"reviews": [{"merchant": m_id, "volume": round(volume), "currency": m["currency"], "pct": round(pct, 1), "verdict": verdict}]}

def write_report(state: MonthEnd):
    """The 'reduce': runs once, after every branch has finished."""
    rows = sorted(state["reviews"], key=lambda r: -r["pct"])
    lines = ["merchant  volume (limit ccy)        used   verdict"]
    lines += [f"{r['merchant']:<8}  {r['volume']:>16,} {r['currency']}  {r['pct']:>6}%  {r['verdict']}" for r in rows]
    return {"report": "\n".join(lines)}

builder = StateGraph(MonthEnd)

builder.add_node("review_merchant", review_merchant)
builder.add_node("write_report", write_report)

builder.add_conditional_edges(START, fan_out, ["review_merchant"])
builder.add_edge("review_merchant", "write_report")
builder.add_edge("write_report", END)

graph = builder.compile()

if __name__ == "__main__":
    # stream_mode="custom" shows our progress events; "updates" shows which node produced what.
    for mode, chunk in graph.stream({"merchants": list(MERCHANTS)}, stream_mode=["custom", "updates"]):
        if mode == "custom":
            print("  ·", chunk["progress"])
        elif "write_report" in chunk:
            print("\n" + chunk["write_report"]["report"])