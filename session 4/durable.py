# durable.py — a settlement run that survives a flaky FX service AND a crash half-way through.
# No API key needed. Run it twice:  python durable.py   (crashes at "settle")  then  python durable.py  (resumes)
import sqlite3
from typing_extensions import TypedDict
from langgraph.cache.memory import InMemoryCache
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import CachePolicy, RetryPolicy

calls = {"fx": 0}

class Run(TypedDict, total=False):
    merchant: str
    amount_eur: float
    eur_usd: float
    amount_usd: float
    settled: str

def fetch_fx(state: Run):
    """A flaky upstream service: the first 2 calls time out. RetryPolicy retries with backoff (0.2s, 0.4s, ...)."""
    calls["fx"] += 1
    print(f"  fetch_fx attempt {calls['fx']}")
    if calls["fx"] <= 2:
        raise ConnectionError("FX provider timed out")
    return {"eur_usd": 1.10}

def convert(state: Run):
    return {"amount_usd": round(state["amount_eur"] * state["eur_usd"], 2)}

def settle(state: Run):
    """Pretend the process crashes here the first time (a deploy, an OOM kill, a laptop lid closed)."""
    import os
    if not os.path.exists("settle.ok"):
        open("settle.ok", "w").close()
        raise SystemExit("💥 crashed while settling (run the script again to resume)")
    return {"settled": f"{state['merchant']}: paid out {state['amount_usd']:,} USD"}

builder = StateGraph(Run)
builder.add_node(
    "fetch_fx", fetch_fx,
    retry_policy=RetryPolicy(max_attempts=6, initial_interval=0.2, backoff_factor=2.0, retry_on=ConnectionError),
    cache_policy=CachePolicy(ttl=300),           # same inputs within 5 minutes -> reuse the result
)
builder.add_node("convert", convert)
builder.add_node("settle", settle)
builder.add_edge(START, "fetch_fx")
builder.add_edge("fetch_fx", "convert")
builder.add_edge("convert", "settle")
builder.add_edge("settle", END)

conn = sqlite3.connect("durable.sqlite", check_same_thread=False)
graph = builder.compile(checkpointer=SqliteSaver(conn), cache=InMemoryCache())
config = {"configurable": {"thread_id": "settlement-ACME-2026-10"}}

if __name__ == "__main__":
    state = graph.get_state(config)
    if state.values.get("settled"):                  # this thread already finished
        print("already settled:", state.values["settled"])
        print("delete durable.sqlite and settle.ok to start over")
        raise SystemExit
    if state.next:                                   # an unfinished run exists for this thread: resume it
        print(f"resuming at {state.next} (fetch_fx and convert are NOT run again)")
        result = graph.invoke(None, config, durability="sync")
    else:
        print("new run")
        result = graph.invoke({"merchant": "ACME", "amount_eur": 6_200_000}, config, durability="sync")
    print(result["settled"])
    print(f"FX service was called {calls['fx']} time(s) in this process")