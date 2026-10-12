# memory_run.py — two conversations (threads), one analyst (user_id). Run:  python memory_run.py
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore
from memory_graph import builder

with SqliteStore.from_conn_string("meridian_store.db") as store, SqliteSaver.from_conn_string("meridian.db") as checkpointer:
    store.setup()                                   # creates the store's tables the first time
    graph = builder.compile(checkpointer=checkpointer, store=store)

    monday = {"configurable": {"thread_id": "mon-session", "user_id": "analyst-42"}, "recursion_limit": 25}
    out = graph.invoke({"messages": [("user", "Remember: always show MTD volumes in GBP as well as the limit currency.")]}, monday)
    print("Monday:", out["messages"][-1].text[:200])

    # A new thread = a new conversation with no chat history. Only the store connects the two.
    tuesday = {"configurable": {"thread_id": "tue-session", "user_id": "analyst-42"}, "recursion_limit": 25}
    out = graph.invoke({"messages": [("user", "What's ACME's month-to-date volume?")]}, tuesday)
    print("Tuesday:", out["messages"][-1].text[:400])

    # What's stored, and for whom
    for item in store.search(("memories", "analyst-42")):
        print("stored:", item.value)