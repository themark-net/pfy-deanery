#!/usr/bin/env python3
"""Optional AgentLint hook on ./pfy build.

Off unless --agentlint or PFY_AGENTLINT=1. A missing binary warns and allows.
A blocking error rejects the attempt. A warning does not. The child process
does not receive an AgentChute license.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

from tests.test_pfy_build_cloud import CloudBuildFailureTests as _CloudBuildFailureTests
from tests.test_pfy_build_cloud import _git, _write_exe

ROOT = Path(__file__).resolve().parents[1]
REAL_BIN = ROOT / "tmp" / "agentlint-venv" / "bin" / "agentlint"


def _fake_agentlint(side: Path) -> Path:
    return _write_exe(
        side / "agentlint",
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['FAKE_AGENTLINT_SEEN']).write_text('seen\\n', encoding='utf-8')\n"
        "Path(os.environ['FAKE_AGENTLINT_ENV']).write_text(\n"
        "    '\\n'.join('%s=%s' % (k, v) for k, v in sorted(os.environ.items())) + '\\n',\n"
        "    encoding='utf-8',\n"
        ")\n"
        "Path(os.environ['FAKE_AGENTLINT_STDIN']).write_text(sys.stdin.read(), encoding='utf-8')\n"
        "mode = os.environ.get('FAKE_AGENTLINT_MODE', 'deny')\n"
        "if mode == 'warn':\n"
        "    print(json.dumps({'blocked': False, 'violations': [\n"
        "        {'severity': 'warning', 'rule_id': 'cicd-pipeline-guard', 'message': 'Dockerfile'}\n"
        "    ]}))\n"
        "    raise SystemExit(0)\n"
        "if mode == 'allow':\n"
        "    raise SystemExit(0)\n"
        "print(json.dumps({'blocked': True, 'violations': [\n"
        "    {'severity': 'error', 'rule_id': 'no-secrets', 'message': 'secret in app.py'}\n"
        "]}))\n"
        "raise SystemExit(1)\n",
    )


class AgentLintBuildGuardTests(_CloudBuildFailureTests):
    def _env(self, mode: str, binary: Path | None) -> dict:
        env = {
            "FAKE_AGENTLINT_MODE": mode,
            "FAKE_AGENTLINT_SEEN": str(self.side / "seen"),
            "FAKE_AGENTLINT_ENV": str(self.side / "child-env"),
            "FAKE_AGENTLINT_STDIN": str(self.side / "child-stdin"),
            "AGENTCHUTE_LICENSE_KEY": "not-a-license",
            "AGENTCHUTE_ENABLED": "true",
        }
        if binary is None:
            env["PFY_AGENTLINT_BIN"] = "/nonexistent/agentlint"
        else:
            env["PFY_AGENTLINT_BIN"] = str(binary)
        return env

    def _grok_writes(self, body: str) -> Path:
        return _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "Path('app.py').write_text(%r, encoding='utf-8')\n"
            "raise SystemExit(0)\n" % body,
        )

    def test_off_by_default_does_not_run_the_linter(self) -> None:
        binary = _fake_agentlint(self.side)
        grok = self._grok_writes("def add(left, right):\n    return left + right\n")
        proc = self._run_task(
            grok,
            self._gate(),
            "add a function",
            extra=["--retries", "0"],
            env=self._env("deny", binary),
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        self.assertFalse((self.side / "seen").exists(), text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS")
        names = _git(self.repo, "ls-tree", "-r", "--name-only", payload["commit"]).stdout
        self.assertIn("app.py", names.splitlines())

    def test_blocking_error_is_not_committed(self) -> None:
        # Fail: the runner commits a file AgentLint would block.
        # Recover: --agentlint rejects the attempt, keeps no branch, and says rerun.
        binary = _fake_agentlint(self.side)
        grok = self._grok_writes("API_TOKEN = \"sk_" "live_FAKE0123456789abcdefNOTREAL\"\n")
        proc = self._run_task(
            grok,
            self._gate(),
            "add a token",
            extra=["--agentlint", "--retries", "0", "--no-review"],
            env=self._env("deny", binary),
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "agentlint-blocked")
        self.assertIsNone(payload["commit"])
        self.assertIsNone(payload["branch"])
        self.assertIn("rerun ./pfy build", payload["recovery"])
        self.assertNotIn("--local", payload["recovery"])
        self.assertNotIn("not-a-license", text)
        child = (self.side / "child-env").read_text(encoding="utf-8")
        self.assertNotIn("not-a-license", child)
        self.assertNotIn("AGENTCHUTE_LICENSE_KEY=", child)
        stdin = (self.side / "child-stdin").read_text(encoding="utf-8")
        self.assertIn("app.py", stdin)
        self.assertIn("sk_" "live_FAKE0123456789abcdefNOTREAL", stdin)

    def test_missing_binary_warns_and_still_commits(self) -> None:
        # Fail: a missing optional binary aborts the build.
        # Recover: warn agentlint-fallback and keep today's commit path.
        grok = self._grok_writes("def add(left, right):\n    return left + right\n")
        proc = self._run_task(
            grok,
            self._gate(),
            "add a function",
            extra=["--agentlint", "--retries", "0"],
            env=self._env("deny", None),
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        self.assertIn("agentlint-fallback", proc.stderr or "")
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS")
        self.assertIsNotNone(payload["commit"])

    def test_warning_does_not_fail_the_build(self) -> None:
        binary = _fake_agentlint(self.side)
        grok = self._grok_writes("def add(left, right):\n    return left + right\n")
        proc = self._run_task(
            grok,
            self._gate(),
            "add a function",
            extra=["--agentlint", "--retries", "0"],
            env=self._env("warn", binary),
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS")
        self.assertIsNotNone(payload["commit"])

    def test_env_flag_blocks_without_the_cli_flag(self) -> None:
        binary = _fake_agentlint(self.side)
        grok = self._grok_writes("def add(left, right):\n    return left + right\n")
        env = self._env("deny", binary)
        env["PFY_AGENTLINT"] = "1"
        proc = self._run_task(
            grok,
            self._gate(),
            "add a function",
            extra=["--retries", "0", "--no-review"],
            env=env,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        self.assertEqual(self._receipt()["reason"], "agentlint-blocked")

    def test_other_env_values_leave_the_hook_off(self) -> None:
        binary = _fake_agentlint(self.side)
        grok = self._grok_writes("def add(left, right):\n    return left + right\n")
        env = self._env("deny", binary)
        env["PFY_AGENTLINT"] = "true"
        proc = self._run_task(
            grok,
            self._gate(),
            "add a function",
            extra=["--retries", "0"],
            env=env,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        self.assertFalse((self.side / "seen").exists(), text)


class RealAgentLintBuildTests(_CloudBuildFailureTests):
    def setUp(self) -> None:
        super().setUp()
        if not REAL_BIN.is_file():
            self.skipTest("pinned agentlint is not installed under tmp/agentlint-venv")

    def test_real_binary_blocks_a_fake_token_prefix(self) -> None:
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('app.py').write_text(\n"
            "    'API_TOKEN = \"sk_" "live_FAKE0123456789abcdefNOTREAL\"\\n',\n"
            "    encoding='utf-8',\n"
            ")\n"
            "raise SystemExit(0)\n",
        )
        proc = self._run_task(
            grok,
            self._gate(),
            "add a token",
            extra=["--agentlint", "--retries", "0", "--no-review"],
            env={"PFY_AGENTLINT_BIN": str(REAL_BIN), "AGENTCHUTE_LICENSE_KEY": "not-a-license"},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "agentlint-blocked")
        self.assertIn("no-secrets", payload["recovery"])
        self.assertIsNone(payload["commit"])
        self.assertNotIn("not-a-license", text)

    def test_real_binary_allows_a_plain_function(self) -> None:
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "if 'PFY-CLOUD-REVIEW' in '\\n'.join(sys.argv):\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "Path('app.py').write_text('def add(left, right):\\n    return left + right\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._run_task(
            grok,
            self._gate(),
            "add a function",
            extra=["--agentlint", "--retries", "0"],
            env={"PFY_AGENTLINT_BIN": str(REAL_BIN)},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        names = _git(self.repo, "ls-tree", "-r", "--name-only", payload["commit"]).stdout
        self.assertIn("app.py", names.splitlines())


def _local_tests_only(cls: type, parent: type) -> None:
    """Reuse the cloud fixture. Discover must not repeat the parent suite."""
    for name, value in parent.__dict__.items():
        if name.startswith("test") and callable(value) and name not in cls.__dict__:
            setattr(cls, name, None)


_local_tests_only(AgentLintBuildGuardTests, _CloudBuildFailureTests)
_local_tests_only(RealAgentLintBuildTests, _CloudBuildFailureTests)
# Discover loads every TestCase in this module. Drop the imported parent
# so its suite runs only from tests.test_pfy_build_cloud.
del _CloudBuildFailureTests


if __name__ == "__main__":
    unittest.main()
