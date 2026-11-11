"""Catalog-fit triage keeps a bad local-model answer off the Grok lane.

How this fails: a mock that disagrees with a golden is treated as fit, bad
JSON is stored as fit, a low confidence blocks promotion, or a confident
skip_install still starts a trial. How we recover: replay exits non-zero,
unusable JSON escalates (exit 3) and is not fit, low confidence leaves
promotion and the queue unchanged, and a confident negative caps I1, blocks
launch, and drops the queue row. A hard stop still fails first.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import catalog_auto_raise as ar  # noqa: E402
from scripts import catalog_fit_triage as fit  # noqa: E402
from scripts import pfy_jev_230 as jev  # noqa: E402
from scripts import promotion_rules as pr  # noqa: E402

GATE = ROOT / "data" / "decision-gates" / "catalog-fit.v0.json"
LAYA = ROOT / "data" / "decision-gates" / "laya-trial.cases.v0.json"
HERMES = ROOT / "data" / "decision-gates" / "hermes-bakeoff.tasks.v0.json"
TRIAGE = ROOT / "scripts" / "catalog_fit_triage.py"
QUEUE = ROOT / "scripts" / "catalog_eval_queue.py"
RAISE = ROOT / "scripts" / "catalog_auto_raise.py"

# Labels written before any model run. Primary label is accept[0].
EXPECTED = {
    "magpie": ["awareness"],
    "antigravity-manager": ["redundant", "skip_install"],
    "hd-01-optional-tool-skip": ["skip_install"],
    "hd-03-antigravity-skip": ["skip_install"],
    "ch-hd-01-optional-tool-skip": ["skip_install"],
    "litellm": ["fit"],
    "codebase-memory-mcp": ["fit"],
    "write-guard-mcp": ["fit"],
}

GATES = {"modularity_gate": "pass", "value_gate": "pass"}


def _by_id(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("cases") or data.get("tasks") or []
    return {row["id"]: row for row in rows if isinstance(row, dict) and "id" in row}


def _answer(slug: str, verdict: str, confidence: float = 1.0) -> dict:
    overlap = "litellm" if verdict == "redundant" else None
    return {
        "slug": slug,
        "fit": verdict == "fit",
        "overlap_with": overlap,
        "verdict": verdict,
        "reason": "labeled before the model run",
        "confidence": confidence,
    }


def _mock_map(cases: list[dict], overrides: dict | None = None) -> dict:
    overrides = overrides or {}
    out = {}
    for case in cases:
        slug = case["slug"]
        verdict = overrides.get(slug, case["accept"][0])
        out[slug] = _answer(slug, verdict)
    return out


def _env() -> dict:
    env = os.environ.copy()
    env["PFY_JEV_CONF_GATE"] = "0.85"
    env.pop("PFY_CATFIT_MOCK", None)
    return env


def _run(argv: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *argv],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        env=env or _env(),
    )


def _card(slug: str, risk: str = "none") -> dict:
    return {
        "name": slug,
        "slug": slug,
        "integration_stage": "I1",
        "tier_ceiling": "I2",
        "risk_class": risk,
        "uses": "format logs",
        "features": [],
        "tags": [],
        "catalog_tags": [],
        "next_gate": "probe",
        "intent": "probe",
        "evidence": ["make:smoke"],
    }


def _stored(slug: str, verdict: str, confidence: float, exit_code: int = 0) -> dict:
    return {
        "chip_conf": "conf ok" if confidence >= 0.85 else "conf low",
        "confidence": confidence,
        "exit": exit_code,
        "fit": verdict == "fit" and confidence >= 0.85 and exit_code == 0,
        "gate": 0.85,
        "model": "mock",
        "overlap_with": None,
        "reason": "stored for the queue",
        "slug": slug,
        "verdict": verdict,
    }


def _write_fit(root: Path, record: dict) -> None:
    dest = root / "eval" / "catalog-fit" / f"{record['slug']}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _flags(results: list) -> list[tuple[str, bool]]:
    return [(rid, ok) for rid, ok, _detail in results]


class CatalogFitTriageTest(unittest.TestCase):
    def setUp(self) -> None:
        self._gate = os.environ.get("PFY_JEV_CONF_GATE")
        os.environ["PFY_JEV_CONF_GATE"] = "0.85"

    def tearDown(self) -> None:
        if self._gate is None:
            os.environ.pop("PFY_JEV_CONF_GATE", None)
        else:
            os.environ["PFY_JEV_CONF_GATE"] = self._gate

    def _cases(self) -> list[dict]:
        data = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertTrue(data.get("labels_before_models"))
        self.assertEqual(data.get("conf_gate"), 0.85)
        cases = data["cases"]
        self.assertEqual(len(cases), len(EXPECTED))
        got = {case["id"]: case["accept"] for case in cases}
        self.assertEqual(got, EXPECTED)
        for case in cases:
            self.assertEqual(case["accept"][0], case["label"])
            self.assertEqual(case["slug"], case["id"])
        return cases

    def test_goldens_copy_sources_and_positive_fits(self) -> None:
        cases = {case["id"]: case for case in self._cases()}
        laya = _by_id(LAYA)
        hermes = _by_id(HERMES)
        self.assertEqual(cases["hd-01-optional-tool-skip"]["state"], laya["hd-01-optional-tool-skip"]["state"])
        self.assertEqual(cases["hd-01-optional-tool-skip"]["source"], "data/decision-gates/laya-trial.cases.v0.json")
        self.assertEqual(cases["hd-01-optional-tool-skip"]["source_id"], "hd-01-optional-tool-skip")
        self.assertEqual(laya["hd-01-optional-tool-skip"]["label"], "skip_install")
        self.assertEqual(cases["hd-03-antigravity-skip"]["state"], laya["hd-03-antigravity-skip"]["state"])
        self.assertEqual(cases["hd-03-antigravity-skip"]["source_id"], "hd-03-antigravity-skip")
        self.assertEqual(laya["hd-03-antigravity-skip"]["label"], "skip_install")
        self.assertEqual(cases["ch-hd-01-optional-tool-skip"]["state"], laya["hd-01-optional-tool-skip"]["state"])
        self.assertEqual(cases["ch-hd-01-optional-tool-skip"]["source"], "data/decision-gates/hermes-bakeoff.tasks.v0.json")
        self.assertEqual(cases["ch-hd-01-optional-tool-skip"]["source_id"], "ch-hd-01-optional-tool-skip")
        self.assertEqual(hermes["ch-hd-01-optional-tool-skip"]["label"], "skip_install")
        magpie = json.loads((ROOT / "data" / "stages" / "magpie.json").read_text(encoding="utf-8"))
        self.assertIn("Rewrites agent configs", magpie["next_gate"])
        self.assertEqual(magpie["risk_class"], "runtime-takeover")
        anti = json.loads((ROOT / "data" / "stages" / "antigravity-manager.json").read_text(encoding="utf-8"))
        uses = anti["uses"]
        text = " ".join(uses) if isinstance(uses, list) else str(uses)
        self.assertIn("LiteLLM", text)
        for slug in ("litellm", "codebase-memory-mcp", "write-guard-mcp"):
            card = json.loads((ROOT / "data" / "stages" / f"{slug}.json").read_text(encoding="utf-8"))
            self.assertEqual(card["integration_stage"], "I3")
            self.assertEqual(cases[slug]["label"], "fit")

    def test_replay_accepts_labeled_mock_and_rejects_a_wrong_magpie(self) -> None:
        cases = self._cases()
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            good = tmp / "good.json"
            good.write_text(json.dumps(_mock_map(cases)), encoding="utf-8")
            out = tmp / "replay.json"
            proc = _run([str(TRIAGE), "replay", "--mock", str(good), "--out", str(out)])
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn(f"passed {len(cases)} failed 0", proc.stdout)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["failed"], 0)
            self.assertTrue(all(row["ok"] for row in report["results"]))

            bad_map = _mock_map(cases, {"magpie": "fit"})
            bad = tmp / "bad.json"
            bad.write_text(json.dumps(bad_map), encoding="utf-8")
            wrong = _run([str(TRIAGE), "replay", "--mock", str(bad), "--out", str(tmp / "wrong.json")])
            self.assertNotEqual(wrong.returncode, 0)
            self.assertIn("failed", wrong.stdout)
            wrong_report = json.loads((tmp / "wrong.json").read_text(encoding="utf-8"))
            magpie = next(row for row in wrong_report["results"] if row["slug"] == "magpie")
            self.assertFalse(magpie["ok"])
            self.assertEqual(magpie["verdict"], "fit")

    def test_bad_json_escalates_and_is_not_fit(self) -> None:
        samples = [
            "not json",
            "```json\nnot json\n```",
            json.dumps({"slug": "magpie", "fit": True, "overlap_with": None, "verdict": "nope", "reason": "x", "confidence": 1}),
            json.dumps({"slug": "magpie", "fit": True, "overlap_with": None, "verdict": "fit", "reason": "x", "confidence": 1.5}),
            json.dumps({"slug": "magpie", "fit": True, "overlap_with": None, "verdict": "fit", "reason": "x", "confidence": True}),
            json.dumps({"slug": "magpie", "fit": False, "verdict": "awareness", "reason": "x", "confidence": 1}),
        ]
        for text in samples:
            code, rec = fit.triage("magpie", root=ROOT, mock={"magpie": text}, write=False)
            self.assertEqual(code, jev.EXIT_ESCALATE, text)
            self.assertFalse(rec["fit"], text)
            self.assertNotEqual(rec["verdict"], "fit", text)
        with tempfile.TemporaryDirectory() as raw:
            mock = Path(raw) / "mock.json"
            mock.write_text(json.dumps({"magpie": "not json"}), encoding="utf-8")
            proc = _run([str(TRIAGE), "triage", "magpie", "--mock", str(mock)])
            self.assertEqual(proc.returncode, jev.EXIT_ESCALATE, proc.stderr)
            body = json.loads(proc.stdout)
            self.assertFalse(body["fit"])
            self.assertIsNone(body["verdict"])
            self.assertFalse((ROOT / "eval" / "catalog-fit" / "magpie.json").exists())

    def test_low_confidence_escalates_and_mock_skips_the_model(self) -> None:
        code, rec = fit.triage(
            "magpie",
            root=ROOT,
            mock={"magpie": _answer("magpie", "awareness", 0.1)},
            write=False,
        )
        self.assertEqual(code, jev.EXIT_ESCALATE)
        self.assertEqual(rec["verdict"], "awareness")
        self.assertFalse(rec["fit"])
        self.assertEqual(rec["chip_conf"], jev.CHIP_CONF_LOW)
        calls: list[str] = []

        def fake(prompt: str, *, model: str, host: str) -> str:
            calls.append(prompt)
            return "not json"

        def boom(prompt: str, *, model: str, host: str) -> str:
            raise AssertionError("model called")

        old = fit.call_model
        try:
            fit.call_model = fake
            code, rec = fit.triage("litellm", root=ROOT, write=False)
            self.assertEqual(code, jev.EXIT_ESCALATE)
            self.assertFalse(rec["fit"])
            self.assertEqual(len(calls), 1)
            fit.call_model = boom
            code, rec = fit.triage(
                "litellm",
                root=ROOT,
                mock={"litellm": _answer("litellm", "fit")},
                write=False,
            )
            self.assertEqual(code, jev.EXIT_READY)
            self.assertTrue(rec["fit"])
            self.assertEqual(rec["verdict"], "fit")
        finally:
            fit.call_model = old

    def test_promotion_caps_i2_and_launch_but_hard_stop_wins(self) -> None:
        rules = pr.load_rules(ROOT)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            slug = "aa-fit"
            card = _card(slug)
            (root / "data" / "stages").mkdir(parents=True)
            (root / "data" / "stages" / f"{slug}.json").write_text(
                json.dumps(card, indent=2) + "\n", encoding="utf-8",
            )
            ctx = pr.Ctx(card=card, slug=slug, root=root, name=slug, verdict=GATES, mode="apply")

            def stage():
                return pr.stage_allowed(rules, ctx, kind="stage", top="I2")

            missing_allowed, _passed, missing_fail = stage()
            self.assertEqual(missing_allowed, "I2")
            self.assertEqual(_flags(missing_fail), [])
            missing_launch = _flags(pr.launch_results(rules, ctx))
            ctx.mode = "apply"

            _write_fit(root, _stored(slug, "awareness", 0.1, exit_code=0))
            low_allowed, _passed, low_fail = stage()
            self.assertEqual(low_allowed, missing_allowed)
            self.assertEqual(_flags(low_fail), _flags(missing_fail))
            self.assertEqual(_flags(pr.launch_results(rules, ctx)), missing_launch)
            ctx.mode = "apply"
            low_plan = ar.plan(card, GATES, root=root, slug=slug)
            bare_plan = ar.plan(_card(slug), GATES, root=root / "absent", slug=slug)
            self.assertEqual(low_plan["action"], bare_plan["action"])
            self.assertEqual(low_plan["action"], "raise")

            _write_fit(root, _stored(slug, "awareness", 1.0))
            allowed, _passed, failing = stage()
            self.assertEqual(allowed, "I1")
            self.assertEqual([rid for rid, ok, _d in failing if not ok], ["R-catalog-fit"])
            i1, _p, i1_fail = pr.stage_allowed(rules, ctx, kind="stage", top="I1")
            self.assertEqual(i1, "I1")
            self.assertEqual(i1_fail, [])
            ctx.mode = "scan"
            scanned = pr.evaluate(rules, ctx, pr.rule_ids(rules, "stage", "default", "I3"), "I3")
            self.assertNotIn("R-catalog-fit", [rid for rid, _ok, _d in scanned])
            ctx.mode = "apply"
            capped = ar.plan(card, GATES, root=root, slug=slug)
            self.assertNotEqual(capped["action"], "raise")
            self.assertIn("R-catalog-fit", capped["reason"])
            self.assertFalse(capped["hard"])
            self.assertFalse(pr.is_hard_stop(rules, "R-catalog-fit"))

            proc = _run([str(RAISE), "--root", str(root), "--launch-check", slug])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.strip(), f"skip\t{slug}\tR-catalog-fit")

            _write_fit(root, _stored(slug, "awareness", 0.1, exit_code=0))
            quiet = _run([str(RAISE), "--root", str(root), "--launch-check", slug])
            self.assertEqual(quiet.stdout.strip(), f"launch\t{slug}\tnone")

            (root / "eval" / "catalog-fit" / f"{slug}.json").write_text("{", encoding="utf-8")
            _allowed, _passed, broken = stage()
            detail = next(item[2] for item in broken if item[0] == "R-catalog-fit")
            self.assertIn("catalog-fit malformed", detail)

            take = "aa-take"
            take_card = _card(take, risk="runtime-takeover")
            (root / "data" / "stages" / f"{take}.json").write_text(
                json.dumps(take_card, indent=2) + "\n", encoding="utf-8",
            )
            _write_fit(root, _stored(take, "fit", 1.0))
            take_ctx = pr.Ctx(card=take_card, slug=take, root=root, name=take, verdict=GATES, mode="launch")
            failed = [rid for rid, ok, _d in pr.launch_results(rules, take_ctx) if not ok]
            self.assertEqual(failed, ["HS-runtime-takeover"])
            self.assertTrue(pr.is_hard_stop(rules, "HS-runtime-takeover"))
            _write_fit(root, _stored(take, "awareness", 1.0))
            both = [rid for rid, ok, _d in pr.launch_results(rules, take_ctx) if not ok]
            self.assertEqual(both[0], "HS-runtime-takeover")
            self.assertIn("R-catalog-fit", both)
            shown = _run([str(RAISE), "--root", str(root), "--launch-check", take])
            self.assertEqual(shown.stdout.strip(), f"skip\t{take}\tHS-runtime-takeover")

    def test_queue_drops_confident_skip_and_keeps_low_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            stages = tmp / "stages"
            stages.mkdir()
            fit_dir = tmp / "catalog-fit"
            fit_dir.mkdir()
            exc = tmp / "exclusions.tsv"
            exc.write_text("slug\treason\n", encoding="utf-8")
            out = tmp / "queue.tsv"
            for slug in ("drop-skip", "keep-low", "keep-fit"):
                (stages / f"{slug}.json").write_text(json.dumps(_card(slug)), encoding="utf-8")
            _write_fit(tmp, _stored("drop-skip", "skip_install", 1.0))
            # The queue file lives under tmp/eval, so point the helper at fit_dir via a root.
            (fit_dir / "drop-skip.json").write_text(
                (tmp / "eval" / "catalog-fit" / "drop-skip.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (fit_dir / "keep-low.json").write_text(
                json.dumps(_stored("keep-low", "skip_install", 0.1, exit_code=0), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            (fit_dir / "keep-fit.json").write_text(
                json.dumps(_stored("keep-fit", "fit", 1.0), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            def run_queue() -> subprocess.CompletedProcess:
                return _run([
                    str(QUEUE), "--stages", str(stages), "--exclusions", str(exc),
                    "--catalog-fit", str(fit_dir), "--out", str(out),
                ])

            first = run_queue()
            self.assertEqual(first.returncode, 0, first.stderr)
            blob = out.read_bytes()
            second = run_queue()
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(out.read_bytes(), blob)
            self.assertIn("unchanged", second.stdout)
            text = blob.decode("utf-8")
            self.assertNotIn("drop-skip", text)
            self.assertIn("keep-low", text)
            self.assertIn("keep-fit", text)

            previous = out.read_bytes()
            (fit_dir / "drop-skip.json").write_text("{", encoding="utf-8")
            broken = run_queue()
            self.assertNotEqual(broken.returncode, 0)
            self.assertIn("drop-skip.json: catalog-fit malformed", broken.stderr)
            self.assertEqual(out.read_bytes(), previous)

    def test_write_then_queue_agrees_and_garbage_is_not_stored(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            gates = root / "data" / "decision-gates"
            gates.mkdir(parents=True)
            shutil.copy(GATE, gates / "catalog-fit.v0.json")
            stages = root / "data" / "stages"
            stages.mkdir()
            slug = "probe-skip"
            other = "probe-stay"
            for name in (slug, other):
                (stages / f"{name}.json").write_text(json.dumps(_card(name)), encoding="utf-8")
            mock = root / "mock.json"
            mock.write_text(json.dumps({slug: _answer(slug, "skip_install")}), encoding="utf-8")
            proc = _run([
                str(TRIAGE), "--root", str(root), "triage", slug, "--mock", str(mock), "--write",
            ])
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            stored = json.loads((root / "eval" / "catalog-fit" / f"{slug}.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["verdict"], "skip_install")
            self.assertEqual(stored["exit"], 0)
            self.assertFalse(stored["fit"])
            exc = root / "exclusions.tsv"
            exc.write_text("slug\treason\n", encoding="utf-8")
            out = root / "queue.tsv"
            queued = _run([
                str(QUEUE), "--stages", str(stages), "--exclusions", str(exc),
                "--catalog-fit", str(root / "eval" / "catalog-fit"), "--out", str(out),
            ])
            self.assertEqual(queued.returncode, 0, queued.stderr)
            text = out.read_text(encoding="utf-8")
            self.assertNotIn(slug, text)
            self.assertIn(other, text)

            bad = root / "bad.json"
            bad.write_text(json.dumps({"probe-stay": "not json"}), encoding="utf-8")
            junk = _run([
                str(TRIAGE), "--root", str(root), "triage", other, "--mock", str(bad), "--write",
            ])
            self.assertEqual(junk.returncode, jev.EXIT_ESCALATE, junk.stderr)
            self.assertFalse((root / "eval" / "catalog-fit" / f"{other}.json").exists())
            kept = out.read_bytes()
            rerun = _run([
                str(QUEUE), "--stages", str(stages), "--exclusions", str(exc),
                "--catalog-fit", str(root / "eval" / "catalog-fit"), "--out", str(out),
            ])
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            self.assertEqual(out.read_bytes(), kept)


if __name__ == "__main__":
    unittest.main()
