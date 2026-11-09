---
name: jev-decision
description: >
  Jev-style typed Choice/Score decision layer for pfy: CUA-S1-FORMS primary
  local, TypeSafe optional cloud, mini-jev teaching fallback. Confidence is a
  margin chip, never percent-correct. Use when /jev-decision, decision layer,
  CUA-S1-FORMS, TypeSafe Jev attach, or compaction/routing middleware.
---

# jev-decision — typed Choice/Score (#230)

Decision API, **not chat**. Cite **#230** only. Do not reopen #76. Catalog 70–75 HOLD.

## Locks

- **Primary local:** CUA-S1-FORMS (https://github.com/trycua/cua). operator-free smoke.
- **Optional cloud:** TypeSafe Jev `jev-1.13.0`. Key missing → FAIL+next or switch local.
- **Fallback only:** mini-jev.
- Confidence = calibrated **margin** (`conf ok` / `conf low`). Gate ~0.85. No silent auto-act.
- Core = compaction + model/tool middleware. Not browser-use.
- Honesty: `decision ≠ gab auto ≠ local`.

Official TypeSafe agent skill (cloud cookbook, not this product surface): https://github.com/typesafe-ai/skills

## Operate

```bash
./pfy decision smoke
python3 scripts/pfy_jev_230.py --selftest
```

Loop wizard: decision off | CUA-S1-FORMS | TypeSafe | mini-jev. Launch session stays #225 when decision is off.

## Headless implement

On pfy-mentat slices, prefer **`./pfy build -p "<prompt>"`** over bare `grok -p`. The wrapper applies the local jev toolset, logs a decision shadow, then runs plain `grok -p`.

Receipt: `pipelines/dogfood/build/`.

```bash
./pfy build -p "Implement …"
```

## `./pfy decision route` exits

**0** = ready, **3** = escalate (conf low — valid, not broken; no silent auto-act), **1** = fail.

## Do not

- Paint Jev as chat or confidence as correctness
- Equate decision with Gab auto or local recommend
- Require a TypeSafe key for default smoke
- Lift catalog 70–75 or reopen #76
- Treat exit 3 / escalate as a broken tool, or auto-act on conf low
- Use bare `grok -p` for headless pfy-mentat implement when `./pfy build -p` can run
