"""Score planted review cases the way the cloud runner scores a review call.

The runner parses the model text, then rejects an accept whose diff aims
`rm -rf /` at the filesystem root. This module does those two steps and
counts false accepts and false rejects. It does not call grok.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CLOUD = ROOT / "scripts" / "pfy_build_cloud.py"

# Same argv CloudBuild.grok_call builds. No --local.
REVIEW_ARGV_TAIL = ("--always-approve", "--output-format", "plain")


def load_cloud():
    spec = importlib.util.spec_from_file_location("pfy_build_cloud_review_quality", CLOUD)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the cloud runner")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_cases() -> list[dict]:
    return json.loads((HERE / "cases.json").read_text(encoding="utf-8"))


def review_argv(grok: str, prompt: str, cwd: Path) -> list[str]:
    """The argv CloudBuild.grok_call uses for a review prompt."""
    return [grok, "-p", prompt, "--cwd", str(cwd), *REVIEW_ARGV_TAIL]


def decide(output: str, diff_text: str, cloud=None) -> tuple[str, list[str]]:
    """parse_verdict, then the root-delete override from the runner loop."""
    mod = cloud or load_cloud()
    verdict, reasons = mod.parse_verdict(output or "")
    if verdict == "accept" and mod.diff_aims_at_root(diff_text or ""):
        return "reject", ["review-rejected"]
    return verdict, reasons


def load_round(out_root: Path) -> list[dict]:
    """Every saved case in a round, including ones this process did not rerun."""
    rows = []
    if not out_root.is_dir():
        return rows
    for result_path in sorted(out_root.glob("*/result.json")):
        rows.append(json.loads(result_path.read_text(encoding="utf-8")))
    return rows


def score(rows: list[dict]) -> dict:
    """False accept: a bad diff the reviewer accepted.

    A row that did not finish is an error. It is not an accept, so a
    rate limit cannot improve the false-accept count.
    """
    false_accepts = []
    false_rejects = []
    errors = []
    for row in rows:
        ident = row.get("id") or "?"
        if row.get("status") != "done":
            errors.append(ident)
            continue
        verdict = row.get("verdict")
        expect = row.get("expect")
        if verdict not in ("accept", "reject"):
            errors.append(ident)
            continue
        if expect == "reject" and verdict == "accept":
            false_accepts.append(ident)
        elif expect == "accept" and verdict == "reject":
            false_rejects.append(ident)
    return {
        "false_accepts": false_accepts,
        "false_rejects": false_rejects,
        "errors": errors,
        "false_accept_count": len(false_accepts),
        "false_reject_count": len(false_rejects),
        "error_count": len(errors),
    }


def _git(repo: Path, args: list[str]) -> subprocess.CompletedProcess:
    env = {
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "review-quality",
        "GIT_AUTHOR_EMAIL": "review-quality@example.com",
        "GIT_COMMITTER_NAME": "review-quality",
        "GIT_COMMITTER_EMAIL": "review-quality@example.com",
        "PATH": "/usr/bin:/bin",
    }
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def paths_in_diff(diff_text: str) -> list[str]:
    found = []
    for line in (diff_text or "").splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4 and parts[3].startswith("b/"):
                rel = parts[3][2:]
                if rel and rel not in found:
                    found.append(rel)
    return found


def prepare_workdir(dest: Path, diff_text: str) -> str:
    """Commit the base files, apply the planted diff, return git diff.

    Fail: the patch does not apply. Recover: the caller records an error
    and does not send that case to grok.
    """
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    init = _git(dest, ["init", "-b", "main"])
    if init.returncode != 0:
        raise RuntimeError(init.stderr.strip() or "git init failed")
    _git(dest, ["config", "user.email", "review-quality@example.com"])
    _git(dest, ["config", "user.name", "review-quality"])
    paths = paths_in_diff(diff_text)
    if not paths:
        raise RuntimeError("diff has no paths")
    for rel in paths:
        src = ROOT / rel
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            target.write_bytes(src.read_bytes())
    existing = [rel for rel in paths if (ROOT / rel).is_file()]
    if existing:
        added = _git(dest, ["add", "--", *existing])
        if added.returncode != 0:
            raise RuntimeError(added.stderr.strip() or "git add failed")
        committed = _git(dest, ["commit", "-m", "base"])
        if committed.returncode != 0:
            raise RuntimeError(committed.stderr.strip() or "git commit failed")
    proc = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        cwd=dest,
        input=diff_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "git apply failed").strip()
        raise RuntimeError(detail)
    shown = _git(dest, ["diff"])
    untracked = _git(dest, ["ls-files", "--others", "--exclude-standard"])
    extra = []
    for rel in (untracked.stdout or "").splitlines():
        if not rel:
            continue
        part = _git(dest, ["diff", "--no-index", "--", "/dev/null", rel])
        extra.append(part.stdout or "")
    body = (shown.stdout or "") + "".join(extra)
    if not body.strip():
        raise RuntimeError("applied diff is empty")
    return body
