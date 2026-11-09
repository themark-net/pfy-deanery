#!/usr/bin/env python3
"""Offline probe for graphifyy 0.9.104 (CLI command graphify).

Scores `graphify affected` against scripts/test_select.py on the same 10
commits as eval/ev1107/chiasmus/results.json. Code-only extract, no model,
no API key, no graphify prs (that command needs gh auth).

Writes results.json next to this file. The clone and graphs stay under
~/.cache/pfy/tools/graphify/. Does not register a git worktree.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

WT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = (Path.home() / ".cache/pfy/tools/graphify")
BIN = BASE / "venv" / "bin" / "graphify"
PY = BASE / "venv" / "bin" / "python"
WHEEL = BASE / "src" / "graphifyy-0.9.104-py3-none-any.whl"
WHEEL_SHA256 = "ecc5f436a44c4e776aa88e96acd0d5f26f9e3f680f1d1a010ca06547a78fbd55"
TAG = "v0.9.104"
TAG_COMMIT = "433a57a002908e74c9f0abd2ad93af8b302b71c4"
CLONE = BASE / "probe" / "repo"
GRAPHS = BASE / "probe" / "graphs"
CHIASMUS = WT / "eval" / "ev1107" / "chiasmus" / "results.json"
RESULTS = OUT / "results.json"
EXTRACT_TIMEOUT = 600
SELECT_TIMEOUT = 120
BATCH_TIMEOUT = 180
LOOP_BUDGET_S = 2700
DEPTH = 2

LOC_RE = re.compile(r"^- .+ \[[^\]]+\] (.+)$")


def is_test_path(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return (
        rel.startswith("tests/")
        and name.startswith("test_")
        and rel.endswith(".py")
        and "/fixtures/" not in rel
    )


def tool_env() -> dict[str, str]:
    return {
        "HOME": str(BASE / "home"),
        "PATH": "%s:/usr/bin:/bin" % (BASE / "venv" / "bin"),
        "XDG_CONFIG_HOME": str(BASE / "xdg-config"),
        "XDG_CACHE_HOME": str(BASE / "xdg-cache"),
        "XDG_DATA_HOME": str(BASE / "xdg-data"),
        "TMPDIR": str(BASE / "tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "GRAPHIFY_BACKEND": "none",
        "GRAPHIFY_QUERY_LOG_DISABLE": "1",
        "GRAPHIFY_NO_AUTO_REFRESH": "1",
    }


def run(argv: list[str], cwd: Path, timeout: float, env: dict[str, str] | None = None) -> dict:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            env=env if env is not None else tool_env(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "code": 124,
            "seconds": round(time.perf_counter() - started, 3),
            "stdout": (exc.stdout or "") if isinstance(exc.stdout, str) else "",
            "stderr": "timeout %ss" % timeout,
        }
    return {
        "code": proc.returncode,
        "seconds": round(time.perf_counter() - started, 3),
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
    }


def tests_in_affected(text: str) -> set[str]:
    found: set[str] = set()
    for line in text.splitlines():
        match = LOC_RE.match(line)
        if not match:
            continue
        loc = match.group(1).strip().replace("\\", "/")
        path = loc.rsplit(":L", 1)[0] if ":L" in loc else loc
        if path.startswith("./"):
            path = path[2:]
        if is_test_path(path):
            found.add(path)
    return found


def module_to_path(module: str) -> str:
    return module.replace(".", "/") + ".py"


def ensure_clone() -> None:
    if (CLONE / ".git").exists():
        return
    CLONE.parent.mkdir(parents=True, exist_ok=True)
    proc = run(
        ["git", "clone", "--shared", "--no-checkout", str(WT), str(CLONE)],
        WT,
        180,
    )
    if proc["code"] != 0:
        raise SystemExit("clone failed: %s" % proc["stderr"][-500:])


def checkout(sha: str) -> dict:
    return run(["git", "-C", str(CLONE), "checkout", "--force", "--detach", sha], CLONE, 180)


def graph_stats(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = data.get("nodes") or []
    edges = data.get("edges") or data.get("links") or []
    confidence: Counter[str] = Counter()
    relations: Counter[str] = Counter()
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        confidence[str(edge.get("confidence") or "?")] += 1
        relations[str(edge.get("relation") or "?")] += 1
    return {
        "bytes": path.stat().st_size,
        "nodes": len(nodes),
        "edges": len(edges),
        "confidence": dict(confidence),
        "relations": relations.most_common(8),
    }


def extract(sha: str) -> dict:
    out_dir = GRAPHS / sha
    graph = out_dir / "graphify-out" / "graph.json"
    if graph.is_file() and graph.stat().st_size > 1000:
        return {"code": 0, "seconds": 0, "cached": True, "graph": str(graph), "stdout": "", "stderr": ""}
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = run(
        [
            str(BIN),
            "extract",
            str(CLONE),
            "--code-only",
            "--no-cluster",
            "--force",
            "--out",
            str(out_dir),
        ],
        CLONE,
        EXTRACT_TIMEOUT,
    )
    proc["cached"] = False
    proc["graph"] = str(graph)
    proc["stdout_tail"] = proc["stdout"][-1500:]
    proc["stderr_tail"] = proc["stderr"][-1500:]
    return proc


def score_files(graph: Path, files: list[str]) -> dict:
    """One graph load, then the same affected walk the CLI prints."""
    proc = run(
        [str(PY), str(Path(__file__).resolve()), "--batch", str(graph), *files],
        CLONE,
        BATCH_TIMEOUT,
    )
    if proc["code"] != 0:
        return {"code": proc["code"], "error": proc["stderr"][-800:], "files": {}}
    try:
        payload = json.loads(proc["stdout"])
    except json.JSONDecodeError as exc:
        return {"code": 1, "error": "batch json: %s" % exc, "files": {}}
    payload["code"] = 0
    payload["seconds"] = proc["seconds"]
    return payload


def batch_main(argv: list[str]) -> int:
    graph_path = Path(argv[0])
    files = argv[1:]
    from graphify.affected import format_affected, load_graph, resolve_seed_outcome
    from graphify.paths import GRAPHIFY_OUT_NAME

    graph = load_graph(graph_path)
    if graph_path.parent.name == GRAPHIFY_OUT_NAME:
        graph_root = graph_path.parent.parent
    else:
        graph_root = graph_path.parent
    files_out: dict[str, dict] = {}
    for rel in files:
        seed, rivals = resolve_seed_outcome(graph, rel, graph_root)
        if seed is None:
            files_out[rel] = {
                "code": 3 if rivals else 4,
                "tests": [],
                "hits": 0,
                "rivals": len(rivals),
            }
            continue
        text = format_affected(graph, rel, depth=DEPTH, root=graph_root, seed=seed)
        files_out[rel] = {
            "code": 0,
            "tests": sorted(tests_in_affected(text)),
            "hits": sum(1 for line in text.splitlines() if line.startswith("- ")),
            "rivals": 0,
        }
    json.dump({"files": files_out}, sys.stdout)
    return 0


def select_tests(sha: str, base: str) -> dict:
    proc = run(
        [
            sys.executable,
            str(WT / "scripts" / "test_select.py"),
            "--root",
            str(CLONE),
            "--base",
            base,
            "--head",
            sha,
        ],
        WT,
        SELECT_TIMEOUT,
        env={**tool_env(), "PATH": "/usr/bin:/bin"},
    )
    if proc["code"] != 0:
        return {"code": proc["code"], "error": proc["stderr"][-500:], "tests": [], "mode": "", "seconds": proc["seconds"]}
    data = json.loads(proc["stdout"])
    tests = []
    for module in data.get("modules") or []:
        path = module_to_path(module)
        if is_test_path(path):
            tests.append(path)
    return {
        "code": 0,
        "mode": data.get("mode") or "",
        "reason": data.get("reason") or "",
        "tests": tests,
        "seconds": proc["seconds"],
        "changed": data.get("changed") or [],
    }


def changed_py(sha: str, base: str) -> list[dict[str, str]]:
    proc = run(
        ["git", "-C", str(CLONE), "diff", "--name-status", "--find-renames", base, sha],
        CLONE,
        60,
    )
    rows = []
    if proc["code"] != 0:
        return rows
    for line in proc["stdout"].splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[-1]
        if path.endswith(".py"):
            rows.append({"status": status, "path": path})
    return rows


CLI_SEEDS = (
    ("56f6df154eeebf29be90c6290a0a28a917e5d4bb", "scripts/grill_ticket.py"),
    ("31c373ba1c77588f0bdbb875383d7185ca3be3cb", "scripts/pipeline_retro.py"),
    ("79c083e9e53a4302ed30188d40fc29d445140ab6", "scripts/catalog_check.py"),
)


def cli_affected() -> list[dict]:
    """The operator command, on the three scripts whose tests do not import them."""
    rows = []
    for sha, rel in CLI_SEEDS:
        graph = GRAPHS / sha / "graphify-out" / "graph.json"
        if not graph.is_file():
            rows.append({"sha": sha[:12], "seed": rel, "code": 127, "stdout": "", "stderr": "missing graph"})
            continue
        proc = run(
            [str(BIN), "affected", rel, "--depth", str(DEPTH), "--graph", str(graph)],
            BASE,
            60,
        )
        rows.append({
            "sha": sha[:12],
            "seed": rel,
            "code": proc["code"],
            "seconds": proc["seconds"],
            "stdout": proc["stdout"],
            "stderr": proc["stderr"][-300:],
        })
    return rows


def du_bytes(path: Path) -> int:
    proc = run(["du", "-sb", str(path)], path if path.is_dir() else path.parent, 60)
    if proc["code"] != 0:
        return -1
    token = proc["stdout"].split()
    return int(token[0]) if token else -1


def home_markers() -> dict[str, bool]:
    home = Path.home()
    names = [".graphify", ".cache/graphify", ".config/graphify", ".local/share/graphify"]
    return {name: (home / name).exists() for name in names}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        return batch_main(sys.argv[2:])
    started = time.perf_counter()
    if not BIN.is_file():
        raise SystemExit("missing %s" % BIN)
    digest = hashlib.sha256(WHEEL.read_bytes()).hexdigest()
    if digest != WHEEL_SHA256:
        raise SystemExit("wheel sha256 mismatch")
    version = run([str(BIN), "--version"], BASE, 30)
    before_home = home_markers()
    ensure_clone()
    window = json.loads(CHIASMUS.read_text(encoding="utf-8"))
    rows = []
    stopped = ""
    for item in window["commits"]:
        if time.perf_counter() - started > LOOP_BUDGET_S:
            stopped = "loop budget"
            break
        if (WT / "tmp" / "STOP").exists():
            stopped = "tmp/STOP"
            break
        sha = item["sha"]
        base = item["base"]
        print("commit %s" % sha[:12], flush=True)
        checked = checkout(sha)
        if checked["code"] != 0:
            rows.append({"sha": sha, "error": "checkout: %s" % checked["stderr"][-300:]})
            continue
        built = extract(sha)
        graph = Path(built["graph"])
        row: dict = {
            "sha": sha,
            "base": base,
            "prior_mode": item.get("mode"),
            "prior_test_select": item.get("test_select"),
            "prior_cbm": item.get("cbm"),
            "prior_cbm_agree": item.get("cbm_agree_test_select"),
            "prior_chiasmus": item.get("chiasmus"),
            "prior_chiasmus_agree": item.get("agree_test_select"),
            "extract_s": built.get("seconds"),
            "extract_cached": built.get("cached"),
            "extract_code": built.get("code"),
        }
        if built.get("code") != 0 or not graph.is_file():
            row["error"] = (built.get("stderr_tail") or built.get("stderr") or "no graph")[-400:]
            rows.append(row)
            continue
        stats = graph_stats(graph)
        row["nodes"] = stats["nodes"]
        row["edges"] = stats["edges"]
        row["graph_bytes"] = stats["bytes"]
        row["confidence"] = stats["confidence"]
        py_rows = changed_py(sha, base)
        present = [item["path"] for item in py_rows if not item["status"].startswith("D") and (CLONE / item["path"]).is_file()]
        deleted = [item["path"] for item in py_rows if item["status"].startswith("D")]
        selected = select_tests(sha, base)
        row["test_select_mode"] = selected.get("mode")
        row["test_select_s"] = selected.get("seconds")
        row["test_select"] = len(selected.get("tests") or [])
        row["changed_py"] = [item["path"] for item in py_rows]
        row["deleted_py"] = deleted
        if selected.get("code") != 0:
            row["error"] = selected.get("error")
            rows.append(row)
            continue
        scored = score_files(graph, present) if present else {"code": 0, "files": {}, "seconds": 0}
        row["affected_s"] = scored.get("seconds")
        if scored.get("code") != 0:
            row["error"] = scored.get("error")
            rows.append(row)
            continue
        tests: set[str] = set()
        ambiguous = 0
        missing = 0
        hits = 0
        for rel, info in (scored.get("files") or {}).items():
            hits += int(info.get("hits") or 0)
            if info.get("code") == 3:
                ambiguous += 1
            elif info.get("code") == 4:
                missing += 1
            tests.update(info.get("tests") or [])
        changed_tests = {rel for rel in present if is_test_path(rel)}
        tests |= changed_tests
        oracle = set(selected.get("tests") or [])
        row["graphify"] = len(tests)
        row["changed_tests"] = len(changed_tests)
        row["affected_added_tests"] = len(tests - changed_tests)
        row["hits"] = hits
        row["ambiguous_files"] = ambiguous
        row["unmatched_files"] = missing
        row["scoped_files"] = len(present)
        row["agree"] = tests == oracle
        row["only_graphify"] = sorted(tests - oracle)[:20]
        row["only_test_select"] = sorted(oracle - tests)[:20]
        row["only_graphify_count"] = len(tests - oracle)
        row["only_test_select_count"] = len(oracle - tests)
        rows.append(row)
        print(
            "  mode=%s select=%s graphify=%s agree=%s extract=%ss affected=%ss"
            % (
                row["test_select_mode"],
                row["test_select"],
                row["graphify"],
                row["agree"],
                row["extract_s"],
                row["affected_s"],
            ),
            flush=True,
        )
    agreed = sum(1 for row in rows if row.get("agree") is True)
    after_home = home_markers()
    venv_bytes = du_bytes(BASE / "venv")
    pip_bytes = du_bytes(BASE / "pip-cache")
    cli_rows = cli_affected()
    payload = {
        "pin": {
            "pypi": "graphifyy==0.9.104",
            "wheel_sha256": digest,
            "tag": TAG,
            "commit": TAG_COMMIT,
            "version_stdout": version.get("stdout", "").strip(),
            "license": "Apache-2.0",
        },
        "skipped": [
            "graphify prs and graphify prs --triage: gh auth and, for triage, a model backend"
        ],
        "window": window.get("window"),
        "depth": DEPTH,
        "extract_flags": ["--code-only", "--no-cluster", "--force"],
        "published_cbm_agreement": window.get("cbm_agreement"),
        "published_chiasmus_agreement": window.get("chiasmus_agreement"),
        "graphify_agreement": "%s/%s" % (agreed, len(rows)),
        "stopped": stopped,
        "wall_s": round(time.perf_counter() - started, 3),
        "venv_bytes": venv_bytes,
        "pip_cache_bytes": pip_bytes,
        "cli_affected": cli_rows,
        "home_markers_before": before_home,
        "home_markers_after": after_home,
        "commits": rows,
    }
    RESULTS.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("wrote %s agreement %s" % (RESULTS, payload["graphify_agreement"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
