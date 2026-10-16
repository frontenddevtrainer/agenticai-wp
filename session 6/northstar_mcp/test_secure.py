# test_secure.py — try the server with no token, a wrong token, an analyst and an officer.
import asyncio
import urllib.error
import urllib.request
from mcp import Client
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

URL = "http://127.0.0.1:8002/mcp"

def raw_post(token: str | None) -> int:
    req = urllib.request.Request(URL, data=b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}', method="POST",
                                 headers={"content-type": "application/json", "accept": "application/json, text/event-stream",
                                          **({"authorization": f"Bearer {token}"} if token else {})})
    try:
        return urllib.request.urlopen(req).status
    except urllib.error.HTTPError as e:
        return e.code

def as_user(token: str) -> Client:
    return Client(streamable_http_client(URL, http_client=create_mcp_http_client(headers={"authorization": f"Bearer {token}"})))

async def main():
    print("no token      ->", raw_post(None))                     # 401
    print("wrong token   ->", raw_post("guess-123"))              # 401

    async with as_user("analyst-demo-token") as analyst:
        r = await analyst.call_tool("get_limit", {"merchant_id": "ACME"})
        print("analyst read  ->", r.content[0].text)
        r = await analyst.call_tool("set_limit", {"merchant_id": "ACME", "new_limit": 99_000_000, "reason": "why not"})
        print("analyst write ->", "ERROR:" if r.is_error else "", r.content[0].text)

    async with as_user("officer-demo-token") as officer:
        r = await officer.call_tool("set_limit", {"merchant_id": "ACME", "new_limit": 10_000_000, "reason": "Black Friday, approved RC-2291"})
        print("officer write ->", r.content[0].text)

asyncio.run(main())