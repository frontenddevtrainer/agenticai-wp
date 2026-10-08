# persist.py
from langgraph.checkpoint.sqlite import SqliteSaver
from graph import builder                      # Lab 1 builder (uncompiled)

with SqliteSaver.from_conn_string("meridian.db") as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
    cfg = {"configurable": {"thread_id": "analyst-42-session-1"}, "recursion_limit": 20}

    graph.invoke({"messages": [("user", "What is ACME's MTD volume vs limit?")]}, cfg)
    out = graph.invoke({"messages": [("user", "And how much headroom would a 1M USD transaction leave?")]}, cfg)
    print(out["messages"][-1].text)


state = graph.get_state(cfg)
print(state.next, len(state.values["messages"]))

for snap in graph.get_state_history(cfg):           # newest first, one per super-step
    print(snap.config["configurable"]["checkpoint_id"], snap.next, len(snap.values["messages"]))

# Fork from an earlier checkpoint (e.g. replay with a corrected input)
old = list(graph.get_state_history(cfg))[3]
graph.invoke(None, old.config)                       # resumes from that point