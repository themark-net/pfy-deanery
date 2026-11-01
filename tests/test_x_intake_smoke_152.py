"""Entry 152 smoke (Kanzo): a missing binary, a version mismatch and a bad timeout exit 2; a failing init, a missing
core MCP tool, a task the MCP server reports but never stores, a server that never replies (timeout, and it must not outlive the smoke), an export
without the task, a write outside --home, or a write into the real HOME FAILs; a correct stub PASSes, including one
that emits unrelated lines before its replies. The stub is a tiny Python `kanzo` (shebang = this interpreter) that
keeps the board in a JSON file under --home; receipts go to a temp dir."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/x-intake-local/smoke_152.py"

STUB = r'''
import json, os, pathlib, sys, time
a = sys.argv[1:]
if a[:1] in (["--version"], ["-V"]):
    print("kanzo " + K.get("version", "0.2.1")); sys.exit(0)
home = pathlib.Path(a[a.index("--home") + 1])
db = home / "kanzo.db"
if K.get("write_home"):
    (pathlib.Path(os.environ["HOME"]) / "kanzo").mkdir(exist_ok=True)
if K.get("touch_real"):
    try:
        pathlib.Path(K["touch_real"], "kanzo").mkdir(exist_ok=True)
    except OSError:
        pass
def load():
    return json.loads(db.read_text())
if a[0] == "init":
    if K.get("init_exit"):
        sys.exit(K["init_exit"])
    home.mkdir(parents=True, exist_ok=True)
    db.write_text(json.dumps({"projects": {}}))
    print("Kanzo data folder ready at %s" % home); sys.exit(0)
if a[0] == "export":
    board = load()
    if "-f" in a:
        print(json.dumps({"projects": [{"slug": s, "tasks": t} for s, t in board["projects"].items()]}))
    else:
        print("# Kanzo board")
        for s, ts in board["projects"].items():
            for t in ts:
                if not K.get("md_missing"):
                    print("#### %s#%d %s" % (s, 1, t["title"]))
    sys.exit(0)
tools = ["add_comment", "create_project", "create_task", "delete_task", "get_task", "link_repo",
         "list_projects", "list_tasks", "next_task", "update_task"]
if K.get("missing_tool"):
    tools.remove(K["missing_tool"])
def reply(i, res):
    if K.get("noise"):
        print(json.dumps({"jsonrpc": "2.0", "method": "notifications/message", "params": {}}))
        print("not json at all")
    print(json.dumps({"jsonrpc": "2.0", "id": i, "result": res}), flush=True)
def text(t):
    return {"content": [{"type": "text", "text": t}], "isError": False}
for line in sys.stdin:
    m = json.loads(line)
    if "id" not in m:
        continue
    if K.get("hang"):
        time.sleep(60)
    meth, p = m["method"], m.get("params", {})
    if meth == "initialize":
        reply(m["id"], {"serverInfo": {"name": "kanzo", "version": "0.2.1"}})
    elif meth == "tools/list":
        reply(m["id"], {"tools": [{"name": n} for n in tools]})
    else:
        board = load(); args = p["arguments"]
        if p["name"] == "create_project":
            board["projects"][args["slug"]] = []
            reply(m["id"], text("Created project %s." % args["slug"]))
        elif p["name"] == "create_task":
            if not K.get("drop_task"):
                board["projects"][args["project"]].append({"title": args["title"], "status": "todo"})
            reply(m["id"], text("Created %s#1 in todo: %s" % (args["project"], args["title"])))
        elif p["name"] == "list_tasks":
            ts = board["projects"].get(args["project"], [])
            reply(m["id"], text("\n".join("%s#1 [todo] %s" % (args["project"], t["title"]) for t in ts)))
        db.write_text(json.dumps(board))
sys.exit(0)
'''


def survivors_of(path: str) -> list[int]:
    """Live pids whose argv mentions the stub path; any found are killed so a failing test can't leak them."""
    found = []
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            argv = (d / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if path.encode() in argv:
            found.append(int(d.name))
            try:
                os.kill(int(d.name), 9)
            except OSError:
                pass
    return found


class Smoke152(unittest.TestCase):
    def run_smoke(self, knobs=None, env=None):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "realhome"
            real.mkdir()
            env2 = {"PATH": os.environ.get("PATH", ""), "HOME": str(real), "PFY_SMOKE_RECEIPT_DIR": str(td / "r")}
            if knobs is not None:
                k = dict(knobs)
                if k.get("touch_real"):
                    k["touch_real"] = str(real)
                stub = td / "kanzo"
                stub.write_text(f"#!{sys.executable}\nK = {k!r}\n" + STUB, encoding="utf-8")
                stub.chmod(0o755)
                env2["KANZO_BIN"] = str(stub)
            else:
                env2["KANZO_BIN"] = str(td / "missing")
            env2.update(env or {})
            p = subprocess.run([sys.executable, str(SCRIPT)], env=env2, capture_output=True, text=True, timeout=120)
            rec = json.loads((td / "r" / "latest.json").read_text())
            survivors = survivors_of(str(td / "kanzo"))
            self.assertEqual(survivors, [], "stub kanzo outlived the smoke (orphan)")
            return p.returncode, rec

    def test_pass(self):
        code, rec = self.run_smoke({})
        self.assertEqual(code, 0, rec)

    def test_noise_lines_before_replies_pass(self):
        code, rec = self.run_smoke({"noise": True})
        self.assertEqual(code, 0, rec)

    def test_missing_binary_exit_2(self):
        self.assertEqual(self.run_smoke(None)[0], 2)

    def test_version_pin_exit_2(self):
        code, rec = self.run_smoke({"version": "0.2.10"})
        self.assertEqual(code, 2)
        self.assertIn("version pin", rec["reason"])

    def test_bad_timeout_exit_2(self):
        self.assertEqual(self.run_smoke({}, {"PFY_XINTAKE_TIMEOUT": "soon"})[0], 2)

    def test_init_failure_fails(self):
        code, rec = self.run_smoke({"init_exit": 1})
        self.assertEqual(code, 1)
        self.assertIn("init_ok", rec["failed"])

    def test_missing_core_tool_fails(self):
        code, rec = self.run_smoke({"missing_tool": "next_task"})
        self.assertEqual(code, 1)
        self.assertEqual(rec["failed"], ["mcp_core_tools"])

    def test_task_not_stored_fails(self):
        code, rec = self.run_smoke({"drop_task": True})
        self.assertEqual(code, 1)
        for name in ("mcp_list_shows_task", "export_json_has_task", "export_md_has_task"):
            self.assertIn(name, rec["failed"])

    def test_markdown_export_without_task_fails(self):
        code, rec = self.run_smoke({"md_missing": True})
        self.assertEqual(code, 1)
        self.assertEqual(rec["failed"], ["export_md_has_task"])

    def test_server_hang_times_out_and_fails(self):
        code, rec = self.run_smoke({"hang": True}, {"PFY_XINTAKE_TIMEOUT": "2"})
        self.assertEqual(code, 1)
        self.assertTrue(any(f.startswith("mcp: no reply") for f in rec["failed"]), rec["failed"])

    def test_write_outside_home_flag_fails(self):
        code, rec = self.run_smoke({"write_home": True})
        self.assertEqual(code, 1)
        self.assertIn("data_only_under_home_flag", rec["failed"])

    def test_real_home_write_fails(self):
        # No bwrap on PATH, so the stub can reach the real HOME (bwrap's read-only bind would block it).
        code, rec = self.run_smoke({"touch_real": True}, {"PATH": "/nonexistent"})
        self.assertEqual(code, 1)
        self.assertIn("real_home_unchanged", rec["failed"])


if __name__ == "__main__":
    unittest.main()
