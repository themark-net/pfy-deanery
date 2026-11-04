#!/usr/bin/env bash
# Probe pluggable OpenAI-compatible local inference (ADR-0014).
# JSON: {"engine","base_url","status"}
# Detect order: freetoken → llama-swap → llama-server → ollama → shimmy
# Ready engines beat PATH-only partials. llama-swap owns :9292, llama-server owns :8080.
# Override: PFY_LOCAL_RUNTIME, LOCAL_OPENAI_BASE_URL
# #167: LOCAL_OPENAI_BASE_URL must not skip FreeToken-first when FreeToken (or earlier spine) is live.
set -euo pipefail
while [[ "${1:-}" == -* ]]; do shift || true; done

have() { command -v "$1" >/dev/null 2>&1; }
have_ft() { have ft || have freetoken; }

emit() {
  python3 -c 'import json,sys; print(json.dumps({"engine":sys.argv[1],"base_url":sys.argv[2],"status":sys.argv[3]}))' "$1" "$2" "$3"
}

http_ok() { curl -sf --max-time 1 "$1" >/dev/null 2>&1; }

probe() {
  local base="${1%/}"
  http_ok "$base/v1/models" && return 0
  http_ok "$base/health" && return 0
  http_ok "$base/api/tags" && return 0
  return 1
}

# Test-only pin. When set, do not probe the host spine or a live Ollama.
# Unset in normal use. A launch test points this at its own fake engine.
if [[ -n "${PFY_TEST_OPENAI_BASE:-}" ]]; then
  eng="${PFY_LOCAL_RUNTIME:-openai-compat}"
  base="${PFY_TEST_OPENAI_BASE%/}"
  if probe "$base"; then emit "$eng" "$base" "ready"; else emit "$eng" "$base" "partial"; fi
  exit 0
fi

# PFY_OLLAMA_BASE moves the Ollama probe off the default port (tests use a closed port).
OLLAMA_BASE="${PFY_OLLAMA_BASE:-http://127.0.0.1:11434}"
OLLAMA_BASE="${OLLAMA_BASE%/}"

# Test hook: do not probe fixed host ports. Honor only LOCAL_OPENAI_BASE_URL.
if [[ "${PFY_DETECT_SKIP_HOST:-}" == "1" ]]; then
  if [[ -n "${LOCAL_OPENAI_BASE_URL:-}" ]]; then
    eng="${PFY_LOCAL_RUNTIME:-openai-compat}"
    base="${LOCAL_OPENAI_BASE_URL%/}"
    if probe "$base"; then emit "$eng" "$base" "ready"; else emit "$eng" "$base" "partial"; fi
    exit 0
  fi
  emit "none" "" "missing"
  exit 0
fi

# First live spine before Ollama / env overrides (#167).
# FreeToken → llama-swap → llama-server (Ollama is later).
emit_spine_ready() {
  if have_ft && probe "http://127.0.0.1:1919"; then emit "freetoken" "http://127.0.0.1:1919" "ready"; return 0; fi
  if probe "http://127.0.0.1:1919"; then emit "freetoken" "http://127.0.0.1:1919" "ready"; return 0; fi
  if have llama-swap && probe "http://127.0.0.1:9292"; then emit "llama-swap" "http://127.0.0.1:9292" "ready"; return 0; fi
  if have llama-server && probe "http://127.0.0.1:8080"; then emit "llama-server" "http://127.0.0.1:8080" "ready"; return 0; fi
  if probe "http://127.0.0.1:8080"; then emit "llama-server" "http://127.0.0.1:8080" "ready"; return 0; fi
  return 1
}

if [[ -n "${LOCAL_OPENAI_BASE_URL:-}" ]]; then
  # Prefer FreeToken (etc.) when live — do not let an Ollama base_url win (#167).
  if emit_spine_ready; then exit 0; fi
  eng="${PFY_LOCAL_RUNTIME:-openai-compat}"
  base="${LOCAL_OPENAI_BASE_URL%/}"
  if probe "$base"; then emit "$eng" "$base" "ready"; else emit "$eng" "$base" "partial"; fi
  exit 0
fi

if [[ -n "${PFY_LOCAL_RUNTIME:-}" ]]; then
  # Hard pin still allowed, but if FreeToken is live and pin is ollama, FreeToken wins for usage (#167).
  case "$PFY_LOCAL_RUNTIME" in
    ollama|openai-compat)
      if emit_spine_ready; then exit 0; fi
      ;;
  esac
  case "$PFY_LOCAL_RUNTIME" in
    freetoken|ft) bases=(http://127.0.0.1:1919) ;;
    llama-swap) bases=(http://127.0.0.1:9292) ;;
    llama-server|llama.cpp) bases=(http://127.0.0.1:8080) ;;
    shimmy) bases=(http://127.0.0.1:11435) ;;
    ollama)
      if probe "$OLLAMA_BASE"; then emit "ollama" "$OLLAMA_BASE" "ready"; exit 0; fi
      if have ollama; then emit "ollama" "$OLLAMA_BASE" "partial"; else emit "ollama" "" "missing"; fi
      exit 0
      ;;
    *) bases=(http://127.0.0.1:1919) ;;
  esac
  for b in "${bases[@]}"; do
    if probe "$b"; then emit "$PFY_LOCAL_RUNTIME" "$b" "ready"; exit 0; fi
  done
  emit "$PFY_LOCAL_RUNTIME" "${bases[0]}" "partial"
  exit 0
fi

# Ready first (do not exit on PATH-only partial).
if emit_spine_ready; then exit 0; fi

if have ollama && probe "$OLLAMA_BASE"; then emit "ollama" "$OLLAMA_BASE" "ready"; exit 0; fi
if probe "$OLLAMA_BASE"; then emit "ollama" "$OLLAMA_BASE" "ready"; exit 0; fi

if have shimmy && probe "http://127.0.0.1:11435"; then emit "shimmy" "http://127.0.0.1:11435" "ready"; exit 0; fi

# PATH-only partial, same order. Missing binary is not a winner.
if have_ft; then emit "freetoken" "http://127.0.0.1:1919" "partial"; exit 0; fi
if have llama-swap; then emit "llama-swap" "http://127.0.0.1:9292" "partial"; exit 0; fi
if have llama-server; then emit "llama-server" "http://127.0.0.1:8080" "partial"; exit 0; fi
if have ollama; then emit "ollama" "$OLLAMA_BASE" "partial"; exit 0; fi
if have shimmy; then emit "shimmy" "http://127.0.0.1:11435" "partial"; exit 0; fi

emit "none" "" "missing"
