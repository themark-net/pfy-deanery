"""Drive the brigade claim probe with a stub binary. No network and no real tool."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "brigade" / "probe.py"


def _ready_count() -> int:
    stages = ROOT / "data" / "stages"
    return sum(1 for path in stages.glob("*.json") if path.stem != "_registry")


STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json
    import os
    import sys
    from pathlib import Path

    MODE = "__MODE__"
    READY = int("__READY__")
    args = sys.argv[1:]

    def target():
        if "--target" in args:
            return Path(args[args.index("--target") + 1])
        return Path.cwd()

    if args[:1] == ["--version"]:
        print("brigade 0.27.0")
        raise SystemExit(0)
    if args[:1] == ["init"]:
        work = target() / ".brigade" / "work"
        work.mkdir(parents=True, exist_ok=True)
        (work / "tasks.json").write_text('{"tasks": []}\\n', encoding="utf-8")
        raise SystemExit(0)
    if "task" in args and "add" in args:
        raise SystemExit(0)
    if "ready" in args:
        print(json.dumps({"ready_count": READY, "ready": []}))
        raise SystemExit(0)
    if "claim" in args:
        if MODE == "error":
            sys.stderr.write("ledger busy\\n")
            raise SystemExit(1)
        actor = args[args.index("--actor") + 1]
        slot = target() / ".stub-claim" / actor
        slot.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(slot, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            print(json.dumps({"reason": "no_ready"}))
            raise SystemExit(1)
        os.close(fd)
        print(json.dumps({"task_id": "shared", "status": "in_progress", "assignee": actor}))
        raise SystemExit(0)
    sys.stderr.write("unhandled " + " ".join(args) + "\\n")
    raise SystemExit(2)
    """
)


class BrigadeClaimProbeTest(unittest.TestCase):
    def _run(self, mode: str) -> tuple[int, dict]:
        ready = _ready_count()
        with tempfile.TemporaryDirectory(prefix="brigade-probe-") as tmp:
            root = Path(tmp)
            cache = root / "cache"
            home = root / "real-home"
            cache.mkdir()
            home.mkdir()
            stub = root / "brigade"
            stub.write_text(
                STUB.replace("__MODE__", mode).replace("__READY__", str(ready)),
                encoding="utf-8",
            )
            stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
            summary = root / "summary.json"
            env = {
                "PATH": os.environ.get("PATH", "/usr/bin"),
                "HOME": str(cache / "home"),
                "PFY_REAL_HOME": str(home),
                "BRIGADE_CACHE": str(cache),
                "BRIGADE_BIN": str(stub),
                "BRIGADE_SUMMARY": str(summary),
                "BRIGADE_NAIVE_WINDOW_S": "0.2",
                "LANG": "C.UTF-8",
            }
            proc = subprocess.run(
                [sys_executable(), str(PROBE)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            self.assertTrue(summary.is_file(), proc.stderr[-500:])
            payload = json.loads(summary.read_text(encoding="utf-8"))
            self.assertFalse((ROOT / ".brigade").exists())
            return proc.returncode, payload


def sys_executable() -> str:
    return os.environ.get("PFY_PYTHON", sys.executable)


class DoubleAwardAndErrorTests(BrigadeClaimProbeTest):
    def test_double_award_is_counted(self) -> None:
        code, payload = self._run("double")
        self.assertEqual(code, 0, payload.get("brigade"))
        brigade = payload["brigade"]
        self.assertEqual(brigade["claim_rows"], 8)
        self.assertEqual(brigade["unique"], 1)
        self.assertEqual(brigade["duplicate_ids"], 1)
        self.assertEqual(brigade["extra_claims"], 7)
        self.assertEqual(brigade["error_rows"], 0)

    def test_claim_errors_are_kept_and_not_counted_as_wins(self) -> None:
        code, payload = self._run("error")
        self.assertEqual(code, 0, payload.get("brigade"))
        brigade = payload["brigade"]
        self.assertEqual(brigade["error_rows"], 8)
        self.assertEqual(brigade["claim_rows"], 0)
        self.assertEqual(brigade["duplicate_ids"], 0)
        sample = brigade.get("error_sample") or []
        self.assertTrue(sample)
        self.assertIn("ledger busy", sample[0].get("stderr") or "")


if __name__ == "__main__":
    unittest.main()
