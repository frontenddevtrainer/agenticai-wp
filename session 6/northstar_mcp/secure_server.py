# secure_server.py — an MCP server that knows WHO is calling and WHAT they may do.
# Every request needs a bearer token; reading needs limits:read, changing a limit needs limits:write.
# Run:  python secure_server.py   (http://127.0.0.1:8002/mcp)   then:  python test_secure.py
import hashlib
import hmac
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

LIMITS = {"ACME": 9_500_000, "BOLT": 5_000_000}

# DEMO ONLY: tokens hashed in code. In production, verify JWTs from your identity provider (Okta, Entra ID, Keycloak):
# check the signature, expiry, issuer and audience (this server's URL), then read the scopes from the token.
TOKENS = {
    hashlib.sha256(b"analyst-demo-token").hexdigest(): ("asha@northstar", ["limits:read"]),
    hashlib.sha256(b"officer-demo-token").hexdigest(): ("ben@northstar", ["limits:read", "limits:write"]),
}

class DemoTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        digest = hashlib.sha256(token.encode()).hexdigest()
        for known, (subject, scopes) in TOKENS.items():
            if hmac.compare_digest(digest, known):                 # constant-time comparison
                return AccessToken(token=token, client_id="northstar-console", subject=subject, scopes=scopes)
        return None                                                # unknown token -> 401

mcp = MCPServer(
    "northstar-limits-secure",
    token_verifier=DemoTokenVerifier(),
    auth=AuthSettings(
        issuer_url="https://auth.northstar.example",               # who issues tokens (advertised to clients)
        resource_server_url="http://127.0.0.1:8002/mcp",           # this server: tokens must be meant for it
        required_scopes=["limits:read"],                           # minimum for ANY request
    ),
)

def require(scope: str) -> str:
    """Per-tool authorisation: the transport checked the token; this checks it allows THIS action."""
    token = get_access_token()
    if token is None or scope not in token.scopes:
        raise ToolError(f"not allowed: this action needs the '{scope}' scope")
    return token.subject or token.client_id

@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
def get_limit(merchant_id: str) -> dict:
    """A merchant's current monthly processing limit."""
    who = require("limits:read")
    return {"merchant_id": merchant_id.upper(), "limit": LIMITS[merchant_id.upper()], "read_by": who}

@mcp.tool(annotations=ToolAnnotations(destructive_hint=False, idempotent_hint=True))
def set_limit(merchant_id: str, new_limit: float, reason: str) -> dict:
    """Set a merchant's monthly processing limit (merchant risk officers only)."""
    who = require("limits:write")
    old = LIMITS[merchant_id.upper()]
    LIMITS[merchant_id.upper()] = new_limit
    print(f"AUDIT {who}: {merchant_id.upper()} {old:,.0f} -> {new_limit:,.0f} ({reason})")   # who did what, and why
    return {"merchant_id": merchant_id.upper(), "old": old, "new": new_limit, "changed_by": who}

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8002)