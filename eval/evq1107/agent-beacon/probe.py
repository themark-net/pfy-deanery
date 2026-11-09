#!/usr/bin/env python3
"""Offline probe for agent-beacon on one planted Grok session.

The session lives under the cache, not the real home. Beacon runs in a
network namespace that does not mount the real home. No key is passed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
# Fixed cache path. A redirected HOME must not hide the binary.
CACHE = (Path.home() / ".cache/pfy/tools/agent-beacon")
BEACON = CACHE / "bin" / "beacon"
WORK = CACHE / "probe-work"
MARKERS = (
    "PFYBEACONC1",
    "PFYBEACONC2",
    "PFYBEACONC3",
    "PFYBEACONC4",
)
SESSION_ID = "pfy-beacon-eval-1"
WORKSPACE = "/tmp/pfy-beacon-probe"
UNSET = (
    "TYPESAFE_API_KEY",
    "BEACON_JEV_API_KEY",
    "BEACON_JEV_ENDPOINT",
    "BEACON_JEV_MODEL",
    "BEACON_EVALUATOR",
    "SUBQ_API_KEY",
    "BEACON_SUBQ_API_KEY",
    "BEACON_SUBQ_ENDPOINT",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


def enc(path: str) -> str:
    return path.replace("/", "%2F").replace(" ", "%20")


def write_fixture(root: Path) -> Path:
    session = root / enc(WORKSPACE) / SESSION_ID
    (session / "terminal").mkdir(parents=True, exist_ok=True)
    (session / "summary.json").write_text(
        json.dumps(
            {
                "created_at": "2026-11-07T20:00:00.000Z",
                "updated_at": "2026-11-07T20:01:00.000Z",
                "generated_title": "Planted corrections",
                "current_model_id": "grok-build",
                "num_messages": 6,
                "num_chat_messages": 5,
            }
        ),
        encoding="utf-8",
    )
    (session / "prompt_context.json").write_text(
        json.dumps({"working_directory": WORKSPACE, "os_name": "linux", "shell_path": "/bin/bash"}),
        encoding="utf-8",
    )
    prompts = [
        "PFYBEACONC1 run catalog_check before a stage card edit",
        "PFYBEACONC2 do not install skills into the real home",
        "PFYBEACONC3 verify the tarball sha256 before extract",
        "PFYBEACONC4 do not call a hosted evaluator",
    ]
    chat = []
    for text in prompts:
        chat.append(json.dumps({"type": "user", "content": [{"type": "text", "text": text}]}))
    chat.append(
        json.dumps(
            {
                "type": "assistant",
                "content": "Noted the four corrections.",
                "model_id": "grok-build",
                "tool_calls": [
                    {
                        "id": "call-pfy-1",
                        "name": "run_terminal_command",
                        "arguments": json.dumps({"command": "true", "description": "noop"}),
                    }
                ],
            }
        )
    )
    chat.append(
        json.dumps(
            {"type": "tool_result", "tool_call_id": "call-pfy-1", "content": "ok"}
        )
    )
    (session / "chat_history.jsonl").write_text("\n".join(chat) + "\n", encoding="utf-8")
    events = [
        {
            "ts": "2026-11-07T20:00:01.000Z",
            "type": "turn_started",
            "session_id": SESSION_ID,
            "turn_number": 0,
            "model_id": "grok-build",
        },
        {
            "ts": "2026-11-07T20:01:00.000Z",
            "type": "turn_ended",
            "outcome": "success",
            "turn_number": 0,
        },
    ]
    (session / "events.jsonl").write_text(
        "\n".join(json.dumps(row) for row in events) + "\n",
        encoding="utf-8",
    )
    return session


def bwrap(args: list[str], out: Path, timeout: int) -> dict:
    home = WORK / "home"
    cmd = [
        "/usr/bin/bwrap",
        "--unshare-net",
        "--die-with-parent",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/lib64", "/lib64",
        "--ro-bind", "/bin", "/bin",
        "--ro-bind", "/etc", "/etc",
        "--proc", "/proc",
        "--dev", "/dev",
        "--tmpfs", "/tmp",
        "--ro-bind", str(CACHE / "bin"), str(CACHE / "bin"),
        "--bind", str(WORK), str(WORK),
        "--setenv", "HOME", str(home),
        "--setenv", "TMPDIR", "/tmp",
        "--setenv", "XDG_CONFIG_HOME", str(home / ".config"),
        "--setenv", "XDG_CACHE_HOME", str(home / ".cache"),
        "--setenv", "PATH", str(CACHE / "bin"),
        "--chdir", str(out),
    ]
    for name in UNSET:
        cmd.extend(["--unsetenv", name])
    cmd.append("--")
    cmd.extend(args)
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        code = 124
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + "\nTIMEOUT"
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        timed_out = True
    return {
        "exit": code,
        "seconds": round(time.perf_counter() - started, 3),
        "timed_out": timed_out,
        "stdout": stdout[-8000:],
        "stderr": stderr[-4000:],
    }


def load_json(text: str):
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def nbytes(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    if path.is_dir():
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
    return total


def marker_hits(text: str) -> dict:
    return {marker: text.count(marker) for marker in MARKERS}


def parse_events(lines: list[str]) -> tuple[dict, int]:
    counts: dict[str, int] = {}
    poll = 0
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        action = ((row.get("event") or {}).get("action")) or ""
        if action:
            counts[action] = counts.get(action, 0) + 1
        method = ((row.get("harness") or {}).get("collection_method")) or ""
        if method == "poll":
            poll += 1
    return counts, poll


def sync_counts(doc: dict) -> dict:
    parsed = load_json(doc.get("stdout") or "")
    if not isinstance(parsed, dict):
        return {}
    keep = (
        "sessions",
        "sessions_changed",
        "events_emitted",
        "errors",
        "malformed_lines",
    )
    return {key: parsed.get(key) for key in keep}


def main() -> int:
    if (ROOT / "tmp" / "STOP").exists():
        print("STOP")
        return 2
    if not BEACON.is_file():
        print("missing beacon binary")
        return 2
    if WORK.exists():
        shutil.rmtree(WORK)
    sessions = WORK / "sessions"
    out = WORK / "out"
    home = WORK / "home"
    for path in (sessions, out, home):
        path.mkdir(parents=True)
    write_fixture(sessions)
    log_path = out / "runtime.jsonl"
    state_path = out / "grok-sessions.json"
    project = out / "project"
    project.mkdir()

    version = bwrap([str(BEACON), "version"], out, 30)
    sync_args = [
        str(BEACON),
        "endpoint",
        "grok",
        "sync",
        "--json",
        "--sessions-dir",
        str(sessions),
        "--log-path",
        str(log_path),
        "--state",
        str(state_path),
    ]
    first = bwrap(sync_args, out, 60)
    second = bwrap(sync_args, out, 60)
    log_text = log_path.read_text(encoding="utf-8") if log_path.is_file() else ""
    log_lines = [line for line in log_text.splitlines() if line.strip()]
    action_counts, poll_lines = parse_events(log_lines)

    dry = bwrap(
        [
            str(BEACON),
            "memory",
            "evaluations",
            "run",
            "--dry-run",
            "--json",
            "--log-path",
            str(log_path),
            "--project",
            str(project),
            "--limit",
            "10",
        ],
        out,
        60,
    )
    live = bwrap(
        [
            str(BEACON),
            "memory",
            "evaluations",
            "run",
            "--json",
            "--log-path",
            str(log_path),
            "--project",
            str(project),
            "--limit",
            "1",
            "--timeout",
            "5s",
        ],
        out,
        30,
    )

    dry_doc = load_json(dry["stdout"])
    trace_ids = []
    if isinstance(dry_doc, dict):
        for key in ("previews", "traces", "evaluations"):
            rows = dry_doc.get(key) or []
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, dict):
                        for field in ("trace", "trace_id", "id"):
                            value = row.get(field)
                            if isinstance(value, str) and value not in trace_ids:
                                trace_ids.append(value)
    if not trace_ids:
        trace_ids.append("session:grok:" + SESSION_ID)

    lesson = project / "lesson.md"
    lesson.write_text(
        "PFYBEACONC1 run catalog_check before a stage card edit.\n",
        encoding="utf-8",
    )
    create = bwrap(
        [
            str(BEACON),
            "memory",
            "candidates",
            "create",
            "--json",
            "--log-path",
            str(log_path),
            "--project",
            str(project),
            "--trace",
            trace_ids[0],
            "--kind",
            "correction",
            "--title",
            "Check the catalog before a stage edit",
            "--body-file",
            str(lesson),
            "--applicability",
            "when a lane edits a stage card",
        ],
        out,
        60,
    )
    create_doc = load_json(create["stdout"])
    candidate_id = ""
    if isinstance(create_doc, dict):
        for field in ("id", "candidate_id"):
            value = create_doc.get(field)
            if isinstance(value, str):
                candidate_id = value
                break
        cand = create_doc.get("candidate")
        if isinstance(cand, dict) and isinstance(cand.get("id"), str):
            candidate_id = cand["id"]
    approve = {"exit": None, "seconds": 0, "stdout": "", "stderr": "no candidate id", "timed_out": False}
    if candidate_id:
        approve = bwrap(
            [
                str(BEACON),
                "memory",
                "candidates",
                "approve",
                candidate_id,
                "--json",
                "--log-path",
                str(log_path),
                "--project",
                str(project),
                "--reason",
                "probe typed the lesson",
            ],
            out,
            60,
        )
    listed = bwrap(
        [
            str(BEACON),
            "memory",
            "list",
            "--json",
            "--log-path",
            str(log_path),
            "--project",
            str(project),
        ],
        out,
        60,
    )
    list_doc = load_json(listed["stdout"])
    approved = []
    if isinstance(list_doc, list):
        approved = list_doc
    elif isinstance(list_doc, dict):
        for key in ("memories", "items", "memory"):
            rows = list_doc.get(key)
            if isinstance(rows, list):
                approved = rows
                break

    home_files = sorted(
        str(path.relative_to(home))
        for path in home.rglob("*")
        if path.is_file()
    )
    result = {
        "version": version,
        "sync_first": {k: first[k] for k in ("exit", "seconds", "timed_out", "stdout", "stderr")},
        "sync_second": {k: second[k] for k in ("exit", "seconds", "timed_out", "stdout", "stderr")},
        "log_lines": len(log_lines),
        "actions": action_counts,
        "markers_in_log": marker_hits(log_text),
        "collection_poll_lines": poll_lines,
        "sync_first_counts": sync_counts(first),
        "sync_second_counts": sync_counts(second),
        "dry_run": {k: dry[k] for k in ("exit", "seconds", "timed_out", "stdout", "stderr")},
        "live_eval": {k: live[k] for k in ("exit", "seconds", "timed_out", "stdout", "stderr")},
        "trace_ids_tried": trace_ids[:5],
        "candidate_create": {k: create[k] for k in ("exit", "seconds", "timed_out", "stdout", "stderr")},
        "candidate_id": candidate_id,
        "candidate_approve": {k: approve[k] for k in ("exit", "seconds", "timed_out", "stdout", "stderr")},
        "memory_list": {k: listed[k] for k in ("exit", "seconds", "timed_out", "stdout", "stderr")},
        "approved_count": len(approved),
        "approved_with_marker": sum(
            1 for row in approved if "PFYBEACONC1" in json.dumps(row)
        ),
        "fake_home_files": home_files[:40],
        "sizes": {
            "tarball": nbytes(CACHE / "dist" / "beacon_1.3.59_linux_amd64.tar.gz"),
            "extract_bytes": nbytes(CACHE / "extract"),
            "beacon": nbytes(CACHE / "bin" / "beacon"),
            "beacon_hooks": nbytes(CACHE / "bin" / "beacon-hooks"),
            "beacon_otelcol": nbytes(CACHE / "bin" / "beacon-otelcol"),
            "beacon_vector": nbytes(CACHE / "bin" / "beacon-vector"),
        },
    }
    dest = OUT_DIR / "results.json"
    dest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "lines",
        result["log_lines"],
        "markers",
        result["markers_in_log"],
        "second_exit",
        second["exit"],
        "dry",
        dry["exit"],
        "live",
        live["exit"],
        "approved",
        result["approved_count"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
