#!/bin/bash
# Drive one catalog eval lane. No pull requests.
# Not ./pfy eval. That command is the product structural gate
# (make eval-integration-change). It writes pipelines/eval.
# It does not call Grok and does not push main.
#
#   scripts/eval_lane.sh --slug <slug> [--date MMDD] [--root DIR] [--state DIR] [--ticket FILE]
#   scripts/eval_lane.sh --dry-run --slug <slug> --state DIR [--root DIR]
#
# --dry-run requires --state, prints one line, and exits before the dispatch
# marker, fetch, Grok, apply, and the push. It does not walk apply and it
# does not take the model lock. The line names each skip.
#
# Worktree: STATE/eval/wt/<slug> cut from origin/main.
# Branch: bot/eval-<slug>-<date>.
# The driver, not the Build, runs catalog_apply_verdict.py. A refusal is
# recorded and the card bytes stay as they were. A missing card is created
# at I0 through pfylib.stage_registry.write_tool.
# Grok is PFY_GROK_BIN (default grok) and is wrapped in scripts/model_lock.sh.
# Do not run this against the real origin from a test. Pass --root and
# PFY_LOOP_STATE or --state.

set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DEFAULT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

dcg_check() {
  # Missing guard.sh cannot apply the built-in denylist, which lives in that
  # file. Say so and let the command run. A missing dcg binary is different:
  # guard.sh still denies that list.
  local guard="$SCRIPT_DIR/integrations/dcg/guard.sh"
  if [ ! -f "$guard" ]; then
    printf '%s\n' "dcg-fallback: guard.sh missing; built-in denylist not applied; command unchanged" >&2
    return 0
  fi
  bash "$guard" "$@"
}

run_checked() {
  dcg_check "$@" || return $?
  "$@"
}

ROOT=""
SLUG=""
DATE=""
TICKET=""
STATE_DIR=""
STATE_SET=0
DRY=0

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
    --state)
      STATE_DIR=${2:-}
      STATE_SET=1
      shift 2
      ;;
    --dry-run)
      DRY=1
      shift
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
if [ "$DRY" = "1" ]; then
  if [ "$STATE_SET" != "1" ] || [ -z "$STATE_DIR" ]; then
    printf '%s\n' "dry-run needs --state" >&2
    exit 1
  fi
  printf '%s\n' "dry-run slug=${SLUG} state=${STATE_DIR} skip-marker skip-fetch skip-grok skip-apply skip-push"
  exit 0
fi
if [ -z "$STATE_DIR" ]; then
  LOOP_STATE="${PFY_LOOP_STATE:-$HOME/DEVELOP/pfy-mentat/tmp/loop}"
  STATE_DIR="$LOOP_STATE/eval"
fi

MARK_DIR="$STATE_DIR"
MARKER="$MARK_DIR/${SLUG}.dispatched"
PARKED="$MARK_DIR/${SLUG}.parked"
DONE="$MARK_DIR/${SLUG}.done"
LANDED="$MARK_DIR/LANDED_${SLUG}"
REFUSED="$MARK_DIR/${SLUG}.refused"
PROGRESS="$MARK_DIR/progress.md"
WT="$MARK_DIR/wt/${SLUG}"
BRANCH="bot/eval-${SLUG}-${DATE}"
GROK_BIN="${PFY_GROK_BIN:-grok}"
LOOP_STATE="${PFY_LOOP_STATE:-$(dirname "$STATE_DIR")}"

mkdir -p "$MARK_DIR"

if [ -f "$MARKER" ] && [ "${PFY_LANE_FROM_LOOP:-}" != "1" ]; then
  printf '%s\n' "already dispatched: $SLUG" >&2
  exit 2
fi
if [ ! -f "$MARKER" ]; then
  if ! (set -o noclobber; printf '%s\n' "pid $$" > "$MARKER") 2>/dev/null; then
    printf '%s\n' "already dispatched: $SLUG" >&2
    exit 2
  fi
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

stop_now() {
  [ -f "$LOOP_STATE/STOP" ] || [ -f "$ROOT/tmp/STOP" ] || [ -f "$MARK_DIR/STOP" ] || [ -f "$WT/tmp/STOP" ]
}

if stop_now; then
  park_exit "STOP file" 0
fi

progress "$SLUG start"

run_checked git -C "$ROOT" fetch origin >&2 || park_exit "git fetch failed"
if [ -e "$WT" ]; then
  park_exit "worktree path exists"
fi
mkdir -p "$MARK_DIR/wt"
run_checked git -C "$ROOT" worktree add -b "$BRANCH" "$WT" origin/main >&2 || park_exit "worktree add failed"
progress "$SLUG worktree $BRANCH"
skill_reads=""
for skill_name in catalog-intake-dedupe catalog-eval-lane catalog-integrate-lane catalog-apply-and-ceiling catalog-loop-operator; do
  skill_rel="bootstrap/grok-cli/skills/${skill_name}/SKILL.md"
  if [ -f "$WT/$skill_rel" ]; then
    skill_sha=$(git -C "$WT" hash-object "$skill_rel")
  else
    skill_sha="missing"
  fi
  progress "skill=${skill_name} sha=${skill_sha}"
  skill_reads="${skill_reads}Read ${skill_rel}."$'\n'
done

mkdir -p "$WT/tmp"
if [ -n "$TICKET" ] && [ -f "$TICKET" ]; then
  cp "$TICKET" "$WT/tmp/TICKET-${SLUG}.md"
elif [ -f "$MARK_DIR/tickets/TICKET-${SLUG}.md" ]; then
  cp "$MARK_DIR/tickets/TICKET-${SLUG}.md" "$WT/tmp/TICKET-${SLUG}.md"
elif [ -f "$ROOT/tmp/TICKET-${SLUG}.md" ]; then
  cp "$ROOT/tmp/TICKET-${SLUG}.md" "$WT/tmp/TICKET-${SLUG}.md"
else
  cat > "$WT/tmp/TICKET-${SLUG}.md" <<EOF
# Eval ticket: ${SLUG}

Write eval/evals/${SLUG}/VERDICT.json that matches docs/ops/VERDICT.schema.json.
Write the prose report to tmp/ops/eval/evals/${SLUG}/REPORT.md. Put traces and raw logs
under tmp/ops/eval/evals/${SLUG}/ too. tmp/ is gitignored; the lane moves them to the
private ops checkout. Commit only VERDICT.json, receipts, probes, and fixtures, with no
home paths or names in them.
Do not hand-edit integration_stage or tier_ceiling.
${skill_reads}Follow those skills, then tmp/TICKET-${SLUG}.md.
EOF
fi
ticket="$WT/tmp/TICKET-${SLUG}.md"

if [ ! -f "$WT/data/stages/${SLUG}.json" ]; then
  (
    cd "$WT"
    python3 - "$SLUG" <<'PY'
import sys
from pfylib.stage_registry import write_tool
slug = sys.argv[1]
write_tool(".", slug, {
    "integration_stage": "I0",
    "uses": "",
    "features": [],
    "potential": "ambiguous",
    "non_goals": ["raised without a verdict"],
    "next_gate": "eval",
    "evidence": [],
    "tier_ceiling": "I0",
    "risk_class": "unknown",
})
PY
  ) || park_exit "I0 card create failed"
  run_checked git -C "$WT" add -- "data/stages/${SLUG}.json" || park_exit "I0 card add failed"
  run_checked git -C "$WT" commit -qm "eval: add I0 card for ${SLUG}" || park_exit "I0 card commit failed"
  progress "$SLUG I0 card created"
fi

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
      run_checked bash "$SCRIPT_DIR/model_lock.sh" "$GROK_BIN" --cwd "$WT" --always-approve --output-format plain --prompt-file "$prompt"
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
  printf '%s\n' "$skill_reads"
  printf '%s\n' "Follow those skills, then tmp/TICKET-${SLUG}.md."
} > "$impl"
{
  printf '%s\n' "$skill_reads"
  printf '%s\n' "Follow those skills, then tmp/TICKET-${SLUG}.md."
  printf '%s\n' "Self-review the diff. Fix correctness, scope, secrets, and tests. Do not push."
} > "$review"

run_grok implement "$impl" || park_exit "grok implement failed"
if stop_now; then
  park_exit "STOP file" 0
fi
run_grok review "$review" || park_exit "grok self-review failed"
if stop_now; then
  park_exit "STOP file" 0
fi

if [ -n "$(git -C "$WT" status --porcelain)" ]; then
  park_exit "dirty worktree after grok"
fi

# Operator records (prose report, traces, raw logs) go to the private ops
# checkout. Public keeps the scrubbed VERDICT, receipt, probe, and fixtures.
if ! python3 "$SCRIPT_DIR/lane_ops_sync.py" --worktree "$WT" --subdir "eval/evals/${SLUG}" --label "eval ${SLUG}" >"$MARK_DIR/${SLUG}.ops" 2>&1; then
  cat "$MARK_DIR/${SLUG}.ops" >&2 || true
  park_exit "public guard failed"
fi
progress "$SLUG ops $(tail -n 1 "$MARK_DIR/${SLUG}.ops" 2>/dev/null)"

sanity() {
  local rel suffix changed
  changed=$(run_checked git -C "$WT" diff --name-only --diff-filter=ACMR origin/main...HEAD) || return 1
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
# Three-dot, not `git diff origin/main HEAD`. A lane that is behind main
# must not select files that only changed on main (that forces mode full).
if ! select_list=$(run_checked git -C "$WT" diff --name-only --diff-filter=ACMR origin/main...HEAD); then
  park_exit "test_select failed"
fi
select_paths=()
while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  select_paths+=("$rel")
done <<< "$select_list"
if [ "${#select_paths[@]}" -eq 0 ]; then
  printf '%s\n' '{"mode":"none","reason":"lane commits do not change files","modules":[],"changed":[],"source":"lane"}' > "$sel"
else
  (
    cd "$WT"
    python3 scripts/test_select.py --paths "${select_paths[@]}"
  ) > "$sel" || park_exit "test_select failed"
fi
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

card_bytes() {
  if [ -f "$WT/data/stages/${SLUG}.json" ]; then
    python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_bytes().hex())' "$WT/data/stages/${SLUG}.json"
  else
    printf '%s\n' "missing"
  fi
}

rebase_onto_main() {
  run_checked git -C "$WT" fetch origin >&2 || return 1
  if run_checked git -C "$WT" merge-base --is-ancestor origin/main HEAD; then
    return 0
  fi
  progress "$SLUG rebase attempt"
  if ! GIT_EDITOR=: GIT_SEQUENCE_EDITOR=: run_checked git -C "$WT" rebase origin/main >&2; then
    run_checked git -C "$WT" rebase --abort >&2 || true
    return 1
  fi
  return 0
}

run_guard() {
  python3 "$SCRIPT_DIR/catalog_card_guard.py" --worktree "$WT" "$@" || return 1
  if [ -n "$(git -C "$WT" status --porcelain)" ]; then
    run_checked git -C "$WT" add -- data/stages || return 1
    run_checked git -C "$WT" commit -qm "eval: restore disallowed card fields" || return 1
  fi
}

rebase_onto_main || park_exit "rebase failed"
run_guard || park_exit "card guard failed"
progress "$SLUG card guard ok"

before_apply=$(card_bytes)
verdict="$WT/eval/evals/${SLUG}/VERDICT.json"
card="$WT/data/stages/${SLUG}.json"
apply_ok=0
if [ ! -f "$verdict" ]; then
  park_exit "missing verdict"
fi
apply_log="$MARK_DIR/${SLUG}.apply"
if python3 "$SCRIPT_DIR/catalog_apply_verdict.py" --card "$card" --verdict "$verdict" >"$apply_log" 2>&1; then
  progress "$SLUG apply ok"
  apply_ok=1
else
  progress "$SLUG apply refused"
  cp "$apply_log" "$REFUSED"
  after_apply=$(card_bytes)
  if [ "$before_apply" != "$after_apply" ]; then
    park_exit "apply refusal changed the card"
  fi
fi
if [ "$apply_ok" -eq 1 ] && [ -n "$(git -C "$WT" status --porcelain)" ]; then
  run_checked git -C "$WT" add -- "data/stages/${SLUG}.json" || park_exit "apply add failed"
  run_checked git -C "$WT" commit -qm "eval: apply verdict for ${SLUG}" || park_exit "apply commit failed"
fi

land() {
  local sha attempt
  sha=$(run_checked git -C "$WT" rev-parse HEAD)
  attempt=1
  while [ "$attempt" -le 3 ]; do
    run_checked git -C "$ROOT" fetch origin >&2 || return 1
    if run_checked git -C "$ROOT" merge-base --is-ancestor origin/main "$sha"; then
      if run_checked git -C "$ROOT" push origin "${sha}:refs/heads/main" >&2; then
        printf '%s\n' "$sha"
        return 0
      fi
    fi
    progress "$SLUG rebase attempt $attempt"
    if ! GIT_EDITOR=: GIT_SEQUENCE_EDITOR=: run_checked git -C "$WT" rebase origin/main >&2; then
      run_checked git -C "$WT" rebase --abort >&2 || true
      return 1
    fi
    if [ "$apply_ok" -eq 1 ]; then
      run_guard --allow-stage "$SLUG" || return 1
    else
      run_guard || return 1
    fi
    sha=$(run_checked git -C "$WT" rev-parse HEAD)
    attempt=$((attempt + 1))
  done
  return 1
}

sha=$(land) || park_exit "land failed"
printf '%s\n' "$sha" > "$LANDED"
printf '%s\n' "$sha" > "$DONE"
progress "$SLUG landed $sha"
printf '%s\n' "landed $SLUG $sha"
