#!/usr/bin/env python3
"""Offline probe of openlore 3.3.1 on this repo.

The clone and the index stay under ~/.cache/pfy/tools/openlore/probe.
This script never runs install, connect, setup, or embed.
It writes results.json beside itself.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "results.json"
CACHE = Path("/home/mark/.cache/pfy/tools/openlore")
PREFIX = CACHE / "prefix"
CLI = PREFIX / "node_modules" / "openlore" / "dist" / "cli" / "index.js"
CLONE = CACHE / "probe" / "repo"
NODE = "/usr/bin/node"
GIT = "/usr/bin/git"

# Same first-parent window as eval/ev1107/chiasmus/results.json.
CHIASMUS = [
    "56f6df154eeebf29be90c6290a0a28a917e5d4bb",
    "9d3688718e964dd9e26df465f22ce61cf31e8a0b",
    "1868e5d1b2c5f8c042ffef24c67153c61b0b2a3c",
    "914b11c8a2c2fc55407874342ee5789ed223a085",
    "9bfc82fcf66c6738b5443bc9972ce7e6e49f251e",
    "25e488764894eb314424660b95ece131ffc9898d",
    "ba18f7cc7947f88f19564ea585ccf68c7276073c",
    "31c373ba1c77588f0bdbb875383d7185ca3be3cb",
    "dd861e01cc8ba33c1547e0e45c40e4623bc9dd1a",
    "79c083e9e53a4302ed30188d40fc29d445140ab6",
]

CALLER_MARKS = (
    "catalog_check.py",
    "test_stage_registry.py",
    "catalog_stage_eval.py",
    "test_catalog_stage_eval.py",
    "test_voice_stage0_ref.py",
    "pfy_catalog_ask_queue_209.py",
)

DOC = {
    "load_stages": (
        "Old monolith shape of stage cards",
        "load_stages",
    ),
    "write_tool": (
        "Write one tool file for a stage card",
        "write_tool",
    ),
    "pipeline_role_hits": (
        "Why a card covers CI testing or review",
        "pipeline_role_hits",
    ),
}


def env() -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(CACHE / "home"),
        "XDG_CONFIG_HOME": str(CACHE / "xdg-config"),
        "XDG_CACHE_HOME": str(CACHE / "xdg-cache"),
        "XDG_DATA_HOME": str(CACHE / "xdg-data"),
        "TMPDIR": str(CACHE / "tmp"),
        "npm_config_cache": str(CACHE / "npm-cache"),
        "OPENLORE_NO_UPDATE_NOTIFIER": "1",
        "NO_UPDATE_NOTIFIER": "1",
        "OPENLORE_TELEMETRY": "0",
        "OPENLORE_NO_AUTO_HEAP": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.autocrlf",
        "GIT_CONFIG_VALUE_0": "false",
    }


def run(argv: list[str], cwd: Path, timeout: int, extra: dict | None = None) -> dict:
    e = env()
    if extra:
        e.update(extra)
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=e,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        timed_out = False
        code = proc.returncode
        out, err = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        code = None
        out = exc.stdout or ""
        err = exc.stderr or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
    return {
        "argv": argv,
        "seconds": round(time.monotonic() - t0, 3),
        "code": code,
        "timed_out": timed_out,
        "stdout": out,
        "stderr": err,
    }


def git(argv: list[str], timeout: int = 120) -> dict:
    return run([GIT, "-C", str(CLONE), *argv], CLONE, timeout)


def ol(argv: list[str], timeout: int, extra: dict | None = None) -> dict:
    return run([NODE, str(CLI), *argv], CLONE, timeout, extra)


def parse_json(text: str) -> dict | None:
    text = text.strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None


def is_test_path(path: str) -> bool:
    name = path.replace("\\", "/")
    if "/tests/" in f"/{name}" or name.startswith("tests/"):
        return True
    base = name.rsplit("/", 1)[-1]
    return base.startswith("test_") and base.endswith(".py")


def sig_of(node: ast.AST) -> tuple:
    if isinstance(node, ast.ClassDef):
        return ("class",)
    assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    args = node.args
    pos = list(args.posonlyargs) + list(args.args)
    n_plain = len(pos) - len(args.defaults)
    parts: list[tuple] = []
    for i, arg in enumerate(pos):
        parts.append((arg.arg, "pos", i >= n_plain))
    if args.vararg:
        parts.append((args.vararg.arg, "vararg", True))
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        parts.append((arg.arg, "kwonly", default is not None))
    if args.kwarg:
        parts.append((args.kwarg.arg, "kwarg", True))
    return tuple(parts)


def public_map(src: str) -> dict[str, tuple] | None:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    out: dict[str, tuple] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name.startswith("_"):
            continue
        out[node.name] = sig_of(node)
    return out


def file_breaks(before: str, after: str) -> list[str]:
    old = public_map(before)
    new = public_map(after)
    if old is None or new is None:
        return []
    found: list[str] = []
    for name, sig in old.items():
        if name not in new:
            found.append(f"removed {name}")
            continue
        if sig == ("class",) or new[name] == ("class",):
            continue
        if sig != new[name]:
            # Optional suffix adds are compatible. Anything else is a break.
            if _optional_suffix(sig, new[name]):
                continue
            found.append(f"signature {name}")
    return found


def _optional_suffix(old: tuple, new: tuple) -> bool:
    if len(new) < len(old):
        return False
    if new[: len(old)] != old:
        return False
    return all(part[2] for part in new[len(old) :])


def show(rev: str, path: str) -> str:
    proc = git(["show", f"{rev}:{path}"])
    if proc["code"] != 0:
        return ""
    return proc["stdout"]


def commit_breaks(sha: str) -> dict:
    parent = git(["rev-parse", f"{sha}^"])["stdout"].strip()
    names = git(["diff", "--name-only", parent, sha])["stdout"].splitlines()
    breaks: list[dict] = []
    py = []
    for path in names:
        if not path.endswith(".py") or is_test_path(path):
            continue
        py.append(path)
        found = file_breaks(show(parent, path), show(sha, path))
        if found:
            breaks.append({"file": path, "breaks": found})
    return {
        "sha": sha,
        "parent": parent,
        "py_files": py,
        "true_breaking": bool(breaks),
        "breaks": breaks,
    }


def ascii_tail(text: str, limit: int = 500) -> str:
    clean = text.encode("ascii", "replace").decode("ascii")
    return clean[-limit:]


def trim_certify(data: dict | None, proc: dict) -> dict:
    if data is None:
        return {
            "seconds": proc["seconds"],
            "code": proc["code"],
            "timed_out": proc["timed_out"],
            "parse_error": True,
            "stderr_tail": ascii_tail(proc["stderr"]),
            "stdout_tail": ascii_tail(proc["stdout"]),
        }
    changes = []
    for change in (data.get("changes") or [])[:40]:
        if not isinstance(change, dict):
            continue
        changes.append(
            {
                "class": change.get("class"),
                "name": change.get("name"),
                "file": change.get("file"),
                "changeKind": change.get("changeKind"),
                "reasons": (change.get("reasons") or [])[:4],
                "ruleCodes": change.get("ruleCodes") or [],
            }
        )
    consumers = []
    for item in (data.get("breaking") or [])[:12]:
        if not isinstance(item, dict):
            continue
        named = []
        for consumer in (item.get("consumers") or [])[:12]:
            if isinstance(consumer, dict):
                named.append({"name": consumer.get("name"), "file": consumer.get("file")})
        consumers.append(
            {
                "name": item.get("name"),
                "file": item.get("file"),
                "consumers": named,
                "truncated": item.get("consumersTruncated"),
            }
        )
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    return {
        "seconds": proc["seconds"],
        "code": proc["code"],
        "timed_out": proc["timed_out"],
        "overall": data.get("overall"),
        "error": data.get("error"),
        "status": data.get("status"),
        "summary": {
            "breaking": summary.get("breaking"),
            "potentiallyBreaking": summary.get("potentiallyBreaking"),
            "nonBreaking": summary.get("nonBreaking"),
        },
        "suggestedBump": data.get("suggestedBump"),
        "changes": changes,
        "breaking": consumers,
        "stderr_tail": ascii_tail(proc["stderr"], 400),
    }


def certify(base: str | None = "HEAD") -> dict:
    argv = ["certify-public-surface", "--json"]
    if base:
        argv.extend(["--base", base])
    proc = ol(argv, 180)
    return trim_certify(parse_json(proc["stdout"]), proc)


def orient(task: str) -> dict:
    proc = ol(["orient", "--json", "--limit", "5", "--task", task], 90)
    data = parse_json(proc["stdout"]) or {}
    names = []
    for item in (data.get("relevantFunctions") or [])[:5]:
        if isinstance(item, dict):
            names.append(item.get("name"))
    return {
        "task": task,
        "seconds": proc["seconds"],
        "code": proc["code"],
        "timed_out": proc["timed_out"],
        "names": names,
        "error": data.get("error"),
        "stderr_tail": ascii_tail(proc["stderr"], 300),
    }


def save(doc: dict) -> None:
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def du(path: Path) -> dict:
    apparent = run(["du", "-sb", str(path)], CACHE, 60)
    alloc = run(["du", "-sh", str(path)], CACHE, 60)
    return {
        "bytes": int(apparent["stdout"].split()[0]) if apparent["code"] == 0 and apparent["stdout"].split() else None,
        "human": alloc["stdout"].split()[0] if alloc["code"] == 0 and alloc["stdout"].split() else None,
    }


def restore_head(head: str) -> None:
    git(["checkout", "--detach", "--force", head], 180)
    git(["reset", "--hard", head], 180)
    git(["clean", "-fd", "-e", ".openlore", "-e", "openspec"], 180)


def apply_commit(sha: str, parent: str) -> None:
    git(["checkout", "--detach", "--force", sha], 180)
    git(["reset", "--mixed", parent], 180)


def replace_once(rel: str, old: str, new: str) -> None:
    path = CLONE / rel
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{rel}: anchor count is {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def external_caller(cert: dict) -> bool:
    for item in cert.get("breaking") or []:
        if item.get("name") != "load_stages":
            continue
        for consumer in item.get("consumers") or []:
            file = consumer.get("file") or ""
            if file.endswith("stage_registry.py"):
                continue
            if any(mark in file or mark in (consumer.get("name") or "") for mark in CALLER_MARKS):
                return True
    return False


def test_paths(blob: object) -> list[str]:
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str) and "tests/test_" in node and node.endswith(".py"):
            # Keep the path tail when a string embeds a path.
            start = node.find("tests/test_")
            tail = node[start:].split()[0].rstrip("\",'")
            if tail not in found:
                found.append(tail)

    walk(blob)
    return found


def main() -> int:
    if (ROOT / "tmp" / "STOP").exists():
        raise SystemExit("tmp/STOP exists")
    for path in (CACHE / "home", CACHE / "tmp", CACHE / "xdg-config", CACHE / "xdg-cache", CACHE / "xdg-data"):
        path.mkdir(parents=True, exist_ok=True)
    if not CLI.is_file():
        raise SystemExit(f"missing CLI {CLI}")

    doc: dict = {"pin": {}, "phases": {}}
    pkg = json.loads((PREFIX / "node_modules" / "openlore" / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((PREFIX / "package-lock.json").read_text(encoding="utf-8"))
    locked = lock["packages"]["node_modules/openlore"]
    doc["pin"] = {
        "version": pkg.get("version"),
        "license": pkg.get("license"),
        "engines": pkg.get("engines"),
        "integrity": locked.get("integrity"),
        "resolved": locked.get("resolved"),
        "tag": "v3.3.1",
        "commit": "f33d3b2fbcd34380dfcb5925d966eccd080c2383",
        "node": run([NODE, "-v"], CACHE, 20)["stdout"].strip(),
        "prefix": du(PREFIX),
        "npm_cache": du(CACHE / "npm-cache"),
        "ignore_scripts": True,
        "no_embed": True,
    }
    watched = {}
    for label, path in (
        ("real_openlore", Path("/home/mark/.openlore")),
        ("real_pi", Path("/home/mark/.pi/agent/extensions")),
    ):
        watched[label] = path.exists()
    doc["watched_before"] = watched
    save(doc)

    if CLONE.exists():
        shutil.rmtree(CLONE)
    CLONE.parent.mkdir(parents=True, exist_ok=True)
    cloned = run([GIT, "clone", "--shared", str(ROOT), str(CLONE)], CACHE, 180)
    doc["phases"]["clone"] = {
        "seconds": cloned["seconds"],
        "code": cloned["code"],
        "stderr_tail": ascii_tail(cloned["stderr"], 300),
    }
    if cloned["code"] != 0:
        save(doc)
        return 1
    head = git(["rev-parse", "HEAD"])["stdout"].strip()
    doc["head"] = head
    save(doc)

    init = ol(["-q", "init"], 120)
    doc["phases"]["init"] = {
        "seconds": init["seconds"],
        "code": init["code"],
        "stderr_tail": ascii_tail(init["stderr"], 400),
        "stdout_tail": ascii_tail(init["stdout"], 400),
    }
    status = git(["status", "--porcelain"])
    doc["phases"]["init"]["status"] = status["stdout"].splitlines()[:30]
    save(doc)
    if init["code"] != 0:
        return 1

    analyze = ol(["analyze", "--no-embed", "--force"], 900)
    if analyze["code"] != 0 or analyze["timed_out"]:
        analyze = ol(
            ["analyze", "--no-embed", "--force"],
            900,
            {"OPENLORE_NO_AUTO_HEAP": "1", "OPENLORE_HEAP_MB": "8192"},
        )
        doc["phases"]["analyze_retry"] = True
    doc["phases"]["analyze"] = {
        "seconds": analyze["seconds"],
        "code": analyze["code"],
        "timed_out": analyze["timed_out"],
        "stderr_tail": ascii_tail(analyze["stderr"], 400),
        "stdout_tail": ascii_tail(analyze["stdout"], 700),
    }
    index = CLONE / ".openlore"
    doc["phases"]["analyze"]["index"] = du(index) if index.exists() else None
    save(doc)
    if analyze["code"] != 0 or analyze["timed_out"]:
        return 1

    # Index presence, then a phrase that does not contain the symbol name.
    orients = []
    for key, (phrase, symbol) in DOC.items():
        by_name = orient(symbol)
        by_phrase = orient(phrase)
        orients.append(
            {
                "symbol": symbol,
                "by_name": by_name,
                "by_name_hit": symbol in by_name["names"],
                "by_phrase": by_phrase,
                "by_phrase_hit": symbol in by_phrase["names"],
            }
        )
        doc["orient"] = orients
        save(doc)

    clean = certify("HEAD")
    doc["clean"] = clean
    save(doc)

    # Historical window: the chiasmus 10, plus up to 5 real breaks from the last 60.
    selected: list[dict] = []
    seen = set()
    log = git(["log", "--first-parent", "-60", "--format=%H"])["stdout"].split()
    extra_breaks = []
    for sha in log:
        if sha in CHIASMUS:
            continue
        info = commit_breaks(sha)
        if info["true_breaking"]:
            extra_breaks.append(info)
        if len(extra_breaks) >= 5:
            break
    ordered = []
    for sha in CHIASMUS + [row["sha"] for row in extra_breaks]:
        if sha in seen:
            continue
        if git(["cat-file", "-e", f"{sha}^{{commit}}"])["code"] != 0:
            continue
        seen.add(sha)
        ordered.append(sha)

    rows = []
    for sha in ordered:
        info = commit_breaks(sha)
        apply_commit(sha, info["parent"])
        cert = certify("HEAD")
        overall = cert.get("overall")
        # potentially-breaking is not a strict pass. A missing overall is not one either.
        strict = (
            cert.get("code") == 0
            and overall in ("breaking", "non-breaking")
            and (overall == "breaking") == info["true_breaking"]
        )
        row = {
            **info,
            "overall": overall,
            "summary": cert.get("summary"),
            "seconds": cert.get("seconds"),
            "code": cert.get("code"),
            "timed_out": cert.get("timed_out"),
            "error": cert.get("error"),
            "strict": strict,
            "tool_breaks": [
                {"name": c.get("name"), "file": c.get("file"), "rules": c.get("ruleCodes")}
                for c in cert.get("changes") or []
                if c.get("class") == "breaking"
            ][:12],
        }
        rows.append(row)
        doc["history"] = rows
        save(doc)
        restore_head(head)

    # Planted edits on the restored HEAD. Ground truth is checked on the file first.
    planted = []

    def plant(name: str, rel: str, old: str, new: str, expect: str | None) -> None:
        replace_once(rel, old, new)
        text = (CLONE / rel).read_text(encoding="utf-8")
        # Ground truth uses the committed file as before and the worktree as after.
        parent_text = show("HEAD", rel)
        truth = file_breaks(parent_text, text)
        cert = certify("HEAD")
        hit = None if expect is None else cert.get("overall") == expect
        if name == "required_param":
            caller = external_caller(cert)
        else:
            caller = None
        planted.append(
            {
                "name": name,
                "expect": expect,
                "truth": truth,
                "hit": hit,
                "caller": caller,
                "cert": cert,
            }
        )
        doc["planted"] = planted
        save(doc)
        git(["checkout", "--", rel])

    plant(
        "required_param",
        "pfylib/stage_registry.py",
        "def load_stages(root: str | os.PathLike) -> dict:\n",
        "def load_stages(root: str | os.PathLike, lane: str) -> dict:\n",
        "breaking",
    )
    # blast-radius while the required edit is NOT still applied. Re-apply for that one call.
    replace_once(
        "pfylib/stage_registry.py",
        "def load_stages(root: str | os.PathLike) -> dict:\n",
        "def load_stages(root: str | os.PathLike, lane: str) -> dict:\n",
    )
    blast = ol(["blast-radius", "--base", "HEAD", "--json"], 180)
    blast_json = parse_json(blast["stdout"])
    select = run(
        ["/usr/bin/python3", str(ROOT / "scripts" / "test_select.py"), "--paths", "pfylib/stage_registry.py"],
        ROOT,
        120,
    )
    select_json = parse_json(select["stdout"])
    doc["blast"] = {
        "seconds": blast["seconds"],
        "code": blast["code"],
        "timed_out": blast["timed_out"],
        "tests": test_paths(blast_json),
        "error": None if blast_json is None else blast_json.get("error"),
        "top_keys": sorted(blast_json.keys())[:20] if isinstance(blast_json, dict) else [],
        "stderr_tail": ascii_tail(blast["stderr"], 400),
    }
    doc["test_select"] = {
        "seconds": select["seconds"],
        "code": select["code"],
        "mode": None if not select_json else select_json.get("mode"),
        "modules": None if not select_json else select_json.get("modules"),
        "reason": None if not select_json else select_json.get("reason"),
    }
    git(["checkout", "--", "pfylib/stage_registry.py"])
    save(doc)

    plant(
        "optional_param",
        "pfylib/stage_registry.py",
        "def load_stages(root: str | os.PathLike) -> dict:\n",
        'def load_stages(root: str | os.PathLike, lane: str = "") -> dict:\n',
        "non-breaking",
    )
    plant(
        "docstring",
        "pfylib/stage_registry.py",
        '"""Old monolith shape: registry fields, computed last_updated, tools by name."""',
        '"""Old monolith shape: registry fields, computed last_updated, tools by name. Probe note."""',
        "non-breaking",
    )
    plant(
        "export_removed",
        "pfylib/stage_registry.py",
        "def load_stages(root: str | os.PathLike) -> dict:\n",
        "def _load_stages(root: str | os.PathLike) -> dict:\n",
        "breaking",
    )
    # None: a method is outside the column-0 surface. hit stays null.
    # method_overall records whether the break was visible.
    plant(
        "method_required_param",
        "pfylib/build_phase_clock.py",
        "    def phase(self, name: str):\n",
        "    def phase(self, name: str, lane: str):\n",
        None,
    )

    watched_after = {}
    for label, path in (
        ("real_openlore", Path("/home/mark/.openlore")),
        ("real_pi", Path("/home/mark/.pi/agent/extensions")),
    ):
        watched_after[label] = path.exists()
    doc["watched_after"] = watched_after
    home_entries = sorted(p.name for p in (CACHE / "home").iterdir())
    doc["redirected_home"] = home_entries
    porcelain = git(["status", "--porcelain"])["stdout"].splitlines()
    doc["clone_status_tail"] = porcelain[:40]

    hist = doc.get("history") or []
    planted_hits = [row for row in planted if row["name"] != "method_required_param"]
    doc["score"] = {
        "orient_name": sum(1 for row in orients if row["by_name_hit"]),
        "orient_name_n": len(orients),
        "orient_phrase": sum(1 for row in orients if row["by_phrase_hit"]),
        "orient_phrase_n": len(orients),
        "planted_contract": sum(1 for row in planted_hits if row["hit"]),
        "planted_contract_n": len(planted_hits),
        "planted_caller": next((row["caller"] for row in planted if row["name"] == "required_param"), None),
        "method_overall": next((row["cert"].get("overall") for row in planted if row["name"] == "method_required_param"), None),
        "history_strict": sum(1 for row in hist if row.get("strict")),
        "history_n": len(hist),
        "history_true_breaks": sum(1 for row in hist if row.get("true_breaking")),
        "history_caught": sum(1 for row in hist if row.get("true_breaking") and row.get("overall") == "breaking"),
        "history_false_breaking": sum(
            1 for row in hist if (not row.get("true_breaking")) and row.get("overall") == "breaking"
        ),
        "history_conservative": sum(
            1
            for row in hist
            if (not row.get("true_breaking")) and row.get("overall") == "potentially-breaking"
        ),
        "analyze_seconds": doc["phases"]["analyze"]["seconds"],
        "prefix_bytes": doc["pin"]["prefix"]["bytes"],
    }
    save(doc)
    print(json.dumps(doc["score"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
