# pk2: grill step before cutting any CI, pipeline or gate ticket (branch bot/grill-step-1107)

Why: the 2026-11-03 trial (a private ops note, already committed on this branch by the driver from 31db5ff) showed a tools-off grill caught a real fail-open the exit test missed. We then never used it on pipeline changes, and the pipeline ran the full suite about 6 times per landing. The operator approved this on 2026-11-07.

Lanes and tickets are cut in two places: (1) sandcastle-grok (`src/lanes.mts`, tickets `{id,title,body,blockedBy[],exitTest{path,content}}`, batches/*.json), a local repo with a worktree for you at $HOME/DEVELOP/pfy-mentat/tmp/pk-2/tmp/sc (inside this worktree's ignored tmp/, so it is in your cwd) on branch bot/grill-step-1107 (node_modules symlinked; commit there too, do not touch $HOME/DEVELOP/sandcastle-grok itself), and (2) bot-written detached drivers that put a TICKET-<label>.md into a pfy-mentat worktree (see ~/DEVELOP/pfy-mentat/tmp/pk1107/lane.sh for the pattern; read only).

## DoD
1. **scripts/grill_ticket.py** (stdlib Python) in pfy-mentat:
   - Input: a ticket (markdown file, or a sandcastle JSON ticket/batch) plus touched paths (`--paths`, or parsed from the ticket body, or `--diff <ref>`).
   - Trigger: runs only when a touched path or the ticket text hits CI, pipeline or gate files: `.github/workflows/**`, `ci/**`, `pipelines/**`, `scripts/pregate*`, `scripts/run_tests.py`, `scripts/test_select.py`, `scripts/test_cache.py`, `scripts/*gate*`, `scripts/model_lock.sh`, Makefile CI/test targets, docs/ops/MODULAR-CI.md, docs/ops/PREGATE.md (keep the list in one place, data or constant, with a test). Otherwise exit 0 with "no grill needed".
   - Grill: one headless grok call with tools off (no tool use at all: use the CLI's flags to remove built-in tools, disable web search and subagents; verify on nimo which flags actually achieve this and record it), `--max-turns` hard cap of 12 or less (enforced in code, reject higher), prompt = the vendored grilling skill text (bootstrap/grok-cli/skills-external/mattpocock/grilling/SKILL.md if present on main; another lane is vendoring it now, so fall back to a short embedded summary and say which was used) + the ticket + seeds: software-factory Q5 "What stops two runs doing the same work?" and the Modular CI rule text (single source: AGENTS.md "Modular CI" section if present, else docs/ops/MODULAR-CI.md, else an embedded copy). Ask for structured output (`--json-schema`): numbered questions, each with a recommended answer and `behavior_change: true|false` plus, when true, a concrete testable assertion.
   - Coordinator answers (never the operator): default is a second tools-off capped call acting as coordinator that accepts or overrides each recommended answer using AGENTS.md rules; `--answers <file>` lets a bot coordinator supply answers instead. Total turns across both calls stay within the cap.
   - Behavior-changing answers become exit tests: append an "Exit tests from grill" section to a markdown ticket, and for sandcastle JSON tickets add executable exit-test cases (extend the contract to a list if needed, keeping the existing single `exitTest` working) so they are committed before Build and are not editable by the agent. Write the full grill record (questions, answers, which became tests, model, turns, cost if reported, which skill text was used) to `<ticket>.grill.json`.
   - Binary via `PFY_GROK_BIN` (default ~/.local/bin/grok). Tests use a fake grok script (no network, no real model): trigger/no-trigger, cap enforcement, tools-off flags present, behavior-change answers turn into exit tests, fallback when the vendored skill is missing.
2. **sandcastle-grok**: add an optional `--grill auto|off` (default auto) step in src/lanes.mts before a lane is cut: for tickets that touch CI, pipeline or gate files it calls `python3 <pfy-mentat checkout>/scripts/grill_ticket.py` (path configurable via env `PFY_MENTAT_DIR`, default ~/DEVELOP/pfy-mentat), merges the resulting exit tests into the ticket, and records the grill in the receipt (count, turns, cost). A grill failure blocks only that ticket with a clear reason; it never silently skips. Update README-INTEGRATION.md. Commit in the sandcastle worktree on bot/grill-step-1107 with a test or smoke run that proves the hook fires for a CI ticket and not for a plain one (use the fake grok).
3. **Bot drivers**: document in docs/ops/GRILL-STEP.md how a coordinator bot runs the grill before writing a TICKET-<label>.md for any CI/pipeline/gate lane, with the exact command, and add it as a short rule line in docs/ops/loop-engineering.md or the most relevant existing ops doc (not AGENTS.md; another lane edits AGENTS.md).
4. **Real run**: run the grill once for real on nimo against this lane's own ticket (it touches gate tooling) and against ~/DEVELOP/pfy-mentat/tmp/fp1107/TICKET-s3.md (read only; write outputs under docs/ops/grill-samples/ or tmp), report question count, behavior-changing answers, turns, wall time and cost in GRILL-STEP.md. No secrets.
5. Keep a private ops note as committed (you may add a one-line pointer to GRILL-STEP.md at the end).
6. Handoff: a private ops note (what changed in both repos, commands, real-run numbers, risks).

## Rules for every pk1107 lane
- Commit on this branch in this worktree; do not push (the driver pushes). Clean `git status` at the end.
- Never print, paste, echo or quote a secret value anywhere (chat, logs, commits). Refer to secrets by name only. No sudo. Never edit `~/.grok/config.toml`, never touch `~/DEVELOP/pfy-mentat` (the operator's checkout) working tree, never stop processes you did not start.
- Modular CI rule (standing): run only the tests your change can affect while you work, the selected or full suite once at the end; no new serialized or long CI job unless it is bound by local-model token speed; light jobs run in parallel. Do not add a step that re-runs work another step already did.
- Pipeline changes check the catalog first: before adding or changing a pipeline, CI or gate step, check docs/eval/TOOLSET-RANKING.md and data/tool_integration_stages.json (or the per-tool files under the split registry, if present) for tools covering the job, and state in your handoff what you used or why not.
- Other lanes are running in parallel: bot/fastpipe-1107 (scripts/run_tests.py, test_select.py, test_cache.py, pregate, AGENTS.md Modular CI), bot/stages-split-1107 (splits data/tool_integration_stages.json into per-tool files, edits catalog_check). Stay out of files outside your DoD to avoid conflicts.
- Tests: behavior only, few, no tautologies; each new test must fail without your change. Self-review the diff before finishing (risky paths: trading/live money, release/deploy, secrets must keep full checks).
- Style: no em dashes in docs or messages. Leave a short handoff doc under docs/ops/ named in the DoD.

## Exit tests from grill

Fixed by the coordinator before Build. Do not edit this section.

### Q1

- Answer: Yes. Lock the ticket path for the duration of the grok calls, store a hash of the ticket bytes and the path set in the sidecar, and skip the model when that hash is unchanged.
- Behavior change: true
- Assertion: Two sequential runs with the same ticket bytes and paths record the same grok launch count, and two overlapping runs record exactly one launch.

Test path: `tests/test_grill_idempotency.py`

```python
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "grill_ticket.py"


def _fake(path: Path) -> None:
    path.write_text(
        "#!/bin/sh\n"
        "cat >/dev/null\n"
        "printf 'x\\n' >> \"$GRILL_COUNT_FILE\"\n"
        "sleep 1\n"
        "printf '%s\\n' '{\"questions\":[{\"n\":1,\"question\":\"q\",\"recommended_answer\":\"Yes\",\"behavior_change\":false}]}'\n"
    )
    path.chmod(0o755)


def _run(ticket: Path, env: dict) -> subprocess.CompletedProcess:
    answers = ticket.parent / "answers.json"
    answers.write_text('{"1":{"answer":"Yes","behavior_change":false}}')
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(ticket), "--paths", "ci/pipeline.yml", "--answers", str(answers)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


class GrillIdempotencyTest(unittest.TestCase):
    def test_same_bytes_do_not_call_grok_again(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            fake = d / "grok"
            _fake(fake)
            ticket = d / "t.md"
            ticket.write_text("lane touches ci/pipeline.yml\n")
            count = d / "count"
            count.write_text("")
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            env["GRILL_COUNT_FILE"] = str(count)
            first = _run(ticket, env)
            self.assertEqual(first.returncode, 0, first.stderr)
            n1 = count.read_text().count("x")
            self.assertEqual(n1, 1)
            second = _run(ticket, env)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(count.read_text().count("x"), n1)

    def test_overlapping_runs_launch_grok_once(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            fake = d / "grok"
            _fake(fake)
            ticket = d / "t.md"
            ticket.write_text("lane touches ci/pipeline.yml\n")
            count = d / "count"
            count.write_text("")
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            env["GRILL_COUNT_FILE"] = str(count)
            answers = d / "answers.json"
            answers.write_text('{"1":{"answer":"Yes","behavior_change":false}}')
            cmd = [sys.executable, str(SCRIPT), str(ticket), "--paths", "ci/pipeline.yml", "--answers", str(answers)]
            a = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            b = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            a.wait(timeout=15)
            b.wait(timeout=15)
            self.assertEqual(a.returncode, 0, a.stderr.read() if a.stderr else "")
            self.assertEqual(b.returncode, 0, b.stderr.read() if b.stderr else "")
            self.assertEqual(count.read_text().count("x"), 1)
```

### Q2

- Answer: Yes. grill_ticket.py is a local pre-cut command. It must not start GitHub Actions, scripts/run_tests.py, pytest, or make, and the sandcastle hook must not run the suite.
- Behavior change: true
- Assertion: scripts/grill_ticket.py contains no reference to run_tests.py, pytest, or a make test target, and the repo has no workflow file whose name contains grill.

Test path: `tests/test_grill_modular_ci.py`

```python
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ModularCiObeyTest(unittest.TestCase):
    def test_grill_script_does_not_run_the_suite_or_add_a_job(self):
        text = (ROOT / "scripts" / "grill_ticket.py").read_text(encoding="utf-8")
        self.assertNotIn("run_tests.py", text)
        self.assertNotIn("pytest", text)
        self.assertNotIn("make test", text)
        workflows = ROOT / ".github" / "workflows"
        if workflows.exists():
            named = [p.name for p in workflows.iterdir() if "grill" in p.name.lower()]
            self.assertEqual(named, [])
```

### Q3

- Answer: Yes. Keep the verified flag spellings in TOOLS_OFF_FLAGS keyed by no_builtin_tools, no_web_search, and no_subagents, and do not exec grok if any of them or --json-schema is absent.
- Behavior change: true
- Assertion: A successful grill argv includes --json-schema and every flag value in TOOLS_OFF_FLAGS for no_builtin_tools, no_web_search, and no_subagents.

Test path: `tests/test_grill_tools_off.py`

```python
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load():
    path = ROOT / "scripts" / "grill_ticket.py"
    spec = importlib.util.spec_from_file_location("grill_ticket", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ToolsOffTest(unittest.TestCase):
    def test_argv_has_schema_and_tools_off_flags(self):
        mod = load()
        self.assertEqual(
            set(mod.TOOLS_OFF_FLAGS),
            {"no_builtin_tools", "no_web_search", "no_subagents"},
        )
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            argv_log = d / "argv"
            fake = d / "grok"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, sys, os\n"
                "pathlib.Path(os.environ['ARGV_LOG']).write_text('\\n'.join(sys.argv))\n"
                "sys.stdin.read()\n"
                "print('{\"questions\":[{\"n\":1,\"question\":\"q\",\"recommended_answer\":\"Yes\",\"behavior_change\":false}]}')\n"
            )
            fake.chmod(0o755)
            ticket = d / "t.md"
            ticket.write_text("ci/pipeline.yml\n")
            answers = d / "a.json"
            answers.write_text('{"1":{"answer":"Yes","behavior_change":false}}')
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            env["ARGV_LOG"] = str(argv_log)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "grill_ticket.py"), str(ticket), "--paths", "ci/pipeline.yml", "--answers", str(answers)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            text = argv_log.read_text(encoding="utf-8")
            self.assertIn("--json-schema", text)
            for flag in mod.TOOLS_OFF_FLAGS.values():
                self.assertTrue(str(flag).startswith("--"), flag)
                self.assertIn(str(flag), text)
```

### Q4

- Answer: Yes. Reject --max-turns above 12 in the script before exec, and pass --max-turns 6 on each of the two calls.
- Behavior change: true
- Assertion: grill_ticket.py --max-turns 13 launches no grok and exits non-zero, and a normal run passes --max-turns 6.

Test path: `tests/test_grill_turn_cap.py`

```python
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "grill_ticket.py"


class TurnCapTest(unittest.TestCase):
    def test_rejects_above_12_without_launch(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            count = d / "count"
            count.write_text("")
            fake = d / "grok"
            fake.write_text("#!/bin/sh\nprintf 'x\\n' >> \"$GRILL_COUNT_FILE\"\ncat >/dev/null\n")
            fake.chmod(0o755)
            ticket = d / "t.md"
            ticket.write_text("ci/x\n")
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            env["GRILL_COUNT_FILE"] = str(count)
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(ticket), "--paths", "ci/x.yml", "--max-turns", "13"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(count.read_text(), "")

    def test_each_call_uses_max_turns_6(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            argv_log = d / "argv"
            fake = d / "grok"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import os, pathlib, sys\n"
                "pathlib.Path(os.environ['ARGV_LOG']).open('a').write(' '.join(sys.argv)+'\\n')\n"
                "sys.stdin.read()\n"
                "print('{\"questions\":[{\"n\":1,\"question\":\"q\",\"recommended_answer\":\"Yes\",\"behavior_change\":false}]}')\n"
            )
            fake.chmod(0o755)
            ticket = d / "t.md"
            ticket.write_text("ci/x\n")
            answers = d / "a.json"
            answers.write_text('{"1":{"answer":"Yes","behavior_change":false}}')
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            env["ARGV_LOG"] = str(argv_log)
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(ticket), "--paths", ".github/workflows/ci.yml", "--answers", str(answers)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("--max-turns 6", argv_log.read_text(encoding="utf-8"))
```

### Q5

- Answer: Yes. When --answers is present, launch only the question call, then apply that file. A string value is not accepted.
- Behavior change: true
- Assertion: With a valid --answers file, grok is launched once and the applied behavior_change is the one in the file.

Test path: `tests/test_grill_answers_file.py`

```python
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "grill_ticket.py"


class AnswersFileTest(unittest.TestCase):
    def test_answers_file_skips_second_call_and_sets_behavior(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            count = d / "count"
            count.write_text("")
            fake = d / "grok"
            fake.write_text(
                "#!/bin/sh\n"
                "printf 'x\\n' >> \"$GRILL_COUNT_FILE\"\n"
                "cat >/dev/null\n"
                "printf '%s\\n' '{\"questions\":[{\"n\":1,\"question\":\"Ship a gate?\",\"recommended_answer\":\"Yes\",\"behavior_change\":false}]}'\n"
            )
            fake.chmod(0o755)
            ticket = d / "t.md"
            ticket.write_text("touches scripts/pregate.sh\n")
            answers = d / "a.json"
            answers.write_text('{"1":{"answer":"Yes, block on empty assertion","behavior_change":true}}')
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            env["GRILL_COUNT_FILE"] = str(count)
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(ticket), "--paths", "scripts/pregate.sh", "--answers", str(answers)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(count.read_text().count("x"), 1)
            record = json.loads(Path(str(ticket) + ".grill.json").read_text(encoding="utf-8"))
            applied = record["questions"][0]
            self.assertTrue(applied["behavior_change"])
            self.assertEqual(applied["answer"], "Yes, block on empty assertion")
            body = ticket.read_text(encoding="utf-8")
            self.assertIn("Exit tests from grill", body)
```

### Q6

- Answer: Yes. Preserve exitTest as-is and append grill cases to exitTests. A ticket with only exitTest remains valid.
- Behavior change: true
- Assertion: After grilling a JSON ticket, the original exitTest object is unchanged and each behavior-changing answer appears as an additional exitTests item.

Test path: `tests/test_grill_exit_tests_list.py`

```python
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "grill_ticket.py"


class ExitTestsListTest(unittest.TestCase):
    def test_preserves_exit_test_and_appends_list(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            fake = d / "grok"
            fake.write_text(
                "#!/bin/sh\n"
                "cat >/dev/null\n"
                "printf '%s\\n' '{\"questions\":[{\"n\":1,\"question\":\"q\",\"recommended_answer\":\"Yes\",\"behavior_change\":true,\"assertion\":\"gate rejects a dirty tree\"}]}'\n"
            )
            fake.chmod(0o755)
            original = {"path": "tests/test_existing.py", "content": "print('keep')\n"}
            ticket = d / "batch.json"
            ticket.write_text(json.dumps({
                "tickets": [{
                    "id": "t1",
                    "title": "gate",
                    "body": "edit .github/workflows/ci.yml",
                    "blockedBy": [],
                    "exitTest": original,
                }]
            }))
            answers = d / "a.json"
            answers.write_text('{"1":{"answer":"Yes","behavior_change":true}}')
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(ticket), "--paths", ".github/workflows/ci.yml", "--answers", str(answers)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(ticket.read_text(encoding="utf-8"))
            item = data["tickets"][0]
            self.assertEqual(item["exitTest"], original)
            self.assertGreaterEqual(len(item["exitTests"]), 1)
            self.assertIn("gate rejects a dirty tree", json.dumps(item["exitTests"]))
```

### Q7

- Answer: Yes. Fail closed for the bad ticket only. Continue the rest of the batch, then exit 3 if any required ticket failed.
- Behavior change: true
- Assertion: A batch with one bad CI ticket and one good CI ticket exits 3, records a non-empty reason for the bad ticket, and still writes a sidecar for the good ticket.

Test path: `tests/test_grill_batch_failure.py`

```python
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "grill_ticket.py"


class BatchFailureTest(unittest.TestCase):
    def test_one_bad_ticket_does_not_drop_the_other(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            fake = d / "grok"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "raw = sys.stdin.read()\n"
                "if 'BADTICKET' in raw:\n"
                "    print('not-json')\n"
                "    raise SystemExit(0)\n"
                "print('{\"questions\":[{\"n\":1,\"question\":\"q\",\"recommended_answer\":\"Yes\",\"behavior_change\":false}]}')\n"
            )
            fake.chmod(0o755)
            batch = d / "batch.json"
            batch.write_text(json.dumps({"tickets": [
                {"id": "bad", "title": "b", "body": "BADTICKET ci/a.yml", "blockedBy": [], "exitTest": {"path": "t.py", "content": "x"}},
                {"id": "good", "title": "g", "body": "GOOD ci/b.yml", "blockedBy": [], "exitTest": {"path": "t.py", "content": "x"}},
            ]}))
            answers = d / "a.json"
            answers.write_text('{"1":{"answer":"Yes","behavior_change":false}}')
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(batch), "--answers", str(answers)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 3, proc.stderr)
            reason = (proc.stderr + proc.stdout).strip()
            self.assertIn("bad", reason.lower() + reason)
            self.assertTrue(reason)
            self.assertTrue((d / "batch.json.good.grill.json").exists() or (d / "good.grill.json").exists())
```

### Q8

- Answer: Yes. One tuple is the only trigger list, and those two paths trigger on name match alone.
- Behavior change: true
- Assertion: TRIGGER_GLOBS includes Makefile and scripts/run_tests.py, and a ticket that only touches Makefile does not print no grill needed.

Test path: `tests/test_grill_trigger_globs.py`

```python
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load():
    path = ROOT / "scripts" / "grill_ticket.py"
    spec = importlib.util.spec_from_file_location("grill_ticket", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TriggerGlobTest(unittest.TestCase):
    def test_tuple_and_makefile_triggers(self):
        mod = load()
        globs = list(mod.TRIGGER_GLOBS)
        self.assertIn("Makefile", globs)
        self.assertIn("scripts/run_tests.py", globs)
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            fake = d / "grok"
            fake.write_text(
                "#!/bin/sh\ncat >/dev/null\n"
                "printf '%s\\n' '{\"questions\":[{\"n\":1,\"question\":\"q\",\"recommended_answer\":\"Yes\",\"behavior_change\":false}]}'\n"
            )
            fake.chmod(0o755)
            ticket = d / "t.md"
            ticket.write_text("docs only in the body\n")
            answers = d / "a.json"
            answers.write_text('{"1":{"answer":"Yes","behavior_change":false}}')
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "grill_ticket.py"), str(ticket), "--paths", "Makefile", "--answers", str(answers)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertNotIn("no grill needed", (proc.stdout + proc.stderr).lower())
```

### Q9

- Answer: Yes. Record which text was used and continue with the embedded summary when the vendored file is absent.
- Behavior change: true
- Assertion: When the vendored skill path is missing, the sidecar skill_source is embedded and the run still exits 0.

Test path: `tests/test_grill_skill_source.py`

```python
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "grill_ticket.py"


class SkillSourceTest(unittest.TestCase):
    def test_missing_skill_records_embedded(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            fake = d / "grok"
            fake.write_text(
                "#!/bin/sh\ncat >/dev/null\n"
                "printf '%s\\n' '{\"questions\":[{\"n\":1,\"question\":\"q\",\"recommended_answer\":\"Yes\",\"behavior_change\":false}]}'\n"
            )
            fake.chmod(0o755)
            ticket = d / "t.md"
            ticket.write_text("ci/pipeline.yml\n")
            answers = d / "a.json"
            answers.write_text('{"1":{"answer":"Yes","behavior_change":false}}')
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            env["GRILL_SKILL_PATH"] = str(d / "missing-SKILL.md")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(ticket), "--paths", "ci/pipeline.yml", "--answers", str(answers)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            record = json.loads(Path(str(ticket) + ".grill.json").read_text(encoding="utf-8"))
            self.assertEqual(record["skill_source"], "embedded")
```

### Q10

- Answer: Yes. Missing cost is not a failure. Write null and continue.
- Behavior change: true
- Assertion: A fake grok that prints questions and no cost field yields exit 0 and sidecar cost null.

Test path: `tests/test_grill_cost_null.py`

```python
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CostNullTest(unittest.TestCase):
    def test_missing_cost_is_null(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            fake = d / "grok"
            fake.write_text(
                "#!/bin/sh\ncat >/dev/null\n"
                "printf '%s\\n' '{\"questions\":[{\"n\":1,\"question\":\"q\",\"recommended_answer\":\"Yes\",\"behavior_change\":false}]}'\n"
            )
            fake.chmod(0o755)
            ticket = d / "t.md"
            ticket.write_text("pipelines/gate.yml\n")
            answers = d / "a.json"
            answers.write_text('{"1":{"answer":"Yes","behavior_change":false}}')
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "grill_ticket.py"), str(ticket), "--paths", "pipelines/gate.yml", "--answers", str(answers)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            record = json.loads(Path(str(ticket) + ".grill.json").read_text(encoding="utf-8"))
            self.assertIsNone(record["cost"])
```

### Q11

- Answer: Yes. The applied coordinator answer decides the exit test. An override to behavior_change false adds no exit test. The coordinator prompt includes the Modular CI rule so it can reject a new full-suite job.
- Behavior change: true
- Assertion: When the first call recommends a behavior change and the coordinator call sets behavior_change false, the ticket file gains no Exit tests from grill section.

Test path: `tests/test_grill_coordinator_override.py`

```python
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CoordinatorOverrideTest(unittest.TestCase):
    def test_override_false_adds_no_exit_section(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            fake = d / "grok"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "raw = sys.stdin.read()\n"
                "if 'coordinator' in raw.lower():\n"
                "    print('{\"answers\":{\"1\":{\"accept\":false,\"answer\":\"No\",\"behavior_change\":false}}}')\n"
                "else:\n"
                "    print('{\"questions\":[{\"n\":1,\"question\":\"Add a full suite job?\",\"recommended_answer\":\"Yes\",\"behavior_change\":true,\"assertion\":\"Add a required full-suite CI job.\"}]}')\n"
            )
            fake.chmod(0o755)
            ticket = d / "t.md"
            ticket.write_text("change ci/pipeline.yml\n")
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "grill_ticket.py"), str(ticket), "--paths", "ci/pipeline.yml"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            body = ticket.read_text(encoding="utf-8")
            self.assertNotIn("Exit tests from grill", body)
            self.assertNotIn("full-suite", body)
```

### Q12

- Answer: Yes. Both seeds are always in the prompt, and the Modular CI text comes from that single fallback chain.
- Behavior change: true
- Assertion: The stdin of the question call contains 'What stops two runs doing the same work?' and the sentence 'run only the tests your change can affect'.

Test path: `tests/test_grill_prompt_seeds.py`

```python
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PromptSeedTest(unittest.TestCase):
    def test_prompt_contains_both_seeds(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            prompt = d / "prompt"
            fake = d / "grok"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import os, pathlib, sys\n"
                "pathlib.Path(os.environ['PROMPT_LOG']).write_text(sys.stdin.read())\n"
                "print('{\"questions\":[{\"n\":1,\"question\":\"q\",\"recommended_answer\":\"Yes\",\"behavior_change\":false}]}')\n"
            )
            fake.chmod(0o755)
            ticket = d / "t.md"
            ticket.write_text("ci/pipeline.yml\n")
            answers = d / "a.json"
            answers.write_text('{"1":{"answer":"Yes","behavior_change":false}}')
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            env["PROMPT_LOG"] = str(prompt)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "grill_ticket.py"), str(ticket), "--paths", "ci/pipeline.yml", "--answers", str(answers)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            text = prompt.read_text(encoding="utf-8")
            self.assertIn("What stops two runs doing the same work?", text)
            self.assertIn("run only the tests your change can affect", text)
```

### Q13

- Answer: Yes. Non-matching tickets are a clean no-op with that exact phrase and no sidecar.
- Behavior change: true
- Assertion: A markdown ticket with path README.md exits 0, stdout contains 'no grill needed', grok is not launched, and no .grill.json file is created.

Test path: `tests/test_grill_no_trigger.py`

```python
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NoTriggerTest(unittest.TestCase):
    def test_plain_ticket_skips(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            count = d / "count"
            count.write_text("")
            fake = d / "grok"
            fake.write_text("#!/bin/sh\nprintf 'x\\n' >> \"$GRILL_COUNT_FILE\"\ncat >/dev/null\n")
            fake.chmod(0o755)
            ticket = d / "t.md"
            ticket.write_text("update the readme only\n")
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            env["GRILL_COUNT_FILE"] = str(count)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "grill_ticket.py"), str(ticket), "--paths", "README.md"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("no grill needed", proc.stdout.lower())
            self.assertEqual(count.read_text(), "")
            self.assertFalse(Path(str(ticket) + ".grill.json").exists())
```

### Q14

- Answer: Yes. A required grill with no binary fails closed. The default binary path is ~/.local/bin/grok when the env var is unset and that file exists.
- Behavior change: true
- Assertion: When PFY_GROK_BIN points at a missing file and the path is ci/pipeline.yml, the process exits non-zero and writes no grill sidecar.

Test path: `tests/test_grill_missing_bin.py`

```python
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MissingBinTest(unittest.TestCase):
    def test_missing_binary_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            ticket = d / "t.md"
            ticket.write_text("ci/pipeline.yml\n")
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(d / "no-such-grok")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "grill_ticket.py"), str(ticket), "--paths", "ci/pipeline.yml"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(Path(str(ticket) + ".grill.json").exists())
            self.assertNotIn("no grill needed", (proc.stdout + proc.stderr).lower())
```

### Q15

- Answer: Yes. Attach assertions to the ticket the cutter commits. Do not write model-supplied paths into the tests tree.
- Behavior change: true
- Assertion: A behavior_change answer that names tests/from_model.py updates the ticket and sidecar and does not create tests/from_model.py.

Test path: `tests/test_grill_no_model_test_files.py`

```python
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NoModelTestFilesTest(unittest.TestCase):
    def test_model_test_path_is_not_written(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            fake = d / "grok"
            fake.write_text(
                "#!/bin/sh\ncat >/dev/null\n"
                "printf '%s\\n' '{\"questions\":[{\"n\":1,\"question\":\"q\",\"recommended_answer\":\"Yes\",\"behavior_change\":true,\"assertion\":\"the gate fails closed\",\"test_path\":\"tests/from_model.py\",\"test_content\":\"print(123)\\n\"}]}'\n"
            )
            fake.chmod(0o755)
            ticket = d / "t.md"
            ticket.write_text("scripts/model_lock.sh\n")
            answers = d / "a.json"
            answers.write_text('{"1":{"answer":"Yes","behavior_change":true}}')
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "grill_ticket.py"), str(ticket), "--paths", "scripts/model_lock.sh", "--answers", str(answers)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("Exit tests from grill", ticket.read_text(encoding="utf-8"))
            self.assertIn("the gate fails closed", ticket.read_text(encoding="utf-8"))
            self.assertFalse((ROOT / "tests" / "from_model.py").exists())
            self.assertTrue(Path(str(ticket) + ".grill.json").exists())
```

### Q16

- Answer: Yes. Pass --model only when PFY_GROK_MODEL is non-empty, and then pass that value.
- Behavior change: true
- Assertion: With PFY_GROK_MODEL unset, grok argv has no --model flag; with PFY_GROK_MODEL=dummy, argv contains --model dummy.

Test path: `tests/test_grill_model_flag.py`

```python
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "grill_ticket.py"


def run(env, ticket, answers, argv_log):
    env = env.copy()
    env["ARGV_LOG"] = str(argv_log)
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(ticket), "--paths", "docs/ops/PREGATE.md", "--answers", str(answers)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


class ModelFlagTest(unittest.TestCase):
    def test_model_flag_follows_env(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            fake = d / "grok"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import os, pathlib, sys\n"
                "pathlib.Path(os.environ['ARGV_LOG']).write_text(' '.join(sys.argv))\n"
                "sys.stdin.read()\n"
                "print('{\"questions\":[{\"n\":1,\"question\":\"q\",\"recommended_answer\":\"Yes\",\"behavior_change\":false}]}')\n"
            )
            fake.chmod(0o755)
            ticket = d / "t.md"
            ticket.write_text("docs/ops/PREGATE.md\n")
            answers = d / "a.json"
            answers.write_text('{"1":{"answer":"Yes","behavior_change":false}}')
            argv_log = d / "argv"
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            env.pop("PFY_GROK_MODEL", None)
            first = run(env, ticket, answers, argv_log)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertNotIn("--model", argv_log.read_text(encoding="utf-8"))
            ticket.write_text("docs/ops/PREGATE.md changed\n")
            sidecar = Path(str(ticket) + ".grill.json")
            if sidecar.exists():
                sidecar.unlink()
            env["PFY_GROK_MODEL"] = "dummy"
            second = run(env, ticket, answers, argv_log)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("--model dummy", argv_log.read_text(encoding="utf-8"))
```
