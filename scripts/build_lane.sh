#!/bin/bash
# Confined Grok Build lane: replaces `grok -p ... --always-approve` in
# an operator's Build lane run-lane.sh scripts. The agent runs in scripts/lane_cage.py
# (rootless podman, no ~/.ssh, throwaway GROK_HOME with memory off, egress
# only to xAI, tool allowlist, web off). It can commit in its worktree; the
# driver (the operator or Grok Bot) reviews and pushes.
#
# usage: scripts/build_lane.sh --wt WORKTREE --prompt FILE [--log FILE] [--max-turns N] [--timeout S]
# The prompt gets the fixed data-not-instructions preamble prepended.
set -euo pipefail
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WT="" PROMPT="" LOG="/dev/stderr" TURNS=250 TIMEOUT=7200
while [ $# -gt 0 ]; do
  case "$1" in
    --wt) WT=$2; shift 2 ;;
    --prompt) PROMPT=$2; shift 2 ;;
    --log) LOG=$2; shift 2 ;;
    --max-turns) TURNS=$2; shift 2 ;;
    --timeout) TIMEOUT=$2; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -d "$WT" ] && [ -f "$PROMPT" ] || { echo "usage: build_lane.sh --wt DIR --prompt FILE" >&2; exit 2; }
git -C "$WT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "refusing: $WT is not a git worktree" >&2; exit 2; }
full=$(mktemp "${TMPDIR:-/tmp}/build-lane-prompt.XXXXXX")
cage_log=$(mktemp "${TMPDIR:-/tmp}/build-lane-cage.XXXXXX")
trap 'rm -f "$full" "$cage_log"' EXIT
{
  python3 "$SCRIPT_DIR/../pfylib/untrusted_text.py" preamble
  printf '\n'
  cat "$PROMPT"
} > "$full"
rc=0
python3 "$SCRIPT_DIR/lane_cage.py" grok --kind build --wt "$WT" --prompt "$full" \
  --max-turns "$TURNS" --timeout "$TIMEOUT" > "$cage_log" 2>&1 || rc=$?
cat "$cage_log" > "$LOG" || true
if [ "$rc" -eq 2 ] && grep -q '^lane-cage: copy-back refused' "$cage_log"; then
  exit 6
fi
exit "$rc"
