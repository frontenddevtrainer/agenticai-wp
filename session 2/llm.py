"""llm.py: connects to Claude through OpenRouter. Every lab imports `client` and `MODEL` from here."""
import os

import anthropic
from dotenv import load_dotenv

load_dotenv() # reads OPENROUTER_API_KEY (and optional MODEL) from .env

# The official Anthropic SDK, pointed at OpenRouter's Anthropic-compatible endpoint
client = anthropic.Anthropic(
    auth_token=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://api.openrouter.ai/v1",
)

MODEL = os.getenv("MODEL", "anthropic/claude-haiku-4.5")