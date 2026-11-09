#!/usr/bin/env bash
# Create one git commit of the red add fixture on branch main.
# Dest must resolve strictly inside the caller's tmp/. A pre-existing
# non-empty dest is left untouched. Usage exits 2.
set -euo pipefail

usage() {
  echo "usage: init_fixture.sh <dest>" >&2
  exit 2
}

if [[ $# -ne 1 ]]; then
  usage
fi

dest_arg=$1
if [[ -z $dest_arg || $dest_arg == -* || $dest_arg == *$'\n'* ]]; then
  usage
fi

if [[ ! -d $PWD/tmp ]]; then
  echo "refusing: caller tmp/ is missing" >&2
  exit 1
fi

caller_tmp=$(realpath "$PWD/tmp")

if [[ $dest_arg == /* ]]; then
  dest_abs=$dest_arg
else
  dest_abs=$PWD/$dest_arg
fi

if [[ -L $dest_abs ]]; then
  echo "refusing: dest is a symlink" >&2
  exit 1
fi

parent=$(dirname "$dest_abs")
if [[ ! -d $parent || -L $parent ]]; then
  echo "refusing: dest parent is missing" >&2
  exit 1
fi

parent_real=$(realpath "$parent")
base=$(basename "$dest_abs")
if [[ -z $base || $base == . || $base == .. ]]; then
  echo "refusing: dest is outside caller tmp/" >&2
  exit 1
fi

if [[ -e $dest_abs ]]; then
  dest_real=$(realpath "$dest_abs")
else
  dest_real=$parent_real/$base
fi

case $dest_real in
  "$caller_tmp"/*) ;;
  *)
    echo "refusing: dest is outside caller tmp/" >&2
    exit 1
    ;;
esac

created=0
if [[ -e $dest_real ]]; then
  if [[ ! -d $dest_real ]]; then
    echo "refusing: dest exists and is not a directory" >&2
    exit 1
  fi
  if [[ -n $(find "$dest_real" -mindepth 1 -print -quit) ]]; then
    echo "refusing: dest exists and is not empty" >&2
    exit 1
  fi
else
  mkdir "$dest_real"
  created=1
fi

cleanup() {
  status=$?
  trap - EXIT
  if [[ $status -ne 0 && $created -eq 1 ]]; then
    rm -rf -- "$dest_real"
  fi
  exit "$status"
}
trap cleanup EXIT

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cp "$script_dir/fixture/add.py" "$dest_real/add.py"
cp "$script_dir/fixture/test_add.py" "$dest_real/test_add.py"

git init -q -b main "$dest_real"
git -C "$dest_real" add -- add.py test_add.py
git -C "$dest_real" \
  -c user.name=mvp-eval-1031 \
  -c user.email=mvp-eval-1031@localhost \
  commit -q -m "Seed a red add fixture."

printf '%s\n' "$dest_real"
