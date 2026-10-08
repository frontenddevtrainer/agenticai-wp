# hitl_graph.py — Meridian with an approval gate. The model can PROPOSE a limit increase; a person decides.
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage
from langchain_openrouter import ChatOpenRouter
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt
from tools_lc import TOOLS                          # Day 3: calculator, lookup_merchant, get_fx_rate

from tools_sensitive import SENSITIVE, increase_processing_limit

load_dotenv()

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

ALL_TOOLS = TOOLS + [increase_processing_limit]

llm = ChatOpenRouter(model="anthropic/claude-haiku-4.5", max_tokens=8000).bind_tools(ALL_TOOLS)

SYSTEM = SystemMessage(
    "You are Meridian, a merchant-risk analyst at Northstar Pay. Use tools for every fact and number. "
    "You may PROPOSE a temporary limit increase with increase_processing_limit; a merchant risk officer decides."
)

def call_model(state: State):
    return {"messages": [llm.invoke([SYSTEM, *state["messages"]])]}

def route_after_model(state: State):
    """Business rule in CODE, not in the prompt: sensitive tools always go to a person first."""
    last = state["messages"][-1]
    if not last.tool_calls:
        return END
    return "approval" if any(c["name"] in SENSITIVE for c in last.tool_calls) else "tools"

def approval(state: State) -> Command:
    last = state["messages"][-1]
    call = next(c for c in last.tool_calls if c["name"] in SENSITIVE)
    # ⏸ interrupt() saves the state and stops the run. The value we pass is what the approver sees.
    # When the run is resumed with Command(resume=...), interrupt() RETURNS that value and the node re-runs from the top.
    decision = interrupt({
        "action": call["name"],
        "args": call["args"],
        "policy": "Increases need a merchant risk officer. Max 30 days.",
    })
    if decision["type"] == "approve":
        return Command(goto="tools")
    if decision["type"] == "edit":                  # the approver changes the arguments, e.g. a smaller increase
        edited = {**call, "args": {**call["args"], **decision["args"]}}
        return Command(goto="tools", update={"messages": [last.model_copy(update={"tool_calls": [edited]})]})
    # reject: answer the tool call with an error, so the model knows and explains instead of retrying
    return Command(goto="call_model", update={"messages": [ToolMessage(
        f"REJECTED by merchant risk officer: {decision.get('note', 'no reason given')}", tool_call_id=call["id"], status="error")]})

builder = StateGraph(State)
builder.add_node("call_model", call_model)
builder.add_node("approval", approval, destinations=("tools", "call_model"))   # where Command may go (for the diagram)
builder.add_node("tools", ToolNode(ALL_TOOLS))


builder.add_edge(START, "call_model")
builder.add_conditional_edges("call_model", route_after_model, ["approval", "tools", END])
builder.add_edge("tools", "call_model")