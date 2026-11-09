# ADR-0016: Jev-style decision layer (typed Choice/Score)

- **Date:** 2026-09-18
- **Status:** Accepted
- **Deciders:** Founder locks on #230
- **Issue:** [#230](https://github.com/themark-net/pfy-mentat/issues/230)

## Context

Coding sessions need a decision API beside Gab cloud (`model=auto`) and local recommend/try: compact tool context without summarizing it away, then pick a model/tool with an honest certainty **margin**. Chat panes, “% correct” meters, and browser-use demos all fail that job.

## Decision

- Attach a **typed Choice/Score** decision layer (not chat) on Loop/Attach.
- **Primary local** attach is **CUA-S1-FORMS** (https://github.com/trycua/cua; operator-free nimo smoke).
- **TypeSafe Jev** (`jev-1.13.0`, `POST https://api.typesafe.ai/v1/systemone`) is **optional cloud**. Missing key → FAIL+next (or switch CUA-S1-FORMS). Never required for default smoke.
- **mini-jev** is a teaching fallback only.
- Confidence gate default **~0.85**. Below gate → visible FAIL / escalate. No silent auto-act.
- Rebuild Choice options from **live** wizard/engine state.
- Honesty chip: `decision ≠ gab auto ≠ local`.
- Catalog 70–75 stay HOLD. Do not reopen #76. No Env tab. #225 Launch and #228 Gab lane stay.

## Rationale

Rejected alternatives:

1. **Chat UI for Jev** — Jev is a decision API; a transcript pane lies about the product.
2. **Browser-use / Jev Ultrafast as core** — not the coding-session value (compaction + routing middleware).
3. **mini-jev as primary local** — additive lock names CUA-S1-FORMS (~706K / ~2.8MB, form-fill specialist) as the FreeToken/local attach.
4. **Require TypeSafe key for smoke** — operator drip; default smoke must run on nimo without ops.
5. **Equate decision with Gab `auto` or local recommend** — three different surfaces.

## Consequences

- Wizard toggle: `off | cua-s1-forms | typesafe | mini-jev`. Off does not block Launch session.
- Operator copy uses chips, not banners. Confidence is never painted as correctness.
- First-party skill `jev-decision` teaches the locks; official TypeSafe skill remains https://github.com/typesafe-ai/skills (pin, not catalog row).

## References

- `scripts/pfy_jev_230.py`
- a private ops note
- `docs/design/JEV-230-CUA-S1-FORMS-LOCK.md`
- `docs/design/DESKTOP-SPEC.md`
- `docs/ops/jev-230.md`
