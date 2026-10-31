"""Entry 149 smoke (MemPalace): missing binary, missing model cache, bad or non-positive timeout, inexact version pin
and unusable bwrap exit 2; a store that ranks the wrong note first, files the wrong drawer count, fails a step, or
writes into the real HOME FAILs; a correct stub PASSes. Sandbox tests kill the no-sandbox mutants: the child must get
no network (a loopback connect never reaches the listener), a read-only root (a write outside the smoke's temp dir
fails) and a temp HOME holding the copied model cache. Stubs are tiny Python scripts (shebang = this interpreter)
with knobs baked in; receipts go to a temp dir. Tests that need a real scan skip when bwrap is not usable, like
Entry 148; the no-bwrap exit-2 contract is asserted on every host."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/x-intake-local/smoke_149.py"
MODEL_REL = ".cache/chroma/onnx_models/all-MiniLM-L6-v2"


def _bwrap_usable() -> bool:
    """Same probe the smoke uses (smoke_149.bwrap_ok), so tests skip exactly when the smoke would exit 2."""
    spec = importlib.util.spec_from_file_location("smoke_149_probe", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.bwrap_ok()


BWRAP_OK = _bwrap_usable()
needs_bwrap = unittest.skipUnless(BWRAP_OK, "SKIP: bwrap-missing; confinement was not demonstrated")

STUB = r'''
import os, sys, pathlib, socket
a = sys.argv[1:]
if a[:1] == ["--version"]:
    print(K["version_text"] if "version_text" in K else "MemPalace " + K["version"])
    sys.exit(K.get("version_rc", 0))
if K.get("dial"):
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect(("127.0.0.1", K["dial"]))
    except OSError:
        pass
    finally:
        s.close()
if K.get("probe"):
    try:
        pathlib.Path(K["probe"]).write_text("escaped")
    except OSError:
        pass
if K.get("expect_temp_home"):
    h = os.environ.get("HOME", "")
    if h == K["expect_temp_home"] or "pfy-smoke-149-" not in h or not pathlib.Path(h, K["model_rel"]).is_dir():
        sys.exit(9)
if K.get("touch_real"):
    try:
        pathlib.Path(K["touch_real"], ".mempalace").mkdir(exist_ok=True)
    except OSError:
        pass
cmd = a[2]
if cmd == "init":
    sys.exit(K.get("init_exit", 0))
if cmd == "mine":
    print("  Drawers filed: %d" % K["drawers"]); sys.exit(K.get("mine_exit", 0))
q = a[3]
first, second = ("auth.md", "ci.md") if "auth" in q else ("ci.md", "auth.md")
if K.get("swap"):
    first, second = second, first
print("  [1] proj / documentation\n      Source: %s\n  [2]\n      Source: %s" % (first, second))
sys.exit(K.get("search_exit", 0))
'''

BASE = {"version": "3.12.0", "drawers": 2}


class Smoke149(unittest.TestCase):
    def run_smoke(self, knobs=None, env=None, model=True, on_path=False):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "realhome"
            real.mkdir()
            mh = td / "mphome"
            if model:
                (mh / ".cache/chroma/onnx_models/all-MiniLM-L6-v2").mkdir(parents=True)
            env2 = {"PATH": os.environ.get("PATH", ""), "HOME": str(real), "MEMPALACE_HOME": str(mh),
                    "PFY_SMOKE_RECEIPT_DIR": str(td / "r")}
            if knobs is not None:
                k = dict(knobs)
                if k.get("touch_real"):
                    k["touch_real"] = str(real)
                if k.get("expect_temp_home"):
                    k["expect_temp_home"] = str(real)
                    k["model_rel"] = MODEL_REL
                if k.get("probe"):
                    k["probe"] = str(td / "escaped.txt")
                stub = td / "mempalace"
                stub.write_text(f"#!{sys.executable}\nK = {k!r}\n" + STUB, encoding="utf-8")
                stub.chmod(0o755)
                if on_path:
                    bindir = td / "bin"
                    bindir.mkdir()
                    path_stub = bindir / "mempalace"
                    path_stub.write_text(stub.read_text(encoding="utf-8"), encoding="utf-8")
                    path_stub.chmod(0o755)
                    env2["PATH"] = str(bindir) + os.pathsep + env2["PATH"]
                else:
                    env2["MEMPALACE_BIN"] = str(stub)
            else:
                env2["MEMPALACE_BIN"] = str(td / "missing")
            env2.update(env or {})
            p = subprocess.run([sys.executable, str(SCRIPT)], env=env2, capture_output=True, text=True, timeout=120)
            rec = json.loads((td / "r" / "latest.json").read_text())
            self.escaped = (td / "escaped.txt").exists()
            return p.returncode, rec

    def _load(self):
        n = getattr(self, "_loads", 0) + 1
        self._loads = n
        spec = importlib.util.spec_from_file_location(f"smoke_149_case_{id(self)}_{n}", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _call_main(self, mod, real, mh, stub, td):
        saved = dict(os.environ)
        try:
            os.environ.clear()
            os.environ.update({
                "PATH": saved.get("PATH", ""),
                "HOME": str(real),
                "MEMPALACE_HOME": str(mh),
                "MEMPALACE_BIN": str(stub),
                "PFY_SMOKE_RECEIPT_DIR": str(td / "r"),
            })
            return mod.main()
        finally:
            os.environ.clear()
            os.environ.update(saved)

    def _run_inprocess(self, knobs, bind_real=False):
        """Call main() in this process. bind_real passes extra_binds; main() never does."""
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "realhome"
            real.mkdir()
            mh = td / "mphome"
            (mh / MODEL_REL).mkdir(parents=True)
            k = dict(knobs)
            if k.get("touch_real"):
                k["touch_real"] = str(real)
            stub = td / "mempalace"
            stub.write_text(f"#!{sys.executable}\nK = {k!r}\n" + STUB, encoding="utf-8")
            stub.chmod(0o755)
            mod = self._load()
            if bind_real:
                orig = mod.run
                home = str(real)
                def wrapped(binary, args, tmp, timeout, extra_binds=None, _orig=orig, _home=home):
                    return _orig(binary, args, tmp, timeout, extra_binds=["--bind", _home, _home])
                mod.run = wrapped
            code = self._call_main(mod, real, mh, stub, td)
            rec = json.loads((td / "r" / "latest.json").read_text(encoding="utf-8"))
            wrote = (real / ".mempalace").is_dir()
            return code, rec, wrote

    def _run_mount_case(self, proc=None, shm=None):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "realhome"
            real.mkdir()
            mh = td / "mphome"
            (mh / MODEL_REL).mkdir(parents=True)
            k = dict(BASE, probe=str(td / "escaped.txt"))
            stub = td / "mempalace"
            stub.write_text(f"#!{sys.executable}\nK = {k!r}\n" + STUB, encoding="utf-8")
            stub.chmod(0o755)
            mod = self._load()
            if proc is not None:
                mod.PROC_PATH = proc
            if shm is not None:
                mod.SHM_PATH = shm
            code = self._call_main(mod, real, mh, stub, td)
            rec = json.loads((td / "r" / "latest.json").read_text(encoding="utf-8"))
            self.escaped = (td / "escaped.txt").exists()
            return code, rec, self.escaped

    @needs_bwrap
    def test_pass(self):
        code, rec = self.run_smoke(dict(BASE))
        self.assertEqual(code, 0, rec)

    def test_missing_binary_exit_2(self):
        self.assertEqual(self.run_smoke(None)[0], 2)

    def test_missing_model_cache_exit_2(self):
        code, rec = self.run_smoke(dict(BASE), model=False)
        self.assertEqual(code, 2)
        self.assertIn("not cached", rec["reason"])

    def test_bad_timeout_exit_2(self):
        self.assertEqual(self.run_smoke(dict(BASE), {"PFY_XINTAKE_TIMEOUT": "nope"})[0], 2)

    @needs_bwrap
    def test_version_pin_exit_2(self):
        # The probe runs inside bwrap, so a host with no bwrap exits 2 for the bwrap reason first.
        code, rec = self.run_smoke(dict(BASE, version="9.9.9"))
        self.assertEqual(code, 2, rec)
        self.assertEqual(rec["reason"], "version pin 3.12.0 != --version 9.9.9")

    @needs_bwrap
    def test_version_of_reads_binary_on_path(self):
        # find_bin falls through to PATH when MEMPALACE_BIN is unset and the staged venv is absent.
        code, rec = self.run_smoke(dict(BASE), on_path=True)
        self.assertEqual(code, 0, rec)
        self.assertEqual(rec["version"], "3.12.0")
        self.assertIn("MemPalace 3.12.0", rec["version_output"])

    @needs_bwrap
    def test_version_of_rejects_broken_binary_on_path(self):
        # Non-zero exit and unparseable output: exit 2, no later step, never treated as the pinned version.
        code, rec = self.run_smoke(dict(BASE, version_rc=1, version_text="not-a-version"), on_path=True)
        self.assertEqual(code, 2, rec)
        self.assertIsNone(rec["version"])
        self.assertEqual(rec["reason"], "version pin 3.12.0 != --version None")
        self.assertIn("not-a-version", rec["version_output"])
        self.assertNotIn("init_exit", rec["checks"])

    def test_version_of_parses_banners_without_bwrap(self):
        # The bwrap-gated cases never import this parser on ubuntu CI. A banner
        # that is not a dotted triple must stay None so it cannot match the pin.
        mod = self._load()
        self.assertEqual(mod.version_of("MemPalace 3.12.0\n"), "3.12.0")
        self.assertEqual(mod.version_of("MemPalace 3.12.0 (also 9.9.9)\n"), "3.12.0")
        self.assertEqual(mod.version_of("mempalace 9.9.9\n"), "9.9.9")
        self.assertIsNone(mod.version_of("not-a-version\n"))
        self.assertIsNone(mod.version_of(""))
        self.assertIsNone(mod.version_of("build 3120\n"))

    def _version_stops_before_init(self, banner: str, parsed: str | None) -> None:
        """Stub bwrap out. A bad parse exits 2 and never starts init."""
        scratch = ROOT / "tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as td:
            td = Path(td)
            real = td / "realhome"
            real.mkdir()
            mh = td / "mphome"
            (mh / MODEL_REL).mkdir(parents=True)
            stub = td / "mempalace"
            stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            stub.chmod(0o755)
            mod = self._load()
            calls: list[list[str]] = []

            def fake_run(binary, args, tmp, timeout, extra_binds=None):
                calls.append(list(args))
                return subprocess.CompletedProcess(list(args), 0, stdout=banner, stderr="")

            mod.bwrap_ok = lambda: True
            mod.run = fake_run
            saved = dict(os.environ)
            try:
                os.environ.clear()
                os.environ.update({
                    "PATH": saved.get("PATH", ""),
                    "HOME": str(real),
                    "TMPDIR": str(scratch),
                    "MEMPALACE_HOME": str(mh),
                    "MEMPALACE_BIN": str(stub),
                    "PFY_SMOKE_RECEIPT_DIR": str(td / "r"),
                })
                code = mod.main()
            finally:
                os.environ.clear()
                os.environ.update(saved)
            rec = json.loads((td / "r" / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(code, 2, rec)
            self.assertEqual(rec.get("version"), parsed)
            self.assertEqual(rec.get("reason"), f"version pin 3.12.0 != --version {parsed}")
            self.assertEqual(calls, [["--version"]])
            self.assertNotIn("init_exit", rec.get("checks", {}))

    def test_unparsed_version_exits_2_before_init_without_bwrap(self):
        self._version_stops_before_init("not-a-version\n", None)

    def test_wrong_parsed_version_exits_2_before_init_without_bwrap(self):
        self._version_stops_before_init("MemPalace 9.9.9\n", "9.9.9")

    @needs_bwrap
    def test_wrong_ranking_fails(self):
        code, rec = self.run_smoke(dict(BASE, swap=True))
        self.assertEqual(code, 1)
        self.assertIn("q0_ranks_auth.md", rec["failed"])

    @needs_bwrap
    def test_wrong_drawer_count_fails(self):
        code, rec = self.run_smoke(dict(BASE, drawers=0))
        self.assertEqual(code, 1)
        self.assertIn("mine_filed_2", rec["failed"])

    @needs_bwrap
    def test_init_failure_fails(self):
        code, rec = self.run_smoke(dict(BASE, init_exit=3))
        self.assertEqual(code, 1)
        self.assertIn("init_ok", rec["failed"])

    @needs_bwrap
    def test_search_failure_fails(self):
        code, rec = self.run_smoke(dict(BASE, search_exit=1))
        self.assertEqual(code, 1)
        self.assertIn("q1_ok", rec["failed"])

    @needs_bwrap
    def test_real_home_write_fails(self):
        # The writable bind is passed only by this test. Production main() never passes extra_binds.
        code, rec, wrote = self._run_inprocess(dict(BASE, touch_real=True), bind_real=True)
        self.assertTrue(wrote, rec)
        self.assertEqual(code, 1, rec)
        self.assertIn("real_home_unchanged", rec["failed"])

    @needs_bwrap
    def test_real_home_env_hook_does_not_bind(self):
        # A leftover PFY_SMOKE_REAL_HOME_BIND must not make the real HOME writable.
        code, rec = self.run_smoke(dict(BASE, touch_real=True), {"PFY_SMOKE_REAL_HOME_BIND": "1"})
        self.assertEqual(code, 0, rec)
        self.assertEqual(rec["real_home_changed"], [])

    def test_bwrap_exit_1_fails_closed(self):
        # A bwrap that exists but exits 1 is not a license to run MemPalace on the host.
        with tempfile.TemporaryDirectory() as d:
            fake = Path(d) / "bwrap"
            fake.write_text(f"#!{sys.executable}\nimport sys\nsys.exit(1)\n", encoding="utf-8")
            fake.chmod(0o755)
            code, rec = self.run_smoke(dict(BASE, probe=True), {"PATH": d})
        self.assertEqual(code, 2, rec)
        self.assertEqual(rec["reason"], "bwrap is not usable here; MemPalace must run with no network")
        self.assertFalse(self.escaped, "MemPalace ran unsandboxed")
        self.assertNotIn("init_exit", rec["checks"])

    def test_required_proc_bind_missing_exits_2(self):
        code, rec, _wrote = self._run_mount_case(proc=str(Path("/no/such/proc-149")))
        self.assertEqual(code, 2, rec)
        self.assertIn("required bind", rec["reason"])
        self.assertIn("not usable", rec["reason"])
        self.assertNotIn("init_exit", rec["checks"])
        self.assertNotIn("sandbox", rec)

    def test_run_rechecks_a_bad_mount_and_does_not_spawn(self):
        # main() already stops on the mount reason. run() must stop again.
        # Removing that raise lets the child start. Recovery: raise the mount reason
        # before subprocess.run.
        scratch = ROOT / "tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as td:
            td = Path(td)
            mod = self._load()
            mod.PROC_PATH = str(td / "no-such-proc")
            spawned: list = []
            orig = mod.subprocess.run

            def fake_run(*args, **kwargs):
                spawned.append(args[0] if args else kwargs.get("args"))
                return subprocess.CompletedProcess([], 0, stdout="", stderr="")

            mod.subprocess.run = fake_run
            try:
                with self.assertRaises(OSError) as ctx:
                    mod.run(str(td / "mempalace"), ["--version"], td, 5)
            finally:
                mod.subprocess.run = orig
        self.assertIn("required bind", str(ctx.exception))
        self.assertIn("not usable", str(ctx.exception))
        self.assertEqual(spawned, [])

    def test_run_rechecks_missing_bwrap_and_does_not_spawn(self):
        # The child PATH is stripped. run() must look up bwrap on the caller PATH
        # again and refuse when that lookup misses. Recovery: raise before spawn.
        scratch = ROOT / "tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as td:
            td = Path(td)
            mod = self._load()
            spawned: list = []
            orig_run = mod.subprocess.run
            orig_which = mod.shutil.which

            def fake_run(*args, **kwargs):
                spawned.append(args[0] if args else kwargs.get("args"))
                return subprocess.CompletedProcess([], 0, stdout="", stderr="")

            def fake_which(cmd, *args, **kwargs):
                if cmd == "bwrap":
                    return None
                return orig_which(cmd, *args, **kwargs)

            mod.subprocess.run = fake_run
            mod.shutil.which = fake_which
            try:
                with self.assertRaises(OSError) as ctx:
                    mod.run(str(td / "mempalace"), ["--version"], td, 5)
            finally:
                mod.subprocess.run = orig_run
                mod.shutil.which = orig_which
        self.assertIn("bwrap is not usable", str(ctx.exception))
        self.assertEqual(spawned, [])

    def test_dir_usable_rejects_a_regular_file(self):
        # A readable file is not a mount point. Dropping the isdir check makes
        # os.access succeed and the smoke would treat the file as /proc.
        # Recovery: return False unless the path is a directory.
        scratch = ROOT / "tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as td:
            td = Path(td)
            regular = td / "not-a-dir"
            regular.write_text("x", encoding="utf-8")
            regular.chmod(0o644)
            mod = self._load()
            self.assertFalse(mod.dir_usable(str(regular), writable=False))
            self.assertFalse(mod.dir_usable(str(regular), writable=True))
            self.assertTrue(mod.dir_usable(str(td), writable=True))

    def test_required_shm_bind_unusable_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            shm = Path(d) / "shm"
            shm.mkdir()
            shm.chmod(0o555)
            try:
                code, rec, _wrote = self._run_mount_case(shm=str(shm))
            finally:
                shm.chmod(0o755)
        self.assertEqual(code, 2, rec)
        self.assertIn(str(shm), rec["reason"])
        self.assertIn("not usable", rec["reason"])
        self.assertNotIn("init_exit", rec["checks"])
        self.assertFalse(self.escaped, "MemPalace ran unsandboxed")

    @needs_bwrap
    def test_proc_and_shm_are_mounted_when_usable(self):
        # The child argv must carry both mounts. A ro-bind of / already exposes the host paths,
        # so seeing them inside the sandbox would not prove the flags were passed.
        real_bwrap = shutil.which("bwrap")
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "argv.log"
            wrap = Path(d) / "bwrap"
            wrap.write_text(
                "#!" + sys.executable + "\n"
                "import os, sys\n"
                f"open({str(log)!r}, 'a').write('\\n'.join(sys.argv) + '\\n---\\n')\n"
                f"os.execv({real_bwrap!r}, sys.argv)\n",
                encoding="utf-8")
            wrap.chmod(0o755)
            path = str(Path(d)) + os.pathsep + os.environ.get("PATH", "")
            code, rec = self.run_smoke(dict(BASE), {"PATH": path})
            text = log.read_text(encoding="utf-8")
        self.assertEqual(code, 0, rec)
        runs = [chunk for chunk in text.split("\n---\n") if "mempalace" in chunk]
        self.assertTrue(runs, text)
        for chunk in runs:
            self.assertIn("--tmpfs", chunk)
            self.assertIn("/dev/shm", chunk)
            self.assertIn("--proc", chunk)
            self.assertIn("/proc", chunk)

    def test_bwrap_without_proc_mount_fails_closed_with_bwrap_reason(self):
        # B1: a bwrap that runs but cannot mount /proc must fail in the probe, not later as a version mismatch.
        with tempfile.TemporaryDirectory() as d:
            fake = Path(d) / "bwrap"
            fake.write_text(f"#!{sys.executable}\nimport sys\nsys.exit(1 if '--proc' in sys.argv else 0)\n",
                            encoding="utf-8")
            fake.chmod(0o755)
            code, rec = self.run_smoke(dict(BASE, probe=True), {"PATH": d})
        self.assertEqual(code, 2, rec)
        self.assertEqual(rec["reason"], "bwrap is not usable here; MemPalace must run with no network")
        # The probe failure must not start MemPalace. A later run would fill checks or write the probe file.
        self.assertFalse(self.escaped, "MemPalace ran unsandboxed")
        self.assertNotIn("init_exit", rec["checks"])
        self.assertEqual(rec["checks"], {})

    def test_no_bwrap_exits_2_never_runs_unsandboxed(self):
        # B2: without bwrap the smoke must not fall back to running MemPalace with network and a writable root.
        with tempfile.TemporaryDirectory() as empty:
            code, rec = self.run_smoke(dict(BASE, probe=True), {"PATH": empty})
        self.assertEqual(code, 2, rec)
        self.assertEqual(rec["reason"], "bwrap is not usable here; MemPalace must run with no network")
        self.assertFalse(self.escaped, "MemPalace ran unsandboxed")
        self.assertNotIn("init_exit", rec["checks"])

    def test_zero_timeout_exit_2(self):
        # The reason matters: without the <=0 guard a zero timeout still exits 2, via a --version TimeoutExpired.
        code, rec = self.run_smoke(dict(BASE), {"PFY_XINTAKE_TIMEOUT": "0"})
        self.assertEqual(code, 2, rec)
        self.assertEqual(rec["reason"], "bad PFY_XINTAKE_TIMEOUT")

    def test_negative_timeout_exit_2(self):
        # The reason matters: without the <=0 guard a zero timeout still exits 2, via a --version TimeoutExpired.
        code, rec = self.run_smoke(dict(BASE), {"PFY_XINTAKE_TIMEOUT": "-5"})
        self.assertEqual(code, 2, rec)
        self.assertEqual(rec["reason"], "bad PFY_XINTAKE_TIMEOUT")

    @needs_bwrap
    def test_version_pin_is_exact(self):
        # The version probe runs inside bwrap, so without it the smoke exits 2 on the bwrap reason first.
        for v in ("3.12.0.1", "13.12.0", "3.12.0rc1"):
            code, rec = self.run_smoke(dict(BASE, version=v))
            self.assertEqual(code, 2, (v, rec))
            self.assertIn("version pin", rec["reason"])

    @needs_bwrap
    def test_mine_failure_fails(self):
        code, rec = self.run_smoke(dict(BASE, mine_exit=4))
        self.assertEqual(code, 1, rec)
        self.assertIn("mine_ok", rec["failed"])

    @needs_bwrap
    def test_child_gets_temp_home_with_model_cache(self):
        # The stub exits 9 on every step if HOME is the real HOME, is not the smoke's temp dir, or lacks the cache.
        code, rec = self.run_smoke(dict(BASE, expect_temp_home=True))
        self.assertEqual(code, 0, rec)

    @needs_bwrap
    def test_child_has_no_network(self):
        # Mutant: --unshare-net dropped, or the sandbox forced off. The listener must see no connection.
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(8)
        srv.settimeout(0.5)
        try:
            code, rec = self.run_smoke(dict(BASE, dial=srv.getsockname()[1]))
            try:
                conn, _ = srv.accept()
            except (socket.timeout, TimeoutError):
                reached = False
            else:
                conn.close()
                reached = True
        finally:
            srv.close()
        self.assertEqual(code, 0, rec)
        self.assertEqual(rec["sandbox"], "bwrap --unshare-net")
        self.assertFalse(reached, "a loopback connect from the child reached the host")

    @needs_bwrap
    def test_child_root_is_read_only(self):
        # Mutant: --bind / / instead of --ro-bind, or the sandbox forced off. A write outside the temp dir must fail.
        code, rec = self.run_smoke(dict(BASE, probe=True))
        self.assertEqual(code, 0, rec)
        self.assertFalse(self.escaped, "the child wrote outside the smoke's temp dir")


if __name__ == "__main__":
    unittest.main()
