"""Day 7 Lab 3: discover the critic via its Agent Card and send a task from a second, independent process.

Prereq: python -m critic_a2a      Run: python a2a_client_call.py
"""
import asyncio
import os

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_message_text, get_stream_response_text, new_text_message
from a2a.types import TaskState
from a2a.types import Role, SendMessageRequest

CRITIC_URL = os.getenv("A2A_CRITIC_URL", "http://127.0.0.1:9999")

DRAFT = """ACME MTD volume 9.3M vs limit 9.5M USD (98%) - NEAR_LIMIT.
CRUX MTD volume 820M INR vs limit 800M INR - OVER_LIMIT, increase requested. Approver: Risk Ops lead."""  # 2 planted errors


async def review(draft: str) -> str:
    async with httpx.AsyncClient() as http:
        card = await A2ACardResolver(httpx_client=http, base_url=CRITIC_URL).get_agent_card()
    print("Discovered:", card.name, [s.id for s in card.skills])
    # LLM-backed agents take longer than httpx's 5 s default: give the client a generous timeout.
    client = await create_client(agent=card, client_config=ClientConfig(
        streaming=False, httpx_client=httpx.AsyncClient(timeout=httpx.Timeout(180.0))))
    req = SendMessageRequest(message=new_text_message(f"Review this committee report:\n{draft}", role=Role.ROLE_USER))
    texts = []
    async for chunk in client.send_message(req):
        if chunk.HasField("task"):   # non-streaming: the final Task; our verdict is in its status message
            print("task state:", TaskState.Name(chunk.task.status.state))
            texts.append(get_message_text(chunk.task.status.message))
        else:                        # streaming: message / status / artifact updates
            texts.append(get_stream_response_text(chunk))
    return "\n".join(t for t in texts if t)


if __name__ == "__main__":
    print(asyncio.run(review(DRAFT)))