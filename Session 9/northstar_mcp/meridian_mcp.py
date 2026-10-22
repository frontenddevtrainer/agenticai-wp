from dotenv import load_dotenv
load_dotenv()  # reads OPENROUTER_API_KEY from .env

import asyncio
from langchain.agents import create_agent
from tools_lc import calculator, lookup_merchant, get_fx_rate     # still local (Day 3)
from mcp_tools import load_mcp_tools

async def main():
    mcp_tools = await load_mcp_tools()                 # search_policies, get_merchant_risk_profile from the server
    meridian = create_agent("openrouter:anthropic/claude-haiku-5.5",
                            tools=[calculator, lookup_merchant, get_fx_rate, *mcp_tools],
                            system_prompt="You are Meridian, a merchant-risk & payments ops analyst at Northstar Pay.")
    out = await meridian.ainvoke({"messages": [("user", "CRUX needs a 12% limit increase. Who must approve it, and is CRUX currently in breach?")]})
    print(out["messages"][-1].text)

asyncio.run(main())