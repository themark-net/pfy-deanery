### Entry 088: Beacon — cross-harness agent session history turned into reusable knowledge

- **URL**: https://github.com/asymptote-labs/agent-beacon (MIT)
- **Date**: 2026-10-05 (daily X intake)
- **Source / Poster**: Mark's bookmark of @_avichawla, https://x.com/_avichawla/status/2101966536798040332
- **Summary / Key Claims** (upstream README): Open-source memory layer for coding agents. Captures session history (prompts, responses, tool calls, commands, file edits, approvals, MCP activity, tokens) across 20+ harnesses into one OpenTelemetry-based event model, written to local JSONL (`~/.beacon/endpoint/logs/runtime.jsonl`) by default. Loop: capture, evaluate what worked, extract knowledge, review and approve, reuse through MCP or Agent Skills. Its harness table lists **Grok Build** (hooks + poll), OpenCode, Hermes Agent, Cursor and Codex. Local terminal browser `beacon traces`, read-only local dashboard `beacon endpoint dashboard`, and a local MCP server `beacon mcp serve` that the README says never touches the network.
- **Jev dependency (unverified)**: The X post says Beacon uses Jev to score which runs are worth learning from. The README does not mention Jev. Check whether the scoring step needs a TypeSafe key before any trial. If it does, the local path would be Laya `laya-serve` (Entry 086), not a key.
- **Fit on nimo**: The binary install is fine, but the default paths need care. Interactive setup signs in through beacon.sh and preselects Beacon Cloud; we must pick **Local** and not sign in. The Linux installer uses `sudo apt`/`dnf`, which is outside `~/DEVELOP` and needs Mark's approval. Upstream documents a user-mode tarball without root, which could live under `~/DEVELOP/pfy-mentat/tmp/`. The wizard also writes skills into `~/.agents/skills` and `~/.claude/skills` unless turned off; that is outside `~/DEVELOP` too and must be off.
- **Why it matters here**: pfy-mentat's self-improvement loop needs exactly this: a record of what Grok Build and the bots actually did, and a way to turn corrections into reusable skills. Compare against Hermes feedback loops (Entry 048, ported as `/hermes-feedback`) and Exo's event log before adopting anything.
- **Extracted Repos / Tools**: https://github.com/asymptote-labs/agent-beacon · https://docs.beacon.sh
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/typed-decisions-local/smoke.py --entry beacon`. It looks for `$BEACON_BIN` or `beacon` on PATH. Missing exits 2 with the user-mode note. Present runs `beacon --version` (falls back to `--help`) and records the output. This only proves the binary runs; it does not exercise capture or learning. Receipt: `pipelines/smoke/beacon/latest.json`.
- **Non-goals**: No sudo install, no Beacon Cloud, no sign-in, no skills written to `~/.agents` or `~/.claude`, no forwarding.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Cloud by default | Accepting the preselected Beacon Cloud forwards session history off nimo | Choose Local. If forwarding started, `beacon endpoint disconnect` (upstream command) and record it in the handoff |
| Writes outside DEVELOP | Wizard installs skills into `~/.agents/skills` / `~/.claude/skills` | Turn that off at install; undo with `beacon skills uninstall` |
| Smoke over-claims | `--version` passing gets read as "Beacon works" | The receipt says install-only. Capture and learning need their own trial slice |

- **Status**: STAY I0 after the 2026-11-07 evq probe on nimo. Pin v1.3.59 commit `f796c550f2be738fc210828826a653ef5ee8cffc` is in the cache only (tarball sha256 `eaf586d3b842c0a7437258a44efa6f813744feb8951616d52e4dcb1405cc74c3`). One planted session synced 9 events in 0.016s (4 of 4 markers). Scoring that trace calls hosted TypeSafe Jev and scored 0 traces here. Not installed into the real home. Report: `eval/evq1107/agent-beacon/REPORT.md`.
