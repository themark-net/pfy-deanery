"""Bake-off behavior tests. Offline. No Ollama. No network.

The live mark is deselected unless HERMES_BAKEOFF_LIVE=1.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BAKE = ROOT / "examples" / "hermes-bakeoff"
if str(BAKE) not in sys.path:
    sys.path.insert(0, str(BAKE))

from guard import assert_hermes_home  # noqa: E402
from fixtures import expected_submit  # noqa: E402
from hermes_arm import _write_config  # noqa: E402
from make_tasks import build, labels_written_stamp  # noqa: E402
from run import child_tmpdir, scrubbed  # noqa: E402
from think_proxy import ThinkProxy  # noqa: E402
from mcp_framing import read_message, write_message  # noqa: E402
from mcp_server import parse_ts, stamp_now  # noqa: E402
from schema import server_name, validate_args  # noqa: E402
from score import (  # noqa: E402
    aggregate,
    count_attempts,
    margin_verdict,
    narrate_flag,
    normalize_client_calls,
    percentile,
    rescore_payload,
    score_task,
    wilson,
)

try:
    import pytest
except ModuleNotFoundError:  # pragma: no cover - unittest path on a machine without pytest
    class _Mark:
        def live(self, obj):
            return obj

        def __getattr__(self, _name):
            def deco(*args, **_kwargs):
                if args and callable(args[0]):
                    return args[0]

                def wrap(fn):
                    return fn

                return wrap

            return deco

    class pytest:  # type: ignore
        mark = _Mark()

        @staticmethod
        def skip(reason):
            raise unittest.SkipTest(reason)


def _arm(success, valid=1.0, narrate=0.0, p50=10.0, peak=1024):
    return {
        "task_success": success,
        "valid_tool_call_rate": valid,
        "narrate_rate": narrate,
        "p50_s": p50,
        "peak_rss_bytes": peak,
    }


class HermesBakeoffTests(unittest.TestCase):
    def test_check_fails_closed_when_ollama_is_unreachable(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(BAKE / "run.py"),
                "--check",
                "--base-url",
                "http://127.0.0.1:59999",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("FAIL", proc.stdout + proc.stderr)

    def test_check_fails_closed_when_model_tag_is_missing(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = json.dumps({"models": [{"name": "other:1"}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt, *args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        import threading

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(BAKE / "run.py"),
                    "--check",
                    "--base-url",
                    f"http://127.0.0.1:{port}/v1",
                    "--model",
                    "qwen3.6:35b",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=15,
            )
        finally:
            server.shutdown()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("FAIL: model tag missing", proc.stdout + proc.stderr)

    def test_schema_invalid_call_is_not_success(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.jsonl"
            proc = subprocess.Popen(
                [
                    sys.executable,
                    str(BAKE / "mcp_server.py"),
                    "--log",
                    str(log),
                    "--task-id",
                    "bad",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            try:
                write_message(
                    proc.stdin,
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
                    },
                )
                reply = read_message(proc.stdout)
                self.assertEqual(reply["id"], 1)
                write_message(
                    proc.stdin,
                    {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
                )
                write_message(
                    proc.stdin,
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "submit_choice", "arguments": {"choice": 3}},
                    },
                )
                reply = read_message(proc.stdout)
                self.assertTrue(reply["result"]["isError"])
            finally:
                proc.kill()
                proc.wait(timeout=5)
            rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertFalse(rows[0]["schema_valid"])
            task = {
                "id": "bad",
                "kind": "choice",
                "requires_call": True,
                "oracle": {
                    "required": [
                        {"tool": "submit_choice", "args": {"case_id": "ph-01-green-idle", "choice": "push"}}
                    ]
                },
            }
            scored = score_task(task, rows, "")
            self.assertFalse(scored["pass"])
            ok, _error = validate_args("submit_choice", {"choice": 3})
            self.assertFalse(ok)

    def test_ttft_keeps_milliseconds_and_rejects_whole_second_stamps(self):
        """A whole-second server stamp must not score. TTFT stays sub-second."""
        import tempfile

        from run import score_one

        stamped = stamp_now()
        self.assertRegex(stamped, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
        whole = stamped.split(".", 1)[0] + "Z"
        with self.assertRaises(ValueError):
            parse_ts(whole)

        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.jsonl"
            proc = subprocess.Popen(
                [
                    sys.executable,
                    str(BAKE / "mcp_server.py"),
                    "--log",
                    str(log),
                    "--task-id",
                    "ttft",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            try:
                write_message(
                    proc.stdin,
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
                    },
                )
                self.assertEqual(read_message(proc.stdout)["id"], 1)
                write_message(
                    proc.stdin,
                    {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
                )
                write_message(
                    proc.stdin,
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "submit_choice",
                            "arguments": {
                                "case_id": "ph-01-green-idle",
                                "choice": "push",
                                "reason": "green",
                            },
                        },
                    },
                )
                reply = read_message(proc.stdout)
                self.assertFalse(reply["result"]["isError"])
            finally:
                if proc.stdin:
                    proc.stdin.close()
                if proc.stdout:
                    proc.stdout.close()
                proc.kill()
                proc.wait(timeout=5)
            rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertRegex(rows[0]["ts"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
            parsed = parse_ts(rows[0]["ts"])
            task = {
                "id": "ttft",
                "kind": "choice",
                "requires_call": True,
                "oracle": {
                    "required": [
                        {"tool": "submit_choice", "args": {"case_id": "ph-01-green-idle", "choice": "push"}}
                    ]
                },
            }
            sampled = {
                "timed_out": False,
                "stderr": "",
                "returncode": 0,
                "stdout": "",
                "wall_s": 1.0,
                "started": parsed - 0.25,
                "peak": {"agent_peak_rss_bytes": 1000, "ollama_peak_rss_bytes": 0},
            }
            missing = Path(tmp) / "no-arm.json"
            scored = score_one(task, missing, log, sampled)
            self.assertEqual(scored["ttft_s"], 0.25)
            whole_row = dict(rows[0])
            whole_row["ts"] = rows[0]["ts"].split(".", 1)[0] + "Z"
            whole_log = Path(tmp) / "whole.jsonl"
            whole_log.write_text(json.dumps(whole_row) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                score_one(task, missing, whole_log, sampled)

    def test_narrate_detects_fenced_json_and_ignores_a_real_call(self):
        fenced = "I would answer like this:\n```json\n{name: submit_choice, arguments: {choice: push}}\n```"
        self.assertTrue(narrate_flag(fenced, structured_reached_server=False, requires_call=True))
        self.assertFalse(narrate_flag(fenced, structured_reached_server=True, requires_call=True))
        task = {
            "kind": "choice",
            "requires_call": True,
            "oracle": {"required": [{"tool": "submit_choice", "args": {"case_id": "x", "choice": "push"}}]},
        }
        real = [{"name": "submit_choice", "schema_valid": True, "arguments": {"case_id": "x", "choice": "push", "reason": "ok"}}]
        self.assertFalse(score_task(task, real, fenced)["narrate"])
        self.assertTrue(score_task(task, [], fenced)["narrate"])

    def test_oracle_fails_when_the_right_tool_has_wrong_args(self):
        task = {
            "kind": "choice",
            "requires_call": True,
            "oracle": {
                "required": [
                    {"tool": "submit_choice", "args": {"case_id": "ph-01-green-idle", "choice": "push"}}
                ]
            },
        }
        calls = [
            {
                "name": "submit_choice",
                "schema_valid": True,
                "arguments": {"case_id": "ph-01-green-idle", "choice": "hold", "reason": "guess"},
            }
        ]
        scored = score_task(task, calls, "")
        self.assertFalse(scored["pass"])
        self.assertIn("submit_choice", scored["reason"])
        # A matching call must pass. Inverting != to == still rejects the wrong
        # call (the first key matches), so only this accept path kills that mutant.
        good = [
            {
                "name": "submit_choice",
                "schema_valid": True,
                "arguments": {"case_id": "ph-01-green-idle", "choice": "push", "reason": "green"},
            }
        ]
        self.assertTrue(score_task(task, good, "")["pass"])

    def test_hermes_tool_call_wrapper_is_not_a_second_invalid_attempt(self):
        client = [
            {"name": "tool_search", "arguments": {"queries": ["submit"]}},
            {
                "name": "tool_call",
                "arguments": {
                    "calls": [
                        {
                            "name": "mcp__bakeoff__submit_choice",
                            "arguments": {"case_id": "ph-01-green-idle", "choice": "push", "reason": "ok"},
                        }
                    ]
                },
            },
        ]
        baked, meta = normalize_client_calls(client)
        server = [
            {
                "name": "submit_choice",
                "schema_valid": True,
                "arguments": {"case_id": "ph-01-green-idle", "choice": "push", "reason": "ok"},
            }
        ]
        attempts, valid = count_attempts(server, baked)
        self.assertEqual(meta, 2)
        self.assertEqual(baked[0]["name"], "submit_choice")
        self.assertEqual((attempts, valid), (1, 1))

    def test_margin_just_below_ten_points_is_no_win(self):
        verdict, reasons = margin_verdict(_arm(0.599), _arm(0.50))
        self.assertEqual(verdict, "NO-WIN")
        self.assertTrue(reasons)
        verdict, reasons = margin_verdict(_arm(0.60), _arm(0.50))
        self.assertEqual(verdict, "WIN")
        self.assertEqual(reasons, [])
        # A peak over 2 GiB fails even when accuracy clears the margin.
        huge = 2 * 1024 ** 3 + 1
        verdict, _reasons = margin_verdict(_arm(0.80, peak=huge), _arm(0.50))
        self.assertEqual(verdict, "NO-WIN")

    def test_margin_fails_on_each_secondary_gate_and_passes_at_its_edge(self):
        clear = 0.80
        cases = (
            ("valid", _arm(clear, valid=0.97), _arm(0.50, valid=1.0), "valid tool-call rate"),
            ("narrate", _arm(clear, narrate=0.03), _arm(0.50, narrate=0.0), "narrate rate"),
            ("p50", _arm(clear, p50=15.1), _arm(0.50, p50=10.0), "p50"),
        )
        for label, hermes, baseline, needle in cases:
            with self.subTest(gate=label):
                verdict, reasons = margin_verdict(hermes, baseline)
                self.assertEqual(verdict, "NO-WIN")
                self.assertEqual(len(reasons), 1, reasons)
                self.assertIn(needle, reasons[0])
        edges = (
            _arm(clear, valid=0.98),
            _arm(clear, narrate=0.02),
            _arm(clear, p50=15.0),
        )
        for hermes in edges:
            verdict, reasons = margin_verdict(hermes, _arm(0.50))
            self.assertEqual((verdict, reasons), ("WIN", []))

    def test_final_submit_must_exist_and_match_every_arg(self):
        bundle = json.loads(
            (ROOT / "data" / "decision-gates" / "hermes-bakeoff.tasks.v0.json").read_text(encoding="utf-8")
        )
        fetch = next(item for item in bundle["tasks"] if item["id"] == "fetch-entry-130-slug")
        slug = fetch["oracle"]["submit"]["args"]["value"]
        lookup = {"name": "catalog_lookup", "schema_valid": True, "arguments": {"entry_number": 130}}
        missing = score_task(fetch, [lookup], "")
        self.assertFalse(missing["pass"])
        self.assertEqual(missing["reason"], "final submit mismatch")
        wrong_task = [
            lookup,
            {"name": "submit_answer", "schema_valid": True, "arguments": {"task_id": "other-task", "value": slug}},
        ]
        self.assertFalse(score_task(fetch, wrong_task, "")["pass"])

    def test_negative_with_a_call_fails_even_with_the_right_text(self):
        task = {
            "kind": "negative",
            "requires_call": False,
            "negative_mode": "contains",
            "expect_text": "4",
            "oracle": {"required": []},
        }
        call = [{"name": "compute_sum", "schema_valid": True, "arguments": {"a": 2, "b": 2}}]
        self.assertFalse(score_task(task, call, "4")["pass"])
        self.assertTrue(score_task(task, [], "4")["pass"])

    def test_fenced_json_alone_is_narrate(self):
        fenced = 'Here:\n```json\n{"name": "lookup", "arguments": {}}\n```'
        self.assertTrue(narrate_flag(fenced, structured_reached_server=False, requires_call=True))
        self.assertFalse(narrate_flag("plain answer with no call", structured_reached_server=False, requires_call=True))

    def test_meta_tools_are_not_attempts(self):
        client = [
            {"name": "tool_search", "arguments": {"queries": ["x"]}},
            {"name": "tool_describe", "arguments": {"name": "submit_choice"}},
        ]
        baked, meta = normalize_client_calls(client)
        self.assertEqual((baked, meta), ([], 2))
        self.assertEqual(count_attempts([], baked), (0, 0))

    def test_rescore_recomputes_a_stale_pass_and_verdict(self):
        bundle = json.loads(
            (ROOT / "data/decision-gates/hermes-bakeoff.tasks.v0.json").read_text(encoding="utf-8")
        )
        stale = json.loads((ROOT / "pipelines/dogfood/hermes-bakeoff/results.json").read_text(encoding="utf-8"))
        for arm_rows in stale["rows"].values():
            for row in arm_rows:
                row["pass"] = True
        stale["verdict"] = "WIN"
        stale["verdict_failures"] = []
        again = rescore_payload(stale, bundle["tasks"])
        self.assertEqual(again["summary"]["hermes"]["n_pass"], 26)
        self.assertEqual(again["summary"]["baseline"]["n_pass"], 25)
        self.assertEqual(sum(1 for row in again["rows"]["hermes"] if not row["pass"]), 1)
        self.assertEqual(again["verdict"], "NO-WIN")
        self.assertTrue(again["verdict_failures"])

    def test_hermes_home_guard_refuses_unset_and_real_home(self):
        with self.assertRaises(SystemExit) as unset:
            assert_hermes_home("")
        self.assertIn("FAIL", str(unset.exception))
        old = os.environ.pop("HERMES_HOME", None)
        try:
            with self.assertRaises(SystemExit) as again:
                assert_hermes_home(None)
            self.assertIn("unset", str(again.exception))
        finally:
            if old is not None:
                os.environ["HERMES_HOME"] = old
        forbidden = Path.home() / ".hermes" / "bakeoff-should-not-exist"
        with self.assertRaises(SystemExit) as under:
            assert_hermes_home(str(forbidden))
        self.assertIn("FAIL", str(under.exception))
        self.assertFalse(forbidden.exists())

    def test_committed_labels_match_laya_and_fixture_oracles(self):
        path = ROOT / "data" / "decision-gates" / "hermes-bakeoff.tasks.v0.json"
        committed = json.loads(path.read_text(encoding="utf-8"))
        fresh = build()
        self.assertEqual(committed["n_tasks"], fresh["n_tasks"])
        self.assertGreaterEqual(committed["n_tasks"], 20)
        self.assertEqual(
            [task["id"] for task in committed["tasks"]],
            [task["id"] for task in fresh["tasks"]],
        )
        laya = json.loads((ROOT / "data" / "decision-gates" / "laya-trial.cases.v0.json").read_text(encoding="utf-8"))
        labels = {case["id"]: case["label"] for case in laya["cases"]}
        choice = [task for task in committed["tasks"] if task["kind"] == "choice"]
        self.assertGreaterEqual(len(choice), 12)
        families = {task["family"] for task in choice}
        self.assertGreaterEqual(len(families), 4)
        for task in choice:
            self.assertEqual(task["label"], labels[task["source_case_id"]])
            required = task["oracle"]["required"][0]
            self.assertEqual(required["args"]["choice"], labels[task["source_case_id"]])
        fetchish = [task for task in committed["tasks"] if task["kind"] in ("fetch", "chain")]
        self.assertGreaterEqual(len(fetchish), 8)
        negatives = [task for task in committed["tasks"] if task["kind"] == "negative"]
        self.assertGreaterEqual(len(negatives), 2)
        self.assertTrue(committed["labels_before_models"])

    def test_percentile_wilson_and_aggregate_lock_the_rates(self):
        self.assertIsNone(percentile([], 0.50))
        self.assertEqual(percentile([4.0], 0.50), 4.0)
        # Midpoint of four walls is 25, not the second or third sample.
        self.assertEqual(percentile([10, 20, 30, 40], 0.50), 25)
        self.assertEqual(percentile([10, 20, 30, 40], 0.0), 10)
        self.assertEqual(percentile([10, 20, 30, 40], 1.0), 40)
        self.assertEqual(wilson(0, 0), (0.0, 0.0))
        low, high = wilson(26, 27)
        self.assertLess(low, 26 / 27)
        self.assertGreater(high, 26 / 27)
        self.assertGreater(high - low, 0.1)
        self.assertGreaterEqual(low, 0.0)
        self.assertLessEqual(high, 1.0)
        self.assertLess(low, high)
        rows = [
            {
                "pass": True,
                "requires_call": True,
                "narrate": True,
                "attempts": 2,
                "valid": 1,
                "wall_s": 10,
                "ttft_s": 1,
                "peak_rss_bytes": 100,
            },
            {
                "pass": False,
                "requires_call": False,
                "narrate": False,
                "attempts": 0,
                "valid": 0,
                "wall_s": 30,
                "ttft_s": 3,
                "peak_rss_bytes": 500,
            },
        ]
        summary = aggregate(rows)
        self.assertEqual(summary["task_success"], 0.5)
        self.assertEqual(summary["valid_tool_call_rate"], 0.5)
        self.assertEqual(summary["narrate_rate"], 1.0)
        self.assertEqual(summary["p50_s"], 20)
        self.assertEqual(summary["peak_rss_bytes"], 500)
        self.assertEqual(summary["wilson95"], wilson(1, 2))
        quiet = aggregate(
            [
                {
                    "pass": True,
                    "requires_call": False,
                    "narrate": False,
                    "attempts": 0,
                    "valid": 0,
                    "wall_s": 1,
                    "peak_rss_bytes": 10,
                }
            ]
        )
        self.assertEqual(quiet["valid_tool_call_rate"], 1.0)

    def test_schema_invalid_right_args_do_not_pass(self):
        task = {
            "kind": "choice",
            "requires_call": True,
            "oracle": {
                "required": [
                    {"tool": "submit_choice", "args": {"case_id": "ph-01-green-idle", "choice": "push"}}
                ]
            },
        }
        calls = [
            {
                "name": "submit_choice",
                "schema_valid": False,
                "arguments": {"case_id": "ph-01-green-idle", "choice": "push", "reason": "x"},
            }
        ]
        self.assertFalse(score_task(task, calls, "")["pass"])

    def test_last_submit_wins_and_a_contained_string_does_not(self):
        task = json.loads(
            (ROOT / "data" / "decision-gates" / "hermes-bakeoff.tasks.v0.json").read_text(encoding="utf-8")
        )
        fetch = next(item for item in task["tasks"] if item["id"] == "fetch-entry-130-slug")
        slug = fetch["oracle"]["submit"]["args"]["value"]
        good = [
            {"name": "catalog_lookup", "schema_valid": True, "arguments": {"entry_number": 130}},
            {
                "name": "submit_answer",
                "schema_valid": True,
                "arguments": {"task_id": "fetch-entry-130-slug", "value": "nope"},
            },
            {
                "name": "submit_answer",
                "schema_valid": True,
                "arguments": {"task_id": "fetch-entry-130-slug", "value": slug},
            },
        ]
        self.assertTrue(score_task(fetch, good, "")["pass"])
        early = [
            {"name": "catalog_lookup", "schema_valid": True, "arguments": {"entry_number": 130}},
            {
                "name": "submit_answer",
                "schema_valid": True,
                "arguments": {"task_id": "fetch-entry-130-slug", "value": slug},
            },
            {
                "name": "submit_answer",
                "schema_valid": True,
                "arguments": {"task_id": "fetch-entry-130-slug", "value": slug + " extra"},
            },
        ]
        self.assertFalse(score_task(fetch, early, "")["pass"])

    def test_negative_wrong_text_fails_and_unmatched_client_is_an_attempt(self):
        task = {
            "kind": "negative",
            "requires_call": False,
            "negative_mode": "contains",
            "expect_text": "4",
            "oracle": {"required": []},
        }
        self.assertFalse(score_task(task, [], "nope")["pass"])
        self.assertTrue(score_task(task, [], "4")["pass"])
        attempts, valid = count_attempts(
            [],
            [{"name": "mcp__bakeoff__submit_choice", "arguments": {"case_id": "x", "choice": "push"}}],
        )
        self.assertEqual((attempts, valid), (1, 0))

    def test_choice_scattershot_fails_even_when_one_choice_is_the_label(self):
        task = {
            "kind": "choice",
            "requires_call": True,
            "oracle": {
                "required": [
                    {"tool": "submit_choice", "args": {"case_id": "ph-08-missing-ci", "choice": "escalate"}}
                ]
            },
        }
        calls = [
            {
                "name": "submit_choice",
                "schema_valid": True,
                "arguments": {"case_id": "ph-08-missing-ci", "choice": "push", "reason": "guess"},
            },
            {
                "name": "mcp__bakeoff__submit_choice",
                "schema_valid": True,
                "arguments": {"case_id": "ph-08-missing-ci", "choice": "escalate", "reason": "missing"},
            },
        ]
        scored = score_task(task, calls, "")
        self.assertFalse(scored["pass"])
        self.assertIn("scattershot", scored["reason"])
        one = [calls[1]]
        self.assertTrue(score_task(task, one, "")["pass"])
        retry = [calls[1], dict(calls[1])]
        self.assertTrue(score_task(task, retry, "")["pass"])

    def test_fetch_oracle_follows_the_fixture_not_a_stale_label(self):
        bundle = json.loads(
            (ROOT / "data" / "decision-gates" / "hermes-bakeoff.tasks.v0.json").read_text(encoding="utf-8")
        )
        fetch = next(item for item in bundle["tasks"] if item["id"] == "fetch-entry-130-slug")
        chain = next(item for item in bundle["tasks"] if item["id"] == "chain-bench-plus-ten")
        self.assertEqual(expected_submit(fetch), fetch["oracle"]["submit"]["args"]["value"])
        self.assertEqual(expected_submit(chain), chain["oracle"]["submit"]["args"]["value"])
        stale = json.loads(json.dumps(fetch))
        stale["oracle"]["submit"]["args"]["value"] = "not-the-slug"
        calls = [
            {"name": "bakeoff_catalog_lookup", "schema_valid": True, "arguments": {"entry_number": 130}},
            {
                "name": "bakeoff_submit_answer",
                "schema_valid": True,
                "arguments": {"task_id": "fetch-entry-130-slug", "value": "not-the-slug"},
            },
        ]
        scored = score_task(stale, calls, "")
        self.assertFalse(scored["pass"])
        self.assertIn("oracle drift", scored["reason"])
        live_calls = [
            {"name": "mcp__bakeoff__catalog_lookup", "schema_valid": True, "arguments": {"entry_number": 130}},
            {
                "name": "submit_answer",
                "schema_valid": True,
                "arguments": {"task_id": "fetch-entry-130-slug", "value": fetch["oracle"]["submit"]["args"]["value"]},
            },
        ]
        self.assertTrue(score_task(fetch, live_calls, "")["pass"])

    def test_mcp_server_accepts_both_wire_prefixes(self):
        import tempfile

        self.assertEqual(server_name("mcp__bakeoff__submit_choice"), "submit_choice")
        self.assertEqual(server_name("bakeoff_submit_choice"), "submit_choice")
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.jsonl"
            proc = subprocess.Popen(
                [sys.executable, str(BAKE / "mcp_server.py"), "--log", str(log), "--task-id", "wire"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            try:
                write_message(
                    proc.stdin,
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
                    },
                )
                self.assertEqual(read_message(proc.stdout)["id"], 1)
                write_message(
                    proc.stdin,
                    {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
                )
                write_message(
                    proc.stdin,
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "bakeoff_submit_choice",
                            "arguments": {"case_id": "ph-01-green-idle", "choice": "push", "reason": "green"},
                        },
                    },
                )
                reply = read_message(proc.stdout)
                self.assertFalse(reply["result"]["isError"])
            finally:
                if proc.stdin:
                    proc.stdin.close()
                if proc.stdout:
                    proc.stdout.close()
                proc.kill()
                proc.wait(timeout=5)
            rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows[0]["name"], "submit_choice")

    def test_labels_written_is_the_newest_source_stamp(self):
        fresh = build()
        atg = json.loads(
            (ROOT / "pipelines/dogfood/atg-compile/receipt-live-qwen36-35b.json").read_text(encoding="utf-8")
        )
        laya = json.loads((ROOT / "data/decision-gates/laya-trial.cases.v0.json").read_text(encoding="utf-8"))
        bench3 = json.loads(
            (ROOT / "pipelines/dogfood/local-bench-3/receipt.json").read_text(encoding="utf-8")
        )
        bench5 = json.loads(
            (ROOT / "pipelines/dogfood/local-bench-5/receipt-qwen36-ollama.json").read_text(encoding="utf-8")
        )
        newest = max(laya["labels_written"], bench3["finished"], bench5["finished"], atg["when"])
        self.assertEqual(labels_written_stamp(), newest)
        self.assertEqual(fresh["labels_written"], newest)
        self.assertEqual(fresh["labels_written"], atg["when"])
        committed = json.loads(
            (ROOT / "data/decision-gates/hermes-bakeoff.tasks.v0.json").read_text(encoding="utf-8")
        )
        self.assertEqual(committed["labels_written"], fresh["labels_written"])
        self.assertEqual(
            [item["oracle"] for item in committed["tasks"]],
            [item["oracle"] for item in fresh["tasks"]],
        )
        self.assertNotEqual(fresh["labels_written"], "2026-10-19T18:00:00Z")

    def test_rescore_reads_the_committed_receipt_only(self):
        import tempfile

        src = ROOT / "pipelines/dogfood/hermes-bakeoff/results.json"
        bundle = json.loads(
            (ROOT / "data/decision-gates/hermes-bakeoff.tasks.v0.json").read_text(encoding="utf-8")
        )
        original = json.loads(src.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "results.json"
            copy.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(BAKE / "run.py"),
                    "--rescore",
                    str(copy),
                    "--tasks",
                    str(ROOT / "data/decision-gates/hermes-bakeoff.tasks.v0.json"),
                    "--out",
                    str(Path(tmp) / "rescored.json"),
                ],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
            rescored = json.loads((Path(tmp) / "rescored.json").read_text(encoding="utf-8"))
        self.assertEqual(rescored["summary"]["hermes"]["n_pass"], original["summary"]["hermes"]["n_pass"])
        self.assertEqual(rescored["summary"]["baseline"]["n_pass"], original["summary"]["baseline"]["n_pass"])
        self.assertEqual(rescored["verdict"], original["verdict"])
        # A direct call also ignores a missing transcript dir.
        again = rescore_payload(original, bundle["tasks"])
        self.assertEqual(again["summary"]["hermes"]["n_pass"], 26)
        self.assertEqual(again["summary"]["baseline"]["n_pass"], 25)

    def test_run_records_start_before_the_closing_ollama_ps(self):
        import tempfile
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        seen = {"ps": 0, "ps_done": None}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                path = self.path.split("?", 1)[0]
                if path == "/api/tags":
                    body = json.dumps({"models": [{"name": "qwen3.6:35b"}]}).encode()
                elif path == "/api/version":
                    body = json.dumps({"version": "test"}).encode()
                elif path == "/api/ps":
                    seen["ps"] += 1
                    if seen["ps"] >= 2:
                        import time as _time

                        _time.sleep(0.35)
                        seen["ps_done"] = _time.time()
                    body = json.dumps({"models": []}).encode()
                else:
                    body = b"{}"
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt, *args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "results.json"
                proc = subprocess.run(
                    [
                        sys.executable,
                        str(BAKE / "run.py"),
                        "--live",
                        "--skip-ctx-probe",
                        "--keep-model",
                        "--task-ids",
                        "__none__",
                        "--num-ctx",
                        "65536",
                        "--base-url",
                        f"http://127.0.0.1:{port}/v1",
                        "--hermes-python",
                        sys.executable,
                        "--hermes-checkout",
                        str(ROOT),
                        "--hermes-home",
                        str(Path(tmp) / "hermes-home"),
                        "--work",
                        str(Path(tmp) / "work"),
                        "--out",
                        str(out),
                    ],
                    cwd=ROOT,
                    env=dict(os.environ, HERMES_BAKEOFF_MEM_FLOOR_KIB="0"),
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                self.assertEqual(proc.returncode, 0, proc.stdout[-400:] + proc.stderr[-400:])
                payload = json.loads(out.read_text(encoding="utf-8"))
        finally:
            server.shutdown()
        started = parse_ts(payload["meta"]["started"])
        self.assertIsNotNone(seen["ps_done"])
        self.assertLess(started, seen["ps_done"] - 0.2)
        self.assertEqual(payload["meta"]["tool_search"], "off")
        self.assertIn("think=false", payload["meta"]["thinking_control"])

    def test_memory_gate_override_returns_without_waiting(self):
        import time

        import run as bake_run

        saved = os.environ.get("HERMES_BAKEOFF_MEM_FLOOR_KIB")
        os.environ["HERMES_BAKEOFF_MEM_FLOOR_KIB"] = "0"
        try:
            began = time.time()
            kib = bake_run.wait_for_memory(10**12)
        finally:
            if saved is None:
                os.environ.pop("HERMES_BAKEOFF_MEM_FLOOR_KIB", None)
            else:
                os.environ["HERMES_BAKEOFF_MEM_FLOOR_KIB"] = saved
        self.assertGreaterEqual(kib, 0)
        self.assertLess(time.time() - began, 5)

    def test_think_proxy_forces_chat_and_leaves_unload_alone(self):
        import threading
        import urllib.request

        seen = {"bodies": []}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self._reply({"models": []})

            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length)
                seen["bodies"].append({"path": self.path.split("?", 1)[0], "body": json.loads(raw.decode())})
                self._reply({"ok": True})

            def _reply(self, payload):
                body = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt, *args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        proxy = ThinkProxy.start(f"http://127.0.0.1:{server.server_address[1]}/v1")
        secret = "sk-should-not-leak"
        try:
            chat = json.dumps(
                {
                    "model": "qwen3.6:35b",
                    "temperature": 0.9,
                    "think": True,
                    "messages": [{"role": "user", "content": secret}],
                }
            ).encode()
            request = urllib.request.Request(
                proxy.base_v1 + "/chat/completions",
                data=chat,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 200)
            unload = json.dumps({"model": "qwen3.6:35b", "keep_alive": 0, "prompt": ""}).encode()
            request = urllib.request.Request(
                proxy.root + "/api/generate",
                data=unload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 200)
        finally:
            proxy.close()
            server.shutdown()
            server.server_close()
        chat_row = next(row for row in seen["bodies"] if row["path"] == "/v1/chat/completions")
        self.assertEqual(chat_row["body"]["temperature"], 0)
        self.assertEqual(chat_row["body"]["seed"], 1)
        self.assertIs(chat_row["body"]["think"], False)
        self.assertEqual(chat_row["body"]["reasoning_effort"], "none")
        self.assertEqual(chat_row["body"]["messages"][0]["content"], secret)
        unload_row = next(row for row in seen["bodies"] if row["path"] == "/api/generate")
        self.assertEqual(unload_row["body"]["keep_alive"], 0)
        self.assertNotIn("think", unload_row["body"])
        public = json.dumps(proxy.forced)
        self.assertNotIn(secret, public)
        self.assertIn("think", public)

    def test_hermes_config_turns_tool_search_off(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            _write_config(home, "qwen3.6:35b", "http://127.0.0.1:9/v1", 65536, home / "calls.jsonl", "t1")
            text = (home / "config.yaml").read_text(encoding="utf-8")
        self.assertIn("tool_search:", text)
        self.assertIn("enabled: off", text)
        self.assertIn('reasoning_effort: "none"', text)
        self.assertNotIn("api_key: sk-", text)

    def test_child_tmpdir_stays_in_the_worktree(self):
        root = (ROOT / "tmp").resolve()
        old = os.environ.pop("TMPDIR", None)
        try:
            got = scrubbed()["TMPDIR"]
            self.assertTrue(Path(got).resolve().is_relative_to(root))
            self.assertNotEqual(Path(got).resolve(), Path("/tmp"))
            os.environ["TMPDIR"] = "/var/tmp"
            outside = child_tmpdir()
            self.assertTrue(Path(outside).resolve().is_relative_to(root))
            custom = root / "custom-scratch"
            os.environ["TMPDIR"] = str(custom)
            self.assertEqual(Path(child_tmpdir()).resolve(), custom.resolve())
        finally:
            if old is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = old

    def test_opencode_run_tmpdir_stays_under_repo_tmp(self):
        """A hardcoded TMPDIR=/tmp in the opencode child must fail this test."""
        import opencode_arm

        base = Path(tempfile.mkdtemp(prefix="opencode-tmp-", dir=ROOT / "tmp"))
        out = base / "out"
        out.mkdir()
        captured = {}

        def fake_run(argv, **kwargs):
            captured["env"] = kwargs["env"]
            return subprocess.CompletedProcess(argv, 0, "", "")

        old = os.environ.get("TMPDIR")
        os.environ["TMPDIR"] = str(base)
        try:
            with mock.patch.object(opencode_arm.shutil, "which", return_value="/bin/true"):
                with mock.patch.object(opencode_arm.subprocess, "run", side_effect=fake_run):
                    result = opencode_arm.run_task(
                        {"id": "t", "prompt": "ping"},
                        "sys",
                        "model",
                        "http://127.0.0.1:9/v1",
                        1024,
                        base / "calls.jsonl",
                        out,
                    )
            self.assertIsNone(result["error"])
            got = Path(captured["env"]["TMPDIR"]).resolve()
            self.assertEqual(got, base.resolve())
            self.assertNotEqual(got, Path("/tmp"))
        finally:
            if old is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = old
            shutil.rmtree(base, ignore_errors=True)


@pytest.mark.live
class HermesBakeoffLiveTests(unittest.TestCase):
    """Live two-task run. unittest and pytest both report a named skip unless HERMES_BAKEOFF_LIVE=1."""

    @unittest.skipUnless(os.environ.get("HERMES_BAKEOFF_LIVE") == "1", "live deselected; set HERMES_BAKEOFF_LIVE=1")
    def test_live_two_tasks_per_arm(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(BAKE / "run.py"),
                "--live",
                "--limit",
                "2",
                "--skip-ctx-probe",
                "--num-ctx",
                "65536",
                "--keep-model",
                "--out",
                str(ROOT / "tmp" / "bakeoff" / "live-pytest.json"),
                "--work",
                str(ROOT / "tmp" / "bakeoff" / "live-pytest"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=900,
        )
        if proc.returncode != 0:
            self.fail(proc.stdout[-500:] + proc.stderr[-500:])
        payload = json.loads((ROOT / "tmp" / "bakeoff" / "live-pytest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(payload["rows"]["hermes"]), 2)
        self.assertEqual(len(payload["rows"]["baseline"]), 2)


if __name__ == "__main__":
    unittest.main()
