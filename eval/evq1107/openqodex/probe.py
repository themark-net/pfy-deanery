#!/usr/bin/env python3
"""One OpenQodex probe for the evq1107 lane.

Builds a throwaway git repo under the tool cache, runs review --agent on a
small diff (three planted defects, one untouched defect, one real-file
comment), then finalize. Does not pass --offline, so semgrep can run. No
model, no init, no account. Writes results JSON to stdout. Secrets in
scanner text are redacted before they leave this process.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PKG = (Path.home() / ".cache/pfy/tools/openqodex/prefix/node_modules/openqodex")
BIN = PKG / "dist/bin.js"
NODE = "/usr/bin/node"
REAL_FILE = "scripts/sync_todo_status.py"
ONLY = "semgrep,gitleaks,bandit,ruff"
SECRET_RE = re.compile(
    r"ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}"
)


def redact(text: str) -> str:
    return SECRET_RE.sub("<redacted>", text)


def env_for(cache: Path) -> dict[str, str]:
    home = cache / "home"
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "TMPDIR": str(cache / "tmp"),
        "XDG_CONFIG_HOME": str(cache / "xdg-config"),
        "XDG_CACHE_HOME": str(cache / "xdg-cache"),
        "OPENQODEX_HOME": str(cache / "oqhome"),
        "OPENQODEX_AUTO_UPDATE": "0",
        "NO_COLOR": "1",
        "LANG": "C.UTF-8",
        "TERM": "dumb",
    }


def run(cmd: list[str], *, cwd: Path, env: dict[str, str], timeout: float) -> dict:
    t0 = time.monotonic()
    try:
        p = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return {
            "exit": p.returncode,
            "seconds": round(time.monotonic() - t0, 3),
            "stdout": redact(p.stdout),
            "stderr": redact(p.stderr),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as e:
        out = e.stdout or ""
        err = e.stderr or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        return {
            "exit": None,
            "seconds": round(time.monotonic() - t0, 3),
            "stdout": redact(out),
            "stderr": redact(err) + "\nTIMEOUT",
            "timed_out": True,
        }


def git(repo: Path, env: dict[str, str], *args: str) -> None:
    r = run(
        ["git", "-c", "user.email=probe@local", "-c", "user.name=probe", *args],
        cwd=repo,
        env=env,
        timeout=30,
    )
    if r["exit"] != 0:
        raise SystemExit(f"git {args[0]} failed: {r['stderr'][-400:]}")


def changed_lines(repo: Path, env: dict[str, str], base: str) -> dict[str, set[int]]:
    r = run(["git", "diff", "-U0", base, "HEAD"], cwd=repo, env=env, timeout=30)
    out: dict[str, set[int]] = {}
    path = None
    new_line = 0
    for line in r["stdout"].splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
            out.setdefault(path, set())
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            new_line = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++") and path is not None:
            out.setdefault(path, set()).add(new_line)
            new_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            continue
        elif path is not None and not line.startswith("\\"):
            new_line += 1
    return out


def line_of(text: str, needle: str) -> int:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    raise SystemExit(f"needle not in file: {needle[:40]}")


def build_repo(repo: Path, env: dict[str, str], worktree: Path, token: str) -> dict:
    if repo.exists():
        shutil.rmtree(repo)
    repo.mkdir(parents=True)
    (repo / "handlers").mkdir()
    (repo / "scripts").mkdir()
    legacy = "import subprocess\n\ndef old_lane(cmd):\n    return subprocess.call(cmd, shell=True)\n"
    runner_base = "import subprocess\n\ndef run_lane(cmd):\n    return subprocess.call(cmd)\n"
    session_base = "def remember(session_token):\n    return len(session_token)\n"
    token_base = "def load():\n    return ''\n"
    (repo / "handlers/legacy.py").write_text(legacy)
    (repo / "handlers/runner.py").write_text(runner_base)
    (repo / "handlers/session.py").write_text(session_base)
    (repo / "handlers/tokenstore.py").write_text(token_base)
    real = (worktree / REAL_FILE).read_text(encoding="utf-8")
    (repo / REAL_FILE).write_text(real)
    git(repo, env, "init", "-q", "-b", "main")
    git(repo, env, "add", ".")
    git(repo, env, "commit", "-qm", "base")
    base = run(["git", "rev-parse", "HEAD"], cwd=repo, env=env, timeout=15)["stdout"].strip()
    runner = "import subprocess\n\ndef run_lane(cmd):\n    return subprocess.call(cmd, shell=True)\n"
    session = (
        "def remember(session_token):\n"
        "    print('session token is ' + session_token)\n"
        "    return len(session_token)\n"
    )
    token_src = f"def load():\n    return '{token}'\n"
    (repo / "handlers/runner.py").write_text(runner)
    (repo / "handlers/session.py").write_text(session)
    (repo / "handlers/tokenstore.py").write_text(token_src)
    comment = real.replace(
        "GAP-33: print GitHub issue open/closed summary",
        "GAP-33: print GitHub issue open/closed summary (comment only)",
        1,
    )
    if comment == real:
        raise SystemExit("real file comment anchor missing")
    (repo / REAL_FILE).write_text(comment)
    git(repo, env, "add", ".")
    git(repo, env, "commit", "-qm", "change")
    plants = {
        "shell_changed": {"file": "handlers/runner.py", "line": line_of(runner, "shell=True")},
        "log_changed": {"file": "handlers/session.py", "line": line_of(session, "session token is")},
        "secret_changed": {"file": "handlers/tokenstore.py", "line": line_of(token_src, "return '")},
        "shell_unchanged": {"file": "handlers/legacy.py", "line": line_of(legacy, "shell=True")},
        "comment_file": REAL_FILE,
    }
    return {"base": base, "plants": plants, "changed": changed_lines(repo, env, base)}


def oq(env: dict[str, str], repo: Path, args: list[str], timeout: float) -> dict:
    return run([NODE, str(BIN), *args], cwd=repo, env=env, timeout=timeout)


def newest_review(repo: Path) -> Path | None:
    files = list(repo.glob(".openqodex/reviews/**/candidates.json"))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime_ns).parent


def find_candidates(repo: Path) -> tuple[list[dict], str, Path | None]:
    directory = newest_review(repo)
    if directory is None:
        return [], "", None
    path = directory / "candidates.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("candidates", [])
    brief = directory / "brief.md"
    text = brief.read_text(encoding="utf-8") if brief.is_file() else ""
    return data, text, directory


def slim_candidate(c: dict) -> dict:
    msg = redact(str(c.get("message") or c.get("text") or ""))
    return {
        "id": c.get("id"),
        "token": c.get("token") or c.get("source"),
        "file": c.get("filePath") or c.get("file_path"),
        "line": c.get("lineStart") or c.get("line_start"),
        "line_end": c.get("lineEnd") or c.get("line_end"),
        "severity": c.get("reviewSeverity") or c.get("severity"),
        "message": msg[:180],
    }


def hit(cands: list[dict], file: str, line: int) -> list[dict]:
    found = []
    for c in cands:
        if c.get("file") != file:
            continue
        start = int(c.get("line") or 0)
        end = int(c.get("line_end") or start)
        if start <= line <= end:
            found.append(c)
    return found


def finding_for(c: dict, title: str) -> dict:
    return {
        "severity": "major",
        "category": "security",
        "confidence": 0.9,
        "file_path": c["file"],
        "line_number": c["line"],
        "line_end": c["line"],
        "title": title,
        "description": "Planted on a changed line. The scanner token matches this candidate.",
        "suggested_change": None,
        "source": c["token"],
        "candidate": c["id"],
    }


def packet(change_id: str, findings: list[dict], dropped: list[dict], summary: str) -> dict:
    return {
        "version": 1,
        "change_id": change_id,
        "summary": summary,
        "reviewer": "subagent",
        "findings": findings,
        "dropped": dropped,
    }


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:240]
    return ""


def change_id_from(brief: str) -> str:
    m = re.search(r"^- Change: ([0-9a-f]{12})\b", brief, re.M)
    if not m:
        raise SystemExit("brief has no change id")
    return m.group(1)


def dir_mtime(path: Path) -> int | None:
    try:
        return path.lstat().st_mtime_ns
    except OSError:
        return None


def tool_versions(cache: Path) -> dict:
    root = cache / "oqhome" / "tools"
    out: dict = {"tools_dir_bytes": 0}
    if root.is_dir():
        out["tools_dir_bytes"] = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
    # Record version strings only. Do not copy binary hashes of huge trees into the report
    # beyond the pinned sha256 already in toolchain.json; confirm the installed version.
    env = env_for(cache)
    for name, flag in (("semgrep", "--version"), ("bandit", "--version"), ("ruff", "--version"), ("gitleaks", "version")):
        bins = list(root.glob(f"{name}/**/bin/{name}")) if root.is_dir() else []
        if not bins:
            out[name] = "not installed"
            continue
        b = bins[-1]
        if name == "gitleaks":
            r = run([str(b), "version"], cwd=cache, env=env, timeout=30)
        else:
            env_bin = dict(env)
            env_bin["PATH"] = str(b.parent) + ":/usr/bin:/bin"
            r = run([str(b), flag], cwd=b.parent, env=env_bin, timeout=60)
        out[name] = first_line(r["stdout"] + "\n" + r["stderr"])[:120]
        if name in ("gitleaks", "ruff"):
            h = hashlib.sha256()
            with b.open("rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            out[name + "_sha256"] = h.hexdigest()
    return out


def main() -> int:
    worktree = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    cache = (Path.home() / ".cache/pfy/tools/openqodex")
    env = env_for(cache)
    for p in (cache / "home", cache / "tmp", cache / "xdg-config", cache / "xdg-cache", cache / "oqhome", cache / "work"):
        p.mkdir(parents=True, exist_ok=True)
    # Mixed hex, not a real credential. A run of one repeated character is low
    # entropy and is a different case; this plant is the one the results score.
    token = "ghp_" + hashlib.sha256(b"openqodex-evq1107-plant").hexdigest()[:36]
    homes = {
        "claude": dir_mtime((Path.home() / ".claude")),
        "codex": dir_mtime((Path.home() / ".codex")),
        "cursor": dir_mtime((Path.home() / ".cursor")),
        "grok": dir_mtime((Path.home() / ".grok")),
        "openqodex": dir_mtime((Path.home() / ".openqodex")),
    }
    repo = cache / "work" / "fixture"
    built = build_repo(repo, env, worktree, token)
    agent = oq(
        env,
        repo,
        ["review", "--agent", "--base", built["base"], "--only", ONLY, "--no-graph", "--cwd", str(repo)],
        900,
    )
    cands_raw, brief, review_dir = find_candidates(repo)
    cands = [slim_candidate(c) for c in cands_raw]
    plants = built["plants"]
    changed = {k: sorted(v) for k, v in built["changed"].items()}
    on_diff = []
    off_diff = []
    for c in cands:
        lines = set(changed.get(c["file"] or "", []))
        start = int(c.get("line") or 0)
        if start in lines:
            on_diff.append(c["id"])
        else:
            off_diff.append(c["id"])
    shell_hits = hit(cands, plants["shell_changed"]["file"], plants["shell_changed"]["line"])
    log_hits = hit(cands, plants["log_changed"]["file"], plants["log_changed"]["line"])
    secret_hits = hit(cands, plants["secret_changed"]["file"], plants["secret_changed"]["line"])
    leak_hits = hit(cands, plants["shell_unchanged"]["file"], plants["shell_unchanged"]["line"])
    comment_hits = [c for c in cands if c.get("file") == plants["comment_file"]]
    planted_hits = sum(1 for group in (shell_hits, log_hits, secret_hits) if group)
    result: dict = {
        "agent": {k: agent[k] for k in ("exit", "seconds", "timed_out")},
        "agent_stdout_head": first_line(agent["stdout"]),
        "agent_stderr_tail": "\n".join(agent["stderr"].splitlines()[-8:]),
        "plants": {
            "shell_changed_line": plants["shell_changed"]["line"],
            "log_changed_line": plants["log_changed"]["line"],
            "secret_changed_line": plants["secret_changed"]["line"],
            "shell_unchanged_line": plants["shell_unchanged"]["line"],
        },
        "changed_lines": changed,
        "candidate_count": len(cands),
        "on_changed_lines": len(on_diff),
        "off_changed_lines": len(off_diff),
        "off_changed_ids": off_diff,
        "shell_hit": bool(shell_hits),
        "log_hit": bool(log_hits),
        "secret_hit": bool(secret_hits),
        "unchanged_shell_leak": bool(leak_hits),
        "comment_file_candidates": len(comment_hits),
        "planted_hits": planted_hits,
        "planted_total": 3,
        "candidates": cands,
    }
    if agent["timed_out"] or not brief:
        result["finalize"] = "SKIPPED"
        result["reason"] = "no brief" if not brief else "agent timed out"
    else:
        cid = change_id_from(brief)
        result["change_id"] = cid
        result["block_line"] = next((ln.strip() for ln in brief.splitlines() if ln.startswith("- Block threshold:")), "")
        result["scanner_line"] = next((ln.strip() for ln in brief.splitlines() if ln.startswith("- Scanners:")), "")
        # Raise the shell candidate when present, else the first candidate, else an empty review.
        raised_src = shell_hits[0] if shell_hits else (cands[0] if cands else None)
        findings = [finding_for(raised_src, "Shell call on a changed line")] if raised_src else []
        raised_id = raised_src["id"] if raised_src else None
        dropped = [
            {"candidate": c["id"], "reason": "not the planted shell call"}
            for c in cands
            if c["id"] != raised_id and c.get("id")
        ]
        good = packet(cid, findings, dropped, "Raises the planted shell call and drops the other candidates.")
        none = packet(cid, [], [], "Answers nothing. Every candidate is left unchecked.")
        made = packet(
            cid,
            [{**findings[0], "source": "made-up"}] if findings else [
                {
                    "severity": "major",
                    "category": "security",
                    "confidence": 0.9,
                    "file_path": "handlers/runner.py",
                    "line_number": plants["shell_changed"]["line"],
                    "line_end": plants["shell_changed"]["line"],
                    "title": "Shell call on a changed line",
                    "description": "Cites a source that is not in this scan.",
                    "suggested_change": None,
                    "source": "made-up",
                }
            ],
            [],
            "One finding cites a source that is not in this scan.",
        )
        if review_dir is None:
            raise SystemExit("brief without a review dir")
        paths = {}
        for name, body in (("good", good), ("none", none), ("madeup", made)):
            path = review_dir / f"{name}-findings.json"
            path.write_text(json.dumps(body))
            paths[name] = path
        fin: dict = {}
        for name in ("good", "none", "madeup"):
            r = oq(env, repo, ["review", "--finalize", "--cwd", str(repo), str(paths[name])], 120)
            fin[name] = {
                "exit": r["exit"],
                "seconds": r["seconds"],
                "first": first_line(r["stdout"]),
                "err": first_line(r["stderr"]),
            }
        result["finalize_default"] = fin
        # Second brief with a block threshold. Config is outside the repo.
        block_cfg = cache / "work" / "block.yaml"
        block_cfg.write_text("version: 1\nreview:\n  block_on_severity: major\n")
        agent_b = oq(
            env,
            repo,
            [
                "review", "--agent", "--base", built["base"], "--only", ONLY, "--no-graph",
                "--config", str(block_cfg), "--cwd", str(repo),
            ],
            900,
        )
        cands_b_raw, brief_b, review_dir_b = find_candidates(repo)
        result["agent_block"] = {
            "exit": agent_b["exit"],
            "seconds": agent_b["seconds"],
            "timed_out": agent_b["timed_out"],
            "block_line": next((ln.strip() for ln in brief_b.splitlines() if ln.startswith("- Block threshold:")), ""),
            "stderr_tail": "\n".join(agent_b["stderr"].splitlines()[-6:]),
        }
        if brief_b and not agent_b["timed_out"]:
            cid_b = change_id_from(brief_b)
            cands_b = [slim_candidate(c) for c in cands_b_raw]
            shell_b = hit(cands_b, plants["shell_changed"]["file"], plants["shell_changed"]["line"])
            raised_b = shell_b[0] if shell_b else (cands_b[0] if cands_b else None)
            findings_b = [finding_for(raised_b, "Shell call on a changed line")] if raised_b else []
            dropped_b = [
                {"candidate": c["id"], "reason": "not the planted shell call"}
                for c in cands_b
                if c.get("id") and (not raised_b or c["id"] != raised_b["id"])
            ]
            if review_dir_b is None:
                raise SystemExit("block brief without a review dir")
            good_b = review_dir_b / "good-findings.json"
            none_b = review_dir_b / "none-findings.json"
            good_b.write_text(json.dumps(packet(cid_b, findings_b, dropped_b, "Raises one major and drops the rest.")))
            none_b.write_text(json.dumps(packet(cid_b, [], [], "Answers nothing under a major block threshold.")))
            fin_b = {}
            for name, path in (("good", good_b), ("none", none_b)):
                r = oq(
                    env,
                    repo,
                    ["review", "--finalize", "--config", str(block_cfg), "--cwd", str(repo), str(path)],
                    120,
                )
                fin_b[name] = {
                    "exit": r["exit"],
                    "seconds": r["seconds"],
                    "first": first_line(r["stdout"]),
                    "err": first_line(r["stderr"]),
                }
            result["finalize_block"] = fin_b
        scan = oq(
            env,
            repo,
            [
                "scan", "--base", built["base"], "--only", ONLY, "--block-on-severity", "major",
                "--cwd", str(repo),
            ],
            900,
        )
        result["scan_block_major"] = {
            "exit": scan["exit"],
            "seconds": scan["seconds"],
            "first": first_line(scan["stdout"]),
            "err": first_line(scan["stderr"]),
        }
    result["tools"] = tool_versions(cache)
    homes_after = {
        "claude": dir_mtime((Path.home() / ".claude")),
        "codex": dir_mtime((Path.home() / ".codex")),
        "cursor": dir_mtime((Path.home() / ".cursor")),
        "grok": dir_mtime((Path.home() / ".grok")),
        "openqodex": dir_mtime((Path.home() / ".openqodex")),
    }
    result["home_mtime_unchanged"] = {name: homes[name] == homes_after[name] for name in homes}
    # Drop the planted token if a scanner echoed it before redaction failed.
    blob = redact(json.dumps(result, indent=2))
    if token in blob:
        blob = blob.replace(token, "<redacted>")
    sys.stdout.write(blob + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
