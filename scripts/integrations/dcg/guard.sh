#!/bin/bash
# Classify one command. Do not execute it.
# Exit 0 allows. Exit 126 denies.
# PFY_DCG_DISABLE=1 is the only opt-out.
# A missing binary, a dcg error, or a 2 second timeout prints dcg-fallback.
# The built-in list still denies known destructive argv.

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CONFIG="$HERE/config.toml"
TIMEOUT_S=2

if [ "${PFY_DCG_DISABLE:-}" = "1" ]; then
  printf '%s\n' "dcg-disabled" >&2
  exit 0
fi

is_destructive() {
  [ "$#" -ge 1 ] || return 1
  case "$1" in
    rm)
      local rf=0 bad=0 arg
      shift
      for arg in "$@"; do
        case "$arg" in
          -rf|-fr) rf=1 ;;
          /|..|../|../*) bad=1 ;;
        esac
      done
      [ "$rf" = 1 ] && [ "$bad" = 1 ]
      return
      ;;
    dd)
      local arg
      shift
      for arg in "$@"; do
        case "$arg" in
          of=/dev/*) return 0 ;;
        esac
      done
      return 1
      ;;
    mkfs|mkfs.*)
      return 0
      ;;
    git)
      shift
      while [ "$#" -gt 0 ]; do
        case "$1" in
          -C|-c|--git-dir|--work-tree)
            shift
            [ "$#" -gt 0 ] && shift
            ;;
          -*)
            shift
            ;;
          *)
            break
            ;;
        esac
      done
      local sub="${1:-}"
      shift || true
      case "$sub" in
        push)
          local arg
          for arg in "$@"; do
            case "$arg" in
              --force|--force-with-lease|-f|--force=*) return 0 ;;
            esac
          done
          return 1
          ;;
        reset)
          local arg
          for arg in "$@"; do
            [ "$arg" = "--hard" ] && return 0
          done
          return 1
          ;;
        clean)
          local arg letters
          for arg in "$@"; do
            case "$arg" in
              --) break ;;
              -*)
                letters=${arg#-}
                case "$letters" in
                  *f*d*|*d*f*) return 0 ;;
                esac
                ;;
            esac
          done
          return 1
          ;;
        *)
          return 1
          ;;
      esac
      ;;
    *)
      return 1
      ;;
  esac
}

fallback() {
  local why="$1"
  shift
  printf '%s\n' "dcg-fallback: ${why}" >&2
  if is_destructive "$@"; then
    exit 126
  fi
  exit 0
}

if [ -n "${PFY_DCG_BIN+x}" ]; then
  BIN=$PFY_DCG_BIN
else
  BIN="${HOME}/.cache/pfy/tools/destructive-command-guard/unpack/dcg"
fi

if [ ! -f "$BIN" ]; then
  fallback "binary missing: ${BIN}" "$@"
fi

if ! command -v timeout >/dev/null 2>&1; then
  fallback "timeout(1) missing" "$@"
fi

joined=""
for arg in "$@"; do
  if [ -n "$joined" ]; then
    joined="$joined "
  fi
  joined="$joined$arg"
done

cache_home="${PFY_DCG_CACHE_HOME:-${HOME}/.cache/pfy/tools/destructive-command-guard/home}"
out=""
status=0
out=$(
  timeout --signal=KILL "${TIMEOUT_S}s" env -i \
    PATH="/usr/bin:/bin" \
    LANG=C \
    NO_COLOR=1 \
    DCG_CONFIG="$CONFIG" \
    HOME="$cache_home" \
    "$BIN" test --stdin --dialect posix --format json --no-color --config "$CONFIG" <<<"$joined" 2>/dev/null
) || status=$?

if [ "$status" -eq 124 ] || [ "$status" -eq 137 ]; then
  fallback "dcg timed out after ${TIMEOUT_S}s" "$@"
fi

decision=$(
  printf '%s' "$out" | python3 -c 'import json,sys
try:
    data=json.loads(sys.stdin.read())
except Exception:
    raise SystemExit(2)
val=data.get("decision")
if not isinstance(val, str):
    raise SystemExit(2)
sys.stdout.write(val)
'
) || decision=""

if [ "$decision" = "deny" ]; then
  printf '%s\n' "dcg deny" >&2
  exit 126
fi
if [ "$decision" = "allow" ]; then
  exit 0
fi
fallback "dcg error (status ${status})" "$@"
