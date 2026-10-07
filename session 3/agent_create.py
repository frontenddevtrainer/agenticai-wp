# agent_create.py
from dotenv import load_dotenv
load_dotenv()  # reads OPENROUTER_API_KEY from .env

from langchain.agents import create_agent
from tools_lc import TOOLS

meridian = create_agent(
    model="openrouter:anthropic/claude-haiku-4.5",      # or pass a ChatOpenRouter instance
    tools=TOOLS,
    system_prompt=("You are Meridian, a merchant-risk & payments ops analyst at Northstar Pay. Use only tools. "
                   "Convert every amount into the limit's currency. Finish with OVER_LIMIT / NEAR_LIMIT / OK + utilisation %."),
)

result = meridian.invoke(
    {"messages": [{"role": "user", "content": "Is ACME over its processing limit?"}]},
    config={"recursion_limit": 20},          # ← was MAX_TURNS
)
for m in result["messages"]:
    m.pretty_print()