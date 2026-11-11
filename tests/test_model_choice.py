"""Per-task model choice and the cost gate. No network and no paid call.

Fail: a cloud backend or a compare run starts without an explicit choice,
or a refused compare still hits the provider.
Recovery: resolve stays local, the provider mock records zero calls, and
the diff file is written only after an explicit yes under the cap.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib import cli, model_choice as mc  # noqa: E402
from pfylib import toolsets  # noqa: E402
from scripts import catalog_fit_triage as fit  # noqa: E402
from tests._model_choice_isolation import begin as iso_begin, end as iso_end  # noqa: E402

LINE_RE = re.compile(
    r"Compare catalog-fit \(8 cases\) on grok-4\.7: ~[\d,]+ input \+ ~[\d,]+ output tokens "
    r"\((?:approx|litellm|tiktoken o200k_base)\) = \$\d+\.\d{4} \(xAI price \$2\.00/\$6\.00 per 1M, "
    r"docs\.x\.ai/docs/models, fetched 2026-11-11\)\. Run it\? \[y/N\]"
)


def _labels() -> dict[str, str]:
    gate = json.loads((ROOT / "data" / "decision-gates" / "catalog-fit.v0.json").read_text(encoding="utf-8"))
    return {case["slug"]: case["label"] for case in gate["cases"]}


def _cloud_text(prompt: str, labels: dict[str, str]) -> str:
    match = re.search(r"slug must be ([a-z0-9][a-z0-9._-]*)\.", prompt)
    slug = match.group(1) if match else ""
    verdict = "fit" if slug == "magpie" else labels.get(slug, "awareness")
    body = {
        "slug": slug,
        "fit": verdict == "fit",
        "overlap_with": "litellm" if verdict == "redundant" else None,
        "verdict": verdict,
        "reason": "compared",
        "confidence": 0.9,
    }
    return json.dumps(body)


class Isolated(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp, self.iso_saved = iso_begin(prefix="pfy-model-choice-")
        self._home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.tmp / "home")
        (self.tmp / "home").mkdir()
        self.calls: list[dict] = []
        self._transport = mc._TRANSPORT
        self._counters = mc._COUNTERS
        self._isatty = mc.sys_isatty
        mc._TRANSPORT = self._refuse
        mc._COUNTERS = lambda text: ((len(text or "") + 3) // 4, "approx")
        mc.sys_isatty = lambda: False
        self.labels = _labels()
        self.run_dir = self.tmp / "run"
        self.run_dir.mkdir()
        self.out = self.tmp / "compare-catalog-fit.json"

    def tearDown(self) -> None:
        mc._TRANSPORT = self._transport
        mc._COUNTERS = self._counters
        mc.sys_isatty = self._isatty
        if self._home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._home
        iso_end(self.tmp, self.iso_saved)

    def _refuse(self, req: dict) -> dict:
        self.calls.append({"backend": req.get("backend"), "url": req.get("url")})
        raise AssertionError("provider called")

    def _cloud(self, req: dict) -> dict:
        self.calls.append(req)
        prompt = req["body"]["messages"][0]["content"]
        return {
            "choices": [{"message": {"content": _cloud_text(prompt, self.labels)}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

    def _compare(self, **kwargs) -> dict:
        buf = io.StringIO()
        args = dict(
            against="grok-4.7",
            run=str(self.run_dir),
            last=False,
            yes=False,
            isatty=False,
            out=str(self.out),
            root=ROOT,
            today=date(2026, 11, 11),
        )
        args.update(kwargs)
        with redirect_stdout(buf):
            result = mc.run_compare("catalog-fit", **args)
        result["stdout"] = buf.getvalue()
        return result


class ResolveTests(Isolated):
    def test_default_is_local_and_cloud_is_not_implied(self) -> None:
        backend, model, source = mc.resolve("catalog-fit", root=ROOT)
        self.assertEqual((backend, model, source), ("local", "qwen3.6:35b", "default"))
        for task in mc.TASK_ORDER:
            chosen, _name, _source = mc.resolve(task, root=ROOT)
            self.assertEqual(chosen, "local")
        self.assertEqual(fit.default_model(), "qwen3.6:35b")

    def test_env_beats_user_file_and_alias_and_bare_names_stay_local(self) -> None:
        mc.save_task("catalog-fit", "cloud", "grok-4.7")
        os.environ["PFY_CATFIT_MODEL"] = "cloud:grok-4.3"
        os.environ["PFY_MODEL_CATALOG_FIT"] = "local:qwen2.5:14b"
        backend, model, source = mc.resolve("catalog-fit", root=ROOT)
        self.assertEqual((backend, model, source), ("local", "qwen2.5:14b", "env"))

        os.environ.pop("PFY_MODEL_CATALOG_FIT")
        backend, model, source = mc.resolve("catalog-fit", root=ROOT)
        self.assertEqual((backend, model, source), ("cloud", "grok-4.3", "alias"))

        os.environ.pop("PFY_CATFIT_MODEL")
        backend, model, source = mc.resolve("catalog-fit", root=ROOT)
        self.assertEqual((backend, model, source), ("cloud", "grok-4.7", "user"))

        os.environ["PFY_MODEL_CATALOG_FIT"] = "grok-4.7"
        backend, model, source = mc.resolve("catalog-fit", root=ROOT)
        self.assertEqual((backend, model, source), ("local", "grok-4.7", "env"))

    def test_committed_cloud_and_unknown_user_backend_stay_local(self) -> None:
        root = self.tmp / "repo"
        shutil.copytree(ROOT / "config", root / "config")
        path = root / "config" / "model-choice.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["tasks"]["catalog-fit"]["backend"] = "cloud"
        data["tasks"]["catalog-fit"]["model"] = "grok-4.7"
        path.write_text(json.dumps(data), encoding="utf-8")
        backend, model, source = mc.resolve("catalog-fit", root=root)
        self.assertEqual(backend, "local")
        self.assertEqual(source, "default")
        self.assertEqual(model, "grok-4.7")

        mc._atomic_write(
            mc.user_config_path(),
            json.dumps({"tasks": {"catalog-fit": {"backend": "satellite", "model": "grok-4.7"}}}),
        )
        backend, model, source = mc.resolve("catalog-fit", root=ROOT)
        self.assertEqual((backend, model, source), ("local", "qwen3.6:35b", "default"))

    def test_fallback_only_when_detection_lists_other_local_tags(self) -> None:
        backend, model, source = mc.resolve("catalog-fit", root=ROOT, local_tags=["qwen2.5:14b"])
        self.assertEqual((backend, model, source), ("local", "qwen2.5:14b", "fallback"))
        backend, model, source = mc.resolve("catalog-fit", root=ROOT, local_tags=[])
        self.assertEqual((backend, model, source), ("local", "qwen3.6:35b", "default"))
        mc.save_task("catalog-fit", "local", "custom:9b")
        backend, model, source = mc.resolve("catalog-fit", root=ROOT, local_tags=["qwen2.5:14b"])
        self.assertEqual((backend, model, source), ("local", "custom:9b", "user"))

    def test_ollama_not_found_retries_the_local_fallback_once(self) -> None:
        seen: list[str] = []

        def transport(req: dict) -> dict:
            self.calls.append(req)
            seen.append(req["body"]["model"])
            self.assertEqual(req["backend"], "local")
            self.assertNotIn("Authorization", req)
            if req["body"]["model"] == "qwen3.6:35b":
                return {"error": "model not found"}
            return {"response": "{\"ok\":true}", "prompt_eval_count": 4, "eval_count": 2}

        mc._TRANSPORT = transport
        text, usage = mc.call_model("prompt", task="catalog-fit", root=ROOT)
        self.assertEqual(seen, ["qwen3.6:35b", "qwen2.5:14b"])
        self.assertIn("ok", text)
        self.assertEqual(usage["prompt_tokens"], 4)
        self.assertEqual(usage["completion_tokens"], 2)

        seen.clear()
        mc._TRANSPORT = lambda req: seen.append(req["body"]["model"]) or {"error": "404"}
        with self.assertRaises(mc.ModelCallError):
            mc.call_model("prompt", task="catalog-fit", root=ROOT)
        self.assertEqual(seen, ["qwen3.6:35b", "qwen2.5:14b"])

    def test_paid_cloud_socket_is_blocked_when_no_transport_is_injected(self) -> None:
        mc._TRANSPORT = None
        with self.assertRaises(mc.ModelCallError) as caught:
            mc.call_model("prompt", task="catalog-fit", model="cloud:grok-4.7", root=ROOT)
        self.assertIn("paid cloud call blocked", str(caught.exception))
        self.assertEqual(self.calls, [])

    def test_catalog_fit_call_path_uses_the_choice(self) -> None:
        # Local stays on catalog_fit_triage's own Ollama path (load errors and
        # the recorded fallback live there). Cloud goes through model_choice.
        self.assertFalse(fit.cloud_selected())
        mc._TRANSPORT = lambda req: self.calls.append(req) or {
            "choices": [{"message": {"content": "{\"ok\":true}"}}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 2},
        }
        text = fit.default_call_model("prompt", model="cloud:grok-4.7", host="http://127.0.0.1:9")
        self.assertIn("ok", text)
        self.assertEqual(self.calls[0]["backend"], "cloud")
        self.assertIn("/chat/completions", self.calls[0]["url"])

        self.calls.clear()
        os.environ["PFY_MODEL_CATALOG_FIT"] = "cloud:grok-4.7"
        try:
            self.assertTrue(fit.cloud_selected())
            self.assertTrue(fit.operator_set_model())
            fit.default_call_model("prompt", model="grok-4.7", host="http://127.0.0.1:9")
        finally:
            os.environ.pop("PFY_MODEL_CATALOG_FIT", None)
        self.assertEqual(self.calls[0]["backend"], "cloud")


class SetupTests(Isolated):
    def test_noninteractive_setup_persists_outside_the_repo(self) -> None:
        refused = SimpleNamespace(model_choice=["catalog-fit=cloud:grok-4.7"], yes=False, model_choice_prompt=False, root=ROOT)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = mc.setup_from_args(refused)
        self.assertEqual(code, 1)
        self.assertIn("needs_confirmation", buf.getvalue())
        self.assertFalse(mc.user_config_path().exists())
        backend, _model, _source = mc.resolve("catalog-fit", root=ROOT)
        self.assertEqual(backend, "local")

        accepted = SimpleNamespace(model_choice=["catalog-fit=cloud:grok-4.7"], yes=True, model_choice_prompt=False, root=ROOT)
        with redirect_stdout(io.StringIO()):
            code = mc.setup_from_args(accepted)
        self.assertEqual(code, 0)
        path = mc.user_config_path()
        self.assertTrue(path.is_file())
        self.assertFalse(str(path).startswith(str(ROOT)))
        stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["tasks"]["catalog-fit"], {"backend": "cloud", "model": "grok-4.7"})
        committed = json.loads((ROOT / "config" / "model-choice.json").read_text(encoding="utf-8"))
        self.assertEqual(committed["tasks"]["catalog-fit"]["backend"], "local")
        backend, model, source = mc.resolve("catalog-fit", root=ROOT)
        self.assertEqual((backend, model, source), ("cloud", "grok-4.7", "user"))

    def test_catalog_setup_flags_do_not_prompt(self) -> None:
        def boom(*_args, **_kwargs):
            raise AssertionError("prompted")

        old_input = __builtins__["input"] if isinstance(__builtins__, dict) else __builtins__.input
        try:
            if isinstance(__builtins__, dict):
                __builtins__["input"] = boom
            else:
                __builtins__.input = boom
            mc.sys_isatty = lambda: True
            code = mc.setup_from_args(SimpleNamespace(model_choice=None, yes=True, model_choice_prompt=False, root=ROOT))
        finally:
            if isinstance(__builtins__, dict):
                __builtins__["input"] = old_input
            else:
                __builtins__.input = old_input
        self.assertIsNone(code)
        self.assertFalse(mc.user_config_path().exists())

    def test_prompt_enter_keeps_the_row_and_a_value_persists(self) -> None:
        answers = iter(["", "cloud:grok-4.7", "", "", ""])
        old_input = __builtins__["input"] if isinstance(__builtins__, dict) else __builtins__.input
        old_detect = mc.detect_local_models
        try:
            mc.detect_local_models = lambda *args, **kwargs: ["qwen2.5:14b"]
            if isinstance(__builtins__, dict):
                __builtins__["input"] = lambda *_a, **_k: next(answers)
            else:
                __builtins__.input = lambda *_a, **_k: next(answers)
            with redirect_stdout(io.StringIO()) as buf:
                code = mc.setup_from_args(SimpleNamespace(
                    model_choice=None, yes=False, model_choice_prompt=True, root=ROOT,
                ))
        finally:
            mc.detect_local_models = old_detect
            if isinstance(__builtins__, dict):
                __builtins__["input"] = old_input
            else:
                __builtins__.input = old_input
        self.assertEqual(code, 0)
        text = buf.getvalue()
        self.assertIn("local models: qwen2.5:14b", text)
        self.assertIn("catalog-fit [local:qwen2.5:14b] (fallback)", text)
        backend, model, source = mc.resolve("catalog-fit", root=ROOT)
        self.assertEqual((backend, model, source), ("local", "qwen3.6:35b", "default"))
        backend, model, source = mc.resolve("eval-suite", root=ROOT)
        self.assertEqual((backend, model, source), ("cloud", "grok-4.7", "user"))

    def test_cli_set_and_show(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(["--root", str(ROOT), "model-choice", "set", "matrix", "local:qwen2.5:14b"])
        self.assertEqual(code, 0)
        self.assertIn("model-choice matrix local:qwen2.5:14b", buf.getvalue())
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(["--root", str(ROOT), "model-choice", "show"])
        self.assertEqual(code, 0)
        self.assertIn("matrix", buf.getvalue())
        self.assertIn("qwen2.5:14b", buf.getvalue())
        self.assertFalse(str(mc.user_config_path()).startswith(str(ROOT)))


class PriceTests(Isolated):
    def test_quote_uses_the_table_and_refuses_unknown_or_uncovered(self) -> None:
        row = mc.quote("grok-4.7", 1000, 100, root=ROOT)
        self.assertEqual(row["cost_text"], "0.0026")
        self.assertEqual(row["provider"], "xAI")
        long_row = mc.quote("grok-4.7", 200000, 10, root=ROOT)
        self.assertEqual(long_row["band"], "long")
        self.assertEqual(long_row["cost_text"], "0.8001")
        local = mc.quote("qwen3.6:35b", 5000, 500, root=ROOT)
        self.assertEqual(local["cost_text"], "0.0000")
        with self.assertRaises(mc.UnknownModelPrice):
            mc.quote("no-such-model", 10, 10, root=ROOT)
        with self.assertRaises(mc.PriceCoverageError):
            mc.quote("gpt-5.4-mini", 272001, 10, root=ROOT)
        covered = mc.quote("gpt-5.4-mini", 272000, 10, root=ROOT)
        self.assertEqual(covered["provider"], "OpenAI")

    def test_stale_boundary_is_45_days(self) -> None:
        self.assertEqual(mc.price_age_days("2026-11-11", date(2026, 12, 26)), 45)
        self.assertEqual(mc.price_age_days("2026-11-11", date(2026, 12, 27)), 46)
        fresh = mc.estimate_catalog_fit(against="grok-4.7", root=ROOT, run=str(self.run_dir), last=False, today=date(2026, 12, 26))
        stale = mc.estimate_catalog_fit(against="grok-4.7", root=ROOT, run=str(self.run_dir), last=False, today=date(2026, 12, 27))
        self.assertFalse(fresh["stale"])
        self.assertTrue(stale["stale"])


class CompareTests(Isolated):
    def test_refuses_leave_the_provider_uncalled(self) -> None:
        no = self._compare(isatty=True, answer="n")
        self.assertTrue(no["ok"])
        self.assertFalse(no["ran"])
        self.assertEqual(no["blocked"], "declined")
        self.assertRegex(no["stdout"], LINE_RE)
        self.assertIn("not run", no["stdout"])
        self.assertEqual(self.calls, [])

        closed = self._compare()
        self.assertFalse(closed["ok"])
        self.assertTrue(closed["needs_confirm"])
        self.assertEqual(closed["blocked"], "no TTY")
        self.assertRegex(closed["line"], LINE_RE)
        self.assertEqual(self.calls, [])

        missing_cap = self._compare(yes=True)
        self.assertIn("--yes requires --max-usd", missing_cap["stdout"])
        self.assertEqual(self.calls, [])

        over = self._compare(yes=True, max_usd=0.0001)
        self.assertGreater(over["cost_usd"], 0.0001)
        self.assertIn("exceeds", over["stdout"])
        self.assertEqual(self.calls, [])

        stale = self._compare(yes=True, max_usd=50, today=date(2026, 12, 27))
        self.assertIn("older than 45 days", stale["stdout"])
        self.assertIn("--accept-stale-price", stale["line"])
        self.assertEqual(stale["blocked"], "stale price")
        self.assertEqual(self.calls, [])

    def test_yes_calls_once_per_case_and_writes_the_diff(self) -> None:
        mc._TRANSPORT = self._cloud
        preview = self._compare()
        result = self._compare(yes=True, max_usd=float(preview["estimate"]["cost_text"]))
        self.assertTrue(result["ran"], result["stdout"])
        self.assertEqual(len(self.calls), 8)
        for req in self.calls:
            self.assertEqual(req["backend"], "cloud")
            self.assertNotIn("Authorization", req)
            self.assertNotIn("api_key", req["body"])
        payload = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(payload["usage"], {"prompt_tokens": 80, "completion_tokens": 40})
        self.assertEqual(payload["cost_usd"], 0.0004)
        magpie = next(row for row in payload["cases"] if row["slug"] == "magpie")
        self.assertEqual(magpie["local"], "awareness")
        self.assertEqual(magpie["cloud"], "fit")
        self.assertFalse(magpie["agree"])
        self.assertFalse(magpie["match_golden_cloud"])
        self.assertTrue(magpie["match_golden_local"])
        others = [row for row in payload["cases"] if row["slug"] != "magpie"]
        self.assertTrue(all(row["agree"] for row in others))
        state = json.loads(mc.compare_state_path().read_text(encoding="utf-8"))
        self.assertIn("catalog-fit", state["tasks"])
        self.assertFalse(mc._lock_path().exists())

    def test_partial_batch_prices_only_the_stored_cases(self) -> None:
        stored = {
            "slug": "magpie",
            "verdict": "awareness",
            "fit": False,
            "reason": "stored",
            "confidence": 0.9,
        }
        (self.run_dir / "magpie.json").write_text(json.dumps(stored), encoding="utf-8")
        mc._TRANSPORT = self._cloud
        result = self._compare(yes=True, max_usd=5)
        self.assertEqual(len(self.calls), 1)
        payload = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual([row["slug"] for row in payload["cases"]], ["magpie"])
        self.assertEqual(payload["cases"][0]["local_source"], "run")
        self.assertTrue(result["ran"])

    def test_unknown_model_and_busy_lock_do_not_call(self) -> None:
        with self.assertRaises(mc.UnknownModelPrice):
            self._compare(against="no-such-model")
        self.assertEqual(self.calls, [])

        lock = mc._lock_path()
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("busy\n", encoding="utf-8")
        with self.assertRaises(mc.CompareBusy):
            self._compare(yes=True, max_usd=50)
        self.assertEqual(self.calls, [])

        os.utime(lock, (time_old(), time_old()))
        mc._TRANSPORT = self._cloud
        result = self._compare(yes=True, max_usd=50)
        self.assertTrue(result["ran"])
        self.assertEqual(len(self.calls), 8)

    def test_cli_no_tty_and_unknown_model_exit_without_a_call(self) -> None:
        env = os.environ.copy()
        env["PFY_MODEL_NO_PAID"] = "1"
        env["PFY_MODEL_CHOICE_PATH"] = str(self.tmp / "cli-choice.json")
        env["PFY_COMPARE_STATE_PATH"] = str(self.tmp / "cli-state.json")
        base = [sys.executable, "-m", "pfylib", "--root", str(ROOT), "compare", "catalog-fit", "--against"]
        refused = subprocess.run(
            base + ["grok-4.7", "--run", str(self.run_dir)],
            cwd=ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(refused.returncode, 1, refused.stderr)
        self.assertRegex(refused.stdout, LINE_RE)
        self.assertIn("no TTY", refused.stdout)
        unknown = subprocess.run(
            base + ["no-such-model", "--run", str(self.run_dir)],
            cwd=ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(unknown.returncode, 1)
        self.assertIn("UnknownModelPrice:", unknown.stderr)
        self.assertNotIn("Run it?", unknown.stdout)


class ReminderTests(Isolated):
    def _root(self) -> tuple[Path, Path]:
        root = self.tmp / "repo"
        root.mkdir()
        (root / "data").symlink_to(ROOT / "data")
        (root / "config").symlink_to(ROOT / "config")
        batch = root / "eval" / "catalog-fit"
        batch.mkdir(parents=True)
        return root, batch

    def test_offer_prints_and_never_calls(self) -> None:
        root, batch = self._root()
        path = batch / "magpie.json"
        path.write_text('{"slug":"magpie","verdict":"awareness"}\n', encoding="utf-8")
        line = mc.reminder_line(root=root, now=datetime(2026, 11, 11, tzinfo=timezone.utc))
        self.assertIsNotNone(line)
        assert line is not None
        self.assertRegex(
            line,
            r"It will cost ~\$\d+\.\d{2} to check your last local catalog-fit run with "
            r"grok-4\.7, gpt-6\.1-sol: \./pfy compare catalog-fit --against grok-4\.7",
        )
        self.assertEqual(self.calls, [])
        self.assertFalse(mc._lock_path().exists())

        os.environ["PFY_ROOT"] = str(root)
        buf = io.StringIO()
        with redirect_stdout(buf):
            mc.print_compare_reminder()
        self.assertIn("./pfy compare catalog-fit --against grok-4.7", buf.getvalue())
        self.assertEqual(self.calls, [])

    def test_recent_compare_or_older_local_run_stays_quiet(self) -> None:
        root, batch = self._root()
        path = batch / "magpie.json"
        path.write_text('{"slug":"magpie","verdict":"awareness"}\n', encoding="utf-8")
        mc._atomic_write(
            mc.compare_state_path(),
            json.dumps({"tasks": {"catalog-fit": {"at": "2026-11-10T00:00:00Z", "against": "grok-4.7"}}}),
        )
        self.assertIsNone(mc.reminder_line(root=root, now=datetime(2026, 11, 11, tzinfo=timezone.utc)))

        old = "2026-10-01T00:00:00Z"
        mc._atomic_write(
            mc.compare_state_path(),
            json.dumps({"tasks": {"catalog-fit": {"at": old, "against": "grok-4.7"}}}),
        )
        older = datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp()
        os.utime(path, (older, older))
        compared = datetime.strptime(old, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self.assertLess(path.stat().st_mtime, compared.timestamp())
        self.assertIsNone(mc.reminder_line(root=root, now=datetime(2026, 11, 11, tzinfo=timezone.utc)))

        os.utime(path, None)
        line = mc.reminder_line(root=root, now=datetime(2026, 11, 11, tzinfo=timezone.utc))
        self.assertIsNotNone(line)
        self.assertEqual(self.calls, [])


class ToolsetTests(Isolated):
    def test_jev_plan_exports_the_decision_route_choice(self) -> None:
        planned = toolsets.plan("jev", "grok", "local", root_dir=ROOT, state=self.tmp / "state")
        self.assertEqual(planned["env"]["PFY_MODEL_DECISION_ROUTE"], "local:qwen3.6:35b")
        self.assertIn("PFY_DECISION_PATH", planned["env"])


class DecisionCompareTests(Isolated):
    def test_parser_accepts_only_a_criteria_key(self) -> None:
        case = {"keys": ["push", "hold", "escalate"]}
        self.assertEqual(mc.parse_decision_choice('{"choice":"hold","confidence":0.4,"why":"red"}', case), "hold")
        self.assertEqual(
            mc.parse_decision_choice('```json\n{"answers":[{"choice":"push"}]}\n```', case),
            "push",
        )
        self.assertIsNone(mc.parse_decision_choice('{"choice":"nope"}', case))
        self.assertIsNone(mc.parse_decision_choice("not json", case))

    def test_eval_lane_is_not_replayable(self) -> None:
        with self.assertRaises(ValueError) as caught:
            mc.run_compare("eval-lane", against="grok-4.7", root=ROOT, yes=True, max_usd=1)
        self.assertIn("not replayable", str(caught.exception))
        self.assertEqual(self.calls, [])
        with self.assertRaises(ValueError) as other:
            mc.run_compare("build-lane", against="grok-4.7", root=ROOT)
        self.assertIn("catalog-fit and decision-route", str(other.exception))

    def test_gates_match_catalog_fit_and_yes_diffs_against_labels(self) -> None:
        closed = self._decision()
        self.assertEqual(closed["blocked"], "no TTY")
        self.assertIn("decision-route (48 cases)", closed["line"])
        self.assertIn("(approx)", closed["line"])
        self.assertIn("docs.x.ai/docs/models", closed["line"])
        self.assertIn("fetched 2026-11-11", closed["line"])
        self.assertEqual(self.calls, [])

        with self.assertRaises(mc.UnknownModelPrice):
            self._decision(against="no-such-model")
        self.assertEqual(self.calls, [])

        stale = self._decision(yes=True, max_usd=50, today=date(2026, 12, 27))
        self.assertEqual(stale["blocked"], "stale price")
        self.assertIn("--accept-stale-price", stale["line"])
        self.assertEqual(self.calls, [])

        missing = self._decision(yes=True)
        self.assertIn("--yes requires --max-usd", missing["stdout"])
        self.assertEqual(self.calls, [])

        lock = mc._lock_path()
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("busy\n", encoding="utf-8")
        with self.assertRaises(mc.CompareBusy):
            self._decision(yes=True, max_usd=50)
        self.assertEqual(self.calls, [])
        lock.unlink()

        # run/last do not filter the labeled set.
        est = mc.estimate_task(
            "decision-route",
            against="grok-4.7",
            root=ROOT,
            run=str(self.tmp / "no-such-run"),
            last=False,
            today=date(2026, 11, 11),
        )
        self.assertEqual(est["cases"], 48)

        mc._TRANSPORT = self._decision_cloud
        result = self._decision(yes=True, max_usd=float(est["cost_text"]))
        self.assertTrue(result["ran"], result.get("stdout"))
        self.assertEqual(len(self.calls), 48)
        for req in self.calls:
            self.assertEqual(req["backend"], "cloud")
            prompt = req["body"]["messages"][0]["content"]
            self.assertIn("Read cases.json", prompt)
            body = json.loads(prompt.split("CASE_JSON:\n", 1)[1])
            self.assertNotIn("label", body)
            self.assertNotIn("note", body)
        payload = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(payload["usage"], {"prompt_tokens": 480, "completion_tokens": 240})
        self.assertEqual(payload["cost_usd"], 0.0024)
        labels = self._labels()
        from scripts import pfy_jev_230 as jev
        raw = json.loads((ROOT / "data" / "decision-gates" / "laya-trial.cases.v0.json").read_text(encoding="utf-8"))
        sample = next(row for row in raw["cases"] if row["id"] == "ph-03-ci-red")
        local = jev.decide_choice(sample["state"], sample["criteria"], instructions=sample["instructions"])
        got = next(row for row in payload["cases"] if row["id"] == "ph-03-ci-red")
        self.assertEqual(got["local"], local["choice"])
        self.assertEqual(got["cloud"], sample["label"])
        self.assertEqual(got["golden"], sample["label"])
        self.assertTrue(all(row["match_golden_cloud"] for row in payload["cases"]))
        self.assertEqual({row["id"] for row in payload["cases"]}, set(labels))
        self.assertFalse(mc._lock_path().exists())
        self.assertIsNone(mc.reminder_line("decision-route", root=ROOT))

    def _labels(self) -> dict[str, str]:
        data = json.loads((ROOT / "data" / "decision-gates" / "laya-trial.cases.v0.json").read_text(encoding="utf-8"))
        return {row["id"]: row["label"] for row in data["cases"]}

    def _decision_cloud(self, req: dict) -> dict:
        self.calls.append(req)
        prompt = req["body"]["messages"][0]["content"]
        match = re.search(r'"id": "([^"]+)"', prompt)
        label = self._labels()[match.group(1)] if match else "hold"
        return {
            "choices": [{"message": {"content": json.dumps({"choice": label, "confidence": 0.9, "why": "replay"})}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

    def _decision(self, **kwargs) -> dict:
        buf = io.StringIO()
        args = dict(
            against="grok-4.7",
            run=str(self.run_dir),
            last=False,
            yes=False,
            isatty=False,
            out=str(self.tmp / "compare-decision-route.json"),
            root=ROOT,
            today=date(2026, 11, 11),
        )
        args.update(kwargs)
        self.out = Path(args["out"])
        with redirect_stdout(buf):
            result = mc.run_compare("decision-route", **args)
        result["stdout"] = buf.getvalue()
        return result


class TokenTests(Isolated):
    def test_three_counters_and_empty_text(self) -> None:
        self.assertEqual(mc.count_tokens(""), (0, "exact"))
        for label in ("litellm", "tiktoken o200k_base", "approx"):
            mc._COUNTERS = lambda text, label=label: (4, label)
            est = mc.estimate_catalog_fit(
                against="grok-4.7",
                root=ROOT,
                run=str(self.run_dir),
                last=False,
                today=date(2026, 11, 11),
            )
            self.assertEqual(est["token_method"], label)
            self.assertIn("(%s)" % label, est["line"])
            self.assertEqual(self.calls, [])

        mc._COUNTERS = lambda text: (1, "approx") if "slug must be" in text else (1, "litellm")
        mixed = mc.estimate_catalog_fit(
            against="grok-4.7", root=ROOT, run=str(self.run_dir), last=False, today=date(2026, 11, 11),
        )
        self.assertEqual(mixed["token_method"], "approx")

    def test_order_is_litellm_then_tiktoken_then_chars(self) -> None:
        mc._COUNTERS = None
        seen: list[str] = []

        def no_lit(text: str):
            seen.append("litellm")
            raise ImportError("no litellm")

        def tik(text: str):
            seen.append("tiktoken")
            return 9, "tiktoken o200k_base"

        def yes_lit(text: str):
            seen.append("litellm")
            return 4, "litellm"

        def no_tik(text: str):
            seen.append("tiktoken")
            raise ImportError("no tiktoken")

        old_l, old_t = mc._count_litellm, mc._count_tiktoken
        try:
            mc._count_litellm, mc._count_tiktoken = no_lit, tik
            self.assertEqual(mc.count_tokens("hello"), (9, "tiktoken o200k_base"))
            self.assertEqual(seen, ["litellm", "tiktoken"])
            seen.clear()
            mc._count_litellm = yes_lit
            self.assertEqual(mc.count_tokens("hello"), (4, "litellm"))
            self.assertEqual(seen, ["litellm"])
            seen.clear()
            mc._count_litellm, mc._count_tiktoken = no_lit, no_tik
            self.assertEqual(mc.count_tokens("abcd"), (1, "approx"))
            self.assertEqual(seen, ["litellm", "tiktoken"])
        finally:
            mc._count_litellm, mc._count_tiktoken = old_l, old_t

    def test_failed_import_uses_the_venv_and_sets_the_cache_dir(self) -> None:
        venv = self.tmp / "tokvenv"
        site = venv / "lib" / "python3.12" / "site-packages"
        site.mkdir(parents=True)
        (site / "pfy_fake_tok.py").write_text("MARKER = 1\n", encoding="utf-8")
        os.environ["PFY_VENV"] = str(venv)
        os.environ.pop("TIKTOKEN_CACHE_DIR", None)
        sys.modules.pop("pfy_fake_tok", None)
        before = list(sys.path)
        try:
            mod = mc._import_mod("pfy_fake_tok")
            self.assertEqual(mod.MARKER, 1)
            self.assertIn(str(site), sys.path)
            self.assertEqual(os.environ["TIKTOKEN_CACHE_DIR"], str(venv / "tiktoken-cache"))
            sys.path[:] = before
            sys.modules.pop("pfy_fake_tok", None)
            os.environ["TIKTOKEN_CACHE_DIR"] = str(self.tmp / "preset-cache")
            again = mc._import_mod("pfy_fake_tok")
            self.assertEqual(again.MARKER, 1)
            self.assertEqual(os.environ["TIKTOKEN_CACHE_DIR"], str(self.tmp / "preset-cache"))
        finally:
            sys.path[:] = before
            sys.modules.pop("pfy_fake_tok", None)
            os.environ.pop("TIKTOKEN_CACHE_DIR", None)
            os.environ.pop("PFY_VENV", None)


def time_old() -> float:
    import time
    return time.time() - 7200


if __name__ == "__main__":
    unittest.main()


class RealBatchReplayTests(unittest.TestCase):
    """Fail: a real loop batch (non-golden slugs) gave 'catalog-fit has no cases'."""

    def test_non_golden_batch_slugs_replay_from_their_cards(self) -> None:
        gate = fit.load_gate(ROOT)
        golden = {c["slug"] for c in gate["cases"] if isinstance(c, dict)}
        slug = next(
            p.stem for p in sorted((ROOT / "data" / "stages").glob("*.json"))
            if not p.name.startswith("_") and p.stem not in golden
        )
        with tempfile.TemporaryDirectory() as raw:
            batch = Path(raw)
            (batch / f"{slug}.json").write_text(json.dumps({
                "slug": slug, "verdict": "skip_install", "confidence": 0.9,
                "fit": False, "overlap_with": None, "reason": "x",
            }), encoding="utf-8")
            (batch / "magpie.json").write_text(json.dumps({
                "slug": "magpie", "verdict": "awareness", "confidence": 0.9,
                "fit": False, "overlap_with": None, "reason": "x",
            }), encoding="utf-8")
            cases = mc.catalog_fit_cases(ROOT, str(batch), False)
        by = {c["slug"]: c for c in cases}
        self.assertEqual(set(by), {slug, "magpie"})
        self.assertIsNone(by[slug]["golden"])
        self.assertEqual(by[slug]["local"], "skip_install")
        self.assertEqual(by[slug]["origin"], "run")
        self.assertIn(slug, by[slug]["prompt"])
        self.assertEqual(by["magpie"]["golden"], "awareness")
