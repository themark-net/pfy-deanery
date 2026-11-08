"""Kenfold probe: a rejected secret is not a hit, and a down server still scores.

The child is eval/evq1107/kenfold/probe.py. Each test runs that script
against a stub kenfold and a stub rg in a temp dir. No network, no model,
no real kenfold binary, no podman.
"""

from __future__ import annotations

import importlib.util
import json
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "kenfold" / "probe.py"
RESULTS = ROOT / "eval" / "evq1107" / "kenfold" / "results.json"

KENFOLD_STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path
    args = sys.argv[1:]
    if args[:1] == ["version"]:
        sys.stdout.write("kenfold v0.1.1 (commit dfc18f9, built test)\\n")
        raise SystemExit(0)
    if args[:1] == ["migrate"]:
        if os.environ.get("KENFOLD_STUB_MIGRATE") == "fail":
            sys.stderr.write("database not reachable\\n")
            raise SystemExit(1)
        sys.stdout.write("schema version 8\\n")
        raise SystemExit(0)
    if args[:1] != ["mcp"]:
        sys.stderr.write("unexpected %s\\n" % args)
        raise SystemExit(2)
    store = Path(os.environ["KENFOLD_STUB_STORE"])
    agent = os.environ.get("KENFOLD_AGENT") or "unknown"

    def load():
        if not store.is_file():
            return []
        return json.loads(store.read_text(encoding="utf-8"))

    def save(rows):
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(json.dumps(rows), encoding="utf-8")

    def reply(obj):
        sys.stdout.write(json.dumps(obj) + "\\n")
        sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        if "id" not in msg:
            continue
        method = msg.get("method")
        if method == "initialize":
            reply({
                "jsonrpc": "2.0",
                "id": msg["id"],
                "result": {"serverInfo": {"name": "kenfold"}, "protocolVersion": "2025-03-26"},
            })
            continue
        if method != "tools/call":
            reply({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": "nope"}})
            continue
        params = msg.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name == "remember":
            content = arguments.get("content") or ""
            if "AKIA" in content:
                sys.stderr.write("rejected write containing a secret\\n")
                reply({
                    "jsonrpc": "2.0",
                    "id": msg["id"],
                    "result": {
                        "isError": True,
                        "content": [{"type": "text", "text": "rejected: AWS access key ID"}],
                    },
                })
                continue
            rows = load()
            rows.append({"content": content, "source_agent": agent, "status": "active"})
            save(rows)
            reply({
                "jsonrpc": "2.0",
                "id": msg["id"],
                "result": {
                    "isError": False,
                    "structuredContent": {"id": "m%s" % len(rows), "status": "active", "type": "semantic"},
                    "content": [{"type": "text", "text": "stored"}],
                },
            })
            continue
        if name == "recall":
            query = arguments.get("query") or ""
            hits = [row for row in load() if query and query in row["content"]]
            reply({
                "jsonrpc": "2.0",
                "id": msg["id"],
                "result": {"isError": False, "structuredContent": {"memories": hits}},
            })
            continue
        reply({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": name or ""}})
    raise SystemExit(0)
    """
)

RG_STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import sys
    needle = sys.argv[-1]
    if "KF1107_NOVEL_" in needle:
        raise SystemExit(1)
    sys.stdout.write("docs/example.md\\n")
    raise SystemExit(0)
    """
)


def _probe_module():
    spec = importlib.util.spec_from_file_location("kenfold_probe", PROBE)
    if spec is None or spec.loader is None:
        raise RuntimeError("probe missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class KenfoldProbeTests(unittest.TestCase):
    def _run(self, tmp: Path, extra_env: dict | None = None) -> dict:
        home = tmp / "home"
        scratch = tmp / "tmp"
        out = tmp / "out.json"
        home.mkdir()
        scratch.mkdir()
        kenfold = tmp / "kenfold"
        rg = tmp / "rg"
        kenfold.write_text(KENFOLD_STUB, encoding="utf-8")
        rg.write_text(RG_STUB, encoding="utf-8")
        kenfold.chmod(kenfold.stat().st_mode | stat.S_IEXEC)
        rg.chmod(rg.stat().st_mode | stat.S_IEXEC)
        before = RESULTS.read_bytes() if RESULTS.is_file() else None
        env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(
            [
                sys.executable,
                str(PROBE),
                "--out",
                str(out),
                "--kenfold-bin",
                str(kenfold),
                "--rg-bin",
                str(rg),
                "--home",
                str(home),
                "--tmp",
                str(scratch),
                "--cache",
                str(tmp / "cache"),
                "--no-server",
                "--skip-pins",
                "--skip-home",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        if before is None:
            self.assertFalse(RESULTS.exists())
        else:
            self.assertEqual(RESULTS.read_bytes(), before)
        self.assertTrue(out.is_file(), proc.stdout)
        text = out.read_text(encoding="utf-8")
        self.assertNotIn(_probe_module().shaped_secret(), text)
        self.assertNotIn("AKIA", text)
        return json.loads(text)

    def test_secret_reject_is_not_a_hit_and_recall_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kf-secret-") as raw:
            doc = self._run(Path(raw))
        self.assertTrue(doc["secret_rejected"])
        self.assertFalse(doc["secret_echoed"])
        self.assertFalse(doc["server_skipped"])
        self.assertEqual(doc["remember_ok"], 8)
        self.assertEqual(doc["recall_hits"], 8)
        self.assertEqual(doc["provenance_hits"], 8)
        self.assertEqual(doc["recall_second_hits"], 8)
        self.assertEqual(doc["agreement"], 8)
        self.assertEqual(doc["repo_recall_hits"], 0)
        self.assertEqual(doc["rg_repo_hits"], 8)
        self.assertEqual(doc["rg_novel_hits"], 0)
        self.assertEqual(doc["h1_graded_cases"], 0)
        names = [row["name"] for row in doc["overlap"]]
        self.assertIn("skill-up", names)
        self.assertIn("opencode-mem", names)

    def test_migrate_failure_records_skip_and_still_scores(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kf-down-") as raw:
            doc = self._run(Path(raw), {"KENFOLD_STUB_MIGRATE": "fail"})
        self.assertTrue(doc["server_skipped"])
        self.assertEqual(doc["migrate_exit"], 1)
        self.assertEqual(doc["remember_ok"], 0)
        self.assertEqual(doc["recall_hits"], 0)
        self.assertEqual(doc["agreement"], 0)
        self.assertFalse(doc["secret_rejected"])
        self.assertEqual(doc["rg_repo_hits"], 8)
        self.assertEqual(doc["rg_novel_hits"], 0)
        self.assertEqual(doc["h1_graded_cases"], 0)


if __name__ == "__main__":
    unittest.main()
