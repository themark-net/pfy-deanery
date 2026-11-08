#!/bin/bash
# Run a command in a detached worktree at origin/main.
# Usage: scripts/loop_worktree.sh [--wt DIR] -- <command...>
# DIR defaults to ${PFY_LOOP_WT:-$HOME/DEVELOP/pfy-mentat/tmp/loop/wt}.
# The repo defaults to ${PFY_LOOP_REPO:-$HOME/DEVELOP/pfy-mentat}.
# Only fetch and worktree add touch that repo. Its working tree is left alone.
# A busy lock on DIR/../loop-worktree.lock exits 75 and does not run the command.
set -euo pipefail

export GIT_TERMINAL_PROMPT=0

WT="${PFY_LOOP_WT:-$HOME/DEVELOP/pfy-mentat/tmp/loop/wt}"
REPO="${PFY_LOOP_REPO:-$HOME/DEVELOP/pfy-mentat}"

usage() {
  echo "usage: scripts/loop_worktree.sh [--wt DIR] -- <command...>" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --wt)
      [[ $# -ge 2 ]] || usage
      WT=$2
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage
      ;;
  esac
done

[[ $# -ge 1 ]] || usage

if [[ ! -d "$REPO" ]]; then
  echo "refusing: repo is not a directory: $REPO" >&2
  exit 2
fi

REPO_ABS=$(realpath -m "$REPO")
WT_ABS=$(realpath -m "$WT")

if [[ "$WT_ABS" == "$REPO_ABS" ]]; then
  echo "refusing: worktree dir is the repo top-level: $WT_ABS" >&2
  exit 2
fi

parent=$(dirname "$WT_ABS")
mkdir -p "$parent"
lock="$parent/loop-worktree.lock"
exec 9>>"$lock"
if ! flock -n 9; then
  echo "loop worktree lock is busy: $lock" >&2
  exit 75
fi

is_our_worktree() {
  local top common repo_common
  top=$(git -C "$WT_ABS" rev-parse --path-format=absolute --show-toplevel 2>/dev/null) || return 1
  [[ "$top" == "$WT_ABS" ]] || return 1
  common=$(git -C "$WT_ABS" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || return 1
  repo_common=$(git -C "$REPO_ABS" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || return 1
  [[ "$common" == "$repo_common" ]]
}

if [[ -e "$WT_ABS" ]]; then
  if ! is_our_worktree; then
    echo "refusing: $WT_ABS is not a worktree of $REPO_ABS" >&2
    exit 2
  fi
else
  git -C "$REPO_ABS" fetch -q origin
  git -C "$REPO_ABS" worktree add --detach "$WT_ABS" origin/main
fi

git -C "$WT_ABS" fetch -q origin
git -C "$WT_ABS" reset -q --hard origin/main
git -C "$WT_ABS" clean -qfdx -e tmp/

cd "$WT_ABS"
"$@"
