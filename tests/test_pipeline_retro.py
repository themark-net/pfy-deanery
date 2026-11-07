#!/usr/bin/env python3
"""Parsing and counting for scripts/pipeline_retro.py. No network."""

from __future__ import annotations

import importlib.util
import json
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_retro():
    path = ROOT / "scripts" / "pipeline_retro.py"
    spec = importlib.util.spec_from_file_location("pipeline_retro", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


retro = load_retro()


def landing(sha, subject="docs: landing"):
    return {
        "sha": sha,
        "subject": subject,
        "committed_at": datetime(2026, 11, 7, 20, 0, tzinfo=timezone.utc),
        "extra_shas": [],
    }


def summary(sha, rows, wall=2347, started="2026-11-07 08:10 PST"):
    body = [
        "# Pregate summary",
        "",
        "- overall: **PASS**",
        f"- ref: `HEAD` = `{sha}`",
        f"- started (local): {started}",
        f"- wall seconds: {wall}",
        "- run id: `run-1`",
        "",
        "| status | check | detail |",
        "|---|---|---|",
    ]
    for status, name in rows:
        body.append(f"| {status} | {name} | detail |")
    return "\n".join(body) + "\n"


class ParseAndCountTest(unittest.TestCase):
    def test_pregate_summary_counts_ran_discovers_not_the_skipped_suite(self):
        sha = "a" * 40
        text = summary(
            sha,
            [
                ("PASS", "lint"),
                ("PASS", "ubuntu-parity"),
                ("FAIL", "eval-structural"),
                ("SKIP", "suite"),
            ],
            wall=2347,
        )
        parsed = retro.parse_pregate_summary(text)
        self.assertEqual(parsed["sha"], sha)
        self.assertEqual(parsed["wall_s"], 2347)
        self.assertEqual(parsed["started"], datetime(2026, 11, 7, 16, 10, tzinfo=timezone.utc))

        rows = retro.build_landing_rows([landing(sha)], [parsed], [], [])
        row = rows[0]
        # ubuntu-parity ran and eval-structural ran. The skipped suite check did not.
        self.assertEqual(row["full_suite_runs"], 2)
        self.assertEqual(row["selected_suite_runs"], 0)
        self.assertEqual(row["pregate_minutes"], round(2347 / 60.0, 1))
        self.assertEqual(row["self_hosted_minutes"], row["pregate_minutes"])
        self.assertEqual(row["github_hosted_minutes"], 0.0)
        self.assertIn("39 min pregate", retro.format_table(retro.make_report(rows, True, "", {})))

    def test_progress_line_is_not_added_on_top_of_a_summary(self):
        sha = "b" * 40
        parsed = retro.parse_pregate_summary(
            summary(sha, [("PASS", "ubuntu-parity")], wall=1200, started="2026-11-07 09:00 PST")
        )
        doubled = (
            f"lane: pregate PASS {sha} in 2400s\n"
            f"lane: pregate PASS {sha} in 2400s\n"
            f"other: pregate PASS {'c' * 40} in 2400s\n"
        )
        progress = retro.parse_progress_text(doubled)
        self.assertEqual(len(progress), 2)
        landings = [landing(sha), landing("c" * 40, "other")]
        rows = retro.build_landing_rows(landings, [parsed], progress, [])
        by_sha = {row["sha"]: row for row in rows}
        # Summary already recorded this sha, so the 2400s line must not add another full run.
        self.assertEqual(by_sha[sha]["full_suite_runs"], 1)
        self.assertEqual(by_sha[sha]["pregate_minutes"], 20.0)
        # No summary for the other sha: the progress line is the only evidence, and 2400s is a full run.
        self.assertEqual(by_sha["c" * 40]["full_suite_runs"], 1)
        self.assertEqual(by_sha["c" * 40]["runner_minutes"], 40.0)
        short = retro.parse_progress_text(f"pregate PASS {'d' * 40} in 120s")
        short_rows = retro.build_landing_rows([landing("d" * 40)], [], short, [])
        self.assertEqual(short_rows[0]["full_suite_runs"], 0)
        self.assertEqual(short_rows[0]["selected_suite_runs"], 0)
        self.assertEqual(short_rows[0]["runner_minutes"], 2.0)

    def test_duplicate_full_suite_on_same_sha_is_flagged(self):
        sha = "e" * 40
        once = retro.parse_pregate_summary(summary(sha, [("PASS", "ubuntu-parity")], wall=60))
        one = retro.build_landing_rows([landing(sha)], [once], [], [])[0]
        self.assertEqual(one["full_suite_runs"], 1)
        self.assertFalse(one["duplicated"])
        self.assertFalse(one["over_baseline"])

        twice = retro.parse_pregate_summary(
            summary(
                sha,
                [("PASS", "ubuntu-parity"), ("PASS", "eval-structural"), ("SKIP", "suite")],
                wall=2340,
            )
        )
        row = retro.build_landing_rows([landing(sha)], [twice], [], [])[0]
        self.assertEqual(row["full_suite_runs"], 2)
        self.assertTrue(row["duplicated"])
        self.assertIn("pregate:ubuntu-parity x1", row["duplicate_sources"])
        self.assertIn("pregate:eval-structural x1", row["duplicate_sources"])

        # The same CI job name twice on one SHA is the same flag.
        start = datetime(2026, 11, 7, 17, 0, tzinfo=timezone.utc)
        jobs = [
            {
                "sha": sha,
                "name": "G0 (ubuntu-24.04)",
                "host": "github-hosted",
                "seconds": 1320,
                "lane": "branch",
                "kind": "full",
                "started": start,
                "completed": start + timedelta(seconds=1320),
            },
            {
                "sha": sha,
                "name": "G0 (ubuntu-24.04)",
                "host": "github-hosted",
                "seconds": 1320,
                "lane": "main",
                "kind": "full",
                "started": start,
                "completed": start + timedelta(seconds=1320),
            },
        ]
        ci = retro.build_landing_rows([landing(sha)], [], [], jobs)[0]
        self.assertEqual(ci["full_suite_runs"], 2)
        self.assertTrue(ci["duplicated"])
        self.assertEqual(ci["duplicate_sources"], ["ci:G0 (ubuntu-24.04) x2"])
        self.assertEqual(ci["github_hosted_minutes"], 44.0)
        self.assertEqual(ci["branch_ci_minutes"], 22.0)
        self.assertEqual(ci["main_ci_minutes"], 22.0)

    def test_selected_job_is_not_full_and_baseline_is_a_flag(self):
        sha = "f" * 40
        start = datetime(2026, 11, 7, 18, 0, tzinfo=timezone.utc)
        selected = {
            "sha": sha,
            "name": "subset",
            "host": "self-hosted",
            "seconds": 60,
            "lane": "branch",
            "kind": "selected",
            "started": start,
            "completed": start + timedelta(seconds=60),
        }
        only = retro.build_landing_rows([landing(sha)], [], [], [selected])[0]
        self.assertEqual(only["full_suite_runs"], 0)
        self.assertEqual(only["selected_suite_runs"], 1)
        self.assertFalse(only["duplicated"])
        self.assertEqual(only["self_hosted_minutes"], 1.0)
        self.assertEqual(only["github_hosted_minutes"], 0.0)

        heavy = []
        for _ in range(7):
            heavy.append(
                {
                    "sha": sha,
                    "name": "G0 (self-hosted nimo)",
                    "host": "self-hosted",
                    "seconds": 60,
                    "lane": "main",
                    "kind": "full",
                    "started": start,
                    "completed": start + timedelta(seconds=60),
                }
            )
        over_count = retro.build_landing_rows([landing(sha)], [], [], heavy)[0]
        self.assertEqual(over_count["full_suite_runs"], 7)
        self.assertTrue(over_count["over_baseline"])
        self.assertTrue(any("full-suite runs" in reason for reason in over_count["over_reasons"]))

        long_job = {
            "sha": sha,
            "name": "G0 (ubuntu-24.04)",
            "host": "github-hosted",
            "seconds": 130 * 60,
            "lane": "main",
            "kind": "full",
            "started": start,
            "completed": start + timedelta(seconds=130 * 60),
        }
        over_minutes = retro.build_landing_rows([landing(sha)], [], [], [long_job])[0]
        self.assertEqual(over_minutes["full_suite_runs"], 1)
        self.assertEqual(over_minutes["runner_minutes"], 130.0)
        self.assertTrue(over_minutes["over_baseline"])
        self.assertFalse(over_minutes["duplicated"])

    def test_repo_g0_jobs_are_full_suite(self):
        classes = retro.load_job_classes(ROOT / ".github" / "workflows")
        self.assertEqual(classes.get("G0 (ubuntu-24.04)"), "full")
        self.assertEqual(classes.get("G0 (self-hosted nimo)"), "full")

    def test_cancelled_and_schedule_do_not_inflate_the_landing(self):
        sha = "1" * 40
        start = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
        items = [
            {
                "run": {
                    "id": 1,
                    "head_sha": sha,
                    "event": "workflow_dispatch",
                    "head_branch": "main",
                },
                "jobs": [
                    {
                        "name": "G0 (ubuntu-24.04)",
                        "conclusion": "cancelled",
                        "started_at": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "completed_at": (start + timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "labels": ["ubuntu-24.04"],
                    }
                ],
            },
            {
                "run": {
                    "id": 2,
                    "head_sha": sha,
                    "event": "schedule",
                    "head_branch": "main",
                },
                "jobs": [
                    {
                        "name": "lab (auto)",
                        "conclusion": "failure",
                        "started_at": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "completed_at": (start + timedelta(seconds=6000)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "labels": ["self-hosted", "Linux"],
                    }
                ],
            },
        ]
        classes = {"G0 (ubuntu-24.04)": "full", "lab (auto)": "full"}
        jobs = retro.ci_jobs_from_payloads(items, classes)
        row = retro.build_landing_rows([landing(sha)], [], [], jobs)[0]
        self.assertEqual(row["full_suite_runs"], 0)
        self.assertFalse(row["duplicated"])
        self.assertEqual(row["schedule_minutes"], 100.0)
        self.assertEqual(row["runner_minutes"], 0.5)
        self.assertFalse(row["over_baseline"])

    def test_github_client_uses_cache_and_stops_before_the_rate_floor(self):
        cache = ROOT / "tmp" / "retro-test-cache"
        cache.mkdir(parents=True, exist_ok=True)
        url = "https://api.github.com/repos/themark-net/pfy-mentat/actions/runs?per_page=1"
        digest = __import__("hashlib").sha256(url.encode()).hexdigest()[:24]
        cached = {"workflow_runs": []}
        (cache / f"{digest}.json").write_text(json.dumps(cached), encoding="utf-8")
        calls = {"n": 0}

        def boom(request, timeout=30):
            calls["n"] += 1
            raise urllib.error.URLError("offline")

        client = retro.GitHubClient(cache, opener=boom)
        self.assertEqual(client.get(url), cached)
        self.assertEqual(calls["n"], 0)
        self.assertTrue(client.ok)

        missing = url + "&page=2"
        self.assertIsNone(client.get(missing))
        self.assertEqual(calls["n"], 1)
        self.assertFalse(client.ok)
        self.assertIn("unavailable", client.note)

        def refuse(request, timeout=30):
            calls["n"] += 1
            raise AssertionError("network used under the rate floor")

        limited = retro.GitHubClient(cache, opener=refuse, min_remaining=10)
        limited.remaining = 3
        self.assertIsNone(limited.get(missing + "&page=3"))
        self.assertEqual(calls["n"], 1)
        self.assertIn("60/hour", limited.note)


if __name__ == "__main__":
    unittest.main()
