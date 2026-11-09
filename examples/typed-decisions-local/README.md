# typed-decisions-local (X intake Entries 086-088)

One stdlib smoke for three I0 catalog entries from the 2026-10-05 daily X intake:

| Entry | Tool | Command | Expected on nimo today |
|------|------|---------|------------------------|
| 086 | Laya | `python3 examples/typed-decisions-local/smoke.py --entry laya` | exit 2 until a venv exists at `~/DEVELOP/pfy-mentat/tmp/laya-venv` |
| 087 | Bespoke Nimble | `python3 examples/typed-decisions-local/smoke.py --entry nimble` | exit 2 (no NVIDIA GPU, not Apple Silicon) |
| 088 | Beacon | `python3 examples/typed-decisions-local/smoke.py --entry beacon` | exit 2 until a user-mode install exists |

Exit 0 = PASS, 1 = ran but the check failed, 2 = can't run here. Each run writes `pipelines/smoke/<entry>/latest.json`.
The script never installs packages or downloads weights itself. Installs go under `~/DEVELOP/pfy-mentat/tmp/` only.

## Entry 086 eval-auto trial (this worktree)

Head-to-head vs the ADR-0016 CUA-S1-FORMS lane on `data/decision-gates/laya-trial.cases.v0.json` (48 labeled Choice cases, labels written before either model ran). Cite #230. Catalog 70–75 HOLD. Not a Feature GO. Default decision lane stays CUA-S1-FORMS.

```bash
# Reuse the trial venv + HF cache (do not copy weights into this worktree).
export LAYA_PYTHON=$HOME/DEVELOP/pfy-mentat/tmp/laya-trial/.venv-laya/bin/python
export HF_HOME=$HOME/DEVELOP/pfy-mentat/tmp/laya-trial/.hf-cache
export HF_HUB_CACHE=$HOME/DEVELOP/pfy-mentat/tmp/laya-trial/.hf-cache
python3 examples/typed-decisions-local/trial.py --check
python3 examples/typed-decisions-local/trial.py
python3 examples/typed-decisions-local/trial.py --shadow
```

The trial binds `laya-serve` to `127.0.0.1` only and points the typesafe lane at it with `PFY_JEV_TYPESAFE_URL` (default `https://api.typesafe.ai/v1/systemone` is unchanged). Missing venv or server → exit 2 with a reason. Receipt: `pipelines/dogfood/laya-trial/receipt.json`. Results: a private ops note.

`--shadow` keeps CUA-S1-FORMS as the decision, runs Laya **english** only on CUA-held cases, and escalates on choice disagreement. Receipt: `pipelines/dogfood/laya-shadow/receipt.json`. Results: a private ops note. Flag `PFY_JEV_LAYA_SHADOW` stays off by default.
