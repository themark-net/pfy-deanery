"""Clean-clone flake gate and task size caps for pfy build --local.

Fail: a gate that passes once and then fails still ends PASS, a stable gate
is marked FLAKY, --flake-runs 0 still re-runs, a literal listen port is
silent, port 0 is warned, or a 20-file diff over the small line cap is
committed without --size product.
Recover: FLAKY with per-run results, PASS when the gate stays green or
N is 0, a receipt warning only for the non-zero port, and --size product
(or a task size field) commits the same diff the default refuses. The
refusal names the flag.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

import tests.test_pfy_build_local as harness


def _lines(name: str, count: int) -> str:
    body = ["value = %r" % name]
    body.extend("# pad %s %d" % (name, i) for i in range(count - 1))
    return "\n".join(body) + "\n"


def _twenty_files() -> dict:
    # 220 lines each. 20 files is under the 40-file small cap. 4400 lines
    # is over the 4000-line small cap and under the product line cap.
    return {"src/part_%02d.py" % i: _lines("part_%02d" % i, 220) for i in range(20)}


PORT_FILE = '''\
import socket


def bind_fixed():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 15439))


def bind_ephemeral():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))


def listen_fixed(sock):
    sock.listen(15439)


def listen_ephemeral(sock):
    sock.listen(0)
'''


def _gate(path: Path, body: str) -> str:
    path.write_text(body, encoding="utf-8")
    return "python3 %s" % path


_ONCE = '''\
import os
import sys
from pathlib import Path

print("HOME=%s" % os.environ.get("HOME", ""))
if "GITHUB_TOKEN" in os.environ:
    print("TOKEN-LEAK")
    print("Ran 1 test in 0.001s")
    print("FAILED (failures=1)")
    raise SystemExit(1)
if not Path("src/feature.py").is_file():
    print("Ran 1 test in 0.001s")
    print("OK")
    raise SystemExit(0)
state = Path("flake-state.txt")
n = int(state.read_text(encoding="utf-8")) if state.is_file() else 0
state.write_text(str(n + 1), encoding="utf-8")
if n == 0:
    print("Ran 1 test in 0.001s")
    print("OK")
    raise SystemExit(0)
print("FLAKE-STATE")
print("Ran 1 test in 0.001s")
print("FAILED (failures=1)")
raise SystemExit(1)
'''

_GREEN = (
    "print('HOME=%s' % __import__('os').environ.get('HOME', ''))\n"
    "print('Ran 1 test in 0.001s')\n"
    "print('OK')\n"
    "raise SystemExit(0)\n"
)


class FlakeAndSizeTests(unittest.TestCase):
    def setUp(self):
        self.inner = harness.LocalBuildTests()
        self.inner.setUp()
        notes = self.inner.tmp / "stub-notes"
        notes.mkdir()
        self.plan = notes / "plan.json"
        self.count = notes / "attempt-count"
        self.parent_home = os.environ.get("HOME", "")

    def tearDown(self):
        self.inner.tearDown()

    def _run(self, task, step, extra, timeout=180):
        self.plan.write_text(json.dumps([step]), encoding="utf-8")
        return self.inner.run_build(
            "plan",
            extra=extra,
            env_extra={
                "PFY_STUB_PLAN": str(self.plan),
                "PFY_STUB_COUNT": str(self.count),
                "PFY_LOCAL_BUILD_TEST_SEAM": "1",
            },
            timeout=timeout,
            task=task,
        )

    def test_pass_once_state_file_is_flaky_and_a_stable_gate_passes(self):
        gate = _gate(self.inner.tmp / "gate_once.py", _ONCE)
        proc, receipt = self._run(
            "add the feature\nfiles: src/feature.py\n",
            {"mode": "noop", "write": {"src/feature.py": "value = 1\n"}},
            ["--retries", "0", "--test-cmd", gate],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        data = self.inner.receipt(proc, receipt)
        self.assertEqual(data["status"], "FLAKY", text)
        self.assertEqual(data["reason"], "flaky")
        self.assertNotEqual(proc.returncode, 0, text)
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        runs = data["flake"]["results"]
        self.assertGreaterEqual(len(runs), 1, data["flake"])
        self.assertTrue(any(not row["ok"] for row in runs), runs)
        joined = "\n".join(row.get("tail") or "" for row in runs)
        self.assertIn("FLAKE-STATE", joined)
        self.assertNotIn("TOKEN-LEAK", joined)
        homes = [
            line.split("=", 1)[1]
            for line in joined.splitlines()
            if line.startswith("HOME=")
        ]
        self.assertTrue(homes, joined)
        for home in homes:
            self.assertNotEqual(home, self.parent_home, joined)
            self.assertIn("flake-home", home, joined)
        self.inner.assert_clean_origin()

        stable = _gate(self.inner.tmp / "gate_stable.py", _GREEN)
        proc, receipt = self._run(
            "add the feature\nfiles: src/feature.py\n",
            {"mode": "noop", "write": {"src/feature.py": "value = 1\n"}},
            ["--retries", "0", "--test-cmd", stable],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        data = self.inner.receipt(proc, receipt)
        self.assertEqual(proc.returncode, 0, text)
        self.assertEqual(data["status"], "PASS", text)
        self.assertEqual(data["reason"], "ok")
        self.assertIsNotNone(data["commit"])
        runs = data["flake"]["results"]
        self.assertEqual(len(runs), 2, data["flake"])
        self.assertTrue(all(row["ok"] for row in runs), runs)
        self.assertFalse(data["flake"]["skipped"])
        self.inner.assert_clean_origin()

    def test_flake_runs_zero_skips_the_clean_clone(self):
        gate = _gate(self.inner.tmp / "gate_once.py", _ONCE)
        proc, receipt = self._run(
            "add the feature\nfiles: src/feature.py\n",
            {"mode": "noop", "write": {"src/feature.py": "value = 1\n"}},
            ["--retries", "0", "--flake-runs", "0", "--test-cmd", gate],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        data = self.inner.receipt(proc, receipt)
        self.assertEqual(proc.returncode, 0, text)
        self.assertEqual(data["status"], "PASS", text)
        self.assertIsNotNone(data["commit"])
        self.assertTrue(data["flake"]["skipped"], data["flake"])
        self.assertEqual(data["flake"]["results"], [])
        self.inner.assert_clean_origin()

    def test_literal_port_is_warned_and_port_zero_is_not(self):
        tests = self.inner.repo / "tests"
        (tests / "test_ports.py").write_text(PORT_FILE, encoding="utf-8")
        self.inner.commit_base("add port samples")
        gate = _gate(self.inner.tmp / "gate_stable.py", _GREEN)
        proc, receipt = self._run(
            "add the feature\nfiles: src/feature.py\n",
            {"mode": "noop", "write": {"src/feature.py": "value = 1\n"}},
            ["--retries", "0", "--test-cmd", gate],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        data = self.inner.receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS", text)
        ports = data["fixed_ports"]
        self.assertTrue(any(item.get("port") == 15439 for item in ports), ports)
        self.assertFalse(any(item.get("port") == 0 for item in ports), ports)
        warned = " ".join(data.get("warnings") or [])
        self.assertIn("15439", warned)
        self.assertNotIn("port 0", warned)
        self.inner.assert_clean_origin()

    def _assert_refused(self, proc, receipt):
        text = (proc.stdout or "") + (proc.stderr or "")
        data = self.inner.receipt(proc, receipt)
        self.assertNotEqual(proc.returncode, 0, text)
        self.assertEqual(data["status"], "FAIL", text)
        self.assertEqual(data["reason"], "review-diff-over-line-cap")
        self.assertIsNone(data["commit"])
        self.assertIn("--max-lines", text)
        self.assertIn("--size", text)
        self.assertIn("The flag that raises the line cap is --max-lines", text)
        self.assertIn("Rerun with --max-lines", text)
        size = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(size["checks"]["size"]["files"], 20)
        self.assertGreater(size["checks"]["size"]["lines"], size["checks"]["size"]["max_lines"])
        self.inner.assert_clean_origin()
        return text

    def test_size_product_allows_the_20_file_diff_the_default_refuses(self):
        gate = _gate(self.inner.tmp / "gate_stable.py", _GREEN)
        files = _twenty_files()
        task = "add twenty parts\nfiles: src/part_*.py\n"
        proc, receipt = self._run(
            task,
            {"mode": "noop", "write": files},
            ["--retries", "0", "--test-cmd", gate, "--flake-runs", "0"],
            timeout=180,
        )
        self._assert_refused(proc, receipt)

        proc, receipt = self._run(
            task,
            {"mode": "noop", "write": files},
            ["--retries", "0", "--test-cmd", gate, "--flake-runs", "0", "--size", "product"],
            timeout=180,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        data = self.inner.receipt(proc, receipt)
        self.assertEqual(proc.returncode, 0, text)
        self.assertEqual(data["status"], "PASS", text)
        self.assertEqual(data["review"].get("size"), "product")
        names = harness._git(
            self.inner.repo,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            data["commit"],
        ).strip().splitlines()
        self.assertEqual(len(names), 20, names)
        self.inner.assert_clean_origin()

        proc, receipt = self._run(
            "add twenty parts\nsize: product\nfiles: src/part_*.py\n",
            {"mode": "noop", "write": files},
            ["--retries", "0", "--test-cmd", gate, "--flake-runs", "0"],
            timeout=180,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        data = self.inner.receipt(proc, receipt)
        self.assertEqual(proc.returncode, 0, text)
        self.assertEqual(data["status"], "PASS", text)
        self.assertEqual(data["review"].get("size"), "product")
        self.inner.assert_clean_origin()
