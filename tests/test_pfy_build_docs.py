"""Operator card for ./pfy build stays readable without the runner source.

Reads docs/ops/pfy-build-daily.md and docs/modules/pfy-build.md. Does not
start a build. Delete a PASS fact, an exit code, a failure name, or point a
relative link at a missing file and this goes red.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = (
    ROOT / "docs" / "ops" / "pfy-build-daily.md",
    ROOT / "docs" / "modules" / "pfy-build.md",
)

# Inline links and images. The first token is the target. A title after a
# space is not part of the path. Reference definitions are a second pass.
_INLINE_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_REF_DEF = re.compile(r"(?m)^\[(?P<id>[^\]]+)\]:\s*(\S+)")

_LOCAL_OPT_IN = re.compile(r"--local`?\s+is opt-in and not the default")
_P_WRAP = re.compile(r"-p`?\s+remains the jev dogfood wrap")
_EXIT_ROWS = (
    re.compile(r"(?m)^\| 0 \| PASS"),
    re.compile(r"(?m)^\| 1 \| FAIL"),
    re.compile(r"(?m)^\| 2 \| usage"),
    re.compile(r"(?m)^\| 3 \| TIMEOUT"),
    re.compile(r"(?m)^\| 4 \| BLOCKED"),
)
_REASONS = (
    "rate-limit",
    "unauthenticated",
    "review-rejected",
    "no-change",
    "scope-commit-mismatch",
    "interrupted",
    "ABORTED",
    "gate red",
    "dirty caller",
)
# Each failure the card names has a recovery a reader can follow.
_RECOVERY = (
    "A rate limit does not auto-start `--local`.",
    "The runner does not read `auth.json`.",
    "log in",
    "gate tail",
    "--no-review",
    "empty diff is still `no-change`",
    "reviewed path list",
    "worktree-failed",
    "process group",
    "no-receipt",
    "`--reap` exits 0 while the receipt `status` is `ABORTED`.",
    "pfy-cloud-build/1",
    "pipelines/dogfood/build-cloud/",
    "pipelines/dogfood/build/",
    "scripts/pfy_build_cloud.py",
)


def _link_targets(text: str) -> list[str]:
    targets = [m.group(1).strip() for m in _INLINE_LINK.finditer(text)]
    targets.extend(m.group(2).strip() for m in _REF_DEF.finditer(text))
    return targets


def missing_relative_links(text: str, doc_path: Path) -> list[str]:
    """Return relative link targets that are not files in this repo.

    Fail: a card links scripts/pfy_build_cloud.py or any other path that is
    not on this branch. Recover: mention that path as inline code, or link a
    file that exists under the repo root.
    """
    missing: list[str] = []
    for raw in _link_targets(text):
        target = raw.split()[0]
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        path = target.split("#", 1)[0]
        if not path:
            continue
        resolved = (doc_path.parent / path).resolve()
        try:
            resolved.relative_to(ROOT)
        except ValueError:
            missing.append(raw)
            continue
        if not resolved.is_file():
            missing.append(raw)
    return missing


class PfyBuildDocsContractTest(unittest.TestCase):
    def test_both_docs_state_the_daily_command_and_exit_codes(self):
        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            # Fail: daily command dropped, so the reader cannot tell cloud from -p.
            # Recover: put `./pfy build "<task>"` back as the daily command.
            self.assertIn('./pfy build', text, path.name)
            self.assertIn('"<task>"', text, path.name)
            # Fail: an exit code row dropped. Recover: restore 0 PASS, 1 FAIL,
            # 2 usage, 3 TIMEOUT, 4 BLOCKED.
            for row in _EXIT_ROWS:
                self.assertRegex(text, row, path.name)
            self.assertRegex(text, _LOCAL_OPT_IN, path.name)
            self.assertRegex(text, _P_WRAP, path.name)
            self.assertIn("pfy-cloud-build/1", text, path.name)

    def test_both_docs_name_each_failure_and_how_to_recover(self):
        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            for reason in _REASONS:
                # Fail: a named failure disappeared. Recover: put the reason
                # back in the failure table with its exit and recovery.
                self.assertIn(reason, text, f"{path.name} missing {reason}")
            for phrase in _RECOVERY:
                # Fail: the name is present but the reader has no next step.
                # Recover: put the recovery sentence back next to that case.
                self.assertIn(phrase, text, f"{path.name} missing {phrase}")
            # Fail: the cloud runner was linked and the link dangles.
            # Recover: keep scripts/pfy_build_cloud.py as inline code.
            self.assertNotRegex(
                text,
                r"\]\([^)]*pfy_build_cloud\.py",
                path.name,
            )

    def test_relative_markdown_links_resolve_on_this_branch(self):
        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            missing = missing_relative_links(text, path)
            self.assertEqual(missing, [], f"{path.name} dangling {missing}")

    def test_link_checker_rejects_a_missing_relative_target(self):
        # Fail: the checker ignores relative links, so a dangling card stays green.
        # Recover: resolve the target from the doc and require a file in-repo.
        text = "See [missing](does-not-exist-pfy-build.md)."
        missing = missing_relative_links(text, DOCS[0])
        self.assertEqual(missing, ["does-not-exist-pfy-build.md"])

    def test_link_checker_accepts_an_existing_file_and_ignores_urls(self):
        # Fail: a real in-repo link is flagged, or an http link must exist on disk.
        # Recover: accept files under the repo root and skip http(s) and mailto.
        text = (
            "See [card](pfy-build-daily.md) and "
            "[off repo](https://example.invalid/not-a-file)."
        )
        self.assertEqual(missing_relative_links(text, DOCS[0]), [])


if __name__ == "__main__":
    unittest.main()
