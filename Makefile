# pfy-mentat — top-level operator entrypoints
# Prefer these from the repo root (avoids "no rule to make target 'test'").
#
# Agent cage is the integration lab. Prefer testing catalog tool installs
# inside the cage (versioned images), not only on the host.

SHELL := /bin/bash
.DEFAULT_GOAL := help
HARNESS := harness/agent-cage
LITELLM_EXAMPLE := examples/litellm-ollama

.PHONY: help help-platform cage-doctor cage-setup cage-init cage-up cage-up-mcp cage-down \
	cage-shell cage-status cage-test cage-logs cage-smoke-host catalog-json \
	env-init env-check cage-grok-install cage-grok-build cage-grok-up \
	cage-grok-smoke cage-grok-ready cage-grok-uninstall cage-grok-auth-import \
	cage-workspace-sync cage-grok-mcp-preset \
	local-ollama-overlay-install local-ollama-up smoke-litellm-ollama \
	smoke-codebase-memory smoke-repowise smoke-context-tools \
	smoke-write-guard smoke-grok-skills smoke-opencode-ollama smoke-voice-stt smoke-voice-remote \
	smoke-voice-agent smoke-voice-orchestrate smoke-tools-model \
	voice-stt-install voice-listen voice-stt-probe voice-remote voice-remote-serve \
	voice-agent-run voice-orchestrate \
	worker-stage worker-env monitor-brief \
	eval-tier0 eval-tier1 eval-mvp eval-suite eval-matrix eval-v02 eval-structural \
	eval-select-models eval-select-tools-model eval-auto \
	cage-grok cage-grok-shell cage-grok-run cage-grok-sessions cage-grok-resume \
	cage-grok-sessions-import-host cage-grok-net-smoke cage-grok-skills-install \
	cage-code-sync cage-code-status cage-code-from-cage cage-code-to-cage

help:
	@echo "pfy-mentat"
	@echo ""
	@echo "Product:"
	@echo "  ./pfy setup                 attach this stack to a project"
	@echo "  ./pfy stage                 local env check"
	@echo "  ./pfy ship                  verify; push if PRODUCT_REMOTE is set"
	@echo "  make project-onboard DIR=path"
	@echo "  make env-stage"
	@echo "  make product-ship"
	@echo ""
	@echo "Also: ./pfy status · ./pfy start"
	@echo "Platform (cage, smoke, eval): make help-platform"

help-platform:
	@echo "pfy-mentat — platform"
	@echo ""
	@echo "Environment (secrets never in git):"
	@echo "  make env-init         Create .env from bootstrap/env/env.example if missing (idempotent)"
	@echo "  make env-check        Validate required vars for DEPLOY_PROFILE"
	@echo ""
	@echo "Agent cage (integration lab) — from repo root:"
	@echo "  make cage-doctor      Host/docker checks"
	@echo "  make cage-setup       Clone pin + install agentcage CLI (idempotent)"
	@echo "  make cage-init        agentcage init → \$$HOME/.agentcage (skips if present)"
	@echo "  make cage-up          Start sandbox"
	@echo "  make cage-up-mcp      Start sandbox + MCP  (do this before cage-test)"
	@echo "  make cage-status      Container health"
	@echo "  make cage-shell       Shell into agent container (generic)"
	@echo "  make cage-test        Policy tests (services must already be up)"
	@echo "  make cage-down        Stop sandbox"
	@echo "  make cage-smoke-host  Host-only smoke (no containers)"
	@echo ""
	@echo "Grok Build in cage (primary operator path — T-0045):"
	@echo "  make cage-grok              # ensure up + workspace + MCP ready, print how to launch"
	@echo "  make cage-grok-shell        # interactive bash at /workspace/pfy-mentat"
	@echo "  make cage-grok-run PROMPT='…'   # new session; prompt is one string"
	@echo "  make cage-grok-sessions         # list Grok sessions for cage repo cwd"
	@echo "  make cage-grok-resume           # continue most recent (or ID=uuid)"
	@echo "  make cage-grok-sessions-import-host  # map host project sessions → cage"
	@echo "  First-time: cage-grok-install → auth-import → build → cage-grok"
	@echo "  Daily:      make cage-grok   then resume | run | shell"
	@echo "  make cage-workspace-sync    # rsync catalog → cage workspace (content only)"
	@echo "  make cage-code-status       # host vs cage HEADs (privileged host)"
	@echo "  make cage-code-from-cage    # import agent commits → host git"
	@echo "  make cage-code-to-cage      # rsync host → cage + align cage git"
	@echo "  make cage-code-sync         # from-cage then to-cage (add PUSH=1 to push origin)"
	@echo "  Auth: host 'grok login' then make cage-grok-auth-import"
	@echo "  Sessions persist: ~/.agentcage/grok-state/sessions (not host ~/.grok alone)"
	@echo "  make cage-grok-net-smoke    # proxy must allow auth.x.ai + cli-chat-proxy"
	@echo "  make cage-grok-skills-install  # first-party skills → cage GROK_HOME"
	@echo "  TUI crash left mouse junk?  host shell:  reset"
	@echo ""
	@echo "LiteLLM + Ollama (in-cage smoke, local-only):"
	@echo "  make local-ollama-overlay-install"
	@echo "  make local-ollama-up"
	@echo "  make smoke-litellm-ollama   # exit 0 required; runs inside agent-cage only"
	@echo "  make smoke-codebase-memory / smoke-repowise / smoke-context-tools"
	@echo "  make smoke-write-guard      # T-0031 write-guard MCP policy smoke"
	@echo "  make smoke-grok-skills      # first-party skill structure (manifest + SKILL.md)"
	@echo "  make smoke-grok-skills INSTALLED=1  # also check ~/.grok/skills"
	@echo "  make smoke-opencode-ollama  # T-0080 host: OpenCode adapter + Ollama worker (no cage)"
	@echo "  make smoke-voice-stt        # T-0091 p1: wiring only (mock/text; no mic)"
	@echo "  make voice-stt-install      # T-0091: .venv + faster-whisper (host, once; PEP 668)"
	@echo "  make voice-listen           # T-0091: desk mic → STT → handoff"
	@echo "  make voice-remote           # T-0091 p4a: HTTP backend :8787 (plain HTTP only)"
	@echo "  make voice-remote-serve     # T-0091: tailscale serve HTTPS :443 → :8787"
	@echo "  make voice-agent-run        # T-0096: orchestrate (high-first) or single tier"
	@echo "  make voice-orchestrate      # T-0096: dual-tier high↔low on last prompt"
	@echo "  make smoke-voice-remote     # T-0091 p4a: localhost API smoke (no phone)"
	@echo "  make smoke-voice-agent      # local opencode path smoke"
	@echo "  make smoke-voice-orchestrate # T-0096 dual-tier mock smoke (no cloud)"
	@echo "  make worker-stage           # T-0085: smoke worker + write monitor brief / worker.env"
	@echo "  make eval-structural           # design/coding gates, NO LLM (always run)"
	@echo "  make eval-golden               # golden-task cards validate (no LLM)"
	@echo "  make eval-unified-agents       # score claude-unified-agents pack"
	@echo "  make eval-integration-change  # Exo-inspired ingest self-mod gates"
	@echo "  make eval-deploy-ready         # G1: structural+golden+soft smokes (HD #33)"
	@echo "  make eval-select-models        # pick gate/matrix models that FIT RAM/disk (may pull)"
	@echo "  make eval-select-tools-model   # T-0093: probe tools-capable Ollama tag + tool-split"
	@echo "  make smoke-tools-model         # T-0093 smoke (Ollama optional soft-skip)"
	@echo "  make eval-auto                 # select-models + pull-gate + eval-v02"
	@echo "  make eval-tier0|eval-tier1|eval-mvp  # OQ-0002 opt5 scored eval"
	@echo "  make eval-suite|eval-matrix|eval-v02 # v0.2 multi-task / multi-model (needs Ollama)"
	@echo ""
	@echo "Or:  cd harness/agent-cage && make help"
	@echo ""
	@echo "Catalog:"
	@echo "  make catalog-json     Validate data/tools.json parses"
	@echo "  # Self-hosted lab (nimo): docs/ops/self-hosted-runner-nimo.md"
	@echo "  make catalog-check    S-tier names in TOOLS.md (GAP-03)"
	@echo "  make catalog-dashboard  scoring dashboard MD (GAP-04)"
	@echo "  make smoke-product-levers  dual-sided onboard (GAP-09)"
	@echo "  make model-pool-inventory  soft 250GB probe (GAP-16)"
	@echo "  make smoke-contract-lint   examples smoke contract (GAP-05)"
	@echo ""
	@echo "Product surface: make help"
	@echo ""
	@echo "Profiles: local-only | balanced | max-performance  (DEPLOY_PROFILE)"
	@echo "  see config/profiles/ and docs/ops/deployment-profiles.md"

cage-doctor:
	@$(MAKE) -C $(HARNESS) doctor

cage-setup:
	@$(MAKE) -C $(HARNESS) setup

cage-init:
	@$(MAKE) -C $(HARNESS) init

cage-up:
	@$(MAKE) -C $(HARNESS) up

cage-up-mcp:
	@$(MAKE) -C $(HARNESS) up-mcp

cage-down:
	@$(MAKE) -C $(HARNESS) down

cage-shell:
	@$(MAKE) -C $(HARNESS) shell

cage-status:
	@$(MAKE) -C $(HARNESS) status

cage-test:
	@$(MAKE) -C $(HARNESS) test

cage-logs:
	@$(MAKE) -C $(HARNESS) logs

cage-smoke-host:
	@$(MAKE) -C $(HARNESS) smoke-host

catalog-json:
	@python3 -c "import json; json.load(open('data/tools.json')); print('data/tools.json: OK')"

cage-grok-install:
	@$(MAKE) -C $(HARNESS) grok-overlay-install

cage-grok-auth-import:
	@$(MAKE) -C $(HARNESS) grok-auth-import

cage-grok-build:
	@$(MAKE) -C $(HARNESS) grok-overlay-build

cage-grok-up:
	@$(MAKE) -C $(HARNESS) grok-up

cage-grok-smoke:
	@$(MAKE) -C $(HARNESS) grok-smoke

cage-workspace-sync:
	@$(MAKE) -C $(HARNESS) workspace-sync

# Host-privileged bidirectional code bridge (see harness/agent-cage/scripts/cage-code-sync.sh)
# PUSH=1  → also git push origin after import
# FORCE=1 → allow dirty / overwrite checks
# SYNC_ARGS extra flags e.g. SYNC_ARGS=--dry-run
cage-code-status:
	@chmod +x harness/agent-cage/scripts/cage-code-sync.sh
	@./harness/agent-cage/scripts/cage-code-sync.sh status $(SYNC_ARGS)

cage-code-from-cage:
	@chmod +x harness/agent-cage/scripts/cage-code-sync.sh
	@./harness/agent-cage/scripts/cage-code-sync.sh from-cage $(if $(filter 1,$(FORCE)),--force,) $(SYNC_ARGS)

cage-code-to-cage:
	@chmod +x harness/agent-cage/scripts/cage-code-sync.sh
	@./harness/agent-cage/scripts/cage-code-sync.sh to-cage $(if $(filter 1,$(FORCE)),--force,) $(SYNC_ARGS)

cage-code-sync:
	@chmod +x harness/agent-cage/scripts/cage-code-sync.sh
	@./harness/agent-cage/scripts/cage-code-sync.sh sync \
	  $(if $(filter 1,$(PUSH)),--push,) \
	  $(if $(filter 1,$(FORCE)),--force,) \
	  $(SYNC_ARGS)

cage-grok-mcp-preset:
	@$(MAKE) -C $(HARNESS) grok-mcp-preset

cage-grok-ready:
	@$(MAKE) -C $(HARNESS) grok-ready

cage-grok:
	@$(MAKE) -C $(HARNESS) grok-ensure

cage-grok-shell:
	@$(MAKE) -C $(HARNESS) grok-shell

cage-grok-run:
	@$(MAKE) -C $(HARNESS) grok-run PROMPT='$(PROMPT)' FLAGS='$(FLAGS)' ARGS='$(ARGS)'

cage-grok-sessions:
	@$(MAKE) -C $(HARNESS) grok-sessions

cage-grok-resume:
	@$(MAKE) -C $(HARNESS) grok-resume ID='$(ID)'

cage-grok-sessions-import-host:
	@$(MAKE) -C $(HARNESS) grok-sessions-import-host

cage-grok-net-smoke:
	@$(MAKE) -C $(HARNESS) grok-net-smoke

cage-grok-skills-install:
	@$(MAKE) -C $(HARNESS) grok-skills-install

cage-grok-uninstall:
	@$(MAKE) -C $(HARNESS) grok-overlay-uninstall

local-ollama-overlay-install:
	@$(MAKE) -C $(HARNESS) local-ollama-overlay-install

local-ollama-up:
	@$(MAKE) -C $(HARNESS) local-ollama-up

smoke-litellm-ollama:
	@$(MAKE) -C $(HARNESS) smoke-litellm-ollama

smoke-codebase-memory:
	@$(MAKE) -C $(HARNESS) smoke-codebase-memory

smoke-repowise:
	@$(MAKE) -C $(HARNESS) smoke-repowise

smoke-context-tools:
	@$(MAKE) -C $(HARNESS) smoke-context-tools

smoke-write-guard:
	@$(MAKE) -C $(HARNESS) smoke-write-guard

# First-party Grok skills: manifest ↔ SKILL.md structure (no LLM). See docs/ops/skill-verification.md
# INSTALLED=1 also checks $GROK_HOME/skills (default ~/.grok/skills)
smoke-grok-skills:
	@python3 bootstrap/grok-cli/scripts/verify_skills.py $(if $(filter 1,$(INSTALLED)),--installed,)

# T-0080: host OpenCode + Ollama worker path (skills SoT + completion; opencode CLI optional)
smoke-opencode-ollama:
	@chmod +x examples/opencode-ollama/smoke.sh
	@LOCAL_CODER_MODEL=$${LOCAL_CODER_MODEL:-deepseek-coder:6.7b} \
	  LITELLM_SMOKE_MODEL=$${LITELLM_SMOKE_MODEL:-deepseek-coder:latest} \
	  OPENAI_BASE_URL=$${OPENAI_BASE_URL:-http://127.0.0.1:11434/v1} \
	  ./examples/opencode-ollama/smoke.sh

# T-0091 phase 1: voice STT edge → text prompt for Grok/OpenCode (mock/text; no mic)
smoke-voice-stt:
	@chmod +x examples/voice-stt-edge/smoke.sh examples/voice-stt-edge/stt_edge.py \
	  examples/voice-stt-edge/listen.sh examples/voice-stt-edge/install-local-stt.sh
	@./examples/voice-stt-edge/smoke.sh

# Host once: project venv + faster-whisper (PEP 668 / Debian safe — not system pip)
voice-stt-install:
	@chmod +x examples/voice-stt-edge/install-local-stt.sh examples/voice-stt-edge/python.sh
	@./examples/voice-stt-edge/install-local-stt.sh

# Host: probe whether real STT is ready (exit 0 ready, 2 not); uses .venv if present
voice-stt-probe:
	@chmod +x examples/voice-stt-edge/python.sh
	@examples/voice-stt-edge/python.sh examples/voice-stt-edge/stt_edge.py --probe

# Host: real mic → STT → artifacts (VOICE_LISTEN_SECONDS=5 VOICE_TARGET=monitor VOICE_HANDOFF=1)
voice-listen:
	@chmod +x examples/voice-stt-edge/listen.sh examples/voice-stt-edge/stt_edge.py \
	  examples/voice-stt-edge/python.sh
	@./examples/voice-stt-edge/listen.sh

# Host: Android/Tailscale remote edge (VOICE_REMOTE_HOST=0.0.0.0 for phone reachability)
voice-remote:
	@chmod +x examples/voice-stt-edge/remote.sh examples/voice-stt-edge/remote_server.py \
	  examples/voice-stt-edge/python.sh
	@./examples/voice-stt-edge/remote.sh

# Host: Tailscale HTTPS front door (run after voice-remote). Phone must use https://MagicDNS/ NOT :8787
voice-remote-serve:
	@chmod +x examples/voice-stt-edge/tailscale-serve.sh
	@./examples/voice-stt-edge/tailscale-serve.sh

# Localhost API smoke for remote edge (no phone / no Tailscale)
smoke-voice-remote:
	@chmod +x examples/voice-stt-edge/smoke-remote.sh examples/voice-stt-edge/remote_server.py \
	  examples/voice-stt-edge/python.sh
	@./examples/voice-stt-edge/smoke-remote.sh

# T-0096: run on last STT (default orchestrate high-first; VOICE_AUTO_AGENT=opencode for local-only)
voice-agent-run:
	@chmod +x examples/voice-stt-edge/agent_runner.py examples/voice-stt-edge/orchestrator.py \
	  examples/voice-stt-edge/python.sh
	@examples/voice-stt-edge/python.sh examples/voice-stt-edge/agent_runner.py \
	  --mode $${VOICE_AGENT_MODE:-$${VOICE_AUTO_AGENT:-orchestrate}} \
	  --out-dir examples/voice-stt-edge/.generated \
	  --repo "$(CURDIR)" \
	  --target $${VOICE_TARGET:-monitor} \
	  --max-turns $${VOICE_AGENT_MAX_TURNS:-8} \
	  --timeout $${VOICE_AGENT_TIMEOUT:-600}

voice-orchestrate:
	@chmod +x examples/voice-stt-edge/orchestrator.py examples/voice-stt-edge/python.sh
	@examples/voice-stt-edge/python.sh examples/voice-stt-edge/orchestrator.py \
	  --route $${VOICE_ROUTE:-high-first} \
	  --out-dir examples/voice-stt-edge/.generated \
	  --repo "$(CURDIR)" \
	  --max-turns $${VOICE_AGENT_MAX_TURNS:-8} \
	  --timeout $${VOICE_AGENT_TIMEOUT:-600} \
	  $(if $(filter 1 true yes,$(VOICE_ORCH_MOCK)),--mock,)

# T-0092 smoke: local opencode path
smoke-voice-agent:
	@chmod +x examples/voice-stt-edge/smoke-agent.sh examples/voice-stt-edge/agent_runner.py \
	  examples/voice-stt-edge/python.sh examples/voice-stt-edge/remote_server.py
	@./examples/voice-stt-edge/smoke-agent.sh

# T-0096 dual-tier mock smoke (no cloud)
smoke-voice-orchestrate:
	@chmod +x examples/voice-stt-edge/smoke-orchestrate.sh examples/voice-stt-edge/orchestrator.py \
	  examples/voice-stt-edge/agent_runner.py examples/voice-stt-edge/python.sh
	@./examples/voice-stt-edge/smoke-orchestrate.sh

# T-0093: select/probe tools-capable Ollama model (writes tools-model.env)
eval-select-tools-model:
	@python3 examples/eval-harness/select_tools_model.py

smoke-tools-model:
	@chmod +x examples/eval-harness/smoke_tools_model.sh
	@./examples/eval-harness/smoke_tools_model.sh

# T-0085: stage local worker + Grok monitor brief
worker-stage:
	@chmod +x examples/opencode-ollama/worker-stage.sh
	@LOCAL_CODER_MODEL=$${LOCAL_CODER_MODEL:-deepseek-coder:6.7b} \
	  LITELLM_SMOKE_MODEL=$${LITELLM_SMOKE_MODEL:-deepseek-coder:latest} \
	  OPENAI_BASE_URL=$${OPENAI_BASE_URL:-http://127.0.0.1:11434/v1} \
	  ./examples/opencode-ollama/worker-stage.sh

worker-env:
	@test -f examples/opencode-ollama/.generated/worker.env \
	  || $(MAKE) worker-stage
	@cat examples/opencode-ollama/.generated/worker.env

monitor-brief:
	@test -f examples/opencode-ollama/.generated/monitor-brief.md \
	  || $(MAKE) worker-stage
	@echo "Monitor brief: examples/opencode-ollama/.generated/monitor-brief.md"
	@head -40 examples/opencode-ollama/.generated/monitor-brief.md

eval-tier0:
	@$(MAKE) -C $(HARNESS) eval-tier0

eval-tier1:
	@$(MAKE) -C $(HARNESS) eval-tier1

eval-mvp:
	@$(MAKE) -C $(HARNESS) eval-mvp

eval-suite:
	@$(MAKE) -C $(HARNESS) eval-suite

eval-matrix:
	@$(MAKE) -C $(HARNESS) eval-matrix

eval-v02:
	@$(MAKE) -C $(HARNESS) eval-v02

# Design/coding structural gates (skills, tools.json, text scorers, launcher, no encoded payloads) — no LLM/Ollama
# Includes scripts/check_no_encoded_payloads.py (no base64/gzip payloads or runtime-assembled shards).
eval-structural:
	@python3 examples/eval-harness/run_structural.py --write-md pipelines/eval/structural.latest.md

# Golden-task cards (deterministic; OQ-0008 / #31) — no LLM
eval-golden:
	@python3 examples/eval-harness/run_golden.py --write-md pipelines/eval/golden.latest.md

# G1 deploy-ready: build green + smoke path (HD #33) — not human UAT
eval-deploy-ready:
	@chmod +x scripts/eval-deploy-ready.sh
	@./scripts/eval-deploy-ready.sh

# Hardware-fit model pick (not limited to already-pulled). Host: ollama tags on :11434.
# EVAL_PULL_GATE=0 to only list; default pulls gate if missing and ollama CLI present.
eval-select-models:
	@python3 examples/eval-harness/select_ollama_models.py \
	  $(if $(filter 0,$(EVAL_PULL_GATE)),,--pull-gate)
	@python3 examples/eval-harness/select_ollama_models.py --exports 2>/dev/null \
	  | grep -E '^(EVAL_|LITELLM_)' > /tmp/pfy-eval-model-exports.sh
	@echo "==> shell exports → /tmp/pfy-eval-model-exports.sh"
	@cat /tmp/pfy-eval-model-exports.sh
	@echo "Re-run suite with:  set -a; . /tmp/pfy-eval-model-exports.sh; set +a; make eval-suite"
	@echo "(typo watch: set +a  not  set +1)"

# Select fit models (pull gate if needed) then full v0.2 ladder.
# Tries EVAL_GATE_CANDIDATES in order until suite passes (chat/instruct before base FIM).
# Select fit models then full v0.2 ladder (T-0074). Soft-SKIP if Ollama down unless EVAL_AUTO_REQUIRE_OLLAMA=1.
eval-auto:
	@chmod +x scripts/eval-auto.sh
	@./scripts/eval-auto.sh


env-init:
	@if [ -f .env ]; then \
	  echo ".env already exists (not overwriting)"; \
	else \
	  cp bootstrap/env/env.example .env; \
	  echo "Created .env from bootstrap/env/env.example — edit secrets before use"; \
	fi
	@echo "Registry: bootstrap/env/REGISTRY.md"
	@echo "Profiles: config/profiles/{local-only,balanced,max-performance}.env"

env-check:
	@python3 bootstrap/env/check_env.py

# --- Product levers (T-0090) — keep ≤5 public product targets ---
project-onboard:
	@chmod +x scripts/product-onboard.sh
	@DIR="$(if $(DIR),$(DIR),.)" ./scripts/product-onboard.sh

env-stage:
	@chmod +x scripts/env-stage.sh
	@./scripts/env-stage.sh

product-ship:
	@chmod +x scripts/product-ship.sh
	@./scripts/product-ship.sh

smoke-opencode-cage:
	@chmod +x examples/opencode-cage/smoke.sh
	@./examples/opencode-cage/smoke.sh

smoke-voice-tts:
	@chmod +x examples/voice-tts-status/smoke.sh
	@./examples/voice-tts-status/smoke.sh

smoke-asm:
	@chmod +x examples/asm-smoke/smoke.sh
	@./examples/asm-smoke/smoke.sh

catalog-dashboard:
	@python3 scripts/catalog_dashboard.py

catalog-check:
	@python3 scripts/catalog_check.py

smoke-contract-lint:
	@python3 scripts/smoke_contract_lint.py

smoke-product-levers:
	@chmod +x scripts/smoke-product-levers.sh
	@./scripts/smoke-product-levers.sh

model-pool-inventory:
	@python3 scripts/model_pool_inventory.py

todo-github-sync:
	@python3 scripts/sync_todo_status.py

worker-brief-refresh:
	@python3 scripts/worker_brief_refresh.py

smoke-integration:
	@chmod +x scripts/smoke-integration.sh
	@./scripts/smoke-integration.sh

eval-unified-agents:
	@python3 scripts/eval_unified_agents_pack.py
	@echo "see pipelines/eval/unified-agents-eval.latest.md"

eval-integration-change:
	@REASON="$(REASON)" python3 scripts/eval_integration_change.py

# --- G8 simple surface (ADR-0012) -------------------------------------------
.PHONY: pfy setup-simple
pfy:
	@./pfy $(ARGS)

setup-simple:
	@./pfy setup $(PROFILE)
