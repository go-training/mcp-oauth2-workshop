"""Read top-to-bottom: trusted discovery, JWT verification, HTTP auth, MCP tools.

Each lab entrypoint selects a stage; transport plumbing stays shared so the
class spends its time learning authorization rather than JSON-RPC internals.
"""

import contextvars
import hmac
import json
import logging
import os
from dataclasses import dataclass
from urllib.parse import quote_plus, urlsplit

import httpx
import jwt
import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, PlainTextResponse

log = logging.getLogger("workshop")
identity = contextvars.ContextVar("identity", default=None)


@dataclass
class Config:
    lab: int
    resource: str = "http://localhost:8000/mcp"
    issuer: str = ""
    read_scope: str = "notes:read"
    write_scope: str = "notes:write"
    introspection_id: str = ""
    introspection_secret: str = ""
    gateway_secret: str = ""

    @classmethod
    def from_env(cls, lab):
        return cls(
            lab=lab,
            resource=os.getenv("MCP_RESOURCE", "http://localhost:8000/mcp"),
            issuer=os.getenv("SIGNET_ISSUER", ""),
            read_scope=os.getenv("READ_SCOPE", "notes:read"),
            write_scope=os.getenv("WRITE_SCOPE", "notes:write"),
            introspection_id=os.getenv("INTROSPECTION_CLIENT_ID", ""),
            introspection_secret=os.getenv("INTROSPECTION_CLIENT_SECRET", ""),
            gateway_secret=os.getenv("GATEWAY_SHARED_SECRET", ""),
        )


def trusted_url(raw):
    u = urlsplit(raw)
    if not u.netloc or u.username or u.password or u.fragment:
        raise ValueError("invalid trusted URL")
    if u.scheme == "https":
        return raw
    if (
        os.getenv("ALLOW_INSECURE_ISSUER") == "1"
        and u.scheme == "http"
        and u.hostname in ("127.0.0.1", "localhost", "::1")
    ):
        return raw
    raise ValueError("issuer and its endpoints must use HTTPS")


def discover(issuer):
    trusted_url(issuer)
    u = urlsplit(issuer)
    origin = f"{u.scheme}://{u.netloc}"
    path = u.path.rstrip("/")
    candidates = [
        origin + "/.well-known/oauth-authorization-server" + path,
        origin + "/.well-known/openid-configuration" + path,
    ]
    if path:
        candidates.append(origin + path + "/.well-known/openid-configuration")
    with httpx.Client(timeout=5, follow_redirects=False) as client:
        for endpoint in candidates:
            try:
                response = client.get(endpoint)
                response.raise_for_status()
                metadata = response.json()
            except (httpx.HTTPError, ValueError):
                continue
            if metadata.get("issuer") != issuer:
                raise ValueError("metadata issuer mismatch")
            for key in (
                "jwks_uri",
                "authorization_endpoint",
                "token_endpoint",
                "revocation_endpoint",
                "introspection_endpoint",
            ):
                if key in metadata:
                    trusted_url(metadata[key])
            return metadata
    raise ValueError("authorization server discovery failed")


def validate_resource(raw):
    u = urlsplit(raw)
    if (
        not u.netloc
        or u.path != "/mcp"
        or u.query
        or u.fragment
        or u.username
        or not (
            u.scheme == "https" or (u.scheme == "http" and u.hostname in ("localhost", "127.0.0.1"))
        )
    ):
        raise ValueError("MCP resource must be HTTPS or loopback HTTP, ending exactly in /mcp")
    return u


class Authorization:
    def __init__(self, app, config):
        self.app, self.config = app, config
        u = validate_resource(config.resource)
        self.origin = f"{u.scheme}://{u.netloc}"
        self.metadata_url = self.origin + "/.well-known/oauth-protected-resource/mcp"
        if 2 <= config.lab <= 5:
            trusted_url(config.issuer)
        if 3 <= config.lab <= 5:
            metadata = discover(config.issuer)
            self.jwks = jwt.PyJWKClient(metadata["jwks_uri"], lifespan=300, timeout=5)
            if config.lab == 5:
                self.introspect = metadata["introspection_endpoint"]
                if not config.introspection_id or not config.introspection_secret:
                    raise ValueError("Lab 05 requires per-team introspection credentials")
        if config.lab == 6 and len(config.gateway_secret) < 32:
            raise ValueError("Lab 06 requires a random GATEWAY_SHARED_SECRET (32+ characters)")

    def verify(self, raw):
        key = self.jwks.get_signing_key_from_jwt(raw)
        claims = jwt.decode(
            raw,
            key.key,
            algorithms=["RS256"],
            issuer=self.config.issuer,
            audience=self.config.resource,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
        if (
            claims.get("type") != "access"
            or not isinstance(claims.get("sub"), str)
            or not claims["sub"]
            or not isinstance(claims.get("scope"), str)
        ):
            raise jwt.InvalidTokenError("invalid access token claims")
        return {
            "subject": claims["sub"],
            "scope": claims["scope"],
            "audience": claims["aud"],
            "token_id": claims.get("jti", ""),
        }

    async def active(self, raw):
        c = self.config
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            response = await client.post(
                self.introspect,
                data={"token": raw, "token_type_hint": "access_token"},
                auth=(quote_plus(c.introspection_id), quote_plus(c.introspection_secret)),
            )
            response.raise_for_status()
            active = response.json().get("active")
            if not isinstance(active, bool):
                raise ValueError("invalid introspection response")
            return active

    def denied(self, status, error, required=None):
        headers = {"Cache-Control": "no-store"}
        if status in (401, 403):
            headers["WWW-Authenticate"] = (
                f'Bearer resource_metadata="{self.metadata_url}", error="{error}", '
                f'scope="{required or self.config.read_scope}"'
            )
        log.info("authorization denied lab=%s status=%s reason=%s", self.config.lab, status, error)
        return JSONResponse({"error": error}, status, headers=headers)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        c = self.config
        headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        response = None
        if headers.get("origin", self.origin) != self.origin:
            response = self.denied(403, "untrusted_origin")
        elif scope["path"] == "/healthz":
            response = PlainTextResponse("ok")
        elif (
            scope["path"]
            in (
                "/.well-known/oauth-protected-resource/mcp",
                "/.well-known/oauth-protected-resource",
            )
            and 2 <= c.lab <= 5
        ):
            response = (
                JSONResponse(
                    {
                        "resource": c.resource,
                        "authorization_servers": [c.issuer],
                        "scopes_supported": [c.read_scope],
                        "bearer_methods_supported": ["header"],
                    },
                    headers={"Cache-Control": "no-store"},
                )
                if scope["method"] == "GET"
                else PlainTextResponse("", 405)
            )
        elif scope["path"] != "/mcp":
            response = PlainTextResponse("Not found", 404)
        else:
            from urllib.parse import parse_qs

            if "access_token" in parse_qs(
                scope.get("query_string", b"").decode(), keep_blank_values=True
            ):
                response = self.denied(400, "token_in_query_forbidden")
        if response:
            return await response(scope, receive, send)
        caller = {"subject": "anonymous", "scope": "", "audience": c.resource}
        if c.lab == 2:
            return await self.denied(401, "invalid_token")(scope, receive, send)
        if 3 <= c.lab <= 5:
            parts = headers.get("authorization", "").split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return await self.denied(401, "invalid_token")(scope, receive, send)
            try:
                caller = await run_in_threadpool(self.verify, parts[1])
            except jwt.PyJWKClientConnectionError:
                return await self.denied(503, "temporarily_unavailable")(scope, receive, send)
            except (jwt.PyJWTError, ValueError, TypeError, KeyError):
                return await self.denied(401, "invalid_token")(scope, receive, send)
            if c.lab == 5:
                try:
                    active = await self.active(parts[1])
                except (httpx.HTTPError, ValueError):
                    return await self.denied(503, "temporarily_unavailable")(scope, receive, send)
                if not active:
                    return await self.denied(401, "invalid_token")(scope, receive, send)
        if c.lab == 6:
            if not hmac.compare_digest(headers.get("x-workshop-gateway", ""), c.gateway_secret):
                return await self.denied(401, "untrusted_gateway")(scope, receive, send)
            caller = {
                "subject": headers.get("x-mcp-subject", ""),
                "scope": headers.get("x-mcp-scope", ""),
                "audience": headers.get("x-mcp-audience", ""),
                "token_id": headers.get("x-mcp-token-id", ""),
            }
            if (
                not caller["subject"]
                or headers.get("x-mcp-issuer") != c.issuer
                or caller["audience"] != c.resource
            ):
                return await self.denied(401, "invalid_gateway_identity")(scope, receive, send)
        if c.lab >= 3 and c.read_scope not in caller["scope"].split():
            return await self.denied(403, "insufficient_scope")(scope, receive, send)
        if c.lab >= 4 and scope["method"] == "POST":
            chunks = []
            size = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > 1024 * 1024:
                    return await self.denied(413, "request_too_large")(scope, receive, send)
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break
            body = b"".join(chunks)
            try:
                rpc = json.loads(body)
                write = (
                    isinstance(rpc, dict)
                    and rpc.get("method") == "tools/call"
                    and isinstance(rpc.get("params"), dict)
                    and rpc["params"].get("name") == "create_note"
                )
            except ValueError:
                write = False
            if write and c.write_scope not in caller["scope"].split():
                return await self.denied(
                    403, "insufficient_scope", c.read_scope + " " + c.write_scope
                )(scope, receive, send)
            original_receive = receive
            delivered = False

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await original_receive()

            receive = replay
        log.info(
            "authorized request lab=%s subject=%s token_id=%s method=%s",
            c.lab,
            caller["subject"],
            caller.get("token_id", ""),
            scope["method"],
        )
        marker = identity.set(caller)
        try:
            await self.app(scope, receive, send)
        finally:
            identity.reset(marker)


def create_app(config):
    if config.lab not in range(1, 7):
        raise ValueError("lab must be 1..6")
    mcp = MCPServer(f"workshop-python-lab{config.lab:02d}")
    notes = {}

    @mcp.tool()
    def whoami() -> dict:
        """Show the verified workshop identity, never the raw token."""
        return identity.get()

    @mcp.tool()
    def list_notes() -> dict:
        """Read your own in-memory workshop notes."""
        return {"notes": list(notes.get(identity.get()["subject"], []))}

    @mcp.tool()
    def create_note(text: str) -> dict:
        """Create a note; requires notes:write in Lab 04 and later."""
        caller = identity.get()
        if config.lab >= 4 and config.write_scope not in caller["scope"].split():
            raise ValueError("insufficient_scope")
        if not 1 <= len(text) <= 500:
            raise ValueError("text must have 1..500 characters")
        own = notes.setdefault(caller["subject"], [])
        if len(own) >= 100:
            raise ValueError("workshop note limit reached")
        own.append(text)
        return {"notes": list(own)}

    app = mcp.streamable_http_app(
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=[urlsplit(config.resource).netloc, "localhost:*", "127.0.0.1:*"],
            allowed_origins=[
                f"{urlsplit(config.resource).scheme}://{urlsplit(config.resource).netloc}"
            ],
        ),
    )
    return Authorization(app, config)


def run(lab):
    logging.basicConfig(level=logging.INFO)
    address = os.getenv("LISTEN_ADDR", "127.0.0.1:8000")
    host, port = address.rsplit(":", 1)
    uvicorn.run(create_app(Config.from_env(lab)), host=host, port=int(port), access_log=False)
