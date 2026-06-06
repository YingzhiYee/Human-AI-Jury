#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v rg >/dev/null 2>&1; then
  echo "rg is required for secret scanning."
  exit 1
fi

PATTERN='(sk-(?!test-placeholder)[A-Za-z0-9_-]{20,}|BSAAf3et[A-Za-z0-9_-]*|OPENAI_API_KEY\s*=\s*["'"'"']?sk-(?!test-placeholder)|XAPI_TOKEN\s*=\s*["'"'"']?sk-(?!test-placeholder)|BRAVE_API_KEY\s*=\s*["'"'"']?[A-Za-z0-9_-]{16,})'

EXCLUDES=(
  --glob '!.env'
  --glob '!.env.*'
  --glob '!.venv/**'
  --glob '!.venv312/**'
  --glob '!frontend/node_modules/**'
  --glob '!frontend/dist/**'
  --glob '!.git/**'
  --glob '!scripts/scan_secrets.sh'
)

echo "Scanning tracked and local workspace files for likely secrets..."
if rg -n --pcre2 --hidden "${EXCLUDES[@]}" "$PATTERN" "$ROOT_DIR"; then
  echo
  echo "Potential secret detected. Review the file before committing or pushing."
  exit 1
fi

echo "No likely secrets found in the workspace scan."
