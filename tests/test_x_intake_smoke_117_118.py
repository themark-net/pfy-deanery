"""Entries 117-118 smokes: fail paths exit 2, compose down -v always runs, receipts stay untracked.

Parent HOME is a temp dir this test owns, so the smoke's tmp/ lookups and stubs never touch the real home.
Fail: a wrong pin, an unpinned image or missing docker does not exit 2; `compose down -v` is skipped after a
failed `up`; or the kander/moira receipts are not gitignored.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "examples/x-intake-local/smoke_117_118.py"
_RECEIPTS: Path | None = None


def _write_exe(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _env(home: Path, **extra: str) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    for key in list(env):
        if key.startswith(("KANDER_", "MOIRA_", "DOCKER_")) or key == "PFY_XINTAKE_TIMEOUT":
            env.pop(key, None)
    env.update(extra)
    if _RECEIPTS is None:
        raise RuntimeError("PFY_SMOKE_RECEIPT_DIR is unset")
    env["PFY_SMOKE_RECEIPT_DIR"] = str(_RECEIPTS)
    return env


def _run(entry: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, SCRIPT, "--entry", entry], cwd=str(ROOT), env=env,
                          capture_output=True, text=True, timeout=60)


TRAEFIK_PINNED = "traefik@sha256:" + "1" * 64


def _moira_dir(root: Path, image: str, traefik: str = TRAEFIK_PINNED) -> Path:
    (root / "config").mkdir(parents=True)
    (root / "docker-compose.yml").write_text(
        f"services:\n  traefik:\n    image: {traefik}\n  moira:\n    image: ${{MOIRA_IMAGE}}\n", encoding="utf-8")
    (root / "config/traefik-self-host.yml").write_text("{}\n", encoding="utf-8")
    (root / ".env").write_text(f"MOIRA_IMAGE={image}\n", encoding="utf-8")
    return root


def _receipt(entry: str) -> dict:
    path = Path(_RECEIPTS) / entry / "latest.json"
    return json.loads(path.read_text(encoding="utf-8"))


PINNED = "ghcr.io/moira-mcp/moira@sha256:" + "0" * 64


class XIntakeSmoke117118Tests(unittest.TestCase):
    def setUp(self) -> None:
        global _RECEIPTS
        self._receipt_tmp = tempfile.TemporaryDirectory(prefix="pfy-xintake-117-receipts-")
        self.addCleanup(self._receipt_tmp.cleanup)
        _RECEIPTS = Path(self._receipt_tmp.name)

    def tearDown(self) -> None:
        global _RECEIPTS
        _RECEIPTS = None

    def test_wrong_kander_version_exits_2(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-117-") as td:
            home = Path(td, "home")
            home.mkdir()
            calls = Path(td, "calls")
            kander = Path(td, "kander")
            _write_exe(kander, f"""#!/bin/sh
echo "$@" >> {shlex.quote(str(calls))}
echo "kander version 0.0.1"
""")
            p = _run("kander", _env(home, KANDER_BIN=str(kander), KANDER_SHA256="skip"))
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertIn("version", _receipt("kander")["reason"])
            self.assertNotIn("doctor", calls.read_text(encoding="utf-8") if calls.exists() else "")

    def test_unpinned_moira_image_exits_2(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-118-") as td:
            home = Path(td, "home")
            home.mkdir()
            calls = Path(td, "calls")
            docker = Path(td, "docker")
            _write_exe(docker, f"#!/bin/sh\necho \"$@\" >> {shlex.quote(str(calls))}\nexit 0\n")
            d = _moira_dir(Path(td, "moira"), "ghcr.io/moira-mcp/moira:latest")
            p = _run("moira", _env(home, MOIRA_DIR=str(d), DOCKER_BIN=str(docker)))
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertIn("digest", _receipt("moira")["reason"])
            self.assertFalse(calls.exists(), "docker ran despite an unpinned image")

    def test_unpinned_traefik_image_exits_2(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-118-") as td:
            home = Path(td, "home")
            home.mkdir()
            calls = Path(td, "calls")
            docker = Path(td, "docker")
            _write_exe(docker, f"#!/bin/sh\necho \"$@\" >> {shlex.quote(str(calls))}\nexit 0\n")
            d = _moira_dir(Path(td, "moira"), PINNED, traefik="traefik:v2.11.58")
            p = _run("moira", _env(home, MOIRA_DIR=str(d), DOCKER_BIN=str(docker)))
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertIn("traefik", _receipt("moira")["reason"])
            self.assertFalse(calls.exists(), "docker ran despite an unpinned traefik image")

    def test_kander_timeout_still_checks_real_home(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-117-") as td:
            home = Path(td, "home")
            (home / ".config/kander").mkdir(parents=True)
            kander = Path(td, "kander")
            _write_exe(kander, """#!/bin/sh
for a in "$@"; do if [ "$a" = version ]; then echo "kander version 0.9.5"; exit 0; fi; done
exec sleep 30
""")
            p = _run("kander", _env(home, KANDER_BIN=str(kander), KANDER_SHA256="skip", PFY_XINTAKE_TIMEOUT="1"))
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            receipt = _receipt("kander")
            self.assertIn("timeout", receipt["reason"])
            self.assertIs(receipt.get("checks", {}).get("real_home_untouched"), True, receipt)

    def test_missing_docker_exits_2(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-118-") as td:
            home = Path(td, "home")
            home.mkdir()
            empty = Path(td, "empty-path")
            empty.mkdir()
            d = _moira_dir(Path(td, "moira"), PINNED)
            p = _run("moira", _env(home, MOIRA_DIR=str(d), PATH=str(empty)))
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            self.assertIn("docker", _receipt("moira")["reason"])

    def test_compose_down_v_runs_after_failed_up(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-118-") as td:
            home = Path(td, "home")
            home.mkdir()
            calls = Path(td, "calls")
            docker = Path(td, "docker")
            _write_exe(docker, f"""#!/bin/sh
echo "$@" >> {shlex.quote(str(calls))}
case " $* " in *" up "*) echo "boom" >&2; exit 1;; esac
exit 0
""")
            d = _moira_dir(Path(td, "moira"), PINNED)
            p = _run("moira", _env(home, MOIRA_DIR=str(d), DOCKER_BIN=str(docker)))
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertNotIn("Traceback", p.stderr)
            lines = calls.read_text(encoding="utf-8").splitlines()
            ups = [i for i, l in enumerate(lines) if " up " in f" {l} "]
            downs = [i for i, l in enumerate(lines) if l.split()[-2:] == ["down", "-v"]]
            self.assertTrue(ups, lines)
            self.assertTrue(downs and downs[-1] > ups[0], f"compose down -v did not run after up: {lines}")

    def test_kander_and_moira_receipts_are_ignored(self) -> None:
        for entry in ("kander", "moira"):
            rel = f"pipelines/smoke/{entry}/latest.json"
            ignored = subprocess.run(["git", "check-ignore", "-q", "--", rel], cwd=str(ROOT))
            self.assertEqual(ignored.returncode, 0, rel)
        tracked = subprocess.run(
            ["git", "check-ignore", "-q", "--", "pipelines/smoke/kolibri1/latest.json"], cwd=str(ROOT))
        self.assertEqual(tracked.returncode, 1)


if __name__ == "__main__":
    unittest.main()
