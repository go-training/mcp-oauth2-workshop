"""Deterministic teaching client: PKCE login, MCP calls and Signet revocation.

Uses a pre-registered public client. Token files are local, ignored, mode 0600.
For daily AI use choose Claude Code or Codex; this client exposes protocol steps.
"""

import argparse
import base64
import hashlib
import json
import os
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx

from workshop.server import discover, validate_resource

PROTOCOL_VERSION = "2026-07-28"


def save_token(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # O_EXCL avoids overwriting another exercise's token or following a symlink.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as out:
        json.dump(data, out)


def login(args):
    validate_resource(args.resource)
    metadata = discover(args.issuer)
    if "S256" not in metadata.get("code_challenge_methods_supported", []):
        raise ValueError("authorization server does not advertise PKCE S256")
    if not args.client_id:
        raise ValueError("set OAUTH_CLIENT_ID to your pre-registered PUBLIC client ID")
    if args.token_file.exists():
        raise ValueError("token file already exists; choose a new --token-file")
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )
    state = secrets.token_urlsafe(32)
    result = {}

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Never log authorization codes or query strings.

        def do_GET(self):
            u = urlsplit(self.path)
            query = parse_qs(u.query)
            if u.path != "/callback" or not secrets.compare_digest(
                query.get("state", [""])[0], state
            ):
                self.send_error(400, "Invalid callback state")
                return
            result.update({k: v[0] for k, v in query.items()})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Callback received. Return to your terminal.")

    server = HTTPServer(("127.0.0.1", args.callback_port), Callback)
    server.timeout = 1
    redirect = f"http://127.0.0.1:{server.server_port}/callback"
    auth_url = (
        metadata["authorization_endpoint"]
        + "?"
        + urlencode(
            {
                "response_type": "code",
                "client_id": args.client_id,
                "redirect_uri": redirect,
                "scope": args.scopes,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": args.resource,
            }
        )
    )
    print("Open this URL in your browser:\n" + auth_url, flush=True)
    if not args.no_browser:
        webbrowser.open(auth_url)
    deadline = time.monotonic() + 180
    try:
        while not result and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()
    if not result or "error" in result or not result.get("code"):
        raise ValueError("authorization denied or timed out")
    # RFC 9207: compare iss exactly; reject a missing iss when the server advertises it.
    if (
        metadata.get("authorization_response_iss_parameter_supported") is True
        and "iss" not in result
    ):
        raise ValueError("callback missing issuer")
    if "iss" in result and result["iss"] != args.issuer:
        raise ValueError("callback issuer mismatch")
    with httpx.Client(timeout=10, follow_redirects=False) as client:
        response = client.post(
            metadata["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "client_id": args.client_id,
                "code": result["code"],
                "redirect_uri": redirect,
                "code_verifier": verifier,
                "resource": args.resource,
            },
        )
        if response.status_code != 200:
            raise ValueError(f"token exchange failed: HTTP {response.status_code}")
        token = response.json()
    if (
        not isinstance(token.get("access_token"), str)
        or token.get("token_type", "").lower() != "bearer"
    ):
        raise ValueError("invalid token response")
    # Store only the access token; no refresh token is needed for these exercises.
    save_token(
        args.token_file,
        {"access_token": token["access_token"], "issuer": args.issuer, "resource": args.resource},
    )
    print(f"Saved access token to {args.token_file} (0600); token value is not printed.")


def call(args):
    target = validate_resource(args.resource)
    if args.allow_cross_resource and target.hostname not in ("localhost", "127.0.0.1"):
        raise ValueError("negative audience exercise is limited to local workshop servers")
    headers = {
        "Accept": "application/json, text/event-stream",
        # MCP 2026-07-28: no initialize handshake; each request carries version and method headers.
        "MCP-Protocol-Version": PROTOCOL_VERSION,
        "Mcp-Method": "tools/call",
        "Mcp-Name": args.tool,
    }
    if args.token_file.exists():
        stored = json.loads(args.token_file.read_text())
        # Explicit --allow-cross-resource is ONLY for the audience rejection exercise.
        if stored["resource"] != args.resource and not args.allow_cross_resource:
            raise ValueError("token resource differs; use --allow-cross-resource only for Lab 04")
        headers["Authorization"] = "Bearer " + stored["access_token"]
    with httpx.Client(timeout=10, follow_redirects=False) as client:
        response = client.post(
            args.resource,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": args.tool,
                    "arguments": {"text": args.text} if args.tool == "create_note" else {},
                    "_meta": {
                        "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
                        "io.modelcontextprotocol/clientInfo": {
                            "name": "workshop-probe",
                            "version": "1.0.0",
                        },
                        "io.modelcontextprotocol/clientCapabilities": {},
                    },
                },
            },
        )
        print(response.status_code, response.headers.get("www-authenticate", ""), response.text)
        return (
            0
            if response.status_code == 200
            and "error" not in response.json()
            and isinstance(response.json().get("result"), dict)
            and not response.json()["result"].get("isError")
            else 1
        )


def revoke(args):
    stored = json.loads(args.token_file.read_text())
    if stored["issuer"] != args.issuer:
        raise ValueError("token issuer differs from configured issuer")
    endpoint = discover(args.issuer)["revocation_endpoint"]
    with httpx.Client(timeout=10, follow_redirects=False) as client:
        response = client.post(
            endpoint, data={"token": stored["access_token"], "token_type_hint": "access_token"}
        )
        response.raise_for_status()
    print("Revocation accepted. Keep this file to prove the SAME token now fails in Lab 05.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["login", "call", "revoke", "metadata"])
    parser.add_argument("--issuer", default=os.getenv("SIGNET_ISSUER", ""))
    parser.add_argument(
        "--resource", default=os.getenv("MCP_RESOURCE", "http://localhost:8000/mcp")
    )
    parser.add_argument("--client-id", default=os.getenv("OAUTH_CLIENT_ID", ""))
    parser.add_argument("--scopes", default="notes:read")
    parser.add_argument("--callback-port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--token-file", type=Path, default=Path(".tokens/access.json"))
    parser.add_argument("--tool", choices=["whoami", "list_notes", "create_note"], default="whoami")
    parser.add_argument("--text", default="Hello workshop")
    parser.add_argument("--allow-cross-resource", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "metadata":
            print(json.dumps(discover(args.issuer), indent=2))
            return 0
        return {"login": login, "call": call, "revoke": revoke}[args.command](args) or 0
    except (ValueError, KeyError, OSError, httpx.HTTPError) as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
