#!/usr/bin/env python3
"""Score pinned sloptrim on house-style fixtures and a fixed prose list.

detect.py comes from --detect, else $SLOPTRIM_DIR/scripts/detect.py, else
~/.cache/pfy/tools/sloptrim/src/scripts/detect.py. Tests pass --detect and
--only so a stub stands in for the real script. No network and no model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DEFAULT = Path(__file__).resolve().parent / "results.json"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
# Absolute path on purpose. A redirected HOME must not hide the pin.
DEFAULT_SRC = Path("/home/mark/.cache/pfy/tools/sloptrim/src")

# Fixed list so a second run scores the same files. Ten have no em dash in
# a pre-pass count. Ten are long docs that already use them.
CORPUS = [
    "docs/ops/MODULAR-CI.md",
    "docs/build-dropins/skill-discovery.md",
    "docs/ops/MVP-DOD-WALKTHROUGH.md",
    "docs/build-dropins/hermes-eval.md",
    "docs/ops/AUTONOMOUS-DECISIONS-2026-10-26.md",
    "docs/ops/HANDOFF-mvp-land-1031.md",
    "docs/plans/MVP-PARALLEL-1031.md",
    "sources/entries/114-sloptrim.md",
    "sources/entries/146-skill-up.md",
    "docs/eval/TOOLSET-RANKING.md",
    "docs/PENDING-HANDOFF.md",
    "docs/TODO.md",
    "docs/DESIGN.md",
    "docs/ops/integration-stages.md",
    "docs/ops/product-operator-surface.md",
    "docs/OPEN_QUESTIONS.md",
    "docs/adr/0010-reject-agenc-as-primary-runtime.md",
    "docs/adr/0012-voice-half-duplex-local-first.md",
    "AGENTS.md",
    "docs/ops/skill-verification.md",
]

# Resample these. Short text has no interval. The two docs are one plain
# ops file and one handoff that already uses em dashes.
CI_NAMES = {
    "plain.md",
    "slop.md",
    "emdash.md",
    "contrast.md",
    "notjust.md",
    "zw.md",
    "MODULAR-CI.md",
    "PENDING-HANDOFF.md",
}

PIN_COMMIT = "38dbb7cb4e97de0b9bf157903c95bdcab016dda2"


def resolve_detect(arg: str) -> Path | None:
    if arg:
        path = Path(arg).expanduser()
        return path if path.is_file() else None
    env = os.environ.get("SLOPTRIM_DIR", "").strip()
    cands = []
    if env:
        cands.append(Path(env) / "scripts/detect.py")
    cands.append(DEFAULT_SRC / "scripts/detect.py")
    for cand in cands:
        if cand.is_file():
            return cand
    return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def git_out(repo: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def pin_block(detect: Path) -> dict:
    repo = detect.parent.parent if detect.parent.name == "scripts" else detect.parent
    commit = git_out(repo, "rev-parse", "HEAD")
    tag_object = git_out(repo, "rev-parse", "v0.9.4")
    described = git_out(repo, "describe", "--tags", "--exact-match", "HEAD")
    return {
        "detect_py": str(detect),
        "detect_py_sha256": sha256_file(detect),
        "commit": commit,
        "commit_matches_entry": commit == PIN_COMMIT if commit else False,
        "tag": described,
        "tag_object": tag_object,
    }


def child_env() -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
    }
    return env


def run_detect(detect: Path, path: Path, extra: list[str], timeout: float) -> tuple[int, str, str, float]:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, str(detect), *extra, str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=child_env(),
        )
    except subprocess.TimeoutExpired:
        return 124, "", "timeout", round(time.perf_counter() - t0, 4)
    except OSError as exc:
        return 127, "", str(exc), round(time.perf_counter() - t0, 4)
    return proc.returncode, proc.stdout, proc.stderr, round(time.perf_counter() - t0, 4)


def parse_report(rc: int, stdout: str, stderr: str) -> tuple[dict | None, str]:
    if rc != 0:
        detail = (stderr or stdout or "").strip().replace("\n", " ")
        return None, "exit %s: %s" % (rc, detail[:240])
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return None, "stdout is not JSON"
    if not isinstance(data, dict):
        return None, "JSON is not an object"
    metrics = data.get("_metrics")
    if not isinstance(metrics, dict) or "ai_tell_score" not in metrics:
        return None, "JSON has no _metrics.ai_tell_score"
    return data, ""


def pattern_keys(data: dict) -> list[str]:
    return sorted(k for k in data if not str(k).startswith("_"))


def rel_of(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def write_out(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def house_counts(text: str) -> tuple[int, int]:
    return text.count("\u2014"), text.lower().count(", not ")


def score_one(detect: Path, root: Path, path: Path, kind: str, with_ci: bool) -> tuple[dict | None, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    em_dashes, comma_not = house_counts(text)
    rc1, out1, err1, sec1 = run_detect(detect, path, [], 60)
    data1, why = parse_report(rc1, out1, err1)
    if data1 is None:
        return None, "%s: %s" % (path.name, why)
    rc2, out2, err2, sec2 = run_detect(detect, path, [], 60)
    data2, why2 = parse_report(rc2, out2, err2)
    if data2 is None:
        return None, "%s second pass: %s" % (path.name, why2)
    m1 = data1["_metrics"]
    m2 = data2["_metrics"]
    score = m1["ai_tell_score"]
    score2 = m2["ai_tell_score"]
    row = {
        "path": rel_of(root, path),
        "kind": kind,
        "words": len(text.split()),
        "em_dashes": em_dashes,
        "comma_not": comma_not,
        "score": score,
        "score_2": score2,
        "abs_delta": abs(score - score2),
        "band": m1.get("ai_tell_band"),
        "confidence": m1.get("confidence"),
        "patterns_flagged": m1.get("patterns_flagged"),
        "pattern_keys": pattern_keys(data1),
        "invisible_chars": m1.get("invisible_chars"),
        "truncated": bool(m1.get("truncated")),
        "score_ci": None,
        "clean_removed_zw": None,
        "seconds": round(sec1 + sec2, 4),
    }
    if with_ci:
        rc, out, err, sec = run_detect(detect, path, ["--ci"], 180)
        data, why = parse_report(rc, out, err)
        if data is None:
            return None, "%s --ci: %s" % (path.name, why)
        ci = data.get("_metrics", {}).get("score_ci")
        row["score_ci"] = ci
        row["seconds"] = round(row["seconds"] + sec, 4)
        # The point score must not move when the interval is added.
        if data["_metrics"].get("ai_tell_score") != score:
            row["abs_delta"] = max(
                row["abs_delta"],
                abs(data["_metrics"].get("ai_tell_score") - score),
            )
    if path.name == "zw.md":
        rc, out, err, sec = run_detect(detect, path, ["--clean"], 60)
        row["seconds"] = round(row["seconds"] + sec, 4)
        if rc != 0:
            return None, "zw.md --clean: exit %s: %s" % (rc, (err or out)[:200])
        row["clean_removed_zw"] = "\u200b" not in out
    return row, ""


def flag(row: dict | None, key: str) -> bool | None:
    if row is None:
        return None
    return key in row["pattern_keys"]


def summarize(rows: list[dict], seconds: float) -> dict:
    by_name = {Path(r["path"]).name: r for r in rows}
    corpus = [r for r in rows if r["kind"] == "corpus"]

    def sc(name: str):
        row = by_name.get(name)
        return None if row is None else row["score"]

    plain_s = sc("plain.md")
    slop_s = sc("slop.md")
    em_s = sc("emdash.md")
    contrast = by_name.get("contrast.md")
    notjust = by_name.get("notjust.md")
    zw = by_name.get("zw.md")
    short = by_name.get("short.md")
    corpus_scores = [r["score"] for r in corpus]
    em_rows = [r for r in corpus if r["em_dashes"] > 0]
    comma_rows = [r for r in corpus if r["comma_not"] > 0]

    def missed(row: dict) -> bool:
        keys = row["pattern_keys"]
        return "17_negative_parallelism" not in keys and "18_not_x_just_y" not in keys

    ci = {}
    for row in rows:
        if row["score_ci"] is not None:
            ci[row["path"]] = row["score_ci"]
    return {
        "files": len(rows),
        "max_abs_delta": max(r["abs_delta"] for r in rows) if rows else None,
        "plain_score": plain_s,
        "slop_score": slop_s,
        "separation": None if plain_s is None or slop_s is None else slop_s - plain_s,
        "emdash_score": em_s,
        "emdash_minus_plain": None if em_s is None or plain_s is None else em_s - plain_s,
        "emdash_flag_58": flag(by_name.get("emdash.md"), "58_em_dash_overuse"),
        "contrast_score": None if contrast is None else contrast["score"],
        "contrast_minus_plain": None
        if contrast is None or plain_s is None
        else contrast["score"] - plain_s,
        "contrast_flag_17": flag(contrast, "17_negative_parallelism"),
        "contrast_flag_18": flag(contrast, "18_not_x_just_y"),
        "notjust_score": None if notjust is None else notjust["score"],
        "notjust_minus_plain": None
        if notjust is None or plain_s is None
        else notjust["score"] - plain_s,
        "notjust_flag_17": flag(notjust, "17_negative_parallelism"),
        "notjust_flag_18": flag(notjust, "18_not_x_just_y"),
        "zw_invisible": None if zw is None else zw["invisible_chars"],
        "zw_score": None if zw is None else zw["score"],
        "zw_minus_plain": None if zw is None or plain_s is None else zw["score"] - plain_s,
        "zw_clean_removed": None if zw is None else zw["clean_removed_zw"],
        "short_score": None if short is None else short["score"],
        "short_confidence": None if short is None else short["confidence"],
        "short_words": None if short is None else short["words"],
        "corpus_n": len(corpus),
        "corpus_median": statistics.median(corpus_scores) if corpus_scores else None,
        "corpus_min": min(corpus_scores) if corpus_scores else None,
        "corpus_max": max(corpus_scores) if corpus_scores else None,
        "corpus_gt_20": sum(1 for s in corpus_scores if s > 20),
        "corpus_gt_40": sum(1 for s in corpus_scores if s > 40),
        "corpus_gt_60": sum(1 for s in corpus_scores if s > 60),
        "corpus_with_em_dash": len(em_rows),
        "corpus_em_dash_score_le_20": sum(1 for r in em_rows if r["score"] <= 20),
        "corpus_flag_58": sum(1 for r in corpus if "58_em_dash_overuse" in r["pattern_keys"]),
        "corpus_comma_not": len(comma_rows),
        "corpus_comma_not_without_17_or_18": sum(1 for r in comma_rows if missed(r)),
        "truncated": sum(1 for r in rows if r["truncated"]),
        "score_ci": ci,
        "harness_comparisons": 0,
        "seconds": round(seconds, 4),
    }


def targets(root: Path, only: str) -> tuple[list[tuple[Path, str]], str]:
    if only:
        folder = Path(only)
        if not folder.is_dir():
            return [], "only dir missing: %s" % folder
        found = sorted(p for p in folder.glob("*.md") if p.is_file())
        if not found:
            return [], "only dir has no markdown: %s" % folder
        return [(p, "only") for p in found], ""
    rows: list[tuple[Path, str]] = []
    if not FIXTURE_DIR.is_dir():
        return [], "fixture dir missing: %s" % FIXTURE_DIR
    for path in sorted(FIXTURE_DIR.glob("*.md")):
        rows.append((path, "fixture"))
    for rel in CORPUS:
        path = root / rel
        if not path.is_file():
            return [], "corpus file missing: %s" % rel
        rows.append((path, "corpus"))
    return rows, ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score sloptrim on a fixed prose set.")
    ap.add_argument("--detect", default="", help="Path to detect.py or a stub")
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--only", default="", help="Score markdown in this dir and skip the corpus")
    args = ap.parse_args(argv)
    started = time.perf_counter()
    out = Path(args.out)
    root = Path(args.root)
    detect = resolve_detect(args.detect)
    if detect is None:
        write_out(
            out,
            {
                "ok": False,
                "error": "detect.py not found (pass --detect or set SLOPTRIM_DIR)",
                "files": [],
            },
        )
        print("detect.py not found")
        return 2
    pin = pin_block(detect)
    items, why = targets(root, args.only)
    if why:
        payload = {"ok": False, "error": why, "pin": pin, "files": []}
        write_out(out, payload)
        print(why)
        return 1
    rows: list[dict] = []
    for path, kind in items:
        with_ci = args.only == "" and path.name in CI_NAMES
        row, err = score_one(detect, root, path, kind, with_ci)
        if row is None:
            payload = {
                "ok": False,
                "error": err,
                "pin": pin,
                "seconds": round(time.perf_counter() - started, 4),
                "files": rows,
            }
            write_out(out, payload)
            print(err)
            return 1
        rows.append(row)
    seconds = time.perf_counter() - started
    summary = summarize(rows, seconds)
    payload = {"ok": True, "error": "", "pin": pin, "seconds": summary["seconds"], "summary": summary, "files": rows}
    write_out(out, payload)
    print(
        "ok separation=%s corpus_gt_20=%s corpus_gt_40=%s max_abs_delta=%s seconds=%s"
        % (
            summary["separation"],
            summary["corpus_gt_20"],
            summary["corpus_gt_40"],
            summary["max_abs_delta"],
            summary["seconds"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
