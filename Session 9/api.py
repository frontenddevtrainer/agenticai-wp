"""Day 9 Lab 2: thin FastAPI wrapper around Meridian (local tools + MCP tools). Runs in the `agent` container.

Run locally:  uvicorn api:api --port 8080     (MCP server must be up)
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

for name, var in [("openrouter_api_key", "OPENROUTER_API_KEY"), ("meridian_mcp_key", "MERIDIAN_KEY")]:
    secret = Path(f"/run/secrets/{name}")           # Docker secrets, mounted at runtime (never baked into images)
    if secret.exists():
        os.environ.setdefault(var, secret.read_text().strip())

from fastapi import FastAPI            # noqa: E402
from pydantic import BaseModel         # noqa: E402

from meridian_graph import abuild_graph  # noqa: E402

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    state["graph"] = await abuild_graph()  # discover MCP tools at start-up (inside the running loop)
    yield


api = FastAPI(title="Meridian - Northstar Pay merchant-risk agent", lifespan=lifespan)


class Ask(BaseModel):
    question: str
    thread_id: str


@api.post("/ask")
async def ask(req: Ask):
    out = await state["graph"].ainvoke({"messages": [("user", req.question)]},
                                       {"configurable": {"thread_id": req.thread_id}, "recursion_limit": 25})
    return {"answer": out["messages"][-1].text}


@api.get("/healthz")
def health():
    return {"ok": True}