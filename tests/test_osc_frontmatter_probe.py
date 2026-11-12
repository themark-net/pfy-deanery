"""Fail-closed stops for the opencode-skill-creator sandlock probe.

How this fails: a missing pin or a prefix that is not the tarball proposes
I1, and the I1 rules would move the card; or a trial record with a home
path stays in the public tree. How we recover: those stops write I0, do
not set sandbox, and delete the leaked record.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evals" / "opencode-skill-creator" / "osc_frontmatter_probe.py"


def load_probe():
    spec = importlib.util.spec_from_file_location("osc_frontmatter_probe", PROBE)
    if spec is None or spec.loader is None:
        raise RuntimeError("probe import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProbeStopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.probe = load_probe()
        self.saved = (self.probe.ROOT, self.probe.HERE, self.probe.PIN, os.environ.get("HOME"))
        self.tmp = Path(tempfile.mkdtemp(prefix="osc-probe-"))
        self.probe.ROOT = self.tmp / "repo"
        self.probe.HERE = self.probe.ROOT / "eval" / "evals" / "opencode-skill-creator"
        self.probe.HERE.mkdir(parents=True)
        os.environ["HOME"] = str(self.tmp / "home")

    def tearDown(self) -> None:
        self.probe.ROOT, self.probe.HERE, self.probe.PIN = self.saved[0], self.saved[1], self.saved[2]
        if self.saved[3] is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self.saved[3]
        shutil.rmtree(self.tmp, ignore_errors=True)

    def verdict(self) -> dict:
        return json.loads((self.probe.HERE / "VERDICT.json").read_text(encoding="utf-8"))

    def test_missing_pin_stays_i0_and_does_not_claim_sandlock(self) -> None:
        code = self.probe.main()
        body = self.verdict()
        self.assertEqual(code, 1)
        self.assertEqual(body["proposed_stage"], "I0")
        self.assertNotIn("sandbox", body)
        self.assertFalse((self.probe.ROOT / "eval" / "integrate").exists())

    def test_dist_mismatch_stays_i0_before_install(self) -> None:
        pack = Path(os.environ["HOME"]) / ".cache" / "pfy" / "tools" / "osc" / "pack"
        tarball = pack / "opencode-skill-creator-0.3.6.tgz"
        tarball.parent.mkdir(parents=True)
        payload = b"tarball-bytes"
        with tarfile.open(tarball, "w:gz") as tf:
            info = tarfile.TarInfo(name="package/dist/skill-creator.js")
            info.size = len(payload)
            tf.addfile(info, io.BytesIO(payload))
        digest = hashlib.sha256(tarball.read_bytes()).hexdigest()
        self.probe.PIN = digest
        prefix = Path(os.environ["HOME"]) / ".cache" / "pfy" / "tools" / "osc" / "prefix"
        pkg = prefix / "node_modules" / "opencode-skill-creator"
        (pkg / "dist").mkdir(parents=True)
        (pkg / "package.json").write_text(json.dumps({"version": "0.3.6"}) + "\n", encoding="utf-8")
        (pkg / "dist" / "skill-creator.js").write_bytes(b"other-bytes")
        code = self.probe.main()
        body = self.verdict()
        self.assertEqual(code, 1)
        self.assertEqual(body["proposed_stage"], "I0")
        self.assertNotIn("sandbox", body)
        self.assertIn("does not match", body["reason"])
        self.assertFalse((self.probe.ROOT / "tmp" / "osc-sandlock" / "stage" / "prefix").exists())

    def test_home_path_record_is_deleted(self) -> None:
        path = self.tmp / "sandbox-trial.json"
        leaked = "/" + "home" + "/example/cache"
        path.write_text(json.dumps({"reads": [leaked]}) + "\n", encoding="utf-8")
        self.assertTrue(self.probe.drop_home_record(path))
        self.assertFalse(path.exists())
        path.write_text('{"reads": ["./tmp/stage"]}\n', encoding="utf-8")
        self.assertFalse(self.probe.drop_home_record(path))
        self.assertTrue(path.is_file())

    def test_committed_eval_files_have_no_home_path_or_owner_name(self) -> None:
        paths = [
            "eval/evals/opencode-skill-creator/VERDICT.json",
            "eval/evals/opencode-skill-creator/osc_frontmatter_probe.py",
            "eval/evals/opencode-skill-creator/fixtures/good/SKILL.md",
            "eval/evals/opencode-skill-creator/fixtures/argument-hint/SKILL.md",
            "eval/evals/opencode-skill-creator/fixtures/disable-model/SKILL.md",
            "eval/evals/opencode-skill-creator/fixtures/bad-key/SKILL.md",
            "eval/evals/opencode-skill-creator/fixtures/bad-name/SKILL.md",
            "eval/evals/opencode-skill-creator/fixtures/shell-true/SKILL.md",
            "eval/evals/opencode-skill-creator/fixtures/missing/README.md",
            "eval/integrate/opencode-skill-creator/sandbox-trial.json",
            "tests/test_osc_frontmatter_probe.py",
        ]
        missing = [rel for rel in paths if not (ROOT / rel).is_file()]
        self.assertEqual(missing, [])
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_public_paths.py"), "--paths", *paths],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
