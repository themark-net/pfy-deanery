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
from contextlib import redirect_stderr, redirect_stdout
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
        self.assertEqual((backend, model, source), ("local", "qwen3.6:35b", "default"))

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
        self.assertEqual((backend, model, source), ("local", "qwen3.6:35b", "refused-cloud"))
        self.assertIn("eval-suite is Ollama-only", buf.getvalue())
        self.assertIn("cloud:grok-4.7 refused", buf.getvalue())
        self.assertIn("keeping qwen3.6:35b", buf.getvalue())
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
        self.assertEqual(model, "qwen3.6:35b")
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
        self.assertEqual(build._pick_build_model(None), ("qwen3.6:35b", "default"))
        mc.save_task("build-lane", "local", "saved:9b")
        self.assertEqual(build._pick_build_model(None), ("saved:9b", "user"))
        os.environ["PFY_MODEL_BUILD_LANE"] = "local:from-pfy:1b"
        self.assertEqual(build._pick_build_model(None), ("from-pfy:1b", "env"))
        os.environ["PFY_LOCAL_BUILD_MODEL"] = "from-runner-env:2b"
        self.assertEqual(build._pick_build_model(None), ("from-runner-env:2b", "env"))
        self.assertEqual(build._pick_build_model("from-flag:3b"), ("from-flag:3b", "flag"))

        os.environ.pop("PFY_LOCAL_BUILD_MODEL", None)
        os.environ["PFY_MODEL_BUILD_LANE"] = "cloud:grok-4.7"
        buf = io.StringIO()
        with redirect_stderr(buf):
            model = build._pick_build_model(None)
        self.assertEqual(model, ("qwen3.6:35b", "refused-cloud"))
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
        self.assertEqual(proc.stdout.strip(), "qwen3.6:35b")
        self.assertIn("matrix is Ollama-only", proc.stderr)
        self.assertNotIn("grok-4.7", proc.stdout)

    def test_eval_suite_and_matrix_default_to_qwen36_and_fall_back_from_tags(self) -> None:
        """Fail: the committed pin is qwen2.5:14b, so a tag list that omits
        qwen3.6:35b never switches and an unrelated tag list still returns 14b.
        Recover: the default is qwen3.6:35b. Tags that list only qwen2.5:14b
        select that fallback. Tags that list neither keep qwen3.6:35b. An env
        model and EVAL_MODEL do not switch. No provider call.
        """
        for task in ("eval-suite", "matrix"):
            backend, model, source = mc.resolve(task, root=ROOT, local_tags=["other:1b"])
            self.assertEqual((backend, model, source), ("local", "qwen3.6:35b", "default"))
            backend, model, source = mc.resolve(task, root=ROOT, local_tags=["qwen2.5:14b"])
            self.assertEqual((backend, model, source), ("local", "qwen2.5:14b", "fallback"))
            backend, model, source = mc.resolve(
                task, root=ROOT, local_tags=["qwen3.6:35b", "qwen2.5:14b"],
            )
            self.assertEqual((backend, model, source), ("local", "qwen3.6:35b", "default"))
            backend, model, source = mc.resolve(task, root=ROOT, local_tags=[])
            self.assertEqual((backend, model, source), ("local", "qwen3.6:35b", "default"))

        os.environ["PFY_MODEL_EVAL_SUITE"] = "local:from-env:7b"
        backend, model, source = mc.resolve(
            "eval-suite", root=ROOT, local_tags=["qwen2.5:14b"],
        )
        self.assertEqual((backend, model, source), ("local", "from-env:7b", "env"))
        os.environ.pop("PFY_MODEL_EVAL_SUITE", None)
        os.environ["EVAL_MODEL"] = "alias-wins:3b"
        backend, model, source = mc.resolve(
            "eval-suite", root=ROOT, local_tags=["qwen2.5:14b"],
        )
        self.assertEqual((backend, model, source), ("local", "alias-wins:3b", "alias"))
        self.assertEqual(self.calls, [])

        scored = _load("run_scored_task_fallback", "examples/eval-harness/run_scored_task.py")
        os.environ.pop("EVAL_MODEL", None)
        os.environ.pop("PFY_MODEL_EVAL_SUITE", None)
        os.environ.pop("LITELLM_SMOKE_MODEL", None)
        self.assertEqual(scored.resolve_model(local_tags=["other:1b"]), "qwen3.6:35b")
        self.assertEqual(scored.resolve_model(local_tags=["qwen2.5:14b"]), "qwen2.5:14b")
        os.environ["EVAL_MODE"] = "matrix"
        self.assertEqual(scored.resolve_model(local_tags=["qwen2.5:14b"]), "qwen2.5:14b")
        os.environ["PFY_MODEL_MATRIX"] = "local:matrix-stays:8b"
        self.assertEqual(scored.resolve_model(local_tags=["qwen2.5:14b"]), "matrix-stays:8b")

    def test_missing_default_tag_retries_once_for_suite_and_matrix(self) -> None:
        """Fail: a missing qwen3.6:35b aborts eval-suite and matrix on that tag.
        Recover: one fake-backend retry on qwen2.5:14b. An explicit other tag
        does not switch.
        """
        for task in ("eval-suite", "matrix"):
            seen: list[str] = []

            def transport(req: dict, seen: list[str] = seen) -> dict:
                seen.append(req["body"]["model"])
                self.assertEqual(req["backend"], "local")
                if req["body"]["model"] == "qwen3.6:35b":
                    return {"error": "model not found"}
                return {"response": "{\"ok\":true}", "prompt_eval_count": 3, "eval_count": 1}

            mc._TRANSPORT = transport
            text, usage = mc.call_model("prompt", task=task, root=ROOT)
            self.assertEqual(seen, ["qwen3.6:35b", "qwen2.5:14b"])
            self.assertIn("ok", text)
            self.assertEqual(usage["prompt_tokens"], 3)

        seen = []

        def explicit_transport(req: dict) -> dict:
            seen.append(req["body"]["model"])
            return {"error": "model not found"}

        mc._TRANSPORT = explicit_transport
        with self.assertRaises(mc.ModelCallError):
            mc.call_model("prompt", task="eval-suite", model="local:custom:9b", root=ROOT)
        self.assertEqual(seen, ["custom:9b"])

    def test_choice_prompt_shows_suite_and_matrix_fallback(self) -> None:
        """Fail: the prompt shows eval-suite and matrix as the 14b pin.
        Recover: detected tags that omit qwen3.6:35b show the fallback row.
        Enter keeps the committed default. An env row is shown and not switched.
        """
        answers = iter(["", "", "", "", ""])
        old_input = __builtins__["input"] if isinstance(__builtins__, dict) else __builtins__.input
        old_detect = mc.detect_local_models
        try:
            mc.detect_local_models = lambda *args, **kwargs: ["qwen2.5:14b"]
            if isinstance(__builtins__, dict):
                __builtins__["input"] = lambda *_a, **_k: next(answers)
            else:
                __builtins__.input = lambda *_a, **_k: next(answers)
            with redirect_stdout(io.StringIO()) as buf:
                mc._prompt(root=ROOT)
        finally:
            mc.detect_local_models = old_detect
            if isinstance(__builtins__, dict):
                __builtins__["input"] = old_input
            else:
                __builtins__.input = old_input
        text = buf.getvalue()
        self.assertIn("eval-suite [local:qwen2.5:14b] (fallback)", text)
        self.assertIn("matrix [local:qwen2.5:14b] (fallback)", text)
        backend, model, source = mc.resolve("eval-suite", root=ROOT)
        self.assertEqual((backend, model, source), ("local", "qwen3.6:35b", "default"))

        os.environ["PFY_MODEL_MATRIX"] = "local:shown-env:4b"
        answers = iter(["", "", "", "", ""])
        try:
            mc.detect_local_models = lambda *args, **kwargs: ["qwen2.5:14b"]
            if isinstance(__builtins__, dict):
                __builtins__["input"] = lambda *_a, **_k: next(answers)
            else:
                __builtins__.input = lambda *_a, **_k: next(answers)
            with redirect_stdout(io.StringIO()) as buf:
                mc._prompt(root=ROOT)
        finally:
            mc.detect_local_models = old_detect
            if isinstance(__builtins__, dict):
                __builtins__["input"] = old_input
            else:
                __builtins__.input = old_input
            os.environ.pop("PFY_MODEL_MATRIX", None)
        self.assertIn("matrix [local:shown-env:4b] (env)", buf.getvalue())
        self.assertNotIn("matrix [local:qwen2.5:14b] (fallback)", buf.getvalue())

    def test_fake_tags_select_the_fallback_without_ollama(self) -> None:
        """Fail: the resolve CLI has no tag list, so it cannot print the fallback.
        Recover: --tags qwen2.5:14b prints that model. OLLAMA_HOST is a closed port.
        """
        env = os.environ.copy()
        env["PFY_MODEL_NO_PAID"] = "1"
        env["OLLAMA_HOST"] = "http://127.0.0.1:9"
        proc = subprocess.run(
            [
                sys.executable, "-m", "pfylib.model_choice", "resolve", "matrix",
                "--field", "model", "--transport", "ollama", "--tags", "qwen2.5:14b",
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "qwen2.5:14b")
        self.assertIn("fallback", proc.stderr)
        self.assertNotIn("qwen3.6:35b", proc.stdout)

    def test_make_and_cage_resolve_with_probe_tags(self) -> None:
        """Fail: make and the cage script pin qwen2.5:14b and do not ask which
        tag is listed. Recover: both call resolve --probe-tags (GET /api/tags,
        no pull). The qwen2.5:14b literal is only the empty-output fallback.
        """
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        cage = (ROOT / "examples/eval-harness/run-in-cage.sh").read_text(encoding="utf-8")
        self.assertIn(
            "resolve eval-suite --field model --transport ollama --probe-tags",
            makefile,
        )
        self.assertIn(
            "resolve matrix --field model --transport ollama --probe-tags",
            makefile,
        )
        self.assertIn("--probe-tags", cage)


if __name__ == "__main__":
    unittest.main()
