#!/usr/bin/env bash
# T-0091 phase 1: voice STT edge smoke (host). No mic / no Whisper required.
#
# Proves:
#   1. stt_edge.py runs (mock + text backends)
#   2. Artifacts: last-transcript.txt, agent-prompt.md, handoff.sh, last-meta.json
#   3. Prompt is wrapped for monitor (tools language) and worker targets
#   4. Optional: real STT backend probe (SKIP, not FAIL, if missing)
#
# Exit: 0 PASS · 1 FAIL
set -euo pipefail
probe_log() { mktemp; }
if [[ "${1:-}" == "--scratch-path" ]]; then
  probe_log
  exit 0
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
EDGE="$ROOT/examples/voice-stt-edge"
OUT="${VOICE_STT_OUT:-$EDGE/.generated}"
RESULT_MD="${VOICE_STT_RESULT:-$ROOT/pipelines/smoke/voice-stt-edge/results.latest.md}"
# Wiring smoke uses system python3 (mock/text only). Real STT uses .venv via python.sh.
# shellcheck source=python.sh
source "$EDGE/python.sh" 2>/dev/null || true
PY="${VOICE_PY:-${PYTHON:-python3}}"
FAIL=0

log() { printf '==> %s\n' "$*"; }
ok() { printf '  OK  %s\n' "$*"; }
bad() { printf '  FAIL %s\n' "$*" >&2; FAIL=1; }

echo "== voice-stt-edge smoke (T-0091 p1) =="
echo "  OUT=$OUT"
echo "  MODE=wiring only (mock + text) — does NOT record mic or run Whisper"
echo "  Real mic: make voice-stt-install && make voice-listen"

mkdir -p "$OUT" "$(dirname "$RESULT_MD")"
rm -f "$OUT/last-transcript.txt" "$OUT/agent-prompt.md" "$OUT/handoff.sh" "$OUT/last-meta.json" "$OUT/STT-NEEDED.txt"

# --- 1) CLI exists ---
log "CLI present"
if [[ ! -f "$EDGE/stt_edge.py" ]]; then
  bad "missing $EDGE/stt_edge.py"
  exit 1
fi
ok "stt_edge.py"

# --- 2) mock backend → monitor wrap ---
log "mock backend → monitor prompt"
if ! "$PY" "$EDGE/stt_edge.py" --backend mock --target monitor --out-dir "$OUT" >"$OUT/smoke-stdout.txt"; then
  bad "mock backend failed"
else
  ok "mock run"
fi

if [[ ! -s "$OUT/last-transcript.txt" ]]; then
  bad "last-transcript.txt missing/empty"
else
  if grep -qi 'smoke-opencode-ollama' "$OUT/last-transcript.txt"; then
    ok "transcript has fixture intent"
  else
    bad "transcript missing expected fixture phrase"
  fi
fi

if [[ ! -s "$OUT/agent-prompt.md" ]]; then
  bad "agent-prompt.md missing"
else
  for needle in "Voice → agent prompt" "Spoken intent" "tools" "monitor"; do
    if grep -qi "$needle" "$OUT/agent-prompt.md"; then
      ok "prompt contains: $needle"
    else
      bad "prompt missing: $needle"
    fi
  done
fi

if [[ ! -x "$OUT/handoff.sh" ]]; then
  bad "handoff.sh missing or not executable"
else
  if grep -q 'grok' "$OUT/handoff.sh" && grep -q 'opencode' "$OUT/handoff.sh"; then
    ok "handoff.sh mentions grok + opencode"
  else
    bad "handoff.sh incomplete"
  fi
fi

if [[ ! -s "$OUT/last-meta.json" ]]; then
  bad "last-meta.json missing"
else
  ok "last-meta.json"
fi

# stdout should be clean transcript only
if grep -qi 'smoke-opencode-ollama' "$OUT/smoke-stdout.txt"; then
  ok "stdout is transcript"
else
  bad "stdout missing transcript"
fi

# --- 3) text backend → worker wrap ---
log "text backend → worker prompt"
WORKER_TXT="Implement the DoD in monitor-brief and run make eval-structural"
if ! "$PY" "$EDGE/stt_edge.py" --backend text --text "$WORKER_TXT" --target worker --out-dir "$OUT" >/dev/null; then
  bad "text→worker failed"
else
  if grep -q 'OpenCode \*\*worker\*\*' "$OUT/agent-prompt.md" || grep -qi 'worker' "$OUT/agent-prompt.md"; then
    ok "worker-targeted prompt"
  else
    bad "worker prompt not wrapped"
  fi
  if grep -F "$WORKER_TXT" "$OUT/last-transcript.txt" >/dev/null; then
    ok "worker transcript exact"
  else
    bad "worker transcript mismatch"
  fi
fi

# --- 4) raw target (in subdir so we do not leave "ping" as the operator handoff) ---
log "raw target (isolated)"
RAW_OUT="$OUT/raw-check"
mkdir -p "$RAW_OUT"
if ! "$PY" "$EDGE/stt_edge.py" --backend text --text "ping" --target raw --out-dir "$RAW_OUT" >/dev/null; then
  bad "raw target failed"
else
  if [[ "$(tr -d '\n' <"$RAW_OUT/agent-prompt.md")" == "ping" ]]; then
    ok "raw prompt is transcript only"
  else
    bad "raw prompt has wrapper: $(head -c 80 "$RAW_OUT/agent-prompt.md")"
  fi
fi

# --- 5) leave monitor-targeted fixture as the default handoff (not smoke ping) ---
log "restore monitor fixture as default handoff"
if ! "$PY" "$EDGE/stt_edge.py" --backend mock --target monitor --out-dir "$OUT" >/dev/null; then
  bad "final mock restore failed"
else
  ok "default handoff = mock fixture → monitor (not raw ping)"
fi

# --- 6) optional real STT probe (informational) ---
log "optional real STT probe (does not fail smoke)"
STT_NOTE="none"
PROBE_RC=0
PROBE_LOG=$(probe_log)
"$PY" "$EDGE/stt_edge.py" --probe >"$PROBE_LOG" 2>&1 || PROBE_RC=$?
if [[ "$PROBE_RC" -eq 0 ]]; then
  STT_NOTE="real STT ready (local or OPENAI_API_KEY)"
  ok "real STT ready — try: make voice-listen"
else
  STT_NOTE="no real STT — mock/text only (install: make voice-stt-install)"
  ok "no Whisper required for this smoke (expected until voice-stt-install)"
fi
cat "$PROBE_LOG" 2>/dev/null | sed 's/^/  | /' || true

# --- result receipt ---
STATUS=PASS
[[ "$FAIL" -eq 0 ]] || STATUS=FAIL
{
  echo "# voice-stt-edge smoke"
  echo ""
  echo "- **When:** $(date -Iseconds 2>/dev/null || date)"
  echo "- **Status:** $STATUS"
  echo "- **Mode:** wiring only (mock/text) — **no mic**"
  echo "- **Out:** \`$OUT\`"
  echo "- **Real STT probe:** $STT_NOTE"
  echo "- **Phase:** T-0091 p1"
  echo ""
  echo "Real mic path: \`make voice-stt-install && make voice-listen\`"
} >"$RESULT_MD"
echo "==> wrote $RESULT_MD"

if [[ "$FAIL" -ne 0 ]]; then
  echo "voice-stt-edge smoke: FAIL" >&2
  exit 1
fi
echo "voice-stt-edge smoke: PASS (wiring only — did not record audio)"
echo ""
echo "Real mic (host):"
echo "  make voice-stt-install     # once: .venv + faster-whisper (PEP 668 safe)"
echo "  make voice-listen          # mic → STT → handoff artifacts"
echo "  examples/voice-stt-edge/.generated/handoff.sh"
echo "If you already recorded last-capture.wav without STT:"
echo "  make voice-stt-install"
echo "  examples/voice-stt-edge/python.sh examples/voice-stt-edge/stt_edge.py \\"
echo "    --audio examples/voice-stt-edge/.generated/last-capture.wav \\"
echo "    --backend local --target monitor"
exit 0
