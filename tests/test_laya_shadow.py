"""Laya shadow second-opinion: flag off is identical; flag on fail-closed. Cite #230."""
from __future__ import annotations

import importlib.util
import io
import os
import unittest
from contextlib import redirect_stderr
from unittest import mock

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
from tests._model_choice_isolation import begin, end  # noqa: E402


def _load():
    spec = importlib.util.spec_from_file_location("pfy_jev_230", ROOT / "scripts" / "pfy_jev_230.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


jev = _load()

ENV_KEYS = (
    "PFY_JEV_LAYA_SHADOW",
    "PFY_JEV_TYPESAFE_URL",
    "PFY_JEV_MODEL",
    "PFY_JEV_TYPESAFE_TIMEOUT",
    "PFY_JEV_OFFLINE",
    "PFY_JEV_CONF_GATE",
    "TYPESAFE_API_KEY",
    "TYPESAFE_KEY",
    "JEV_API_KEY",
)

STATE = "push green tip now"
CRITERIA = {"push": "push green tip now", "hold": "zzzz unrelated hold"}
LIVE = {
    "wizard_lane": "local",
    "wizard_harness": "opencode",
    "wizard_toolsets": "bare",
    "models": ["qwen3-coder:30b", "deepseek-coder:6.7b"],
}


def _ready_choice():
    rec = jev.decide_choice(STATE, CRITERIA)
    if not rec.get("auto_act"):
        raise unittest.SkipTest("logit margin not peaked enough in this environment")
    rec = dict(rec)
    rec["engine"] = "cua-s1-forms"
    return rec


class LayaShadowFlagTests(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in ENV_KEYS}
        for k in ENV_KEYS:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_flag_off_decide_and_route_have_no_shadow_key_and_no_network(self):
        # Fail: flag off still POSTs to Laya or stamps a shadow key on the rec.
        # Recover: maybe_laya_shadow is a no-op unless PFY_JEV_LAYA_SHADOW is on.
        os.environ.pop("PFY_JEV_LAYA_SHADOW", None)
        with mock.patch.object(jev, "typesafe_evaluate") as ev:
            choice = jev.decide_choice(STATE, CRITERIA)
            route = jev.route_model_tool(LIVE, path="cua-s1-forms")
            plan = jev.cua_s1_forms_plan(ROOT=ROOT)
            ev.assert_not_called()
        self.assertNotIn("shadow", choice)
        self.assertNotIn("shadow", route)
        self.assertNotIn("shadow", plan)
        for ans in plan.get("answers") or []:
            self.assertNotIn("shadow", ans)
        self.assertEqual(jev.PRIMARY_LOCAL, "cua-s1-forms")

    def test_flag_on_does_not_touch_decide_choice(self):
        # Fail: decide_choice itself starts calling Laya → unit selftests need a server.
        # Recover: keep decide_choice local; apply shadow at the CUA lane boundary.
        os.environ["PFY_JEV_LAYA_SHADOW"] = "1"
        os.environ["PFY_JEV_TYPESAFE_URL"] = "http://127.0.0.1:8765/v1/systemone"
        with mock.patch.object(jev, "typesafe_evaluate") as ev:
            rec = jev.decide_choice(STATE, CRITERIA)
            ev.assert_not_called()
        self.assertNotIn("shadow", rec)

    def test_flag_on_disagree_escalates_with_shadow_fields(self):
        # Fail: CUA ready + Laya other choice still auto-acts.
        # Recover: disagree → escalate (exit 3), attach shadow.action=escalate.
        os.environ["PFY_JEV_LAYA_SHADOW"] = "1"
        os.environ["PFY_JEV_TYPESAFE_URL"] = "http://127.0.0.1:8765/v1/systemone"
        ready = _ready_choice()
        cua_choice = ready.get("choice")

        def fake_eval(state, questions, ROOT=None):
            qid = next(iter(questions))
            return {
                "ok": True,
                "answers": {qid: {"choice": "not-" + str(cua_choice), "confidence": 0.4}},
                "model": "english",
            }

        with mock.patch.object(jev, "typesafe_evaluate", side_effect=fake_eval) as ev:
            rec = jev.maybe_laya_shadow(ready, STATE, CRITERIA, instructions="test", qid="case")
            ev.assert_called_once()
        self.assertFalse(rec.get("ok"))
        self.assertFalse(rec.get("auto_act"))
        self.assertFalse(rec.get("usable"))
        self.assertEqual(jev.classify_decision(rec), "escalate")
        self.assertEqual(jev.decision_exit_code(rec), jev.EXIT_ESCALATE)
        shadow = rec.get("shadow") or {}
        self.assertTrue(shadow.get("enabled"))
        self.assertEqual(shadow.get("engine"), "laya")
        self.assertEqual(shadow.get("cua_choice"), cua_choice)
        self.assertEqual(shadow.get("laya_choice"), "not-" + str(cua_choice))
        self.assertFalse(shadow.get("agree"))
        self.assertEqual(shadow.get("action"), "escalate")
        self.assertIn("latency_s", shadow)
        self.assertEqual(rec.get("error"), jev.CHIP_CONF_LOW)
        self.assertEqual(rec.get("chip_shadow"), jev.CHIP_SHADOW_DISAGREE)

    def test_flag_on_agree_stays_ready(self):
        # Fail: agreement still flips auto_act off.
        # Recover: leave CUA ready; log shadow.action=pass.
        os.environ["PFY_JEV_LAYA_SHADOW"] = "1"
        os.environ["PFY_JEV_TYPESAFE_URL"] = "http://127.0.0.1:8765/v1/systemone"
        ready = _ready_choice()
        cua_choice = ready.get("choice")

        def fake_eval(state, questions, ROOT=None):
            qid = next(iter(questions))
            return {
                "ok": True,
                "answers": {qid: {"choice": cua_choice, "confidence": 0.2}},
                "model": "english",
            }

        with mock.patch.object(jev, "typesafe_evaluate", side_effect=fake_eval):
            rec = jev.maybe_laya_shadow(ready, STATE, CRITERIA, qid="case")
        self.assertTrue(rec.get("ok"))
        self.assertTrue(rec.get("auto_act"))
        self.assertTrue(rec.get("usable"))
        self.assertEqual(jev.classify_decision(rec), "ready")
        self.assertEqual(jev.decision_exit_code(rec), jev.EXIT_READY)
        shadow = rec.get("shadow") or {}
        self.assertTrue(shadow.get("agree"))
        self.assertEqual(shadow.get("action"), "pass")
        self.assertEqual(shadow.get("laya_choice"), cua_choice)

    def test_flag_on_laya_error_fail_closed(self):
        # Fail: unreachable Laya still auto-acts on CUA.
        # Recover: escalate, record shadow.error, no silent auto-act.
        os.environ["PFY_JEV_LAYA_SHADOW"] = "1"
        os.environ["PFY_JEV_TYPESAFE_URL"] = "http://127.0.0.1:8765/v1/systemone"
        ready = _ready_choice()
        with mock.patch.object(
            jev,
            "typesafe_evaluate",
            return_value=jev.fail("decision", "TypeSafe network: timed out", jev.NEXT_LOW, engine="typesafe"),
        ):
            rec = jev.maybe_laya_shadow(ready, STATE, CRITERIA, qid="case")
        self.assertFalse(rec.get("auto_act"))
        self.assertEqual(jev.classify_decision(rec), "escalate")
        self.assertEqual(jev.decision_exit_code(rec), jev.EXIT_ESCALATE)
        shadow = rec.get("shadow") or {}
        self.assertEqual(shadow.get("action"), "escalate")
        self.assertFalse(shadow.get("agree"))
        self.assertIn("error", shadow)
        self.assertIn("timed out", str(shadow.get("error")))

    def test_flag_on_cloud_url_refuses_network(self):
        # Fail: shadow flag ON with default TypeSafe URL spends cloud.
        # Recover: fail closed locally; typesafe_evaluate never called.
        os.environ["PFY_JEV_LAYA_SHADOW"] = "1"
        os.environ.pop("PFY_JEV_TYPESAFE_URL", None)
        ready = _ready_choice()
        with mock.patch.object(jev, "typesafe_evaluate") as ev:
            rec = jev.maybe_laya_shadow(ready, STATE, CRITERIA, qid="case")
            ev.assert_not_called()
        self.assertFalse(rec.get("auto_act"))
        self.assertEqual(jev.classify_decision(rec), "escalate")
        self.assertIn("cloud TypeSafe", str((rec.get("shadow") or {}).get("error")))

    def test_route_wires_shadow_when_flag_on(self):
        # Fail: helper exists but route_model_tool never applies it.
        # Recover: CUA lane boundary calls maybe_laya_shadow after decide_choice.
        os.environ["PFY_JEV_LAYA_SHADOW"] = "1"
        os.environ["PFY_JEV_TYPESAFE_URL"] = "http://127.0.0.1:8765/v1/systemone"
        seen = []

        def passthrough(rec, state, criteria, *, instructions="", qid="shadow"):
            seen.append(qid)
            rec = dict(rec)
            rec["shadow"] = {
                "enabled": True,
                "engine": "laya",
                "action": "pass",
                "agree": True,
                "cua_choice": rec.get("choice"),
                "laya_choice": rec.get("choice"),
            }
            return rec

        with mock.patch.object(jev, "maybe_laya_shadow", side_effect=passthrough):
            rec = jev.route_model_tool(LIVE, path="cua-s1-forms")
        self.assertEqual(seen, ["route"])
        self.assertIn("shadow", rec)

    def test_flag_off_maybe_laya_shadow_is_identity(self):
        ready = _ready_choice()
        with mock.patch.object(jev, "typesafe_evaluate") as ev:
            out = jev.maybe_laya_shadow(ready, STATE, CRITERIA)
            ev.assert_not_called()
        self.assertIs(out, ready)
        self.assertNotIn("shadow", out)


class LayaShadowFallbackTests(unittest.TestCase):
    """Fail: a missing default laya tag aborts, or typesafe_model is retargeted.
    Recover: one fake POST retry on qwen2.5:14b. PFY_JEV_MODEL and a saved
    other tag stay put. typesafe_model stays jev-1.13.0.
    """

    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in ENV_KEYS}
        for k in ENV_KEYS:
            os.environ.pop(k, None)
        self.tmp, self.iso = begin(prefix="pfy-laya-fb-")

    def tearDown(self):
        end(self.tmp, self.iso)
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_fake_tags_select_the_committed_fallback(self):
        self.assertEqual(
            jev.laya_shadow_model(local_tags=["qwen2.5:14b"]),
            "qwen2.5:14b",
        )
        self.assertEqual(
            jev.laya_shadow_model(local_tags=["other:1b"]),
            "qwen3.6:35b",
        )
        self.assertEqual(jev.laya_shadow_model(local_tags=[]), "qwen3.6:35b")
        os.environ["PFY_JEV_MODEL"] = "english"
        self.assertEqual(
            jev.laya_shadow_model(local_tags=["qwen2.5:14b"]),
            "english",
        )

    def test_typesafe_model_stays_off_model_choice(self):
        os.environ.pop("PFY_JEV_MODEL", None)
        self.assertEqual(jev.laya_shadow_model(), "qwen3.6:35b")
        self.assertEqual(jev.typesafe_model(), "jev-1.13.0")

    def test_load_error_retries_the_fallback_once_unless_the_model_is_explicit(self):
        os.environ["PFY_JEV_LAYA_SHADOW"] = "1"
        os.environ["PFY_JEV_TYPESAFE_URL"] = "http://127.0.0.1:8765/v1/systemone"
        ready = _ready_choice()
        cua_choice = ready.get("choice")
        seen: list[str] = []

        def fake_eval(state, questions, ROOT=None):
            model = jev.typesafe_model()
            seen.append(model)
            if model == "qwen3.6:35b":
                return jev.fail(
                    "decision",
                    "TypeSafe HTTP 404",
                    jev.NEXT_KEY,
                    engine="typesafe",
                    model=model,
                )
            if model != "qwen2.5:14b":
                raise AssertionError(model)
            qid = next(iter(questions))
            return {
                "ok": True,
                "answers": {qid: {"choice": cua_choice, "confidence": 0.2}},
                "model": model,
            }

        err = io.StringIO()
        with redirect_stderr(err):
            with mock.patch.object(jev, "typesafe_evaluate", side_effect=fake_eval):
                rec = jev.maybe_laya_shadow(ready, STATE, CRITERIA, qid="case")
        self.assertEqual(seen, ["qwen3.6:35b", "qwen2.5:14b"])
        self.assertTrue(rec.get("auto_act"))
        shadow = rec.get("shadow") or {}
        self.assertEqual(shadow.get("model"), "qwen2.5:14b")
        self.assertEqual(shadow.get("fallback_from"), "qwen3.6:35b")
        self.assertEqual(shadow.get("action"), "pass")
        self.assertIn(
            "decision-route: fallback qwen3.6:35b -> qwen2.5:14b",
            err.getvalue(),
        )
        self.assertEqual(jev.typesafe_model(), "jev-1.13.0")

        seen.clear()
        os.environ["PFY_JEV_MODEL"] = "english"
        err = io.StringIO()
        with redirect_stderr(err):
            with mock.patch.object(jev, "typesafe_evaluate", side_effect=fake_eval):
                rec = jev.maybe_laya_shadow(ready, STATE, CRITERIA, qid="case")
        self.assertEqual(seen, ["english"])
        self.assertFalse(rec.get("auto_act"))
        self.assertNotIn("fallback qwen3.6:35b", err.getvalue())
        shadow = rec.get("shadow") or {}
        self.assertNotIn("fallback_from", shadow)
        os.environ.pop("PFY_JEV_MODEL", None)

        seen.clear()
        from pfylib import model_choice as mc

        mc.save_task("decision-route", "local", "custom:9b")
        err = io.StringIO()
        with redirect_stderr(err):
            with mock.patch.object(jev, "typesafe_evaluate", side_effect=fake_eval):
                rec = jev.maybe_laya_shadow(ready, STATE, CRITERIA, qid="case")
        self.assertEqual(seen, ["custom:9b"])
        self.assertFalse(rec.get("auto_act"))
        self.assertNotIn("fallback qwen3.6:35b", err.getvalue())


if __name__ == "__main__":
    unittest.main()
