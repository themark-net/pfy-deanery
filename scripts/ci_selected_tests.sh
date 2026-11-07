#!/usr/bin/env bash
# One unittest run for the current commit: select, optionally reuse the
# pregate cache, run scripts/run_tests.py on that list (or nothing when the
# mode is structural or none).
#
#   PFY_CI_EVENT   github.event_name (push, pull_request, workflow_dispatch)
#   PFY_CI_REF     github.ref
#   PFY_CI_BEFORE  github.event.before (push to main)
#   PFY_CI_USE_CACHE  1 on the self-hosted nimo job, 0 on ubuntu
set -euo pipefail
cd "$(dirname "$0")/.."

EVENT="${PFY_CI_EVENT:-}"
REF="${PFY_CI_REF:-}"
BEFORE="${PFY_CI_BEFORE:-}"
USE_CACHE="${PFY_CI_USE_CACHE:-0}"
ZERO="0000000000000000000000000000000000000000"

git fetch --no-tags origin main
if [[ "$EVENT" == "push" && "$REF" == "refs/heads/main" && -n "$BEFORE" && "$BEFORE" != "$ZERO" ]]; then
  if ! git cat-file -e "${BEFORE}^{commit}" 2>/dev/null; then
    git fetch --no-tags origin "$BEFORE" || git fetch --no-tags --unshallow origin
  fi
  BASE="$BEFORE"
else
  if ! BASE="$(git merge-base HEAD origin/main 2>/dev/null)"; then
    git fetch --no-tags --unshallow origin || git fetch --no-tags --depth=500 origin main
    BASE="$(git merge-base HEAD origin/main)"
  fi
fi

SEL="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/pfy-selection.json"
python3 scripts/test_select.py --base "$BASE" --head HEAD >"$SEL"
MODE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["mode"])' "$SEL")"
COUNT="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["modules"]))' "$SEL")"
echo "selection mode=$MODE modules=$COUNT base=$BASE"

if [[ "$USE_CACHE" == "1" ]]; then
  if python3 scripts/test_cache.py check --need "$MODE"; then
    KEY="$(python3 scripts/test_cache.py key)"
    echo "cache hit $KEY from pregate"
    exit 0
  fi
fi

if [[ "$MODE" == "none" || "$MODE" == "structural" ]]; then
  echo "no unittest modules (mode=$MODE)"
  python3 scripts/test_select.py --structural-checks --selection "$SEL"
  if [[ "$USE_CACHE" == "1" ]]; then
    python3 scripts/test_cache.py record --selection "$SEL"
  fi
  exit 0
fi

mapfile -t MODS < <(python3 -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["modules"]))' "$SEL")
if [[ ${#MODS[@]} -eq 0 ]]; then
  # An empty argv would make run_tests.py run every module. Refuse that.
  echo "selection mode=$MODE produced no modules"
  exit 1
fi
RECEIPT="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/pfy-tests-receipt.json"
python3 scripts/run_tests.py --receipt "$RECEIPT" "${MODS[@]}"
if [[ "$USE_CACHE" == "1" ]]; then
  python3 scripts/test_cache.py record --selection "$SEL" --receipt "$RECEIPT"
fi
