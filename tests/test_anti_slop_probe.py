#!/usr/bin/env python3
"""Drive the anti-slop probe with a stub pack. No network and no real tree.

A missing node must not look like a passed self-check. A self-check that
exits 1 must still leave the lexical score on disk. A version mismatch
must not look like the pinned release. An external heading that uses an
em dash must count: the pack's own carve-out does not apply here.
"""

from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "anti-slop" / "probe.py"

CORE = """#### R-02 \u2014 Copywriting

- **FORBIDDEN**: em dash character (`\u2014`) in any text

#### R-15 \u2014 CTA (Call to Action)

- **FORBIDDEN**: "Get Started", "Learn More", "Explore" as default CTAs

#### R-16 \u2014 Copywriting & Buzzwords

- **FORBIDDEN**: "AI Powered", "Seamless"
"""

CODE_SKILL = """---
name: antislop-code
description: comments
---

## Comments That Add Nothing

- **Tell:** `// Main logic` above the code.

## Not a Ban (preserve these)

- `// Stripe may retry webhook deliveries for up to three days.`
"""


def write_pack(src: Path, version: str = "3.2.20") -> None:
    (src / "skills" / "antislop").mkdir(parents=True)
    (src / "skills" / "antislop-code").mkdir()
    (src / "scripts").mkdir()
    (src / "antislop.md").write_text(CORE, encoding="utf-8")
    (src / "skills" / "antislop" / "VERSION").write_text(version + "\n", encoding="utf-8")
    (src / "package.json").write_text(
        json.dumps({"version": "3.2.20"}) + "\n", encoding="utf-8"
    )
    (src / "skills" / "antislop-code" / "SKILL.md").write_text(CODE_SKILL, encoding="utf-8")
    (src / "scripts" / "check-repo.mjs").write_text("// stub\n", encoding="utf-8")


def write_fixtures(folder: Path) -> None:
    folder.mkdir()
    (folder / "slop.md").write_text(
        "Ship it \u2014 now.\nGet Started today. It is AI Powered.\n",
        encoding="utf-8",
    )
    (folder / "clean.md").write_text(
        "An exploration of the pin uses a comma.\n",
        encoding="utf-8",
    )
    (folder / "heading.md").write_text(
        "#### R-02 \u2014 Copywriting\n",
        encoding="utf-8",
    )
    (folder / "notes.js").write_text(
        "// Main logic\n// Stripe may retry webhook deliveries for up to three days.\n",
        encoding="utf-8",
    )


class AntiSlopProbeTest(unittest.TestCase):
    def _run(self, src: Path, fixtures: Path, out: Path, node: str, cache: Path) -> subprocess.CompletedProcess:
        repo = cache / "repo"
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "note.txt").write_text("plain note\n", encoding="utf-8")
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(cache / "real-home"),
            "LANG": "C.UTF-8",
            "ANTISLOP_CACHE": str(cache),
        }
        (cache / "real-home").mkdir(exist_ok=True)
        return subprocess.run(
            [
                sys.executable,
                str(PROBE),
                "--src", str(src),
                "--fixtures", str(fixtures),
                "--repo", str(repo),
                "--out", str(out),
                "--node", node,
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )

    def test_missing_node_is_skipped_and_heading_dash_counts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="antislop-probe-") as tmp:
            folder = Path(tmp)
            src = folder / "src"
            fixtures = folder / "fixtures"
            write_pack(src)
            write_fixtures(fixtures)
            out = folder / "results.json"
            proc = self._run(src, fixtures, out, str(folder / "missing-node"), folder / "cache")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            body = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(body["upstream"]["check_repo"]["status"], "skipped")
            self.assertFalse(body["upstream"]["check_repo"]["ok"])
            self.assertTrue(body["lexical"]["passes_agree"])
            files = {row["name"]: row for row in body["lexical"]["fixture_files"]}
            self.assertGreaterEqual(files["slop.md"]["em_dash"], 1)
            self.assertGreaterEqual(files["slop.md"]["phrase_hits"]["Get Started"], 1)
            self.assertGreaterEqual(files["slop.md"]["phrase_hits"]["AI Powered"], 1)
            self.assertEqual(files["clean.md"]["em_dash"], 0)
            self.assertEqual(files["clean.md"]["phrase_hits"]["Explore"], 0)
            self.assertEqual(files["clean.md"]["phrase_hits"]["Get Started"], 0)
            self.assertGreaterEqual(files["heading.md"]["em_dash"], 1)
            self.assertEqual(files["notes.js"]["comment_hits"].get("// Main logic"), 1)
            self.assertNotIn(
                "// Stripe may retry webhook deliveries for up to three days.",
                files["notes.js"]["comment_hits"],
            )
            self.assertNotIn("Ship it", out.read_text(encoding="utf-8"))

    def test_failed_self_check_still_writes_the_score(self) -> None:
        with tempfile.TemporaryDirectory(prefix="antislop-probe-") as tmp:
            folder = Path(tmp)
            src = folder / "src"
            fixtures = folder / "fixtures"
            write_pack(src)
            write_fixtures(fixtures)
            node = folder / "node"
            node.write_text("#!/bin/sh\necho '1 of 13 checks failed'\nexit 1\n", encoding="utf-8")
            node.chmod(node.stat().st_mode | stat.S_IEXEC)
            out = folder / "results.json"
            proc = self._run(src, fixtures, out, str(node), folder / "cache")
            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            self.assertTrue(out.is_file())
            body = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(body["upstream"]["check_repo"]["status"], "fail")
            self.assertGreater(body["lexical"]["fixtures"]["multi_word_hits"], 0)
            self.assertTrue(body["lexical"]["passes_agree"])
            self.assertGreaterEqual(body["rules"]["defined"], 3)

    def test_version_mismatch_is_not_the_pin(self) -> None:
        with tempfile.TemporaryDirectory(prefix="antislop-probe-") as tmp:
            folder = Path(tmp)
            src = folder / "src"
            fixtures = folder / "fixtures"
            write_pack(src, version="9.9.9")
            write_fixtures(fixtures)
            out = folder / "results.json"
            proc = self._run(src, fixtures, out, str(folder / "missing-node"), folder / "cache")
            self.assertEqual(proc.returncode, 2, proc.stderr)
            body = json.loads(out.read_text(encoding="utf-8"))
            self.assertFalse(body["versions"]["agree"])
            self.assertIsNone(body["versions"]["version"])
            self.assertIn("lexical", body)
            self.assertGreater(body["lexical"]["fixtures"]["em_dash"], 0)


if __name__ == "__main__":
    unittest.main()
