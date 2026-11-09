#!/usr/bin/env python3
"""Public repo guard: only code and product docs go public.

Fails (exit 1) when the tracked tree has:
  1. a file in a private-only path (handoffs, decision and run logs, plans,
     Build drop-ins, internal eval runs, raw grok logs, operator queues);
  2. a new file under docs/ops/ that is not in ci/public-docs-ops-allow.txt;
  3. a .tsv file other than the two code-read catalog inputs;
  4. an employer name (see EMPLOYER_RE) outside an agent-cage attribution line;
  5. under eval/: a traces/ dir, a .jsonl log (inputs under fixtures/ are
     fine), a .log file, or a prose REPORT.md / notes.md;
  6. an absolute /home/<user> path (the agent-cage container user is fine);
  7. the owner's first name in text (LICENSE files are exempt; "Mark the" and
     "Mark it" as verbs and one cited third-party author are fine).

Those files belong in the private ops checkout named by PFY_OPS_ROOT.
Exit 2 on a usage or git error. Runs in scripts/pregate.sh (lint), the
eval-structural workflow, and the light path of scripts/test_select.py.

Usage: python3 scripts/check_public_paths.py [--root DIR] [--paths P ...]
--paths checks only those repo-relative paths (path rules only; still reads
their text for the employer rule). Default: every tracked file.
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW_FILE = "ci/public-docs-ops-allow.txt"

# Private-only globs. fnmatch: "*" also matches "/".
PRIVATE_GLOBS = (
    "docs/HANDOFF-*",
    "docs/PENDING-HANDOFF*",
    "docs/ops/HANDOFF-*",
    "docs/ops/AUTONOMOUS-DECISIONS-*",
    "docs/ops/RUN-LOG-*",
    "docs/ops/PR-BODY-*",
    "docs/ops/GATE-NOTES*",
    "docs/ops/session-brief-*",
    "docs/ops/integrate/tickets/*",
    "docs/plans/*",
    "docs/handoffs/*",
    "docs/research/*",
    "docs/build-dropins/*",
    "docs/dogfood/*",
    "docs/open-questions/*",
    "docs/automation/*handoff*",
    "docs/design/*HANDOFF*",
    "docs/eval/*HANDOFF*",
    "eval/mvp-*",
    "eval/mvp[0-9]*",
    "eval/dogfood[0-9]*",
    "eval/gom-dogfood-*",
    "eval/selfhost*",
    "eval/mutation-*",
    "eval/stop-*",
    "eval/local-build/live-*",
    "pipelines/dogfood/build/*",
    "pipelines/dogfood/d1/*",
    "*/handoffs/*",
    "*/build-dropins/*",
    "*/run-logs/*",
    "*needs-mark*",
    "*grok-stdout*",
    "*grok-stderr*",
    "*grok-usage*",
    "*AUTONOMOUS-DECISIONS-*",
    "*RUN-LOG-*",
)
# Templates that create these files in a new project are product code.
TEMPLATE_PREFIXES = ("bootstrap/project-process/templates/",)
TSV_ALLOWED = {"eval/catalog-queue/queue.tsv", "eval/catalog-queue/exclusions.tsv"}
TSV_ALLOWED_PREFIXES = ("tests/fixtures/",)

# Built from parts so this file does not trip its own employer rule.
_NAMES = ("pn" + "nl", "batt" + "elle", "rich" + "land")
EMPLOYER_RE = re.compile(r"\b(" + "|".join(_NAMES) + r")\b", re.IGNORECASE)
# agent-cage is an upstream project published under that org. Its attribution
# lines may name the org. Only the first name is allowed there.
CAGE_RE = re.compile(r"agent-cage", re.IGNORECASE)
EMPLOYER_EXEMPT = {"scripts/check_public_paths.py", "tests/test_check_public_paths.py"}

# Rule 5: eval/ keeps structured verdicts, receipts, probes, and fixtures.
# Traces, raw logs, and prose reports are operator records.
EVAL_PROSE_NAMES = {"report.md", "notes.md"}
# Rule 6: /home/<user>. Not preceded by a path or word char, so a cache dir
# like .../tools/x/home/.local and $HOME/... do not match.
HOME_RE = re.compile(r"(?<![\w.~$}/-])/home/(?!agent\b)([A-Za-z_][A-Za-z0-9_-]*)")
# Rule 7: built from parts so the guard does not flag itself.
_OWNER = "Ma" + "rk"
OWNER_RE = re.compile(r"\b" + _OWNER + r"\b(?! Ritson\b)(?! (?:the|it)\b)")
TEXT_EXEMPT_PREFIXES = ("LICENSE",)


def git_files(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace").strip() or "git ls-files failed")
    return [p for p in proc.stdout.decode("utf-8", "replace").split("\0") if p]


def load_allow(root: Path) -> set[str]:
    path = root / ALLOW_FILE
    if not path.is_file():
        return set()
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return out


def path_problems(rel: str, allow: set[str]) -> list[str]:
    if rel.startswith(TEMPLATE_PREFIXES):
        return []
    found = []
    for glob in PRIVATE_GLOBS:
        if fnmatch.fnmatchcase(rel, glob):
            found.append(f"{rel}: private-only path ({glob}); move it to PFY_OPS_ROOT")
            break
    if not found and rel.startswith("docs/ops/") and rel not in allow:
        found.append(f"{rel}: new docs/ops file; operator notes go to PFY_OPS_ROOT, reference docs go in {ALLOW_FILE}")
    if rel.endswith(".tsv") and rel not in TSV_ALLOWED and not rel.startswith(TSV_ALLOWED_PREFIXES):
        found.append(f"{rel}: .tsv queue in the public repo; operator queues go to PFY_OPS_ROOT")
    found.extend(eval_problems(rel))
    return found


def eval_problems(rel: str) -> list[str]:
    if not rel.startswith("eval/"):
        return []
    parts = rel.split("/")
    name = parts[-1].lower()
    if "traces" in parts[:-1]:
        return [f"{rel}: trace under eval/; traces go to PFY_OPS_ROOT"]
    if name.endswith(".jsonl") and "fixtures" not in parts[:-1]:
        return [f"{rel}: .jsonl log under eval/; raw logs go to PFY_OPS_ROOT (inputs go under fixtures/)"]
    if name.endswith(".log"):
        return [f"{rel}: .log under eval/; raw logs go to PFY_OPS_ROOT"]
    if name in EVAL_PROSE_NAMES:
        return [f"{rel}: prose report under eval/; reports go to PFY_OPS_ROOT, public keeps VERDICT and receipt files"]
    return []


def _text(root: Path, rel: str) -> str | None:
    try:
        data = (root / rel).read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", "replace")


def text_problems(root: Path, rel: str) -> list[str]:
    """Rules 6 and 7: operator home paths and the owner's name."""
    if rel in EMPLOYER_EXEMPT or rel.split("/")[-1].startswith(TEXT_EXEMPT_PREFIXES):
        return []
    text = _text(root, rel)
    if text is None or (not HOME_RE.search(text) and not OWNER_RE.search(text)):
        return []
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        if HOME_RE.search(line):
            found.append(f"{rel}:{number}: absolute /home/<user> path; use $HOME, ~, or a repo-relative path")
        if OWNER_RE.search(line):
            found.append(f"{rel}:{number}: owner name in public text; say the operator or the maintainer")
    return found


def employer_problems(root: Path, rel: str) -> list[str]:
    if rel in EMPLOYER_EXEMPT:
        return []
    path = root / rel
    try:
        data = path.read_bytes()
    except OSError:
        return []
    if b"\0" in data[:8192]:
        return []
    text = data.decode("utf-8", "replace")
    if not EMPLOYER_RE.search(text):
        return []
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        for match in EMPLOYER_RE.finditer(line):
            first = match.group(1).lower() == _NAMES[0]
            if first and CAGE_RE.search(line):
                continue
            found.append(f"{rel}:{number}: employer name outside agent-cage attribution")
            break
    return found


def check(root: Path, paths: list[str] | None = None) -> list[str]:
    allow = load_allow(root)
    rels = paths if paths is not None else git_files(root)
    problems: list[str] = []
    for rel in rels:
        problems.extend(path_problems(rel, allow))
        problems.extend(employer_problems(root, rel))
        problems.extend(text_problems(root, rel))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail when private operator material is in the public tree.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--paths", nargs="*", default=None)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        problems = check(root, args.paths)
    except RuntimeError as exc:
        print(f"check_public_paths: {exc}", file=sys.stderr)
        return 2
    if problems:
        for line in problems[:200]:
            print(f"FAIL {line}")
        if len(problems) > 200:
            print(f"FAIL ... {len(problems) - 200} more")
        return 1
    print("PASS check_public_paths: no private paths, queues, eval logs, home paths, or names")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
