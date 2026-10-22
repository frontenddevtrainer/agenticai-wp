"""Day 8 Lab 2: eval harness. Outcome + trajectory checks in code, plus tiered LLM-as-judge
(fast judge on every case, strong judge spot-checks 30% + everything flagged).

Run:  python run_evals.py [--with-policies] [--repeat 3] [--workers 4]

Speed knobs (env vars):
  MERIDIAN_MODEL=anthropic/claude-sonnet-5.5   model the AGENT uses (default in llm.py is Opus 5.5)
  EVAL_FAST_JUDGE / EVAL_STRONG_JUDGE           judge models (default: Haiku / Opus via llm.py)
"""
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from langchain_core.messages import AIMessage
from pydantic import BaseModel

from eval_dataset import CASES
from llm import MODEL, MODEL_FAST, chat_model
from meridian import ALL_TOOLS, LimitVerdict, build_agent


class Judgement(BaseModel):
    faithful: bool       # every number/claim is supported by the tool outputs
    currency_ok: bool    # amounts compared in the limit currency
    clear_verdict: bool  # ends with an unambiguous verdict / answer
    reason: str


RUBRIC = ("You grade a merchant-risk agent's final answer. Use ONLY the facts given. Return faithful, currency_ok, "
          "clear_verdict (booleans) and a one-line reason.")

# Fast judge runs on EVERY case -> use the fast model. Strong judge only on flagged cases + 30% spot-checks.
cheap_judge = chat_model(os.getenv("EVAL_FAST_JUDGE", MODEL_FAST), max_tokens=1000).with_structured_output(Judgement)
strong_judge = chat_model(os.getenv("EVAL_STRONG_JUDGE", MODEL), max_tokens=2000).with_structured_output(Judgement)


def agents(with_policies: bool):
    tools = list(ALL_TOOLS)
    if with_policies:
        from agentic_rag import search_policies
        tools.append(search_policies)
    return build_agent(tools=tools, response_format=LimitVerdict), build_agent(tools=tools)


def run_case(c, verdict_agent, text_agent) -> dict:
    agent = verdict_agent if c["kind"] == "verdict" else text_agent
    t0 = time.time()
    try:
        out = agent.invoke({"messages": [("user", c["q"])]}, {"recursion_limit": 25})
    except Exception as e:
        return {"final": f"ERROR {type(e).__name__}: {e}", "verdict": None, "calls": [], "tokens": 0,
                "error": True, "agent_s": round(time.time() - t0, 1)}
    calls = [tc["name"] for m in out["messages"] if isinstance(m, AIMessage) for tc in m.tool_calls
             if tc["name"] != LimitVerdict.__name__]   # create_agent emits the structured response as a tool call
    tokens = sum((m.usage_metadata or {}).get("total_tokens", 0) for m in out["messages"] if isinstance(m, AIMessage))
    verdict = getattr(out.get("structured_response"), "verdict", None)
    return {"final": out["messages"][-1].text, "verdict": verdict, "calls": calls, "tokens": tokens,
            "error": False, "agent_s": round(time.time() - t0, 1)}


def grade_code(c, r) -> dict:
    checks = {}
    if "expect_verdict" in c:
        checks["outcome"] = r["verdict"] == c["expect_verdict"]
    if "expect_text" in c:
        checks["outcome"] = c["expect_text"].lower() in r["final"].lower()
    checks["traj_required"] = all(t in r["calls"] for t in c["must_call"])
    checks["traj_forbidden"] = not any(t in r["calls"] for t in c["must_not_call"])
    checks["traj_efficient"] = len(r["calls"]) <= 10
    return checks


def judge(j, c, r):
    try:
        return j.invoke(f"{RUBRIC}\n\nQUESTION: {c['q']}\nTOOLS CALLED: {r['calls']}\nFINAL ANSWER:\n{r['final']}")
    except Exception as e:
        return Judgement(faithful=False, currency_ok=False, clear_verdict=False, reason=f"judge error: {e}")


def eval_one(c, i, verdict_agent, text_agent) -> dict:
    t0 = time.time()
    r = run_case(c, verdict_agent, text_agent)
    code = grade_code(c, r)
    if r["error"]:  # agent crashed: nothing to judge, don't spend two judge calls on an error string
        cheap = strong = Judgement(faithful=False, currency_ok=False, clear_verdict=False, reason="agent error")
        judged_strong = False
    else:
        cheap = judge(cheap_judge, c, r)
        flagged = not all([cheap.faithful, cheap.currency_ok, cheap.clear_verdict]) or not all(code.values())
        judged_strong = flagged or random.random() < 0.3
        strong = judge(strong_judge, c, r) if judged_strong else None
    line = (f"{c['id']:18} run{i} outcome={code.get('outcome')} "
            f"traj={code['traj_required'] and code['traj_forbidden']} calls={r['calls']} "
            f"[agent {r['agent_s']}s, total {time.time() - t0:.1f}s]")
    if r["error"]:
        line += f"\n    {r['final'][:400]}"
    print(line, flush=True)
    return {"id": c["id"], "run": i, **code, "calls": r["calls"], "verdict": r["verdict"],
            "final": r["final"][:2000], "error": r["error"], "cheap": cheap.model_dump(),
            "strong": strong.model_dump() if (judged_strong and strong) else None,
            "tokens": r["tokens"], "seconds": round(time.time() - t0, 1)}


def main() -> None:
    with_policies = "--with-policies" in sys.argv
    repeat = int(sys.argv[sys.argv.index("--repeat") + 1]) if "--repeat" in sys.argv else 1
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    verdict_agent, text_agent = agents(with_policies)
    cases = [c for c in CASES if with_policies or c["kind"] != "policy"]
    jobs = [(c, i) for c in cases for i in range(repeat)]
    print(f"{len(jobs)} runs, {workers} in parallel | agent={MODEL}\n", flush=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda ci: eval_one(*ci, verdict_agent, text_agent), jobs))

    n = len(results)
    errors = sum(x["error"] for x in results)
    print(f"\nfinished in {time.time() - t0:.0f}s")
    if errors:
        print(f"AGENT ERRORS: {errors}/{n} runs crashed -> fix these first (see messages above)")
    print("outcome pass rate:   ", round(sum(bool(x.get("outcome")) for x in results) / n, 3))
    print("trajectory pass rate:", round(sum(x["traj_required"] and x["traj_forbidden"] for x in results) / n, 3))
    checked = [x for x in results if x["strong"]]
    if checked:
        agree = sum(x["cheap"]["faithful"] == x["strong"]["faithful"] for x in checked) / len(checked)
        print(f"fast/strong judge agreement on 'faithful': {agree:.0%} over {len(checked)} spot-checks")
    with open("eval_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("details -> eval_results.json")


if __name__ == "__main__":
    main()