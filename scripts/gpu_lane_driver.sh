#!/usr/bin/env bash
# Run operator-approved GPU and over-25 GB eval lanes one at a time.
#
#   scripts/gpu_lane_driver.sh --root WT [--state DIR] [--slugs "a b c"] [--once]
#
# Slugs default to eval/catalog-queue/approvals.tsv in the private ops
# checkout ($PFY_OPS_ROOT, else $ROOT/tmp/ops), first-seen order. The
# catalog loop skips these slugs (--launch-check prints gpu-driver), so this
# driver is the only thing that starts them, and it starts one lane at a
# time: no two GPU runs compete.
#
# Before each lane:
#   - STOP: $STATE/STOP, $GPU_STATE/STOP, or $ROOT/tmp/STOP stops the driver.
#   - GPU and RAM headroom: three samples PFY_GPU_SAMPLE_SEC apart must all
#     show GPU busy <= PFY_GPU_BUSY_MAX percent (rocm-smi, else
#     /sys/class/drm/card*/device/gpu_busy_percent, else nvidia-smi) and
#     MemAvailable >= PFY_GPU_MIN_RAM_GIB. Otherwise wait PFY_GPU_WAIT_SEC and
#     check again, up to PFY_GPU_MAX_WAITS times, then park "no headroom".
#     The driver never stops, signals, or reconfigures another process.
#   - Disk: a slug approved for pull-over-25gb needs the largest GB figure on
#     its card (default 40) plus PFY_GPU_DISK_MARGIN_GB free under
#     PFY_GPU_PULL_DIR (default ~/.cache/pfy/tools), else park "no disk".
# Then it writes the lane marker (noclobber), a GPU ticket in
# $STATE/tickets/TICKET-<slug>.md, and runs scripts/eval_lane.sh in the
# foreground. The lane writes VERDICT.json, its receipt, and ops traces the
# normal way (lane_ops_sync.py).
#
# Markers in $GPU_STATE (default $STATE/../gpu):
#   driver.pid  driver pid      progress.md  timestamped lines
#   current     slug now running
#   <slug>.started / <slug>.finished (exit code) / <slug>.parked (reason)
#   ALL_DONE    every slug finished or parked
# A slug with .finished or .parked is skipped on a rerun. A second driver
# exits 2 while driver.pid names a live process.
set -u

ROOT=""
STATE="${PFY_LOOP_STATE:-$HOME/DEVELOP/pfy-mentat/tmp/loop}/eval"
SLUGS=""
ONCE=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --root) ROOT=${2:-}; shift 2 ;;
    --state) STATE=${2:-}; shift 2 ;;
    --slugs) SLUGS=${2:-}; shift 2 ;;
    --once) ONCE=1; shift ;;
    *) printf 'unknown arg %s\n' "$1" >&2; exit 2 ;;
  esac
done
[ -n "$ROOT" ] || { printf '%s\n' "missing --root" >&2; exit 2; }
ROOT=$(cd "$ROOT" && pwd) || exit 2
HERE=$(cd "$(dirname "$0")" && pwd) || exit 2
GPU_STATE="${PFY_GPU_STATE:-$(dirname "$STATE")/gpu}"
BUSY_MAX="${PFY_GPU_BUSY_MAX:-30}"
MIN_RAM="${PFY_GPU_MIN_RAM_GIB:-24}"
SAMPLE_SEC="${PFY_GPU_SAMPLE_SEC:-10}"
WAIT_SEC="${PFY_GPU_WAIT_SEC:-300}"
MAX_WAITS="${PFY_GPU_MAX_WAITS:-36}"
MARGIN="${PFY_GPU_DISK_MARGIN_GB:-50}"
PULL_DIR="${PFY_GPU_PULL_DIR:-$HOME/.cache/pfy/tools}"
LANE="${PFY_GPU_LANE:-$ROOT/scripts/eval_lane.sh}"
APPROVALS="${PFY_OPS_ROOT:-$ROOT/tmp/ops}/eval/catalog-queue/approvals.tsv"
mkdir -p "$GPU_STATE" "$STATE/tickets" "$PULL_DIR"

progress() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$GPU_STATE/progress.md"; }

if [ -f "$GPU_STATE/driver.pid" ]; then
  old=$(awk 'NR==1{print $1}' "$GPU_STATE/driver.pid")
  if [[ "$old" =~ ^[0-9]+$ ]] && [ "$old" != "$$" ] && [ -d "/proc/$old" ]; then
    printf 'driver already running: %s\n' "$old" >&2
    exit 2
  fi
fi
printf '%s\n' "$$" > "$GPU_STATE/driver.pid"
trap 'rm -f "$GPU_STATE/current"' EXIT

if [ -z "$SLUGS" ]; then
  SLUGS=$(awk -F'\t' 'NR>1 && $1!="" && !seen[$1]++ {print $1}' "$APPROVALS")
fi

stop_now() { [ -f "$(dirname "$STATE")/STOP" ] || [ -f "$GPU_STATE/STOP" ] || [ -f "$ROOT/tmp/STOP" ]; }

gpu_busy() {
  local v=""
  if command -v rocm-smi >/dev/null 2>&1; then
    v=$(rocm-smi --showuse 2>/dev/null | sed -n 's/.*GPU use (%): *\([0-9][0-9]*\).*/\1/p' | sort -n | tail -n 1)
  fi
  if [ -z "$v" ]; then
    v=$(cat /sys/class/drm/card*/device/gpu_busy_percent 2>/dev/null | sort -n | tail -n 1)
  fi
  if [ -z "$v" ] && command -v nvidia-smi >/dev/null 2>&1; then
    v=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | sort -n | tail -n 1)
  fi
  printf '%s\n' "${v:-100}"
}

ram_gib() { awk '/^MemAvailable:/ {printf "%d\n", $2/1048576}' /proc/meminfo; }

headroom() {
  local i busy ram
  for i in 1 2 3; do
    busy=$(gpu_busy); ram=$(ram_gib)
    HEADROOM_LAST="gpu_busy=${busy}% ram_avail=${ram}GiB"
    if [ "$busy" -gt "$BUSY_MAX" ] || [ "$ram" -lt "$MIN_RAM" ]; then
      return 1
    fi
    [ "$i" -lt 3 ] && sleep "$SAMPLE_SEC"
  done
  return 0
}

approved_pull() { awk -F'\t' -v s="$1" '$1==s && $2=="pull-over-25gb" {f=1} END {exit !f}' "$APPROVALS"; }

need_gb() {
  local card="$ROOT/data/stages/$1.json" n=""
  if [ -f "$card" ]; then
    n=$(grep -o -i -E '[0-9]+(\.[0-9]+)? ?gi?b\b' "$card" | grep -o -E '^[0-9]+(\.[0-9]+)?' | sort -n | tail -n 1)
  fi
  printf '%s\n' "${n:-40}" | awk '{printf "%d\n", $1 + 0.999}'
}

free_gb() { df -P -BG "$PULL_DIR" | awk 'NR==2 {gsub("G","",$4); print $4}'; }

write_ticket() {
  local slug="$1" t="$STATE/tickets/TICKET-$1.md"
  cat > "$t" <<T
# GPU eval ticket: ${slug}

The operator approved the GPU and over-25 GB runs for this tool on 2026-11-10.
This lane is started by scripts/gpu_lane_driver.sh, one GPU lane at a time.

Write eval/evals/${slug}/VERDICT.json that matches docs/ops/VERDICT.schema.json.
Write the prose report to tmp/ops/eval/evals/${slug}/REPORT.md. Put traces and raw
logs under tmp/ops/eval/evals/${slug}/ too; the lane moves them to the private ops
checkout. Commit only VERDICT.json, receipts, probes, and fixtures, with no home
paths or names in them. Do not hand-edit integration_stage or tier_ceiling.
Read bootstrap/grok-cli/skills/catalog-eval-lane/SKILL.md and
bootstrap/grok-cli/skills/catalog-apply-and-ceiling/SKILL.md first.

## GPU rules

- Use the local GPU for the trial the card's next_gate asks for. Wrap every model
  start and every completion in scripts/model_lock.sh.
- Before starting a model, check rocm-smi --showuse --showmemuse and free -g. If
  GPU use is over ${BUSY_MAX}% or under ${MIN_RAM} GiB RAM is available, wait and
  check again. Do not start the model while the GPU is busy.
- Never stop, signal, restart, or reconfigure a process this lane did not start,
  including ollama serve and every process of the machine owner. No sudo, no
  system packages, no services, no port binds other than 127.0.0.1 on a free port.
- Before any download over 25 GB, run df -h on the target directory. If free
  space is less than the download plus ${MARGIN} GB, do not download: propose STAY
  with the reason "no disk". Put downloads under ~/.cache/pfy/tools/${slug}/.
- Stop every process this lane started before it finishes.
- A timeout is not a pass. Record the measured numbers in VERDICT.json.
T
  printf '%s\n' "$t"
}

total=0; ended=0
for slug in $SLUGS; do
  total=$((total + 1))
  if [ -f "$GPU_STATE/$slug.finished" ] || [ -f "$GPU_STATE/$slug.parked" ]; then
    ended=$((ended + 1)); continue
  fi
  if stop_now; then progress "STOP file, driver exits before $slug"; exit 0; fi
  waits=0
  until headroom; do
    waits=$((waits + 1))
    progress "$slug waiting for headroom ($HEADROOM_LAST) $waits/$MAX_WAITS"
    if [ "$waits" -ge "$MAX_WAITS" ]; then break; fi
    sleep "$WAIT_SEC"
    if stop_now; then progress "STOP file while waiting"; exit 0; fi
  done
  if [ "$waits" -ge "$MAX_WAITS" ]; then
    printf '%s\n' "no headroom ($HEADROOM_LAST)" > "$GPU_STATE/$slug.parked"
    progress "$slug parked: no headroom"; ended=$((ended + 1)); continue
  fi
  if approved_pull "$slug"; then
    need=$(need_gb "$slug"); have=$(free_gb)
    if [ "$have" -lt $((need + MARGIN)) ]; then
      printf 'no disk (free %sG, need %sG + %sG)\n' "$have" "$need" "$MARGIN" > "$GPU_STATE/$slug.parked"
      progress "$slug parked: no disk free=${have}G need=${need}G"; ended=$((ended + 1)); continue
    fi
    progress "$slug disk ok free=${have}G need=${need}G"
  fi
  marker="$STATE/$slug.dispatched"
  if ! (set -o noclobber; printf 'pid %s gpu-driver\n' "$$" > "$marker") 2>/dev/null; then
    printf '%s\n' "already dispatched" > "$GPU_STATE/$slug.parked"
    progress "$slug parked: already dispatched"; ended=$((ended + 1)); continue
  fi
  ticket=$(write_ticket "$slug")
  printf '%s\n' "$slug" > "$GPU_STATE/current"
  date -u +%Y-%m-%dT%H:%M:%SZ > "$GPU_STATE/$slug.started"
  progress "$slug start ($HEADROOM_LAST)"
  if [ "$slug" = "leann" ]; then
    # One leann lane holds scripts/model_lock.sh leann-model.lock across the trial and VERDICT.json.
    # An inherited held flag would skip this flock. The child drops the flag and
    # PFY_MODEL_LOCK so the lane still takes the shared model lock instead of
    # waiting on this same file. Light jobs never set PFY_LEANN_MODEL_LOCK and
    # do not take this flock.
    env -u PFY_MODEL_LOCK_HELD \
      PFY_MODEL_LOCK="${PFY_LEANN_MODEL_LOCK:-$HOME/.cache/pfy/locks/leann-model.lock}" \
      bash "$HERE/model_lock.sh" env -u PFY_MODEL_LOCK_HELD -u PFY_MODEL_LOCK PFY_LEANN_LANE=leann PFY_LANE_FROM_LOOP=1 "PFY_LOOP_STATE=$(dirname "$STATE")" \
      bash "$LANE" --slug leann --root "$ROOT" --state "$STATE" --ticket "$ticket" \
      > "$GPU_STATE/$slug.out" 2>&1
  else
    PFY_LANE_FROM_LOOP=1 PFY_LOOP_STATE="$(dirname "$STATE")" \
      bash "$LANE" --slug "$slug" --root "$ROOT" --state "$STATE" --ticket "$ticket" \
      > "$GPU_STATE/$slug.out" 2>&1
  fi
  rc=$?
  printf '%s\n' "$rc" > "$GPU_STATE/$slug.finished"
  rm -f "$GPU_STATE/current"
  progress "$slug finished rc=$rc"
  ended=$((ended + 1))
  [ "$ONCE" -eq 1 ] && break
done
if [ "$ended" -ge "$total" ]; then
  date -u +%Y-%m-%dT%H:%M:%SZ > "$GPU_STATE/ALL_DONE"
  progress "all done ($total slugs)"
fi
exit 0
