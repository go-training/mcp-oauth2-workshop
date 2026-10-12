#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
lab="${1:-01}"
language="${2:-go}"
case "$lab" in 01|02|03|04|05|06) ;; *) echo 'Lab must be 01..06' >&2; exit 1;; esac
case "$language" in
  go) cd "$repo_root/go"; exec go run "./labs/$lab" ;;
  python) export PYTHONPATH="$repo_root/python"; exec uv run --project "$repo_root/python" --frozen python "$repo_root/python/labs/$lab/main.py" ;;
  *) echo 'Language must be go or python' >&2; exit 1;;
esac
