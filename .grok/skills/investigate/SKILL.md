---
name: investigate
description: >
  Systematic debugging with root-cause investigation before any fix. Use when
  the user reports bugs, errors, stack traces, regressions, "it was working
  yesterday", or asks for root cause analysis / RCA. Iron Law: no fixes without
  a confirmed root-cause hypothesis. Inspired by gstack /investigate method
  (first-party rewrite, T-0017 / ADR-0009) — not a raw upstream snapshot.
argument-hint: "[bug description or error text]"
---

# /investigate — Root-cause debugging (pfy-deanery)

**Iron Law: NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

Symptom-only patches create whack-a-mole. Find a specific, testable root-cause
hypothesis, confirm it, then apply the smallest fix. Method inspired by
[gstack investigate](https://github.com/garrytan/gstack) (MIT); this skill is
**owned first-party** — no Claude hooks, gstack bins, freeze, GBrain, or telemetry.

**Attribution:** process adapted from gstack `/investigate` phases; see
[docs/ops/gstack-skill-port-comparison.md](../../../../docs/ops/gstack-skill-port-comparison.md).

## When to run

- Bug reports, 500s, stack traces, flaky tests, unexpected behavior  
- "Why is this broken?" / "root cause" / "debug this"  
- After a regression ("worked yesterday")  

**Do not** jump to implement or `/one-shot` until Phase 3 confirms the hypothesis
(unless the user explicitly waives RCA for a trivial typo with clear evidence).

## Phase 1 — Root cause investigation

Gather evidence before any hypothesis.

1. **Symptoms** — error text, logs, reproduction steps. Ask **one** clarifying question at a time if blocked.
2. **Code path** — read/trace from symptom to likely causes; search call sites.
3. **Recent changes** — `git log --oneline -20 -- <affected-paths>`; regressions often live in the diff.
4. **Reproduce** — deterministic repro if possible; if not, state what is missing.
5. **History** — note prior fixes in the same area (recurring bugs ≈ architectural smell).

**Output:** `Root cause hypothesis: <specific, testable claim>.`

## Phase 2 — Pattern analysis

Check whether the bug matches a known class:

| Pattern | Signature | Where to look |
|---------|-----------|---------------|
| Race | Intermittent, timing-dependent | Shared state, concurrency |
| Null/nil | TypeError, optional deref | Missing guards |
| State corruption | Inconsistent / partial updates | Transactions, hooks |
| Integration failure | Timeout, bad response | APIs, cage network, MCP |
| Config drift | Works host, fails cage/CI | Env, profiles, mounts |
| Stale cache | Old data until clear | Caches, rebuilds |

Also check `docs/TODO.md`, open questions, and cage/smoke notes if integration-related.

Optional: search for generic `{framework} {error type}` — **sanitize** first (no secrets, hosts, paths, SQL, customer data).

## Phase 3 — Hypothesis testing

**Before writing a fix:**

1. Confirm the hypothesis (log, assert, minimal probe, or targeted test).
2. If wrong: gather more evidence; do not stack random patches.
3. **3-strike rule:** after 3 failed hypotheses, **STOP** and ask:
   - Continue with a new hypothesis?  
   - Escalate (human / architecture)?  
   - Instrument and wait?

**Red flags:** "quick fix for now"; fix before tracing data flow; each fix births a new bug elsewhere.

## Phase 4 — Implementation (only after confirm)

1. Fix the **root cause**, not the symptom. Minimal diff.
2. Prefer fewest files; no drive-by refactors.
3. **Regression test** when the stack allows: fails without fix, passes with fix. Prefer mattpocock **`tdd`** (paths pack) for test-first style.
4. Run relevant tests / `make smoke-*` if the bug was integration-scoped.
5. If fix touches **>5 files**, pause and confirm blast radius with the user.

## Phase 5 — Verification and report

Reproduce original failure path; confirm fixed. Run suite or targeted checks; paste key output.

```text
DEBUG REPORT
════════════════════════════════════════
Symptom:         [what was observed]
Root cause:      [what was actually wrong]
Fix:             [what changed — file:line]
Evidence:        [repro after fix / test output]
Regression test: [path or "none — reason"]
Related:         [TODO/OQ/ADR if any]
Status:          DONE | DONE_WITH_CONCERNS | BLOCKED
════════════════════════════════════════
```

## Status codes

| Status | Meaning |
|--------|---------|
| **DONE** | Root cause found, fix verified, tests green (or justified skip) |
| **DONE_WITH_CONCERNS** | Fixed but cannot fully verify (intermittent, needs staging) |
| **BLOCKED** | Root cause unclear after investigation; what was tried + ask |
| **NEEDS_CONTEXT** | Missing repro/logs/env; state exactly what is needed |

## Scope discipline

- Prefer confining edits to the module that owns the root cause.
- Shell can bypass write-guard; still respect `WRITE_GUARD_*` and cage policy when applicable.
- Do not force-push; do not commit secrets.

## Handoffs (this stack)

| Situation | Next |
|-----------|------|
| Architecture is the bug | `/adr` |
| Unsettled product/tech choice | `/open-questions` |
| Clear DoD after RCA for a build | `/one-shot` |
| Need stronger tests | mattpocock `tdd` (skills.paths) |
| Diff review after fix | mattpocock `code-review` |
| Integration failure | `make cage-test` / `make smoke-*` ([examples-smokes](../../../../docs/modules/examples-smokes.md)) |
| Catalog docs drift from fix | `/catalog-docs` |

## Do not

- Ship a fix you cannot verify  
- Say "this should fix it" without evidence  
- Infinite retries (use 3-strike)  
- Port or depend on gstack binaries/hooks  
- Treat write-guard as a full security audit (that is a different skill later)  
