"""Static skill scan wrapper. Stubs stand in for SkillSpector. No network and no real binary.

How it fails and how we recover:
- missing binary exits 2 with a next step; a stub on PATH then exits 0
- garbage or a nonzero exit with no JSON exits 2; a SAFE stub then exits 0
- DO_NOT_INSTALL exits 1 and names the path; a SAFE stub then exits 0
- CAUTION is not safe; --allow-caution is the recovery
- a receipt path that cannot be written exits 2 and still deletes the raw scanner JSON
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pfy_skill_scan.py"

SECRET = "SUPER_SECRET_SNIPPET_DO_NOT_LEAK"

SAFE_BODY = r"""
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
Path(os.environ["STUB_ARGV"]).write_text(json.dumps({
    "argv": args,
    "provider": os.environ.get("SKILLSPECTOR_PROVIDER"),
}))
out = Path(args[args.index("--output") + 1])
out.write_text(json.dumps({
    "risk_assessment": {"score": 0, "severity": "LOW", "recommendation": "SAFE"},
    "issues": [],
    "metadata": {"llm_requested": False},
}))
"""

FLAGGED_BODY = r"""
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
out = Path(args[args.index("--output") + 1])
out.write_text(json.dumps({
    "risk_assessment": {"score": 93, "severity": "CRITICAL", "recommendation": "DO_NOT_INSTALL"},
    "issues": [{
        "id": "P1",
        "category": "prompt injection",
        "severity": "HIGH",
        "finding": "Instruction override",
        "code_snippet": "%s",
        "explanation": "%s",
    }],
}))
sys.exit(1)
""" % (SECRET, SECRET)

CAUTION_BODY = r"""
import json, sys
from pathlib import Path
args = sys.argv[1:]
out = Path(args[args.index("--output") + 1])
out.write_text(json.dumps({
    "risk_assessment": {"score": 40, "severity": "MEDIUM", "recommendation": "CAUTION"},
    "issues": [{
        "id": "SC2",
        "category": "supply chain",
        "severity": "MEDIUM",
        "finding": "curl pipe to shell",
    }],
}))
"""

GARBAGE_BODY = r"""
import sys
from pathlib import Path
args = sys.argv[1:]
out = Path(args[args.index("--output") + 1])
out.write_text("this is not json\n")
sys.exit(0)
"""

NONZERO_BODY = r"""
import sys
sys.stderr.write("scanner crashed\n")
sys.exit(3)
"""

SPLIT_BODY = r"""
import json, sys
from pathlib import Path
args = sys.argv[1:]
skill = args[args.index("scan") + 1]
out = Path(args[args.index("--output") + 1])
if skill.endswith("evil"):
    rec, score, issues, code = "DO_NOT_INSTALL", 90, [{
        "id": "PE3", "category": "privilege escalation", "severity": "HIGH",
        "finding": "reads a private key",
    }], 1
else:
    rec, score, issues, code = "SAFE", 0, [], 0
out.write_text(json.dumps({
    "risk_assessment": {"score": score, "severity": "HIGH" if code else "LOW", "recommendation": rec},
    "issues": issues,
}))
sys.exit(code)
"""


class SkillScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.home = self.td / "home"
        self.state = self.td / "state"
        self.bindir = self.td / "bin"
        self.skill = self.td / "skill"
        for path in (self.home, self.state, self.bindir, self.skill):
            path.mkdir()
        (self.skill / "SKILL.md").write_text("# skill\n", encoding="utf-8")
        self.argv_path = self.td / "argv.json"
        self.out = self.td / "receipt.json"

    def tearDown(self):
        self.tmp.cleanup()

    def write_stub(self, body: str) -> Path:
        path = self.bindir / "skillspector"
        path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
        return path

    def run_scan(self, args, stub=None, extra_env=None, on_path=False):
        env = {
            "PATH": str(self.bindir) if on_path else "/usr/bin:/bin",
            "HOME": str(self.home),
            "PFY_STATE_DIR": str(self.state),
            "STUB_ARGV": str(self.argv_path),
            "SKILLSPECTOR_PROVIDER": "ollama",
        }
        if stub is not None and not on_path:
            env["PFY_SKILLSPECTOR_BIN"] = str(self.write_stub(stub))
        elif stub is not None and on_path:
            self.write_stub(stub)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_missing_binary_recovers_when_stub_is_on_path(self):
        """Fail: no binary exits 2 and names the next step.
        Recovery: the same call with a SAFE stub on PATH exits 0 and records SAFE.
        A set but missing PFY_SKILLSPECTOR_BIN does not fall through to PATH.
        """
        missing = self.run_scan(["--out", str(self.out), str(self.skill)], on_path=True)
        self.assertEqual(missing.returncode, 2, missing.stdout + missing.stderr)
        self.assertIn("Next:", missing.stdout)
        self.assertIn("PFY_SKILLSPECTOR_BIN", missing.stdout)
        receipt = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["verdict"], "ERROR")
        self.assertEqual(receipt["llm"], False)

        pinned_missing = self.run_scan(
            ["--out", str(self.out), str(self.skill)],
            stub=SAFE_BODY,
            on_path=True,
            extra_env={"PFY_SKILLSPECTOR_BIN": str(self.td / "missing-bin")},
        )
        self.assertEqual(pinned_missing.returncode, 2, pinned_missing.stdout)

        recovered = self.run_scan(
            ["--out", str(self.out), str(self.skill)],
            stub=SAFE_BODY,
            on_path=True,
        )
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        receipt = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["verdict"], "SAFE")
        self.assertEqual(receipt["paths"][0]["recommendation"], "SAFE")
        self.assertEqual(receipt["mode"], "static")
        recorded = json.loads(self.argv_path.read_text(encoding="utf-8"))
        self.assertIn("scan", recorded["argv"])
        self.assertIn("--no-llm", recorded["argv"])
        self.assertIsNone(recorded["provider"])

    def test_cache_bin_runs_when_env_and_path_miss(self):
        """Fail: no binary on PATH and no PFY_SKILLSPECTOR_BIN exits 2.
        Recovery: an executable at $HOME/.cache/pfy/bin/skillspector exits 0 SAFE.
        A set but missing PFY_SKILLSPECTOR_BIN still does not use that file.
        """
        missing = self.run_scan(["--out", str(self.out), str(self.skill)])
        self.assertEqual(missing.returncode, 2, missing.stdout + missing.stderr)

        cache_bin = self.home / ".cache" / "pfy" / "bin"
        cache_bin.mkdir(parents=True)
        stub = cache_bin / "skillspector"
        stub.write_text(f"#!{sys.executable}\n{SAFE_BODY}", encoding="utf-8")
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        recovered = self.run_scan(["--out", str(self.out), str(self.skill)])
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        receipt = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["verdict"], "SAFE")

        pinned = self.run_scan(
            ["--out", str(self.out), str(self.skill)],
            extra_env={"PFY_SKILLSPECTOR_BIN": str(self.td / "missing-bin")},
        )
        self.assertEqual(pinned.returncode, 2, pinned.stdout + pinned.stderr)

    def test_garbage_and_nonzero_recover_to_safe(self):
        """Fail: garbage JSON and a nonzero exit with no report are unreadable (exit 2).
        Recovery: a SAFE stub on the same path exits 0.
        """
        garbage = self.run_scan(["--out", str(self.out), str(self.skill)], stub=GARBAGE_BODY)
        self.assertEqual(garbage.returncode, 2, garbage.stdout + garbage.stderr)
        self.assertIn("Next:", garbage.stdout)
        self.assertIn(str(self.skill), garbage.stdout)

        crashed = self.run_scan(["--out", str(self.out), str(self.skill)], stub=NONZERO_BODY)
        self.assertEqual(crashed.returncode, 2, crashed.stdout + crashed.stderr)
        self.assertIn("Next:", crashed.stdout)
        self.assertIn("scanner crashed", crashed.stdout)

        recovered = self.run_scan(["--out", str(self.out), str(self.skill)], stub=SAFE_BODY)
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        receipt = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["verdict"], "SAFE")

    def test_flagged_skill_exits_1_and_hides_snippet(self):
        """Fail: DO_NOT_INSTALL exits 1 and prints the path, recommendation, and finding id.
        The receipt keeps the short title and drops the code snippet.
        Recovery: a SAFE stub on the same path exits 0.
        A second safe path does not hide the flagged one.
        """
        flagged = self.run_scan(["--out", str(self.out), str(self.skill)], stub=FLAGGED_BODY)
        self.assertEqual(flagged.returncode, 1, flagged.stdout + flagged.stderr)
        self.assertIn(str(self.skill), flagged.stdout)
        self.assertIn("DO_NOT_INSTALL", flagged.stdout)
        self.assertIn("P1", flagged.stdout)
        self.assertNotIn(SECRET, flagged.stdout)
        raw = self.out.read_text(encoding="utf-8")
        self.assertNotIn(SECRET, raw)
        self.assertFalse((self.out.parent / ".skill-scan-work").exists())
        receipt = json.loads(raw)
        self.assertEqual(receipt["verdict"], "FLAGGED")
        self.assertEqual(receipt["paths"][0]["findings"][0]["title"], "Instruction override")
        self.assertEqual(receipt["paths"][0]["findings"][0]["category"], "prompt injection")

        evil = self.td / "evil"
        evil.mkdir()
        (evil / "SKILL.md").write_text("# evil\n", encoding="utf-8")
        both = self.run_scan(
            ["--out", str(self.out), str(self.skill), str(evil)],
            stub=SPLIT_BODY,
        )
        self.assertEqual(both.returncode, 1, both.stdout + both.stderr)
        self.assertIn(str(evil), both.stdout)
        self.assertIn("PE3", both.stdout)
        receipt = json.loads(self.out.read_text(encoding="utf-8"))
        by_path = {row["path"]: row for row in receipt["paths"]}
        self.assertTrue(by_path[str(self.skill)]["ok"])
        self.assertFalse(by_path[str(evil)]["ok"])
        self.assertEqual(by_path[str(evil)]["recommendation"], "DO_NOT_INSTALL")

        recovered = self.run_scan(["--out", str(self.out), str(self.skill)], stub=SAFE_BODY)
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)

    def test_unwritable_receipt_still_drops_raw_report(self):
        """Fail: the receipt path is a directory, so the write fails (exit 2).
        The raw scanner JSON, which holds the code snippet, is still removed.
        Recovery: the same stub with a writable --out exits 1 and leaves no scratch dir.
        """
        blocked = self.td / "not-a-file"
        blocked.mkdir()
        result = self.run_scan(["--out", str(blocked), str(self.skill)], stub=FLAGGED_BODY)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("Next:", result.stdout)
        self.assertNotIn(SECRET, result.stdout)
        self.assertFalse((blocked.parent / ".skill-scan-work").exists())
        self.assertEqual(list(self.td.rglob("report-*.json")), [])

        recovered = self.run_scan(["--out", str(self.out), str(self.skill)], stub=FLAGGED_BODY)
        self.assertEqual(recovered.returncode, 1, recovered.stdout + recovered.stderr)
        self.assertFalse((self.out.parent / ".skill-scan-work").exists())
        self.assertNotIn(SECRET, self.out.read_text(encoding="utf-8"))

    def test_caution_is_not_safe_until_allow_caution(self):
        """Fail: CAUTION exits 1 even when the scanner process exits 0.
        Recovery: the same report with --allow-caution exits 0.
        """
        blocked = self.run_scan(["--out", str(self.out), str(self.skill)], stub=CAUTION_BODY)
        self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
        self.assertIn("CAUTION", blocked.stdout)
        self.assertIn("SC2", blocked.stdout)
        receipt = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["verdict"], "FLAGGED")
        self.assertFalse(receipt["paths"][0]["ok"])

        allowed = self.run_scan(
            ["--allow-caution", "--out", str(self.out), str(self.skill)],
            stub=CAUTION_BODY,
        )
        self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)
        receipt = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["verdict"], "SAFE")
        self.assertTrue(receipt["allow_caution"])
        self.assertEqual(receipt["paths"][0]["recommendation"], "CAUTION")

    def test_default_receipt_uses_state_dir(self):
        """No --out writes $PFY_STATE_DIR/skill-scan.json and does not require a pre-created file."""
        proc = self.run_scan([str(self.skill)], stub=SAFE_BODY)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        receipt_path = self.state / "skill-scan.json"
        self.assertTrue(receipt_path.is_file())
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["verdict"], "SAFE")
        self.assertFalse((self.home / ".pfy-mentat").exists())


if __name__ == "__main__":
    unittest.main()
