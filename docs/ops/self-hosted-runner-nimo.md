# Self-hosted runner **nimo** — how we use it

**Runner:** GitHub Actions self-hosted · labels `self-hosted`, `Linux`, `X64`, `pfy-mentat`  
**Status check:** `gh api repos/themark-net/pfy-mentat/actions/runners`  
**Host stack:** Ollama (`:11434`), optional gateway (`:11435`), local disk models (250GB pool)

## Why nimo exists

GitHub-hosted runners cannot see your Ollama weights, mic, or cage. **nimo** is the lab machine that:

| Capability | GitHub-hosted | nimo |
|------------|---------------|------|
| `eval-structural` / golden (G0) | yes | yes (dual) |
| `eval-auto` / implement-lane | no real models | yes |
| Model matrix / nightly ranking | no | **primary** |
| Model pool inventory (GB) | empty | real paths |
| Product levers + soft smokes | partial | full host tools |
| Voice / OpenCode / docker cage | no | when installed |

## Workflow map

| Workflow | Trigger | Role |
|----------|---------|------|
| **eval-structural** | push / PR | G0 dual: ubuntu + nimo (nimo soft if offline) |
| **local-lab** | schedule `04:15 UTC` + **manual** slices | G1 deploy-ready, product, integration, eval-auto soft |
| **nightly-models** | schedule `07:00 UTC` + manual models list | Implement-lane matrix vs local Ollama |
| **post-merge-brief** | push main | Monitor brief + pool + dashboard artifacts |

**Manual slices (local-lab):**

```bash
gh workflow run local-lab.yml -f mode=g1-only
gh workflow run local-lab.yml -f mode=eval-auto
gh workflow run local-lab.yml -f mode=inventory
gh workflow run local-lab.yml -f mode=product
gh workflow run local-lab.yml -f mode=integration
gh workflow run local-lab.yml -f mode=full
```

**Model matrix:**

```bash
# auto-pick preferred coders present on host
gh workflow run nightly-models.yml

# explicit list
gh workflow run nightly-models.yml -f models='qwen2.5-coder:7b-instruct,deepseek-coder:6.7b-instruct'
```

## Useful local-system patterns

### 1. Free CI of LLM work (default design)

- **Push/PR:** only G0 on GitHub-hosted (merge gate) + dual G0 on nimo (observational).
- **Heavy:** schedule or dispatch on nimo so the free runner queue stays short.

### 2. Model league table (nightly)

Rank local models on the same four coding tasks (`001`, `002`, `011`, `012`). Artifacts: `pipelines/eval/nightly-models.latest.md`.

Use to decide **which mini models stay in the 250GB pool** and which get deleted.

### 3. Golden-task replay later

When LLM golden replay lands (HD #36), run it **only on nimo** with a worktree sandbox — never on free GitHub minutes for multi-minute agent loops.

### 4. Catalog + ops heartbeat

`post-merge-brief` refreshes:

- monitor brief (git + receipt index)
- model pool GB
- scoring dashboard

Operators download the artifact after merge instead of SSHing.

### 5. Slice-before-sleep / slice-before-PR

Dispatch `local-lab` `g1-only` or `product` after a platform change without waiting for nightly.

### 6. Eval-auto observational

`mode=eval-auto` runs implement ladder when Ollama is up; **soft exit** so flaky local models don’t red-badge main. Read `eval-auto.latest.md` for truth.

### 7. Optional: pin a “house gate model”

On nimo, keep one small instruct model always pulled (e.g. `deepseek-coder:6.7b-instruct` or `qwen2.5-coder:7b-instruct`). Nightly and eval-auto prefer it.

### 8. Voice / cage (future workflow)

`voice-clean` lived on branch `fix-voice-remote-port-20260727`. Re-home to main when voice UAT is ready — **only** self-hosted.

## Host prerequisites (nimo)

```text
✓ actions-runner with label pfy-mentat
✓ python3
✓ ollama serve  → 127.0.0.1:11434
✓ at least one coder/instruct model pulled
○ optional: host-ollama-gateway :11435 (for docker/cage)
○ optional: docker for smoke-integration cage path
○ litellm NOT required — scored tasks use stdlib HTTP fallback
```

## Debugging a red/soft lab

```bash
gh run list --workflow=nightly-models.yml --limit 5
gh run view <id> --log-failed
gh run download <id> -n nightly-models-<id>
```

Common failure (fixed 2026-07-30): `litellm not installed` → now falls back to Ollama HTTP.

## Do not

- Point self-hosted jobs at cloud-only secrets for routine G0 (waste + flakes).
- Auto-run full `local-lab` on every push (starves dual G0 / cancels).
- Commit model weights from the runner workspace.
