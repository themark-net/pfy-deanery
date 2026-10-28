"""Entries 112-114 smoke: child env is the reduced allowlist, and a timeout kills grandchildren.

Parent HOME is a temp dir this test owns so a stub cannot touch the operator's real home.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_RECEIPTS: Path | None = None
ALLOW = {"HOME", "PATH", "TERM", "LANG", "NO_COLOR"}
# Fake values only. A child that still sees the parent env fails the test.
SENTINELS = {
    "GROK_API_KEY": "pfy-sentinel-grok",
    "OPENAI_API_KEY": "pfy-sentinel-openai",
    "ANTHROPIC_API_KEY": "pfy-sentinel-anthropic",
    "AWS_SECRET_ACCESS_KEY": "pfy-sentinel-aws",
    "GITHUB_TOKEN": "pfy-sentinel-github",
    "PFY_SENTINEL_PARENT": "pfy-sentinel-parent",
}

# --version dumps the execve environment and prints a new-enough Node. Any other command exits 0
# without creating an agent, so the smoke stops at the folder check.
NODE_VERSION_STUB = """#!/usr/bin/python3
import os
import sys
from pathlib import Path
out = Path(__file__).resolve().parent / "node.environ"
if sys.argv[1:2] == ["--version"]:
    lines = [f"{k}={v}" for k, v in sorted(os.environ.items())]
    out.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    print("v22.19.0")
raise SystemExit(0)
"""

# Prints a commit that will not match the pin, after dumping the execve environment.
GIT_STUB = """#!/usr/bin/python3
import os
from pathlib import Path
out = Path(__file__).resolve().parent / "git.environ"
lines = [f"{k}={v}" for k, v in sorted(os.environ.items())]
out.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
print("not-a-real-commit")
"""

# Not --version: dirty the baked-in real ~/overtime, fork a sleeper, then sleep.
# Fail: the sleeper is still alive after the smoke, or the receipt never reports the dirty home.
# Recover: the process group is gone, and the receipt names the real-HOME check.
GRANDCHILD_STUB = """#!/bin/sh
if [ "$1" = "--version" ]; then
  echo v22.19.0
  exit 0
fi
if [ "$1" = "--grandchild" ]; then
  sleep 60
  exit 0
fi
mkdir -p "__PARENT_OT__"
echo touched > "__PARENT_OT__/marker"
"$0" --grandchild __MARKER__ >/dev/null 2>&1 &
sleep 60
"""

# node --version that never returns: forks a sleeper, then sleeps. The pid file proves the
# grandchild started. Fail: node_ok waits out its own timeout and the sleeper is still alive.
# Recover: node_ok returns false quickly and the sleeper is dead.
HANGING_NODE = """#!/bin/sh
if [ "$1" = "--grandchild" ]; then
  echo $$ > "__PIDFILE__"
  sleep 60
  exit 0
fi
"$0" --grandchild >/dev/null 2>&1 &
sleep 60
"""

# Records the bwrap probe's environment (the invocation whose command is true or /bin/true).
# Any later wrapped tool command exits without running, so the probe file is not overwritten.
BWRAP_STUB = """#!/usr/bin/python3
import os
import sys
from pathlib import Path
args = sys.argv[1:]
out = Path(__file__).resolve().parent.joinpath("bwrap.probe-env")
if args and args[-1] in ("true", "/bin/true") and not out.exists():
    lines = [f"{k}={v}" for k, v in sorted(os.environ.items())]
    out.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
raise SystemExit(0)
"""

GIT_PIN_STUB = """#!/usr/bin/python3
print("112114bwrapprobesentinelcommit")
"""


def _write_exe(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _overtime_tree(root: Path) -> Path:
    pkg = root / "node_modules" / "@ukanwat" / "overtime"
    (pkg / "dist").mkdir(parents=True)
    (pkg / "dist" / "bin.js").write_text("// stub\n", encoding="utf-8")
    (pkg / "package.json").write_text('{"version": "0.5.3"}\n', encoding="utf-8")
    return root


def _parent_env(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    for key in (
        "OVERTIME_DIR", "OVERTIME_NODE", "OVERTIME_VERSION",
        "FEST_BIN", "FEST_SHA256", "CAMP_SHA256",
        "SLOPTRIM_DIR", "SLOPTRIM_COMMIT",
        "PFY_XINTAKE_TIMEOUT",
    ):
        env.pop(key, None)
    env.update(SENTINELS)
    if _RECEIPTS is None:
        raise RuntimeError("PFY_SMOKE_RECEIPT_DIR is unset")
    env["PFY_SMOKE_RECEIPT_DIR"] = str(_RECEIPTS)
    return env


def _run(entry: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "examples/x-intake-local/smoke_112_114.py", "--entry", entry],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=60,
    )


def _receipt(entry: str) -> dict:
    path = Path(_RECEIPTS) / entry / "latest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _seen(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            out[key] = value
    return out


class XIntakeSmoke112114Tests(unittest.TestCase):
    def setUp(self) -> None:
        global _RECEIPTS
        self._receipt_tmp = tempfile.TemporaryDirectory(prefix="pfy-xintake-112-receipts-")
        self.addCleanup(self._receipt_tmp.cleanup)
        _RECEIPTS = Path(self._receipt_tmp.name)

    def tearDown(self) -> None:
        global _RECEIPTS
        _RECEIPTS = None

    def test_node_version_and_git_rev_parse_do_not_see_parent_sentinels(self) -> None:
        # Fail: node --version or sloptrim's git rev-parse inherits the parent env, so a planted
        # key is visible or HOME is still the parent HOME.
        # Recover: the child env is only PATH/HOME/TERM/LANG/NO_COLOR and HOME is a different temp dir.
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-112-env-") as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            with self.subTest("overtime node --version"):
                ot = _overtime_tree(root / "overtime")
                node = root / "node-stub"
                _write_exe(node, NODE_VERSION_STUB)
                env = _parent_env(home)
                env["OVERTIME_DIR"] = str(ot)
                env["OVERTIME_NODE"] = str(node)
                proc = _run("overtime", env)
                blob = proc.stdout + proc.stderr
                self.assertNotIn("Traceback", proc.stderr, blob)
                probe = root / "node.environ"
                self.assertTrue(probe.is_file(), blob)
                seen = _seen(probe.read_text(encoding="utf-8"))
                self.assertLessEqual(set(seen), ALLOW, sorted(set(seen) - ALLOW))
                for key, value in SENTINELS.items():
                    self.assertNotIn(key, seen)
                    self.assertNotIn(value, probe.read_text(encoding="utf-8"))
                self.assertNotEqual(Path(seen["HOME"]).resolve(), home.resolve())
            with self.subTest("sloptrim git rev-parse"):
                slop = root / "sloptrim" / "scripts"
                slop.mkdir(parents=True)
                (slop / "detect.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
                bindir = root / "bin"
                bindir.mkdir()
                _write_exe(bindir / "git", GIT_STUB)
                env = _parent_env(home)
                env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
                env["SLOPTRIM_DIR"] = str(root / "sloptrim")
                proc = _run("sloptrim", env)
                blob = proc.stdout + proc.stderr
                self.assertNotIn("Traceback", proc.stderr, blob)
                self.assertEqual(proc.returncode, 2, blob)
                probe = bindir / "git.environ"
                self.assertTrue(probe.is_file(), blob)
                seen = _seen(probe.read_text(encoding="utf-8"))
                self.assertLessEqual(set(seen), ALLOW, sorted(set(seen) - ALLOW))
                for key, value in SENTINELS.items():
                    self.assertNotIn(key, seen)
                    self.assertNotIn(value, probe.read_text(encoding="utf-8"))
                self.assertNotEqual(Path(seen["HOME"]).resolve(), home.resolve())

    def test_timeout_kills_grandchild_and_still_checks_real_home(self) -> None:
        # Fail: PFY_XINTAKE_TIMEOUT kills only the direct child, so the stub's grandchild is still
        # alive, or the timeout returns before the ~/overtime compare.
        # Recover: the grandchild is dead and the receipt reports that the real HOME changed.
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-112-gc-") as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            parent_ot = home / "overtime"
            marker = f"pfy-grandchild-112-{os.getpid()}"
            ot = _overtime_tree(root / "overtime-pkg")
            node = root / "node-stub"
            body = GRANDCHILD_STUB.replace("__PARENT_OT__", str(parent_ot)).replace("__MARKER__", marker)
            _write_exe(node, body)
            env = _parent_env(home)
            env["OVERTIME_DIR"] = str(ot)
            env["OVERTIME_NODE"] = str(node)
            env["PFY_XINTAKE_TIMEOUT"] = "1"
            left: list[str] = []
            try:
                proc = _run("overtime", env)
            finally:
                time.sleep(0.5)
                left = subprocess.run(
                    ["pgrep", "-f", marker], capture_output=True, text=True,
                ).stdout.split()
                for pid in left:
                    try:
                        os.kill(int(pid), 9)
                    except OSError:
                        pass
            blob = proc.stdout + proc.stderr
            self.assertNotIn("Traceback", proc.stderr, blob)
            self.assertEqual(proc.returncode, 1, blob)
            self.assertTrue((parent_ot / "marker").is_file(), blob)
            receipt = _receipt("overtime")
            self.assertIn("real HOME ~/overtime was created or changed", receipt.get("reason") or "", blob)
            self.assertEqual(left, [], "a forked tool grandchild outlived the smoke timeout")

    def test_bwrap_probe_drops_paid_keys_and_uses_temp_home(self) -> None:
        # Fail: bwrap_prefix's `bwrap ... true` inherits the parent env, so a planted paid key
        # is visible or HOME is still the operator HOME.
        # Recover: the probe child has none of PAID_KEYS and HOME is a different temp dir.
        loc = str(ROOT / "examples" / "x-intake-local")
        if loc not in sys.path:
            sys.path.insert(0, loc)
        from smoke import PAID_KEYS

        real_home = Path.home()
        paid = {key: f"pfy-fake-{key}" for key in PAID_KEYS}
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-112-bwrap-") as td:
            root = Path(td)
            operator = root / "operator-home"
            operator.mkdir()
            bindir = root / "bin"
            bindir.mkdir()
            _write_exe(bindir / "bwrap", BWRAP_STUB)
            _write_exe(bindir / "git", GIT_PIN_STUB)
            slop = root / "sloptrim" / "scripts"
            slop.mkdir(parents=True)
            (slop / "detect.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
            env = _parent_env(operator)
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            env["SLOPTRIM_DIR"] = str(root / "sloptrim")
            env["SLOPTRIM_COMMIT"] = "112114bwrapprobesentinelcommit"
            env.update(paid)
            proc = _run("sloptrim", env)
            blob = proc.stdout + proc.stderr
            self.assertNotIn("Traceback", proc.stderr, blob)
            probe = bindir / "bwrap.probe-env"
            self.assertTrue(probe.is_file(), blob)
            text = probe.read_text(encoding="utf-8")
            seen = _seen(text)
            leaked = [key for key, value in paid.items() if key in seen or value in text]
            self.assertEqual(leaked, [], blob)
            child_home = Path(seen["HOME"])
            self.assertNotEqual(child_home.resolve(), operator.resolve())
            self.assertNotEqual(child_home.resolve(), real_home.resolve())
            self.assertTrue(str(child_home).startswith(tempfile.gettempdir()))

    def test_node_ok_hanging_stub_on_path_reaps_grandchild(self) -> None:
        # Fail: node_ok's `node --version` uses subprocess.run, so a forked sleeper outlives the timeout.
        # Recover: node_ok returns false and that grandchild is dead.
        loc = str(ROOT / "examples" / "x-intake-local")
        if loc not in sys.path:
            sys.path.insert(0, loc)
        import smoke_112_114

        with tempfile.TemporaryDirectory(prefix="pfy-xintake-112-nodeok-") as td:
            root = Path(td)
            bindir = root / "bin"
            bindir.mkdir()
            pidfile = root / "grandchild.pid"
            _write_exe(bindir / "node", HANGING_NODE.replace("__PIDFILE__", str(pidfile)))
            found = shutil.which("node", path=str(bindir) + os.pathsep + os.environ.get("PATH", ""))
            self.assertEqual(found, str(bindir / "node"))
            previous = os.environ.get("PFY_XINTAKE_TIMEOUT")
            os.environ["PFY_XINTAKE_TIMEOUT"] = "0.4"
            ok, detail = True, ""
            try:
                ok, detail = smoke_112_114.node_ok(found)
            finally:
                if previous is None:
                    os.environ.pop("PFY_XINTAKE_TIMEOUT", None)
                else:
                    os.environ["PFY_XINTAKE_TIMEOUT"] = previous
                time.sleep(0.2)
                alive = _pid_alive(pidfile)
                if alive and pidfile.is_file():
                    try:
                        os.kill(int(pidfile.read_text(encoding="utf-8").strip()), 9)
                    except (OSError, ValueError):
                        pass
            self.assertTrue(pidfile.is_file(), "the node stub never forked its grandchild")
            self.assertFalse(ok, detail)
            self.assertIn("not runnable", detail)
            self.assertFalse(alive, "a node --version grandchild outlived node_ok")

    def test_overtime_timeout_reason_is_shared_text(self) -> None:
        # Fail: a timed-out `new` records "timeout after <s>s: <cmd>".
        # Recover: exit 1 and the receipt reason names the overtime step and 0.4s.
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-112-to-") as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            ot = _overtime_tree(root / "overtime-pkg")
            node = root / "node-stub"
            _write_exe(node, "#!/bin/sh\nif [ \"$1\" = --version ]; then echo v22.19.0; exit 0; fi\nsleep 30\n")
            env = _parent_env(home)
            env["OVERTIME_DIR"] = str(ot)
            env["OVERTIME_NODE"] = str(node)
            env["PFY_XINTAKE_TIMEOUT"] = "0.4"
            proc = _run("overtime", env)
            blob = proc.stdout + proc.stderr
            self.assertNotIn("Traceback", proc.stderr, blob)
            self.assertEqual(proc.returncode, 1, blob)
            self.assertFalse((home / "overtime").exists(), blob)
            self.assertEqual(_receipt("overtime").get("reason"), "new timeout after 0.4s", blob)

    def test_festival_timeout_reason_is_shared_text(self) -> None:
        # Fail: a timed-out fest --version records "timeout after <s>s: <cmd>" from main().
        # Recover: exit 1 and the receipt reason names the festival step and 0.4s.
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-112-fest-") as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            body = "#!/bin/sh\nsleep 30\n"
            fest, camp = root / "fest", root / "camp"
            _write_exe(fest, body)
            _write_exe(camp, body)

            def digest(path: Path) -> str:
                return hashlib.sha256(path.read_bytes()).hexdigest()

            env = _parent_env(home)
            env["FEST_BIN"] = str(fest)
            env["FEST_SHA256"] = digest(fest)
            env["CAMP_SHA256"] = digest(camp)
            env["PFY_XINTAKE_TIMEOUT"] = "0.4"
            proc = _run("festival", env)
            blob = proc.stdout + proc.stderr
            self.assertNotIn("Traceback", proc.stderr, blob)
            self.assertEqual(proc.returncode, 1, blob)
            self.assertEqual(_receipt("festival").get("reason"), "version timeout after 0.4s", blob)

    def test_overtime_daemon_stop_timeout_uses_shared_text(self) -> None:
        # Fail: a daemon-stop timeout is recorded as the bare word "timeout".
        # Recover: the step value is timeout_reason("overtime daemon stop").
        stub = r"""#!/bin/sh
if [ "$1" = --version ]; then echo v22.19.0; exit 0; fi
sub=$2
agent="$HOME/overtime/agents/smoke-agent"
case "$sub" in
  new)
    mkdir -p "$agent/.overtime"
    printf 'dailyBudgetUsd: 1\n' > "$agent/AGENT.md"
    printf '%s\n' '{"dailyBudgetUsd": 1, "protect": []}' > "$agent/.overtime/settings.json"
    printf '%s\n' '{"status": "idle"}' > "$agent/.overtime/state.json"
    ;;
  ls) echo smoke-agent ;;
  set)
    prot=${5#protect=}
    printf '%s\n' "$prot" > "$agent/.overtime/prot"
    printf '%s\n' "{\"dailyBudgetUsd\": 1, \"protect\": [\"$prot\"]}" > "$agent/.overtime/settings.json"
    setsid sh -c "sleep 0.2; printf '%s\n' '{\"dailyBudgetUsd\": 999}' > \"$agent/.overtime/settings.json\"" >/dev/null 2>&1 &
    ;;
  settings)
    prot=$(cat "$agent/.overtime/prot")
    echo "\$1 a day $prot"
    ;;
  daemon) sleep 30 ;;
esac
exit 0
"""
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-112-dstop-") as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            ot = _overtime_tree(root / "overtime-pkg")
            node = root / "node-stub"
            _write_exe(node, stub)
            env = _parent_env(home)
            env["OVERTIME_DIR"] = str(ot)
            env["OVERTIME_NODE"] = str(node)
            env["PFY_XINTAKE_TIMEOUT"] = "0.4"
            proc = _run("overtime", env)
            blob = proc.stdout + proc.stderr
            self.assertNotIn("Traceback", proc.stderr, blob)
            receipt = _receipt("overtime")
            stops = [s.get("daemon_stop") for s in receipt.get("steps") or [] if "daemon_stop" in s]
            self.assertEqual(stops, ["overtime daemon stop timeout after 0.4s"], blob + "\n" + str(receipt.get("reason")))

    def test_overtime_festival_sloptrim_receipts_are_ignored(self) -> None:
        for entry in ("overtime", "festival", "sloptrim"):
            rel = f"pipelines/smoke/{entry}/latest.json"
            ignored = subprocess.run(["git", "check-ignore", "-q", "--", rel], cwd=str(ROOT))
            self.assertEqual(ignored.returncode, 0, rel)
        tracked = subprocess.run(
            ["git", "check-ignore", "-q", "--", "pipelines/smoke/kolibri1/latest.json"], cwd=str(ROOT))
        self.assertEqual(tracked.returncode, 1)


def _pid_alive(pidfile: Path) -> bool:
    if not pidfile.is_file():
        return False
    try:
        pid = int(pidfile.read_text(encoding="utf-8").strip())
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except (OSError, ValueError):
        return False
    state = stat.rsplit(")", 1)[-1].split()[0]
    return state not in ("Z", "X")


if __name__ == "__main__":
    unittest.main()
