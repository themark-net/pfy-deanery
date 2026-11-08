# HiRoute ev1107

PROMOTE I2. Routing was right on 20/20. Decision median was 746 ms, under the 2 s gate. Nothing was wired into `./pfy`.

## Pins

HiRoute 0.3.1, tag commit `13856abd873da5b4373d39322493b4cc105c4867`. Staged under `~/.cache/pfy/tools/hiroute/`. Re-hashed on this lane:

| File | sha256 |
| --- | --- |
| `hiroute-0.3.1-13856abd873d-x86_64-unknown-linux-gnu.tar.gz` | `dfa35ada12fcef9d0d2e10e680422cd0bf6a0454a8809c27879b74ba932d21aa` |
| manifest `.tar.gz.json` | `e7e313ac6d709ecaed9411f1c01121542d512f572bbe40542f8f2dd6a9474509` |
| `standalone.py` that was installed | `3a7ef92f0dd55119aa31b19877e3ac34dedcd5b4b32cbb012ef396b70649b7c2` |

All three match `sources/entries/147-hiroute.md`. The live download of `https://hiroute.ai/install/standalone.py` on 2026-11-07 hashed to `7fe4bd69ecfc362c96c79cbc6993c8797e2e166158310f302a34a2552363e221` and was not used. The installer in the v0.3.1 tag tree hashed to `ea1bd00efe8e86a1c27669bc7d7814da0afaa4bdd0050ae4ab32354b106b5db2` and was not used. Install used the pinned file and `--console-mode off`.

Archive is 64 MB. Installed lib is 40 MB and share is 52 MB, all under the cache home. None of that is committed.

## What ran

Trial `HOME` and `XDG_*` point at `~/.cache/pfy/tools/hiroute/home`. `XDG_RUNTIME_DIR` and `TMPDIR` point at the same cache tree. A `systemctl` stub on that `PATH` exits 1, so the user unit is not reported active. Console listener mode is `off`. Gateway is `127.0.0.1:43075`. After install, these real-home paths were absent: `~/.local/bin/hiroute`, `~/.local/bin/hirouted`, `~/.config/systemd/user/ai.hiroute.cli.service`, `~/.agents/skills/hiroute-management`, `~/.claude/skills/hiroute-management`.

The published alias is `hiroute-eval-difficulty-route`. Economy binding is `qwen2.5-coder:7b-instruct`. Primary binding is the loopback stub `premium-stub`. The decision service is a custom endpoint with no auth header: `http://127.0.0.1:44564/v1/decisions`. HiRoute selects economy when P(simple) is at least 0.8.

CLIProxyAPI is in the install and was not configured as a subscription proxy. No paid key and no hosted judge.

HiRoute 0.3.1 rejects a non-null `system_fingerprint` on a chat completion. Ollama 0.30.8 sends `fp_ollama`. A loopback shim on `127.0.0.1:44565` strips that field, fixes `usage.total_tokens`, and forwards `/v1/chat/completions` to `127.0.0.1:11434`. The economy source was updated to that shim before the locked run. The shim log shows 10 responses, all HTTP 200, model `qwen2.5-coder:7b-instruct`.

The premium stub on `127.0.0.1:44563` records the request and returns a chat completion whose content is `STUB_PREMIUM`. A first wiring call with a smaller body got HTTP 502 `UPSTREAM_ATTEMPT_FAILED`. The same call with `id`, `model`, `choices[].index`, `message.role` `assistant`, and `finish_reason` `stop` returned HTTP 200. That wiring call used a constant complex decider and did not call Ollama. The stub log has 11 hits: that wiring call plus the 10 hard prompts.

The client is `POST /v1/responses` with header `X-HiRoute-Token` read from the grant file. The grant value is not in this report and not in git. Body model is the alias, `stream` false, `max_output_tokens` 64.

## Commands

Hedge does not read the prompt. Trivial prompts are task `bulk`. Hard prompts are task `hard`. `--local ready` skips the detector, so this does not call Ollama. No `--record`. `PFY_STATE_DIR` keeps the ledger off `~/.pfy-mentat`.

```bash
PFY_STATE_DIR=eval/ev1107/hiroute/hedge-state \
  ./pfy hedge decide --task bulk --local ready --budget 100000 --json
PFY_STATE_DIR=eval/ev1107/hiroute/hedge-state \
  ./pfy hedge decide --task hard --local ready --budget 100000 --json
```

The live step is one lock hold, not one hold per prompt. Default `HOME` so the lock file is `~/.cache/pfy/locks/local-model.lock`.

```bash
scripts/model_lock.sh python3 -u eval/ev1107/hiroute/probe.py live
```

`ollama list` already had `qwen2.5-coder:7b-instruct` at 4.7 GB and `qwen3.6:35b` at 22 GB. This lane did not pull. The judge and the economical tier are the 7B coder. The 35B model is over the size this gate can afford: the decision budget is 2 s, and the ticket allows a smaller qwen coder.

At lock start, `ollama ps` was empty, so this lane loaded the 7B and sent `keep_alive` `2m` on each decision call. It did not call `ollama stop`. `MemAvailable` was 91582873600 bytes. The floor was model size rounded up plus 25 GiB, 31843545600 bytes. The live step did not wait and did not record HOST-BUSY.

## Numbers

Decision latency is the Ollama `/api/chat` time inside the decision adapter. Answer latency is the client total minus that time, so gateway time sits in the answer number. The first decision is 5712 ms and includes the model load. The other 19 are 654 ms to 768 ms. Median of all 20 is 746 ms. Minimum 654 ms. Maximum 5712 ms.

Economy answer median 183 ms. Primary stub answer median 44.5 ms. Every live HTTP status is 200. Route comes from the daemon diagnostic `native_model`. `qwen2.5-coder:7b-instruct` counts as economy. `premium-stub` counts as primary.

The deterministic check is case-sensitive. It passed 17/20. `t03` answered `Yes`, `t04` answered `Blue`, and `t10` answered `Ok`. The route on those three was still economy. `h07` has a blank diagnostic outcome in the per-prompt file. The daemon log for the whole process has 22 attempts: 21 `completed` and 1 `failed`. The failure is the earlier 502, before this set. `h07` still returned HTTP 200 and `STUB_PREMIUM`.

Hedge lanes: 10 trivial `local`, 10 hard `cloud`. HiRoute agreed on 20/20. Hedge never saw the text. Agreement means the text judge matched the label policy.

| id | route | decision ms | answer ms | route ok | check ok | hedge |
| --- | --- | --- | --- | --- | --- | --- |
| t01 | economy | 5712 | 257 | yes | yes | local |
| t02 | economy | 768 | 187 | yes | yes | local |
| t03 | economy | 753 | 180 | yes | no | local |
| t04 | economy | 758 | 185 | yes | no | local |
| t05 | economy | 755 | 196 | yes | yes | local |
| t06 | economy | 755 | 182 | yes | yes | local |
| t07 | economy | 763 | 182 | yes | yes | local |
| t08 | economy | 747 | 173 | yes | yes | local |
| t09 | economy | 747 | 184 | yes | yes | local |
| t10 | economy | 745 | 173 | yes | no | local |
| h01 | primary | 761 | 4 | yes | yes | cloud |
| h02 | primary | 663 | 44 | yes | yes | cloud |
| h03 | primary | 657 | 46 | yes | yes | cloud |
| h04 | primary | 654 | 44 | yes | yes | cloud |
| h05 | primary | 656 | 46 | yes | yes | cloud |
| h06 | primary | 655 | 44 | yes | yes | cloud |
| h07 | primary | 656 | 44 | yes | yes | cloud |
| h08 | primary | 656 | 45 | yes | yes | cloud |
| h09 | primary | 658 | 46 | yes | yes | cloud |
| h10 | primary | 655 | 45 | yes | yes | cloud |

Per-prompt JSON is `results.jsonl`. Prompts are `prompts.jsonl`.

## Gates

Value gate (needed for I3, recorded here, not claimed):

1. Gap fill: yes. `./pfy hedge decide` needs a bulk or hard label. HiRoute judged the message text and matched that label on 20/20.
2. Operator leverage: no. A working call needs a custom decision HTTP service, a unix-socket grant, a fingerprint shim, and a trial-home client registration. That is not a product lever.
3. Evidence: yes. This probe, with pins and commands above.
4. Blast radius: yes. Apache-2.0, loopback only, trial home, no subscription login, no key. The binary stays in the cache.

Score 3 of 4. This lane stops at I2.

Modularity gate (all 4 required for this I2 probe):

1. Local code needed: yes. The entry's decision example is a hosted judge. The local decision body and the fingerprint rejection showed up only by running the binary.
2. Bounded surface: yes. One pinned CLI and daemon. The probe published one route alias.
3. Isolatable: yes. The process uses the cache home. It is not the product runtime.
4. Reversible: yes. Delete `~/.cache/pfy/tools/hiroute`. The pin and the entry remain. `./pfy` does not call HiRoute.

The lightweight size gate would refuse a repo copy: the archive is 64 MB and the install is about 92 MB. The binary is not in the repo. The I2 claim is the ticket's numeric rule (at least 16/20 and median under 2 s), and the stage card keeps `tier_ceiling` at I1.

`uses` and `features` are routing, not CI, testing, or review, so `self_pipeline` is not set. No `TOOLS.md` row and no `data/tools.json` row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Installer reach | A real-home install writes skills and a user unit | Trial home only. The real paths above were absent |
| Hosted judge | The documented decision endpoint is a paid cloud | This probe used local Ollama. A bad or missing ordinal body falls back to primary |
| Fingerprint | Direct Ollama chat completions get HTTP 502 after a full body | Shim strips `system_fingerprint`. If the shim is down, economy fails closed to an error, and the route is still visible in diagnostics |
| Subscription proxy | CLIProxyAPI can reuse a coding-subscription login | Not configured. Any subscription use needs a separate go-ahead |
| Listener | A non-loopback bind exposes the gateway | Verified `127.0.0.1` and console mode `off` |
| Cold decision | The first judge call was 5712 ms while the model loaded | Median stayed 746 ms. A later gate that must beat 2 s on every call, including the first, has to find the model already loaded |
| Answer case | The 7B capitalized three expected tokens | Score the route from `native_model`. Do not fail the route on case |
| Grant file | The gateway token is a secret on disk | Mode 0600 under the cache. Not printed, not committed |
| Host memory | Loading a model without 25 GiB free on top of its size can crowd other lanes | The lock checks `MemAvailable`. On a miss it waits up to 30 min, then records HOST-BUSY and skips the live calls. This run did not hit that path |

## Next gate

Do not wire HiRoute into `./pfy`, pregate, or CI. The card ceiling stays I1. A later ticket has to grill any gate wiring and decide whether the ceiling moves. Until then this I2 is the cache probe only.

## Pipeline questions

How HiRoute would run if a later ticket put it in the pipeline. This lane did not add that path.

1. What triggers it? A client request to the loopback gateway for the published route alias. Not a CI job.
2. What does it do, and which services does it read and write? It reads the user message, asks the local decision model, and sends the turn to Ollama or the primary tier. It reads Ollama on `127.0.0.1:11434` and its own daemon state under the trial home. It does not write the repo or a hosted model.
3. What does it trigger next? The chosen model answers the client. It does not start a test, a review, or a land step.
4. Where does a human re-enter? Before any gate wiring, any subscription proxy, or any install into the real home.
5. What stops two runs doing the same work? One daemon publication for the route, and `scripts/model_lock.sh` for any live Ollama use. This lane held that lock once for all 20 prompts.
