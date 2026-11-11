#!/usr/bin/env bash
# Eval harness inside agent-cage (LiteLLM → host Ollama).
# Modes: single (default), suite (all tasks / one model), matrix (tasks × models).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${EVAL_MODE:-single}"  # single | suite | matrix
TASK="${EVAL_TASK:-001-is-palindrome}"
BASE="${OPENAI_BASE_URL:-http://host.docker.internal:11435/v1}"
# EVAL_MODEL, else LITELLM_SMOKE_MODEL, else model_choice for this mode.
# The cage copy of this script may not have pfylib; the host Makefile resolves
# first and passes EVAL_MODEL in. A cloud choice is refused (Ollama only).
if [ -z "${EVAL_MODEL:-}" ] && [ -z "${LITELLM_SMOKE_MODEL:-}" ]; then
  _task=eval-suite
  if [ "$MODE" = "matrix" ]; then
    _task=matrix
  fi
  _root="$(cd "$SCRIPT_DIR/../.." && pwd)"
  if [ -f "$_root/pfylib/model_choice.py" ]; then
    _got="$(cd "$_root" && python3 -m pfylib.model_choice resolve "$_task" --field model --transport ollama || true)"
    if [ -n "$_got" ]; then
      EVAL_MODEL="$_got"
    fi
  fi
  unset _task _root _got
fi
MODEL="${EVAL_MODEL:-${LITELLM_SMOKE_MODEL:-qwen2.5:14b}}"
# Matrix default: capable coders present on this lab host (missing → SKIP cell)
MODELS="${EVAL_MODELS:-qwen2.5:14b,codestral:22b,deepseek-coder:6.7b-instruct}"
VENV="${EVAL_VENV:-/workspace/.venvs/eval-harness}"

export EVAL_MODE="$MODE"
export EVAL_MODEL="$MODEL"
export EVAL_MODELS="$MODELS"
export EVAL_GATE_MODEL="${EVAL_GATE_MODEL:-$MODEL}"
export OPENAI_BASE_URL="$BASE"

echo "== eval-harness mode=$MODE =="
echo "  base=$BASE model=$MODEL models=$MODELS gate=$EVAL_GATE_MODEL"

HOST_ROOT="${BASE%/v1}"
# Bypass cage HTTP_PROXY (mitm 403/empty for urllib/curl default proxy)
curl -sS -m 15 --noproxy '*' "${HOST_ROOT}/api/tags" -o /tmp/ollama-tags-eval.json
python3 - <<PY
import json, os, sys
raw = open("/tmp/ollama-tags-eval.json").read().strip()
if not raw or raw[0] not in "{[":
    print("error: non-JSON from Ollama tags; check OPENAI_BASE_URL and gateway", file=sys.stderr)
    print(raw[:200], file=sys.stderr)
    sys.exit(2)
d = json.loads(raw)
names = [m.get("name") for m in (d.get("models") or [])]
mode = os.environ.get("EVAL_MODE", "single")
if mode == "matrix":
    want_list = [m.strip() for m in os.environ.get("EVAL_MODELS", "").split(",") if m.strip()]
    if not want_list:
        want_list = [os.environ.get("EVAL_MODEL", "qwen2.5:14b")]
    missing = [w for w in want_list if w not in names]
    print(f"  ollama models: {len(names)}; matrix want={want_list}; missing={missing or 'none'}")
    gate = os.environ.get("EVAL_GATE_MODEL") or want_list[0]
    if gate not in names:
        print(f"error: gate model {gate!r} not on Ollama — pull on host or re-run make eval-select-models", file=sys.stderr)
        sys.exit(2)
else:
    want = os.environ.get("EVAL_MODEL") or os.environ.get("LITELLM_SMOKE_MODEL", "qwen2.5:14b")
    if want not in names:
        print(f"error: model {want!r} not on Ollama — pull on host or re-run make eval-select-models", file=sys.stderr)
        sys.exit(2)
    print(f"  ollama models: {len(names)}; {want}: yes")
PY

if [[ ! -x "${VENV}/bin/python" ]]; then
  mkdir -p "$(dirname "$VENV")"
  python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "${VENV}/bin/activate"
python -m pip install -q --upgrade pip
python -c "import litellm" 2>/dev/null || python -m pip install -q "litellm>=1.40.0"

export LITELLM_SMOKE_MODEL="$MODEL"
export EVAL_RESULT_JSON="${EVAL_RESULT_JSON:-/tmp/eval-result.json}"

cd "${SCRIPT_DIR}"
case "$MODE" in
  single)
    export EVAL_RESULT_JSON="${EVAL_RESULT_JSON:-/tmp/eval-tier1-result.json}"
    python "${SCRIPT_DIR}/run_scored_task.py" --task "$TASK" --tasks-root "${SCRIPT_DIR}/tasks"
    ;;
  suite)
    export EVAL_MATRIX_MD="${EVAL_MATRIX_MD:-/tmp/eval-suite.md}"
    python "${SCRIPT_DIR}/run_suite.py" \
      --tasks-root "${SCRIPT_DIR}/tasks" \
      --models "$MODEL" \
      --gate-model "$EVAL_GATE_MODEL"
    ;;
  matrix)
    export EVAL_MATRIX_MD="${EVAL_MATRIX_MD:-/tmp/eval-matrix.md}"
    python "${SCRIPT_DIR}/run_suite.py" \
      --tasks-root "${SCRIPT_DIR}/tasks" \
      --models "$MODELS" \
      --gate-model "$EVAL_GATE_MODEL"
    ;;
  *)
    echo "error: unknown EVAL_MODE=$MODE (single|suite|matrix)" >&2
    exit 1
    ;;
esac
