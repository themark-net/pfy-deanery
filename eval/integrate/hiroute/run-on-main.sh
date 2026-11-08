#!/bin/bash
# Offline dry classification for the HiRoute difficulty router.
# no-listen: do not bind a port. Do not use port 11434. Do not start a daemon.
# A missing binary, a required socket, a listen, or a timeout writes no receipt.
# This script does not create the dispatched marker and does not push.
# modular-ci: no .github/workflows job, no ci/ job, no model_lock.sh
# extra lock: flock eval/integrate/hiroute/hiroute-ff.lock
# The main push is a fast-forward under that flock. A second start exits 2.
# Difficulty classification is the gateway listener plus a decision hop.
# schema show and routing preview are Local Control commands and need that socket.
# There is no offline classify command. Do not exec hiroute. Do not signal Ollama.

set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/hiroute/run-on-main.sh RECEIPT.json" >&2
  exit 2
fi

dest=$1
marker=/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/hiroute.dispatched
if [ -e "$marker" ]; then
  printf '%s\n' "already dispatched: $marker" >&2
  exit 2
fi

if [ -n "${HIROUTE_BIN+x}" ]; then
  bin=$HIROUTE_BIN
else
  bin=${HOME:-/nonexistent}/.cache/pfy/tools/hiroute/home/.local/bin/hiroute
fi
if [ ! -x "$bin" ]; then
  printf '%s\n' "hiroute binary missing; no receipt" >&2
  exit 1
fi

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$here/../../.." && pwd)
cd "$root"

if ! git rev-parse --verify --quiet 'origin/main^{commit}' >/dev/null 2>&1; then
  printf '%s\n' "origin/main is missing; no receipt" >&2
  exit 1
fi
sha=$(git rev-parse HEAD)
if ! git merge-base --is-ancestor "$sha" origin/main; then
  printf '%s\n' "HEAD is not an ancestor of origin/main; no receipt" >&2
  exit 1
fi

# no-listen. Port 11434 is Ollama and is not a classification path.
printf '%s\n' "classification needs a listener; no-listen; no receipt: $dest" >&2
exit 1
