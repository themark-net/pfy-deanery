"""Opt-in clean-clone flake gate for the cloud build route.

Fail: a gate that passes once and then fails still ends PASS or tests-flaky,
a stable gate is marked FLAKY, --flake-runs 0 still re-runs, or
PFY_BUILD_FLAKE_RUNS changes the daily same-tree second gate.
Recover: FLAKY with per-run results and no retry, PASS when the gate stays
green or N is 0, and the env var leaves reason tests-flaky in place.
The flag is off unless it is passed. The dollar quote is unchanged.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import unittest
from pathlib import Path

from tests.test_pfy_build_cloud import CLOUD, SCRATCH, _drop_external_worktrees, _git, _init_repo, _run, _write_exe

_ONCE = """\
import os
from pathlib import Path

print("HOME=%s" % os.environ.get("HOME", ""))
if "GITHUB_TOKEN" in os.environ:
    print("TOKEN-LEAK")
    raise SystemExit(1)
if not Path("src/feature.py").is_file():
    print("NEED-FEATURE")
    raise SystemExit(0)
state = Path("flake-state.txt")
n = int(state.read_text(encoding="utf-8")) if state.is_file() else 0
state.write_text(str(n + 1), encoding="utf-8")
if n == 0:
    print("GATE-OK")
    raise SystemExit(0)
print("FLAKE-STATE")
raise SystemExit(1)
"""

_GREEN = """\
import os

print("HOME=%s" % os.environ.get("HOME", ""))
if "GITHUB_TOKEN" in os.environ:
    print("TOKEN-LEAK")
    raise SystemExit(1)
print("GATE-OK")
raise SystemExit(0)
"""

_COUNTER = """\
import os
from pathlib import Path

path = Path(os.environ["PFY_GATE_COUNT"])
n = int(path.read_text()) + 1 if path.exists() else 1
path.write_text(str(n))
print("GATE-FLAKY-TAIL")
raise SystemExit(1 if n >= 3 else 0)
"""


class CloudCleanCloneFlakeTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir(parents=True, exist_ok=True)
        self.receipt_dir = SCRATCH / (self.id().replace(".", "_") + "-receipt")
        ignore = self.repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "flake-state.txt\n", encoding="utf-8")
        added = _git(self.repo, "add", ".gitignore")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "ignore flake state")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        self.parent_home = os.environ.get("HOME", "")
        self.grok_count = self.side / "grok-count"

    def tearDown(self) -> None:
        _drop_external_worktrees(self.repo)
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)
        shutil.rmtree(self.receipt_dir, ignore_errors=True)

    def _receipt(self) -> dict:
        return json.loads((self.receipt_dir / "receipt.json").read_text(encoding="utf-8"))

    def _grok(self, review: bool) -> Path:
        count = str(self.grok_count)
        body = (
            "#!/usr/bin/env python3\n"
            "import os\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "count = Path(os.environ['PFY_GROK_COUNT'])\n"
            "n = int(count.read_text()) + 1 if count.exists() else 1\n"
            "count.write_text(str(n))\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "Path('src').mkdir(exist_ok=True)\n"
            "Path('src/feature.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n"
        )
        if not review:
            body = body.replace("if 'PFY-CLOUD-REVIEW' in blob:\n    print('verdict: accept')\n    raise SystemExit(0)\n", "")
        return _write_exe(self.side / "grok.py", body)

    def _gate(self, name: str, body: str) -> str:
        path = _write_exe(self.side / name, "#!/usr/bin/env python3\n" + body)
        return "%s %s" % (sys.executable, path)

    def _run(self, gate: str, extra: list[str], env: dict | None = None, review: bool = False):
        merged = {
            "GITHUB_TOKEN": "cloud-flake-test-token",
            "PFY_GROK_COUNT": str(self.grok_count),
        }
        if env:
            merged.update(env)
        argv = [
            sys.executable,
            str(CLOUD),
            "add the feature",
            "--repo",
            str(self.repo),
            "--receipt-dir",
            str(self.receipt_dir),
            "--timeout",
            "30",
            "--test-cmd",
            gate,
            "--grok-cmd",
            str(self._grok(review)),
        ]
        argv.extend(extra)
        return _run(argv, self.repo, env=merged, timeout=90)

    def test_pass_once_is_flaky_and_a_stable_gate_passes(self) -> None:
        # Fail: the second read of the state file is tests-flaky, or it is
        # retried, or the clone still has the parent HOME or the token.
        # Recover: status FLAKY, one grok call, per-run tail, fresh HOME.
        proc = self._run(
            self._gate("gate_once.py", _ONCE),
            ["--retries", "1", "--flake-runs", "1"],
            review=True,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        data = self._receipt()
        self.assertEqual(data["status"], "FLAKY", text)
        self.assertEqual(data["reason"], "flaky")
        self.assertEqual(proc.returncode, 1, text)
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(data["attempts"][0]["status"], "FLAKY")
        self.assertEqual(data["attempts"][0]["reason"], "flaky")
        self.assertEqual(self.grok_count.read_text(encoding="utf-8"), "1", text)
        self.assertIn("clean-clone", data["recovery"])
        self.assertIn("--flake-runs 0", data["recovery"])
        self.assertIn("./pfy build", data["recovery"])
        self.assertIn(data["recovery"], text)
        runs = data["flake"]["results"]
        self.assertEqual(len(runs), 1, data["flake"])
        self.assertFalse(runs[0]["ok"], runs)
        self.assertIn("FLAKE-STATE", runs[0]["tail"])
        self.assertNotIn("TOKEN-LEAK", runs[0]["tail"])
        self.assertEqual(data["gate"]["after"]["exit"], 0)
        homes = [
            line.split("=", 1)[1]
            for line in runs[0]["tail"].splitlines()
            if line.startswith("HOME=")
        ]
        self.assertTrue(homes, runs[0]["tail"])
        for home in homes:
            self.assertNotEqual(home, self.parent_home, runs[0]["tail"])
            self.assertIn("flake-home", home, runs[0]["tail"])
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

        stable = self._run(
            self._gate("gate_stable.py", _GREEN),
            ["--retries", "0", "--no-review", "--flake-runs", "2"],
        )
        text = (stable.stdout or "") + (stable.stderr or "")
        data = self._receipt()
        self.assertEqual(stable.returncode, 0, text)
        self.assertEqual(data["status"], "PASS", text)
        self.assertEqual(data["reason"], "ok")
        self.assertIsNotNone(data["commit"])
        runs = data["flake"]["results"]
        self.assertEqual(len(runs), 2, data["flake"])
        self.assertTrue(all(row["ok"] for row in runs), runs)
        self.assertFalse(data["flake"]["skipped"])
        for row in runs:
            self.assertNotIn("TOKEN-LEAK", row["tail"])
            self.assertIn("flake-home", row["tail"])

    def test_flake_runs_zero_skips_the_clean_clone(self) -> None:
        # Fail: N=0 still runs the same-tree second gate, so the state file
        # fails the build. Recover: PASS, skipped, empty results, a commit.
        proc = self._run(
            self._gate("gate_once.py", _ONCE),
            ["--retries", "0", "--no-review", "--flake-runs", "0"],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        data = self._receipt()
        self.assertEqual(proc.returncode, 0, text)
        self.assertEqual(data["status"], "PASS", text)
        self.assertIsNotNone(data["commit"])
        self.assertTrue(data["flake"]["skipped"], data["flake"])
        self.assertEqual(data["flake"]["runs"], 0)
        self.assertEqual(data["flake"]["results"], [])

    def test_env_flake_runs_does_not_replace_the_same_tree_gate(self) -> None:
        # Fail: PFY_BUILD_FLAKE_RUNS turns the daily path into FLAKY or skips
        # the second gate. Recover: reason stays tests-flaky and flake is absent.
        count = self.side / "gate-count"
        for raw in ("2", "0"):
            if count.exists():
                count.unlink()
            if self.receipt_dir.exists():
                shutil.rmtree(self.receipt_dir)
            if self.grok_count.exists():
                self.grok_count.unlink()
            proc = self._run(
                self._gate("gate_count.py", _COUNTER),
                ["--retries", "0", "--no-review"],
                env={"PFY_GATE_COUNT": str(count), "PFY_BUILD_FLAKE_RUNS": raw},
            )
            text = (proc.stdout or "") + (proc.stderr or "")
            data = self._receipt()
            self.assertEqual(proc.returncode, 1, text)
            self.assertEqual(data["status"], "FAIL", text)
            self.assertEqual(data["reason"], "tests-flaky", text)
            self.assertNotIn("flake", data)
            self.assertIsNone(data["commit"])


if __name__ == "__main__":
    unittest.main()
