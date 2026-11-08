#!/usr/bin/env python3
"""Drive the sloptrim probe with a stub detect.py. No network and no clone.

A stub that prints garbage must not exit 0 or write a separation number.
The same probe recovers when the stub returns two stable scores.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "sloptrim" / "probe.py"

STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json
    import sys

    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        sys.stderr.write("no file\\n")
        sys.exit(2)
    text = open(args[0], encoding="utf-8").read()
    if "FORCE_BAD" in text:
        sys.stdout.write("not json\\n")
        sys.exit(1)
    score = 80 if "SLOP_MARK" in text else 5
    body = {
        "_metrics": {
            "ai_tell_score": score,
            "ai_tell_band": "heavy tells" if score >= 60 else "clean",
            "confidence": "high",
            "patterns_flagged": 1 if score >= 60 else 0,
            "invisible_chars": 0,
        }
    }
    if score >= 60:
        body["69_canonical_slop"] = {"count": 1, "label": "stub"}
    sys.stdout.write(json.dumps(body))
    """
)


class SloptrimProbeTest(unittest.TestCase):
    def _run(self, detect: Path, folder: Path, out: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(PROBE),
                "--detect",
                str(detect),
                "--only",
                str(folder),
                "--root",
                str(folder),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": str(folder),
                "TMPDIR": str(folder),
                "LANG": "C.UTF-8",
            },
        )

    def test_bad_stdout_fails_and_stable_scores_recover(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sloptrim-probe-") as tmp:
            folder = Path(tmp)
            stub = folder / "detect.py"
            stub.write_text(STUB, encoding="utf-8")
            bad = folder / "bad.md"
            bad.write_text("FORCE_BAD\n", encoding="utf-8")
            out = folder / "results.json"
            failed = self._run(stub, folder, out)
            self.assertNotEqual(failed.returncode, 0, failed.stdout + failed.stderr)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertIs(payload["ok"], False)
            self.assertNotIn("summary", payload)

            bad.unlink()
            (folder / "plain.md").write_text("The dock opens at six.\n", encoding="utf-8")
            (folder / "slop.md").write_text("SLOP_MARK on the page.\n", encoding="utf-8")
            recovered = self._run(stub, folder, out)
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertIs(payload["ok"], True)
            self.assertEqual(payload["summary"]["separation"], 75)
            self.assertEqual(payload["summary"]["max_abs_delta"], 0)
            self.assertEqual(payload["summary"]["harness_comparisons"], 0)


if __name__ == "__main__":
    unittest.main()
