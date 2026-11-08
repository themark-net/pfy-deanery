"""Behavior of scripts/grok_trace_export.py. No network, no neatroots binary."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "grok_trace_export.py"


def run_export(src: Path, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(src), "-o", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )


class GrokTraceExportTest(unittest.TestCase):
    def test_three_identical_calls_stay_identical(self):
        body = "tool_call read_file target_file=same.py\ntool_result read_file same-body\n"
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "repeat.log"
            out = Path(tmp) / "trace.json"
            src.write_text(body * 3, encoding="utf-8")
            proc = run_export(src, out)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            trace = json.loads(out.read_text(encoding="utf-8"))
            tools = [child for child in trace["children"] if child["kind"] == "TOOL"]
            self.assertEqual(len(tools), 3)
            self.assertEqual(tools[0]["name"], "read_file")
            self.assertEqual(tools[0]["input"], tools[1]["input"])
            self.assertEqual(tools[1]["input"], tools[2]["input"])
            self.assertEqual(tools[0]["output"], tools[1]["output"])
            self.assertEqual(tools[1]["output"], tools[2]["output"])

    def test_error_streak_recovers_on_later_success(self):
        # Risk: a later success is still marked ERROR, so a recovered run looks stuck.
        lines = []
        for _ in range(3):
            lines.append("tool_call read_file target_file=a.py")
            lines.append("tool_result read_file status=error missing")
        lines.append("tool_call read_file target_file=b.py")
        lines.append("tool_result read_file status=ok found")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "streak.log"
            out = Path(tmp) / "trace.json"
            src.write_text("\n".join(lines) + "\n", encoding="utf-8")
            proc = run_export(src, out)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            tools = [
                child for child in json.loads(out.read_text(encoding="utf-8"))["children"]
                if child["kind"] == "TOOL"
            ]
            self.assertEqual([tool["status"] for tool in tools], ["ERROR", "ERROR", "ERROR", "OK"])
            self.assertNotIn("error", tools[-1])

    def test_clip_keeps_different_long_outputs_apart(self):
        # Risk: clipping makes two different tool results look identical.
        head = "A" * 500
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "clip.log"
            out = Path(tmp) / "trace.json"
            src.write_text(
                "tool_call read_file target_file=a.py\n"
                "tool_result read_file " + head + "TAIL-A\n"
                "tool_call read_file target_file=a.py\n"
                "tool_result read_file " + head + "TAIL-B\n",
                encoding="utf-8",
            )
            proc = run_export(src, out)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            tools = [
                child for child in json.loads(out.read_text(encoding="utf-8"))["children"]
                if child["kind"] == "TOOL"
            ]
            self.assertEqual(len(tools), 2)
            self.assertNotEqual(tools[0]["output"], tools[1]["output"])
            self.assertTrue(tools[0]["output"].startswith("A" * 400))
            self.assertTrue(tools[1]["output"].startswith("A" * 400))
            self.assertIn("sha256:", tools[0]["output"])
            self.assertIn("sha256:", tools[1]["output"])
            self.assertNotIn("TAIL-A", tools[0]["output"])
            self.assertNotIn("TAIL-B", tools[1]["output"])

    def test_missing_source_exits_nonzero_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "no-such.log"
            out = Path(tmp) / "trace.json"
            proc = run_export(missing, out)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(out.exists())
            self.assertIn("source not found", proc.stderr)

    def test_session_directory_marks_tool_error_from_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = Path(tmp) / "session"
            session.mkdir()
            (session / "chat_history.jsonl").write_text(
                "\n".join([
                    json.dumps({
                        "type": "user",
                        "content": "read the file",
                    }),
                    json.dumps({
                        "type": "assistant",
                        "content": "",
                        "tool_calls": [{
                            "id": "c1",
                            "name": "read_file",
                            "arguments": json.dumps({"target_file": "a.py"}),
                        }],
                    }),
                    json.dumps({
                        "type": "tool_result",
                        "tool_call_id": "c1",
                        "content": "Error: missing a.py",
                    }),
                    json.dumps({
                        "type": "assistant",
                        "content": "The file is missing.",
                    }),
                ]) + "\n",
                encoding="utf-8",
            )
            (session / "events.jsonl").write_text(
                json.dumps({
                    "type": "tool_completed",
                    "tool_call_id": "c1",
                    "tool_name": "read_file",
                    "outcome": "error",
                }) + "\n",
                encoding="utf-8",
            )
            out = Path(tmp) / "trace.json"
            proc = run_export(session, out)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            trace = json.loads(out.read_text(encoding="utf-8"))
            tools = [child for child in trace["children"] if child["kind"] == "TOOL"]
            llms = [child for child in trace["children"] if child["kind"] == "LLM"]
            self.assertEqual(len(tools), 1)
            self.assertEqual(tools[0]["status"], "ERROR")
            self.assertEqual(tools[0]["name"], "read_file")
            self.assertIn("a.py", tools[0]["input"])
            self.assertEqual(len(llms), 1)
            self.assertIn("missing", trace["output"])

    def test_bracket_log_is_plain_text(self):
        # Risk: a pregate line that starts with [FAIL] is parsed as JSON and dropped.
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "pregate.log"
            out = Path(tmp) / "trace.json"
            src.write_text("[PASS] lint\n[FAIL] interrupted: SIGTERM\nOVERALL=FAIL wall=1s\n", encoding="utf-8")
            proc = run_export(src, out)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            trace = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(trace["status"], "ERROR")
            self.assertIn("[FAIL] interrupted", trace["output"])

    def test_narrative_failure_sets_run_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "attempt0.log"
            out = Path(tmp) / "trace.json"
            src.write_text(
                "Couldn't create session: Invalid params: example\nError: Couldn't create session\n",
                encoding="utf-8",
            )
            proc = run_export(src, out)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            trace = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(trace["status"], "ERROR")
            self.assertEqual(trace["children"], [])
            self.assertIn("Couldn't create session", trace["output"])


if __name__ == "__main__":
    unittest.main()
