#!/bin/bash
# Run the Agent Autoloop trial confined:
# - its own user+network namespace (unshare -rn): loopback only, no route out;
#   the one way to the local model is a unix socket ($STAGE/ollama.sock)
#   forwarded to Ollama on 127.0.0.1:11434 by sock_proxy.py outside;
# - sandlock --no-supervisor (Landlock): reads on system dirs, the autoloop
#   checkout, node 24 and these scripts; writes only in the stage dir under
#   ./tmp; clean env; throwaway HOME. The real home is not readable.
#   Supervisor mode is not used: in sandlock 0.8.9 its readlink returns ENOENT
#   for a non-symlink, which breaks glibc realpath (Node fs.realpath.native),
#   and --no-supervisor cannot take --net-allow, so Landlock TCP rules are
#   off (--disable net-tcp) and the namespace is the network boundary.
# Usage: run_trial.sh STAGE SRC NODE_DIR [PORT]
set -euo pipefail
STAGE=$(realpath -m "$1"); SRC=$(realpath "$2"); NODE_DIR=$(realpath "$3"); PORT=${4:-3391}
HERE=$(cd "$(dirname "$0")" && pwd)
SANDLOCK=${SANDLOCK_REAL:-$HOME/.cache/pfy/tools/sandlock/unpack/sandlock}
rm -rf "$STAGE"; mkdir -p "$STAGE"
python3 "$HERE/sock_proxy.py" "$STAGE/ollama.sock" 127.0.0.1:11434 &
PROXY=$!
trap 'kill $PROXY 2>/dev/null || true' EXIT
for _ in $(seq 50); do [ -S "$STAGE/ollama.sock" ] && break; sleep 0.1; done
rc=0
timeout 900 unshare -rn /bin/sh -c 'ip link set lo up && exec "$@"' sh \
  "$SANDLOCK" run --no-supervisor \
  -r /usr -r /lib -r /lib64 -r /bin -r /etc -r /proc -r /dev \
  -r "$SRC" -r "$NODE_DIR" -r "$HERE" \
  -w "$STAGE" -r "$STAGE" -w /dev/null \
  --disable net-tcp --clean-env \
  --env "STAGE=$STAGE" --env "SRC=$SRC" --env "NODE=$NODE_DIR/bin/node" \
  --env "LANE_BIN=$HERE" --env "PORT=$PORT" --env "PATH=$NODE_DIR/bin:/usr/bin:/bin" \
  --env "REAL_HOME=$HOME" --env "HOME=$STAGE/home" --env "LANG=C.UTF-8" \
  -- /usr/bin/python3 "$HERE/trial_driver.py" || rc=$?
exit $rc
