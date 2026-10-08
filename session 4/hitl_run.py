# hitl_run.py — run until the graph pauses, show the request, decide, resume.
#   python hitl_run.py              # asks you: approve / edit / reject
# Resuming can happen hours later, in another process: the SQLite checkpoint holds everything.
import json
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from hitl_graph import builder

REQUEST = "ACME is in breach. Raise their limit to 10.5M USD for 5 days; the Black Friday sale starts tomorrow."

with SqliteSaver.from_conn_string("meridian.db") as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "increase-acme-1"}, "recursion_limit": 25}

    out = graph.invoke({"messages": [("user", REQUEST)]}, config)
    if "__interrupt__" not in out:
        print("No approval needed:", out["messages"][-1].text)
        raise SystemExit

    request = out["__interrupt__"][0].value
    print("⏸ APPROVAL NEEDED\n" + json.dumps(request, indent=2))
    print("paused before:", graph.get_state(config).next)       # ('approval',)

    choice = input("approve / edit / reject? ").strip().lower()
    if choice == "edit":
        decision = {"type": "edit", "args": {"new_limit": 10_000_000, "days": 3}}
    elif choice == "reject":
        decision = {"type": "reject", "note": input("reason: ")}
    else:
        decision = {"type": "approve"}

    out = graph.invoke(Command(resume=decision), config)
    print("\nMeridian:", out["messages"][-1].text)