# X intake triage (baseline: an excerpt of the repo rules today)

Source: README.md "Stage 0 gate" and docs/evaluation-framework.md "Phase 0: Triage & relevance gate",
excerpted (not verbatim; see skill/README.md) at origin/main 7b5107d. pfy-deanery has no separate triage SKILL.md; these two passages
are the written rules the daily X intake applies.

## Stage 0 gate

Items must satisfy all of the following before catalog consideration:

- Runnable self-hosted path under ~5 minutes on a clean Ubuntu or macOS system (or a documented one-liner).
- Permissive open-source license suitable for embedding and modification.
- Working hello-world or quickstart that demonstrates the core capability.

Rejections are logged with short, explicit reasons. There is no silent ignoring of candidates.

## Phase 0: Triage & relevance gate

- Local/self-hosted value, open source/reproducible, pipeline fit.
- Accept → Phase 1, Defer, or Reject.

## Output

Answer with exactly one word: CATALOG (accept into the catalog) or SKIP (reject).
