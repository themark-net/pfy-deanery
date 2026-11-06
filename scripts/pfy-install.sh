#!/usr/bin/env bash
# PATH launchers for mentat and pfy. scripts/pfy is the only caller.
# No sudo. Does not edit shell rc files.
set -euo pipefail

MARKER='# pfy-mentat launcher (pfy install)'

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

# Temps live in the prefix. A trap string would eval a quote in that path.
PFY_INSTALL_T1=
PFY_INSTALL_T2=
cleanup_launchers() {
  if [ -n "${PFY_INSTALL_T1:-}" ]; then
    rm -f -- "$PFY_INSTALL_T1" || true
  fi
  if [ -n "${PFY_INSTALL_T2:-}" ]; then
    rm -f -- "$PFY_INSTALL_T2" || true
  fi
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
  grep -F -q -x "$MARKER" "$f"
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
  for name in mentat pfy; do
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
  local mentat="$prefix/mentat"
  local pfy="$prefix/pfy"
  local cm=missing cp=missing old="" old_p=""
  warn_unstable
  if [ -e "$prefix" ] && [ ! -d "$prefix" ]; then
    die "install: $prefix exists and is not a directory"
  fi
  if [ -d "$prefix" ]; then
    cm=$(classify "$mentat")
    cp=$(classify "$pfy")
  fi
  if [ "$cm" = "foreign" ] || [ "$cp" = "foreign" ]; then
    if [ "$cm" = "foreign" ]; then
      printf 'error: refusing to overwrite %s (not a pfy-mentat launcher)\n' "$mentat" >&2
    fi
    if [ "$cp" = "foreign" ]; then
      printf 'error: refusing to overwrite %s (not a pfy-mentat launcher)\n' "$pfy" >&2
    fi
    exit 1
  fi
  if [ "$cm" = "ours" ] && [ "$cp" = "ours" ]; then
    if cmp -s "$mentat" <(wrapper_body) && cmp -s "$pfy" <(wrapper_body); then
      printf 'already installed\n'
      warn_path
      return 0
    fi
    old=$(baked_root "$mentat")
    old_p=$(baked_root "$pfy")
    if [ "$old" = "$ROOT" ]; then
      old=$old_p
    fi
  elif [ "$cm" = "ours" ]; then
    old=$(baked_root "$mentat")
  elif [ "$cp" = "ours" ]; then
    old=$(baked_root "$pfy")
  fi
  if [ "$dry" -eq 1 ]; then
    printf 'would install mentat and pfy in %s\n' "$prefix"
    warn_path
    return 0
  fi
  if [ "$cp" = "shim" ]; then
    printf 'note: replacing install.sh shim at %s\n' "$pfy" >&2
  fi
  ensure_prefix
  local t1 t2
  t1=$(mktemp "$prefix/.pfy-launcher.XXXXXX")
  PFY_INSTALL_T1=$t1
  trap cleanup_launchers EXIT
  t2=$(mktemp "$prefix/.pfy-launcher.XXXXXX")
  PFY_INSTALL_T2=$t2
  wrapper_body > "$t1"
  wrapper_body > "$t2"
  chmod 755 "$t1" "$t2"
  mv -f "$t1" "$mentat"
  PFY_INSTALL_T1=
  mv -f "$t2" "$pfy"
  PFY_INSTALL_T2=
  if [ -n "$old" ] && [ "$old" != "$ROOT" ]; then
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
