#!/bin/sh
# Persistent tool cache. Created on demand, shared across worktrees, never
# inside a git checkout.
#
#   ${PFY_TOOL_CACHE:-$HOME/.cache/pfy}/bin
#   ${PFY_TOOL_CACHE:-$HOME/.cache/pfy}/tools
#   ${PFY_TOOL_CACHE:-$HOME/.cache/pfy}/uv-cache
#
# SkillSpector v2.12.0 lives at tools/skillspector (a venv) with a wrapper
# at bin/skillspector. codebase-memory-mcp is resolved from bin/ when
# PFY_CODEBASE_MEMORY is unset and the name is not on PATH.
#
#   scripts/tool_cache.sh check
#
# Exit 0 when bin, tools, and uv-cache are directories (they are created
# when missing). Exit 1 when one of those paths exists and is not a directory.
# Prints one line per directory and whether the known binaries are executable.
set -eu
cache="${PFY_TOOL_CACHE:-$HOME/.cache/pfy}"
if [ "${1:-check}" != "check" ]; then
  echo "usage: scripts/tool_cache.sh check" >&2
  exit 2
fi
status=0
for name in bin tools uv-cache; do
  path="$cache/$name"
  if [ -e "$path" ] && [ ! -d "$path" ]; then
    echo "FAIL $path exists and is not a directory" >&2
    status=1
    continue
  fi
  mkdir -p "$path"
  echo "ok $path"
done
for tool in skillspector codebase-memory-mcp; do
  bin="$cache/bin/$tool"
  if [ -x "$bin" ]; then
    echo "bin $tool executable"
  else
    echo "bin $tool absent"
  fi
done
if [ -d "$cache/tools/skillspector" ]; then
  echo "venv skillspector present"
else
  echo "venv skillspector absent"
fi
exit "$status"
