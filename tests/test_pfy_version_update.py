"""Phase 4: product version SoT and read-only pfy update --check.

Temp HOME, fake GitHub fetcher, no public network, no writes to product or
harness files, no auto-update.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import stat
import subprocess
import tomllib
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "pfy"


def _sha(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _Home(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self.home = Path(tempfile.mkdtemp(prefix="pfy-version-p4-"))
        self.addCleanup(__import__("shutil").rmtree, self.home, ignore_errors=True)
        self.state = self.home / "state"
        self.state.mkdir()
        self.fixture = self.home / "update-source.json"

    def env(self, **extra: str) -> dict[str, str]:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["XDG_CONFIG_HOME"] = str(self.home / ".config")
        env["XDG_STATE_HOME"] = str(self.home / ".local" / "state")
        env["PFY_ROOT"] = str(ROOT)
        env["PFY_STATE_DIR"] = str(self.state)
        env["PFY_DETECT_SKIP_HOST"] = "1"
        env.pop("PFY_TEST_UPDATE_SOURCE", None)
        env.pop("GITHUB_TOKEN", None)
        env.pop("GH_TOKEN", None)
        env.update(extra)
        return env

    def run_pfy(self, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PFY), *args],
            cwd=str(ROOT),
            env=self.env(**extra),
            capture_output=True,
            text=True,
            timeout=15,
        )

    def write_source(self, payload: dict) -> str:
        self.fixture.write_text(json.dumps(payload) + "\n")
        return str(self.fixture)

    def fingerprint(self) -> dict[str, str | None]:
        paths = [
            ROOT / "pyproject.toml",
            ROOT / "pfylib" / "__init__.py",
            ROOT / "install.sh",
            self.home / ".local" / "bin" / "pfy",
            self.home / ".hermes" / "config.yaml",
            self.home / ".gemini" / "settings.json",
            self.home / ".claude.json",
        ]
        return {str(p): _sha(p) for p in paths}


class VersionSoT(_Home):
    def test_pyproject_is_the_version_source(self) -> None:
        path = ROOT / "pyproject.toml"
        self.assertTrue(path.is_file(), "pyproject.toml is the PEP 621 version SoT")
        data = tomllib.loads(path.read_text())
        version = data["project"]["version"]
        self.assertTrue(version, "project.version must be set")
        self.assertNotIn("v", version.lower())

    def test_pfylib_version_matches_pyproject(self) -> None:
        from pfylib import __version__
        from pfylib.version import product_version

        data = tomllib.loads((ROOT / "pyproject.toml").read_text())
        sot = data["project"]["version"]
        self.assertEqual(__version__, sot)
        self.assertEqual(product_version(ROOT), sot)

    def test_pfy_version_prints_sot_and_writes_nothing(self) -> None:
        data = tomllib.loads((ROOT / "pyproject.toml").read_text())
        sot = data["project"]["version"]
        before = self.fingerprint()
        proc = self.run_pfy("--version")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertEqual(proc.stdout.strip(), "pfy %s" % sot)
        self.assertEqual(self.fingerprint(), before)
        self.assertFalse(self.state.joinpath("last-verb").exists())

    def test_init_stays_import_light(self) -> None:
        text = (ROOT / "pfylib" / "__init__.py").read_text()
        head, _sep, _tail = text.partition("def __getattr__")
        self.assertNotIn("from .version import", head)
        self.assertIn("def __getattr__", text)


class UpdateCheck(_Home):
    def test_update_without_check_does_not_apply_or_write(self) -> None:
        before = self.fingerprint()
        proc = self.run_pfy("update")
        self.assertEqual(proc.returncode, 2, proc.stderr + proc.stdout)
        text = (proc.stdout + proc.stderr).lower()
        self.assertIn("check", text)
        self.assertTrue("apply" in text or "not in this slice" in text, text)
        self.assertEqual(self.fingerprint(), before)
        self.assertFalse((self.home / ".local" / "share" / "pfy").exists())

    def test_update_check_reports_newer_and_writes_nothing(self) -> None:
        from pfylib.version import product_version

        local = product_version(ROOT)
        source = self.write_source({"tag": "v99.0.0", "kind": "release"})
        before = self.fingerprint()
        proc = self.run_pfy("update", "--check", "--json", PFY_TEST_UPDATE_SOURCE=source)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout)
        self.assertEqual(rec["local"], local)
        self.assertEqual(rec["remote"], "99.0.0")
        self.assertEqual(rec["remote_kind"], "release")
        self.assertTrue(rec["newer"])
        self.assertFalse(rec.get("wrote", False))
        self.assertFalse(rec.get("auto_update", False))
        self.assertIn("not in this slice", rec.get("next_step", "").lower())
        self.assertEqual(self.fingerprint(), before)

    def test_update_check_already_current(self) -> None:
        from pfylib.version import product_version

        local = product_version(ROOT)
        source = self.write_source({"tag": "v" + local, "kind": "tag"})
        proc = self.run_pfy("update", "--check", "--json", PFY_TEST_UPDATE_SOURCE=source)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout)
        self.assertFalse(rec["newer"])
        self.assertEqual(rec["remote"], local)
        self.assertEqual(rec["remote_kind"], "tag")

    def test_update_check_no_tagged_release(self) -> None:
        source = self.write_source({"tag": None, "kind": None})
        proc = self.run_pfy("update", "--check", "--json", PFY_TEST_UPDATE_SOURCE=source)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout)
        self.assertFalse(rec["newer"])
        self.assertIsNone(rec["remote"])
        text = (rec.get("next_step") or "").lower()
        self.assertIn("no tagged", text)

    def test_update_check_does_not_open_a_network_socket(self) -> None:
        source = self.write_source({"tag": "v99.0.0", "kind": "release"})

        def blocked(*args, **kwargs):  # noqa: ANN002
            raise AssertionError("unexpected network: %r %r" % (args, kwargs))

        with mock.patch("socket.socket", blocked), mock.patch("urllib.request.urlopen", blocked):
            # Direct helper, same path the CLI uses when the fake source is set.
            from pfylib.update_check import check_update

            rec = check_update(root=ROOT, fetcher=None, source_path=source)
        self.assertTrue(rec["newer"])
        self.assertEqual(rec["remote"], "99.0.0")

    def test_real_fetcher_is_not_used_when_source_is_injected(self) -> None:
        source = self.write_source({"tag": "v1.2.3", "kind": "release"})

        def boom(*args, **kwargs):  # noqa: ANN002
            raise AssertionError("real GitHub fetcher called")

        with mock.patch("pfylib.update_check.fetch_github_latest", boom):
            proc = self.run_pfy("update", "--check", "--json", PFY_TEST_UPDATE_SOURCE=source)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout)
        self.assertEqual(rec["remote"], "1.2.3")
