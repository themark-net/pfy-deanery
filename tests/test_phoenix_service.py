"""Behavior of scripts/phoenix_service.sh. No network and no systemctl.

Fail: a unit binds a non-loopback host, leaks a caller variable, or ignores
the pin file. Recovery: exit 2 with no unit, or read config/phoenix/version.txt.
Fail: status hangs or says up when nothing listens. Recovery: exit 1 quickly,
and accept / when /healthz is missing.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "phoenix_service.sh"
PIN_FILE = ROOT / "config" / "phoenix" / "version.txt"


class _Handler(BaseHTTPRequestHandler):
    routes: dict[str, tuple[int, bytes]] = {}

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        code, body = self.routes.get(path, (404, b""))
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        return


def _serve(routes: dict[str, tuple[int, bytes]]) -> ThreadingHTTPServer:
    handler = type("Routes", (_Handler,), {"routes": routes})
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    httpd._serve_thread = thread  # type: ignore[attr-defined]
    return httpd


def _stop(httpd: ThreadingHTTPServer) -> None:
    httpd.shutdown()
    thread = getattr(httpd, "_serve_thread", None)
    if thread is not None:
        thread.join(timeout=2)
    httpd.server_close()


class PhoenixServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(self.id().replace(".", "_"))
        base = ROOT / "tmp" / "phoenix-service-tests"
        base.mkdir(parents=True, exist_ok=True)
        self.tmp = Path(self._mkdtemp(base))
        self.home = self.tmp / "home"
        self.cache = self.tmp / "cache"
        self.state = self.tmp / "state"
        self.home.mkdir()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _mkdtemp(self, base: Path) -> str:
        import tempfile

        return tempfile.mkdtemp(prefix="phoenix-", dir=base)

    def env(self, **extra: str) -> dict[str, str]:
        out = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "PFY_TOOL_CACHE": str(self.cache),
            "PFY_STATE_DIR": str(self.state),
            "LANG": "C",
            "LC_ALL": "C",
        }
        out.update(extra)
        return out

    def run_script(self, *args: str, script: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(script or SCRIPT), *args],
            cwd=ROOT,
            env=env or self.env(),
            text=True,
            capture_output=True,
            timeout=8,
            check=False,
        )

    def test_unit_binds_loopback_and_keeps_caller_env_out(self) -> None:
        """Fail: either port is unbound, telemetry or bash stays on, or a caller
        variable is copied into the unit. Recovery: the printed unit names
        127.0.0.1, both ports, and the state dir, and omits the caller value."""
        secret = "caller-value-should-not-print"
        proc = self.run_script(
            "unit",
            env=self.env(PHOENIX_SECRET=secret, PFY_PHOENIX_HOST="127.0.0.1"),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = proc.stdout
        self.assertNotIn(secret, text)
        self.assertNotIn("PHOENIX_SECRET", text)
        self.assertIn("Environment=PHOENIX_HOST=127.0.0.1", text)
        self.assertIn("Environment=PHOENIX_PORT=6006", text)
        self.assertIn("Environment=PHOENIX_GRPC_PORT=4317", text)
        self.assertIn("Environment=PHOENIX_TELEMETRY_ENABLED=false", text)
        self.assertIn("Environment=PHOENIX_DISABLE_AGENT_ASSISTANT=true", text)
        self.assertIn("Environment=PHOENIX_AGENTS_DISABLE_BASH=true", text)
        self.assertIn("Environment=PHOENIX_ENABLE_MCP_SERVER=false", text)
        self.assertIn("Environment=PHOENIX_WORKING_DIR=%s/phoenix" % self.state, text)
        self.assertIn("NoNewPrivileges=yes", text)
        self.assertIn("WantedBy=default.target", text)
        self.assertIn("Restart=on-failure", text)
        self.assertNotIn("IPAddressDeny", text)
        self.assertNotIn("PrivateTmp", text)

    def test_refuses_non_loopback_host(self) -> None:
        """Fail: 0.0.0.0 or a LAN address still prints a unit. Recovery: exit 2
        and an empty stdout."""
        for host in ("0.0.0.0", "192.168.1.50"):
            with self.subTest(host=host):
                proc = self.run_script("unit", env=self.env(PFY_PHOENIX_HOST=host))
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertEqual(proc.stdout, "")
                self.assertNotIn("[Unit]", proc.stdout)
                self.assertNotIn("ExecStart", proc.stdout)
                self.assertIn("refusing host %s" % host, proc.stderr)

    def test_status_down_is_fast_and_up_on_healthz(self) -> None:
        """Fail: a closed port hangs or exits 0, or /healthz 200 exits 1.
        Recovery: exit 1 in under 5s, exit 0 when /healthz answers."""
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        closed = sock.getsockname()[1]
        sock.close()
        started = time.perf_counter()
        down = self.run_script("status", env=self.env(PFY_PHOENIX_PORT=str(closed)))
        elapsed = time.perf_counter() - started
        self.assertEqual(down.returncode, 1, down.stderr)
        self.assertLess(elapsed, 5, "status on a closed port took %.2fs" % elapsed)
        self.assertTrue(down.stdout.startswith("down "), down.stdout)

        httpd = _serve({"/healthz": (200, b"ok")})
        self.addCleanup(_stop, httpd)
        port = httpd.server_address[1]
        up = self.run_script("status", env=self.env(PFY_PHOENIX_PORT=str(port)))
        self.assertEqual(up.returncode, 0, up.stderr)
        self.assertTrue(up.stdout.startswith("up "), up.stdout)

    def test_status_falls_back_to_root_when_healthz_is_missing(self) -> None:
        """Fail: a 404 on /healthz is down even when / is up. Recovery: exit 0."""
        httpd = _serve({"/healthz": (404, b"missing"), "/": (200, b"ui")})
        self.addCleanup(_stop, httpd)
        port = httpd.server_address[1]
        proc = self.run_script("status", env=self.env(PFY_PHOENIX_PORT=str(port)))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(proc.stdout.startswith("up "), proc.stdout)

    def test_pin_is_single_sourced_and_read_by_unit_and_install(self) -> None:
        """Fail: 21.0.0 is copied into the script, or unit/install ignore the
        pin file. Recovery: one version file, and a relocated tree with a
        different pin is what both commands print."""
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("21.0.0", script)
        self.assertEqual(PIN_FILE.read_text(encoding="utf-8").strip(), "21.0.0")
        names = sorted(p.name for p in (ROOT / "config" / "phoenix").iterdir())
        self.assertEqual(names, ["version.txt"])

        tree = self.tmp / "tree"
        (tree / "scripts").mkdir(parents=True)
        (tree / "config" / "phoenix").mkdir(parents=True)
        copied = tree / "scripts" / "phoenix_service.sh"
        shutil.copy(SCRIPT, copied)
        copied.chmod(0o755)
        (tree / "config" / "phoenix" / "version.txt").write_text("0.0.7\n", encoding="utf-8")

        unit = self.run_script("unit", script=copied)
        self.assertEqual(unit.returncode, 0, unit.stderr)
        self.assertIn("arize-phoenix 0.0.7", unit.stdout)
        self.assertNotIn("21.0.0", unit.stdout)

        bindir = self.tmp / "bin"
        bindir.mkdir()
        log = self.tmp / "uv.log"
        uv = bindir / "uv"
        uv.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$*\" >> \"${UV_LOG:?}\"\n"
            "if [ \"$1\" = venv ]; then\n"
            "  dest=\n"
            "  for arg in \"$@\"; do dest=$arg; done\n"
            "  mkdir -p \"$dest/bin\"\n"
            "  cat > \"$dest/bin/python\" << 'EOF'\n"
            "#!/bin/sh\n"
            "verfile=$(dirname \"$0\")/installed-version\n"
            "cat \"$verfile\"\n"
            "EOF\n"
            "  chmod +x \"$dest/bin/python\"\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = pip ]; then\n"
            "  py= spec= prev=\n"
            "  for arg in \"$@\"; do\n"
            "    if [ \"$prev\" = --python ]; then py=$arg; fi\n"
            "    case $arg in arize-phoenix==*) spec=$arg ;; esac\n"
            "    prev=$arg\n"
            "  done\n"
            "  printf '%s\\n' \"${spec#arize-phoenix==}\" > \"$(dirname \"$py\")/installed-version\"\n"
            "  exit 0\n"
            "fi\n"
            "echo \"unexpected uv: $*\" >&2\n"
            "exit 1\n",
            encoding="utf-8",
        )
        uv.chmod(0o755)
        install = self.run_script(
            "install",
            script=copied,
            env=self.env(PATH=str(bindir) + os.pathsep + os.environ["PATH"], UV_LOG=str(log)),
        )
        self.assertEqual(install.returncode, 0, install.stderr)
        self.assertEqual(install.stdout.strip(), "0.0.7")
        self.assertIn("arize-phoenix==0.0.7", log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
