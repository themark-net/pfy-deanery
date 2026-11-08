#!/usr/bin/env python3
"""Score assay against the operator frontend and one planted page.

The number is how many of 4 planted defects assay fails a case for.
A green run is not the operator window working. Stdlib only. No network
of its own: the assay binary is the only child.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "gui" / "operator" / "frontend"
PLANTED = Path(__file__).resolve().parent / "fixture" / "planted.html"
TAURI = (
    ROOT / "gui" / "operator" / "src-tauri" / "target" / "release" / "pfy-operator",
    ROOT / "gui" / "operator" / "src-tauri" / "target" / "debug" / "pfy-operator",
)
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "source", "track", "wbr",
}
CONTROL_TAGS = {"button", "input", "select", "textarea"}
PLANTED_IDS = ("visible-throw", "dead-button", "fail-text", "hidden-throw")


def view_rule_present(html: str) -> bool:
    compact = re.sub(r"\s+", "", html)
    return ".view{display:none" in compact and ".view.on{display:block" in compact


def _hidden_open(attrs: dict, parent_hidden: bool, use_view_class: bool) -> bool:
    style = attrs.get("style") or ""
    if re.search(r"display\s*:\s*none", style, re.I):
        return True
    classes = (attrs.get("class") or "").split()
    if use_view_class and "view" in classes and "on" not in classes:
        return True
    return parent_hidden


class _Controls(HTMLParser):
    def __init__(self, use_view_class: bool) -> None:
        super().__init__(convert_charrefs=True)
        self.use_view_class = use_view_class
        self.stack: list[bool] = []
        self.rows: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k: (v or "") for k, v in attrs}
        parent = self.stack[-1] if self.stack else False
        hidden = _hidden_open(ad, parent, self.use_view_class)
        if tag in CONTROL_TAGS or (tag == "a" and ad.get("href")):
            self.rows.append({
                "tag": tag,
                "id": ad.get("id") or "",
                "hidden": hidden,
            })
        if tag not in VOID:
            self.stack.append(hidden)

    def handle_endtag(self, tag: str) -> None:
        if tag not in VOID and self.stack:
            self.stack.pop()


def count_markup(html: str) -> dict:
    use_view = view_rule_present(html)
    parser = _Controls(use_view)
    parser.feed(html)
    rows = parser.rows
    hidden = [r for r in rows if r["hidden"]]
    return {
        "view_rule": use_view,
        "controls": len(rows),
        "hidden": len(hidden),
        "visible": len(rows) - len(hidden),
        "hidden_ids": [r["id"] for r in hidden if r["id"]],
    }


def _blob(case: dict) -> str:
    parts = [str(case.get("detail") or ""), str(case.get("measured") or ""),
             str(case.get("what") or "")]
    for act in case.get("acts") or []:
        if isinstance(act, dict):
            parts.extend(str(v) for v in act.values())
    return "\n".join(parts)


def _clicked(case: dict, needle: str) -> bool:
    for act in case.get("acts") or []:
        if isinstance(act, dict) and needle in str(act.get("click") or ""):
            return True
    return False


def _failed(case: dict) -> bool:
    return case.get("outcome") == "failed"


def score_planted(report: dict) -> dict:
    """Which of the 4 planted defects produced a failed case.

    A hidden control that only shows up in the surface list is not caught.
    The case has to fail.
    """
    cases = [c for c in (report.get("cases") or []) if isinstance(c, dict)]
    visible = any(_failed(c) and "undefinedFn" in _blob(c) for c in cases)
    dead = any(_failed(c) and _clicked(c, "#dead") for c in cases)
    fail_text = any(_failed(c) and _clicked(c, "#failpaint") for c in cases)
    hidden = any(
        _failed(c) and ("hiddenBoom" in _blob(c) or "#hidden-throw" in _blob(c))
        for c in cases
    )
    items = {
        "visible-throw": visible,
        "dead-button": dead,
        "fail-text": fail_text,
        "hidden-throw": hidden,
    }
    caught = sum(1 for key in PLANTED_IDS if items[key])
    return {"caught": caught, "of": 4, "items": items, "helps": caught == 4}


def _selectors(report: dict) -> list[str]:
    found: list[str] = []
    for case in report.get("cases") or []:
        if not isinstance(case, dict):
            continue
        for act in case.get("acts") or []:
            if not isinstance(act, dict):
                continue
            for value in act.values():
                text = str(value)
                if text and text not in found:
                    found.append(text)
    return found


def _short_fails(report: dict) -> list[dict]:
    out = []
    for case in report.get("cases") or []:
        if not isinstance(case, dict) or not _failed(case):
            continue
        links = [
            str(link.get("kind") or "")
            for link in (case.get("links") or [])
            if isinstance(link, dict)
        ]
        out.append({
            "id": case.get("id") or "",
            "rules": list(case.get("rules") or [])[:6],
            "links": links[:4],
            "detail": str(case.get("detail") or "")[:180],
        })
        if len(out) >= 12:
            break
    return out


def _samples(report: dict, key: str, limit: int = 4) -> list[str]:
    out: list[str] = []
    for item in report.get(key) or []:
        text = " ".join(str(item).split())[:160]
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _watched(report: dict, needles: tuple[str, ...]) -> list[dict]:
    out = []
    for case in report.get("cases") or []:
        if not isinstance(case, dict):
            continue
        blob = _blob(case)
        if not any(needle in blob for needle in needles):
            continue
        out.append({
            "id": case.get("id") or "",
            "outcome": case.get("outcome") or "",
            "what": str(case.get("what") or "")[:80],
            "measured": str(case.get("measured") or "")[:160],
        })
        if len(out) >= 6:
            break
    return out


def _parse_stdout(text: str) -> dict:
    raw = text.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise
        data = json.loads(raw[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("assay JSON is not an object")
    return data


def run_assay(binary: str, folder: Path, env: dict, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            [binary, str(folder), "--json"],
            cwd=str(folder),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "skipped": "TIMEOUT",
            "seconds": round(time.perf_counter() - started, 3),
            "exit": None,
        }
    except OSError as exc:
        return {
            "ok": False,
            "skipped": "assay not runnable: %s" % exc.__class__.__name__,
            "seconds": round(time.perf_counter() - started, 3),
            "exit": None,
        }
    seconds = round(time.perf_counter() - started, 3)
    if proc.returncode not in (0, 1):
        err = (proc.stderr or proc.stdout or "").strip().splitlines()
        return {
            "ok": False,
            "skipped": "assay exit %s" % proc.returncode,
            "stderr": err[-4:],
            "seconds": seconds,
            "exit": proc.returncode,
        }
    try:
        data = _parse_stdout(proc.stdout or "")
    except (json.JSONDecodeError, ValueError):
        return {
            "ok": False,
            "skipped": "assay stdout was not JSON",
            "seconds": seconds,
            "exit": proc.returncode,
        }
    surface = data.get("surface") if isinstance(data.get("surface"), list) else []
    return {
        "ok": True,
        "seconds": seconds,
        "exit": proc.returncode,
        "report": data,
        "summary": {
            "planned": data.get("planned"),
            "passed": data.get("passed"),
            "failed": data.get("failed"),
            "works": data.get("works"),
            "surface": len(surface),
            "pressed": len(_selectors(data)),
            "console_errors": len(data.get("console_errors") or []),
            "failed_requests": len(data.get("failed_requests") or []),
            "console_error_samples": _samples(data, "console_errors"),
            "failed_request_samples": _samples(data, "failed_requests"),
            "launch_cases": _watched(data, ("#btnlaunchsess", "#btnlaunch", "#dead", "#failpaint")),
            "fails": _short_fails(data),
        },
    }


def child_env(home: Path, tmp: Path, browsers: str) -> dict:
    path = os.environ.get("PATH") or "/usr/bin:/bin"
    return {
        "PATH": path,
        "HOME": str(home),
        "TMPDIR": str(tmp),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "PLAYWRIGHT_BROWSERS_PATH": browsers,
        "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1",
        "LANG": "C.UTF-8",
    }


def _copy_frontend(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True)
    for item in src.iterdir():
        if item.is_file() and item.suffix.lower() in {".html", ".js", ".css"}:
            shutil.copyfile(item, dest / item.name)


def _prepare(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    if src.is_dir():
        _copy_frontend(src, dest)
    else:
        dest.mkdir(parents=True)
        shutil.copyfile(src, dest / "index.html")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score one assay pin on the operator page.")
    ap.add_argument("--assay", required=True, help="path to the assay executable")
    ap.add_argument("--frontend", type=Path, default=FRONTEND)
    ap.add_argument("--planted", type=Path, default=PLANTED)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--home", type=Path, default=None)
    ap.add_argument("--tmp", type=Path, default=None)
    ap.add_argument("--browsers", default="")
    ap.add_argument("--timeout", type=float, default=360.0)
    args = ap.parse_args(argv)

    binary = args.assay
    if not Path(binary).is_file() or not os.access(binary, os.X_OK):
        print("assay binary missing", flush=True)
        return 2
    if not args.frontend.is_file() and not (args.frontend / "index.html").is_file():
        print("frontend missing", flush=True)
        return 2
    if not args.planted.is_file():
        print("planted page missing", flush=True)
        return 2

    work = args.tmp or Path(os.environ.get("TMPDIR") or "/tmp") / "assay-probe"
    home = args.home or (work / "home")
    tmp = work / "tmp"
    for folder in (work, home, tmp, home / ".config", home / ".cache", home / ".local" / "share"):
        folder.mkdir(parents=True, exist_ok=True)
    browsers = args.browsers or str(home / "ms-playwright")
    env = child_env(home, tmp, browsers)

    frontend_html = args.frontend / "index.html" if args.frontend.is_dir() else args.frontend
    markup = count_markup(frontend_html.read_text(encoding="utf-8", errors="replace"))
    operator_dir = work / "operator-page"
    planted_dir = work / "planted-page"
    _prepare(args.frontend if args.frontend.is_dir() else args.frontend, operator_dir)
    _prepare(args.planted, planted_dir)

    operator = run_assay(binary, operator_dir, env, args.timeout)
    planted = run_assay(binary, planted_dir, env, min(args.timeout, 180.0))
    if not planted.get("ok"):
        result = {
            "helps": False,
            "skipped": planted.get("skipped") or "planted run failed",
            "markup": markup,
            "operator": operator.get("summary") or {"skipped": operator.get("skipped")},
            "tauri_binary": any(p.is_file() for p in TAURI),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(result["skipped"], flush=True)
        return 2

    scored = score_planted(planted["report"])
    result = {
        "helps": scored["helps"],
        "planted": {
            "caught": scored["caught"],
            "of": scored["of"],
            "items": scored["items"],
            "seconds": planted["seconds"],
            "exit": planted["exit"],
            "summary": planted["summary"],
        },
        "operator": {
            "markup_controls": markup["controls"],
            "markup_hidden": markup["hidden"],
            "markup_visible": markup["visible"],
            "view_rule": markup["view_rule"],
            "hidden_ids": markup["hidden_ids"],
            "seconds": operator.get("seconds"),
            "exit": operator.get("exit"),
            **(operator.get("summary") or {}),
        },
        "tauri_binary": any(p.is_file() for p in TAURI),
    }
    if operator.get("skipped"):
        result["operator"]["skipped"] = operator["skipped"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "planted %s/%s helps %s" % (scored["caught"], scored["of"], scored["helps"]),
        flush=True,
    )
    return 0 if scored["helps"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
