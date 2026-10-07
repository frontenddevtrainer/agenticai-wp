# agent_bind_tools.py
from dotenv import load_dotenv
load_dotenv()  # reads OPENROUTER_API_KEY from .env

from langchain_openrouter import ChatOpenRouter      # Claude via OpenRouter
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from tools_lc import TOOLS

model = ChatOpenRouter(model="anthropic/claude-haiku-4.5", max_tokens=16000).bind_tools(TOOLS)
by_name = {t.name: t for t in TOOLS}

SYSTEM = ("You are Meridian, a merchant-risk & payments ops analyst at Northstar Pay. Use only tools. "
          "Convert every amount into the limit's currency. Finish with OVER_LIMIT / NEAR_LIMIT / OK + utilisation %.")

def run(question: str, max_turns: int = 10) -> str:
    messages = [SystemMessage(SYSTEM), HumanMessage(question)]
    for _ in range(max_turns):
        ai = model.invoke(messages)                     # ← was client.messages.create
        messages.append(ai)
        if not ai.tool_calls:                           # ← was stop_reason == "end_turn"
            return ai.text                              # .text property on langchain-core 1.x messages
        for call in ai.tool_calls:                      # ← was iterating tool_use blocks
            try:
                print(call["args"])
                out = by_name[call["name"]].invoke(call["args"])
                messages.append(ToolMessage(str(out), tool_call_id=call["id"]))
            except Exception as e:
                messages.append(ToolMessage(f"error: {e}", tool_call_id=call["id"], status="error"))
    return "[stopped: max_turns]"


if __name__ == "__main__":
    question = "what is the capital of France"
    print("\nANSWER:", run(question))