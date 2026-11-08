#!/usr/bin/env python3
"""Offline RoBrain probe for gap H1 (a repeatable with/without memory score).

Runs the pinned VetoBench retrieval layer (hash embedder, no API key, no
--live) and ranks 10 re-proposals of rejected options from docs/adr.
Postgres + pgvector is not started: Perception needs an embedding provider.

Child HOME, XDG_*, and TMPDIR stay under the path passed as --home.
The child env is not the parent env. No model lock.
"""

from __future__ import annotations

import argparse
import json
import os
import pwd
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RANK = HERE / "rank.mjs"
PIN = "ac53011016e5f7dd42bae9c00c1a9b7d207a68b8"
EXPECT = {
    "default": {"rows": 10, "files": 1.00, "nofiles": 0.70},
    "lifecycle": {"rows": 4, "files": 1.00, "nofiles": 1.00},
}
K = 5
OVERLAP_WORDS = ("memory", "veto", "pgvector", "postgres", "embedding", "embeddings")
RECALL_RE = re.compile(
    r"veto recall@5:\s*([0-9.]+)\s+with files known.*?([0-9.]+)\s+without",
    re.S,
)
ROW_RE = re.compile(r"^(s\w+)\s+\S+\s+\d+\s+[✓✗]\s+\d+\s+[✓✗]\s*$", re.M)
WATCHED = (".robrain", ".mem0")
SYS_PATH = "/usr/bin:/bin"


def cache_base() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir) / ".cache" / "pfy" / "tools" / "robrain"


def real_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def tokens(text: str) -> set[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return {part for part in cleaned.split() if len(part) > 2}


def decision_text(row: dict, *, with_rejected: bool) -> str:
    parts = [row.get("decision") or "", row.get("rationale") or ""]
    if with_rejected:
        for item in row.get("rejected") or []:
            parts.append(item.get("option") or "")
            parts.append(item.get("reason") or "")
    return " ".join(parts)


def overlap_ranks(corpus: list[dict], fixture: dict, *, with_rejected: bool, with_files: bool) -> list[dict]:
    """Token overlap on the same fields the hash embedder sees, or on the ADR text."""
    rows = []
    query_files_key = "files_in_scope"
    for scenario in fixture["scenarios"]:
        query = tokens(scenario["task"])
        scope = set(scenario.get(query_files_key) or []) if with_files else set()
        scored = []
        for index, row in enumerate(corpus):
            doc = tokens(decision_text(row, with_rejected=with_rejected))
            lexical = (len(query & doc) / len(query)) if query else 0.0
            file_hit = 1.0 if scope and scope <= set(row.get("files_affected") or []) else 0.0
            # File boost is recorded only for the files-known arm. Lexical stays the rank key
            # when files are empty, matching the "no files" retrieval arm.
            score = lexical + file_hit
            scored.append((score, index, row["id"]))
        scored.sort(key=lambda item: (-item[0], item[1]))
        order = [item[2] for item in scored]
        veto = scenario["veto_decision_id"]
        rank = order.index(veto) + 1 if veto in order else 0
        rows.append({
            "id": scenario["id"],
            "veto": veto,
            "trap": scenario.get("trap"),
            "rank": rank,
        })
    return rows


def recall(rows: list[dict] | None, key: str = "rank") -> float | None:
    if not rows:
        return None
    hits = 0
    for row in rows:
        rank = row.get(key)
        if isinstance(rank, int) and 0 < rank <= K:
            hits += 1
    return round(hits / len(rows), 4)


def count_hits(rows: list[dict] | None, key: str = "rank") -> int | None:
    if rows is None:
        return None
    return sum(1 for row in rows if isinstance(row.get(key), int) and 0 < row[key] <= K)


def count_top1(rows: list[dict] | None, key: str = "rank") -> int | None:
    if rows is None:
        return None
    return sum(1 for row in rows if row.get(key) == 1)


def home_sig(home: Path) -> dict:
    sig = {}
    for rel in WATCHED:
        path = home / rel
        if path.is_dir():
            sig[rel] = sorted(
                (str(item.relative_to(path)), item.stat().st_size, item.stat().st_mtime_ns)
                for item in path.rglob("*")
                if item.is_file()
            )
        elif path.exists():
            sig[rel] = [path.stat().st_size, path.stat().st_mtime_ns]
        else:
            sig[rel] = None
    return sig


def dir_bytes(path: Path, *, skip_parts: tuple[str, ...] = ()) -> int | None:
    if not path.exists():
        return None
    total = 0
    if path.is_file():
        return path.stat().st_size
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        if skip_parts and any(part in skip_parts for part in item.relative_to(path).parts):
            continue
        try:
            total += item.stat().st_size
        except OSError:
            continue
    return total


def child_env(home: Path, tmp: Path, node: str) -> dict[str, str]:
    return {
        "PATH": f"{Path(node).resolve().parent}:{SYS_PATH}",
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / "xdg-config"),
        "XDG_CACHE_HOME": str(home / "xdg-cache"),
        "XDG_DATA_HOME": str(home / "xdg-data"),
        "TMPDIR": str(tmp),
        "LANG": "C.UTF-8",
        "NO_COLOR": "1",
        "TERM": "dumb",
        "ROBRAIN_VETOBENCH": "",
    }


def run_node(node: str, args: list[str], cwd: Path, env: dict[str, str], timeout: float) -> subprocess.CompletedProcess:
    if "--live" in args:
        raise RuntimeError("refusing --live")
    return subprocess.run(
        [node, *args],
        cwd=str(cwd),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def parse_upstream(text: str) -> dict:
    match = RECALL_RE.search(text)
    got = None
    if match:
        got = {"files": float(match.group(1)), "nofiles": float(match.group(2))}
    return {
        "recall": got,
        "rows": len(ROW_RE.findall(text)),
        "offline": "offline run" in text,
        "passed": ("PASS" in text) and ("FAIL" not in text),
        "tail": text[-500:],
    }


def pin_ok(name: str, parsed: dict) -> bool:
    want = EXPECT[name]
    got = parsed.get("recall")
    if not got or not parsed.get("offline") or not parsed.get("passed"):
        return False
    return (
        parsed.get("rows") == want["rows"]
        and abs(got["files"] - want["files"]) < 1e-9
        and abs(got["nofiles"] - want["nofiles"]) < 1e-9
    )


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def card_matches(repo: Path) -> list[dict]:
    stages = repo / "data" / "stages"
    found = []
    if not stages.is_dir():
        return found
    for path in sorted(stages.glob("*.json")):
        if path.name == "_registry.json" or path.name == "robrain.json":
            continue
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        blob = json.dumps({
            "uses": card.get("uses"),
            "features": card.get("features"),
            "tags": card.get("tags"),
            "catalog_tags": card.get("catalog_tags"),
        }).lower()
        hits = [word for word in OVERLAP_WORDS if re.search(rf"\b{word}\b", blob)]
        if not hits:
            continue
        found.append({
            "file": path.name,
            "name": card.get("name"),
            "integration_stage": card.get("integration_stage"),
            "hits": hits,
            "uses": card.get("uses") if isinstance(card.get("uses"), str) else "",
        })
    return found


def verdict_lines(repo: Path) -> dict:
    names = {
        "skill-up": repo / "eval" / "catchup-1107" / "skill-up" / "VERDICT",
        "cass-memory": repo / "eval" / "evq1107" / "cass-memory" / "VERDICT",
        "opencontext": repo / "eval" / "evq1107" / "opencontext" / "VERDICT",
        "leann": repo / "eval" / "evq1107" / "leann" / "VERDICT",
        "mempalace": repo / "eval" / "evq1107" / "mempalace" / "VERDICT",
        "ai-memory": repo / "eval" / "evq1107" / "ai-memory" / "VERDICT",
        "opencode-mem": repo / "eval" / "evq1107" / "opencode-mem" / "VERDICT",
        "kenfold": repo / "eval" / "evq1107" / "kenfold" / "VERDICT",
    }
    out = {}
    for name, path in names.items():
        if path.is_file():
            out[name] = path.read_text(encoding="utf-8").strip().splitlines()[0][:240]
    return out


def git_head(repo: Path) -> str | None:
    git = repo / ".git"
    try:
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not head.startswith("ref: "):
        return head or None
    ref = head[5:]
    try:
        return (git / ref).read_text(encoding="utf-8").strip()
    except OSError:
        pass
    try:
        for line in (git / "packed-refs").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == ref:
                return parts[0]
    except OSError:
        pass
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--node", default="")
    parser.add_argument("--vetobench", type=Path, default=None)
    parser.add_argument("--corpus", type=Path, default=HERE / "corpus.json")
    parser.add_argument("--scenarios", type=Path, default=HERE / "scenarios.json")
    parser.add_argument("--home", type=Path, default=None)
    parser.add_argument("--real-home", type=Path, default=None)
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    started = time.perf_counter()
    node = args.node or shutil.which("node") or ""
    vetobench = args.vetobench or (cache_base() / "src" / "robrain" / "packages" / "vetobench")
    candidate = vetobench.parent.parent
    if (candidate / "package.json").is_file() and (candidate / "packages" / "vetobench").is_dir():
        checkout = candidate
    else:
        checkout = None
    home = args.home or (cache_base() / "probe-home")
    watched = args.real_home or real_home()
    tmp = home / "tmp"
    home.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    for rel in ("xdg-config", "xdg-cache", "xdg-data"):
        (home / rel).mkdir(parents=True, exist_ok=True)

    before = home_sig(watched)
    corpus = load_json(args.corpus)
    fixture = load_json(args.scenarios)
    built = (vetobench / "dist" / "run.js").is_file() and (vetobench / "dist" / "adapters.js").is_file()
    head = git_head(checkout) if checkout is not None and (checkout / ".git").exists() else None

    result: dict = {
        "pin": PIN,
        "head": head,
        "pin_match": head == PIN if head else None,
        "node": node,
        "vetobench": str(vetobench),
        "built": built,
        "corpus_rows": len(corpus),
        "scenarios": len(fixture["scenarios"]),
        "k": K,
        "as_of": fixture.get("as_of"),
        "postgres_pgvector": {
            "status": "SKIPPED",
            "reason": "Perception embeds at 1536 dims and needs an API key or a local model. This lane takes neither, and it does not start podman.",
        },
        "live": "not run",
        "commands": [],
        "upstream": {},
        "upstream_pin_ok": False,
        "robrain": None,
        "overlap_decision": None,
        "overlap_adr": None,
        "cards": card_matches(args.repo),
        "neighbor_verdicts": verdict_lines(args.repo),
        "bytes": {
            "checkout": dir_bytes(checkout) if checkout is not None else None,
            "node_modules": dir_bytes(checkout / "node_modules") if checkout is not None else None,
            "source_without_deps": dir_bytes(checkout, skip_parts=(".git", "node_modules")) if checkout is not None else None,
        },
        "node_version": None,
    }

    overlap_decision_files = overlap_ranks(corpus, fixture, with_rejected=False, with_files=True)
    overlap_decision_none = overlap_ranks(corpus, fixture, with_rejected=False, with_files=False)
    overlap_adr_files = overlap_ranks(corpus, fixture, with_rejected=True, with_files=True)
    overlap_adr_none = overlap_ranks(corpus, fixture, with_rejected=True, with_files=False)
    result["overlap_decision"] = {
        "files_known": {
            "hits": count_hits(overlap_decision_files),
            "top1": count_top1(overlap_decision_files),
            "recall": recall(overlap_decision_files),
            "rows": overlap_decision_files,
        },
        "no_files": {
            "hits": count_hits(overlap_decision_none),
            "top1": count_top1(overlap_decision_none),
            "recall": recall(overlap_decision_none),
            "rows": overlap_decision_none,
        },
    }
    result["overlap_adr"] = {
        "files_known": {
            "hits": count_hits(overlap_adr_files),
            "top1": count_top1(overlap_adr_files),
            "recall": recall(overlap_adr_files),
            "rows": overlap_adr_files,
        },
        "no_files": {
            "hits": count_hits(overlap_adr_none),
            "top1": count_top1(overlap_adr_none),
            "recall": recall(overlap_adr_none),
            "rows": overlap_adr_none,
        },
    }
    result["none_memory_hits"] = 0
    result["flatfile_hits"] = len(fixture["scenarios"])

    if not node or not built:
        result["robrain_status"] = "SKIPPED"
        result["robrain_reason"] = "node or vetobench dist is missing"
    else:
        env = child_env(home, tmp, node)
        env["ROBRAIN_VETOBENCH"] = str(vetobench)
        try:
            ver = run_node(node, ["--version"], vetobench, env, min(args.timeout, 15.0))
            result["node_version"] = (ver.stdout or "").strip()
        except (OSError, subprocess.TimeoutExpired, RuntimeError):
            result["node_version"] = None
        upstream_ok = True
        for name, extra in (("default", []), ("lifecycle", ["--suite", "lifecycle"])):
            cmd = ["dist/run.js", *extra]
            result["commands"].append(cmd)
            t0 = time.perf_counter()
            try:
                proc = run_node(node, cmd, vetobench, env, args.timeout)
                text = (proc.stdout or "") + (proc.stderr or "")
                parsed = parse_upstream(text)
                parsed["exit"] = proc.returncode
                parsed["ms"] = round((time.perf_counter() - t0) * 1000.0, 1)
            except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
                parsed = {"error": str(exc), "recall": None, "rows": 0, "offline": False, "passed": False, "tail": ""}
                upstream_ok = False
            result["upstream"][name] = parsed
            if not pin_ok(name, parsed):
                upstream_ok = False
        result["upstream_pin_ok"] = upstream_ok
        rank_cmd = [str(RANK), str(args.corpus), str(args.scenarios)]
        result["commands"].append(rank_cmd)
        t1 = time.perf_counter()
        try:
            proc = run_node(
                node,
                rank_cmd,
                vetobench,
                env,
                args.timeout,
            )
            raw = (proc.stdout or "").strip().splitlines()
            payload = json.loads(raw[-1]) if raw else {}
            rows = payload.get("rows")
            if proc.returncode != 0 or not isinstance(rows, list) or len(rows) != len(fixture["scenarios"]):
                raise ValueError(f"rank exit {proc.returncode}")
            result["robrain"] = {
                "files_known": {
                    "hits": count_hits(rows, "rank_files"),
                    "top1": count_top1(rows, "rank_files"),
                    "recall": recall(rows, "rank_files"),
                },
                "no_files": {
                    "hits": count_hits(rows, "rank_nofiles"),
                    "top1": count_top1(rows, "rank_nofiles"),
                    "recall": recall(rows, "rank_nofiles"),
                },
                "rows": rows,
                "ms": round((time.perf_counter() - t1) * 1000.0, 1),
                "exit": proc.returncode,
            }
            result["robrain_status"] = "RAN"
        except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            result["robrain_status"] = "FAIL"
            result["robrain_reason"] = str(exc)[:300]
            result["robrain"] = None

    rob_nf = None if not result["robrain"] else result["robrain"]["no_files"]["recall"]
    adr_nf = result["overlap_adr"]["no_files"]["recall"]
    dec_nf = result["overlap_decision"]["no_files"]["recall"]
    result["beats_adr_text"] = None if rob_nf is None or adr_nf is None else rob_nf > adr_nf
    result["beats_decision_overlap"] = None if rob_nf is None or dec_nf is None else rob_nf > dec_nf
    result["home_unchanged"] = home_sig(watched) == before
    result["ms"] = round((time.perf_counter() - started) * 1000.0, 1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "robrain_status": result["robrain_status"],
        "upstream_pin_ok": result["upstream_pin_ok"],
        "robrain_nofiles": None if not result["robrain"] else result["robrain"]["no_files"],
        "overlap_adr_nofiles": result["overlap_adr"]["no_files"]["hits"],
        "beats_adr_text": result["beats_adr_text"],
        "home_unchanged": result["home_unchanged"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
