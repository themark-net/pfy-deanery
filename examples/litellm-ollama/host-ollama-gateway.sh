#!/usr/bin/env bash
# User-space TCP gateway: 0.0.0.0:GATEWAY_PORT → 127.0.0.1:OLLAMA_PORT
# So Docker/cage can reach host Ollama without sudo rebinding Ollama.
set -euo pipefail

GATEWAY_PORT="${OLLAMA_GATEWAY_PORT:-11435}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
# Pid and log follow XDG_RUNTIME_DIR, then TMPDIR, then /tmp.
PID_FILE="${OLLAMA_GATEWAY_PID_FILE:-${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}/pfy-mentat-ollama-gateway.pid}"
LOG_FILE="${OLLAMA_GATEWAY_LOG:-${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}/pfy-mentat-ollama-gateway.log}"

if [[ "${1:-}" == "--paths" ]]; then
  printf '%s\n' "$PID_FILE" "$LOG_FILE"
  exit 0
fi

cmd="${1:-status}"

is_running() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(cat "$PID_FILE" 2>/dev/null || true)
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

start() {
  if is_running; then
    echo "host-ollama-gateway already running (pid $(cat "$PID_FILE")) on :$GATEWAY_PORT"
    return 0
  fi
  # Ensure local Ollama answers
  if ! curl -sS -m 2 "http://127.0.0.1:${OLLAMA_PORT}/api/tags" >/dev/null; then
    echo "error: Ollama not reachable at 127.0.0.1:${OLLAMA_PORT}" >&2
    exit 1
  fi
  nohup python3 - "$GATEWAY_PORT" "$OLLAMA_PORT" >>"$LOG_FILE" 2>&1 <<'PY' &
import socket, select, sys, threading

listen_port = int(sys.argv[1])
target_port = int(sys.argv[2])
target_host = "127.0.0.1"

def pipe(a, b):
    try:
        while True:
            data = a.recv(65536)
            if not data:
                break
            b.sendall(data)
    except Exception:
        pass
    finally:
        try:
            a.shutdown(socket.SHUT_RD)
        except Exception:
            pass
        try:
            b.shutdown(socket.SHUT_WR)
        except Exception:
            pass

def handle(client):
    try:
        upstream = socket.create_connection((target_host, target_port), timeout=30)
    except Exception as e:
        try:
            client.close()
        except Exception:
            pass
        return
    t1 = threading.Thread(target=pipe, args=(client, upstream), daemon=True)
    t2 = threading.Thread(target=pipe, args=(upstream, client), daemon=True)
    t1.start(); t2.start()
    t1.join(); t2.join()
    try:
        client.close()
    except Exception:
        pass
    try:
        upstream.close()
    except Exception:
        pass

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("0.0.0.0", listen_port))
srv.listen(128)
print(f"gateway listening 0.0.0.0:{listen_port} -> {target_host}:{target_port}", flush=True)
while True:
    conn, _ = srv.accept()
    threading.Thread(target=handle, args=(conn,), daemon=True).start()
PY
  echo $! >"$PID_FILE"
  sleep 0.3
  if ! is_running; then
    echo "error: gateway failed to start; see $LOG_FILE" >&2
    exit 1
  fi
  # self-check via localhost gateway port
  if ! curl -sS -m 3 "http://127.0.0.1:${GATEWAY_PORT}/api/tags" >/dev/null; then
    echo "error: gateway up but /api/tags failed on :${GATEWAY_PORT}" >&2
    exit 1
  fi
  echo "host-ollama-gateway started pid=$(cat "$PID_FILE")  0.0.0.0:${GATEWAY_PORT} → 127.0.0.1:${OLLAMA_PORT}"
}

stop() {
  if is_running; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE"
    echo "host-ollama-gateway stopped"
  else
    rm -f "$PID_FILE"
    echo "host-ollama-gateway not running"
  fi
}

status() {
  if is_running; then
    echo "running pid=$(cat "$PID_FILE") port=${GATEWAY_PORT}"
    curl -sS -m 2 "http://127.0.0.1:${GATEWAY_PORT}/api/tags" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("models:", len(d.get("models") or []))' 2>/dev/null || echo "tags: fail"
  else
    echo "stopped"
    exit 1
  fi
}

case "$cmd" in
  start) start ;;
  stop) stop ;;
  status) status ;;
  restart) stop; start ;;
  *) echo "usage: $0 start|stop|status|restart"; exit 2 ;;
esac
