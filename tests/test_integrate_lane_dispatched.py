import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = "grill-fixture-not-a-real-lane"


class DispatchedMarkerTest(unittest.TestCase):
    def test_second_start_exits_2_before_git_or_grok(self):
        script = ROOT / "scripts" / "integrate_lane.sh"
        marker = ROOT / "tmp" / "integrate" / f"{SLUG}.dispatched"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("busy\n")
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            log = td / "calls.log"
            bindir = td / "bin"
            bindir.mkdir()
            fake = "#!/bin/sh\nprintf '%s\\n' \"$0 $*\" >> " + str(log) + "\nexit 0\n"
            for name in ("git", "grok"):
                path = bindir / name
                path.write_text(fake)
                path.chmod(path.stat().st_mode | stat.S_IEXEC)
            env = os.environ.copy()
            env["PFY_MODEL_LOCK"] = str(td / "model.lock")
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            try:
                result = subprocess.run(
                    ["bash", str(script), "--slug", SLUG],
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            finally:
                marker.unlink(missing_ok=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(log.exists(), "git or grok ran: " + log.read_text() if log.exists() else "")

    def test_dry_run_skips_marker_grok_and_push(self):
        script = ROOT / "scripts" / "integrate_lane.sh"
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            log = td / "calls.log"
            bindir = td / "bin"
            bindir.mkdir()
            fake = "#!/bin/sh\nprintf '%s\\n' \"$0 $*\" >> " + str(log) + "\nexit 0\n"
            for name in ("git", "grok"):
                path = bindir / name
                path.write_text(fake)
                path.chmod(path.stat().st_mode | stat.S_IEXEC)
            env = os.environ.copy()
            env["PFY_MODEL_LOCK"] = str(td / "model.lock")
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            result = subprocess.run(
                ["bash", str(script), "--dry-run", "--slug", SLUG, "--root", str(td)],
                cwd=td,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(
                result.stdout.strip(),
                "dry-run slug=%s skip-card skip-marker skip-fetch skip-grok skip-apply skip-push"
                % SLUG,
            )
            self.assertFalse((td / "tmp" / "integrate" / f"{SLUG}.dispatched").exists())
            self.assertFalse(log.exists())


GUARD = "guard-fixture"


class I2BeforeMarkerTest(unittest.TestCase):
    """A non-I2, excluded, or parked slug must not create a dispatch marker.

    Failure: the marker used to be written first, so a bad start exited 2
    forever and a later good start could not run. Recovery: the refusal
    leaves every marker in place, and a later I2 start with no park file
    and no exclusion writes the marker. Git and Grok stay stubbed.
    """

    def _env(self, td, extra=None):
        log = td / "calls.log"
        bindir = td / "bin"
        bindir.mkdir(exist_ok=True)
        fake = "#!/bin/sh\nprintf '%s\\n' \"$0 $*\" >> " + str(log) + "\nexit 0\n"
        for name in ("git", "grok"):
            path = bindir / name
            if not path.exists():
                path.write_text(fake)
                path.chmod(path.stat().st_mode | stat.S_IEXEC)
        env = os.environ.copy()
        env.pop("PFY_LOOP_STATE", None)
        env.pop("PFY_LANE_FROM_LOOP", None)
        env["PFY_MODEL_LOCK"] = str(td / "model.lock")
        env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
        if extra:
            env.update(extra)
        return env, log

    def _others(self, td):
        mark = td / "tmp" / "integrate"
        mark.mkdir(parents=True, exist_ok=True)
        disp = mark / "other-unit.dispatched"
        park = mark / "other-unit.parked"
        disp.write_text("other-pid\n")
        park.write_text("leave-me\n")
        return disp, park

    def _card(self, td, body):
        path = td / "data" / "stages" / f"{GUARD}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        return path

    def _run(self, td, env, extra_args=None):
        script = ROOT / "scripts" / "integrate_lane.sh"
        args = ["bash", str(script), "--slug", GUARD, "--root", str(td), "--date", "1108"]
        if extra_args:
            args.extend(extra_args)
        return subprocess.run(
            args,
            cwd=td,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def _same_others(self, disp, park):
        self.assertEqual(disp.read_text(), "other-pid\n")
        self.assertEqual(park.read_text(), "leave-me\n")

    def test_non_i2_writes_no_marker_then_i2_dispatches_without_git(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            env, log = self._env(td)
            disp, park = self._others(td)
            marker = td / "tmp" / "integrate" / f"{GUARD}.dispatched"

            missing = self._run(td, env)
            self.assertEqual(missing.returncode, 1, missing.stderr)
            self.assertIn("missing-card", missing.stderr)
            self.assertFalse(marker.exists())
            self.assertFalse(log.exists())
            self._same_others(disp, park)

            self._card(td, "{\n")
            bad = self._run(td, env)
            self.assertEqual(bad.returncode, 1, bad.stderr)
            self.assertIn("malformed-card", bad.stderr)
            self.assertFalse(marker.exists())

            self._card(td, json.dumps({"name": GUARD, "integration_stage": "I0"}) + "\n")
            early = self._run(td, env)
            self.assertEqual(early.returncode, 1, early.stderr)
            self.assertIn("stage=I0", early.stderr)
            self.assertFalse(marker.exists())

            self._card(td, json.dumps({"name": GUARD, "integration_stage": "I3"}) + "\n")
            later = self._run(td, env)
            self.assertEqual(later.returncode, 1, later.stderr)
            self.assertIn("stage=I3", later.stderr)
            self.assertFalse(marker.exists())
            self.assertFalse(log.exists())
            self._same_others(disp, park)

            self._card(td, json.dumps({"name": GUARD, "integration_stage": "I2"}) + "\n")
            accepted = self._run(td, env)
            self.assertEqual(accepted.returncode, 1, accepted.stderr + accepted.stdout)
            self.assertIn("missing ticket", accepted.stderr)
            self.assertTrue(marker.is_file())
            self.assertTrue(marker.read_text().startswith("pid "))
            self.assertFalse(log.exists())
            self._same_others(disp, park)
            self.assertEqual(
                (td / "tmp" / "integrate" / f"{GUARD}.parked").read_text().strip(),
                "missing ticket",
            )

    def test_excluded_and_parked_refuse_then_a_clean_i2_dispatches(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            env, log = self._env(td)
            disp, park = self._others(td)
            marker = td / "tmp" / "integrate" / f"{GUARD}.dispatched"
            self._card(td, json.dumps({"name": GUARD, "integration_stage": "I2"}) + "\n")
            excl = td / "eval" / "catalog-queue" / "exclusions.tsv"
            excl.parent.mkdir(parents=True)
            excl.write_text("slug\treason\n" + GUARD + "\theld for the guard test\n")

            blocked = self._run(td, env)
            self.assertEqual(blocked.returncode, 1, blocked.stderr)
            self.assertIn("excluded: " + GUARD, blocked.stderr)
            self.assertFalse(marker.exists())
            self.assertFalse(log.exists())
            self._same_others(disp, park)

            excl.write_text("slug\treason\n")
            held = td / "tmp" / "integrate" / f"{GUARD}.parked"
            held.write_text("held\n")
            parked = self._run(td, env)
            self.assertEqual(parked.returncode, 1, parked.stderr)
            self.assertIn("parked: " + GUARD, parked.stderr)
            self.assertFalse(marker.exists())
            self.assertEqual(held.read_text(), "held\n")
            self._same_others(disp, park)

            held.unlink()
            loop = td / "loopstate"
            loop_park = loop / "integrate" / f"{GUARD}.parked"
            loop_park.parent.mkdir(parents=True)
            loop_park.write_text("loop-held\n")
            env["PFY_LOOP_STATE"] = str(loop)
            from_loop = self._run(td, env)
            self.assertEqual(from_loop.returncode, 1, from_loop.stderr)
            self.assertIn("parked: " + GUARD, from_loop.stderr)
            self.assertFalse(marker.exists())
            self.assertEqual(loop_park.read_text(), "loop-held\n")
            self._same_others(disp, park)

            loop_park.unlink()
            excl.write_text("nope\n")
            malformed = self._run(td, env)
            self.assertEqual(malformed.returncode, 1, malformed.stderr)
            self.assertIn("excluded: " + GUARD, malformed.stderr)
            self.assertIn("header must be slug and reason", malformed.stderr)
            self.assertFalse(marker.exists())
            self.assertFalse(log.exists())

            excl.write_text("slug\treason\n")
            accepted = self._run(td, env)
            self.assertEqual(accepted.returncode, 1, accepted.stderr + accepted.stdout)
            self.assertIn("missing ticket", accepted.stderr)
            self.assertTrue(marker.is_file())
            self.assertFalse(log.exists())
            self._same_others(disp, park)
            self.assertEqual(loop_park.exists(), False)

    def test_existing_marker_exits_2_even_when_the_card_is_not_i2(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            env, log = self._env(td)
            disp, park = self._others(td)
            self._card(td, json.dumps({"name": GUARD, "integration_stage": "I0"}) + "\n")
            marker = td / "tmp" / "integrate" / f"{GUARD}.dispatched"
            marker.write_text("busy\n")
            result = self._run(td, env)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("already dispatched", result.stderr)
            self.assertEqual(marker.read_text(), "busy\n")
            self.assertFalse(log.exists())
            self._same_others(disp, park)

    def test_dry_run_exits_before_the_card_check(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            env, log = self._env(td)
            disp, park = self._others(td)
            result = self._run(td, env, ["--dry-run"])
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(
                result.stdout.strip(),
                "dry-run slug=%s skip-card skip-marker skip-fetch skip-grok skip-apply skip-push"
                % GUARD,
            )
            self.assertFalse((td / "data" / "stages" / f"{GUARD}.json").exists())
            self.assertFalse((td / "tmp" / "integrate" / f"{GUARD}.dispatched").exists())
            self.assertFalse(log.exists())
            self._same_others(disp, park)

    def test_missing_guard_script_names_fall_open_and_still_runs_git(self):
        """A missing guard.sh used to mention only ordinary commands.

        Failure: the line hid that the built-in denylist was skipped, or
        the miss returned with no line on the other lanes. Recovery: stderr
        names the fall-open, git still runs, and a fetch failure parks.
        The stub records fetch and does not see a push.
        """
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            scripts = td / "driver" / "scripts"
            scripts.mkdir(parents=True)
            for name in ("integrate_lane.sh", "catalog_eval_queue.py"):
                dest = scripts / name
                shutil.copy2(ROOT / "scripts" / name, dest)
                dest.chmod(dest.stat().st_mode | stat.S_IEXEC)
            self.assertFalse((scripts / "integrations" / "dcg" / "guard.sh").exists())
            work = td / "work"
            card = work / "data" / "stages" / f"{GUARD}.json"
            card.parent.mkdir(parents=True)
            card.write_text(json.dumps({"name": GUARD, "integration_stage": "I2"}) + "\n")
            ticket = work / "tmp" / f"TICKET-{GUARD}.md"
            ticket.parent.mkdir(parents=True)
            ticket.write_text("ticket\n")
            log = td / "git.log"
            bindir = td / "bin"
            bindir.mkdir()
            git = bindir / "git"
            git.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$*\" >> " + str(log) + "\nexit 1\n",
                encoding="utf-8",
            )
            git.chmod(git.stat().st_mode | stat.S_IEXEC)
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            env["PFY_MODEL_LOCK"] = str(td / "model.lock")
            env.pop("PFY_LOOP_STATE", None)
            env.pop("PFY_DCG_DISABLE", None)
            proc = subprocess.run(
                [
                    "bash", str(scripts / "integrate_lane.sh"),
                    "--slug", GUARD,
                    "--root", str(work),
                    "--date", "1108",
                ],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            self.assertIn(
                "dcg-fallback: guard.sh missing; built-in denylist not applied; command unchanged",
                proc.stderr,
            )
            self.assertIn("parked: git fetch failed", proc.stderr)
            self.assertTrue(log.is_file(), proc.stderr)
            recorded = log.read_text(encoding="utf-8")
            self.assertIn("fetch", recorded)
            self.assertNotIn("push", recorded)
            self.assertTrue((work / "tmp" / "integrate" / f"{GUARD}.dispatched").is_file())
            self.assertFalse((work / "tmp" / "integrate" / f"{GUARD}.done").exists())
