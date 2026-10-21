"""Day 7 Lab 3: publish the critic's Agent Card and serve it over A2A (JSON-RPC).

Run (from meridian/):  python -m critic_a2a      -> card at http://127.0.0.1:9999/.well-known/agent-card.json
"""
import os

import uvicorn
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from starlette.applications import Starlette

from critic_a2a.agent_executor import CriticExecutor

HOST, PORT = os.getenv("A2A_HOST", "127.0.0.1"), int(os.getenv("A2A_PORT", "8888"))
PUBLIC_URL = os.getenv("A2A_PUBLIC_URL", f"http://{HOST}:{PORT}")

skill = AgentSkill(
    id="review_merchant_risk_report",
    name="Review merchant risk report",
    description="Independently reviews a merchant risk report for figure, currency, eligibility and approver errors. "
                "Returns JSON {approved: bool, issues: [str]}.",
    input_modes=["text/plain"], output_modes=["application/json", "text/plain"],
    tags=["payments", "merchant-risk", "review"],
    examples=["Review this committee report: ..."],
)

card = AgentCard(
    name="Northstar Risk Report Critic",
    description="Second-line-of-defence reviewer for Northstar Pay merchant risk reports (fictional payment processor).",
    version="1.0.0",
    default_input_modes=["text/plain"], default_output_modes=["application/json"],
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[AgentInterface(protocol_binding="JSONRPC", url=PUBLIC_URL, protocol_version="1.0")],
    skills=[skill],
)

handler = DefaultRequestHandler(agent_executor=CriticExecutor(), task_store=InMemoryTaskStore(), agent_card=card)
app = Starlette(routes=[*create_agent_card_routes(card), *create_jsonrpc_routes(handler, "/")])

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)