"""Advisory MCP and package scan. Stubs stand in for bumblebee. No network and no real binary.

How it fails and how we recover:
- a root of $HOME or a home config directory exits 2 and does not run the scanner; an explicit project path then exits 0
- a scanner that echoes a config value exits 1 with the value removed; a clean stub then exits 0
- a missing binary, a pinned missing binary, or unreadable ndjson exits 2; a cache stub then exits 0
- a git selector still exits 2 when the binary is missing, then exits 1 once a clean stub is present; a local command then exits 0
- a plaintext env value is named by key and never printed; a harmless env value then exits 0
- a symlinked MCP file is not read; a real clean file then exits 0
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pfy_mcp_scan.py"

TOKEN = "FAKE_TOKEN_PLACEHOLDER"
SHORT = "abc123"
GIT_ARG = "github:evil-example/mcp-server"

CLEAN_BODY = r"""
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
Path(os.environ["STUB_ARGV"]).write_text(json.dumps({
    "argv": args,
    "home": os.environ.get("HOME"),
    "xdg": os.environ.get("XDG_CONFIG_HOME"),
}))
out = Path(args[args.index("--output-file") + 1])
out.write_text(json.dumps({
    "record_type": "scan_summary",
    "status": "complete",
    "findings_emitted": 0,
}) + "\n")
"""

LEAK_BODY = r"""
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
Path(os.environ["STUB_ARGV"]).write_text(json.dumps({"argv": args, "home": os.environ.get("HOME")}))
out = Path(args[args.index("--output-file") + 1])
out.write_text(json.dumps({
    "record_type": "finding",
    "finding_type": "package_exposure",
    "package_name": "node-ipc",
    "version": "10.1.1",
    "severity": "critical",
    "catalog_id": "socket-test-node-ipc",
    "evidence": "leaked %s" % "FAKE_TOKEN_PLACEHOLDER",
    "source_file": "bad-app/FAKE_TOKEN_PLACEHOLDER/abc123/package-lock.json",
}) + "\n")
"""

GARBAGE_BODY = r"""
import sys
from pathlib import Path
args = sys.argv[1:]
out = Path(args[args.index("--output-file") + 1])
out.write_text("this is not json\n")
sys.exit(0)
"""


class McpScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.home = self.td / "home"
        self.bindir = self.td / "bin"
        self.fixture = self.td / "fixture"
        self.argv_path = self.td / "argv.json"
        self.out = self.td / "receipt.json"
        for path in (self.home, self.bindir, self.fixture):
            path.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write_stub(self, body: str, path: Path | None = None) -> Path:
        dest = path or (self.bindir / "bumblebee")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
        dest.chmod(dest.stat().st_mode | stat.S_IEXEC)
        return dest

    def run_scan(self, args, stub=None, extra_env=None, on_path=False):
        env = {
            "PATH": str(self.bindir) if on_path else "/usr/bin:/bin",
            "HOME": str(self.home),
            "STUB_ARGV": str(self.argv_path),
            "TMPDIR": str(self.td),
        }
        if stub is not None and not on_path:
            env["PFY_BUMBLEBEE_BIN"] = str(self.write_stub(stub))
        elif stub is not None and on_path:
            self.write_stub(stub)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def write_mcp(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_home_and_config_dir_refused_then_fixture_ok(self):
        """Fail: $HOME, a missing path, and a home config directory exit 2 and do not start the scanner.
        Recovery: an explicit project path under the home, outside those directories, exits 0.
        The child HOME is not the caller HOME and not the scan root.
        """
        self.write_stub(CLEAN_BODY)
        stub = str(self.bindir / "bumblebee")
        refused = self.run_scan(
            ["--root", str(self.home), "--out", str(self.out)],
            extra_env={"PFY_BUMBLEBEE_BIN": stub},
        )
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn("Next:", refused.stdout)
        self.assertIn("fixture", refused.stdout)
        self.assertFalse(self.argv_path.exists())

        missing = self.run_scan(
            ["--root", str(self.td / "missing"), "--out", str(self.out)],
            extra_env={"PFY_BUMBLEBEE_BIN": stub},
        )
        self.assertEqual(missing.returncode, 2, missing.stdout + missing.stderr)
        self.assertFalse(self.argv_path.exists())

        secret_dir = self.home / ".grok"
        secret_dir.mkdir()
        secret = self.run_scan(
            ["--root", str(secret_dir), "--out", str(self.out)],
            extra_env={"PFY_BUMBLEBEE_BIN": stub},
        )
        self.assertEqual(secret.returncode, 2, secret.stdout + secret.stderr)
        self.assertIn(".grok", secret.stdout)
        self.assertFalse(self.argv_path.exists())

        no_args = self.run_scan([])
        self.assertEqual(no_args.returncode, 2, no_args.stdout + no_args.stderr)

        project = self.home / "DEVELOP" / "proj"
        project.mkdir(parents=True)
        self.write_mcp(project / ".cursor" / "mcp.json", {
            "mcpServers": {"local-notes": {"command": "node", "args": ["./server.js"]}},
        })
        recovered = self.run_scan(
            ["--root", str(project), "--out", str(self.out)],
            extra_env={"PFY_BUMBLEBEE_BIN": stub},
        )
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        self.assertIn("CLEAN", recovered.stdout)
        recorded = json.loads(self.argv_path.read_text(encoding="utf-8"))
        self.assertIn("--profile", recorded["argv"])
        self.assertIn("deep", recorded["argv"])
        self.assertIn(str(project), recorded["argv"])
        self.assertNotIn("--exposure-catalog", recorded["argv"])
        self.assertNotEqual(recorded["home"], str(self.home))
        self.assertNotEqual(recorded["home"], str(project))
        self.assertTrue(recorded["xdg"])
        receipt = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["verdict"], "CLEAN")
        self.assertEqual(receipt["findings"], [])

    def test_scanner_leak_is_redacted_and_finding_exits_1(self):
        """Fail: a package finding exits 1 and echoed config values are absent from stdout and the receipt.
        A 6-character value is redacted too. Recovery: a clean stub on a config with no secret-like key exits 0.
        """
        self.write_mcp(self.fixture / ".config" / "Claude" / "claude_desktop_config.json", {
            "mcpServers": {
                "paid-tool": {
                    "command": "npx",
                    "args": ["-y", "@example/mcp-server"],
                    "env": {"API_TOKEN": TOKEN, "PASSWORD": SHORT},
                },
            },
        })
        flagged = self.run_scan(
            ["--root", str(self.fixture), "--out", str(self.out)],
            stub=LEAK_BODY,
        )
        self.assertEqual(flagged.returncode, 1, flagged.stdout + flagged.stderr)
        self.assertNotIn(TOKEN, flagged.stdout)
        self.assertNotIn(TOKEN, flagged.stderr)
        self.assertNotIn(SHORT, flagged.stdout)
        self.assertNotIn(SHORT, flagged.stderr)
        raw = self.out.read_text(encoding="utf-8")
        self.assertNotIn(TOKEN, raw)
        self.assertNotIn(SHORT, raw)
        self.assertIn("node-ipc", raw)
        self.assertIn("10.1.1", raw)
        receipt = json.loads(raw)
        self.assertEqual(receipt["verdict"], "FLAGGED")
        kinds = {row["kind"] for row in receipt["findings"]}
        self.assertIn("package-exposure", kinds)
        self.assertIn("plaintext-env", kinds)

        for path in self.fixture.rglob("*.json"):
            path.unlink()
        self.write_mcp(self.fixture / ".cursor" / "mcp.json", {
            "mcpServers": {"local-notes": {"command": "node", "args": ["./server.js"]}},
        })
        recovered = self.run_scan(
            ["--root", str(self.fixture), "--out", str(self.out)],
            stub=CLEAN_BODY,
        )
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        self.assertNotIn(TOKEN, recovered.stdout)
        receipt = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["verdict"], "CLEAN")

    def test_missing_or_unreadable_scanner_exits_2(self):
        """Fail: no binary, a set but missing binary, garbage ndjson, and a token-bearing broken config exit 2.
        The broken config does not echo the value, and a git selector in another file is still named.
        A set PFY_BUMBLEBEE_BIN does not fall through to PATH.
        Recovery: an executable at $HOME/.cache/pfy/tools/bumblebee/bumblebee exits 0.
        """
        missing = self.run_scan(["--root", str(self.fixture), "--out", str(self.out)], on_path=True)
        self.assertEqual(missing.returncode, 2, missing.stdout + missing.stderr)
        self.assertIn("Next:", missing.stdout)
        self.assertIn("PFY_BUMBLEBEE_BIN", missing.stdout)

        pinned = self.run_scan(
            ["--root", str(self.fixture), "--out", str(self.out)],
            stub=CLEAN_BODY,
            on_path=True,
            extra_env={"PFY_BUMBLEBEE_BIN": str(self.td / "missing-bin")},
        )
        self.assertEqual(pinned.returncode, 2, pinned.stdout + pinned.stderr)
        self.assertFalse(self.argv_path.exists())

        garbage = self.run_scan(
            ["--root", str(self.fixture), "--out", str(self.out)],
            stub=GARBAGE_BODY,
        )
        self.assertEqual(garbage.returncode, 2, garbage.stdout + garbage.stderr)
        self.assertIn("Next:", garbage.stdout)

        broken = self.fixture / "mcp.json"
        broken.write_text('{ "x": "%s"' % TOKEN, encoding="utf-8")
        self.write_mcp(self.fixture / ".cursor" / "mcp.json", {
            "mcpServers": {"git-tool": {"command": "npx", "args": ["-y", GIT_ARG]}},
        })
        self.argv_path.unlink(missing_ok=True)
        bad_json = self.run_scan(
            ["--root", str(self.fixture), "--out", str(self.out)],
            stub=CLEAN_BODY,
        )
        self.assertEqual(bad_json.returncode, 2, bad_json.stdout + bad_json.stderr)
        self.assertIn("git-selector", bad_json.stdout)
        self.assertNotIn(TOKEN, bad_json.stdout)
        self.assertNotIn(TOKEN, bad_json.stderr)
        self.assertNotIn(GIT_ARG, bad_json.stdout)
        self.assertFalse(self.argv_path.exists())
        broken.unlink()
        (self.fixture / ".cursor" / "mcp.json").unlink()

        blocked = self.td / "not-a-file"
        blocked.mkdir()
        unwritable = self.run_scan(
            ["--root", str(self.fixture), "--out", str(blocked)],
            stub=CLEAN_BODY,
        )
        self.assertEqual(unwritable.returncode, 2, unwritable.stdout + unwritable.stderr)
        self.assertIn("Next:", unwritable.stdout)

        cache_bin = self.home / ".cache" / "pfy" / "tools" / "bumblebee" / "bumblebee"
        self.write_stub(CLEAN_BODY, cache_bin)
        recovered = self.run_scan(["--root", str(self.fixture), "--out", str(self.out)])
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        receipt = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["verdict"], "CLEAN")

    def test_git_selector_exits_1_when_scanner_is_clean(self):
        """Fail: with no binary, a git selector still exits 2 and names the server.
        With a clean scanner, the same file exits 1. The raw selector is not printed.
        Recovery: a local command with a clean scanner exits 0.
        """
        mcp = self.fixture / ".codeium" / "windsurf" / "mcp_config.json"
        self.write_mcp(mcp, {
            "mcpServers": {
                "git-tool": {"command": "npx", "args": ["-y", GIT_ARG]},
            },
        })
        offline = self.run_scan(["--root", str(self.fixture), "--out", str(self.out)])
        self.assertEqual(offline.returncode, 2, offline.stdout + offline.stderr)
        self.assertIn("git-selector", offline.stdout)
        self.assertIn("git-tool", offline.stdout)
        self.assertNotIn(GIT_ARG, offline.stdout)
        self.assertNotIn(GIT_ARG, self.out.read_text(encoding="utf-8"))
        self.assertIn("Next:", offline.stdout)

        flagged = self.run_scan(
            ["--root", str(self.fixture), "--out", str(self.out)],
            stub=CLEAN_BODY,
        )
        self.assertEqual(flagged.returncode, 1, flagged.stdout + flagged.stderr)
        self.assertNotIn(GIT_ARG, flagged.stdout)
        receipt = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["verdict"], "FLAGGED")
        self.assertEqual(receipt["findings"][0]["kind"], "git-selector")
        self.assertEqual(receipt["findings"][0]["server"], "git-tool")
        self.assertNotIn(GIT_ARG, self.out.read_text(encoding="utf-8"))

        self.write_mcp(mcp, {
            "mcpServers": {"local-notes": {"command": "node", "args": ["./server.js"]}},
        })
        recovered = self.run_scan(
            ["--root", str(self.fixture), "--out", str(self.out)],
            stub=CLEAN_BODY,
        )
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        receipt = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["findings"], [])

    def test_plaintext_env_key_is_named_and_value_hidden(self):
        """Fail: a secret-like env key exits 1. The value is not printed. A harmless key is not a finding.
        Recovery: the same server with only NODE_ENV exits 0.
        """
        mcp = self.fixture / "mcp.json"
        self.write_mcp(mcp, {
            "mcpServers": {
                "paid-tool": {
                    "command": "npx",
                    "args": ["-y", "@example/mcp-server"],
                    "env": {"API_TOKEN": TOKEN, "NODE_ENV": "production"},
                },
                "local-notes": {"command": "node", "args": ["./server.js"]},
            },
        })
        flagged = self.run_scan(
            ["--root", str(self.fixture), "--out", str(self.out)],
            stub=CLEAN_BODY,
        )
        self.assertEqual(flagged.returncode, 1, flagged.stdout + flagged.stderr)
        self.assertIn("API_TOKEN", flagged.stdout)
        self.assertIn("plaintext-env", flagged.stdout)
        self.assertNotIn(TOKEN, flagged.stdout)
        self.assertNotIn(TOKEN, flagged.stderr)
        raw = self.out.read_text(encoding="utf-8")
        self.assertNotIn(TOKEN, raw)
        receipt = json.loads(raw)
        self.assertEqual(len(receipt["findings"]), 1)
        self.assertEqual(receipt["findings"][0]["key"], "API_TOKEN")
        self.assertNotIn("local-notes", flagged.stdout)
        self.assertNotIn("NODE_ENV", json.dumps(receipt["findings"]))

        self.write_mcp(mcp, {
            "mcpServers": {
                "paid-tool": {
                    "command": "npx",
                    "args": ["-y", "@example/mcp-server"],
                    "env": {"NODE_ENV": "production"},
                },
            },
        })
        recovered = self.run_scan(
            ["--root", str(self.fixture), "--out", str(self.out)],
            stub=CLEAN_BODY,
        )
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        receipt = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["verdict"], "CLEAN")

    def test_symlink_to_secret_config_is_skipped(self):
        """Fail: a symlinked MCP file, and a symlinked directory of one, are not read (exit 0).
        The value is absent. Recovery: a real clean file at the same path still exits 0.
        """
        outside = self.td / "outside.json"
        outside.write_text(json.dumps({
            "mcpServers": {
                "git-tool": {
                    "command": "npx",
                    "args": ["-y", GIT_ARG],
                    "env": {"API_TOKEN": TOKEN},
                },
            },
        }), encoding="utf-8")
        link = self.fixture / "mcp.json"
        link.symlink_to(outside)
        outside_dir = self.td / "outside-dir"
        outside_dir.mkdir()
        (outside_dir / "mcp.json").write_text(outside.read_text(encoding="utf-8"), encoding="utf-8")
        (self.fixture / "linked-home").symlink_to(outside_dir)
        skipped = self.run_scan(
            ["--root", str(self.fixture), "--out", str(self.out)],
            stub=CLEAN_BODY,
        )
        self.assertEqual(skipped.returncode, 0, skipped.stdout + skipped.stderr)
        self.assertNotIn(TOKEN, skipped.stdout)
        self.assertNotIn(GIT_ARG, skipped.stdout)
        receipt = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(receipt["findings"], [])

        link.unlink()
        self.write_mcp(link, {
            "mcpServers": {"local-notes": {"command": "node", "args": ["./server.js"]}},
        })
        recovered = self.run_scan(
            ["--root", str(self.fixture), "--out", str(self.out)],
            stub=CLEAN_BODY,
        )
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)


if __name__ == "__main__":
    unittest.main()
