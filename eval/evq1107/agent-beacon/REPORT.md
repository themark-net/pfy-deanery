# agent-beacon evq1107

STAY I0. One planted Grok session synced into a local JSONL: 4 of 4 correction markers, 9 events, 0.016s, 0 malformed. A second sync emitted 0 events. Scoring that trace is a hosted TypeSafe Jev call. With no key, inside a network namespace, it scored 0 traces (exit 1, 0.014s). The one approved memory row is text this probe typed. The extracted bundle is 236037920 bytes, over the 50 MB lightweight bar. It does not beat skill-up on a repeatable score, and it does not beat the Hermes feedback skill on a lesson a person accepts.

`STAY I0 4 of 4 markers captured in 0.016s, 0 of 1 traces scored offline, bundle 236037920 bytes`

## Catalog overlap

The job is H1: a repeatable score, plus memory and context. The reason this tool is in the lane is session history turned into reusable knowledge. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07 section and the 2026-10-06 table) and the batch-1 verdicts under `eval/ev1107/` and `eval/catchup-1107/`. This lane builds no pipeline, CI, or gate step.

| Tool | Stage | Why it covers this job | How Agent Beacon compares |
| --- | --- | --- | --- |
| skill-up | I3 | Grade a with-skill run against a no-skill baseline. Catch-up verdict: both arms 5/5, delta 0, flake 0/10. | Dry-run priced 1 trace at 0.00035 USD and would call Jev. The live call scored 0 traces. |
| Hermes Agent (feedback loops) | I1 | Feedback-loop pattern ported as a skill. Not the Hermes runtime. | Same shape: a person accepts a lesson. This probe stored 1 row only because the script wrote the body. The skill is already in the tree. |
| neatroots | I2 | Offline rule checks on saved traces. Found a real repeated-call streak on pfy traces. | Sync made 9 events. neatroots was not re-run. Beacon added no rule finding. |
| Grok CLI bootstrap | I3 | Operator env and the sessions Grok already writes. | The fixture matches that session shape. Sync copied it. It did not add a score. |
| opencode-mem | I1 | Memory plugin for the OpenCode worker. | Different surface. Not run. |
| codebase-memory-mcp | I2 | Primary code-graph MCP. | Code structure, not session lessons. |
| MemPalace | I0 | Verbatim local memory. Post-MVP bake-off. | Not run. Beacon listed the one typed row. |
| RoBrain | I0 | Decision memory. Needs Postgres. | Not run. |
| Memvid | I1 | Video-backed memory. No current operator job. | Not run. |
| LEANN | I1 | Compressed RAG. Not our code memory. | Not run. |
| Chroma (or LanceDB) | I0 | Vector store. Code memory is already chosen. | Not run. |
| Exo (exoharness) | I1 | Pattern extract. The entry names its event log. Unsafe as a runtime. | Not run. Different log. Not adopted. |
| agentplay | I0 | Session replay map. Card says no Grok transcript reader. | This sync read a Grok-shaped fixture (4 prompts). agentplay was not run. |
| Tracekit | I0 | Signed tool-call records. Post-MVP. | Not run. |
| imcodes | I0 | Reference for final-answer memory. Not an install. | Not run. |
| MUE-X | I1 | Self-rewriting agent. Unsafe as a runtime. | Not run. |

The 2026-11-07 ranking gives H1 to skill-up (entry 146): a with/without score. Beacon does not grade a case set offline. Gap H1 stays with skill-up.

Beats what we have: no.

## Pins

The entry records no commit and no checksum. The pin is the release that was current on this run.

| Piece | Value |
| --- | --- |
| Repo | https://github.com/asymptote-labs/agent-beacon |
| Release | v1.3.59 |
| Tag object | `b15fcc7890e20a47312fd2a197d197f455d7c462` |
| Commit | `f796c550f2be738fc210828826a653ef5ee8cffc` |
| `beacon version` | `beacon version 1.3.59 (f796c550) built on 2026-11-08T03:14:49Z` |
| Tarball | `beacon_1.3.59_linux_amd64.tar.gz` |
| Bytes | 89394071 |
| sha256 | `eaf586d3b842c0a7437258a44efa6f813744feb8951616d52e4dcb1405cc74c3` |
| Signature | `checksums.txt.sig` valid for fingerprint `07BEA34ED6A411F4C066D98322F94195DCDC8F45` |
| License | MIT, copyright 2026 Asymptote Labs, at that commit |
| Extracted files | 236037920 bytes |
| `beacon` | 46149792 |
| `beacon-hooks` | 10854560 |
| `beacon-otelcol` | 30736544 |
| `beacon-vector` | 148260448 |
| Account | none |
| Skills install | not run |
| Endpoint service | not installed |
| Jev | SKIPPED. Default host `https://api.typesafe.ai/v1/systemone`. No key. Laya not started. |

The three binaries the install guide says are required (`beacon`, `beacon-hooks`, `beacon-otelcol`) sum to 87740896 bytes. That is already over 50 MB. `beacon-vector` is extra and was not executed.

## Commands

Install and the probe used dirs under `~/.cache/pfy/tools/agent-beacon/`. The probe sets `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` inside `bwrap --unshare-net`. The real home is not mounted. These names are unset in the child: `TYPESAFE_API_KEY`, `BEACON_JEV_API_KEY`, `BEACON_JEV_ENDPOINT`, `BEACON_JEV_MODEL`, `BEACON_EVALUATOR`, `SUBQ_API_KEY`, `BEACON_SUBQ_API_KEY`, `BEACON_SUBQ_ENDPOINT`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and the proxy variables. No model lock. `ollama` was not called.

```bash
BASE=/home/mark/.cache/pfy/tools/agent-beacon
mkdir -p "$BASE/dist"
cd "$BASE/dist"
VER=1.3.59
ARCHIVE="beacon_${VER}_linux_amd64.tar.gz"
BASEURL="https://github.com/asymptote-labs/agent-beacon/releases/download/v${VER}"
curl -fsSL -o checksums.txt "${BASEURL}/checksums.txt"
curl -fsSL -o checksums.txt.sig "${BASEURL}/checksums.txt.sig"
curl -fsSL -o beacon-release-key.gpg "${BASEURL}/beacon-release-key.gpg"
curl -fL --retry 3 -o "$ARCHIVE" "${BASEURL}/${ARCHIVE}"
grep "  ${ARCHIVE}$" checksums.txt | sha256sum --check -
# gpgv against fingerprint 07BEA34ED6A411F4C066D98322F94195DCDC8F45: gpg-ok
tar -xzf "$ARCHIVE" -C "$BASE/extract"
```

Download wall clock was about 7s (19:32:47 to 19:32:54 local). `sha256sum --check` printed OK.

The measurement is:

```bash
python3 eval/evq1107/agent-beacon/probe.py
```

That writes a four-prompt fixture under the cache, runs `beacon endpoint grok sync --json` twice, then `beacon memory evaluations run --dry-run`, then the same command without `--dry-run`, then `candidates create`, `candidates approve`, and `memory list`. Counts are in `results.json`.

## Numbers

| Step | Exit | Seconds | Result |
| --- | --- | --- | --- |
| `beacon version` | 0 | 0.013 | 1.3.59 (f796c550) |
| sync, first | 0 | 0.016 | 1 session, 9 events, 0 errors, 0 malformed |
| sync, second | 0 | 0.011 | 0 events emitted |
| evaluations `--dry-run` | 0 | 0.013 | 1 trace, 1 estimated call, 0.00035 USD |
| evaluations live, no key | 1 | 0.014 | SKIPPED. DNS to `api.typesafe.ai` failed inside the empty net namespace |
| candidates create + approve | 0 | 0.021 + 0.018 | 1 candidate, then 1 approved row |
| memory list | 0 | 0.013 | 1 row, and it contains the typed marker |

Log lines: 9. All 9 have `harness.collection_method` `poll`. Actions: `prompt.submitted` 4, `session.started` 1, `session.context` 1, `agent.message` 1, `tool.invoked` 1, `command.executed` 1. Each planted marker appears once.

The dry-run reason string is `explicit evaluation command; hooks and collectors do not call Jev`. The entry's Jev note is confirmed for v1.3.59: the score step defaults to Jev at the hosted TypeSafe System One URL and looks for `TYPESAFE_API_KEY`, then `BEACON_JEV_API_KEY`. The catalog-time README did not name Jev. This binary does.

Automatic knowledge items from the 4 corrections: 0. Typed approved memories: 1 of 4, body supplied by the probe. The other three markers stayed in the log only.

The fake home gained one file, `.beacon/endpoint/state/session-sweep.lock`. No skills directory. No Grok hook file. `beacon endpoint install`, `beacon login`, and `beacon skills install` were not run.

## Gates

Value gate (3 of 4 for I3):

| Check | Result |
| --- | --- |
| Gap fill | No. skill-up already scores a case set offline. The Hermes feedback skill already holds a lesson a person accepts. Grok already stores the session. |
| Operator leverage | No. The copy works in one command. The score this gap asks for does not run without a hosted key. |
| Evidence | Yes. User-mode tarball runs. `probe.py` is the receipt. |
| Blast radius | No. 236037920 byte extract, a wizard that preselects Beacon Cloud, and skills plus Grok hooks that write outside the repo. |

1 of 4.

Modularity gate (all 4 for I2):

| Check | Result |
| --- | --- |
| Local code needed | Yes. The entry did not show the default Jev host or that a typed candidate stores without a key. |
| Bounded surface | No. The install unit is four binaries and 236037920 bytes. |
| Isolatable | Yes. Cache path plus `bwrap`. No collector process left running. |
| Reversible | Yes. Delete the cache. The pin and the entry remain. |

The lightweight size gate for an I2 copy is a working tree under 50 MB and no large binaries. This bundle fails both. I2 is not open. I3 is not open: no repeatable onboard script, and the value gate is 1 of 4.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Cloud by default | Accepting the wizard forwards session history | This lane did not run `endpoint install` or `login`. Do not pass `--connect`. If a later run connects, `beacon endpoint disconnect` and record it. |
| Skills outside the repo | `beacon skills install` writes `~/.agents/skills` and `~/.claude/skills` | Not run. Keep it off. Undo only inside a redirected HOME with `beacon skills uninstall`. |
| Grok hooks in the real home | `endpoint hooks install --harness grok` writes `~/.grok/hooks` | Not run. The probe passed `--sessions-dir` and did not mount the real home. |
| Score posts the trace | `memory evaluations run` without `--dry-run` POSTs to `api.typesafe.ai` | No key was set. The call died at DNS inside `--unshare-net` (connection refused to `[::1]:53`), so the trace was not sent. Keep the namespace until a later ticket names a local System One. |
| Cursor deleted | A fresh state file makes sync append the same 9 events again | Keep the state file. The second sweep emitted 0 while it was present. |
| Version treated as knowledge | `beacon version` exit 0 gets read as the learning loop | The receipt splits capture (4 of 4) from scored traces (0). |

## Next gate

Stay I0. Re-open only if a later ticket points `beacon memory evaluations run` at an already running local System One and that ticket allows the model lock. No cloud sign-in, no skills install, no Grok hooks in the real home, no gate, and no Feature GO.

## Five questions

How this tool would run in the pipeline:

1. What triggers it? Nothing in this repo calls Beacon. A person would run `beacon endpoint grok sync` on a sessions directory under the cache.
2. What does it do, and which services does it read and write? It reads that sessions directory. It writes `runtime.jsonl`, a cursor file, and `memory.db` beside the log. The score step would POST to `https://api.typesafe.ai/v1/systemone`. This lane did not complete that call.
3. What does it trigger next? Nothing. A person can run `beacon memory list`. No gate is wired.
4. Where does a human re-enter? At `candidates approve`. The evaluator does not write the lesson. This probe typed the body.
5. What stops two runs doing the same work? The cursor file. The second sync emitted 0 events for the same session. One cache directory. Do not start a collector.
