#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root/go"
test -z "$(gofmt -l .)"
go vet ./...
go test ./...
cd "$repo_root"
uv sync --project python --frozen
uv run --project python --frozen ruff check python tests scripts
uv run --project python --frozen ruff format --check python tests scripts
uv run --project python --frozen pytest -q
