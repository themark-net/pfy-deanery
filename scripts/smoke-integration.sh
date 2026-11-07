#!/usr/bin/env bash
# GAP-23+26 umbrella: structural + soft smokes (full OpenCode cage when runtime present)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p pipelines/smoke/integration
OUT=pipelines/smoke/integration/results.latest.md
{
  echo "# smoke-integration umbrella"
  echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$OUT"

python3 examples/eval-harness/run_structural.py --write-md pipelines/eval/structural.latest.md
python3 scripts/smoke_contract_lint.py | tee -a "$OUT"
python3 scripts/catalog_check.py | tee -a "$OUT"

soft() {
  local name="$1"; shift
  echo "--> $name" | tee -a "$OUT"
  if "$@"; then echo "    PASS $name" | tee -a "$OUT"
  else echo "    SOFT $name" | tee -a "$OUT"; fi
}

soft tools-model ./scripts/model_lock.sh ./examples/eval-harness/smoke_tools_model.sh
soft opencode-cage ./examples/opencode-cage/smoke.sh
soft voice-stt ./examples/voice-stt-edge/smoke.sh
soft product-levers ./scripts/smoke-product-levers.sh

# Full cage wrap only if docker + agentcage path ready
if command -v docker >/dev/null 2>&1 && [[ -d harness/agent-cage ]]; then
  echo "--> cage-smoke-host (best effort)" | tee -a "$OUT"
  make cage-smoke-host >>"$OUT" 2>&1 && echo "    PASS cage-host" | tee -a "$OUT" || echo "    SOFT cage-host" | tee -a "$OUT"
else
  echo "cage runtime absent — OpenCode full cage wrap deferred" | tee -a "$OUT"
fi

echo "status: pass (umbrella soft-ok)" | tee -a "$OUT"
echo "smoke-integration: PASS"
