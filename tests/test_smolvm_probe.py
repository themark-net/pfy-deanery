#!/usr/bin/env python3
"""Drive the smolvm probe with a stub binary. No network and no KVM.

A stub that prints the host kernel and rewrites the sentinel must not count
as isolated. A stub that prints a different kernel and leaves the sentinel
must. A sha256 mismatch must not exec the stub.
"""

from __future__ import annotations

import hashlib
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
PROBE = ROOT / "eval" / "evq1107" / "smolvm" / "probe.py"

LEAK = textwrap.dedent(
    """\
    #!/bin/sh
    touch "$(dirname "$0")/executed"
    script=""
    for a in "$@"; do script=$a; done
    sent=$(printf '%s\\n' "$script" | sed -n 's/.*SENTINEL=\\([^;]*\\).*/\\1/p' | tr -d "'")
    printf 'pwn\\n' > "$sent"
    printf '%s\\n' pfy-smolvm-install-ok "name: probe-skill" "$(uname -r)" host-visible host-write-ok cwd-visible
    """
)

RECOVER = textwrap.dedent(
    """\
    #!/bin/sh
    touch "$(dirname "$0")/executed"
    printf '%s\\n' "Using cached image e3e932cf66304460" pfy-smolvm-install-ok "name: probe-skill" "6.12.95" host-hidden host-write-blocked cwd-hidden
    """
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


NO_IMAGE = textwrap.dedent(
    """\
    #!/bin/sh
    printf '%s\\n' pfy-smolvm-install-ok "name: probe-skill" "6.12.95" host-hidden host-write-blocked cwd-hidden
    """
)

DELETE = textwrap.dedent(
    """\
    #!/bin/sh
    script=""
    for a in "$@"; do script=$a; done
    sent=$(printf '%s\\n' "$script" | sed -n 's/.*SENTINEL=\\([^;]*\\).*/\\1/p' | tr -d "'")
    rm -f "$sent"
    printf '%s\\n' pfy-smolvm-install-ok "name: probe-skill" "6.12.95" host-hidden host-write-blocked cwd-hidden
    """
)


def write_stub(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class SmolvmProbeTests(unittest.TestCase):
    def run_probe(
        self,
        stub: Path,
        out: Path,
        base: Path,
        expect_sha: str,
        require_image: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["SMOLVM_BIN"] = str(stub)
        env["SMOLVM_SHA256"] = expect_sha
        env["SMOLVM_OUT"] = str(out)
        env["SMOLVM_PROBE_BASE"] = str(base)
        if require_image:
            env["SMOLVM_REQUIRE_IMAGE"] = "1"
        else:
            env.pop("SMOLVM_REQUIRE_IMAGE", None)
        return subprocess.run(
            [sys.executable, str(PROBE)],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_visible_guest_is_not_isolated_and_a_hidden_guest_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="smolvm-probe-") as raw:
            folder = Path(raw)
            leak = folder / "leak-smolvm"
            write_stub(leak, LEAK)
            leak_out = folder / "leak.json"
            leak_base = folder / "leak-base"
            proc = self.run_probe(leak, leak_out, leak_base, sha256_file(leak))
            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            body = json.loads(leak_out.read_text(encoding="utf-8"))
            self.assertEqual(body["guest_escapes_blocked"], 0)
            self.assertFalse(body["sentinel_unchanged"])
            self.assertFalse(body["kernel_differs"])
            self.assertTrue((folder / "executed").is_file())

            recover = folder / "recover-smolvm"
            write_stub(recover, RECOVER)
            recover_out = folder / "recover.json"
            recover_base = folder / "recover-base"
            proc = self.run_probe(recover, recover_out, recover_base, sha256_file(recover))
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            body = json.loads(recover_out.read_text(encoding="utf-8"))
            self.assertEqual(body["guest_escapes_blocked"], 3)
            self.assertEqual(body["control_escapes_blocked"], 0)
            self.assertTrue(body["kernel_differs"])
            self.assertTrue(body["sentinel_unchanged"])
            self.assertTrue(body["cwd_marker_unchanged"])
            self.assertEqual(body["guest_kernel"], "6.12.95")

    def test_deleted_sentinel_is_not_unchanged_and_a_left_file_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="smolvm-delete-") as raw:
            folder = Path(raw)
            delete = folder / "delete-smolvm"
            write_stub(delete, DELETE)
            out = folder / "delete.json"
            proc = self.run_probe(delete, out, folder / "base", sha256_file(delete))
            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            body = json.loads(out.read_text(encoding="utf-8"))
            self.assertFalse(body["sentinel_unchanged"])
            self.assertLess(body["guest_escapes_blocked"], 3)

            recover = folder / "recover-smolvm"
            write_stub(recover, RECOVER)
            recover_out = folder / "recover.json"
            proc = self.run_probe(recover, recover_out, folder / "recover-base", sha256_file(recover))
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            body = json.loads(recover_out.read_text(encoding="utf-8"))
            self.assertTrue(body["sentinel_unchanged"])
            self.assertEqual(body["guest_escapes_blocked"], 3)

    def test_missing_image_line_is_not_a_pass_when_required(self) -> None:
        with tempfile.TemporaryDirectory(prefix="smolvm-image-") as raw:
            folder = Path(raw)
            bare = folder / "bare-smolvm"
            write_stub(bare, NO_IMAGE)
            out = folder / "bare.json"
            proc = self.run_probe(
                bare, out, folder / "base", sha256_file(bare), require_image=True
            )
            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            body = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("pinned image", body["reason"])
            self.assertEqual(body["guest_escapes_blocked"], 3)

            recover = folder / "recover-smolvm"
            write_stub(recover, RECOVER)
            recover_out = folder / "recover.json"
            proc = self.run_probe(
                recover,
                recover_out,
                folder / "recover-base",
                sha256_file(recover),
                require_image=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            body = json.loads(recover_out.read_text(encoding="utf-8"))
            self.assertTrue(body["image_evidence"].startswith("Using cached image "))

    def test_sha_mismatch_does_not_exec(self) -> None:
        with tempfile.TemporaryDirectory(prefix="smolvm-sha-") as raw:
            folder = Path(raw)
            stub = folder / "smolvm"
            write_stub(stub, LEAK)
            out = folder / "results.json"
            base = folder / "base"
            proc = self.run_probe(stub, out, base, "0" * 64)
            self.assertEqual(proc.returncode, 2, proc.stderr + proc.stdout)
            self.assertFalse((folder / "executed").exists())
            body = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("sha256", body["reason"])
            self.assertNotIn("guest_escapes_blocked", body)


if __name__ == "__main__":
    unittest.main()
