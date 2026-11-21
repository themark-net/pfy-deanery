#!/usr/bin/env python3
"""Git environment for lane copy-back and the lane drivers (issue #11).

Failure: a missing git binary, a caller PATH, or a planted git env can
escape the copy-back or point a worktree check at the wrong repository.
Recovery: copy-back refuses with the lane-cage refusal line and exit 2
(drivers park that as copy-back refused), and worktree checks keep reading
the real worktree with a throwaway HOME.
"""
from __future__ import annotations

import io
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import lane_cage  # noqa: E402

READ_TOKENS = {
    "status",
    "diff",
    "hash-object",
    "rev-parse",
    "show",
    "merge-base",
    "symbolic-ref",
}


def _real_git() -> str:
    found = shutil.which("git")
    if not found:
        raise AssertionError("git is required for these tests")
    return found


def _git(cwd, *args, env=None):
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        [_real_git(), *args], cwd=cwd, env=run_env, check=True,
        capture_output=True, text=True,
    ).stdout


def _init_repo(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.email", "t@example.com")
    _git(path, "config", "user.name", "T")
    (path / "README").write_text("base\n", encoding="utf-8")
    _git(path, "add", "README")
    _git(path, "commit", "-qm", "base")
    return _git(path, "rev-parse", "HEAD").strip()


def _object_snapshot(repo: Path) -> dict:
    objects = repo / ".git" / "objects"
    snap = {}
    if not objects.is_dir():
        return snap
    for path in objects.rglob("*"):
        if path.is_file():
            snap[path.relative_to(objects).as_posix()] = path.read_bytes()
    return snap


def _write_recording_git(bindir: Path, log: Path) -> Path:
    bindir.mkdir(parents=True, exist_ok=True)
    script = bindir / "git"
    script.write_text(
        "#!/bin/sh\n"
        "log=%s\n"
        "parent=$(tr '\\0' ' ' < /proc/$PPID/cmdline 2>/dev/null || true)\n"
        "printf '%%s\\n' \"PARENT=$parent\" >> \"$log\"\n"
        "printf '%%s\\n' \"ARGS=$*\" >> \"$log\"\n"
        "printf '%%s\\n' \"ARGV0=$0\" >> \"$log\"\n"
        "printf '%%s\\n' \"GIT_DIR=${GIT_DIR-unset}\" >> \"$log\"\n"
        "printf '%%s\\n' \"GIT_TRACE=${GIT_TRACE-unset}\" >> \"$log\"\n"
        "printf '%%s\\n' \"GIT_CONFIG_PARAMETERS=${GIT_CONFIG_PARAMETERS-unset}\" >> \"$log\"\n"
        "printf '%%s\\n' \"XDG_CONFIG_HOME=${XDG_CONFIG_HOME-unset}\" >> \"$log\"\n"
        "printf '%%s\\n' \"HOME=${HOME-unset}\" >> \"$log\"\n"
        "printf '%%s\\n' '---' >> \"$log\"\n"
        "exec %s \"$@\"\n" % (shlex.quote(str(log)), shlex.quote(_real_git())),
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def _bash_read_commands(log_text: str, script_name: str) -> list[str]:
    found = []
    for block in log_text.split("---\n"):
        parent = ""
        args = ""
        for line in block.splitlines():
            if line.startswith("PARENT="):
                parent = line[len("PARENT="):]
            elif line.startswith("ARGS="):
                args = line[len("ARGS="):]
        if script_name not in parent:
            continue
        parts = args.split()
        if any(part in READ_TOKENS for part in parts):
            found.append(args)
    return found


def _planted_home(td: Path, trace_target: Path | None) -> Path:
    home = td / "planted-home"
    (home / ".config" / "git").mkdir(parents=True)
    lines = [
        "[user]",
        "  name = PlantedIdentity",
        "  email = planted@example.com",
        "[alias]",
        "  planted = !true",
    ]
    if trace_target is not None:
        lines += ["[trace2]", "  eventTarget = %s" % trace_target]
    (home / ".gitconfig").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (home / ".config" / "git" / "config").write_text(
        "[user]\n  name = XdgPlanted\n", encoding="utf-8",
    )
    return home


def _plant_env(base: dict, td: Path, other: Path, home: Path, trace: Path) -> dict:
    env = dict(base)
    env["GIT_DIR"] = str(other / ".git")
    env["GIT_WORK_TREE"] = str(other)
    env["GIT_INDEX_FILE"] = str(td / "planted.index")
    env["GIT_CONFIG_PARAMETERS"] = "'core.commentChar=;'"
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "core.commentChar"
    env["GIT_CONFIG_VALUE_0"] = ";"
    env["GIT_TRACE"] = str(trace)
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


class LaneGitEnvTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self._saved_safe = lane_cage._SAFE_GIT_PATH
        self._saved_cache = getattr(lane_cage, "_git_bin_cache", None)

    def tearDown(self):
        lane_cage._SAFE_GIT_PATH = self._saved_safe
        if hasattr(lane_cage, "_git_bin_cache"):
            lane_cage._git_bin_cache = self._saved_cache
        reset = getattr(lane_cage, "_reset_git_bin_cache", None)
        if callable(reset) and not hasattr(self, "_keep_cache"):
            reset()
            lane_cage._SAFE_GIT_PATH = self._saved_safe
        self.tmp.cleanup()

    def _reset_resolver(self, safe_path: str) -> None:
        lane_cage._SAFE_GIT_PATH = safe_path
        reset = getattr(lane_cage, "_reset_git_bin_cache", None)
        if callable(reset):
            reset()

    def test_missing_git_at_finalize_refuses_copy_back(self):
        """A cage that exits 0 must still refuse when git is gone at finalize.

        Fail: FileNotFoundError (or any raw OSError) leaves the process with
        a traceback. Recover: lane_cage exits 2, stderr names the copy-back
        refusal, and the shared refs and objects stay as they were.
        """
        repo = self.td / "repo"
        sha = _init_repo(repo)
        before_objects = _object_snapshot(repo)
        before_head = (repo / ".git" / "HEAD").read_text(encoding="utf-8")
        bindir = self.td / "git-bin"
        bindir.mkdir()
        wrapper = bindir / "git"
        wrapper.write_text(
            "#!/bin/sh\nexec %s \"$@\"\n" % shlex.quote(_real_git()),
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        vanish = self.td / "vanish.sh"
        vanish.write_text(
            "#!/bin/sh\nrm -f %s\nexit 0\n" % shlex.quote(str(wrapper)),
            encoding="utf-8",
        )
        vanish.chmod(0o755)
        self._reset_resolver(str(bindir))
        err = io.StringIO()
        try:
            with redirect_stderr(err):
                rc = lane_cage.main(
                    ["exec", "--wt", str(repo), "--", "sh", str(vanish)],
                )
        except OSError as exc:
            self.fail("git failure leaked as %s" % type(exc).__name__)
        text = err.getvalue()
        self.assertEqual(rc, 2, text)
        self.assertIn("lane-cage: copy-back refused:", text)
        self.assertNotIn("Traceback", text)
        self.assertNotIn("unavailable", text.lower())
        self.assertEqual(_git(repo, "rev-parse", "HEAD").strip(), sha)
        self.assertEqual((repo / ".git" / "HEAD").read_text(encoding="utf-8"), before_head)
        self.assertEqual(_object_snapshot(repo), before_objects)

    def test_absolute_git_and_throwaway_home_for_host_pack_query(self):
        """Host, pack, and query git must use the pinned binary and a throwaway HOME.

        Fail: git is invoked by a bare name on the caller PATH, or HOME /
        XDG_CONFIG_HOME from the caller reach those helpers. Recover: every
        helper runs the absolute git from the fixed safe path, the planted
        identity config is not read, and a valid copy-back still lands.
        """
        repo = self.td / "repo"
        _init_repo(repo)
        wt = self.td / "lane"
        _git(repo, "worktree", "add", "-q", "-b", "lane", str(wt), "main")
        cage = self.td / "cage"
        cage.mkdir()
        log = self.td / "git-env.log"
        bindir = self.td / "safe-git"
        wrapper = _write_recording_git(bindir, log)
        home = _planted_home(self.td, self.td / "home-trace2")
        xdg = home / ".config"
        planted = {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(xdg),
            "GIT_DIR": str(self.td / "missing-git-dir"),
            "GIT_TRACE": str(self.td / "caller-git-trace"),
        }
        saved = {key: os.environ.get(key) for key in planted}
        self._reset_resolver(str(bindir))
        os.environ.update(planted)
        try:
            store = lane_cage.prepare_git_store(wt, cage)
            (wt / "work.txt").write_text("from the lane\n", encoding="utf-8")
            # The overlay commit is the simulated cage commit, not a host helper.
            # Give it a clean env so it cannot write the planted trace markers.
            commit_home = self.td / "commit-home"
            commit_home.mkdir()
            commit_env = {
                "PATH": os.environ.get("PATH", ""),
                "HOME": str(commit_home),
                "GIT_OBJECT_DIRECTORY": str(store.objects),
                "GIT_AUTHOR_NAME": "T",
                "GIT_AUTHOR_EMAIL": "t@example.com",
                "GIT_COMMITTER_NAME": "T",
                "GIT_COMMITTER_EMAIL": "t@example.com",
            }
            subprocess.run(
                [_real_git(), "--git-dir", str(store.overlay), "--work-tree", str(wt),
                 "add", "work.txt"],
                check=True, capture_output=True, text=True, env=commit_env,
            )
            subprocess.run(
                [_real_git(), "--git-dir", str(store.overlay), "--work-tree", str(wt),
                 "-c", "user.email=t@example.com", "-c", "user.name=T",
                 "commit", "-qm", "lane work"],
                check=True, capture_output=True, text=True, env=commit_env,
            )
            lane_cage.finalize_git_store(store)
            argv = lane_cage.base_run(
                "podman", "localhost/pfy-test:3.12", wt, cage, "none", store,
            )
        finally:
            for key, prev in saved.items():
                if prev is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = prev
        self.assertIn("from the lane", _git(wt, "show", "HEAD:work.txt"))
        self.assertTrue(log.is_file(), "helpers did not run the safe-path git")
        blocks = [b for b in log.read_text(encoding="utf-8").split("---\n") if b.strip()]
        self.assertGreaterEqual(len(blocks), 2)
        for block in blocks:
            fields = {}
            for line in block.splitlines():
                if "=" in line:
                    key, val = line.split("=", 1)
                    fields[key] = val
            self.assertEqual(fields.get("ARGV0"), str(wrapper))
            self.assertTrue(os.path.isabs(fields.get("ARGV0", "")))
            self.assertNotEqual(fields.get("HOME"), str(home))
            self.assertTrue(fields.get("HOME"))
            self.assertNotEqual(fields.get("HOME"), os.environ.get("HOME"))
            self.assertEqual(fields.get("XDG_CONFIG_HOME"), "unset")
            self.assertEqual(fields.get("GIT_DIR"), "unset")
            self.assertEqual(fields.get("GIT_TRACE"), "unset")
            self.assertEqual(fields.get("GIT_CONFIG_PARAMETERS"), "unset")
        self.assertFalse((self.td / "home-trace2").exists())
        self.assertFalse((self.td / "caller-git-trace").exists())
        joined = "\n".join(argv)
        self.assertNotIn("PlantedIdentity", joined)
        self.assertNotIn("XdgPlanted", joined)

    def test_prepare_finalize_subprocess_pins_git_and_drops_caller_env(self):
        """Every git subprocess in a prepare/finalize cycle uses the pinned env.

        Fail: a helper calls git by name, or passes the caller HOME or a
        caller GIT_* value. Recover: argv[0] is the absolute safe-path git
        and the recorded env does not carry those caller values. --print
        paths are included so identity lookup is covered too.
        """
        repo = self.td / "repo"
        _init_repo(repo)
        wt = self.td / "lane"
        _git(repo, "worktree", "add", "-q", "-b", "lane", str(wt), "main")
        cage = self.td / "cage"
        cage.mkdir()
        records = []
        real_run = subprocess.run
        real_popen = subprocess.Popen
        # The simulated cage commit uses subprocess too. Record only while
        # the lane_cage helpers are the caller, not that commit.
        recording = {"on": True}

        def spy_run(cmd, **kwargs):
            argv = list(cmd)
            env = kwargs.get("env")
            if recording["on"]:
                records.append((argv, None if env is None else dict(env)))
            return real_run(cmd, **kwargs)

        def spy_popen(cmd, **kwargs):
            argv = list(cmd)
            env = kwargs.get("env")
            if recording["on"]:
                records.append((argv, None if env is None else dict(env)))
            return real_popen(cmd, **kwargs)

        home = _planted_home(self.td, None)
        other = self.td / "other"
        _init_repo(other)
        planted = {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "GIT_DIR": str(other / ".git"),
            "GIT_WORK_TREE": str(other),
            "GIT_INDEX_FILE": str(self.td / "planted.index"),
            "GIT_CONFIG_PARAMETERS": "'user.name=PlantedName'",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "user.name",
            "GIT_CONFIG_VALUE_0": "PlantedName",
            "GIT_TRACE": str(self.td / "spy-trace"),
            "GIT_TEMPLATE_DIR": str(self.td / "tmpl"),
        }
        saved = {key: os.environ.get(key) for key in planted}
        caller_home = os.environ.get("HOME")
        os.environ.update(planted)
        try:
            with mock.patch.object(lane_cage.subprocess, "run", spy_run), \
                    mock.patch.object(lane_cage.subprocess, "Popen", spy_popen):
                store = lane_cage.prepare_git_store(wt, cage)
                commit_env = {
                    "PATH": os.environ.get("PATH", ""),
                    "HOME": caller_home or str(home),
                    "GIT_OBJECT_DIRECTORY": str(store.objects),
                    "GIT_AUTHOR_NAME": "T",
                    "GIT_AUTHOR_EMAIL": "t@example.com",
                    "GIT_COMMITTER_NAME": "T",
                    "GIT_COMMITTER_EMAIL": "t@example.com",
                }
                (wt / "work.txt").write_text("spy\n", encoding="utf-8")
                recording["on"] = False
                real_run(
                    [_real_git(), "--git-dir", str(store.overlay), "--work-tree", str(wt),
                     "add", "work.txt"],
                    check=True, capture_output=True, text=True, env=commit_env,
                )
                real_run(
                    [_real_git(), "--git-dir", str(store.overlay), "--work-tree", str(wt),
                     "-c", "user.email=t@example.com", "-c", "user.name=T",
                     "commit", "-qm", "spy"],
                    check=True, capture_output=True, text=True, env=commit_env,
                )
                # Pack path: copy a real pack into the private store.
                listed = real_run(
                    [_real_git(), "--git-dir", str(store.overlay), "rev-list", "--objects", "HEAD"],
                    check=True, capture_output=True, text=True, env=commit_env,
                ).stdout
                shas = "\n".join(line.split()[0] for line in listed.splitlines() if line) + "\n"
                packdir = store.objects / "pack"
                packdir.mkdir(parents=True, exist_ok=True)
                real_run(
                    [_real_git(), "--git-dir", str(store.overlay), "pack-objects", str(packdir / "pack")],
                    check=True, capture_output=True, text=True, env=commit_env, input=shas,
                )
                recording["on"] = True
                lane_cage.finalize_git_store(store)
                prompt = self.td / "p.txt"
                prompt.write_text("Follow the ticket.\n", encoding="utf-8")
                grok = self.td / "grok"
                grok.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                grok.chmod(0o755)
                err = io.StringIO()
                with redirect_stderr(err):
                    rc_exec = lane_cage.main(
                        ["exec", "--print", "--wt", str(wt), "--", "true"],
                    )
                    rc_grok = lane_cage.main(
                        ["grok", "--print", "--kind", "build", "--wt", str(wt),
                         "--prompt", str(prompt), "--grok", str(grok)],
                    )
        finally:
            for key, prev in saved.items():
                if prev is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = prev
        self.assertEqual(rc_exec, 0, err.getvalue())
        self.assertEqual(rc_grok, 0, err.getvalue())
        pinned = shutil.which("git", path=lane_cage._SAFE_GIT_PATH)
        self.assertTrue(pinned and os.path.isabs(pinned))
        git_records = []
        for argv, env in records:
            if not argv:
                continue
            name = os.path.basename(str(argv[0]))
            if name != "git":
                continue
            git_records.append((argv, env))
        self.assertGreaterEqual(len(git_records), 3)
        allowed_git = {
            "GIT_CONFIG_NOSYSTEM",
            "GIT_CONFIG_GLOBAL",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        }
        for argv, env in git_records:
            self.assertEqual(argv[0], pinned)
            self.assertTrue(os.path.isabs(argv[0]))
            self.assertIsNotNone(env, "git inherited the caller environment")
            self.assertNotEqual(env.get("HOME"), str(home), argv)
            self.assertNotEqual(env.get("HOME"), caller_home, argv)
            self.assertNotIn("XDG_CONFIG_HOME", env)
            for key, value in planted.items():
                if key in ("HOME", "XDG_CONFIG_HOME"):
                    continue
                self.assertNotEqual(env.get(key), value)
            for key in env:
                if key.startswith("GIT_") and key not in allowed_git:
                    self.fail("unexpected git env %s" % key)
        self.assertFalse((self.td / "spy-trace").exists())

    def _driver_git_log_asserts(self, log: Path, script_name: str, trace: Path):
        self.assertFalse(trace.exists(), "planted GIT_TRACE file was written")
        text = log.read_text(encoding="utf-8") if log.is_file() else ""
        reads = _bash_read_commands(text, script_name)
        self.assertEqual(reads, [], "driver worktree check used the caller git: %s" % reads)

    def test_lane_git_alone_ignores_caller_git_env(self):
        """lane_git is its own layer, even without lane_git_scrub_env.

        Fail: a driver that forgets the scrub reads a caller GIT_DIR /
        GIT_WORK_TREE repo, or git writes a planted trace file. Recover: the
        same call reports the real worktree head.
        """
        repo = self.td / "wt"
        sha = _init_repo(repo)
        other = self.td / "other"
        _init_repo(other)
        (other / "README").write_text("other\n", encoding="utf-8")
        _git(other, "commit", "-qam", "other")
        other_sha = _git(other, "rev-parse", "HEAD").strip()
        self.assertNotEqual(sha, other_sha)
        trace = self.td / "lane-git-trace"
        env = os.environ.copy()
        env.update({
            "GIT_DIR": str(other / ".git"),
            "GIT_WORK_TREE": str(other),
            "GIT_TRACE": str(trace),
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.hooksPath",
            "GIT_CONFIG_VALUE_0": str(self.td / "hooks"),
        })
        helper = ROOT / "scripts" / "lane_git_env.sh"
        proc = subprocess.run(
            ["bash", "-c", '. "$1"; lane_git -C "$2" rev-parse HEAD', "x", str(helper), str(repo)],
            capture_output=True, text=True, env=env, timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), sha)
        self.assertFalse(trace.exists(), "planted GIT_TRACE reached lane_git")

    def test_build_lane_checks_ignore_planted_git_env(self):
        """build_lane.sh must check the real worktree, not the caller git env.

        Fail: a planted GIT_DIR makes a non-repo look valid, or the check
        writes a HOME/GIT_TRACE marker. Recover: a real worktree still runs
        (same exit as a clean env) and a plain directory is refused.
        """
        from tests.test_eval_lane import write_grok

        repo = self.td / "wt"
        _init_repo(repo)
        other = self.td / "other"
        other_sha = _init_repo(other)
        prompt = self.td / "prompt.txt"
        prompt.write_text("Follow the ticket.\n", encoding="utf-8")
        grok = self.td / "bin" / "grok"
        write_grok(grok, "#!/bin/sh\nexit 0\n")
        script = ROOT / "scripts" / "build_lane.sh"
        log = self.td / "calls.log"
        bindir = self.td / "path-git"
        _write_recording_git(bindir, log)
        trace = self.td / "git-trace"
        home_trace = self.td / "home-trace2"
        home = _planted_home(self.td, home_trace)

        def run(env):
            return subprocess.run(
                ["bash", str(script), "--wt", str(repo), "--prompt", str(prompt),
                 "--log", str(self.td / "build.log")],
                capture_output=True, text=True, env=env, timeout=90,
            )

        clean = os.environ.copy()
        clean["PATH"] = str(grok.parent) + os.pathsep + clean.get("PATH", "")
        clean["PYTHONDONTWRITEBYTECODE"] = "1"
        control = run(clean)
        planted = _plant_env(clean, self.td, other, home, trace)
        planted["PATH"] = str(bindir) + os.pathsep + str(grok.parent) + os.pathsep + os.environ.get("PATH", "")
        # A preset resolver cache must not pick the binary.
        planted["_LANE_GIT_BIN"] = str(bindir / "git")
        planted["_LANE_GIT_BIN_KEY"] = "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"
        poisoned = run(planted)
        self.assertEqual(control.returncode, 0, control.stderr + control.stdout)
        self.assertEqual(poisoned.returncode, control.returncode, poisoned.stderr + poisoned.stdout)
        self._driver_git_log_asserts(log, "build_lane.sh", trace)
        self.assertFalse(home_trace.exists(), "worktree check read the caller HOME gitconfig")
        self.assertEqual(_git(other, "rev-parse", "HEAD").strip(), other_sha)

        plain_root = Path(tempfile.mkdtemp(prefix="pfyb11-plain-", dir="/var/tmp"))
        try:
            plain = plain_root / "plain"
            plain.mkdir()
            env = _plant_env(clean, self.td, repo, home, self.td / "trace-plain")
            env["PATH"] = clean["PATH"]
            refused = subprocess.run(
                ["bash", str(script), "--wt", str(plain), "--prompt", str(prompt)],
                capture_output=True, text=True, env=env, timeout=30,
            )
        finally:
            shutil.rmtree(plain_root, ignore_errors=True)
        self.assertEqual(refused.returncode, 2, refused.stderr + refused.stdout)
        self.assertIn("not a git worktree", refused.stderr)
        self.assertNotIn("copy-back refused", refused.stderr)

    def test_eval_and_integrate_checks_ignore_planted_git_env(self):
        """Eval and integrate worktree reads must ignore the caller git env.

        Fail: GIT_DIR redirects fetch or a later read, or a read command
        runs as the caller git and writes GIT_TRACE. Recover: the same exit
        as a clean run, and the driver script itself does not issue those
        reads through the caller PATH.
        """
        from tests.test_eval_lane import card, lane_env, make_fixture, write_grok, SCRIPT as EVAL
        from tests.test_integrate_lane_land import make_fixture as integ_fixture, SCRIPT as INTEG

        def assert_pair(script_name, control, poisoned, log, trace, label):
            self.assertEqual(
                control.returncode, poisoned.returncode,
                "%s control rc %s\n%s\npoisoned rc %s\n%s" % (
                    label, control.returncode, control.stderr + control.stdout,
                    poisoned.returncode, poisoned.stderr + poisoned.stdout,
                ),
            )
            self._driver_git_log_asserts(log, script_name, trace)

        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            clone, _bare = make_fixture(td, {"widget": card(
                "widget", integration_stage="I0", tier_ceiling="I0", evidence=[],
            )})
            grok = td / "bin" / "grok"
            write_grok(grok, textwrap.dedent("""\
                #!/bin/sh
                set -e
                prompt=""
                prev=""
                for arg in "$@"; do
                  if [ "$prev" = "--prompt-file" ]; then
                    prompt=$arg
                  fi
                  prev=$arg
                done
                if grep -q "Self-review" "$prompt"; then
                  exit 0
                fi
                mkdir -p eval/evals/widget
                cat > eval/evals/widget/VERDICT.json <<'EOF'
                {
                  "metric": "probe_score",
                  "threshold": 1,
                  "value_gate": "pass",
                  "modularity_gate": "pass",
                  "proposed_stage": "I3"
                }
                EOF
                printf '%s\\n' "report" > eval/evals/widget/REPORT.md
                git add eval/evals/widget
                git commit -m "eval verdict"
                exit 0
            """))
            state = td / "evalstate"
            clean = lane_env(td, grok, approve=True)
            clean["XAI_API_KEY"] = "dummy-not-a-key"
            control = subprocess.run(
                ["bash", str(EVAL), "--root", str(clone), "--state", str(state),
                 "--slug", "widget", "--date", "1108"],
                cwd=clone, env=clean, capture_output=True, text=True, timeout=120,
            )
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            clone, bare = make_fixture(td, {"widget": card(
                "widget", integration_stage="I0", tier_ceiling="I0", evidence=[],
            )})
            other = td / "other"
            other_sha = _init_repo(other)
            before = subprocess.check_output(
                [_real_git(), "--git-dir", str(bare), "rev-parse", "main"], text=True,
            ).strip()
            grok = td / "bin" / "grok"
            write_grok(grok, textwrap.dedent("""\
                #!/bin/sh
                set -e
                prompt=""
                prev=""
                for arg in "$@"; do
                  if [ "$prev" = "--prompt-file" ]; then
                    prompt=$arg
                  fi
                  prev=$arg
                done
                if grep -q "Self-review" "$prompt"; then
                  exit 0
                fi
                mkdir -p eval/evals/widget
                cat > eval/evals/widget/VERDICT.json <<'EOF'
                {
                  "metric": "probe_score",
                  "threshold": 1,
                  "value_gate": "pass",
                  "modularity_gate": "pass",
                  "proposed_stage": "I3"
                }
                EOF
                printf '%s\\n' "report" > eval/evals/widget/REPORT.md
                git add eval/evals/widget
                git commit -m "eval verdict"
                exit 0
            """))
            log = td / "calls.log"
            bindir = td / "path-git"
            _write_recording_git(bindir, log)
            trace = td / "git-trace"
            home = _planted_home(td, None)
            state = td / "evalstate"
            base = lane_env(td, grok, approve=True)
            base["XAI_API_KEY"] = "dummy-not-a-key"
            env = _plant_env(base, td, other, home, trace)
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            poisoned = subprocess.run(
                ["bash", str(EVAL), "--root", str(clone), "--state", str(state),
                 "--slug", "widget", "--date", "1108"],
                cwd=clone, env=env, capture_output=True, text=True, timeout=120,
            )
            assert_pair("eval_lane.sh", control, poisoned, log, trace, "eval")
            after = subprocess.check_output(
                [_real_git(), "--git-dir", str(bare), "rev-parse", "main"], text=True,
            ).strip()
            if control.returncode == 0:
                self.assertNotEqual(after, before)
            self.assertEqual(_git(other, "rev-parse", "HEAD").strip(), other_sha)

        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            clone, _bare = integ_fixture(td)
            grok = td / "bin" / "grok"
            write_grok(grok, "#!/bin/sh\nexit 0\n")
            env = {k: v for k, v in os.environ.items() if k != "PFY_OPS_ROOT"}
            env.update({
                "PFY_GROK_BIN": str(grok),
                "PFY_MODEL_LOCK": str(td / "model.lock"),
                "PFY_CLOUD_YES": "1",
                "PFY_CLOUD_MAX_USD": "99",
                "PFY_DCG_DISABLE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "XAI_API_KEY": "dummy-not-a-key",
                "GIT_TERMINAL_PROMPT": "0",
            })
            (clone / "tmp").mkdir(exist_ok=True)
            (clone / "tmp" / "TICKET-goodtool.md").write_text("goodtool ticket\n", encoding="utf-8")
            control = subprocess.run(
                ["bash", str(INTEG), "--root", str(clone), "--slug", "goodtool", "--date", "1108"],
                cwd=clone, env=env, capture_output=True, text=True, timeout=120,
            )
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            clone, _bare = integ_fixture(td)
            other = td / "other"
            other_sha = _init_repo(other)
            grok = td / "bin" / "grok"
            write_grok(grok, "#!/bin/sh\nexit 0\n")
            log = td / "calls.log"
            bindir = td / "path-git"
            _write_recording_git(bindir, log)
            trace = td / "git-trace"
            home = _planted_home(td, None)
            env = {k: v for k, v in os.environ.items() if k != "PFY_OPS_ROOT"}
            env.update({
                "PFY_GROK_BIN": str(grok),
                "PFY_MODEL_LOCK": str(td / "model.lock"),
                "PFY_CLOUD_YES": "1",
                "PFY_CLOUD_MAX_USD": "99",
                "PFY_DCG_DISABLE": "1",
                "GIT_TERMINAL_PROMPT": "0",
                "XAI_API_KEY": "dummy-not-a-key",
            })
            env = _plant_env(env, td, other, home, trace)
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            (clone / "tmp").mkdir(exist_ok=True)
            (clone / "tmp" / "TICKET-goodtool.md").write_text("goodtool ticket\n", encoding="utf-8")
            poisoned = subprocess.run(
                ["bash", str(INTEG), "--root", str(clone), "--slug", "goodtool", "--date", "1108"],
                cwd=clone, env=env, capture_output=True, text=True, timeout=120,
            )
            assert_pair("integrate_lane.sh", control, poisoned, log, trace, "integrate")
            self.assertEqual(_git(other, "rev-parse", "HEAD").strip(), other_sha)

    def test_loop_worktree_checks_ignore_planted_git_dir(self):
        """loop_worktree.sh toplevel checks must use the real worktree.

        Fail: GIT_DIR makes fetch or the second-run check use another repo.
        Recover: the command runs, the worktree belongs to the real repo,
        and the check is not a caller-PATH git.
        """
        from tests.test_loop_worktree_behavior import SCRIPT

        origin = self.td / "origin.git"
        repo = self.td / "repo"
        subprocess.check_call([_real_git(), "init", "--bare", "-b", "main", str(origin)])
        _init_repo(repo)
        _git(repo, "remote", "add", "origin", str(origin))
        _git(repo, "push", "-u", "origin", "main")
        other = self.td / "other"
        other_sha = _init_repo(other)
        log = self.td / "calls.log"
        bindir = self.td / "path-git"
        _write_recording_git(bindir, log)
        trace = self.td / "git-trace"
        home = _planted_home(self.td, None)
        wt = self.td / "wt"
        env = _plant_env(os.environ.copy(), self.td, other, home, trace)
        env["PFY_LOOP_REPO"] = str(repo)
        env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
        marker = self.td / "ran"
        first = subprocess.run(
            ["bash", str(SCRIPT), "--wt", str(wt), "--", "touch", str(marker)],
            capture_output=True, text=True, env=env, timeout=60,
        )
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        self.assertTrue(marker.is_file())
        top = _git(wt, "rev-parse", "--show-toplevel").strip()
        self.assertEqual(top, str(wt))
        common = _git(wt, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
        repo_common = _git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
        self.assertEqual(common, repo_common)
        second = subprocess.run(
            ["bash", str(SCRIPT), "--wt", str(wt), "--", "true"],
            capture_output=True, text=True, env=env, timeout=60,
        )
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        self._driver_git_log_asserts(log, "loop_worktree.sh", trace)
        self.assertEqual(_git(other, "rev-parse", "HEAD").strip(), other_sha)

    def test_missing_git_parks_lane_drivers_as_copy_back_refused(self):
        """Drivers must park a vanished git at finalize as copy-back refused.

        Fail: the raw missing-binary error becomes exit 5, a traceback, or
        'lane cage unavailable'. Recover: build_lane exits 6 and eval /
        integrate park with 'copy-back refused'. Shared refs do not move.
        """
        from tests.test_eval_lane import card, lane_env, make_fixture, write_grok, SCRIPT as EVAL
        from tests.test_integrate_lane_land import make_fixture as integ_fixture, SCRIPT as INTEG

        real_python = sys.executable
        runner = self.td / "lane_cage_runner.py"
        runner.write_text(
            "import importlib.util, os, sys\n"
            "args = sys.argv[1:]\n"
            "idx = next(i for i, a in enumerate(args) if str(a).endswith('lane_cage.py'))\n"
            "script = args[idx]\n"
            "rest = args[idx + 1:]\n"
            "spec = importlib.util.spec_from_file_location('lane_cage_under_test', script)\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "sys.modules[spec.name] = mod\n"
            "spec.loader.exec_module(mod)\n"
            "mod._SAFE_GIT_PATH = os.environ['PFY_TEST_SAFE_GIT_PATH']\n"
            "reset = getattr(mod, '_reset_git_bin_cache', None)\n"
            "if callable(reset):\n"
            "    reset()\n"
            "raise SystemExit(mod.main(rest))\n",
            encoding="utf-8",
        )
        bindir = self.td / "py"
        bindir.mkdir()
        wrapper = bindir / "python3"
        wrapper.write_text(
            "#!%s\n"
            "import os, sys\n"
            "real = os.environ['PFY_TEST_REAL_PYTHON']\n"
            "args = sys.argv[1:]\n"
            "if any(str(a).endswith('lane_cage.py') for a in args):\n"
            "    os.execv(real, [real, os.environ['PFY_TEST_LANE_CAGE_RUNNER'], *args])\n"
            "os.execv(real, [real, *args])\n" % real_python,
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        git_dir = self.td / "git-bin"
        git_dir.mkdir()
        git_wrap = git_dir / "git"
        git_wrap.write_text(
            "#!/bin/sh\nexec %s \"$@\"\n" % shlex.quote(_real_git()),
            encoding="utf-8",
        )
        git_wrap.chmod(0o755)
        grok_body = "#!/bin/sh\nrm -f \"$PFY_TEST_VANISH_GIT\"\nexit 0\n"

        def base_env():
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            env["PFY_TEST_REAL_PYTHON"] = real_python
            env["PFY_TEST_LANE_CAGE_RUNNER"] = str(runner)
            env["PFY_TEST_SAFE_GIT_PATH"] = str(git_dir)
            env["PFY_TEST_VANISH_GIT"] = str(git_wrap)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["XAI_API_KEY"] = "dummy-not-a-key"
            return env

        repo = self.td / "build-wt"
        sha = _init_repo(repo)
        before_objects = _object_snapshot(repo)
        prompt = self.td / "prompt.txt"
        prompt.write_text("Follow the ticket.\n", encoding="utf-8")
        grok = self.td / "grok-bin" / "grok"
        write_grok(grok, grok_body)
        blog = self.td / "build.log"
        env = base_env()
        env["PATH"] = str(grok.parent) + os.pathsep + env["PATH"]
        built = subprocess.run(
            ["bash", str(ROOT / "scripts" / "build_lane.sh"),
             "--wt", str(repo), "--prompt", str(prompt), "--log", str(blog)],
            capture_output=True, text=True, env=env, timeout=90,
        )
        blog_text = blog.read_text(encoding="utf-8") if blog.is_file() else ""
        combined = built.stderr + built.stdout + blog_text
        self.assertEqual(built.returncode, 6, combined)
        self.assertIn("lane-cage: copy-back refused:", blog_text)
        self.assertIn("copy-back refused", combined)
        self.assertNotIn("Traceback", combined)
        self.assertNotIn("unavailable", combined.lower())
        self.assertEqual(_git(repo, "rev-parse", "HEAD").strip(), sha)
        self.assertEqual(_object_snapshot(repo), before_objects)
        git_wrap.write_text(
            "#!/bin/sh\nexec %s \"$@\"\n" % shlex.quote(_real_git()),
            encoding="utf-8",
        )
        git_wrap.chmod(0o755)

        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            clone, bare = make_fixture(td, {"widget": card("widget")})
            before = subprocess.check_output(
                [_real_git(), "--git-dir", str(bare), "rev-parse", "main"], text=True,
            ).strip()
            grok = td / "bin" / "grok"
            write_grok(grok, grok_body)
            env = lane_env(td, grok, approve=True)
            env.update(base_env())
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            state = td / "evalstate"
            proc = subprocess.run(
                ["bash", str(EVAL), "--root", str(clone), "--state", str(state),
                 "--slug", "widget", "--date", "1108"],
                cwd=clone, env=env, capture_output=True, text=True, timeout=120,
            )
            parked = state / "widget.parked"
            self.assertTrue(parked.is_file(), proc.stderr + proc.stdout)
            reason = parked.read_text(encoding="utf-8")
            self.assertIn("copy-back refused", reason, proc.stderr[-4000:] + proc.stdout[-2000:])
            self.assertNotIn("unavailable", reason.lower())
            self.assertNotIn("Traceback", proc.stderr + proc.stdout)
            after = subprocess.check_output(
                [_real_git(), "--git-dir", str(bare), "rev-parse", "main"], text=True,
            ).strip()
            self.assertEqual(after, before)
        git_wrap.write_text(
            "#!/bin/sh\nexec %s \"$@\"\n" % shlex.quote(_real_git()),
            encoding="utf-8",
        )
        git_wrap.chmod(0o755)

        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            clone, bare = integ_fixture(td)
            before = subprocess.check_output(
                [_real_git(), "--git-dir", str(bare), "rev-parse", "main"], text=True,
            ).strip()
            grok = td / "bin" / "grok"
            write_grok(grok, grok_body)
            env = {k: v for k, v in os.environ.items() if k != "PFY_OPS_ROOT"}
            env.update({
                "PFY_GROK_BIN": str(grok),
                "PFY_MODEL_LOCK": str(td / "model.lock"),
                "PFY_CLOUD_YES": "1",
                "PFY_CLOUD_MAX_USD": "99",
                "PFY_DCG_DISABLE": "1",
                "XAI_API_KEY": "dummy-not-a-key",
                "GIT_TERMINAL_PROMPT": "0",
            })
            env.update(base_env())
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            (clone / "tmp").mkdir(exist_ok=True)
            (clone / "tmp" / "TICKET-goodtool.md").write_text("ticket\n", encoding="utf-8")
            proc = subprocess.run(
                ["bash", str(INTEG), "--root", str(clone), "--slug", "goodtool", "--date", "1108"],
                cwd=clone, env=env, capture_output=True, text=True, timeout=120,
            )
            parked = clone / "tmp" / "integrate" / "goodtool.parked"
            self.assertTrue(parked.is_file(), proc.stderr + proc.stdout)
            reason = parked.read_text(encoding="utf-8")
            self.assertIn("copy-back refused", reason, proc.stderr[-4000:] + proc.stdout[-2000:])
            self.assertNotIn("unavailable", reason.lower())
            self.assertNotIn("Traceback", proc.stderr + proc.stdout)
            after = subprocess.check_output(
                [_real_git(), "--git-dir", str(bare), "rev-parse", "main"], text=True,
            ).strip()
            self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
