# agent-cage harness wrapper for pfy-mentat
# Multi-OS friendly entry (Linux / macOS / Windows-WSL).
#
# IMPORTANT:
#   - Run targets from this directory OR use repo-root: make cage-*
#   - `agentcage` discovers the project via AGENTCAGE_DIR or ~/.agentcage
#     (after `agentcage init`), NOT the catalog repo root.
#   - Services must be started (`make up` / `make up-mcp`) before `make test`.
#   - Prefer running catalog tool smokes INSIDE the cage (versioned images).

SHELL := /bin/bash
.DEFAULT_GOAL := help

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
CATALOG_ROOT := $(abspath $(ROOT)/../..)
PIN := $(shell tr -d '[:space:]' < $(ROOT)/PINNED_COMMIT)
UPSTREAM := https://github.com/pnnl/agent-cage.git

# Runtime project directory used by the agentcage CLI (after init).
# Override: make up AGENTCAGE_DIR=/path/to/project
AGENTCAGE_DIR ?= $(HOME)/.agentcage

# Optional source checkout (for pin tracking / editable install). Separate from runtime.
CAGE_SRC ?= $(HOME)/.local/share/pfy-mentat/agent-cage

export AGENTCAGE_DIR
export PATH := $(HOME)/.local/bin:$(PATH)

UNAME_S := $(shell uname -s 2>/dev/null || echo unknown)

GROK_OVERLAY := $(ROOT)/overlays/grok
GROK_IMAGE := pfy-mentat/agent-cage-grok:0.1.0
POLICY ?= default

LOCAL_OLLAMA_OVERLAY := $(ROOT)/overlays/local-ollama
LITELLM_EXAMPLE := $(CATALOG_ROOT)/examples/litellm-ollama
MODEL_LOCK := $(CATALOG_ROOT)/scripts/model_lock.sh
LITELLM_SMOKE_MODEL ?= deepseek-coder:latest
CM_EXAMPLE := $(CATALOG_ROOT)/examples/codebase-memory-mcp
RW_EXAMPLE := $(CATALOG_ROOT)/examples/repowise
REPOWISE_PIP_SPEC ?= repowise==0.30.0

.PHONY: help setup init update up up-mcp down shell status test logs dashboard \
	smoke-host smoke-integration doctor ensure-cli ensure-project \
	grok-overlay-install grok-overlay-uninstall grok-overlay-build grok-up grok-smoke \
	grok-auth-import workspace-sync grok-mcp-preset grok-ready \
	grok-ensure grok-shell grok-run grok-state-init fix-grok-state-perms \
	grok-skills-install grok-sessions-export grok-sessions-import-host \
	grok-sessions grok-resume grok-net-smoke \
	local-ollama-overlay-install local-ollama-up smoke-litellm-ollama \
	smoke-codebase-memory smoke-repowise smoke-context-tools \
	smoke-write-guard write-guard-overlay-install \
	eval-tier0 eval-tier1 eval-mvp eval-suite eval-matrix eval-v02

help:
	@echo "agent-cage harness (upstream pin $(PIN))"
	@echo "  AGENTCAGE_DIR=$(AGENTCAGE_DIR)   # runtime project for agentcage CLI"
	@echo "  CAGE_SRC=$(CAGE_SRC)            # optional pinned source clone"
	@echo "  OS=$(UNAME_S)"
	@echo ""
	@echo "First-time (this machine):"
	@echo "  make setup          # install agentcage CLI (+ optional source pin)"
	@echo "  make init           # materialize runtime to AGENTCAGE_DIR (~/.agentcage)"
	@echo "  make up-mcp         # start containers (build/pull images — can take a while)"
	@echo "  make status && make test && make shell"
	@echo "  make down"
	@echo ""
	@echo "From catalog repo root you can use: make cage-up-mcp  (etc.)"
	@echo ""
	@echo "Targets: doctor setup init update up up-mcp down shell status test logs"
	@echo "         dashboard smoke-host smoke-integration"
	@echo "Grok-in-image:"
	@echo "  make grok-overlay-install   # copy overlay into AGENTCAGE_DIR"
	@echo "  make grok-auth-import       # copy host ~/.grok/auth.json (OIDC session) into cage"
	@echo "  make grok-overlay-build     # build $(GROK_IMAGE)"
	@echo "  make grok-up                # up --mcp with coding-agent-grok policy"
	@echo "  make workspace-sync         # sync catalog repo → /workspace/pfy-mentat"
	@echo "  make grok-mcp-preset        # project .grok MCP → cage filesystem server"
	@echo "  make grok-smoke             # grok --version + auth.json"
	@echo "  make grok-ready             # T-0045 smoke (version+workspace+MCP)"
	@echo "  make grok-ensure            # idempotent: overlay+auth+build+up+sync+ready"
	@echo "  make grok-shell             # interactive bash @ /workspace/pfy-mentat"
	@echo "  make grok-run PROMPT='…'    # interactive grok in catalog tree"
	@echo "  make grok-net-smoke         # verify proxy allows xAI / cli-chat-proxy"
	@echo "  make grok-overlay-uninstall # remove override from runtime project"
	@echo "  Auth: browser/OIDC → auth.json (primary); XAI_API_KEY optional fallback"
	@echo "  If TUI corrupts terminal after crash: run  reset  (host shell)"
	@echo ""
	@echo "LiteLLM + host Ollama (in-cage smoke):"
	@echo "  make local-ollama-overlay-install"
	@echo "  make local-ollama-up          # policy coding-agent-local + host-gateway"
	@echo "  make smoke-litellm-ollama     # LiteLLM completion inside agent container"
	@echo "Context tools (in-cage):"
	@echo "  make smoke-codebase-memory    # binary index+search fixture"
	@echo "  make smoke-repowise           # pip pin + health (zero LLM)"
	@echo "  make smoke-context-tools      # both + T-0013 compare note"
	@echo "Write-guard:"
	@echo "  make smoke-write-guard        # policy selftest + audit/enforce in cage"
	@echo "  make write-guard-overlay-install"
	@echo "Eval (OQ-0002 opt5 + v0.2):"
	@echo "  make eval-tier0               # connectivity smoke (litellm-ollama)"
	@echo "  make eval-tier1               # one scored task (EVAL_TASK)"
	@echo "  make eval-mvp                 # tier0 + tier1"
	@echo "  make eval-suite               # all tasks, gate model"
	@echo "  make eval-matrix              # tasks × EVAL_MODELS (gate must pass)"
	@echo "  make eval-v02                 # tier0 + suite"

doctor:
	@echo "== OS =="; uname -a || true
	@echo "== docker =="; docker version --format '{{.Server.Version}}' 2>/dev/null || docker version 2>/dev/null | head -5 || echo "MISS docker"
	@echo "== docker compose =="; docker compose version 2>/dev/null || echo "MISS docker compose"
	@echo "== agentcage =="; command -v agentcage >/dev/null && agentcage --version || echo "MISS agentcage (make setup)"
	@echo "== AGENTCAGE_DIR =="; ls -la "$(AGENTCAGE_DIR)" 2>/dev/null | head -8 || echo "missing — run: make init"
	@echo "== pin (source) =="; echo $(PIN)
	@echo "== CAGE_SRC =="; ls -la "$(CAGE_SRC)" 2>/dev/null | head -5 || echo "optional source not cloned"

ensure-cli:
	@command -v agentcage >/dev/null 2>&1 || (echo "error: agentcage not on PATH. Run: make setup"; echo "hint: export PATH=\"\$$HOME/.local/bin:\$$PATH\""; exit 1)

ensure-project:
	@test -f "$(AGENTCAGE_DIR)/docker/docker-compose.yaml" \
	  || test -f "$(AGENTCAGE_DIR)/docker-compose.yaml" \
	  || (echo "error: no Agent Cage project at AGENTCAGE_DIR=$(AGENTCAGE_DIR)"; \
	      echo "Run: make init    # or: agentcage init"; exit 1)

setup:
	@mkdir -p "$(dir $(CAGE_SRC))"
	@if [ ! -d "$(CAGE_SRC)/.git" ]; then \
	  echo "==> clone $(UPSTREAM) @ $(PIN) → $(CAGE_SRC)"; \
	  git clone --filter=blob:none $(UPSTREAM) "$(CAGE_SRC)"; \
	  git -C "$(CAGE_SRC)" checkout $(PIN); \
	else \
	  echo "==> source already at $(CAGE_SRC); make update to re-pin"; \
	fi
	@echo "==> install agentcage CLI (uv tool preferred)"
	@if command -v uv >/dev/null 2>&1; then \
	  uv tool install -e "$(CAGE_SRC)" 2>/dev/null \
	    || uv tool install -e "$(CAGE_SRC)"; \
	else \
	  (cd "$(CAGE_SRC)" && python3 -m pip install -e . --user); \
	fi
	@command -v agentcage >/dev/null 2>&1 \
	  && echo "agentcage CLI OK: $$(agentcage --version 2>/dev/null || true)" \
	  || (echo "warn: agentcage not on PATH — add \$$HOME/.local/bin to PATH"; exit 1)
	@echo "Next: make init   then   make up-mcp"

init: ensure-cli
	@if [ -f "$(AGENTCAGE_DIR)/docker/docker-compose.yaml" ] || [ -f "$(AGENTCAGE_DIR)/docker-compose.yaml" ]; then \
	  echo "init: already present at $(AGENTCAGE_DIR) (skip — idempotent)"; \
	else \
	  echo "==> agentcage init --path $(AGENTCAGE_DIR)"; \
	  agentcage init --path "$(AGENTCAGE_DIR)" --no-completion; \
	fi
	@echo "Runtime project: $(AGENTCAGE_DIR)"
	@echo "Next: make up-mcp   (or: make grok-ensure for Grok Build path)"

update:
	@test -d "$(CAGE_SRC)/.git" || (echo "run make setup first"; exit 1)
	git -C "$(CAGE_SRC)" fetch origin
	git -C "$(CAGE_SRC)" checkout $(PIN)
	@echo "source checked out $(PIN)"

up: ensure-cli ensure-project
	@echo "==> agentcage up  (AGENTCAGE_DIR=$(AGENTCAGE_DIR) POLICY=$(POLICY))"
	@echo "    First run builds images — may take several minutes."
	POLICY=$(POLICY) agentcage up --policy $(POLICY)

up-mcp: ensure-cli ensure-project
	@echo "==> agentcage up --mcp  (AGENTCAGE_DIR=$(AGENTCAGE_DIR) POLICY=$(POLICY))"
	@echo "    First run builds images — may take several minutes."
	POLICY=$(POLICY) agentcage up --mcp --policy $(POLICY)

down: ensure-cli ensure-project
	agentcage down

shell: ensure-cli ensure-project
	agentcage shell

status: ensure-cli ensure-project
	agentcage status

test: ensure-cli ensure-project
	@echo "==> Requires running services. If agent is not running: make up-mcp"
	agentcage test --quick

logs: ensure-cli ensure-project
	agentcage logs

dashboard: ensure-cli ensure-project
	agentcage dashboard

smoke-host:
	@$(MAKE) doctor
	@test -n "$(PIN)"
	@python3 -c "import json; json.load(open('$(CATALOG_ROOT)/data/tools.json'))"
	@test -f "$(ROOT)/manifest.json"
	@echo "smoke-host: OK (no containers required)"

# Full path: host checks → ensure project → up-mcp → test (leaves stack up)
smoke-integration: smoke-host ensure-cli
	@if [ ! -f "$(AGENTCAGE_DIR)/docker/docker-compose.yaml" ] && [ ! -f "$(AGENTCAGE_DIR)/docker-compose.yaml" ]; then \
	  $(MAKE) init; \
	fi
	@$(MAKE) up-mcp
	@$(MAKE) status
	@$(MAKE) test || true
	@echo ""
	@echo "smoke-integration: stack should be UP. Inspect with: make shell | make status"
	@echo "Tear down: make down"
	@echo "Catalog tool smokes: install/run inside 'make shell' (/workspace); see README."

# --- Grok-in-image overlay ---------------------------------------------------

GROK_STATE_DIR := $(AGENTCAGE_DIR)/grok-state
GROK_SESSIONS_HOST := $(GROK_STATE_DIR)/sessions

# Dual host/agent write for sessions bind-mount (see scripts/fix-grok-state-perms.sh).
fix-grok-state-perms: ensure-project
	@chmod +x "$(ROOT)/scripts/fix-grok-state-perms.sh"
	@AGENTCAGE_DIR="$(AGENTCAGE_DIR)" "$(ROOT)/scripts/fix-grok-state-perms.sh" "$(AGENTCAGE_DIR)"

# Host store for Grok sessions (T-0047). Idempotent.
grok-state-init: ensure-project
	@mkdir -p "$(GROK_SESSIONS_HOST)"
	@$(MAKE) fix-grok-state-perms
	@# If container has sessions not yet on host, export them once before first mount.
	@if docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running; then \
	  if [ -z "$$(find "$(GROK_SESSIONS_HOST)" -mindepth 1 -maxdepth 1 2>/dev/null | head -1)" ]; then \
	    echo "==> exporting in-container sessions → $(GROK_SESSIONS_HOST)"; \
	    docker cp agent-cage-agent:/home/agent/.grok/sessions/. "$(GROK_SESSIONS_HOST)/" 2>/dev/null || true; \
	    $(MAKE) fix-grok-state-perms; \
	  fi; \
	fi
	@echo "grok-state-init: $(GROK_SESSIONS_HOST)"

grok-overlay-install: ensure-project
	@test -f "$(GROK_OVERLAY)/Dockerfile"
	@mkdir -p "$(AGENTCAGE_DIR)/docker/overlays-grok"
	@mkdir -p "$(AGENTCAGE_DIR)/grok-home"
	@chmod 700 "$(AGENTCAGE_DIR)/grok-home"
	@$(MAKE) grok-state-init
	@cp "$(GROK_OVERLAY)/Dockerfile" "$(AGENTCAGE_DIR)/docker/overlays-grok/Dockerfile"
	@cp "$(GROK_OVERLAY)/docker-compose.override.yaml" "$(AGENTCAGE_DIR)/docker/docker-compose.override.yaml"
	@cp "$(GROK_OVERLAY)/coding-agent-grok.yaml" "$(AGENTCAGE_DIR)/policies/coding-agent-grok.yaml"
	@# Active policy mount uses POLICY name; keep file fresh for mitm hot-reload
	@cp "$(GROK_OVERLAY)/coding-agent-grok.yaml" "$(AGENTCAGE_DIR)/policies/coding-agent-grok.yaml"
	@touch "$(AGENTCAGE_DIR)/policies/coding-agent-grok.yaml"
	@# ensure auth.json path exists so volume mount is a file-friendly dir
	@touch "$(AGENTCAGE_DIR)/grok-home/.keep"
	@echo "Installed Grok overlay into $(AGENTCAGE_DIR)"
	@echo "  docker/docker-compose.override.yaml"
	@echo "  docker/overlays-grok/Dockerfile"
	@echo "  policies/coding-agent-grok.yaml"
	@echo "  grok-home/auth.json → /home/agent/.grok/auth.json"
	@echo "  grok-state/sessions → /home/agent/.grok/sessions (persistent)"
	@echo "Next: make grok-auth-import   # copy host browser/OIDC session"
	@echo "      make grok-sessions-import-host   # map host project sessions into cage cwd"
	@echo "      make grok-overlay-build && make grok-up"

# Cage agent uid is 1001 in stock agent-cage image. Host copies are often uid 1000
# and mode 600 → agent cannot read auth.json → Grok falls back to ApiKey → 401 / OIDC noise.
CAGE_AGENT_UID ?= 1001
CAGE_AGENT_GID ?= 1001

grok-auth-import: ensure-project
	@test -f "$(HOME)/.grok/auth.json" \
	  || (echo "error: no host $(HOME)/.grok/auth.json — run 'grok login' on the host first"; exit 1)
	@mkdir -p "$(AGENTCAGE_DIR)/grok-home"
	@chmod 700 "$(AGENTCAGE_DIR)/grok-home"
	@# Always refresh from host OIDC (stale cage auth → login prompt / Auth: ApiKey 401).
	@# Prefer docker root write into the bind mount (no host sudo; avoids agent-owned 0600 trap).
	@set -e; \
	  tmp=$$(mktemp); \
	  cp "$(HOME)/.grok/auth.json" "$$tmp"; \
	  chmod 600 "$$tmp"; \
	  echo "Importing host OIDC/browser session → $(AGENTCAGE_DIR)/grok-home/auth.json"; \
	  echo "  auth_mode/email (redacted check):"; \
	  python3 -c "import json; d=json.load(open('$$tmp')); \
	    v=next(iter(d.values())) if isinstance(d, dict) else {}; \
	    print('  mode=', v.get('auth_mode'), ' email=', v.get('email','?'), ' expires_at=', v.get('expires_at','?'))"; \
	  written=0; \
	  if docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running; then \
	    if docker exec -i -u root agent-cage-agent bash -lc \
	        'cat > /home/agent/.grok/auth.json && chown agent:agent /home/agent/.grok/auth.json && chmod 600 /home/agent/.grok/auth.json' \
	        < "$$tmp"; then \
	      written=1; \
	      echo "  wrote via docker bind mount (agent-owned 0600)"; \
	    fi; \
	  fi; \
	  if [ "$$written" -eq 0 ]; then \
	    if install -m 600 -o $(CAGE_AGENT_UID) -g $(CAGE_AGENT_GID) "$$tmp" "$(AGENTCAGE_DIR)/grok-home/auth.json" 2>/dev/null; then \
	      written=1; echo "  wrote via install uid $(CAGE_AGENT_UID)"; \
	    elif sudo install -m 600 -o $(CAGE_AGENT_UID) -g $(CAGE_AGENT_GID) "$$tmp" "$(AGENTCAGE_DIR)/grok-home/auth.json"; then \
	      written=1; echo "  wrote via sudo install uid $(CAGE_AGENT_UID)"; \
	    fi; \
	  fi; \
	  rm -f "$$tmp"; \
	  if [ "$$written" -eq 0 ]; then \
	    echo "error: could not write cage auth.json (start agent or: sudo make cage-grok-auth-import)"; \
	    exit 1; \
	  fi
	@python3 -c "import os; p='$(AGENTCAGE_DIR)/grok-home/auth.json'; st=os.stat(p); \
	  print('  file uid:gid=', st.st_uid, st.st_gid, ' perm=', oct(st.st_mode)[-3:], \
	        '(agent-owned; host cannot open — expected)')" 2>/dev/null || true
	@echo "Done. Host 'grok login' then re-run this target whenever cage prompts for login."

grok-overlay-uninstall:
	@rm -f "$(AGENTCAGE_DIR)/docker/docker-compose.override.yaml"
	@rm -rf "$(AGENTCAGE_DIR)/docker/overlays-grok"
	@rm -f "$(AGENTCAGE_DIR)/policies/coding-agent-grok.yaml"
	@echo "Removed Grok overlay compose/policy (left grok-home/ and image in place)"
	@echo "To wipe imported auth: rm -rf $(AGENTCAGE_DIR)/grok-home"

grok-overlay-build: ensure-project
	@docker image inspect agent-cage-agent:latest >/dev/null 2>&1 \
	  || (echo "error: agent-cage-agent:latest missing — run make up once to build base"; exit 1)
	@test -f "$(AGENTCAGE_DIR)/docker/overlays-grok/Dockerfile" \
	  || (echo "error: run make grok-overlay-install first"; exit 1)
	docker build \
	  -t $(GROK_IMAGE) \
	  --build-arg BASE_IMAGE=agent-cage-agent:latest \
	  -f "$(AGENTCAGE_DIR)/docker/overlays-grok/Dockerfile" \
	  "$(AGENTCAGE_DIR)/docker/overlays-grok"
	@echo "Built $(GROK_IMAGE)"

# agentcage CLI only passes -f docker-compose.yaml (+ mcp). It does NOT load
# docker-compose.override.yaml when -f is set. Grok-up must call compose itself.
COMPOSE_DIR = $(AGENTCAGE_DIR)/docker
COMPOSE_GROK = docker compose -p agent-cage \
	-f $(COMPOSE_DIR)/docker-compose.yaml \
	-f $(COMPOSE_DIR)/docker-compose.mcp.yaml \
	-f $(COMPOSE_DIR)/docker-compose.override.yaml

grok-up: ensure-project
	@test -f "$(COMPOSE_DIR)/docker-compose.override.yaml" \
	  || (echo "error: run make grok-overlay-install first"; exit 1)
	@docker image inspect $(GROK_IMAGE) >/dev/null 2>&1 \
	  || (echo "error: $(GROK_IMAGE) missing — run make grok-overlay-build"; exit 1)
	@$(MAKE) grok-state-init
	@# Re-install override so sessions volume is present (idempotent)
	@cp "$(GROK_OVERLAY)/docker-compose.override.yaml" "$(COMPOSE_DIR)/docker-compose.override.yaml"
	@mkdir -p "$(AGENTCAGE_DIR)/grok-home"
	@if [ ! -f "$(AGENTCAGE_DIR)/grok-home/auth.json" ]; then \
	  echo "warn: no grok-home/auth.json — run make grok-auth-import or device-login in cage"; \
	fi
	@# Always re-copy Grok policy so proxy mount path POLICY=coding-agent-grok is correct
	@cp "$(GROK_OVERLAY)/coding-agent-grok.yaml" "$(AGENTCAGE_DIR)/policies/coding-agent-grok.yaml"
	@echo "==> docker compose up with Grok override (POLICY=coding-agent-grok)"
	@echo "    Note: agentcage CLI ignores compose override; this target uses -f override explicitly."
	@if [ -f "$(AGENTCAGE_DIR)/.env" ]; then set -a; . "$(AGENTCAGE_DIR)/.env"; set +a; fi; \
	cd "$(COMPOSE_DIR)" && \
	POLICY=coding-agent-grok \
	$(COMPOSE_GROK) --env-file "$(AGENTCAGE_DIR)/.env" up -d --force-recreate proxy agent 2>/dev/null \
	|| POLICY=coding-agent-grok $(COMPOSE_GROK) up -d --force-recreate proxy agent
	@echo "Waiting for agent container..."
	@sleep 4
	@# Auth: agent-only. Sessions: do NOT chown -R agent (breaks host import); open perms instead.
	@docker exec -u root agent-cage-agent bash -lc \
	  'if [ -f /home/agent/.grok/auth.json ]; then chown agent:agent /home/agent/.grok/auth.json; chmod 600 /home/agent/.grok/auth.json; fi; \
	   if [ -d /home/agent/.grok/sessions ]; then chmod -R a+rwX /home/agent/.grok/sessions; fi' \
	  2>/dev/null || true
	@$(MAKE) fix-grok-state-perms
	@docker inspect agent-cage-agent --format 'image={{.Config.Image}}'
	@docker exec -u agent agent-cage-agent bash -lc 'findmnt /home/agent/.grok/sessions 2>/dev/null || mount | grep sessions || ls -la /home/agent/.grok/sessions | head -5'
	@$(MAKE) grok-net-smoke || (echo "warn: grok-net-smoke failed — API may still be blocked"; true)
	@echo "Next: make grok-sessions-import-host && make grok-sessions"

grok-smoke: ensure-project
	@echo "==> which image is running?"
	@docker inspect agent-cage-agent --format 'Config.Image={{.Config.Image}}' 2>/dev/null \
	  || (echo "error: agent-cage-agent not running — make grok-up"; exit 1)
	@docker exec -u root agent-cage-agent bash -lc \
	  'if [ -f /home/agent/.grok/auth.json ]; then chown agent:agent /home/agent/.grok/auth.json; chmod 600 /home/agent/.grok/auth.json; ls -ln /home/agent/.grok/auth.json; fi' \
	  2>/dev/null || true
	@echo "==> grok --version + auth smoke inside agent container"
	@docker exec -u agent \
	  -e HOME=/home/agent \
	  -e GROK_HOME=/home/agent/.grok \
	  -e PATH=/usr/local/bin:/home/agent/.local/bin:/usr/bin:/bin \
	  agent-cage-agent bash -lc 'command -v grok; grok --version; test -r /home/agent/.grok/auth.json && echo auth.json:readable || echo auth.json:NOT_READABLE'

# Sync catalog repo into cage workspace so filesystem MCP + Grok share one tree.
# Destination: $(AGENTCAGE_DIR)/workspace/pfy-mentat → /workspace/pfy-mentat in agent.
WORKSPACE_REPO_NAME ?= pfy-mentat
WORKSPACE_REPO := $(AGENTCAGE_DIR)/workspace/$(WORKSPACE_REPO_NAME)

workspace-sync: ensure-project
	@test -d "$(CATALOG_ROOT)" || (echo "error: CATALOG_ROOT missing: $(CATALOG_ROOT)"; exit 1)
	@mkdir -p "$(AGENTCAGE_DIR)/workspace"
	@# Workspace is often owned by cage agent (uid 1001) or prior runs — ensure host can write.
	@docker exec -u root agent-cage-agent bash -lc \
	  'chmod a+rwx /workspace 2>/dev/null; mkdir -p /workspace/$(WORKSPACE_REPO_NAME); chown -R agent:agent /workspace/$(WORKSPACE_REPO_NAME) 2>/dev/null; chmod -R a+rwX /workspace/$(WORKSPACE_REPO_NAME) 2>/dev/null' \
	  2>/dev/null || chmod -R a+rwX "$(AGENTCAGE_DIR)/workspace" 2>/dev/null || true
	@echo "==> rsync catalog → $(WORKSPACE_REPO)"
	@# Content-only rsync: bind mounts often reject owner/group/times (rsync 23).
	@set +e; \
	  rsync -r --delete \
	    --exclude '.venv/' --exclude '**/.venv/' \
	    --exclude 'node_modules/' --exclude '**/node_modules/' \
	    --exclude '.agentcage/' --exclude '__pycache__/' --exclude '.grok/sessions/' \
	    --exclude '.env' --exclude '.env.*' \
	    "$(CATALOG_ROOT)/" "$(WORKSPACE_REPO)/"; \
	  rc=$$?; \
	  if [ $$rc -ne 0 ] && [ $$rc -ne 23 ] && [ $$rc -ne 24 ]; then \
	    docker exec -u root agent-cage-agent bash -lc \
	      'chmod -R a+rwX /workspace; mkdir -p /workspace/$(WORKSPACE_REPO_NAME)' 2>/dev/null; \
	    rsync -r --delete \
	      --exclude '.venv/' --exclude '**/.venv/' \
	      --exclude 'node_modules/' --exclude '**/node_modules/' \
	      --exclude '.agentcage/' --exclude '__pycache__/' --exclude '.grok/sessions/' \
	      --exclude '.env' --exclude '.env.*' \
	      "$(CATALOG_ROOT)/" "$(WORKSPACE_REPO)/"; \
	    rc=$$?; \
	  fi; \
	  if [ $$rc -ne 0 ] && [ $$rc -ne 23 ] && [ $$rc -ne 24 ]; then exit $$rc; fi; \
	  set -e
	@$(MAKE) grok-mcp-preset
	@# Keep project .grok/skills in sync with bootstrap first-party sources (cwd discovery).
	@mkdir -p "$(WORKSPACE_REPO)/.grok/skills"
	@if [ -d "$(WORKSPACE_REPO)/bootstrap/grok-cli/skills" ]; then \
	  for d in "$(WORKSPACE_REPO)/bootstrap/grok-cli/skills"/*/; do \
	    [ -d "$$d" ] || continue; \
	    name=$$(basename "$$d"); \
	    mkdir -p "$(WORKSPACE_REPO)/.grok/skills/$$name"; \
	    if command -v rsync >/dev/null 2>&1; then \
	      rsync -r --delete "$$d" "$(WORKSPACE_REPO)/.grok/skills/$$name/"; \
	    else \
	      rm -rf "$(WORKSPACE_REPO)/.grok/skills/$$name"; \
	      mkdir -p "$(WORKSPACE_REPO)/.grok/skills/$$name"; \
	      cp -a "$$d". "$(WORKSPACE_REPO)/.grok/skills/$$name/"; \
	    fi; \
	  done; \
	  echo "workspace-sync: project .grok/skills ← bootstrap first-party"; \
	fi
	@docker exec -u root agent-cage-agent bash -lc \
	  'chmod -R a+rX /workspace/$(WORKSPACE_REPO_NAME) 2>/dev/null; chown -R agent:agent /workspace/$(WORKSPACE_REPO_NAME) 2>/dev/null || true' \
	  2>/dev/null || true
	@echo "workspace-sync: OK ($(WORKSPACE_REPO))"
	@test -f "$(WORKSPACE_REPO)/README.md" && test -f "$(WORKSPACE_REPO)/Makefile"

# Project-scoped Grok MCP: cage mcp-host filesystem server (covers /workspace).
grok-mcp-preset: ensure-project
	@mkdir -p "$(WORKSPACE_REPO)/.grok"
	@cp "$(GROK_OVERLAY)/presets/project.grok.config.toml" "$(WORKSPACE_REPO)/.grok/config.toml"
	@echo "grok-mcp-preset: $(WORKSPACE_REPO)/.grok/config.toml → filesystem @ 172.30.0.10:8096"

# T-0045 full readiness: Grok image up + repo in workspace + filesystem MCP healthy
grok-ready: ensure-project
	@docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running \
	  || (echo "error: agent not running — make grok-up first"; exit 1)
	@$(MAKE) workspace-sync
	@$(MAKE) grok-smoke
	@echo "==> workspace has catalog repo"
	@docker exec -u agent agent-cage-agent bash -lc \
	  'test -f /workspace/$(WORKSPACE_REPO_NAME)/README.md && test -f /workspace/$(WORKSPACE_REPO_NAME)/Makefile && \
	   test -f /workspace/$(WORKSPACE_REPO_NAME)/.grok/config.toml && \
	   echo "workspace/$(WORKSPACE_REPO_NAME): OK"'
	@echo "==> mcp-host filesystem MCP (Streamable HTTP)"
	@docker exec -u agent agent-cage-agent bash -lc '\
	  set -e; \
	  out=$$(curl -sS -m 10 -X POST http://172.30.0.10:8096/servers/filesystem/mcp \
	    -H "Content-Type: application/json" \
	    -H "Accept: application/json, text/event-stream" \
	    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"grok-ready\",\"version\":\"0\"}}}"); \
	  echo "$$out" | grep -q secure-filesystem-server; \
	  echo "filesystem MCP initialize: OK"'
	@echo "==> filesystem MCP can see catalog tree under /workspace"
	@docker exec -u agent agent-cage-agent bash -lc '\
	  set -e; \
	  test -d /workspace/$(WORKSPACE_REPO_NAME)/harness/agent-cage; \
	  test -d /workspace/$(WORKSPACE_REPO_NAME)/bootstrap/grok-cli; \
	  ls /workspace/$(WORKSPACE_REPO_NAME) | head -8; \
	  echo "catalog paths: OK"'
	@echo "==> grok mcp list (project config in synced repo)"
	@docker exec -u agent \
	  -e HOME=/home/agent \
	  -e GROK_HOME=/home/agent/.grok \
	  -e PATH=/usr/local/bin:/home/agent/.local/bin:/usr/bin:/bin \
	  -w /workspace/$(WORKSPACE_REPO_NAME) \
	  agent-cage-agent bash -lc '\
	    set -e; \
	    grok mcp list 2>&1 | tee /tmp/grok-mcp-list.txt; \
	    grep -qi filesystem /tmp/grok-mcp-list.txt; \
	    echo "grok mcp list: filesystem present"'
	@mkdir -p "$(CATALOG_ROOT)/pipelines/smoke/cage-grok"
	@printf '| %s | cage-grok-ready | PASS | workspace+MCP+grok |\n' "$$(date -Iseconds)" \
	  >> "$(CATALOG_ROOT)/pipelines/smoke/cage-grok/results.latest.md"
	@echo "grok-ready: PASS (T-0045)"

# Verify cage proxy allows Grok Build CLI egress (not a model completion).
grok-net-smoke: ensure-project
	@docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running \
	  || (echo "error: agent not running"; exit 1)
	@echo "==> grok-net-smoke (proxy allowlist for Grok CLI)"
	@docker exec -u agent agent-cage-agent bash -lc 'set -e; \
	  fail=0; \
	  check() { \
	    url="$$1"; want="$$2"; \
	    out=$$(mktemp); \
	    code=000; \
	    for attempt in 1 2 3; do \
	      code=$$(curl -sS -m 15 -o "$$out" -w "%{http_code}" "$$url" 2>/dev/null || echo 000); \
	      body=$$(head -c 160 "$$out" 2>/dev/null | tr "\n" " "); \
	      if echo "$$body" | grep -q blocked_by_agent_cage; then \
	        echo "FAIL $$url  proxy-blocked  $$body"; fail=1; rm -f "$$out"; return; \
	      fi; \
	      if [ "$$code" != "000" ] && [ "$$code" != "502" ]; then break; fi; \
	      sleep 2; \
	    done; \
	    case " $$want " in \
	      *" $$code "*) echo "OK   $$url  http=$$code" ;; \
	      *) echo "WARN $$url  http=$$code (wanted: $$want)  $$body" ;; \
	    esac; \
	    rm -f "$$out"; \
	  }; \
	  check "https://auth.x.ai/.well-known/openid-configuration" "200"; \
	  check "https://api.x.ai/" "200 421 404"; \
	  check "https://cli-chat-proxy.grok.com/" "401 403 404 200"; \
	  check "https://storage.googleapis.com/" "200 400 404"; \
	  check "https://grok.com/" "200 301 302 403 404"; \
	  if [ "$$fail" -ne 0 ]; then \
	    echo "hint: make cage-grok-up (POLICY=coding-agent-grok); check ~/.agentcage/logs/audit.jsonl"; \
	    exit 1; \
	  fi; \
	  echo "grok-net-smoke: PASS (no proxy blocks on critical hosts)"'

# Export live container sessions to host store (before wipe / after work).
grok-sessions-export: ensure-project
	@$(MAKE) grok-state-init
	@docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running \
	  || (echo "error: agent not running"; exit 1)
	@echo "==> export container sessions → $(GROK_SESSIONS_HOST)"
	@docker cp agent-cage-agent:/home/agent/.grok/sessions/. "$(GROK_SESSIONS_HOST)/"
	@$(MAKE) fix-grok-state-perms
	@echo "grok-sessions-export: OK"

# Map host-cwd sessions for this catalog repo into cage cwd key (so old host chats appear).
grok-sessions-import-host: ensure-project
	@$(MAKE) grok-state-init
	@$(MAKE) fix-grok-state-perms
	@chmod +x "$(ROOT)/scripts/import-host-sessions-for-cage.sh"
	@HOST_CWD="$(CATALOG_ROOT)" CAGE_CWD="/workspace/$(WORKSPACE_REPO_NAME)" \
	  AGENTCAGE_DIR="$(AGENTCAGE_DIR)" \
	  "$(ROOT)/scripts/import-host-sessions-for-cage.sh"
	@# Keep dual-write; do not chown -R agent (that re-breaks host Make).
	@docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running \
	  && docker exec -u root agent-cage-agent bash -lc \
	    'chmod -R a+rwX /home/agent/.grok/sessions 2>/dev/null || true' \
	  || true
	@$(MAKE) fix-grok-state-perms
	@echo "grok-sessions-import-host: done (re-run grok-up if sessions mount was missing)"

# List sessions Grok sees for /workspace/pfy-mentat
grok-sessions: ensure-project
	@docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running \
	  || (echo "error: agent not running — make grok-up"; exit 1)
	@docker exec -u agent \
	  -e HOME=/home/agent -e GROK_HOME=/home/agent/.grok \
	  -e PATH=/usr/local/bin:/home/agent/.local/bin:/usr/bin:/bin \
	  -w /workspace/$(WORKSPACE_REPO_NAME) \
	  agent-cage-agent bash -lc 'grok sessions list'

# Resume most recent session for catalog cwd, or ID=...
ID ?=
grok-resume: ensure-project
	@docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running \
	  || (echo "error: agent not running — make grok-up"; exit 1)
	@test -f "$(WORKSPACE_REPO)/README.md" || $(MAKE) workspace-sync
	@if [ -n "$(ID)" ]; then \
	  echo "==> grok --resume $(ID)"; \
	  docker exec -it -u agent \
	    -e HOME=/home/agent -e GROK_HOME=/home/agent/.grok \
	    -e PATH=/usr/local/bin:/home/agent/.local/bin:/usr/bin:/bin \
	    -w /workspace/$(WORKSPACE_REPO_NAME) \
	    agent-cage-agent bash -lc 'exec grok --resume $(ID)'; \
	else \
	  echo "==> grok --continue (most recent for cwd)"; \
	  docker exec -it -u agent \
	    -e HOME=/home/agent -e GROK_HOME=/home/agent/.grok \
	    -e PATH=/usr/local/bin:/home/agent/.local/bin:/usr/bin:/bin \
	    -w /workspace/$(WORKSPACE_REPO_NAME) \
	    agent-cage-agent bash -lc 'exec grok --continue'; \
	fi

# Install first-party Grok skills into the *container* GROK_HOME (not host ~/.grok).
# Requires agent running + workspace-sync so /workspace/pfy-mentat has bootstrap/.
grok-skills-install: ensure-project
	@docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running \
	  || (echo "error: agent not running — make grok-up first"; exit 1)
	@echo "==> first-party skills → cage /home/agent/.grok/skills"
	@docker exec -u agent \
	  -e HOME=/home/agent -e GROK_HOME=/home/agent/.grok \
	  -e PATH=/usr/local/bin:/home/agent/.local/bin:/usr/bin:/bin \
	  -w /workspace/$(WORKSPACE_REPO_NAME) \
	  agent-cage-agent bash -lc \
	  'test -x ./bootstrap/grok-cli/install.sh || { echo "missing install.sh — run workspace-sync"; exit 1; }; \
	   ./bootstrap/grok-cli/install.sh --skills-only; \
	   python3 bootstrap/grok-cli/scripts/verify_skills.py --installed --grok-home "$$GROK_HOME" || true'
	@echo "grok-skills-install: done (restart grok session to reload slash menu if stale)"

# Idempotent “get me to a launchable Grok in cage” ladder (safe to re-run).
grok-ensure: ensure-project
	@$(MAKE) grok-overlay-install
	@docker image inspect $(GROK_IMAGE) >/dev/null 2>&1 \
	  || $(MAKE) grok-overlay-build
	@# Always re-apply compose override + up so sessions volume is attached
	@$(MAKE) grok-up
	@# Always refresh OIDC from host (stale cage auth → login prompt / ApiKey 401).
	@# Needs host ~/.grok/auth.json from a recent 'grok login' / host grok session.
	@if [ -f "$(HOME)/.grok/auth.json" ]; then \
	  $(MAKE) grok-auth-import; \
	else \
	  echo "warn: no host $(HOME)/.grok/auth.json — cage will prompt login (host: grok login)"; \
	fi
	@$(MAKE) grok-sessions-import-host
	@$(MAKE) workspace-sync
	@$(MAKE) grok-skills-install
	@$(MAKE) grok-ready
	@echo ""
	@echo "=== Launch Grok Build in cage ==="
	@echo "  make cage-grok-sessions          # list sessions for this repo"
	@echo "  make cage-grok-resume            # continue most recent"
	@echo "  make cage-grok-resume ID=uuid    # resume specific"
	@echo "  make cage-grok-run PROMPT='…'    # new session with prompt"
	@echo "  make cage-grok-shell             # bash then: grok / grok -c"
	@echo "  make cage-grok-skills-install    # re-copy first-party skills into cage GROK_HOME"
	@echo "Sessions host store: $(GROK_SESSIONS_HOST)"
	@echo "MCP: project filesystem → mcp-host /workspace (includes pfy-mentat/)"

# Interactive shell in catalog tree (Grok binary on PATH from image).
grok-shell: ensure-project
	@docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running \
	  || (echo "error: agent not running — make grok-ensure first"; exit 1)
	@test -f "$(WORKSPACE_REPO)/README.md" || $(MAKE) workspace-sync
	@echo "==> shell as agent @ /workspace/$(WORKSPACE_REPO_NAME)  (exit to leave)"
	@docker exec -it -u agent \
	  -e HOME=/home/agent \
	  -e GROK_HOME=/home/agent/.grok \
	  -e PATH=/usr/local/bin:/home/agent/.local/bin:/usr/bin:/bin \
	  -w /workspace/$(WORKSPACE_REPO_NAME) \
	  agent-cage-agent bash -l

# Interactive Grok session in catalog tree.
# Prompt must stay ONE argv for grok (spaces break if unquoted).
#
#   make cage-grok-run PROMPT='Read docs/ops/foo.md and implement T-0047'
#   make cage-grok-run FLAGS='--always-approve' PROMPT='summarize README'
#   make cage-grok-run                          # bare TUI, no initial prompt
#   make cage-grok-run ARGS='…'                 # back-compat alias for PROMPT
#
# Avoid: ARGS with bare paths as separate shell words (old bug).
PROMPT ?=
FLAGS ?=
ARGS ?=
grok-run: ensure-project
	@docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running \
	  || (echo "error: agent not running — make grok-ensure first"; exit 1)
	@test -f "$(WORKSPACE_REPO)/README.md" || $(MAKE) workspace-sync
	@test -f "$(WORKSPACE_REPO)/.grok/config.toml" || $(MAKE) grok-mcp-preset
	@prompt='$(if $(strip $(PROMPT)),$(PROMPT),$(ARGS))'; \
	  echo "==> grok $(FLAGS) [prompt chars: $$(printf '%s' \"$$prompt\" | wc -c)] @ /workspace/$(WORKSPACE_REPO_NAME)"; \
	  docker exec -it -u agent \
	    -e HOME=/home/agent \
	    -e GROK_HOME=/home/agent/.grok \
	    -e PATH=/usr/local/bin:/home/agent/.local/bin:/usr/bin:/bin \
	    -e GROK_PROMPT="$$prompt" \
	    -w /workspace/$(WORKSPACE_REPO_NAME) \
	    agent-cage-agent bash -lc \
	    'if [ -n "$$GROK_PROMPT" ]; then exec grok $(FLAGS) "$$GROK_PROMPT"; else exec grok $(FLAGS); fi'

# --- Local Ollama (host) + LiteLLM in-cage smoke -----------------------------

# agentcage CLI ignores extra compose files; use docker compose explicitly.
COMPOSE_LOCAL_OLLAMA = docker compose -p agent-cage \
	-f $(COMPOSE_DIR)/docker-compose.yaml \
	-f $(COMPOSE_DIR)/docker-compose.mcp.yaml \
	$(if $(wildcard $(COMPOSE_DIR)/docker-compose.override.yaml),-f $(COMPOSE_DIR)/docker-compose.override.yaml,) \
	-f $(COMPOSE_DIR)/docker-compose.local-ollama.yaml

local-ollama-overlay-install: ensure-project
	@test -f "$(LOCAL_OLLAMA_OVERLAY)/coding-agent-local.yaml"
	@test -f "$(LOCAL_OLLAMA_OVERLAY)/docker-compose.local-ollama.yaml"
	@cp "$(LOCAL_OLLAMA_OVERLAY)/coding-agent-local.yaml" \
	  "$(AGENTCAGE_DIR)/policies/coding-agent-local.yaml"
	@cp "$(LOCAL_OLLAMA_OVERLAY)/docker-compose.local-ollama.yaml" \
	  "$(COMPOSE_DIR)/docker-compose.local-ollama.yaml"
	@echo "Installed local-ollama overlay:"
	@echo "  policies/coding-agent-local.yaml"
	@echo "  docker/docker-compose.local-ollama.yaml"
	@echo "Next: $(LITELLM_EXAMPLE)/host-ollama-gateway.sh start"
	@echo "      make local-ollama-up && make smoke-litellm-ollama"

local-ollama-up: ensure-project
	@$(MODEL_LOCK) $(MAKE) local-ollama-up-body

local-ollama-up-body: ensure-project
	@test -f "$(COMPOSE_DIR)/docker-compose.local-ollama.yaml" \
	  || (echo "error: run make local-ollama-overlay-install first"; exit 1)
	@test -f "$(AGENTCAGE_DIR)/policies/coding-agent-local.yaml" \
	  || (echo "error: missing coding-agent-local policy — make local-ollama-overlay-install"; exit 1)
	@# Host gateway (user-space) so Docker can reach 127.0.0.1-bound Ollama
	@$(LITELLM_EXAMPLE)/host-ollama-gateway.sh start
	@echo "==> docker compose up with local-ollama fragment (POLICY=coding-agent-local)"
	@if [ -f "$(AGENTCAGE_DIR)/.env" ]; then set -a; . "$(AGENTCAGE_DIR)/.env"; set +a; fi; \
	cd "$(COMPOSE_DIR)" && \
	POLICY=coding-agent-local \
	LITELLM_SMOKE_MODEL=$(LITELLM_SMOKE_MODEL) \
	DEPLOY_PROFILE=$${DEPLOY_PROFILE:-local-only} \
	$(COMPOSE_LOCAL_OLLAMA) up -d
	@sleep 3
	@docker inspect agent-cage-agent --format 'image={{.Config.Image}} status={{.State.Status}}' 2>/dev/null \
	  || (echo "error: agent-cage-agent not running"; exit 1)
	@echo "Policy should allow host.docker.internal. Next: make smoke-litellm-ollama"

# Host IP as seen from agent-cage custom bridge (often 172.30.0.1).
# Docker "host-gateway" maps to 172.17.0.1 (docker0) which is NOT reachable from 172.30/24.
define CAGE_HOST_IP_CMD
docker exec agent-cage-agent python3 -c "import re,subprocess,ipaddress;\
 o=subprocess.check_output(['ip','-4','-o','addr','show','scope','global'],text=True);\
 m=re.search(r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)',o);\
 assert m, 'no eth inet';\
 net=ipaddress.ip_interface(m.group(1)+'/'+m.group(2)).network;\
 print(net.network_address+1)"
endef

smoke-litellm-ollama: ensure-project
	@$(MODEL_LOCK) $(MAKE) smoke-litellm-ollama-body

smoke-litellm-ollama-body: ensure-project
	@test -f "$(LITELLM_EXAMPLE)/run-in-cage.sh" \
	  || (echo "error: missing $(LITELLM_EXAMPLE)/run-in-cage.sh"; exit 1)
	@# Always (re)apply local-ollama compose + policy (whitelist host.docker.internal).
	@$(MAKE) local-ollama-overlay-install
	@$(MAKE) local-ollama-up
	@# Resolve host on *cage* bridge (not docker0 host-gateway).
	@ip=$$($(CAGE_HOST_IP_CMD)); \
	  echo "cage→host Ollama via $$ip:11435 (not host-gateway/172.17.0.1)"; \
	  echo "  (skip /etc/hosts rewrite — bind-mount often EBUSY; URL uses IP)"; \
	  if ! docker exec -u agent agent-cage-agent bash -lc \
	      "curl -sS -m 5 --noproxy '*' -o /dev/null -w '%{http_code}' http://$$ip:11435/api/tags" \
	      | grep -qE '200|301|302'; then \
	    echo "error: agent cannot reach http://$$ip:11435/api/tags"; \
	    echo "  host: ./examples/litellm-ollama/host-ollama-gateway.sh status"; \
	    echo "  host: curl -sS http://127.0.0.1:11435/api/tags | head"; \
	    exit 1; \
	  fi; \
	  docker exec -u root agent-cage-agent bash -lc \
	    'mkdir -p /workspace/examples/litellm-ollama && chown agent:agent /workspace/examples /workspace/examples/litellm-ollama'; \
	  docker cp "$(LITELLM_EXAMPLE)/." agent-cage-agent:/workspace/examples/litellm-ollama/; \
	  docker exec -u root agent-cage-agent bash -lc \
	    'chown -R agent:agent /workspace/examples/litellm-ollama && chmod +x /workspace/examples/litellm-ollama/*.sh /workspace/examples/litellm-ollama/smoke_completion.py'; \
	  echo "==> in-cage LiteLLM → Ollama smoke (model=$(LITELLM_SMOKE_MODEL) host=$$ip)"; \
	  docker exec -u agent \
	    -e HOME=/home/agent \
	    -e PATH=/home/agent/.local/bin:/usr/local/bin:/usr/bin:/bin \
	    -e OPENAI_BASE_URL=http://$$ip:11435/v1 \
	    -e OLLAMA_HOST=http://$$ip:11435 \
	    -e LITELLM_SMOKE_MODEL=$(LITELLM_SMOKE_MODEL) \
	    -e DEPLOY_PROFILE=local-only \
	    -e no_proxy=localhost,127.0.0.1,$$ip,host.docker.internal,172.30.0.0/24 \
	    -e NO_PROXY=localhost,127.0.0.1,$$ip,host.docker.internal,172.30.0.0/24 \
	    agent-cage-agent bash -lc \
	    'cd /workspace/examples/litellm-ollama && bash ./run-in-cage.sh'
	@echo "smoke-litellm-ollama: PASS"
	@mkdir -p "$(CATALOG_ROOT)/pipelines/smoke/litellm-ollama"
	@printf '| %s | PASS | %s | in-cage LiteLLM→Ollama via cage-bridge host IP:11435 |\n' \
	  "$$(date -Iseconds)" "$(LITELLM_SMOKE_MODEL)" \
	  >> "$(CATALOG_ROOT)/pipelines/smoke/litellm-ollama/results.latest.md"

# --- codebase-memory-mcp + repowise in-cage smokes (T-0021 / T-0013) --------

smoke-codebase-memory: ensure-project
	@test -f "$(CM_EXAMPLE)/run-in-cage.sh"
	@docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running \
	  || (echo "error: agent not running — make up-mcp or local-ollama-up first"; exit 1)
	@docker exec -u root agent-cage-agent bash -lc \
	  'mkdir -p /workspace/examples/codebase-memory-mcp /home/agent/.local/bin && chown -R agent:agent /workspace/examples /home/agent/.local 2>/dev/null || true'
	@# Prefer host binary (~270MB) to avoid re-download; fallback install inside cage
	@if [ -x "$(HOME)/.local/bin/codebase-memory-mcp" ]; then \
	  docker cp "$(HOME)/.local/bin/codebase-memory-mcp" agent-cage-agent:/home/agent/.local/bin/codebase-memory-mcp; \
	  docker exec -u root agent-cage-agent bash -lc 'chown agent:agent /home/agent/.local/bin/codebase-memory-mcp && chmod +x /home/agent/.local/bin/codebase-memory-mcp'; \
	fi
	@docker cp "$(CM_EXAMPLE)/." agent-cage-agent:/workspace/examples/codebase-memory-mcp/
	@docker exec -u root agent-cage-agent bash -lc \
	  'chown -R agent:agent /workspace/examples/codebase-memory-mcp && chmod +x /workspace/examples/codebase-memory-mcp/run-in-cage.sh'
	@echo "==> in-cage codebase-memory-mcp smoke"
	@docker exec -u agent \
	  -e HOME=/home/agent \
	  -e PATH=/home/agent/.local/bin:/usr/local/bin:/usr/bin:/bin \
	  agent-cage-agent bash -lc \
	  'cd /workspace/examples/codebase-memory-mcp && bash ./run-in-cage.sh'
	@echo "smoke-codebase-memory: PASS"
	@mkdir -p "$(CATALOG_ROOT)/pipelines/smoke/codebase-memory-mcp"
	@printf '| %s | PASS | codebase-memory-mcp | in-cage index+search fixture |\n' \
	  "$$(date -Iseconds)" >> "$(CATALOG_ROOT)/pipelines/smoke/codebase-memory-mcp/results.latest.md"

smoke-repowise: ensure-project
	@test -f "$(RW_EXAMPLE)/run-in-cage.sh"
	@docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running \
	  || (echo "error: agent not running — make up-mcp or local-ollama-up first"; exit 1)
	@docker exec -u root agent-cage-agent bash -lc \
	  'mkdir -p /workspace/examples/repowise && chown -R agent:agent /workspace/examples'
	@docker cp "$(RW_EXAMPLE)/." agent-cage-agent:/workspace/examples/repowise/
	@docker exec -u root agent-cage-agent bash -lc \
	  'chown -R agent:agent /workspace/examples/repowise && chmod +x /workspace/examples/repowise/run-in-cage.sh'
	@echo "==> in-cage repowise smoke (pip $(REPOWISE_PIP_SPEC))"
	@docker exec -u agent \
	  -e HOME=/home/agent \
	  -e PATH=/home/agent/.local/bin:/usr/local/bin:/usr/bin:/bin \
	  -e REPOWISE_PIP_SPEC=$(REPOWISE_PIP_SPEC) \
	  agent-cage-agent bash -lc \
	  'cd /workspace/examples/repowise && bash ./run-in-cage.sh'
	@echo "smoke-repowise: PASS"
	@mkdir -p "$(CATALOG_ROOT)/pipelines/smoke/repowise"
	@printf '| %s | PASS | %s | in-cage health (zero LLM) |\n' \
	  "$$(date -Iseconds)" "$(REPOWISE_PIP_SPEC)" \
	  >> "$(CATALOG_ROOT)/pipelines/smoke/repowise/results.latest.md"

smoke-context-tools: smoke-codebase-memory smoke-repowise
	@test -f "$(CATALOG_ROOT)/pipelines/smoke/context-tools-compare.md"
	@echo "smoke-context-tools: PASS (see pipelines/smoke/context-tools-compare.md)"

# --- write-guard MCP (T-0031) ------------------------------------------------

WG_PKG := $(CATALOG_ROOT)/harness/write-guard-mcp
WG_EXAMPLE := $(CATALOG_ROOT)/examples/write-guard-mcp

write-guard-overlay-install: ensure-project
	@mkdir -p "$(AGENTCAGE_DIR)/overlays-write-guard"
	@cp "$(ROOT)/overlays/write-guard/mcp-servers.write-guard.yaml" \
	  "$(AGENTCAGE_DIR)/overlays-write-guard/mcp-servers.write-guard.yaml"
	@cp "$(ROOT)/overlays/write-guard/README.md" \
	  "$(AGENTCAGE_DIR)/overlays-write-guard/README.md"
	@echo "Installed write-guard overlay docs → $(AGENTCAGE_DIR)/overlays-write-guard/"
	@echo "  Enable MCP entry after package is on mcp-host PATH (see overlay README)."

# --- Eval harness (OQ-0002 option 5 / T-0003 MVP + T-0041 v0.2) --------------

EVAL_EXAMPLE := $(CATALOG_ROOT)/examples/eval-harness
EVAL_TASK ?= 001-is-palindrome
# Defaults overridden by eval-select-models / eval-auto when fit selection runs.
EVAL_MODEL ?= qwen2.5:14b
EVAL_MODELS ?= qwen2.5:14b,codestral:22b,deepseek-coder:6.7b-instruct
EVAL_GATE_MODEL ?= $(EVAL_MODEL)
EVAL_MODE ?= single
# Auto-pull gate if it fits but is not local yet (host needs `ollama` on PATH).
EVAL_PULL_GATE ?= 1

# Shared: copy harness into cage and run run-in-cage.sh with EVAL_MODE.
# Uses cage-bridge host IP (same as smoke-litellm-ollama), not host-gateway.
define eval-in-cage
	@test -f "$(EVAL_EXAMPLE)/run-in-cage.sh"
	@$(LITELLM_EXAMPLE)/host-ollama-gateway.sh start
	@docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running \
	  || (echo "error: agent not running — make local-ollama-up or smoke-litellm-ollama first"; exit 1)
	@docker exec -u root agent-cage-agent bash -lc \
	  'mkdir -p /workspace/examples/eval-harness && chown -R agent:agent /workspace/examples'
	@docker cp "$(EVAL_EXAMPLE)/." agent-cage-agent:/workspace/examples/eval-harness/
	@docker exec -u root agent-cage-agent bash -lc \
	  'chown -R agent:agent /workspace/examples/eval-harness && chmod +x /workspace/examples/eval-harness/*.sh /workspace/examples/eval-harness/*.py'
	@ip=$$($(CAGE_HOST_IP_CMD)); \
	  echo "==> eval $(1) task=$(EVAL_TASK) model=$(EVAL_MODEL) models=$(EVAL_MODELS) host=$$ip"; \
	  docker exec -u agent \
	    -e HOME=/home/agent \
	    -e PATH=/home/agent/.local/bin:/usr/local/bin:/usr/bin:/bin \
	    -e OPENAI_BASE_URL=http://$$ip:11435/v1 \
	    -e OLLAMA_HOST=http://$$ip:11435 \
	    -e EVAL_MODEL=$(EVAL_MODEL) \
	    -e EVAL_MODELS=$(EVAL_MODELS) \
	    -e EVAL_GATE_MODEL=$(EVAL_GATE_MODEL) \
	    -e EVAL_MODE=$(1) \
	    -e LITELLM_SMOKE_MODEL=$(LITELLM_SMOKE_MODEL) \
	    -e EVAL_TASK=$(EVAL_TASK) \
	    -e EVAL_MATRIX_MD=/tmp/eval-matrix-out.md \
	    -e EVAL_RESULT_JSON=/tmp/eval-result.json \
	    -e no_proxy=localhost,127.0.0.1,$$ip,host.docker.internal,172.30.0.0/24 \
	    -e NO_PROXY=localhost,127.0.0.1,$$ip,host.docker.internal,172.30.0.0/24 \
	    agent-cage-agent bash -lc \
	    'cd /workspace/examples/eval-harness && bash ./run-in-cage.sh'
	@mkdir -p "$(CATALOG_ROOT)/pipelines/eval"
endef

eval-tier0: smoke-litellm-ollama
	@echo "eval-tier0: PASS (smoke-litellm-ollama)"

eval-tier1: ensure-project
	@$(MODEL_LOCK) $(MAKE) eval-tier1-body

eval-tier1-body: ensure-project
	$(call eval-in-cage,single)
	@echo "eval-tier1: PASS"
	@printf '| %s | 1 | PASS | %s | model=%s single task |\n' \
	  "$$(date -Iseconds)" "$(EVAL_TASK)" "$(EVAL_MODEL)" \
	  >> "$(CATALOG_ROOT)/pipelines/eval/results.latest.md"

# v0.2: all implement tasks with gate model
eval-suite: ensure-project
	@$(MODEL_LOCK) $(MAKE) eval-suite-body

eval-suite-body: ensure-project
	$(call eval-in-cage,suite)
	@echo "eval-suite: PASS"
	@printf '| %s | suite | PASS | all tasks | gate=%s |\n' \
	  "$$(date -Iseconds)" "$(EVAL_GATE_MODEL)" \
	  >> "$(CATALOG_ROOT)/pipelines/eval/results.latest.md"
	@docker exec -u agent agent-cage-agent bash -lc \
	  'test -f /tmp/eval-matrix-out.md && cat /tmp/eval-matrix-out.md' \
	  >> "$(CATALOG_ROOT)/pipelines/eval/results.latest.md" 2>/dev/null || true

# v0.2: tasks × models matrix (gate model must pass all tasks)
eval-matrix: ensure-project
	@$(MODEL_LOCK) $(MAKE) eval-matrix-body

eval-matrix-body: ensure-project
	$(call eval-in-cage,matrix)
	@echo "eval-matrix: PASS (gate $(EVAL_GATE_MODEL))"
	@printf '| %s | matrix | PASS | tasks×models | gate=%s models=%s |\n' \
	  "$$(date -Iseconds)" "$(EVAL_GATE_MODEL)" "$(EVAL_MODELS)" \
	  >> "$(CATALOG_ROOT)/pipelines/eval/results.latest.md"
	@docker exec -u agent agent-cage-agent bash -lc \
	  'test -f /tmp/eval-matrix-out.md && cat /tmp/eval-matrix-out.md' \
	  >> "$(CATALOG_ROOT)/pipelines/eval/results.latest.md" 2>/dev/null || true

eval-mvp: eval-tier0 eval-tier1
	@echo "eval-mvp: PASS (OQ-0002 option 5)"

# Full v0.2 ladder: connectivity + multi-task suite (gate model)
eval-v02: eval-tier0 eval-suite
	@echo "eval-v02: PASS (suite + tier0)"

smoke-write-guard: ensure-project
	@test -f "$(WG_EXAMPLE)/run-in-cage.sh"
	@test -d "$(WG_PKG)/src/write_guard"
	@docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running \
	  || (echo "error: agent not running — make up-mcp first"; exit 1)
	@docker exec -u root agent-cage-agent bash -lc \
	  'mkdir -p /workspace/examples/write-guard-mcp/pkg && chown -R agent:agent /workspace/examples'
	@# stage package + example driver
	@docker cp "$(WG_PKG)/." agent-cage-agent:/workspace/examples/write-guard-mcp/pkg/
	@docker cp "$(WG_EXAMPLE)/run-in-cage.sh" agent-cage-agent:/workspace/examples/write-guard-mcp/run-in-cage.sh
	@docker cp "$(WG_EXAMPLE)/README.md" agent-cage-agent:/workspace/examples/write-guard-mcp/README.md
	@docker exec -u root agent-cage-agent bash -lc \
	  'chown -R agent:agent /workspace/examples/write-guard-mcp && chmod +x /workspace/examples/write-guard-mcp/run-in-cage.sh'
	@echo "==> in-cage write-guard smoke"
	@docker exec -u agent \
	  -e HOME=/home/agent \
	  -e PATH=/home/agent/.local/bin:/usr/local/bin:/usr/bin:/bin \
	  -e WRITE_GUARD_SRC=/workspace/examples/write-guard-mcp/pkg \
	  agent-cage-agent bash -lc \
	  'cd /workspace/examples/write-guard-mcp && bash ./run-in-cage.sh'
	@echo "smoke-write-guard: PASS"
	@mkdir -p "$(CATALOG_ROOT)/pipelines/smoke/write-guard-mcp"
	@printf '| %s | PASS | write-guard-mcp 0.1.0 | selftest+audit+enforce in cage |\n' \
	  "$$(date -Iseconds)" >> "$(CATALOG_ROOT)/pipelines/smoke/write-guard-mcp/results.latest.md"
