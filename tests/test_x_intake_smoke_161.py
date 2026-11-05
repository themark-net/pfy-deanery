"""Entry 161 smoke (agentgg): a missing node exits 2, a hang and a grandchild
are killed, no local model exits 2 after help, a loopback Ollama scan omits
--live-validate and any key, and the receipt is gitignored."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/x-intake-local/smoke_161.py"

CLI = r'''
import os, sys, time
from pathlib import Path
a = sys.argv[1:]
if K.get("orphan"):
    if os.fork() == 0:
        time.sleep(30)
        os._exit(0)
    os._exit(0)
if K.get("hang"):
    time.sleep(60)
if K.get("touch_real"):
    os.makedirs(os.path.join(K["touch_real"], ".agentgg"), exist_ok=True)
if "--version" in a:
    print(K.get("version", "0.1.29"))
    raise SystemExit(0)
if "--help" in a:
    print("Usage: agentgg")
    raise SystemExit(0)
if a and a[0] == "scan":
    Path(K["scan_mark"]).write_text("\n".join(a))
    if "--live-validate" in a or "--api-key" in a:
        raise SystemExit(3)
    if K.get("scan_fail"):
        print("scan failed", file=sys.stderr)
        raise SystemExit(1)
    print("scan finished")
    raise SystemExit(0)
raise SystemExit(2)
'''

NPM = r'''
import os, pathlib, sys
argv = sys.argv[1:]
prefix = pathlib.Path(argv[argv.index("--prefix") + 1])
home = pathlib.Path(os.environ["HOME"])
cache = pathlib.Path(os.environ["npm_config_cache"])
pathlib.Path(K["mark"]).write_text(str(home) + "\n" + str(cache) + "\n" + str(prefix) + "\n" + " ".join(argv))
bin_dir = prefix / "bin"
bin_dir.mkdir(parents=True, exist_ok=True)
cli = bin_dir / "agentgg"
cli.write_text("#!" + sys.executable + "\n" + K["cli"], encoding="utf-8")
cli.chmod(0o755)
raise SystemExit(0)
'''


def survivors_of(path: str) -> list[int]:
    found = []
    needle = path.encode()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if needle in argv or any(needle in part for part in argv):
            found.append(int(entry.name))
            try:
                os.kill(int(entry.name), 9)
            except OSError:
                pass
    return found


class _Tags(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?", 1)[0] != "/api/tags":
            self.send_response(404)
            self.end_headers()
            return
        body = b'{"models":[{"name":"fixture:test"}]}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


class Smoke161(unittest.TestCase):
    def run_smoke(self, knobs=None, env=None, npm=False, probe=None):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "realhome"
            real.mkdir()
            env2 = {
                "PATH": os.environ.get("PATH", ""),
                "HOME": str(real),
                "PFY_SMOKE_RECEIPT_DIR": str(td / "r"),
                "AGENTGG_PROBE_URL": probe or "http://127.0.0.1:9",
            }
            stub_path = td / "agentgg"
            scan_mark = td / "scan"
            mark = td / "mark"
            if npm:
                cli_body = "K = {'version': '0.1.29', 'scan_mark': %r}\n" % str(scan_mark) + CLI
                npm_path = td / "npm"
                npm_path.write_text(
                    f"#!{sys.executable}\nK = {{'mark': {str(mark)!r}, 'cli': {cli_body!r}}}\n" + NPM,
                    encoding="utf-8",
                )
                npm_path.chmod(0o755)
                env2["AGENTGG_NPM"] = str(npm_path)
                env2["AGENTGG_NODE"] = sys.executable
            elif knobs is not None:
                k = dict(knobs)
                k["scan_mark"] = str(scan_mark)
                if k.get("touch_real"):
                    k["touch_real"] = str(real)
                stub_path.write_text(f"#!{sys.executable}\nK = {k!r}\n" + CLI, encoding="utf-8")
                stub_path.chmod(0o755)
                env2["AGENTGG_BIN"] = str(stub_path)
            else:
                env2["AGENTGG_NODE"] = str(td / "missing-node")
            env2.update(env or {})
            proc = subprocess.run(
                [sys.executable, str(SCRIPT)], env=env2, capture_output=True, text=True, timeout=60,
            )
            receipt = json.loads((td / "r" / "agentgg" / "latest.json").read_text())
            survivors = survivors_of(str(stub_path))
            self.assertEqual(survivors, [], "agentgg outlived the smoke")
            scan_text = scan_mark.read_text() if scan_mark.exists() else None
            mark_text = mark.read_text() if mark.exists() else ""
            return proc.returncode, receipt, scan_text, mark_text

    def test_missing_node_exits_2(self):
        code, rec, _scan, _td = self.run_smoke(None)
        self.assertEqual(code, 2)
        self.assertIn("node is not available", rec["reason"])

    def test_hang_is_killed(self):
        code, rec, _scan, _td = self.run_smoke({"hang": True}, {"PFY_XINTAKE_TIMEOUT": "2"})
        self.assertEqual(code, 2, rec)
        self.assertIn("timeout after 2s", rec["reason"])

    def test_grandchild_does_not_survive(self):
        code, rec, _scan, _td = self.run_smoke({"orphan": True}, {"PFY_XINTAKE_TIMEOUT": "5"})
        self.assertEqual(code, 2, rec)

    def test_no_local_endpoint_exits_2(self):
        code, rec, scan, _td = self.run_smoke({})
        self.assertEqual(code, 2, rec)
        self.assertIn("no local Ollama", rec["reason"])
        self.assertIn("--live-validate", rec["reason"])
        self.assertEqual(rec["checks"]["scan"], "not_run")
        self.assertIsNone(scan)

    def test_loopback_scan_has_no_key_and_no_live_validate(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Tags)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            code, rec, scan, _td = self.run_smoke({}, probe=f"http://127.0.0.1:{port}")
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(code, 0, rec)
        argv = scan.splitlines()
        self.assertIn("--provider", argv)
        self.assertIn("ollama", argv)
        self.assertIn("--model", argv)
        self.assertIn("fixture:test", argv)
        self.assertNotIn("--live-validate", argv)
        self.assertNotIn("--api-key", argv)
        self.assertNotIn("app.agentgg.dev", " ".join(argv))
        self.assertEqual(rec["checks"]["scan"], "finished")

    def test_npm_scratch_stays_in_the_worktree(self):
        code, rec, _scan, mark_text = self.run_smoke(npm=True)
        self.assertEqual(code, 2, rec)
        home, cache, prefix, _argv = mark_text.splitlines()
        root = str((ROOT / "tmp").resolve())
        for place in (home, cache, prefix, rec["checks"]["npm_cache"]):
            self.assertTrue(str(place).startswith(root + "/"), place)

    def test_real_home_write_fails(self):
        code, rec, _scan, _td = self.run_smoke({"touch_real": True})
        self.assertEqual(code, 1, rec)
        self.assertIn("real_home_unchanged", rec["failed"])

    def test_bad_timeout_exits_2(self):
        self.assertEqual(self.run_smoke({}, {"PFY_XINTAKE_TIMEOUT": "soon"})[0], 2)

    def test_hosted_probe_is_refused(self):
        code, rec, _scan, _td = self.run_smoke({}, probe="https://app.agentgg.dev")
        self.assertEqual(code, 2, rec)
        self.assertIn("loopback", rec["reason"])

    def test_receipt_dir_is_gitignored(self):
        proc = subprocess.run(
            ["git", "check-ignore", "-q", "pipelines/smoke/agentgg/latest.json"],
            cwd=ROOT,
        )
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
