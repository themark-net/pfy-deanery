# PARKED: naming and repo split

**Status:** PARKED. Secondary to the MVP of the main project goals (track, catalog, integrate, local suite). Nothing here moves until Mark reopens it.

Recorded 2026-11-08 at Mark's request so these todos are not lost.

## Split study result (2026-11-08)

Study Page: [pfy-mentat split study: catalog vs runtime](https://cursor.com/canvas/store-4bf68549-29ed-45f2-ba59-5394f97d09b6/6ac64d8e-0cde-49b2-9611-d9971607bf84)

- Keep one repo for now. Split it internally into two installable packages, catalog and runtime, with a lint test that blocks cross-side imports outside the agreed interface. About 1.5 to 2 Build days.
- A real two-repo split later is about a day. Do it only on a trigger, such as an outsider wanting one half.

Interface work needed under any option:

- JSON Schemas for stage cards and receipts.
- A one-way catalog link: runtime `toolsets.json` names a catalog entry, and the catalog stops pointing back (ADR-0017).
- A `PFY_CATALOG_DIR`-style setting for the catalog location.
- A stable lane and model-lock CLI.
- One owner side per skill (`.grok/skills` and `bootstrap/grok-cli/skills` have drifted).

## Open split questions

- Which name goes on which half (`./pfy` and `pfylib` are runtime-side).
- Where the shared test and CI kit lives.
- What triggers a real split.
- Whether the runtime pins catalog releases or reads them live.
- Whether a wiring change and its receipt can land in different repos.

## Naming todos

- [ ] Working name for the Mentat side is "Deanery". In BOFH terms, the human is the BOFH and Deanery is a structure the BOFH uses for his own goals. Mark noted the .org and .ai domains were open as of 2026-11-08. They are not registered and must not be registered without Mark's go.
- [ ] Check whether "Pimply Faced Youth" is free to use, or coin a new term.
- [ ] Decide on a name for the whole suite.
- [ ] Decide whether a third glue or integration repo is worth having, or whether two repos are enough.
- [ ] Deep dive later on BOFH trademark and copyright. Mark's current read is that the term is old and obscure enough to be open to adoption and is not bound like Dilbert-style IP. Not verified.

## Context

Mark's belief that nobody else does exactly this suite still holds. See the [supersede watch](../ops/supersede-watch.md).
