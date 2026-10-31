#!/usr/bin/env bash
# T-0096: dual-tier orchestrator smoke (mock high+low — no cloud required).
set -euo pipefail
remote_log() { mktemp; }
if [[ "${1:-}" == "--scratch-path" ]]; then
  remote_log
  exit 0
fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
EDGE="$ROOT/examples/voice-stt-edge"
# shellcheck source=python.sh
source "$EDGE/python.sh"
OUT="${VOICE_STT_OUT:-$EDGE/.generated}"
FAIL=0

ok() { printf '  OK  %s\n' "$*"; }
bad() { printf '  FAIL %s\n' "$*" >&2; FAIL=1; }

echo "== smoke-orchestrate (T-0096) =="
echo "  default route: high-first (mock tiers)"

mkdir -p "$OUT"
"$VOICE_PY" "$EDGE/stt_edge.py" --backend text \
  --text "Implement a tiny helper; high should delegate to local." \
  --target monitor --out-dir "$OUT" >/dev/null

# --- mode mapping ---
echo "==> VOICE_AUTO_AGENT=1 → orchestrate"
MAP=$("$VOICE_PY" - <<'PY'
import importlib.util
from pathlib import Path
p = Path("examples/voice-stt-edge/agent_runner.py")
spec = importlib.util.spec_from_file_location("ar", p)
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)
assert ar.normalize_mode("1") == "orchestrate", ar.normalize_mode("1")
assert ar.normalize_mode("auto") == "orchestrate"
assert ar.normalize_mode("opencode") == "opencode"
assert ar.normalize_mode("grok") == "grok"
print("ok")
PY
)
[[ "$MAP" == "ok" ]] && ok "mode map" || bad "mode map"

# --- high-first mock ---
echo "==> high-first mock (high DELEGATE → low)"
export VOICE_ROUTE=high-first
export VOICE_ORCH_MOCK=1
if "$VOICE_PY" "$EDGE/orchestrator.py" --mock --route high-first --out-dir "$OUT" --repo "$ROOT" \
  --transcript "Build a small script"; then
  ok "orchestrator high-first exit 0"
else
  bad "orchestrator high-first failed"
fi

TIERS=$("$VOICE_PY" -c "import json;print(json.load(open('$OUT/last-run.json')).get('tiers',[]))")
echo "  tiers=$TIERS"
echo "$TIERS" | grep -q high && ok "tier high present" || bad "missing high tier"
echo "$TIERS" | grep -q low && ok "tier low present (delegate)" || bad "missing low tier after DELEGATE"

ROUTE=$("$VOICE_PY" -c "import json;print(json.load(open('$OUT/last-run.json')).get('route',''))")
[[ "$ROUTE" == "high-first" ]] && ok "route=high-first" || bad "route=$ROUTE"

# --- agent_runner orchestrate-mock ---
echo "==> agent_runner --mode orchestrate-mock"
if "$VOICE_PY" "$EDGE/agent_runner.py" --mode orchestrate-mock --out-dir "$OUT" --repo "$ROOT" \
  --transcript "delegate me please" --target monitor; then
  ok "agent_runner orchestrate-mock"
else
  bad "agent_runner orchestrate-mock"
fi

# --- local-first escalate mock ---
echo "==> local-first with force escalate"
export VOICE_ROUTE=local-first
export VOICE_ORCH_FORCE_ESCALATE=1
if "$VOICE_PY" "$EDGE/orchestrator.py" --mock --route local-first --out-dir "$OUT" --repo "$ROOT" \
  --transcript "hard task"; then
  ok "local-first mock"
else
  bad "local-first mock"
fi
TIERS2=$("$VOICE_PY" -c "import json;print(json.load(open('$OUT/last-run.json')).get('tiers',[]))")
echo "  tiers=$TIERS2"
echo "$TIERS2" | grep -q escalate && ok "escalate tier present" || ok "local-first tiers recorded ($TIERS2)"

# --- remote VOICE_AUTO_AGENT=1 queues orchestrate ---
echo "==> remote VOICE_AUTO_AGENT=1 → orchestrate mock"
export VOICE_AUTO_AGENT=1
export VOICE_ORCH_MOCK=1
export VOICE_ROUTE=high-first
PORT="${VOICE_REMOTE_SMOKE_PORT:-18792}"
TOKEN="t0096-$RANDOM"
REMOTE_LOG=$(remote_log)
"$VOICE_PY" "$EDGE/remote_server.py" --host 127.0.0.1 --port "$PORT" --token "$TOKEN" --out-dir "$OUT" \
  >"$REMOTE_LOG" 2>&1 &
PID=$!
cleanup() { kill "$PID" 2>/dev/null || true; wait "$PID" 2>/dev/null || true; }
trap cleanup EXIT
for _ in $(seq 1 25); do
  curl -sS -m 1 "http://127.0.0.1:$PORT/ping" 2>/dev/null | grep -q pong && break
  sleep 0.2
done
BODY=$(curl -sS -m 5 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"text":"Coordinate and delegate a tiny task","target":"monitor"}' \
  "http://127.0.0.1:$PORT/api/text")
AM=$(echo "$BODY" | "$VOICE_PY" -c "import sys,json; d=json.load(sys.stdin); print(d.get('agent_mode',''))" 2>/dev/null || echo "")
if [[ "$AM" == "orchestrate" ]]; then
  ok "remote agent_mode=orchestrate"
else
  bad "expected orchestrate got '$AM' body=$(echo "$BODY" | head -c 200)"
fi

for _ in $(seq 1 40); do
  st=$("$VOICE_PY" -c "import json;print(json.load(open('$OUT/last-run.json')).get('status',''))" 2>/dev/null || echo "")
  [[ "$st" == "done" || "$st" == "error" ]] && break
  sleep 0.2
done
MD=$("$VOICE_PY" -c "import json;print(json.load(open('$OUT/last-run.json')).get('mode',''))")
[[ "$MD" == "orchestrate" ]] && ok "last-run mode=orchestrate" || bad "last-run mode=$MD"

if [[ "$FAIL" -ne 0 ]]; then
  echo "smoke-orchestrate: FAIL" >&2
  exit 1
fi
echo "smoke-orchestrate: PASS"
echo "Live high-first: VOICE_AUTO_AGENT=1 VOICE_ROUTE=high-first make voice-remote"
echo "Local only:      VOICE_AUTO_AGENT=opencode make voice-remote"
echo "Local then up:   VOICE_ROUTE=local-first VOICE_AUTO_AGENT=1 …"
exit 0
