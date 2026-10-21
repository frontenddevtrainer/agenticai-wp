"""llm.py (Day 3+): Claude via OpenRouter, for raw-SDK code AND for LangChain."""
import os

import anthropic
from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter

load_dotenv()  # reads OPENROUTER_API_KEY from .env

MODEL = os.getenv("MODEL", "anthropic/claude-opus-5.5")
MODEL_FAST = os.getenv("MODEL_FAST", "anthropic/claude-haiku-4.5")

# Raw Anthropic SDK (as on Day 2)
client = anthropic.Anthropic(base_url="https://openrouter.ai/api", auth_token=os.environ["OPENROUTER_API_KEY"])


def chat_model(model: str = MODEL, **kwargs) -> ChatOpenRouter:
    """A LangChain chat model for Claude via OpenRouter (reads OPENROUTER_API_KEY)."""
    kwargs.setdefault("max_tokens", 8000)
    return ChatOpenRouter(model=model, **kwargs)