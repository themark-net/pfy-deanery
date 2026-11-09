#!/usr/bin/env bash
# Local pre-gate for themark-net/pfy-mentat: catch Tester/Reviewer failure
# classes on nimo before spending bot gate rounds. See docs/ops/PREGATE.md.
#
# Usage:
#   ./scripts/pregate.sh [options] [REF]       REF defaults to HEAD
#
# Options:
#   --only a,b        run only these checks (comma list); unknown names exit 2
#   --force-suite     also run the standalone suite check (normally skipped)
#   --full            force the full unittest suite (ignore affected selection)
#   --base REF        base for the committed gate-file diff (default: origin/main)
#   --in-place        run in this checkout (HEAD must equal REF; must be clean)
#   --allow-dirty     with --in-place, allow a dirty tree (dev only)
#   --keep-worktree   keep the run worktree and scratch for debugging
#
# Several pregates may run on one host. Each run has its own worktree, scratch,
# and log folder. Those names include the pid. Repo paths with whitespace are
# refused (exit 2). An unresolvable --base exits 2.
#
# Checks: lint ci-parity ubuntu-parity eval-structural suite orphans gate-hash
# Logs and summary persist in <state>/pregate-runs/<run-id>/.
# State defaults to <git-common-parent>/tmp. Set PREGATE_STATE_ROOT to move it.
# Exit: 0 PASS, 1 FAIL (or no check passed), 2 usage/setup error, 130/143 signal.
# Keeps the newest PREGATE_KEEP_RUNS (default 20) run folders, and never
# deletes a folder whose pregate pid is still live.
set -euo pipefail

ALL_CHECKS="lint ci-parity ubuntu-parity eval-structural suite orphans gate-hash"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REF="HEAD"
BASE_REF="origin/main"
IN_PLACE=0
ALLOW_DIRTY=0
KEEP_WORKTREE=0
FORCE_SUITE=0
FORCE_FULL=0
ONLY=""
REF_SET=0
STEP_TIMEOUT="${PREGATE_STEP_TIMEOUT:-2400}"
MAX_ROOT_LEN="${PREGATE_MAX_ROOT_LEN:-60}"
KEEP_RUNS="${PREGATE_KEEP_RUNS:-20}"
MAIN_PID=$$

die2() { echo "pregate: $*" >&2; exit 2; }
usage() { awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "$0"; exit "${1:-0}"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage 0 ;;
    --in-place) IN_PLACE=1; shift ;;
    --allow-dirty) ALLOW_DIRTY=1; shift ;;
    --keep-worktree) KEEP_WORKTREE=1; shift ;;
    --force-suite) FORCE_SUITE=1; shift ;;
    --full) FORCE_FULL=1; shift ;;
    --only|--base)
      if [[ $# -lt 2 || -z "$2" || "$2" == -* ]]; then die2 "$1 needs a value"; fi
      if [[ "$1" == "--only" ]]; then ONLY="$2"; else BASE_REF="$2"; fi
      shift 2 ;;
    --) shift; [[ $# -gt 0 ]] && { [[ "$REF_SET" -eq 0 ]] || die2 "only one REF allowed"; REF="$1"; shift; }; break ;;
    -*) echo "pregate: unknown flag: $1" >&2; usage 2 ;;
    *) [[ "$REF_SET" -eq 0 ]] || die2 "only one REF allowed (got '$REF' and '$1')"; REF="$1"; REF_SET=1; shift ;;
  esac
done
[[ $# -eq 0 ]] || die2 "unexpected extra arguments: $*"

if [[ -n "$ONLY" ]]; then
  for c in ${ONLY//,/ }; do
    [[ " $ALL_CHECKS " == *" $c "* ]] || die2 "unknown check '$c' (valid: $ALL_CHECKS)"
  done
fi
[[ "$STEP_TIMEOUT" =~ ^[0-9]+$ ]] || die2 "PREGATE_STEP_TIMEOUT must be seconds"
[[ "$KEEP_RUNS" =~ ^[1-9][0-9]*$ ]] || die2 "PREGATE_KEEP_RUNS must be a positive integer"

command -v git >/dev/null 2>&1 || die2 "git not found on PATH"
command -v python3 >/dev/null 2>&1 || die2 "python3 not found on PATH"
command -v ps >/dev/null 2>&1 || die2 "ps not found on PATH (orphan check needs it)"
cd "$REPO_ROOT"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die2 "not a git repo: $REPO_ROOT"
SHA="$(git rev-parse --verify --quiet "${REF}^{commit}")" || die2 "unknown ref or SHA: $REF"
SHORT="${SHA:0:7}"
# B4: gate-hash diffs committed gate files vs this base; an unresolvable base
# must not silently skip that diff, so it is a setup error.
BASE_SHA="$(git rev-parse --verify --quiet "${BASE_REF}^{commit}")" || die2 "unknown base ref: $BASE_REF (fetch it or pass --base REF)"
export BASE_SHA
GIT_COMMON="$(git rev-parse --path-format=absolute --git-common-dir)"
MAIN_ROOT="$(dirname "$GIT_COMMON")"
HOST="$(hostname -s 2>/dev/null || hostname)"
STATE_ROOT="${PREGATE_STATE_ROOT:-$MAIN_ROOT/tmp}"

case "$MAIN_ROOT$REPO_ROOT$STATE_ROOT" in
  *[[:space:]]*) die2 "repo path contains whitespace; not supported: $MAIN_ROOT" ;;
esac

RUN_TS="$(date -u +%Y%m%dT%H%M%SZ)"
HHMMSS="${RUN_TS:9:6}"
# Persist id keeps the full UTC stamp and the raw pid. Worktree and scratch
# stay short so harness2 sockets fit sun_path. Their pid is zero-padded to 7
# digits so the path length does not change between runs (the length guard
# compares with `>`).
RUN_PID="$(printf '%07d' "$$")"
RUN_TAG="${SHORT}-${HHMMSS}-${RUN_PID}"
RUN_ID="${SHORT}-${RUN_TS}-$$"
PERSIST="$STATE_ROOT/pregate-runs/$RUN_ID"
LOG_DIR="$PERSIST/logs"
RECEIPTS="$PERSIST/receipts"
SUMMARY="$PERSIST/pregate-summary.md"
PG_DIR="$STATE_ROOT/pg"
SCRATCH="$STATE_ROOT/pgs/$RUN_TAG"

if [[ "$IN_PLACE" -eq 1 ]]; then
  RUN_ROOT="$REPO_ROOT"
  if [[ "$ALLOW_DIRTY" -eq 0 && -n "$(git status --porcelain)" ]]; then
    die2 "working tree dirty; commit, stash, or pass --allow-dirty"
  fi
  [[ "$(git rev-parse HEAD)" == "$SHA" ]] || die2 "--in-place HEAD != $SHA; check out the REF or omit --in-place"
else
  RUN_ROOT="$PG_DIR/$RUN_TAG"
fi

# Unix socket paths (sun_path, 108 bytes) used by harness2 sandbox tests are
# built under the run root and TMPDIR. Measured: 51-54 char roots pass, 76+ fail.
for p in "$RUN_ROOT" "$SCRATCH"; do
  if [[ ${#p} -gt $MAX_ROOT_LEN ]]; then
    die2 "path too long (${#p} > $MAX_ROOT_LEN chars): $p. Use a checkout whose git common dir is short (e.g. ~/DEVELOP/pfy-mentat) or set PREGATE_MAX_ROOT_LEN."
  fi
done
[[ "$IN_PLACE" -eq 1 || ! -e "$RUN_ROOT" ]] || die2 "run root already exists: $RUN_ROOT"

# --- process helpers: only ever touch this script's own descendants ---------
descendants() {
  local p
  for p in $(ps -o pid= --ppid "$1" 2>/dev/null); do
    descendants "$p"
    echo "$p"
  done
}
# True only while PID is still a direct child of this pregate (guards PID reuse:
# after the child exits, or after pregate itself is SIGKILLed and the child is
# reparented, the parent no longer matches and nothing is signalled).
own_child() {
  local pp
  pp="$( { ps -o ppid= -p "$1" 2>/dev/null || true; } | tr -d ' ')"
  [[ -n "$pp" && "$pp" == "$MAIN_PID" ]]
}
kill_tree() {
  local pids
  own_child "$1" || return 0
  pids="$(descendants "$1") $1"
  # shellcheck disable=SC2086
  kill -TERM $pids 2>/dev/null || true
  sleep 1
  own_child "$1" || return 0
  pids="$(descendants "$1") $1"
  # shellcheck disable=SC2086
  kill -KILL $pids 2>/dev/null || true
}
is_live_pregate() {
  [[ -n "${1:-}" && -r "/proc/$1/cmdline" ]] && tr '\0' ' ' <"/proc/$1/cmdline" | grep -q 'pregate\.sh'
}
run_pid_from_name() {
  local base="${1##*/}"
  if [[ "$base" =~ -([0-9]+)$ ]]; then
    echo "${BASH_REMATCH[1]}"
  fi
}
# A run folder is live when its trailing pid is still a pregate, or any of
# this user's processes still has that folder as cwd or argv.
run_dir_is_live() {
  local dir="$1" pid
  pid="$(run_pid_from_name "$dir")"
  if is_live_pregate "$pid"; then
    return 0
  fi
  [[ -n "$(procs_under "$dir")" ]]
}

# PIDs of this user's processes whose cwd or argv is under any of the given dirs.
procs_under() {
  local pid cwd cmd d out=""
  for pid in $(ps -u "$(id -un)" -o pid= 2>/dev/null); do
    cwd="$(readlink "/proc/$pid/cwd" 2>/dev/null || true)"
    cmd="$( { tr '\0' ' ' <"/proc/$pid/cmdline"; } 2>/dev/null || true)"
    for d in "$@"; do
      if [[ "$cwd/" == "$d/"* || "$cmd" == *"$d/"* ]]; then out+=" $pid"; break; fi
    done
  done
  echo "$out"
}

# --- prune stale runs this script registered (owner pid gone, e.g. SIGKILL) --
mkdir -p "$PG_DIR"
for owner in "$PG_DIR"/.owner-*; do
  [[ -e "$owner" ]] || continue
  name="${owner##*/.owner-}"
  if [[ ! "$name" =~ ^[0-9a-f]{7}-[0-9]{6}(-[0-9]+)?$ ]]; then
    echo "pregate: ignoring owner file with unexpected name: $owner" >&2
    continue
  fi
  opid="$(cat "$owner" 2>/dev/null || true)"
  if is_live_pregate "$opid"; then continue; fi
  if [[ "$opid" =~ ^[0-9]+$ && -d "/proc/$opid" ]]; then
    why="owner pid $opid is alive but is not a pregate (pid reused)"
  else
    why="owner pid ${opid:-?} is gone"
  fi
  busy="$(procs_under "$PG_DIR/$name" "$STATE_ROOT/pgs/$name")"
  if [[ -n "$busy" ]]; then
    echo "pregate: stale run $PG_DIR/$name still has live processes (pids:$busy); not pruning, not signalling" >&2
    continue
  fi
  echo "pregate: pruning stale run $PG_DIR/$name ($why)"
  git -C "$REPO_ROOT" worktree remove --force "$PG_DIR/$name" >/dev/null 2>&1 || rm -rf "${PG_DIR:?}/$name"
  rm -rf "$STATE_ROOT/pgs/$name"
  rm -f "$owner"
done

mkdir -p "$LOG_DIR" "$RECEIPTS"
# Retention: keep the newest KEEP_RUNS run folders (this one included). Only
# names matching the run-id pattern inside tmp/pregate-runs are ever removed.
RUNS_DIR="$STATE_ROOT/pregate-runs"
mapfile -t _old_runs < <(find "$RUNS_DIR" -mindepth 1 -maxdepth 1 -type d -regextype posix-extended \
  -regex '.*/[0-9a-f]{7}-[0-9]{8}T[0-9]{6}Z-[0-9]+' -printf '%T@ %p\n' | sort -rn | tail -n +"$((KEEP_RUNS + 1))" | cut -d' ' -f2-)
for d in "${_old_runs[@]}"; do
  if [[ -z "$d" || "$d" == "$PERSIST" || "$d" != "$RUNS_DIR/"* ]]; then
    continue
  fi
  if run_dir_is_live "$d"; then
    echo "pregate: keeping live run $d" >&2
    continue
  fi
  rm -rf -- "$d"
done
CLEANUP_WORKTREE=""
OWNER_FILE=""
if [[ "$IN_PLACE" -eq 0 ]]; then
  OWNER_FILE="$PG_DIR/.owner-$RUN_TAG"
  echo "$$" >"$OWNER_FILE"
  CLEANUP_WORKTREE="$RUN_ROOT"
fi

# Report-only. Detached so a shadow failure cannot change the exit status
# and the index does not sit on the pregate clock. PFY_CBM_SHADOW=0 skips.
launch_cbm_shadow() {
  if [[ "${PFY_CBM_SHADOW:-1}" == "0" ]]; then
    return 0
  fi
  if [[ -z "${BASE_SHA:-}" || -z "${SHA:-}" ]]; then
    return 0
  fi
  # Subshell cds to / so a removed run root cannot block exec. setsid leaves
  # the orphan reaper's tree. The child writes the JSONL itself.
  (
    cd / || exit 0
    exec setsid python3 "$SCRIPT_DIR/cbm_shadow.py" --base "$BASE_SHA" --head "$SHA"
  ) </dev/null >/dev/null 2>&1 &
  disown || true
  return 0
}

reap_recorded_orphans() {
  [[ -z "${PS_BEFORE_FAILED:-}" && -n "${ORPHAN_SEEN:-}" && -s "$ORPHAN_SEEN" ]] || return 0
  local pids pid
  pids="$(python3 "$SCRIPT_DIR/pregate_orphans.py" signal "$ORPHAN_SEEN" "$$" "$LOG_DIR/ps-before.txt" "$RUN_ROOT" "$SCRATCH" 2>/dev/null || true)"
  if [[ -n "${pids//[[:space:]]/}" ]]; then
    # shellcheck disable=SC2086
    kill -TERM $pids 2>/dev/null || true; sleep 1; kill -KILL $pids 2>/dev/null || true
  fi
  while read -r pid _; do
    [[ "$pid" =~ ^[0-9]+$ ]] && own_child "$pid" && kill_tree "$pid" || true
  done <"$ORPHAN_SEEN"
}
cleanup() {
  rm -f "$LOG_DIR/.orphan-sample"; if [[ -n "${SAMPLER_PID:-}" ]]; then kill "$SAMPLER_PID" 2>/dev/null || true; wait "$SAMPLER_PID" 2>/dev/null || true; fi
  reap_recorded_orphans
  if [[ -n "$CLEANUP_WORKTREE" && "$KEEP_WORKTREE" -eq 0 ]]; then
    git -C "$REPO_ROOT" worktree remove --force "$CLEANUP_WORKTREE" >/dev/null 2>&1 || rm -rf "$CLEANUP_WORKTREE"
  fi
  if [[ "$KEEP_WORKTREE" -eq 0 ]]; then rm -rf "$SCRATCH"; fi
  # Normal exit (incl. --keep-worktree) drops the owner marker; only a run that
  # never reached cleanup (SIGKILL) leaves one for the next run to prune.
  if [[ -n "$OWNER_FILE" ]]; then rm -f "$OWNER_FILE"; fi
  # After the reaper, so this child is not recorded and then killed.
  launch_cbm_shadow || true
}
trap cleanup EXIT

RESULTS=()
FAIL_COUNT=0
PASS_COUNT=0
SKIP_COUNT=0
START_EPOCH="$(date +%s)"
INTERRUPTED=""

record() {
  local status="$1" name="$2" detail="${3:-}"
  RESULTS+=("$status|$name|$detail")
  case "$status" in
    PASS) PASS_COUNT=$((PASS_COUNT + 1)) ;;
    FAIL) FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
    SKIP) SKIP_COUNT=$((SKIP_COUNT + 1)) ;;
    NOTE) ;;
  esac
  printf '[%s] %s%s\n' "$status" "$name" "${detail:+: $detail}"
}

should_run() {
  [[ -z "$ONLY" ]] && return 0
  [[ ",$ONLY," == *",$1,"* ]]
}

write_summary() {
  local end wall overall row st name detail
  end="$(date +%s)"; wall=$((end - START_EPOCH))
  overall="PASS"
  if [[ "$FAIL_COUNT" -gt 0 || "$PASS_COUNT" -eq 0 || -n "$INTERRUPTED" ]]; then overall="FAIL"; fi
  {
    echo "# Pregate summary"
    echo
    echo "- overall: **$overall**"
    if [[ "$PASS_COUNT" -eq 0 && "$FAIL_COUNT" -eq 0 ]]; then
      echo "- note: no check ran to completion, so this is not a PASS"
    fi
    [[ -n "$INTERRUPTED" ]] && echo "- note: interrupted by SIG$INTERRUPTED"
    echo "- ref: \`$REF\` = \`$SHA\`"
    echo "- base for gate-file diff: \`$BASE_REF\` = \`$BASE_SHA\`"
    echo "- host: $HOST, python: $(python3 -V 2>&1), bwrap on host PATH: $(command -v bwrap >/dev/null && echo yes || echo no)"
    echo "- started (local): $(date -d "@$START_EPOCH" '+%Y-%m-%d %H:%M %Z')"
    echo "- wall seconds: $wall"
    echo "- counts: pass=$PASS_COUNT fail=$FAIL_COUNT skip=$SKIP_COUNT"
    echo "- selection: mode=${SEL_MODE:-unknown} modules=${SEL_COUNT:-0} ${SEL_REASON:-}"
    echo "- run id: \`$RUN_ID\`"
    echo "- logs: \`$LOG_DIR/\` (persist after the run)"
    echo
    echo "| status | check | detail |"
    echo "|---|---|---|"
    for row in "${RESULTS[@]}"; do
      IFS='|' read -r st name detail <<<"$row"
      echo "| $st | $name | ${detail//|/\\|} |"
    done
    echo
    echo "Unittest skip counts depend on the host (bwrap, grok, Ollama, Python version), so compare them across runs on the same host only."
    echo
    echo "Attach this file to any Tester/Reviewer gate request. See docs/ops/PREGATE.md."
  } >"$SUMMARY"
  echo
  echo "Summary: $SUMMARY"
  echo "OVERALL=$overall wall=${wall}s pass=$PASS_COUNT fail=$FAIL_COUNT skip=$SKIP_COUNT"
  [[ "$overall" == "PASS" ]]
}

on_signal() {
  trap - INT TERM HUP
  INTERRUPTED="$1"
  echo "pregate: SIG$1 received; stopping this run's own child processes" >&2
  kill_tree_children
  record FAIL interrupted "SIG$1 before all checks finished"
  write_summary || true
  case "$1" in INT) exit 130 ;; TERM) exit 143 ;; *) exit 129 ;; esac
}
kill_tree_children() {
  local c
  for c in $(ps -o pid= --ppid $$ 2>/dev/null); do kill_tree "$c"; done
}
trap 'on_signal INT' INT
trap 'on_signal TERM' TERM
trap 'on_signal HUP' HUP

# run_check NAME PASS_DETAIL FUNC: runs FUNC in a background subshell (so
# signals reach our trap promptly), with a watchdog timeout; logs persist.
run_check() {
  local name="$1" pass_detail="$2" fn="$3" log="$LOG_DIR/$1.log" child wd rc
  ( set -euo pipefail; "$fn" ) >"$log" 2>&1 </dev/null &
  child=$!
  ( sleep "$STEP_TIMEOUT"; echo "TIMEOUT: $name exceeded ${STEP_TIMEOUT}s" >>"$log"
    touch "$LOG_DIR/$name.timeout"; kill_tree "$child" ) >/dev/null 2>&1 </dev/null &
  wd=$!
  set +e
  wait "$child"
  rc=$?
  set -e
  kill_tree "$wd" >/dev/null 2>&1
  wait "$wd" 2>/dev/null || true
  if [[ -e "$LOG_DIR/$name.timeout" ]]; then
    record FAIL "$name" "timed out after ${STEP_TIMEOUT}s; see $log"
  elif [[ $rc -eq 0 ]]; then
    record PASS "$name" "$pass_detail"
  else
    record FAIL "$name" "exit $rc; see $log"
  fi
}

# --- create the isolated worktree --------------------------------------------
if [[ "$IN_PLACE" -eq 0 ]]; then
  git worktree add --detach "$RUN_ROOT" "$SHA" >"$LOG_DIR/worktree.log" 2>&1 \
    || { cat "$LOG_DIR/worktree.log" >&2; die2 "git worktree add failed"; }
fi
mkdir -p "$SCRATCH"
cd "$RUN_ROOT"

# Snapshot our user's processes before any check (orphan before/after diff).
ps -u "$(id -un)" -o pid= >"$LOG_DIR/ps-before.txt" 2>/dev/null || PS_BEFORE_FAILED=1
# Remember pids while they are still under the run, so a later chdir is still a leak.
ORPHAN_SEEN="$LOG_DIR/orphan-seen.txt"; : >"$ORPHAN_SEEN"; touch "$LOG_DIR/.orphan-sample"
python3 "$SCRIPT_DIR/pregate_orphans.py" watch "$ORPHAN_SEEN" "$LOG_DIR/.orphan-sample" "$RUN_ROOT" "$SCRATCH" &
SAMPLER_PID=$!

export PFY_STATE_DIR="$SCRATCH/state"
mkdir -p "$PFY_STATE_DIR"
# TMPDIR: product tmp/ scratch, never /tmp. Exception: a checkout under
# /workspace/* (box/agentcage) where scripts/pfy treats /workspace paths as the
# cage tree and test_lab_stage false-fails; there the caller's TMPDIR is kept.
case "$MAIN_ROOT" in
  /workspace/*) TMPDIR_POLICY="inherited (repo under /workspace)" ;;
  *) export TMPDIR="$SCRATCH/tmp"; mkdir -p "$TMPDIR"; TMPDIR_POLICY="$TMPDIR" ;;
esac

# PATH mirror without bwrap: every executable on the caller's PATH except bwrap,
# so the only difference from the host is "bwrap unavailable" (ubuntu CI).
CI_PATH="$SCRATCH/nobwrap-path"
mkdir -p "$CI_PATH"
IFS=':' read -r -a _path_dirs <<<"$PATH"
for d in "${_path_dirs[@]}"; do
  [[ -d "$d" ]] || continue
  for f in "$d"/*; do
    b="${f##*/}"
    [[ "$b" == bwrap || -e "$CI_PATH/$b" || -d "$f" || ! -x "$f" ]] && continue
    ln -s "$f" "$CI_PATH/$b"
  done
done

nobwrap_env() {
  export PATH="$CI_PATH"
  if command -v bwrap >/dev/null 2>&1; then echo "FAIL: bwrap still visible"; return 1; fi
  echo "bwrap hidden: OK"
}

# --- checks ------------------------------------------------------------------
check_lint() {
  local fail=0 p mode
  echo "== filemode =="
  for p in pfy scripts/pfy scripts/detect-local-runtime.sh; do
    mode="$(git ls-files -s -- "$p" | awk '{print $1}')"
    echo "$p gitmode=$mode"
    if [[ "$mode" != "100755" ]]; then echo "FAIL: $p is ${mode:-missing}"; fail=1; fi
    if [[ ! -x "$p" ]]; then echo "FAIL: $p not executable"; fail=1; fi
  done
  echo "== launchers =="
  python3 -m py_compile scripts/pfy-board.py scripts/pfy-gui.py
  bash -n scripts/pfy
  ./pfy help >/dev/null
  echo "== encoded payloads =="
  python3 scripts/check_no_encoded_payloads.py --selftest
  python3 scripts/check_no_encoded_payloads.py
  echo "== public paths (no operator notes, queues, or employer names) =="
  python3 scripts/check_public_paths.py
  echo "== smoke_contract_lint =="
  python3 scripts/smoke_contract_lint.py
  echo "== catalog_check =="
  python3 scripts/catalog_check.py
  echo "== workflow image pin =="
  # GitHub-hosted jobs must pin ubuntu-24.04 (the image ubuntu-parity mirrors;
  # bwrap is unusable there, so bwrap-gated tests skip). Parsed as YAML so a
  # list or a matrix expression cannot hide ubuntu-latest. The interpreter is
  # the absolute PATH python3 (the same lookup the hosted G0 step uses). Do
  # not resolve symlinks: a venv python3 is a symlink to a base interpreter
  # that may have PyYAML while the venv does not. Missing PyYAML fails closed
  # and the helper names that path. The helper also requires
  # eval-structural.yml to install ripgrep in a run step and invoke rg.
  pin_py="$(command -v python3 || true)"
  # PREGATE_IMAGE_PIN_ROOT is a test hook. Unset or empty, the helper checks
  # this repo's workflows. Set to a directory or file, it checks that path,
  # so a fixture can fail the lint without editing the real rules. A missing
  # path fails closed inside the helper.
  pin_root=".github/workflows"
  if [[ -n "${PREGATE_IMAGE_PIN_ROOT:-}" ]]; then
    pin_root="$PREGATE_IMAGE_PIN_ROOT"
  fi
  if [[ -z "$pin_py" ]]; then
    echo "FAIL: workflow image pin: python3 not on PATH"
    fail=1
  elif ! "$pin_py" scripts/check_workflow_image_pin.py "$pin_root"; then
    fail=1
  fi
  return "$fail"
}

check_ci_parity() {
  nobwrap_env
  export PFY_STATE_DIR="$SCRATCH/state-ci"; mkdir -p "$PFY_STATE_DIR"
  local static_rc=0
  python3 - <<'PY' || static_rc=1
import re, sys
from pathlib import Path
p = Path("tests/test_pfy_build_local.py")
if not p.exists():
    print("FAIL: tests/test_pfy_build_local.py is missing")
    sys.exit(1)
text = p.read_text(encoding="utf-8")
fail = []
for name in ("test_missing_runtime_dir_is_not_reported_as_missing_bwrap",
             "test_runtime_dir_under_system_tmp_is_blocked"):
    m = re.search(rf"def {name}\(self\).*?(?=\n    def |\nclass |\Z)", text, re.S)
    if not m:
        fail.append(f"missing {name}")
        continue
    code = re.sub(r"#[^\n]*", "", m.group(0))  # a comment must not satisfy the pin
    if "auto_unsafe=False" not in code:
        fail.append(f"{name} does not pass auto_unsafe=False (CI auto-adds --unsafe-no-sandbox without bwrap)")
if fail:
    print("FAIL ci-parity static:", "; ".join(fail))
    sys.exit(1)
print("PASS static: runtime-dir tests pin auto_unsafe=False")
PY
  # Behavioral: run them with bwrap hidden even if the static pin failed.
  python3 -m unittest -v \
    tests.test_pfy_build_local.LocalBuildTests.test_missing_runtime_dir_is_not_reported_as_missing_bwrap \
    tests.test_pfy_build_local.LocalBuildTests.test_runtime_dir_under_system_tmp_is_blocked
  return "$static_rc"
}

check_ubuntu_parity() {
  # One suite run for this commit. bwrap is hidden so this matches the pinned
  # ubuntu-24.04 image. eval-structural does not run the suite again. It
  # re-runs only the bwrap-sensitive modules with the host PATH, so sandbox
  # tests still execute on nimo. A docs-only or empty selection runs nothing.
  echo "selection mode=$SEL_MODE modules=$SEL_COUNT reason=$SEL_REASON"
  if [[ "$SEL_MODE" == "error" ]]; then
    echo "selection failed"
    return 1
  fi
  if [[ "$SEL_MODE" == "none" || "$SEL_MODE" == "structural" || "${SEL_COUNT:-0}" -eq 0 ]]; then
    echo "no unittest modules (mode=$SEL_MODE)"
    return 0
  fi
  nobwrap_env
  export PFY_STATE_DIR="$SCRATCH/state-ubuntu"; mkdir -p "$PFY_STATE_DIR"
  python3 scripts/run_tests.py --receipt "$RECEIPTS/ubuntu-tests.json" "${SEL_MODULES[@]}"
}

check_eval_structural() {
  # Same non-suite commands as the G0 ubuntu job. Receipts go to the run folder
  # so the tracked pipelines/eval/*.latest.md files are never rewritten (--in-place).
  # Unittests are SKIP here. ubuntu-parity already ran the selected suite once
  # with bwrap hidden. Modules whose source mentions bwrap run again with the
  # host PATH so the sandbox cases are not only skipped.
  if [[ "$SEL_MODE" == "error" ]]; then
    echo "selection failed"
    return 1
  fi
  python3 examples/eval-harness/run_structural.py --skip-unittests --write-md "$RECEIPTS/structural.latest.md"
  python3 examples/eval-harness/run_golden.py --write-md "$RECEIPTS/golden.latest.md"
  PFY_GAB_OFFLINE=1 python3 scripts/pfy_gab_228.py --selftest
  PFY_JEV_OFFLINE=1 python3 scripts/pfy_jev_230.py --selftest
  python3 scripts/pfy_launch_wizard_225.py --selftest
  python3 scripts/catalog_check.py
  ./pfy toolset matrix
  ./pfy toolset plan jev --harness opencode
  ./pfy hedge decide --task bulk --local ready --budget 0
  git ls-files -s -- pfy scripts/pfy
  test -x pfy && test -x scripts/pfy
  bash -n scripts/pfy
  python3 -m py_compile scripts/pfy-board.py scripts/pfy-gui.py
  ./pfy help >/dev/null
  python3 scripts/check_no_encoded_payloads.py --selftest
  python3 scripts/check_no_encoded_payloads.py
  if [[ -f "$SEL_JSON" ]]; then
    python3 scripts/test_select.py --structural-checks --selection "$SEL_JSON"
  fi
  if [[ "$SEL_MODE" == "none" || "$SEL_MODE" == "structural" || "${SEL_COUNT:-0}" -eq 0 ]]; then
    echo "no bwrap re-run (mode=$SEL_MODE)"
    return 0
  fi
  mapfile -t BWRAP_MODS < <(python3 scripts/run_tests.py --print-bwrap "${SEL_MODULES[@]}")
  if [[ ${#BWRAP_MODS[@]} -eq 0 ]]; then
    echo "no bwrap-sensitive modules in the selection"
    return 0
  fi
  echo "bwrap-sensitive re-run: ${#BWRAP_MODS[@]} module(s) with host PATH"
  export PFY_STATE_DIR="$SCRATCH/state-bwrap"; mkdir -p "$PFY_STATE_DIR"
  python3 scripts/run_tests.py --receipt "$RECEIPTS/bwrap-host.json" "${BWRAP_MODS[@]}"
}

check_suite() {
  export PFY_STATE_DIR="$SCRATCH/state-suite"; mkdir -p "$PFY_STATE_DIR"
  if [[ "${SEL_COUNT:-0}" -eq 0 ]]; then
    echo "selection mode=$SEL_MODE has no modules"
    return 0
  fi
  python3 scripts/run_tests.py "${SEL_MODULES[@]}"
}

check_orphans() {
  if [[ -n "${PS_BEFORE_FAILED:-}" ]]; then echo "FAIL: ps snapshot before checks failed"; return 1; fi
  local leak=0
  python3 "$SCRIPT_DIR/pregate_orphans.py" leaks \
    "$ORPHAN_SEEN" "$LOG_DIR/ps-before.txt" "$$" "$RUN_ROOT" "$SCRATCH" || leak=1
  if find "$RUN_ROOT/tmp" "$SCRATCH" \( -name 'orphan*.pid' -o -name 'orphan*.heartbeat' \) 2>/dev/null | grep .; then
    echo "LEAK: orphan pid/heartbeat files above"
    leak=1
  fi
  [[ $leak -eq 0 ]] && echo "no new live processes under this run root/scratch (argv or cwd)"
  return "$leak"
}

check_gate_hash() {
  python3 - <<'PY'
"""Worktree vs HEAD for tests/ and gate files, plus committed gate-file changes vs base."""
import os, subprocess, sys
from pathlib import Path

GATE = {"conftest.py", "pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml",
        "sitecustomize.py", "usercustomize.py", ".gitignore", ".gitattributes"}
STRICT = GATE - {".gitignore", ".gitattributes"}

def git(*a):
    return subprocess.run(["git", *a], check=True, capture_output=True).stdout

def names(raw):
    return [r.decode("utf-8", "surrogateescape") for r in raw.split(b"\0") if r]

def protected(rel):
    return rel.startswith("tests/") or Path(rel).name in GATE

fail, notes = [], []
head = {}
for line in git("ls-tree", "-r", "-z", "HEAD").split(b"\0"):
    if not line:
        continue
    meta, path = line.split(b"\t", 1)
    rel = path.decode("utf-8", "surrogateescape")
    if protected(rel):
        head[rel] = meta.split()[2].decode()
for rel, blob in head.items():
    p = Path(rel)
    if not p.exists():
        fail.append(f"deleted or renamed vs HEAD: {rel}")
    elif p.is_file() and git("hash-object", "--", rel).decode().strip() != blob:
        fail.append(f"modified vs HEAD: {rel}")
current = set(names(git("ls-files", "-z", "--cached", "--others", "--exclude-standard")))
for rel in sorted(current - set(head)):
    if rel.startswith("tmp/") or not protected(rel):
        continue
    if Path(rel).name in GATE or rel.endswith(".py"):
        fail.append(f"new vs HEAD (staged or untracked): {rel}")

base = os.environ.get("BASE_SHA", "")
if base:
    mb = git("merge-base", base, "HEAD").decode().strip()
    raw = names(git("diff", "--name-status", "-z", "--no-renames", mb, "HEAD"))
    for status, rel in zip(raw[0::2], raw[1::2]):
        name = Path(rel).name
        if name in STRICT:
            fail.append(f"committed {status} of gate file vs base {mb[:7]}: {rel} (needs explicit reviewer waiver)")
        elif name in GATE:
            notes.append(f"committed {status} vs base: {rel}")
        elif rel.startswith("tests/") and status in ("M", "D"):
            notes.append(f"REVIEW: existing test {'modified' if status == 'M' else 'deleted'} vs base: {rel}")
else:
    fail.append("base sha missing; committed gate-file diff cannot run")

print(f"checked {len(head)} protected paths at HEAD")
for n in notes:
    print("NOTE", n)
if fail:
    print("FAIL gate-hash:")
    for f in fail:
        print(" ", f)
    sys.exit(1)
print("PASS gate-hash")
PY
}

# Selection is one diff. ubuntu-parity runs that list once (bwrap hidden).
# eval-structural skips the suite inside run_structural and re-runs only
# bwrap-sensitive modules with the host PATH.
SEL_JSON="$LOG_DIR/selection.json"
SEL_MODE="error"
SEL_COUNT=0
SEL_REASON=""
SEL_MODULES=()
compute_selection() {
  if [[ "$FORCE_FULL" -eq 1 ]]; then
    mapfile -t SEL_MODULES < <(python3 scripts/run_tests.py --list)
    SEL_MODE="full"
    SEL_REASON="pregate --full"
    SEL_COUNT="${#SEL_MODULES[@]}"
    MODE="$SEL_MODE" REASON="$SEL_REASON" OUT="$SEL_JSON" python3 - "${SEL_MODULES[@]}" <<'PY'
import json, os, sys
json.dump(
    {
        "mode": os.environ["MODE"],
        "reason": os.environ["REASON"],
        "modules": sys.argv[1:],
        "changed": [],
        "source": "ast",
    },
    open(os.environ["OUT"], "w", encoding="utf-8"),
    indent=2,
)
PY
    return 0
  fi
  if ! python3 scripts/test_select.py --base "$BASE_SHA" --head HEAD >"$SEL_JSON"; then
    return 1
  fi
  SEL_MODE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["mode"])' "$SEL_JSON")"
  SEL_REASON="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["reason"])' "$SEL_JSON")"
  mapfile -t SEL_MODULES < <(python3 -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["modules"]))' "$SEL_JSON")
  SEL_COUNT="${#SEL_MODULES[@]}"
}
if compute_selection; then
  echo "selection mode=$SEL_MODE modules=$SEL_COUNT"
else
  record FAIL selection "test_select failed"
  SEL_MODE="error"
fi

# Order: fast checks first, then the one selected suite, then the after-scan.
should_run lint && run_check lint "filemode, launchers, encoded payloads, smoke_contract, catalog, workflow image pin" check_lint
should_run ci-parity && run_check ci-parity "bwrap hidden; runtime-dir tests pin auto_unsafe=False and pass" check_ci_parity
should_run gate-hash && run_check gate-hash "tests/ and gate files match HEAD; no committed gate-file change vs base" check_gate_hash
should_run ubuntu-parity && run_check ubuntu-parity "selected suite once with bwrap hidden (mode=${SEL_MODE} modules=${SEL_COUNT})" check_ubuntu_parity
should_run eval-structural && run_check eval-structural "G0 steps with unittests skipped; bwrap-sensitive modules again on host PATH (mode=${SEL_MODE})" check_eval_structural
if should_run suite; then
  if [[ "$FORCE_SUITE" -eq 1 || ",$ONLY," == *",suite,"* ]]; then
    run_check suite "extra host-PATH run of the selection; use --force-suite" check_suite
  else
    record SKIP suite "ubuntu-parity already ran the selected suite once; use --force-suite"
  fi
fi
should_run orphans && run_check orphans "no new live processes under the run root or scratch" check_orphans

if [[ "$FAIL_COUNT" -eq 0 && "$PASS_COUNT" -gt 0 && "$SEL_MODE" != "error" && -f "$SEL_JSON" ]]; then
  if [[ -n "$(git status --porcelain 2>/dev/null || true)" ]]; then
    echo "test cache not recorded: dirty worktree"
  elif [[ "$SEL_MODE" == "affected" || "$SEL_MODE" == "full" ]] && [[ ! -f "$RECEIPTS/ubuntu-tests.json" ]]; then
    # --only lint (or a skipped ubuntu-parity) must not cache a suite PASS.
    echo "test cache not recorded: no suite receipt for mode=$SEL_MODE"
  else
    receipt_args=()
    if [[ -f "$RECEIPTS/ubuntu-tests.json" ]]; then
      receipt_args=(--receipt "$RECEIPTS/ubuntu-tests.json")
    fi
    if python3 scripts/test_cache.py record --selection "$SEL_JSON" "${receipt_args[@]}"; then
      record PASS test-cache "recorded mode=$SEL_MODE modules=$SEL_COUNT"
    else
      record FAIL test-cache "record failed"
    fi
  fi
fi

# Notes from gate-hash (e.g. modified tests vs base) go into the summary detail.
if [[ -f "$LOG_DIR/gate-hash.log" ]] && grep -q '^NOTE REVIEW' "$LOG_DIR/gate-hash.log"; then
  record NOTE gate-hash "$(grep -c '^NOTE REVIEW' "$LOG_DIR/gate-hash.log") existing test file(s) changed vs base; reviewer should read gate-hash.log"
fi
echo "TMPDIR: $TMPDIR_POLICY" >"$LOG_DIR/env.txt"

trap - INT TERM HUP
if write_summary; then exit 0; else exit 1; fi
