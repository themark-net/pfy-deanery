#!/bin/bash
# Local Phoenix span around a command, or sourceable helpers for lane scripts.
#
#   scripts/otel_span.sh NAME [k=v ...] -- CMD ARGS...
#
# Exit status, stdout, and stderr of CMD are unchanged. The span is emitted
# in the background. PFY_OTEL=0, a closed Phoenix port, a missing SDK, and a
# non-loopback endpoint are no-ops (non-loopback prints one stderr warning).
# Do not set shell flags at source time: lane scripts source this under set -u.

OTEL_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
OTEL_DEPTH=${OTEL_DEPTH:-0}
if [ "${OTEL_STACK_READY:-}" != "1" ]; then
  OTEL_STACK_NAME=()
  OTEL_STACK_TP=()
  OTEL_STACK_PARENT=()
  OTEL_STACK_START=()
  OTEL_STACK_ATTRS=()
  OTEL_STACK_KIND=()
  OTEL_LAUNCH_ENV=()
  OTEL_STACK_READY=1
fi

otel_off() {
  case "${PFY_OTEL:-}" in
    0 | false | no | off) return 0 ;;
  esac
  return 1
}

otel_is_loopback() {
  local host="$1"
  local o1 o2 o3 o4
  [ "$host" = "localhost" ] && return 0
  [ "$host" = "::1" ] && return 0
  IFS=. read -r o1 o2 o3 o4 extra <<EOF
$host
EOF
  [ -z "${extra:-}" ] || return 1
  [ -n "${o4:-}" ] || return 1
  case "$o1$o2$o3$o4" in
    *[!0-9]*) return 1 ;;
  esac
  [ "$o1" -eq 127 ] || return 1
  [ "$o2" -le 255 ] && [ "$o3" -le 255 ] && [ "$o4" -le 255 ]
}

otel_parse_endpoint() {
  local url="${PFY_OTEL_ENDPOINT:-http://127.0.0.1:6006/v1/traces}"
  local rest="${url#*://}"
  local hostport host port
  case "$rest" in
    *@*) rest="${rest#*@}" ;;
  esac
  hostport="${rest%%/*}"
  if [ "${hostport#\[}" != "$hostport" ]; then
    host="${hostport#\[}"
    host="${host%%\]*}"
    port="${hostport##*:}"
  elif [ "${hostport#*:}" != "$hostport" ]; then
    host="${hostport%%:*}"
    port="${hostport##*:}"
  else
    host="$hostport"
    port=80
  fi
  case "$port" in
    "" | *[!0-9]*) return 1 ;;
  esac
  OTEL_HOST="$host"
  OTEL_PORT="$port"
  otel_is_loopback "$host" || return 2
  return 0
}

otel_port_open() {
  timeout 0.2 bash -c "echo >/dev/tcp/${OTEL_HOST}/${OTEL_PORT}" >/dev/null 2>&1
}

otel_sdk_present() {
  local py cache
  py=$(python3 -c 'import sys; print("%d%d" % (sys.version_info[0], sys.version_info[1]))' 2>/dev/null) || return 1
  cache="${PFY_TOOL_CACHE:-$HOME/.cache/pfy}"
  [ -d "$cache/tools/otel/site-py${py}/opentelemetry" ]
}

# Latch for this process. Closed port and missing SDK stay silent.
# Run a tracing helper in the background with no inherited descriptors above
# stderr. A caller's lock fd (catalog_loop.sh holds STATE/loop.lock on fd 8)
# must not outlive the caller inside a slow exporter, or the next tick
# reports busy. The subshell drops them before exec.
otel_bg() {
  (
    local fd n
    for fd in /proc/$BASHPID/fd/*; do
      n=${fd##*/}
      case $n in '' | *[!0-9]*) continue ;; esac
      [ "$n" -gt 2 ] && eval "exec $n>&-" 2>/dev/null
    done
    "$@"
  ) </dev/null >/dev/null 2>&1 &
  disown $! 2>/dev/null || true
}

otel_live() {
  if [ "${OTEL_LIVE_CACHED:-}" = "1" ]; then
    return 0
  fi
  if [ "${OTEL_LIVE_CACHED:-}" = "0" ]; then
    return 1
  fi
  if otel_off; then
    OTEL_LIVE_CACHED=0
    return 1
  fi
  # `cmd || var=$?` so set -e in a sourced lane does not abort on a refused endpoint.
  _otel_parse=0
  otel_parse_endpoint || _otel_parse=$?
  if [ "$_otel_parse" -ne 0 ]; then
    if [ "$_otel_parse" -eq 2 ] && [ "${OTEL_WARNED:-}" != "1" ]; then
      printf '%s\n' "otel: refusing non-loopback endpoint" >&2
      OTEL_WARNED=1
    fi
    OTEL_LIVE_CACHED=0
    return 1
  fi
  if ! otel_port_open || ! otel_sdk_present; then
    OTEL_LIVE_CACHED=0
    return 1
  fi
  OTEL_LIVE_CACHED=1
  return 0
}

otel_py() {
  PYTHONPATH="${OTEL_ROOT}${PYTHONPATH:+:$PYTHONPATH}" python3 -m pfylib.otel "$@"
}

otel_emit_bg() {
  local name="$1" tp="$2" parent="$3" start="$4" end="$5" status="$6" kind="$7"
  shift 7
  local args=(
    emit
    --name "$name"
    --traceparent "$tp"
    --start-ns "$start"
    --end-ns "$end"
    --status "$status"
    --kind "$kind"
  )
  if [ -n "$parent" ]; then
    args+=(--parent "$parent")
  fi
  local item
  for item in "$@"; do
    [ -n "$item" ] || continue
    args+=(--attr "$item")
  done
  otel_bg otel_py "${args[@]}"
}

otel_span_begin() {
  local name="$1"
  shift
  local kind="CHAIN"
  local kept=()
  local item parent="" tp="" start=""
  for item in "$@"; do
    case "$item" in
      kind=*) kind="${item#kind=}" ;;
      *) kept+=("$item") ;;
    esac
  done
  if otel_live; then
    parent="${TRACEPARENT:-}"
    tp=$(otel_py traceparent 2>/dev/null || true)
    tp=${tp//$'\n'/}
    start=$(date +%s%N 2>/dev/null || echo 0)
  fi
  OTEL_STACK_NAME+=("$name")
  OTEL_STACK_TP+=("$tp")
  OTEL_STACK_PARENT+=("$parent")
  OTEL_STACK_START+=("$start")
  OTEL_STACK_ATTRS+=("${kept[*]-}")
  OTEL_STACK_KIND+=("$kind")
  OTEL_DEPTH=$((OTEL_DEPTH + 1))
  if [ -n "$tp" ]; then
    export TRACEPARENT="$tp"
  fi
  return 0
}

otel_span_end() {
  local status="${1:-0}"
  local i name tp parent start attrs kind end st
  if [ "${OTEL_DEPTH:-0}" -le 0 ]; then
    return 0
  fi
  i=$((OTEL_DEPTH - 1))
  name="${OTEL_STACK_NAME[$i]}"
  tp="${OTEL_STACK_TP[$i]}"
  parent="${OTEL_STACK_PARENT[$i]}"
  start="${OTEL_STACK_START[$i]}"
  attrs="${OTEL_STACK_ATTRS[$i]}"
  kind="${OTEL_STACK_KIND[$i]}"
  OTEL_DEPTH=$i
  if [ "$i" -eq 0 ]; then
    OTEL_STACK_NAME=()
    OTEL_STACK_TP=()
    OTEL_STACK_PARENT=()
    OTEL_STACK_START=()
    OTEL_STACK_ATTRS=()
    OTEL_STACK_KIND=()
  else
    OTEL_STACK_NAME=("${OTEL_STACK_NAME[@]:0:$i}")
    OTEL_STACK_TP=("${OTEL_STACK_TP[@]:0:$i}")
    OTEL_STACK_PARENT=("${OTEL_STACK_PARENT[@]:0:$i}")
    OTEL_STACK_START=("${OTEL_STACK_START[@]:0:$i}")
    OTEL_STACK_ATTRS=("${OTEL_STACK_ATTRS[@]:0:$i}")
    OTEL_STACK_KIND=("${OTEL_STACK_KIND[@]:0:$i}")
  fi
  export TRACEPARENT="$parent"
  if [ -z "$tp" ]; then
    return 0
  fi
  st=ok
  if [ "$status" -ne 0 ] 2>/dev/null; then
    st=error
  fi
  end=$(date +%s%N 2>/dev/null || echo 0)
  # Attrs are k=v tokens with no spaces. Splitting is the point.
  # shellcheck disable=SC2086
  otel_emit_bg "$name" "$tp" "$parent" "$start" "$end" "$st" "${kind:-CHAIN}" $attrs
  return 0
}

otel_lane_trap() {
  local status=$?
  while [ "${OTEL_DEPTH:-0}" -gt 0 ]; do
    otel_span_end "$status" || true
  done
  exit "$status"
}

otel_tick_begin() {
  local id
  id="tick-$(date -u +%Y%m%dT%H%M%SZ)"
  export DEANERY_JOB_ID="$id"
  export DEANERY_LANE_ID=catalog-loop
  export DEANERY_ROUTE=local
  export DEANERY_TASK_CLASS=catalog-loop
  otel_span_begin "catalog-loop" \
    deanery.lane_id=catalog-loop \
    deanery.job_id="$id" \
    deanery.route=local \
    deanery.task_class=catalog-loop \
    deanery.parent_lane= \
    deanery.iteration=0
}

otel_tick_finish() {
  otel_lane_trap
}

# Fill OTEL_LAUNCH_ENV with --setenv lines when tracing is live.
# Usage: otel_launch_setenv KIND SLUG
otel_launch_setenv() {
  local kind="$1" slug="$2"
  local parent="" tp="" now="" route=cloud
  OTEL_LAUNCH_ENV=()
  otel_live || return 0
  case "$kind" in
    fit | catalog-fit) route=local ;;
  esac
  parent="${TRACEPARENT:-}"
  tp=$(otel_py traceparent 2>/dev/null || true)
  tp=${tp//$'\n'/}
  [ -n "$tp" ] || return 0
  now=$(date +%s%N 2>/dev/null || echo 0)
  otel_emit_bg "lane.launch" "$tp" "$parent" "$now" "$now" ok CHAIN \
    "deanery.lane_id=${kind}-${slug}" \
    "deanery.job_id=${DEANERY_JOB_ID:-}" \
    deanery.parent_lane=catalog-loop \
    "deanery.task_class=${kind}" \
    "deanery.route=${route}" \
    deanery.iteration=0
  OTEL_LAUNCH_ENV=(
    --setenv=TRACEPARENT="$tp"
    --setenv=DEANERY_JOB_ID="${DEANERY_JOB_ID:-}"
    --setenv=DEANERY_PARENT_LANE=catalog-loop
    --setenv=DEANERY_LANE_ID="${kind}-${slug}"
    --setenv=DEANERY_ROUTE="$route"
    --setenv=DEANERY_TASK_CLASS="$kind"
  )
  return 0
}

otel_ingest_bg() {
  local log="$1"
  [ -n "$log" ] && [ -f "$log" ] || return 0
  otel_live || return 0
  otel_bg otel_py ingest --log "$log"
  return 0
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  set +e
  _otel_child=0
  _otel_forward() {
    local sig="$1"
    local status=143
    if [ "${_otel_child:-0}" -ne 0 ]; then
      kill -s "$sig" "$_otel_child" 2>/dev/null || true
      wait "$_otel_child" 2>/dev/null
      status=$?
    fi
    exit "$status"
  }
  trap '_otel_forward TERM' TERM
  trap '_otel_forward INT' INT
  trap '_otel_forward HUP' HUP

  if [ "$#" -lt 1 ]; then
    printf '%s\n' "usage: otel_span.sh NAME [k=v ...] -- CMD" >&2
    exit 2
  fi
  _otel_name="$1"
  shift
  _otel_kind="CHAIN"
  _otel_attrs=()
  while [ "$#" -gt 0 ]; do
    if [ "$1" = "--" ]; then
      shift
      break
    fi
    case "$1" in
      kind=*) _otel_kind="${1#kind=}" ;;
      *) _otel_attrs+=("$1") ;;
    esac
    shift
  done
  if [ "$#" -eq 0 ]; then
    exit 2
  fi

  _otel_parent="${TRACEPARENT:-}"
  _otel_tp=""
  _otel_start=0
  if otel_live; then
    _otel_tp=$(otel_py traceparent 2>/dev/null || true)
    _otel_tp=${_otel_tp//$'\n'/}
    _otel_start=$(date +%s%N 2>/dev/null || echo 0)
    if [ -n "$_otel_tp" ]; then
      export TRACEPARENT="$_otel_tp"
    fi
  fi

  "$@" &
  _otel_child=$!
  wait "$_otel_child"
  _otel_status=$?
  if [ -n "$_otel_tp" ]; then
    _otel_end=$(date +%s%N 2>/dev/null || echo 0)
    _otel_st=ok
    if [ "$_otel_status" -ne 0 ]; then
      _otel_st=error
    fi
    # shellcheck disable=SC2086
    otel_emit_bg "$_otel_name" "$_otel_tp" "$_otel_parent" "$_otel_start" "$_otel_end" "$_otel_st" "$_otel_kind" ${_otel_attrs[@]+"${_otel_attrs[@]}"}
  fi
  exit "$_otel_status"
fi
