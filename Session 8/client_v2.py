# client_v2.py — a streaming A2A client that handles input-required and reads the artifact.
# Start critic_v2.py first.   Run:  python client_v2.py
import asyncio
import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_data_parts, get_message_text, new_text_message
from a2a.types import Role, SendMessageRequest, TaskState

URL = "http://127.0.0.1:9998"
REPORT = """ACME MTD 9.3M vs limit 9.5M USD (98%) - NEAR_LIMIT.
CRUX MTD 820M INR vs 800M INR - OVER_LIMIT; +12% increase recommended, approver Risk Ops lead."""   # 3 planted errors

async def send(client, text, task_id=None, context_id=None):
    """Send one message and print every streamed event. Returns (task_id, context_id, final state)."""
    msg = new_text_message(text, role=Role.ROLE_USER, task_id=task_id, context_id=context_id)
    state = None
    async for event in client.send_message(SendMessageRequest(message=msg)):
        if event.HasField("task"):
            task_id, context_id, state = event.task.id, event.task.context_id, event.task.status.state
            print(f"  task {task_id[:8]}… {TaskState.Name(state)}")
        elif event.HasField("status_update"):
            u = event.status_update
            state = u.status.state
            print(f"  status: {TaskState.Name(state):<26} {get_message_text(u.status.message)}")
        elif event.HasField("artifact_update"):
            a = event.artifact_update.artifact
            print(f"  artifact '{a.name}':", get_data_parts(a.parts)[0])
    return task_id, context_id, state

async def main():
    async with httpx.AsyncClient() as http:
        card = await A2ACardResolver(httpx_client=http, base_url=URL).get_agent_card()
    print(f"Discovered: {card.name} (streaming={card.capabilities.streaming})")
    client = await create_client(agent=card, client_config=ClientConfig(
        streaming=True, httpx_client=httpx.AsyncClient(timeout=httpx.Timeout(300.0))))

    print("\n1) Ask without a report:")
    task_id, context_id, state = await send(client, "Can you review our committee report?")
    if state == TaskState.TASK_STATE_INPUT_REQUIRED:
        print("\n2) Answer on the SAME task:")
        await send(client, f"Here it is:\n{REPORT}", task_id=task_id, context_id=context_id)

asyncio.run(main())