# measure.py — is the crew worth it? Same task, one agent vs the Lab 1 crew: tokens, time, and an independent grade.
# Run:  python measure.py      (makes many model calls: a few minutes, and real tokens)
import time
from langchain.agents import create_agent
from langchain_core.callbacks import get_usage_metadata_callback
from pydantic import BaseModel
from crew_langgraph import INITIAL, crew                    # Lab 1
from llm import chat_model
from tools_lc import calculator, get_fx_rate, lookup_merchant

TASK = INITIAL["task"]
single = create_agent(chat_model(), tools=[calculator, lookup_merchant, get_fx_rate], system_prompt=(
    "You are Northstar Pay's merchant risk analyst. Compute each merchant's MTD volume in its limit currency with the tools, "
    "utilisation % and verdict (OVER_LIMIT >100%, NEAR_LIMIT >90%, else OK), then write a short committee report: "
    "summary, table, and recommended actions for any breach. Never invent numbers."))

class Grade(BaseModel):
    correct_verdicts: int                                    # out of 3
    has_actions_for_breaches: bool

grader = chat_model(max_tokens=2000).with_structured_output(Grade)
KEY = "Correct: ACME 9.92M USD 104.4% OVER_LIMIT; BOLT 3.15M GBP 63.1% OK; CRUX 820M INR 102.5% OVER_LIMIT (on chargeback watchlist)."

def run(name, fn):
    start = time.perf_counter()
    with get_usage_metadata_callback() as usage:             # counts tokens across every model call inside
        report = fn()
    seconds = time.perf_counter() - start
    tokens = sum(u["total_tokens"] for u in usage.usage_metadata.values())
    g = grader.invoke(f"{KEY}\n\nREPORT:\n{report}\n\nHow many of the 3 verdicts are correct? Are actions given for breaches?")
    print(f"{name:<8} {tokens:>8,} tokens  {seconds:>6.1f}s   verdicts {g.correct_verdicts}/3   actions: {g.has_actions_for_breaches}")

if __name__ == "__main__":
    run("single", lambda: single.invoke({"messages": [("user", TASK)]}, {"recursion_limit": 40})["messages"][-1].text)
    run("crew", lambda: crew.invoke(INITIAL, {"recursion_limit": 30})["draft"])