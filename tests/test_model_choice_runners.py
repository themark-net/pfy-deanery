"""Runners take their default from model_choice and keep their own flag.

Fail: a cloud choice on an Ollama-only runner is sent to the provider, or
PFY_MODEL_<TASK> beats the runner's own env. Recover: one refusal line, the
committed local model, and zero provider calls.
"""
from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib import model_choice as mc  # noqa: E402
from tests._model_choice_isolation import begin, end  # noqa: E402


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RunnerChoiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp, self.saved = begin(prefix="pfy-runner-")
        self.calls: list = []
        self._transport = mc._TRANSPORT
        mc._TRANSPORT = self._refuse

    def tearDown(self) -> None:
        mc._TRANSPORT = self._transport
        end(self.tmp, self.saved)

    def _refuse(self, req: dict) -> dict:
        self.calls.append(req)
        raise AssertionError("provider called")

    def test_eval_suite_precedence_and_cloud_refusal(self) -> None:
        # Committed default, then user, then PFY_MODEL, then the runner env.
        backend, model, source = mc.runner_choice("eval-suite", transport="ollama", root=ROOT)
        self.assertEqual((backend, model, source), ("local", "qwen2.5:14b", "default"))

        mc.save_task("eval-suite", "local", "custom:9b")
        backend, model, source = mc.runner_choice("eval-suite", transport="ollama", root=ROOT)
        self.assertEqual((backend, model, source), ("local", "custom:9b", "user"))

        os.environ["PFY_MODEL_EVAL_SUITE"] = "local:from-env:7b"
        backend, model, source = mc.runner_choice("eval-suite", transport="ollama", root=ROOT)
        self.assertEqual((backend, model, source), ("local", "from-env:7b", "env"))

        backend, model, source = mc.runner_choice(
            "eval-suite", explicit="EVAL_MODEL_WINS:3b", transport="ollama", root=ROOT,
        )
        self.assertEqual((backend, model, source), ("local", "EVAL_MODEL_WINS:3b", "flag"))

        os.environ["PFY_MODEL_EVAL_SUITE"] = "cloud:grok-4.7"
        buf = io.StringIO()
        with redirect_stderr(buf):
            backend, model, source = mc.runner_choice("eval-suite", transport="ollama", root=ROOT)
        self.assertEqual((backend, model, source), ("local", "qwen2.5:14b", "refused-cloud"))
        self.assertIn("eval-suite is Ollama-only", buf.getvalue())
        self.assertIn("cloud:grok-4.7 refused", buf.getvalue())
        self.assertIn("keeping qwen2.5:14b", buf.getvalue())
        self.assertEqual(self.calls, [])

        scored = _load("run_scored_task_runner", "examples/eval-harness/run_scored_task.py")
        os.environ.pop("PFY_MODEL_EVAL_SUITE", None)
        os.environ["EVAL_MODEL"] = "explicit-suite:1b"
        os.environ["PFY_MODEL_EVAL_SUITE"] = "local:should-not-win:1b"
        self.assertEqual(scored.resolve_model(), "explicit-suite:1b")
        os.environ.pop("EVAL_MODEL", None)
        self.assertEqual(scored.resolve_model(), "should-not-win:1b")

    def test_matrix_gate_follows_choice_unless_eval_model_is_set(self) -> None:
        os.environ["PFY_MODEL_MATRIX"] = "local:matrix-model:8b"
        os.environ["EVAL_MODE"] = "matrix"
        scored = _load("run_scored_task_matrix", "examples/eval-harness/run_scored_task.py")
        self.assertEqual(scored.resolve_model(), "matrix-model:8b")
        os.environ["EVAL_MODEL"] = "gate-flag:2b"
        self.assertEqual(scored.resolve_model(), "gate-flag:2b")

        os.environ.pop("EVAL_MODEL", None)
        os.environ["PFY_MODEL_MATRIX"] = "cloud:grok-4.7"
        buf = io.StringIO()
        with redirect_stderr(buf):
            model = scored.resolve_model()
        self.assertEqual(model, "qwen2.5:14b")
        self.assertIn("matrix is Ollama-only", buf.getvalue())
        self.assertEqual(self.calls, [])

    def test_decision_route_jev_env_beats_choice_and_cloud_is_refused(self) -> None:
        jev = _load("pfy_jev_230_runner", "scripts/pfy_jev_230.py")
        self.assertEqual(jev.laya_shadow_model(), "qwen3.6:35b")

        mc.save_task("decision-route", "local", "operator:14b")
        self.assertEqual(jev.laya_shadow_model(), "operator:14b")

        os.environ["PFY_MODEL_DECISION_ROUTE"] = "local:routed:6b"
        self.assertEqual(jev.laya_shadow_model(), "routed:6b")

        os.environ["PFY_JEV_MODEL"] = "english"
        self.assertEqual(jev.laya_shadow_model(), "english")

        os.environ.pop("PFY_JEV_MODEL", None)
        os.environ["PFY_MODEL_DECISION_ROUTE"] = "cloud:grok-4.7"
        buf = io.StringIO()
        with redirect_stderr(buf):
            model = jev.laya_shadow_model()
        self.assertEqual(model, "qwen3.6:35b")
        self.assertIn("decision-route is Ollama-only", buf.getvalue())
        self.assertEqual(self.calls, [])

    def test_build_lane_flag_and_env_beat_choice(self) -> None:
        build = _load("pfy_build_local_runner", "scripts/pfy_build_local.py")
        self.assertEqual(build._pick_build_model(None), "qwen3.6:35b")
        mc.save_task("build-lane", "local", "saved:9b")
        self.assertEqual(build._pick_build_model(None), "saved:9b")
        os.environ["PFY_MODEL_BUILD_LANE"] = "local:from-pfy:1b"
        self.assertEqual(build._pick_build_model(None), "from-pfy:1b")
        os.environ["PFY_LOCAL_BUILD_MODEL"] = "from-runner-env:2b"
        self.assertEqual(build._pick_build_model(None), "from-runner-env:2b")
        self.assertEqual(build._pick_build_model("from-flag:3b"), "from-flag:3b")

        os.environ.pop("PFY_LOCAL_BUILD_MODEL", None)
        os.environ["PFY_MODEL_BUILD_LANE"] = "cloud:grok-4.7"
        buf = io.StringIO()
        with redirect_stderr(buf):
            model = build._pick_build_model(None)
        self.assertEqual(model, "qwen3.6:35b")
        self.assertIn("build-lane is Ollama-only", buf.getvalue())
        self.assertEqual(self.calls, [])

    def test_cli_resolve_refuses_cloud_on_stdout_model_only(self) -> None:
        mc.save_task("matrix", "cloud", "grok-4.7")
        env = os.environ.copy()
        env["PFY_MODEL_NO_PAID"] = "1"
        proc = subprocess.run(
            [
                sys.executable, "-m", "pfylib.model_choice", "resolve", "matrix",
                "--field", "model", "--transport", "ollama",
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "qwen2.5:14b")
        self.assertIn("matrix is Ollama-only", proc.stderr)
        self.assertNotIn("grok-4.7", proc.stdout)


if __name__ == "__main__":
    unittest.main()
