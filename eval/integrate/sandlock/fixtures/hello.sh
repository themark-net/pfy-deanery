#!/bin/sh
# Harmless local fixture. Writes one word to the path in $1.
if [ -z "${1:-}" ]; then
  echo "usage: hello.sh OUT" >&2
  exit 2
fi
printf '%s\n' ok > "$1"
