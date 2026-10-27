"""Shared (Day 6+): Meridian with local tools + tools discovered from the MCP server. Used by the Day 9 API.

Run (server must be up):  python meridian_graph.py "Can CRUX get a processing limit increase?"
"""
import asyncio
import sys

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from llm import chat_model
from mcp_tools import load_mcp_tools
from meridian import SYSTEM_PROMPT
from tools_lc import calculator, get_fx_rate, lookup_merchant


async def abuild_graph(checkpointer=None):
    mcp_tools = await load_mcp_tools()       # search_policies, get_merchant_risk_profile
    return create_agent(chat_model(), tools=[calculator, lookup_merchant, get_fx_rate, *mcp_tools],
                        system_prompt=SYSTEM_PROMPT, checkpointer=checkpointer or InMemorySaver())


def build_graph(checkpointer=None):
    """Sync helper (don't call inside a running event loop; use abuild_graph there)."""
    return asyncio.run(abuild_graph(checkpointer))


async def main(q: str) -> None:
    g = await abuild_graph()
    out = await g.ainvoke({"messages": [("user", q)]}, {"configurable": {"thread_id": "demo"}, "recursion_limit": 25})
    print(out["messages"][-1].text)


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "Is CRUX on the chargeback watchlist, and is it over its processing limit?"))