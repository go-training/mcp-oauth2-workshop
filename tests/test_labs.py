"""Black-box parity tests. The local issuer is a TEST FIXTURE, not Signet.

No real user credentials or live authorization service are needed. HTTP is
explicitly enabled only for loopback fixtures. All six real MCP servers run.
"""

import base64
import hashlib
import json
import os
import re
import socket
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "python/.venv/bin/python"
HEADERS = {
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2025-11-25",
}


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Issuer:
    def __init__(self):
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()))
        self.jwk.update(kid="workshop-test", alg="RS256", use="sig")
        self.revoked = set()
        self.offline = False
        self.codes = {}
        self.exchanges = []

    def token(self, resource, **changes):
        claims = dict(
            iss=self.url,
            aud=resource,
            sub="alice",
            scope="notes:read",
            type="access",
            exp=int(time.time()) + 300,
            iat=int(time.time()) - 1,
            jti=str(uuid.uuid4()),
        )
        claims.update(changes)
        return jwt.encode(
            claims, self.key, algorithm="RS256", headers={"kid": "workshop-test"}
        )


@pytest.fixture(scope="session")
def issuer():
    fixture = Issuer()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, body):
            raw = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path in (
                "/.well-known/oauth-authorization-server",
                "/.well-known/openid-configuration",
            ):
                self.reply(
                    200,
                    dict(
                        issuer=fixture.url,
                        jwks_uri=fixture.url + "/jwks",
                        authorization_endpoint=fixture.url + "/authorize",
                        token_endpoint=fixture.url + "/token",
                        revocation_endpoint=fixture.url + "/revoke",
                        introspection_endpoint=fixture.url + "/introspect",
                        code_challenge_methods_supported=["S256"],
                    ),
                )
            elif path == "/jwks":
                self.reply(200, {"keys": [fixture.jwk]})
            elif path == "/authorize":
                q = {k: v[0] for k, v in parse_qs(urlsplit(self.path).query).items()}
                assert q["code_challenge_method"] == "S256"
                code = str(uuid.uuid4())
                fixture.codes[code] = q
                self.send_response(302)
                self.send_header(
                    "Location",
                    q["redirect_uri"]
                    + "?"
                    + urlencode(
                        {"code": code, "state": q["state"], "iss": fixture.url}
                    ),
                )
                self.end_headers()
            else:
                self.reply(404, {})

        def do_POST(self):
            q = {
                k: v[0]
                for k, v in parse_qs(
                    self.rfile.read(int(self.headers["Content-Length"])).decode()
                ).items()
            }
            if self.path == "/introspect":
                expected = "Basic " + base64.b64encode(b"team:secret").decode()
                if self.headers.get("Authorization") != expected:
                    return self.reply(401, {})
                if fixture.offline:
                    return self.reply(503, {})
                # Signet's ownership default can return JUST active across clients.
                self.reply(200, {"active": q["token"] not in fixture.revoked})
            elif self.path == "/revoke":
                fixture.revoked.add(q["token"])
                self.reply(200, {})
            elif self.path == "/token":
                original = fixture.codes.pop(q["code"])
                challenge = (
                    base64.urlsafe_b64encode(
                        hashlib.sha256(q["code_verifier"].encode()).digest()
                    )
                    .rstrip(b"=")
                    .decode()
                )
                if (
                    challenge != original["code_challenge"]
                    or q["resource"] != original["resource"]
                    or q["redirect_uri"] != original["redirect_uri"]
                    or q["client_id"] != original["client_id"]
                ):
                    return self.reply(400, {"error": "invalid_grant"})
                fixture.exchanges.append(q)
                self.reply(
                    200,
                    {
                        "access_token": fixture.token(
                            q["resource"], scope=original["scope"]
                        ),
                        "token_type": "Bearer",
                    },
                )
            else:
                self.reply(404, {})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    fixture.url = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield fixture
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="session", autouse=True)
def build_go():
    (ROOT / ".build").mkdir(exist_ok=True)
    for lab in range(1, 7):
        subprocess.run(
            [
                "go",
                "build",
                "-o",
                str(ROOT / f".build/lab{lab:02d}"),
                f"./labs/{lab:02d}",
            ],
            cwd=ROOT / "go",
            check=True,
        )
    subprocess.run(
        ["go", "build", "-o", str(ROOT / ".build/oauth"), "./cmd/oauth"],
        cwd=ROOT / "go",
        check=True,
    )


@pytest.fixture(params=["go", "python"])
def language(request):
    return request.param


@pytest.fixture
def start(language, issuer, tmp_path):
    processes = []

    def launch(lab, **overrides):
        p = port()
        resource = f"http://localhost:{p}/mcp"
        env = {
            **os.environ,
            "PYTHONPATH": str(ROOT / "python"),
            "SIGNET_ISSUER": issuer.url,
            "MCP_RESOURCE": resource,
            "LISTEN_ADDR": f"127.0.0.1:{p}",
            "ALLOW_INSECURE_ISSUER": "1",
            "INTROSPECTION_CLIENT_ID": "team",
            "INTROSPECTION_CLIENT_SECRET": "secret",
            "GATEWAY_SHARED_SECRET": "test-gateway-secret-with-32-characters",
            **overrides,
        }
        cmd = (
            [str(ROOT / f".build/lab{lab:02d}")]
            if language == "go"
            else [str(PYTHON), str(ROOT / f"python/labs/{lab:02d}/main.py")]
        )
        log = (tmp_path / f"{lab}-{p}.log").open("w+")
        proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=log)
        processes.append((proc, log))
        for _ in range(100):
            if proc.poll() is not None:
                log.seek(0)
                pytest.fail(log.read())
            try:
                if (
                    httpx.get(
                        resource.replace("/mcp", "/healthz"), timeout=0.3
                    ).status_code
                    == 200
                ):
                    return resource
            except httpx.HTTPError:
                pass
            time.sleep(0.05)
        pytest.fail("server did not become healthy")

    yield launch
    for proc, log in processes:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        log.close()
    issuer.offline = False


def rpc(
    resource, token=None, method="tools/call", name="whoami", arguments=None, extra=None
):
    headers = dict(HEADERS)
    if token:
        headers["Authorization"] = "Bearer " + token
    headers.update(extra or {})
    params = {"name": name, "arguments": arguments or {}}
    if method == "initialize":
        params = {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        }
    if method == "tools/list":
        params = {}
    return httpx.post(
        resource,
        headers=headers,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=10,
    )


def data(response):
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert not result.get("isError"), result
    return result.get("structuredContent") or json.loads(result["content"][0]["text"])


def test_lab01_baseline(start):
    resource = start(1)
    response = rpc(resource, method="initialize")
    assert response.status_code == 200
    assert "tools" in response.json()["result"]["capabilities"]
    tools = rpc(resource, method="tools/list").json()["result"]["tools"]
    assert {t["name"] for t in tools} == {"whoami", "list_notes", "create_note"}
    assert data(rpc(resource))["subject"] == "anonymous"


def test_lab02_discovery(start, issuer):
    resource = start(2)
    response = rpc(resource)
    assert response.status_code == 401
    metadata_url = re.search(
        'resource_metadata="([^"]+)"', response.headers["www-authenticate"]
    )[1]
    metadata = httpx.get(metadata_url).json()
    assert metadata["resource"] == resource
    assert metadata["authorization_servers"] == [issuer.url]
    assert metadata["scopes_supported"] == ["notes:read"]
    assert (
        rpc(resource, issuer.token(resource)).status_code == 401
    )  # discovery-only checkpoint


@pytest.mark.parametrize(
    "changes",
    [
        None,
        {"exp": 1},
        {"iss": "https://wrong.example"},
        {"aud": "https://other.example/mcp"},
        {"type": "refresh"},
        {"sub": ""},
        {"exp": None},
    ],
)
def test_lab03_rejects_invalid_tokens(start, issuer, changes):
    resource = start(3)
    token = None if changes is None else issuer.token(resource, **changes)
    assert rpc(resource, token).status_code == 401


def test_lab03_signature_and_valid_identity(start, issuer):
    resource = start(3)
    token = issuer.token(resource)
    assert data(rpc(resource, token))["subject"] == "alice"
    forged = jwt.encode(
        {"sub": "alice", "type": "access"},
        "not-the-private-key-and-not-an-rsa-key-either",
        algorithm="HS256",
        headers={"kid": "workshop-test"},
    )
    assert rpc(resource, forged).status_code == 401
    assert rpc(resource + "?access_token=leak", token).status_code == 400
    assert (
        rpc(resource, token, extra={"Origin": "https://evil.example"}).status_code
        == 403
    )
    assert (
        data(rpc(resource, token, extra={"X-MCP-Subject": "mallory"}))["subject"]
        == "alice"
    )


def test_lab04_scope_isolation_and_audience(start, issuer):
    resource = start(4)
    read = issuer.token(resource)
    denied = rpc(resource, read, name="create_note", arguments={"text": "secret"})
    assert denied.status_code == 403
    assert "notes:write" in denied.headers["www-authenticate"]
    write = issuer.token(resource, scope="notes:read notes:write")
    assert data(
        rpc(resource, write, name="create_note", arguments={"text": "alice note"})
    )["notes"] == ["alice note"]
    assert data(rpc(resource, read, name="list_notes"))["notes"] == ["alice note"]
    bob = issuer.token(resource, sub="bob")
    assert data(rpc(resource, bob, name="list_notes"))["notes"] == []
    resource_b = start(4)
    assert rpc(resource_b, read).status_code == 401
    assert data(rpc(resource_b, issuer.token(resource_b)))["subject"] == "alice"


def test_lab05_revocation_and_outage(start, issuer):
    resource = start(5)
    token = issuer.token(resource)
    assert data(rpc(resource, token))["subject"] == "alice"
    issuer.revoked.add(token)
    assert rpc(resource, token).status_code == 401
    fresh = issuer.token(resource)
    issuer.offline = True
    assert rpc(resource, fresh).status_code == 503


def test_lab06_gateway_boundary(start, issuer):
    resource = start(6)
    identity_headers = {
        "X-MCP-Subject": "alice",
        "X-MCP-Scope": "notes:read",
        "X-MCP-Issuer": issuer.url,
        "X-MCP-Audience": resource,
    }
    assert rpc(resource, extra=identity_headers).status_code == 401
    identity_headers["X-Workshop-Gateway"] = "test-gateway-secret-with-32-characters"
    assert data(rpc(resource, extra=identity_headers))["subject"] == "alice"
    assert (
        rpc(
            resource,
            extra=identity_headers,
            name="create_note",
            arguments={"text": "no"},
        ).status_code
        == 403
    )
    identity_headers["X-MCP-Audience"] = "https://other.example/mcp"
    assert rpc(resource, extra=identity_headers).status_code == 401


def test_reference_client_pkce_call_revoke(language, issuer, start, tmp_path):
    resource = start(5)
    token_file = tmp_path / "token.json"
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "python"),
        "ALLOW_INSECURE_ISSUER": "1",
    }

    def command(operation, *extra):
        if language == "go":
            return [
                str(ROOT / ".build/oauth"),
                "-command",
                operation,
                "-issuer",
                issuer.url,
                "-resource",
                resource,
                "-token-file",
                str(token_file),
                *extra,
            ]
        return [
            str(PYTHON),
            "-m",
            "workshop.oauth",
            operation,
            "--issuer",
            issuer.url,
            "--resource",
            resource,
            "--token-file",
            str(token_file),
            *extra,
        ]

    login_args = (
        ["-client-id", "test-public", "-callback-port", "0"]
        if language == "go"
        else ["--client-id", "test-public", "--callback-port", "0", "--no-browser"]
    )
    proc = subprocess.Popen(
        command("login", *login_args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        # Read asynchronously with a deadline so failed clients cannot hang CI.
        lines = []

        def reader():
            for line in proc.stdout:
                lines.append(line)

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        deadline = time.monotonic() + 15
        while (
            not any(line.startswith("http") for line in lines)
            and proc.poll() is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.05)
        auth_url = next(line.strip() for line in lines if line.startswith("http"))
        original = parse_qs(urlsplit(auth_url).query)
        bad_callback = original["redirect_uri"][0] + "?state=wrong&code=bad"
        assert httpx.get(bad_callback).status_code == 400
        assert httpx.get(auth_url, follow_redirects=True).status_code == 200
        assert proc.wait(timeout=10) == 0, lines
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    assert token_file.stat().st_mode & 0o777 == 0o600
    assert issuer.exchanges[-1]["resource"] == resource
    assert subprocess.run(command("call"), env=env, capture_output=True).returncode == 0
    assert (
        subprocess.run(command("revoke"), env=env, capture_output=True).returncode == 0
    )
    assert subprocess.run(command("call"), env=env, capture_output=True).returncode != 0


def test_reference_client_rejects_unsafe_destination(language, tmp_path):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "python")}
    if language == "go":
        command = [str(ROOT / ".build/oauth"), "-command", "call"]
    else:
        command = [str(PYTHON), "-m", "workshop.oauth", "call"]
    for destination, cross in [
        ("http://remote.example/mcp", False),
        ("https://remote.example/mcp", True),
    ]:
        args = [
            "--resource",
            destination,
            "--token-file",
            str(tmp_path / "absent.json"),
        ]
        if cross:
            args.append("--allow-cross-resource")
        result = subprocess.run(
            command + args, env=env, capture_output=True, text=True, timeout=5
        )
        assert result.returncode != 0
        assert (
            "loopback" in result.stdout + result.stderr
            or "local workshop" in result.stdout + result.stderr
        )


def test_reference_client_reports_jsonrpc_error(language, tmp_path):
    class ErrorHandler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if body["method"] == "initialize":
                reply = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {"protocolVersion": "2025-11-25", "capabilities": {}},
                }
            else:
                reply = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "error": {"code": -32601, "message": "No such method"},
                }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(reply).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), ErrorHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    env = {**os.environ, "PYTHONPATH": str(ROOT / "python")}
    command = (
        [str(ROOT / ".build/oauth"), "-command", "call"]
        if language == "go"
        else [str(PYTHON), "-m", "workshop.oauth", "call"]
    )
    try:
        result = subprocess.run(
            command
            + [
                "--resource",
                f"http://localhost:{server.server_port}/mcp",
                "--token-file",
                str(tmp_path / "absent.json"),
            ],
            env=env,
            capture_output=True,
            timeout=10,
        )
        assert result.returncode != 0
    finally:
        server.shutdown()
        server.server_close()


def test_gateway_config_and_python_host(tmp_path, monkeypatch):
    import importlib.util
    import sys

    sys.path.insert(0, str(ROOT / "python"))
    from starlette.testclient import TestClient
    from workshop.server import Config, create_app

    spec = importlib.util.spec_from_file_location(
        "gateway_config", ROOT / "scripts/configure_gateway.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = tmp_path
    (tmp_path / "labs/06").mkdir(parents=True)
    (tmp_path / ".env").write_text("SIGNET_ISSUER=https://issuer.example\n")
    monkeypatch.setenv("SIGNET_ISSUER", "https://issuer.example")
    monkeypatch.delenv("GATEWAY_SHARED_SECRET", raising=False)
    previous_umask = os.umask(0o077)
    try:
        module.main()
        generated = tmp_path / "labs/06/.runtime/kong.yml"
        generated.chmod(0o600)
        module.main()  # Repair existing restrictive permissions too.
    finally:
        os.umask(previous_umask)
    path = tmp_path / "labs/06/.runtime/kong.yml"
    config = json.loads(path.read_text())
    assert config["services"][0]["routes"][0]["preserve_host"] is True
    assert config["services"][0]["routes"][0]["strip_path"] is False
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert path.stat().st_mode & 0o777 == 0o644
    assert (tmp_path / ".env").stat().st_mode & 0o777 == 0o600
    secret = (tmp_path / ".env").read_text().split("GATEWAY_SHARED_SECRET=")[1].strip()
    app = create_app(
        Config(
            lab=6,
            resource="http://localhost:9000/mcp",
            issuer="https://issuer.example",
            gateway_secret=secret,
        )
    )
    with TestClient(app, base_url="http://localhost:9000") as client:
        response = client.post(
            "/mcp",
            headers={
                **HEADERS,
                "X-Workshop-Gateway": secret,
                "X-MCP-Subject": "alice",
                "X-MCP-Scope": "notes:read",
                "X-MCP-Issuer": "https://issuer.example",
                "X-MCP-Audience": "http://localhost:9000/mcp",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "whoami", "arguments": {}},
            },
        )
        assert data(response)["subject"] == "alice"
        bad = client.post(
            "/mcp",
            headers={
                **HEADERS,
                "Host": "evil.example",
                "X-Workshop-Gateway": secret,
                "X-MCP-Subject": "alice",
                "X-MCP-Scope": "notes:read",
                "X-MCP-Issuer": "https://issuer.example",
                "X-MCP-Audience": "http://localhost:9000/mcp",
            },
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )
        assert bad.status_code == 421
