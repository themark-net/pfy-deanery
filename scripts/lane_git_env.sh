#!/bin/bash
# Git environment for lane drivers.
#
# lane_git runs local worktree reads (rev-parse, status, diff, hash-object,
# show, merge-base, symbolic-ref). It uses the absolute git resolved from
# the same fixed path as scripts/lane_cage.py, under env -i, with a throwaway
# HOME. Caller PATH, HOME, and GIT_* do not reach that process.
#
# lane_git_scrub_env drops repository-redirect and config-injection variables
# from the caller. Call it once near the top of a lane driver. HOME and the
# operator's ssh transport settings stay so commit, fetch, push, rebase, and
# worktree add can use the operator identity. That is deliberate.
#
# lane_git_checked classifies the command as git, then runs lane_git. The
# guard matches the program name git. A function name is not on that list,
# so the check has to see git even though the read itself is lane_git.

LANE_GIT_SAFE_PATH="/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"
# The resolver cache starts empty; a value from the caller env is never used.
unset _LANE_GIT_BIN _LANE_GIT_BIN_KEY

_lane_git_bin() {
  if [ "${_LANE_GIT_BIN_KEY-}" = "$LANE_GIT_SAFE_PATH" ] && [ -n "${_LANE_GIT_BIN-}" ] && [ -x "${_LANE_GIT_BIN}" ]; then
    printf '%s\n' "$_LANE_GIT_BIN"
    return 0
  fi
  local IFS=:
  local dir
  for dir in $LANE_GIT_SAFE_PATH; do
    if [ -n "$dir" ] && [ -x "$dir/git" ]; then
      _LANE_GIT_BIN=$dir/git
      _LANE_GIT_BIN_KEY=$LANE_GIT_SAFE_PATH
      printf '%s\n' "$_LANE_GIT_BIN"
      return 0
    fi
  done
  printf '%s\n' "lane-git: git cannot be executed" >&2
  return 127
}

lane_git() {
  local bin home rc
  bin=$(_lane_git_bin) || return $?
  home=$(mktemp -d "${TMPDIR:-/tmp}/lane-git-home.XXXXXX") || return $?
  env -i \
    "PATH=${LANE_GIT_SAFE_PATH}" \
    LANG=C \
    LC_ALL=C \
    "HOME=${home}" \
    GIT_CONFIG_NOSYSTEM=1 \
    GIT_CONFIG_GLOBAL=/dev/null \
    "$bin" "$@" && rc=0 || rc=$?
  rm -rf "$home"
  return "$rc"
}

lane_git_scrub_env() {
  unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE \
    GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES \
    GIT_COMMON_DIR GIT_NAMESPACE GIT_CEILING_DIRECTORIES \
    GIT_DISCOVERY_ACROSS_FILESYSTEM GIT_CONFIG \
    GIT_CONFIG_PARAMETERS GIT_CONFIG_COUNT GIT_CONFIG_SYSTEM \
    GIT_TEMPLATE_DIR GIT_EXEC_PATH GIT_REPLACE_REF_BASE \
    GIT_ATTR_SOURCE GIT_EXTERNAL_DIFF GIT_PAGER GIT_EDITOR
  local name
  for name in $(compgen -e); do
    case "$name" in
      GIT_CONFIG_KEY_*|GIT_CONFIG_VALUE_*|GIT_TRACE*)
        unset "$name"
        ;;
    esac
  done
}

lane_git_checked() {
  if declare -F dcg_check >/dev/null 2>&1; then
    dcg_check git "$@" || return $?
  fi
  lane_git "$@"
}
