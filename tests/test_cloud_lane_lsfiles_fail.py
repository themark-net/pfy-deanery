"""B4: if git ls-files fails, the gate-rewrite check fails closed."""

from __future__ import annotations

import os
import shutil
import unittest

from tests.test_cloud_lane_busy import REVIEW_OK
from tests.test_cloud_lane_manifest import HEAD, _Rewrite
from tests.test_pfy_build_cloud import _git, _run, _write_exe


class LsFilesFailureFailsClosed(_Rewrite):
    def shim(self, only_after_marker: bool) -> dict:
        real = shutil.which("git")
        self.assertTrue(real)
        bindir = self.side / "gitshim"
        bindir.mkdir(parents=True, exist_ok=True)
        marker = self.side / "gate-ran"
        cond = '[ -e "%s" ]' % marker if only_after_marker else "true"
        script = (
            "#!/bin/sh\n"
            'for a in "$@"; do if [ "$a" = ls-files ] && %s; then echo "shim: ls-files broken" >&2; exit 128; fi; done\n'
            'exec "%s" "$@"\n'
        ) % (cond, real)
        (bindir / "git").write_text(script, encoding="utf-8")
        (bindir / "git").chmod(0o755)
        self.marker = marker
        return {"PATH": "%s%s%s" % (bindir, os.pathsep, os.environ.get("PATH", ""))}

    def run_build(self, env: dict) -> dict:
        self.commit_file("src/kept.py", "kept = 1\n")
        grok = _write_exe(self.side / "grok.py", HEAD + REVIEW_OK + "Path('k.py').write_text('k = 1\\n')\n")
        gate = _write_exe(
            self.side / "gate.py",
            HEAD + "Path('src/kept.py').write_text('kept = 2\\n')\nPath(%r).write_text('1')\nprint('ok')\n" % str(self.marker),
        )
        proc = _run(self.argv("change things", grok, gate, "r"), self.repo, env=env, timeout=90)
        r = self.receipt("r") if (self.side / "r" / "receipt.json").exists() else {}
        r["_out"] = ((proc.stdout or "") + (proc.stderr or ""))[-1500:]
        r["_rc"] = proc.returncode
        return r

    def assert_not_kept(self, r: dict) -> None:
        self.assertNotEqual(r.get("status"), "PASS", r)
        self.assertFalse(r.get("commit"), r)
        self.assertNotEqual(r["_rc"], 0, r)
        self.assertEqual(_git(self.repo, "branch", "--list", "cloud/*").stdout.strip(), "", r)
        self.assertTrue(r.get("recovery"), r)
        self.assertNotEqual(r.get("reason"), "runner-crash", r)

    def test_ls_files_failing_throughout_does_not_pass(self) -> None:
        self.assert_not_kept(self.run_build(self.shim(only_after_marker=False)))

    def test_ls_files_failing_only_after_the_gate_does_not_pass(self) -> None:
        self.assert_not_kept(self.run_build(self.shim(only_after_marker=True)))


if __name__ == "__main__":
    unittest.main()
