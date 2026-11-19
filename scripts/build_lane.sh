#!/bin/bash
# Confined Grok Build lane: replaces `grok -p ... --always-approve` in
# ~/DEVELOP/lanes-*/run-lane.sh. The agent runs in scripts/lane_cage.py
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
case "$(realpath "$WT")" in
  */DEVELOP/pfy-mentat|*/DEVELOP/pfy-mentat/*) echo "refusing: never run a lane in ~/DEVELOP/pfy-mentat" >&2; exit 2 ;;
esac
full=$(mktemp "${TMPDIR:-/tmp}/build-lane-prompt.XXXXXX")
trap 'rm -f "$full"' EXIT
{
  python3 "$SCRIPT_DIR/../pfylib/untrusted_text.py" preamble
  printf '\n'
  cat "$PROMPT"
} > "$full"
rc=0
python3 "$SCRIPT_DIR/lane_cage.py" grok --kind build --wt "$WT" --prompt "$full" \
  --max-turns "$TURNS" --timeout "$TIMEOUT" > "$LOG" 2>&1 || rc=$?
exit "$rc"
