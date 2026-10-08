# graph.py
from dotenv import load_dotenv
load_dotenv()  # reads OPENROUTER_API_KEY from .env

from typing import Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel
from langchain_openrouter import ChatOpenRouter      # Claude via OpenRouter
from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from tools_lc import TOOLS                     # Day 3 @tool functions



# Global State shared between agents. its custom state you can design this according to your requirements.
class MeridianState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    route: Literal["direct", "agent"] | None

llm = ChatOpenRouter(model="anthropic/claude-haiku-4.5", max_tokens=16000)
agent_llm = llm.bind_tools(TOOLS)

SYSTEM = SystemMessage("You are Meridian, a merchant-risk & payments ops analyst at Northstar Pay. "
                       "Convert all amounts into the limit currency. Use the calculator for arithmetic.")

# --- node 1: classify (structured output → deterministic routing) ---
class Route(BaseModel):
    route: Literal["direct", "agent"]
    reason: str

classifier = llm.with_structured_output(Route)

def classify(state: MeridianState):
    response = classifier.invoke([SystemMessage(
        "Route to 'direct' if the question is a definition/concept answerable without Northstar data. "
        "Route to 'agent' if it needs merchant data, FX rates, or calculations."), state["messages"][-1]])
    return {"route": response.route}

# --- node 2a: direct answer ---
def answer_direct(state: MeridianState):
    return {"messages": [llm.invoke([SYSTEM, *state["messages"]])]}

# --- node 2b: agent (ReAct) ---
def call_model(state: MeridianState):
    return {"messages": [agent_llm.invoke([SYSTEM, *state["messages"]])]}

builder = StateGraph(MeridianState)

builder.add_node("classify", classify)
builder.add_node("answer_direct", answer_direct)
builder.add_node("call_model", call_model)
builder.add_node("tools", ToolNode(TOOLS))     # executes tool calls, returns ToolMessages, handles errors

builder.add_edge(START, "classify")

builder.add_conditional_edges("classify", lambda state: state["route"],
                              {"direct": "answer_direct", "agent": "call_model"})

builder.add_edge("answer_direct", END)

builder.add_conditional_edges("call_model", tools_condition)   # → "tools" or END

builder.add_edge("tools", "call_model")                        # the cycle

graph = builder.compile()
# print(graph.get_graph().draw_mermaid())

for q in ["What is a rolling reserve?",                            # → direct
          "Is ACME over its processing limit?"]:                  # → agent + tools
    out = graph.invoke({"messages": [("user", q)]}, {"recursion_limit": 20})
    print(out["route"], "→", out["messages"][-1].text[:300])