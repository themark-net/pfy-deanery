#!/bin/bash
# One catalog loop tick. Idempotent. Does not install units and does not
# start a model. PFY_LOOP_NO_PUSH=1 and --dry-run push nothing.
# Optional command word: tick (same as no argument).
#
# State: ${PFY_CATALOG_STATE_DIR:-${PFY_LOOP_STATE:-$HOME/DEVELOP/pfy-mentat/tmp/loop}}
# Worktree: ${PFY_LOOP_WT:-$HOME/DEVELOP/pfy-mentat/tmp/loop/wt}
# Lock: STATE/loop.lock. A busy lock exits 0 with status busy.
# STOP and QUOTA_STOP exit 0 with status stopped and launch nothing.
# PFY_CATALOG_OFFLINE=1 skips fetch, regen writes, and push. Tests use it.
# PFY_SUPERSEDE_CHECK, when set, replaces python3 scripts/supersede_check.py.
# Operator queues never go in the public repo. needs-mark.tsv is written to
# $PFY_OPS_ROOT/eval/catalog-queue/needs-mark.tsv and committed in that private
# checkout. Unset, it goes to tmp/ops/ in the worktree (gitignored), uncommitted.
set -euo pipefail

export GIT_TERMINAL_PROMPT=0
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -n "${PFY_CATALOG_STATE_DIR:-}" ]; then
  STATE="$PFY_CATALOG_STATE_DIR"
else
  STATE="${PFY_LOOP_STATE:-$HOME/DEVELOP/pfy-mentat/tmp/loop}"
fi
WT="${PFY_LOOP_WT:-$HOME/DEVELOP/pfy-mentat/tmp/loop/wt}"
REPO="${PFY_LOOP_REPO:-$HOME/DEVELOP/pfy-mentat}"
INTEGRATE_ROOT="${PFY_INTEGRATE_ROOT:-$HOME/DEVELOP/pfy-mentat/tmp/integrate}"
INTEGRATE2_ROOT="${PFY_INTEGRATE2_ROOT:-$HOME/DEVELOP/pfy-mentat/tmp/integrate2}"
EVQ_ROOT="${PFY_EVQ_ROOT:-$HOME/DEVELOP/pfy-mentat/tmp/evq}"
SYSTEMD_RUN="${PFY_SYSTEMD_RUN:-systemd-run}"
DRY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)
      DRY=1
      shift
      ;;
    tick)
      shift
      ;;
    *)
      printf '%s\n' "unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "$STATE"

OFFLINE=0
if [ "${PFY_CATALOG_OFFLINE:-}" = "1" ]; then
  # No fetch and no regen writes. Isolate marker roots so a live integrate2
  # batch cannot fill the cap or receive a ticket from this test tick.
  OFFLINE=1
  export PFY_LOOP_NO_PUSH=1
  if [ -z "${PFY_LOOP_WT:-}" ]; then
    WT="$STATE/offline-wt"
  fi
  if [ -z "${PFY_INTEGRATE_ROOT:-}" ]; then
    INTEGRATE_ROOT="$STATE/integrate"
  fi
  if [ -z "${PFY_INTEGRATE2_ROOT:-}" ]; then
    INTEGRATE2_ROOT="$STATE/integrate2"
  fi
  if [ -z "${PFY_EVQ_ROOT:-}" ]; then
    EVQ_ROOT="$STATE/evq"
  fi
fi

now_pair() {
  printf '%s' "{\"utc\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"pt\":\"$(TZ=America/Los_Angeles date +%Y-%m-%dT%H:%M:%S%z)\"}"
}

TICK_STARTED=$(now_pair)
export PFY_TICK_STARTED="$TICK_STARTED"
export PFY_TICK_FINISHED="$TICK_STARTED"
export PFY_ORIGIN_MAIN=""
export PFY_STOP_FILES="[]"
export PFY_RUNNING="[]"
export PFY_STARTED_TODAY=0
export PFY_SLOTS=0
export PFY_LAUNCHED="[]"
export PFY_SKIPPED="[]"
export PFY_NEEDS_COUNT=0
export PFY_NEEDS_CHANGED=0
export PFY_APPLIED="[]"
export PFY_RAISED="[]"
export PFY_REFUSED="[]"
export PFY_APPLY_REFUSED="[]"
export PFY_PARKED="[]"
export PFY_ERRORS="[]"
export PFY_SUPERSEDE=""
export PFY_SUPERSEDE_STALE="[]"
export PFY_PARK_RETRY="[]"

write_status() {
  local status="$1"
  local repo_copy="$PWD/pipelines/catalog/loop.latest.json"
  if [ "${PFY_LOOP_IN_WORKTREE:-}" != "1" ]; then
    repo_copy=""
  fi
  PFY_TICK_FINISHED=$(now_pair)
  export PFY_TICK_FINISHED
  python3 - "$STATE/loop.latest.json" "$repo_copy" "$status" <<'PY'
import json, os, sys
from pathlib import Path

state_path, repo_path, status = sys.argv[1:4]

def grab(name, default):
    raw = os.environ.get(name, "")
    if not raw:
        return default
    return json.loads(raw)

doc = {
    "tick_started": grab("PFY_TICK_STARTED", {}),
    "tick_finished": grab("PFY_TICK_FINISHED", {}),
    "origin_main": os.environ.get("PFY_ORIGIN_MAIN", ""),
    "status": status,
    "stop_files": grab("PFY_STOP_FILES", []),
    "running": grab("PFY_RUNNING", []),
    "started_today": int(os.environ.get("PFY_STARTED_TODAY", "0") or "0"),
    "cap": {"running": 4, "daily": 20},
    "slots": int(os.environ.get("PFY_SLOTS", "0") or "0"),
    "launched": grab("PFY_LAUNCHED", []),
    "skipped_taken": grab("PFY_SKIPPED", []),
    "needs_mark_count": int(os.environ.get("PFY_NEEDS_COUNT", "0") or "0"),
    "needs_mark_changed": os.environ.get("PFY_NEEDS_CHANGED", "") == "1",
    "applied": grab("PFY_APPLIED", []),
    "auto_raised": grab("PFY_RAISED", []),
    "refused": grab("PFY_REFUSED", []),
    "apply_refused": grab("PFY_APPLY_REFUSED", []),
    "parked": grab("PFY_PARKED", []),
    "errors": grab("PFY_ERRORS", []),
    "supersede": os.environ.get("PFY_SUPERSEDE", ""),
    "supersede_stale": grab("PFY_SUPERSEDE_STALE", []),
    "park_retry": grab("PFY_PARK_RETRY", []),
    "rule_retry": grab("PFY_RULE_RETRY", []),
}
text = json.dumps(doc, indent=2, sort_keys=True) + "\n"
for dest in (state_path, repo_path):
    if not dest:
        continue
    path = Path(dest)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError:
        if dest == state_path:
            raise
PY
}

fail() {
  local msg="$1"
  local code="${2:-1}"
  PFY_ERRORS=$(python3 -c 'import json,sys; print(json.dumps([sys.argv[1]]))' "$msg")
  export PFY_ERRORS
  write_status error || true
  printf '%s\n' "status=error ${msg}" >&2
  exit "$code"
}

drop_supersede_rows() {
  local dest="$1"
  python3 - "$dest" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.is_file():
    raise SystemExit(0)
kept = []
for line in path.read_text(encoding="utf-8").splitlines():
    parts = line.split("\t")
    if len(parts) >= 2 and parts[1] == "supersede-stop":
        continue
    kept.append(line)
body = [line for line in kept if line and not line.startswith("slug\t")]
if not body:
    path.unlink()
    raise SystemExit(0)
path.write_text("\n".join(kept) + "\n", encoding="utf-8")
PY
}

append_supersede_row() {
  local dest="$1"
  local slug="$2"
  local since="$3"
  python3 - "$dest" "$slug" "$since" <<'PY'
import sys
from pathlib import Path

dest, slug, since = sys.argv[1:]
slug = slug.replace("\t", " ").strip() or "supersede-watch"
header = "slug\tkind\treason\tevidence\tsince"
row = "\t".join((
    slug,
    "supersede-stop",
    "supersede check exit 1",
    "scripts/supersede_check.py",
    since or "-",
))
path = Path(dest)
lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
for line in lines:
    parts = line.split("\t")
    if len(parts) >= 2 and parts[0] == slug and parts[1] == "supersede-stop":
        print("kept")
        raise SystemExit(0)
if not lines or not lines[0].startswith("slug\t"):
    lines.insert(0, header)
lines.append(row)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("added")
PY
}

supersede_project_id() {
  python3 - "$1" "$2" <<'PY'
import re
import sys
from pathlib import Path

def read(path):
    file = Path(path)
    if not file.is_file():
        return []
    return file.read_text(encoding="utf-8", errors="replace").splitlines()

named = []
bare = []
skip = ("projects=", "candidate:", "stale:", "note:")
for raw in read(sys.argv[1]) + read(sys.argv[2]):
    text = raw.strip()
    if not text or text.startswith(skip):
        continue
    if text.startswith("FAIL "):
        body = text[5:].strip()
        if body.startswith("cannot read") or ":" not in body:
            continue
        name = body.split(":", 1)[0].strip()
        if not name or "must be" in name:
            continue
        named.append(name)
        continue
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", text):
        bare.append(text)
if named:
    print(named[0])
elif bare:
    print(bare[0])
else:
    print("supersede-watch")
PY
}

run_supersede_check() {
  local out="$STATE/supersede.out"
  local err="$STATE/supersede.err"
  local rc=0
  local slug=""
  local since=""
  SUPERSEDE_ACTION=error
  PFY_SUPERSEDE=""
  export PFY_SUPERSEDE
  : >"$out"
  : >"$err"
  set +e
  if [ -n "${PFY_SUPERSEDE_CHECK:-}" ]; then
    timeout 60 "$PFY_SUPERSEDE_CHECK" >"$out" 2>"$err"
    rc=$?
  else
    # Reads data/supersede-watchlist.json only. No offline flag exists.
    # Passing one would make argparse exit 2 and stop every tick.
    timeout 60 python3 scripts/supersede_check.py >"$out" 2>"$err"
    rc=$?
  fi
  set -e
  if [ "$rc" -eq 0 ]; then
    PFY_SUPERSEDE_STALE=$(python3 - "$out" <<'PY'
import json
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
stale = [line for line in text.splitlines() if line.startswith("stale:")]
print(json.dumps(stale))
PY
)
    export PFY_SUPERSEDE_STALE
    drop_supersede_rows "$STATE/needs-mark.tsv"
    SUPERSEDE_ACTION=continue
    return 0
  fi
  if [ "$rc" -eq 1 ]; then
    slug=$(supersede_project_id "$out" "$err")
    since=$(TZ=America/Los_Angeles date +%Y-%m-%d)
    state_add=$(append_supersede_row "$STATE/needs-mark.tsv" "$slug" "$since")
    repo_add=kept
    if [ "$OFFLINE" -eq 0 ]; then
      repo_add=$(append_supersede_row "$(needs_file)" "$slug" "$since")
    fi
    if [ "$repo_add" = "added" ] || { [ "$OFFLINE" -eq 1 ] && [ "$state_add" = "added" ]; }; then
      PFY_NEEDS_COUNT=$(( ${PFY_NEEDS_COUNT:-0} + 1 ))
      PFY_NEEDS_CHANGED=1
      export PFY_NEEDS_COUNT PFY_NEEDS_CHANGED
    fi
    PFY_SUPERSEDE=stop
    export PFY_SUPERSEDE
    SUPERSEDE_ACTION=stop
    return 0
  fi
  # Exit other than 0 or 1, including timeout 124. No stop row.
  # The tick still exits 0. Grilled tests require that. Status carries error.
  PFY_ERRORS=$(python3 -c 'import json,sys; print(json.dumps([sys.argv[1]]))' "supersede check exit ${rc}")
  export PFY_ERRORS
  SUPERSEDE_ACTION=error
}

# The needs-mark queue path. Private checkout when PFY_OPS_ROOT is set, else a
# gitignored path under the current worktree.
needs_file() {
  if [ -n "${PFY_OPS_ROOT:-}" ]; then
    printf '%s\n' "$PFY_OPS_ROOT/eval/catalog-queue/needs-mark.tsv"
  else
    printf '%s\n' "$PWD/tmp/ops/eval/catalog-queue/needs-mark.tsv"
  fi
}

json_list() {
  python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "$@"
}

in_prepared_worktree() {
  local here wt_abs lock
  here=$(realpath -m "$PWD")
  wt_abs=$(realpath -m "$WT")
  [ "$here" = "$wt_abs" ] || return 1
  lock="$(dirname "$wt_abs")/loop-worktree.lock"
  if flock -n "$lock" -c true; then
    return 1
  fi
  return 0
}

stop_files=()
[ -f "$STATE/STOP" ] && stop_files+=("$STATE/STOP")
[ -f "$STATE/QUOTA_STOP" ] && stop_files+=("$STATE/QUOTA_STOP")
if [ "${#stop_files[@]}" -gt 0 ] && [ "${PFY_LOOP_IN_WORKTREE:-}" != "1" ]; then
  PFY_STOP_FILES=$(json_list "${stop_files[@]}")
  export PFY_STOP_FILES
  printf '%s\n' "status=stopped"
  write_status stopped
  exit 0
fi

if [ "${PFY_LOOP_IN_WORKTREE:-}" != "1" ]; then
  exec 8>>"$STATE/loop.lock"
  if ! flock -n 8; then
    printf '%s\n' "status=busy"
    write_status busy
    exit 0
  fi
  if [ "$OFFLINE" -eq 1 ]; then
    export PFY_LOOP_IN_WORKTREE=1
  elif ! in_prepared_worktree; then
    export PFY_LOOP_IN_WORKTREE=1
    if [ "$DRY" -eq 1 ]; then
      "$SCRIPT_DIR/loop_worktree.sh" --wt "$WT" -- scripts/catalog_loop.sh --dry-run
    else
      "$SCRIPT_DIR/loop_worktree.sh" --wt "$WT" -- scripts/catalog_loop.sh
    fi
    exit $?
  fi
  export PFY_LOOP_IN_WORKTREE=1
fi

# Inner tick. Parent holds STATE/loop.lock, or this process is already in the worktree.
if [ -f "$STATE/STOP" ] || [ -f "$STATE/QUOTA_STOP" ]; then
  stop_files=()
  [ -f "$STATE/STOP" ] && stop_files+=("$STATE/STOP")
  [ -f "$STATE/QUOTA_STOP" ] && stop_files+=("$STATE/QUOTA_STOP")
  PFY_STOP_FILES=$(json_list "${stop_files[@]}")
  export PFY_STOP_FILES
  printf '%s\n' "status=stopped"
  write_status stopped
  exit 0
fi

export GIT_AUTHOR_NAME=catalog-loop
export GIT_AUTHOR_EMAIL=catalog-loop@localhost
export GIT_COMMITTER_NAME=catalog-loop
export GIT_COMMITTER_EMAIL=catalog-loop@localhost

origin_main=$(git rev-parse origin/main 2>/dev/null || true)
export PFY_ORIGIN_MAIN="$origin_main"

applied=()
refused=()
apply_refused=()
raised=()
SUPERSEDE_ACTION=continue
if [ "$OFFLINE" -eq 1 ]; then
  run_supersede_check
else

python3 scripts/catalog_counts.py || fail "catalog_counts failed"
python3 scripts/catalog_eval_queue.py || fail "catalog_eval_queue failed"
python3 scripts/catalog_apply_verdict.py --scan || fail "ceiling scan failed"

applied=()
refused=()
apply_refused=()
apply_verdict() {
  local slug="$1"
  local verdict="$2"
  local card="data/stages/${slug}.json"
  [ -f "$card" ] || return 0
  [ -f "$verdict" ] || return 0
  local log="$STATE/apply-${slug}.log"
  if python3 scripts/catalog_apply_verdict.py --card "$card" --verdict "$verdict" >"$log" 2>&1; then
    applied+=("$slug")
  else
    refused+=("$slug")
    apply_refused+=("$slug")
  fi
}

shopt -s nullglob
for base in "$STATE/integrate" "$INTEGRATE_ROOT" "$INTEGRATE2_ROOT"; do
  [ -d "$base" ] || continue
  for marker in "$base"/LANDED_*; do
    [ -f "$marker" ] || continue
    slug=${marker##*/LANDED_}
    receipt="eval/integrate/${slug}/receipt.json"
    verdict="eval/integrate/${slug}/VERDICT.json"
    [ -f "$receipt" ] || continue
    apply_verdict "$slug" "$verdict"
  done
done
if [ -d "$STATE/eval" ]; then
  for marker in "$STATE/eval"/LANDED_*; do
    [ -f "$marker" ] || continue
    slug=${marker##*/LANDED_}
    verdict=$(find eval -type f -path "*/${slug}/VERDICT.json" 2>/dev/null | sort | tail -n 1 || true)
    [ -n "${verdict:-}" ] || continue
    apply_verdict "$slug" "$verdict"
  done
fi
shopt -u nullglob

# Rule refusals re-check themselves: a card whose last promotion_history
# entry is a refusal with no hard stop is re-applied once eval-structural is
# green on origin/main (data/promotion-rules.json, "retry").
rule_retry=()
if retry_rules=$(python3 scripts/catalog_apply_verdict.py --retry-refused --root "$PWD"); then
  while IFS=$'\t' read -r action slug why; do
    [ -n "${action:-}" ] || continue
    rule_retry+=("$action $slug $why")
    if [ "$action" = "promote" ]; then
      applied+=("$slug")
    fi
  done <<< "$retry_rules"
else
  rule_retry+=("error retry-refused failed")
fi
if [ "${#rule_retry[@]}" -gt 0 ]; then
  PFY_RULE_RETRY=$(json_list "${rule_retry[@]}")
  export PFY_RULE_RETRY
fi

today_iso=$(TZ=America/Los_Angeles date +%Y-%m-%d)
raised=()
raise_out=$(python3 scripts/catalog_auto_raise.py --root "$PWD" --date "$today_iso") || fail "auto-raise failed"
while IFS=$'\t' read -r action slug reason; do
  [ -n "${action:-}" ] || continue
  if [ "$action" = "raise" ]; then
    raised+=("$slug")
  elif [ "$action" = "refuse" ]; then
    refused+=("$slug")
  fi
done <<< "$raise_out"

# Re-open parked eval/integrate lanes once main is green (cap 2, backoff
# 2h doubling). Runs before needs-mark so a re-opened slug is not listed
# there, and before launch so the daily and running caps still apply.
# Every park is logged to $STATE/park-history.tsv with its reason.
retry_lines=()
if [ "$DRY" -eq 0 ]; then
  if retry_out=$(python3 scripts/catalog_park_retry.py --repo "$PWD" \
      --dir eval="$STATE/eval" --dir integrate="$STATE/integrate" \
      --history "$STATE/park-history.tsv"); then
    while IFS= read -r line; do
      [ -n "$line" ] && retry_lines+=("$line")
    done <<< "$retry_out"
  else
    retry_lines+=("error park-retry failed")
    printf '%s\n' "park-retry failed" >&2
  fi
fi
if [ "${#retry_lines[@]}" -gt 0 ]; then
  PFY_PARK_RETRY=$(json_list "${retry_lines[@]}")
  export PFY_PARK_RETRY
fi

parked_args=()
for base in "$STATE/eval" "$STATE/integrate" "$INTEGRATE_ROOT" "$INTEGRATE2_ROOT" "$EVQ_ROOT"; do
  parked_args+=(--parked "$base")
done
if ! needs_line=$(python3 scripts/catalog_needs_mark.py --root "$PWD" "${parked_args[@]}"); then
  fail "needs-mark failed"
fi
if printf '%s\n' "$needs_line" | grep -q '^wrote '; then
  PFY_NEEDS_CHANGED=1
else
  PFY_NEEDS_CHANGED=0
fi
needs_count=$(printf '%s\n' "$needs_line" | awk '{print $2}')
PFY_NEEDS_COUNT=${needs_count:-0}
export PFY_NEEDS_CHANGED PFY_NEEDS_COUNT

run_supersede_check

allow_args=()
for slug in "${raised[@]+"${raised[@]}"}"; do
  allow_args+=(--allow-ceiling "$slug")
done
for slug in "${applied[@]+"${applied[@]}"}"; do
  allow_args+=(--allow-stage "$slug")
done

path_allowed() {
  case "$1" in
    data/stages/_registry.json|pipelines/catalog/dashboard.latest.md|pipelines/catalog/counts.latest.json|eval/catalog-queue/queue.tsv|eval/catalog-verdicts/CEILING-MISMATCHES.md)
      return 0
      ;;
    data/stages/*.json)
      case "$1" in
        data/stages/*/*) return 1 ;;
      esac
      return 0
      ;;
  esac
  return 1
}

commit_generated() {
  local paths=()
  local bad=0
  local line path
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    [ "${#line}" -ge 4 ] || continue
    path=${line:3}
    if [[ "$path" == *" -> "* ]]; then
      path=${path##* -> }
    fi
    paths+=("$path")
    if ! path_allowed "$path"; then
      bad=1
    fi
  done < <(git status --porcelain -uall)
  if [ "${#paths[@]}" -eq 0 ]; then
    printf '%s\n' "unchanged"
    return 0
  fi
  if [ "$bad" -eq 1 ]; then
    printf '%s\n' "${paths[@]}" >&2
    return 3
  fi
  if [ "$DRY" -eq 1 ] || [ "${PFY_LOOP_NO_PUSH:-}" = "1" ]; then
    printf '%s\n' "${paths[@]}"
    return 0
  fi
  git add -- "${paths[@]}" || return 1
  git commit -m "catalog: regenerate loop outputs" || return 1
  local attempt=1
  while [ "$attempt" -le 3 ]; do
    git fetch -q origin || return 1
    if ! git merge-base --is-ancestor origin/main HEAD; then
      if ! git rebase origin/main; then
        git rebase --abort || true
        return 1
      fi
      if [ "${#allow_args[@]}" -gt 0 ]; then
        python3 scripts/catalog_card_guard.py --worktree "$PWD" "${allow_args[@]}" || return 1
      else
        python3 scripts/catalog_card_guard.py --worktree "$PWD" || return 1
      fi
      if [ -n "$(git status --porcelain)" ]; then
        git add -- data/stages || return 1
        git commit -m "catalog: restore disallowed card fields" || return 1
      fi
    fi
    if git push origin HEAD:refs/heads/main; then
      return 0
    fi
    attempt=$((attempt + 1))
  done
  return 1
}

# Commit the needs-mark queue in the private ops checkout. Only that one path
# is staged, so other work in the ops tree is left alone. No PFY_OPS_ROOT, dry
# run, or no-push: commit nothing. A failure is reported in errors and does not
# stop the tick, because the public outputs already landed.
commit_ops() {
  [ -n "${PFY_OPS_ROOT:-}" ] || { printf '%s\n' "ops unset"; return 0; }
  local ops="$PFY_OPS_ROOT"
  local rel="eval/catalog-queue/needs-mark.tsv"
  [ -d "$ops/.git" ] || [ -f "$ops/.git" ] || { printf '%s\n' "ops not a git checkout: $ops" >&2; return 1; }
  if [ -z "$(git -C "$ops" status --porcelain -- "$rel")" ]; then
    printf '%s\n' "ops unchanged"
    return 0
  fi
  if [ "$DRY" -eq 1 ] || [ "${PFY_LOOP_NO_PUSH:-}" = "1" ]; then
    printf '%s\n' "ops would commit $rel"
    return 0
  fi
  git -C "$ops" add -- "$rel" || return 1
  git -C "$ops" commit -q -m "catalog: needs-mark queue" -- "$rel" || return 1
  local attempt=1
  while [ "$attempt" -le 3 ]; do
    git -C "$ops" fetch -q origin || return 1
    if ! git -C "$ops" merge-base --is-ancestor origin/main HEAD; then
      if ! git -C "$ops" -c rebase.autoStash=true rebase -q origin/main; then
        git -C "$ops" rebase --abort || true
        return 1
      fi
    fi
    if git -C "$ops" push -q origin HEAD:refs/heads/main; then
      return 0
    fi
    attempt=$((attempt + 1))
  done
  return 1
}

set +e
commit_generated
commit_rc=$?
set -e
if [ "$commit_rc" -eq 3 ]; then
  fail "stray generated paths" 3
elif [ "$commit_rc" -ne 0 ]; then
  fail "loop commit failed"
fi

set +e
commit_ops
ops_rc=$?
set -e
if [ "$ops_rc" -ne 0 ]; then
  PFY_ERRORS=$(python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1] or "[]") + [sys.argv[2]]))' "${PFY_ERRORS:-[]}" "ops commit failed")
  export PFY_ERRORS
fi

fi # online regeneration. PFY_CATALOG_OFFLINE=1 skips this block.

today=$(TZ=America/Los_Angeles date +%Y%m%d)
counter="$STATE/started-${today}"
started=0
if [ -f "$counter" ]; then
  started=$(tr -cd '0-9' < "$counter" || true)
fi
[ -n "$started" ] || started=0
if [ "$started" -lt 20 ] && [ -f "$STATE/QUOTA_STOP.auto" ]; then
  rm -f "$STATE/QUOTA_STOP.auto"
fi

RUN_JSON=$(python3 - "$STATE" "$INTEGRATE_ROOT" "$INTEGRATE2_ROOT" <<'PY'
import json, sys, time
from pathlib import Path
state, integrate, integrate2 = map(Path, sys.argv[1:4])
roots = [
    (state / "eval", "eval", "state"),
    (state / "integrate", "integrate", "state"),
    (integrate, "integrate", "integrate"),
    (integrate2, "integrate", "integrate2"),
]
rows = []
tails_path = state / "tails.json"
prev = {}
if tails_path.is_file():
    try:
        loaded = json.loads(tails_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            prev = loaded
    except (OSError, json.JSONDecodeError):
        prev = {}
new_tails = {}
for root, kind, source in roots:
    if not root.is_dir():
        continue
    for path in sorted(root.glob("*.pid")):
        slug = path.name[:-4]
        # scheduler.pid has no sibling .dispatched, so it is not a lane.
        if not (root / f"{slug}.dispatched").is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace").strip().split()
        except OSError:
            continue
        if not text or not text[0].isdigit():
            continue
        pid = int(text[0])
        if not Path(f"/proc/{pid}").exists():
            continue
        age = max(0, int(time.time() - path.stat().st_mtime))
        log = None
        for candidate in (root / f"{slug}.log", root / f"{slug}-implement.log", root / f"driver-{slug}.out"):
            if candidate.is_file():
                log = candidate
                break
        tail = ""
        if log is not None:
            lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
            tail = lines[-1] if lines else ""
        key = f"{source}:{slug}"
        new_tails[key] = tail
        row = {
            "slug": slug,
            "kind": kind,
            "unit": f"pfy-lane-{kind}-{slug}",
            "pid": pid,
            "source": source,
            "pid_age_s": age,
        }
        if tail and prev.get(key) == tail:
            row["hang_same_tail"] = True
        rows.append(row)
seen_pids = set()
unique = []
for row in rows:
    if row["pid"] in seen_pids:
        continue
    seen_pids.add(row["pid"])
    unique.append(row)
rows = unique
tails_path.write_text(json.dumps(new_tails, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(rows))
PY
)
export PFY_RUNNING="$RUN_JSON"
running=$(python3 -c 'import json,sys; print(len(json.loads(sys.argv[1] or "[]")))' "$RUN_JSON")
slots=$((4 - running))
remain=$((20 - started))
if [ "$slots" -gt "$remain" ]; then
  slots=$remain
fi
if [ "$slots" -lt 0 ]; then
  slots=0
fi
status_name=ok
if [ "$started" -ge 20 ]; then
  printf '%s\n' "daily cap 20" > "$STATE/QUOTA_STOP.auto"
  slots=0
  status_name=quota
fi
export PFY_STARTED_TODAY="$started"
export PFY_SLOTS="$slots"
if [ "$SUPERSEDE_ACTION" = "stop" ]; then
  status_name=stopped
elif [ "$SUPERSEDE_ACTION" = "error" ]; then
  status_name=error
fi

pid_alive() {
  local file="$1"
  [ -f "$file" ] || return 1
  local pid
  pid=$(awk 'NR==1 {print $1; exit}' "$file" 2>/dev/null || true)
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  [ -d "/proc/$pid" ]
}

is_taken() {
  local slug="$1"
  local kind="$2"
  local dir
  local dirs=("$STATE/eval" "$STATE/integrate" "$INTEGRATE_ROOT" "$INTEGRATE2_ROOT")
  if [ "$kind" != "integrate" ]; then
    dirs+=("$EVQ_ROOT")
  fi
  for dir in "${dirs[@]}"; do
    [ -d "$dir" ] || continue
    [ -f "$dir/${slug}.dispatched" ] && return 0
    [ -f "$dir/${slug}.done" ] && return 0
    [ -f "$dir/${slug}.parked" ] && return 0
    [ -f "$dir/LANDED_${slug}" ] && return 0
    pid_alive "$dir/${slug}.pid" && return 0
  done
  return 1
}

needs_skip() {
  local slug="$1"
  local file
  file=$(needs_file)
  [ -f "$file" ] || return 1
  awk -F '\t' -v slug="$slug" 'NR > 1 && $1 == slug {found=1} END {exit found ? 0 : 1}' "$file"
}

write_integrate_ticket() {
  local slug="$1"
  local dest="$WT/tmp/TICKET-${slug}.md"
  mkdir -p "$WT/tmp"
  python3 - "$PWD" "$slug" "$dest" <<'PY'
import json, sys
from pathlib import Path
root, slug, dest = sys.argv[1:]
template = Path(root) / "docs" / "ops" / "integrate" / "TEMPLATE.md"
card_path = Path(root) / "data" / "stages" / f"{slug}.json"
card = {}
if card_path.is_file():
    loaded = json.loads(card_path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        card = loaded
body = template.read_text(encoding="utf-8") if template.is_file() else "# Integration ticket: <slug>\n"
body = body.replace("<slug>", slug)
uses = card.get("uses", "")
if not isinstance(uses, str):
    uses = " ".join(item for item in uses if isinstance(item, str)) if isinstance(uses, list) else ""
lines = [
    "",
    "## Card fields",
    "",
    f"- integration_stage: {card.get('integration_stage', '')}",
    f"- tier_ceiling: {card.get('tier_ceiling', '')}",
    f"- uses: {uses}",
    f"- next_gate: {card.get('next_gate', '')}",
    "",
    "Do not raise tier_ceiling. Do not edit integration_stage by hand.",
    "Read bootstrap/grok-cli/skills/catalog-intake-dedupe/SKILL.md.",
    "Read bootstrap/grok-cli/skills/catalog-eval-lane/SKILL.md.",
    "Read bootstrap/grok-cli/skills/catalog-integrate-lane/SKILL.md.",
    "Read bootstrap/grok-cli/skills/catalog-apply-and-ceiling/SKILL.md.",
    "Read bootstrap/grok-cli/skills/catalog-loop-operator/SKILL.md.",
    "Follow those skills, then this ticket.",
    "",
]
Path(dest).write_text(body + "\n".join(lines), encoding="utf-8")
PY
}

lock_env=()
if [ -n "${PFY_MODEL_LOCK:-}" ]; then
  lock_env=(--setenv=PFY_MODEL_LOCK="$PFY_MODEL_LOCK")
fi

queue_supersede_recheck() {
  local nnames stamp
  [ "$DRY" -eq 0 ] || return 0
  [ "$SUPERSEDE_ACTION" = "continue" ] || return 0
  [ "$slots" -gt 0 ] || return 0
  nnames=$(python3 -c 'import json,os; print(len(json.loads(os.environ.get("PFY_SUPERSEDE_STALE") or "[]")))')
  [ "$nnames" -gt 0 ] || return 0
  mkdir -p "$STATE/supersede"
  stamp="$STATE/supersede/tried-$(TZ=America/Los_Angeles date +%Y%m%d)"
  [ -f "$stamp" ] && return 0
  [ -f "$STATE/supersede/recheck.dispatched" ] && return 0
  [ -f "$STATE/supersede/recheck.parked" ] && return 0
  python3 - "$STATE/supersede/stale.txt" <<'PY'
import json, os, sys
from pathlib import Path
names = []
for line in json.loads(os.environ.get("PFY_SUPERSEDE_STALE") or "[]"):
    text = line.split(":", 1)[1].strip() if line.startswith("stale:") else line.strip()
    if text:
        names.append(text)
Path(sys.argv[1]).write_text("".join(name + "\n" for name in names), encoding="utf-8")
PY
  if ! (set -o noclobber; printf '%s\n' "loop-parent $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$STATE/supersede/recheck.dispatched") 2>/dev/null; then
    return 0
  fi
  printf '%s\n' "queued" > "$stamp"
  if ! "$SYSTEMD_RUN" --user --collect --unit="pfy-lane-supersede-recheck" --property=Nice=10 \
    --setenv=PFY_LANE_FROM_LOOP=1 \
    --setenv=PFY_LOOP_STATE="$STATE" \
    --setenv=PFY_LOOP_REPO="$REPO" \
    --setenv=PFY_GROK_BIN="${PFY_GROK_BIN:-grok}" \
    "${lock_env[@]+"${lock_env[@]}"}" \
    "$WT/scripts/supersede_recheck_lane.sh"; then
    fail "systemd-run failed for supersede recheck"
  fi
  launched+=("supersede-recheck")
  started=$((started + 1))
  printf '%s\n' "$started" > "$counter"
  if [ "$started" -ge 20 ]; then
    printf '%s\n' "daily cap 20" > "$STATE/QUOTA_STOP.auto"
    status_name=quota
    slots=0
  fi
}

launched=()
skipped=()
queue_supersede_recheck
if [ "$SUPERSEDE_ACTION" = "continue" ] && [ "$DRY" -eq 0 ] && [ -f eval/catalog-queue/queue.tsv ]; then
  while IFS=$'\t' read -r n slug mode gap entry card why; do
    [ "${n:-}" = "n" ] && continue
    [ -n "${slug:-}" ] || continue
    [ "${#launched[@]}" -ge "$slots" ] && break
    kind=$(python3 scripts/catalog_auto_raise.py --root "$PWD" --kind "$slug" | tail -n 1)
    if is_taken "$slug" "$kind"; then
      skipped+=("$slug")
      continue
    fi
    if needs_skip "$slug"; then
      skipped+=("$slug")
      continue
    fi
    check=$(python3 scripts/catalog_auto_raise.py --root "$PWD" --launch-check "$slug" | tail -n 1)
    check_action=${check%%$'\t'*}
    if [ "$check_action" != "launch" ]; then
      skipped+=("$slug")
      continue
    fi
    marker_dir="$STATE/$kind"
    mkdir -p "$marker_dir"
    marker="$marker_dir/${slug}.dispatched"
    if ! (set -o noclobber; printf '%s\n' "loop-parent $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$marker") 2>/dev/null; then
      skipped+=("$slug")
      continue
    fi
    sandbox_env=()
    if [ "${check##*$'\t'}" = "security-sandbox" ]; then
      # Security scanner or guard: the I2 trial runs under sandlock.
      sandbox_env=(--setenv=PFY_LANE_SANDBOX=sandlock)
    fi
    unit="pfy-lane-${kind}-${slug}"
    if [ "$kind" = "integrate" ]; then
      write_integrate_ticket "$slug" || fail "ticket write failed for $slug"
      launch_cmd=("$WT/scripts/integrate_lane.sh" --slug "$slug" --root "$WT" --ticket "$WT/tmp/TICKET-${slug}.md")
    else
      launch_cmd=("$WT/scripts/eval_lane.sh" --slug "$slug" --root "$WT" --state "$STATE/eval")
    fi
    if ! "$SYSTEMD_RUN" --user --collect --unit="$unit" --property=Nice=10 \
      --setenv=PFY_LANE_FROM_LOOP=1 \
      --setenv=PFY_LOOP_STATE="$STATE" \
      --setenv=PFY_LOOP_REPO="$REPO" \
      --setenv=PFY_GROK_BIN="${PFY_GROK_BIN:-grok}" \
      "${lock_env[@]+"${lock_env[@]}"}" \
      "${sandbox_env[@]+"${sandbox_env[@]}"}" \
      "${launch_cmd[@]}"; then
      fail "systemd-run failed for $slug"
    fi
    launched+=("$slug")
    started=$((started + 1))
    printf '%s\n' "$started" > "$counter"
    if [ "$started" -ge 20 ]; then
      printf '%s\n' "daily cap 20" > "$STATE/QUOTA_STOP.auto"
      status_name=quota
      break
    fi
  done < eval/catalog-queue/queue.tsv
fi

if [ "${#launched[@]}" -gt 0 ]; then
  PFY_LAUNCHED=$(json_list "${launched[@]}")
else
  PFY_LAUNCHED="[]"
fi
if [ "${#skipped[@]}" -gt 0 ]; then
  PFY_SKIPPED=$(json_list "${skipped[@]}")
else
  PFY_SKIPPED="[]"
fi
if [ "${#applied[@]}" -gt 0 ]; then
  PFY_APPLIED=$(json_list "${applied[@]}")
else
  PFY_APPLIED="[]"
fi
if [ "${#raised[@]}" -gt 0 ]; then
  PFY_RAISED=$(json_list "${raised[@]}")
else
  PFY_RAISED="[]"
fi
if [ "${#refused[@]}" -gt 0 ]; then
  refused_json=$(json_list "${refused[@]}")
else
  refused_json="[]"
fi
if [ "${#apply_refused[@]}" -gt 0 ]; then
  apply_json=$(json_list "${apply_refused[@]}")
else
  apply_json="[]"
fi
# Drop a slug this tick auto-raised. Keep each remaining slug once.
# apply_refused keeps every apply failure, including one that was raised.
filtered=$(python3 -c '
import json, sys
raised = set(json.loads(sys.argv[1]))
seen = []
for slug in json.loads(sys.argv[2]):
    if slug in raised or slug in seen:
        continue
    seen.append(slug)
apply_seen = []
for slug in json.loads(sys.argv[3]):
    if slug not in apply_seen:
        apply_seen.append(slug)
sys.stdout.write(json.dumps(seen) + "\n" + json.dumps(apply_seen) + "\n")
' "$PFY_RAISED" "$refused_json" "$apply_json")
PFY_REFUSED=$(printf '%s\n' "$filtered" | awk 'NR==1')
PFY_APPLY_REFUSED=$(printf '%s\n' "$filtered" | awk 'NR==2')
export PFY_LAUNCHED PFY_SKIPPED PFY_APPLIED PFY_RAISED PFY_REFUSED PFY_APPLY_REFUSED
export PFY_STARTED_TODAY="$started"
export PFY_SLOTS="$slots"
export PFY_ORIGIN_MAIN
PFY_ORIGIN_MAIN=$(git rev-parse origin/main 2>/dev/null || true)
export PFY_ORIGIN_MAIN
write_status "$status_name"
printf '%s\n' "status=${status_name}"
exit 0
