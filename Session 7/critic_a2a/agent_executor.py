"""Day 7 Lab 3: the critic wrapped as an A2A AgentExecutor (a2a-sdk 1.x)."""
from a2a.helpers import get_message_text, new_task_from_user_message, new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState
from pydantic import BaseModel

from llm import chat_model


class Review(BaseModel):
    approved: bool
    issues: list[str]


RUBRIC = ("You are Northstar Pay's independent merchant risk report reviewer. Facts: ACME limit 9.5M USD with batches "
          "4.2M EUR, 3.1M USD, 2.0M EUR (EUR/USD 1.10); CRUX is High risk tier and on the chargeback watchlist, so it "
          "is NOT eligible for a limit increase. Check: (1) figures internally consistent and FX-converted, "
          "(2) currencies stated and consistent with each limit, (3) any limit increase names the correct approver and "
          "respects eligibility, (4) no unsupported claims.")


class CriticExecutor(AgentExecutor):
    def __init__(self):
        self.llm = chat_model(max_tokens=4000).with_structured_output(Review)

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task or new_task_from_user_message(context.message)
        if not context.current_task:
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue=event_queue, task_id=task.id, context_id=task.context_id)
        await updater.update_status(state=TaskState.TASK_STATE_WORKING,
                                    message=new_text_message("Reviewing merchant risk report..."))
        report = get_message_text(context.message) or ""
        try:
            review = await self.llm.ainvoke(f"{RUBRIC}\n\nREPORT:\n{report}")
        except Exception as e:  # report failures as a failed task, not a crashed server
            await updater.update_status(state=TaskState.TASK_STATE_FAILED, message=new_text_message(f"error: {e}"))
            return
        await updater.update_status(state=TaskState.TASK_STATE_COMPLETED,
                                    message=new_text_message(review.model_dump_json()))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancel not supported")