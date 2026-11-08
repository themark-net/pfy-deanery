"""Charlotte probe: hidden controls, a bad id, and a server that ignores EOF.

The child is eval/evq1107/charlotte/probe.py. Each test runs that script
against a stub MCP server in a temp dir. No network, no browser, no install.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "charlotte" / "probe.py"
RESULTS = ROOT / "eval" / "evq1107" / "charlotte" / "results.json"

FIXTURE = """<!doctype html><html><head><meta charset=utf-8><title>pfy</title></head><body>
<nav>
  <button type=button class="navbtn on">Loop</button>
  <button type=button style=display:none>Org</button>
</nav>
<section class="view on" id=view-loop>
  <button hidden>Nope</button>
  <input type=text id=q>
  <button type=button id=btnlaunchsess>Launch session</button>
</section>
<section class=view id=view-attach>
  <input type=text id=hiddenq>
  <button type=button id=att-grok>Attach grok</button>
</section>
<button type=button id=after>After</button>
</body></html>
"""

STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, signal, subprocess, sys, time
    from pathlib import Path

    HERE = Path(__file__).resolve().parent
    ME = Path(__file__)
    MODE = ME.with_suffix(".mode").read_text(encoding="utf-8").strip()
    STARTS = ME.with_suffix(".starts")
    with STARTS.open("a", encoding="utf-8") as handle:
        handle.write(" ".join(sys.argv) + "\\n")

    def env_dump():
        ME.with_suffix(".env").write_text(json.dumps({
            "HOME": os.environ.get("HOME"),
            "XDG_CONFIG_HOME": os.environ.get("XDG_CONFIG_HOME"),
            "TMPDIR": os.environ.get("TMPDIR"),
            "PUPPETEER_SKIP_DOWNLOAD": os.environ.get("PUPPETEER_SKIP_DOWNLOAD"),
            "CANARY": os.environ.get("CHARLOTTE_CANARY"),
        }), encoding="utf-8")

    if MODE == "sandbox" and "--no-sandbox" not in sys.argv:
        SERVE = False
    else:
        SERVE = True

    if SERVE and MODE in ("ok", "hang", "sandbox"):
        env_dump()
        orphan = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
        ME.with_suffix(".orphan").write_text(str(orphan.pid), encoding="utf-8")

    def reply(ident, result, is_error=False):
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": ident, "result": result}) + "\\n")
        sys.stdout.flush()

    def tool(body, is_error=False):
        return {
            "content": [{"type": "text", "text": body if isinstance(body, str) else json.dumps(body)}],
            "isError": is_error,
        }

    ELEMENTS = [
        {"id": "btn-loop", "type": "button", "label": "Loop"},
        {"id": "btn-launch", "type": "button", "label": "Launch session"},
        {"id": "btn-grok", "type": "button", "label": "Attach grok"},
        {"id": "btn-after", "type": "button", "label": "After"},
    ]

    def on_term(signum, frame):
        ME.with_suffix(".how").write_text("term", encoding="utf-8")
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, on_term)

    core = [
        "charlotte_click", "charlotte_find", "charlotte_navigate", "charlotte_observe",
        "charlotte_submit", "charlotte_tools", "charlotte_type",
    ]
    if "--profile" not in sys.argv or "core" not in sys.argv:
        core = core + ["charlotte_screenshot"]

    while True:
        line = sys.stdin.readline()
        if not line:
            if MODE == "hang":
                signal.pause()
            raise SystemExit(0)
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if "id" not in msg:
            continue
        method = msg.get("method")
        if MODE == "die" and method == "tools/call":
            raise SystemExit(0)
        if MODE == "sandbox" and "--no-sandbox" not in sys.argv and method == "tools/call":
            sys.stderr.write("No usable sandbox\\n")
            sys.stderr.flush()
            raise SystemExit(1)
        if method == "initialize":
            reply(msg["id"], {"serverInfo": {"name": "charlotte", "version": "0.8.0"}})
            continue
        if method == "tools/list":
            reply(msg["id"], {"tools": [{"name": name} for name in core]})
            continue
        params = msg.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == "charlotte_navigate":
            ME.with_suffix(".url").write_text(str(args.get("url") or ""), encoding="utf-8")
            body = {"title": "pfy", "interactive_summary": {"total": 3},
                    "structure": {"headings": [{"text": "LOOP"}]}}
            reply(msg["id"], tool(body))
            continue
        if name == "charlotte_observe":
            view = args.get("view") or "default"
            detail = args.get("detail") or "summary"
            if view == "tree":
                reply(msg["id"], tool("button\\nbutton\\n"))
                continue
            if view == "tree-labeled":
                reply(msg["id"], tool("button Loop\\nbutton Launch session\\n"))
                continue
            if detail == "minimal":
                body = {"title": "pfy", "interactive_summary": {"total": 3},
                        "structure": {"headings": [{"text": "LOOP"}]}}
            elif detail == "full":
                body = {"title": "pfy", "interactive": ELEMENTS,
                        "structure": {"full_content": "LOOP Launch session", "headings": [{"text": "LOOP"}]}}
            else:
                body = {"title": "pfy", "interactive": ELEMENTS}
            reply(msg["id"], tool(body))
            continue
        if name == "charlotte_find":
            text = str(args.get("text") or "").lower()
            found = [row for row in ELEMENTS if text in row["label"].lower()]
            reply(msg["id"], tool({"elements": found}))
            continue
        if name == "charlotte_click" and args.get("element_id") == "btn-000000":
            reply(msg["id"], tool({
                "error": {"code": "ELEMENT_NOT_FOUND", "message": "Unknown element",
                          "suggestion": "did you mean btn-launch"},
            }, is_error=True))
            continue
        reply(msg["id"], tool({"ok": True}))
    """
)


class CharlotteProbeTests(unittest.TestCase):
    def _tmp(self) -> Path:
        path = Path(tempfile.mkdtemp(prefix="charlotte-probe-"))
        self.addCleanup(shutil.rmtree, path, True)
        return path

    def _run(self, tmp: Path, mode: str, **extra: str) -> subprocess.CompletedProcess[str]:
        home = tmp / "home"
        scratch = tmp / "scratch"
        page_dir = tmp / "page"
        repo = tmp / "repo"
        prefix = tmp / "prefix"
        package = prefix / "node_modules" / "@ticktockbent" / "charlotte"
        real_home = tmp / "real-home"
        for path in (home, scratch, page_dir, repo, package, real_home):
            path.mkdir(parents=True)
        version = extra.get("version", "0.8.0")
        (package / "package.json").write_text(
            json.dumps({"name": "@ticktockbent/charlotte", "version": version}),
            encoding="utf-8",
        )
        page = page_dir / "index.html"
        page.write_text(FIXTURE, encoding="utf-8")
        if extra.get("outside"):
            page = tmp / "outside.html"
            page.write_text(FIXTURE, encoding="utf-8")
        server = tmp / "server.py"
        server.write_text(STUB, encoding="utf-8")
        server.chmod(server.stat().st_mode | stat.S_IEXEC)
        server.with_suffix(".mode").write_text(mode, encoding="utf-8")
        if extra.get("plant_tauri"):
            binary = repo / "gui/operator/src-tauri/target/release/pfy-operator"
            binary.parent.mkdir(parents=True)
            binary.write_text("x", encoding="utf-8")
        if extra.get("plant_chrome"):
            (scratch / "com.google.Chrome.leftover").mkdir()
        tarball = tmp / "charlotte.tgz"
        if extra.get("bad_tarball"):
            tarball.write_bytes(b"not-the-package")
        out = tmp / "out.json"
        cmd = [
            sys.executable,
            str(PROBE),
            "--prefix", str(prefix),
            "--page", str(page),
            "--page-dir", str(page_dir),
            "--repo", str(repo),
            "--out", str(out),
            "--home", str(home),
            "--tmp", str(scratch),
            "--node", sys.executable,
            "--server", str(server),
            "--chrome", str(server),
            "--skip-ax",
        ]
        if extra.get("bad_tarball"):
            cmd.extend(["--tarball", str(tarball)])
        env = os.environ.copy()
        env["HOME"] = str(real_home)
        env["CHARLOTTE_CANARY"] = "pfy-canary-not-a-secret"
        self.addCleanup(self._reap, server.with_suffix(".orphan"))
        before = RESULTS.read_bytes() if RESULTS.exists() else None
        done = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30, check=False)
        after = RESULTS.read_bytes() if RESULTS.exists() else None
        self.assertEqual(before, after)
        done.out_path = out  # type: ignore[attr-defined]
        done.server = server  # type: ignore[attr-defined]
        done.home = home  # type: ignore[attr-defined]
        done.real_home = real_home  # type: ignore[attr-defined]
        done.page = page_dir / "index.html"  # type: ignore[attr-defined]
        return done

    def _reap(self, pid_path: Path) -> None:
        if not pid_path.is_file():
            return
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except ValueError:
            return
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            return

    def _data(self, done: subprocess.CompletedProcess[str]) -> dict:
        path = done.out_path  # type: ignore[attr-defined]
        self.assertTrue(path.is_file(), done.stderr)
        return json.loads(path.read_text(encoding="utf-8"))

    def _starts(self, done: subprocess.CompletedProcess[str]) -> list[str]:
        path = done.server.with_suffix(".starts")  # type: ignore[attr-defined]
        if not path.is_file():
            return []
        return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _assert_dead(self, done: subprocess.CompletedProcess[str]) -> None:
        path = done.server.with_suffix(".orphan")  # type: ignore[attr-defined]
        self.assertTrue(path.is_file(), self._starts(done))
        pid = int(path.read_text(encoding="utf-8").strip())
        for _ in range(50):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.05)
        self.fail("orphan %s still alive" % pid)

    def test_bad_tarball_does_not_start(self) -> None:
        done = self._run(self._tmp(), "ok", bad_tarball="1")
        self.assertEqual(done.returncode, 2, done.stderr)
        data = self._data(done)
        self.assertFalse(data["ok"])
        self.assertIn("sha256", data["reason"])
        self.assertEqual(self._starts(done), [])

    def test_wrong_version_does_not_start(self) -> None:
        done = self._run(self._tmp(), "ok", version="9.9.9")
        self.assertEqual(done.returncode, 2, done.stderr)
        data = self._data(done)
        self.assertFalse(data["ok"])
        self.assertIn("9.9.9", data["reason"])
        self.assertEqual(self._starts(done), [])
        self.assertFalse(done.server.with_suffix(".env").exists())  # type: ignore[attr-defined]

    def test_refuses_page_outside_dir(self) -> None:
        done = self._run(self._tmp(), "ok", outside="1")
        self.assertEqual(done.returncode, 2, done.stderr)
        data = self._data(done)
        self.assertIn("outside", data["reason"])
        self.assertEqual(self._starts(done), [])

    def test_summary_agreement_bad_id_and_isolated_env(self) -> None:
        done = self._run(self._tmp(), "ok", plant_tauri="1", plant_chrome="1")
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
        data = self._data(done)
        self.assertTrue(data["ok"])
        self.assertEqual(data["visible_expected"], ["After", "Launch session", "Loop"])
        self.assertEqual(data["visible_found"], 3)
        self.assertEqual(data["agreement"], 1.0)
        self.assertEqual(data["hidden_leaked"], ["Attach grok"])
        self.assertEqual(data["hidden_leaked_count"], 1)
        self.assertEqual(data["extra_labels"], [])
        self.assertNotIn("Nope", data["visible_expected"])
        self.assertNotIn("Org", data["visible_expected"])
        self.assertFalse(data["calls"]["navigate"]["has_ids"])
        self.assertEqual(data["calls"]["navigate"]["interactive_total"], 3)
        self.assertFalse(data["calls"]["minimal"]["has_ids"])
        self.assertFalse(data["calls"]["tree"]["has_launch"])
        self.assertTrue(data["calls"]["tree_labeled"]["has_launch"])
        self.assertTrue(data["ids_stable"])
        self.assertTrue(data["find_matches_summary"])
        self.assertTrue(data["server_survived_bad_id"])
        self.assertTrue(data["calls"]["bad_click"]["is_error"])
        self.assertEqual(data["calls"]["bad_click"]["code"], "ELEMENT_NOT_FOUND")
        self.assertEqual(data["tools_exact_core"], True)
        self.assertEqual(data["sandbox"], "on")
        self.assertEqual(data["sandbox_attempts"], 1)
        self.assertEqual(data["stopped"], "eof")
        self.assertEqual(data["tauri_binaries"], 1)
        self.assertEqual(data["profiles_left"], ["com.google.Chrome.leftover"])
        self.assertTrue(data["page_url_in_scratch"])
        url = done.server.with_suffix(".url").read_text(encoding="utf-8")  # type: ignore[attr-defined]
        self.assertIn("/site/index.html", url)
        self.assertNotIn("/page/", url)
        self.assertTrue(url.startswith("file:"))
        env = json.loads(done.server.with_suffix(".env").read_text(encoding="utf-8"))  # type: ignore[attr-defined]
        self.assertEqual(Path(env["HOME"]).resolve(), done.home.resolve())  # type: ignore[attr-defined]
        self.assertNotEqual(Path(env["HOME"]).resolve(), done.real_home.resolve())  # type: ignore[attr-defined]
        self.assertTrue(env["XDG_CONFIG_HOME"].startswith(str(done.home)))  # type: ignore[attr-defined]
        self.assertEqual(env["PUPPETEER_SKIP_DOWNLOAD"], "1")
        self.assertIsNone(env["CANARY"])
        self.assertEqual((done.page).read_text(encoding="utf-8"), FIXTURE)  # type: ignore[attr-defined]
        self._assert_dead(done)

    def test_eof_hang_is_sigterm_and_orphan_dies(self) -> None:
        done = self._run(self._tmp(), "hang")
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
        data = self._data(done)
        self.assertEqual(data["stopped"], "term")
        self.assertEqual(data["tauri_binaries"], 0)
        how = done.server.with_suffix(".how").read_text(encoding="utf-8")  # type: ignore[attr-defined]
        self.assertEqual(how, "term")
        self._assert_dead(done)

    def test_sandbox_refusal_retries_once(self) -> None:
        done = self._run(self._tmp(), "sandbox")
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
        data = self._data(done)
        self.assertTrue(data["ok"])
        self.assertEqual(data["sandbox"], "off")
        self.assertEqual(data["sandbox_attempts"], 2)
        self.assertIn("No usable sandbox", data["sandbox_error"])
        self.assertEqual(data["agreement"], 1.0)
        starts = self._starts(done)
        self.assertEqual(len(starts), 2)
        self.assertNotIn("--no-sandbox", starts[0])
        self.assertIn("--no-sandbox", starts[1])
        self._assert_dead(done)

    def test_dead_server_is_not_a_pass(self) -> None:
        done = self._run(self._tmp(), "die")
        self.assertEqual(done.returncode, 1, done.stderr + done.stdout)
        data = self._data(done)
        self.assertFalse(data["ok"])
        self.assertNotIn("agreement", data)
        self.assertEqual(len(self._starts(done)), 1)
        self.assertFalse(done.server.with_suffix(".orphan").exists())  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
