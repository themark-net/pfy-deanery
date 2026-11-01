"""A harness symlink must be rejected without reading the target.

surface._present uses is_file and read_text, which follow links. A symlink
at a disallowed path whose target is mode 000 raises, so adopt crashes
instead of naming the path. The link must be rejected, the target bytes
must stay, and the repo snapshot must stay.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "examples" / "harness2-local" / "surface.py"
SOURCES = (
    "examples/typed-decisions-local/trial.py",
    ".grok/skills/jev-decision/SKILL.md",
    "AGENTS.md",
)
PLANTED = ".github/workflows/x.yml"


def _snap(root: Path) -> dict[str, bytes]:
    out = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()):
        out[path.relative_to(root).as_posix()] = path.read_bytes()
    return out


class Harness2SurfaceSymlinkTests(unittest.TestCase):
    def test_disallowed_symlink_is_rejected_without_reading_target(self) -> None:
        scratch_root = ROOT / "tmp" / "selfhost2-tests"
        scratch_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="h2-symlink-", dir=scratch_root) as td:
            root = Path(td)
            repo = root / "repo"
            harness = root / "harness"
            repo.mkdir()
            for rel in SOURCES:
                dest = repo / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / rel, dest)
            before = _snap(repo)
            exported = subprocess.run(
                [sys.executable, str(SURFACE), "export", "--repo", str(repo), "--dest", str(harness)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(exported.returncode, 0, exported.stderr)
            outside = root / "outside.yml"
            outside.write_bytes(b"secret-workflow\n")
            outside.chmod(0)
            planted = harness / PLANTED
            planted.parent.mkdir(parents=True, exist_ok=True)
            planted.symlink_to(outside)
            receipt = root / "receipt.json"
            try:
                adopted = subprocess.run(
                    [sys.executable, str(SURFACE), "adopt", "--repo", str(repo), "--harness", str(harness),
                     "--receipt", str(receipt)],
                    cwd=ROOT, text=True, capture_output=True, check=False,
                )
            finally:
                outside.chmod(stat.S_IRUSR | stat.S_IWUSR)
            blob = adopted.stdout + adopted.stderr
            self.assertNotIn("Traceback", blob, blob)
            self.assertEqual(adopted.returncode, 2, blob)
            self.assertIn(PLANTED, blob)
            got = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertIn(PLANTED, got.get("rejected_paths") or [])
            self.assertEqual(outside.read_bytes(), b"secret-workflow\n")
            self.assertTrue(planted.is_symlink())
            self.assertEqual(os.readlink(planted), str(outside))
            self.assertEqual(_snap(repo), before)


if __name__ == "__main__":
    unittest.main()
