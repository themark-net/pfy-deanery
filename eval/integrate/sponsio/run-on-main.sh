#!/bin/bash
# Offline pre-call check of one fixture tool call.
# The pinned wheel must already be cached. This script does not fetch it.
# Missing wheel, import error, or timeout writes no receipt.
# A timeout is not a pass.
#
# Skill writes stay as they are when this script is not called.
#
# A second start that finds
# /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/sponsio.dispatched
# exits 2 and writes no receipt, unless that marker's pid is an ancestor of
# this process. The driver writes "pid <lane-pid>" and still holds the marker
# when it runs this script, so that admitted lane continues.
# This script does not create the marker and does not push.
#
# extra lock: flock /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/push.lock
# The main fast-forward uses that flock. This script does not take it.
# The temp env is the only lock this script uses.
#
# Usage: eval/integrate/sponsio/run-on-main.sh RECEIPT.json

set -euo pipefail

work=
receipt_tmp=
cleanup() {
  if [ -n "${receipt_tmp:-}" ]; then
    rm -f "$receipt_tmp"
  fi
  if [ -n "${work:-}" ]; then
    rm -rf "$work"
  fi
}
trap cleanup EXIT

marker_pid_is_ancestor() {
  local file=$1
  local target cur guard ppid
  target=$(sed -n 's/^pid \([0-9][0-9]*\)[[:space:]]*$/\1/p' "$file" 2>/dev/null | head -n 1 || true)
  target=${target%%$'\n'*}
  if [ -z "$target" ]; then
    return 1
  fi
  cur=$$
  guard=0
  while [ "$cur" -gt 1 ] && [ "$guard" -lt 40 ]; do
    if [ "$cur" = "$target" ]; then
      return 0
    fi
    if [ ! -r "/proc/$cur/status" ]; then
      return 1
    fi
    ppid=$(awk '/^PPid:/ {print $2}' "/proc/$cur/status" 2>/dev/null || true)
    if [ -z "$ppid" ] || [ "$ppid" = "$cur" ]; then
      return 1
    fi
    cur=$ppid
    guard=$((guard + 1))
  done
  return 1
}

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/sponsio/run-on-main.sh RECEIPT.json" >&2
  exit 2
fi

receipt=$1
if [ "${receipt#/}" = "$receipt" ]; then
  receipt="$PWD/$receipt"
fi

marker=${SPONSIO_LANE_MARKER:-/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/sponsio.dispatched}
if [ -e "$marker" ]; then
  if ! marker_pid_is_ancestor "$marker"; then
    printf '%s\n' "already dispatched: $marker" >&2
    exit 2
  fi
fi

if ! root=$(git rev-parse --show-toplevel 2>/dev/null); then
  printf '%s\n' "not a git checkout; no receipt" >&2
  exit 1
fi
cd "$root"

if ! git rev-parse --verify --quiet 'origin/main^{commit}' >/dev/null; then
  printf '%s\n' "origin/main is missing; no receipt" >&2
  exit 1
fi
sha=$(git rev-parse HEAD)
if ! git merge-base --is-ancestor "$sha" origin/main; then
  printf '%s\n' "HEAD is not an ancestor of origin/main; no receipt" >&2
  exit 1
fi
if [[ ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
  printf '%s\n' "main_sha is not 40 hex characters; no receipt" >&2
  exit 1
fi

cache=${SPONSIO_CACHE:-/home/mark/.cache/pfy/tools/sponsio}
wheel=${SPONSIO_WHEEL:-$cache/wheels/sponsio-0.2.0a17-py3-none-any.whl}
expected=0e755cf9027da62051d3b05ec92a3557f34ec97aac142bc47704be16d86f0809
if [ ! -f "$wheel" ]; then
  printf '%s\n' "pinned wheel is not cached; no receipt" >&2
  exit 1
fi
actual=$(sha256sum "$wheel" | awk '{print $1}')
if [ "$actual" != "$expected" ]; then
  printf '%s\n' "pinned wheel sha256 mismatch; no receipt" >&2
  exit 1
fi

work=$(mktemp -d "${TMPDIR:-/tmp}/sponsio-integrate.XXXXXX")
mkdir -p "$work/home" "$work/tmp" "$work/config" "$work/cache" "$work/pkg"
python3 -m venv --without-pip "$work/venv"
python3 -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$wheel" "$work/pkg"

pyver=$(python3 -c 'import sys; print("%d.%d" % (sys.version_info[0], sys.version_info[1]))')
deps="$cache/venv/lib/python${pyver}/site-packages"
pypath=$work/pkg
if [ -d "$deps" ]; then
  pypath=$pypath:$deps
fi

result=$work/version.txt
set +e
timeout 30 env -i \
  HOME="$work/home" \
  TMPDIR="$work/tmp" \
  XDG_CONFIG_HOME="$work/config" \
  XDG_CACHE_HOME="$work/cache" \
  PATH="/usr/bin:/bin" \
  LANG="${LANG:-C.UTF-8}" \
  SPONSIO_NO_AUTO_PUSH=1 \
  PYTHONNOUSERSITE=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="$pypath" \
  VIRTUAL_ENV="$work/venv" \
  "$work/venv/bin/python" - "$work" "$work/pkg" >"$result" <<'PY'
import os
import sys
from pathlib import Path

work = Path(sys.argv[1])
pkg = Path(sys.argv[2]).resolve()
os.chdir(work)
try:
    import sponsio
except Exception as exc:
    sys.stderr.write("import error: %s\n" % exc)
    raise SystemExit(1)
src = Path(sponsio.__file__).resolve()
if pkg != src and pkg not in src.parents:
    sys.stderr.write("import did not load the pinned wheel\n")
    raise SystemExit(1)
version = getattr(sponsio, "__version__", "") or ""
if version != "0.2.0a17":
    sys.stderr.write("unexpected version\n")
    raise SystemExit(1)
ws = work / "ws"
ws.mkdir(parents=True, exist_ok=True)
cfg = work / "check.yaml"
cfg.write_text(
    'version: "1"\n'
    "agents:\n"
    "  probe:\n"
    '    workspace: "%s"\n'
    "    include:\n"
    "      - sponsio:capability/shell\n" % ws,
    encoding="utf-8",
)
guard = sponsio.Sponsio(
    config=str(cfg),
    agent_id="probe",
    mode="enforce",
    verbose=False,
    verbosity=0,
    init_banner=False,
    auto_summary=False,
    dashboard=False,
)
checked = guard.guard_before("exec", {"command": "rm -rf /"})
if bool(checked.allowed):
    sys.stderr.write("destructive command was allowed\n")
    raise SystemExit(1)
sys.stdout.write(version + "\n")
PY
rc=$?
set -e
if [ "$rc" -eq 124 ]; then
  printf '%s\n' "timeout is not a pass; no receipt" >&2
  exit 124
fi
if [ "$rc" -ne 0 ]; then
  printf '%s\n' "fixture check failed; no receipt" >&2
  exit "$rc"
fi
version=$(head -n 1 "$result" | tr -d '\r')
if [ -z "$version" ]; then
  printf '%s\n' "tool version missing; no receipt" >&2
  exit 1
fi

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
dest_dir=$(dirname -- "$receipt")
mkdir -p "$dest_dir"
receipt_tmp=$(mktemp "$dest_dir/.receipt.XXXXXX")
export RECEIPT_TMP=$receipt_tmp
export RECEIPT_SHA=$sha
export RECEIPT_RUN_ID="sponsio-${sha:0:12}-${started}"
export RECEIPT_STARTED=$started
export RECEIPT_FINISHED=$finished
export RECEIPT_VERSION="sponsio $version"
export RECEIPT_DID="Checked one fixture exec call with the pinned wheel in a temp env. The destructive command was denied."
python3 - <<'PY'
import json
import os
from pathlib import Path

doc = {
    "slug": "sponsio",
    "run_kind": "pipeline",
    "main_sha": os.environ["RECEIPT_SHA"],
    "run_id": os.environ["RECEIPT_RUN_ID"],
    "started": os.environ["RECEIPT_STARTED"],
    "finished": os.environ["RECEIPT_FINISHED"],
    "outcome": "ok",
    "tool_version": os.environ["RECEIPT_VERSION"],
    "did": os.environ["RECEIPT_DID"],
}
Path(os.environ["RECEIPT_TMP"]).write_text(
    json.dumps(doc, indent=2) + "\n",
    encoding="utf-8",
)
PY
mv -f "$receipt_tmp" "$receipt"
receipt_tmp=
printf '%s\n' "$receipt"
