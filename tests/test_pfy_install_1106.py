"""Behavior of ./pfy install PATH launchers.

Seam: ./pfy install / install --uninstall / uninstall --launchers, and the
mentat and pfy scripts those commands write. Every test uses a temp HOME
and a temp prefix. Nothing here may touch the real ~/.local/bin.

Fail if the launchers disappear, point at another cwd, or overwrite a
foreign file. Recovery is a non-zero exit and an unchanged prefix.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "pfy"
REAL_BIN = Path.home() / ".local" / "bin"
MARKER = "# pfy-mentat launcher (pfy install)"


def _snapshot_real_bin() -> tuple:
    if not REAL_BIN.exists():
        return ("missing",)
    names = tuple(sorted(p.name for p in REAL_BIN.iterdir()))
    stats = []
    for name in ("mentat", "pfy"):
        path = REAL_BIN / name
        if path.exists() or path.is_symlink():
            st = path.lstat()
            stats.append((name, st.st_ino, st.st_mtime_ns, st.st_size, st.st_mode))
        else:
            stats.append((name, None))
    return (names, tuple(stats))


class PfyInstall1106(unittest.TestCase):
    def setUp(self) -> None:
        self._real = _snapshot_real_bin()
        parent = ROOT / "tmp"
        parent.mkdir(parents=True, exist_ok=True)
        self.home = Path(tempfile.mkdtemp(prefix="pfy-install-home-", dir=str(parent)))
        self.prefix = Path(tempfile.mkdtemp(prefix="pfy-install-prefix-", dir=str(parent)))
        self.other = Path(tempfile.mkdtemp(prefix="pfy-install-cwd-", dir=str(parent)))
        self.addCleanup(self._cleanup)

    def tearDown(self) -> None:
        self.assertEqual(
            _snapshot_real_bin(),
            self._real,
            "install tests touched the real ~/.local/bin",
        )

    def _cleanup(self) -> None:
        for path in (self.prefix, self.home, self.other):
            if path.exists() or path.is_symlink():
                if path.is_dir() and not path.is_symlink():
                    os.chmod(path, 0o755)
                    for child in path.rglob("*"):
                        if child.is_dir() and not child.is_symlink():
                            os.chmod(child, 0o755)
                shutil.rmtree(path, ignore_errors=True)

    def env(self, **extra: str) -> dict[str, str]:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["PFY_STATE_DIR"] = str(self.home / "state")
        env["PFY_SKIP_WINDOW"] = "1"
        env["XDG_STATE_HOME"] = str(self.home / "xdg-state")
        env["XDG_CONFIG_HOME"] = str(self.home / "xdg-config")
        env["XDG_DATA_HOME"] = str(self.home / "xdg-data")
        env.pop("DISPLAY", None)
        env.pop("WAYLAND_DISPLAY", None)
        env.pop("PFY_START_ENGINE", None)
        env.pop("PFY_START_ENGINE_FLAG", None)
        env.update(extra)
        return env

    def run_pfy(self, args: list[str], cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=str(cwd or self.other),
            env=env or self.env(),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    def install(self, prefix: Path | None = None, extra: list[str] | None = None, pfy: Path | None = None) -> subprocess.CompletedProcess[str]:
        cmd = [str(pfy or PFY), "install", "--prefix", str(prefix or self.prefix)]
        if extra:
            cmd.extend(extra)
        return self.run_pfy(cmd)

    def assert_ran_this_repo(self, launcher: Path) -> None:
        proc = self.run_pfy([str(launcher), "help"])
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertIn("pfy install", proc.stdout)
        self.assertIn("--launchers", proc.stdout)
        body = launcher.read_text(encoding="utf-8")
        self.assertIn(MARKER, body)
        self.assertIn("exec '%s/scripts/pfy'" % ROOT, body)
        self.assertNotIn(str(self.other), body)

    def test_help_lists_install_and_uninstall_flags(self) -> None:
        """Fail: ./pfy help omits install, --uninstall, or --launchers.
        Recovery: put those flags back on the usage text."""
        proc = self.run_pfy([str(PFY), "help"])
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        for needle in (
            "pfy install",
            "--prefix",
            "--dry-run",
            "--uninstall",
            "--launchers",
        ):
            self.assertIn(needle, proc.stdout, needle)

    def test_install_then_launchers_work_from_another_cwd(self) -> None:
        """Fail: mentat or pfy is missing, or help does not run this checkout.
        Recovery: rewrite the wrappers so they exec this repo from any cwd."""
        proc = self.install()
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assert_ran_this_repo(self.prefix / "mentat")
        self.assert_ran_this_repo(self.prefix / "pfy")
        mentat_mode = (self.prefix / "mentat").stat().st_mode
        self.assertTrue(mentat_mode & stat.S_IXUSR)

    def test_default_prefix_is_home_local_bin(self) -> None:
        """Fail: a bare ./pfy install writes outside $HOME/.local/bin.
        Recovery: default the prefix back to $HOME/.local/bin."""
        proc = self.run_pfy([str(PFY), "install"])
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        dest = self.home / ".local" / "bin"
        self.assert_ran_this_repo(dest / "mentat")
        self.assert_ran_this_repo(dest / "pfy")
        self.assertIn('export PATH="$HOME/.local/bin:$PATH"', blob)
        self.assertNotEqual(dest.resolve(), REAL_BIN.resolve())

    def test_rerun_same_root_is_byte_identical(self) -> None:
        """Fail: a second install rewrites the launchers or exits non-zero.
        Recovery: leave matching launchers untouched and say already installed."""
        first = self.install()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        mentat = (self.prefix / "mentat").read_bytes()
        pfy = (self.prefix / "pfy").read_bytes()
        second = self.install()
        blob = second.stdout + second.stderr
        self.assertEqual(second.returncode, 0, blob)
        self.assertEqual((self.prefix / "mentat").read_bytes(), mentat)
        self.assertEqual((self.prefix / "pfy").read_bytes(), pfy)
        self.assertIn("already installed", blob)

    def test_foreign_mentat_is_kept_and_pfy_is_not_created(self) -> None:
        """Fail: install overwrites a foreign mentat or still creates pfy.
        Recovery: exit non-zero before writing either launcher."""
        foreign = self.prefix / "mentat"
        foreign.write_text("#!/bin/sh\necho foreign-mentat\n", encoding="utf-8")
        before = foreign.read_bytes()
        proc = self.install()
        blob = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, blob)
        self.assertEqual(foreign.read_bytes(), before)
        self.assertFalse((self.prefix / "pfy").exists())
        self.assertIn(str(foreign), blob)

    def test_foreign_mentat_blocks_shim_replacement(self) -> None:
        """Fail: a foreign mentat still lets install replace the install.sh shim.
        Recovery: classify both names and write nothing when either is foreign."""
        foreign = self.prefix / "mentat"
        foreign.write_text("#!/bin/sh\necho foreign-mentat\n", encoding="utf-8")
        before = foreign.read_bytes()
        shim = "#!/bin/sh\nexec '%s/.local/share/pfy/v0.4.17/pfy' \"$@\"\n" % self.home
        pfy = self.prefix / "pfy"
        pfy.write_text(shim, encoding="utf-8")
        proc = self.install()
        blob = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, blob)
        self.assertEqual(foreign.read_bytes(), before)
        self.assertEqual(pfy.read_text(encoding="utf-8"), shim)
        self.assertIn(str(foreign), blob)

    def test_foreign_pfy_is_kept_and_mentat_is_not_created(self) -> None:
        """Fail: install writes mentat before noticing a foreign pfy.
        Recovery: classify both names, then exit non-zero with no writes."""
        foreign = self.prefix / "pfy"
        foreign.write_text("#!/bin/sh\necho foreign-pfy\n", encoding="utf-8")
        before = foreign.read_bytes()
        proc = self.install()
        blob = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, blob)
        self.assertEqual(foreign.read_bytes(), before)
        self.assertFalse((self.prefix / "mentat").exists())
        self.assertIn(str(foreign), blob)

    def test_prefix_not_on_path_prints_export_line(self) -> None:
        """Fail: a prefix outside PATH produces no export PATH line.
        Recovery: print the line and do not edit shell rc files."""
        proc = self.install()
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertIn('export PATH="%s:$PATH"' % self.prefix, blob)
        self.assertIn("~/.bashrc", blob)
        self.assertIn("~/.profile", blob)

    def test_prefix_on_path_has_no_path_warning(self) -> None:
        """Fail: install warns about PATH when the prefix is already on it.
        Recovery: skip the PATH warning for that prefix."""
        env = self.env(PATH="%s:%s" % (self.prefix, os.environ.get("PATH", "")))
        proc = self.run_pfy(
            [str(PFY), "install", "--prefix", str(self.prefix)],
            env=env,
        )
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertNotIn("not on PATH", blob)
        self.assertNotIn("export PATH=", blob)

    def test_dry_run_writes_nothing(self) -> None:
        """Fail: --dry-run creates a launcher or the prefix contents change.
        Recovery: print the plan and leave the prefix empty."""
        before = sorted(self.prefix.iterdir())
        proc = self.install(extra=["--dry-run"])
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertEqual(sorted(self.prefix.iterdir()), before)
        self.assertFalse((self.prefix / "mentat").exists())
        self.assertFalse((self.prefix / "pfy").exists())

    def test_install_uninstall_removes_ours_leaves_foreign_and_repeats(self) -> None:
        """Fail: install --uninstall deletes a foreign file or leaves a launcher.
        Recovery: remove only marker files, then succeed again with them gone."""
        keep = self.prefix / "keep-me"
        keep.write_text("keep\n", encoding="utf-8")
        proc = self.install()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        removed = self.run_pfy([str(PFY), "install", "--uninstall", "--prefix", str(self.prefix)])
        blob = removed.stdout + removed.stderr
        self.assertEqual(removed.returncode, 0, blob)
        self.assertFalse((self.prefix / "mentat").exists())
        self.assertFalse((self.prefix / "pfy").exists())
        self.assertEqual(keep.read_text(encoding="utf-8"), "keep\n")
        again = self.run_pfy([str(PFY), "install", "--uninstall", "--prefix", str(self.prefix)])
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertEqual(keep.read_text(encoding="utf-8"), "keep\n")
        self.assertIn("already uninstalled", again.stdout + again.stderr)

    def test_uninstall_launchers_removes_ours_leaves_foreign_and_repeats(self) -> None:
        """Fail: uninstall --launchers is not the same removal as install --uninstall.
        Recovery: route --launchers to the launcher remover only."""
        keep = self.prefix / "keep-me"
        keep.write_text("keep\n", encoding="utf-8")
        proc = self.install()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        removed = self.run_pfy([str(PFY), "uninstall", "--launchers", "--prefix", str(self.prefix)])
        blob = removed.stdout + removed.stderr
        self.assertEqual(removed.returncode, 0, blob)
        self.assertFalse((self.prefix / "mentat").exists())
        self.assertFalse((self.prefix / "pfy").exists())
        self.assertEqual(keep.read_text(encoding="utf-8"), "keep\n")
        again = self.run_pfy([str(PFY), "uninstall", "--launchers", "--prefix", str(self.prefix)])
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertIn("already uninstalled", again.stdout + again.stderr)

    def test_plain_uninstall_does_not_remove_launchers(self) -> None:
        """Fail: plain ./pfy uninstall starts removing PATH launchers.
        Recovery: keep ledger uninstall on its own path unless --launchers is set."""
        proc = self.install()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        before_m = (self.prefix / "mentat").read_bytes()
        before_p = (self.prefix / "pfy").read_bytes()
        plain = self.run_pfy([str(PFY), "uninstall"])
        blob = plain.stdout + plain.stderr
        self.assertIn("needs_confirmation", blob)
        self.assertEqual((self.prefix / "mentat").read_bytes(), before_m)
        self.assertEqual((self.prefix / "pfy").read_bytes(), before_p)

    def test_install_from_outside_cwd_bakes_real_root(self) -> None:
        """Fail: the wrapper execs a path under the caller's cwd.
        Recovery: bake the checkout that contains scripts/pfy."""
        proc = self.install()
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        body = (self.prefix / "mentat").read_text(encoding="utf-8")
        self.assertIn("exec '%s/scripts/pfy'" % ROOT, body)
        self.assertNotIn(str(self.other), body)
        self.assert_ran_this_repo(self.prefix / "mentat")

    def test_symlinked_pfy_bakes_real_root(self) -> None:
        """Fail: a symlinked ./pfy bakes the symlink directory.
        Recovery: resolve ./pfy to this checkout before writing launchers."""
        link_dir = self.home / "linked"
        link_dir.mkdir()
        link = link_dir / "pfy"
        link.symlink_to(PFY)
        proc = self.run_pfy(
            [str(link), "install", "--prefix", str(self.prefix)],
        )
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        body = (self.prefix / "pfy").read_text(encoding="utf-8")
        self.assertIn("exec '%s/scripts/pfy'" % ROOT, body)
        self.assertNotIn(str(link_dir), body)
        self.assert_ran_this_repo(self.prefix / "mentat")

    def test_different_root_updates_our_launchers(self) -> None:
        """Fail: a second install leaves a launcher pointed at another root.
        Recovery: rewrite our own marker files and say they were updated."""
        proc = self.install()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        stale = "/tmp/pfy-install-other-root"
        for name in ("mentat", "pfy"):
            path = self.prefix / name
            text = path.read_text(encoding="utf-8").replace(str(ROOT), stale)
            path.write_text(text, encoding="utf-8")
        again = self.install()
        blob = again.stdout + again.stderr
        self.assertEqual(again.returncode, 0, blob)
        self.assertIn("updated", blob)
        body = (self.prefix / "mentat").read_text(encoding="utf-8")
        self.assertIn("exec '%s/scripts/pfy'" % ROOT, body)
        self.assertNotIn(stale, body)
        self.assert_ran_this_repo(self.prefix / "pfy")

    def test_install_sh_shim_is_replaced_with_a_note(self) -> None:
        """Fail: the 2-line install.sh shim is treated as a foreign pfy.
        Recovery: replace that shim, say so, and leave a foreign mentat alone."""
        shim = "#!/bin/sh\nexec '%s/.local/share/pfy/v0.4.17/pfy' \"$@\"\n" % self.home
        (self.prefix / "pfy").write_text(shim, encoding="utf-8")
        proc = self.install()
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertIn("shim", blob)
        body = (self.prefix / "pfy").read_text(encoding="utf-8")
        self.assertIn(MARKER, body)
        self.assertIn("exec '%s/scripts/pfy'" % ROOT, body)
        self.assertNotIn(".local/share/pfy", body)

    def test_uninstall_leaves_install_sh_shim(self) -> None:
        """Fail: launcher removal deletes the install.sh shim (it has no marker).
        Recovery: remove marker files only and note the foreign shim."""
        proc = self.install()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        shim = "#!/bin/sh\nexec '%s/.local/share/pfy/v0.4.17/pfy' \"$@\"\n" % self.home
        (self.prefix / "pfy").write_text(shim, encoding="utf-8")
        removed = self.run_pfy([str(PFY), "uninstall", "--launchers", "--prefix", str(self.prefix)])
        blob = removed.stdout + removed.stderr
        self.assertEqual(removed.returncode, 0, blob)
        self.assertFalse((self.prefix / "mentat").exists())
        self.assertEqual((self.prefix / "pfy").read_text(encoding="utf-8"), shim)
        self.assertIn("foreign", blob)

    def test_prefix_with_a_quote_installs_without_eval(self) -> None:
        """Fail: a prefix containing a quote breaks install or runs a trap command.
        Recovery: write both launchers and do not eval the prefix path."""
        stamp_name = "pfy-install-trap-stamp"
        prefix = self.home / ("pre'$(touch %s)'fix" % stamp_name)
        prefix.mkdir()
        watched = (
            self.other / stamp_name,
            self.home / stamp_name,
            ROOT / stamp_name,
            Path.cwd() / stamp_name,
        )
        self.addCleanup(lambda: [p.unlink() for p in watched if p.is_file()])
        proc = self.install(prefix)
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertFalse(any(p.exists() for p in watched), "prefix path was eval'd")
        self.assert_ran_this_repo(prefix / "mentat")
        self.assert_ran_this_repo(prefix / "pfy")
        leftovers = [p.name for p in prefix.iterdir() if p.name not in ("mentat", "pfy")]
        self.assertEqual(leftovers, [])

    def test_unwritable_prefix_fails_without_invoking_sudo(self) -> None:
        """Fail: an unwritable prefix exits 0, stays silent, or runs sudo.
        Recovery: exit non-zero, print a sudo command, invoke nothing."""
        if os.geteuid() == 0:
            self.skipTest("chmod 555 does not block root")
        os.chmod(self.prefix, 0o555)
        stamp = self.home / "sudo-ran"
        bindir = self.home / "bin"
        bindir.mkdir()
        sudo = bindir / "sudo"
        sudo.write_text("#!/bin/sh\ntouch '%s'\nexit 99\n" % stamp, encoding="utf-8")
        sudo.chmod(0o755)
        env = self.env(PATH="%s:%s" % (bindir, os.environ.get("PATH", "")))
        before = sorted(os.listdir(self.prefix))
        proc = self.run_pfy(
            [str(PFY), "install", "--prefix", str(self.prefix)],
            env=env,
        )
        blob = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, blob)
        self.assertIn("not writable", blob)
        self.assertIn("sudo ./pfy install --prefix %s" % self.prefix, blob)
        self.assertFalse(stamp.exists(), "sudo was invoked")
        self.assertEqual(sorted(os.listdir(self.prefix)), before)

    def test_unstable_checkout_warns_and_still_installs(self) -> None:
        """Fail: a tmp/ or linked worktree install is silent, or a main checkout warns.
        Recovery: warn and still write the launchers. Do not refuse."""
        proc = self.install()
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertTrue((self.prefix / "mentat").is_file())
        git_dir = subprocess.run(
            ["git", "rev-parse", "--absolute-git-dir"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        under_tmp = "/tmp/" in ("%s/" % ROOT) or str(ROOT).endswith("/tmp")
        linked = git_dir.returncode == 0 and common.returncode == 0 and git_dir.stdout.strip() != common.stdout.strip()
        if under_tmp or linked:
            self.assertIn("stable checkout", blob)
        else:
            self.assertNotIn("stable checkout", blob)

    def test_docs_name_install_prefix_path_and_removal(self) -> None:
        """Fail: README, the build quickstart, or DEPLOY drop the install step.
        Recovery: document ./pfy install, mentat, --prefix, the PATH line, and removal."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        simple = readme.split("## Simple path", 1)[1].split("\n## ", 1)[0]
        self.assertIn("./pfy install", simple)
        self.assertIn("mentat", simple)
        self.assertIn("--prefix", simple)
        self.assertIn('export PATH="$HOME/.local/bin:$PATH"', simple)
        self.assertIn("--uninstall", simple)
        self.assertIn("--launchers", simple)
        quick = (ROOT / "docs" / "QUICKSTART-pfy-build.md").read_text(encoding="utf-8")
        self.assertIn("./pfy install", quick)
        self.assertIn("--prefix", quick)
        deploy = (ROOT / "docs" / "ops" / "DEPLOY.md").read_text(encoding="utf-8")
        self.assertIn("./pfy install", deploy)
        self.assertIn("--uninstall", deploy)
        self.assertIn("--launchers", deploy)
