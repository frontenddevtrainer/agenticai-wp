"""Day 6 Lab 3: MCP client -> LangChain tools (our own small adapter on the MCP SDK v2 `Client`).

Why not langchain-mcp-adapters? Its 0.3.x release does not import against MCP SDK v2 (checked 2026-10-05).
Run (server must be up):  python mcp_tools.py
"""
import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from langchain_core.tools import StructuredTool
from mcp import Client
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

load_dotenv()
MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:8000/mcp")


@asynccontextmanager
async def mcp_client(url: str = MCP_URL, api_key: str | None = None):
    """MCP client over Streamable HTTP. Sends `Authorization: Bearer <key>` if a key is set (Day 9 secure server)."""
    key = api_key or os.getenv("MERIDIAN_KEY")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    async with create_mcp_http_client(headers=headers) as http:
        async with Client(streamable_http_client(url, http_client=http)) as c:
            yield c


async def _call(name: str, args: dict) -> str:
    async with mcp_client() as c:
        result = await c.call_tool(name, args)
    text = "\n".join(getattr(b, "text", "") for b in result.content or [])
    if result.is_error:
        return f"error: {text}"
    return text or str(result.structured_content)


def _make_tool(t) -> StructuredTool:
    async def acall(**kwargs) -> str:
        return await _call(t.name, kwargs)

    def scall(**kwargs) -> str:
        return asyncio.run(_call(t.name, kwargs))

    return StructuredTool.from_function(func=scall, coroutine=acall, name=t.name,
                                        description=t.description or t.name, args_schema=t.input_schema)


async def load_mcp_tools(url: str = MCP_URL) -> list[StructuredTool]:
    """Discover tools at run time (tools/list) and wrap each as a LangChain tool."""
    async with mcp_client(url) as c:
        listed = await c.list_tools()
    return [_make_tool(t) for t in listed.tools]


if __name__ == "__main__":
    for tool in asyncio.run(load_mcp_tools()):
        print(tool.name, "|", tool.description[:80])