# Decision gates (offline stubs)

Versioned offline decision-gate stubs for org / pfy **shadow** mode. Dogfood **D1**. Cites: [ADR-0016](../../docs/adr/0016-jev-decision-layer.md) · [#230](https://github.com/themark-net/pfy-deanery/issues/230).

Choice, Score, and Noul criteria, plus the conf gate, live in these files. That is the offline fallback. The files are data, so a later adapter can speak HTTP or an SDK without this repo locking one in.

## Paths

| Path | Role |
|------|------|
| **CUA-S1-FORMS** / **org-spinny-decide** | Primary local. Every stub here sets engine preference `local`. |
| TypeSafe | Optional cloud, and unkeyed for this dogfood. These files do not call it. |

Shadow mode records the gate id, state, choice, margin, and whether the margin is under the conf gate. The existing org or pfy path still acts. This directory is schema only: no network call and no live bridge.

Catalog **HOLD 70–75** stays. These stubs are not a `TOOLS.md` row (ADR-0016).

## Files

| File | Gate |
|------|------|
| [push_hold.shadow.v0.json](push_hold.shadow.v0.json) | Org `push_hold`. Criteria keys `push` \| `hold` \| `escalate`. `conf_gate` **0.55** matches org-spinny defaults. |
| [laya-trial.cases.v0.json](laya-trial.cases.v0.json) | Entry 086 eval-auto labeled Choice set (48 cases). Labels written before either model ran. Coding-session gate **0.85**. Same set for the Laya shadow follow-up (`PFY_JEV_LAYA_SHADOW`, default off) and Entry 089 local-inference bench. Cite **#230**. Not a default-lane swap. |
| [atg-compile.cases.v0.json](atg-compile.cases.v0.json) | Ten synthetic tool-DAG tasks for `examples/atg-compile/bench.py`. Oracles written before any live model. Calls pinned atg-framework by path. Not a paper benchmark. Stage stays I1. |
| [catalog-fit.v0.json](catalog-fit.v0.json) | Catalog-fit Choice for Deanery. Criteria keys `fit` \| `skip_install` \| `redundant` \| `awareness`. `conf_gate` **0.85**. Labels written before any model run. Script `scripts/catalog_fit_triage.py`. Cite **ADR-0016** and **#230**. |

ADR-0016 keeps the coding-session Choice gate near **0.85**. The **0.55** figure belongs only to this org `push_hold` shadow stub. Confidence is a margin (`conf ok` / `conf low`), never percent-correct. Under the gate, the shadow result is escalate.
