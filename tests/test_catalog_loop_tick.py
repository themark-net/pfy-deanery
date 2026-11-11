"""One catalog loop tick against a local bare remote and a systemd-run stub.

No network and no model. The tick is the real scripts/catalog_loop.sh, which
prepares a worktree with scripts/loop_worktree.sh.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
LOOP = ROOT / "scripts" / "catalog_loop.sh"
COPY_REL = (
    "scripts/catalog_loop.sh",
    "scripts/supersede_check.py",
    "scripts/supersede_recheck_lane.sh",
    "data/supersede-watchlist.json",
    "scripts/catalog_counts.py",
    "scripts/catalog_eval_queue.py",
    "scripts/catalog_apply_verdict.py",
    "scripts/catalog_auto_raise.py",
    "scripts/promotion_rules.py",
    "scripts/catalog_fit_triage.py",
    "scripts/pfy_jev_230.py",
    "data/promotion-rules.json",
    "scripts/catalog_needs_mark.py",
    "scripts/catalog_park_retry.py",
    "scripts/ops_paths.py",
    "scripts/catalog_card_guard.py",
    "scripts/integrate_intake.py",
    "scripts/catalog_check.py",
    "pfylib/__init__.py",
    "pfylib/model_choice.py",
    "config/model-choice.json",
    "data/model-prices.json",
    "pfylib/stage_registry.py",
    "pfylib/registry.py",
)


def card(slug, **extra):
    body = {
        "name": slug,
        "integration_stage": "I0",
        "intent": "staged_evaluation",
        "next_gate": "eval",
        "entry": "",
        "uses": "format logs",
        "features": [],
        "tags": [],
        "potential": "ambiguous",
        "non_goals": ["no install"],
        "evidence": [],
        "tier_ceiling": "I1",
        "risk_class": "none",
    }
    body.update(extra)
    return body


def git(repo, *args):
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "Lane",
        "GIT_AUTHOR_EMAIL": "lane@example.com",
        "GIT_COMMITTER_NAME": "Lane",
        "GIT_COMMITTER_EMAIL": "lane@example.com",
        "GIT_TERMINAL_PROMPT": "0",
    })
    subprocess.check_call(["git", *args], cwd=repo, env=env)


def write_stub(path: Path, log: Path, code: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/bin/sh\nprintf '%%s\\n' \"$*\" >> '%s'\nexit %s\n" % (log, code),
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def build_repo(td: Path, cards: dict[str, dict]) -> Path:
    seed = td / "seed"
    bare = td / "origin.git"
    clone = td / "clone"
    seed.mkdir()
    subprocess.check_call(["git", "init", "-b", "main", str(seed)])
    git(seed, "config", "user.email", "lane@example.com")
    git(seed, "config", "user.name", "Lane")
    for rel in COPY_REL:
        dest = seed / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dest)
    os.chmod(seed / "scripts" / "catalog_loop.sh", 0o755)
    os.chmod(seed / "scripts" / "supersede_recheck_lane.sh", 0o755)
    stages = seed / "data" / "stages"
    stages.mkdir(parents=True)
    (stages / "_registry.json").write_text('{"version": "1"}\n', encoding="utf-8")
    for slug, body in cards.items():
        (stages / f"{slug}.json").write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    queue = seed / "eval" / "catalog-queue"
    queue.mkdir(parents=True)
    (queue / "exclusions.tsv").write_text("slug\treason\nzz-mark\tneeds the operator\n", encoding="utf-8")
    # Match the real repo: lane tickets live under tmp/ and must not look like catalog output.
    (seed / ".gitignore").write_text("tmp/\n", encoding="utf-8")
    verdict = seed / "eval" / "evals" / "aa-raise" / "VERDICT.json"
    verdict.parent.mkdir(parents=True, exist_ok=True)
    verdict.write_text(json.dumps({
        "metric": "probe_score",
        "threshold": 1,
        "value_gate": "pass",
        "modularity_gate": "pass",
        "proposed_stage": "I2",
    }, indent=2) + "\n", encoding="utf-8")
    git(seed, "add", ".")
    git(seed, "commit", "-m", "seed")
    subprocess.check_call(["git", "init", "--bare", str(bare)])
    git(seed, "remote", "add", "origin", str(bare))
    git(seed, "push", "-u", "origin", "main")
    subprocess.check_call(["git", "--git-dir", str(bare), "symbolic-ref", "HEAD", "refs/heads/main"])
    subprocess.check_call(["git", "clone", str(bare), str(clone)])
    git(clone, "config", "user.email", "lane@example.com")
    git(clone, "config", "user.name", "Lane")
    return clone


def run_tick(td: Path, clone: Path, code: int = 0, ops: Path | None = None, extra: dict | None = None):
    state = td / "state"
    wt = td / "wt"
    for name in ("integrate", "integrate2", "evq"):
        (td / name).mkdir(exist_ok=True)
    state.mkdir(exist_ok=True)
    log = td / "systemd.log"
    stub = td / "bin" / "systemd-run"
    write_stub(stub, log, code)
    env = os.environ.copy()
    env.update({
        "PFY_LOOP_STATE": str(state),
        "PFY_LOOP_REPO": str(clone),
        "PFY_LOOP_WT": str(wt),
        "PFY_LOOP_NO_PUSH": "1",
        "PFY_SYSTEMD_RUN": str(stub),
        "PFY_INTEGRATE_ROOT": str(td / "integrate"),
        "PFY_INTEGRATE2_ROOT": str(td / "integrate2"),
        "PFY_EVQ_ROOT": str(td / "evq"),
        "PFY_GROK_BIN": str(td / "bin" / "grok"),
        "PFY_DCG_DISABLE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_TERMINAL_PROMPT": "0",
    })
    env.pop("PFY_OPS_ROOT", None)
    for key in (
        "PFY_CATFIT_MOCK",
        "PFY_CATFIT_MODEL",
        "PFY_CATFIT_FALLBACK_MODEL",
        "PFY_CATFIT_HOST",
        "PFY_CATFIT_TIMEOUT",
        "PFY_CATFIT_PER_TICK",
    ):
        env.pop(key, None)
    if ops is not None:
        env["PFY_OPS_ROOT"] = str(ops)
    if extra:
        env.update(extra)
    proc = subprocess.run(
        ["bash", str(LOOP)],
        cwd=td,
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
    )
    return proc, state, wt, log


def open_integrate(slug):
    return card(
        slug,
        integration_stage="I2",
        tier_ceiling="I3",
        evidence=["probe:local"],
        potential="medium",
    )


class CatalogLoopTickTest(unittest.TestCase):
    def test_stop_exits_without_launching(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            state = td / "state"
            state.mkdir()
            (state / "STOP").write_text("stop\n", encoding="utf-8")
            log = td / "systemd.log"
            stub = td / "bin" / "systemd-run"
            write_stub(stub, log, 0)
            env = os.environ.copy()
            env["PFY_LOOP_STATE"] = str(state)
            env["PFY_LOOP_NO_PUSH"] = "1"
            env["PFY_SYSTEMD_RUN"] = str(stub)
            proc = subprocess.run(
                ["bash", str(LOOP)],
                cwd=td,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertFalse(log.exists())
            status = json.loads((state / "loop.latest.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "stopped")
            self.assertEqual(status["launched"], [])

    def test_launch_skips_and_second_tick_is_idle(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            cards = {
                "aa-evq": card("aa-evq"),
                "aa-gpu": card("aa-gpu", uses="needs a gpu"),
                "aa-huge": card("aa-huge", uses="pull a 37.6 GB pack"),
                "aa-i3": card("aa-i3", integration_stage="I3", tier_ceiling="I3", evidence=["probe:local"]),
                "aa-int": open_integrate("aa-int"),
                "aa-iopen": open_integrate("aa-iopen"),
                "aa-landed": open_integrate("aa-landed"),
                "aa-money": card("aa-money", risk_class="live-money"),
                "aa-raise": card("aa-raise"),
                "aa-sec": card("aa-sec", risk_class="security"),
                "aa-stay": card("aa-stay", integration_stage="I4", tier_ceiling="I4"),
                "aa-take": card("aa-take", risk_class="runtime-takeover"),
                "aa-unknown": card("aa-unknown", risk_class="mystery", uses=""),
                "zz-open": card("zz-open"),
            }
            clone = build_repo(td, cards)
            (td / "integrate2").mkdir()
            (td / "integrate2" / "aa-int.dispatched").write_text("pid 1\n", encoding="utf-8")
            (td / "integrate2" / "LANDED_aa-landed").write_text("abc\n", encoding="utf-8")
            (td / "evq").mkdir()
            (td / "evq" / "aa-evq.done").write_text("done\n", encoding="utf-8")
            (td / "state").mkdir()
            (td / "state" / "QUOTA_STOP.auto").write_text("stale\n", encoding="utf-8")
            proc, state, wt, log = run_tick(td, clone)
            blob = proc.stdout + "\n" + proc.stderr
            self.assertEqual(proc.returncode, 0, blob[-4000:])
            status = json.loads((state / "loop.latest.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "ok", blob[-2000:])
            self.assertFalse((state / "QUOTA_STOP.auto").exists())
            launched = set(status["launched"])
            # aa-sec: security scanner or guard, raised to I2 and launched under sandlock.
            self.assertEqual(launched, {"aa-iopen", "aa-raise", "aa-sec", "zz-open"})
            text = log.read_text(encoding="utf-8")
            self.assertIn("--unit=pfy-lane-integrate-aa-iopen", text)
            self.assertIn("--unit=pfy-lane-eval-aa-raise", text)
            self.assertIn("--unit=pfy-lane-eval-zz-open", text)
            self.assertIn("--property=Nice=10", text)
            self.assertEqual(text.count("--unit=pfy-lane-eval-zz-open"), 1)
            sec_line = [line for line in text.splitlines() if "pfy-lane-eval-aa-sec" in line]
            self.assertEqual(len(sec_line), 1, text)
            self.assertIn("PFY_LANE_SANDBOX=sandlock", sec_line[0])
            self.assertNotIn("PFY_LANE_SANDBOX", " ".join(line for line in text.splitlines() if "aa-sec" not in line))
            sec = json.loads((wt / "data" / "stages" / "aa-sec.json").read_text(encoding="utf-8"))
            self.assertEqual(sec["tier_ceiling"], "I2")
            self.assertEqual(sec["ceiling_history"][-1]["to"], "I2")
            for slug in ("aa-int", "aa-landed", "aa-evq", "aa-gpu", "aa-huge", "aa-money", "aa-take", "aa-unknown"):
                self.assertNotIn(slug, text, slug)
            ticket = (wt / "tmp" / "TICKET-aa-iopen.md").read_text(encoding="utf-8")
            self.assertIn("catalog-integrate-lane", ticket)
            self.assertIn("aa-iopen", ticket)
            raised = json.loads((wt / "data" / "stages" / "aa-raise.json").read_text(encoding="utf-8"))
            self.assertEqual(raised["tier_ceiling"], "I3")
            self.assertEqual(raised["ceiling_history"][-1]["by"], "catalog_loop")
            self.assertEqual(raised["ceiling_history"][-1]["to"], "I3")
            stayed = json.loads((wt / "data" / "stages" / "aa-i3.json").read_text(encoding="utf-8"))
            self.assertEqual(stayed["tier_ceiling"], "I3")
            self.assertEqual(stayed["integration_stage"], "I3")
            high = json.loads((wt / "data" / "stages" / "aa-stay.json").read_text(encoding="utf-8"))
            self.assertEqual(high["tier_ceiling"], "I4")
            # Operator queue: never in the public tree. Unset PFY_OPS_ROOT puts
            # it under the worktree's gitignored tmp/ops/.
            self.assertFalse((wt / "eval" / "catalog-queue" / "needs-mark.tsv").exists())
            needs = (wt / "tmp" / "ops" / "eval" / "catalog-queue" / "needs-mark.tsv").read_bytes()
            needs_text = needs.decode("utf-8")
            self.assertTrue(needs_text.startswith("slug\tkind\treason\tevidence\tsince\n"))
            self.assertNotIn(str(td), needs_text)
            # Only hard stops are rows, each naming its rule (data/promotion-rules.json).
            self.assertIn("aa-gpu\thard-stop\tHS-gpu-unapproved: ", needs_text)
            self.assertIn("aa-huge\thard-stop\tHS-pull-over-25gb-unapproved: ", needs_text)
            self.assertNotIn("aa-sec\t", needs_text)
            self.assertIn("aa-money\thard-stop\tHS-live-money: ", needs_text)
            self.assertIn("aa-take\thard-stop\tHS-runtime-takeover: ", needs_text)
            # Unknown risk and a demotion flag are failed rules, not rows.
            self.assertNotIn("aa-unknown\t", needs_text)
            self.assertNotIn("aa-i3\t", needs_text)
            self.assertNotIn("\naa-iopen\t", "\n" + needs_text)
            self.assertNotIn("\naa-int\t", "\n" + needs_text)
            log.write_text("", encoding="utf-8")
            again, state2, wt2, log2 = run_tick(td, clone)
            self.assertEqual(again.returncode, 0, (again.stdout + again.stderr)[-4000:])
            status2 = json.loads((state2 / "loop.latest.json").read_text(encoding="utf-8"))
            self.assertEqual(status2["launched"], [])
            self.assertEqual(log2.read_text(encoding="utf-8"), "")
            self.assertEqual((wt2 / "tmp" / "ops" / "eval" / "catalog-queue" / "needs-mark.tsv").read_bytes(), needs)

    def test_needs_mark_goes_to_the_ops_checkout_not_public(self):
        """Fail: needs-mark.tsv shows up in the public worktree or its commit list.
        Recovery: write it under PFY_OPS_ROOT and drop it from path_allowed."""
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            clone = build_repo(td, {"aa-gpu": card("aa-gpu", uses="needs a gpu"), "zz-open": card("zz-open")})
            ops = td / "ops"
            ops.mkdir()
            subprocess.check_call(["git", "init", "-q", "-b", "main"], cwd=ops)
            proc, state, wt, _log = run_tick(td, clone, ops=ops)
            blob = proc.stdout + "\n" + proc.stderr
            self.assertEqual(proc.returncode, 0, blob[-4000:])
            status = json.loads((state / "loop.latest.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "ok", blob[-2000:])
            self.assertEqual(status["errors"], [], blob[-2000:])
            text = (ops / "eval" / "catalog-queue" / "needs-mark.tsv").read_text(encoding="utf-8")
            self.assertIn("aa-gpu\thard-stop\tHS-gpu-unapproved: ", text)
            self.assertFalse((wt / "eval" / "catalog-queue" / "needs-mark.tsv").exists())
            self.assertFalse((wt / "tmp" / "ops").exists())
            self.assertIn("ops would commit eval/catalog-queue/needs-mark.tsv", blob)
            self.assertNotIn("needs-mark", subprocess.run(
                ["git", "status", "--porcelain", "-uall"], cwd=wt, capture_output=True, text=True,
            ).stdout)

    def test_daily_cap_writes_quota_stop_and_launches_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            clone = build_repo(td, {"zz-open": card("zz-open")})
            state = td / "state"
            state.mkdir()
            day = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y%m%d")
            (state / f"started-{day}").write_text("20\n", encoding="utf-8")
            proc, state, _wt, log = run_tick(td, clone)
            self.assertEqual(proc.returncode, 0, (proc.stdout + proc.stderr)[-4000:])
            status = json.loads((state / "loop.latest.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "quota")
            self.assertEqual(status["launched"], [])
            self.assertEqual(status["slots"], 0)
            self.assertTrue((state / "QUOTA_STOP.auto").is_file())
            self.assertFalse(log.exists())

    def test_running_cap_counts_integrate2_pids(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            clone = build_repo(td, {"zz-open": card("zz-open")})
            integrate2 = td / "integrate2"
            integrate2.mkdir()
            procs = []
            try:
                for name in ("p-one", "p-two", "p-three", "p-four"):
                    proc = subprocess.Popen(["sleep", "60"])
                    procs.append(proc)
                    (integrate2 / f"{name}.pid").write_text(f"{proc.pid} lane\n", encoding="utf-8")
                    (integrate2 / f"{name}.dispatched").write_text("lane\n", encoding="utf-8")
                tick, state, _wt, log = run_tick(td, clone)
            finally:
                for proc in procs:
                    proc.kill()
                    proc.wait()
            self.assertEqual(tick.returncode, 0, (tick.stdout + tick.stderr)[-4000:])
            status = json.loads((state / "loop.latest.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "ok")
            self.assertEqual(status["launched"], [])
            self.assertEqual(status["slots"], 0)
            self.assertEqual(len(status["running"]), 4)
            self.assertTrue(all(row["source"] == "integrate2" for row in status["running"]))
            self.assertFalse(log.exists())

    def test_systemd_failure_launches_nothing_further(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            clone = build_repo(td, {
                "aa-first": card("aa-first"),
                "zz-second": card("zz-second"),
            })
            proc, state, _wt, log = run_tick(td, clone, code=1)
            self.assertNotEqual(proc.returncode, 0, proc.stdout[-1500:] + proc.stderr[-1500:])
            status = json.loads((state / "loop.latest.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "error")
            self.assertTrue(status["errors"])
            self.assertTrue((state / "eval" / "aa-first.dispatched").is_file())
            self.assertFalse((state / "eval" / "zz-second.dispatched").exists())
            self.assertEqual(log.read_text(encoding="utf-8").count("--unit="), 1)

    def test_refused_is_unique_and_a_raised_slug_is_apply_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            passing = {
                "metric": "probe_score",
                "threshold": 1,
                "value_gate": "pass",
                "modularity_gate": "pass",
                "proposed_stage": "I2",
            }
            clone = build_repo(td, {
                "aa-both": card("aa-both"),
                "aa-dup": card("aa-dup", risk_class="live-money"),
            })
            both = clone / "eval" / "evals" / "aa-both" / "VERDICT.json"
            both.parent.mkdir(parents=True, exist_ok=True)
            both.write_text(json.dumps(passing, indent=2) + "\n", encoding="utf-8")
            dup_dir = clone / "eval" / "integrate" / "aa-dup"
            dup_dir.mkdir(parents=True)
            (dup_dir / "receipt.json").write_text("{}\n", encoding="utf-8")
            (dup_dir / "VERDICT.json").write_text(
                json.dumps(passing, indent=2) + "\n",
                encoding="utf-8",
            )
            git(clone, "add", ".")
            git(clone, "commit", "-m", "verdicts")
            git(clone, "push", "origin", "main")
            state = td / "state"
            (state / "eval").mkdir(parents=True)
            (state / "eval" / "LANDED_aa-both").write_text("landed\n", encoding="utf-8")
            (td / "integrate").mkdir()
            (td / "integrate2").mkdir()
            (td / "integrate" / "LANDED_aa-dup").write_text("landed\n", encoding="utf-8")
            (td / "integrate2" / "LANDED_aa-dup").write_text("landed\n", encoding="utf-8")
            proc, state, _wt, _log = run_tick(td, clone)
            self.assertEqual(proc.returncode, 0, (proc.stdout + proc.stderr)[-4000:])
            status = json.loads((state / "loop.latest.json").read_text(encoding="utf-8"))
            self.assertEqual(status["refused"], ["aa-dup"])
            self.assertNotIn("aa-both", status["refused"])
            self.assertEqual(status["apply_refused"], ["aa-dup", "aa-both"])
            self.assertIn("aa-both", status["auto_raised"])
            self.assertNotIn("aa-dup", status["auto_raised"])

    def test_integrate2_dispatched_skips_eval_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            clone = build_repo(td, {"zz-open": card("zz-open")})
            (td / "integrate2").mkdir()
            (td / "integrate2" / "zz-open.dispatched").write_text("pid 1\n", encoding="utf-8")
            proc, state, _wt, log = run_tick(td, clone)
            self.assertEqual(proc.returncode, 0, (proc.stdout + proc.stderr)[-4000:])
            status = json.loads((state / "loop.latest.json").read_text(encoding="utf-8"))
            self.assertNotIn("zz-open", status["launched"])
            self.assertIn("zz-open", status["skipped_taken"])
            text = log.read_text(encoding="utf-8") if log.exists() else ""
            self.assertNotIn("pfy-lane-eval-zz-open", text)

    def test_stale_watchlist_queues_one_recheck_per_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            clone = build_repo(td, {"zz-open": card("zz-open")})
            wl_path = clone / "data" / "supersede-watchlist.json"
            doc = json.loads(wl_path.read_text(encoding="utf-8"))
            for proj in doc["projects"]:
                proj["last_checked"] = "2020-01-01"
            wl_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            git(clone, "add", "data/supersede-watchlist.json")
            git(clone, "commit", "-m", "stale watchlist")
            git(clone, "push", "origin", "main")
            proc, state, _wt, log = run_tick(td, clone)
            self.assertEqual(proc.returncode, 0, (proc.stdout + proc.stderr)[-4000:])
            status = json.loads((state / "loop.latest.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "ok", (proc.stdout + proc.stderr)[-2000:])
            self.assertTrue(status["supersede_stale"])
            self.assertEqual(status["launched"][0], "supersede-recheck")
            self.assertIn("zz-open", status["launched"])
            text = log.read_text(encoding="utf-8")
            self.assertEqual(text.count("supersede_recheck_lane.sh"), 1)
            log.write_text("", encoding="utf-8")
            again, state2, _wt2, log2 = run_tick(td, clone)
            self.assertEqual(again.returncode, 0, (again.stdout + again.stderr)[-4000:])
            status2 = json.loads((state2 / "loop.latest.json").read_text(encoding="utf-8"))
            self.assertEqual(status2["launched"], [])
            self.assertNotIn("supersede_recheck_lane.sh", log2.read_text(encoding="utf-8") if log2.exists() else "")

    def test_tick_triages_i0_offline_safe_and_a_down_model_does_not_fail(self):
        """Fail: the tick calls Ollama, triages after the queue, or a broken
        local model aborts the tick. Recover: PFY_CATFIT_MOCK writes fit files
        before the queue (a confident skip drops the slug) and a refused
        Ollama logs one line and still exits 0."""
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            cards = {
                "aa-keep": card("aa-keep"),
                "bb-drop": card("bb-drop"),
                "cc-stay": card("cc-stay", integration_stage="I1", tier_ceiling="I2"),
                "zz-mark": card("zz-mark"),
            }
            clone = build_repo(td, cards)
            gate_dir = clone / "data" / "decision-gates"
            gate_dir.mkdir(parents=True)
            shutil.copy(
                ROOT / "data" / "decision-gates" / "catalog-fit.v0.json",
                gate_dir / "catalog-fit.v0.json",
            )
            git(clone, "add", "data/decision-gates/catalog-fit.v0.json")
            git(clone, "commit", "-m", "gate")
            git(clone, "push", "origin", "main")
            mock = td / "mock.json"
            mock.write_text(json.dumps({
                "aa-keep": {
                    "slug": "aa-keep",
                    "fit": True,
                    "overlap_with": None,
                    "verdict": "fit",
                    "reason": "loop mock",
                    "confidence": 1,
                },
                "bb-drop": {
                    "slug": "bb-drop",
                    "fit": False,
                    "overlap_with": None,
                    "verdict": "skip_install",
                    "reason": "loop mock",
                    "confidence": 1,
                },
            }), encoding="utf-8")
            safe = {
                "PFY_CATFIT_MOCK": str(mock),
                "PFY_CATFIT_HOST": "http://127.0.0.1:9",
                "PFY_CATFIT_TIMEOUT": "1",
            }
            proc, state, wt, _log = run_tick(td, clone, extra=safe)
            blob = proc.stdout + "\n" + proc.stderr
            self.assertEqual(proc.returncode, 0, blob[-4000:])
            status = json.loads((state / "loop.latest.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "ok", blob[-2000:])
            self.assertNotIn("catalog-fit: zz-mark", proc.stderr)
            self.assertNotIn("catalog-fit: cc-stay", proc.stderr)
            self.assertNotIn("catalog-fit: fallback", proc.stderr)
            kept = json.loads((wt / "eval" / "catalog-fit" / "aa-keep.json").read_text(encoding="utf-8"))
            dropped = json.loads((wt / "eval" / "catalog-fit" / "bb-drop.json").read_text(encoding="utf-8"))
            self.assertEqual(kept["verdict"], "fit")
            self.assertEqual(kept["model"], "qwen3.6:35b")
            self.assertNotIn("fallback_from", kept)
            self.assertEqual(dropped["verdict"], "skip_install")
            self.assertEqual(dropped["exit"], 0)
            self.assertFalse((wt / "eval" / "catalog-fit" / "cc-stay.json").exists())
            self.assertFalse((wt / "eval" / "catalog-fit" / "zz-mark.json").exists())
            queue = (wt / "eval" / "catalog-queue" / "queue.tsv").read_text(encoding="utf-8")
            self.assertIn("aa-keep", queue)
            self.assertNotIn("bb-drop", queue)
            self.assertNotIn("bb-drop", status["launched"])

            down = {
                "PFY_CATFIT_HOST": "http://127.0.0.1:9",
                "PFY_CATFIT_TIMEOUT": "1",
            }
            again, state2, wt2, _log2 = run_tick(td, clone, extra=down)
            blob2 = again.stdout + "\n" + again.stderr
            self.assertEqual(again.returncode, 0, blob2[-4000:])
            status2 = json.loads((state2 / "loop.latest.json").read_text(encoding="utf-8"))
            self.assertEqual(status2["status"], "ok", blob2[-2000:])
            self.assertIn("ollama unreachable", again.stderr)
            self.assertIn("catalog-fit: aa-keep:", again.stderr)
            fit_dir = wt2 / "eval" / "catalog-fit"
            written = list(fit_dir.glob("*.json")) if fit_dir.is_dir() else []
            self.assertEqual(written, [])
