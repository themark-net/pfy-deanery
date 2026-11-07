# Fast pipeline slices 3+6: parallel light jobs, model-bound lane only for local models (branch bot/fastpipe-par-1107)

Slice 1 already landed on main: scripts/run_tests.py (parallel), scripts/test_select.py, scripts/test_cache.py, docs/ops/MODULAR-CI.md, AGENTS.md "Modular CI" section. Read them first. Standing rule: only jobs bound by local-model token speed get a long serialized lane; light jobs must run concurrently. Commit on this branch in this worktree; do not push. No secrets printed. No em dashes. No sudo anywhere (nimo is a user-level host).

## DoD
1. **pregate concurrency**: make scripts/pregate.sh safe to run several at once on one host (unique run roots/scratch per run including pid, no shared mutable files, orphan check scoped per run, retention pruning that never deletes another live run). Remove the "one pregate per host" limitation from docs. Add a test that starts two pregate runs on two tiny refs concurrently (use `--only lint,gate-hash` or a cheap check list so it is fast) and both finish PASS without touching each other.
2. **Model lock only for model jobs**: add `scripts/model_lock.sh <cmd...>` (flock on `${PFY_MODEL_LOCK:-$HOME/.cache/pfy/locks/local-model.lock}`) and use it only in jobs that load local models (Ollama, Strata, local-lab, nightly-models, benches, smoke-litellm-ollama etc; grep Makefile and workflows). Document in MODULAR-CI.md that landings never take this lock and never wait for Runner.Worker; the old ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock convention is retired for light jobs.
3. **Landings off the single nimo runner**: in .github/workflows/eval-structural.yml, the `G0 (self-hosted nimo)` job runs only on push to main and schedule (not on workflow_dispatch or pull_request for branches); for branch landings the nimo evidence is pregate's cached pass (scripts/test_cache.py) and the GitHub-hosted ubuntu job is the CI gate. On push to main the nimo job must first `scripts/test_cache.py check` and skip the suite on a hit. Shard the ubuntu tests job with a matrix if the selected/full suite is still over ~5 minutes (e.g. 4 shards by module hash, via run_tests.py --shard i/n; add that option with a test). Keep every non-test check.
4. **local-lab and model jobs never block landings**: local-lab.yml and nightly-models.yml: add concurrency groups so only one model-bound job runs at a time, cancel-in-progress false, timeout-minutes sane; move schedules to off-hours PT (document the UTC conversion; America/Los_Angeles is UTC-8 now) and wrap model steps in scripts/model_lock.sh. Since branch landings no longer use the nimo runner (item 3), local-lab cannot block them; say so in MODULAR-CI.md.
5. **Persistent tool cache**: add `scripts/tool_cache.sh` documenting and checking `~/.cache/pfy/{bin,tools,uv-cache}` (SkillSpector v2.12.0 venv already lives at ~/.cache/pfy/tools/skillspector with ~/.cache/pfy/bin/skillspector). Make scripts/pfy_skill_scan.py (if on main) and `make skill-scan` also look in ~/.cache/pfy/bin when PFY_SKILLSPECTOR_BIN and PATH miss (keep PFY_SKILLSPECTOR_BIN precedence). Do the same lookup for codebase-memory-mcp where the repo resolves it. Add a pinned test container definition `ci/test-image/Containerfile` (python 3.12 slim + git + ripgrep + bubblewrap, no secrets) and `make test-image` / `make test-in-container` that build with rootless podman (available on nimo at /usr/bin/podman) and run scripts/run_tests.py inside with the repo mounted read-only and a tmp volume; this lets several lanes run tests in parallel isolated containers. Verify it builds and runs a selected subset on nimo; if rootless podman cannot run here, record the exact error in MODULAR-CI.md and leave the target documented, do not fake success.
6. Update docs/ops/MODULAR-CI.md (mark slices 3, 5, 6 done with what was verified), docs/ops/PREGATE.md, and docs/HANDOFF-fast-pipeline-1107.md. Tests: behavior only, few. Self-review: no risky-path check weakened (trading/live money, release/deploy, secrets always full), nothing silently skipped. Clean git status.

## Exit tests from grill

Fixed by the coordinator before Build. Do not edit this section.

### Q1

- Answer: Yes. PFY_TEST_CACHE_DIR isolates the cache. `record <key>` then `check <key>` exits 0 and, when GITHUB_OUTPUT is set, writes hit=true. `check` of an unknown key exits 0 and writes hit=false. A hit is the only suite dedup. Light pregates are not single-flighted. model_lock.sh is only the local-model wait.
- Behavior change: true
- Assertion: With PFY_TEST_CACHE_DIR set, scripts/test_cache.py record <key> then check <key> exits 0 and writes hit=true to GITHUB_OUTPUT, and check of an unknown key exits 0 and writes hit=false.

Test path: `tests/test_fastpipe_cache_dedup.py`

```python
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "test_cache.py"


class TestCacheDedup(unittest.TestCase):
    def test_check_exits_zero_and_reports_hit_or_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache"
            out = Path(tmp) / "github_output.txt"
            out.write_text("")
            env = os.environ.copy()
            env["PFY_TEST_CACHE_DIR"] = str(cache)
            env["GITHUB_OUTPUT"] = str(out)
            recorded = subprocess.run(
                [sys.executable, str(SCRIPT), "record", "abc"],
                cwd=ROOT,
                env=env,
                text=True,
            )
            self.assertEqual(recorded.returncode, 0, recorded.stderr)
            hit = subprocess.run(
                [sys.executable, str(SCRIPT), "check", "abc"],
                cwd=ROOT,
                env=env,
                text=True,
            )
            self.assertEqual(hit.returncode, 0, hit.stderr)
            self.assertIn("hit=true", out.read_text())
            out.write_text("")
            miss = subprocess.run(
                [sys.executable, str(SCRIPT), "check", "missing-key"],
                cwd=ROOT,
                env=env,
                text=True,
            )
            self.assertEqual(miss.returncode, 0, miss.stderr)
            self.assertIn("hit=false", out.read_text())


if __name__ == "__main__":
    unittest.main()
```

### Q2

- Answer: Yes. pregate and the GitHub-hosted ubuntu gate never call model_lock.sh, never use the pfy-local-model concurrency group, and never flock heavy-1030.lock or local-model.lock.
- Behavior change: true
- Assertion: scripts/pregate.sh and the ubuntu-latest job in .github/workflows/eval-structural.yml do not reference model_lock.sh, pfy-local-model, heavy-1030.lock, or local-model.lock.

Test path: `tests/test_fastpipe_modular_ci_rule.py`

```python
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jobs(text):
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "jobs:":
            start = i + 1
            break
    if start is None:
        return {}
    found = {}
    current = None
    buf = []
    for line in lines[start:]:
        if line.startswith("  ") and not line.startswith("   ") and line.rstrip().endswith(":"):
            if current is not None:
                found[current] = "\n".join(buf)
            current = line.strip()[:-1]
            buf = [line]
        elif current is not None:
            if line and not line.startswith(" ") and not line.startswith("#"):
                break
            buf.append(line)
    if current is not None:
        found[current] = "\n".join(buf)
    return found


class TestModularCiRule(unittest.TestCase):
    def test_light_paths_do_not_take_the_model_lock(self):
        pregate = (ROOT / "scripts" / "pregate.sh").read_text()
        for banned in ("model_lock.sh", "pfy-local-model", "heavy-1030.lock", "local-model.lock"):
            self.assertNotIn(banned, pregate)
        workflow = (ROOT / ".github" / "workflows" / "eval-structural.yml").read_text()
        ubuntu = [body for body in jobs(workflow).values() if "ubuntu-latest" in body]
        self.assertTrue(ubuntu)
        for body in ubuntu:
            for banned in ("model_lock.sh", "pfy-local-model", "heavy-1030.lock", "local-model.lock"):
                self.assertNotIn(banned, body)


if __name__ == "__main__":
    unittest.main()
```

### Q3

- Answer: Yes. Same commit twice is enough. A live root is one whose pid file names a process that is still alive. Prune deletes dead roots and nothing else.
- Behavior change: true
- Assertion: Two concurrent pregate.sh --only lint,gate-hash processes both exit 0, print distinct RUN_ROOT values under PFY_PREGATE_RUNS that contain their pids, remove a dead sibling root, and leave a sibling root with a live pid in place.

Test path: `tests/test_fastpipe_pregate_concurrency.py`

```python
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREGATE = ROOT / "scripts" / "pregate.sh"


class TestPregateConcurrency(unittest.TestCase):
    def test_two_runs_isolate_and_prune_only_dead_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            sleeper = subprocess.Popen(["sleep", "60"])
            live = runs / "live-holder"
            live.mkdir()
            (live / "pid").write_text(str(sleeper.pid))
            (live / "keep.txt").write_text("keep")
            dead = runs / "dead-holder"
            dead.mkdir()
            (dead / "pid").write_text("999999")
            env = os.environ.copy()
            env["PFY_PREGATE_RUNS"] = str(runs)
            cmd = ["bash", str(PREGATE), "--only", "lint,gate-hash"]
            try:
                first = subprocess.Popen(cmd, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                second = subprocess.Popen(cmd, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out1, err1 = first.communicate(timeout=180)
                out2, err2 = second.communicate(timeout=180)
            finally:
                sleeper.kill()
                sleeper.wait(timeout=5)
            self.assertEqual(first.returncode, 0, err1)
            self.assertEqual(second.returncode, 0, err2)
            roots = []
            for pid, out in ((first.pid, out1), (second.pid, out2)):
                found = [line.split("=", 1)[1].strip() for line in out.splitlines() if line.startswith("RUN_ROOT=")]
                self.assertEqual(len(found), 1, out)
                self.assertIn(str(pid), found[0])
                self.assertTrue(found[0].startswith(str(runs) + os.sep))
                roots.append(found[0])
            self.assertNotEqual(roots[0], roots[1])
            self.assertFalse(dead.exists())
            self.assertTrue((live / "keep.txt").exists())


if __name__ == "__main__":
    unittest.main()
```

### Q4

- Answer: Yes. The wait is blocking, not flock -n, and a held lock delays the next command instead of failing it.
- Behavior change: true
- Assertion: scripts/model_lock.sh waits while the lock is held, returns the wrapped command status, honors PFY_MODEL_LOCK, and creates a missing lock parent directory.

Test path: `tests/test_fastpipe_model_lock.py`

```python
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "model_lock.sh"


class TestModelLock(unittest.TestCase):
    def test_blocks_propagates_status_and_creates_parent(self):
        text = SCRIPT.read_text()
        self.assertIn("PFY_MODEL_LOCK", text)
        self.assertIn(".cache/pfy/locks/local-model.lock", text)
        self.assertNotIn("flock -n", text)
        self.assertNotIn("nonblock", text)
        with tempfile.TemporaryDirectory() as tmp:
            lock = str(Path(tmp) / "nested" / "local-model.lock")
            env = os.environ.copy()
            env["PFY_MODEL_LOCK"] = lock
            holder = subprocess.Popen(["bash", str(SCRIPT), "sleep", "1"], env=env)
            time.sleep(0.2)
            started = time.monotonic()
            waited = subprocess.run(
                ["bash", str(SCRIPT), "python3", "-c", "import sys; sys.exit(3)"],
                env=env,
            )
            elapsed = time.monotonic() - started
            holder.wait(timeout=5)
            self.assertEqual(waited.returncode, 3)
            self.assertGreaterEqual(elapsed, 0.5)
            self.assertTrue(Path(lock).parent.is_dir())


if __name__ == "__main__":
    unittest.main()
```

### Q5

- Answer: Yes. Match those names only. Lint, pregate, skill-scan, and ordinary test recipes must not call model_lock.sh.
- Behavior change: true
- Assertion: Each Makefile recipe whose body mentions ollama, strata, local-lab, nightly-models, benches, or smoke-litellm also mentions model_lock.sh, and recipes that mention none of those do not mention model_lock.sh.

Test path: `tests/test_fastpipe_make_model_lock.py`

```python
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ("ollama", "strata", "local-lab", "nightly-models", "benches", "smoke-litellm")


def recipes(text):
    blocks = []
    current = []
    for line in text.splitlines():
        if line and not line[0].isspace() and line.rstrip().endswith(":"):
            if current:
                blocks.append(current)
            current = [line]
        else:
            if current:
                current.append(line)
    if current:
        blocks.append(current)
    return blocks


class TestMakeModelLock(unittest.TestCase):
    def test_only_model_recipes_use_the_lock(self):
        blocks = recipes((ROOT / "Makefile").read_text())
        self.assertTrue(blocks)
        for block in blocks:
            body = "\n".join(block[1:]).lower()
            name = block[0].lower()
            uses_model = any(token in body or token in name for token in TOKENS)
            if uses_model:
                self.assertIn("model_lock.sh", body, block[0])
            else:
                self.assertNotIn("model_lock.sh", body, block[0])


if __name__ == "__main__":
    unittest.main()
```

### Q6

- Answer: Yes. Shared group serializes model jobs without canceling a running one. Stagger the two schedules by two hours. Document 10:00 UTC and 12:00 UTC as 02:00 and 04:00 PT while UTC-8.
- Behavior change: true
- Assertion: local-lab.yml contains cron 0 10 * * * and nightly-models.yml contains cron 0 12 * * *, and both contain concurrency group pfy-local-model, cancel-in-progress false, timeout-minutes 120, and scripts/model_lock.sh.

Test path: `tests/test_fastpipe_model_workflows.py`

```python
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class TestModelWorkflows(unittest.TestCase):
    def test_shared_group_timeout_lock_and_off_hours(self):
        local_lab = (WORKFLOWS / "local-lab.yml").read_text()
        nightly = (WORKFLOWS / "nightly-models.yml").read_text()
        self.assertRegex(local_lab, r"cron:\s*['\"]0 10 \* \* \*['\"]")
        self.assertRegex(nightly, r"cron:\s*['\"]0 12 \* \* \*['\"]")
        for text in (local_lab, nightly):
            self.assertIn("pfy-local-model", text)
            self.assertIn("cancel-in-progress: false", text)
            self.assertRegex(text, r"timeout-minutes:\s*120\b")
            self.assertIn("scripts/model_lock.sh", text)


if __name__ == "__main__":
    unittest.main()
```

### Q7

- Answer: Yes. The ubuntu job remains the branch and pull_request gate. On a cache hit the nimo job stays green and does not rerun the suite.
- Behavior change: true
- Assertion: The G0 job if condition requires refs/heads/main or schedule and does not mention pull_request or workflow_dispatch, and its run_tests.py step comes after test_cache.py check and runs only when the cache hit output is not true.

Test path: `tests/test_fastpipe_g0_triggers.py`

```python
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jobs(text):
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "jobs:":
            start = i + 1
            break
    if start is None:
        return {}
    found = {}
    current = None
    buf = []
    for line in lines[start:]:
        if line.startswith("  ") and not line.startswith("   ") and line.rstrip().endswith(":"):
            if current is not None:
                found[current] = "\n".join(buf)
            current = line.strip()[:-1]
            buf = [line]
        elif current is not None:
            if line and not line.startswith(" ") and not line.startswith("#"):
                break
            buf.append(line)
    if current is not None:
        found[current] = "\n".join(buf)
    return found


class TestG0Triggers(unittest.TestCase):
    def test_nimo_job_is_main_or_schedule_and_skips_on_hit(self):
        text = (ROOT / ".github" / "workflows" / "eval-structural.yml").read_text()
        matched = [body for body in jobs(text).values() if "nimo" in body or "self-hosted" in body]
        self.assertEqual(len(matched), 1)
        block = matched[0]
        ifs = [line for line in block.splitlines() if "if:" in line]
        self.assertTrue(any("refs/heads/main" in line for line in ifs))
        self.assertTrue(any("schedule" in line for line in ifs))
        self.assertFalse(any("pull_request" in line for line in ifs))
        self.assertFalse(any("workflow_dispatch" in line for line in ifs))
        self.assertLess(block.index("test_cache.py"), block.index("run_tests.py"))
        run_at = block.index("run_tests.py")
        window = block[max(0, run_at - 400):run_at]
        self.assertIn("hit", window)
        self.assertIn("if:", window)


if __name__ == "__main__":
    unittest.main()
```

### Q8

- Answer: Yes. Importing the module must not start a suite. Risky paths stay on every shard so a single shard cannot drop them.
- Behavior change: true
- Assertion: shard_keeps uses sha256 modulo for ordinary paths, returns true for every index on trading/live, release/deploy, and secrets paths, --list --shard 99/99 exits 0, and --list --shard 0/2 exits non-zero.

Test path: `tests/test_fastpipe_shard.py`

```python
import hashlib
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_tests.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_tests_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestShard(unittest.TestCase):
    def test_shard_keeps_and_cli(self):
        module = load_module()
        ordinary = "scripts/test_cache.py"
        bucket = int(hashlib.sha256(ordinary.encode()).hexdigest(), 16) % 4
        for index in range(1, 5):
            self.assertEqual(module.shard_keeps(ordinary, index, 4), index - 1 == bucket)
        for path in ("trading/live/test_money.py", "release/deploy/test_ship.py", "pkg/secrets/test_scan.py"):
            for index in range(1, 5):
                self.assertTrue(module.shard_keeps(path, index, 4))
        empty = subprocess.run(
            [sys.executable, str(SCRIPT), "--list", "--shard", "99/99"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(empty.returncode, 0, empty.stderr)
        invalid = subprocess.run(
            [sys.executable, str(SCRIPT), "--list", "--shard", "0/2"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(invalid.returncode, 0)


if __name__ == "__main__":
    unittest.main()
```

### Q9

- Answer: Yes. Add --shard now. Add the workflow matrix only after a measured suite time over five minutes is written on that line.
- Behavior change: true
- Assertion: The ubuntu-latest job in eval-structural.yml has no strategy.matrix unless docs/ops/MODULAR-CI.md contains `measured suite minutes:` with a value greater than 5.

Test path: `tests/test_fastpipe_shard_matrix_gate.py`

```python
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jobs(text):
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "jobs:":
            start = i + 1
            break
    if start is None:
        return {}
    found = {}
    current = None
    buf = []
    for line in lines[start:]:
        if line.startswith("  ") and not line.startswith("   ") and line.rstrip().endswith(":"):
            if current is not None:
                found[current] = "\n".join(buf)
            current = line.strip()[:-1]
            buf = [line]
        elif current is not None:
            if line and not line.startswith(" ") and not line.startswith("#"):
                break
            buf.append(line)
    if current is not None:
        found[current] = "\n".join(buf)
    return found


class TestShardMatrixGate(unittest.TestCase):
    def test_matrix_requires_a_measured_slow_suite(self):
        doc = (ROOT / "docs" / "ops" / "MODULAR-CI.md").read_text()
        match = re.search(r"measured suite minutes:\s*(\d+)", doc)
        over = bool(match) and int(match.group(1)) > 5
        workflow = (ROOT / ".github" / "workflows" / "eval-structural.yml").read_text()
        ubuntu = [body for body in jobs(workflow).values() if "ubuntu-latest" in body]
        self.assertTrue(ubuntu)
        if not over:
            for body in ubuntu:
                self.assertNotIn("matrix:", body)


if __name__ == "__main__":
    unittest.main()
```

### Q10

- Answer: Yes. An empty explicit env var falls through. make skill-scan and any scripts that name those tools use that same order, with the explicit env var first.
- Behavior change: true
- Assertion: tool_cache.sh check fails when a cache dir is missing and passes without deleting a sentinel when all three exist; resolve returns PFY_SKILLSPECTOR_BIN or PFY_CODEBASE_MEMORY_BIN first, else PATH, else ~/.cache/pfy/bin.

Test path: `tests/test_fastpipe_tool_cache.py`

```python
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tool_cache.sh"


def write_exec(path, label):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nprintf '%s\\n' " + label + "\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class TestToolCache(unittest.TestCase):
    def test_check_and_resolve_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            base = home / ".cache" / "pfy"
            env = {"HOME": str(home), "PATH": "/usr/bin:/bin", "PFY_SKILLSPECTOR_BIN": "", "PFY_CODEBASE_MEMORY_BIN": ""}
            missing = subprocess.run(["bash", str(SCRIPT), "check"], env=env, text=True, capture_output=True)
            self.assertNotEqual(missing.returncode, 0)
            for name in ("bin", "tools", "uv-cache"):
                (base / name).mkdir(parents=True)
            sentinel = base / "bin" / "sentinel.txt"
            sentinel.write_text("keep")
            ready = subprocess.run(["bash", str(SCRIPT), "check"], env=env, text=True, capture_output=True)
            self.assertEqual(ready.returncode, 0, ready.stderr)
            self.assertEqual(sentinel.read_text(), "keep")
            path_dir = Path(tmp) / "pathbin"
            cache_skill = base / "bin" / "skillspector"
            path_skill = path_dir / "skillspector"
            explicit_skill = Path(tmp) / "explicit" / "skillspector"
            write_exec(cache_skill, "cache")
            write_exec(path_skill, "path")
            write_exec(explicit_skill, "explicit")
            path_env = env.copy()
            path_env["PATH"] = str(path_dir) + ":/usr/bin:/bin"
            from_path = subprocess.run(["bash", str(SCRIPT), "resolve", "skillspector"], env=path_env, text=True, capture_output=True)
            self.assertEqual(from_path.returncode, 0, from_path.stderr)
            self.assertEqual(from_path.stdout.strip(), str(path_skill))
            bare = env.copy()
            from_cache = subprocess.run(["bash", str(SCRIPT), "resolve", "skillspector"], env=bare, text=True, capture_output=True)
            self.assertEqual(from_cache.stdout.strip(), str(cache_skill))
            forced = bare.copy()
            forced["PFY_SKILLSPECTOR_BIN"] = str(explicit_skill)
            from_env = subprocess.run(["bash", str(SCRIPT), "resolve", "skillspector"], env=forced, text=True, capture_output=True)
            self.assertEqual(from_env.stdout.strip(), str(explicit_skill))
            cache_mem = base / "bin" / "codebase-memory-mcp"
            explicit_mem = Path(tmp) / "explicit" / "codebase-memory-mcp"
            write_exec(cache_mem, "memcache")
            write_exec(explicit_mem, "memexplicit")
            mem_cache = subprocess.run(["bash", str(SCRIPT), "resolve", "codebase-memory-mcp"], env=bare, text=True, capture_output=True)
            self.assertEqual(mem_cache.stdout.strip(), str(cache_mem))
            mem_env = bare.copy()
            mem_env["PFY_CODEBASE_MEMORY_BIN"] = str(explicit_mem)
            mem_hit = subprocess.run(["bash", str(SCRIPT), "resolve", "codebase-memory-mcp"], env=mem_env, text=True, capture_output=True)
            self.assertEqual(mem_hit.stdout.strip(), str(explicit_mem))


if __name__ == "__main__":
    unittest.main()
```

### Q11

- Answer: Yes. The image is python 3.12 slim plus git, ripgrep, and bubblewrap, with no secrets. A podman failure exits non-zero. Landing and pregate do not depend on these targets.
- Behavior change: true
- Assertion: Containerfile names python 3.12, git, ripgrep, and bubblewrap and assigns no secrets; Makefile test-in-container uses podman with a read-only mount and a tmp volume; pregate.sh does not call that target.

Test path: `tests/test_fastpipe_container_optin.py`

```python
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def recipe(text, name):
    lines = text.splitlines()
    buf = []
    capture = False
    for line in lines:
        if line.startswith(name + ":"):
            capture = True
            buf = [line]
            continue
        if capture:
            if line and not line[0].isspace():
                break
            buf.append(line)
    return "\n".join(buf)


class TestContainerOptIn(unittest.TestCase):
    def test_container_target_is_opt_in_and_isolated(self):
        container = (ROOT / "ci" / "test-image" / "Containerfile").read_text()
        self.assertIn("3.12", container)
        lowered = container.lower()
        self.assertIn("git", lowered)
        self.assertTrue("ripgrep" in lowered or "rg" in lowered)
        self.assertIn("bubblewrap", lowered)
        self.assertIsNone(re.search(r"(?i)(api_key|token|password|secret)\s*=", container))
        make = (ROOT / "Makefile").read_text()
        body = recipe(make, "test-in-container")
        self.assertIn("podman", body)
        self.assertIn(":ro", body)
        self.assertIn("tmp", body.lower())
        self.assertNotIn(".cache/pfy", body)
        pregate = (ROOT / "scripts" / "pregate.sh").read_text()
        self.assertNotIn("test-in-container", pregate)
        self.assertNotIn("test-image", pregate)


if __name__ == "__main__":
    unittest.main()
```
