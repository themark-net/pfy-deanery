# 01 stale enterable

Why picked: T-0124 says OpenCode enterable (`scripts/pfy_enterable_162.py`) is still its own path. Folding it into `pfylib/attach.py` is too big for one cloud task. The not-ok branch of `arm_launch_env_session` strips enterable and session steps and then returns without storing that list. A local call before the run kept id `enterable`. The same early return is on `origin/main`. Type: code fix.

Gate: `python3 dogfood_gate.py` on the throwaway. Before exit 1 (stale markers). After exit 0. Status PASS so the second gate was green too.

Review: verdict accept. Reasons empty.

Human accept: yes. The cloud diff is one assignment, `out["next_steps"] = next_steps`, on the not-ok branch only. No other file. That is the change Mark asked for in the task text. The commit is not on the caller branch and was not pushed.

Wall: 39 seconds. One attempt.
