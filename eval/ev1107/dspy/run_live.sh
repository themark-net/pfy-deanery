#!/bin/sh
# One live DSPy step under the host model lock.
# The lock path is the real home lock. HOME for the python process is the
# cache dir, so DSPy and LiteLLM do not write the operator home.
# Install lives in ~/.cache/pfy/tools/dspy (dspy==3.4.1). This script does not
# install, pull a model, or unload anyone else's model.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/../../.." && pwd)
REAL_HOME=$HOME
CACHE=${PFY_DSPY_CACHE:-"$REAL_HOME/.cache/pfy/tools/dspy"}
export PFY_DSPY_CACHE="$CACHE"
export PFY_MODEL_LOCK="$REAL_HOME/.cache/pfy/locks/local-model.lock"
mkdir -p "$CACHE/home" "$CACHE/xdg-cache" "$CACHE/xdg-config" "$CACHE/tmp" "$CACHE/dspy-cache"
echo "taking model lock $PFY_MODEL_LOCK" >&2
exec "$ROOT/scripts/model_lock.sh" env \
  HOME="$CACHE/home" \
  XDG_CACHE_HOME="$CACHE/xdg-cache" \
  XDG_CONFIG_HOME="$CACHE/xdg-config" \
  TMPDIR="$CACHE/tmp" \
  DSPY_CACHEDIR="$CACHE/dspy-cache" \
  PFY_DSPY_CACHE="$CACHE" \
  LITELLM_LOCAL_MODEL_COST_MAP=True \
  NO_PROXY=127.0.0.1,localhost \
  UV_PYTHON_DOWNLOADS=never \
  "$CACHE/venv/bin/python" "$ROOT/eval/ev1107/dspy/live.py" "$@"
