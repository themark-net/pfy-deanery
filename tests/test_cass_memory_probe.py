"""cass-memory probe failure modes.

The child is eval/evq1107/cass-memory/probe.py. It reads
eval/evq1107/cass-memory/rules.json and writes
eval/evq1107/cass-memory/results.json on a real run. These tests pass a stub
cm and a temp --out so the real results file stays put. No network, no model,
no real cm binary.
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
PROBE = ROOT / "eval" / "evq1107" / "cass-memory" / "probe.py"
RESULTS = ROOT / "eval" / "evq1107" / "cass-memory" / "results.json"
NEEDLES = (
    "write-guard-mcp",
    "smoke-codebase-memory",
    "self_pipeline",
    "best-effort-and-bot-budget-build-max",
    "prefer-behavior-and-fail-recover-tests",
    "eval-structural",
    "codebase-memory-mcp",
    "integration-stages.md",
)

STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, re, sys
    from pathlib import Path
    MODE = "__MODE__"
    STOP = {
        "a", "an", "the", "of", "to", "and", "or", "for", "in", "on", "with",
        "before", "after", "when", "one", "it", "its", "by", "is", "are", "be",
        "this", "that", "from", "into", "not", "any", "must", "stay", "how",
        "should", "which", "where", "what", "while", "under", "out", "own",
        "does", "do", "can", "will", "than",
    }
    args = sys.argv[1:]
    home = Path(os.environ["HOME"])
    state_path = home / "state.json"

    def tokens(text):
        return {tok for tok in re.findall(r"[a-z0-9]{3,}", text.lower()) if tok not in STOP}

    def load():
        if state_path.is_file():
            return json.loads(state_path.read_text(encoding="utf-8"))
        return {"bullets": [], "marks": {}}

    def save(state):
        state_path.write_text(json.dumps(state), encoding="utf-8")

    def emit(data):
        sys.stdout.write(json.dumps({
            "success": True,
            "command": args[0] if args else "",
            "data": data,
            "metadata": {"executionMs": 1, "version": "0.0-stub"},
        }))

    if args[:1] == ["--version"]:
        sys.stdout.write("0.0-stub\\n")
        raise SystemExit(0)
    if args[:1] == ["init"]:
        save({"bullets": [], "marks": {}})
        emit({"cassAvailable": False, "created": ["playbook.yaml"]})
        raise SystemExit(0)
    if args[:1] == ["doctor"]:
        emit({
            "overallStatus": "unhealthy",
            "checks": [{"item": "cass", "status": "fail", "message": "CASS binary missing"}],
        })
        raise SystemExit(0)
    if args[:1] == ["ls"]:
        state = load()
        emit({"bullets": [row for row in state["bullets"] if not row.get("deprecated")]})
        raise SystemExit(0)
    if args[:1] == ["reflect"]:
        sys.stderr.write(
            "[cm] WARNING: Provider anthropic is not configured, falling back to local CLI\\n"
        )
        emit({"deltas": []})
        raise SystemExit(0)
    if args[:1] == ["add"]:
        state = load()
        content = args[1]
        category = args[args.index("--category") + 1]
        row = {
            "id": "b-stub-%d" % (len(state["bullets"]) + 1),
            "content": content,
            "category": category,
            "deprecated": False,
        }
        state["bullets"].append(row)
        save(state)
        emit({"bullet": row})
        raise SystemExit(0)
    if args[:1] == ["context"]:
        task = args[1]
        if MODE == "badjson" and "sha256" in task:
            sys.stderr.write("CMK_PIN leaked on stderr\\n")
            sys.stdout.write("NOT JSON\\n")
            raise SystemExit(1)
        state = load()
        ranked = []
        for row in state["bullets"]:
            visible = not row.get("deprecated")
            if MODE == "sticky" and "CMK_PLANT" in row["content"] and "friday" in task:
                visible = True
            if not visible:
                continue
            score = len(tokens(task) & tokens(row["content"]))
            if score > 0:
                ranked.append((score, row))
        ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
        emit({
            "relevantBullets": [row for _score, row in ranked],
            "semanticMode": "keyword",
        })
        raise SystemExit(0)
    if args[:1] == ["mark"]:
        state = load()
        bullet_id = args[1]
        count = int(state["marks"].get(bullet_id, 0)) + 1
        state["marks"][bullet_id] = count
        new_state = "deprecated" if count >= 3 else "candidate"
        for row in state["bullets"]:
            if row["id"] == bullet_id and new_state == "deprecated" and MODE != "sticky":
                row["deprecated"] = True
        save(state)
        emit({"bulletId": bullet_id, "newState": new_state})
        raise SystemExit(0)
    if args[:1] == ["usage"]:
        emit({"today": 0, "month": 0, "total": 0})
        raise SystemExit(0)
    sys.stderr.write("unexpected %s\\n" % args)
    raise SystemExit(2)
    """
)


class CassMemoryProbeTest(unittest.TestCase):
    def _run(self, root: Path, mode: str) -> dict:
        home = root / "home"
        home.mkdir()
        repo = root / "repo"
        (repo / "docs").mkdir(parents=True)
        (repo / "docs" / "facts.txt").write_text("\n".join(NEEDLES) + "\n", encoding="utf-8")
        stub = root / "cm"
        stub.write_text(STUB.replace("__MODE__", mode), encoding="utf-8")
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        out = root / "results.json"
        before = RESULTS.read_bytes() if RESULTS.is_file() else None
        proc = subprocess.run(
            [
                sys.executable,
                str(PROBE),
                "--out",
                str(out),
                "--cm-bin",
                str(stub),
                "--home",
                str(home),
                "--real-home",
                str(root / "real-home"),
                "--repo",
                str(repo),
                "--skip-sha",
                "--no-unshare",
            ],
            cwd=str(ROOT),
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(home)},
            text=True,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        if before is None:
            self.assertFalse(RESULTS.is_file())
        else:
            self.assertEqual(RESULTS.read_bytes(), before)
        return json.loads(out.read_text(encoding="utf-8"))

    def test_bad_context_json_is_a_miss_and_later_queries_recover(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cm-badjson-") as raw:
            doc = self._run(Path(raw), "badjson")
        self.assertTrue(doc["ran"])
        self.assertEqual(doc["history"]["rules_extracted"], 0)
        self.assertTrue(doc["history"]["llm_skipped"])
        self.assertEqual(doc["history"]["status"], "ran")
        self.assertEqual(doc["h1_graded_cases"], 0)
        self.assertEqual(doc["playbook_queries"], 8)
        self.assertEqual(doc["bad_json_queries"], 1)
        self.assertEqual(doc["playbook_top1"], 7)
        self.assertEqual(doc["overlap_top1"], 8)
        self.assertEqual(doc["top1_delta"], -1)
        pin = next(row for row in doc["queries"] if row["name"] == "pin")
        self.assertFalse(pin["parse_ok"])
        self.assertFalse(pin["hit"])
        self.assertFalse(pin["recalled"])
        others = [row for row in doc["queries"] if row["name"] != "pin"]
        self.assertTrue(all(row["hit"] for row in others))
        self.assertEqual(doc["agreement"], 7)
        self.assertEqual(doc["repo_rg_hits"], 8)
        self.assertEqual(doc["repo_playbook_hits"], 0)
        self.assertEqual(doc["usage"]["total"], 0)
        self.assertEqual(doc["distractor_leaks"], 0)
        self.assertTrue(doc["deprecation"]["removed_from_context"])
        self.assertEqual(doc["deprecation"]["last_state"], "deprecated")
        self.assertFalse(doc["real_home_changed"])

    def test_deprecated_state_still_in_context_is_not_a_drop(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cm-sticky-") as raw:
            doc = self._run(Path(raw), "sticky")
        self.assertEqual(doc["playbook_top1"], 8)
        self.assertEqual(doc["bad_json_queries"], 0)
        self.assertEqual(doc["deprecation"]["last_state"], "deprecated")
        self.assertTrue(doc["deprecation"]["mark_ok"])
        self.assertFalse(doc["deprecation"]["removed_from_context"])
        pin = next(row for row in doc["queries"] if row["name"] == "pin")
        self.assertTrue(pin["hit"])
        self.assertEqual(doc["h1_graded_cases"], 0)
        self.assertEqual(doc["history"]["rules_extracted"], 0)

    def test_sha_mismatch_does_not_execute(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cm-sha-") as raw:
            root = Path(raw)
            flag = root / "executed"
            binary = root / "cm"
            binary.write_text("#!/bin/sh\ntouch '%s'\nexit 0\n" % flag, encoding="utf-8")
            binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
            out = root / "results.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(PROBE),
                    "--out",
                    str(out),
                    "--cm-bin",
                    str(binary),
                    "--home",
                    str(root / "home"),
                    "--real-home",
                    str(root / "real-home"),
                    "--repo",
                    str(root / "repo"),
                    "--no-unshare",
                ],
                cwd=str(ROOT),
                env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
                text=True,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertFalse(flag.exists())
            doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertFalse(doc["ran"])
        self.assertFalse(doc["sha256_ok"])
        self.assertEqual(doc["history"]["status"], "SKIPPED")
        self.assertEqual(doc["history"]["rules_extracted"], 0)
        self.assertIn("not executed", doc["reason"])


if __name__ == "__main__":
    unittest.main()
