# ADR-0006: Deployment profiles (local-only → max-performance)

- **Date:** 2026-07-12
- **Status:** Accepted

## Context

The catalog integrates local inference, cloud APIs, and harnesses. A single fixed topology forces either “everything local” or “everything cloud” and breaks multi-dev / multi-machine use. Operators need a first-class **gradient** and a secure way to provision variables on init.

## Decision

1. Introduce **named deployment profiles**: `local-only`, `balanced` (default), `max-performance`, plus optional custom files under `config/profiles/`.
2. Select via `DEPLOY_PROFILE` (env / `.env`).
3. Maintain a **variable registry** at `bootstrap/env/REGISTRY.md` and an `env.example`; `make env-init` / `make env-check` provision and validate.
4. Secrets only in `.env` or process environment - never in git, never baked into container images.
5. Tool integrations **must** register new vars in REGISTRY when added.

## Rationale

- Matches real use: bulk local, hard tasks cloud (balanced).
- Explicit local-only supports privacy/airgap experiments.
- max-performance documents cloud-first without pretending local is free.
- Registry prevents env drift across bootstrap, cage, and recipes.

Rejected alternatives:

1. **Single hard-coded stack in README only** - not machine-checkable; secrets leak into docs.
2. **Profile = separate git branches** - unmaintainable.
3. **Secrets in docker-compose committed files** - unsafe.

## Consequences

- New env keys update REGISTRY + env.example in the same change.
- LiteLLM/router configs should key off `DEPLOY_PROFILE` when introduced.
- `make env-check` may fail closed for missing required secrets on max-performance / balanced.

## References

- `docs/ops/deployment-profiles.md`
- `bootstrap/env/`
- `config/profiles/`
