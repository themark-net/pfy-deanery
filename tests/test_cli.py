"""pfylib.cli + the bash dispatcher: `./pfy toolset|hedge ...` (ADR-0017)."""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib import cli, registry  # noqa: E402



def run_cli(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.main(list(argv))
    return code, buf.getvalue()


class _Tmp(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in ("PFY_STATE_DIR", "PFY_CLOUD_BUDGET", "DEPLOY_PROFILE", "CODEX_HOME", "PFY_JEV_OFFLINE")}
        self.tmp = Path(tempfile.mkdtemp(prefix="pfylib-cli-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.state = self.tmp / "state"
        os.environ["PFY_STATE_DIR"] = str(self.state)
        os.environ["CODEX_HOME"] = str(self.tmp / "codex")
        os.environ["PFY_JEV_OFFLINE"] = "1"
        os.environ.pop("PFY_CLOUD_BUDGET", None)
        os.environ.pop("DEPLOY_PROFILE", None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class ToolsetCliTests(_Tmp):
    def test_matrix_json_parses_and_is_complete(self):
        code, out = run_cli("--root", str(ROOT), "toolset", "matrix", "--json")
        self.assertEqual(code, cli.EXIT_READY)
        data = json.loads(out)
        self.assertEqual(data["problems"], [])
        self.assertEqual(len(data["rows"]), len(registry.toolset_ids(ROOT)) * len(registry.harness_ids(ROOT)))
        self.assertTrue(all(r["status"] in ("implemented", "partial", "stub") for r in data["rows"]))

    def test_matrix_text(self):
        code, out = run_cli("--root", str(ROOT), "toolset", "matrix")
        self.assertEqual(code, 0)
        self.assertIn("TOOLSET", out)
        self.assertIn("cells:", out)

    def test_list_and_validate(self):
        code, out = run_cli("--root", str(ROOT), "toolset", "list")
        self.assertEqual(code, 0)
        self.assertIn("jev", out)
        code, out = run_cli("--root", str(ROOT), "toolset", "list", "--json")
        self.assertEqual(len(json.loads(out)), len(registry.toolset_ids(ROOT)))
        code, out = run_cli("--root", str(ROOT), "toolset", "validate")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("READY"))

    def test_plan_ready_stub_fail_exit_codes(self):
        code, out = run_cli("--root", str(ROOT), "toolset", "plan", "jev", "--harness", "opencode")
        self.assertEqual(code, cli.EXIT_READY)
        self.assertIn("READY plan", out)
        self.assertIn("export PFY_DECISION_PATH", out)
        code, out = run_cli("--root", str(ROOT), "toolset", "plan", "jev", "--harness", "gemini")
        self.assertEqual(code, cli.EXIT_STUB)
        self.assertIn("STUB", out)
        code, out = run_cli("--root", str(ROOT), "toolset", "plan", "jev", "--harness", "nope")
        self.assertEqual(code, cli.EXIT_FAIL)

    def test_plan_json_and_env_only(self):
        code, out = run_cli("--root", str(ROOT), "toolset", "plan", "jev", "--harness", "codex", "--json")
        self.assertEqual(code, 0)
        p = json.loads(out)
        self.assertEqual(p["harness"], "codex")
        self.assertTrue(p["brief"])
        code, out = run_cli("--root", str(ROOT), "toolset", "plan", "jev", "--harness", "codex", "--env")
        self.assertEqual(code, 0)
        self.assertTrue(all(line.startswith("export ") for line in out.strip().splitlines()))

    def test_apply_dry_run_then_yes(self):
        code, out = run_cli("--root", str(ROOT), "toolset", "apply", "jev", "--harness", "codex")
        self.assertEqual(code, 0)
        self.assertIn("DRY-RUN", out)
        self.assertFalse(self.state.exists())
        code, out = run_cli("--root", str(ROOT), "toolset", "apply", "jev", "--harness", "codex", "--yes", "--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertFalse(data["dry_run"])
        self.assertEqual(data["failed"], [])
        self.assertTrue((self.tmp / "codex" / "AGENTS.md").is_file())

    def test_usage_error(self):
        with redirect_stderr(io.StringIO()):
            code, _ = run_cli("--root", str(ROOT), "toolset", "plan")
        self.assertEqual(code, cli.EXIT_USAGE)


class HedgeCliTests(_Tmp):
    def test_decide_json_all_task_classes(self):
        for task in ("bulk", "hard", "interactive"):
            code, out = run_cli("--root", str(ROOT), "hedge", "decide", "--task", task, "--local", "ready", "--budget", "0", "--json")
            self.assertEqual(code, 0, task)
            rec = json.loads(out)
            self.assertEqual(rec["lane"], "local")
        code, out = run_cli("--root", str(ROOT), "hedge", "decide", "--task", "bulk", "--local", "missing", "--budget", "0", "--json")
        self.assertEqual(code, cli.EXIT_FAIL)
        self.assertIsNone(json.loads(out)["lane"])

    def test_decide_record_and_ledger(self):
        code, out = run_cli("--root", str(ROOT), "hedge", "decide", "--task", "hard", "--local", "missing", "--budget", "2", "--record")
        self.assertEqual(code, 0)
        self.assertIn("lane=cloud", out)
        code, out = run_cli("--root", str(ROOT), "hedge", "ledger", "--budget", "2", "--json")
        self.assertEqual(code, 0)
        led = json.loads(out)
        self.assertEqual((led["spent"], led["remaining"]), (1, 1))
        code, out = run_cli("--root", str(ROOT), "hedge", "record", "1", "--task", "hard", "--budget", "2", "--json")
        self.assertEqual(json.loads(out)["remaining"], 0)
        code, out = run_cli("--root", str(ROOT), "hedge", "ledger")
        self.assertIn("2 entries", out)
        code, out = run_cli("--root", str(ROOT), "hedge", "ledger", "--reset")
        self.assertEqual(json.loads(run_cli("--root", str(ROOT), "hedge", "ledger", "--json")[1])["spent"], 0)


class DispatcherTests(_Tmp):
    """The bash `./pfy` verbs exec pfylib/cli.py -- exercised as a subprocess."""

    def _pfy(self, *args: str) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        return subprocess.run(["bash", str(ROOT / "scripts" / "pfy"), *args], cwd=ROOT, capture_output=True, text=True, env=env, timeout=60)

    def test_pfy_toolset_matrix_json(self):
        p = self._pfy("toolset", "matrix", "--json")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["problems"], [])

    def test_pfy_hedge_decide_exit_codes(self):
        p = self._pfy("hedge", "decide", "--task", "bulk", "--local", "ready", "--budget", "0")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("lane=local", p.stdout)

    def test_pfy_help_lists_new_verbs(self):
        p = self._pfy("help")
        self.assertEqual(p.returncode, 0)
        self.assertIn("pfy toolset matrix", p.stdout)
        self.assertIn("pfy hedge decide", p.stdout)

    def test_pfy_help_separates_product_eval_from_catalog_eval(self):
        # Fail: `pfy eval` reads as the catalog verdict lane, so a new user
        # runs the product gate (or the lane) for the other job.
        # Recovery: help names the make target, the receipt dir, and the lane.
        p = self._pfy("help")
        self.assertEqual(p.returncode, 0, p.stderr)
        for phrase in (
            "not a catalog verdict",
            "make eval-integration-change",
            "pipelines/eval",
            "does not call Grok and does not push main",
            "scripts/eval_lane.sh --slug <slug>",
            "scripts/catalog_intake_dedupe.py",
        ):
            self.assertIn(phrase, p.stdout, phrase)

    def test_pfy_eval_runs_product_gate_not_catalog_lane(self):
        # Fail: `./pfy eval` starts scripts/eval_lane.sh (Grok, then push main)
        # or writes the product receipt during the check.
        # Recovery: it only execs `make eval-integration-change` and returns.
        bindir = self.tmp / "bin"
        bindir.mkdir()
        log = self.tmp / "make.log"
        grok_flag = self.tmp / "grok-called"
        make = bindir / "make"
        make.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"argv0=$0\" \"REASON=${REASON-}\" \"$*\" > "
            + repr(str(log))
            + "\nexit 0\n",
            encoding="utf-8",
        )
        make.chmod(0o755)
        grok = bindir / "grok"
        grok.write_text(
            "#!/bin/sh\nprintf '%s\\n' called > " + repr(str(grok_flag)) + "\nexit 99\n",
            encoding="utf-8",
        )
        grok.chmod(0o755)
        receipt = ROOT / "pipelines" / "eval" / "integration-change.latest.md"
        before = receipt.stat().st_mtime_ns if receipt.is_file() else None
        env = dict(os.environ)
        env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
        env["PFY_STATE_DIR"] = str(self.state)
        env.pop("REASON", None)
        p = subprocess.run(
            [str(ROOT / "pfy"), "eval"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        self.assertNotIn("eval_lane", p.stdout + p.stderr)
        self.assertNotIn("missing --slug", p.stderr)
        self.assertFalse(grok_flag.exists(), "pfy eval called grok")
        after = receipt.stat().st_mtime_ns if receipt.is_file() else None
        self.assertEqual(before, after, "pfy eval wrote the product receipt")
        text = log.read_text(encoding="utf-8")
        self.assertIn("REASON=pfy eval", text)
        self.assertEqual(text.strip().splitlines()[-1], "eval-integration-change")

    def test_operator_docs_name_both_eval_commands(self):
        # Fail: a product doc calls ./pfy eval the catalog lane, so the next
        # reader runs scripts/eval_lane.sh or the product gate for the wrong job.
        # Recovery: each surface names make eval-integration-change and the lane.
        required = (
            ROOT / "README.md",
            ROOT / "docs" / "DESIGN.md",
            ROOT / "docs" / "modules" / "pfy.md",
            ROOT / "docs" / "ops" / "simple-launch.md",
            ROOT / "docs" / "ops" / "product-operator-surface.md",
            ROOT / "docs" / "ops" / "consultant-eval.md",
            ROOT / "docs" / "ops" / "integration-self-mod-eval.md",
            ROOT / "Makefile",
            ROOT / "scripts" / "eval_lane.sh",
            ROOT / "scripts" / "pfy",
            ROOT / "bootstrap" / "grok-cli" / "skills" / "catalog-eval-lane" / "SKILL.md",
            ROOT / ".grok" / "skills" / "catalog-eval-lane" / "SKILL.md",
        )
        for path in required:
            text = path.read_text(encoding="utf-8")
            self.assertIn("eval-integration-change", text, path)
            self.assertIn("scripts/eval_lane.sh", text, path)
        for path in (
            ROOT / "docs" / "ops" / "simple-launch.md",
            ROOT / "docs" / "ops" / "consultant-eval.md",
        ):
            self.assertNotIn("catalog self-mod", path.read_text(encoding="utf-8"), path)

    def test_python_m_pfylib_entry(self):
        p = subprocess.run([sys.executable, "-m", "pfylib", "toolset", "validate", "--json"], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(json.loads(p.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
