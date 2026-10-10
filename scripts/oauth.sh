#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
language="${1:?Usage: oauth.sh go|python login|call|revoke|metadata [options]}"
operation="${2:?Missing operation}"
shift 2
# Both CLIs accept double-dash flags. Keep token files relative to repo root.
cd "$repo_root"
case "$language" in
  go) mkdir -p .build; (cd go && go build -o ../.build/oauth ./cmd/oauth); exec .build/oauth -command "$operation" "$@" ;;
  python) export PYTHONPATH="$repo_root/python"; exec uv run --project python python -m workshop.oauth "$operation" "$@" ;;
  *) echo 'Language must be go or python' >&2; exit 1;;
esac
