#!/usr/bin/env bash
# T-0091 p4a: remote voice edge smoke (host). No phone required.
set -euo pipefail
scratch_dir() { mktemp -d; }
if [[ "${1:-}" == "--scratch-path" ]]; then
  scratch_dir
  exit 0
fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
EDGE="$ROOT/examples/voice-stt-edge"
# shellcheck source=python.sh
source "$EDGE/python.sh"
OUT="${VOICE_STT_OUT:-$EDGE/.generated}"
PORT="${VOICE_REMOTE_SMOKE_PORT:-18787}"
TOKEN="smoke-token-$(date +%s)"
HOST="127.0.0.1"
FAIL=0

log() { printf '==> %s\n' "$*"; }
ok() { printf '  OK  %s\n' "$*"; }
bad() { printf '  FAIL %s\n' "$*" >&2; FAIL=1; }

echo "== voice-remote smoke (T-0091 p4a) =="
echo "  MODE=localhost HTTP + /api/text (no mic, no Tailscale required)"

mkdir -p "$OUT"
SCRATCH=$(scratch_dir)
export SCRATCH
# start server
"$VOICE_PY" "$EDGE/remote_server.py" --host "$HOST" --port "$PORT" --token "$TOKEN" --out-dir "$OUT" \
  >"$SCRATCH/voice-remote-smoke.log" 2>&1 &
PID=$!
cleanup() { kill "$PID" 2>/dev/null || true; wait "$PID" 2>/dev/null || true; rm -rf "$SCRATCH"; }
trap cleanup EXIT

# wait for health
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sS -m 1 "http://$HOST:$PORT/health" >$SCRATCH/vr-health.json 2>/dev/null; then
    break
  fi
  sleep 0.3
done

log "ping"
PING=$(curl -sS -m 2 "http://$HOST:$PORT/ping" || true)
if [[ "$PING" == "pong" || "$PING" == $'pong\n' ]]; then
  ok "ping → pong"
else
  bad "ping: '$PING'"
fi

log "health"
if grep -q '"ok": true' $SCRATCH/vr-health.json 2>/dev/null || grep -q '"ok":true' $SCRATCH/vr-health.json 2>/dev/null; then
  ok "health"
else
  # health may not have been fetched if loop failed — try once
  curl -sS -m 2 "http://$HOST:$PORT/health" >$SCRATCH/vr-health.json 2>/dev/null || true
  if grep -q 'pfy-voice-remote' $SCRATCH/vr-health.json 2>/dev/null; then
    ok "health"
  else
    bad "health: $(cat $SCRATCH/vr-health.json 2>/dev/null || echo none)"
    cat $SCRATCH/voice-remote-smoke.log 2>/dev/null | tail -20 || true
  fi
fi

log "unauthorized blocked"
CODE=$(curl -sS -o $SCRATCH/vr-unauth.json -w '%{http_code}' -X POST \
  -H 'Content-Type: application/json' \
  -d '{"text":"nope","target":"monitor"}' \
  "http://$HOST:$PORT/api/text" || echo 000)
if [[ "$CODE" == "401" ]]; then
  ok "401 without token"
else
  bad "expected 401 got $CODE"
fi

log "text → artifacts"
CODE=$(curl -sS -o $SCRATCH/vr-text.json -w '%{http_code}' -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Remote smoke: run make eval-structural","target":"monitor"}' \
  "http://$HOST:$PORT/api/text" || echo 000)
if [[ "$CODE" == "200" ]] && grep -q 'Remote smoke' $SCRATCH/vr-text.json; then
  ok "api/text 200"
else
  bad "api/text code=$CODE body=$(head -c 200 $SCRATCH/vr-text.json 2>/dev/null)"
fi

if grep -q 'Remote smoke' "$OUT/last-transcript.txt" 2>/dev/null; then
  ok "last-transcript written"
else
  bad "last-transcript missing remote text"
fi

if [[ -x "$OUT/handoff.sh" ]] && grep -q 'grok' "$OUT/handoff.sh"; then
  ok "handoff.sh ready"
else
  bad "handoff incomplete"
fi

log "audio-raw (tiny silent wav → may 422; endpoint must exist)"
# minimal valid-ish wav header + silence (not for STT quality — just HTTP path)
python3 - <<'PY' >"$SCRATCH/vr-tiny.wav"
import os, wave, struct
with wave.open(os.environ["SCRATCH"] + "/vr-tiny.wav","w") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
    w.writeframes(struct.pack("<"+"h"*800, *([0]*800)))
PY
CODE=$(curl -sS -o $SCRATCH/vr-raw.json -w '%{http_code}' -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: audio/wav" \
  -H "X-Voice-Target: monitor" \
  --data-binary @"$SCRATCH/vr-tiny.wav" \
  "http://$HOST:$PORT/api/audio-raw" || echo 000)
# 200 if STT invents text, 422 if empty/silent — both prove route works
if [[ "$CODE" == "200" || "$CODE" == "422" ]]; then
  ok "audio-raw HTTP $CODE (route live)"
else
  bad "audio-raw unexpected code=$CODE $(head -c 120 $SCRATCH/vr-raw.json 2>/dev/null)"
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "voice-remote smoke: FAIL" >&2
  exit 1
fi
echo "voice-remote smoke: PASS"
echo "Phone: prefer Termux client if browser hangs — examples/voice-stt-edge/clients/"
echo "Docs: docs/ops/voice-remote-android.md · make voice-remote"
exit 0
