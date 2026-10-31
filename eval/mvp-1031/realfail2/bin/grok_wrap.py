#!/usr/bin/env python3
"""Log a real grok call, then optionally plant a fixture inside the worktree.

The plant runs only after grok returns, and only when the worktree path is
inside PFY_REALFAIL2_CLONE. This process never executes danger.sh.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

MARKER_IMPLEMENT = "PFY-CLOUD-IMPLEMENT"
MARKER_REVIEW = "PFY-CLOUD-REVIEW"
DANGER_LINE = "rm -rf /\n"


def _prompt(argv: list[str]) -> str:
    if "-p" in argv:
        index = argv.index("-p")
        if index + 1 < len(argv):
            return argv[index + 1]
    return ""


def _cwd(argv: list[str]) -> Path | None:
    if "--cwd" not in argv:
        return None
    index = argv.index("--cwd")
    if index + 1 >= len(argv):
        return None
    return Path(argv[index + 1]).resolve()


def _allowed(cwd: Path | None) -> bool:
    root = os.environ.get("PFY_REALFAIL2_CLONE", "").strip()
    if cwd is None or not root:
        return False
    try:
        cwd.relative_to(Path(root).resolve())
    except ValueError:
        return False
    return "cloud-build" in cwd.parts


def _log(line: str) -> None:
    path = os.environ.get("PFY_REALFAIL2_LOG", "").strip()
    if not path:
        return
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def _plant(kind: str, cwd: Path, prompt: str) -> None:
    if kind == "outsider":
        kept = cwd / "kept.py"
        if not kept.is_file() or kept.read_text(encoding="utf-8").strip() != "value = 1":
            kept.write_text("value = 1\n", encoding="utf-8")
        outsider = cwd / "tmp" / "outsider.txt"
        outsider.parent.mkdir(parents=True, exist_ok=True)
        outsider.write_text("outside\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "-f", "--", "tmp/outsider.txt"],
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
        )
        return
    if kind == "protected":
        (cwd / "auth.json").write_text('{"marker":"not-a-secret"}\n', encoding="utf-8")
        (cwd / ".env").write_text("MARKER=1\n", encoding="utf-8")
        return
    if kind == "danger-first":
        if "previous attempt was rejected" in prompt:
            _log("plant=skip-retry")
            return
        danger = cwd / "danger.sh"
        danger.write_text(DANGER_LINE, encoding="utf-8")
        kept = cwd / "kept.py"
        if kept.exists():
            kept.unlink()
        _log("plant=danger-first")


def main() -> int:
    argv = sys.argv[1:]
    prompt = _prompt(argv)
    kind = "review" if MARKER_REVIEW in prompt else "implement" if MARKER_IMPLEMENT in prompt else "other"
    _log("call kind=%s" % kind)
    if kind == "implement" and "previous attempt was rejected" in prompt:
        has_reason = "review-rejected" in prompt
        _log("retry_has_review_rejected=%s" % ("yes" if has_reason else "no"))
    real = os.environ.get("PFY_REALFAIL2_GROK", "").strip() or "grok"
    proc = subprocess.run([real, *argv], check=False)
    plant = os.environ.get("PFY_REALFAIL2_PLANT", "").strip()
    cwd = _cwd(argv)
    if plant and kind == "implement" and _allowed(cwd) and cwd is not None:
        _plant(plant, cwd, prompt)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
