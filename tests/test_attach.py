"""pfylib.attach: one harness-parameterised Attach vs. the pre-refactor clones (T-0121).

``EXPECTED`` was captured from ``scripts/pfy_attach_usable_{196,202,220,221}.py``
at commit de0da83 (before they became shims) by driving each
``open_enterable_<x>_session`` offline: missing binary, no local engine, and
terminal-cannot-start with ``spawn_terminal_opencode`` stubbed. These values are
the contract the shared body must keep -- do not regenerate them from the new
code.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib import _legacy, attach, registry  # noqa: E402

BASE = "http://127.0.0.1:1919/v1"
NEXT_UP = "Launch env or ./pfy up"

# harness id -> pre-refactor observations (verbatim).
EXPECTED = {
    "hermes": {
        "script": "pfy_attach_usable_196",
        "session_id": "hermes",
        "which_bin_calls": [["hermes", "hermes-agent"]],
        "SESSION_FILE": "hermes-session-reach",
        "TERMINAL_PID_FILE": "hermes-terminal.pid",
        "ATTACH_BASE_FILE": "hermes-attach-base",
        "SESSION_REACH_OK": "terminal \u00b7 Hermes \u00b7 models \u00b7 smoke",
        "NEXT_INSTALL": "curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash",
        "stub_default": "./pfy start hermes",
        "missing": {"copy": "./pfy start hermes", "error": "hermes missing", "id": "hermes", "live": "FAIL", "next_step": "curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash", "ok": False, "session_reach": "FAIL", "usable": False},
        "log_name": "sidecar-hermes.log",
        "no_start_error": "Hermes terminal cannot start (captured)",
    },
    "grok": {
        "script": "pfy_attach_usable_202",
        "session_id": "grok",
        "which_bin_calls": [["grok"]],
        "SESSION_FILE": "grok-session-reach",
        "TERMINAL_PID_FILE": "grok-terminal.pid",
        "ATTACH_BASE_FILE": "grok-attach-base",
        "SESSION_REACH_OK": "terminal \u00b7 Grok \u00b7 models \u00b7 smoke",
        "NEXT_INSTALL": None,
        "stub_default": "./pfy start grok",
        "missing": {"copy": "./pfy start grok", "error": "grok missing", "id": "grok", "live": "FAIL", "ok": False, "session_reach": "FAIL", "usable": False},
        "log_name": "sidecar-grok.log",
        "no_start_error": "Grok terminal cannot start (captured)",
    },
    "codex": {
        "script": "pfy_attach_usable_220",
        "session_id": "codex",
        "which_bin_calls": [["codex"]],
        "SESSION_FILE": "codex-session-reach",
        "TERMINAL_PID_FILE": "codex-terminal.pid",
        "ATTACH_BASE_FILE": "codex-attach-base",
        "SESSION_REACH_OK": "terminal \u00b7 Codex \u00b7 models \u00b7 smoke",
        "NEXT_INSTALL": "curl -fsSL https://chatgpt.com/codex/install.sh | sh",
        "stub_default": "./pfy start codex",
        "missing": {"copy": "./pfy start codex", "error": "codex missing", "id": "codex", "live": "FAIL", "next_step": "curl -fsSL https://chatgpt.com/codex/install.sh | sh", "ok": False, "session_reach": "FAIL", "usable": False},
        "log_name": "sidecar-codex.log",
        "no_start_error": "Codex terminal cannot start (captured)",
    },
    "claude-code": {
        "script": "pfy_attach_usable_221",
        "session_id": "claude",
        "which_bin_calls": [["claude"]],
        "SESSION_FILE": "claude-session-reach",
        "TERMINAL_PID_FILE": "claude-terminal.pid",
        "ATTACH_BASE_FILE": "claude-attach-base",
        "SESSION_REACH_OK": "terminal \u00b7 Claude \u00b7 models \u00b7 smoke",
        "NEXT_INSTALL": "curl -fsSL https://claude.ai/install.sh | bash",
        "stub_default": "./pfy start claude",
        "missing": {"copy": "./pfy start claude", "error": "claude missing", "id": "claude", "live": "FAIL", "next_step": "curl -fsSL https://claude.ai/install.sh | bash", "ok": False, "session_reach": "FAIL", "usable": False},
        "log_name": "sidecar-claude.log",
        "no_start_error": "Claude terminal cannot start (captured)",
    },
}
# Same for every harness (captured identical four times).
NO_ENGINE = {"copy": "FAIL attach -- no local engine \u00b7 Launch env or ./pfy up", "detect_status": "missing", "engine": "none", "error": "no local engine", "next_step": NEXT_UP}
ENV_ADDED = {"LOCAL_OPENAI_BASE_URL": BASE, "OPENAI_API_KEY": "local", "OPENAI_BASE_URL": BASE, "PFY_ATTACH_MODE": "bare"}
SPAWN_CWD_IS_ROOT = True


def _deps(state):
    return dict(
        ROOT=ROOT, STATE=state, inspect_models=lambda b: [],
        record_sidecar_pid=lambda *a: None, record_last_verb=lambda *a: None,
        pid_alive=lambda p: False,
    )


def _load_shim(script):
    spec = importlib.util.spec_from_file_location("shim_" + script, ROOT / "scripts" / (script + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Tmp(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in ("PFY_STATE_DIR", "LOCAL_OPENAI_BASE_URL", "OPENAI_API_KEY", "PATH")}
        self.tmp = Path(tempfile.mkdtemp(prefix="pfylib-attach-"))
        self.state = self.tmp / "state"
        self.state.mkdir()
        os.environ["PFY_STATE_DIR"] = str(self.state)
        os.environ.pop("LOCAL_OPENAI_BASE_URL", None)
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ["PATH"] = str(self.tmp / "empty-bin")  # no oc / axon / harness binaries

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class ProfileTests(unittest.TestCase):
    def test_registry_has_exactly_the_four_attach_profiles(self):
        self.assertEqual(sorted(registry.attach_harness_ids(ROOT)), sorted(EXPECTED))

    def test_profile_matches_pre_refactor_constants(self):
        for hid, exp in EXPECTED.items():
            prof = attach.profile(hid, ROOT)
            self.assertIsNotNone(prof, hid)
            self.assertEqual(prof["session_id"], exp["session_id"], hid)
            self.assertEqual(prof["script"], exp["script"], hid)
            self.assertEqual(list(prof["binaries"]), exp["which_bin_calls"][0], hid)
            self.assertEqual(prof["session_file"], exp["SESSION_FILE"], hid)
            self.assertEqual(prof["terminal_pid_file"], exp["TERMINAL_PID_FILE"], hid)
            self.assertEqual(prof["attach_base_file"], exp["ATTACH_BASE_FILE"], hid)
            self.assertEqual(prof["session_reach_ok"], exp["SESSION_REACH_OK"], hid)
            self.assertEqual(prof["next_install"], exp["NEXT_INSTALL"], hid)
            self.assertEqual(prof["stub_line"], exp["stub_default"], hid)
            self.assertEqual(prof["log_file"], exp["log_name"], hid)

    def test_profile_accepts_session_id_alias(self):
        self.assertEqual(attach.profile("claude", ROOT)["id"], "claude-code")
        self.assertIsNone(attach.profile("gemini", ROOT))
        with self.assertRaises(KeyError):
            attach.prepare("gemini", root_dir=ROOT)

    def test_codex_fallback_is_in_registry_not_code(self):
        self.assertEqual(list(attach.profile("codex", ROOT)["bin_fallbacks"]), ["~/.local/bin/codex"])
        self.assertEqual(attach.profile("hermes", ROOT)["bin_fallbacks"], ())

    def test_shim_modules_expose_board_names_and_constants(self):
        for hid, exp in EXPECTED.items():
            mod = _load_shim(exp["script"])
            self.assertTrue(hasattr(mod, "open_enterable_%s_session" % exp["session_id"]), hid)
            self.assertTrue(callable(mod.live_session_reach), hid)
            self.assertEqual(mod.SESSION_FILE, exp["SESSION_FILE"])
            self.assertEqual(mod.SESSION_REACH_OK, exp["SESSION_REACH_OK"])
            if exp["NEXT_INSTALL"]:
                self.assertEqual(mod.NEXT_INSTALL, exp["NEXT_INSTALL"])
            lines = (ROOT / "scripts" / (exp["script"] + ".py")).read_text().splitlines()
            self.assertLessEqual(len(lines), 45, "%s shim grew past a thin shim" % exp["script"])


class PrepareTests(_Tmp):
    def test_prepare_env_keys_and_binary_match_pre_refactor(self):
        for hid, exp in EXPECTED.items():
            plan = attach.prepare(hid, env={}, base=BASE, state=self.state, root_dir=ROOT)
            self.assertTrue(plan.ok, hid)
            self.assertEqual(plan.env, ENV_ADDED, hid)
            self.assertEqual(list(plan.binaries), exp["which_bin_calls"][0], hid)
            self.assertEqual(plan.hid, exp["session_id"])
            self.assertEqual(plan.log_file, str(self.state / exp["log_name"]))
            self.assertEqual(plan.session_reach_ok, exp["SESSION_REACH_OK"])
            self.assertEqual(plan.mode, "bare")
            self.assertEqual(plan.lane, "local")
            self.assertIsNone(plan.brief)  # no attach-agents.md until 208 --prepare ran
            self.assertFalse(list(self.state.iterdir()), "prepare must not write")

    def test_prepare_brief_is_attach_agents_when_present(self):
        agents = self.state / attach.AGENTS_FILE
        agents.write_text("# brief\n")
        plan = attach.prepare("grok", env={}, base=BASE, state=self.state, root_dir=ROOT)
        self.assertEqual(plan.brief, str(agents))
        self.assertEqual(plan.env["PFY_ATTACH_AGENTS"], str(agents))

    def test_prepare_does_not_override_parent_api_key(self):
        plan = attach.prepare("codex", env={"OPENAI_API_KEY": "keep"}, base=BASE, state=self.state, root_dir=ROOT)
        self.assertNotIn("OPENAI_API_KEY", plan.env)

    def test_prepare_rejects_cloud_lane_and_unprepared_mode(self):
        p = attach.prepare("grok", lane="cloud", state=self.state, root_dir=ROOT)
        self.assertFalse(p.ok)
        self.assertIn("gab", p.next_step)
        p = attach.prepare("grok", mode="orchestration", state=self.state, root_dir=ROOT)
        self.assertFalse(p.ok)
        self.assertIn("--prepare grok orchestration", p.next_step)
        p = attach.prepare("grok", mode="quantum", state=self.state, root_dir=ROOT)
        self.assertFalse(p.ok)
        self.assertIn("unknown mode", p.error)
        import contextlib
        import io

        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(attach.run(p), 1)

    def test_as_dict_is_json_shaped(self):
        d = attach.prepare("hermes", env={}, base=BASE, state=self.state, root_dir=ROOT).as_dict()
        self.assertIsInstance(d["binaries"], list)
        self.assertEqual(d["harness"], "hermes")


class OpenSessionTests(_Tmp):
    def test_missing_binary_dict_is_verbatim(self):
        for hid, exp in EXPECTED.items():
            calls = []

            def which(*names):
                calls.append(list(names))
                return ""

            out = attach.open_session(hid, which_bin=which, live_openai_base=lambda: ("", {}), root_dir=ROOT, **_deps(self.state))
            self.assertEqual(out, exp["missing"], hid)
            self.assertEqual(calls, exp["which_bin_calls"], hid)

    def test_no_engine_dict_is_verbatim(self):
        for hid, exp in EXPECTED.items():
            out = attach.open_session(
                hid, which_bin=lambda *a: "/tmp/fake-" + hid,
                live_openai_base=lambda: ("", {"engine": "none", "status": "missing"}),
                root_dir=ROOT, **_deps(self.state),
            )
            self.assertEqual({k: out[k] for k in NO_ENGINE}, NO_ENGINE, hid)
            self.assertEqual(out["id"], exp["session_id"])
            self.assertFalse(out["ok"])
            self.assertFalse(out["usable"])
            self.assertEqual(out["session_reach"], "FAIL")

    def test_spawn_env_bin_log_and_no_start_dict_are_verbatim(self):
        term = _legacy.enterable_helpers(ROOT)
        real_spawn = term.spawn_terminal_opencode
        try:
            for hid, exp in EXPECTED.items():
                captured = {}

                def fake_spawn(bin_path, cwd, env, log, pid_alive):
                    captured.update(bin=bin_path, cwd=cwd, env=dict(env), log=str(log))
                    return False, 0, "OpenCode terminal cannot start (captured)"

                term.spawn_terminal_opencode = fake_spawn
                before = dict(os.environ)
                out = attach.open_session(
                    hid, which_bin=lambda *a: "/tmp/fake-" + hid,
                    live_openai_base=lambda: (BASE, {"engine": "freetoken", "status": "ready"}),
                    root_dir=ROOT, **_deps(self.state),
                )
                self.assertEqual(captured["bin"], "/tmp/fake-" + hid, hid)
                self.assertEqual(captured["cwd"], str(ROOT), hid)
                self.assertEqual(captured["log"], str(self.state / exp["log_name"]), hid)
                added = {k: v for k, v in captured["env"].items() if before.get(k) != v}
                self.assertEqual(added, ENV_ADDED, hid)
                self.assertEqual(out["error"], exp["no_start_error"], hid)
                self.assertEqual(out["copy"], "FAIL open session -- " + exp["no_start_error"], hid)
                self.assertEqual(out["log"], str(self.state / exp["log_name"]))
                self.assertEqual(out["base_url"], BASE)
                self.assertEqual(out["next_step"], NEXT_UP)
                self.assertEqual(out["pid"], "")
                self.assertFalse(out["ok"])
        finally:
            term.spawn_terminal_opencode = real_spawn

    def test_live_session_reach_clears_when_pid_dead(self):
        attach.write_session_reach("codex", self.state, EXPECTED["codex"]["SESSION_REACH_OK"])
        attach.write_terminal_pid("codex", self.state, 4242)
        self.assertEqual(attach.live_session_reach("codex", self.state, lambda p: True), EXPECTED["codex"]["SESSION_REACH_OK"])
        self.assertEqual(attach.live_session_reach("codex", self.state, lambda p: False), "")
        self.assertFalse((self.state / "codex-session-reach").exists())
        self.assertFalse((self.state / "codex-terminal.pid").exists())

    def test_selftest_passes_for_every_harness(self):
        import contextlib
        import io

        for hid in EXPECTED:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = attach.selftest(hid, ROOT)
            self.assertEqual(rc, 0, buf.getvalue())
            self.assertTrue(buf.getvalue().startswith("PASS selftest \u00b7 Attach "), buf.getvalue())


class ProveCliTests(_Tmp):
    def test_prove_without_base_prints_fail_next(self):
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = attach.main("grok", ["--prove"])
        self.assertEqual(rc, 1)
        self.assertEqual(buf.getvalue(), "FAIL attach -- no live local endpoint \u00b7 Launch env or ./pfy up\n  equiv: ./pfy models\n")

    def test_usage_exit_2(self):
        import contextlib
        import io

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = attach.main("grok", ["--bogus"], prog="pfy_attach_usable_202.py")
        self.assertEqual(rc, 2)
        self.assertTrue(err.getvalue().startswith("usage: pfy_attach_usable_202.py --prove [BASE]"))


if __name__ == "__main__":
    unittest.main()
