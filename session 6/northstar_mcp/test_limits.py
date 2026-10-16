# test_limits.py — test an MCP server IN-PROCESS: no network, no LLM, runs in a second. Run:  python test_limits.py
import asyncio
from mcp import Client
from mcp.types import ElicitResult
import limits_server
from limits_server import mcp

def person(action: str, **data):
    """A fake human for tests: answers every elicitation the same way."""
    async def respond(context, params):
        print(f"    asked: {params.message}")
        return ElicitResult(action=action, content=data or None)
    return respond

async def main():
    async with Client(mcp) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
        assert tools["get_risk_profile"].annotations.read_only_hint is True
        assert tools["get_risk_profile"].output_schema["properties"]["risk_tier"]          # typed result
        print("✓ tools listed with annotations and an output schema")

        r = await client.call_tool("get_risk_profile", {"merchant_id": "acme"})
        assert r.structured_content["monthly_limit"] == 9_500_000
        print("✓ structured result:", r.structured_content)

        r = await client.call_tool("get_risk_profile", {"merchant_id": "DUNE"})
        assert r.is_error and "unknown merchant" in r.content[0].text
        print("✓ unknown merchant is a tool error (the model can read it and recover), not a crash")

    async with Client(mcp, elicitation_callback=person("accept", approve=True, new_limit=10_000_000, days=3)) as client:
        r = await client.call_tool("request_limit_increase", {"merchant_id": "ACME", "new_limit": 10_500_000, "days": 5, "justification": "Black Friday"})
        assert r.structured_content["status"] == "applied" and r.structured_content["limit"] == 10_000_000
        print("✓ person lowered it to 10M for 3 days:", r.structured_content)

    async with Client(mcp, elicitation_callback=person("decline")) as client:
        r = await client.call_tool("request_limit_increase", {"merchant_id": "BOLT", "new_limit": 5_500_000, "days": 5, "justification": "sale"})
        assert r.structured_content["status"] == "declined"
        print("✓ person declined:", r.structured_content["reason"])

    asked = []
    async def must_not_ask(context, params):
        asked.append(params.message)
        return ElicitResult(action="accept", content={"approve": True, "new_limit": 900_000_000, "days": 5})
    async with Client(mcp, elicitation_callback=must_not_ask) as client:
        r = await client.call_tool("request_limit_increase", {"merchant_id": "CRUX", "new_limit": 900_000_000, "days": 5, "justification": "IPL"})
        assert r.is_error and "chargeback watchlist" in r.content[0].text
        print("✓ watchlist merchant refused BEFORE asking anyone:", r.content[0].text)

    assert not asked, "nobody should be asked about an ineligible merchant"
    assert limits_server.MERCHANTS["CRUX"]["limit"] == 800_000_000
    print("\nall checks passed")

asyncio.run(main())