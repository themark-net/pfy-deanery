#!/bin/sh
# One model-bound ngram step on a commit that is already on origin/main.
# Usage: eval/integrate/llama-cpp-ngram-mod/run-on-main.sh RECEIPT.json
# The whole step runs inside scripts/model_lock.sh. Exit nonzero when HEAD
# is not an ancestor of origin/main, or when a receipt for that sha exists.
set -eu
if [ "$#" -ne 1 ]; then
  echo "usage: eval/integrate/llama-cpp-ngram-mod/run-on-main.sh RECEIPT.json" >&2
  exit 2
fi
out=$1
root=$(CDPATH= cd -- "$(dirname "$0")/../../.." && pwd)
cd "$root"
sha=$(git rev-parse HEAD)
if ! git merge-base --is-ancestor "$sha" origin/main; then
  echo "HEAD $sha is not an ancestor of origin/main" >&2
  exit 1
fi
# Known local blob only. Never download. Unset stays unset when the file is absent.
if [ -z "${PFY_LLAMA_NGRAM_MODEL:-}" ]; then
  known=/usr/share/ollama/.ollama/models/blobs/sha256-60e05f2100071479f596b964f89f510f057ce397ea22f2833a0cfe029bfc2463
  if [ -f "$known" ]; then
    PFY_LLAMA_NGRAM_MODEL=$known
    export PFY_LLAMA_NGRAM_MODEL
  fi
fi
export PFY_LLAMA_NGRAM=1
export PFY_LLAMA_NGRAM_SHA=$sha
export PFY_LLAMA_NGRAM_RECEIPT=$out
exec "$root/scripts/model_lock.sh" python3 "$root/scripts/integrations/llama_ngram/run.py" --receipt-out "$out"
