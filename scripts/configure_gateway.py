#!/usr/bin/env python3
"""Render Kong configuration from a trusted issuer; no secret in tracked files.

Run after `set -a; source .env; set +a`. Existing shared secret is preserved;
otherwise a random secret is generated and written into the ignored .env.
"""

import json
import os
import secrets
import stat
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main():
    issuer = os.environ.get("SIGNET_ISSUER", "")
    u = urlsplit(issuer)
    if u.scheme != "https" or not u.netloc or u.username or u.query or u.fragment:
        raise SystemExit(
            "Set SIGNET_ISSUER to the instructor's real HTTPS issuer first"
        )
    if u.hostname == "signet.example.com":
        raise SystemExit(
            "Replace the example issuer before generating gateway settings"
        )
    env_path = ROOT / ".env"
    if not env_path.is_file() or env_path.is_symlink():
        raise SystemExit("Create a regular .env from .env.example first")
    secret = os.environ.get("GATEWAY_SHARED_SECRET") or secrets.token_hex(32)
    if len(secret) < 32 or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for c in secret
    ):
        raise SystemExit("Gateway secret must be 32+ URL-safe characters")
    lines = [
        line
        for line in env_path.read_text().splitlines()
        if not line.startswith("GATEWAY_SHARED_SECRET=")
    ]
    env_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    env_path.write_text("\n".join(lines) + f"\nGATEWAY_SHARED_SECRET={secret}\n")
    document = {
        "_format_version": "3.0",
        "services": [
            {
                "name": "workshop-mcp",
                "url": "http://mcp:8000",
                "routes": [
                    {
                        "name": "workshop-mcp",
                        "paths": ["/mcp", "/.well-known/oauth-protected-resource/mcp"],
                        "strip_path": False,
                        "preserve_host": True,
                    }
                ],
                "plugins": [
                    {
                        "name": "mcp-oauth2",
                        "config": {
                            "issuer": issuer,
                            "gateway_origin": "http://localhost:9000",
                            "resource_path": "/mcp",
                            "required_scopes": [
                                os.environ.get("READ_SCOPE", "notes:read")
                            ],
                            "leeway_seconds": 0,
                        },
                    },
                    {
                        "name": "request-transformer",
                        "config": {
                            "remove": {"headers": ["X-Workshop-Gateway"]},
                            "add": {"headers": ["X-Workshop-Gateway:" + secret]},
                        },
                    },
                ],
            }
        ],
    }
    runtime = ROOT / "labs/06/.runtime"
    runtime.mkdir(mode=0o700, exist_ok=True)
    runtime.chmod(0o700)
    path = runtime / "kong.yml"
    if path.is_symlink():
        raise SystemExit("Refusing symlink config")
    # JSON is valid YAML; JSON encoding safely handles issuer/scope strings.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    os.fchmod(fd, 0o644)  # Bind mount must be readable by Kong even under umask 077.
    with os.fdopen(fd, "w") as out:
        json.dump(document, out, indent=2)
    print(
        "Created ignored labs/06/.runtime/kong.yml and updated .env. Secret was not printed."
    )
    print(
        "Private host directory (0700), container-readable config (0644), read-only bind mount."
    )


if __name__ == "__main__":
    main()
