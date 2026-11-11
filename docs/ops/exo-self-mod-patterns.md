# Exo self-mod patterns (extract for pfy-deanery)

**Upstream:** [exoharness/exo](https://github.com/exoharness/exo)  
**Pin:** `372602d1b553af06e9843e19f31fa8a7f749ab6e`  
**Primary sources:** `docs/RSI.md`, `examples/exo/docs/SELF-CONTROL.md`, `docs/design/skills-arch.md`  
**Posture:** **I1 pattern extract** — not primary runtime (Grok + agent-cage remain).

## What Exo actually is

A complete long-running agent harness whose *differentiator* is **recursive self-improvement with scaffolding**:

| Primitive | Role |
|-----------|------|
| **Repo mount** | Own source at `/workspace/exo` — agent can edit harness, prompts, tools |
| **Canonical event log** | Append-only; **survives** sandbox rewind; answers “what did I already try?” |
| **Sandbox snapshot/rewind** | Experiment FS without erasing identity |
| **`rebuild_and_restart_exo`** | Guarded validate → build → drain restart (preserves `.exo` state) |
| **Skills as artifacts** | Progressive disclosure (`name+description` always; body on demand); durable outside sandbox |
| **Guardian** | Host-side service control; operator visibility |

Immutable kernel (policy): event log + secret backend + (default) exo-harness code not rewritten casually.

## Do they have a formal self-change rubric?

**No numeric scorecard.** Self-verification is **§8 practice + primitives**, not a 0–100 eval harness:

1. **Before:** `snapshot_sandbox` and/or clean git  
2. **Validate:** run `cargo`/`pnpm` checks; call `rebuild_and_restart_exo(reason=…)`  
3. **Adopt:** commit; drain-restart services  
4. **Rollback:** `git revert`, `rewind_sandbox`, disable tool/adapter  
5. **Memory of failure:** event log keeps tries after rewind  

**Explicit gap (upstream):** no canary clone that compares behavior before adopting on the live instance.

### Design principles (worth stealing)

From SELF-CONTROL “Mutation and Transparency”:

1. **Auditable** — event log + git + host logs reconstruct *what* and *why*  
2. **Visible** — agent can see code, logs, events  
3. **Named tools** — durable mutations go through schemas, not silent host file hacks  
4. **Reversible by default** — disable/checkpoint > hard delete  

## Map → pfy-deanery (safer, catalog-shaped)

| Exo idea | Our equivalent |
|----------|----------------|
| Canonical event log | `pipelines/eval/*`, `pipelines/smoke/*`, golden tasks, git history |
| Snapshot before change | Branch / worktree / temp DIR product-onboard |
| rebuild_and_restart | `make eval-structural` + `eval-deploy-ready` + restart only if needed |
| Skills progressive disclosure | first-party + paths packs; `verify_skills` / structural |
| Self-mod of harness | **ADR + PR**; hermes-feedback; **not** unattended kernel rewrite (MUE-X same rule) |
| Self-mod for *ingest* | **`make eval-integration-change`** (below) — automated gates for catalog/skill ingestion |

We deliberately **do not** run full RSI on the catalog monorepo. We **do** adopt Exo’s loop shape for **integration ingestion**: propose → gate → receipt → adopt/rollback.

## Integration ingestion loop (implemented)

See [integration-self-mod-eval.md](integration-self-mod-eval.md) and:

```bash
make eval-integration-change
# or
python3 scripts/eval_integration_change.py --help
```

That is our portable “evaluate a change to ourselves (catalog/skills/smokes)” without giving agents free rewrite of the operator kernel.

## Non-goals

- Replace Grok CLI / agent-cage with Exo  
- Unattended `rebuild_and_restart` of pfy-deanery  
- Subtree-embed Exo  
- Numeric RSI fitness function (upstream doesn’t have one either)

## Related

- [MUE-X patterns](mue-x-patterns.md) (self-rewrite caution)  
- [integration-stages.md](integration-stages.md) (I0–I4)  
- [eval-gates-and-ux-uat.md](eval-gates-and-ux-uat.md) (G0/G1/G2)  
