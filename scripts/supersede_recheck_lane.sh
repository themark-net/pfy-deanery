#!/bin/bash
# One supersede recheck. Public web, GitHub, and X reads only.
# No installs, no GPU, no model pulls. Updates data/supersede-watchlist.json
# coverage and last_checked, then fast-forwards that one file onto main.
#
# The catalog loop writes STATE/supersede/recheck.dispatched and
# STATE/supersede/stale.txt before systemd-run. PFY_LANE_FROM_LOOP=1
# continues when that marker already exists.
set -euo pipefail
export GIT_TERMINAL_PROMPT=0
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
STATE="${PFY_LOOP_STATE:-$HOME/DEVELOP/pfy-mentat/tmp/loop}"
REPO="${PFY_LOOP_REPO:-$HOME/DEVELOP/pfy-mentat}"
MARK_DIR="$STATE/supersede"
WT="$MARK_DIR/wt"
MARKER="$MARK_DIR/recheck.dispatched"
PARKED="$MARK_DIR/recheck.parked"
DONE="$MARK_DIR/recheck.done"
PROGRESS="$MARK_DIR/progress.md"
STALE="$MARK_DIR/stale.txt"
GROK_BIN="${PFY_GROK_BIN:-grok}"

dcg_check() {
  local guard="$SCRIPT_DIR/integrations/dcg/guard.sh"
  if [ ! -f "$guard" ]; then
    return 0
  fi
  bash "$guard" "$@"
}

run_checked() {
  dcg_check "$@" || return $?
  "$@"
}

progress() {
  mkdir -p "$MARK_DIR"
  printf '%s\n' "$1" >> "$PROGRESS"
}

park_exit() {
  local msg="$1"
  local code="${2:-1}"
  mkdir -p "$MARK_DIR"
  printf '%s\n' "$msg" > "$PARKED"
  progress "parked $msg"
  if [ -d "$WT" ]; then
    git -C "$REPO" worktree remove --force "$WT" >/dev/null 2>&1 || true
  fi
  printf '%s\n' "parked $msg" >&2
  exit "$code"
}

if [ "${PFY_LANE_FROM_LOOP:-}" != "1" ] && [ -f "$MARKER" ]; then
  printf '%s\n' "already dispatched: supersede-recheck" >&2
  exit 2
fi
mkdir -p "$MARK_DIR"
if [ ! -f "$MARKER" ]; then
  if ! (set -o noclobber; printf '%s\n' "pid $$" > "$MARKER") 2>/dev/null; then
    printf '%s\n' "already dispatched: supersede-recheck" >&2
    exit 2
  fi
fi
if [ ! -s "$STALE" ]; then
  park_exit "no stale projects"
fi

if [ -e "$WT" ]; then
  park_exit "worktree path exists"
fi
run_checked git -C "$REPO" fetch origin >&2 || park_exit "git fetch failed"
run_checked git -C "$REPO" worktree add --detach "$WT" origin/main >&2 || park_exit "worktree add failed"
progress "worktree ready"

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

prompt="$MARK_DIR/recheck.prompt"
{
  printf '%s\n' "$skill_reads"
  printf '%s\n' "Update data/supersede-watchlist.json for these stale projects:"
  cat "$STALE"
  printf '%s\n' "Public web, GitHub, and X reads only. No installs. No GPU. No pulls. No stage card edits."
  printf '%s\n' "Update coverage and last_checked only. Leave every other file untouched."
} > "$prompt"

if ! (
  cd "$WT"
  run_checked bash "$SCRIPT_DIR/model_lock.sh" "$GROK_BIN" --cwd "$WT" --always-approve --output-format plain --prompt-file "$prompt"
) >"$MARK_DIR/recheck.log" 2>&1; then
  park_exit "grok failed"
fi

only_watchlist() {
  local rel
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    [ "$rel" = "data/supersede-watchlist.json" ] || return 1
  done
  return 0
}

dirty=$(git -C "$WT" status --porcelain)
if [ -n "$dirty" ]; then
  printf '%s\n' "$dirty" | awk '{print substr($0, 4)}' | only_watchlist || park_exit "unexpected edits"
  run_checked git -C "$WT" add -- data/supersede-watchlist.json || park_exit "git add failed"
  run_checked git -C "$WT" commit -m "catalog: recheck stale supersede projects" || park_exit "commit failed"
fi

changed=$(git -C "$WT" diff --name-only origin/main...HEAD || true)
if [ -z "$changed" ]; then
  printf '%s\n' "no-change" > "$DONE"
  rm -f "$MARKER"
  git -C "$REPO" worktree remove --force "$WT" >/dev/null 2>&1 || true
  progress "no change"
  exit 0
fi
printf '%s\n' "$changed" | only_watchlist || park_exit "commit is not only the watchlist"
python3 -c 'import json,sys; json.load(open(sys.argv[1], encoding="utf-8"))' "$WT/data/supersede-watchlist.json" || park_exit "watchlist is not json"
(
  cd "$WT"
  python3 scripts/supersede_check.py
) || park_exit "supersede_check still exits 1"

sha=$(git -C "$WT" rev-parse HEAD)
attempt=1
while [ "$attempt" -le 3 ]; do
  run_checked git -C "$REPO" fetch origin >&2 || park_exit "git fetch failed"
  if run_checked git -C "$REPO" merge-base --is-ancestor origin/main "$sha"; then
    if run_checked git -C "$REPO" push origin "${sha}:refs/heads/main" >&2; then
      printf '%s\n' "$sha" > "$DONE"
      printf '%s\n' "$sha" > "$MARK_DIR/LANDED_recheck"
      rm -f "$MARKER"
      git -C "$REPO" worktree remove --force "$WT" >/dev/null 2>&1 || true
      progress "landed $sha"
      printf '%s\n' "landed $sha"
      exit 0
    fi
  fi
  if ! GIT_EDITOR=: GIT_SEQUENCE_EDITOR=: run_checked git -C "$WT" rebase origin/main >&2; then
    git -C "$WT" rebase --abort >&2 || true
    park_exit "rebase failed"
  fi
  sha=$(git -C "$WT" rev-parse HEAD)
  attempt=$((attempt + 1))
done
park_exit "push failed"
