#!/usr/bin/env bash
# GAP-09 dual-sided product onboard smoke
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p pipelines/smoke/product-levers
OUT=pipelines/smoke/product-levers/results.latest.md
TMP=$(mktemp -d /tmp/pfy-product-XXXXXX)
trap 'rm -rf "$TMP"' EXIT
{
  echo "# Product levers smoke"
  echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "tmp: $TMP"
} >"$OUT"
help_out=$(make help)
printf '%s\n' "$help_out" | grep -q 'make product-ship' || { echo "FAIL help missing product-ship"; exit 1; }
printf '%s\n' "$help_out" | grep -q 'make help-platform' || { echo "FAIL help missing help-platform"; exit 1; }
if printf '%s\n' "$help_out" | grep -E -q 'cage-grok|eval-structural|smoke-'; then
  echo "FAIL help still lists platform targets"
  exit 1
fi
plat_out=$(make help-platform)
printf '%s\n' "$plat_out" | grep -q 'cage-grok' || { echo "FAIL help-platform missing cage-grok"; exit 1; }
printf '%s\n' "$plat_out" | grep -q 'eval-structural' || { echo "FAIL help-platform missing eval-structural"; exit 1; }
chmod +x scripts/product-onboard.sh
DIR="$TMP" ./scripts/product-onboard.sh "$TMP" | tee -a "$OUT"
python3 examples/eval-harness/run_structural.py --write-md pipelines/eval/structural.latest.md
echo "status: pass (onboard tmp + structural)" | tee -a "$OUT"
echo "smoke-product-levers: PASS"
