#!/usr/bin/env bash
# T-0093: tools-model select/probe smoke (host Ollama).
set -euo pipefail
sel_json() { mktemp; }
sel_err() { mktemp; }
if [[ "${1:-}" == "--scratch-path" ]]; then
  sel_json
  sel_err
  exit 0
fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
FAIL=0

ok() { printf '  OK  %s\n' "$*"; }
bad() { printf '  FAIL %s\n' "$*" >&2; FAIL=1; }

echo "== smoke-tools-model (T-0093) =="

SEL_JSON=$(sel_json)
SEL_ERR=$(sel_err)
export SEL_JSON SEL_ERR
if ! "$PY" examples/eval-harness/select_tools_model.py --json > "$SEL_JSON" 2>"$SEL_ERR"; then
  if grep -qi 'cannot reach Ollama\|no Ollama\|ollama_unreachable' "$SEL_ERR" "$SEL_JSON" 2>/dev/null; then
    echo "  SKIP Ollama unreachable (start ollama on host for full probe)"
    # structural: script importable
    "$PY" -m py_compile examples/eval-harness/select_tools_model.py && ok "select_tools_model.py compiles"
    test -f docs/ops/local-tools-split.md && ok "local-tools-split.md present"
    echo "smoke-tools-model: PASS (structural; Ollama skip)"
    exit 0
  fi
  bad "select_tools_model failed"
  cat "$SEL_ERR" | tail -20
  exit 1
fi

MODE=$("$PY" -c 'import json,os; print(json.load(open(os.environ["SEL_JSON"])).get("tools_mode",""))')
CODER=$("$PY" -c 'import json,os; print(json.load(open(os.environ["SEL_JSON"])).get("LOCAL_CODER_MODEL",""))')
TOOLS=$("$PY" -c 'import json,os; print(json.load(open(os.environ["SEL_JSON"])).get("LOCAL_TOOLS_MODEL",""))')

echo "  tools_mode=$MODE"
echo "  LOCAL_CODER_MODEL=$CODER"
echo "  LOCAL_TOOLS_MODEL=${TOOLS:-'(none)'}"

if [[ "$MODE" == "local_tools" || "$MODE" == "split" ]]; then
  ok "tools_mode=$MODE"
else
  bad "unexpected tools_mode=$MODE"
fi

if [[ -f examples/opencode-ollama/.generated/tools-model.env ]]; then
  ok "tools-model.env written"
  grep -q TOOLS_MODE= examples/opencode-ollama/.generated/tools-model.env && ok "TOOLS_MODE in env file"
else
  bad "tools-model.env missing"
fi

test -f docs/ops/local-tools-split.md && ok "docs present" || bad "docs missing"

if [[ "$FAIL" -ne 0 ]]; then
  echo "smoke-tools-model: FAIL" >&2
  exit 1
fi
echo "smoke-tools-model: PASS"
if [[ "$MODE" == "split" ]]; then
  echo "  Tip: ollama pull qwen2.5-coder:7b-instruct && make eval-select-tools-model"
fi
exit 0
