# Autonomous decisions mvp-preflight-1031

One line each: choice | alternatives | why. Conservative and reversible. No questions asked.

- Treat `repo-handoff-doc-required` and `write-loop-exits-first` as the drop-in rules (exits in this run log before code, handoff file on every exit) | block the lane until those skill files appear | neither name exists as a SKILL.md in this worktree or `~/.grok/skills`; the drop-in already states both rules
- Lead writes the one workstream | spawn a coding sub-agent in this same worktree | the owned files overlap, and a second writer would race commits; the orchestrator spawn rule is for disjoint workstreams
- Match phrases by casefolded substring, rate-limit rule before auth rule | word-boundary regex, or auth before rate-limit | the drop-in lists literal phrases and says the first rule wins; a boundary is not in the contract and could drop a specified `429` hit
- `rc == 0` is the only short-circuit to `other` | coerce None or non-ints to `other` before matching | the contract classifies whenever `rc` is not 0; tests pass integers; hiding a bad `rc` would look like a clean `other`
- Do not add `build_preflight` to `pfylib/__init__.py` | export it from the package root | `__init__.py` is not an owned file; callers import `pfylib.build_preflight`
- Fixture markers in tests are the strings the acceptance names, not a real key | paste a PEM block | the return-value check needs those markers, and a real secret must not be committed
- After the classifier, do not wire `scripts/` or start round 2 | edit the cloud runner from this lane | `scripts/` is forbidden here; `mvp-dedupe-1031` waits on `origin/bot/mvp-integrate-1031`, which is absent; G10 is excluded by plan decision D18
