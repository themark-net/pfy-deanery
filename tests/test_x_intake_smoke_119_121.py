"""Entries 119-121 smokes: real-HOME writes FAIL, pins and a busy port exit 2, down timeout keeps the up failure.

Parent HOME is a temp dir this test owns. Children run under run_isolated with a different HOME, so a planted
real-HOME write uses that temp HOME's absolute path inside the stub. AgentDescent and TSA pass a bwrap writable
list; bwrap is chosen with shutil.which on the smoke process PATH (there is no disable switch), and a hit makes
the child root read-only outside the smoke temp dir. Those tests set PATH to the stub dir so the write can land.
"""
from __future__ import annotations

import json
import os
import shlex
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "examples/x-intake-local/smoke_119_121.py"
PORT = 7077
_RECEIPTS: Path | None = None


def _write_exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _env(home: Path, **extra: str) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    for key in list(env):
        if key.startswith(("AGENTDESCENT_", "KENFOLD_", "TSA_", "DOCKER_")) or key == "PFY_XINTAKE_TIMEOUT":
            env.pop(key, None)
    env.update(extra)
    if _RECEIPTS is None:
        raise RuntimeError("PFY_SMOKE_RECEIPT_DIR is unset")
    env["PFY_SMOKE_RECEIPT_DIR"] = str(_RECEIPTS)
    return env


def _run(entry: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, SCRIPT, "--entry", entry],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=90,
    )


def _receipt(entry: str) -> dict:
    path = Path(_RECEIPTS) / entry / "latest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _port_answers(port: int = PORT) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


def _git(repo: Path, *args: str) -> None:
    env = os.environ.copy()
    env.update({
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "pfy-smoke",
        "GIT_AUTHOR_EMAIL": "smoke@localhost",
        "GIT_COMMITTER_NAME": "pfy-smoke",
        "GIT_COMMITTER_EMAIL": "smoke@localhost",
    })
    subprocess.run(["git", "-C", str(repo), *args], env=env, check=True, capture_output=True, text=True, timeout=30)


def _kenfold_repo(path: Path, tag: str) -> Path:
    path.mkdir(parents=True)
    (path / "compose.yaml").write_text("name: pfy-kenfold-smoke\nservices: {}\n", encoding="utf-8")
    _git(path, "init", "-q")
    _git(path, "add", "compose.yaml")
    _git(path, "-c", "user.name=pfy-smoke", "-c", "user.email=smoke@localhost",
         "-c", "commit.gpgsign=false", "commit", "-q", "-m", "init")
    _git(path, "tag", tag)
    return path


def _python_stub(version: str) -> str:
    return f"#!/bin/sh\necho {shlex.quote(version)}\n"


def _demo_stub(home: Path | None, *, sleep_s: int = 0, log: Path | None = None) -> str:
    lines = ["#!/bin/sh"]
    if log is not None:
        lines.append(f"echo \"$@\" >> {shlex.quote(str(log))}")
    if sleep_s and home is not None:
        dest = home / ".agentdescent" / "runs"
        lines.append(f"mkdir -p {shlex.quote(str(dest))}")
        lines.append(f"echo planted > {shlex.quote(str(dest / 'planted'))}")
        lines.append(f"sleep {sleep_s}")
        lines.append("exit 0")
        return "\n".join(lines) + "\n"
    lines += [
        "dir=",
        "prev=",
        'for a in "$@"; do',
        '  if [ "$prev" = "--dir" ]; then dir=$a; fi',
        "  prev=$a",
        "done",
        'echo "held-out reward: 1.000"',
        "echo \"rules.md -> 'COLUMN: amount'\"",
        'mkdir -p "$dir/x/references"',
        "printf '%s\\n' \"COLUMN: id\" > \"$dir/x/references/rules.md\"",
    ]
    if home is not None:
        dest = home / ".agentdescent" / "runs"
        lines.append(f"mkdir -p {shlex.quote(str(dest))}")
        lines.append(f"echo planted > {shlex.quote(str(dest / 'planted'))}")
    if sleep_s:
        lines.append(f"sleep {sleep_s}")
    lines.append("exit 0")
    return "\n".join(lines) + "\n"


def _agentdescent_bin(bin_dir: Path, version: str, demo: str) -> Path:
    _write_exe(bin_dir / "python", _python_stub(version))
    binary = bin_dir / "agentdescent"
    _write_exe(binary, demo)
    return binary


def _tsa_stub(version: str, calls: Path, plant: str) -> str:
    return f"""#!/bin/sh
echo "$@" >> {shlex.quote(str(calls))}
if [ "$1" = "--version" ]; then
  echo "tree-sitter-analyzer {version}"
  exit 0
fi
{plant}echo '{{"methods":[{{"name":"tax"}},{{"name":"total"}}]}}'
"""


def _tsa_bins(bin_dir: Path, version: str, calls: Path, home: Path | None) -> Path:
    plant = ""
    if home is not None:
        dest = home / ".tsa" / "sessions"
        plant = f"mkdir -p {shlex.quote(str(dest))}\necho '{{}}' > {shlex.quote(str(dest / 'x.json'))}\n"
    _write_exe(bin_dir / "tree-sitter-analyzer", _tsa_stub(version, calls, plant))
    _write_exe(bin_dir / "miswire-audit", """#!/bin/sh
echo "python:3 javascript:1"
echo "Tree-sitter Analyzer mis-wires 0"
""")
    return bin_dir / "tree-sitter-analyzer"


def _docker_stub(path: Path, calls: Path, cases: str) -> None:
    _write_exe(path, f"""#!/bin/sh
echo "$@" >> {shlex.quote(str(calls))}
case " $* " in
{cases}esac
exit 0
""")


def _up_writes_home(home: Path) -> str:
    dest = home / ".local" / "state" / "kenfold"
    return f"""  *" version "*) exit 0 ;;
  *" up "*)
    mkdir -p {shlex.quote(str(dest))}
    echo planted > {shlex.quote(str(dest / "x"))}
    exit 0 ;;
  *" exec "*) exit 0 ;;
  *" down "*) exit 0 ;;
"""


def _up_fails_down_sleeps() -> str:
    return """  *" version "*) exit 0 ;;
  *" up "*) exit 1 ;;
  *" down "*) sleep 30; exit 0 ;;
"""


class _OkHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args: object) -> None:
        return


class XIntakeSmoke119121Tests(unittest.TestCase):
    def setUp(self) -> None:
        global _RECEIPTS
        self._receipt_tmp = tempfile.TemporaryDirectory(prefix="pfy-xintake-119-receipts-")
        self.addCleanup(self._receipt_tmp.cleanup)
        _RECEIPTS = Path(self._receipt_tmp.name)

    def tearDown(self) -> None:
        global _RECEIPTS
        _RECEIPTS = None

    def test_agentdescent_real_home_write_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-119-") as td:
            home, bindir = Path(td, "home"), Path(td, "bin")
            home.mkdir()
            binary = _agentdescent_bin(bindir, "0.5.1", _demo_stub(home))
            p = _run("agentdescent", _env(home, PATH=str(bindir), AGENTDESCENT_BIN=str(binary)))
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertNotIn("Traceback", p.stdout)
            self.assertIs(_receipt("agentdescent")["checks"]["real_home_untouched"], False)
            self.assertTrue((home / ".agentdescent" / "runs" / "planted").is_file())

    def test_agentdescent_clean_passes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-119-") as td:
            home, bindir = Path(td, "home"), Path(td, "bin")
            home.mkdir()
            binary = _agentdescent_bin(bindir, "0.5.1", _demo_stub(None))
            p = _run("agentdescent", _env(home, PATH=str(bindir), AGENTDESCENT_BIN=str(binary)))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertNotIn("Traceback", p.stdout)
            self.assertIs(_receipt("agentdescent")["checks"]["real_home_untouched"], True)

    def test_agentdescent_timeout_keeps_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-119-") as td:
            home, bindir = Path(td, "home"), Path(td, "bin")
            home.mkdir()
            binary = _agentdescent_bin(bindir, "0.5.1", _demo_stub(home, sleep_s=30))
            p = _run("agentdescent", _env(
                home, PATH=str(bindir), AGENTDESCENT_BIN=str(binary), PFY_XINTAKE_TIMEOUT="2"))
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertNotIn("Traceback", p.stdout)
            receipt = _receipt("agentdescent")
            self.assertIs(receipt["checks"]["real_home_untouched"], False)
            self.assertIn("timeout", receipt["reason"].lower())
            self.assertIn("real HOME", receipt["reason"])

    def test_agentdescent_wrong_version_exits_2(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-119-") as td:
            home, bindir = Path(td, "home"), Path(td, "bin")
            home.mkdir()
            calls = Path(td, "calls")
            binary = _agentdescent_bin(bindir, "0.4.0", _demo_stub(None, log=calls))
            p = _run("agentdescent", _env(home, PATH=str(bindir), AGENTDESCENT_BIN=str(binary)))
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertNotIn("Traceback", p.stdout)
            receipt = _receipt("agentdescent")
            self.assertIn("0.4.0", receipt["reason"])
            self.assertIn("version", receipt["reason"])
            text = calls.read_text(encoding="utf-8") if calls.exists() else ""
            self.assertNotIn("demo", text)

    def test_tsa_real_home_write_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-121-") as td:
            home, bindir = Path(td, "home"), Path(td, "bin")
            home.mkdir()
            calls = Path(td, "calls")
            binary = _tsa_bins(bindir, "2.2.0", calls, home)
            p = _run("tsa", _env(home, PATH=str(bindir), TSA_BIN=str(binary)))
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertNotIn("Traceback", p.stdout)
            self.assertIs(_receipt("tsa")["checks"]["real_home_untouched"], False)
            self.assertTrue((home / ".tsa" / "sessions" / "x.json").is_file())

    def test_tsa_wrong_version_exits_2(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-121-") as td:
            home, bindir = Path(td, "home"), Path(td, "bin")
            home.mkdir()
            calls = Path(td, "calls")
            binary = _tsa_bins(bindir, "1.0.0", calls, None)
            p = _run("tsa", _env(home, PATH=str(bindir), TSA_BIN=str(binary)))
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertNotIn("Traceback", p.stdout)
            receipt = _receipt("tsa")
            self.assertIn("1.0.0", receipt["reason"])
            self.assertIn("2.2.0", receipt["reason"])
            text = calls.read_text(encoding="utf-8") if calls.exists() else ""
            self.assertNotIn("structure", text)

    def test_kenfold_real_home_write_fails(self) -> None:
        if _port_answers():
            self.skipTest("127.0.0.1:7077 is already answering")
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-120-") as td:
            home = Path(td, "home")
            home.mkdir()
            repo = _kenfold_repo(Path(td, "kenfold"), "v0.1.1")
            calls, docker = Path(td, "calls"), Path(td, "docker")
            _docker_stub(docker, calls, _up_writes_home(home))
            p = _run("kenfold", _env(
                home, KENFOLD_DIR=str(repo), KENFOLD_COMMIT="skip", DOCKER_BIN=str(docker),
                PFY_XINTAKE_TIMEOUT="3"))
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertNotIn("Traceback", p.stdout)
            self.assertIs(_receipt("kenfold")["checks"]["real_home_untouched"], False)
            self.assertTrue((home / ".local" / "state" / "kenfold" / "x").is_file())

    def test_kenfold_down_timeout_keeps_up_failure(self) -> None:
        if _port_answers():
            self.skipTest("127.0.0.1:7077 is already answering")
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-120-") as td:
            home = Path(td, "home")
            home.mkdir()
            repo = _kenfold_repo(Path(td, "kenfold"), "v0.1.1")
            calls, docker = Path(td, "calls"), Path(td, "docker")
            _docker_stub(docker, calls, _up_fails_down_sleeps())
            p = _run("kenfold", _env(
                home, KENFOLD_DIR=str(repo), KENFOLD_COMMIT="skip", DOCKER_BIN=str(docker),
                PFY_XINTAKE_TIMEOUT="2"))
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertNotIn("Traceback", p.stdout)
            receipt = _receipt("kenfold")
            self.assertEqual(receipt["reason"], "docker compose up failed")
            self.assertIn("down", receipt["down_reason"])

    def test_kenfold_wrong_tag_exits_2(self) -> None:
        if _port_answers():
            self.skipTest("127.0.0.1:7077 is already answering")
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-120-") as td:
            home = Path(td, "home")
            home.mkdir()
            repo = _kenfold_repo(Path(td, "kenfold"), "v0.1.0")
            docker = Path(td, "docker")
            _docker_stub(docker, Path(td, "calls"), '  *" version "*) exit 0 ;;\n')
            p = _run("kenfold", _env(home, KENFOLD_DIR=str(repo), DOCKER_BIN=str(docker)))
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertNotIn("Traceback", p.stdout)
            receipt = _receipt("kenfold")
            self.assertEqual(receipt["ref"], "v0.1.0")
            self.assertIn("v0.1.1", receipt["reason"])

    def test_kenfold_commit_mismatch_exits_2(self) -> None:
        if _port_answers():
            self.skipTest("127.0.0.1:7077 is already answering")
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-120-") as td:
            home = Path(td, "home")
            home.mkdir()
            repo = _kenfold_repo(Path(td, "kenfold"), "v0.1.1")
            docker = Path(td, "docker")
            _docker_stub(docker, Path(td, "calls"), '  *" version "*) exit 0 ;;\n')
            p = _run("kenfold", _env(home, KENFOLD_DIR=str(repo), DOCKER_BIN=str(docker)))
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertNotIn("Traceback", p.stdout)
            receipt = _receipt("kenfold")
            self.assertEqual(receipt["ref"], "v0.1.1")
            self.assertIn("dfc18f9f", receipt["reason"])
            self.assertIn("commit", receipt["reason"])

    def test_kenfold_missing_docker_exits_2(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-120-") as td:
            home = Path(td, "home")
            home.mkdir()
            repo = Path(td, "kenfold")
            repo.mkdir()
            (repo / "compose.yaml").write_text("services: {}\n", encoding="utf-8")
            self.assertFalse((home / "DEVELOP/pfy-mentat/tmp/docker/docker").exists())
            empty = Path(td, "emptybin")
            empty.mkdir()  # PATH with no docker, even on hosts that have one in /usr/bin
            p = _run("kenfold", _env(home, PATH=str(empty), KENFOLD_DIR=str(repo)))
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertNotIn("Traceback", p.stdout)
            self.assertIn("docker", _receipt("kenfold")["reason"])

    def test_kenfold_busy_port_exits_2(self) -> None:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", PORT), _OkHandler)
        except OSError:
            self.skipTest("127.0.0.1:7077 already bound")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            deadline = time.time() + 2
            while time.time() < deadline and not _port_answers():
                time.sleep(0.05)
            if not _port_answers():
                self.fail("test http.server did not accept connections on 127.0.0.1:7077")
            with tempfile.TemporaryDirectory(prefix="pfy-xintake-120-") as td:
                home = Path(td, "home")
                home.mkdir()
                repo = Path(td, "kenfold")
                repo.mkdir()
                (repo / "compose.yaml").write_text("services: {}\n", encoding="utf-8")
                calls, docker = Path(td, "calls"), Path(td, "docker")
                _docker_stub(docker, calls, '  *" up "*) exit 0 ;;\n')
                p = _run("kenfold", _env(home, KENFOLD_DIR=str(repo), DOCKER_BIN=str(docker)))
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertNotIn("Traceback", p.stderr)
                self.assertNotIn("Traceback", p.stdout)
                self.assertIn("7077", _receipt("kenfold")["reason"])
                text = calls.read_text(encoding="utf-8") if calls.exists() else ""
                self.assertNotIn(" up ", f" {text} ")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_receipts_gitignored(self) -> None:
        for entry in ("agentdescent", "kenfold", "tsa"):
            rel = f"pipelines/smoke/{entry}/latest.json"
            ignored = subprocess.run(["git", "check-ignore", "-q", "--", rel], cwd=str(ROOT), timeout=30)
            self.assertEqual(ignored.returncode, 0, rel)


if __name__ == "__main__":
    unittest.main()
