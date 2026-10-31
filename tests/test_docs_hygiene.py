"""Docs links resolve, and closed eval rows are not left doing."""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MISSING_ADR = "0017-product-catalog-evaluation-handoff-harness.md"
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _missing_relative_links():
    missing = []
    for path in DOCS.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in LINK_RE.finditer(text):
            target = match.group(1).strip()
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            path_part = target.split("#", 1)[0].strip().split()[0]
            if not path_part or path_part.startswith("~/"):
                continue
            resolved = (path.parent / path_part).resolve()
            alt = (ROOT / path_part).resolve()
            if resolved.exists() or alt.exists():
                continue
            missing.append(f"{path.relative_to(ROOT)} -> {path_part}")
    return missing


class DocsHygieneTests(unittest.TestCase):
    def test_docs_relative_links_resolve(self):
        """Fail: a markdown link under docs/ points at a file that is not there.
        Recovery: point it at a real file, or drop the link. Do not add an ADR
        file just to satisfy the link."""
        missing = _missing_relative_links()
        self.assertEqual(missing, [])
        self.assertFalse((DOCS / "adr" / MISSING_ADR).exists())
        cited = (DOCS / "modules" / "pfylib.md").read_text(encoding="utf-8")
        self.assertNotIn(MISSING_ADR, cited)
        self.assertTrue((DOCS / "design" / "pfy-launcher.md").is_file())

    def test_closed_eval_rows_are_done_with_the_main_sha(self):
        """Fail: T-0070 or T-0074 is doing again while the landed files are gone,
        or the done note cites a sha that does not contain the file.
        Recovery: put the row back only if the file is not on origin/main."""
        todo = (DOCS / "TODO.md").read_text(encoding="utf-8")
        active = todo.split("## Active (sorted", 1)[1].split("## Done", 1)[0]
        done = todo.split("## Done", 1)[1]
        self.assertNotIn("| T-0070 | P1 | doing |", active)
        self.assertNotIn("| T-0074 | P1 | doing |", active)
        self.assertIn("| T-0070 | P1 | done |", done)
        self.assertIn("| T-0074 | P1 | done |", done)
        self.assertIn("`7197200`", done)
        self.assertIn("`c0d9072`", done)
        self.assertTrue((ROOT / "scripts" / "eval-auto.sh").is_file())
        self.assertTrue((ROOT / "examples" / "eval-harness" / "tasks" / "010-mutation-safety-note").is_dir())
        self.assertTrue((ROOT / "examples" / "eval-harness" / "tasks" / "013-stage-card").is_dir())
        for sha, rel in (
            ("7197200", "scripts/eval-auto.sh"),
            ("7197200", "examples/eval-harness/tasks/010-mutation-safety-note/score.py"),
            ("c0d9072", "scripts/eval-auto.sh"),
            ("c0d9072", "examples/eval-harness/tasks/013-stage-card/score.py"),
        ):
            probe = subprocess.run(
                ["git", "cat-file", "-e", f"{sha}:{rel}"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(probe.returncode, 0, f"{sha}:{rel} missing: {probe.stderr}")


if __name__ == "__main__":
    unittest.main()
