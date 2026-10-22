# limits_server.py — typed results, tool annotations, and a person's confirmation inside a tool call (elicitation).
# Run as a server:  python limits_server.py   (http://127.0.0.1:8001/mcp)   — or test it in-process: python test_limits.py
from typing import Annotated
from pydantic import BaseModel, Field
from mcp.server.mcpserver import AcceptedElicitation, Context, Elicit, ElicitationResult, MCPServer, Resolve
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

MERCHANTS = {
    "ACME": {"tier": "Medium", "limit": 9_500_000, "currency": "USD", "chargeback_pct": 0.6, "watchlist": False},
    "BOLT": {"tier": "Low", "limit": 5_000_000, "currency": "GBP", "chargeback_pct": 0.3, "watchlist": False},
    "CRUX": {"tier": "High", "limit": 800_000_000, "currency": "INR", "chargeback_pct": 1.2, "watchlist": True},
}

mcp = MCPServer("northstar-limits", title="Northstar Pay processing limits", version="1.1.0")

class RiskProfile(BaseModel):
    """Returning a Pydantic model gives the tool an outputSchema, and clients get structuredContent they can parse."""
    merchant_id: str
    risk_tier: str
    monthly_limit: float
    currency: str
    chargeback_ratio_pct: float
    on_watchlist: bool

class Confirmation(BaseModel):
    """What the person is asked to fill in. Elicitation schemas may only use flat, primitive fields."""
    approve: bool = Field(description="Approve this increase?")
    new_limit: float = Field(description="Limit to apply (you may lower it)")
    days: int = Field(description="Number of days (max 30)")

class IncreaseResult(BaseModel):
    merchant_id: str
    status: str                       # applied | declined | refused
    limit: float
    days: int = 0
    reason: str = ""

def profile(merchant_id: str) -> dict:
    m = MERCHANTS.get(merchant_id.strip().upper())
    if m is None:
        # ToolError = an error you EXPECTED: the model sees this message and can recover (fix the ID, ask the user).
        # Any other exception is treated as a crash: the model sees only "Error executing tool ...", no internals.
        raise ToolError(f"unknown merchant '{merchant_id}'; valid: {sorted(MERCHANTS)}")
    return m

@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
def get_risk_profile(merchant_id: str) -> RiskProfile:
    """A merchant's risk tier, monthly processing limit, chargeback ratio and watchlist status."""
    m = profile(merchant_id)
    return RiskProfile(merchant_id=merchant_id.upper(), risk_tier=m["tier"], monthly_limit=m["limit"], currency=m["currency"],
                       chargeback_ratio_pct=m["chargeback_pct"], on_watchlist=m["watchlist"])

def confirm_increase(merchant_id: str, new_limit: float, days: int, justification: str) -> Elicit[Confirmation]:
    """A RESOLVER: runs before the tool body. Policy checks no person may override come first, in code;
    then it asks a person. The SDK delivers the question to the client and resumes the call with the answer."""
    m = profile(merchant_id)
    if m["watchlist"]:
        raise ToolError(f"{merchant_id.upper()} is not eligible: it is on the chargeback watchlist")
    if days > 30:
        raise ToolError("increases last at most 30 days")
    pct = (new_limit / m["limit"] - 1) * 100
    return Elicit(f"Approve {merchant_id.upper()}: {m['limit']:,.0f} → {new_limit:,.0f} {m['currency']} "
                  f"(+{pct:.1f}%) for {days} days? Reason: {justification}", Confirmation)

@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False))
async def request_limit_increase(
    merchant_id: str, new_limit: float, days: int, justification: str, ctx: Context,
    answer: Annotated[ElicitationResult[Confirmation], Resolve(confirm_increase)],
) -> IncreaseResult:
    """Request a TEMPORARY processing limit increase. A person confirms it before anything changes.
    Merchants on the chargeback watchlist are never eligible."""
    m = profile(merchant_id)
    mid = merchant_id.upper()
    if not isinstance(answer, AcceptedElicitation) or not answer.data.approve:
        return IncreaseResult(merchant_id=mid, status="declined", limit=m["limit"], reason=f"person chose: {answer.action}")
    if answer.data.days > 30:                                   # the person's edit is checked too
        raise ToolError("increases last at most 30 days")
    m["limit"] = answer.data.new_limit                          # mock side effect
    await ctx.info(f"limit for {mid} set to {answer.data.new_limit:,.0f} for {answer.data.days} days")
    return IncreaseResult(merchant_id=mid, status="applied", limit=answer.data.new_limit, days=answer.data.days)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8001)