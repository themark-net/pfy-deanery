---
name: tests-in-main-evals-in-ops
description: >
  Use when writing, moving, or reviewing tests, drafting a Build or Cursor DoD,
  or deciding whether a fixture, eval, dogfood run, or Tester evidence belongs
  in a product repo or in that product's ops repo.
argument-hint: "[review | dod]"
---

# Tests in main, evals in ops

Use this when writing or moving tests, reviewing a test suite, or deciding where a fixture or eval should live.

See [PORT.md](PORT.md). Structural check: `make smoke-grok-skills` ([skill-verification.md](../../../../docs/ops/skill-verification.md)).

## Standing rule (2026-11-22)

Any testing beyond built-in or unit must be done in a separate repo, so the generalized tooling stays clean and reusable. The main repo still has tests; those tests are the generalized "does the code work" checks.

In practice:

| Product main repo | Product ops repo (for example `gomjobbar-ops`, `pfy-mentat-ops`) |
|-------------------|------------------------------------------------------------------|
| Built-in, unit, and general does-the-code-work tests | Dogfood runs against a real account or personal journal |
| Behavior, integration, and E2E tests on synthetic fixtures | Real-data or end-to-end evals |
| Smokes that use generated or checked-in synthetic inputs | Personal fixtures and Tester evidence |

This is compatible with **`prefer-behavior-and-fail-recover-tests`**: sociable behavior tests on synthetic fixtures stay in main. The split is about whose data and which repo, not about dropping behavior tests from main.

## Existing tests that use real data

1. Move the real-data test, fixture, or evidence pack to the product's `-ops` repo (or `$PFY_OPS_ROOT`).
2. Keep (or add) a general synthetic version in main that still proves the code works.
3. Do not leave personal or live account data in the product tree "just until ops is ready."

## Examples

- `gomjobbar` keeps unit tests and synthetic intake or PDF fixtures. Real journal applications, live resume PDFs, and Tester evidence live in `gomjobbar-ops`.
- `pfy-deanery` keeps `make smoke-grok-skills` and synthetic catalog fixtures. Live eval runs and dogfood receipts live in `pfy-mentat-ops`.

## Red flags

- A personal resume, journal export, or live posting captured into the main test suite
- Skipping main-repo tests because "ops already covers it"
- Calling a real-data eval a unit test so it can stay in main
- Copying Tester evidence into the public product repo

## Build / Cursor DoD line (paste into every implement prompt)

```
Tests: the product main repo keeps built-in, unit, and general does-the-code-work tests on synthetic fixtures. Dogfood, real-data or end-to-end evals, personal fixtures, and Tester evidence go in the product's ops repo. Behavior tests on synthetic fixtures stay in main (prefer-behavior-and-fail-recover-tests).
```
