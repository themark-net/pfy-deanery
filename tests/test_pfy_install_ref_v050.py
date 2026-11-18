"""install.sh honours PFY_REF=v0.5.0 offline; default stays main.

Temp HOME, fake git on PATH, no public network. Lives in a new module so
this release prep does not modify tests/test_pfy_install_ref.py.
"""
from __future__ import annotations

from tests.test_pfy_install_ref import InstallRefTests


class InstallRefV050Tests(InstallRefTests):
    # Do not inherit the parent test_* methods; only reuse the fake-git fixture.
    test_one_liner_points_at_main = None
    test_default_ref_is_main_and_resolves_with_fake_git = None
    test_version_and_dry_run_print_main = None
    test_missing_pfy_ref_fails_clearly_and_writes_nothing = None
    test_pfy_ref_sha_resolves_when_fake_allows_it = None

    def test_pfy_ref_v050_tag_resolves_offline_when_fake_allows_it(self) -> None:
        proc = self.run_install("--no-setup", PFY_REF="v0.5.0", PFY_FAKE_GIT_REFS="v0.5.0")
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        dest = self.home / ".local" / "share" / "pfy" / "v0.5.0"
        self.assertTrue((dest / "pfy").is_file())
        fetches = [c for c in self.git_calls() if c["args"] and c["args"][0] == "fetch"]
        self.assertTrue(fetches, blob)
        self.assertEqual(fetches[0]["args"][-1], "v0.5.0")
        self.assertNotIn("ref: main", proc.stdout)

    def test_missing_v050_tag_fails_closed_and_default_stays_main(self) -> None:
        proc = self.run_install("--no-setup", PFY_REF="v0.5.0", PFY_FAKE_GIT_REFS="main")
        blob = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, blob)
        self.assertIn("does not exist", blob.lower())
        self.assertIn("v0.5.0", blob)
        share = self.home / ".local" / "share" / "pfy"
        leftovers = [p.name for p in share.iterdir()] if share.exists() else []
        self.assertEqual(leftovers, [], leftovers)
        self.assertFalse((self.home / ".local" / "bin" / "pfy").exists())
        proc = self.run_install("--dry-run")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("ref: main", proc.stdout)
