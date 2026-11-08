# HarnessRouter evq1107

## Catalog tools on this job

The job is gap L: local inference on this host, plus one self-hosted API in front of the harnesses that would call it. HiRoute is the named comparison. These cards already cover that job.

| Tool | Stage | What that card covers | How HarnessRouter compares |
|------|-------|----------------------|----------------------------|
| Ollama | I2 | Local OpenAI-compatible server. `make smoke-litellm-ollama` checks it. | The engine this gap is missing a second of. HarnessRouter ships 0 weight files and serves 0 tokens. |
| Strata | I2 | Second local engine. 2026-11-07 trial: median decode 51.86 tok/s vs Ollama 61.71 (0.84x), 18/18 valid. | An engine with a measured rate. HarnessRouter is a harness front door. |
| llama.cpp (server mode) | I1 | GGUF server already in the pfy up order. | Another engine path. This probe did not start one. |
| LiteLLM | I2 | One OpenAI-compatible proxy for Grok and local models. Smoke path exists. | Already the proxy in front of a local base URL. |
| HiRoute | I2 | Difficulty router. ev1107: 20/20 routes, decision median 746 ms, local judge, loopback gateway. | Already measured at sending cheap turns to a local model. |
| magpie | I0 | One gateway config for every agent. Needs a later GO. | Same "one config" shape, still awareness. |
| Open WebUI | I1 | Chat UI for local models. Docker. | A UI, not a harness protocol. |
| Continue.dev | I1 | IDE recipe pointed at the local OpenAI base. | A client of a local base URL. |
| Antigravity-Manager | I1 | Account-pool proxy. LiteLLM plus keys is the default. | A key pool. This lane used no key. |
| harness2 | I1 | Local harness edit trial with its own llama-server. Held-out gain was 0. | A harness trial that already sits on a local engine. |

HarnessRouter does not beat Ollama, Strata, LiteLLM, or HiRoute on gap L. The pinned tree maps a custom connection onto a caller base URL for 23 of 26 default backends. That is a source count. This lane observed 0 completions.

## Verdict

STAY I0. 0 weight files and 0 engines. Of 26 default backends, 15 custom rows target `openai-api` (chat completions, the shape Ollama, llama-server, and Strata serve) and 8 target `tokenrouter` (a caller base URL; the codex row is the Responses API). gemini, systemone, and qoder have no custom row. The pinned image reached ready in 1.186 s and a keyless POST got 401. No task ran. Nothing is wired into a gate.

## Pin

Tag `v0.34.2`, commit `0c43dc333abb1db1954bb36e8dc712724af7550b`, committed 2026-10-16 10:55:07 -0700. GitHub release `v0.34.2` has 0 assets. Docker Hub tag `0.34.2` digest is `sha256:db412234ea41162e70ecf92f0140402f7cf1fc2a7e00db9180906c7447eb9ad5`, the same digest `examples/x-intake-local/smoke_122_124.py` pins. Hub lists the amd64 image at 805646717 bytes. `docker image inspect` on the pulled image reported `Size` 805671098 and id `sha256:db412234ea41162e70ecf92f0140402f7cf1fc2a7e00db9180906c7447eb9ad5`.

Checkout is `~/.cache/pfy/tools/harnessrouter/src` (not committed). 633 files, 40742048 bytes without `.git`. The clone directory with `.git` is 69153700 bytes. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` for the clone were directories under that cache. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`.

```bash
BASE=$HOME/.cache/pfy/tools/harnessrouter
mkdir -p "$BASE/home" "$BASE/config" "$BASE/cache" "$BASE/tmp" "$BASE/src"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache" TMPDIR="$BASE/tmp"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git clone --depth 1 --branch v0.34.2 https://github.com/HarnessRouter/harnessrouter.git "$BASE/src"
```

The image was pulled by digest, run once, and removed. It is not left in the shared docker store.

```bash
docker pull harnessrouter/harnessrouter@sha256:db412234ea41162e70ecf92f0140402f7cf1fc2a7e00db9180906c7447eb9ad5
```

Pull command duration was 58.91 s.

## Probe

Offline count, from this worktree:

```bash
python3 eval/evq1107/harnessrouter/probe.py \
  --src "$HOME/.cache/pfy/tools/harnessrouter/src" \
  --out eval/evq1107/harnessrouter/results.json
```

Exit 0. It reads `gateway/app.py` (`_INTEGRATION_WIRING`), `runner/server.py` (`*_PROVIDERS`), and the default `HR_BACKENDS` line in `docker/entrypoint.sh`. A missing tree exits 2 and writes nothing. `python3 -m unittest tests.test_harnessrouter_probe` drives that with a temp fixture (no network, no docker, no cache checkout). The `pin` and `live` objects in `results.json` were added after that run. Running the probe again replaces the file with the count object only.

| Count | Value |
|-------|------:|
| Default backends | 26 |
| Custom row target `openai-api` | 15 |
| Custom row target `tokenrouter` | 8 |
| No custom row | 3 (gemini, systemone, qoder) |
| Provider set contains `openai-api` | 21 |
| Provider sets | 27 (gajae is extra and not in the default list) |

The 21 provider sets are the 15 custom `openai-api` rows plus pi, dsh, opencode, kilo, omp, and mimo. Those six list `openai-api` in the runner set and use `tokenrouter` as the custom-row target. Claude and codex are the other two `tokenrouter` rows, and their provider sets do not list `openai-api`.
| Weight files (`.gguf`, `.safetensors`, `.onnx`, `.pt`, `.pth`, or any file >= 20 MB) | 0 |
| Engines added | 0 |

Names are in `eval/evq1107/harnessrouter/results.json`. The 15 `openai-api` rows are the ones that match a chat-completions base URL. The 8 `tokenrouter` rows also carry a caller base URL. Codex's comment in the wiring says that target speaks the OpenAI Responses API. This probe did not send either shape to a stub.

## Live boot

`HR_BACKENDS=none`, so `install_backends` did not download a harness CLI. Publish was `127.0.0.1:39217` to container port 3000. The data dir was a bind mount under the cache. The console password was a random value in a mode 600 env file under the cache. That file was deleted after the run. It is not in this report and not in git. The container name was `pfy-evq-hr-1107`.

| Check | Result |
|-------|--------|
| Ready after process start | 1.186 s |
| Log lines | 9 |
| Lines that mention installing | 0 |
| Backends available | none |
| `GET /` | 200 |
| `POST /api/harness/v1/responses` with no key, body `{"model":"none","input":"ping"}` | 401 |
| Volume bytes before wipe | 73728 |
| Task | SKIPPED |

The task is SKIPPED. A task needs a harness CLI, and the image installs those on first start from upstream releases. This lane did not download them and did not send a prompt. The container, the volume, and the image were removed after the numbers were recorded. No other container was stopped.

## Gates

Value gate, 1 of 4. I3 needs 3.

1. Gap fill. Not met. Ollama, Strata, LiteLLM, and HiRoute already cover a local engine and a local route. This probe added 0 engines and 0 tokens.
2. Operator leverage. Not met. Ready in 1.186 s with no backends does not give a local completion. A real task still means a CLI download plus a base URL, and that path was not run.
3. Evidence. Met. The digest-pinned image booted on loopback and refused a keyless call with 401, which is the smoke's expected refusal. The wiring count is repeatable from the pinned tree.
4. Blast radius. Not met for a default runtime. Apache-2.0 is fine. The runnable image is 805671098 bytes, over the 50 MB I2 copy limit. The entrypoint runs as root so it can install CLIs. The README's full set is about 4 GB of those CLIs. This lane did not make it the product runtime.

Modularity gate, 3 of 4. I2 needs all 4, and the image is over the lightweight limit.

1. Local code needed. Met. The README quickstart asks for a provider key. The pinned `.env.example` and the wiring table are what show a caller `base_url`. The boot is what shows the keyless refusal.
2. Bounded surface. Not met. One image, and inside it 26 default backends with their own installers. That is the unit that would have to be evaluated for a task.
3. Isolatable. Met. Cache checkout plus a removed image. It is not the product runtime.
4. Reversible. Met. Deleting the cache checkout leaves the entry, the card, and this report. The image was already removed.

I3 would also need `self_pipeline` evidence. This lane wires no gate. The card stays I0. Potential is low for gap L.

## Risks

| Risk | How it fails | How we recover |
|------|----------------|----------------|
| Tag moves | `latest` is not this digest | Pull `sha256:db412234ea41162e70ecf92f0140402f7cf1fc2a7e00db9180906c7447eb9ad5` |
| Default `HR_BACKENDS` | First start downloads every harness CLI | Set `HR_BACKENDS` to a name this lane used: `none` |
| Default console password | The published default is in the README | This run set a random password, bound `127.0.0.1` only, and deleted the env file |
| Wiring count read as a live forward | 15/26 is a source row, not a stub hit | Stay I0 until a later ticket records one completion |
| Root-owned volume | The mount was uid 10001 and mode 750 | Wipe it from a container. Do not sudo. This lane removed it |
| Keyless call treated as success | 401 is the refusal | A task is still SKIPPED |

## Next gate

Stay I0. A later ticket can grill one stub completion through a single `openai-api` backend against the LiteLLM and HiRoute paths. No pregate, CI, or other gate wiring in this lane.

## Five questions (this tool in the pipeline)

1. What triggers it? A person starts the pinned image when a harness comparison needs one HTTP API. This lane adds no trigger.
2. What does it do, and which services does it read and write? It reads the image and, on a real task, a provider base URL. It writes `/data` (SQLite, blobs, and any CLIs it installs). This lane wrote 73728 bytes and then deleted them. No hosted model and no account.
3. What does it trigger next? Nothing in this lane. A task would start one harness CLI. That handoff is not built.
4. Where does a human re-enter? Before any harness CLI install, before any port that is not loopback, and before any provider key is stored.
5. What stops two runs doing the same work? One container name and one data directory. This lane used `pfy-evq-hr-1107` and removed it. The catalog card is only `data/stages/harnessrouter.json`.
