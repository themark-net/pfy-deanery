#!/bin/sh
# Loopback-only Arize Phoenix trace sink.
# The pin is config/phoenix/version.txt. install and unit read that file.
# enable/disable talk to systemd --user. This script does not start a unit
# unless the operator runs enable.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PIN_FILE=$ROOT/config/phoenix/version.txt

die() {
  echo "phoenix_service: $*" >&2
  exit 2
}

read_pin() {
  if [ ! -f "$PIN_FILE" ]; then
    die "missing pin file $PIN_FILE"
  fi
  ver=$(tr -d '[:space:]' < "$PIN_FILE")
  case $ver in
    ""|*[!0-9A-Za-z._-]*) die "pin file must be one version token" ;;
  esac
  printf '%s\n' "$ver"
}

abs_path() {
  case $1 in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s\n' "$PWD/$1" ;;
  esac
}

cache_dir() {
  abs_path "${PFY_TOOL_CACHE:-$HOME/.cache/pfy}"
}

state_dir() {
  # Same rule as pfylib/registry.state_dir: PFY_STATE_DIR or ~/.pfy-mentat.
  if [ -n "${PFY_STATE_DIR:-}" ]; then
    abs_path "$PFY_STATE_DIR"
  else
    abs_path "$HOME/.pfy-mentat"
  fi
}

need_int() {
  name=$1
  val=$2
  min=$3
  max=$4
  case $val in
    ""|*[!0-9]*) die "$name must be an integer" ;;
  esac
  case $val in
    0*) [ "$val" = "0" ] || die "$name must not have a leading zero" ;;
  esac
  if [ "$val" -lt "$min" ] || [ "$val" -gt "$max" ]; then
    die "$name is outside $min-$max"
  fi
  printf '%s\n' "$val"
}

loopback_host() {
  host=${PFY_PHOENIX_HOST:-127.0.0.1}
  case $host in
    127.0.0.1|::1|localhost) printf '%s\n' "$host" ;;
    *) die "refusing host $host (only 127.0.0.1, ::1, or localhost)" ;;
  esac
}

http_port() {
  need_int PFY_PHOENIX_PORT "${PFY_PHOENIX_PORT:-6006}" 1 65535
}

grpc_port() {
  need_int PFY_PHOENIX_GRPC_PORT "${PFY_PHOENIX_GRPC_PORT:-4317}" 1 65535
}

retention_days() {
  need_int PFY_PHOENIX_RETENTION_DAYS "${PFY_PHOENIX_RETENTION_DAYS:-30}" 0 3650
}

unit_path() {
  config=${XDG_CONFIG_HOME:-$HOME/.config}
  printf '%s\n' "$config/systemd/user/pfy-phoenix.service"
}

emit_unit() {
  host=$(loopback_host) || exit $?
  ver=$(read_pin) || exit $?
  port=$(http_port) || exit $?
  grpc=$(grpc_port) || exit $?
  days=$(retention_days) || exit $?
  cache=$(cache_dir) || exit $?
  state=$(state_dir) || exit $?
  venv=$cache/tools/phoenix/venv
  work=$state/phoenix
  home=$cache/tools/phoenix/home
  # PrivateTmp and IPAddressAllow/Deny need a user namespace or BPF. This
  # host's user manager is not granted that, so the unit does not set them.
  cat <<EOF
[Unit]
Description=pfy Phoenix trace sink (arize-phoenix $ver, loopback)
After=network.target

[Service]
Type=simple
ExecStart=$venv/bin/phoenix serve
Restart=on-failure
RestartSec=2
NoNewPrivileges=yes
WorkingDirectory=$work
Environment=PHOENIX_HOST=$host
Environment=PHOENIX_PORT=$port
Environment=PHOENIX_GRPC_PORT=$grpc
Environment=PHOENIX_WORKING_DIR=$work
Environment=PHOENIX_TELEMETRY_ENABLED=false
Environment=PHOENIX_DISABLE_MODEL_COST_AUTO_UPDATE=true
Environment=PHOENIX_ALLOW_EXTERNAL_RESOURCES=false
Environment=PHOENIX_DISABLE_AGENT_ASSISTANT=true
Environment=PHOENIX_AGENTS_DISABLE_BASH=true
Environment=PHOENIX_AGENTS_DISABLE_WEB_ACCESS=true
Environment=PHOENIX_AGENTS_DISABLE_GITHUB=true
Environment=PHOENIX_ENABLE_MCP_SERVER=false
Environment=PHOENIX_DEFAULT_RETENTION_POLICY_DAYS=$days
Environment=PYTHONNOUSERSITE=1
Environment=HOME=$home

[Install]
WantedBy=default.target
EOF
}

install_cmd() {
  ver=$(read_pin) || exit $?
  cache=$(cache_dir) || exit $?
  state=$(state_dir) || exit $?
  command -v uv >/dev/null 2>&1 || die "uv is not on PATH"
  uvcache=$cache/uv-cache
  venv=$cache/tools/phoenix/venv
  mkdir -p "$uvcache" "$cache/tools/phoenix/home" "$state/phoenix"
  if [ ! -x "$venv/bin/python" ]; then
    UV_CACHE_DIR=$uvcache uv venv --python 3.13 "$venv"
  fi
  UV_CACHE_DIR=$uvcache uv pip install --python "$venv/bin/python" "arize-phoenix==$ver"
  installed=$("$venv/bin/python" -c 'import importlib.metadata as m; print(m.version("arize-phoenix"))') || exit $?
  if [ "$installed" != "$ver" ]; then
    echo "phoenix_service: installed $installed does not match pin $ver" >&2
    exit 1
  fi
  printf '%s\n' "$installed"
}

enable_cmd() {
  text=$(emit_unit) || exit $?
  cache=$(cache_dir) || exit $?
  state=$(state_dir) || exit $?
  mkdir -p "$state/phoenix" "$cache/tools/phoenix/home"
  dest=$(unit_path)
  mkdir -p "$(dirname "$dest")"
  printf '%s\n' "$text" > "$dest"
  systemctl --user daemon-reload
  systemctl --user enable --now pfy-phoenix.service
}

disable_cmd() {
  dest=$(unit_path)
  systemctl --user disable --now pfy-phoenix.service || true
  rm -f "$dest"
  systemctl --user daemon-reload
}

status_cmd() {
  loopback_host >/dev/null || exit $?
  port=$(http_port) || exit $?
  ver=$(read_pin) || exit $?
  command -v python3 >/dev/null 2>&1 || die "python3 is not on PATH"
  if python3 - "$port" <<'PY'
import sys
import urllib.request

port = sys.argv[1]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = urllib.request.build_opener(NoRedirect, urllib.request.ProxyHandler({}))
for path in ("/healthz", "/"):
    url = "http://127.0.0.1:%s%s" % (port, path)
    try:
        with opener.open(url, timeout=1) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            if 200 <= int(code) < 300:
                sys.exit(0)
    except Exception:
        continue
sys.exit(1)
PY
  then
    printf 'up %s\n' "$ver"
    exit 0
  fi
  printf 'down %s\n' "$ver"
  exit 1
}

url_cmd() {
  host=$(loopback_host) || exit $?
  port=$(http_port) || exit $?
  case $host in
    ::1)
      printf 'http://[::1]:%s/\n' "$port"
      printf 'ssh -N -L %s:[::1]:%s <nimo-host>\n' "$port" "$port"
      ;;
    *)
      printf 'http://127.0.0.1:%s/\n' "$port"
      printf 'ssh -N -L %s:127.0.0.1:%s <nimo-host>\n' "$port" "$port"
      ;;
  esac
}

usage() {
  echo "usage: scripts/phoenix_service.sh install|unit|enable|disable|status|url" >&2
}

if [ $# -lt 1 ]; then
  usage
  exit 2
fi

case $1 in
  install) install_cmd ;;
  unit) emit_unit ;;
  enable) enable_cmd ;;
  disable) disable_cmd ;;
  status) status_cmd ;;
  url) url_cmd ;;
  *) usage; exit 2 ;;
esac
