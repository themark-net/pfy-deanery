"""Behavior of scripts/grill_ticket.py. The grok binary is a local fake."""
from __future__ import annotations

import json
import os
import subprocess
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "grill_ticket.py"

FAKE = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path
    argv = sys.argv[1:]
    prompt = ""
    if "--prompt-file" in argv:
        prompt = Path(argv[argv.index("--prompt-file") + 1]).read_text()
    log = os.environ.get("GRILL_FAKE_LOG")
    if log:
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"argv": argv, "prompt": prompt, "cwd": os.getcwd()}) + "\\n")
    if os.environ.get("GRILL_FAKE_MODE") == "fail":
        sys.stderr.write("fake grok failed\\n")
        raise SystemExit(1)
    behavior = os.environ.get("GRILL_FAKE_MODE") != "nochange"
    content = "GRILL_EXIT_SENTINEL = True\\n" if behavior else ""
    assertion = "the exit section is written once" if behavior else ""
    if "You are the coordinator" in prompt:
        payload = {"answers": [{
            "n": 1, "decision": "accept",
            "answer": "replace the previous grill section",
            "behavior_change": behavior, "assertion": assertion,
            "test_path": "tests/test_grill_once.py", "test_content": content,
        }]}
    else:
        payload = {"questions": [{
            "n": 1,
            "question": "What stops two runs doing the same work?",
            "recommended_answer": "replace the previous grill section",
            "behavior_change": behavior, "assertion": assertion,
            "test_path": "tests/test_grill_once.py", "test_content": content,
        }]}
    print(json.dumps({
        "text": json.dumps(payload),
        "num_turns": 1,
        "total_cost_usd": 0.01,
        "stopReason": "end_turn",
        "modelUsage": {"grok-test": {}},
    }))
    """
)


class GrillTicketTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.id().replace(".", "_"))
        # unittest id is stable; use a real temp dir under /tmp
        import tempfile
        self.dir = Path(tempfile.mkdtemp(prefix="grill-test-"))
        self.fake = self.dir / "fake-grok.py"
        self.fake.write_text(FAKE, encoding="utf-8")
        self.fake.chmod(0o755)
        self.log = self.dir / "calls.jsonl"
        self.env = os.environ.copy()
        self.env["PFY_GROK_BIN"] = str(self.fake)
        self.env["GRILL_FAKE_LOG"] = str(self.log)
        self.env.pop("GRILL_FAKE_MODE", None)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_grill(self, args, env=None):
        proc = subprocess.run(
            [sys_exe(), str(SCRIPT), *args],
            cwd=self.dir,
            env=env or self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines() if line.strip()]

    def test_plain_ticket_does_not_call_grok(self):
        ticket = self.dir / "plain.md"
        ticket.write_text("# Add slugify\n\nAdd a slugify helper.\n", encoding="utf-8")
        proc = self.run_grill([str(ticket)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("no grill needed", proc.stdout)
        self.assertEqual(self.calls(), [])
        self.assertFalse((str(ticket) + ".grill.json") and Path(str(ticket) + ".grill.json").exists())
        self.assertNotIn("Exit tests from grill", ticket.read_text())

    def test_ci_ticket_turns_behavior_change_into_exit_test(self):
        ticket = self.dir / "ci.md"
        ticket.write_text("Edit scripts/pregate.sh so two runs can overlap.\n", encoding="utf-8")
        proc = self.run_grill([str(ticket)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = ticket.read_text()
        self.assertEqual(text.count("## Exit tests from grill"), 1)
        self.assertIn("GRILL_EXIT_SENTINEL", text)
        record = json.loads(Path(str(ticket) + ".grill.json").read_text())
        self.assertEqual(record["skill_source"], "embedded" if not (REPO / "bootstrap/grok-cli/skills-external/mattpocock/grilling/SKILL.md").is_file() else record["skill_source"])
        self.assertTrue(record["skill_source"] == "embedded" or record["skill_source"].startswith("vendored:"))
        self.assertEqual(len(record["exit_tests"]), 1)
        self.assertGreaterEqual(record["turns"], 1)
        # A second run replaces the section instead of stacking a second copy.
        proc = self.run_grill([str(ticket)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(ticket.read_text().count("## Exit tests from grill"), 1)

    def test_json_ticket_keeps_exit_test_and_appends_grill_case(self):
        ticket = self.dir / "ci.json"
        original = "import unittest\nclass T(unittest.TestCase):\n    def test_old(self):\n        self.assertEqual(1, 0)\n"
        ticket.write_text(json.dumps({
            "id": "CI",
            "title": "pregate",
            "body": "Change scripts/pregate.sh.",
            "exitTest": {"path": "tests/test_old.py", "content": original},
        }), encoding="utf-8")
        proc = self.run_grill([str(ticket)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(ticket.read_text())
        self.assertEqual(data["exitTest"]["content"], original)
        self.assertEqual(len(data["exitTests"]), 2)
        self.assertEqual(data["exitTests"][0]["path"], "tests/test_old.py")
        self.assertTrue(data["exitTests"][1]["fromGrill"])
        self.assertIn("GRILL_EXIT_SENTINEL", data["exitTests"][1]["content"])
        proc = self.run_grill([str(ticket)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        again = json.loads(ticket.read_text())
        self.assertEqual(len(again["exitTests"]), 2)

    def test_cap_rejects_before_any_grok_call(self):
        ticket = self.dir / "ci.md"
        ticket.write_text("Edit scripts/run_tests.py.\n", encoding="utf-8")
        proc = self.run_grill([str(ticket), "--max-turns", "13"])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("cap is 12", proc.stderr)
        self.assertEqual(self.calls(), [])
        self.assertNotIn("Exit tests from grill", ticket.read_text())

    def test_tools_off_flags_and_turn_split(self):
        ticket = self.dir / "ci.md"
        ticket.write_text("Edit scripts/model_lock.sh.\n", encoding="utf-8")
        proc = self.run_grill([str(ticket), "--max-turns", "4"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        seen = self.calls()
        self.assertEqual(len(seen), 2)
        turns = []
        for call in seen:
            argv = call["argv"]
            self.assertIn("--disable-web-search", argv)
            self.assertIn("--no-subagents", argv)
            self.assertIn("--no-plan", argv)
            self.assertEqual(argv[argv.index("--reasoning-effort") + 1], "low")
            self.assertIn("--verbatim", argv)
            self.assertNotIn("--tools", argv)
            deny = argv[argv.index("--disallowed-tools") + 1]
            self.assertIn("read_file", deny)
            self.assertIn("update_goal", deny)
            self.assertIn("run_terminal_cmd", deny)
            turns.append(int(argv[argv.index("--max-turns") + 1]))
            self.assertLessEqual(int(argv[argv.index("--max-turns") + 1]), 12)
            cwd = Path(call["cwd"]).resolve()
            self.assertFalse(any((parent / "AGENTS.md").is_file() for parent in [cwd, *cwd.parents]))
        self.assertEqual(sum(turns), 4)
        # The prompt carries whichever skill text skill_text() would load from
        # this checkout. Another lane already vendored the grilling skill, so
        # the embedded summary is only present when that file is absent.
        skill_file = REPO / "bootstrap/grok-cli/skills-external/mattpocock/grilling/SKILL.md"
        prompt = seen[0]["prompt"]
        if skill_file.is_file():
            self.assertIn(skill_file.read_text(encoding="utf-8")[:80], prompt)
            self.assertNotIn("embedded summary", prompt)
        else:
            self.assertIn("embedded summary", prompt)

    def test_answers_file_skips_coordinator_and_overrides(self):
        ticket = self.dir / "ci.md"
        ticket.write_text("Edit docs/ops/PREGATE.md.\n", encoding="utf-8")
        answers = self.dir / "answers.json"
        answers.write_text(json.dumps({"answers": [{
            "n": 1, "decision": "override", "answer": "use the per-run directory",
            "behavior_change": True, "assertion": "two runs do not share a summary file",
            "test_path": "tests/test_grill_lock.py",
            "test_content": "GRILL_LOCK_SENTINEL = True\n",
        }]}), encoding="utf-8")
        proc = self.run_grill([str(ticket), "--answers", str(answers), "--max-turns", "3"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        seen = self.calls()
        self.assertEqual(len(seen), 1)
        self.assertEqual(int(seen[0]["argv"][seen[0]["argv"].index("--max-turns") + 1]), 3)
        self.assertIn("GRILL_LOCK_SENTINEL", ticket.read_text())
        self.assertNotIn("GRILL_EXIT_SENTINEL", ticket.read_text())

    def test_grok_failure_leaves_the_ticket_unchanged(self):
        ticket = self.dir / "ci.md"
        original = "Edit pipelines/nightly.yml.\n"
        ticket.write_text(original, encoding="utf-8")
        env = dict(self.env)
        env["GRILL_FAKE_MODE"] = "fail"
        proc = self.run_grill([str(ticket)], env=env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(ticket.read_text(), original)
        self.assertFalse(Path(str(ticket) + ".grill.json").exists())

    def test_no_behavior_change_writes_no_exit_section(self):
        ticket = self.dir / "ci.md"
        ticket.write_text("Edit ci/test-image/Containerfile.\n", encoding="utf-8")
        env = dict(self.env)
        env["GRILL_FAKE_MODE"] = "nochange"
        proc = self.run_grill([str(ticket)], env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("Exit tests from grill", ticket.read_text())
        record = json.loads(Path(str(ticket) + ".grill.json").read_text())
        self.assertEqual(record["exit_tests"], [])

    def test_makefile_test_target_triggers_and_help_target_does_not(self):
        help_ticket = self.dir / "help.md"
        help_ticket.write_text("Update the Makefile help wording.\n", encoding="utf-8")
        proc = self.run_grill([str(help_ticket), "--paths", "Makefile"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("no grill needed", proc.stdout)
        self.assertEqual(self.calls(), [])
        ci_ticket = self.dir / "make.md"
        ci_ticket.write_text("Wire make eval-structural in the Makefile.\n", encoding="utf-8")
        proc = self.run_grill([str(ci_ticket), "--paths", "Makefile"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("no grill needed", proc.stdout)
        self.assertGreaterEqual(len(self.calls()), 1)

    def test_diff_of_pregate_triggers(self):
        repo = self.dir / "repo"
        repo.mkdir()
        subprocess.check_call(["git", "init", "-q", "-b", "main"], cwd=repo)
        (repo / "README").write_text("x\n", encoding="utf-8")
        subprocess.check_call(["git", "add", "README"], cwd=repo)
        subprocess.check_call(
            ["git", "-c", "user.name=t", "-c", "user.email=t@localhost", "commit", "-qm", "readme"],
            cwd=repo,
        )
        pre = repo / "scripts"
        pre.mkdir()
        (pre / "pregate.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        subprocess.check_call(["git", "add", "scripts/pregate.sh"], cwd=repo)
        subprocess.check_call(
            ["git", "-c", "user.name=t", "-c", "user.email=t@localhost", "commit", "-qm", "pregate"],
            cwd=repo,
        )
        parent = subprocess.check_output(["git", "rev-parse", "HEAD~1"], cwd=repo, text=True).strip()
        ticket = self.dir / "diff.md"
        ticket.write_text("See the diff.\n", encoding="utf-8")
        proc = self.run_grill([str(ticket), "--repo", str(repo), "--diff", parent])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Exit tests from grill", ticket.read_text())

    def test_skill_file_is_used_when_present(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("grill_ticket", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        missing = self.dir / "empty-root"
        text, source = mod.skill_text(missing)
        self.assertEqual(source, "embedded")
        self.assertIn("embedded summary", text)
        root = self.dir / "with-skill"
        skill = root / "bootstrap/grok-cli/skills-external/mattpocock/grilling/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("VENDORED_GRILL_SENTINEL ask one round\n", encoding="utf-8")
        text, source = mod.skill_text(root)
        self.assertEqual(source, "vendored:bootstrap/grok-cli/skills-external/mattpocock/grilling/SKILL.md")
        self.assertIn("VENDORED_GRILL_SENTINEL", text)
        on_disk = REPO / "bootstrap/grok-cli/skills-external/mattpocock/grilling/SKILL.md"
        live, live_source = mod.skill_text(REPO)
        if on_disk.is_file():
            self.assertTrue(live_source.startswith("vendored:"))
            self.assertIn(on_disk.read_text(encoding="utf-8")[:40], live)
        else:
            self.assertEqual(live_source, "embedded")


def sys_exe():
    import sys
    return sys.executable


if __name__ == "__main__":
    unittest.main()
