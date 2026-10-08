# tools_sensitive.py
from langchain_core.tools import tool
from data import MERCHANTS

@tool
def increase_processing_limit(merchant_id: str, new_limit: float, currency: str, days: int, justification: str) -> str:
    """Request a TEMPORARY processing limit increase. Requires merchant-risk-officer approval. Max 30 days."""
    cp = MERCHANTS[merchant_id.upper()]
    old = cp["processing_limit"]["amount"]
    cp["processing_limit"]["amount"] = new_limit          # mock side effect
    return f"Limit for {merchant_id} changed {old:,.0f} → {new_limit:,.0f} {currency} for {days} days."

SENSITIVE = {"increase_processing_limit"}