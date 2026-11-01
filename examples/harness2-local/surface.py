#!/usr/bin/env python3
"""Map the decision harness onto harness2 components, and map it back.

Writable targets are the decision prompt in trial.py and the decision skill
files. AGENTS.md hard rules land in guardrails.md and are read-only. Any other
path is rejected.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROMPT_BEGIN = "# HARNESS2_PROMPT_BEGIN\n"
PROMPT_END = "# HARNESS2_PROMPT_END\n"
TRIAL_REL = "examples/typed-decisions-local/trial.py"
AGENTS_REL = "AGENTS.md"
GATE_PREFIX = "Docs, skills, and reversible dogfood follow"
TOOL_HEAD = "### Custom Scripts, Tools & Automation\n"
TOOL_NEXT = "\n### Autonomous"
GUARD_HEAD = "## Do not\n"
GUARD_NEXT = "\n## Bootstrap environment\n"
TOOL_REL = "tool_descriptions/tool_guidance.md"
GUARD_REL = "guardrails.md"
PROMPT_REL = "systemprompt.md"
# The skill names `python3 scripts/pfy_jev_230.py`. Upstream rejects a skill
# that invokes a script it does not ship. This stub is harness-only: it is not
# an editable repo path, and adopt ignores it when the bytes are unchanged.
HARNESS_SCRIPT = "scripts/pfy_jev_230.py"
HARNESS_SCRIPT_BODY = "print('pfy_jev_230 is not in this workspace')\n"

# The decision task is the #230 Choice set. jev-decision is the skill that
# defines that procedure. Listed in the run log.
DECISION_SKILLS = ("jev-decision",)

# Harness files whose bytes may be written back. guardrails.md is not here.
WRITABLE = {
    PROMPT_REL: TRIAL_REL,
    **{f"skills/{name}/SKILL.md": f".grok/skills/{name}/SKILL.md" for name in DECISION_SKILLS},
}


class SurfaceError(Exception):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> str:
    if not path.is_file():
        raise SurfaceError(f"missing source {path}")
    return path.read_text(encoding="utf-8")


def prompt_span(trial_text: str) -> tuple[int, int, str]:
    begin = trial_text.find(PROMPT_BEGIN)
    if begin < 0:
        raise SurfaceError(f"missing {PROMPT_BEGIN.strip()} in {TRIAL_REL}")
    end = trial_text.find(PROMPT_END, begin)
    if end < 0:
        raise SurfaceError(f"missing {PROMPT_END.strip()} in {TRIAL_REL}")
    region = trial_text[begin:end]
    key = 'return """'
    start = region.find(key)
    if start < 0:
        raise SurfaceError(f"decision_prompt has no return string in {TRIAL_REL}")
    start += len(key)
    stop = region.find('"""', start)
    if stop < 0:
        raise SurfaceError(f"decision_prompt string is not closed in {TRIAL_REL}")
    return begin + start, begin + stop, region[start:stop]


def guardrail_text(agents: str) -> str:
    start = agents.find(GUARD_HEAD)
    end = agents.find(GUARD_NEXT, start if start >= 0 else 0)
    if start < 0 or end < 0:
        raise SurfaceError(f"missing Do-not block in {AGENTS_REL}")
    block = agents[start:end]
    gate = ""
    for line in agents.splitlines(keepends=True):
        if line.startswith(GATE_PREFIX):
            gate = line if line.endswith("\n") else line + "\n"
            break
    if not gate:
        raise SurfaceError(f"missing gate line in {AGENTS_REL}")
    if not block.endswith("\n"):
        block += "\n"
    return block + "\n" + gate


def tool_text(agents: str) -> str:
    start = agents.find(TOOL_HEAD)
    end = agents.find(TOOL_NEXT, start if start >= 0 else 0)
    if start < 0 or end < 0:
        raise SurfaceError(f"missing tool section in {AGENTS_REL}")
    return agents[start:end]


def skill_rel(name: str) -> str:
    return f".grok/skills/{name}/SKILL.md"


def load_sources(repo: Path) -> dict[str, str]:
    """Harness-relative path to text. Raises SurfaceError naming a missing skill."""
    trial = _read(repo / TRIAL_REL)
    _start, _stop, prompt = prompt_span(trial)
    agents = _read(repo / AGENTS_REL)
    out = {
        PROMPT_REL: prompt,
        GUARD_REL: guardrail_text(agents),
        TOOL_REL: tool_text(agents),
    }
    for name in DECISION_SKILLS:
        rel = skill_rel(name)
        path = repo / rel
        if not path.is_file():
            raise SurfaceError(f"missing source skill {rel}")
        out[f"skills/{name}/SKILL.md"] = path.read_text(encoding="utf-8")
    return out


def export_tree(repo: Path, dest: Path) -> dict[str, str]:
    files = load_sources(repo)
    dest.mkdir(parents=True, exist_ok=True)
    if any(dest.iterdir()):
        raise SurfaceError(f"dest not empty: {dest}")
    for rel, text in files.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return files


def write_base(dest: Path) -> None:
    """Adapter hook. Writes the mapped base harness into an empty directory."""
    dest = Path(dest)
    export_tree(repo_root(), dest)
    script = dest / HARNESS_SCRIPT
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(HARNESS_SCRIPT_BODY, encoding="utf-8")


def rule_edits(source: str, proposed: str) -> list[dict]:
    """Diff of AGENTS.md-sourced guardrail lines. Empty when the text matches."""
    if source == proposed:
        return []
    old = source.splitlines()
    new = proposed.splitlines()
    edits = []
    for index, (was, now) in enumerate(zip(old, new), start=1):
        if was != now:
            edits.append({"path": AGENTS_REL, "line": index, "was": was, "now": now})
    if len(new) != len(old):
        edits.append(
            {
                "path": AGENTS_REL,
                "line": 0,
                "was": f"{len(old)} lines",
                "now": f"{len(new)} lines",
            }
        )
    return edits


def enforce_path_allow(present: list[tuple[str, bool]]) -> list[str]:
    """Return harness paths outside the write allow-list.

    ``present`` is ``(rel, changed)``. The prompt and mapped skills may change.
    An unchanged tool-guidance file may sit in the tree. Everything else that
    is new or changed is rejected.
    """
    rejected = []
    for rel, changed in present:
        if rel in WRITABLE:
            continue
        if rel == GUARD_REL:
            continue
        if rel == TOOL_REL and not changed:
            continue
        if rel == HARNESS_SCRIPT and not changed:
            continue
        rejected.append(rel)
    return rejected


def _present(harness: Path, expected: dict[str, str]) -> list[tuple[str, bool]]:
    rows = []
    for path in sorted(harness.rglob("*")):
        # A symlink is changed. Do not stat or read its target, even if missing.
        link = path.is_symlink()
        if not link and not path.is_file():
            continue
        rel = path.relative_to(harness).as_posix()
        if link:
            rows.append((rel, True))
            continue
        text = path.read_text(encoding="utf-8")
        if rel == HARNESS_SCRIPT:
            changed = text != HARNESS_SCRIPT_BODY
        else:
            changed = rel not in expected or text != expected[rel]
        rows.append((rel, changed))
    return rows


def _splice_prompt(trial_text: str, prompt: str) -> str:
    if '"""' in prompt:
        raise SurfaceError("prompt contains a triple quote")
    start, stop, _old = prompt_span(trial_text)
    return trial_text[:start] + prompt + trial_text[stop:]


def adopt(repo: Path, harness: Path, receipt_path: Path) -> dict:
    expected = load_sources(repo)
    rejected_rules: list[dict] = []
    guard_path = harness / GUARD_REL
    if guard_path.is_file():
        rejected_rules = rule_edits(expected[GUARD_REL], guard_path.read_text(encoding="utf-8"))
    rejected_paths = enforce_path_allow(_present(harness, expected))
    written: list[str] = []
    receipt = {
        "rejected_rule_edits": rejected_rules,
        "rejected_paths": rejected_paths,
        "written": written,
    }
    if rejected_rules or rejected_paths:
        _write_receipt(receipt_path, receipt)
        return receipt
    trial_path = repo / TRIAL_REL
    prompt_path = harness / PROMPT_REL
    if prompt_path.is_file():
        prompt = prompt_path.read_text(encoding="utf-8")
        if prompt != expected[PROMPT_REL]:
            trial_path.write_text(_splice_prompt(trial_path.read_text(encoding="utf-8"), prompt), encoding="utf-8")
            written.append(TRIAL_REL)
    for name in DECISION_SKILLS:
        rel = f"skills/{name}/SKILL.md"
        src = harness / rel
        if not src.is_file():
            continue
        text = src.read_text(encoding="utf-8")
        if text != expected[rel]:
            dest = repo / skill_rel(name)
            dest.write_text(text, encoding="utf-8")
            written.append(skill_rel(name))
    receipt["written"] = written
    _write_receipt(receipt_path, receipt)
    return receipt


def _write_receipt(path: Path, receipt: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def _die(exc: SurfaceError) -> int:
    print(str(exc), file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Map the decision harness out and back")
    sub = parser.add_subparsers(dest="cmd", required=True)
    exp = sub.add_parser("export")
    exp.add_argument("--repo", type=Path, required=True)
    exp.add_argument("--dest", type=Path, required=True)
    ad = sub.add_parser("adopt")
    ad.add_argument("--repo", type=Path, required=True)
    ad.add_argument("--harness", type=Path, required=True)
    ad.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "export":
            export_tree(args.repo, args.dest)
            return 0
        receipt = adopt(args.repo, args.harness, args.receipt)
    except SurfaceError as exc:
        return _die(exc)
    for edit in receipt["rejected_rule_edits"]:
        print(f"rejected rule edit {edit['path']} line {edit['line']}", file=sys.stderr)
    for rel in receipt["rejected_paths"]:
        print(f"rejected path {rel}", file=sys.stderr)
    if receipt["rejected_rule_edits"] or receipt["rejected_paths"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
