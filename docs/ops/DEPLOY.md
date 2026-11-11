# Deploy / new-machine stand-up (pfy-deanery)

**Repo:** https://github.com/themark-net/pfy-deanery  

## 1. Clone

```bash
git clone git@github.com:themark-net/pfy-deanery.git
cd pfy-deanery
```

Optional local folder rename if you still have the old path:

```bash
mv ~/DEVELOP/local-llm-dev-tools ~/DEVELOP/pfy-mentat
cd ~/DEVELOP/pfy-mentat
git remote set-url origin git@github.com:themark-net/pfy-deanery.git
git fetch origin && git checkout main && git pull
```

## 2. Environment

```bash
./pfy install
# launchers in ~/.local/bin (deanery and pfy, plus the mentat alias). Pass --prefix for another directory.
# If it is not on PATH, add the printed export PATH="$HOME/.local/bin:$PATH"
# line to ~/.bashrc or ~/.profile. This command does not edit those files and does not run sudo.
# Remove: ./pfy install --uninstall
#     or: ./pfy uninstall --launchers
make env-init
# edit .env: DEPLOY_PROFILE=local-only|balanced|max-performance
# Grok subscription: use host `grok login` (OIDC → ~/.grok/auth.json)
# Optional CI: XAI_API_KEY in .env
make env-check
```

See [bootstrap/env/REGISTRY.md](../../bootstrap/env/REGISTRY.md) and [deployment-profiles.md](deployment-profiles.md).

## 3. Grok operator skills + MCP

```bash
# install Grok CLI if needed: curl -fsSL https://x.ai/cli/install.sh | bash
./bootstrap/grok-cli/install.sh --with-codebase-memory
# ensure ~/.local/bin on PATH
```

## 4. Agent cage (integration lab)

```bash
make cage-doctor
make cage-setup
make cage-init          # once → ~/.agentcage
make cage-up-mcp
make cage-test
make cage-down
```

## 5. Grok-in-cage (optional)

```bash
make cage-grok-install
make cage-grok-auth-import   # copy host OIDC session
make cage-grok-build
make cage-grok-up            # not plain cage-up-mcp
make cage-grok-smoke
make cage-shell              # grok available as /usr/local/bin/grok
```

Details: [harness/agent-cage/overlays/grok/README.md](../../harness/agent-cage/overlays/grok/README.md).

## 6. Docs skills

- `/catalog-docs` — keep this repo documented  
- `/one-shot` — unattended-until-green (DoD + lab); example DoDs: [one-shot-example-dods.md](one-shot-example-dods.md)  
- Process: DESIGN / ADR / TODO / OQ  

## 7. Integration smokes (after cage up)

Prefer these over ad-hoc host-only checks ([harness framework](harness-integration-framework.md)):

| Target | What |
|--------|------|
| `make smoke-write-guard` | Write-guard policy (audit/enforce) |
| `make smoke-codebase-memory` | codebase-memory-mcp index+search |
| `make smoke-repowise` | repowise health (zero LLM) |
| `make smoke-context-tools` | both context tools |
| `make smoke-litellm-ollama` | LiteLLM → host Ollama (needs gateway) |

## Not fully automated yet

| Item | Status |
|------|--------|
| Write-guard MCP server | v0.1 implemented (`make smoke-write-guard`); mcp-host wiring optional |
| LiteLLM profile recipes | **T-0012 done** — `config/litellm/{local-only,balanced,max-performance}.yaml` |
| Full eval harness | **MVP + v0.2:** `make eval-mvp` / `eval-v02` / `eval-matrix`; DSPy later |
| OpenCode / Claude validation | TODO T-0040 (P3) |
| AgenC host runtime | **Demoted (ADR-0010)** — catalog reference only; prefer Grok CLI + `make cage-grok-*` |
| Grok Build in cage | **T-0045 done:** `make cage-grok-up` + `make cage-grok-ready` (workspace sync + filesystem MCP) |

## Verify checklist

- [ ] `git remote -v` → `themark-net/pfy-deanery.git`
- [ ] `make env-check` OK for chosen profile  
- [ ] `grok --version` on host  
- [ ] `make cage-test` green (stack up)  
- [ ] Optional: `make cage-grok-smoke` green  
- [ ] Optional: `make smoke-write-guard` / `smoke-context-tools` / `smoke-litellm-ollama`  

