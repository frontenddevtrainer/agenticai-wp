"""Day 8 Lab 1: trace the Day 7 crew with self-hosted Langfuse (and attach the cost ledger).

Prereq: Langfuse running (docker compose up in the langfuse repo) and LANGFUSE_* keys in .env.
Run:    python traced_crew.py
"""
import os

from dotenv import load_dotenv

load_dotenv()
if not (os.getenv("LANGFUSE_PUBLIC_KEY", "").startswith("pk-lf-") and len(os.getenv("LANGFUSE_PUBLIC_KEY")) > 8):
    raise SystemExit("Set LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST in .env (create a project in the "
                     "Langfuse UI at http://localhost:3000).")

from langfuse import get_client, observe            # noqa: E402
from langfuse.langchain import CallbackHandler      # noqa: E402  (v3+/v4 path; NOT langfuse.callback)

from cost_ledger import CostLedger                  # noqa: E402
from crew_langgraph import INITIAL, crew            # noqa: E402
from data import MERCHANTS                          # noqa: E402

langfuse = get_client()


@observe(name="load-month-end-settlements")
def load_settlements(month: str) -> dict:
    """A plain-Python step that shows up as its own span."""
    return {mid: len(m["mtd_volume"]) for mid, m in MERCHANTS.items()}


if __name__ == "__main__":
    load_settlements("2026-10")
    ledger = CostLedger(budget_usd=2.00)
    out = crew.invoke(INITIAL, config={
        "callbacks": [CallbackHandler(), ledger],
        "metadata": {"langfuse_session_id": "month-end-2026-10", "langfuse_user_id": "analyst-42",
                     "langfuse_tags": ["crew-v1", "lab"]},
        "run_name": "monthly-risk-report",
        "recursion_limit": 30,
    })
    langfuse.flush()  # short-lived script: flush before exit
    print(out["draft"][:600], "\n\nREVIEW:", out["review"])
    ledger.print_report()
    print("\nOpen http://localhost:3000 -> Traces -> 'monthly-risk-report'")