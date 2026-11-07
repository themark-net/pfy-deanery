#!/usr/bin/env bash
# In-cage smoke: codebase-memory-mcp CLI (index + search on fixture).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURE="${CM_FIXTURE:-${SCRIPT_DIR}/fixture}"
PROJECT_NAME="${CM_PROJECT_NAME:-pfy-mentat-cm-smoke}"
BIN_DIR="${CM_BIN_DIR:-${HOME}/.local/bin}"
export PATH="${BIN_DIR}:${PATH}"

echo "== codebase-memory-mcp in-cage smoke =="
echo "  fixture=$FIXTURE project=$PROJECT_NAME"

ensure_binary() {
  if command -v codebase-memory-mcp >/dev/null 2>&1; then
    echo "  binary: $(command -v codebase-memory-mcp)"
    codebase-memory-mcp --version
    return 0
  fi
  cache_bin="${PFY_TOOL_CACHE:-$HOME/.cache/pfy}/bin/codebase-memory-mcp"
  if [[ -x "$cache_bin" ]]; then
    export PATH="$(dirname "$cache_bin"):${PATH}"
    echo "  binary: $cache_bin"
    codebase-memory-mcp --version
    return 0
  fi
  echo "  binary missing — installing via official install.sh --skip-config"
  curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh \
    | bash -s -- --skip-config
  export PATH="${HOME}/.local/bin:${PATH}"
  command -v codebase-memory-mcp >/dev/null 2>&1 \
    || { echo "error: codebase-memory-mcp still not on PATH"; exit 1; }
  codebase-memory-mcp --version
}

ensure_binary

echo "== index fixture =="
# Prefer flags (JSON args deprecated upstream)
OUT=$(codebase-memory-mcp cli index_repository \
  --repo-path "$FIXTURE" \
  --name "$PROJECT_NAME" \
  --mode fast 2>&1) || true
echo "$OUT" | tail -20
echo "$OUT" | grep -q '"status":"indexed"' \
  || echo "$OUT" | grep -qi 'indexed' \
  || { echo "error: index did not report indexed status"; exit 1; }

echo "== list_projects =="
LP=$(codebase-memory-mcp cli list_projects 2>&1)
echo "$LP" | tail -5
echo "$LP" | grep -q "$PROJECT_NAME" \
  || { echo "error: project $PROJECT_NAME not listed"; exit 1; }

echo "== search_code pattern=greet =="
SC=$(codebase-memory-mcp cli search_code \
  --pattern greet \
  --project "$PROJECT_NAME" \
  --limit 5 2>&1)
echo "$SC" | tail -30
# Must find fixture symbol / file somehow
echo "$SC" | grep -Eiq 'greet|app\.py' \
  || { echo "error: search_code did not hit fixture symbol"; exit 1; }

echo "smoke: PASS (codebase-memory-mcp)"
