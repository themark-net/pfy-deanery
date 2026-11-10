"""trial.py records a sandlock trial with the profile confine.py built.

How this fails: a trial record claims a sandbox it did not have, has no
profile, or leaks a host home path into a public record. How we recover:
outcome is ok only when the command ran inside sandlock, exited 0, and a
profile was written; paths are ./ or $HOME relative; a fallback run logs
"sandlock: unsandboxed" and the record says failed. S-profile-readonly in
data/promotion-rules.json passes on a clean record.
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

from tests.test_integrate_sandlock_confine import REAL

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TRIAL = ROOT / "scripts" / "integrations" / "sandlock" / "trial.py"

from scripts import promotion_rules as pr  # noqa: E402

SCAN = "import json,sys; open(sys.argv[1],'w').write(json.dumps({'verdict':'CLEAN','findings':[]}))"


class SandlockTrialProfileTest(unittest.TestCase):
    def _run(self, td: Path, real: Path | None, slug: str) -> tuple[subprocess.CompletedProcess, dict]:
        env = os.environ.copy()
        env["TRACE"] = str(td / "trace.log")
        env.pop("CHECK_FAIL", None)
        if real is None:
            env["SANDLOCK_REAL"] = str(td / "missing-sandlock")
        else:
            env["SANDLOCK_REAL"] = str(real)
        out = td / "sandbox-trial.json"
        proc = subprocess.run(
            [sys.executable, str(TRIAL), "--slug", slug, "--out", str(out), "--read", str(td), "--scan-json", "scan.json",
             "--", sys.executable, "-c", SCAN, "{stage}/scan.json"],
            env=env, capture_output=True, text=True, timeout=120, cwd=ROOT,
        )
        return proc, json.loads(out.read_text(encoding="utf-8"))

    def test_clean_trial_records_a_readonly_profile(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            fake = td / "sandlock"
            fake.write_text(REAL)
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            proc, record = self._run(td, fake, "zz-trial-ok")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(record["outcome"], "ok")
            self.assertEqual(record["scan_verdict"], "CLEAN")
            self.assertEqual(record["findings"], 0)
            self.assertEqual(record["unsandboxed_lines"], 0)
            profile = record["profile"]
            self.assertEqual(profile["network"], "deny")
            self.assertTrue(profile["clean_env"])
            self.assertFalse(profile["sudo"])
            self.assertEqual(pr.profile_problems(profile), [])
            text = json.dumps(record)
            self.assertNotIn(str(Path.home()) + "/", text)
            self.assertNotIn(str(ROOT), text)
            self.assertTrue(all(item.startswith("./tmp/") or item == "/dev/null" for item in profile["writes"]), profile["writes"])

    def test_unsandboxed_fallback_is_not_ok(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            proc, record = self._run(td, None, "zz-trial-open")
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(record["outcome"], "failed")
            self.assertGreaterEqual(record["unsandboxed_lines"], 1)
            self.assertIsNone(record["profile"])


if __name__ == "__main__":
    unittest.main()
