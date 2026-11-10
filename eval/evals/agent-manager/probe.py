#!/usr/bin/env python3
"""Score the agent-manager pin from a local tree.

Does not build, install, or launch the tool. Does not attach to a live
tmux socket and does not write a grok config.

Exit 0: all eight source features are in the tree and LICENSE is Apache-2.0.
Exit 1: the tree is readable and at least one of those checks failed.
Exit 2: the tree path is missing or not a directory.

A pass means the pinned source matches the entry claims. It does not mean
the binary ran.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PIN = "cbe5fb9bd248636ebeb5ac6f97ab83940d04fb2d"
THRESHOLD = 8

# Eight claims from the catalog entry, checked as source text at the pin.
FEATURES = (
    {
        "id": "private_tmux_socket",
        "path": "internal/tmux/tmux.go",
        "needles": ('const defaultSocket = "agentmgr"',),
    },
    {
        "id": "grok_no_leader",
        "path": "internal/launch/launch.go",
        "needles": ('if toolName == "grok"', 'baseCommand += " --no-leader"'),
    },
    {
        "id": "grok_status_rules",
        "path": "internal/config/builtin.go",
        "needles": (
            "[tools.grok]",
            'resume_by_id_command = "grok --resume {id}"',
            'Grok prints a live "Worked for 1m20s"',
        ),
    },
    {
        "id": "grok_fork_command",
        "path": "internal/config/builtin.go",
        "needles": (
            'fork_command = "grok --resume {id} --fork-session --session-id {new_id}"',
        ),
    },
    {
        "id": "cli_spawn_and_send",
        "path": "internal/cli/session.go",
        "needles": (
            "spawn [--name <name>] [--prompt <text>] [--saved <name>]",
            'send <session-id> ["<message>"] [--saved <name>] [--from <name>] [--json]',
        ),
    },
    {
        "id": "mcp_create_session",
        "path": "internal/mcpserver/mcpserver.go",
        "needles": ('Name: "create_session"',),
    },
    {
        "id": "diff_review_cli",
        "path": "internal/cli/review.go",
        "needles": ('"review-repo <path>"',),
    },
    {
        "id": "script_outside_tui",
        "path": "internal/cli/cli.go",
        "needles": ("also run from a script outside Agent Manager",),
    },
)


def _read(root: Path, rel: str) -> str | None:
    path = root / rel
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git_head(root: Path) -> str | None:
    head = root / ".git" / "HEAD"
    if not head.is_file():
        return None
    raw = head.read_text(encoding="utf-8", errors="replace").strip()
    if raw.startswith("ref:"):
        ref = root / ".git" / raw.split(" ", 1)[1].strip()
        if not ref.is_file():
            return None
        raw = ref.read_text(encoding="utf-8", errors="replace").strip()
    if len(raw) < 7 or any(ch not in "0123456789abcdef" for ch in raw.lower()):
        return None
    return raw.lower()


def _cost_tracking_go(root: Path) -> list[str]:
    hits = []
    base = root / "internal"
    if not base.is_dir():
        return hits
    for path in base.rglob("*.go"):
        if "cost tracking" in path.read_text(encoding="utf-8", errors="replace").lower():
            hits.append(str(path.relative_to(root)))
    return hits


def score(root: Path) -> dict:
    rows = []
    confirmed = 0
    for feature in FEATURES:
        text = _read(root, feature["path"])
        missing = []
        if text is None:
            missing = list(feature["needles"])
            digest = None
        else:
            digest = _sha(text)
            missing = [needle for needle in feature["needles"] if needle not in text]
        ok = not missing
        if ok:
            confirmed += 1
        rows.append(
            {
                "id": feature["id"],
                "path": feature["path"],
                "ok": ok,
                "missing": missing,
                "sha256": digest,
            }
        )
    license_text = _read(root, "LICENSE")
    license_ok = bool(
        license_text
        and "Apache License" in license_text
        and "Version 2.0" in license_text
    )
    readme = _read(root, "README.md") or ""
    theme = _read(root, "internal/launch/grok_theme.go") or ""
    headless = _read(root, "examples/headless/main.go") or ""
    gomod = _read(root, "go.mod") or ""
    go_line = ""
    for line in gomod.splitlines():
        if line.startswith("go "):
            go_line = line.strip()
            break
    head = _git_head(root)
    pin_match = None if head is None else head == PIN
    cost_hits = _cost_tracking_go(root)
    return {
        "pin": PIN,
        "git_head": head,
        "pin_match": pin_match,
        "metric": "source_features_at_pin",
        "threshold": THRESHOLD,
        "source_features_confirmed": confirmed,
        "features": rows,
        "license_apache_2": license_ok,
        "cost_tracking_readme_claim": "Not here yet: cost tracking." in readme,
        "cost_tracking_go_files": cost_hits,
        "grok_config_write_on_launch": "func ensureGrokTerminalTheme()" in theme,
        "headless_observe_example": "--profile and --socket are required" in headless,
        "go_mod_line": go_line,
        "runs": 0,
        "built": False,
        "installed": False,
    }


def passed(result: dict) -> bool:
    pin_ok = result["pin_match"] is not False
    return (
        result["source_features_confirmed"] >= result["threshold"]
        and result["license_apache_2"]
        and pin_ok
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score an agent-manager source tree.")
    parser.add_argument("--source", required=True, help="Pinned checkout. Not copied into the repo.")
    parser.add_argument("--out", default="", help="Write results JSON here. Default: beside this probe.")
    args = parser.parse_args(argv)
    root = Path(args.source)
    out = Path(args.out) if args.out else Path(__file__).resolve().parent / "results.json"
    if not root.is_dir():
        print(f"missing source tree: {root}", file=sys.stderr)
        return 2
    result = score(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"{result['source_features_confirmed']}/{result['threshold']} "
        f"license={result['license_apache_2']} pin_match={result['pin_match']}"
    )
    return 0 if passed(result) else 1


if __name__ == "__main__":
    raise SystemExit(main())
