#!/usr/bin/env python3
"""Score MemPalace recall on eight verbatim excerpts from this repo.

The palace, HOME, and temp files stay under --work and --home. Init is
--no-llm and --embedding-model minilm. No API key is read or set. Gap H1
is a with/without harness grade. This probe does not grade one, so
h1_graded_cases stays 0. The number it does emit is top-1 recall, top-5
recovery, repeat agreement, and wing-filter leaks, against a word-overlap
walk of the same excerpts.
"""

from __future__ import annotations

import argparse
import json
import os
import pwd
import re
import subprocess
import time
from pathlib import Path

PIN = "84582fb055a6429261f9c779da86c0561ec80adc"
VERSION = "3.12.0"
WATCHED = (".mempalace", ".config/mempalace", ".cache/chroma")
JOB_TOKENS = (
    "memory",
    "verbatim",
    "recall",
    "rag",
    "embedding",
    "embeddings",
    "chroma",
    "handoff",
    "vector",
    "bm25",
    "code-memory",
)
STOP = frozenset(
    """
    how many the this that with from your does which where what before after
    only into each must pass have been was were they them than then and for
    relative records asks stops taking same against about when will over four
    tool give does not are its
    """.split()
)
HIT_RE = re.compile(
    r"\[(\d+)\]\s+(.+?)\s+/\s+(.+?)\n\s+Source:\s+(\S+)"
)
FACTS = (
    {
        "id": "value-gate",
        "wing": "handoff",
        "source": "docs/ops/integration-stages.md",
        "anchor": "Promote toward onboard only if",
        "question": "How many of the four value checks must pass before a tool is onboarded?",
    },
    {
        "id": "state-file",
        "wing": "handoff",
        "source": "docs/ops/MODULAR-CI.md",
        "anchor": "Give each tool its own state file.",
        "question": "What does modular CI give each tool so two lanes do not share state?",
    },
    {
        "id": "worker-model",
        "wing": "handoff",
        "source": "AGENTS.md",
        "anchor": "LOCAL_CODER_MODEL",
        "question": "Which environment variable names the local worker model?",
    },
    {
        "id": "code-graph",
        "wing": "handoff",
        "source": "data/stages/codebase-memory-mcp.json",
        "anchor": "Primary code-graph MCP",
        "question": "Which tool is the primary code graph MCP?",
    },
    {
        "id": "memory-slot",
        "wing": "ranking",
        "source": "docs/eval/TOOLSET-RANKING.md",
        "anchor": "Post-MVP memory slot",
        "question": "Where does the 2026-11-07 ranking place the memory slot relative to the MVP?",
    },
    {
        "id": "h1-gap",
        "wing": "ranking",
        "source": "docs/eval/TOOLSET-RANKING.md",
        "anchor": "harness2 showed no gain",
        "question": "Which gap records that harness2 showed no gain and asks for a with and without score?",
    },
    {
        "id": "skill-grade",
        "wing": "ranking",
        "source": "data/stages/skill-up.json",
        "anchor": "Grade a with-skill run against a no-skill baseline.",
        "question": "Which use grades a run that has a skill against a run that does not?",
    },
    {
        "id": "claim-once",
        "wing": "ranking",
        "source": "sources/entries/132-ai-memory.md",
        "anchor": "claim-once guarantee",
        "question": "What guarantee stops two bots from taking the same handoff?",
    },
)


def login_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def home_sig(home: Path) -> dict:
    out = {}
    for rel in WATCHED:
        path = home / rel
        try:
            st = path.lstat()
        except FileNotFoundError:
            out[rel] = None
            continue
        except OSError:
            out[rel] = "unreadable"
            continue
        out[rel] = {"mode": st.st_mode, "size": st.st_size, "mtime_ns": st.st_mtime_ns}
    return out


def excerpt(text: str, anchor: str, max_chars: int = 500) -> str | None:
    """A short verbatim window around the anchor, snapped to line breaks."""
    found = text.find(anchor)
    if found < 0:
        return None
    start = max(0, found - (max_chars // 2))
    end = min(len(text), found + len(anchor) + (max_chars // 2))
    if start > 0:
        newline = text.find("\n", start, found)
        if newline != -1:
            start = newline + 1
    if end < len(text):
        newline = text.rfind("\n", found, end)
        if newline != -1:
            end = newline
    chunk = text[start:end].strip()
    if anchor not in chunk:
        chunk = text[found : found + len(anchor)].strip()
    return chunk


def content_tokens(text: str) -> set[str]:
    found = set()
    for word in re.findall(r"[A-Za-z0-9_+.-]+", text.lower()):
        if len(word) >= 4 and word not in STOP:
            found.add(word)
    return found


def file_walk_winner(question: str, bodies: dict[str, str]) -> str | None:
    wanted = content_tokens(question)
    scores = {name: len(wanted & content_tokens(body)) for name, body in bodies.items()}
    if not scores:
        return None
    best = max(scores.values())
    if best <= 0:
        return None
    winners = [name for name, score in scores.items() if score == best]
    if len(winners) != 1:
        return None
    return winners[0]


def parse_hits(text: str) -> list[dict]:
    hits = []
    for match in HIT_RE.finditer(text):
        hits.append(
            {
                "rank": int(match.group(1)),
                "wing": match.group(2).strip(),
                "room": match.group(3).strip(),
                "source": match.group(4),
            }
        )
    return hits


def parse_drawers(text: str) -> int | None:
    match = re.search(r"Drawers filed:\s*(\d+)", text)
    if not match:
        return None
    return int(match.group(1))


def version_of(text: str) -> str | None:
    match = re.search(r"\b(\d+\.\d+\.\d+[0-9A-Za-z.+-]*)", text)
    return match.group(1) if match else None


def tree_bytes(path: Path, skip_git: bool = False) -> int:
    if not path.exists():
        return 0
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        if skip_git and ".git" in dirnames:
            dirnames.remove(".git")
        for name in filenames:
            try:
                total += (Path(dirpath) / name).stat().st_size
            except OSError:
                continue
    return total


def yaml_paths(repo: Path, sources: list[str]) -> list[str]:
    parents = {repo}
    for rel in sources:
        parents.add((repo / rel).parent)
    found = []
    for parent in sorted(parents):
        path = parent / "mempalace.yaml"
        if path.exists():
            found.append(str(path))
    return found


def card_blob(card: dict) -> str:
    parts: list[str] = []
    for key in ("uses", "features", "tags", "catalog_tags"):
        value = card.get(key)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
    return " ".join(parts)


def job_tokens(text: str) -> list[str]:
    lowered = text.lower()
    words = set(re.findall(r"[a-z0-9_+-]+", lowered))
    found = []
    for token in JOB_TOKENS:
        if token in words or token in lowered.split():
            found.append(token)
    return found


def catalog_overlaps(stages: Path) -> list[dict]:
    rows = []
    if not stages.is_dir():
        return rows
    for path in sorted(stages.glob("*.json")):
        if path.name == "_registry.json":
            continue
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(card, dict):
            continue
        name = str(card.get("name") or path.stem)
        if name.lower().replace(" ", "") == "mempalace":
            continue
        tokens = job_tokens(card_blob(card))
        if not tokens:
            continue
        uses = card.get("uses")
        rows.append(
            {
                "name": name,
                "file": path.name,
                "integration_stage": card.get("integration_stage"),
                "tokens": tokens,
                "uses": uses if isinstance(uses, str) else "",
            }
        )
    return rows


def under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def run_cmd(args: list[str], cwd: Path, env: dict, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "exit": None,
            "timed_out": True,
            "seconds": round(time.perf_counter() - started, 3),
            "stdout": (exc.stdout or "")[-800:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-800:] if isinstance(exc.stderr, str) else "",
        }
    text_out = proc.stdout or ""
    text_err = proc.stderr or ""
    return {
        "exit": proc.returncode,
        "timed_out": False,
        "seconds": round(time.perf_counter() - started, 3),
        "stdout": text_out[-800:],
        "stderr": text_err[-800:],
        "combined": text_out + "\n" + text_err,
    }


def child_env(home: Path, work: Path, binary: Path) -> dict:
    return {
        "PATH": "/usr/bin:/bin:" + str(binary.parent),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / "xdg-config"),
        "XDG_CACHE_HOME": str(home / "xdg-cache"),
        "XDG_DATA_HOME": str(home / "xdg-data"),
        "TMPDIR": str(work / "tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "NO_COLOR": "1",
        "TERM": "dumb",
        "ANONYMIZED_TELEMETRY": "False",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "MEMPALACE_EMBEDDING_DEVICE": "cpu",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def search_once(binary: Path, palace: Path, question: str, wing: str | None, cwd: Path, env: dict, timeout: float) -> dict:
    args = [str(binary), "--palace", str(palace), "search", question, "--results", "5"]
    if wing:
        args.extend(["--wing", wing])
    result = run_cmd(args, cwd, env, timeout)
    hits = parse_hits(result.get("combined") or "")
    result["hits"] = hits
    result.pop("combined", None)
    result.pop("stdout", None)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MemPalace recall probe on this repo")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bin", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--real-home", type=Path, default=None)
    parser.add_argument("--src", type=Path, default=None)
    parser.add_argument("--timeout", type=float, default=240.0)
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    work = args.work.resolve()
    home = args.home.resolve()
    real = (args.real_home or login_home()).resolve()
    stages = Path(__file__).resolve().parents[3] / "data" / "stages"
    doc: dict = {
        "pin": PIN,
        "version_expected": VERSION,
        "h1_graded_cases": 0,
        "status": "skipped",
        "repo_mempalace_yaml_before": [],
        "repo_mempalace_yaml_after": [],
        "repo_mempalace_yaml_new": [],
        "questions": [],
    }
    before_home = home_sig(real)
    before_yaml = yaml_paths(repo, [fact["source"] for fact in FACTS])
    doc["repo_mempalace_yaml_before"] = before_yaml

    def finish(code: int = 0) -> int:
        after_home = home_sig(real)
        changed = [rel for rel in WATCHED if before_home.get(rel) != after_home.get(rel)]
        doc["real_home_changed"] = changed
        after_yaml = yaml_paths(repo, [fact["source"] for fact in FACTS])
        doc["repo_mempalace_yaml_after"] = after_yaml
        doc["repo_mempalace_yaml_new"] = [item for item in after_yaml if item not in before_yaml]
        doc["overlaps"] = catalog_overlaps(stages)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        return code

    if not args.bin.is_file():
        doc["reason"] = "mempalace binary missing"
        return finish(0)
    if under(work, repo) or under(home, repo):
        doc["reason"] = "work and home must stay outside the repo"
        return finish(0)

    for path in (work, home, work / "tmp", home / "xdg-config", home / "xdg-cache", home / "xdg-data"):
        path.mkdir(parents=True, exist_ok=True)
    corpus = work / "corpus"
    palace = work / "palace"
    env = child_env(home, work, args.bin)

    prepared = []
    for fact in FACTS:
        source = repo / fact["source"]
        try:
            text = source.read_text(encoding="utf-8")
        except OSError:
            text = ""
        body = excerpt(text, fact["anchor"])
        row = {
            "id": fact["id"],
            "wing": fact["wing"],
            "source": fact["source"],
            "anchor_found": body is not None,
            "question": fact["question"],
        }
        if body is None:
            doc["questions"].append(row)
            continue
        dest_dir = corpus / fact["wing"]
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / f"{fact['id']}.md").write_text(body + "\n", encoding="utf-8")
        row["bytes"] = len(body.encode("utf-8"))
        prepared.append((fact, body, row))
    doc["anchors_found"] = len(prepared)
    if len(prepared) != len(FACTS):
        doc["reason"] = "one or more anchors missing from the repo"
        return finish(0)

    if args.src and (args.src / ".git").exists():
        git = run_cmd(["git", "-C", str(args.src), "rev-parse", "HEAD"], work, env, 30)
        doc["src_head"] = (git.get("stdout") or "").strip()
        doc["src_head_matches_pin"] = doc["src_head"] == PIN
        doc["src_bytes"] = tree_bytes(args.src)
        doc["src_git_bytes"] = tree_bytes(args.src / ".git")
        doc["src_worktree_bytes"] = tree_bytes(args.src, skip_git=True)
    else:
        doc["src_head"] = None
        doc["src_head_matches_pin"] = None

    version = run_cmd([str(args.bin), "--version"], work, env, args.timeout)
    doc["version_output"] = ((version.get("stdout") or "") + (version.get("stderr") or "")).strip()[:200]
    doc["version"] = version_of(doc["version_output"])
    doc["version_ok"] = doc["version"] == VERSION
    if version.get("exit") != 0 or not doc["version_ok"]:
        doc["reason"] = "version pin mismatch"
        return finish(0)

    init_target = corpus
    if not under(init_target, work):
        doc["reason"] = "init target escaped the work dir"
        return finish(0)
    init = run_cmd(
        [
            str(args.bin),
            "--palace",
            str(palace),
            "init",
            str(init_target),
            "--yes",
            "--no-llm",
            "--embedding-model",
            "minilm",
        ],
        work,
        env,
        max(args.timeout, 600),
    )
    doc["init_exit"] = init.get("exit")
    doc["init_seconds"] = init.get("seconds")
    doc["init_target"] = str(init_target)
    if init.get("exit") != 0:
        doc["reason"] = "init failed"
        doc["init_stderr"] = init.get("stderr")
        return finish(0)

    drawers = 0
    retries = 0
    mine_seconds = 0.0
    wings = []
    for wing in ("handoff", "ranking"):
        target = corpus / wing
        if not under(target, work):
            doc["reason"] = "mine target escaped the work dir"
            return finish(0)
        wings.append(str(target))
        args_mine = [str(args.bin), "--palace", str(palace), "mine", str(target), "--wing", wing]
        mined = run_cmd(args_mine, work, env, max(args.timeout, 600))
        mine_seconds += float(mined.get("seconds") or 0)
        if mined.get("exit") != 0:
            retries += 1
            mined = run_cmd(args_mine, work, env, max(args.timeout, 600))
            mine_seconds += float(mined.get("seconds") or 0)
        filed = parse_drawers(mined.get("combined") or "")
        if mined.get("exit") != 0 or filed is None:
            doc["mine_retries"] = retries
            doc["mine_seconds"] = round(mine_seconds, 3)
            doc["reason"] = "mine failed after one retry: " + wing
            doc["mine_stderr"] = mined.get("stderr")
            return finish(0)
        drawers += filed
    doc["mine_targets"] = wings
    doc["mine_retries"] = retries
    doc["mine_seconds"] = round(mine_seconds, 3)
    doc["drawers_filed"] = drawers

    bodies = {fact["id"]: body for fact, body, _row in prepared}
    other = {"handoff": "ranking", "ranking": "handoff"}
    top1 = 0
    top5 = 0
    agree = 0
    leaks = 0
    mismatches = 0
    scoped_results = 0
    kept = 0
    walk_hits = 0
    search_seconds = 0.0
    questions = []
    for fact, _body, row in prepared:
        expected = fact["id"] + ".md"
        walk = file_walk_winner(fact["question"], bodies)
        first = search_once(args.bin, palace, fact["question"], None, work, env, args.timeout)
        second = search_once(args.bin, palace, fact["question"], None, work, env, args.timeout)
        wrong = search_once(args.bin, palace, fact["question"], other[fact["wing"]], work, env, args.timeout)
        own = search_once(args.bin, palace, fact["question"], fact["wing"], work, env, args.timeout)
        for part in (first, second, wrong, own):
            search_seconds += float(part.get("seconds") or 0)
        first_src = first["hits"][0]["source"] if first["hits"] else None
        second_src = second["hits"][0]["source"] if second["hits"] else None
        sources = [hit["source"] for hit in first["hits"]]
        hit1 = first_src == expected
        hit5 = expected in sources
        same = first_src == second_src
        leak = any(hit["source"] == expected for hit in wrong["hits"])
        mismatch = sum(1 for hit in wrong["hits"] if hit["wing"] != other[fact["wing"]])
        keep = any(hit["source"] == expected for hit in own["hits"])
        top1 += int(hit1)
        top5 += int(hit5)
        agree += int(same)
        leaks += int(leak)
        mismatches += mismatch
        scoped_results += len(wrong["hits"])
        kept += int(keep)
        walk_hits += int(walk == fact["id"])
        questions.append(
            {
                "id": fact["id"],
                "wing": fact["wing"],
                "source": fact["source"],
                "anchor_found": True,
                "bytes": row["bytes"],
                "question": fact["question"],
                "top1": hit1,
                "top5": hit5,
                "top_source": first_src,
                "repeat_top_source": second_src,
                "repeat_agree": same,
                "file_walk_top": walk,
                "file_walk_hit": walk == fact["id"],
                "scoped_leak": leak,
                "scoped_kept": keep,
                "search_exit": first.get("exit"),
            }
        )
    doc["questions"] = questions
    doc["top1_hits"] = top1
    doc["top5_hits"] = top5
    doc["repeat_agreement"] = agree
    doc["file_walk_top1"] = walk_hits
    doc["scoped_expected_leaks"] = leaks
    doc["scoped_wing_mismatches"] = mismatches
    doc["scoped_results"] = scoped_results
    doc["scoped_kept"] = kept
    doc["search_seconds"] = round(search_seconds, 3)
    doc["scored"] = len(prepared)
    chroma = home / ".cache" / "chroma"
    doc["chroma_bytes"] = tree_bytes(chroma)
    doc["palace_bytes"] = tree_bytes(palace)
    doc["status"] = "scored"
    doc["reason"] = None
    return finish(0)


if __name__ == "__main__":
    raise SystemExit(main())
