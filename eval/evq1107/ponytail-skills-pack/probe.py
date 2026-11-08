#!/usr/bin/env python3
"""Probe: does smoke-grok-skills assert the ponytail pack, and is the pack an install gate?

Offline. Reads the pin under ~/.cache/pfy/tools/ponytail-skills-pack/src.
Does not copy the pack into a skills dir and does not call a model.

  python3 eval/evq1107/ponytail-skills-pack/probe.py
  python3 eval/evq1107/ponytail-skills-pack/probe.py --count-verify /path/to/stub
  python3 eval/evq1107/ponytail-skills-pack/probe.py --s7-fixture
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PROBE_DIR = Path(__file__).resolve().parent
VENDOR = REPO / "bootstrap/grok-cli/skills-external/ponytail"
MANIFEST = REPO / "bootstrap/grok-cli/manifest.json"
VERIFY = REPO / "bootstrap/grok-cli/scripts/verify_skills.py"
STRUCTURAL = REPO / "examples/eval-harness/run_structural.py"
EIC = REPO / "scripts/eval_integration_change.py"
OK_LINE = re.compile(r"^  OK (?:source|installed) (\S+)$")
FENCE_OPEN = re.compile(r"^```([A-Za-z0-9]*)\s*$")
FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
NAME_LINE = re.compile(r"^name:\s*[\"']?([a-z0-9][a-z0-9-]*)[\"']?\s*$", re.M)
PHRASES = (
    "do not install",
    "do_not_install",
    "install gate",
    "before it is copied",
    "before copy",
)
SHELL_LANG = {"", "sh", "bash", "shell", "console"}


def pack_record() -> tuple[str, list[str]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    block = manifest["external_skills"]["ponytail"]
    pin = str(block["pinned_commit"])
    names = [str(item) for item in block["skills"]]
    if not pin.startswith("8e69b4a") or len(names) != 6:
        raise SystemExit("manifest pin or skill list does not match the catalog row")
    return pin, names


def asserted_names(output: str, names: set[str]) -> list[str]:
    """Count a skill only when a smoke OK line names it. A loose mention does not count."""
    found: list[str] = []
    for line in output.splitlines():
        match = OK_LINE.match(line)
        if match and match.group(1) in names and match.group(1) not in found:
            found.append(match.group(1))
    return found


def run_cmd(cmd: list[str]) -> tuple[int, str, float]:
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    elapsed = time.perf_counter() - started
    return proc.returncode, (proc.stdout or "") + (proc.stderr or ""), elapsed


def cache_src() -> Path:
    override = os.environ.get("PFY_PONYTAIL_SRC", "")
    if override:
        return Path(override)
    return Path.home() / ".cache/pfy/tools/ponytail-skills-pack/src"


def file_map(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def frontmatter_problem(path: Path, expected: str) -> str:
    match = FRONT.match(path.read_text(encoding="utf-8"))
    if not match:
        return "no-frontmatter"
    block = match.group(1)
    name = NAME_LINE.search(block)
    if not name or name.group(1) != expected:
        return "name"
    if not re.search(r"^description:\s*", block, re.M):
        return "description"
    return ""


def gate_fences(text: str) -> int:
    lines = text.splitlines()
    count = 0
    index = 0
    while index < len(lines):
        match = FENCE_OPEN.match(lines[index])
        if not match:
            index += 1
            continue
        lang = match.group(1).lower()
        index += 1
        body: list[str] = []
        while index < len(lines) and not lines[index].startswith("```"):
            body.append(lines[index])
            index += 1
        if index < len(lines):
            index += 1
        if lang not in SHELL_LANG:
            continue
        blob = "\n".join(body)
        if re.search(r"\b(exit|sys\.exit)\b", blob) and "SKILL" in blob:
            count += 1
    return count


def skill_safety(skills_root: Path, names: list[str]) -> dict:
    problems: list[str] = []
    fences = 0
    phrases = 0
    host_install = 0
    executables = 0
    shebangs = 0
    for name in names:
        path = skills_root / name / "SKILL.md"
        if not path.is_file():
            problems.append("%s missing" % name)
            continue
        problem = frontmatter_problem(path, name)
        if problem:
            problems.append("%s %s" % (name, problem))
        text = path.read_text(encoding="utf-8")
        fences += gate_fences(text)
        folded = text.casefold()
        phrases += sum(folded.count(phrase) for phrase in PHRASES)
        for line in text.splitlines():
            if "npm install -g" in line or "brew upgrade" in line or "curl " in line:
                host_install += 1
        mode = path.stat().st_mode
        if mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            executables += 1
        if text.startswith("#!"):
            shebangs += 1
    return {
        "frontmatter_bad": problems,
        "frontmatter_ok": len(names) - len(problems),
        "shell_fences_that_gate": fences,
        "phrase_hits": phrases,
        "host_install_lines": host_install,
        "executable_skill_files": executables,
        "shebang_skill_files": shebangs,
    }


def load_eic():
    spec = importlib.util.spec_from_file_location("evq_ponytail_eic", EIC)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load paths-pack gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def s7_on(module, root: Path) -> tuple[bool, str]:
    saved = module.ROOT
    try:
        module.ROOT = root
        ok, detail = module.gate_paths_pack()
    finally:
        module.ROOT = saved
    return bool(ok), str(detail)


def write_skill_tree(root: Path, count: int) -> None:
    pack = root / "bootstrap/grok-cli/skills-external/claude-unified-agents"
    for index in range(count):
        skill = pack / ("skill%02d" % index)
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("name: skill%02d\n" % index, encoding="utf-8")


def s7_fixture(module) -> tuple[bool, dict]:
    parent = REPO / "tmp" / "ponytail-skills-pack-s7"
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=parent) as raw:
        missing = Path(raw) / "missing"
        write_skill_tree(missing, 10)
        missing_ok, missing_detail = s7_on(module, missing)
        short = Path(raw) / "short"
        write_skill_tree(short, 9)
        short_ok, short_detail = s7_on(module, short)
    passed = missing_ok and "missing ponytail" in missing_detail and not short_ok
    return passed, {
        "missing_ok": missing_ok,
        "missing_detail": missing_detail,
        "short_ok": short_ok,
        "short_detail": short_detail,
    }


def register_refusal_checks(text: str) -> int | None:
    """How many refusal checks sit in front of register_skill in register()."""
    start = text.find("def register(")
    if start < 0:
        return None
    nxt = text.find("\ndef ", start + 1)
    body = text[start:] if nxt < 0 else text[start:nxt]
    loop = body.find("for child")
    call = body.find("register_skill", loop if loop >= 0 else 0)
    if loop < 0 or call < 0:
        return None
    checks = 0
    for line in body[loop:call].splitlines():
        stripped = line.strip()
        if not stripped.startswith("if "):
            continue
        if "exists" in stripped or "is_dir" in stripped:
            continue
        checks += 1
    return checks


def structural_named(names: list[str]) -> list[str]:
    text = STRUCTURAL.read_text(encoding="utf-8")
    return [
        name
        for name in names
        if "skills-external/ponytail/%s/SKILL.md" % name in text
    ]


def tree_bytes(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        total += path.stat().st_size
    return total


def full_probe() -> int:
    started = time.perf_counter()
    pin, names = pack_record()
    src = cache_src()
    if not (src / ".git").is_dir():
        print("SKIPPED: pin checkout missing at %s" % src, file=sys.stderr)
        return 2
    code, head, _ = run_cmd(["git", "-C", str(src), "rev-parse", "HEAD"])
    head = head.strip()
    if code != 0 or head != pin:
        print("SKIPPED: cache HEAD %s != pin %s" % (head, pin), file=sys.stderr)
        return 2
    _, date_line, _ = run_cmd(["git", "-C", str(src), "log", "-1", "--format=%cI"])
    pin_skills = src / "skills"
    vendor_map = file_map(VENDOR)
    pin_map = file_map(pin_skills)
    only_pin = sorted(set(pin_map) - set(vendor_map))
    only_vendor = sorted(set(vendor_map) - set(pin_map))
    differ = sorted(rel for rel in set(pin_map) & set(vendor_map) if pin_map[rel] != vendor_map[rel])
    safety = skill_safety(pin_skills, names)
    smoke_code, smoke_out, smoke_s = run_cmd([sys.executable, str(VERIFY)])
    asserted = asserted_names(smoke_out, set(names))
    module = load_eic()
    live_ok, live_detail = module.gate_paths_pack()
    fixture_ok, fixture = s7_fixture(module)
    init_py = src / "__init__.py"
    refusal = register_refusal_checks(init_py.read_text(encoding="utf-8")) if init_py.is_file() else None
    package = json.loads((src / "package.json").read_text(encoding="utf-8"))
    payload = {
        "pin": pin,
        "pin_date": date_line.strip(),
        "package_version": package.get("version"),
        "license": "MIT",
        "cache_bytes_no_git": tree_bytes(src),
        "skills_bytes": tree_bytes(pin_skills),
        "skill_count": len(names),
        "byte_identical": len(set(pin_map) & set(vendor_map)) - len(differ),
        "byte_differ": differ,
        "only_pin": only_pin,
        "only_vendor": only_vendor,
        "sha256": {rel: pin_map[rel] for rel in sorted(pin_map)},
        "safety": safety,
        "smoke": {
            "exit": smoke_code,
            "seconds": round(smoke_s, 4),
            "asserted": asserted,
            "asserted_count": len(asserted),
            "pack_count": len(names),
        },
        "structural_named": structural_named(names),
        "s7": {
            "live_ok": bool(live_ok),
            "live_detail": live_detail,
            "fixture_ok": fixture_ok,
            **fixture,
        },
        "register_refusal_checks": refusal,
        "seconds": round(time.perf_counter() - started, 4),
    }
    out = PROBE_DIR / "results.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        "asserted=%d/%d identical=%d differ=%d gates=%d phrases=%d "
        "s7_missing_passes=%d smoke_exit=%d seconds=%s"
        % (
            len(asserted),
            len(names),
            payload["byte_identical"],
            len(differ),
            safety["shell_fences_that_gate"],
            safety["phrase_hits"],
            1 if fixture["missing_ok"] and "missing ponytail" in fixture["missing_detail"] else 0,
            smoke_code,
            payload["seconds"],
        )
    )
    print("wrote %s" % out)
    if smoke_code != 0 or not fixture_ok or differ or only_pin or only_vendor:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count-verify", default="", help="Run this stub and print asserted=N")
    parser.add_argument("--s7-fixture", action="store_true", help="Temp-dir check of the paths-pack count")
    args = parser.parse_args(argv)
    _pin, names = pack_record()
    if args.count_verify:
        code, output, _elapsed = run_cmd([args.count_verify])
        found = asserted_names(output, set(names))
        print("asserted=%d" % len(found))
        print("verify_exit=%d" % code)
        return 0 if code == 0 else code
    if args.s7_fixture:
        _ok, fixture = s7_fixture(load_eic())
        missing_passes = fixture["missing_ok"] and "missing ponytail" in fixture["missing_detail"]
        short_fails = not fixture["short_ok"]
        print("s7_missing_passes=%d" % (1 if missing_passes else 0))
        print("s7_short_claude_fails=%d" % (1 if short_fails else 0))
        return 0 if missing_passes and short_fails else 1
    return full_probe()


if __name__ == "__main__":
    sys.exit(main())
