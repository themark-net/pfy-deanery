"""Entry 148 smoke (SkillSpector): missing binary, bad timeout, version pin and unusable bwrap exit 2; a scanner
that calls the malicious fixture safe, misses a rule family, exits 0 on it, misreports the benign fixture, or writes
into its temp HOME or the real HOME FAILs; a connect to the host loopback stays blocked and a correct stub PASSes.
Stubs are tiny Python scripts (shebang = this interpreter) with knobs baked in; receipts go to a temp dir.
Issue objects use `id`, the same key the real tool emits."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/x-intake-local/smoke_148.py"


def _bwrap_usable() -> bool:
    """Same probe the smoke uses (smoke_148.bwrap_ok), so the tests skip exactly when the smoke would exit 2."""
    spec = importlib.util.spec_from_file_location("smoke_148_probe", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.bwrap_ok()


BWRAP_OK = _bwrap_usable()
# Hosts without usable bwrap (ubuntu-latest CI) cannot demonstrate confinement; the scan paths skip there, like
# test_pfy_build_local. The no-bwrap exit-2 contract is still asserted by test_no_bwrap_exits_2 on every host.
needs_bwrap = unittest.skipUnless(BWRAP_OK, "SKIP: bwrap-missing; confinement was not demonstrated")

STUB = r'''
import json, socket, sys, os, pathlib
a = sys.argv[1:]
if a[:1] == ["--version"]:
    print("SkillSpector v" + K["version"]); sys.exit(0)
src = pathlib.Path(a[1]); out = pathlib.Path(a[a.index("-o") + 1])
if K.get("real_home"):
    try:
        planted = pathlib.Path(K["real_home"], ".skillspector")
        planted.mkdir(parents=True, exist_ok=True)
        (planted / "planted").write_text("x")
    except OSError:
        pass
if K.get("dial"):
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect(("127.0.0.1", K["dial"]))
    except OSError:
        pass
    else:
        pathlib.Path(os.environ["HOME"], ".skillspector-net").write_text("net")
    finally:
        s.close()
bad = "evil.example" in (src / "SKILL.md").read_text()
if K.get("touch_home"):
    pathlib.Path(os.environ["HOME"], ".skillspector-cache").write_text("x")
llm = False
if K.get("misreport_good") and not bad:
    ids = ["P9"]
    ra = {"score": 40, "recommendation": "CAUTION"}
    code, llm = 1, True
elif bad and not K.get("blind"):
    ids = [i for i in K["ids"]]
    ra = {"score": K["score"], "recommendation": "DO_NOT_INSTALL"}
    code = K["bad_exit"]
else:
    ids, ra, code = [], {"score": 0, "recommendation": "SAFE"}, 0
out.write_text(json.dumps({"risk_assessment": ra, "issues": [{"id": i} for i in ids],
                           "metadata": {"llm_requested": llm}}))
sys.exit(code)
'''

BASE = {"version": "2.12.0", "ids": ["P1", "SC2", "TM2"], "score": 93, "bad_exit": 1}


class Smoke148(unittest.TestCase):
    def run_smoke(self, knobs=None, env=None):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            env2 = {"PATH": os.environ.get("PATH", ""), "HOME": str(td / "realhome"),
                    "PFY_SMOKE_RECEIPT_DIR": str(td / "r")}
            (td / "realhome").mkdir()
            if knobs is not None:
                knobs = dict(knobs)
                if knobs.pop("touch_real_home", False):
                    knobs["real_home"] = str(td / "realhome")
                stub = td / "skillspector"
                stub.write_text(f"#!{sys.executable}\nK = {knobs!r}\n" + STUB, encoding="utf-8")
                stub.chmod(0o755)
                env2["SKILLSPECTOR_BIN"] = str(stub)
            else:
                env2["SKILLSPECTOR_BIN"] = str(td / "missing")
            env2.update(env or {})
            p = subprocess.run([sys.executable, str(SCRIPT)], env=env2, capture_output=True, text=True, timeout=120)
            rec = json.loads((td / "r" / "latest.json").read_text())
            return p.returncode, rec

    def _load(self):
        spec = importlib.util.spec_from_file_location("smoke_148_under_test", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _run_inprocess(self, knobs, bind_real=False, env=None):
        """Call main() in this process. bind_real passes extra_binds; main() never does."""
        keys = ("HOME", "PATH", "SKILLSPECTOR_BIN", "PFY_SMOKE_RECEIPT_DIR",
                "PFY_SMOKE_REAL_HOME_BIND", "PFY_XINTAKE_TIMEOUT")
        old = {k: os.environ.get(k) for k in keys}
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "realhome"
            real.mkdir()
            knobs = dict(knobs)
            if knobs.pop("touch_real_home", False):
                knobs["real_home"] = str(real)
            stub = td / "skillspector"
            stub.write_text(f"#!{sys.executable}\nK = {knobs!r}\n" + STUB, encoding="utf-8")
            stub.chmod(0o755)
            mod = self._load()
            if bind_real:
                orig = mod.run
                home = str(real)
                def wrapped(binary, args, tmp, timeout, extra_binds=None, _orig=orig, _home=home):
                    return _orig(binary, args, tmp, timeout, extra_binds=["--bind", _home, _home])
                mod.run = wrapped
            try:
                os.environ["HOME"] = str(real)
                os.environ["PATH"] = os.environ.get("PATH", "")
                os.environ["SKILLSPECTOR_BIN"] = str(stub)
                os.environ["PFY_SMOKE_RECEIPT_DIR"] = str(td / "r")
                for k, v in (env or {}).items():
                    os.environ[k] = v
                with contextlib.redirect_stdout(io.StringIO()):
                    code = mod.main()
            finally:
                for k, v in old.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
            rec = json.loads((td / "r" / "latest.json").read_text())
            wrote = (real / ".skillspector").is_dir()
            return code, rec, wrote

    @needs_bwrap
    def test_pass(self):
        code, rec = self.run_smoke(dict(BASE))
        self.assertEqual(code, 0, rec)

    def test_missing_binary_exit_2(self):
        self.assertEqual(self.run_smoke(None)[0], 2)

    def test_bad_timeout_exit_2(self):
        self.assertEqual(self.run_smoke(dict(BASE), {"PFY_XINTAKE_TIMEOUT": "nope"})[0], 2)

    def test_version_pin_exit_2(self):
        code, rec = self.run_smoke(dict(BASE, version="9.9.9"))
        self.assertEqual(code, 2, rec)
        self.assertEqual(rec["reason"], "version pin 2.12.0 not in --version output")

    @needs_bwrap
    def test_blind_scanner_fails(self):
        code, rec = self.run_smoke(dict(BASE, blind=True))
        self.assertEqual(code, 1)
        self.assertIn("bad_do_not_install", rec["failed"])

    @needs_bwrap
    def test_missing_supply_chain_fails(self):
        code, rec = self.run_smoke(dict(BASE, ids=["P1", "TM2"]))
        self.assertEqual(code, 1)
        self.assertIn("bad_flags_supply_chain", rec["failed"])

    @needs_bwrap
    def test_missing_prompt_injection_fails(self):
        code, rec = self.run_smoke(dict(BASE, ids=["PE3", "SC2"]))
        self.assertEqual(code, 1)
        self.assertIn("bad_flags_prompt_injection", rec["failed"])

    @needs_bwrap
    def test_low_score_fails(self):
        code, rec = self.run_smoke(dict(BASE, score=40))
        self.assertIn("bad_score_ge_70", rec["failed"])

    @needs_bwrap
    def test_bad_exit_zero_fails(self):
        code, rec = self.run_smoke(dict(BASE, bad_exit=0))
        self.assertIn("bad_exit_nonzero", rec["failed"])

    @needs_bwrap
    def test_temp_home_write_fails(self):
        code, rec = self.run_smoke(dict(BASE, touch_home=True))
        self.assertEqual(code, 1)
        self.assertIn("temp_home_empty", rec["failed"])

    def test_no_bwrap_exits_2(self):
        with tempfile.TemporaryDirectory() as empty:
            code, rec = self.run_smoke(dict(BASE), {"PATH": empty})
        self.assertEqual(code, 2, rec)
        self.assertIn("bwrap is not usable", rec["reason"])

    @needs_bwrap
    def test_misreported_benign_fails(self):
        code, rec = self.run_smoke(dict(BASE, misreport_good=True))
        self.assertEqual(code, 1, rec)
        for name in ("good_exit_0", "good_safe", "good_no_issues", "no_llm"):
            self.assertIn(name, rec["failed"], rec)
        self.assertTrue(rec["checks"]["good_report_written"], rec)
        self.assertNotIn("bad_do_not_install", rec["failed"])

    @needs_bwrap
    def test_network_connect_attempt_stays_blocked(self):
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(8)
        try:
            code, rec = self.run_smoke(dict(BASE, dial=srv.getsockname()[1]))
        finally:
            srv.close()
        self.assertEqual(code, 0, rec)
        self.assertEqual(rec["sandbox"], "bwrap --unshare-net")
        self.assertTrue(rec["checks"]["temp_home_empty"], rec)

    @needs_bwrap
    def test_real_home_write_fails(self):
        # The writable bind is passed only by this test. Production main() never passes extra_binds.
        code, rec, wrote = self._run_inprocess(dict(BASE, touch_real_home=True), bind_real=True)
        self.assertTrue(wrote, rec)
        self.assertEqual(code, 1, rec)
        self.assertIn("real_home_unchanged", rec["failed"], rec)
        self.assertEqual(rec["real_home_changed"], [".skillspector"])

    @needs_bwrap
    def test_real_home_env_hook_does_not_bind(self):
        # A leftover PFY_SMOKE_REAL_HOME_BIND must not make the real HOME writable.
        code, rec = self.run_smoke(dict(BASE, touch_real_home=True), {"PFY_SMOKE_REAL_HOME_BIND": "1"})
        self.assertEqual(code, 0, rec)
        self.assertEqual(rec["real_home_changed"], [])


if __name__ == "__main__":
    unittest.main()
