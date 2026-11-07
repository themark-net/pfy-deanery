#!/bin/sh
# Hold the local-model lock for the duration of one command.
#
#   scripts/model_lock.sh <command> [args...]
#
# Lock file: ${PFY_MODEL_LOCK:-$HOME/.cache/pfy/locks/local-model.lock}
# Landings (pregate, G0, scripts/run_tests.py) do not call this and do not
# wait on it. A nested call sees PFY_MODEL_LOCK_HELD=1 and runs the command
# without taking the lock again, so a Make target can wrap a recipe that
# itself calls model_lock.sh.
#
# The old ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock file is not used here.
# Light jobs must not flock that path either.
set -eu
if [ "$#" -lt 1 ]; then
  echo "usage: scripts/model_lock.sh <command> [args...]" >&2
  exit 2
fi
if [ "${PFY_MODEL_LOCK_HELD:-}" = "1" ]; then
  exec "$@"
fi
lock="${PFY_MODEL_LOCK:-$HOME/.cache/pfy/locks/local-model.lock}"
mkdir -p "$(dirname "$lock")"
exec flock "$lock" env PFY_MODEL_LOCK_HELD=1 "$@"
