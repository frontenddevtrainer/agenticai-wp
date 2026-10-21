"""Day 7 Lab 1: supervisor-worker crew in LangGraph: research + writer + critic -> monthly Merchant Risk Report.

Run:  python crew_langgraph.py
"""
from typing import Literal

from langchain.agents import create_agent
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from pydantic import BaseModel
from typing_extensions import TypedDict

from llm import chat_model
from tools_lc import calculator, get_fx_rate, lookup_merchant

research = create_agent(chat_model(), tools=[calculator, lookup_merchant, get_fx_rate],
                        system_prompt="You are the RESEARCH analyst at Northstar Pay. For each merchant compute MTD "
                                      "volume in the limit currency (use get_fx_rate and the calculator), utilisation %, "
                                      "and verdict (OVER_LIMIT >100%, NEAR_LIMIT >90%, else OK). Output a factual table only.")
writer = create_agent(chat_model(), tools=[],                       # no data access: segregation of duties
                      system_prompt="You are the REPORT WRITER for Northstar's risk committee. Turn research findings "
                                    "into a concise report: executive summary, table, limit breaches & recommended "
                                    "actions. Never invent numbers.")


class Review(BaseModel):
    approved: bool
    issues: list[str]


critic_llm = chat_model(max_tokens=4000).with_structured_output(Review)
CRITIC_RUBRIC = ("Check: (1) every figure matches the research table, (2) currencies are stated and consistent with "
                 "each limit, (3) every OVER_LIMIT merchant has a recommended action, (4) no invented data. "
                 "Approve only if all pass.")


class CrewState(TypedDict):
    task: str
    research: str
    draft: str
    review: Review | None
    revisions: int


class Next(BaseModel):
    next: Literal["research", "writer", "critic", "FINISH"]
    reason: str


supervisor_llm = chat_model(max_tokens=2000).with_structured_output(Next)


def supervisor(s: CrewState) -> Command[Literal["research", "writer", "critic", "__end__"]]:
    # Deterministic guards first (business rules in code), then let the LLM decide.
    if s.get("review") and s["review"].approved:
        return Command(goto=END)
    if s.get("revisions", 0) >= 2:
        return Command(goto=END)
    
    if not s.get("research"):
        return Command(goto="research")
    if not s.get("draft"):
        return Command(goto="writer")
    
    status = f"research done: True; draft exists: True; last review: {s.get('review')}"
    d = supervisor_llm.invoke(f"Task: {s['task']}\nStatus: {status}\nPick the next worker "
                              "(critic if the draft is unreviewed; writer if the critic found issues).")
    print(f"  supervisor -> {d.next} ({d.reason[:80]})")
    return Command(goto=END if d.next == "FINISH" else d.next)


def run_research(s: CrewState):
    out = research.invoke({"messages": [("user", s["task"])]}, {"recursion_limit": 40})
    print("  research done")
    return Command(goto="supervisor", update={"research": out["messages"][-1].text})


def run_writer(s: CrewState):
    feedback = f"\n\nCritic feedback to fix:\n{s['review'].issues}" if s.get("review") else ""
    out = writer.invoke({"messages": [("user", f"Research findings:\n{s['research']}{feedback}")]})
    print("  draft written")
    return Command(goto="supervisor", update={"draft": out["messages"][-1].text,
                                              "revisions": s.get("revisions", 0) + (1 if s.get("review") else 0)})


def run_critic(s: CrewState):
    r = critic_llm.invoke(f"{CRITIC_RUBRIC}\n\nRESEARCH:\n{s['research']}\n\nDRAFT:\n{s['draft']}")
    print(f"  critic: approved={r.approved} issues={r.issues}")
    return Command(goto="supervisor", update={"review": r})


g = StateGraph(CrewState)
g.add_node("supervisor", supervisor)
g.add_node("research", run_research)
g.add_node("writer", run_writer)
g.add_node("critic", run_critic)
g.add_edge(START, "supervisor")
crew = g.compile()

INITIAL = {"task": "Monthly merchant risk report for ACME, BOLT, CRUX (October 2026).",
           "research": "", "draft": "", "review": None, "revisions": 0}

if __name__ == "__main__":
    out = crew.invoke(INITIAL, {"recursion_limit": 30})
    print("\n" + out["draft"])
    print("\nREVIEW:", out["review"])