#!/usr/bin/env python3
"""Offline taste-skill probe for the operator page. No network and no model.

Measures app-mode lint on gui/operator/frontend against planted pages, a seeded
app draw, and one headless inspect when Chrome is requested. Writes JSON and
exits 1 when the planted page is not separated from the clean page, or when
draw history lands in HOME/.taste-skill. Exit 2 when lint cannot start.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
from collections import Counter
from pathlib import Path

PIN = "6010f91a9935f1c167dfc500fb1a475681892e6b"
DRAW_KIND = "devtools"
DRAW_BRIEF = "native operator window for a local agent harness"
DRAW_THEME = "dark"
DRAW_SEED = "7"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _tree_bytes(root: Path) -> int:
    total = 0
    if not root.is_dir():
        return 0
    for path in root.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        total += path.stat().st_size
    return total


def _rel(path: Path, repo: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path)


def _listing(path: Path) -> list[str] | None:
    if not path.exists():
        return None
    if path.is_file():
        return [path.name]
    return sorted(str(item.relative_to(path)) for item in path.rglob("*") if item.is_file())


def _run(args: list[str], cwd: Path, env: dict, timeout: float) -> dict:
    started = time.perf_counter()
    proc = subprocess.Popen(
        args,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate()
        code = 124
    return {
        "rc": code,
        "seconds": round(time.perf_counter() - started, 4),
        "stdout": stdout or "",
        "stderr": stderr or "",
    }


def _as_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _summarize(payload, stdout: str, stderr: str) -> dict:
    if not isinstance(payload, dict):
        return {
            "parse": False,
            "fail_n": None,
            "warn_n": None,
            "fail_ids": {},
            "warn_ids": {},
            "samples": [],
            "stdout_tail": stdout[-400:],
            "stderr_tail": stderr[-400:],
        }
    findings = [item for item in payload.get("findings") or [] if isinstance(item, dict)]
    fail = [item for item in findings if item.get("level") == "FAIL"]
    warn = [item for item in findings if item.get("level") == "WARN"]

    def counts(rows: list) -> dict:
        return dict(Counter(str(item.get("id")) for item in rows))

    samples = []
    for item in findings[:40]:
        samples.append(
            {
                "level": item.get("level"),
                "id": item.get("id"),
                "line": item.get("line"),
                "match": str(item.get("match") or "")[:80],
            }
        )
    return {
        "parse": True,
        "files": payload.get("files"),
        "fail_n": len(fail),
        "warn_n": len(warn),
        "fail_ids": counts(fail),
        "warn_ids": counts(warn),
        "samples": samples,
    }


def _sheet(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(body, dict):
        return None
    style = body.get("style") if isinstance(body.get("style"), dict) else {}
    shell = body.get("shell") if isinstance(body.get("shell"), dict) else {}
    screens = []
    for row in body.get("screens") or []:
        if not isinstance(row, dict):
            continue
        pattern = row.get("pattern") if isinstance(row.get("pattern"), dict) else {}
        screens.append({"name": row.get("name"), "pattern": pattern.get("id")})
    return {
        "seed": body.get("seed"),
        "style": style.get("id"),
        "shell": shell.get("id"),
        "screens": screens,
    }


def _option_ids(text: str) -> list[str]:
    ids = []
    for line in text.splitlines():
        if not line.startswith("## `"):
            continue
        end = line.find("`", 4)
        if end > 4:
            ids.append(line[4:end])
    return ids


def _child_env(home: Path, tmp: Path, history: Path, chrome: str | None) -> dict:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / "config"),
        "XDG_CACHE_HOME": str(home / "cache"),
        "XDG_DATA_HOME": str(home / "data"),
        "TMPDIR": str(tmp),
        "TASTE_SKILL_TMP": str(tmp / "taste-tmp"),
        "TASTE_SKILL_HISTORY": str(history),
        "LANG": "C.UTF-8",
        "NO_COLOR": "1",
    }
    if chrome:
        env["CHROME_PATH"] = chrome
    return env


def _lint(node: str, script: Path, target: str, app: bool, cwd: Path, env: dict) -> dict:
    args = [node, str(script), target]
    if app:
        args.append("--app")
    args.append("--json")
    ran = _run(args, cwd, env, 30)
    summary = _summarize(_as_json(ran["stdout"]), ran["stdout"], ran["stderr"])
    summary["rc"] = ran["rc"]
    summary["seconds"] = ran["seconds"]
    return summary


def _draw(node: str, script: Path, out: Path | None, options: bool, cwd: Path, env: dict) -> dict:
    args = [
        node,
        str(script),
        "--app",
        "--kind",
        DRAW_KIND,
        "--brief",
        DRAW_BRIEF,
        "--theme",
        DRAW_THEME,
        "--seed",
        DRAW_SEED,
    ]
    if options:
        args.extend(["--options", "3"])
    elif out is not None:
        args.extend(["--out", str(out)])
    ran = _run(args, cwd, env, 30)
    sheet = _sheet(out / "direction.json") if out is not None else None
    return {
        "rc": ran["rc"],
        "seconds": ran["seconds"],
        "bytes": len(ran["stdout"].encode("utf-8")),
        "sha256": hashlib.sha256(ran["stdout"].encode("utf-8")).hexdigest(),
        "option_ids": _option_ids(ran["stdout"]),
        "sheet": sheet,
        "stderr_tail": ran["stderr"][-400:],
    }


def _inspect(node: str, script: Path, html: Path, out: Path, cwd: Path, env: dict) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    ran = _run(
        [node, str(script), str(html), "--app", "--out", str(out), "--widths", "1280", "--json"],
        cwd,
        env,
        120,
    )
    payload = _as_json(ran["stdout"])
    summary = _summarize(payload, ran["stdout"], ran["stderr"])
    shots = list(out.glob("*.jpg"))
    shot_bytes = sum(path.stat().st_size for path in shots)
    for path in shots:
        path.unlink()
    summary["rc"] = ran["rc"]
    summary["seconds"] = ran["seconds"]
    summary["shots"] = len(shots)
    summary["shot_bytes"] = shot_bytes
    return summary


def _tauri_bins(repo: Path) -> list[str]:
    found = []
    root = repo / "gui" / "operator" / "src-tauri" / "target"
    if not root.is_dir():
        return found
    for path in root.rglob("pfy-operator"):
        if path.is_file():
            found.append(str(path.relative_to(repo)))
    return sorted(found)


def _prepare(home: Path, tmp: Path) -> None:
    for path in (home, home / "config", home / "cache", home / "data", tmp, tmp / "taste-tmp"):
        path.mkdir(parents=True, exist_ok=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    root = here.parents[2]
    parser = argparse.ArgumentParser(description="Probe taste-skill against the operator page.")
    parser.add_argument("--repo", type=Path, default=root)
    parser.add_argument("--node", default=os.environ.get("TASTE_NODE", "node"))
    parser.add_argument("--scripts", type=Path, required=True)
    parser.add_argument("--src", type=Path, default=None)
    parser.add_argument("--expect-pin", default="")
    parser.add_argument("--fixtures", type=Path, default=here / "fixtures")
    parser.add_argument("--operator-html", type=Path, default=None)
    parser.add_argument("--frontend", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--tmp", type=Path, required=True)
    parser.add_argument("--chrome", default="")
    parser.add_argument("--skip-inspect", action="store_true")
    parser.add_argument("--login-home", type=Path, default=Path.home())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.perf_counter()
    repo = args.repo.resolve()
    scripts = args.scripts.resolve()
    fixtures = args.fixtures.resolve()
    operator_html = (args.operator_html or (repo / "gui" / "operator" / "frontend" / "index.html")).resolve()
    frontend = (args.frontend or operator_html.parent).resolve()
    home = args.home.resolve()
    tmp = args.tmp.resolve()
    out_path = args.out.resolve()
    _prepare(home, tmp)
    # A previous run's history file steers the next seeded draw. Drop only the
    # files this probe writes so one run does not inherit another.
    for name in (
        "h-lint.json",
        "h-version.json",
        "h-opt.json",
        "h-fresh-a.json",
        "h-fresh-b.json",
        "h-shared.json",
        "h-inspect.json",
        "pin-history.json",
    ):
        stale = tmp / name
        if stale.is_file():
            stale.unlink()
    login_taste = args.login_home.resolve() / ".taste-skill"
    before_login = _listing(login_taste)

    lint_script = scripts / "lint.mjs"
    draw_script = scripts / "draw.mjs"
    inspect_script = scripts / "inspect.mjs"
    if not lint_script.is_file() or not draw_script.is_file():
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps({"error": "lint.mjs or draw.mjs missing", "scripts": str(scripts)}, indent=2) + "\n",
            encoding="utf-8",
        )
        return 2

    pin = ""
    if args.src is not None and (args.src / ".git").exists():
        pin_env = _child_env(home, tmp, tmp / "pin-history.json", None)
        pin_env["GIT_CONFIG_GLOBAL"] = os.devnull
        pin_env["GIT_CONFIG_NOSYSTEM"] = "1"
        ran = _run(["git", "-C", str(args.src), "rev-parse", "HEAD"], tmp, pin_env, 20)
        pin = ran["stdout"].strip()
        if args.expect_pin and pin != args.expect_pin:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps({"error": "pin mismatch", "pin": pin, "expect": args.expect_pin}, indent=2) + "\n",
                encoding="utf-8",
            )
            return 2

    work = tmp / "work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    cwd = work / "cwd"
    cwd.mkdir()
    def env_for(history: Path) -> dict:
        return _child_env(home, tmp, history, args.chrome or None)

    version = _run([args.node, "-p", "process.version"], cwd, env_for(tmp / "h-version.json"), 10)
    lint_rows = {
        "smoke_slop": _lint(args.node, lint_script, str(fixtures / "smoke-slop.html"), False, cwd, env_for(tmp / "h-lint.json")),
        "smoke_clean": _lint(args.node, lint_script, str(fixtures / "smoke-clean.html"), False, cwd, env_for(tmp / "h-lint.json")),
        "missing": _lint(args.node, lint_script, str(tmp / "no-such-dir"), False, cwd, env_for(tmp / "h-lint.json")),
        "operator_html": _lint(args.node, lint_script, str(operator_html), False, cwd, env_for(tmp / "h-lint.json")),
        "operator_html_app": _lint(args.node, lint_script, str(operator_html), True, cwd, env_for(tmp / "h-lint.json")),
        "operator_dir_app": _lint(args.node, lint_script, str(frontend), True, cwd, env_for(tmp / "h-lint.json")),
        "planted_slop": _lint(args.node, lint_script, str(fixtures / "operator-slop.html"), False, cwd, env_for(tmp / "h-lint.json")),
        "planted_slop_app": _lint(args.node, lint_script, str(fixtures / "operator-slop.html"), True, cwd, env_for(tmp / "h-lint.json")),
        "planted_clean": _lint(args.node, lint_script, str(fixtures / "operator-clean.html"), False, cwd, env_for(tmp / "h-lint.json")),
        "planted_clean_app": _lint(args.node, lint_script, str(fixtures / "operator-clean.html"), True, cwd, env_for(tmp / "h-lint.json")),
        "eyebrow": _lint(args.node, lint_script, str(fixtures / "operator-eyebrow.html"), False, cwd, env_for(tmp / "h-lint.json")),
        "eyebrow_app": _lint(args.node, lint_script, str(fixtures / "operator-eyebrow.html"), True, cwd, env_for(tmp / "h-lint.json")),
    }

    opt_hist = tmp / "h-opt.json"
    opt_a = _draw(args.node, draw_script, None, True, cwd, env_for(opt_hist))
    opt_b = _draw(args.node, draw_script, None, True, cwd, env_for(opt_hist))
    fresh_a_dir = work / "fresh-a"
    fresh_b_dir = work / "fresh-b"
    fresh_a = _draw(args.node, draw_script, fresh_a_dir, False, cwd, env_for(tmp / "h-fresh-a.json"))
    fresh_b = _draw(args.node, draw_script, fresh_b_dir, False, cwd, env_for(tmp / "h-fresh-b.json"))
    shared_hist = tmp / "h-shared.json"
    shared_a = _draw(args.node, draw_script, work / "shared-a", False, cwd, env_for(shared_hist))
    shared_b = _draw(args.node, draw_script, work / "shared-b", False, cwd, env_for(shared_hist))

    inspect_rows: dict = {"status": "skipped"}
    if not args.skip_inspect:
        if not inspect_script.is_file():
            inspect_rows = {"status": "skipped", "reason": "inspect.mjs missing"}
        elif not args.chrome:
            inspect_rows = {"status": "skipped", "reason": "no chrome path"}
        else:
            page_copy = work / "frontend"
            if frontend.is_dir():
                shutil.copytree(frontend, page_copy)
                page = page_copy / operator_html.name
                page_cwd = page_copy
            else:
                page = operator_html
                page_cwd = operator_html.parent
            inspect_rows = {
                "status": "ran",
                "operator_app": _inspect(args.node, inspect_script, page, work / "inspect-operator", page_cwd, env_for(tmp / "h-inspect.json")),
                "planted_slop_app": _inspect(
                    args.node,
                    inspect_script,
                    fixtures / "operator-slop.html",
                    work / "inspect-slop",
                    fixtures,
                    env_for(tmp / "h-inspect.json"),
                ),
                "planted_clean_app": _inspect(
                    args.node,
                    inspect_script,
                    fixtures / "operator-clean.html",
                    work / "inspect-clean",
                    fixtures,
                    env_for(tmp / "h-inspect.json"),
                ),
            }

    after_login = _listing(login_taste)
    home_leak = (home / ".taste-skill").exists() or before_login != after_login
    profiles = sorted(path.name for path in (tmp / "taste-tmp").glob("ad-chrome-*"))
    slop_n = lint_rows["planted_slop_app"]["fail_n"]
    clean_n = lint_rows["planted_clean_app"]["fail_n"]
    separation = None if slop_n is None or clean_n is None else slop_n - clean_n
    style_a = (fresh_a.get("sheet") or {}).get("style")
    style_b = (fresh_b.get("sheet") or {}).get("style")
    shared_style_a = (shared_a.get("sheet") or {}).get("style")
    shared_style_b = (shared_b.get("sheet") or {}).get("style")

    script_sha = {}
    for name in ("lint.mjs", "draw.mjs", "inspect.mjs"):
        path = scripts / name
        if path.is_file():
            script_sha[name] = _sha256(path)

    long_lines = 0
    if operator_html.is_file():
        long_lines = sum(1 for line in operator_html.read_text(encoding="utf-8", errors="replace").splitlines() if len(line) > 2000)

    body = {
        "pin": pin or args.expect_pin,
        "expect_pin": args.expect_pin,
        "node": args.node,
        "node_version": version["stdout"].strip(),
        "chrome": args.chrome,
        "src_bytes_no_git": _tree_bytes(args.src) if args.src else None,
        "script_sha256": script_sha,
        "tauri_bins": _tauri_bins(repo),
        "operator_html": _rel(operator_html, repo),
        "operator_lines_over_2000": long_lines,
        "lint": lint_rows,
        "separation_app": separation,
        "draw": {
            "options_equal": opt_a["sha256"] == opt_b["sha256"] and opt_a["rc"] == 0 and opt_b["rc"] == 0,
            "options_bytes": opt_a["bytes"],
            "options_asked": 3,
            "options_got": len(opt_a["option_ids"]),
            "option_ids": opt_a["option_ids"],
            "options_wrote_history": opt_hist.exists(),
            "fresh_agree": style_a is not None and style_a == style_b and fresh_a.get("sheet") == fresh_b.get("sheet"),
            "fresh": [fresh_a.get("sheet"), fresh_b.get("sheet")],
            "fresh_seconds": [fresh_a["seconds"], fresh_b["seconds"]],
            "shared_changed": shared_style_a is not None and shared_style_b is not None and shared_style_a != shared_style_b,
            "shared": [shared_a.get("sheet"), shared_b.get("sheet")],
            "shared_history_entries": None,
        },
        "inspect": inspect_rows,
        "home_leak": home_leak,
        "login_taste_before": before_login,
        "login_taste_after": after_login,
        "profiles_left": profiles,
        "seconds": round(time.perf_counter() - started, 4),
    }
    if shared_hist.is_file():
        try:
            hist = json.loads(shared_hist.read_text(encoding="utf-8"))
            body["draw"]["shared_history_entries"] = len(hist) if isinstance(hist, list) else None
        except json.JSONDecodeError:
            body["draw"]["shared_history_entries"] = None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")

    smoke_ok = (
        lint_rows["smoke_slop"]["rc"] == 1
        and lint_rows["smoke_clean"]["rc"] == 0
        and lint_rows["missing"]["rc"] == 2
    )
    draw_ok = fresh_a["rc"] == 0 and fresh_b["rc"] == 0 and opt_a["rc"] == 0
    if home_leak or not smoke_ok or not draw_ok or separation is None or separation <= 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
