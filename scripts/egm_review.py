#!/usr/bin/env python3
"""Advisory Elephant-Goldfish spec review. Not a gate.

One tools-off grok process drafts a spec from a ticket and the cited
excerpts. Two or three fresh processes then review that spec. They do not
share a session, a cwd, or a conversation. Nothing here is wired into
pregate, CI, or another gate.

A missing grok binary exits 2 and prints a next step. A missing ticket
or cited file exits 2 and names that file. It does not ask for a grok
install. A reviewer that times out, exits nonzero, or returns unreadable
JSON is recorded, the other reviewers still run, and the process exits 1.
Rerun the same command after the binary works. Partial findings stay in
the report.

Usage:
  python3 scripts/egm_review.py --ticket FILE --cited FILE --out FILE
      [--scratch DIR] [--max-turns N] [--personas readiness,critic,codebase]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MAX_TURNS = 4
CALL_TIMEOUT_S = 180
ATTEMPTS = 2

# Shell-route tool ids verified on nimo with grok 1.0.77 (2026-11-07).
# An empty --tools is ignored. This denylist plus the flags below left
# tool_definitions empty in the grill step on the same binary.
TOOLS_OFF = (
    "run_terminal_cmd",
    "run_terminal_command",
    "grep",
    "read_file",
    "search_replace",
    "list_dir",
    "todo_write",
    "task",
    "write",
    "get_task_output",
    "get_command_or_subagent_output",
    "kill_task",
    "kill_command_or_subagent",
    "enter_plan_mode",
    "exit_plan_mode",
    "monitor",
    "scheduler_create",
    "scheduler_delete",
    "scheduler_list",
    "image_gen",
    "image_edit",
    "image_to_video",
    "reference_to_video",
    "ask_user_question",
    "send_feedback",
    "search_tool",
    "use_tool",
    "hashline_read",
    "hashline_grep",
    "hashline_edit",
    "Agent",
    "update_goal",
)

ELEPHANT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "spec": {"type": "string"},
        "unstated": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["spec", "unstated"],
}

GOLDFISH_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "severity": {"type": "string"},
                    "scope": {"type": "string"},
                    "finding": {"type": "string"},
                },
                "required": ["severity", "scope", "finding"],
            },
        }
    },
    "required": ["findings"],
}

PERSONAS = {
    "readiness": (
        "You are Implementation Readiness Goldfish. You will write the code. "
        "Flag a step that leaves a design choice to the implementer: error "
        "status, directory mode, cleanup, skip condition, or which files "
        "change. Severity Blocker when the missing choice can make the change "
        "fail or do the wrong thing. Severity Major when the plan is vague but "
        "the outcome is still bounded. Severity Nit for wording."
    ),
    "critic": (
        "You are Design Critic Goldfish. Flag an unmitigated failure mode: a "
        "path that fails, a lock or timeout, a cleanup that does not run, a "
        "retry that hides an environment failure, or a world-readable tree. "
        "Do not invent a load number. Severity Blocker when the failure would "
        "ship a wrong result or skip the check the ticket exists to fix. "
        "Severity Major for a real hole with a bounded blast. Severity Nit "
        "for polish."
    ),
    "codebase": (
        "You are Codebase Details Goldfish. Compare the spec to the cited "
        "excerpts only. Flag a contradiction between the spec and the code, "
        "a function the spec names that the excerpt does not contain, and a "
        "behavior in the excerpt that the spec must preserve but does not "
        "mention. Do not flag a file the spec says it will create. Severity "
        "Blocker when the spec describes current behavior the excerpt does "
        "not have. Severity Major when the excerpt shows a rule the new code "
        "is likely to break and the spec is silent. Severity Nit for a "
        "missing comment."
    ),
}


def grok_bin() -> str:
    return os.environ.get("PFY_GROK_BIN") or str(Path.home() / ".local/bin/grok")


def scrub(text: str) -> str:
    kept = []
    for line in (text or "").splitlines():
        if re.search(
            r"(authorization|bearer |api[_-]?key|secret|password|cookie)",
            line,
            re.I,
        ):
            kept.append("[redacted]")
        else:
            kept.append(line)
    return "\n".join(kept)[:800]


def grok_argv(binary: str, max_turns: int, prompt_file: Path, schema: dict) -> list[str]:
    if max_turns < 1 or max_turns > MAX_TURNS:
        raise ValueError("refusing grok call with max-turns %s" % max_turns)
    return [
        binary,
        "--prompt-file",
        str(prompt_file),
        "--max-turns",
        str(max_turns),
        "--reasoning-effort",
        "low",
        "--verbatim",
        "--no-plan",
        "--disable-web-search",
        "--no-subagents",
        "--disallowed-tools",
        ",".join(TOOLS_OFF),
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(schema, separators=(",", ":")),
    ]


def grok_env() -> dict[str, str]:
    env = dict(os.environ)
    env["GROK_WORKFLOWS"] = "0"
    env["GROK_SUBAGENTS"] = "0"
    return env


def parse_envelope(stdout: str) -> dict:
    raw = (stdout or "").strip()
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.rfind("\n{")
        if start < 0 and raw.startswith("{"):
            start = 0
        else:
            start = start + 1 if start >= 0 else -1
        if start < 0:
            raise ValueError("grok stdout was not JSON")
        envelope = json.loads(raw[start:])
    if not isinstance(envelope, dict):
        raise ValueError("grok stdout JSON was not an object")
    text = envelope.get("text")
    if isinstance(text, dict):
        data = text
    elif isinstance(text, str) and text.strip():
        body = text.strip()
        if body.startswith("```"):
            body = re.sub(r"^```(?:json)?\s*", "", body)
            body = re.sub(r"\s*```$", "", body)
        data = json.loads(body)
    else:
        raise ValueError("grok JSON had no text")
    if not isinstance(data, dict):
        raise ValueError("grok text JSON was not an object")
    models = envelope.get("modelUsage")
    model = None
    if isinstance(models, dict) and models:
        model = next(iter(models))
    return {
        "data": data,
        "turns": int(envelope.get("num_turns") or 0),
        "model": model,
    }


def call_grok(binary: str, max_turns: int, prompt: str, schema: dict, cwd: Path) -> dict:
    cwd.mkdir(parents=True, exist_ok=True)
    prompt_path = cwd / "prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    argv = grok_argv(binary, max_turns, prompt_path, schema)
    started = time.monotonic()
    proc = subprocess.run(
        argv,
        cwd=cwd,
        env=grok_env(),
        capture_output=True,
        text=True,
        timeout=CALL_TIMEOUT_S,
        check=False,
    )
    wall = round(time.monotonic() - started, 3)
    if proc.returncode != 0:
        raise RuntimeError(
            "grok exited %s: %s" % (proc.returncode, scrub(proc.stderr or proc.stdout or ""))
        )
    parsed = parse_envelope(proc.stdout)
    parsed["wall_s"] = wall
    parsed["attempts"] = 1
    return parsed


def call_with_retry(binary: str, max_turns: int, prompt: str, schema: dict, cwd: Path) -> dict:
    last = "grok did not run"
    for attempt in range(1, ATTEMPTS + 1):
        try:
            got = call_grok(binary, max_turns, prompt, schema, cwd)
            got["attempts"] = attempt
            got["ok"] = True
            got["error"] = ""
            return got
        except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            last = scrub(str(exc))
    return {
        "ok": False,
        "error": last,
        "data": {},
        "turns": 0,
        "model": None,
        "wall_s": 0,
        "attempts": ATTEMPTS,
    }


def elephant_prompt(ticket: str, cited: str) -> str:
    return (
        "You are the Elephant. You draft a build spec from the ticket. "
        "You do not review it.\n"
        "Tools are off. Do not call tools. Do not ask a question.\n"
        "Use only the ticket and the cited excerpts. Do not add a requirement "
        "that is not written there.\n"
        "Restate every numbered requirement. Do not drop one.\n"
        "Do not choose an answer for an unstated choice. List those choices.\n"
        "Write plain sentences. Do not use an em dash.\n\n"
        "Return JSON with keys spec and unstated.\n"
        "spec is markdown with these headings: Problem, Required behavior, "
        "Files named, Tests named.\n"
        "unstated is an array of short strings, one per choice the ticket "
        "does not settle.\n\n"
        "TICKET\n---\n%s\n---\nCITED EXCERPTS\n---\n%s\n---\n" % (ticket, cited)
    )


def goldfish_prompt(persona: str, instructions: str, spec: str, cited: str) -> str:
    return (
        "You are a Goldfish reviewer. This is a fresh process. "
        "You have no earlier conversation.\n"
        "Tools are off. Do not call tools.\n"
        "You may use only the spec and the cited excerpts below. Mode is REVIEW.\n"
        "Persona: %s\n\n%s\n\n"
        "Return JSON with key findings. Each finding has severity "
        "(Blocker, Major, or Nit), scope, and finding.\n"
        "At most 6 findings. If the spec is actionable and matches the "
        "excerpts, return an empty array.\n"
        "Do not flag a file as missing when the spec says it is a proposed change.\n"
        "Do not use an em dash.\n\n"
        "SPEC\n---\n%s\n---\nCITED EXCERPTS\n---\n%s\n---\n"
        % (persona, instructions, spec, cited)
    )


def normalize_findings(data: dict) -> list[dict]:
    raw = data.get("findings")
    if not isinstance(raw, list):
        raise ValueError("findings is not a list")
    out = []
    for item in raw[:6]:
        if not isinstance(item, dict):
            raise ValueError("finding is not an object")
        severity = str(item.get("severity") or "")
        if severity not in {"Blocker", "Major", "Nit"}:
            raise ValueError("severity is not Blocker, Major, or Nit")
        out.append(
            {
                "severity": severity,
                "scope": str(item.get("scope") or "")[:240],
                "finding": str(item.get("finding") or "")[:800],
            }
        )
    return out


def review(ticket_path: Path, cited_path: Path, out_path: Path, scratch: Path, max_turns: int, personas: list[str]) -> int:
    binary = grok_bin()
    report: dict = {
        "ok": False,
        "ticket": str(ticket_path),
        "cited": str(cited_path),
        "grok_bin": binary,
        "max_turns": max_turns,
        "personas": personas,
        "elephant": {},
        "goldfish": [],
        "wall_s": 0,
        "error": "",
    }
    started = time.monotonic()
    code = 1
    try:
        if not Path(binary).is_file():
            report["error"] = "grok binary is missing: %s" % binary
            code = 2
            return code
        if not ticket_path.is_file() or not cited_path.is_file():
            report["error"] = "ticket or cited file is missing"
            code = 2
            return code
        ticket = ticket_path.read_text(encoding="utf-8")
        cited = cited_path.read_text(encoding="utf-8")
        elephant_dir = scratch / "elephant"
        elephant_dir.mkdir(parents=True, exist_ok=True)
        (elephant_dir / "ticket.md").write_text(ticket, encoding="utf-8")
        (elephant_dir / "cited.md").write_text(cited, encoding="utf-8")
        elephant = call_with_retry(
            binary,
            max_turns,
            elephant_prompt(ticket, cited),
            ELEPHANT_SCHEMA,
            elephant_dir,
        )
        spec = ""
        unstated: list[str] = []
        if elephant.get("ok"):
            data = elephant.get("data") or {}
            spec = data.get("spec") if isinstance(data.get("spec"), str) else ""
            raw_unstated = data.get("unstated")
            if isinstance(raw_unstated, list):
                unstated = [str(item)[:240] for item in raw_unstated[:12]]
            if not spec.strip():
                elephant["ok"] = False
                elephant["error"] = "elephant returned an empty spec"
        report["elephant"] = {
            "ok": bool(elephant.get("ok")),
            "turns": elephant.get("turns") or 0,
            "wall_s": elephant.get("wall_s") or 0,
            "attempts": elephant.get("attempts") or 0,
            "model": elephant.get("model"),
            "error": elephant.get("error") or "",
            "spec": spec,
            "unstated": unstated,
        }
        if not elephant.get("ok"):
            report["error"] = "elephant failed: %s" % (elephant.get("error") or "empty spec")
            code = 1
            return code
        rows = []

        def one(name: str) -> dict:
            role_dir = scratch / name
            role_dir.mkdir(parents=True, exist_ok=True)
            (role_dir / "spec.md").write_text(spec, encoding="utf-8")
            (role_dir / "cited.md").write_text(cited, encoding="utf-8")
            got = call_with_retry(
                binary,
                max_turns,
                goldfish_prompt(name, PERSONAS[name], spec, cited),
                GOLDFISH_SCHEMA,
                role_dir,
            )
            findings: list[dict] = []
            error = got.get("error") or ""
            ok = bool(got.get("ok"))
            if ok:
                try:
                    findings = normalize_findings(got.get("data") or {})
                except ValueError as exc:
                    ok = False
                    error = scrub(str(exc))
            return {
                "persona": name,
                "ok": ok,
                "turns": got.get("turns") or 0,
                "wall_s": got.get("wall_s") or 0,
                "attempts": got.get("attempts") or 0,
                "model": got.get("model"),
                "error": error,
                "findings": findings,
            }

        with ThreadPoolExecutor(max_workers=len(personas)) as pool:
            rows = list(pool.map(one, personas))
        report["goldfish"] = rows
        failed = [row["persona"] for row in rows if not row["ok"]]
        if failed:
            report["error"] = "reviewer failed: %s" % ", ".join(failed)
            code = 1
            return code
        report["ok"] = True
        report["error"] = ""
        code = 0
        return code
    finally:
        report["wall_s"] = round(time.monotonic() - started, 3)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if code == 2 and str(report["error"]).startswith("grok binary is missing"):
            print(
                "next step: set PFY_GROK_BIN to a grok binary, or install grok "
                "on PATH as ~/.local/bin/grok. Do not install the EGM plugin "
                "into an agent home. %s" % report["error"],
                file=sys.stderr,
            )
        elif code == 2:
            print("next step: %s" % report["error"], file=sys.stderr)
        elif code == 1:
            print(
                "Rerun scripts/egm_review.py after the reviewer process succeeds. "
                "Partial findings are in %s. %s" % (out_path, report["error"]),
                file=sys.stderr,
            )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Advisory Elephant-Goldfish review")
    parser.add_argument("--ticket", required=True, type=Path)
    parser.add_argument("--cited", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--max-turns", type=int, default=2)
    parser.add_argument(
        "--personas",
        default="readiness,critic,codebase",
        help="Comma-separated goldfish names",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.max_turns < 1 or args.max_turns > MAX_TURNS:
        print("refusing max-turns %s (cap %s)" % (args.max_turns, MAX_TURNS), file=sys.stderr)
        return 2
    personas = [part.strip() for part in args.personas.split(",") if part.strip()]
    unknown = [name for name in personas if name not in PERSONAS]
    if not personas or unknown:
        print("unknown personas: %s" % ", ".join(unknown), file=sys.stderr)
        return 2
    scratch = args.scratch
    if scratch is None:
        scratch = Path(tempfile.mkdtemp(prefix="egm-review-"))
    return review(args.ticket, args.cited, args.out, scratch, args.max_turns, personas)


if __name__ == "__main__":
    sys.exit(main())
