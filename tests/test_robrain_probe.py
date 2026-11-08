"""RoBrain probe failure modes.

The child is eval/evq1107/robrain/probe.py. A real run needs the pinned
VetoBench build under ~/.cache/pfy/tools/robrain/. These tests pass a stub
node and a temp --out. No network, no model, no podman, no real node.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "robrain" / "probe.py"
CORPUS = ROOT / "eval" / "evq1107" / "robrain" / "corpus.json"
SCENARIOS = ROOT / "eval" / "evq1107" / "robrain" / "scenarios.json"

STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, sys
    from pathlib import Path
    here = Path(__file__).resolve().parent
    mode = (here / "mode").read_text(encoding="utf-8").strip()
    (here / "home_seen").write_text(__import__("os").environ.get("HOME", ""), encoding="utf-8")
    args = sys.argv[1:]
    if args == ["--version"]:
        sys.stdout.write("v0.0-stub\\n")
        raise SystemExit(0)
    seen = here / "args.json"
    prev = json.loads(seen.read_text(encoding="utf-8")) if seen.is_file() else []
    prev.append(args)
    seen.write_text(json.dumps(prev), encoding="utf-8")
    if "--live" in args:
        (here / "live_called").write_text("yes", encoding="utf-8")
        raise SystemExit(3)
    if args and args[0].endswith("rank.mjs"):
        if mode == "badjson":
            sys.stdout.write("NOT JSON\\n")
            raise SystemExit(1)
        fixture = json.loads(Path(args[2]).read_text(encoding="utf-8"))
        rank = 9 if mode == "miss" else 1
        rows = [{
            "id": row["id"],
            "veto": row["veto_decision_id"],
            "trap": row.get("trap"),
            "rank_files": rank,
            "rank_nofiles": rank,
        } for row in fixture["scenarios"]]
        sys.stdout.write(json.dumps({"rows": rows}) + "\\n")
        raise SystemExit(0)
    if args and args[0] == "dist/run.js":
        rows = 4 if "lifecycle" in args else 10
        if mode == "pinbad" and "lifecycle" not in args:
            sys.stdout.write("veto recall@5: 0.40 with files known (gate: >= 0.80) · 0.10 without\\n")
            sys.stdout.write("FAIL\\n")
            raise SystemExit(1)
        files = "1.00"
        nofiles = "1.00" if "lifecycle" in args else "0.70"
        lines = []
        for i in range(1, rows + 1):
            lines.append("s%02d      d%03d           1 ✓        1 ✓" % (i, i))
        lines.append(
            "veto recall@5: %s with files known (gate: >= 0.80) · %s without" % (files, nofiles)
        )
        lines.append("(offline run - behavioral layer not started)")
        lines.append("✓ PASS")
        sys.stdout.write("\\n".join(lines) + "\\n")
        raise SystemExit(0)
    sys.stderr.write("unexpected args\\n")
    raise SystemExit(2)
    """
)

PODMAN = textwrap.dedent(
    """\
    #!/bin/sh
    echo called >> "$(dirname "$0")/podman_called"
    exit 99
    """
)


class RobrainProbeTest(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        node = self.bin / "node"
        node.write_text(STUB, encoding="utf-8")
        node.chmod(node.stat().st_mode | stat.S_IEXEC)
        podman = self.bin / "podman"
        podman.write_text(PODMAN, encoding="utf-8")
        podman.chmod(podman.stat().st_mode | stat.S_IEXEC)
        self.veto = self.tmp / "vetobench"
        (self.veto / "dist").mkdir(parents=True)
        (self.veto / "dist" / "run.js").write_text("// stub dist\n", encoding="utf-8")
        (self.veto / "dist" / "adapters.js").write_text("// stub dist\n", encoding="utf-8")
        self.home = self.tmp / "home"
        self.real = self.tmp / "real-home"
        self.real.mkdir()
        (self.real / ".robrain").mkdir()
        (self.real / ".robrain" / "keep.txt").write_text("same\n", encoding="utf-8")
        self.repo = self.tmp / "repo"
        stages = self.repo / "data" / "stages"
        stages.mkdir(parents=True)
        (stages / "mempalace.json").write_text(
            json.dumps({"name": "MemPalace", "integration_stage": "I0", "uses": "Verbatim local memory."}),
            encoding="utf-8",
        )
        (stages / "other.json").write_text(
            json.dumps({"name": "Other", "integration_stage": "I1", "uses": "A memorable footnote, not a store."}),
            encoding="utf-8",
        )
        (stages / "robrain.json").write_text(
            json.dumps({"name": "RoBrain", "integration_stage": "I0", "uses": "Decision memory with vetoes."}),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self._td.cleanup()

    def write_mode(self, mode: str) -> None:
        (self.bin / "mode").write_text(mode, encoding="utf-8")

    def run_probe(self, mode: str) -> dict:
        self.write_mode(mode)
        out = self.tmp / f"{mode}.json"
        before = (self.real / ".robrain" / "keep.txt").read_bytes()
        proc = subprocess.run(
            [
                sys_executable(),
                str(PROBE),
                "--out", str(out),
                "--repo", str(self.repo),
                "--node", str(self.bin / "node"),
                "--vetobench", str(self.veto),
                "--corpus", str(CORPUS),
                "--scenarios", str(SCENARIOS),
                "--home", str(self.home),
                "--real-home", str(self.real),
            ],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((self.real / ".robrain" / "keep.txt").read_bytes(), before)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertTrue(data["home_unchanged"])
        self.assertIsNone(data["bytes"]["checkout"])
        self.assertEqual((self.bin / "home_seen").read_text(encoding="utf-8"), str(self.home))
        self.assertFalse((self.bin / "podman_called").exists())
        self.assertFalse((self.bin / "live_called").exists())
        blob = json.dumps(data["commands"])
        self.assertNotIn("--live", blob)
        names = [row["file"] for row in data["cards"]]
        self.assertEqual(names, ["mempalace.json"])
        return data

    def test_rank_past_five_is_a_miss_and_rank_one_recovers(self) -> None:
        missed = self.run_probe("miss")
        self.assertEqual(missed["robrain_status"], "RAN")
        self.assertEqual(missed["robrain"]["no_files"]["hits"], 0)
        self.assertEqual(missed["robrain"]["files_known"]["hits"], 0)
        overlap = missed["overlap_adr"]["no_files"]["hits"]
        self.assertIsInstance(overlap, int)
        hit = self.run_probe("hit")
        self.assertEqual(hit["robrain"]["no_files"]["hits"], 10)
        self.assertEqual(hit["robrain"]["files_known"]["hits"], 10)
        self.assertEqual(hit["overlap_adr"]["no_files"]["hits"], overlap)
        self.assertEqual(hit["none_memory_hits"], 0)
        self.assertEqual(hit["flatfile_hits"], 10)

    def test_non_json_is_not_a_score_and_json_recovers(self) -> None:
        bad = self.run_probe("badjson")
        self.assertEqual(bad["robrain_status"], "FAIL")
        self.assertIsNone(bad["robrain"])
        self.assertIsNone(bad["beats_adr_text"])
        good = self.run_probe("hit")
        self.assertEqual(good["robrain_status"], "RAN")
        self.assertEqual(good["robrain"]["no_files"]["recall"], 1.0)

    def test_bad_pin_is_not_ok_and_the_offline_line_recovers(self) -> None:
        bad = self.run_probe("pinbad")
        self.assertFalse(bad["upstream_pin_ok"])
        self.assertFalse(bad["upstream"]["default"]["offline"])
        good = self.run_probe("hit")
        self.assertTrue(good["upstream_pin_ok"])
        self.assertTrue(good["upstream"]["default"]["offline"])
        self.assertTrue(good["upstream"]["lifecycle"]["offline"])
        self.assertEqual(good["upstream"]["default"]["recall"]["nofiles"], 0.70)
        self.assertEqual(good["upstream"]["lifecycle"]["rows"], 4)
        self.assertEqual(good["postgres_pgvector"]["status"], "SKIPPED")

    def test_missing_dist_skips_and_a_present_dist_scores(self) -> None:
        (self.veto / "dist" / "run.js").unlink()
        self.write_mode("hit")
        out = self.tmp / "skip.json"
        proc = subprocess.run(
            [
                sys_executable(),
                str(PROBE),
                "--out", str(out),
                "--repo", str(self.repo),
                "--node", str(self.bin / "node"),
                "--vetobench", str(self.veto),
                "--corpus", str(CORPUS),
                "--scenarios", str(SCENARIOS),
                "--home", str(self.home),
                "--real-home", str(self.real),
            ],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["robrain_status"], "SKIPPED")
        self.assertIsNone(data["robrain"])
        self.assertEqual(data["commands"], [])
        self.assertFalse((self.bin / "args.json").exists())
        (self.veto / "dist" / "run.js").write_text("// stub dist\n", encoding="utf-8")
        scored = self.run_probe("hit")
        self.assertEqual(scored["robrain_status"], "RAN")
        self.assertEqual(scored["robrain"]["no_files"]["hits"], 10)


def sys_executable() -> str:
    return os.environ.get("PFY_PYTHON") or __import__("sys").executable


if __name__ == "__main__":
    unittest.main()
