"""Security scanners and guards reach I3 by rules, with no sign-off.

Operator decision 2026-11-10 7:04am PT (replaces the GATE.json full gate).
How this fails: a security card reaches I3 without a clean sandlock trial, a
read-only profile, advisory or deny-only wiring, a main-run receipt, or a
green eval-structural; or a refusal hides which rule failed; or a card that
now passes stays stuck. How we recover: apply names each failed rule in the
card's promotion_history and changes nothing else, and --retry-refused
promotes the card once the missing rule passes and main is green.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tests._ledger import assert_only_ledger
from tests.test_catalog_apply_verdict_receipt import load_mod, make_repo, write_receipt

ROOT = Path(__file__).resolve().parents[1]
RAISE = ROOT / "scripts" / "catalog_auto_raise.py"
APPLY = ROOT / "scripts" / "catalog_apply_verdict.py"

PROFILE = {
    "sandbox": "sandlock",
    "reads": ["/usr", "/etc", "./scripts", "./tmp/fixture", "$HOME/.cache/pfy/tools/x"],
    "writes": ["./tmp/sandlock-trial/x/stage"],
    "network": "deny",
    "clean_env": True,
    "sudo": False,
}


def load_raise():
    spec = importlib.util.spec_from_file_location("auto_raise_security_test", RAISE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sec_card(repo: Path, slug: str, stage: str = "I2", ceiling: str = "I3", wiring: dict | None = None) -> Path:
    path = repo / "data" / "stages" / f"{slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"name": slug, "integration_stage": stage, "tier_ceiling": ceiling, "risk_class": "security",
            "uses": "Scan lockfiles.", "evidence": ["entry:sources/entries/001-x.md", f"receipt:eval/integrate/{slug}/receipt.json"]}
    if wiring is not None:
        body["wiring"] = wiring
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


def write_trial(repo: Path, slug: str, **over) -> None:
    doc = {"slug": slug, "run_kind": "sandbox-trial", "sandbox": "sandlock", "outcome": "ok",
           "exit_code": 0, "unsandboxed_lines": 0, "scan_verdict": "CLEAN", "profile": dict(PROFILE)}
    doc.update(over)
    path = repo / "eval" / "integrate" / slug / "sandbox-trial.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def write_workflow(repo: Path, slug: str, continue_on_error: bool = True) -> str:
    rel = ".github/workflows/ci.yml"
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["jobs:", "  a:", "    steps:", f"      - name: {slug} advisory", f"        # pfy-advisory: {slug}"]
    if continue_on_error:
        lines.append("        continue-on-error: true")
    lines += ["        run: echo scan", "      - name: next", "        run: true", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return rel


class SecurityRulesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = load_mod()
        self._td = tempfile.TemporaryDirectory()
        self.td = Path(self._td.name)
        self.repo, self.main_sha, self.side_sha = make_repo(self.td)
        self._env = dict(os.environ)
        os.environ["PFY_MAIN_GREEN"] = "1"
        os.environ.pop("PFY_OPS_ROOT", None)
        os.environ["PFY_LOOP_TODAY"] = "2026-11-10"

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env)
        self._td.cleanup()

    def _verdict(self, slug: str, stage: str, sandbox: bool = True) -> Path:
        v = {"metric": "probe_exit", "threshold": 0, "value": 0, "value_gate": "pass",
             "modularity_gate": "pass", "proposed_stage": stage}
        if sandbox:
            v["sandbox"] = "sandlock"
        vp = self.repo / "eval" / "integrate" / slug / "VERDICT.json"
        vp.parent.mkdir(parents=True, exist_ok=True)
        vp.write_text(json.dumps(v), encoding="utf-8")
        return vp

    def _apply(self, slug: str, card: Path, stage: str, sandbox: bool = True):
        vp = self._verdict(slug, stage, sandbox)
        before = card.read_bytes()
        try:
            with redirect_stdout(io.StringIO()):
                self.mod.apply_verdict(card, vp, None, self.repo)
        except self.mod.Refuse as exc:
            assert_only_ledger(self, card, before)
            return str(exc)
        return None

    def _card(self, card: Path) -> dict:
        return json.loads(card.read_text(encoding="utf-8"))

    def _failed(self, card: Path) -> list[str]:
        return [item["rule"] for item in self._card(card)["promotion_history"][-1]["failed"]]

    def test_all_rules_pass_reaches_i3_without_a_gate_file(self) -> None:
        write_receipt(self.repo, "bb", self.main_sha)
        write_trial(self.repo, "bb")
        card = sec_card(self.repo, "bb", wiring={"mode": "advisory", "where": write_workflow(self.repo, "bb")})
        self.assertIsNone(self._apply("bb", card, "I3"))
        body = self._card(card)
        self.assertEqual(body["integration_stage"], "I3")
        entry = body["promotion_history"][-1]
        self.assertEqual(entry["result"], "promote")
        self.assertEqual(entry["failed"], [])
        for rid in ("S-sandlock-trial-clean", "S-profile-readonly", "S-wiring", "S-ci-green", "R-main-receipt"):
            self.assertIn(rid, entry["passed"])
        self.assertFalse((self.repo / "eval" / "integrate" / "bb" / "GATE.json").exists())

    def test_each_failed_rule_is_named_and_nothing_else_changes(self) -> None:
        cases = {
            "notrial": ("S-sandlock-trial-clean", None),
            "dirty": ("S-sandlock-trial-clean", dict(scan_verdict="FINDINGS")),
            "escaped": ("S-sandlock-trial-clean", dict(unsandboxed_lines=1)),
            "noprofile": ("S-profile-readonly", dict(profile=None)),
            "writer": ("S-profile-readonly", dict(profile=dict(PROFILE, writes=["$HOME/.bashrc"]))),
            "sneaky": ("S-profile-readonly", dict(profile=dict(PROFILE, writes=["$HOME/.config/tmp/x"]))),
            "climber": ("S-profile-readonly", dict(profile=dict(PROFILE, writes=["./tmp/../.git"]))),
            "netty": ("S-profile-readonly", dict(profile=dict(PROFILE, network="open"))),
            "homer": ("S-profile-readonly", dict(profile=dict(PROFILE, reads=["$HOME"]))),
            "sshy": ("S-profile-readonly", dict(profile=dict(PROFILE, reads=["$HOME/.ssh"]))),
            "sudoer": ("S-profile-readonly", dict(profile=dict(PROFILE, sudo=True))),
        }
        for slug, (rule, trial) in cases.items():
            write_receipt(self.repo, slug, self.main_sha)
            if trial is not None or slug != "notrial":
                write_trial(self.repo, slug, **(trial or {}))
            card = sec_card(self.repo, slug, wiring={"mode": "advisory", "where": write_workflow(self.repo, slug)})
            err = self._apply(slug, card, "I3")
            self.assertIsNotNone(err, slug)
            self.assertIn(rule, err, slug)
            self.assertIn(rule, self._failed(card), slug)
            self.assertEqual(self._card(card)["integration_stage"], "I2", slug)

    def test_wiring_rules(self) -> None:
        write_receipt(self.repo, "w1", self.main_sha)
        write_trial(self.repo, "w1")
        nowire = sec_card(self.repo, "w1")
        self.assertIn("S-wiring", self._apply("w1", nowire, "I3"))
        blocking = sec_card(self.repo, "w1", wiring={"mode": "advisory", "where": write_workflow(self.repo, "w1", continue_on_error=False)})
        self.assertIn("continue-on-error", self._apply("w1", blocking, "I3"))
        hook = self.repo / "scripts" / "hook.sh"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text("#!/bin/sh\n", encoding="utf-8")
        guard = sec_card(self.repo, "w1", wiring={"mode": "deny-only", "where": "scripts/hook.sh", "fail_open_test": "tests/missing.py"})
        self.assertIn("fail_open_test", self._apply("w1", guard, "I3"))
        test = self.repo / "tests" / "test_fail_open.py"
        test.parent.mkdir(parents=True, exist_ok=True)
        test.write_text("", encoding="utf-8")
        guard = sec_card(self.repo, "w1", wiring={"mode": "deny-only", "where": "scripts/hook.sh", "fail_open_test": "tests/test_fail_open.py"})
        self.assertIsNone(self._apply("w1", guard, "I3"))

    def test_red_main_refuses_then_retry_promotes_once_green(self) -> None:
        write_receipt(self.repo, "ci", self.main_sha)
        write_trial(self.repo, "ci")
        card = sec_card(self.repo, "ci", wiring={"mode": "advisory", "where": write_workflow(self.repo, "ci")})
        os.environ["PFY_MAIN_GREEN"] = "0"
        err = self._apply("ci", card, "I3")
        self.assertIn("S-ci-green", err)
        self.assertEqual(self._failed(card), ["S-ci-green"])
        self.assertEqual(self.mod.retry_refused(self.repo), ["hold\tci\tmain-not-green"])
        self.assertEqual(self._card(card)["integration_stage"], "I2")
        os.environ["PFY_MAIN_GREEN"] = "1"
        self.assertEqual(self.mod.retry_refused(self.repo), ["promote\tci\tI3"])
        body = self._card(card)
        self.assertEqual(body["integration_stage"], "I3")
        self.assertEqual([e["result"] for e in body["promotion_history"]], ["refuse", "promote"])
        self.assertEqual(self.mod.retry_refused(self.repo), [])

    def test_security_verdict_without_sandlock_stops_below_i2(self) -> None:
        card = sec_card(self.repo, "trial", stage="I1", ceiling="I2")
        err = self._apply("trial", card, "I2", sandbox=False)
        self.assertIn("S-sandlock-verdict", err)
        self.assertEqual(self._card(card)["integration_stage"], "I1")

    def test_auto_raise_takes_security_to_i3_only_when_trial_profile_and_wiring_pass(self) -> None:
        raiser = load_raise()
        passing = {"value_gate": "pass", "modularity_gate": "pass"}
        base = {"name": "s", "risk_class": "security", "uses": "scan", "integration_stage": "I1", "tier_ceiling": "I1"}
        self.assertEqual(raiser.plan(base, None, root=self.repo, slug="s")["target"], "I2")
        at_i2 = dict(base, tier_ceiling="I2")
        result = raiser.plan(at_i2, passing, root=self.repo, slug="s")
        self.assertEqual(result["action"], "skip")
        self.assertIn("S-sandlock-trial-clean", result["reason"])
        write_trial(self.repo, "s")
        wired = dict(at_i2, wiring={"mode": "advisory", "where": write_workflow(self.repo, "s")})
        result = raiser.plan(wired, passing, root=self.repo, slug="s")
        self.assertEqual((result["action"], result["target"]), ("raise", "I3"))
        money = dict(base, risk_class="live-money")
        self.assertEqual(raiser.plan(money, passing, root=self.repo, slug="m")["action"], "refuse")


if __name__ == "__main__":
    unittest.main()
