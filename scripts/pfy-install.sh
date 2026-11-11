#!/usr/bin/env bash
# PATH launchers for deanery and pfy, plus mentat as a transition alias
# (the project was pfy-mentat until 2026-11-11). scripts/pfy is the only caller.
# No sudo. Does not edit shell rc files.
set -euo pipefail

MARKER='# pfy-deanery launcher (pfy install)'
# Launchers written before the Deanery rename carry this marker. Still ours.
OLD_MARKER='# pfy-mentat launcher (pfy install)'
LAUNCHERS=(deanery pfy mentat)

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

# Temps live in the prefix. A trap string would eval a quote in that path.
PFY_INSTALL_TMPS=()
cleanup_launchers() {
  local t
  for t in "${PFY_INSTALL_TMPS[@]}"; do
    if [ -n "$t" ]; then
      rm -f -- "$t" || true
    fi
  done
}

source=${BASH_SOURCE[0]}
hops=0
while [ -L "$source" ]; do
  hops=$((hops + 1))
  [ "$hops" -le 16 ] || die "too many symlinks: ${BASH_SOURCE[0]}"
  dir=$(cd "$(dirname "$source")" && pwd)
  target=$(readlink "$source")
  case "$target" in
    /*) source=$target ;;
    *) source=$dir/$target ;;
  esac
done
ROOT=$(cd "$(dirname "$source")/.." && pwd -P)

mode=install
prefix=""
prefix_set=0
dry=0

while [ $# -gt 0 ]; do
  case "$1" in
    --prefix)
      [ $# -ge 2 ] || die "install: --prefix needs a directory"
      prefix=$2
      prefix_set=1
      shift
      ;;
    --prefix=*)
      prefix=${1#--prefix=}
      prefix_set=1
      ;;
    --dry-run)
      dry=1
      ;;
    --uninstall|--launchers)
      mode=uninstall
      ;;
    -h|--help)
      cat <<'EOF'
usage: pfy install [--prefix DIR] [--dry-run]
       pfy install --uninstall [--prefix DIR]
       pfy uninstall --launchers [--prefix DIR]
EOF
      exit 0
      ;;
    *)
      die "install: unknown argument: $1"
      ;;
  esac
  shift
done

if [ "$prefix_set" -eq 0 ]; then
  [ -n "${HOME:-}" ] || die "install: HOME is not set"
  prefix="${HOME}/.local/bin"
fi
if [ "$prefix" != "/" ]; then
  prefix=${prefix%/}
fi
[ -n "$prefix" ] || die "install: --prefix needs a directory"

sq() {
  printf '%s' "$1" | sed "s/'/'\\\\''/g"
}

wrapper_body() {
  local q
  q=$(sq "$ROOT")
  printf '%s\n' '#!/bin/sh' "$MARKER" "# root: $ROOT" "exec '${q}/scripts/pfy' \"\$@\""
}

is_ours() {
  local f=$1
  [ -f "$f" ] || return 1
  grep -F -q -x -e "$MARKER" -e "$OLD_MARKER" "$f"
}

is_install_sh_shim() {
  local f=$1
  [ "$(basename "$f")" = "pfy" ] || return 1
  [ -f "$f" ] && [ ! -L "$f" ] || return 1
  local -a lines=()
  mapfile -t lines < "$f"
  [ "${#lines[@]}" -eq 2 ] || return 1
  [ "${lines[0]}" = "#!/bin/sh" ] || return 1
  local re='^exec '"'"'[^'"'"']*/\.local/share/pfy/[^/'"'"']+/pfy'"'"' "\$@"$'
  printf '%s\n' "${lines[1]}" | grep -Eq "$re"
}

classify() {
  local f=$1
  if [ ! -e "$f" ] && [ ! -L "$f" ]; then
    printf 'missing'
    return 0
  fi
  if is_ours "$f"; then
    printf 'ours'
    return 0
  fi
  if is_install_sh_shim "$f"; then
    printf 'shim'
    return 0
  fi
  printf 'foreign'
}

baked_root() {
  local f=$1 line
  [ -f "$f" ] || return 0
  while IFS= read -r line; do
    case "$line" in
      "# root: "*)
        printf '%s\n' "${line#"# root: "}"
        return 0
        ;;
    esac
  done < "$f"
}

on_path() {
  local dir=$1
  (
    set -f
    want=
    if [ -d "$dir" ]; then
      want=$(cd "$dir" && pwd -P) || exit 1
    else
      want=${dir%/}
    fi
    path_copy=${PATH-}
    IFS=:
    for entry in $path_copy; do
      [ -n "$entry" ] || continue
      if [ -d "$entry" ]; then
        phys=$(cd "$entry" && pwd -P) || continue
      else
        phys=${entry%/}
      fi
      if [ "$phys" = "$want" ]; then
        exit 0
      fi
    done
    exit 1
  )
}

path_hint() {
  local home_bin="" a b
  if [ -n "${HOME:-}" ]; then
    home_bin="${HOME}/.local/bin"
    a=$prefix
    b=$home_bin
    [ "$a" = "/" ] || a=${a%/}
    [ "$b" = "/" ] || b=${b%/}
    if [ "$a" = "$b" ]; then
      printf '%s\n' 'export PATH="$HOME/.local/bin:$PATH"'
      return 0
    fi
  fi
  printf '%s\n' "export PATH=\"${prefix}:\$PATH\""
}

warn_path() {
  if on_path "$prefix"; then
    return 0
  fi
  printf 'warn: %s is not on PATH\n' "$prefix" >&2
  printf 'Add this line to ~/.bashrc or ~/.profile:\n' >&2
  path_hint >&2
}

warn_unstable() {
  local unstable=0 gd common
  case "$ROOT" in
    */tmp|*/tmp/*) unstable=1 ;;
  esac
  if command -v git >/dev/null 2>&1 \
    && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    gd=$(git -C "$ROOT" rev-parse --absolute-git-dir 2>/dev/null || true)
    common=$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)
    if [ -n "$gd" ] && [ -n "$common" ] && [ "$gd" != "$common" ]; then
      unstable=1
    fi
  fi
  if [ "$unstable" -eq 1 ]; then
    printf 'warn: %s is under tmp/ or is not the main checkout. Launchers should point at a stable checkout.\n' "$ROOT" >&2
  fi
}

refuse_unwritable() {
  printf 'error: cannot write %s (not writable)\n' "$prefix" >&2
  printf 'sudo ./pfy install --prefix %s\n' "$prefix" >&2
  exit 1
}

ensure_prefix() {
  if [ -e "$prefix" ] && [ ! -d "$prefix" ]; then
    die "install: $prefix exists and is not a directory"
  fi
  if [ -d "$prefix" ]; then
    [ -w "$prefix" ] || refuse_unwritable
    return 0
  fi
  mkdir -p "$prefix" 2>/dev/null || refuse_unwritable
  [ -w "$prefix" ] || refuse_unwritable
}

do_uninstall() {
  local name f removed=0
  if [ ! -d "$prefix" ]; then
    printf 'already uninstalled\n'
    return 0
  fi
  for name in "${LAUNCHERS[@]}"; do
    f="$prefix/$name"
    if [ ! -e "$f" ] && [ ! -L "$f" ]; then
      continue
    fi
    if is_ours "$f"; then
      if [ "$dry" -eq 1 ]; then
        printf 'would remove %s\n' "$f"
      else
        rm -f -- "$f"
        printf 'removed %s\n' "$f"
      fi
      removed=1
    else
      printf 'note: left foreign file %s\n' "$f"
    fi
  done
  if [ "$removed" -eq 0 ]; then
    printf 'already uninstalled\n'
  fi
}

do_install() {
  local name f c r old="" foreign=0 current=1 i
  local -A cls=()
  warn_unstable
  if [ -e "$prefix" ] && [ ! -d "$prefix" ]; then
    die "install: $prefix exists and is not a directory"
  fi
  for name in "${LAUNCHERS[@]}"; do
    if [ -d "$prefix" ]; then
      cls[$name]=$(classify "$prefix/$name")
    else
      cls[$name]=missing
    fi
  done
  for name in "${LAUNCHERS[@]}"; do
    if [ "${cls[$name]}" = "foreign" ]; then
      printf 'error: refusing to overwrite %s (not a pfy-deanery launcher)\n' "$prefix/$name" >&2
      foreign=1
    fi
  done
  [ "$foreign" -eq 0 ] || exit 1
  for name in "${LAUNCHERS[@]}"; do
    f="$prefix/$name"
    if [ "${cls[$name]}" = "ours" ]; then
      r=$(baked_root "$f")
      if [ -z "$old" ] && [ -n "$r" ] && [ "$r" != "$ROOT" ]; then
        old=$r
      fi
      cmp -s "$f" <(wrapper_body) || current=0
    else
      current=0
    fi
  done
  if [ "$current" -eq 1 ]; then
    printf 'already installed\n'
    warn_path
    return 0
  fi
  if [ "$dry" -eq 1 ]; then
    printf 'would install deanery, pfy and mentat (alias) in %s\n' "$prefix"
    warn_path
    return 0
  fi
  if [ "${cls[pfy]}" = "shim" ]; then
    printf 'note: replacing install.sh shim at %s\n' "$prefix/pfy" >&2
  fi
  ensure_prefix
  trap cleanup_launchers EXIT
  for i in "${!LAUNCHERS[@]}"; do
    PFY_INSTALL_TMPS[i]=$(mktemp "$prefix/.pfy-launcher.XXXXXX")
    wrapper_body > "${PFY_INSTALL_TMPS[i]}"
    chmod 755 "${PFY_INSTALL_TMPS[i]}"
  done
  for i in "${!LAUNCHERS[@]}"; do
    mv -f "${PFY_INSTALL_TMPS[i]}" "$prefix/${LAUNCHERS[i]}"
    PFY_INSTALL_TMPS[i]=
  done
  if [ -n "$old" ]; then
    printf 'updated launchers (was %s, now %s)\n' "$old" "$ROOT"
  else
    printf 'installed %s\n' "$prefix"
  fi
  warn_path
}

if [ "$mode" = "uninstall" ]; then
  do_uninstall
else
  do_install
fi
