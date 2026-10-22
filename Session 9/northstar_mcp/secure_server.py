"""Day 9 Lab 1 (Part A): the Day 6 MCP server behind API-key auth with per-key tool scopes.

Lab-grade: production uses OAuth 2.1 tokens (iss/aud/exp/scope validated) via the SDK's auth support or a gateway.
Run (from meridian/):  MERIDIAN_KEY=... DISPUTES_KEY=... python -m northstar_mcp.secure_server
"""
import hmac
import json
import os

import uvicorn
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from northstar_mcp.server import mcp

load_dotenv()

# key -> scopes (load from a secret store in real life; never commit keys)
API_KEYS = {
    os.environ["MERIDIAN_KEY"]: {"policies:read", "merchants:read"},
    os.environ["DISPUTES_KEY"]: {"policies:read"},
}
TOOL_SCOPES = {"search_policies": "policies:read", "get_merchant_risk_profile": "merchants:read"}


class ApiKeyAuth(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        supplied = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        scopes = next((s for k, s in API_KEYS.items() if hmac.compare_digest(k, supplied)), None)
        if scopes is None:
            return JSONResponse({"error": "unauthorized"}, status_code=401,
                                headers={"WWW-Authenticate": 'Bearer realm="northstar-kb"'})
        if request.method == "POST":                       # per-tool scope check on JSON-RPC tools/call
            try:
                msg = json.loads(await request.body() or b"{}")
            except json.JSONDecodeError:
                msg = {}
            if isinstance(msg, dict) and msg.get("method") == "tools/call":
                needed = TOOL_SCOPES.get(msg.get("params", {}).get("name"))
                if needed and needed not in scopes:
                    return JSONResponse({"jsonrpc": "2.0", "id": msg.get("id"),
                                         "error": {"code": -32003, "message": f"forbidden: missing scope {needed}"}},
                                        status_code=200)  # JSON-RPC errors travel in a 200 response
        return await call_next(request)


HOST = os.getenv("MCP_HOST", "127.0.0.1")
app = mcp.streamable_http_app(host=HOST)   # ASGI app (SDK v2: transport options go here / to run())
app.add_middleware(ApiKeyAuth)

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=int(os.getenv("MCP_PORT", "8000")))