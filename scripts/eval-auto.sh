#!/usr/bin/env bash
# T-0074 eval-auto: structural always; implement ladder if Ollama up.
set -euo pipefail
# mktemp with no template honors TMPDIR. A template that already names a directory does not.
exports_file() { mktemp; }
if [[ "${1:-}" == "--exports-path" ]]; then
  exports_file
  exit 0
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p pipelines/eval

python3 examples/eval-harness/run_structural.py --write-md pipelines/eval/structural.latest.md

if ! curl -sf --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  if [[ "${EVAL_AUTO_REQUIRE_OLLAMA:-0}" == "1" ]]; then
    echo "eval-auto: Ollama required but unreachable" >&2
    exit 1
  fi
  cat > pipelines/eval/eval-auto.latest.md <<MD
# eval-auto soft-skip $(date -u +%Y-%m-%dT%H:%M:%SZ)
status: soft-skip
reason: Ollama not on :11434
note: structural green; set EVAL_AUTO_REQUIRE_OLLAMA=1 to hard-fail
MD
  echo "eval-auto: SOFT-SKIP (Ollama not on :11434) — structural already green"
  exit 0
fi

./examples/litellm-ollama/host-ollama-gateway.sh start 2>/dev/null || true
python3 examples/eval-harness/select_ollama_models.py --pull-gate
exports=$(exports_file)
python3 examples/eval-harness/select_ollama_models.py --exports 2>/dev/null \
  | grep -E '^(EVAL_|LITELLM_)' > "$exports"
echo "==> using selected models:"; cat "$exports"
set -a
# shellcheck disable=SC1091
source "$exports"
set +a
mapfile -t arr < <(python3 scripts/eval_auto_candidates.py)
ok=0
tried=""
for g in "${arr[@]}"; do
  [[ -z "$g" ]] && continue
  tried="${tried:+$tried,}$g"
  echo "==> eval-v02 gate candidate: $g"
  if make eval-v02 \
    EVAL_MODEL="$g" EVAL_GATE_MODEL="$g" \
    EVAL_MODELS="${EVAL_MODELS:-}" \
    LITELLM_SMOKE_MODEL="${LITELLM_SMOKE_MODEL:-deepseek-coder:latest}"; then
    ok=1
    echo "eval-auto: PASS with gate $g"
    cat > pipelines/eval/eval-auto.latest.md <<MD
# eval-auto pass $(date -u +%Y-%m-%dT%H:%M:%SZ)
status: pass
gate: $g
tried: $tried
note: structural green, then this gate passed
MD
    break
  fi
  echo "eval-auto: gate $g failed — try next candidate"
done
if [[ $ok -ne 1 ]]; then
  cat > pipelines/eval/eval-auto.latest.md <<MD
# eval-auto fail $(date -u +%Y-%m-%dT%H:%M:%SZ)
status: fail
tried: ${tried:-"(none)"}
note: structural green; every gate candidate failed
MD
  echo "eval-auto: all gate candidates failed" >&2
  exit 1
fi
