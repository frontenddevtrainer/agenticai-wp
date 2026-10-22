"""A single LangChain agent served over HTTP (FastAPI).

POST /chat   {"message": "...", "thread_id": "optional"}  ->  {"answer": "...", "thread_id": "..."}
GET  /health                                                ->  {"status": "ok"}

Run locally:  uvicorn app:app --port 8080
"""
import os
import uuid

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel

load_dotenv()

# --- Tools (fictional data, same merchants as the course) -------------------
LIMITS_USD = {"ACME": 9_500_000, "BOLT": 4_000_000, "CRUX": 2_500_000}
FX_TO_USD = {"USD": 1.0, "EUR": 1.10, "GBP": 1.27}


@tool
def get_merchant_limit(merchant: str) -> str:
    """Return a merchant's monthly processing limit in USD. Known merchants: ACME, BOLT, CRUX."""
    limit = LIMITS_USD.get(merchant.upper())
    return f"{merchant.upper()} limit: {limit:,} USD" if limit else f"Unknown merchant: {merchant}"


@tool
def convert_to_usd(amount: float, currency: str) -> str:
    """Convert an amount in USD, EUR or GBP to USD."""
    rate = FX_TO_USD.get(currency.upper())
    if rate is None:
        return f"Unsupported currency: {currency}"
    return f"{amount:,.2f} {currency.upper()} = {amount * rate:,.2f} USD (rate {rate})"


SYSTEM_PROMPT = ("You are Northstar Pay's merchant risk assistant. Use the tools for every figure; "
                 "always state currencies; never invent numbers.")


# --- Model ------------------------------------------------------------------
def build_model():
    if os.getenv("MERIDIAN_BACKEND", "openrouter").lower() == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
                          base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    from langchain_openrouter import ChatOpenRouter
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SystemExit("OPENROUTER_API_KEY is not set (put it in .env).")
    return ChatOpenRouter(model=os.getenv("MERIDIAN_MODEL", "anthropic/claude-sonnet-5.5"), max_tokens=2000)


agent = create_agent(build_model(), tools=[get_merchant_limit, convert_to_usd],
                     system_prompt=SYSTEM_PROMPT, checkpointer=InMemorySaver())


# --- HTTP API ---------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None  # reuse to continue a conversation


class ChatResponse(BaseModel):
    answer: str
    thread_id: str


def check_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("AGENT_API_KEY")  # unset = no auth (local dev only)
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")


app = FastAPI(title="Merchant Risk Agent")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(check_api_key)])
async def chat(req: ChatRequest) -> ChatResponse:
    thread_id = req.thread_id or str(uuid.uuid4())
    try:
        result = await agent.ainvoke({"messages": [("user", req.message)]},
                                     {"configurable": {"thread_id": thread_id}, "recursion_limit": 20})
    except Exception as e:  # LLM/provider errors -> 502, not a stack trace
        raise HTTPException(status_code=502, detail=f"agent error: {type(e).__name__}: {e}") from e
    return ChatResponse(answer=result["messages"][-1].text, thread_id=thread_id)