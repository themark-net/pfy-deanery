#!/bin/sh
# Entry inside the lane container. Starts the loopback forwarder to the
# driver's egress proxy, then execs the lane command. The container has no
# network besides loopback, so the proxy allowlist is the only way out.
set -eu
if [ -n "${PFY_CAGE_PROXY_SOCK:-}" ] && [ "${PFY_CAGE_FAKE:-0}" != "1" ]; then
  python3 "$PFY_CAGE_FORWARDER" "${PFY_CAGE_PROXY_PORT:-3128}" "$PFY_CAGE_PROXY_SOCK" &
  i=0
  while [ "$i" -lt 50 ]; do
    python3 -c 'import socket,sys; s=socket.socket(); s.settimeout(0.2); s.connect(("127.0.0.1", int(sys.argv[1])))' "${PFY_CAGE_PROXY_PORT:-3128}" 2>/dev/null && break
    i=$((i + 1)); sleep 0.1
  done
fi
exec "$@"
