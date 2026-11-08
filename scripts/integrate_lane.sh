#!/bin/bash
# Drive one I2-to-I3 integration lane. No pull requests.
#
# The first write is tmp/integrate/<slug>.dispatched. A second start exits 2
# before fetch, worktree, grok, or push. Land with a fast-forward push of the
# worktree SHA onto origin/main. Rebase and retry when origin/main is not an
# ancestor of that SHA. Park instead of pushing when a step fails.
#
#   scripts/integrate_lane.sh --slug <slug> [--root DIR] [--date MMDD] [--ticket FILE]
#
# Do not run this against the real origin from a test. Pass --root.

set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DEFAULT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

ROOT=""
SLUG=""
DATE=""
TICKET=""

while [ $# -gt 0 ]; do
  case "$1" in
    --slug)
      SLUG=${2:-}
      shift 2
      ;;
    --root)
      ROOT=${2:-}
      shift 2
      ;;
    --date)
      DATE=${2:-}
      shift 2
      ;;
    --ticket)
      TICKET=${2:-}
      shift 2
      ;;
    *)
      printf '%s\n' "unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

if [ -z "$SLUG" ]; then
  printf '%s\n' "missing --slug" >&2
  exit 1
fi
if ! printf '%s\n' "$SLUG" | grep -E -q '^[a-z0-9][a-z0-9-]*$'; then
  printf '%s\n' "bad slug: $SLUG" >&2
  exit 1
fi
if [ -z "$ROOT" ]; then
  ROOT=$DEFAULT_ROOT
fi
if [ -z "$DATE" ]; then
  DATE=$(date -u +%m%d)
fi
if ! printf '%s\n' "$DATE" | grep -E -q '^[0-9]{4}$'; then
  printf '%s\n' "bad date: $DATE" >&2
  exit 1
fi

MARK_DIR="$ROOT/tmp/integrate"
MARKER="$MARK_DIR/${SLUG}.dispatched"
PARKED="$MARK_DIR/${SLUG}.parked"
DONE="$MARK_DIR/${SLUG}.done"
LANDED="$MARK_DIR/LANDED_${SLUG}"
PROGRESS="$MARK_DIR/progress.md"
WT="$MARK_DIR/wt/${SLUG}"
BRANCH="bot/integrate-${SLUG}-${DATE}"

# Second start: no git and no grok.
if [ -f "$MARKER" ]; then
  printf '%s\n' "already dispatched: $SLUG" >&2
  exit 2
fi

mkdir -p "$MARK_DIR"
if ! (set -o noclobber; printf '%s\n' "pid $$" > "$MARKER") 2>/dev/null; then
  printf '%s\n' "already dispatched: $SLUG" >&2
  exit 2
fi

progress() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$PROGRESS"
}

park_exit() {
  local reason="$1"
  local code="${2:-1}"
  printf '%s\n' "$reason" > "$PARKED"
  progress "$SLUG parked: $reason"
  printf '%s\n' "parked: $reason" >&2
  exit "$code"
}

if [ -f "$ROOT/tmp/STOP" ]; then
  park_exit "STOP file" 0
fi

progress "$SLUG start"

if [ -n "$TICKET" ]; then
  ticket=$TICKET
elif [ -f "$ROOT/tmp/TICKET-${SLUG}.md" ]; then
  ticket=$ROOT/tmp/TICKET-${SLUG}.md
elif [ -f "$ROOT/docs/ops/integrate/tickets/${SLUG}.md" ]; then
  ticket=$ROOT/docs/ops/integrate/tickets/${SLUG}.md
else
  park_exit "missing ticket"
fi
if [ ! -f "$ticket" ]; then
  park_exit "missing ticket"
fi

git -C "$ROOT" fetch origin >&2 || park_exit "git fetch failed"
if [ -e "$WT" ]; then
  park_exit "worktree path exists"
fi
mkdir -p "$MARK_DIR/wt"
git -C "$ROOT" worktree add -b "$BRANCH" "$WT" origin/main >&2 || park_exit "worktree add failed"
progress "$SLUG worktree $BRANCH"

(
  cd "$WT"
  python3 scripts/catalog_check.py
) || park_exit "catalog_check failed"
progress "$SLUG catalog_check ok"

(
  cd "$WT"
  python3 scripts/grill_ticket.py "$ticket"
) || park_exit "grill failed"
progress "$SLUG grill ok"

run_grok() {
  local label="$1"
  local prompt="$2"
  local log="$MARK_DIR/${SLUG}-${label}.log"
  local try=1
  while [ "$try" -le 3 ]; do
    if (
      cd "$WT"
      grok --always-approve --output-format plain --prompt-file "$prompt"
    ) >"$log" 2>&1; then
      progress "$SLUG grok $label ok"
      return 0
    fi
    progress "$SLUG grok $label attempt $try failed"
    try=$((try + 1))
  done
  tail -n 40 "$log" >&2 || true
  return 1
}

impl="$MARK_DIR/${SLUG}-implement.prompt"
review="$MARK_DIR/${SLUG}-review.prompt"
{
  printf '%s\n' "Implement the integration ticket. Follow docs/ops/INTEGRATE.md. Do not push. Do not open a pull request."
  printf '%s\n' "Ticket path: $ticket"
  printf '\n'
  cat "$ticket"
} > "$impl"
{
  printf '%s\n' "Self-review the integration diff. Fix correctness, scope, secrets, and tests. Do not push."
  printf '%s\n' "Ticket path: $ticket"
} > "$review"

run_grok implement "$impl" || park_exit "grok implement failed"
if [ -f "$ROOT/tmp/STOP" ] || [ -f "$WT/tmp/STOP" ]; then
  park_exit "STOP file" 0
fi
run_grok review "$review" || park_exit "grok self-review failed"

if [ -n "$(git -C "$WT" status --porcelain)" ]; then
  park_exit "dirty worktree after grok"
fi

sanity() {
  local rel suffix changed
  changed=$(git -C "$WT" diff --name-only --diff-filter=ACMR origin/main...HEAD) || return 1
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    [ -f "$WT/$rel" ] || continue
    suffix=${rel##*.}
    case "$suffix" in
      py)
        python3 -m py_compile "$WT/$rel" || return 1
        ;;
      sh)
        bash -n "$WT/$rel" || return 1
        ;;
      json|yml|yaml)
        python3 - "$WT/$rel" <<'PY' || return 1
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
suf = path.suffix.lower()
if suf == ".json":
    json.loads(text)
    raise SystemExit(0)
try:
    import yaml
except ImportError:
    yaml = None
if yaml is not None:
    loaded = yaml.safe_load(text)
    if loaded is None and text.strip():
        raise SystemExit("yaml: empty document")
    raise SystemExit(0)
body = text.lstrip()
if body.startswith("{") or body.startswith("["):
    raise SystemExit("yaml flow document needs PyYAML")
for n, line in enumerate(text.splitlines(), 1):
    raw = line.split("#", 1)[0].rstrip()
    if not raw.strip():
        continue
    item = raw.lstrip()
    if item.startswith("- ") or item == "-":
        continue
    if ":" not in item:
        raise SystemExit("yaml:%s: expected key" % n)
raise SystemExit(0)
PY
        ;;
    esac
  done <<< "$changed"
}

sanity || park_exit "sanity failed"
progress "$SLUG sanity ok"

(
  cd "$WT"
  python3 scripts/catalog_check.py
) || park_exit "catalog_check failed"
(
  cd "$WT"
  python3 scripts/check_no_encoded_payloads.py
) || park_exit "encoded payload check failed"

sel="$MARK_DIR/${SLUG}-select.json"
(
  cd "$WT"
  python3 scripts/test_select.py --base origin/main
) > "$sel" || park_exit "test_select failed"
modules=()
while IFS= read -r line; do
  [ -n "$line" ] || continue
  modules+=("$line")
done < <(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("\n".join(d.get("modules") or []))' "$sel")
mode=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("mode",""))' "$sel")
progress "$SLUG test_select mode=$mode modules=${#modules[@]}"
if [ "${#modules[@]}" -gt 0 ]; then
  (
    cd "$WT"
    python3 scripts/run_tests.py "${modules[@]}"
  ) || park_exit "run_tests failed"
fi

land() {
  local sha attempt
  sha=$(git -C "$WT" rev-parse HEAD)
  attempt=1
  while [ "$attempt" -le 3 ]; do
    git -C "$ROOT" fetch origin >&2 || return 1
    if git -C "$ROOT" merge-base --is-ancestor origin/main "$sha"; then
      if git -C "$ROOT" push origin "${sha}:refs/heads/main" >&2; then
        printf '%s\n' "$sha"
        return 0
      fi
    fi
    progress "$SLUG rebase attempt $attempt"
    GIT_EDITOR=: GIT_SEQUENCE_EDITOR=: git -C "$WT" rebase origin/main >&2 || return 1
    sha=$(git -C "$WT" rev-parse HEAD)
    attempt=$((attempt + 1))
  done
  return 1
}

sha=$(land) || park_exit "land failed"
printf '%s\n' "$sha" > "$LANDED"
printf '%s\n' "$sha" > "$DONE"
progress "$SLUG landed $sha"
printf '%s\n' "landed $SLUG $sha"
