# aider evq1107

Verdict: STAY I1. `aider-chat` 0.86.2 committed one correct edit on a 2-line fixture. `add(2, 2)` became 4, the line is `return a + b`, and git added 1 commit. Aider's own clock was 7.6536 s. The locked probe wall was 13.52 s. Gap B stayed 0. The venv is 568274598 bytes (`du -sb`), over the 50 MB copy bar. OpenCode through `./pfy build --local` already does this job. It does not beat what we have. Nothing was wired into a gate.

`results.json` field `status` is `pass` for that one fixture. That is the edit score. It is not a promotion.

## Catalog comparison

The job is gap B from the 2026-11-07 ranking: `./pfy build` is not proven bot-usable (3 h timeout, recheck parked). This tool is a headless git editor with a local model. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07 section and the 2026-10-06 table). Batch-1 notes under `eval/ev1107/` and `eval/catchup-1107/` do not install aider. The closer measured editor is OpenCode, in the local-build handoff and in `eval/catchup-1107/skill-up/`.

There is no `sources/entries` file for aider. The catalog row is the TOOLS.md line. This lane did not edit TOOLS.md.

| Card | Stage | What it already covers | How aider compares |
| --- | --- | --- | --- |
| `./pfy build --local` | first-party, no card | Headless OpenCode edit, test gate, one commit on PASS. Post-fix rerun 8/8 in 608 s on `qwen3.6:35b` (`docs/ops/HANDOFF-pfy-local-build-mvp.md`). | Same job. This probe was 1/1 on a smaller file, 7.6536 s, `qwen2.5-coder:7b-instruct`. It does not touch the 3 h timeout. |
| skill-up | I3 | `opencode run` against Ollama. Recorded run 5/5 and 5/5, about 20 s a case (`eval/catchup-1107/skill-up/REPORT.md`). | That path already lands the seeded fix. Aider is a second editor. |
| harness2 | I1 | Local edit trial on sandboxed OpenCode. | The editor is already OpenCode. |
| Grok CLI bootstrap | I3 | Operator sessions and skills. | This probe did not call Grok. Grok is the hosted monitor, not the local editor. |
| Continue.dev | I1 | IDE recipe. The card says not to exec it. | Aider is a CLI. Continue is not the headless path. |
| opencode-mem | I1 | Memory plugin for the OpenCode worker. | Memory for the editor we already run. |
| kanbots | I1 | Kanban that fans CLIs into worktrees. The 2026-11-07 probe dispatched 0 of 11 CLIs. | Aider would be one more CLI on that board. The board did not move the timeout. |
| overtime | I0 | Wake layer for an ACP agent. Usable backends were 0. | Aider did edit. Overtime did not. Neither closed gap B. |
| AgenC | I0 | Daemon coding agent. The card says not to run it as the operator. | Same shape: a second coding CLI. |
| Reasonix | I0 | DeepSeek-native coding agent. Comparison only. | Not installed here. |
| gitai | I0 | CAS lands for many agents on one branch. | Not an editor. |
| ponytail (skills pack) | I1 | Skill pack already on the path. Tag `#coding-agent`. | A skill, not a git editor. |

The 2026-11-07 ranking says no entry from 137 to 167 closes gap B. Aider is older than that range. The 2026-10-06 table does not pick it as a next install. The local editor in that table is the llama-server lane and the OpenCode worker.

## Pins

| Item | Value |
| --- | --- |
| Package | `aider-chat==0.86.2` |
| Git tag | `v0.86.2` at `253f0368b873ba30d8ee26e463718f0c03614ddf`. `__version__` on that commit is `0.86.2`. |
| Wheel | `aider_chat-0.86.2-py3-none-any.whl`, 377009 bytes |
| Wheel sha256 | `64f6a0c66c9f4633ad9f479bca3e64ebcba02b9da03c6b604b74a44736b2416e` (rechecked with `sha256sum`) |
| Requires | Python `>=3.10,<3.13` |
| Interpreter | CPython 3.12.12 already present under `~/.local/share/uv/python/`. `aider --version` printed `aider 0.86.2`. |
| License | Apache-2.0 (tag `LICENSE.txt` header, PyPI classifier Apache Software License) |
| Venv `du -sb` | 568274598 bytes. Whole cache dir `du -sb` 602526028 bytes. |
| Probe `venv_bytes` | 651702798. That sum uses `stat` per file. The size gate uses `du -sb`. Both are over 50 MB. |
| Model | `qwen2.5-coder:7b-instruct`, on disk, 4683087561 bytes (`/api/tags`). Not pulled. |
| Install | `~/.cache/pfy/tools/aider/venv`. Nothing from the install is in git. |

No account and no key. `--no-analytics` on every aider process. `HOME` for those processes was the cache home. `/home/mark/.aider` was absent before and after.

## Commands

Offline install and an `--exit` smoke (no prompt, no model lock). The smoke took 3.16 s. It wrote `~/.cache/pfy/tools/aider/home/.aider/` including a 3481599 byte litellm price cache. `LITELLM_LOCAL_MODEL_COST_MAP=True` was set. The file still downloaded. It stayed under that home.

```bash
BASE=$HOME/.cache/pfy/tools/aider
mkdir -p "$BASE/home" "$BASE/config" "$BASE/cache" "$BASE/tmp" "$BASE/uv-cache" "$BASE/dl"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache" \
  TMPDIR="$BASE/tmp" UV_CACHE_DIR="$BASE/uv-cache" UV_LINK_MODE=copy \
  LITELLM_LOCAL_MODEL_COST_MAP=True
curl -fsSL -o "$BASE/dl/aider_chat-0.86.2-py3-none-any.whl" \
  https://files.pythonhosted.org/packages/75/f7/e20749d9a510673e7adf910b005e3efe4ceaf9c194f1dd40d6931a3f34b9/aider_chat-0.86.2-py3-none-any.whl
sha256sum "$BASE/dl/aider_chat-0.86.2-py3-none-any.whl"
uv venv --python ~/.local/share/uv/python/cpython-3.12.12-linux-x86_64-gnu/bin/python3.12 "$BASE/venv"
uv pip install --python "$BASE/venv/bin/python" "$BASE/dl/aider_chat-0.86.2-py3-none-any.whl"
```

The scored run used the real `HOME` for `scripts/model_lock.sh` so the lock file stayed `~/.cache/pfy/locks/local-model.lock`. The probe sets the child `HOME` itself.

```bash
scripts/model_lock.sh python3 eval/evq1107/aider/probe.py live \
  --work "$BASE/work" \
  --out eval/evq1107/aider/results.json \
  --home "$BASE/home" \
  --gitconfig "$BASE/empty-gitconfig"
```

Before the lock, `/api/ps` was `{"models":[]}` and MemAvailable was 78833096 KiB. Model size 4683087561 plus 25 GiB is under that, so the probe loaded the model. The load request sent `keep_alive: "2m"`. Aider's own calls do not send `keep_alive`. After the run, `/api/ps` showed `qwen2.5-coder:7b-instruct` with `context_length` 8560 and `expires_at` `2026-11-07T20:30:43.491057802-08:00`. This lane did not call `ollama stop`.

The fixture repo was `$BASE/work`, not this worktree. `git status` here stayed limited to the new eval files and the test.

Stub tests, no network and no aider binary:

```bash
python3 -m unittest tests.test_aider_probe -v
```

## Numbers

| Check | Result |
| --- | --- |
| Fixture before | `return a - b`. `add(2, 2)` is 0. |
| Asked edit | `return a + b` only. Prompt is `eval/evq1107/aider/message.txt`. |
| `correct_edits` | 1 |
| `add(2, 2) == 4` | true |
| `new_commits` | 1 |
| `git_edit` | 1 |
| aider exit | 0 |
| aider seconds | 7.6536 |
| locked wall | 13.52 s (`/usr/bin/time`) |
| tokens | 680 sent, 20 received (aider's line) |
| edit format | whole |
| commit subject | `fix(mathutil.py): correct addition operation` |
| commit trailer | `Co-authored-by: aider (ollama_chat/qwen2.5-coder:7b-instruct) <aider@aider.chat>` |
| author | `Aider Probe`, from the fixture repo's local identity |
| `model_loaded_before` | false |
| `keep_alive_sent` | true |
| `host_busy` | false |
| gap B | 0. `./pfy build` was not run. |
| context | 8560. This was not a repo-sized edit. |

The worktree file `eval/evq1107/aider/fixtures/mathutil.py` is still the broken line. The fixed text is only in the cache repo and in `results.json`.

## Gates

Value gate, 2 of 4. Short of I3.

1. Gap fill. Not met. Gap B stayed 0. `./pfy build --local` and the skill-up OpenCode run already commit local edits.
2. Operator leverage. Not met. One 2-line commit in 7.6536 s does not make the build lane bot-usable. Adopting aider would be a second coding CLI, which the card already lists as a non-goal.
3. Evidence. Met. The pinned wheel ran under the model lock and the stub tests pass.
4. Blast radius. Met for this wording. Apache-2.0, no model weights in the venv, and this lane did not make aider the product runtime. The copy is still too big for an I2 checkout. See the size gate below.

Modularity gate, all four hold for a cache probe. That does not promote the card.

1. Local package needed. Met. The commit, the whole-file edit, and the analytics file are host behavior.
2. Bounded surface. Met. One `aider` bin. This probe used `--message-file` and `--yes-always`.
3. Isolatable. Met. Cache venv plus a redirected home. It is not the product runtime.
4. Reversible. Met. Deleting the cache directory leaves the TOOLS.md row, the card, and this report.

I2 needs a probe that measurably helps while potential is still open, and a copy under 50 MB. The edit works, and the job is already covered, so potential is low. The venv is over 50 MB. Stay I1.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| `--yes-always` commits the model diff | A wrong edit becomes a commit on whatever repo is current | This probe used a cache repo. Point aider at a throwaway worktree. Read the diff before trusting it. |
| Default analytics | A share of runs phone home and write `~/.aider` | Pass `--no-analytics`. Set `HOME` under the cache. This run did. `/home/mark/.aider` stayed absent. |
| Context 8560 | A real checkout blows the window or gets a partial edit | Do not treat 7.6536 s as a build-lane time. A repo-sized run is a later ticket. |
| Aider calls omit `keep_alive` | The preload used `2m`. Later calls refresh Ollama's own timer | Do not `ollama stop` a model this lane loaded while another lane might be using it. This lane did not stop it. |
| Price-cache download | The first `--exit` fetched litellm's model price file into the redirected home | Leave it in the cache. Do not commit it. |
| Host Python 3.14 | `pip install` on `/usr/bin/python3` fails the `requires` bound | Use the existing CPython 3.12.12 venv. Do not install a second interpreter. |
| Two editors, one checkout | A second aider races git with OpenCode | One worktree per run, and the model lock for Ollama. |
| Preload error | Ollama rejects the load and aider never starts | The probe writes `SKIPPED` and does not start the editor. The card stays I1. |
| `run` pointed at the real binary | A stub-path command would call Ollama without the lock | `run` refuses that path. The model step is `live`, which re-execs `scripts/model_lock.sh`. |

## Next gate

Stay I1. Re-open only if a later ticket shows a headless git edit that `./pfy build --local` cannot do, on a repo-sized diff, with an install under 50 MB, and still no account. No gate wiring. Not a Feature GO.

## How aider would sit in the pipeline

1. What triggers it? A person or a bot starts `aider --message-file ... --yes-always` when they want a local git commit and they are not using `./pfy build --local`. Nothing in this repo starts it today.
2. What does it do, and which services does it read and write? It reads the git checkout and writes a commit. The model call goes to Ollama on `127.0.0.1:11434` under `scripts/model_lock.sh`. No hosted model and no account.
3. What does it trigger next? The lane's own test command, if someone passes `--test-cmd`. This probe left auto-test off. The driver then does whatever it already does. This lane does not add that step.
4. Where does a human re-enter? After the commit, if the diff is wrong. `--yes-always` does not stop to ask. Replacing OpenCode with aider needs Mark's GO. This lane does not ask.
5. What stops two runs doing the same work? The model lock serializes Ollama. Two aider processes on one checkout can still race on git. One worktree per run is the stop. This probe used a cache repo so it could not commit here.
