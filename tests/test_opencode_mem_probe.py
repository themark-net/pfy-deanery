"""opencode-mem probe: a failed recall that prints the salt is not a hit.

The child is eval/evq1107/opencode-mem/probe.py. Each test runs that script
against a stub driver and a stub rg in a temp dir. No network, no model, no
real opencode-mem package.
"""

from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "opencode-mem" / "probe.py"
RESULTS = ROOT / "eval" / "evq1107" / "opencode-mem" / "results.json"

DRIVER_STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, sys
    from pathlib import Path

    args = sys.argv[1:]
    command = args[0]
    out = Path(args[args.index("--out") + 1])
    salt = "OCM1107_SALT_01"
    if command == "store":
        doc = {"ok": True, "command": "store", "stored": 8, "rows": []}
    elif command == "recall":
        doc = {
            "ok": True,
            "command": "recall",
            "rows": [
                {"salt": "OCM1107_SALT_%02d" % i, "listed": True, "searched": True}
                for i in range(1, 9)
            ],
        }
    elif command == "corrupt":
        # The salt is on the wire, and the row claims a hit. ok is false.
        doc = {
            "ok": False,
            "command": "corrupt",
            "error": "database disk image is malformed near %s" % salt,
            "rows": [{"salt": salt, "listed": True, "searched": True}],
        }
    else:
        doc = {"ok": False, "command": command, "error": "unexpected"}
    text = json.dumps(doc)
    out.write_text(text, encoding="utf-8")
    sys.stdout.write(text + "\\n")
    raise SystemExit(0)
    """
)

RG_STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import sys
    from pathlib import Path

    positionals = []
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--glob":
            i += 2
            continue
        if arg in ("-F", "-l"):
            i += 1
            continue
        positionals.append(arg)
        i += 1
    needle, path = positionals[0], positionals[1]
    target = Path(path)
    if target.is_file():
        if needle in target.read_text(encoding="utf-8"):
            sys.stdout.write(path + "\\n")
            raise SystemExit(0)
        raise SystemExit(1)
    if needle.startswith("OCM1107_SALT_"):
        raise SystemExit(1)
    sys.stdout.write("docs/example.md\\n")
    raise SystemExit(0)
    """
)


class OpenCodeMemProbeTests(unittest.TestCase):
    def _run(self, tmp: Path, *, skip_config: bool = True, storage: Path | None = None) -> dict:
        home = tmp / "home"
        scratch = tmp / "tmp"
        out = tmp / "out.json"
        for path in (home, scratch):
            path.mkdir()
        driver = tmp / "driver.py"
        rg = tmp / "rg"
        driver.write_text(DRIVER_STUB, encoding="utf-8")
        rg.write_text(RG_STUB, encoding="utf-8")
        driver.chmod(driver.stat().st_mode | stat.S_IEXEC)
        rg.chmod(rg.stat().st_mode | stat.S_IEXEC)
        before = RESULTS.read_bytes() if RESULTS.exists() else None
        cmd = [
            sys.executable,
            str(PROBE),
            "--out",
            str(out),
            "--node",
            sys.executable,
            "--driver",
            str(driver),
            "--rg-bin",
            str(rg),
            "--home",
            str(home),
            "--tmp",
            str(scratch),
            "--skip-pins",
        ]
        if skip_config:
            cmd.append("--skip-config")
        if storage is not None:
            cmd.extend(["--storage", str(storage)])
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        if before is not None:
            self.assertEqual(RESULTS.read_bytes(), before)
        self.assertTrue(out.is_file(), proc.stdout)
        return json.loads(out.read_text(encoding="utf-8"))

    def test_failed_recall_does_not_count_a_salt_in_the_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ocm-probe-") as raw:
            doc = self._run(Path(raw))
        self.assertEqual(doc["recall_search_hits"], 8)
        self.assertEqual(doc["recall_list_hits"], 8)
        self.assertEqual(doc["repo_novel_hits"], 0)
        self.assertEqual(doc["repo_known_hits"], 8)
        self.assertEqual(doc["file_baseline_hits"], 8)
        self.assertFalse(doc["corrupt"]["ok"])
        self.assertIn("OCM1107_SALT_01", doc["corrupt"]["error"])
        self.assertEqual(doc["corrupt_search_hits"], 0)
        self.assertEqual(doc["corrupt_list_hits"], 0)
        self.assertTrue(doc["results_written"])

    def test_reset_drops_a_named_shard_and_keeps_the_cache(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ocm-probe-") as raw:
            tmp = Path(raw)
            storage = tmp / "storage"
            projects = storage / "projects"
            projects.mkdir(parents=True)
            (storage / "metadata.db").write_text("named shard\n", encoding="utf-8")
            (projects / "project_x_shard_0.db").write_text("not a database\n", encoding="utf-8")
            cache = storage / ".cache"
            cache.mkdir()
            (cache / "marker").write_text("keep\n", encoding="utf-8")
            self._run(tmp, skip_config=False, storage=storage)
            self.assertFalse((storage / "metadata.db").exists())
            self.assertFalse(projects.exists())
            self.assertEqual((cache / "marker").read_text(encoding="utf-8"), "keep\n")


if __name__ == "__main__":
    unittest.main()
