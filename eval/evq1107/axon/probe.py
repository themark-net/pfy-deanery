#!/usr/bin/env python3
"""Offline axon impact probe for the evq1107 lane.

Compares bare-name `axon impact` with file-qualified call edges on the
chiasmus 10-commit window. No embeddings, no axon ui, no API key.
A missing binary writes SKIPPED and exits 0.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

WT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = (Path.home() / ".cache/pfy/tools/axon")
CHIASMUS = WT / "eval" / "ev1107" / "chiasmus" / "results.json"
TSA = WT / "eval" / "evq1107" / "tree-sitter-analyzer" / "results.json"
CLONE = BASE / "probe" / "repo"
CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
TABLES = ("Function", "Class", "Method")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
DIFF_FILE = re.compile(r"^diff --git a/.+? b/(.+)$")
ROW = re.compile(r"^\s*\d+\.\s+(.*)$")
IMPACT_PATH = re.compile(r"--\s+(\S+):\d+")
CONTEXT_FILE = re.compile(r"File:\s*(\S+):\d+")


def tool_home() -> Path:
    return Path(os.environ.get("AXON_TOOL_HOME", str(BASE / "home")))


def axon_bin() -> Path:
    raw = os.environ.get("AXON_BIN", "")
    if raw:
        return Path(raw)
    return BASE / "venv" / "bin" / "axon"


def tool_env() -> dict[str, str]:
    home = tool_home()
    env = {
        "HOME": str(home),
        "PATH": "/usr/bin:/bin",
        "XDG_CONFIG_HOME": str(BASE / "xdg-config"),
        "XDG_CACHE_HOME": str(BASE / "xdg-cache"),
        "XDG_DATA_HOME": str(BASE / "xdg-data"),
        "TMPDIR": str(BASE / "tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "NO_COLOR": "1",
        "TERM": "dumb",
        "COLUMNS": "400",
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "pfy-probe",
        "GIT_AUTHOR_EMAIL": "probe@localhost",
        "GIT_COMMITTER_NAME": "pfy-probe",
        "GIT_COMMITTER_EMAIL": "probe@localhost",
    }
    stub_log = os.environ.get("STUB_LOG", "")
    if stub_log:
        env["STUB_LOG"] = stub_log
    return env


def clean(text: str) -> str:
    return ANSI.sub("", text or "")


def run(argv: list[str], cwd: Path, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            env=tool_env(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "exit": 124,
            "seconds": round(time.perf_counter() - started, 3),
            "stdout": clean(exc.stdout or "" if isinstance(exc.stdout, str) else ""),
            "stderr": "timeout",
        }
    return {
        "exit": proc.returncode,
        "seconds": round(time.perf_counter() - started, 3),
        "stdout": clean(proc.stdout or ""),
        "stderr": clean(proc.stderr or "")[-400:],
    }


def axon(args: list[str], cwd: Path, timeout: float = 120) -> dict:
    return run([str(axon_bin()), *args], cwd, timeout)


def parse_cypher(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    buf: str | None = None
    for line in clean(text).splitlines():
        match = ROW.match(line)
        if match:
            if buf is not None:
                rows.append([part.strip() for part in buf.split("|")])
            buf = match.group(1)
            continue
        if buf is None:
            continue
        if not line.strip() or line.startswith("Results"):
            continue
        buf += line.strip()
    if buf is not None:
        rows.append([part.strip() for part in buf.split("|")])
    return rows


def parse_diff(text: str) -> dict[str, list[tuple[int, int]]]:
    files: dict[str, list[tuple[int, int]]] = {}
    current: str | None = None
    for line in text.splitlines():
        file_match = DIFF_FILE.match(line)
        if file_match:
            current = file_match.group(1)
            if current != "/dev/null":
                files.setdefault(current, [])
            else:
                current = None
            continue
        hunk = HUNK.match(line)
        if hunk and current:
            start = int(hunk.group(1))
            count = int(hunk.group(2) or "1")
            end = start if count == 0 else start + count - 1
            files[current].append((start, end))
    return files


def is_test_path(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return (
        rel.startswith("tests/")
        and name.startswith("test_")
        and rel.endswith(".py")
        and "/fixtures/" not in rel
    )


def module_to_path(mod: str) -> str:
    return mod.replace(".", "/") + ".py"


def overlaps(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= stop and end >= begin for begin, stop in ranges)


def impact_paths(text: str) -> list[str]:
    flat = clean(text).replace("\n", "")
    return IMPACT_PATH.findall(flat)


def context_file(text: str) -> str:
    flat = clean(text).replace("\n", "")
    match = CONTEXT_FILE.search(flat)
    return match.group(1) if match else ""


def test_paths(paths: list[str]) -> set[str]:
    return {path for path in paths if is_test_path(path)}


def changed_tests(repo: Path, base: str, sha: str) -> set[str]:
    proc = run(["git", "diff", "--name-only", base, sha], repo, 60)
    found = set()
    for line in proc["stdout"].splitlines():
        rel = line.strip()
        if is_test_path(rel):
            found.add(rel)
    return found


def select_tests(repo: Path, base: str, sha: str) -> dict:
    proc = run(
        [sys.executable, str(WT / "scripts" / "test_select.py"), "--base", base, "--head", sha, "--root", str(repo)],
        WT,
        180,
    )
    if proc["exit"] != 0:
        return {"mode": "error", "paths": [], "error": proc["stderr"] or proc["stdout"][-300:]}
    try:
        data = json.loads(proc["stdout"])
    except json.JSONDecodeError:
        return {"mode": "error", "paths": [], "error": "test_select did not print JSON"}
    paths = sorted(module_to_path(mod) for mod in data.get("modules") or [])
    return {"mode": data.get("mode") or "", "paths": paths, "error": "", "seconds": proc["seconds"]}


def load_graph(repo: Path) -> tuple[list[dict], dict[str, set[str]], float]:
    symbols: list[dict] = []
    callers: dict[str, set[str]] = {}
    seconds = 0.0
    for table in TABLES:
        sym = axon(
            ["cypher", "MATCH (n:%s) RETURN n.id, n.name, n.file_path, n.start_line, n.end_line" % table],
            repo,
            180,
        )
        seconds += sym["seconds"]
        for row in parse_cypher(sym["stdout"]):
            if len(row) < 5:
                continue
            try:
                start = int(row[3])
                end = int(row[4])
            except ValueError:
                continue
            symbols.append({"id": row[0], "name": row[1], "file": row[2], "start": start, "end": end})
        calls = axon(
            [
                "cypher",
                "MATCH (caller)-[r:CodeRelation]->(callee:%s) WHERE r.rel_type = 'calls' RETURN callee.id, caller.file_path, caller.name" % table,
            ],
            repo,
            180,
        )
        seconds += calls["seconds"]
        for row in parse_cypher(calls["stdout"]):
            if len(row) < 2 or not row[0]:
                continue
            callers.setdefault(row[0], set()).add(row[1])
    return symbols, callers, round(seconds, 3)


def score_repo(repo: Path, base: str, sha: str, index: bool) -> dict:
    row: dict = {"sha": sha, "base": base}
    if index:
        axon_dir = repo / ".axon"
        if axon_dir.exists():
            shutil.rmtree(axon_dir)
        analyzed = axon(["analyze", ".", "--no-embeddings"], repo, 300)
        row["analyze_exit"] = analyzed["exit"]
        row["analyze_s"] = analyzed["seconds"]
        if analyzed["exit"] != 0:
            row["error"] = (analyzed["stderr"] or analyzed["stdout"])[-300:]
            return row
        meta_path = repo / ".axon" / "meta.json"
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            row["stats"] = meta.get("stats") or {}
            total = 0
            for path in (repo / ".axon").rglob("*"):
                if path.is_file():
                    total += path.stat().st_size
            row["index_bytes"] = total
    symbols, callers, graph_s = load_graph(repo)
    row["graph_s"] = graph_s
    row["symbols"] = len(symbols)
    diff = run(["git", "diff", "-U0", base, sha], repo, 60)
    hunks = parse_diff(diff["stdout"])
    targets = []
    for path, ranges in hunks.items():
        if Path(path).suffix.lower() not in CODE_SUFFIXES or not ranges:
            continue
        for sym in symbols:
            if sym["file"] == path and overlaps(sym["start"], sym["end"], ranges):
                targets.append(sym)
    names = sorted({sym["name"] for sym in targets if sym["name"]})
    row["targets"] = len(targets)
    row["names"] = len(names)
    bare: set[str] = set()
    resolved: dict[str, str] = {}
    impact_s = 0.0
    for name in names:
        impact = axon(["impact", name, "--depth", "1"], repo, 60)
        impact_s += impact["seconds"]
        bare |= test_paths(impact_paths(impact["stdout"]))
        ctx = axon(["context", name], repo, 60)
        impact_s += ctx["seconds"]
        resolved[name] = context_file(ctx["stdout"])
    qualified: set[str] = set()
    ids = {sym["id"] for sym in targets}
    for node_id in ids:
        qualified |= test_paths(sorted(callers.get(node_id, ())))
    own = changed_tests(repo, base, sha)
    bare |= own
    qualified |= own
    selected = select_tests(repo, base, sha)
    wanted = set(selected["paths"])
    defining = {}
    for sym in targets:
        defining.setdefault(sym["name"], set()).add(sym["file"])
    mis = 0
    for name, files in defining.items():
        hit = resolved.get(name, "")
        if hit and hit not in files:
            mis += 1
    row.update(
        {
            "impact_s": round(impact_s, 3),
            "test_select_mode": selected["mode"],
            "test_select": sorted(wanted),
            "test_select_count": len(wanted),
            "bare_tests": sorted(bare),
            "qualified_tests": sorted(qualified),
            "bare_agree": bare == wanted and selected["mode"] != "error",
            "qualified_agree": qualified == wanted and selected["mode"] != "error",
            "resolved": resolved,
            "misresolved": mis,
            "changed_test_files": sorted(own),
            "error": selected.get("error") or "",
        }
    )
    return row


def skipped(out: Path, reason: str) -> int:
    payload = {"status": "SKIPPED", "reason": reason, "home": str(tool_home())}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("SKIPPED %s" % reason)
    return 0


def fixture_main(repo: Path, out: Path) -> int:
    if not axon_bin().is_file():
        return skipped(out, "axon binary missing: %s" % axon_bin())
    base = run(["git", "rev-parse", "HEAD^"], repo, 30)["stdout"].strip()
    sha = run(["git", "rev-parse", "HEAD"], repo, 30)["stdout"].strip()
    row = score_repo(repo, base, sha, index=True)
    names = list((row.get("resolved") or {}).values())
    payload = {
        "status": "ok" if not row.get("error") else "error",
        "home": str(tool_home()),
        "bare_tests": row.get("bare_tests") or [],
        "qualified_tests": row.get("qualified_tests") or [],
        "bare_agree": bool(row.get("bare_agree")),
        "qualified_agree": bool(row.get("qualified_agree")),
        "resolved_file": names[0] if len(names) == 1 else "",
        "test_select": row.get("test_select") or [],
        "test_select_mode": row.get("test_select_mode") or "",
        "error": row.get("error") or "",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if payload["error"]:
        print(payload["error"])
        return 1
    print(
        "bare %s qualified %s mode %s"
        % (payload["bare_agree"], payload["qualified_agree"], payload["test_select_mode"])
    )
    return 0


def home_flags() -> dict[str, str]:
    flags = {}
    for rel in (".axon", ".cache/axon", ".config/axon"):
        flags[rel] = "present" if Path.home().joinpath(rel).exists() else "absent"
    return flags


def du_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    proc = run(["du", "-sb", str(path)], path if path.is_dir() else path.parent, 60)
    token = proc["stdout"].split()
    if not token:
        return 0
    try:
        return int(token[0])
    except ValueError:
        return 0


def real_main(out: Path) -> int:
    if not axon_bin().is_file():
        return skipped(out, "axon binary missing: %s" % axon_bin())
    if (WT / "tmp" / "STOP").exists():
        return skipped(out, "tmp/STOP")
    window = json.loads(CHIASMUS.read_text(encoding="utf-8"))
    tsa_by_sha = {}
    if TSA.is_file():
        for item in json.loads(TSA.read_text(encoding="utf-8")).get("commits") or []:
            tsa_by_sha[item.get("sha")] = item
    before = home_flags()
    version = axon(["--version"], WT, 30)
    commits = []
    started = time.perf_counter()
    for item in window["commits"]:
        if (WT / "tmp" / "STOP").exists():
            break
        sha = item["sha"]
        base = item["base"]
        checkout = run(["git", "checkout", "--force", "--detach", sha], CLONE, 120)
        if checkout["exit"] != 0:
            commits.append({"sha": sha, "base": base, "error": checkout["stderr"] or checkout["stdout"][-200:]})
            continue
        row = score_repo(CLONE, base, sha, index=True)
        row["cbm"] = item.get("cbm")
        row["chiasmus"] = item.get("chiasmus")
        row["cbm_agree_test_select"] = item.get("cbm_agree_test_select")
        row["chiasmus_agree_test_select"] = item.get("agree_test_select")
        tsa = tsa_by_sha.get(sha) or {}
        row["tsa"] = tsa.get("tsa_tests")
        row["tsa_agree_test_select"] = tsa.get("agree_test_select")
        commits.append(row)
        print(
            "%s bare %s qualified %s select %s"
            % (sha[:12], row.get("bare_agree"), row.get("qualified_agree"), row.get("test_select_count"))
        )
        out.write_text(json.dumps({"commits": commits}, indent=2) + "\n", encoding="utf-8")
    bare_hits = sum(1 for row in commits if row.get("bare_agree"))
    qual_hits = sum(1 for row in commits if row.get("qualified_agree"))
    payload = {
        "status": "ok",
        "pin": {
            "git": "2b386fb38a468201ab2ec825ddea5ebf4c33f513",
            "pypi": "axoniq==1.0.1",
            "pypi_wheel_sha256": "4632b2f6d11a7c365ade3a307d3d49b7f4e0010ef338ee2531a12caf57260a60",
            "mcp": "1.30.0",
            "version_output": version["stdout"].strip(),
            "venv_bytes": du_bytes(BASE / "venv"),
            "no_embeddings": True,
        },
        "window": window.get("window"),
        "bare_agreement": "%s/%s" % (bare_hits, len(commits)),
        "qualified_agreement": "%s/%s" % (qual_hits, len(commits)),
        "cbm_agreement": window.get("cbm_agreement"),
        "chiasmus_agreement": window.get("chiasmus_agreement"),
        "wall_s": round(time.perf_counter() - started, 3),
        "home_before": before,
        "home_after": home_flags(),
        "commits": commits,
    }
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(payload["bare_agreement"], payload["qualified_agreement"], payload["wall_s"])
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    fixture = ""
    out = str(OUT / "results.json")
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--fixture" and index + 1 < len(args):
            fixture = args[index + 1]
            index += 2
            continue
        if token == "--out" and index + 1 < len(args):
            out = args[index + 1]
            index += 2
            continue
        print("unknown arg %s" % token)
        return 2
    if fixture:
        return fixture_main(Path(fixture), Path(out))
    return real_main(Path(out))


if __name__ == "__main__":
    raise SystemExit(main())
