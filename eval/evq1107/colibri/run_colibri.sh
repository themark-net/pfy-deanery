#!/bin/sh
# One colibri serve + probe. Caller holds scripts/model_lock.sh.
# vulkan: COLI_VULKAN=1 on RADV. cpu: COLI_VULKAN=0 and --gpu none.
set -eu

gpu_mode="${1:?vulkan or cpu}"
root=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
cache="${COLIBRI_CACHE:-$HOME/.cache/pfy/tools/colibri}"
model="$cache/models/qwen36.colibri"
port=18112
log="$root/serve-${gpu_mode}.log"
pidfile="$root/serve-${gpu_mode}.pid"
out="$root/colibri-${gpu_mode}.json"
need_bytes=$((21718480960 + 25 * 1024 * 1024 * 1024))

mem_kib() {
  awk '/MemAvailable/ {print $2}' /proc/meminfo
}

echo "ollama ps before:"
ollama ps || true
avail=$(mem_kib)
echo "MemAvailable_kB $avail need_bytes $need_bytes"
# Wait only when the headroom rule fails. Cap 30 minutes.
deadline=$(( $(date +%s) + 1800 ))
while [ $((avail * 1024)) -lt "$need_bytes" ]; do
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "HOST-BUSY MemAvailable_kB=$avail"
    printf '%s\n' '{"summary":{"error":"HOST-BUSY"}}' > "$out"
    exit 3
  fi
  sleep 30
  avail=$(mem_kib)
  echo "wait MemAvailable_kB $avail"
done

# --gpu is the CUDA switch. This Linux archive has no CUDA build.
# Vulkan is COLI_VULKAN=1 plus the shader dir. Pin RADV so llvmpipe is not chosen.
export HOME="$cache/home"
export XDG_CONFIG_HOME="$cache/xdg/config"
export XDG_CACHE_HOME="$cache/xdg/cache"
export TMPDIR="$cache/tmp"
unset COLI_API_KEY || true
unset COLI_CUDA || true
if [ "$gpu_mode" = "vulkan" ]; then
  export COLI_VULKAN=1
  export COLI_VK_SHADERS="$cache/app/shaders"
  export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.json
  export VK_DRIVER_FILES=/usr/share/vulkan/icd.d/radeon_icd.json
  gpu_args=""
else
  export COLI_VULKAN=0
  gpu_args="--gpu none"
fi

cleanup() {
  if [ -f "$pidfile" ]; then
    pid=$(cat "$pidfile" || true)
    if [ -n "${pid:-}" ]; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
    rm -f "$pidfile"
  fi
  # Stop only the port this script opened. coli stop defaults to 8000.
  (cd "$cache/app" && ./coli stop --port "$port" >/dev/null 2>&1) || true
}
trap cleanup EXIT INT TERM

cd "$cache/app"
# --auto-tier: upstream says Qwen3.6's default 8 slots/layer is the slow path.
# --ram 48 keeps the plan inside the headroom we checked.
# shellcheck disable=SC2086
./coli serve \
  --model "$model" \
  --host 127.0.0.1 \
  --port "$port" \
  --model-id qwen36-colibri \
  $gpu_args \
  --auto-tier \
  --ram 48 \
  --ctx 2048 \
  --no-think \
  --temp 0 \
  --no-tune-profile \
  --policy quality \
  > "$log" 2>&1 &
echo $! > "$pidfile"

ready=0
i=0
while [ "$i" -lt 90 ]; do
  if curl -fsS "http://127.0.0.1:${port}/v1/models" >/dev/null 2>&1; then
    ready=1
    break
  fi
  if ! kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "server exited early"
    break
  fi
  i=$((i + 1))
  sleep 2
done

if [ "$ready" != 1 ]; then
  echo "NOT READY"
  tail -n 40 "$log" || true
  exit 1
fi

python3 "$root/probe.py" \
  --api openai \
  --url "http://127.0.0.1:${port}/v1/chat/completions" \
  --model qwen36-colibri \
  --out "$out" \
  --timeout 180 \
  --runs 2
echo "probe wrote $out"
