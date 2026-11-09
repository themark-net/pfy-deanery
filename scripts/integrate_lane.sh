#!/bin/bash
# Drive one I2-to-I3 integration lane. No pull requests.
#
# If tmp/integrate/<slug>.dispatched already exists, a second start exits 2
# before fetch, worktree, grok, or push. Otherwise the stage card, the
# exclusions file, and park files are read first. The marker is created only
# when integration_stage is I2, the slug is not listed in
# eval/catalog-queue/exclusions.tsv, and no <slug>.parked file exists.
# A refusal writes no marker and deletes none. A lost race on the create
# exits 2. Land with a fast-forward push of the worktree SHA onto origin/main.
# Rebase and retry when origin/main is not an ancestor of that SHA. Park
# instead of pushing when a later step fails.
#
#   scripts/integrate_lane.sh --slug <slug> [--root DIR] [--date MMDD] [--ticket FILE]
#   scripts/integrate_lane.sh --dry-run --slug <slug> [--root DIR]
#
# --dry-run prints one line and exits before the card check, the dispatch
# marker, fetch, Grok, apply, and the push. It does not take the model lock.
# The line names each skip. Do not run the default path against the real
# origin from a test. Pass --root.

set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DEFAULT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

# dcg classifies argv and does not run it. Exit 126 denies.
# sandlock and llama-cpp-ngram-mod add their own checks beside this one.
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
  printf '%s\n' "dry-run slug=${SLUG} skip-card skip-marker skip-fetch skip-grok skip-apply skip-push"
  exit 0
fi

MARK_DIR="$ROOT/tmp/integrate"
MARKER="$MARK_DIR/${SLUG}.dispatched"
PARKED="$MARK_DIR/${SLUG}.parked"
DONE="$MARK_DIR/${SLUG}.done"
LANDED="$MARK_DIR/LANDED_${SLUG}"
PROGRESS="$MARK_DIR/progress.md"
WT="$MARK_DIR/wt/${SLUG}"
BRANCH="bot/integrate-${SLUG}-${DATE}"

# Second start: no git and no grok. Leave the marker bytes alone.
if [ -f "$MARKER" ]; then
  printf '%s\n' "already dispatched: $SLUG" >&2
  exit 2
fi

# Refuse before the marker. A miss writes nothing and deletes nothing.
if ! python3 - "$ROOT" "$SLUG" "$MARK_DIR" "$DEFAULT_ROOT" <<'PY'
import json
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
slug = sys.argv[2]
mark_dir = Path(sys.argv[3])
repo = sys.argv[4]
sys.path.insert(0, repo)
from scripts.catalog_eval_queue import QueueError, exclusion_reason


def refuse(msg):
    sys.stderr.write(msg + "\n")
    raise SystemExit(1)


card_path = root / "data" / "stages" / f"{slug}.json"
if not card_path.is_file():
    refuse(f"not I2: {slug} missing-card")
try:
    card = json.loads(card_path.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError):
    refuse(f"not I2: {slug} malformed-card")
if not isinstance(card, dict):
    refuse(f"not I2: {slug} malformed-card")
stage = card.get("integration_stage")
if stage != "I2":
    shown = stage if isinstance(stage, str) else "missing"
    refuse(f"not I2: {slug} stage={shown}")

park_files = [mark_dir / f"{slug}.parked"]
loop = os.environ.get("PFY_LOOP_STATE", "").strip()
if loop:
    park_files.append(Path(loop) / "integrate" / f"{slug}.parked")
for path in park_files:
    if path.is_file():
        refuse(f"parked: {slug}")

try:
    reason = exclusion_reason(root, slug)
except QueueError as exc:
    refuse(f"excluded: {slug} {exc}")
if reason:
    refuse(f"excluded: {slug}")
PY
then
  exit 1
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
      run_checked bash "$SCRIPT_DIR/model_lock.sh" "${PFY_GROK_BIN:-grok}" --always-approve --output-format plain --prompt-file "$prompt"
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
  printf '%s\n' "Ticket path: $ticket"
  printf '\n'
  cat "$ticket"
} > "$impl"
{
  printf '%s\n' "Self-review the integration diff. Fix correctness, scope, secrets, and tests. Do not push."
  printf '%s\n' "$skill_reads"
  printf '%s\n' "Follow those skills, then tmp/TICKET-${SLUG}.md."
  printf '%s\n' "Ticket path: $ticket"
} > "$review"

run_grok implement "$impl" || park_exit "grok implement failed"
if [ -f "$ROOT/tmp/STOP" ] || [ -f "$WT/tmp/STOP" ]; then
  park_exit "STOP file" 0
fi
run_grok review "$review" || park_exit "grok self-review failed"
if [ -f "$ROOT/tmp/STOP" ] || [ -f "$WT/tmp/STOP" ]; then
  park_exit "STOP file" 0
fi

if [ -n "$(git -C "$WT" status --porcelain)" ]; then
  park_exit "dirty worktree after grok"
fi

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
    sha=$(run_checked git -C "$WT" rev-parse HEAD)
    attempt=$((attempt + 1))
  done
  return 1
}

sha=$(land) || park_exit "land failed"

# After the fast-forward, run the slug receipt once and apply the verdict.
# A missing script keeps today's behavior. Apply refusal does not rewrite a card.
receipt_script="$WT/eval/integrate/${SLUG}/run-on-main.sh"
if [ -f "$receipt_script" ]; then
  run_checked git -C "$WT" fetch origin >&2 || progress "$SLUG receipt fetch failed"
  receipt_path="$WT/eval/integrate/${SLUG}/receipt.json"
  if (cd "$WT" && bash "$receipt_script" "$receipt_path"); then
    progress "$SLUG receipt wrote"
  else
    progress "$SLUG receipt refused"
  fi
  verdict="$WT/eval/integrate/${SLUG}/VERDICT.json"
  card="$WT/data/stages/${SLUG}.json"
  if [ -f "$verdict" ] && [ -f "$card" ]; then
    apply_log="$MARK_DIR/${SLUG}.apply"
    if python3 "$WT/scripts/catalog_apply_verdict.py" --card "$card" --verdict "$verdict" >"$apply_log" 2>&1; then
      progress "$SLUG apply ok"
    else
      progress "$SLUG apply refused"
    fi
  fi
fi

printf '%s\n' "$sha" > "$LANDED"
printf '%s\n' "$sha" > "$DONE"
progress "$SLUG landed $sha"
printf '%s\n' "landed $SLUG $sha"
