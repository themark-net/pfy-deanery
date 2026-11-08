"""MemPalace probe: a wrong top-1 stays a miss until top-5, a failed mine retries.

The child is eval/evq1107/mempalace/probe.py. Each test runs that script
against a stub mempalace binary in a temp dir. No network, no model, no
real mempalace binary.
"""

from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "mempalace" / "probe.py"

FILES = {
    "docs/ops/integration-stages.md": "Promote toward onboard only if the value gate passes.\n",
    "docs/ops/MODULAR-CI.md": "Give each tool its own state file.\n",
    "AGENTS.md": "LOCAL_CODER_MODEL names the worker model.\n",
    "data/stages/codebase-memory-mcp.json": '{"uses": "Primary code-graph MCP"}\n',
    "docs/eval/TOOLSET-RANKING.md": (
        "| H1 | harness2 showed no gain and there is no repeatable score |\n"
        "| 10 | 149 MemPalace | memory | Post-MVP memory slot | M to L | I0 |\n"
    ),
    "data/stages/skill-up.json": '{"uses": "Grade a with-skill run against a no-skill baseline."}\n',
    "sources/entries/132-ai-memory.md": "A claim-once guarantee stops two bots from taking the same handoff.\n",
}

STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import os, sys
    from pathlib import Path
    args = sys.argv[1:]
    if "--version" in args:
        sys.stdout.write("MemPalace 3.12.0\\n")
        raise SystemExit(0)
    home = Path(os.environ["HOME"])
    (home / ".mempalace").mkdir(parents=True, exist_ok=True)
    (home / ".mempalace" / "touched").write_text("stub\\n", encoding="utf-8")
    mapping = (
        ("onboarded", "value-gate.md", "handoff"),
        ("share state", "state-file.md", "handoff"),
        ("environment variable", "worker-model.md", "handoff"),
        ("code graph", "code-graph.md", "handoff"),
        ("memory slot", "memory-slot.md", "ranking"),
        ("harness2", "h1-gap.md", "ranking"),
        ("grades a run", "skill-grade.md", "ranking"),
        ("two bots", "claim-once.md", "ranking"),
    )

    def target_after(flag):
        return Path(args[args.index(flag) + 1])

    if "init" in args:
        dest = target_after("init")
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "mempalace.yaml").write_text("rooms: []\\n", encoding="utf-8")
        raise SystemExit(0)
    if "mine" in args:
        dest = target_after("mine")
        dest.mkdir(parents=True, exist_ok=True)
        counter = dest / ".attempts"
        n = int(counter.read_text(encoding="utf-8")) if counter.is_file() else 0
        counter.write_text(str(n + 1), encoding="utf-8")
        if Path(__file__).with_name("fail-once").is_file() and n == 0:
            sys.stderr.write("mine failed once\\n")
            raise SystemExit(1)
        sys.stdout.write("  Drawers filed: 4\\n")
        raise SystemExit(0)
    if "search" in args:
        query = args[args.index("search") + 1]
        wing = args[args.index("--wing") + 1] if "--wing" in args else None
        picked = None
        for phrase, source, owner in mapping:
            if phrase in query:
                picked = (source, owner)
                break
        if picked is None:
            sys.stderr.write("unmapped query\\n")
            raise SystemExit(2)
        source, owner = picked
        if wing and wing != owner:
            sys.stdout.write("  [1] %s / general\\n      Source: other.md\\n" % wing)
            raise SystemExit(0)
        shown = wing or owner
        sys.stdout.write(
            "  [1] other / general\\n      Source: decoy.md\\n"
            "  [2] %s / general\\n      Source: %s\\n" % (shown, source)
        )
        raise SystemExit(0)
    sys.stderr.write("unexpected %s\\n" % args)
    raise SystemExit(2)
    """
)


class MempalaceProbeTests(unittest.TestCase):
    def _run(self, tmp: Path, mine_fail: bool) -> dict:
        repo = tmp / "repo"
        work = tmp / "work"
        home = tmp / "home"
        real = tmp / "real-home"
        out = tmp / "out.json"
        for path in (repo, real):
            path.mkdir()
        (repo / "REPO_MARKER").write_text("keep\n", encoding="utf-8")
        for rel, text in FILES.items():
            dest = repo / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
        binary = tmp / "mempalace"
        binary.write_text(STUB, encoding="utf-8")
        binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
        if mine_fail:
            (tmp / "fail-once").write_text("1\n", encoding="utf-8")
        env = {"PATH": "/usr/bin:/bin", "HOME": str(real), "LANG": "C.UTF-8"}
        proc = subprocess.run(
            [
                sys.executable,
                str(PROBE),
                "--repo",
                str(repo),
                "--out",
                str(out),
                "--bin",
                str(binary),
                "--work",
                str(work),
                "--home",
                str(home),
                "--real-home",
                str(real),
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertTrue(out.is_file(), proc.stderr)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertFalse((repo / "mempalace.yaml").exists())
        self.assertEqual((repo / "REPO_MARKER").read_text(encoding="utf-8"), "keep\n")
        self.assertEqual(doc["repo_mempalace_yaml_new"], [])
        self.assertTrue(str(doc["init_target"]).endswith("/corpus") or str(doc["init_target"]).endswith("\\corpus"))
        self.assertTrue((Path(doc["init_target"]) / "mempalace.yaml").is_file())
        self.assertTrue((home / ".mempalace" / "touched").is_file())
        self.assertFalse((real / ".mempalace").exists())
        self.assertEqual(doc["real_home_changed"], [])
        self.assertEqual(doc["h1_graded_cases"], 0)
        return doc

    def test_wrong_top1_is_a_miss_and_top5_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mp-rank-") as raw:
            doc = self._run(Path(raw), mine_fail=False)
        self.assertEqual(doc["status"], "scored")
        self.assertEqual(doc["anchors_found"], 8)
        self.assertEqual(doc["mine_retries"], 0)
        self.assertEqual(doc["drawers_filed"], 8)
        self.assertEqual(doc["top1_hits"], 0)
        self.assertEqual(doc["top5_hits"], 8)
        self.assertEqual(doc["repeat_agreement"], 8)
        self.assertEqual(doc["scoped_expected_leaks"], 0)
        self.assertEqual(doc["scoped_kept"], 8)
        self.assertEqual(doc["scoped_wing_mismatches"], 0)
        self.assertEqual(len(doc["questions"]), 8)
        for row in doc["questions"]:
            self.assertFalse(row["top1"])
            self.assertTrue(row["top5"])
            self.assertEqual(row["top_source"], "decoy.md")
            self.assertFalse(row["scoped_leak"])
            self.assertTrue(row["scoped_kept"])

    def test_mine_failure_retries_once_and_then_scores(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mp-mine-") as raw:
            doc = self._run(Path(raw), mine_fail=True)
        self.assertEqual(doc["status"], "scored")
        self.assertEqual(doc["mine_retries"], 2)
        self.assertEqual(doc["drawers_filed"], 8)
        self.assertEqual(doc["top1_hits"], 0)
        self.assertEqual(doc["top5_hits"], 8)
        self.assertIsNone(doc["reason"])
