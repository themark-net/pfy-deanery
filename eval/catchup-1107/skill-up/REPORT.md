# skill-up catch-up trial (2026-11-07)

## What ran

skill-up v0.14.0 (binary sha256 `5b1bdd0a30f57653c8f6a3a679e992b29982fe18709b2556d53a6f9ea1c85ab6`, tarball sha256 `307f2082ce5489c61f6a01ce6c78225dfd3974b4b54227426b87e1b6330dbfc9`). Engine `pfy-local` is `eval/catchup-1107/skill-up/engine_local.py`. It runs `opencode run` in the case workspace against local Ollama `qwen3.6:35b` through a loopback proxy. OpenCode was on PATH (1.18.32). The with-skill arm installs `bootstrap/grok-cli/skills/karpathy-guidelines`. That skill says to edit only the lines the task names and to keep the existing function. These cases fail if the function is renamed or left with the seeded bug.

Five cases, script judges, baseline on, two iterations, parallelism 1. About 20 seconds a case. The recorded run took about 7 minutes. Reports are under `tmp/skill-up-reports` (gitignored). `summary.json` is the committed score.

The proxy forces temperature 0, seed 230, and `reasoning_effort: none`. On Ollama 0.30.8, `think: false` alone left `content` empty and filled `reasoning`. `reasoning_effort: none` returned the answer.

A loopback probe (no real model) showed the repo `AGENTS.md` text was not in the request. The with-skill arm listed `karpathy-guidelines`. The without-skill arm did not. OpenCode does not paste the skill body until the model calls the skill tool.

## Numbers

Recorded run, MemAvailable 87031072 KiB before load. skill-up exit 0. 20 grades, 0 errors.

| Arm | Iteration 1 | Iteration 2 |
|-----|-------------|-------------|
| with karpathy-guidelines | 5/5 | 5/5 |
| without a skill | 5/5 | 5/5 |

Flake 0/10. Pass-rate delta 0.00. Script evidence included `span ok` and `clamp ok` (the hidden clamp checks live only in the judge).

An earlier pass in this same session graded 16/20 and then stopped. MemAvailable had fallen to 48822384 KiB, under the 47 GiB pre-load gate, while `qwen3.6:35b` was already resident. Those four grades were HOST-BUSY errors, not model failures. The adapter now applies the 47 GiB gate only when that model is not already loaded. The table above is the rerun after that fix.

## Verdict

PROMOTE I3. skill-up ran the cases end to end, wrote a with/without baseline, and the repeat was stable enough to read. The skill arm did not beat the plain arm. On this set the model fixed every seeded bug either way. That is a ceiling, and it is still a readable comparison.

## Risks

The case set cannot show a skill gain until a task fails without the skill. `keep_alive: 2m` is sent only when `/api/ps` `expires_at` matches the marker from our last request, so a stale marker does not refresh someone else's copy. If `/api/ps` cannot be read on the real Ollama URL, the adapter does not call the model. Judge scripts are copied under `/tmp/skill-up-judge-*` even when TMPDIR is set. They were removed when the run ended. Bash is allowed inside the case workspace, so a model can still read a parent file if it tries. This is not a Feature GO.

## Next gate

Use the same cases and adapter to score a pfy run against a plain Build run, or add cases the plain arm fails. Stay I3 until one of those comparisons is the thing being measured. Do not promote to I4 from this receipt.
