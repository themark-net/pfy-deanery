"""Drive the repository-harness probe with a stub binary. No network and no real tool.

Risk: a rewrite of AGENTS.md is reported as a clean adopt.
Fail: the clobber stub overwrites AGENTS.md and the probe must say so.
Recover: the keep stub leaves the seeded bytes alone.

Risk: an update that drops a local marker is reported as preserved.
Fail: the drop stub removes the marker and the probe must say so.
Recover: the keep stub leaves the marker in place.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "repository-harness" / "probe.py"

STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json
    import sys
    from pathlib import Path

    MODE = "__MODE__"
    args = sys.argv[1:]

    def directory():
        if "--directory" in args:
            return Path(args[args.index("--directory") + 1])
        return Path.cwd()

    def emit(payload):
        print(json.dumps(payload))
        raise SystemExit(0)

    cmd = args[0] if args else ""
    root = directory()
    if cmd == "install" and "--dry-run" in args:
        emit({
            "applied": False,
            "dry_run": True,
            "version": "0.1.10",
            "changes": [
                {"path": "AGENTS.md", "kind": "adopt"},
                {"path": "docs/README.md", "kind": "create"},
                {"path": "docs/WORKFLOW.md", "kind": "create"},
                {"path": "docs/plans/README.md", "kind": "create"},
            ],
        })
    if cmd == "install":
        agents = root / "AGENTS.md"
        if MODE == "clobber" and agents.is_file():
            agents.write_text("replaced\\n", encoding="utf-8")
        workflow = root / "docs" / "WORKFLOW.md"
        readme = root / "docs" / "README.md"
        workflow.parent.mkdir(parents=True, exist_ok=True)
        if not workflow.is_file():
            workflow.write_text("# Repository Workflow\\n", encoding="utf-8")
        if not readme.is_file():
            readme.write_text("# Documentation Map\\n", encoding="utf-8")
        emit({"applied": True, "version": "0.1.10", "changes": []})
    if cmd == "update":
        if MODE == "drop":
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                if "pfy-local-edit-1107" in text:
                    path.write_text(text.replace("pfy-local-edit-1107", ""), encoding="utf-8")
        emit({
            "applied": True,
            "from_version": "0.1.10",
            "to_version": "0.1.10",
            "conflicts": [],
        })
    if cmd == "doctor":
        emit({"healthy": True})
    if cmd == "status":
        emit({"files": []})
    sys.stderr.write("unhandled " + " ".join(args) + "\\n")
    raise SystemExit(2)
    """
)


class RepositoryHarnessProbeTest(unittest.TestCase):
    def _run(self, mode: str) -> dict:
        with tempfile.TemporaryDirectory(prefix="repository-harness-probe-") as tmp:
            root = Path(tmp)
            repo = root / "repo"
            (repo / "docs" / "plans").mkdir(parents=True)
            (repo / "AGENTS.md").write_text(
                "# router\n"
                "docs/DESIGN.md docs/adr/README.md docs/TODO.md docs/OPEN_QUESTIONS.md\n",
                encoding="utf-8",
            )
            (repo / "docs" / "plans" / "keep.md").write_text("keep this plan\n", encoding="utf-8")
            stub = root / "harness"
            stub.write_text(STUB.replace("__MODE__", mode), encoding="utf-8")
            stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
            out = root / "results.json"
            env = {
                "PATH": "/usr/bin:/bin",
                "HOME": str(root / "home"),
                "TMPDIR": str(root / "tmp"),
                "LANG": "C.UTF-8",
            }
            (root / "home").mkdir()
            (root / "tmp").mkdir()
            proc = subprocess.run(
                [sys.executable, str(PROBE), "--repo", str(repo), "--harness", str(stub), "--out", str(out)],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr[-800:] + proc.stdout[-400:])
            self.assertTrue(out.is_file())
            return json.loads(out.read_text(encoding="utf-8"))

    def test_rewrite_is_visible_and_adopt_keeps_bytes(self) -> None:
        bad = self._run("clobber")
        self.assertFalse(bad["install"]["agents_sha_same"])
        self.assertIn("AGENTS.md", bad["install"]["preexisting_changed"])
        self.assertEqual(bad["install"]["plans_changed"], [])
        good = self._run("keep")
        self.assertTrue(good["install"]["agents_sha_same"])
        self.assertEqual(good["install"]["preexisting_changed"], [])
        self.assertEqual(good["install"]["plans_changed"], [])

    def test_dropped_marker_is_visible_and_kept_marker_survives(self) -> None:
        bad = self._run("drop")
        self.assertGreater(len(bad["update"]["planted"]), 0)
        self.assertEqual(bad["update"]["markers_kept"], 0)
        self.assertFalse(bad["update"]["agents_keeps_pre_update_body"])
        good = self._run("keep")
        self.assertEqual(good["update"]["markers_kept"], len(good["update"]["planted"]))
        self.assertGreater(good["update"]["markers_kept"], 0)
        self.assertTrue(good["update"]["agents_keeps_pre_update_body"])
