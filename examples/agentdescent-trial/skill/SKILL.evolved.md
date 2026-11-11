# X intake triage (baseline, as written in the repo today)

Source: README.md "Stage 0 gate" and docs/evaluation-framework.md "Phase 0: Triage & relevance gate",
copied verbatim at origin/main 7b5107d. pfy-deanery has no separate triage SKILL.md; these two passages
are the written rules the daily X intake applies.

## Stage 0 gate

Items must satisfy all of the following before catalog consideration:

- Runnable self-hosted path under ~5 minutes on a clean Ubuntu or macOS system (or a documented one-liner), accepting text-based artifacts with a clear installation one-liner as satisfying this criterion.
- Permissive open-source license suitable for embedding and modification, accepting standard attribution or usage riders as compliant unless explicit restrictions on those rights are stated.
- Working hello-world or quickstart that demonstrates the core capability.
- Open-source licensing and reproducibility inferred from standard technology stack indicators rather than requiring explicit confirmation in the initial description.

Rejections are logged with short, explicit reasons. There is no silent ignoring of candidates.

## Phase 0: Triage & relevance gate

- Local/self-hosted value, open source/reproducible, pipeline fit.
- Default to CATALOG when candidate descriptions align with acceptance criteria, issuing SKIP only for explicitly stated disqualifiers.

## Output

Answer with exactly one word: CATALOG (accept into the catalog) or SKIP (reject).