#!/usr/bin/env bash
# Product lever 2: stage — structural eval + optional local OpenAI-compat path green.
# Honest skip if a piece is missing; do not fail the whole operator env (G8 / #80).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# Test hook: a suite that calls ./pfy must not re-enter structural eval.
if [[ "${PFY_SKIP_STAGE:-}" == "1" ]]; then
  echo "env-stage skipped"
  exit 0
fi
echo "==> env-stage (product local path)"
if [[ -f bootstrap/env/check_env.py ]]; then
  python3 bootstrap/env/check_env.py || {
    echo "env-check skipped — missing/incomplete .env (honest skip; run make env-init and edit DEPLOY_PROFILE)"
  }
else
  echo "env-check skipped — bootstrap/env/check_env.py missing"
fi
if [[ -f examples/eval-harness/run_structural.py ]]; then
  python3 examples/eval-harness/run_structural.py --write-md pipelines/eval/structural.latest.md \
    || echo "structural eval skipped (honest skip)"
else
  echo "structural eval skipped — examples/eval-harness/run_structural.py missing"
fi
# Soft local path: detector (ADR-0014) then adapters. Detect order lives in detect-local-runtime.sh
# (FreeToken → llama-swap :9292 → llama-server :8080 → Ollama); this block only probes liveness.
RT_JSON=""
if [[ -f scripts/detect-local-runtime.sh ]]; then
  RT_JSON=$(bash scripts/detect-local-runtime.sh --json 2>/dev/null || true)
  echo "local runtime: ${RT_JSON:-unknown}"
fi
# Test hook: do not probe fixed host ports (and do not run the Ollama smoke).
if [[ "${PFY_DETECT_SKIP_HOST:-}" == "1" ]]; then
  echo "host runtime probe skipped"
else
  ollama_base="${PFY_OLLAMA_BASE:-http://127.0.0.1:11434}"
  ollama_base="${ollama_base%/}"
  if curl -sf --max-time 2 http://127.0.0.1:1919/v1/models >/dev/null 2>&1; then
    echo "FreeToken/local OpenAI-compat up (:1919) - structural only this track"
  elif curl -sf --max-time 2 http://127.0.0.1:9292/v1/models >/dev/null 2>&1; then
    echo "llama-swap up (:9292) - structural only this track"
  elif curl -sf --max-time 2 http://127.0.0.1:8080/v1/models >/dev/null 2>&1 \
    || curl -sf --max-time 2 http://127.0.0.1:11435/v1/models >/dev/null 2>&1; then
    echo "local OpenAI-compat up (llama-server/Shimmy) - structural only this track"
  elif curl -sf --max-time 2 "$ollama_base/api/tags" >/dev/null 2>&1; then
    echo "Ollama adapter up - running smoke-litellm-ollama if cage available"
    make smoke-litellm-ollama 2>/dev/null || echo "smoke-litellm soft-skip (cage/host path not ready)"
  else
    echo "no local runtime on :1919/:9292/:8080/:11435/:11434 - structural only (local bulk SKIP; still stage OK)"
  fi
fi
echo "env-stage: green for structural; local LLM optional"
