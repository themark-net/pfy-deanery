#!/usr/bin/env python3
"""local-lab.yml must cap each long step and start before nightly-models.

How this fails: a step hang has no timeout-minutes, so the run dies at the
job wall with no named step (#310). A comment or an echo of the numbers
would hide the miss if the check grepped the file. The job wall stays at 90
while the measured suite is already about 100 minutes.

How we recover: put the caps back on the five named steps (G0 30, G1 30,
Product levers 30, smoke-integration 40, eval-auto 20), set the only
schedule cron to 15 10 * * * (02:15 America/Los_Angeles, UTC-8), and set
job lab timeout-minutes to 120. A hang then fails that step. That wall ends
at 12:15 UTC, before nightly-models at 30 12 * * * (04:30 PT, 12:30 UTC).
Both workflows share concurrency group pfy-local-model with
cancel-in-progress false. The 120 minute job wall covers the grown suite.
Per-step caps still stop a hang inside that wall.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "local-lab.yml"

# Spec from #310. The workflow file is the other side. Drift fails the test.
CRON = "15 10 * * *"
NIGHTLY_CRON = "30 12 * * *"
MODEL_GROUP = "pfy-local-model"
JOB_TIMEOUT = 120
REQUIRED_STEPS = {
    "G0 structural": 30,
    "G1 deploy-ready (soft smokes)": 30,
    "Product levers smoke": 30,
    "smoke-integration umbrella": 40,
    "eval-auto (Ollama when present)": 20,
}

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def require_yaml(case: unittest.TestCase) -> None:
    if yaml is None:
        case.fail(
            "PyYAML is not importable in %s. Recovery: pip install pyyaml "
            "for that interpreter. The ubuntu G0 job installs it before discover."
            % sys.executable
        )


def _triggers(doc: dict) -> dict | None:
    """GitHub writes `on:`. PyYAML 1.1 loads that bare key as True."""
    raw = doc.get("on")
    if not isinstance(raw, dict):
        raw = doc.get(True)
    if isinstance(raw, dict):
        return raw
    return None


def _crons(triggers: dict) -> list[str]:
    schedule = triggers.get("schedule")
    if not isinstance(schedule, list):
        return []
    found: list[str] = []
    for item in schedule:
        if isinstance(item, dict) and isinstance(item.get("cron"), str):
            found.append(item["cron"])
    return found


def budget_problems(doc: object) -> list[str]:
    """Return why this workflow no longer matches the #310 budget.

    Empty means the parsed document has the early cron, the 120 minute job
    wall, and an integer timeout-minutes on each named step. Text inside
    `run` or a YAML comment is invisible here because the caller parsed first.
    """
    if not isinstance(doc, dict):
        return ["workflow YAML is not a mapping"]
    problems: list[str] = []
    triggers = _triggers(doc)
    if triggers is None:
        problems.append("schedule trigger is missing")
    else:
        crons = _crons(triggers)
        if crons != [CRON]:
            problems.append(
                "schedule cron is %r, need %r so local-lab's 120 minute wall ends before nightly-models at 12:30 UTC"
                % (crons, CRON)
            )
    jobs = doc.get("jobs")
    lab = jobs.get("lab") if isinstance(jobs, dict) else None
    if not isinstance(lab, dict):
        problems.append("job lab is missing")
        return problems
    wall = lab.get("timeout-minutes")
    if wall != JOB_TIMEOUT:
        problems.append(
            "job lab timeout-minutes is %r, need %d because the grown suite wall is already past 90 minutes"
            % (wall, JOB_TIMEOUT)
        )
    steps = lab.get("steps")
    if not isinstance(steps, list):
        problems.append("job lab has no steps")
        return problems
    by_name: dict[str, list[object]] = {}
    for step in steps:
        if isinstance(step, dict) and isinstance(step.get("name"), str):
            by_name.setdefault(step["name"], []).append(step.get("timeout-minutes"))
    for name, expected in REQUIRED_STEPS.items():
        found = by_name.get(name)
        if not found:
            problems.append(
                "step %r is missing; a hang would not fail on that step" % name
            )
            continue
        for value in found:
            if value != expected:
                problems.append(
                    "step %r timeout-minutes is %r, need %d so a hang fails on that step"
                    % (name, value, expected)
                )
    return problems


def _valid_doc() -> dict:
    steps: list[dict] = [{"uses": "actions/checkout@v4"}]
    for name, minutes in REQUIRED_STEPS.items():
        steps.append({"name": name, "timeout-minutes": minutes, "run": "true"})
    return {
        "name": "local-lab",
        True: {"schedule": [{"cron": CRON}]},
        "jobs": {"lab": {"timeout-minutes": JOB_TIMEOUT, "steps": steps}},
    }


def _named(doc: dict, name: str) -> dict:
    for step in doc["jobs"]["lab"]["steps"]:
        if step.get("name") == name:
            return step
    raise AssertionError("fixture missing %r" % name)


_COMMENTS_DO_NOT_COUNT = """\
# cron: "15 10 * * *"
# timeout-minutes: 120
name: local-lab
on:
  schedule:
    - cron: "15 6 * * *"
jobs:
  lab:
    timeout-minutes: 90
    steps:
      - name: G0 structural
        run: echo timeout-minutes 30
      - name: G1 deploy-ready (soft smokes)
        run: echo timeout-minutes 30
      - name: Product levers smoke
        run: echo timeout-minutes 30
      - name: smoke-integration umbrella
        run: echo timeout-minutes 40
      - name: eval-auto (Ollama when present)
        run: echo timeout-minutes 20
"""


class LocalLabBudgetTests(unittest.TestCase):
    def test_checked_in_workflow_has_step_caps_and_early_cron(self) -> None:
        require_yaml(self)
        doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        problems = budget_problems(doc)
        self.assertEqual(problems, [], problems)

    def test_removed_step_timeout_fails(self) -> None:
        doc = _valid_doc()
        del _named(doc, "G0 structural")["timeout-minutes"]
        problems = budget_problems(doc)
        self.assertTrue(
            any("G0 structural" in item and "hang" in item for item in problems),
            problems,
        )

    def test_wrong_step_cap_fails(self) -> None:
        doc = _valid_doc()
        _named(doc, "smoke-integration umbrella")["timeout-minutes"] = 90
        problems = budget_problems(doc)
        self.assertTrue(
            any("smoke-integration umbrella" in item and "90" in item for item in problems),
            problems,
        )

    def test_old_cron_fails(self) -> None:
        doc = _valid_doc()
        doc[True]["schedule"][0]["cron"] = "15 6 * * *"
        problems = budget_problems(doc)
        self.assertTrue(any("15 6 * * *" in item for item in problems), problems)

    def test_extra_cron_fails(self) -> None:
        doc = _valid_doc()
        doc[True]["schedule"].append({"cron": "15 6 * * *"})
        problems = budget_problems(doc)
        self.assertTrue(problems, problems)

    def test_job_wall_90_fails(self) -> None:
        doc = _valid_doc()
        doc["jobs"]["lab"]["timeout-minutes"] = 90
        problems = budget_problems(doc)
        self.assertTrue(any("90" in item and "120" in item for item in problems), problems)

    def test_comment_and_echo_do_not_satisfy_the_budget(self) -> None:
        require_yaml(self)
        problems = budget_problems(yaml.safe_load(_COMMENTS_DO_NOT_COUNT))
        self.assertTrue(any("G0 structural" in item for item in problems), problems)
        self.assertTrue(any("15 6 * * *" in item for item in problems), problems)
        self.assertTrue(any("90" in item for item in problems), problems)

    def test_nightly_models_follows_the_lab_wall_and_shares_its_group(self) -> None:
        """Fail: nightly starts during the lab wall, or either workflow cancels the other.
        Recovery: nightly cron is 30 12 * * * and both groups are pfy-local-model
        with cancel-in-progress false. Step caps on local-lab stay in the other test.
        """
        require_yaml(self)
        nightly_path = ROOT / ".github" / "workflows" / "nightly-models.yml"
        nightly = yaml.safe_load(nightly_path.read_text(encoding="utf-8"))
        triggers = _triggers(nightly)
        self.assertIsNotNone(triggers)
        self.assertEqual(_crons(triggers), [NIGHTLY_CRON])
        lab = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        for doc in (lab, nightly):
            group = doc.get("concurrency")
            self.assertIsInstance(group, dict, doc.get("name"))
            self.assertEqual(group.get("group"), MODEL_GROUP)
            self.assertIs(group.get("cancel-in-progress"), False)
        self.assertEqual(lab["jobs"]["lab"]["timeout-minutes"], JOB_TIMEOUT)
        self.assertEqual(nightly["jobs"]["matrix"]["timeout-minutes"], JOB_TIMEOUT)


if __name__ == "__main__":
    unittest.main()
