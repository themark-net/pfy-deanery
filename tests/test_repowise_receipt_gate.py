import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/repowise/run-on-main.sh"


class TestRepowiseReceiptGate(unittest.TestCase):
    def test_script_withholds_receipt_unless_ancestor_and_smoke_ok(self):
        text = Path("eval/integrate/repowise/run-on-main.sh").read_text()
        self.assertIn("origin/main", text)
        self.assertIn("smoke-repowise", text)
        self.assertIn("receipt.json", text)
        self.assertIn("ancestor", text)


def _git(repo: Path, *args: str, env: dict[str, str]) -> None:
    proc = subprocess.run(["git", "-C", str(repo), *args], env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)


def _git_env(base: dict[str, str]) -> dict[str, str]:
    env = dict(base)
    env["GIT_AUTHOR_NAME"] = "test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    return env


def _init_repo(repo: Path, env: dict[str, str], *, on_main: bool) -> str:
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", env=env)
    (repo / "README").write_text("fixture\n", encoding="utf-8")
    _git(repo, "add", "README", env=env)
    _git(repo, "commit", "-qm", "init", env=env)
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD", env=env)
    if not on_main:
        (repo / "README").write_text("ahead\n", encoding="utf-8")
        _git(repo, "add", "README", env=env)
        _git(repo, "commit", "-qm", "ahead", env=env)
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], env=env, text=True).strip()
    return sha


def _write_make(bin_dir: Path, rc: int) -> None:
    path = bin_dir / "make"
    path.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$*\" > \"$REPOWISE_MAKE_LOG\"\n"
        "printf '%s\\n' \"$TMPDIR\" > \"$REPOWISE_TMP_LOG\"\n"
        "exit {rc}\n".format(rc=rc),
        encoding="utf-8",
    )
    path.chmod(0o755)


def _link_tools(bin_dir: Path, names: list[str]) -> None:
    for name in names:
        source = shutil.which(name)
        if not source:
            raise AssertionError("missing tool: " + name)
        os.symlink(source, bin_dir / name)


def _run(repo: Path, receipt: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    run_env = dict(env)
    run_env["PFY_REPOWISE_LANE_MARKER"] = str(receipt.parent / "missing-marker")
    bash = shutil.which("bash")
    if not bash:
        raise AssertionError("bash is missing")
    return subprocess.run(
        [bash, str(SCRIPT), str(receipt)],
        cwd=repo,
        env=run_env,
        capture_output=True,
        text=True,
    )


class TestRepowiseReceiptGateBehavior(unittest.TestCase):
    def test_non_ancestor_writes_nothing_and_skips_smoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = _git_env(os.environ.copy())
            repo = tmp_path / "repo"
            _init_repo(repo, env, on_main=False)
            make_log = tmp_path / "make.log"
            env["REPOWISE_MAKE_LOG"] = str(make_log)
            env["REPOWISE_TMP_LOG"] = str(tmp_path / "tmp.log")
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir()
            _write_make(bin_dir, 0)
            env["PATH"] = str(bin_dir) + ":" + env["PATH"]
            receipt = tmp_path / "out" / "receipt.json"
            proc = _run(repo, receipt, env)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertFalse((tmp_path / "out").exists())
            self.assertFalse(make_log.exists())
            self.assertIn("not an ancestor", proc.stderr)

    def test_missing_origin_main_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = _git_env(os.environ.copy())
            repo = tmp_path / "repo"
            repo.mkdir()
            _git(repo, "init", "-q", env=env)
            (repo / "README").write_text("fixture\n", encoding="utf-8")
            _git(repo, "add", "README", env=env)
            _git(repo, "commit", "-qm", "init", env=env)
            receipt = tmp_path / "receipt.json"
            proc = _run(repo, receipt, env)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertIn("origin/main is missing", proc.stderr)

    def test_smoke_failure_writes_nothing_and_removes_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = _git_env(os.environ.copy())
            repo = tmp_path / "repo"
            _init_repo(repo, env, on_main=True)
            make_log = tmp_path / "make.log"
            tmp_log = tmp_path / "tmp.log"
            env["REPOWISE_MAKE_LOG"] = str(make_log)
            env["REPOWISE_TMP_LOG"] = str(tmp_log)
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir()
            _write_make(bin_dir, 3)
            env["PATH"] = str(bin_dir) + ":" + env["PATH"]
            receipt = repo / "eval" / "integrate" / "repowise" / "receipt.json"
            proc = _run(repo, receipt, env)
            self.assertEqual(proc.returncode, 3, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertFalse(receipt.parent.exists())
            self.assertEqual(make_log.read_text(encoding="utf-8").strip(), "smoke-repowise")
            smoke_tmp = tmp_log.read_text(encoding="utf-8").strip()
            self.assertIn("repowise-smoke.", smoke_tmp)
            self.assertFalse(Path(smoke_tmp).exists())
            self.assertIn("no receipt", proc.stderr)

    def test_timeout_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = _git_env(os.environ.copy())
            repo = tmp_path / "repo"
            _init_repo(repo, env, on_main=True)
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir()
            timeout_bin = bin_dir / "timeout"
            timeout_bin.write_text("#!/bin/sh\nexit 124\n", encoding="utf-8")
            timeout_bin.chmod(0o755)
            _write_make(bin_dir, 0)
            env["PATH"] = str(bin_dir) + ":" + env["PATH"]
            env["REPOWISE_MAKE_LOG"] = str(tmp_path / "make.log")
            receipt = tmp_path / "receipt.json"
            proc = _run(repo, receipt, env)
            self.assertEqual(proc.returncode, 124, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertFalse((tmp_path / "make.log").exists())
            self.assertIn("timeout", proc.stderr)

    def test_missing_make_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = _git_env(os.environ.copy())
            repo = tmp_path / "repo"
            _init_repo(repo, env, on_main=True)
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir()
            _link_tools(bin_dir, ["git", "timeout", "sed", "awk", "mktemp", "date", "grep", "head", "tr", "mkdir", "rm", "dirname"])
            env["PATH"] = str(bin_dir)
            receipt = tmp_path / "receipt.json"
            proc = _run(repo, receipt, env)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertIn("make is missing", proc.stderr)

    def test_smoke_exit_zero_writes_pipeline_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = _git_env(os.environ.copy())
            env["NOTASECRET_REPOWISE_REVIEW"] = "leak-me"
            repo = tmp_path / "repo"
            _init_repo(repo, env, on_main=True)
            pins = repo / "examples" / "repowise"
            pins.mkdir(parents=True)
            (pins / "pins.env").write_text("REPOWISE_PIP_SPEC=repowise==0.30.0\n", encoding="utf-8")
            _git(repo, "add", "examples/repowise/pins.env", env=env)
            _git(repo, "commit", "-qm", "pin", env=env)
            _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD", env=env)
            sha = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                env=env,
                text=True,
            ).strip()
            make_log = tmp_path / "make.log"
            tmp_log = tmp_path / "tmp.log"
            env["REPOWISE_MAKE_LOG"] = str(make_log)
            env["REPOWISE_TMP_LOG"] = str(tmp_log)
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir()
            _write_make(bin_dir, 0)
            env["PATH"] = str(bin_dir) + ":" + env["PATH"]
            receipt = repo / "eval" / "integrate" / "repowise" / "receipt.json"
            proc = _run(repo, receipt, env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(receipt.is_file())
            doc = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(doc["slug"], "repowise")
            self.assertEqual(doc["run_kind"], "pipeline")
            self.assertEqual(doc["main_sha"], sha)
            self.assertEqual(len(doc["main_sha"]), 40)
            self.assertEqual(doc["outcome"], "ok")
            self.assertEqual(doc["tool_version"], "repowise==0.30.0")
            self.assertIn("smoke-repowise", doc["did"])
            self.assertTrue(doc["run_id"])
            self.assertTrue(doc["started"])
            self.assertTrue(doc["finished"])
            blob = receipt.read_text(encoding="utf-8") + proc.stdout + proc.stderr
            self.assertNotIn("leak-me", blob)
            self.assertEqual(make_log.read_text(encoding="utf-8").strip(), "smoke-repowise")
            smoke_tmp = Path(tmp_log.read_text(encoding="utf-8").strip())
            self.assertFalse(smoke_tmp.exists())
            self.assertEqual(list(receipt.parent.glob(".receipt.*")), [])
            status = subprocess.check_output(
                ["git", "-C", str(repo), "status", "--porcelain", "-uall"],
                env=env,
                text=True,
            )
            self.assertEqual(status.strip(), "?? eval/integrate/repowise/receipt.json")


if __name__ == "__main__":
    unittest.main()
