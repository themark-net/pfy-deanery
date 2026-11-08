import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/neatroots/run-on-main.sh"
FIXTURE = ROOT / "eval/integrate/neatroots/fixtures/trace.json"
CARD = ROOT / "data/stages/neatroots.json"
CACHE = Path.home() / ".cache/pfy/tools/neatroots"
PINNED_NODE = CACHE / "node/bin/node"
PINNED_APP = CACHE / "app"

CLEAN = '{"runs":[{"findings":[]}],"errors":[]}\n'
FINDINGS = (
    '{"runs":[{"findings":[{"check_id":"repeated-tool-call"}]}],"errors":[]}\n'
)

STUB_NODE = r"""#!/bin/sh
mode=
for arg in "$@"; do
  case "$arg" in
    --version) mode=version ;;
    check) mode=check ;;
  esac
done
if [ "$mode" = version ]; then
  if [ -n "${NEAT_VERSION_OUT+x}" ]; then
    printf '%s' "$NEAT_VERSION_OUT"
  else
    printf '%s\n' "0.2.9"
  fi
  exit 0
fi
if [ "$mode" = check ]; then
  if [ -n "${NEAT_CHECK_OUT:-}" ]; then
    printf '%s' "$NEAT_CHECK_OUT"
  fi
  exit "${NEAT_CHECK_RC:-0}"
fi
exit 2
"""


def _git(repo, *args):
    subprocess.check_call(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.email=lane@example.com",
            "-c",
            "user.name=lane",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        stdout=subprocess.DEVNULL,
    )


def _repo(td):
    repo = td / "repo"
    repo.mkdir()
    subprocess.check_call(["git", "init", "-q"], cwd=repo)
    dest = repo / "eval/integrate/neatroots/fixtures"
    dest.mkdir(parents=True)
    (dest / "trace.json").write_bytes(FIXTURE.read_bytes())
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "fixture")
    subprocess.check_call(
        ["git", "-C", str(repo), "update-ref", "refs/remotes/origin/main", "HEAD"]
    )
    return repo


def _stub(td):
    node = td / "node"
    node.write_text(STUB_NODE, encoding="utf-8")
    node.chmod(0o755)
    cli = td / "app/neatroots/dist/cli.js"
    cli.parent.mkdir(parents=True)
    cli.write_text("// stub\n", encoding="utf-8")
    return {"NEATROOTS_NODE": str(node), "NEATROOTS_APP": str(td / "app")}


def _env(repo, extra=None):
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "NEATROOTS_NODE", "NEATROOTS_APP"):
        env.pop(key, None)
    env["PFY_NEATROOTS_LANE_MARKER"] = str(repo / "missing-marker")
    if extra:
        env.update(extra)
    return env


def _run(repo, receipt, env, cwd=None, timeout=30):
    return subprocess.run(
        ["bash", str(SCRIPT), str(receipt)],
        cwd=cwd or repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestNeatrootsReceiptBehavior(unittest.TestCase):
    def test_usage_exits_2(self):
        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 2, proc.stderr)

    def test_off_main_head_refuses_and_writes_nothing(self):
        # Behavior, not repo state: a checkout whose HEAD is not an ancestor
        # of origin/main must refuse, create no receipt, and leave an
        # existing receipt byte-identical.
        before = CARD.read_bytes()
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            repo = _repo(td)
            stub = _stub(td)
            _git(repo, "commit", "--allow-empty", "-qm", "not on main")
            receipt = td / "absent" / "receipt.json"
            env = _env(repo, {**stub, "NEAT_CHECK_OUT": CLEAN})
            proc = _run(repo, receipt, env)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertIn("not an ancestor", proc.stderr)
            self.assertFalse(receipt.parent.exists())
            existing = td / "existing.json"
            existing.write_text("keep\n", encoding="utf-8")
            again = _run(repo, existing, env)
            self.assertEqual(again.returncode, 1, again.stderr)
            self.assertEqual(existing.read_text(encoding="utf-8"), "keep\n")
        self.assertEqual(CARD.read_bytes(), before)

    def test_foreign_and_pidless_markers_exit_2(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            for body in ("pid 1\n", "dispatched\n"):
                marker = td / "marker"
                marker.write_text(body, encoding="utf-8")
                receipt = td / "receipt.json"
                receipt.write_text("keep\n", encoding="utf-8")
                env = _env(td, {"PFY_NEATROOTS_LANE_MARKER": str(marker)})
                proc = _run(ROOT, receipt, env)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("already dispatched", proc.stderr)
                self.assertEqual(receipt.read_text(encoding="utf-8"), "keep\n")

    def test_owning_lane_is_admitted_then_ancestry_refuses(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            marker = td / "marker"
            marker.write_text(f"pid {os.getpid()}\n", encoding="utf-8")
            receipt = td / "receipt.json"
            repo = _repo(td)
            stub = _stub(td)
            _git(repo, "commit", "--allow-empty", "-qm", "not on main")
            env = _env(repo, {**stub, "PFY_NEATROOTS_LANE_MARKER": str(marker)})
            proc = _run(repo, receipt, env)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertNotIn("already dispatched", proc.stderr)
            self.assertIn("not an ancestor", proc.stderr)
            self.assertFalse(receipt.exists())

    def test_closed_paths_write_no_receipt_and_a_clean_run_recovers(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            repo = _repo(td)
            stub = _stub(td)
            receipt = td / "receipt.json"
            receipt.write_text("keep\n", encoding="utf-8")

            missing = _run(
                repo,
                receipt,
                _env(repo, {**stub, "NEATROOTS_NODE": str(td / "no-such-node")}),
            )
            self.assertEqual(missing.returncode, 2, missing.stderr)
            self.assertEqual(receipt.read_text(encoding="utf-8"), "keep\n")

            empty_version = _run(
                repo,
                receipt,
                _env(repo, {**stub, "NEAT_VERSION_OUT": ""}),
            )
            self.assertEqual(empty_version.returncode, 1, empty_version.stderr)
            self.assertIn("version missing", empty_version.stderr)
            self.assertEqual(receipt.read_text(encoding="utf-8"), "keep\n")

            tool_exit = _run(
                repo,
                receipt,
                _env(repo, {**stub, "NEAT_CHECK_RC": "2"}),
            )
            self.assertEqual(tool_exit.returncode, 2, tool_exit.stderr)
            self.assertEqual(receipt.read_text(encoding="utf-8"), "keep\n")

            blank = _run(repo, receipt, _env(repo, stub))
            self.assertNotEqual(blank.returncode, 0, blank.stderr)
            self.assertEqual(receipt.read_text(encoding="utf-8"), "keep\n")

            findings = _run(
                repo,
                receipt,
                _env(repo, {**stub, "NEAT_CHECK_OUT": FINDINGS}),
            )
            self.assertNotEqual(findings.returncode, 0, findings.stderr)
            self.assertIn("findings", findings.stderr)
            self.assertEqual(receipt.read_text(encoding="utf-8"), "keep\n")

            fake_bin = td / "bin"
            fake_bin.mkdir()
            timeout_bin = fake_bin / "timeout"
            timeout_bin.write_text(
                "#!/bin/sh\nif [ \"$1\" = \"60\" ]; then exit 124; fi\nexit 125\n",
                encoding="utf-8",
            )
            timeout_bin.chmod(0o755)
            timed = _run(
                repo,
                receipt,
                _env(
                    repo,
                    {
                        **stub,
                        "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", ""),
                    },
                ),
            )
            self.assertEqual(timed.returncode, 124, timed.stderr)
            self.assertIn("timeout is not a pass", timed.stderr)
            self.assertEqual(receipt.read_text(encoding="utf-8"), "keep\n")

            caller = repo / "caller"
            caller.mkdir()
            relative = "lane-receipt.json"
            clean = _run(
                repo,
                relative,
                _env(repo, {**stub, "NEAT_CHECK_OUT": CLEAN}),
                cwd=caller,
            )
            self.assertEqual(clean.returncode, 0, clean.stderr)
            written = caller / relative
            self.assertTrue(written.is_file())
            self.assertFalse((repo / relative).exists())
            doc = json.loads(written.read_text(encoding="utf-8"))
            head = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            self.assertEqual(doc["slug"], "neatroots")
            self.assertEqual(doc["run_kind"], "pipeline")
            self.assertEqual(doc["main_sha"], head)
            self.assertEqual(len(doc["main_sha"]), 40)
            self.assertTrue(doc["run_id"])
            self.assertTrue(doc["started"])
            self.assertTrue(doc["finished"])
            self.assertEqual(doc["outcome"], "ok")
            self.assertEqual(doc["tool_version"], "0.2.9")
            self.assertIn("fixtures/trace.json", doc["did"])
            kept = written.read_bytes()

            _git(repo, "commit", "--allow-empty", "-qm", "not on main")
            missed = td / "missed.json"
            again = _run(
                repo,
                missed,
                _env(repo, {**stub, "NEAT_CHECK_OUT": CLEAN}),
            )
            self.assertEqual(again.returncode, 1, again.stderr)
            self.assertFalse(missed.exists())
            self.assertEqual(written.read_bytes(), kept)

    def test_pinned_check_on_the_fixture_writes_a_receipt(self):
        if not os.access(PINNED_NODE, os.X_OK) or not (PINNED_APP / "neatroots/dist/cli.js").is_file():
            self.skipTest("pinned neatroots is absent")
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            repo = _repo(td)
            receipt = td / "receipt.json"
            proc = _run(
                repo,
                receipt,
                _env(
                    repo,
                    {
                        "NEATROOTS_NODE": str(PINNED_NODE),
                        "NEATROOTS_APP": str(PINNED_APP),
                    },
                ),
                timeout=90,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            doc = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(doc["slug"], "neatroots")
            self.assertEqual(doc["run_kind"], "pipeline")
            self.assertEqual(doc["outcome"], "ok")
            self.assertEqual(doc["tool_version"], "0.2.9")
            self.assertIn("offline", doc["did"])


if __name__ == "__main__":
    unittest.main()
