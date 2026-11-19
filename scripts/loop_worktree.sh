#!/bin/bash
# Run a command in a detached worktree at origin/main, or at PFY_LOOP_REF when set.
# Usage: scripts/loop_worktree.sh [--wt DIR] -- <command...>
# DIR defaults to ${PFY_LOOP_WT:-$PFY_TMP/loop/wt}.
# The repo defaults to ${PFY_LOOP_REPO:-$PFY_ROOT}.
# Only fetch and worktree add touch that repo. Its working tree is left alone.
# A busy lock on DIR/../loop-worktree.lock exits 75 and does not run the command.
set -euo pipefail

# Generic path defaults (no private checkout layout).
: "${PFY_ROOT:=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
: "${PFY_TMP:=${PFY_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || printf %s "${XDG_CACHE_HOME:-${HOME}/.cache}/pfy")}/tmp}"

export GIT_TERMINAL_PROMPT=0

WT="${PFY_LOOP_WT:-$PFY_TMP/loop/wt}"
REPO="${PFY_LOOP_REPO:-$PFY_ROOT}"
# PFY_LOOP_REF pins the loop to a reviewed commit instead of origin/main.
# It must be a full 40-hex SHA or a tag named loop-reviewed-*, and it must
# already be on origin/main. Unset keeps the old behavior (origin/main).
LOOP_REF="${PFY_LOOP_REF:-}"

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

git -C "$WT_ABS" fetch -q --tags origin
target=origin/main
if [[ -n "$LOOP_REF" ]]; then
  if [[ ! "$LOOP_REF" =~ ^[0-9a-f]{40}$ && ! "$LOOP_REF" =~ ^loop-reviewed-[A-Za-z0-9._-]+$ ]]; then
    echo "refusing: PFY_LOOP_REF must be a full commit SHA or a loop-reviewed-* tag: $LOOP_REF" >&2
    exit 2
  fi
  pinned=$(git -C "$WT_ABS" rev-parse --verify -q "${LOOP_REF}^{commit}") || {
    echo "refusing: PFY_LOOP_REF not found: $LOOP_REF" >&2
    exit 2
  }
  if ! git -C "$WT_ABS" merge-base --is-ancestor "$pinned" origin/main; then
    echo "refusing: PFY_LOOP_REF $LOOP_REF is not on origin/main (not reviewed)" >&2
    exit 2
  fi
  target=$pinned
  echo "loop pinned to $pinned ($LOOP_REF)" >&2
fi
git -C "$WT_ABS" reset -q --hard "$target"
git -C "$WT_ABS" clean -qfdx -e tmp/

cd "$WT_ABS"
"$@"
