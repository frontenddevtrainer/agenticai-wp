"""llm.py: connects to Claude through OpenRouter. Every lab imports `client` and `MODEL` from here."""
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()  # reads OPENROUTER_API_KEY (and optional MODEL) from .env

# The official Anthropic SDK, pointed at OpenRouter's Anthropic-compatible endpoint
client = anthropic.Anthropic(
    base_url=os.getenv("BASE_URL", "https://openrouter.ai/api"),
    auth_token=os.environ["OPENROUTER_API_KEY"],
)
MODEL = os.getenv("MODEL", "anthropic/claude-haiku-4.5")