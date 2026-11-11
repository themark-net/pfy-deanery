#!/usr/bin/env python3
"""Read-only Neuronto tool search against this catalog.

Asks https://neuronto.com/tools for three catalog-capability queries.
A hit is on intent when every query word (routing stems to "rout",
model also matches the French spelling) appears in the tool, server,
or description. A hit is already cataloged when its server or tool
normalizes to a stage slug or card name, or when a github.com
owner/repo in the hit equals one on a stage card or in TOOLS.md.

Does not install, clone, submit, or call any listed tool.
Writes results.json and receipt.json beside this file.
--self-check reads fixtures/intent.json and does not use the network.

Exit 0: three queries parsed, or the self-check matched.
Exit 1: a response parsed and the shape was wrong, or the self-check missed.
Exit 2: a request failed before a comparable body.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PIN = "09d4fa8b0576981d93ae608ff4509ded4ef2df2e"
REPO = "neuronto/agentic-resource-discovery"
QUERIES = ("code review", "memory", "local model routing")
LIMIT = 8
THRESHOLD = 1
STEMS = {
    "model": ("model", "modèle", "modele"),
    "routing": ("rout",),
}
GITHUB_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", re.I)
UA = {"User-Agent": "pfy-eval-neuronto", "Accept": "application/json"}


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def content_words(query: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9]+", query.lower()) if len(word) >= 3]


def on_intent(query: str, tool: str, server: str, description: str) -> tuple[bool, list[str]]:
    blob = f"{tool}\n{server}\n{description}".lower()
    missed = []
    for word in content_words(query):
        stems = STEMS.get(word, (word,))
        if not any(stem in blob for stem in stems):
            missed.append(word)
    return not missed, missed


def github_repos(text: str) -> set[str]:
    found = set()
    for owner_repo in GITHUB_RE.findall(text or ""):
        owner, repo = owner_repo.split("/", 1)
        repo = repo.removesuffix(".git")
        found.add(f"{owner.lower()}/{repo.lower()}")
    return found


def load_catalog(root: Path) -> tuple[set[str], set[str]]:
    names: set[str] = set()
    repos: set[str] = set()
    stages = root / "data" / "stages"
    for path in stages.glob("*.json"):
        if path.name.startswith("_"):
            continue
        names.add(path.stem)
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(card, dict) and isinstance(card.get("name"), str):
            names.add(norm(card["name"]))
        repos.update(github_repos(path.read_text(encoding="utf-8", errors="replace")))
    tools = root / "TOOLS.md"
    if tools.is_file():
        text = tools.read_text(encoding="utf-8", errors="replace")
        repos.update(github_repos(text))
        for raw in re.findall(r"\|\s+\*\*([^*|]+)\*\*", text):
            names.add(norm(raw))
    names.discard("")
    return names, repos


def catalog_match(hit: dict, names: set[str], repos: set[str]) -> str | None:
    tool = str(hit.get("tool") or "")
    server = str(hit.get("server") or "")
    blob = " ".join(str(hit.get(key) or "") for key in ("tool", "server", "identifier", "endpoint", "description"))
    shared = github_repos(blob) & repos
    if shared:
        return "github:" + sorted(shared)[0]
    for label, value in (("server", server), ("tool", tool)):
        token = norm(value)
        if token and token in names:
            return f"{label}:{token}"
    return None


def get_json(url: str, timeout: float = 30.0) -> tuple[int, object]:
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"http {exc.code} for {url}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"fetch failed for {url}: {type(exc).__name__}") from exc
    try:
        return status, json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"not json from {url}") from exc


def summarize_query(query: str, payload: object, names: set[str], repos: set[str]) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError(f"{query}: results is not a list")
    rows = []
    novel_servers: set[str] = set()
    on_servers: set[str] = set()
    off = 0
    catalog_hits = 0
    for item in payload["results"]:
        if not isinstance(item, dict):
            raise ValueError(f"{query}: a result is not an object")
        tool = str(item.get("tool") or "")
        server = str(item.get("server") or "")
        description = str(item.get("description") or "")
        identifier = str(item.get("identifier") or "")
        intent, missed = on_intent(query, tool, server, description)
        match = catalog_match(item, names, repos)
        if match:
            catalog_hits += 1
        if intent:
            on_servers.add(identifier or server or tool)
            if not match:
                novel_servers.add(identifier or server or tool)
        else:
            off += 1
        rows.append({
            "tool": tool,
            "server": server,
            "identifier": identifier,
            "score": item.get("score"),
            "verified": item.get("verified"),
            "on_intent": intent,
            "missed": missed,
            "in_catalog": match is not None,
            "catalog_match": match,
        })
    return {
        "q": query,
        "returned": len(rows),
        "on_intent": sum(1 for row in rows if row["on_intent"]),
        "off_intent": off,
        "catalog_hits": catalog_hits,
        "novel_on_intent_servers": len(novel_servers),
        "hits": rows,
        "_novel": novel_servers,
        "_on": on_servers,
    }


def github_pin() -> dict:
    status, repo = get_json(f"https://api.github.com/repos/{REPO}")
    _, pin = get_json(f"https://api.github.com/repos/{REPO}/commits/{PIN}")
    _, main = get_json(f"https://api.github.com/repos/{REPO}/commits/main")
    if not isinstance(repo, dict) or not isinstance(pin, dict) or not isinstance(main, dict):
        raise ValueError("github metadata was not an object")
    license_obj = repo.get("license") if isinstance(repo.get("license"), dict) else {}
    pin_sha = str(pin.get("sha") or "")
    main_sha = str(main.get("sha") or "")
    return {
        "http_status": status,
        "license": license_obj.get("spdx_id"),
        "repo_kb": repo.get("size"),
        "stars": repo.get("stargazers_count"),
        "default_branch": repo.get("default_branch"),
        "pin": pin_sha,
        "main_sha": main_sha,
        "pin_matches_main": pin_sha == PIN and main_sha == PIN,
    }


def self_check() -> int:
    fixture = json.loads((HERE / "fixtures" / "intent.json").read_text(encoding="utf-8"))
    failed = 0
    for case in fixture["cases"]:
        intent, missed = on_intent(case["query"], case["tool"], case["server"], case["description"])
        if intent != case["on_intent"]:
            print(f"miss {case['tool']}: on_intent={intent} missed={missed}")
            failed += 1
    names = {"ollama", "litellm"}
    repos = {"ollama/ollama", "berriai/litellm"}
    known = catalog_match(
        {"tool": "list", "server": "Ollama", "description": "local models", "identifier": "", "endpoint": ""},
        names,
        repos,
    )
    unknown = catalog_match(
        {
            "tool": "memory_search",
            "server": "WorkingMemory",
            "description": "Search session memory.",
            "identifier": "urn:air:example:mcp:memory",
            "endpoint": "https://example.invalid/mcp",
        },
        names,
        repos,
    )
    linked = catalog_match(
        {
            "tool": "route",
            "server": "proxy",
            "description": "see https://github.com/BerriAI/litellm",
            "identifier": "",
            "endpoint": "",
        },
        names,
        repos,
    )
    if known != "server:ollama" or unknown is not None or linked != "github:berriai/litellm":
        print(f"catalog match known={known} unknown={unknown} linked={linked}")
        failed += 1
    if failed:
        return 1
    print("self-check ok")
    return 0


def main() -> int:
    if "--self-check" in sys.argv:
        return self_check()
    names, repos = load_catalog(ROOT)
    trace = Path(sys.argv[sys.argv.index("--trace") + 1]) if "--trace" in sys.argv else None
    if trace is not None:
        trace.mkdir(parents=True, exist_ok=True)
    try:
        pin = github_pin()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    summaries = []
    novel: set[str] = set()
    on_servers: set[str] = set()
    for query in QUERIES:
        url = "https://neuronto.com/tools?" + urllib.parse.urlencode({"q": query, "limit": LIMIT})
        try:
            status, payload = get_json(url)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if trace is not None:
            slug = query.replace(" ", "-")
            (trace / f"tools-{slug}.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        try:
            summary = summarize_query(query, payload, names, repos)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        summary["status"] = status
        novel |= summary.pop("_novel")
        on_servers |= summary.pop("_on")
        summaries.append(summary)
    value = len(novel)
    results = {
        "pin": PIN,
        "pin_matches_main": pin["pin_matches_main"],
        "main_sha": pin["main_sha"],
        "license": pin["license"],
        "repo_kb": pin["repo_kb"],
        "stars": pin["stars"],
        "installed": False,
        "catalog_names": len(names),
        "catalog_repos": len(repos),
        "limit": LIMIT,
        "queries": summaries,
        "on_intent_servers": len(on_servers),
        "on_intent_novel_servers": value,
        "off_intent_hits": sum(item["off_intent"] for item in summaries),
        "catalog_hits": sum(item["catalog_hits"] for item in summaries),
        "threshold": THRESHOLD,
    }
    text = json.dumps(results, indent=2, ensure_ascii=False) + "\n"
    (HERE / "results.json").write_text(text, encoding="utf-8")
    receipt = {
        "slug": "neuronto-ard-registry",
        "run_kind": "eval-probe",
        "outcome": "measured" if value >= THRESHOLD else "below-threshold",
        "installed": False,
        "pin": PIN,
        "pin_matches_main": pin["pin_matches_main"],
        "license": pin["license"],
        "repo_kb": pin["repo_kb"],
        "metric": "on_intent_novel_servers",
        "value": value,
        "threshold": THRESHOLD,
        "queries": list(QUERIES),
    }
    (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(
        f"on_intent_novel_servers={value} threshold={THRESHOLD} "
        f"off_intent_hits={results['off_intent_hits']} catalog_hits={results['catalog_hits']} "
        f"pin_matches_main={pin['pin_matches_main']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(1)
