#!/usr/bin/env python3
"""Operate-or-FAIL check for the Ix Stage-0 receipt. Cite #198.

Does not install Ix, pull container images, or download weights.
Exit 1 if the receipt is missing, if it claims Stage-0 PASS without
license / quickstart / hello-world evidence (or while upstream timing
quotes still contradict a fresh under-5-minute setup), or if product
files attach Ix.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "sources" / "entries" / "084-ix.md"
ISSUE = "https://github.com/themark-net/pfy-deanery/issues/198"
UPSTREAM = "https://github.com/ix-infrastructure/Ix"

NEEDLES = (
    "ix-infrastructure",
    "ix-infra.com",
    "ix-memory-layer",
    "ghcr.io/ix-infrastructure",
)

PRODUCT_FILES = (
    "TOOLS.md",
    "data/tools.json",
    "data/toolsets.json",
    "pfy",
    "Makefile",
    "bootstrap/env/REGISTRY.md",
    "bootstrap/env/env.example",
)
PRODUCT_DIRS = ("pfylib", "gui", "tools", "harness")

# Phrases copied from the upstream installer / prerequisites. A Stage-0 PASS
# that still contains them has not shown a fresh setup under 5 minutes.
TIMING_QUOTES = (
    "may take a few minutes",
    "~700MB",
    "waits up to 5 minutes",
)


def bullet(text: str, label: str) -> str:
    needle = f"**{label}:**"
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if needle in line:
            start = i
            break
    if start is None:
        return ""
    out = [lines[start]]
    for line in lines[start + 1 :]:
        stripped = line.lstrip()
        if stripped.startswith("- **") or line.startswith("### "):
            break
        out.append(line)
    return "\n".join(out)


def status_line(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("- **Status**"):
            return line
    return ""


def claims_stage0_pass(text: str) -> bool:
    blob = (bullet(text, "Fail closed") + "\n" + status_line(text)).lower()
    if "stage-0 pass" in blob or "stage-0 passes" in blob:
        return True
    if "stage 0 gate **pass**" in blob:
        return True
    status = status_line(text)
    return "PASS" in status and "FAIL" not in status


def product_hits() -> list[str]:
    files = [ROOT / rel for rel in PRODUCT_FILES]
    stages = ROOT / "data" / "stages"
    if stages.is_dir():
        files.extend(p for p in stages.glob("*.json") if p.is_file())
    for rel in PRODUCT_DIRS:
        base = ROOT / rel
        if base.is_dir():
            files.extend(p for p in base.rglob("*") if p.is_file())
    scripts = ROOT / "scripts"
    checker = Path(__file__).resolve()
    if scripts.is_dir():
        files.extend(
            p
            for p in scripts.rglob("*")
            if p.is_file() and p.resolve() != checker
        )
    hits: list[str] = []
    seen: set[Path] = set()
    for path in files:
        if not path.is_file():
            continue
        resolved = path.resolve()
        if resolved in seen or resolved == checker:
            continue
        seen.add(resolved)
        try:
            data = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for needle in NEEDLES:
            if needle in data:
                hits.append(f"{path.relative_to(ROOT)} contains {needle}")
                break
    return hits


def check_receipt(problems: list[str]) -> None:
    if not RECEIPT.is_file():
        problems.append(f"missing receipt {RECEIPT.relative_to(ROOT)}")
        return
    entries = sorted((ROOT / "sources" / "entries").glob("084-*"))
    names = [p.name for p in entries]
    if names != [RECEIPT.name]:
        problems.append(
            "entry id 084 must be only sources/entries/084-ix.md, found "
            + (", ".join(names) or "(none)")
        )
    text = RECEIPT.read_text(encoding="utf-8")
    if not text.startswith("### Entry 084:"):
        problems.append("receipt must start with '### Entry 084:'")
    if ISSUE not in text:
        problems.append(f"receipt does not cite {ISSUE}")
    if UPSTREAM not in text:
        problems.append(f"receipt does not cite {UPSTREAM}")

    license_b = bullet(text, "License")
    quick_b = bullet(text, "Self-host / quickstart")
    hello_b = bullet(text, "Hello-world")
    if "Apache" not in license_b or "LICENSE" not in license_b:
        problems.append("license evidence missing (Apache + LICENSE)")
    if "install.sh" not in quick_b:
        problems.append("quickstart evidence missing (install.sh)")
    if "ix map" not in hello_b:
        problems.append("hello-world evidence missing (ix map)")
    if "arangodb" in text.lower() and "Business Source License" not in text:
        problems.append("arangodb cited without Business Source License")

    if claims_stage0_pass(text):
        if "Apache" not in license_b or "LICENSE" not in license_b:
            problems.append("Stage-0 PASS without license evidence")
        if "install.sh" not in quick_b:
            problems.append("Stage-0 PASS without quickstart evidence")
        if "ix map" not in hello_b:
            problems.append("Stage-0 PASS without hello-world evidence")
        if "under 5" not in quick_b and "<5" not in quick_b:
            problems.append("Stage-0 PASS without an under-5-minute quickstart claim")
        quoted = [q for q in TIMING_QUOTES if q in quick_b]
        if quoted:
            problems.append(
                "Stage-0 PASS contradicts upstream timing quotes: " + ", ".join(quoted)
            )
        return

    status = status_line(text)
    if "FAIL" not in status or "I0" not in status:
        problems.append("FAIL receipt must say FAIL and I0 on the Status line")
    missing = [q for q in TIMING_QUOTES if q not in quick_b]
    if missing:
        problems.append(
            "quickstart evidence must keep the upstream timing quotes: "
            + ", ".join(missing)
        )


def main() -> int:
    problems: list[str] = []
    check_receipt(problems)
    problems.extend(product_hits())
    if problems:
        for item in problems:
            print(f"FAIL {item}")
        return 1
    print("ok receipt sources/entries/084-ix.md")
    print("ok stage-0 evidence (license, quickstart, hello-world) matches verdict")
    print("ok product files do not attach Ix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
