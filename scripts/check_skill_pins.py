#!/usr/bin/env python3
"""Blocking guard for vendored external skill packs.

Vendored third-party SKILL.md files are loaded by Grok as instructions, so a
poisoned upstream update would become an instruction to every session. Each
pack and each skill dir under bootstrap/grok-cli/skills-external is pinned by
content hash in PINS.json, together with the SkillSpector recommendation a
person accepted at that hash.

  python3 scripts/check_skill_pins.py            # verify hashes (fast, no binary)
  python3 scripts/check_skill_pins.py --scan     # verify + SkillSpector static scan,
                                                 # each skill no worse than accepted
  python3 scripts/check_skill_pins.py --write --receipt R.json --reviewed "who, when"
                                                 # re-pin after a full-gate review

Exit 0 ok, 1 drift or a scan worse than accepted, 2 scanner missing or unreadable.
A re-pin is a release-class change: it needs Tester and Reviewer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "bootstrap" / "grok-cli" / "skills-external"
PINS = EXT / "PINS.json"
RANK = {"SAFE": 0, "CAUTION": 1}


def tree_sha256(path: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(path.rglob("*")):
        if p.name == "PINS.json" and p.parent == EXT:
            continue
        if "__pycache__" in p.parts:
            continue
        rel = p.relative_to(path).as_posix()
        if p.is_symlink():
            h.update(b"L" + rel.encode() + b"\0" + os.readlink(p).encode() + b"\0")
        elif p.is_file():
            h.update(b"F" + rel.encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def current(ext: Path = EXT) -> tuple[dict, dict]:
    packs = {d.name: tree_sha256(d) for d in sorted(ext.iterdir()) if d.is_dir()}
    skills = {s.parent.relative_to(ext).as_posix(): tree_sha256(s.parent) for s in sorted(ext.rglob("SKILL.md"))}
    return packs, skills


def verify(pins: dict, ext: Path = EXT) -> list[str]:
    packs, skills = current(ext)
    errs = []
    pinned_packs = pins.get("packs", {})
    pinned_skills = pins.get("skills", {})
    for name, sha in packs.items():
        if name not in pinned_packs:
            errs.append(f"unpinned pack: {name}")
        elif pinned_packs[name] != sha:
            errs.append(f"pack changed: {name} (pinned {pinned_packs[name][:12]}, now {sha[:12]})")
    for name in pinned_packs:
        if name not in packs:
            errs.append(f"pinned pack missing: {name}")
    for rel, sha in skills.items():
        if rel not in pinned_skills:
            errs.append(f"unpinned skill: {rel}")
        elif pinned_skills[rel].get("tree_sha256") != sha:
            errs.append(f"skill changed: {rel}")
    for rel in pinned_skills:
        if rel not in skills:
            errs.append(f"pinned skill missing: {rel}")
    return errs


def run_scan(skill_rels: list[str], receipt: Path) -> int:
    dirs = [str((EXT / rel).relative_to(ROOT)) for rel in skill_rels]
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "pfy_skill_scan.py"), *dirs, "--out", str(receipt)],
                       cwd=ROOT, text=True, capture_output=True)
    if r.returncode == 2 or not receipt.is_file():
        sys.stdout.write(r.stdout[-2000:])
        sys.stderr.write(r.stderr[-2000:])
        return 2
    return 0


def compare(pins: dict, receipt: dict) -> list[str]:
    errs = []
    got = {}
    for row in receipt.get("paths", []):
        rel = Path(row.get("path", "")).as_posix()
        prefix = "bootstrap/grok-cli/skills-external/"
        got[rel[len(prefix):] if rel.startswith(prefix) else rel] = str(row.get("recommendation", ""))
    for rel, meta in pins.get("skills", {}).items():
        rec = got.get(rel)
        accepted = meta.get("accepted_scan", "SAFE")
        if rec is None:
            errs.append(f"not scanned: {rel}")
        elif rec not in RANK:
            errs.append(f"scan {rec}: {rel} (blocked; only SAFE or an accepted CAUTION pass)")
        elif RANK[rec] > RANK.get(accepted, 0):
            errs.append(f"scan {rec} is worse than accepted {accepted}: {rel}")
    return errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pin and scan vendored external skills.")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--receipt", default="")
    ap.add_argument("--reviewed", default="")
    args = ap.parse_args(argv)

    if args.write:
        if not args.receipt or not args.reviewed:
            print("--write needs --receipt (a scan receipt for this tree) and --reviewed", file=sys.stderr)
            return 2
        receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        recs = {}
        for row in receipt.get("paths", []):
            rel = Path(row["path"]).as_posix().split("skills-external/", 1)[-1]
            recs[rel] = row.get("recommendation")
        packs, skills = current()
        out = {
            "note": "Vendored external skills, pinned by content hash. Changing a pack or this file is a "
                    "release-class change (Tester + Reviewer). See scripts/check_skill_pins.py.",
            "reviewed": args.reviewed,
            "skillspector": "e7172462caf367736645f66c1aa154ca5f9c64dc",
            "packs": packs,
            "skills": {rel: {"tree_sha256": sha, "accepted_scan": recs.get(rel, "UNSCANNED")}
                       for rel, sha in skills.items()},
        }
        PINS.write_text(json.dumps(out, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        print(f"wrote {PINS.relative_to(ROOT)}")
        return 0

    if not PINS.is_file():
        print(f"missing {PINS.relative_to(ROOT)}", file=sys.stderr)
        return 1
    pins = json.loads(PINS.read_text(encoding="utf-8"))
    errs = verify(pins)
    for e in errs:
        print(e)
    if errs:
        print("skills-external drift: a vendored skill changed without a reviewed re-pin. Blocked.")
        return 1
    if not args.scan:
        print(f"skill pins ok ({len(pins.get('skills', {}))} skills)")
        return 0
    with tempfile.TemporaryDirectory(prefix="skill-pins-") as tmp:
        receipt_path = Path(args.receipt) if args.receipt else Path(tmp) / "scan.json"
        rc = run_scan(sorted(pins.get("skills", {})), receipt_path)
        if rc == 2:
            print("Next: install the pinned SkillSpector (docs/ops/skill-scan.md) and set PFY_SKILLSPECTOR_BIN.")
            return 2
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    errs = compare(pins, receipt)
    for e in errs:
        print(e)
    if errs:
        return 1
    print(f"skill pins + scan ok ({len(pins.get('skills', {}))} skills)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
