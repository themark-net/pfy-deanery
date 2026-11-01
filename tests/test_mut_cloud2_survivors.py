"""Behavior tests that kill the wave-5 cloud mutants the suite left alive.

Each test passes on the current runner and fails when its mutant is applied
to a copy. The runner file in this worktree is not edited.

C19  writable-test glob is ignored
C21  git add uses a glob pathspec, so a bracket name is missed
C23  an archive-recheck timeout is treated as a pass
C27  protected basename match is off, so nested/auth.json is committed
C30  a private-key body survives when the PEM block pass is skipped
C39  a review timeout is recorded as review-rejected
C40  a hung before-gate still starts grok
C41  --timeout 0 is accepted
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / "tmp" / "mut-cloud2-tests"
CLOUD = ROOT / "scripts" / "pfy_build_cloud.py"


def _run(
    argv: list[str],
    cwd: Path,
    env: dict | None = None,
    timeout: float = 30,
) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    merged["TMPDIR"] = str(SCRATCH)
    merged["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(
        argv,
        cwd=cwd,
        env=merged,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return _run(["git", *args], repo)


def _write_exe(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    init = _git(path, "init", "-b", "main")
    if init.returncode != 0:
        raise RuntimeError(init.stderr)
    _git(path, "config", "user.email", "mut-cloud2@example.com")
    _git(path, "config", "user.name", "mut-cloud2")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    (path / ".gitignore").write_text("tmp/\npipelines/dogfood/build-cloud/\n", encoding="utf-8")
    _git(path, "add", "README.md", ".gitignore")
    committed = _git(path, "commit", "-m", "init")
    if committed.returncode != 0:
        raise RuntimeError(committed.stderr)
    return path


class Cloud2SurvivorTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir(parents=True, exist_ok=True)
        self.receipt_dir = self.side / "receipt"

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def _cloud(self, task: str, extra: list[str], grok: Path, gate: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
        argv = [
            sys.executable,
            str(CLOUD),
            task,
            "--repo",
            str(self.repo),
            "--retries",
            "0",
            "--no-review",
            "--timeout",
            "30",
            "--receipt-dir",
            str(self.receipt_dir),
            "--grok-cmd",
            str(grok),
        ]
        if gate is not None:
            argv.extend(["--test-cmd", "%s %s" % (sys.executable, gate)])
        argv.extend(extra)
        return _run(argv, self.repo, env=env, timeout=25)

    def _receipt(self) -> dict:
        return json.loads((self.receipt_dir / "receipt.json").read_text(encoding="utf-8"))

    def _gate_ok(self) -> Path:
        return _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )

    def test_writable_glob_lets_the_matching_base_test_change(self) -> None:
        # Fail: --writable-test tests/test_ed*.py is compared as literal text,
        # so the allowed test_edit.py is tests-tampered and nothing lands.
        # Recover: the glob matches test_edit.py, the edit commits, test_keep.py stays.
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_keep.py").write_text("def test_keep():\n    assert True\n", encoding="utf-8")
        (tests / "test_edit.py").write_text("def test_edit():\n    assert True\n", encoding="utf-8")
        added = _git(self.repo, "add", "tests")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "tests")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('tests/test_edit.py').write_text('def test_edit():\\n    assert 1 == 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._cloud(
            "edit the allowed test",
            ["--writable-test", "tests/test_ed*.py"],
            grok,
            self._gate_ok(),
        )
        # _cloud forces --no-review before extra, so the glob flag is present.
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", payload)
        self.assertIsNotNone(payload["commit"])
        shown = _git(self.repo, "show", payload["commit"] + ":tests/test_edit.py")
        self.assertEqual(shown.stdout, "def test_edit():\n    assert 1 == 1\n")
        kept = _git(self.repo, "show", payload["commit"] + ":tests/test_keep.py")
        self.assertEqual(kept.stdout, "def test_keep():\n    assert True\n")

    def test_bracket_filename_is_committed_literally(self) -> None:
        # Fail: git add :(glob)foo[1].py looks for foo1.py, so the bracket file
        # never lands (scope mismatch or an empty commit).
        # Recover: :(literal) stages foo[1].py and that body is the commit.
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('foo[1].py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._cloud("add the bracket file", [], grok, self._gate_ok())
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", payload)
        shown = _git(self.repo, "show", payload["commit"] + ":foo[1].py")
        self.assertEqual(shown.stdout, "value = 1\n")

    def test_recheck_timeout_does_not_commit(self) -> None:
        # Fail: the fourth gate (the archive recheck) hangs and the runner
        # still creates the branch.
        # Recover: exit 3, reason timeout, no branch. The earlier gates passed.
        count = self.side / "gate-count"
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "import os, time\n"
            "from pathlib import Path\n"
            "path = Path(os.environ['PFY_GATE_COUNT'])\n"
            "n = int(path.read_text()) + 1 if path.exists() else 1\n"
            "path.write_text(str(n))\n"
            "if n >= 4:\n"
            "    time.sleep(30)\n"
            "print('GATE-OK')\n"
            "raise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add kept",
                "--repo",
                str(self.repo),
                "--retries",
                "0",
                "--no-review",
                "--timeout",
                "1",
                "--receipt-dir",
                str(self.receipt_dir),
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
            env={"PFY_GATE_COUNT": str(count)},
            timeout=20,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 3, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "TIMEOUT", payload)
        self.assertEqual(payload["reason"], "timeout")
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertIn("the gate timed out", payload["recovery"])
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_nested_auth_json_is_protected(self) -> None:
        # Fail: auth.json is protected only at the repo root, so nested/auth.json
        # is committed next to kept.py.
        # Recover: the basename match rejects the attempt and no branch is kept.
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('nested').mkdir()\n"
            "Path('nested/auth.json').write_text('{}\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._cloud("do not touch nested auth", [], grok, self._gate_ok())
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "protected-path-changed", payload)
        self.assertIn("nested/auth.json", payload["recovery"])
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_private_key_body_is_redacted(self) -> None:
        # Fail: BEGIN/END are replaced but the key body MIIB-CLOUD2-SECRET
        # stays in the receipt.
        # Recover: the PEM block pass removes the body before the receipt is written.
        body = "MIIB-CLOUD2-SECRET"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "print('-----BEGIN PRIVATE KEY-----')\n"
            "print(%r)\n"
            "print('-----END PRIVATE KEY-----')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n" % body,
        )
        proc = self._cloud("add kept", [], grok, self._gate_ok())
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        raw = (self.receipt_dir / "receipt.json").read_text(encoding="utf-8")
        self.assertNotIn(body, raw)
        self.assertNotIn("BEGIN PRIVATE KEY", raw)
        self.assertIn("[redacted-private-key]", raw)
        payload = json.loads(raw)
        shown = _git(self.repo, "show", payload["commit"] + ":kept.py")
        self.assertEqual(shown.stdout, "value = 1\n")

    def test_review_timeout_is_timeout_not_reject(self) -> None:
        # Fail: a hung review is review-rejected and exits 1.
        # Recover: exit 3, reason timeout, and no branch. The edit is not committed.
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys, time\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    time.sleep(30)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add kept",
                "--repo",
                str(self.repo),
                "--retries",
                "0",
                "--timeout",
                "1",
                "--receipt-dir",
                str(self.receipt_dir),
                "--test-cmd",
                "%s %s" % (sys.executable, self._gate_ok()),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
            timeout=20,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 3, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "TIMEOUT", payload)
        self.assertEqual(payload["reason"], "timeout")
        self.assertNotEqual(payload["reason"], "review-rejected")
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])

    def test_hung_before_gate_does_not_start_grok(self) -> None:
        # Fail: the baseline gate hangs and grok still runs.
        # Recover: exit 3 before any grok call. The marker file is absent.
        marker = self.side / "grok-started"
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nimport time\ntime.sleep(30)\nraise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path(%r).write_text('started\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n" % str(marker),
        )
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add kept",
                "--repo",
                str(self.repo),
                "--retries",
                "0",
                "--no-review",
                "--timeout",
                "1",
                "--receipt-dir",
                str(self.receipt_dir),
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
            timeout=20,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 3, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "timeout", payload)
        self.assertIn("the gate timed out", payload["recovery"])
        self.assertFalse(marker.exists(), text)
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])

    def test_timeout_zero_is_usage_and_does_not_start_grok(self) -> None:
        # Fail: --timeout 0 is accepted and the build starts.
        # Recover: exit 2 names the timeout rule, and grok is not started.
        marker = self.side / "grok-started"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path(%r).write_text('started\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n" % str(marker),
        )
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add kept",
                "--repo",
                str(self.repo),
                "--timeout",
                "0",
                "--grok-cmd",
                str(grok),
                "--receipt-dir",
                str(self.receipt_dir),
            ],
            self.repo,
            timeout=20,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 2, text)
        self.assertIn("--timeout must be > 0", text)
        self.assertFalse(marker.exists(), text)
        self.assertFalse((self.receipt_dir / "receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
