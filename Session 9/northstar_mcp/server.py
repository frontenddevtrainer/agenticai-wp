"""Day 6 Lab 1: Northstar knowledge base as an MCP server (SDK v2, Streamable HTTP).

Run (from the meridian/ root):  python -m northstar_mcp.server        -> http://127.0.0.1:8000/mcp
Inspect:                         npx @modelcontextprotocol/inspector   (Streamable HTTP, that URL)
"""
import os
import pathlib

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError

from data import MERCHANTS

DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"

mcp = MCPServer(
    "northstar-kb",
    title="Northstar Pay Knowledge Base",
    description="Merchant risk policies, SOPs, chargeback/reserve rules, API limits and pricing for Northstar Pay (fictional).",
    version="1.0.0",
)


# ---------- resources (application-controlled context) ----------
@mcp.resource("northstar://docs")
def list_docs() -> list[str]:
    """List available Northstar documents."""
    return sorted(p.stem for p in DOCS.glob("*.md"))


@mcp.resource("northstar://docs/{name}")
def read_doc(name: str) -> str:
    """Read a Northstar policy / SOP / pricing document by name (e.g. merchant-risk-policy-2026)."""
    path = DOCS / f"{name}.md"
    if not path.exists():
        raise ResourceError(f"unknown document '{name}'. Available: {list_docs()}")
    return path.read_text()


# ---------- tools (model-controlled actions) ----------
@mcp.tool()
async def search_policies(question: str, ctx: Context) -> str:
    """Search Northstar Pay's internal merchant risk policies, SOPs, chargeback/reserve rules, API limits and pricing.
    Returns a cited answer, or an explicit 'not found'. Superseded policies are excluded."""
    from agentic_rag import rag_graph  # Day 5 Lab 3 (imported lazily: needs the Chroma index + embeddings)

    await ctx.report_progress(0.1, 1.0, "retrieving")
    out = await rag_graph.ainvoke({"question": question, "query": question, "docs": [], "retries": 0,
                                   "grade": None, "answer": ""})
    await ctx.report_progress(1.0, 1.0, f"done after {out['retries']} retries")
    return out["answer"]


@mcp.tool()
def get_merchant_risk_profile(merchant_id: str) -> dict:
    """Get a merchant's risk tier, MCC, chargeback ratio, rolling reserve % and watchlist/KYB status."""
    m = MERCHANTS.get(merchant_id.strip().upper())
    if m is None:
        raise ToolError(f"unknown merchant; valid: {sorted(MERCHANTS)}")   # ToolError: the model sees this message
    return {"merchant_id": merchant_id.upper(), "risk_tier": m["risk_tier"], "mcc": m["mcc"],
            "chargeback_ratio_pct": m["chargeback_ratio_pct"], "rolling_reserve_pct": m["rolling_reserve_pct"],
            "kyb_notes": m["kyb_notes"]}


# ---------- prompts (user-controlled templates) ----------
@mcp.prompt()
def limit_report(merchant_id: str) -> str:
    """Draft a processing-limit notification for the risk committee."""
    return (f"Prepare a processing-limit notification for {merchant_id}: MTD volume vs limit (in limit currency), "
            "utilisation %, required approver for any increase per Merchant Risk Policy §3, and next steps. Cite policy sections.")


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host=os.getenv("MCP_HOST", "127.0.0.1"), port=int(os.getenv("MCP_PORT", "8000")))