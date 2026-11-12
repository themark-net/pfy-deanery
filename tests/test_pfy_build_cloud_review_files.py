"""Per-file cloud review: a large multi-file diff can still be accepted.

The 12k whole-diff cap refused a 24 KB change before any reviewer saw it.
Review is now one file at a time, with a per-file cap and a change-impact map.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from tests.test_pfy_build_cloud import CLOUD, SCRATCH, _git, _init_repo, _run, _write_exe

MISSING_TOOL = "/no/such/pfy-impact-tool"


def _accept_grok(log: Path, writer: str) -> str:
    return (
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "from pathlib import Path\n"
        "blob = '\\n'.join(sys.argv)\n"
        "Path(os.environ['PFY_PROMPT_LOG']).open('a', encoding='utf-8').write(blob + '\\n---PROMPT---\\n')\n"
        "if 'PFY-CLOUD-REVIEW' in blob:\n"
        "    print('verdict: accept')\n"
        "    raise SystemExit(0)\n"
        "%s\n"
        "raise SystemExit(0)\n" % writer
    )


def _diff_sections(prompt: str) -> str:
    marker = "\nDiff:\n"
    gate = "\n\nGate:\n"
    start = prompt.find(marker)
    end = prompt.find(gate, start if start >= 0 else 0)
    if start < 0 or end < 0:
        return ""
    return prompt[start + len(marker) : end]


class PerFileReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir(parents=True, exist_ok=True)
        self.log = self.side / "prompts.txt"
        self.gate_log = self.side / "gate.txt"

    def tearDown(self) -> None:
        subprocess.run(["git", "-C", str(self.repo), "worktree", "prune"], check=False)
        import shutil

        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def _gate(self, watch: str = "wide.py") -> Path:
        return _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "import os\n"
            "from pathlib import Path\n"
            "log = Path(os.environ['PFY_GATE_LOG'])\n"
            "seen = Path(%r).exists()\n"
            "log.open('a', encoding='utf-8').write('seen=%%s\\n' %% seen)\n"
            "print('GATE-OK')\n"
            "raise SystemExit(0)\n" % watch,
        )

    def _run(
        self,
        grok: Path,
        task: str,
        extra: list[str] | None = None,
        env: dict | None = None,
        timeout: float = 60,
    ) -> subprocess.CompletedProcess:
        argv = [
            sys.executable,
            str(CLOUD),
            task,
            "--repo",
            str(self.repo),
            "--retries",
            "0",
            "--timeout",
            "30",
            "--test-cmd",
            "%s %s" % (sys.executable, self._gate()),
            "--grok-cmd",
            str(grok),
        ]
        if extra:
            argv.extend(extra)
        merged = {
            "PFY_PROMPT_LOG": str(self.log),
            "PFY_GATE_LOG": str(self.gate_log),
            "PFY_CODEBASE_MEMORY": MISSING_TOOL,
            "PFY_TSA_BIN": MISSING_TOOL,
        }
        if env:
            merged.update(env)
        return _run(argv, self.repo, env=merged, timeout=timeout)

    def _receipt(self) -> dict:
        receipts = sorted((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))
        self.assertTrue(receipts, "no receipt")
        return json.loads(receipts[-1].read_text(encoding="utf-8"))

    def _reviews(self) -> list[str]:
        if not self.log.is_file():
            return []
        return [item for item in self.log.read_text(encoding="utf-8").split("---PROMPT---") if "PFY-CLOUD-REVIEW" in item]

    def test_four_files_over_24kb_review_and_commit(self) -> None:
        """A 24 KB diff split across four files under the cap is accepted.

        Fail: the runner still refuses the whole diff at 12000 characters,
        so a five-file task never reaches review and never commits.
        Recover: each file is reviewed whole, any single accept is not enough
        unless every file is accepted, and the commit is published.
        """
        writer = (
            "files = [\n"
            "    ('a_one.py', 'TOKEN_A'),\n"
            "    ('b_two.py', 'TOKEN_B'),\n"
            "    ('c_three.py', 'TOKEN_C'),\n"
            "    ('d_four.py', 'TOKEN_D'),\n"
            "]\n"
            "for name, token in files:\n"
            "    Path(name).write_text(\n"
            "        'def %s():\\n    return %r\\n' % (name[:-3], token) + ('x' * 7000) + '\\n',\n"
            "        encoding='utf-8',\n"
            "    )\n"
        )
        grok = _write_exe(self.side / "grok.py", _accept_grok(self.log, writer))
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = self._run(grok, "add four marker files")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        self.assertEqual(payload["reason"], "ok")
        self.assertEqual(payload["review"]["verdict"], "accept")
        self.assertIs(payload["review"]["truncated"], False)
        self.assertIsNotNone(payload["commit"])
        self.assertTrue(str(payload["branch"] or "").startswith("cloud/"), payload["branch"])
        reviews = self._reviews()
        self.assertEqual(len(reviews), 4, [len(item) for item in reviews])
        total = 0
        tokens = ("TOKEN_A", "TOKEN_B", "TOKEN_C", "TOKEN_D")
        for prompt, token in zip(reviews, tokens):
            diff = _diff_sections(prompt)
            total += len(diff)
            self.assertIn(token, diff, token)
            self.assertIn("Change-impact map:", prompt)
            self.assertNotIn("...[diff truncated]", prompt)
            for other in tokens:
                if other != token:
                    self.assertNotIn(other, diff, (token, other))
        self.assertGreaterEqual(total, 24000, total)
        self.assertNotEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), "")
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        names = _git(self.repo, "ls-tree", "-r", "--name-only", payload["branch"]).stdout
        for name in ("a_one.py", "b_two.py", "c_three.py", "d_four.py"):
            self.assertIn(name, names)

    def test_one_file_over_the_cap_stops_before_the_gate(self) -> None:
        """One file over the cap is split into review parts and still published.

        Fail: the runner refuses review-file-too-large, or a part omits lines.
        Recover: more than one review prompt, the gate runs, every x is shown.
        """
        grok = _write_exe(
            self.side / "grok.py",
            _accept_grok(self.log, "Path('wide.py').write_text('x' * 20000, encoding='utf-8')"),
        )
        proc = self._run(grok, "add a long marker file")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        self.assertEqual(payload["reason"], "ok")
        self.assertIsNotNone(payload["commit"])
        self.assertIn("seen=True", self.gate_log.read_text(encoding="utf-8"))
        reviews = self._reviews()
        self.assertGreater(len(reviews), 1, [len(item) for item in reviews])
        shown = "".join(_diff_sections(item) for item in reviews)
        self.assertGreaterEqual(shown.count("x"), 20000)
        self.assertNotIn("...[diff truncated]", shown)

    def test_env_and_flag_change_the_file_cap(self) -> None:
        """PFY_REVIEW_FILE_CAP and --review-file-cap replace the default 12000.

        Fail: a 20k file still dies at the default cap when the operator
        raised it, or a small file is reviewed when the operator lowered it.
        Recover: the env accepts the 20k file; the flag refuses a 400-character
        file before the post-change gate. When both are set, the flag wins.
        """
        long_grok = _write_exe(
            self.side / "grok-long.py",
            _accept_grok(self.log, "Path('wide.py').write_text('y' * 20000, encoding='utf-8')"),
        )
        proc = self._run(
            long_grok,
            "add a long marker file",
            env={"PFY_REVIEW_FILE_CAP": "30000"},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        self.assertIsNotNone(payload["commit"])
        self.assertIn("seen=True", self.gate_log.read_text(encoding="utf-8"))
        self.assertEqual(len(self._reviews()), 1)

        self.gate_log.write_text("", encoding="utf-8")
        self.log.write_text("", encoding="utf-8")
        short_grok = _write_exe(
            self.side / "grok-short.py",
            _accept_grok(self.log, "Path('wide.py').write_text('z' * 400, encoding='utf-8')"),
        )
        proc = self._run(
            short_grok,
            "add a short marker file",
            extra=["--review-file-cap", "100"],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        reviews = self._reviews()
        self.assertGreater(len(reviews), 1, reviews)
        for prompt in reviews:
            self.assertLessEqual(len(_diff_sections(prompt)), 100)
        self.assertGreaterEqual("".join(_diff_sections(item) for item in reviews).count("z"), 400)
        self.assertIn("seen=True", self.gate_log.read_text(encoding="utf-8"))
        self.assertIsNotNone(payload["commit"])

        self.gate_log.write_text("", encoding="utf-8")
        self.log.write_text("", encoding="utf-8")
        proc = self._run(
            short_grok,
            "add a short marker file",
            extra=["--review-file-cap", "100"],
            env={"PFY_REVIEW_FILE_CAP": "30000"},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        reviews = self._reviews()
        self.assertGreater(len(reviews), 1, reviews)
        for prompt in reviews:
            self.assertLessEqual(len(_diff_sections(prompt)), 100)
        self.assertIn("seen=True", self.gate_log.read_text(encoding="utf-8"))

    def test_missing_tools_record_git_grep_on_each_prompt(self) -> None:
        """A missing impact tool does not fail the build.

        Fail: codebase-memory-mcp and Tree-sitter Analyzer are absent, so
        the runner exits before review or omits the map.
        Recover: git grep of the changed symbol is the map, impact.source
        is git-grep, and the accept still commits.
        """
        lib = self.repo / "lib.py"
        lib.write_text("def kept_helper():\n    return 1\n", encoding="utf-8")
        added = _git(self.repo, "add", "lib.py")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "helper")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        writer = (
            "Path('use.py').write_text("
            "'def kept_helper():\\n    return 2\\n', encoding='utf-8')"
        )
        grok = _write_exe(self.side / "grok.py", _accept_grok(self.log, writer))
        proc = self._run(grok, "retarget the helper")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        self.assertEqual(payload["impact"]["source"], "git-grep")
        reviews = self._reviews()
        self.assertEqual(len(reviews), 1, reviews)
        self.assertIn("Change-impact map:", reviews[0])
        self.assertIn("kept_helper", reviews[0])
        self.assertIn("lib.py", reviews[0])
        self.assertIn("use.py", _diff_sections(reviews[0]))
        self.assertIsNotNone(payload["commit"])

    def test_codebase_memory_is_preferred_and_tree_sitter_is_the_fallback(self) -> None:
        """Callers come from codebase-memory-mcp, then Tree-sitter Analyzer.

        Fail: the map is git grep even when a cataloged tool answered, or
        a dead codebase-memory-mcp aborts the build instead of falling through.
        Recover: a live codebase-memory-mcp sets impact.source and is the
        only map in the prompt. When it fails, Tree-sitter Analyzer is used.
        Neither failure path skips the commit after an accept.
        """
        cm = _write_exe(
            self.side / "cm.py",
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "blob = ' '.join(sys.argv)\n"
            "if 'list_projects' in blob:\n"
            "    print(json.dumps({'projects':[{'name':'stub','root_path': os.getcwd()}]}))\n"
            "    raise SystemExit(0)\n"
            "if 'trace_path' in blob:\n"
            "    print('CALLERS stub_fn -> kept_helper')\n"
            "    raise SystemExit(0)\n"
            "raise SystemExit(1)\n",
        )
        tsa = _write_exe(
            self.side / "tsa.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if '--change-impact' not in sys.argv:\n"
            "    raise SystemExit(1)\n"
            "print('TSA-IMPACT-OK')\n"
            "raise SystemExit(0)\n",
        )
        writer = "Path('use.py').write_text('def kept_helper():\\n    return 3\\n', encoding='utf-8')"
        grok = _write_exe(self.side / "grok.py", _accept_grok(self.log, writer))
        proc = self._run(
            grok,
            "note the helper",
            env={"PFY_CODEBASE_MEMORY": str(cm), "PFY_TSA_BIN": str(tsa)},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["impact"]["source"], "codebase-memory-mcp", text)
        reviews = self._reviews()
        self.assertEqual(len(reviews), 1)
        self.assertIn("Change-impact map:", reviews[0])
        self.assertIn("CALLERS stub_fn -> kept_helper", reviews[0])
        self.assertNotIn("TSA-IMPACT-OK", reviews[0])
        self.assertIsNotNone(payload["commit"])

        dead = _write_exe(
            self.side / "cm-dead.py",
            "#!/usr/bin/env python3\nraise SystemExit(1)\n",
        )
        self.log.write_text("", encoding="utf-8")
        proc = self._run(
            grok,
            "note the helper",
            env={"PFY_CODEBASE_MEMORY": str(dead), "PFY_TSA_BIN": str(tsa)},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["impact"]["source"], "tree-sitter-analyzer", text)
        reviews = self._reviews()
        self.assertTrue(reviews, text)
        self.assertIn("TSA-IMPACT-OK", reviews[-1])
        self.assertNotIn("CALLERS stub_fn", reviews[-1])
        self.assertIsNotNone(payload["commit"])

    def test_one_rejected_file_rejects_the_build(self) -> None:
        """Any one file reject rejects the build. The other file cannot save it.

        Fail: the runner accepts because the first file's verdict was accept,
        and publishes both files.
        Recover: review-rejected, exit 1, no branch. Each prompt carried
        only that file's diff, so the reject is about the bad file.
        """
        writer = (
            "Path('a_good.py').write_text('def kept_good():\\n    return \"GOOD_TOKEN\"\\n', encoding='utf-8')\n"
            "Path('z_bad.py').write_text('def kept_bad():\\n    return \"BAD_TOKEN\"\\n', encoding='utf-8')\n"
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "Path(os.environ['PFY_PROMPT_LOG']).open('a', encoding='utf-8').write(blob + '\\n---PROMPT---\\n')\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    if 'BAD_TOKEN' in blob:\n"
            "        print('verdict: reject')\n"
            "        print('reasons: bad file')\n"
            "    else:\n"
            "        print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "%s\n"
            "raise SystemExit(0)\n" % writer,
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = self._run(grok, "add a good file and a bad file")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["reason"], "review-rejected")
        self.assertEqual(payload["review"]["verdict"], "reject")
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        reviews = self._reviews()
        self.assertGreaterEqual(len(reviews), 2, reviews)
        diffs = [_diff_sections(item) for item in reviews]
        self.assertTrue(any("GOOD_TOKEN" in item and "BAD_TOKEN" not in item for item in diffs), diffs)
        self.assertTrue(any("BAD_TOKEN" in item and "GOOD_TOKEN" not in item for item in diffs), diffs)
        for prompt in reviews:
            self.assertIn("Change-impact map:", prompt)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_stopped_review_does_not_publish_unread_files(self) -> None:
        """A review that dies before the last file does not publish the rest.

        Fail: the middle grok exits non-zero after `verdict: accept`, the
        loop stops, and the runner still treats the unread file as accepted.
        Recover: review-rejected, no branch, and the unread hunk is not in
        a review that was allowed to accept the build.
        """
        writer = (
            "Path('a_ok.py').write_text('def kept_ok():\\n    return \"OK_TOKEN\"\\n', encoding='utf-8')\n"
            "Path('m_stop.py').write_text('def kept_stop():\\n    return \"STOP_TOKEN\"\\n', encoding='utf-8')\n"
            "Path('z_later.py').write_text('def kept_later():\\n    return \"LATER_TOKEN\"\\n', encoding='utf-8')\n"
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "Path(os.environ['PFY_PROMPT_LOG']).open('a', encoding='utf-8').write(blob + '\\n---PROMPT---\\n')\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    if 'STOP_TOKEN' in blob:\n"
            "        raise SystemExit(1)\n"
            "    raise SystemExit(0)\n"
            "%s\n"
            "raise SystemExit(0)\n" % writer,
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = self._run(grok, "add three files")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "review-rejected", text)
        self.assertEqual(payload["review"]["verdict"], "reject")
        self.assertIsNone(payload["commit"])
        self.assertIsNone(payload["branch"])
        diffs = [_diff_sections(item) for item in self._reviews()]
        self.assertTrue(any("STOP_TOKEN" in item for item in diffs), diffs)
        self.assertFalse(any("LATER_TOKEN" in item for item in diffs), diffs)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)


if __name__ == "__main__":
    unittest.main()
