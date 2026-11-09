"""The public-paths guard fails on private operator material and passes clean trees.

How this fails: a planted needs-mark.tsv, handoff, new docs/ops note, stray
.tsv queue, employer name outside agent-cage attribution, eval trace, .jsonl
or .log, prose eval report, /home/<user> path, or the owner's name exits 0,
so a lane can publish operator history again. Or the real tree fails, so pregate blocks
every change.
Recover: put the private glob or rule back in scripts/check_public_paths.py,
or move the flagged file to PFY_OPS_ROOT.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "check_public_paths.py"
EMP = "PN" + "NL"
OWNER = "Ma" + "rk"


def _git(repo: Path, *args: str) -> None:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
    subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)


def _run(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(GUARD), "--root", str(repo)],
                          capture_output=True, text=True, timeout=60)


class PublicPathsGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _git(self.repo, "init", "-q", "-b", "main")
        self._write("README.md", "agent-cage (%s) is the lab.\n" % EMP)
        self._write("ci/public-docs-ops-allow.txt", "# allow\ndocs/ops/PREGATE.md\n")
        self._write("docs/ops/PREGATE.md", "How pregate works.\n")
        self._write("eval/catalog-queue/queue.tsv", "slug\n")
        self._write("eval/catalog-queue/exclusions.tsv", "slug\treason\n")
        self._write("eval/evals/x/VERDICT.json", "{}\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, rel: str, text: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        _git(self.repo, "add", "-f", rel)

    def test_clean_tree_passes(self) -> None:
        proc = _run(self.repo)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_planted_needs_mark_fails(self) -> None:
        self._write("eval/catalog-queue/needs-mark.tsv", "slug\tkind\treason\tevidence\tsince\n")
        proc = _run(self.repo)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("eval/catalog-queue/needs-mark.tsv: private-only path", proc.stdout)

    def test_planted_handoff_and_run_log_fail(self) -> None:
        for rel in ("docs/ops/HANDOFF-x-1109.md", "docs/HANDOFF-y.md", "docs/ops/RUN-LOG-z.md",
                    "docs/build-dropins/a.md", "eval/mvp-1031/REPORT.md", "pipelines/dogfood/build/s/grok-stdout.log"):
            self._write(rel, "note\n")
        out = _run(self.repo).stdout
        for rel in ("HANDOFF-x-1109", "HANDOFF-y", "RUN-LOG-z", "build-dropins/a.md", "mvp-1031", "grok-stdout"):
            self.assertIn(rel, out)

    def test_new_docs_ops_note_fails_until_allowed(self) -> None:
        self._write("docs/ops/lane-notes-1109.md", "what we did today\n")
        proc = _run(self.repo)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("new docs/ops file", proc.stdout)

    def test_stray_tsv_queue_fails(self) -> None:
        self._write("eval/catalog-queue/operator-asks.tsv", "slug\n")
        proc = _run(self.repo)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn(".tsv queue", proc.stdout)

    def test_employer_outside_cage_attribution_fails(self) -> None:
        self._write("sources/x.md", "Prefer %s for MCP.\n" % EMP.lower())
        proc = _run(self.repo)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("sources/x.md:1: employer name", proc.stdout)

    def test_other_employer_names_fail_even_on_a_cage_line(self) -> None:
        self._write("docs/y.md", "agent-cage from " + "Batt" + "elle\n")
        self.assertEqual(_run(self.repo).returncode, 1)

    def test_project_templates_are_product_code(self) -> None:
        self._write("bootstrap/project-process/templates/docs/open-questions/README.md", "template\n")
        self.assertEqual(_run(self.repo).returncode, 0)

    def test_eval_traces_logs_and_prose_reports_fail(self) -> None:
        for rel in ("eval/ev/x/traces/session-a.json", "eval/ev/x/results.jsonl",
                    "eval/integrate/x/receipt.log", "eval/evq/x/REPORT.md", "eval/integrate/x/notes.md"):
            self._write(rel, "{}\n")
        proc = _run(self.repo)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        for want in ("traces/session-a.json: trace", "results.jsonl: .jsonl log", "receipt.log: .log",
                     "evq/x/REPORT.md: prose report", "x/notes.md: prose report"):
            self.assertIn(want, proc.stdout)

    def test_eval_structured_outputs_and_fixture_inputs_pass(self) -> None:
        for rel in ("eval/evq/x/VERDICT", "eval/evq/x/results.json", "eval/integrate/x/receipt.json",
                    "eval/evq/x/probe.py", "eval/ev/x/fixtures/prompts.jsonl"):
            self._write(rel, "{}\n")
        proc = _run(self.repo)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_home_user_path_fails(self) -> None:
        self._write("eval/evq/x/results.json", '{"bin": "/home/%s/.local/bin/tool"}\n' % OWNER.lower())
        self._write("tests/test_x.py", 'P = "/home/someone/DEVELOP/x"\n')
        proc = _run(self.repo)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("eval/evq/x/results.json:1: absolute /home/<user> path", proc.stdout)
        self.assertIn("tests/test_x.py:1: absolute /home/<user> path", proc.stdout)

    def test_home_placeholders_and_cage_user_pass(self) -> None:
        self._write("docs/z.md", "Use $HOME/.cache/pfy, ~/DEVELOP, /home/agent in the cage, "
                    "and ${HOME}/.cache/pfy/tools/x/home/.local/bin.\n")
        self.assertEqual(_run(self.repo).returncode, 0, _run(self.repo).stdout)

    def test_owner_name_fails_in_text(self) -> None:
        self._write("sources/entries/1-x.md", "Needs %s's GO.\n" % OWNER)
        self._write("scripts/x.py", '# release stays with %s\n' % OWNER)
        proc = _run(self.repo)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("sources/entries/1-x.md:1: owner name", proc.stdout)
        self.assertIn("scripts/x.py:1: owner name", proc.stdout)

    def test_owner_name_allowed_as_verb_and_in_license(self) -> None:
        self._write("docs/w.md", "%s the wet sign. %s it binary. markdown, needs-mark, MARK_DIR.\n" % (OWNER, OWNER))
        self._write("LICENSE", "Copyright 2026 %s\n" % OWNER)
        proc = _run(self.repo)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_real_tree_passes(self) -> None:
        proc = subprocess.run([sys.executable, str(GUARD)], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout[-3000:])


if __name__ == "__main__":
    unittest.main()
