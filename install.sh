#!/bin/sh
{
# User-level pfy installer. No sudo, no system packages.
# One-liner:
#   curl -fsSL https://raw.githubusercontent.com/themark-net/pfy-deanery/v0.4.17/install.sh | sh
# A missing closing brace makes a truncated pipe a syntax error, so nothing runs.

set -eu

TAG=v0.4.17
REPO_URL=https://github.com/themark-net/pfy-deanery.git
DEST="${HOME:-}/.local/share/pfy/${TAG}"
SHIM="${HOME:-}/.local/bin/pfy"

stage=
shimtmp=

cleanup() {
  if [ -n "${stage:-}" ] && [ -d "$stage" ]; then
    rm -rf "$stage"
  fi
  if [ -n "${shimtmp:-}" ] && [ -e "$shimtmp" ]; then
    rm -rf "$shimtmp"
  fi
  return 0
}
trap cleanup EXIT

# Refuse root before flags, dry-run, or version. Tests stub `id` on PATH.
uid=$(id -u)
if [ "$uid" = "0" ] && [ "${PFY_ALLOW_ROOT:-}" != "1" ]; then
  printf '%s\n' "pfy install: refusing to run as root. Set PFY_ALLOW_ROOT=1 to override (containers only)." >&2
  exit 1
fi

if [ -z "${HOME:-}" ]; then
  printf '%s\n' "pfy install: HOME is not set" >&2
  exit 1
fi

version=0
dry_run=0
no_setup=0
while [ $# -gt 0 ]; do
  case "$1" in
    --version) version=1 ;;
    --dry-run) dry_run=1 ;;
    --no-setup) no_setup=1 ;;
    -h|--help)
      printf '%s\n' "Usage: install.sh [--dry-run] [--version] [--no-setup]"
      printf '%s\n' "Installs ${TAG} under \$HOME/.local/share/pfy and a shim at \$HOME/.local/bin/pfy."
      printf '%s\n' "PFY_INSTALL_SOURCE: copy that directory instead of cloning."
      printf '%s\n' "PFY_ALLOW_ROOT=1: allow uid 0."
      exit 0
      ;;
    *)
      printf '%s\n' "pfy install: unknown argument: $1" >&2
      exit 2
      ;;
  esac
  shift
done

if [ "$version" = "1" ]; then
  printf '%s\n' "$TAG"
  exit 0
fi

src="${PFY_INSTALL_SOURCE:-}"
if [ "$dry_run" = "1" ]; then
  printf '%s\n' "tag: ${TAG}"
  printf '%s\n' "dry_run: true"
  if [ -n "$src" ] && [ -d "$src" ]; then
    printf '%s\n' "copy: ${src} -> ${DEST}"
    printf '%s\n' "git clone --depth 1 --branch ${TAG} ${REPO_URL} ${DEST} (skipped; PFY_INSTALL_SOURCE is set)"
  else
    printf '%s\n' "git clone --depth 1 --branch ${TAG} ${REPO_URL} ${DEST}"
  fi
  printf '%s\n' "shim: ${SHIM}"
  exit 0
fi

parent=$(dirname "$DEST")
mkdir -p "$parent"
stage="${parent}/.stage.$$"
rm -rf "$stage"

if [ -n "$src" ] && [ -d "$src" ]; then
  mkdir -p "$stage"
  cp -a "${src}/." "$stage/"
else
  if ! command -v git >/dev/null 2>&1; then
    printf '%s\n' "pfy install: git is required, or set PFY_INSTALL_SOURCE to a local checkout" >&2
    exit 1
  fi
  GIT_TERMINAL_PROMPT=0
  export GIT_TERMINAL_PROMPT
  git clone --depth 1 --branch "$TAG" "$REPO_URL" "$stage"
fi

if [ ! -f "${stage}/pfy" ]; then
  printf '%s\n' "pfy install: ${TAG} has no pfy launcher" >&2
  exit 1
fi
chmod +x "${stage}/pfy"

old="${DEST}.old.$$"
rm -rf "$old"
if [ -e "$DEST" ]; then
  mv "$DEST" "$old"
fi
mv "$stage" "$DEST"
stage=
rm -rf "$old"

mkdir -p "$(dirname "$SHIM")"
shimtmp="${SHIM}.tmp.$$"
# shellcheck disable=SC2016
printf '%s\n' '#!/bin/sh' "exec '$(printf '%s' "${DEST}/pfy" | sed "s/'/'\\\\''/g")' \"\$@\"" > "$shimtmp"
chmod 755 "$shimtmp"
mv "$shimtmp" "$SHIM"
shimtmp=

printf '%s\n' "installed: ${TAG}"
printf '%s\n' "shim: ${SHIM}"

if [ "$no_setup" = "0" ] && [ -t 0 ]; then
  exec "${DEST}/pfy" setup
fi

if [ "$no_setup" = "0" ]; then
  printf '%s\n' "no TTY; run: pfy setup"
fi
}
