# memory_graph.py — memory that lasts across conversations: Monday's preference is used on Tuesday.
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openrouter import ChatOpenRouter
from langgraph.config import get_config, get_store
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from tools_lc import TOOLS                         # Day 3 tools

load_dotenv()

def namespace():
    """Each analyst gets their own memory: ("memories", <user_id from the run config>)."""
    return ("memories", get_config()["configurable"]["user_id"])

@tool
def remember(fact: str) -> str:
    """Save a lasting preference or working fact about this analyst (e.g. preferred currency).
    Never store cardholder data, passwords or other personal data."""
    key = str(abs(hash(fact)))
    get_store().put(namespace(), key, {"fact": fact})
    return "saved"

@tool
def recall() -> list[str]:
    """List everything remembered about this analyst. Call it at the start of a conversation."""
    return [item.value["fact"] for item in get_store().search(namespace())]

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

ALL_TOOLS = TOOLS + [remember, recall]
llm = ChatOpenRouter(model="anthropic/claude-haiku-4.5", max_tokens=8000).bind_tools(ALL_TOOLS)
SYSTEM = SystemMessage(
    "You are Meridian, a merchant-risk analyst at Northstar Pay. At the start of every conversation call recall() "
    "and follow the analyst's saved preferences. When they state a lasting preference, save it with remember()."
)

def call_model(state: State):
    return {"messages": [llm.invoke([SYSTEM, *state["messages"]])]}

builder = StateGraph(State)
builder.add_node("call_model", call_model)
builder.add_node("tools", ToolNode(ALL_TOOLS))
builder.add_edge(START, "call_model")
builder.add_conditional_edges("call_model", tools_condition)
builder.add_edge("tools", "call_model")