#!/usr/bin/env python3
"""Offline probe for tree-sitter-analyzer 2.2.0.

Compares change-impact with the chiasmus 10-commit window and runs
miswire-audit on this repo. Writes results.json next to this file.
Uses a shared clone under the tool cache. Does not register a worktree.
No network and no API key.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

WT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = Path.home() / ".cache" / "pfy" / "tools" / "tree-sitter-analyzer"
# The lane redirects HOME before launch. Prefer the real cache when the
# process HOME is already the tool home.
if not (BASE / "venv" / "bin" / "tree-sitter-analyzer").is_file():
    BASE = (Path.home() / ".cache/pfy/tools/tree-sitter-analyzer")
BIN = BASE / "venv" / "bin" / "tree-sitter-analyzer"
MISWIRE = BASE / "venv" / "bin" / "miswire-audit"
WHEEL = BASE / "src" / "tree_sitter_analyzer-2.2.0-py3-none-any.whl"
WHEEL_SHA256 = "678ac7708e238c578ca11fb3433b200a007d14ba954f3eb79d8913c552ba1203"
TAG_COMMIT = "a1656acde0d1065f7670c4d041f81a0e344ef6d7"
CLONE = BASE / "probe" / "repo"
CHIASMUS = WT / "eval" / "ev1107" / "chiasmus" / "results.json"
RESULTS = OUT / "results.json"
BUILD_TIMEOUT = 20
FULL_TIMEOUT = 150
MISWIRE_TIMEOUT = 600
LOOP_BUDGET_S = 1500

EXPECTED_SHA = WHEEL_SHA256


def tool_env() -> dict[str, str]:
    return {
        "HOME": str(BASE / "home"),
        "PATH": "%s:/usr/bin:/bin" % (BASE / "venv" / "bin"),
        "XDG_CONFIG_HOME": str(BASE / "xdg" / "config"),
        "XDG_CACHE_HOME": str(BASE / "xdg" / "cache"),
        "XDG_DATA_HOME": str(BASE / "xdg" / "data"),
        "TMPDIR": str(BASE / "tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "pfy-probe",
        "GIT_AUTHOR_EMAIL": "probe@localhost",
        "GIT_COMMITTER_NAME": "pfy-probe",
        "GIT_COMMITTER_EMAIL": "probe@localhost",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def git_env() -> dict[str, str]:
    env = tool_env()
    env["PATH"] = "/usr/bin:/bin"
    return env


def run(argv: list[str], cwd: Path, timeout: float, env: dict[str, str]) -> dict:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        err = exc.stderr or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        return {
            "exit": 124,
            "timed_out": True,
            "seconds": round(time.perf_counter() - started, 3),
            "stdout": out,
            "stderr": err[-2000:],
        }
    return {
        "exit": proc.returncode,
        "timed_out": False,
        "seconds": round(time.perf_counter() - started, 3),
        "stdout": proc.stdout or "",
        "stderr": (proc.stderr or "")[-2000:],
    }


def load_json(text: str):
    start = (text or "").find("{")
    if start < 0:
        return None
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        return None


def usable_map(proc: dict) -> bool:
    """Same rule as scripts/pfy_build_cloud.py change_impact_map."""
    if proc["exit"] != 0:
        return False
    body = (proc["stdout"] or "").strip()
    if not body:
        return False
    if body.startswith("{") and '"error"' in body[:400]:
        return False
    return True


def du_bytes(path: Path) -> int | None:
    if not path.exists():
        return None
    proc = subprocess.run(
        ["du", "-sb", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return int(proc.stdout.split()[0])


def home_stamps() -> dict[str, str]:
    home = Path.home()
    found = {}
    for rel in (".tsa", ".cache/tree-sitter-analyzer", ".config/tree-sitter-analyzer"):
        path = home / rel
        found[rel] = "exists" if path.exists() else "absent"
    return found


def parse_miswire(text: str) -> dict:
    import re

    def num(pattern: str):
        match = re.search(pattern, text)
        if not match:
            return None
        return int(match.group(1).replace(",", ""))

    langs = ""
    offenders = []
    for line in text.splitlines():
        if "languages indexed:" in line:
            langs = line.split("languages indexed:", 1)[1].strip()
        if "caller `" in line:
            offenders.append(line.encode("ascii", "ignore").decode().strip())
    return {
        "call_edges": num(r"call edges analysed: ([0-9,]+)"),
        "naive_miswires": num(r"would mis-wire ([0-9,]+) call edges"),
        "genuine_miswires": num(r"([0-9,]+) are GENUINE"),
        "tsa_miswires": num(r"Tree-sitter Analyzer mis-wires ([0-9,]+)"),
        "languages": langs,
        "fts5_missing": "SQLite has no FTS5" in text,
        "offenders": offenders[:8],
    }


def test_paths(modules: list) -> set[str]:
    found = set()
    for name in modules or []:
        if not isinstance(name, str) or not name:
            continue
        found.add(name.replace(".", "/") + ".py")
    return found


def tsa_test_paths(payload) -> tuple[set[str], int, int]:
    if not isinstance(payload, dict):
        return set(), 0, 0
    raw = payload.get("tests_to_run")
    if not isinstance(raw, list):
        summary = payload.get("agent_summary")
        if isinstance(summary, dict) and isinstance(summary.get("tests_to_run"), list):
            raw = summary["tests_to_run"]
        else:
            raw = []
    paths: set[str] = set()
    for item in raw:
        text = ""
        if isinstance(item, str):
            text = item
        elif isinstance(item, dict):
            for key in ("path", "file", "file_path", "test"):
                if isinstance(item.get(key), str):
                    text = item[key]
                    break
        text = text.replace("\\", "/").lstrip("./")
        if text.startswith("tests.") and "/" not in text:
            text = text.replace(".", "/") + ".py"
        idx = text.find("tests/")
        if idx >= 0 and text.endswith(".py"):
            paths.add(text[idx:])
    omitted = payload.get("tests_to_run_omitted_count")
    count = payload.get("tests_to_run_count")
    if not isinstance(omitted, int):
        omitted = 0
    if not isinstance(count, int):
        count = len(paths)
    return paths, count, omitted


def changed_paths(base: str, sha: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(WT), "diff", "--name-only", base, sha],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line for line in proc.stdout.splitlines() if line]


def select_tests(base: str, sha: str) -> dict:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/test_select.py",
            "--base",
            base,
            "--head",
            sha,
        ],
        cwd=str(WT),
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    payload = load_json(proc.stdout or "")
    if not isinstance(payload, dict):
        return {"mode": "", "modules": [], "error": (proc.stderr or "")[-300:]}
    return payload


def stop_requested() -> bool:
    return (WT / "tmp" / "STOP").exists()


def write_results(payload: dict) -> None:
    RESULTS.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def ensure_clone() -> None:
    if CLONE.exists():
        shutil.rmtree(CLONE)
    CLONE.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "clone", "--shared", "--no-checkout", str(WT), str(CLONE)],
        capture_output=True,
        text=True,
        check=False,
        env=git_env(),
    )
    if proc.returncode != 0:
        raise SystemExit("shared clone failed: %s" % (proc.stderr or "")[-400:])


def place_diff(sha: str, parent: str) -> None:
    """HEAD is parent. The worktree matches sha. The diff is unstaged."""
    env = git_env()
    subprocess.run(
        ["git", "-C", str(CLONE), "checkout", "--force", "--detach", sha],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(CLONE), "reset", "--mixed", parent],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )


def scope_args(paths: list[str], limit: int | None, repeated: bool = False) -> list[str]:
    """One --change-impact-scope takes every path (nargs +).

    Repeating the flag stores only the last path. The build loop in
    scripts/pfy_build_cloud.py repeats it. repeated=True measures that.
    """
    chosen = paths if limit is None else paths[:limit]
    if not chosen:
        return []
    if repeated:
        argv: list[str] = []
        for path in chosen:
            argv.extend(["--change-impact-scope", path])
        return argv
    return ["--change-impact-scope", *chosen]


def impact_row(proc: dict) -> dict:
    payload = load_json(proc["stdout"])
    paths, count, omitted = tsa_test_paths(payload)
    summary = ""
    risk = ""
    verdict = ""
    affected = None
    changed = None
    if isinstance(payload, dict):
        summary = str(payload.get("summary_line") or "")[:240]
        risk = str(payload.get("risk_level") or "")
        verdict = str(payload.get("verdict") or "")
        if isinstance(payload.get("affected_count"), int):
            affected = payload["affected_count"]
        if isinstance(payload.get("changed_count"), int):
            changed = payload["changed_count"]
    return {
        "exit": proc["exit"],
        "timed_out": proc["timed_out"],
        "seconds": proc["seconds"],
        "usable": usable_map(proc),
        "stdout_bytes": len(proc["stdout"] or ""),
        "stderr_tail": (proc["stderr"] or "")[-400:],
        "summary_line": summary,
        "risk_level": risk,
        "verdict": verdict,
        "changed_count": changed,
        "affected_count": affected,
        "tests_to_run_count": count,
        "tests_to_run_omitted_count": omitted,
        "parsed": isinstance(payload, dict),
        "_paths": paths,
    }


def main() -> int:
    if not BIN.is_file() or not MISWIRE.is_file():
        raise SystemExit("missing pin install under %s" % BASE)
    digest = hashlib.sha256(WHEEL.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA:
        raise SystemExit("wheel sha256 mismatch")
    window = json.loads(CHIASMUS.read_text(encoding="utf-8"))
    commits = window["commits"]
    head = subprocess.check_output(
        ["git", "-C", str(WT), "rev-parse", "HEAD"], text=True
    ).strip()
    version = subprocess.check_output([str(BIN), "--version"], text=True, env=tool_env()).strip()
    payload = {
        "pin": {
            "pypi": "tree-sitter-analyzer==2.2.0",
            "wheel_sha256": digest,
            "tag": "v2.2.0",
            "tag_commit": TAG_COMMIT,
            "version_output": version,
            "venv_bytes": du_bytes(BASE / "venv"),
            "no_extras": True,
        },
        "head": head,
        "window": window.get("window"),
        "chiasmus_agreement": window.get("chiasmus_agreement"),
        "cbm_agreement": window.get("cbm_agreement"),
        "home_before": home_stamps(),
        "commits": [],
        "miswire": {},
        "notes": [],
    }
    write_results(payload)
    print("clone", flush=True)
    ensure_clone()
    deadline = time.monotonic() + LOOP_BUDGET_S
    # Cold 20s call first, on the commit where chiasmus blew up to 139 tests.
    cold_sha = "56f6df154eeebf29be90c6290a0a28a917e5d4bb"
    ordered = sorted(commits, key=lambda row: 0 if row["sha"].startswith(cold_sha[:12]) else 1)

    for row in ordered:
        if stop_requested():
            payload["notes"].append("STOP file present; commit loop ended early")
            break
        if time.monotonic() > deadline:
            payload["notes"].append("loop budget elapsed; remaining commits skipped")
            break
        sha = row["sha"]
        parent = row["base"]
        paths = changed_paths(parent, sha)
        selected = select_tests(parent, sha)
        modules = selected.get("modules") if isinstance(selected.get("modules"), list) else []
        select_set = test_paths(modules)
        print("place", sha[:12], "files", len(paths), flush=True)
        place_diff(sha, parent)
        cache = CLONE / ".ast-cache"
        cold_row = None
        warm_row = None
        if sha == cold_sha or sha.startswith(cold_sha[:12]):
            if cache.exists():
                shutil.rmtree(cache)
            print("cold 20s", sha[:12], flush=True)
            cold = run(
                [str(BIN), "--change-impact", "--format", "json", "--change-impact-no-tests"]
                + scope_args(paths, 20),
                CLONE,
                BUILD_TIMEOUT,
                tool_env(),
            )
            cold_row = impact_row(cold)
            cold_row.pop("_paths", None)
            repeated = run(
                [str(BIN), "--change-impact", "--format", "json", "--change-impact-no-tests"]
                + scope_args(paths, 20, repeated=True),
                CLONE,
                BUILD_TIMEOUT,
                tool_env(),
            )
            repeated_row = impact_row(repeated)
            repeated_row.pop("_paths", None)
            cold_row["repeated_flag_changed_count"] = repeated_row.get("changed_count")
            cold_row["repeated_flag_seconds"] = repeated_row.get("seconds")
            cold_row["one_flag_changed_count"] = cold_row.get("changed_count")
        print("full", sha[:12], flush=True)
        full = run(
            [str(BIN), "--change-impact", "--format", "json", "--change-impact-full"]
            + scope_args(paths, None),
            CLONE,
            FULL_TIMEOUT,
            tool_env(),
        )
        full_row = impact_row(full)
        tsa_set = full_row.pop("_paths")
        # One warm 20s call after a finished index, on the next commit.
        if cold_row is None and payload["commits"] and not any(
            item.get("warm_20s") for item in payload["commits"]
        ):
            print("warm 20s", sha[:12], flush=True)
            warm = run(
                [str(BIN), "--change-impact", "--format", "json", "--change-impact-no-tests"]
                + scope_args(paths, 20),
                CLONE,
                BUILD_TIMEOUT,
                tool_env(),
            )
            warm_row = impact_row(warm)
            warm_row.pop("_paths", None)
        agree = bool(full_row["parsed"]) and not full_row["timed_out"] and tsa_set == select_set
        if full_row.get("tests_to_run_omitted_count"):
            agree = False
        item = {
            "sha": sha,
            "base": parent,
            "chiasmus_mode": row.get("mode"),
            "changed_files": len(paths),
            "test_select_mode": selected.get("mode"),
            "test_select": len(select_set),
            "cbm": row.get("cbm"),
            "chiasmus": row.get("chiasmus"),
            "cbm_agree_test_select": row.get("cbm_agree_test_select"),
            "chiasmus_agree_test_select": row.get("agree_test_select"),
            "tsa_sample": sorted(tsa_set)[:8],
            "tsa_tests": len(tsa_set),
            "agree_test_select": agree,
            "only_tsa": len(tsa_set - select_set),
            "only_select": len(select_set - tsa_set),
            "only_tsa_sample": sorted(tsa_set - select_set)[:8],
            "only_select_sample": sorted(select_set - tsa_set)[:8],
            "cold_20s": cold_row,
            "warm_20s": warm_row,
            "full": full_row,
            "ast_cache_bytes": du_bytes(cache),
        }
        payload["commits"].append(item)
        write_results(payload)
        print(
            "done",
            sha[:12],
            "agree",
            agree,
            "tsa",
            len(tsa_set),
            "select",
            len(select_set),
            "full_s",
            full_row["seconds"],
            flush=True,
        )

    if not stop_requested():
        print("miswire", flush=True)
        subprocess.run(
            ["git", "-C", str(CLONE), "checkout", "--force", "--detach", head],
            check=False,
            env=git_env(),
            capture_output=True,
            text=True,
        )
        proc = run([str(MISWIRE), str(CLONE), "--top", "8"], CLONE, MISWIRE_TIMEOUT, tool_env())
        parsed = parse_miswire(proc["stdout"] or "")
        parsed["exit"] = proc["exit"]
        parsed["timed_out"] = proc["timed_out"]
        parsed["seconds"] = proc["seconds"]
        parsed["stderr_tail"] = proc["stderr"]
        payload["miswire"] = parsed
        payload["ast_cache_bytes"] = du_bytes(CLONE / ".ast-cache")
    payload["home_after"] = home_stamps()
    scored = [item for item in payload["commits"] if item["full"]["parsed"] and not item["full"]["timed_out"]]
    payload["tsa_agreement"] = "%s/%s" % (
        sum(1 for item in scored if item["agree_test_select"]),
        len(scored),
    )
    payload["scored_commits"] = len(scored)
    write_results(payload)
    print("agreement", payload["tsa_agreement"], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
