#!/usr/bin/env python3
"""Offline festival probe. No model, no account, no product-repo writes.

One filled 3-task plan restates gap B from docs/eval/TOOLSET-RANKING.md.
The probe measures fest next order and resume, whether a later task or the
testing gate can be marked done with no evidence, and agreement with a
filename sort of pending tasks. It does not run ./pfy build.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CACHE = Path.home() / ".cache/pfy/tools/festival"
FEST = CACHE / "unpack/fest"
CAMP_BIN = CACHE / "unpack/camp"
CAMP_ROOT = CACHE / "home/campaigns/probe"

GOAL = (
    "Name the unfinished pfy build step after a session ends. "
    "Success is fest next returning that step from files, with no second 3 hour build."
)
TASKS = [
    (
        "record timeout",
        "Copy the gap B sentence that the 2026-11-06 ./pfy build trial hit the 3 hour timeout.",
    ),
    (
        "record pregate",
        "Copy the gap B sentence that the recheck fix is parked after two pregate FAILs.",
    ),
    (
        "record recovery",
        "Write the recovery: do not start another 3 hour build; resume the parked recheck.",
    ),
]
MARKER = re.compile(r"\[(?:REPLACE|FILL|GUIDANCE):")
STATUS = re.compile(r"^fest_status:\s*(\S+)", re.M)


def env() -> dict[str, str]:
    base = CACHE
    home = base / "home"
    e = os.environ.copy()
    e["HOME"] = str(home)
    e["XDG_CONFIG_HOME"] = str(base / "xdg/config")
    e["XDG_CACHE_HOME"] = str(base / "xdg/cache")
    e["XDG_DATA_HOME"] = str(base / "xdg/data")
    e["TMPDIR"] = str(base / "tmp")
    e["PATH"] = str(base / "unpack") + os.pathsep + e.get("PATH", "")
    e["GIT_AUTHOR_NAME"] = "probe"
    e["GIT_AUTHOR_EMAIL"] = "probe@localhost"
    e["GIT_COMMITTER_NAME"] = "probe"
    e["GIT_COMMITTER_EMAIL"] = "probe@localhost"
    e["NO_COLOR"] = "1"
    e["TERM"] = "dumb"
    return e


def run(cmd: list[str], cwd: Path, timeout: float = 45.0) -> dict:
    t0 = time.perf_counter()
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env(),
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        rc, out, err, timed = p.returncode, p.stdout, p.stderr, False
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        err = exc.stderr or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        rc, timed = 124, True
    parsed = None
    text = (out or "").strip()
    if text.startswith("{") or text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
    return {
        "cmd": cmd,
        "cwd": str(cwd),
        "rc": rc,
        "seconds": round(time.perf_counter() - t0, 3),
        "timeout": timed,
        "stdout_tail": (out or "")[-1500:],
        "stderr_tail": (err or "")[-800:],
        "json": parsed,
    }


def count_markers(root: Path) -> int:
    n = 0
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".yaml", ".yml"}:
            n += len(MARKER.findall(path.read_text(encoding="utf-8", errors="replace")))
    return n


def fill_markers(root: Path) -> int:
    pat = re.compile(r"\[(?:REPLACE|FILL|GUIDANCE):\s*([^\]]+)\]")
    changed = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml"}:
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")

        def repl(m: re.Match) -> str:
            hint = " ".join(m.group(1).split())
            return "Gap B probe field: %s." % hint

        nxt = pat.sub(repl, raw)
        if nxt != raw:
            path.write_text(nxt, encoding="utf-8")
            changed += 1
    return changed


def set_objectives(seq: Path) -> None:
    files = sorted(p for p in seq.glob("[0-9][0-9]_*.md") if "QUALITY" not in p.name)
    work = [p for p in files if p.name < "04_"]
    for path, (_, sentence) in zip(work, TASKS):
        text = path.read_text(encoding="utf-8", errors="replace")
        needle = "## Objective"
        if needle not in text:
            continue
        head, _, tail = text.partition(needle)
        rest = tail.split("\n## ", 1)
        body = "\n\n" + sentence + "\n\n"
        if len(rest) == 2:
            text = head + needle + body + "## " + rest[1]
        else:
            text = head + needle + body
        path.write_text(text, encoding="utf-8")


def set_working_dir(seq: Path) -> None:
    goal = seq / "SEQUENCE_GOAL.md"
    text = goal.read_text(encoding="utf-8")
    if "fest_working_dir:" in text:
        return
    anchor = "fest_tracking: true\n"
    if anchor not in text:
        raise SystemExit("SEQUENCE_GOAL.md has no fest_tracking line")
    goal.write_text(
        text.replace(anchor, anchor + 'fest_working_dir: "projects/probe-notes"\n', 1),
        encoding="utf-8",
    )


def task_status(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = STATUS.search(text)
    return m.group(1) if m else ""


def boxes(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return text.count("- [ ]"), text.count("- [x]") + text.count("- [X]")


def basename_of_next(step: dict) -> str:
    data = step.get("json")
    if isinstance(data, dict):
        task = data.get("task")
        if isinstance(task, dict) and task.get("path"):
            return Path(str(task["path"])).name
    tail = (step.get("stdout_tail") or "").strip().splitlines()
    if tail:
        return Path(tail[-1].strip()).name
    return ""


def flat_pending(seq: Path) -> str:
    pending = []
    for path in sorted(seq.glob("[0-9][0-9]_*.md")):
        if task_status(path) != "completed":
            pending.append(path.name)
            break
    return pending[0] if pending else ""


def main() -> int:
    if not FEST.is_file() or not CAMP_BIN.is_file() or not CAMP_ROOT.is_dir():
        raise SystemExit("pinned fest/camp or the probe camp is missing")
    t_all = time.perf_counter()
    steps: list[dict] = []

    def add(cmd: list[str], cwd: Path, timeout: float = 45.0) -> dict:
        step = run(cmd, cwd, timeout)
        steps.append(step)
        print("%s rc=%s %.3fs" % (Path(cmd[0]).name + " " + " ".join(cmd[1:3]), step["rc"], step["seconds"]))
        return step

    notes = CAMP_ROOT / "projects/probe-notes"
    notes.mkdir(parents=True, exist_ok=True)
    (notes / "NOTE.md").write_text("notes for the festival probe. not the product repo.\n", encoding="utf-8")

    for dest in ("planning", "ready", "active", "completed"):
        parent = CAMP_ROOT / "festivals" / dest
        if not parent.is_dir():
            continue
        for child in parent.iterdir():
            if child.is_dir() and (
                child.name.startswith("gap-b-resume") or child.name.startswith("unfilled-control")
            ):
                shutil.rmtree(child)

    created = add(
        [
            str(FEST), "create", "festival", "--json", "--skip-markers",
            "--name", "gap-b-resume", "--goal", GOAL, "--type", "implementation",
        ],
        CAMP_ROOT,
    )
    created_path = (created.get("json") or {}).get("created_path")
    if not created_path:
        raise SystemExit("create festival returned no path")
    festival = CAMP_ROOT / created_path
    markers_scaffold = count_markers(festival)
    fill_markers(festival)
    phase = next(festival.glob("00*_*/"))
    seq_step = add(
        [
            str(FEST), "create", "sequence", "--json", "--skip-markers", "--no-prompt",
            "--name", "record the park", "--path", str(phase),
        ],
        festival,
    )
    seq_rel = (seq_step.get("json") or {}).get("created_path") or (seq_step.get("json") or {}).get("path")
    if not seq_rel:
        found = list(phase.glob("0*"))
        if not found:
            raise SystemExit("sequence create failed: %s" % seq_step["stdout_tail"][-400:])
        sequence = found[0]
    else:
        sequence = Path(seq_rel)
        if not sequence.is_absolute():
            sequence = (festival / sequence).resolve()
    task_cmd = [str(FEST), "create", "task", "--json", "--skip-markers", "--path", str(sequence)]
    for name, _ in TASKS:
        task_cmd.extend(["--name", name])
    add(task_cmd, festival)
    markers_before_fill = count_markers(festival)
    fill_markers(festival)
    set_objectives(sequence)
    set_working_dir(sequence)
    markers_after_fill = count_markers(festival)
    add(
        [
            str(FEST), "gates", "apply", "--json", "--approve",
            "--sequence", "001_IMPLEMENT/01_record_the_park",
        ],
        festival,
    )
    # Gate files are new templates. Fill any markers they brought in.
    fill_markers(sequence)
    validated = add([str(FEST), "validate", "--json", str(festival)], festival)

    control = add(
        [
            str(FEST), "create", "festival", "--json", "--skip-markers",
            "--name", "unfilled-control", "--goal", "Print hello", "--type", "implementation",
        ],
        CAMP_ROOT,
    )
    control_dir = CAMP_ROOT / (control.get("json") or {}).get("created_path", "")
    control_next = add([str(FEST), "next", "--json"], control_dir)

    # planning -> ready -> active. Each promote moves the directory.
    for _ in range(2):
        promoted = add([str(FEST), "promote", "--json", "--no-commit"], festival)
        new_path = (promoted.get("json") or {}).get("new_path")
        if new_path and Path(new_path).is_dir():
            festival = Path(new_path)
            sequence = festival / "001_IMPLEMENT/01_record_the_park"

    first = add([str(FEST), "next", "--json"], festival)
    resumed = add([str(FEST), "next", "--json"], festival)

    work = sorted(sequence.glob("0[1-3]_*.md"))
    gates = sorted(sequence.glob("0[4-9]_*.md"))
    skip = add(
        [str(FEST), "task", "completed", "--yes", "--json", work[2].name],
        festival,
    )
    next_after_skip = add([str(FEST), "next", "--json"], festival)
    add([str(FEST), "task", "reset", "--yes", "--json", work[2].name], festival)

    order = []
    for path in work:
        nxt = add([str(FEST), "next", "--json"], festival)
        flat = flat_pending(sequence)
        handed = basename_of_next(nxt)
        order.append({
            "expect": path.name,
            "fest_next": handed,
            "flat_pending": flat,
            "agree": handed == flat == path.name,
            "rc": nxt["rc"],
        })
        add([str(FEST), "task", "completed", "--yes", "--json", path.name], festival)

    gate_path = sequence / "04_testing.md"
    unchecked_before, checked_before = boxes(gate_path)
    gate_next = add([str(FEST), "next", "--json"], festival)
    gate_done = add(
        [str(FEST), "task", "completed", "--yes", "--json", gate_path.name],
        festival,
    )
    unchecked_after, checked_after = boxes(gate_path)

    # Finish the sequence gate files the same way, then try to complete.
    for path in gates:
        if task_status(path) == "completed":
            continue
        add([str(FEST), "task", "completed", "--yes", "--json", path.name], festival)
    phase_gate = add([str(FEST), "next"], festival)
    blocked = add([str(FEST), "promote", "--json", "--no-commit"], festival)
    # The other 4 of 11 are the template copies. Complete them with no boxes checked.
    template_gates = sorted((festival / "gates/implementation").glob("QUALITY_GATE_*.md"))
    template_results = []
    for path in template_gates:
        rel = str(path.relative_to(festival))
        before_u, before_c = boxes(path)
        step = add([str(FEST), "task", "completed", "--yes", "--json", rel], festival)
        after_u, after_c = boxes(path)
        template_results.append({
            "file": rel,
            "rc": step["rc"],
            "status": (step.get("json") or {}).get("status"),
            "unchecked_before": before_u,
            "checked_before": before_c,
            "unchecked_after": after_u,
            "checked_after": after_c,
            "file_status_after": task_status(path),
        })
    finished = add([str(FEST), "promote", "--json", "--no-commit"], festival)

    real = Path("/home/mark")
    sizes = {name: (CACHE / "unpack" / name).stat().st_size for name in ("fest", "camp", "festival")}
    payload = {
        "seconds_total": round(time.perf_counter() - t_all, 3),
        "festival_final": str(festival),
        "markers_scaffold": markers_scaffold,
        "markers_before_second_fill": markers_before_fill,
        "markers_after_fill": markers_after_fill,
        "validate_rc": validated["rc"],
        "validate_valid": (validated.get("json") or {}).get("valid"),
        "validate_score": (validated.get("json") or {}).get("score"),
        "control_next_rc": control_next["rc"],
        "control_refused": "VALIDATION FAILED" in (
            (control_next.get("stdout_tail") or "") + (control_next.get("stderr_tail") or "")
        ),
        "first_next": basename_of_next(first),
        "first_next_rc": first["rc"],
        "resume_same": basename_of_next(first) == basename_of_next(resumed) and first["rc"] == 0,
        "progress": (first.get("json") or {}).get("progress"),
        "skip_ahead_rc": skip["rc"],
        "skip_ahead_status": (skip.get("json") or {}).get("status"),
        "next_after_skip": basename_of_next(next_after_skip),
        "order": order,
        "order_hits": sum(1 for row in order if row["agree"]),
        "gate_was_next": basename_of_next(gate_next) == "04_testing.md",
        "gate_complete_rc": gate_done["rc"],
        "gate_complete_status": (gate_done.get("json") or {}).get("status"),
        "gate_unchecked_before": unchecked_before,
        "gate_checked_before": checked_before,
        "gate_unchecked_after": unchecked_after,
        "gate_checked_after": checked_after,
        "gate_file_status_after": task_status(gate_path),
        "phase_gate_rc": phase_gate["rc"],
        "phase_gate_needs_operator": "do not approve it yourself" in (phase_gate.get("stdout_tail") or ""),
        "phase_gate_excerpt": (phase_gate.get("stdout_tail") or "")[-900:],
        "promote_blocked_rc": blocked["rc"],
        "promote_blocked_error": (blocked.get("json") or {}).get("error"),
        "template_gates": template_results,
        "promote_completed_rc": finished["rc"],
        "promote_completed_to": (finished.get("json") or {}).get("to"),
        "promote_completed_success": (finished.get("json") or {}).get("success"),
        "promote_completed_error": (finished.get("json") or {}).get("error"),
        "isolation": {
            "real_obey_exists": (real / ".obey").exists(),
            "real_campaigns_exists": (real / "campaigns").exists(),
            "worktree_camp_file": (ROOT / ".camp").exists(),
            "notes_files": sorted(p.name for p in notes.iterdir()),
        },
        "binary_bytes": sizes,
        "steps": [
            {
                "cmd": s["cmd"][1:],
                "rc": s["rc"],
                "seconds": s["seconds"],
                "timeout": s["timeout"],
                "stdout_tail": s["stdout_tail"] if s["rc"] != 0 else "",
                "stderr_tail": s["stderr_tail"] if s["rc"] != 0 else "",
            }
            for s in steps
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in payload if k != "steps"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
