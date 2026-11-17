# Cost-gate a parked-lane Grok prompt with pfylib.cloud_cost_gate (11/11 rules).
# Usage: gate_cloud_call --prompt-file PATH
# Exit 0 = allowed, 4 = skip with $0 spend, 1 = usage/error.
# Source this file; it does not start grok.
# shellcheck shell=bash

gate_cloud_call() {
  local prompt_file="" root
  if [ "${1:-}" = "--prompt-file" ]; then
    prompt_file=${2:-}
  else
    prompt_file=${1:-}
  fi
  if [ -z "$prompt_file" ] || [ ! -f "$prompt_file" ]; then
    printf '%s\n' "skipping: prompt file missing. \$0 spend. No model was called." >&2
    return 4
  fi
  root="${GATE_CLOUD_ROOT:-${ROOT:-}}"
  if [ -z "$root" ]; then
    root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
  fi
  PYTHONPATH="$root${PYTHONPATH:+:$PYTHONPATH}" python3 -m pfylib.cloud_cost_gate --prompt-file "$prompt_file"
}
