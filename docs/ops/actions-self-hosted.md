# GitHub Actions + self-hosted runner (`nimo`)

**Runner:** `nimo` · labels: `self-hosted`, `Linux`, `X64`, `pfy-mentat` · status must be **online**  
**Policy:** GitHub-hosted = always-on G0; self-hosted = lab (Ollama, product smokes, inventory).

## Workflows

| Workflow | Runner | Trigger | Purpose |
|----------|--------|---------|---------|
| `eval-structural` | ubuntu-24.04 (pinned) **and** self-hosted | push/PR/manual | G0 structural+golden; local also catalog receipts |
| `local-lab` | self-hosted only | push (paths), nightly 04:15 UTC, manual modes | G1 deploy-ready, product levers, integration, eval-auto soft, inventory |
| `nightly-models` | self-hosted only | 07:00 UTC + manual | Implement-lane matrix vs local Ollama (soft on schedule) |
| `post-merge-brief` | self-hosted only | main push + manual | Operator brief + pool + dashboard artifacts |

### Manual lab modes (`local-lab`)

```bash
gh workflow run local-lab.yml -R themark-net/pfy-mentat -f mode=full
gh workflow run local-lab.yml -R themark-net/pfy-mentat -f mode=eval-auto
gh workflow run local-lab.yml -R themark-net/pfy-mentat -f mode=g1-only
gh workflow run local-lab.yml -R themark-net/pfy-mentat -f mode=inventory
gh workflow run local-lab.yml -R themark-net/pfy-mentat -f mode=product
gh workflow run local-lab.yml -R themark-net/pfy-mentat -f mode=integration
```

### Nightly models

```bash
gh workflow run nightly-models.yml -R themark-net/pfy-mentat
gh workflow run nightly-models.yml -R themark-net/pfy-mentat -f models='deepseek-coder:6.7b,qwen2.5-coder:7b-instruct'
```

## Why split hosted vs self-hosted

| Job class | Why |
|-----------|-----|
| G0 schema/skills | Must not depend on lab machine uptime |
| Ollama implement-lane | Needs local GPUs/CPU models on nimo |
| Model pool GB | Host disk only |
| Product onboard smoke | Exercises real checkout + scripts on lab OS |
| Cage/docker | Only if docker present on nimo |

## Offline runner behavior

- `structural-local` and `post-merge-brief` use `continue-on-error: true` so offline nimo does not red-X the whole push.
- `local-lab` / `nightly-models` will **queue** until the runner is online (or fail if removed).

## Artifacts

Download from the Actions run UI: `g0-*`, `local-lab-*`, `nightly-models-*`, `operator-brief-*`.

## Secrets

None required for G0. Ollama is local on nimo (no cloud key). Optional later: `XAI_API_KEY` for cloud monitor jobs — do not put in logs.


## Verified on nimo (2026-07-30)

| Run | Result |
|-----|--------|
| `eval-structural` dual job | **PASS** github + self-hosted (~9s each) |
| `post-merge-brief` | **PASS** |
| `local-lab` mode=g1-only | **PASS** (~1m) |
| `nightly-models` first dispatch | failed on CLI flag; fixed to `--matrix-md` |

Use Actions → Artifacts for receipts after each run.

## Design notes (nimo)

- **eval-auto is observational** on `local-lab` (always exit 0 after run): model quality must not red-X lab G0/G1.
- **Nightly matrix** tracks implement-lane pass rates over time (artifacts); also exit 0.
- Single runner serializes jobs — prefer one `workflow_dispatch` at a time for long eval-auto.
- First real eval-auto on nimo: deepseek-coder:6.7b-instruct **3/4** (failed 012-slugify); qwen 14b not installed.


## Host vs cage base URL

On **nimo** (self-hosted job, not inside agent-cage):

```bash
export OPENAI_BASE_URL=http://127.0.0.1:11435/v1   # host-ollama-gateway
# or direct Ollama:
# export OPENAI_BASE_URL=http://127.0.0.1:11434/v1
```

Default in eval scripts is `host.docker.internal:11435` for **in-cage** smokes — wrong for bare runner processes.
