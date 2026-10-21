# critic_v2.py — the A2A critic, upgraded: streams progress, asks for input when it needs it,
# and returns its review as a structured ARTIFACT. Run:  python critic_v2.py   (http://127.0.0.1:9998)
import re
import uvicorn
from a2a.helpers import get_message_text, new_data_part, new_task_from_user_message, new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from pydantic import BaseModel
from starlette.applications import Starlette
from llm import chat_model

URL = "http://127.0.0.1:9998"

class Review(BaseModel):
    approved: bool
    issues: list[str]

RUBRIC = ("You are Northstar Pay's independent merchant risk report reviewer. Facts: ACME limit 9.5M USD, MTD 9.92M USD "
          "after converting 6.2M EUR at 1.10 (OVER_LIMIT, 104.4%); CRUX is High tier and on the chargeback watchlist, so it "
          "is NOT eligible for a limit increase; 5–15% increases for High tier need the Head of Merchant Risk. "
          "Check figures, currencies, eligibility and approvers. Approve only if everything is right.")

class CriticExecutor(AgentExecutor):
    def __init__(self):
        self.llm = chat_model(max_tokens=4000).with_structured_output(Review)

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task or new_task_from_user_message(context.message)
        if not context.current_task:
            await event_queue.enqueue_event(task)                      # a NEW task (first message)
        updater = TaskUpdater(event_queue=event_queue, task_id=task.id, context_id=task.context_id)
        text = get_message_text(context.message) or ""

        # 1. Multi-turn: if there's nothing to review, pause the SAME task and ask for what's missing.
        if not re.search(r"\d", text):
            await updater.requires_input(new_text_message(
                "Send me the report to review: the figures, currencies and any limit-increase requests.",
                task_id=task.id, context_id=task.context_id))
            return

        # 2. Streaming progress: the caller sees each status as it happens (if it streams).
        await updater.start_work(new_text_message("Checking figures and currencies…", task_id=task.id, context_id=task.context_id))
        try:
            review = await self.llm.ainvoke(f"{RUBRIC}\n\nREPORT:\n{text}")
        except Exception as e:                                       # a failed TASK, not a crashed server
            await updater.failed(new_text_message(f"review failed: {e}", task_id=task.id, context_id=task.context_id))
            return

        # 3. The result is an ARTIFACT with typed data, not text the caller has to parse.
        await updater.add_artifact([new_data_part(review.model_dump())], name="review")
        verdict = "approved" if review.approved else f"{len(review.issues)} issue(s)"
        await updater.complete(new_text_message(f"Review done: {verdict}", task_id=task.id, context_id=task.context_id))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancel not supported")

card = AgentCard(
    name="Northstar Risk Report Critic v2",
    description="Reviews merchant risk reports (fictional payment processor). Streams progress; returns a 'review' artifact "
                "{approved, issues}; asks for the report if you send none.",
    version="2.0.0",
    default_input_modes=["text/plain"], default_output_modes=["application/json"],
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[AgentInterface(protocol_binding="JSONRPC", url=URL, protocol_version="1.0")],
    skills=[AgentSkill(id="review_merchant_risk_report", name="Review merchant risk report",
                       description="Checks figures, currencies, eligibility and approvers.", tags=["payments", "risk"],
                       input_modes=["text/plain"], output_modes=["application/json"])],
)

handler = DefaultRequestHandler(agent_executor=CriticExecutor(), task_store=InMemoryTaskStore(), agent_card=card)
app = Starlette(routes=[*create_agent_card_routes(card), *create_jsonrpc_routes(handler, "/")])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9998)