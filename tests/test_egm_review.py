"""Behavior of scripts/egm_review.py. The grok binary is a local fake.

No network and no real model. A reviewer that dies is not a clean review:
the other personas stay in the report and the process exits 1.
"""
from __future__ import annotations

import json
import os
import pty
import select
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "egm_review.py"

FAKE = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path
    argv = sys.argv[1:]
    prompt = ""
    if "--prompt-file" in argv:
        prompt = Path(argv[argv.index("--prompt-file") + 1]).read_text()
    kind = "elephant" if "You are the Elephant" in prompt else "goldfish"
    persona = ""
    for name in ("readiness", "critic", "codebase"):
        if ("Persona: %s" % name) in prompt:
            persona = name
    log = os.environ.get("EGM_FAKE_LOG")
    if log:
        row = {
            "argv": argv,
            "cwd": os.getcwd(),
            "kind": kind,
            "persona": persona,
            "saw_spec": "ELEPHANT_SPEC_MARKER" in prompt,
            "always_approve": "--always-approve" in argv,
            "resume": "--resume" in argv or "--continue" in argv,
        }
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\\n")
    fail = os.environ.get("EGM_FAKE_FAIL") or ""
    if fail and persona == fail:
        sys.stderr.write("fake goldfish failed\\n")
        raise SystemExit(1)
    if kind == "elephant":
        payload = {"spec": "Problem\\n\\nELEPHANT_SPEC_MARKER\\n", "unstated": ["directory mode"]}
    else:
        payload = {"findings": [{
            "severity": "Major",
            "scope": persona,
            "finding": "mode is not stated",
        }]}
    print(json.dumps({
        "text": json.dumps(payload),
        "num_turns": 1,
        "stopReason": "end_turn",
        "modelUsage": {"grok-test": {}},
    }))
    """
)


class EgmReviewTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="egm-test-"))
        self.fake = self.root / "fake-grok.py"
        self.fake.write_text(FAKE, encoding="utf-8")
        self.fake.chmod(self.fake.stat().st_mode | stat.S_IEXEC)
        self.log = self.root / "calls.jsonl"
        self.ticket = self.root / "ticket.md"
        self.cited = self.root / "cited.md"
        self.out = self.root / "report.json"
        self.scratch = self.root / "scratch"
        self.ticket.write_text("Do the ticket.\n", encoding="utf-8")
        self.cited.write_text("cited line\n", encoding="utf-8")
        self.env = os.environ.copy()
        self.env["PFY_GROK_BIN"] = str(self.fake)
        self.env["EGM_FAKE_LOG"] = str(self.log)
        self.env.pop("EGM_FAKE_FAIL", None)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.root, ignore_errors=True)

    def run_review(self, extra=None, env=None, max_turns="2", stdin=None):
        argv = [
            sys.executable,
            str(SCRIPT),
            "--ticket",
            str(self.ticket),
            "--cited",
            str(self.cited),
            "--out",
            str(self.out),
            "--scratch",
            str(self.scratch),
            "--max-turns",
            str(max_turns),
            "--personas",
            "readiness,critic",
        ]
        if extra:
            argv.extend(extra)
        return subprocess.run(
            argv,
            cwd=self.root,
            env=self.env if env is None else env,
            stdin=stdin,
            capture_output=True,
            text=True,
            check=False,
        )

    def calls(self):
        rows = []
        if self.log.is_file():
            for line in self.log.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def test_off_tty_does_not_call_grok_until_the_estimate_is_accepted(self):
        """Fail: the fake grok runs with no cost line.
        Recover: off a TTY the process exits 2 until --yes and a covering
        --max-cost, and the same review then runs.
        """
        # DEVNULL keeps stdin off a TTY even when the runner itself is a terminal.
        off = subprocess.DEVNULL
        proc = self.run_review(stdin=off)
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 2, blob)
        self.assertIn("cost estimate: $", blob)
        self.assertIn("grok-4.7", blob)
        self.assertIn("no TTY", blob)
        self.assertIn("No model was called", blob)
        self.assertFalse(self.log.exists(), blob)
        report = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertFalse(report["ok"])
        self.assertEqual(report["goldfish"], [])

        if self.out.exists():
            self.out.unlink()
        proc = self.run_review(extra=["--yes"], stdin=off)
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 2, blob)
        self.assertIn("--yes requires --max-usd", blob)
        self.assertFalse(self.log.exists(), blob)

        if self.out.exists():
            self.out.unlink()
        proc = self.run_review(extra=["--yes", "--max-cost", "0"], stdin=off)
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 2, blob)
        self.assertIn("exceeds --max-usd", blob)
        self.assertFalse(self.log.exists(), blob)

        if self.out.exists():
            self.out.unlink()
        proc = self.run_review(extra=["--yes", "--max-cost", "50"], stdin=off)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.calls())
        report = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertTrue(report["ok"])

    def _pty_review(self, typed: bytes) -> tuple[int, str]:
        master, slave = pty.openpty()
        argv = [
            sys.executable,
            str(SCRIPT),
            "--ticket",
            str(self.ticket),
            "--cited",
            str(self.cited),
            "--out",
            str(self.out),
            "--scratch",
            str(self.scratch),
            "--max-turns",
            "2",
            "--personas",
            "readiness,critic",
        ]
        proc = subprocess.Popen(
            argv,
            cwd=self.root,
            env=self.env,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            close_fds=True,
        )
        os.close(slave)
        try:
            os.write(master, typed)
        except OSError:
            pass
        chunks: list[bytes] = []
        deadline = time.time() + 20
        while time.time() < deadline:
            ready, _, _ = select.select([master], [], [], 0.2)
            if ready:
                try:
                    data = os.read(master, 4096)
                except OSError:
                    break
                if not data:
                    break
                chunks.append(data)
            if proc.poll() is not None:
                break
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)
        while True:
            ready, _, _ = select.select([master], [], [], 0.05)
            if not ready:
                break
            try:
                data = os.read(master, 4096)
            except OSError:
                break
            if not data:
                break
            chunks.append(data)
        os.close(master)
        code = proc.returncode if proc.returncode is not None else 1
        return code, b"".join(chunks).decode("utf-8", "replace")

    def _reset_review_outputs(self) -> None:
        if self.log.exists():
            self.log.unlink()
        if self.out.exists():
            self.out.unlink()

    def test_tty_y_starts_fake_grok_and_other_lines_do_not(self):
        """Fail: a terminal that answers y still declines and never starts grok.
        Recover: y starts the local fake. n, blank, and any other line decline
        and leave no call log.
        """
        code, text = self._pty_review(b"y\n")
        self.assertEqual(code, 0, text)
        self.assertIn("cost estimate:", text)
        self.assertNotIn("No model was called", text)
        self.assertTrue(self.calls(), text)
        report = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertTrue(report["ok"])
        self.assertEqual(report["route"], "grok")

        for typed in (b"n\n", b"\n", b"nope\n"):
            self._reset_review_outputs()
            code, text = self._pty_review(typed)
            self.assertEqual(code, 2, text)
            self.assertIn("declined", text)
            self.assertIn("No model was called", text)
            self.assertFalse(self.log.exists(), text)

    def test_stub_review_is_isolated_and_records_findings(self):
        proc = self.run_review(extra=["--yes", "--max-cost", "50"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertTrue(report["ok"])
        self.assertEqual(report["elephant"]["turns"], 1)
        self.assertIn("ELEPHANT_SPEC_MARKER", report["elephant"]["spec"])
        self.assertEqual(
            [row["persona"] for row in report["goldfish"]],
            ["readiness", "critic"],
        )
        self.assertEqual(report["goldfish"][0]["findings"][0]["severity"], "Major")
        rows = self.calls()
        kinds = {(row["kind"], row["persona"]) for row in rows}
        self.assertIn(("elephant", ""), kinds)
        self.assertIn(("goldfish", "readiness"), kinds)
        self.assertIn(("goldfish", "critic"), kinds)
        cwds = {row["cwd"] for row in rows}
        self.assertEqual(len(cwds), 3)
        for row in rows:
            self.assertNotIn("--always-approve", row["argv"])
            self.assertIn("--no-subagents", row["argv"])
            self.assertIn("--disable-web-search", row["argv"])
            self.assertIn("--verbatim", row["argv"])
            self.assertEqual(row["argv"][row["argv"].index("--max-turns") + 1], "2")
            self.assertFalse(row["always_approve"])
            self.assertFalse(row["resume"])
            tools = row["argv"][row["argv"].index("--disallowed-tools") + 1]
            self.assertIn("read_file", tools)
            self.assertIn("run_terminal_command", tools)
        elephant = [row for row in rows if row["kind"] == "elephant"]
        goldfish = [row for row in rows if row["kind"] == "goldfish"]
        self.assertTrue(all(not row["saw_spec"] for row in elephant))
        self.assertTrue(all(row["saw_spec"] for row in goldfish))

    def test_one_goldfish_failure_keeps_the_other_and_exits_1(self):
        self.env["EGM_FAKE_FAIL"] = "critic"
        proc = self.run_review(extra=["--yes", "--max-cost", "50"])
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("Rerun scripts/egm_review.py", proc.stderr)
        report = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertFalse(report["ok"])
        by_name = {row["persona"]: row for row in report["goldfish"]}
        self.assertTrue(by_name["readiness"]["ok"])
        self.assertEqual(by_name["readiness"]["findings"][0]["finding"], "mode is not stated")
        self.assertFalse(by_name["critic"]["ok"])
        self.assertEqual(by_name["critic"]["findings"], [])
        self.assertIn("ELEPHANT_SPEC_MARKER", report["elephant"]["spec"])

    def test_max_turns_outside_1_to_4_exits_2_without_calling_grok(self):
        for bad in ("0", "5"):
            if self.log.exists():
                self.log.unlink()
            if self.out.exists():
                self.out.unlink()
            proc = self.run_review(max_turns=bad)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn("refusing max-turns %s (cap 4)" % bad, proc.stderr)
            self.assertNotIn("Rerun scripts/egm_review.py", proc.stderr)
            self.assertFalse(self.log.exists(), proc.stderr)
            self.assertFalse(self.out.exists(), proc.stderr)

    def test_missing_cited_exits_2_without_a_grok_install_hint(self):
        self.cited.unlink()
        proc = self.run_review()
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("next step:", proc.stderr)
        self.assertIn("ticket or cited file is missing", proc.stderr)
        self.assertNotIn("PFY_GROK_BIN", proc.stderr)
        self.assertNotIn("EGM plugin", proc.stderr)
        self.assertFalse(self.log.exists())
        report = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertFalse(report["ok"])
        self.assertEqual(report["goldfish"], [])

    def test_missing_binary_exits_2_with_a_next_step(self):
        env = self.env.copy()
        env["PFY_GROK_BIN"] = str(self.root / "missing-grok")
        proc = self.run_review(env=env)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("next step:", proc.stderr)
        self.assertIn("missing-grok", proc.stderr)
        self.assertIn("Do not install the EGM plugin", proc.stderr)
        report = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertFalse(report["ok"])
        self.assertEqual(report["goldfish"], [])
