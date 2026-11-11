#!/usr/bin/env python3
"""GAP-33: print GitHub issue open/closed summary vs docs/TODO map (helper, not full rewrite)."""
from __future__ import annotations
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def gh_issues():
    try:
        p = subprocess.run(
            ["gh", "issue", "list", "--repo", "themark-net/pfy-deanery", "--state", "all", "--limit", "100",
             "--json", "number,title,state"],
            capture_output=True, text=True, timeout=60,
        )
        if p.returncode != 0:
            return []
        return json.loads(p.stdout)
    except Exception:
        return []

def main() -> int:
    issues = {i["number"]: i for i in gh_issues()}
    todo = (ROOT / "docs/TODO.md").read_text(encoding="utf-8", errors="replace")
    nums = sorted(set(int(n) for n in re.findall(r"github\.com/themark-net/pfy-(?:deanery|mentat)/issues/(\d+)", todo)))
    lines = ["# TODO ↔ GitHub sync helper", "", f"links_in_TODO: {len(nums)}", ""]
    closed_still_active = []
    for n in nums:
        st = issues.get(n, {}).get("state", "?")
        title = issues.get(n, {}).get("title", "")
        lines.append(f"- #{n} {st}: {title[:80]}")
        if st == "CLOSED" and re.search(rf"#{n}[^\n]*\|[^\n]*todo", todo, re.I):
            closed_still_active.append(n)
    out = ROOT / "pipelines" / "catalog" / "todo-github-sync.latest.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    if closed_still_active:
        print("HINT closed issues still look active in TODO map:", closed_still_active)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
