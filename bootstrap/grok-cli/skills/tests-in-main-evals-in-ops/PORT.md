# tests-in-main-evals-in-ops - first-party port

- **Placement:** `bootstrap/grok-cli/skills/tests-in-main-evals-in-ops/` (portable SoT)
- **Org Bot skill:** pointer only. SoT: pfy `bootstrap/grok-cli/skills/tests-in-main-evals-in-ops`
- **Taken:** main-repo tests stay built-in / unit / general does-the-code-work; dogfood, real-data or end-to-end evals, personal fixtures, and Tester evidence go in the product ops repo; move real-data tests to ops and keep a synthetic version in main; compatible with prefer-behavior-and-fail-recover-tests (synthetic behavior tests stay in main); DoD paste line
- **Omitted:** founder personal name; bot-only ids; product checkout paths
- **Not a slash-only ops note:** invoke as `/tests-in-main-evals-in-ops` after install
- **Verify:** `make smoke-grok-skills` ([skill-verification.md](../../../../docs/ops/skill-verification.md))
