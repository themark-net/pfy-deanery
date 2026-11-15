"""Behavior tests for pfy build -p and decision route escalate exit contract."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


jev = _load("pfy_jev_230", "scripts/pfy_jev_230.py")
build = _load("pfy_build_p", "scripts/pfy_build_p.py")


class RouteEscalateExitTests(unittest.TestCase):
    def test_conf_low_is_escalate_exit_3_not_broken(self):
        os.environ["PFY_JEV_CONF_GATE"] = "0.99"
        try:
            low = jev.decide_choice(
                "ambiguous state",
                {"a": "maybe", "b": "also maybe", "c": "unclear"},
            )
        finally:
            os.environ.pop("PFY_JEV_CONF_GATE", None)
        self.assertFalse(low.get("auto_act"))
        self.assertEqual(jev.classify_decision(low), "escalate")
        self.assertEqual(jev.decision_exit_code(low), jev.EXIT_ESCALATE)
        text = jev.format_decision_cli(low)
        self.assertTrue(text.startswith("ESCALATE"), text)
        self.assertNotIn("tool failure", text.lower())

    def test_route_main_escalate_rc(self):
        os.environ["PFY_JEV_CONF_GATE"] = "0.99"
        try:
            rc = jev.main(["--route"])
        finally:
            os.environ.pop("PFY_JEV_CONF_GATE", None)
        self.assertEqual(rc, jev.EXIT_ESCALATE)

    def test_ready_exit_0(self):
        # Peaked criteria → high margin
        rec = jev.decide_choice(
            "push green tip now",
            {"push": "push green tip now", "hold": "zzzz unrelated hold"},
        )
        if not rec.get("auto_act"):
            self.skipTest("logit margin not peaked enough in this environment")
        self.assertEqual(jev.classify_decision(rec), "ready")
        self.assertEqual(jev.decision_exit_code(rec), jev.EXIT_READY)


class BuildHelperFailRecoverTests(unittest.TestCase):
    def test_missing_grok_on_path_fails_honestly(self):
        with tempfile.TemporaryDirectory(prefix="pfy-build-") as td:
            td = Path(td)
            # Empty PATH → which('grok') is None
            rc = build.build_p(
                "should not run",
                cwd=td,
                repo=ROOT,
                dry_run=False,
                path_env="",  # empty PATH
            )
            self.assertEqual(rc, build.EXIT_FAIL)
            receipts = list((td / "pipelines" / "dogfood" / "build").glob("*/receipt.jsonl"))
            self.assertTrue(receipts, "receipt.jsonl must be written on fail")
            lines = receipts[0].read_text(encoding="utf-8").strip().splitlines()
            self.assertGreaterEqual(len(lines), 2)
            rows = [json.loads(x) for x in lines]
            self.assertEqual(rows[0]["event"], "start")
            self.assertTrue(any(r.get("reason") == "grok_missing" for r in rows), rows)

    def test_dry_run_writes_real_receipt_without_exec_grok(self):
        with tempfile.TemporaryDirectory(prefix="pfy-build-dry-") as td:
            td = Path(td)
            # Provide a fake grok on PATH so missing-bin check passes; dry-run must not exec it
            fake_bin = td / "bin"
            fake_bin.mkdir()
            fake_grok = fake_bin / "grok"
            fake_grok.write_text("#!/bin/sh\necho UNEXPECTED_GROK_EXEC >&2\nexit 99\n")
            fake_grok.chmod(0o755)
            # Auth file under fake GROK_HOME so auth check can pass if dry_run skipped auth —
            # dry_run skips auth failure; still ok.
            gh = td / "grok-home"
            gh.mkdir()
            (gh / "auth.json").write_text('{"token":"test-not-real"}')
            path_env = "%s%s%s" % (fake_bin, os.pathsep, os.environ.get("PATH", ""))
            with mock.patch.dict(os.environ, {"GROK_HOME": str(gh)}, clear=False):
                rc = build.build_p(
                    "dry-run prompt",
                    cwd=td,
                    repo=ROOT,
                    dry_run=True,
                    path_env=path_env,
                    grok_home=gh,
                )
            self.assertEqual(rc, build.EXIT_OK)
            receipts = list((td / "pipelines" / "dogfood" / "build").glob("*/receipt.jsonl"))
            self.assertEqual(len(receipts), 1)
            rows = [json.loads(x) for x in receipts[0].read_text().splitlines() if x.strip()]
            events = [r["event"] for r in rows]
            self.assertIn("start", events)
            self.assertIn("toolset_apply", events)
            self.assertIn("decision_smoke", events)
            self.assertIn("decision_route_shadow", events)
            self.assertIn("grok_p", events)
            self.assertIn("done", events)
            grok_row = next(r for r in rows if r["event"] == "grok_p")
            self.assertTrue(grok_row.get("dry_run"))
            # Fake grok must not have been executed
            self.assertNotEqual(grok_row.get("rc"), 99)


# Fixed task. Same text for trimmed vs full. Unique so a merged prompt cannot hide the split.
FIXTURE_TASK = (
    "FIXTURE_TASK_D3_263\n"
    "Keep the jev gate and record preamble size apart from this task.\n"
)
# Body line that lives only in the full jev-decision skill, not in the lean contract.
_FULL_SKILL_MARKER = "Official TypeSafe agent skill"


class PreambleTrimTests(unittest.TestCase):
    """#263 trimmed preamble is smaller than the full skill dump and still gates.

    Fail: skill bodies inlined (tokens jump, ratio ~1) or the receipt has no
    preamble size (cbda54a). Recover: default trimmed pointer; set
    PFY_BUILD_FULL_PREAMBLE=1 only when the full dump is required.
    """

    def test_trimmed_preamble_bounded_against_full_dump(self):
        # How it fails: re-inlining SKILL.md blows past 400 tokens or 1/4 of full.
        # Recover: put the gate, exits, and path pointer back; leave bodies in full mode.
        trimmed = build.build_preamble(ROOT, mode="trimmed")
        full = build.build_preamble(ROOT, mode="full")
        trimmed_tok = max(1, (len(trimmed) + 3) // 4)
        full_tok = max(1, (len(full) + 3) // 4)
        self.assertLessEqual(trimmed_tok, 400, "trimmed preamble_tokens_est=%s chars=%s" % (trimmed_tok, len(trimmed)))
        self.assertGreater(full_tok, trimmed_tok)
        # ratio ≤ 0.25 ↔ 4 * trimmed <= full
        self.assertLessEqual(4 * trimmed_tok, full_tok, "trimmed/full=%s/%s" % (trimmed_tok, full_tok))
        self.assertRegex(trimmed, r"0\.85|PFY_JEV_CONF_GATE")
        self.assertIn("3=escalate", trimmed)
        self.assertIn("escalate", trimmed.lower())
        self.assertIn("pipelines/dogfood/build/", trimmed)
        self.assertIn("GROK_HOME/skills/pfy-jev-decision", trimmed)
        skill = (ROOT / "bootstrap/grok-cli/skills/jev-decision/SKILL.md").read_text(encoding="utf-8")
        self.assertIn(_FULL_SKILL_MARKER, skill)
        self.assertIn(_FULL_SKILL_MARKER, full)
        self.assertNotIn(_FULL_SKILL_MARKER, trimmed)
        self.assertNotIn("FIXTURE_TASK_D3_263", trimmed)
        self.assertEqual(build.preamble_mode_from_env({}), "trimmed")
        self.assertEqual(build.preamble_mode_from_env({"PFY_BUILD_FULL_PREAMBLE": "1"}), "full")

    def _fake_grok(self, bin_dir: Path, record_dir: Path) -> None:
        bin_dir.mkdir(parents=True, exist_ok=True)
        record_dir.mkdir(parents=True, exist_ok=True)
        script = bin_dir / "grok"
        script.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "from pathlib import Path\n"
            "rec = Path(os.environ['RECORD_DIR'])\n"
            "rec.mkdir(parents=True, exist_ok=True)\n"
            "(rec / 'grok-home').write_text(os.environ.get('GROK_HOME', ''))\n"
            "(rec / 'prompt').write_text(sys.argv[2] if len(sys.argv) > 2 else '')\n"
            "(rec / 'argv').write_text('\\n'.join(sys.argv))\n"
            "raise SystemExit(0)\n"
        )
        script.chmod(0o755)

    def test_dry_run_receipt_records_preamble_size_apart_from_task(self):
        # How it fails: start row has only prompt_head (pre-#263). Recover: write chars/4 fields.
        with tempfile.TemporaryDirectory(prefix="pfy-build-preamble-") as td:
            td = Path(td)
            fake_bin = td / "bin"
            gh = td / "grok-home-real"
            gh.mkdir()
            (gh / "auth.json").write_text('{"token":"test-not-real-0123456789"}')
            (gh / "SHOULD_NOT_COPY.txt").write_text("whole-tree-copy")
            decoy = gh / "skills" / "marketing-council"
            decoy.mkdir(parents=True)
            (decoy / "SKILL.md").write_text("DECOY_SKILL_BODY " * 200)
            self._fake_grok(fake_bin, td / "record")
            path_env = "%s%s%s" % (fake_bin, os.pathsep, os.environ.get("PATH", ""))
            rc = build.build_p(
                FIXTURE_TASK,
                cwd=td,
                repo=ROOT,
                dry_run=True,
                path_env=path_env,
                grok_home=gh,
            )
            self.assertEqual(rc, build.EXIT_OK)
            receipts = list((td / "pipelines" / "dogfood" / "build").glob("*/receipt.jsonl"))
            self.assertEqual(len(receipts), 1)
            rows = [json.loads(x) for x in receipts[0].read_text(encoding="utf-8").splitlines() if x.strip()]
            start = next(r for r in rows if r["event"] == "start")
            self.assertEqual(start.get("preamble_mode"), "trimmed")
            self.assertEqual(start.get("preamble_tokens_method"), "chars/4")
            self.assertEqual(start.get("task_prompt_chars"), len(FIXTURE_TASK))
            self.assertEqual(start.get("task_prompt_tokens_est"), max(1, (len(FIXTURE_TASK) + 3) // 4))
            preamble = build.build_preamble(ROOT, mode="trimmed")
            self.assertEqual(start.get("preamble_chars"), len(preamble))
            self.assertEqual(start.get("preamble_tokens_est"), max(1, (len(preamble) + 3) // 4))
            self.assertLessEqual(start["preamble_tokens_est"], 400)
            self.assertNotEqual(start["preamble_chars"], start["task_prompt_chars"])
            self.assertNotIn("FIXTURE_TASK_D3_263", preamble)

            grok_row = next(r for r in rows if r["event"] == "grok_p")
            argv = grok_row["argv"]
            self.assertIn("--output-format", argv)
            self.assertEqual(argv[argv.index("--output-format") + 1], "plain")
            composed = argv[argv.index("-p") + 1]
            self.assertTrue(composed.startswith(preamble), composed[:80])
            self.assertIn("--- task ---\n" + FIXTURE_TASK, composed)
            self.assertIn("3=escalate", composed)
            self.assertNotIn(_FULL_SKILL_MARKER, composed.split("--- task ---", 1)[0])

            isolated = receipts[0].parent / "grok-home"
            self.assertEqual(grok_row.get("grok_home"), str(isolated))
            self.assertEqual(
                sorted(p.name for p in (isolated / "skills").iterdir()),
                ["pfy-jev-decision"],
            )
            pointer = (isolated / "skills" / "pfy-jev-decision" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("3=escalate", pointer)
            self.assertRegex(pointer, r"0\.85|PFY_JEV_CONF_GATE")
            self.assertNotIn(_FULL_SKILL_MARKER, pointer)
            self.assertNotIn("DECOY_SKILL_BODY", pointer)
            self.assertFalse((isolated / "SHOULD_NOT_COPY.txt").exists())
            self.assertFalse((isolated / "skills" / "marketing-council").exists())
            self.assertEqual(
                (isolated / "auth.json").read_text(encoding="utf-8"),
                (gh / "auth.json").read_text(encoding="utf-8"),
            )

    def test_child_grok_sees_trimmed_preamble_not_full_skill_tree(self):
        # How it fails: toolset apply writes the full skill into the child GROK_HOME,
        # or grok is handed the real home and loads every skill.
        # Recover: apply keeps the real home; child home is the pointer + auth.json.
        with tempfile.TemporaryDirectory(prefix="pfy-build-child-") as td:
            td = Path(td)
            fake_bin = td / "bin"
            record = td / "record"
            gh = td / "grok-home-real"
            gh.mkdir()
            (gh / "auth.json").write_text('{"token":"test-not-real-0123456789"}')
            (gh / "bundled").mkdir()
            (gh / "SHOULD_NOT_COPY.txt").write_text("whole-tree-copy")
            self._fake_grok(fake_bin, record)
            path_env = "%s%s%s" % (fake_bin, os.pathsep, os.environ.get("PATH", ""))
            state = td / "state"
            with mock.patch.dict(
                os.environ,
                {
                    "PFY_STATE_DIR": str(state),
                    "RECORD_DIR": str(record),
                    "PFY_BUILD_YES": "1",
                },
                clear=False,
            ):
                rc = build.build_p(
                    FIXTURE_TASK,
                    cwd=td,
                    repo=ROOT,
                    dry_run=False,
                    path_env=path_env,
                    grok_home=gh,
                )
            self.assertEqual(rc, build.EXIT_OK, "route/apply/grok failed; see receipt under %s" % td)
            seen_home = (record / "grok-home").read_text(encoding="utf-8")
            prompt = (record / "prompt").read_text(encoding="utf-8")
            self.assertTrue(seen_home.endswith("/grok-home"), seen_home)
            self.assertNotEqual(Path(seen_home).resolve(), gh.resolve())
            self.assertIn("FIXTURE_TASK_D3_263", prompt)
            self.assertIn("3=escalate", prompt)
            self.assertRegex(prompt, r"0\.85|PFY_JEV_CONF_GATE")
            self.assertNotIn(_FULL_SKILL_MARKER, prompt.split("--- task ---", 1)[0])
            pointer = Path(seen_home) / "skills" / "pfy-jev-decision" / "SKILL.md"
            self.assertTrue(pointer.is_file(), pointer)
            body = pointer.read_text(encoding="utf-8")
            self.assertIn("Pointer only", body)
            self.assertNotIn("Do not paint Jev as chat", body)
            self.assertFalse((Path(seen_home) / "SHOULD_NOT_COPY.txt").exists())
            # Apply still landed the real toolset skill on the configured home.
            applied = gh / "skills" / "pfy-jev-decision" / "SKILL.md"
            self.assertTrue(applied.is_file(), "toolset apply did not write the real GROK_HOME skill")
            self.assertIn("Do not paint Jev as chat", applied.read_text(encoding="utf-8"))

    def test_full_preamble_flag_keeps_real_grok_home(self):
        # How it fails: the flag still isolates or still trims. Recover: full inlines bodies
        # and does not swap GROK_HOME.
        with tempfile.TemporaryDirectory(prefix="pfy-build-full-") as td:
            td = Path(td)
            fake_bin = td / "bin"
            gh = td / "grok-home-real"
            gh.mkdir()
            (gh / "auth.json").write_text('{"token":"test-not-real-0123456789"}')
            self._fake_grok(fake_bin, td / "record")
            path_env = "%s%s%s" % (fake_bin, os.pathsep, os.environ.get("PATH", ""))
            with mock.patch.dict(os.environ, {"PFY_BUILD_FULL_PREAMBLE": "1"}, clear=False):
                rc = build.build_p(
                    FIXTURE_TASK,
                    cwd=td,
                    repo=ROOT,
                    dry_run=True,
                    path_env=path_env,
                    grok_home=gh,
                )
            self.assertEqual(rc, build.EXIT_OK)
            receipts = list((td / "pipelines" / "dogfood" / "build").glob("*/receipt.jsonl"))
            rows = [json.loads(x) for x in receipts[0].read_text(encoding="utf-8").splitlines() if x.strip()]
            start = next(r for r in rows if r["event"] == "start")
            self.assertEqual(start.get("preamble_mode"), "full")
            self.assertGreater(start["preamble_tokens_est"], 400)
            self.assertIn(_FULL_SKILL_MARKER, build.build_preamble(ROOT, mode="full", grok_home=gh))
            grok_row = next(r for r in rows if r["event"] == "grok_p")
            self.assertEqual(grok_row.get("grok_home"), str(gh))
            self.assertFalse((receipts[0].parent / "grok-home").exists())
            composed = grok_row["argv"][grok_row["argv"].index("-p") + 1]
            self.assertIn(_FULL_SKILL_MARKER, composed.split("--- task ---", 1)[0])
            self.assertIn("FIXTURE_TASK_D3_263", composed)


# Concrete cap for the fixed fixture. The fixture's user-skills payload alone is
# above this, so copying real_home/skills into dest fails the assert.
FIXTURE_SKILLS_BUNDLE_TOKENS_MAX = 30_000
# Opt-in host probe (CI must leave this unset). Checked before any ~/.grok access.
HOST_BUNDLED_TEST_ENV = "PFY_HOST_BUNDLED_TEST"


def _tree_fingerprint(root: Path) -> str:
    """Content, mode, and symlink-target fingerprint. Does not follow links."""
    digest = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        kept = []
        for name in dirnames:
            child = Path(dirpath) / name
            if child.is_symlink():
                digest.update(b"D")
                digest.update(str(child.relative_to(root)).encode())
                digest.update(os.readlink(child).encode())
                continue
            kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            child = Path(dirpath) / name
            rel = str(child.relative_to(root)).encode()
            if child.is_symlink():
                digest.update(b"L")
                digest.update(rel)
                digest.update(os.readlink(child).encode())
                continue
            st = child.lstat()
            digest.update(b"F")
            digest.update(rel)
            digest.update(str(st.st_mode).encode())
            digest.update(str(st.st_size).encode())
            with child.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    digest.update(chunk)
    return digest.hexdigest()


class SkillsBundleTests(unittest.TestCase):
    """#265: expose bundled skills as dest byte copies, measure them, fail closed.

    How it fails: file symlinks let a dest write change real_home/bundled
    (run 1 write-through). a8977c33 isolates a pointer only (no bundled tree,
    no skills_bundle receipt) and a missing bundled/ still runs grok. A
    directory symlink at dest/bundled, or a copy of real_home/skills,
    over-exposes text or writes the real tree.
    Recover: real dest/bundled tree of byte copies, chmod a-w on the copies
    only, plus a pointer file. Live path exits non-zero with reason
    bundled_missing. PFY_BUILD_FULL_SKILLS=1 restores D3 pointer-only
    isolation and does not keep the real GROK_HOME.
    """

    def _fake_grok(self, bin_dir: Path, record_dir: Path) -> None:
        bin_dir.mkdir(parents=True, exist_ok=True)
        record_dir.mkdir(parents=True, exist_ok=True)
        script = bin_dir / "grok"
        script.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "from pathlib import Path\n"
            "rec = Path(os.environ['RECORD_DIR'])\n"
            "rec.mkdir(parents=True, exist_ok=True)\n"
            "(rec / 'grok-home').write_text(os.environ.get('GROK_HOME', ''))\n"
            "(rec / 'prompt').write_text(sys.argv[2] if len(sys.argv) > 2 else '')\n"
            "(rec / 'argv').write_text('\\n'.join(sys.argv))\n"
            "raise SystemExit(0)\n"
        )
        script.chmod(0o755)

    def _fixture_home(self, root: Path, *, bundled: bool) -> Path:
        gh = root / "grok-home-real"
        gh.mkdir()
        (gh / "auth.json").write_bytes(b'{"token":"test-not-real-0123456789"}')
        user = gh / "skills" / "marketing-council"
        user.mkdir(parents=True)
        (user / "SKILL.md").write_text("USER_SKILL_LEAK\n" * 9000, encoding="utf-8")
        other = gh / "skills" / "catalog-docs"
        other.mkdir(parents=True)
        (other / "SKILL.md").write_text("USER_SKILL_LEAK catalog\n", encoding="utf-8")
        if bundled:
            demo = gh / "bundled" / "skills" / "demo-bundled"
            demo.mkdir(parents=True)
            (demo / "SKILL.md").write_text(
                "BUNDLED_FIXTURE_MARKER\n" + ("bundled line\n" * 30),
                encoding="utf-8",
            )
            (demo / "refs").mkdir()
            (demo / "refs" / "note.md").write_text("bundled ref\n", encoding="utf-8")
            outside = root / "outside"
            outside.mkdir()
            (outside / "secret.txt").write_text("SECRET_OUTSIDE_LEAK", encoding="utf-8")
            (demo / "escape.md").symlink_to(outside / "secret.txt")
            (gh / "bundled" / "alias").symlink_to(outside, target_is_directory=True)
        return gh

    def _run(self, td: Path, gh: Path, *, dry_run: bool, extra_env: dict | None = None) -> tuple[int, Path, str]:
        fake_bin = td / "bin"
        record = td / "record"
        self._fake_grok(fake_bin, record)
        path_env = "%s%s%s" % (fake_bin, os.pathsep, os.environ.get("PATH", ""))
        env = {
            "PFY_STATE_DIR": str(td / "state"),
            "RECORD_DIR": str(record),
            "PFY_BUILD_YES": "1",
        }
        if extra_env:
            env.update(extra_env)
        err = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=False):
            with redirect_stderr(err):
                rc = build.build_p(
                    FIXTURE_TASK,
                    cwd=td,
                    repo=ROOT,
                    dry_run=dry_run,
                    path_env=path_env,
                    grok_home=gh,
                )
        return rc, record, err.getvalue()

    def _receipt_rows(self, cwd: Path) -> list[dict]:
        receipts = list((cwd / "pipelines" / "dogfood" / "build").glob("*/receipt.jsonl"))
        self.assertEqual(len(receipts), 1, receipts)
        return [json.loads(x) for x in receipts[0].read_text(encoding="utf-8").splitlines() if x.strip()]

    def _assert_no_user_skills(self, isolated: Path) -> None:
        self.assertFalse((isolated / "skills" / "marketing-council").exists())
        self.assertFalse((isolated / "skills" / "catalog-docs").exists())
        for path in isolated.rglob("*"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            self.assertNotIn("USER_SKILL_LEAK", text, path)
            self.assertNotIn("SECRET_OUTSIDE_LEAK", text, path)

    def test_fixture_bundle_under_bound_without_user_skills(self):
        # How it fails: user skills copied in, or bundled not copied (a8977c33),
        # or dest/bundled is one directory symlink, or dest files are symlinks
        # (write-through).
        # Recover: byte copies under a real dest/bundled, a-w on those copies;
        # leave real_home/skills out.
        with tempfile.TemporaryDirectory(prefix="pfy-build-bundle-") as td:
            td = Path(td)
            gh = self._fixture_home(td, bundled=True)
            rc, record, _err = self._run(td, gh, dry_run=False)
            self.assertEqual(rc, build.EXIT_OK, _err)
            rows = self._receipt_rows(td)
            start = next(r for r in rows if r["event"] == "start")
            self.assertEqual(start.get("skills_bundle_method"), "chars/4")
            self.assertEqual(start.get("skills_bundle_mode"), "bundled_link")
            self.assertNotEqual(start.get("skills_bundle_chars"), start.get("preamble_chars"))
            self.assertNotEqual(start.get("skills_bundle_chars"), start.get("task_prompt_chars"))
            isolated = Path((record / "grok-home").read_text(encoding="utf-8"))
            chars, tokens = build.measure_skills_bundle(isolated)
            self.assertEqual(start.get("skills_bundle_chars"), chars)
            self.assertEqual(start.get("skills_bundle_tokens_est"), tokens)
            self.assertLessEqual(tokens, FIXTURE_SKILLS_BUNDLE_TOKENS_MAX, tokens)
            self.assertGreater(tokens, 0)
            grok_row = next(r for r in rows if r["event"] == "grok_p")
            self.assertEqual(grok_row.get("skills_bundle_tokens_est"), tokens)
            self.assertEqual(grok_row.get("grok_home"), str(isolated))
            self.assertNotEqual(isolated.resolve(), gh.resolve())

            bundled_root = isolated / "bundled"
            self.assertTrue(bundled_root.is_dir())
            self.assertFalse(bundled_root.is_symlink())
            copied = bundled_root / "skills" / "demo-bundled" / "SKILL.md"
            real_skill = gh / "bundled" / "skills" / "demo-bundled" / "SKILL.md"
            self.assertTrue(copied.is_file(), copied)
            self.assertFalse(copied.is_symlink(), copied)
            self.assertEqual(copied.stat().st_mode & 0o222, 0)
            self.assertEqual(copied.read_bytes(), real_skill.read_bytes())
            self.assertIn("BUNDLED_FIXTURE_MARKER", copied.read_text(encoding="utf-8"))
            ref = bundled_root / "skills" / "demo-bundled" / "refs" / "note.md"
            self.assertTrue(ref.is_file())
            self.assertFalse(ref.is_symlink())
            self.assertEqual(ref.stat().st_mode & 0o222, 0)
            self.assertFalse((bundled_root / "skills").is_symlink())
            self.assertFalse((bundled_root / "alias").exists())
            self.assertFalse((bundled_root / "skills" / "demo-bundled" / "escape.md").exists())
            for path in bundled_root.rglob("*"):
                self.assertFalse(path.is_symlink(), path)
                if path.is_file():
                    self.assertEqual(path.stat().st_mode & 0o222, 0, path)
            self._assert_no_user_skills(isolated)
            auth = isolated / "auth.json"
            self.assertTrue(auth.is_file())
            self.assertFalse(auth.is_symlink())
            self.assertEqual(auth.read_bytes(), (gh / "auth.json").read_bytes())
            self.assertEqual(auth.stat().st_mode & 0o777, 0o600, oct(auth.stat().st_mode))
            self.assertEqual(isolated.stat().st_mode & 0o077, 0, oct(isolated.stat().st_mode))

    def test_pointer_skill_is_a_real_file(self):
        # How it fails: pointer removed, or symlinked into real_home/skills.
        # Removing dest/skills/pfy-jev-decision/SKILL.md fails this test.
        with tempfile.TemporaryDirectory(prefix="pfy-build-pointer-") as td:
            td = Path(td)
            gh = self._fixture_home(td, bundled=True)
            dest = td / "isolated"
            build.isolate_trimmed_grok_home(gh, dest)
            pointer = dest / "skills" / "pfy-jev-decision" / "SKILL.md"
            self.assertTrue(
                pointer.is_file(),
                "removing dest/skills/pfy-jev-decision/SKILL.md fails this test",
            )
            self.assertFalse(pointer.is_symlink())
            text = pointer.read_text(encoding="utf-8")
            self.assertIn("3=escalate", text)
            self.assertRegex(text, r"0\.85|PFY_JEV_CONF_GATE")
            self.assertNotIn(_FULL_SKILL_MARKER, text)
            bundled_skill = dest / "bundled" / "skills" / "demo-bundled" / "SKILL.md"
            self.assertTrue(bundled_skill.is_file(), bundled_skill)
            self.assertFalse(bundled_skill.is_symlink(), bundled_skill)
            self.assertEqual(bundled_skill.stat().st_mode & 0o222, 0)
            self.assertEqual(
                sorted(p.name for p in (dest / "skills").iterdir()),
                ["pfy-jev-decision"],
            )

    def test_dest_write_does_not_change_real_bundled_marker(self):
        # How it fails: dest/bundled/marker.txt is a symlink (or chmod follows
        # one). Opening that path and writing changes real_home/bundled/marker.txt
        # bytes or mode. Measure that follows the link counts outside text.
        # Recover: byte-copy into a real dest file and chmod a-w on the copy
        # only. A later write, even after making the dest path writable, leaves
        # the real bytes and mode unchanged. Symlinks add nothing to the measure.
        known = b"PFY265-MARKER-KNOWN\n"
        with tempfile.TemporaryDirectory(prefix="pfy-build-writethrough-") as td:
            td = Path(td)
            gh = self._fixture_home(td, bundled=True)
            marker = gh / "bundled" / "marker.txt"
            marker.write_bytes(known)
            mode_before = marker.stat().st_mode
            self.assertTrue(mode_before & 0o200, "fixture marker must be user-writable")
            real_fp = _tree_fingerprint(gh / "bundled")
            dest = td / "isolated"
            build.isolate_trimmed_grok_home(gh, dest)
            self.assertEqual(marker.read_bytes(), known)
            self.assertEqual(marker.stat().st_mode, mode_before)
            self.assertEqual(_tree_fingerprint(gh / "bundled"), real_fp)
            dest_marker = dest / "bundled" / "marker.txt"
            self.assertTrue(dest_marker.is_file(), dest_marker)
            self.assertFalse(dest_marker.is_symlink(), dest_marker)
            self.assertFalse((dest / "bundled").is_symlink())
            self.assertEqual(dest_marker.read_bytes(), known)
            self.assertEqual(dest_marker.stat().st_mode & 0o222, 0)
            # Simulate grok opening the dest path. A symlink into the writable
            # real file accepts the write; a read-only copy raises.
            try:
                with dest_marker.open("r+b") as fh:
                    fh.write(b"GROK-WRITE-THROUGH\n")
            except OSError:
                pass
            self.assertEqual(marker.read_bytes(), known)
            self.assertEqual(marker.stat().st_mode, mode_before)
            # Confused grok clears the write bit on the dest path and rewrites.
            # chmod/open on a symlink hit the real file.
            dest_marker.chmod(dest_marker.stat().st_mode | 0o200)
            with dest_marker.open("r+b") as fh:
                fh.seek(0)
                fh.write(b"GROK-WRITE-THROUGH\n")
                fh.truncate()
            self.assertEqual(marker.read_bytes(), known)
            self.assertEqual(marker.stat().st_mode, mode_before)
            self.assertEqual(_tree_fingerprint(gh / "bundled"), real_fp)
            self.assertNotEqual(dest_marker.read_bytes(), known)
            chars_before, _tokens_before = build.measure_skills_bundle(dest)
            leak = td / "leak.txt"
            leak.write_text("MEASURE_FOLLOW_LEAK" * 5000, encoding="utf-8")
            (dest / "bundled" / "leak.txt").symlink_to(leak)
            chars_after, _tokens_after = build.measure_skills_bundle(dest)
            self.assertEqual(chars_before, chars_after)

    def test_dry_run_receipt_has_skills_bundle_field(self):
        # How it fails: start row has no skills_bundle size (a8977c33).
        # Recover: record chars/4 for the linked tree, separate from preamble and task.
        with tempfile.TemporaryDirectory(prefix="pfy-build-bundle-dry-") as td:
            td = Path(td)
            gh = self._fixture_home(td, bundled=True)
            rc, _record, err = self._run(td, gh, dry_run=True)
            self.assertEqual(rc, build.EXIT_OK, err)
            rows = self._receipt_rows(td)
            start = next(r for r in rows if r["event"] == "start")
            for key in (
                "skills_bundle_chars",
                "skills_bundle_tokens_est",
                "skills_bundle_method",
                "skills_bundle_mode",
            ):
                self.assertIn(key, start)
            self.assertEqual(start["skills_bundle_method"], "chars/4")
            self.assertEqual(start["skills_bundle_mode"], "bundled_link")
            self.assertIsInstance(start["skills_bundle_tokens_est"], int)
            self.assertLessEqual(start["skills_bundle_tokens_est"], FIXTURE_SKILLS_BUNDLE_TOKENS_MAX)
            self.assertNotEqual(start["skills_bundle_chars"], start["preamble_chars"])
            self.assertNotEqual(start["skills_bundle_chars"], start["task_prompt_chars"])
            self.assertIn("preamble_tokens_est", start)
            self.assertIn("task_prompt_tokens_est", start)

    def test_missing_bundled_fails_closed_and_full_skills_recovers(self):
        # How it fails: live build keeps going and grok sees the real home (a8977c33).
        # Recover: exit non-zero, receipt reason bundled_missing, do not exec grok.
        # Dry-run may still plan. PFY_BUILD_FULL_SKILLS=1 plans pointer-only,
        # not the real GROK_HOME and not the user skills tree.
        with tempfile.TemporaryDirectory(prefix="pfy-build-nobundle-") as td:
            td = Path(td)
            gh = self._fixture_home(td, bundled=False)
            live = td / "live"
            live.mkdir()
            rc, record, err = self._run(live, gh, dry_run=False)
            self.assertNotEqual(rc, 0)
            self.assertEqual(rc, build.EXIT_FAIL)
            self.assertIn("Refusing to fall back", err)
            self.assertIn("bundled", err.lower())
            rows = self._receipt_rows(live)
            self.assertTrue(any(r.get("reason") == "bundled_missing" for r in rows), rows)
            self.assertNotIn("grok_p", [r["event"] for r in rows])
            self.assertFalse((record / "argv").exists(), "grok must not exec when bundled is missing")

            dry = td / "dry"
            dry.mkdir()
            rc_dry, _record_dry, err_dry = self._run(dry, gh, dry_run=True)
            self.assertEqual(rc_dry, build.EXIT_OK, err_dry)
            dry_rows = self._receipt_rows(dry)
            dry_start = next(r for r in dry_rows if r["event"] == "start")
            self.assertIn("skills_bundle_tokens_est", dry_start)
            self.assertEqual(dry_start.get("skills_bundle_mode"), "bundled_skipped")
            self.assertNotEqual(dry_start.get("skills_bundle_mode"), "full_skills")

            recover = td / "recover"
            recover.mkdir()
            rc2, record2, err2 = self._run(
                recover,
                gh,
                dry_run=False,
                extra_env={"PFY_BUILD_FULL_SKILLS": "1"},
            )
            self.assertEqual(rc2, build.EXIT_OK, err2)
            rows2 = self._receipt_rows(recover)
            start2 = next(r for r in rows2 if r["event"] == "start")
            self.assertEqual(start2.get("skills_bundle_mode"), "pointer_only")
            seen = Path((record2 / "grok-home").read_text(encoding="utf-8"))
            self.assertNotEqual(seen.resolve(), gh.resolve())
            self.assertFalse((seen / "bundled").exists())
            self.assertTrue((seen / "skills" / "pfy-jev-decision" / "SKILL.md").is_file())
            self.assertFalse((seen / "skills" / "pfy-jev-decision" / "SKILL.md").is_symlink())
            self._assert_no_user_skills(seen)

    def test_isolated_auth_json_forced_to_0600(self):
        # How it fails: isolate leaves auth.json at copy2's broader source mode
        # (e.g. 0644) or leaves the isolated home world-readable.
        # Recover: chmod dest auth to 0600 and dest home to 0700 after the copy.
        with tempfile.TemporaryDirectory(prefix="pfy-build-auth-mode-") as td:
            td = Path(td)
            gh = self._fixture_home(td, bundled=True)
            (gh / "auth.json").chmod(0o644)
            self.assertEqual((gh / "auth.json").stat().st_mode & 0o777, 0o644)
            dest = td / "isolated"
            build.isolate_trimmed_grok_home(gh, dest)
            auth = dest / "auth.json"
            self.assertTrue(auth.is_file())
            self.assertFalse(auth.is_symlink())
            self.assertEqual(auth.read_bytes(), (gh / "auth.json").read_bytes())
            self.assertEqual(
                auth.stat().st_mode & 0o777,
                0o600,
                "leaving auth at 0644 (or any mode other than 0600) fails this test",
            )
            self.assertEqual(
                dest.stat().st_mode & 0o077,
                0,
                "world/group-readable isolated home fails this test: %s"
                % oct(dest.stat().st_mode),
            )
            self.assertEqual(dest.stat().st_mode & 0o700, 0o700)

    def test_this_host_bundled_link_under_measured_bound(self):
        # Opt-in only (PFY_HOST_BUNDLED_TEST=1). Default CI / local runs must not
        # touch ~/.grok. Check the env flag BEFORE any Path.home()/.grok access.
        # How it fails (when opted in): dest/bundled is a directory symlink, dest
        # files are symlinks (write-through into real bundled), or user skills
        # are mirrored into dest.
        # Recover: byte copies only, a-w on the dest copies; pointer only under
        # dest/skills. dry-run so toolset apply does not write the real home.
        if os.environ.get(HOST_BUNDLED_TEST_ENV, "").strip() not in ("1", "true", "yes"):
            self.skipTest(
                "set %s=1 to probe this host's ~/.grok/bundled (skipped by default)"
                % HOST_BUNDLED_TEST_ENV
            )
        real = Path.home() / ".grok"
        bundled = real / "bundled"
        try:
            bundled_ok = bundled.is_dir() and not bundled.is_symlink()
        except OSError:
            bundled_ok = False
        if not bundled_ok:
            self.skipTest("opted in but ~/.grok/bundled missing or not a real directory")
        with tempfile.TemporaryDirectory(prefix="pfy-build-host-bundle-") as td:
            td = Path(td)
            # Auth stays on the real home; isolate byte-copies it into the temp dest.
            # Never dry_run=False here: toolset apply writes the configured GROK_HOME.
            # Never write ~/.grok/bundled. The fingerprint catches a chmod or
            # copy that lands on the real tree.
            before = _tree_fingerprint(bundled)
            rc, record, err = self._run(td, real, dry_run=True)
            self.assertEqual(_tree_fingerprint(bundled), before)
            self.assertEqual(rc, build.EXIT_OK, err)
            rows = self._receipt_rows(td)
            start = next(r for r in rows if r["event"] == "start")
            tokens = start.get("skills_bundle_tokens_est")
            self.assertEqual(start.get("skills_bundle_mode"), "bundled_link")
            self.assertIsInstance(tokens, int)
            # No host-specific token cap. Fixture bound is the portable ceiling
            # for the synthetic tree; a real host tree is larger, and must still
            # be finite / positive. User-skills leak is caught by path asserts.
            self.assertGreater(tokens, FIXTURE_SKILLS_BUNDLE_TOKENS_MAX, tokens)
            isolated = next((td / "pipelines" / "dogfood" / "build").glob("*/grok-home"))
            self.assertFalse((isolated / "bundled").is_symlink())
            real_root = bundled.resolve()
            copied = 0
            for path in (isolated / "bundled").rglob("*"):
                self.assertFalse(path.is_symlink(), path)
                if not path.is_file():
                    continue
                src = real_root / path.relative_to(isolated / "bundled")
                self.assertTrue(src.is_file(), src)
                self.assertEqual(path.stat().st_mode & 0o222, 0, path)
                self.assertEqual(path.read_bytes(), src.read_bytes(), path)
                copied += 1
            self.assertGreater(copied, 0)
            self.assertEqual(_tree_fingerprint(bundled), before)
            pointer = isolated / "skills" / "pfy-jev-decision" / "SKILL.md"
            self.assertTrue(pointer.is_file())
            self.assertFalse(pointer.is_symlink())
            auth = isolated / "auth.json"
            if auth.is_file():
                self.assertEqual(auth.stat().st_mode & 0o777, 0o600, oct(auth.stat().st_mode))
            self.assertEqual(isolated.stat().st_mode & 0o077, 0, oct(isolated.stat().st_mode))
            skills = real / "skills"
            if skills.is_dir():
                for child in skills.iterdir():
                    if child.name == "pfy-jev-decision":
                        continue
                    self.assertFalse((isolated / "skills" / child.name).exists(), child.name)
            self.assertFalse((record / "argv").exists())


if __name__ == "__main__":
    unittest.main()
