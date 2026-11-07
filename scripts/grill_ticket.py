#!/usr/bin/env python3
"""Grill a ticket before it is cut, only when it touches CI, pipeline, or gate files.

One tools-off grok call asks the questions. A second tools-off call (or
--answers) accepts or overrides them. Answers that change behavior are written
back as exit tests, and the full record lands in <ticket>.grill.json.

The turn cap is 12 for both calls together. A higher --max-turns is rejected
before any model call. If the ticket does not hit the trigger list, the
process prints "no grill needed" and exits 0 without calling grok.

Recovery: a grok failure, a timeout, or a behavior-changing answer with no
executable test leaves the ticket unchanged and exits non-zero. Run the
command again after fixing the ticket or the answers file. A second successful
run replaces the previous "Exit tests from grill" section instead of stacking
another copy.

Usage:
  python3 scripts/grill_ticket.py TICKET [--paths P ...] [--diff REF]
      [--answers FILE] [--max-turns N] [--repo DIR]
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MAX_CAP = 12
CALL_TIMEOUT_S = 600

# Shell-route tool ids verified on nimo with grok 1.0.77 (2026-11-07).
# An empty --tools is ignored. An unknown --tools name keeps the full toolset.
# This denylist plus the flags in grok_argv left tool_definitions empty.
TOOLS_OFF_DISALLOW = (
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

# Path triggers. Makefile is not in this list: only its CI/test targets count.
TRIGGER_GLOBS = (
    ".github/workflows/**",
    "ci/**",
    "pipelines/**",
    "scripts/pregate*",
    "scripts/run_tests.py",
    "scripts/test_select.py",
    "scripts/test_cache.py",
    "scripts/*gate*",
    "scripts/model_lock.sh",
    "docs/ops/MODULAR-CI.md",
    "docs/ops/PREGATE.md",
)

TEXT_NEEDLES = (
    ".github/workflows",
    "docs/ops/MODULAR-CI.md",
    "docs/ops/PREGATE.md",
    "scripts/run_tests.py",
    "scripts/test_select.py",
    "scripts/test_cache.py",
    "scripts/model_lock.sh",
    "scripts/pregate",
    "run_tests.py",
    "test_select.py",
    "test_cache.py",
    "model_lock.sh",
    "pregate",
    "pipelines/",
    "ci/",
)

_CI_TARGET = re.compile(
    r"(^|[-_])(test|tests|ci|gate|pregate|smoke|lint)($|[-_])|pregate|eval-structural",
    re.IGNORECASE,
)

EMBEDDED_SKILL = """\
Grilling (embedded summary; the vendored skill file was not on disk):
Interview the plan in one round. Ask every question you can ask now without
guessing at an answer you do not have. Number each question, word it so yes
accepts your recommended answer, and give that recommended answer. For each
question decide whether the answer changes behavior. If it does, give a
concrete testable assertion and a Python unittest module that fails until
that behavior exists. One round only. Do not explore and do not call tools.
"""

EMBEDDED_MODULAR_CI = """\
Modular CI (standing rule): run only the tests your change can affect while
you work, the selected or full suite once at the end; no new serialized or
long CI job unless it is bound by local-model token speed; light jobs run in
parallel. Do not add a step that re-runs work another step already did.
"""

SECTION = "## Exit tests from grill"
SKILL_REL = Path("bootstrap/grok-cli/skills-external/mattpocock/grilling/SKILL.md")

QUESTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["questions"],
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["n", "question", "recommended_answer", "behavior_change"],
                "properties": {
                    "n": {"type": "integer"},
                    "question": {"type": "string"},
                    "recommended_answer": {"type": "string"},
                    "behavior_change": {"type": "boolean"},
                    "assertion": {"type": "string"},
                    "test_path": {"type": "string"},
                    "test_content": {"type": "string"},
                },
            },
        }
    },
}

ANSWER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answers"],
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["n", "decision", "answer", "behavior_change"],
                "properties": {
                    "n": {"type": "integer"},
                    "decision": {"type": "string", "enum": ["accept", "override"]},
                    "answer": {"type": "string"},
                    "behavior_change": {"type": "boolean"},
                    "assertion": {"type": "string"},
                    "test_path": {"type": "string"},
                    "test_content": {"type": "string"},
                },
            },
        }
    },
}


class GrillError(Exception):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def skill_text(root: Path) -> tuple[str, str]:
    path = root / SKILL_REL
    if path.is_file():
        return path.read_text(encoding="utf-8"), f"vendored:{SKILL_REL.as_posix()}"
    return EMBEDDED_SKILL, "embedded"


def extract_modular_ci(text: str) -> str | None:
    lines = text.splitlines()
    start = None
    level = None
    for i, line in enumerate(lines):
        m = re.match(r"^(#+)\s+(.*)$", line)
        if not m:
            continue
        if start is None and re.search(r"modular\s+ci", m.group(2), re.I):
            start = i
            level = len(m.group(1))
            continue
        if start is not None and len(m.group(1)) <= (level or 1):
            return "\n".join(lines[start:i]).strip()
    if start is not None:
        return "\n".join(lines[start:]).strip()
    return None


def modular_ci_text(repo: Path, script_repo: Path) -> tuple[str, str]:
    """Single source: AGENTS.md section, else MODULAR-CI.md, else embedded."""
    for root in (repo, script_repo):
        agents = root / "AGENTS.md"
        if agents.is_file():
            section = extract_modular_ci(agents.read_text(encoding="utf-8", errors="replace"))
            if section:
                return section[:8000], f"{agents}:Modular CI"
        doc = root / "docs/ops/MODULAR-CI.md"
        if doc.is_file():
            return doc.read_text(encoding="utf-8", errors="replace")[:8000], str(doc)
    return EMBEDDED_MODULAR_CI, "embedded"


def _norm(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def path_hits(path: str) -> bool:
    p = _norm(path)
    if p.startswith(".github/workflows/") or p == ".github/workflows":
        return True
    if p == "ci" or p.startswith("ci/"):
        return True
    if p == "pipelines" or p.startswith("pipelines/"):
        return True
    if p in {
        "scripts/run_tests.py",
        "scripts/test_select.py",
        "scripts/test_cache.py",
        "scripts/model_lock.sh",
        "docs/ops/MODULAR-CI.md",
        "docs/ops/PREGATE.md",
    }:
        return True
    if p.startswith("scripts/"):
        base = p.split("/", 1)[1]
        if fnmatch_gate(base):
            return True
    return False


def fnmatch_gate(base: str) -> bool:
    """scripts/pregate* and scripts/*gate* on the filename, one path segment."""
    if "/" in base:
        return False
    if base.startswith("pregate"):
        return True
    return "gate" in base


def _ci_target(name: str) -> bool:
    base = name.split("/")[-1].lower()
    if base in {"eval-structural", "cage-test"}:
        return True
    return _CI_TARGET.search(base) is not None


def _makefile_blob_hits(blob: str) -> bool:
    for line in blob.splitlines():
        stripped = line.strip().lstrip("+-")
        target = re.match(r"^([\w.%-]+)\s*:", stripped)
        if target and _ci_target(target.group(1)):
            return True
        invoked = re.search(r"\bmake\s+([\w./%-]+)", stripped)
        if invoked and _ci_target(invoked.group(1)):
            return True
    return False


def text_hits(text: str) -> bool:
    for needle in TEXT_NEEDLES:
        if needle in text:
            return True
    if "Makefile" in text and _makefile_blob_hits(text):
        return True
    for tok in re.findall(r"[\w./~*-]+", text):
        if path_hits(tok):
            return True
    return False


def makefile_change_hits(diff_text: str, ticket_text: str) -> bool:
    if _makefile_blob_hits(diff_text):
        return True
    return "Makefile" in ticket_text and _makefile_blob_hits(ticket_text)


def needs_grill(paths: list[str], ticket_text: str, makefile_diff: str = "") -> bool:
    for p in paths:
        if _norm(p) in {"Makefile", "makefile"} or _norm(p).endswith("/Makefile"):
            if makefile_change_hits(makefile_diff, ticket_text):
                return True
            continue
        if path_hits(p):
            return True
    return text_hits(ticket_text)


def grok_bin() -> str:
    return os.environ.get("PFY_GROK_BIN") or str(Path.home() / ".local/bin/grok")


def grok_argv(max_turns: int, prompt_file: Path, schema: dict) -> list[str]:
    if max_turns < 1 or max_turns > MAX_CAP:
        raise GrillError(f"refusing grok call with max-turns {max_turns}")
    return [
        grok_bin(),
        "--output-format", "json",
        "--max-turns", str(max_turns),
        # Default on grok 1.0.77 is xhigh. xhigh and medium stayed in
        # streaming_reasoning (300s and 7 min) and returned no questions.
        # low returns the JSON. --verbatim sends this prompt as given.
        "--reasoning-effort", "low",
        "--verbatim",
        "--no-plan",
        "--disable-web-search",
        "--no-subagents",
        "--disallowed-tools", ",".join(TOOLS_OFF_DISALLOW),
        "--json-schema", json.dumps(schema, separators=(",", ":")),
        "--prompt-file", str(prompt_file),
    ]


def grok_env() -> dict[str, str]:
    env = dict(os.environ)
    env["GROK_WORKFLOWS"] = "0"
    env["GROK_SUBAGENTS"] = "0"
    return env


def _scrub(text: str) -> str:
    kept = []
    for line in text.splitlines():
        if re.search(r"(authorization|bearer |api[_-]?key|secret|password|cookie)", line, re.I):
            kept.append("[redacted]")
        else:
            kept.append(line)
    return "\n".join(kept)[:800]


def call_grok(max_turns: int, prompt: str, schema: dict) -> dict:
    # Always under /tmp. A TMPDIR inside a checkout would make grok load that
    # repo's AGENTS.md. HOME stays the caller's so login still works.
    with tempfile.TemporaryDirectory(prefix="grill-", dir="/tmp") as tmp:
        prompt_path = Path(tmp) / "prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        argv = grok_argv(max_turns, prompt_path, schema)
        try:
            proc = subprocess.run(
                argv,
                cwd=tmp,
                env=grok_env(),
                capture_output=True,
                text=True,
                timeout=CALL_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GrillError(f"grok timed out after {CALL_TIMEOUT_S}s") from exc
        except OSError as exc:
            raise GrillError(f"could not run grok ({grok_bin()}): {exc}") from exc
    if proc.returncode != 0:
        raise GrillError(
            f"grok exited {proc.returncode}: {_scrub(proc.stderr or proc.stdout or '')}"
        )
    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise GrillError(f"grok stdout was not JSON: {_scrub(proc.stdout)}") from exc
    structured = _structured(envelope)
    usage = envelope.get("usage") if isinstance(envelope.get("usage"), dict) else {}
    models = list((envelope.get("modelUsage") or {}).keys()) if isinstance(envelope.get("modelUsage"), dict) else []
    return {
        "data": structured,
        "turns": int(envelope.get("num_turns") or 0),
        "cost_usd": float(envelope.get("total_cost_usd") or 0),
        "stop": envelope.get("stopReason"),
        "model": models[0] if models else None,
    }


def _structured(envelope: dict) -> dict:
    text = envelope.get("text")
    if isinstance(text, dict):
        return text
    if not isinstance(text, str) or not text.strip():
        raise GrillError("grok JSON had no text")
    body = text.strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body)
        body = re.sub(r"\s*```$", "", body)
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise GrillError(f"grok text was not JSON: {_scrub(body)}") from exc
    if not isinstance(parsed, dict):
        raise GrillError("grok text JSON was not an object")
    return parsed


def _bool(value: object, where: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise GrillError(f"{where} behavior_change is not a boolean")


def _questions(data: dict) -> list[dict]:
    raw = data.get("questions")
    if not isinstance(raw, list) or not raw:
        raise GrillError("grill returned no questions")
    out = []
    for item in raw:
        if not isinstance(item, dict):
            raise GrillError("question was not an object")
        try:
            n = int(item["n"])
        except (KeyError, TypeError, ValueError) as exc:
            raise GrillError("question missing n") from exc
        behavior = _bool(item.get("behavior_change"), f"Q{n}")
        assertion = str(item.get("assertion") or "")
        if behavior and not assertion.strip():
            raise GrillError(f"Q{n} changes behavior but has no assertion")
        out.append({
            "n": n,
            "question": str(item.get("question") or "").strip(),
            "recommended_answer": str(item.get("recommended_answer") or "").strip(),
            "behavior_change": behavior,
            "assertion": assertion.strip(),
            "test_path": str(item.get("test_path") or ""),
            "test_content": str(item.get("test_content") or ""),
        })
    return out


def _safe_test_path(path: str, n: int) -> str:
    raw = (path or f"tests/test_grill_q{n}.py").replace("\\", "/").lstrip("/")
    if raw.startswith("../") or "/../" in f"/{raw}" or raw == "..":
        raise GrillError(f"Q{n} test path escapes the tree")
    if not raw.endswith(".py"):
        raw += ".py"
    return raw


def load_answers(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GrillError(f"cannot read answers file: {exc}") from exc
    raw = data.get("answers") if isinstance(data, dict) else data
    if not isinstance(raw, list):
        raise GrillError("answers file needs an answers list")
    return raw


def resolve_answers(questions: list[dict], supplied: list[dict]) -> list[dict]:
    by_n = {q["n"]: q for q in questions}
    seen = set()
    out = []
    for item in supplied:
        if not isinstance(item, dict) or "n" not in item:
            raise GrillError("answer missing n")
        n = int(item["n"])
        if n not in by_n:
            raise GrillError(f"answer for unknown question {n}")
        seen.add(n)
        q = by_n[n]
        decision = str(item.get("decision") or "accept")
        if decision not in {"accept", "override"}:
            raise GrillError(f"Q{n} decision must be accept or override")
        if decision == "accept":
            behavior = _bool(item["behavior_change"], f"Q{n}") if "behavior_change" in item else q["behavior_change"]
            answer = str(item.get("answer") or q["recommended_answer"])
            assertion = str(item.get("assertion") or q["assertion"])
            test_path = str(item.get("test_path") or q["test_path"])
            test_content = str(item.get("test_content") or q["test_content"])
        else:
            if "behavior_change" not in item or "answer" not in item:
                raise GrillError(f"Q{n} override needs answer and behavior_change")
            behavior = _bool(item["behavior_change"], f"Q{n}")
            answer = str(item.get("answer") or "")
            assertion = str(item.get("assertion") or "")
            test_path = str(item.get("test_path") or "")
            test_content = str(item.get("test_content") or "")
        if behavior and not assertion.strip():
            raise GrillError(f"Q{n} changes behavior but has no assertion")
        out.append({
            "n": n,
            "decision": decision,
            "answer": answer.strip(),
            "behavior_change": behavior,
            "assertion": assertion.strip(),
            "test_path": test_path,
            "test_content": test_content,
        })
    missing = [n for n in by_n if n not in seen]
    if missing:
        raise GrillError(f"answers missing questions {missing}")
    return out


def question_prompt(skill: str, ticket: str, paths: list[str], rule: str) -> str:
    path_block = "\n".join(paths) if paths else "(none parsed)"
    return f"""{skill}

You are grilling this ticket before it is cut. Tools are off. Ask one round, then stop.
Include these seeds as numbered questions, each with your recommended answer:
- software-factory Q5: What stops two runs doing the same work?
- Does this change obey the Modular CI rule below?

Modular CI rule:
{rule}

Touched paths:
{path_block}

Ticket:
{ticket}

Return only the JSON object. When behavior_change is false, assertion is an empty string.
When behavior_change is true, assertion is one concrete testable sentence, test_path is a
relative tests/*.py path, and test_content is a complete Python unittest module that fails
until that behavior exists. Do not include secrets.
"""


def coordinator_prompt(rule: str, questions: list[dict]) -> str:
    return f"""You are the coordinator, not the human who filed the ticket.
Accept or override each recommended answer using the rules below.
Prefer the recommended answer when it does not contradict the rules.
Do not weaken checks on trading, live money, release, deploy, or secrets.
Do not add a step that re-runs work another step already did.

Modular CI rule:
{rule}

Questions:
{json.dumps(questions, indent=2)}

Return only the JSON object. decision is "accept" or "override".
When you accept, copy the recommended answer, behavior_change, assertion, test_path, and test_content.
When behavior_change is true, keep a concrete assertion and the executable test_content.
"""


def _md_section(answers: list[dict]) -> str:
    parts = [
        SECTION,
        "",
        "Fixed by the coordinator before Build. Do not edit this section.",
        "",
    ]
    for a in answers:
        if not a["behavior_change"]:
            continue
        parts.append(f"### Q{a['n']}")
        parts.append("")
        parts.append(f"- Answer: {a['answer']}")
        parts.append("- Behavior change: true")
        parts.append(f"- Assertion: {a['assertion']}")
        parts.append("")
        if a["test_content"].strip():
            parts.append(f"Test path: `{_safe_test_path(a['test_path'], a['n'])}`")
            parts.append("")
            parts.append("```python")
            parts.append(a["test_content"].rstrip())
            parts.append("```")
            parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def apply_markdown(text: str, answers: list[dict]) -> tuple[str, list[dict]]:
    changing = [a for a in answers if a["behavior_change"]]
    body = text
    if SECTION in body:
        body = body[:body.index(SECTION)].rstrip() + "\n"
    if not changing:
        return body.rstrip() + "\n", []
    return body.rstrip() + "\n\n" + _md_section(answers), changing


def apply_json_ticket(ticket: dict, answers: list[dict]) -> list[dict]:
    changing = [a for a in answers if a["behavior_change"]]
    existing = list(ticket.get("exitTests") or [])
    if not existing and isinstance(ticket.get("exitTest"), dict):
        existing = [dict(ticket["exitTest"])]
    kept = [item for item in existing if not (isinstance(item, dict) and item.get("fromGrill"))]
    added = []
    used = {item.get("path") for item in kept if isinstance(item, dict)}
    for a in changing:
        if not str(a.get("test_content") or "").strip():
            raise GrillError(f"Q{a['n']} changes behavior but has no executable test_content")
        path = _safe_test_path(a["test_path"], a["n"])
        if path in used:
            path = _safe_test_path(f"tests/test_grill_q{a['n']}.py", a["n"])
        case = {
            "path": path,
            "content": a["test_content"] if a["test_content"].endswith("\n") else a["test_content"] + "\n",
            "fromGrill": True,
            "assertion": a["assertion"],
            "n": a["n"],
        }
        kept.append(case)
        added.append(case)
        used.add(path)
    if added:
        ticket["exitTests"] = kept
    elif "exitTests" in ticket:
        ticket["exitTests"] = kept
    return added


def diff_names(repo: Path, ref: str) -> tuple[list[str], str]:
    try:
        names = subprocess.run(
            ["git", "diff", "--name-only", ref],
            cwd=repo, capture_output=True, text=True, check=False,
        )
        makefile = subprocess.run(
            ["git", "diff", "-U0", ref, "--", "Makefile", "makefile"],
            cwd=repo, capture_output=True, text=True, check=False,
        )
    except OSError as exc:
        raise GrillError(f"git diff failed: {exc}") from exc
    if names.returncode != 0:
        raise GrillError(f"git diff failed: {_scrub(names.stderr)}")
    paths = [line for line in names.stdout.splitlines() if line.strip()]
    return paths, makefile.stdout


def load_ticket(path: Path) -> tuple[str, object]:
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return "markdown", raw
    if isinstance(data, list):
        return "batch-list", data
    if isinstance(data, dict) and isinstance(data.get("tickets"), list):
        return "batch", data
    if isinstance(data, dict) and "body" in data:
        return "ticket", data
    return "markdown", raw


def ticket_text(kind: str, data: object) -> str:
    if kind == "markdown":
        return str(data)
    if kind == "ticket":
        item = data if isinstance(data, dict) else {}
        return f"{item.get('title', '')}\n{item.get('body', '')}"
    items = data if kind == "batch-list" else (data.get("tickets") if isinstance(data, dict) else [])
    chunks = []
    for item in items or []:
        if isinstance(item, dict):
            chunks.append(f"{item.get('title', '')}\n{item.get('body', '')}")
    return "\n".join(chunks)


def paths_from_text(text: str) -> list[str]:
    found = []
    for tok in re.findall(r"(?:[\w.-]+/)+[\w.*-]+|Makefile", text):
        found.append(tok.strip(".,)`'\""))
    return found


def parse_cap(argv: list[str]) -> int:
    if "--max-turns" not in argv:
        return MAX_CAP
    i = argv.index("--max-turns")
    if i + 1 >= len(argv):
        raise GrillError("--max-turns needs a number")
    try:
        n = int(argv[i + 1])
    except ValueError as exc:
        raise GrillError("--max-turns must be an integer") from exc
    if n > MAX_CAP:
        raise GrillError(f"max-turns cap is {MAX_CAP}, got {n}")
    if n < 1:
        raise GrillError("max-turns must be at least 1")
    return n


def split_turns(cap: int, has_answers: bool) -> tuple[int, int]:
    if has_answers:
        return cap, 0
    if cap < 2:
        raise GrillError("need at least 2 turns for the question call and the coordinator, or pass --answers")
    return cap - 1, 1


def _one(text_or_ticket: object, kind: str, paths: list[str], makefile_diff: str,
         skill: str, skill_source: str, rule: str, rule_source: str,
         cap: int, answers_path: Path | None) -> dict:
    if kind == "markdown":
        body = str(text_or_ticket)
        label = body
    else:
        body = text_or_ticket if isinstance(text_or_ticket, dict) else {}
        label = f"{body.get('title', '')}\n{body.get('body', '')}"
    local_paths = list(paths) + paths_from_text(label)
    if not needs_grill(local_paths, label, makefile_diff):
        return {"needed": False, "turns": 0, "cost_usd": 0, "exit_tests": []}
    q_turns, c_turns = split_turns(cap, answers_path is not None)
    asked = call_grok(q_turns, question_prompt(skill, label, local_paths, rule), QUESTION_SCHEMA)
    questions = _questions(asked["data"])
    calls = [{"role": "grill", "turns": asked["turns"], "cost_usd": asked["cost_usd"],
              "stop": asked["stop"], "model": asked["model"], "max_turns": q_turns}]
    if answers_path is not None:
        answers = resolve_answers(questions, load_answers(answers_path))
    else:
        coord = call_grok(c_turns, coordinator_prompt(rule, questions), ANSWER_SCHEMA)
        raw = coord["data"].get("answers")
        if not isinstance(raw, list):
            raise GrillError("coordinator returned no answers")
        answers = resolve_answers(questions, raw)
        calls.append({"role": "coordinator", "turns": coord["turns"], "cost_usd": coord["cost_usd"],
                      "stop": coord["stop"], "model": coord["model"], "max_turns": c_turns})
    if kind == "markdown":
        new_text, changing = apply_markdown(str(text_or_ticket), answers)
        exit_rows = [{"n": a["n"], "assertion": a["assertion"],
                      "test_path": _safe_test_path(a["test_path"], a["n"]) if a["test_content"].strip() else ""}
                     for a in changing]
        return {
            "needed": True,
            "markdown": new_text,
            "questions": questions,
            "answers": answers,
            "exit_tests": exit_rows,
            "turns": sum(c["turns"] for c in calls),
            "cost_usd": sum(c["cost_usd"] for c in calls),
            "calls": calls,
            "skill_source": skill_source,
            "modular_ci_source": rule_source,
            "flags": ["--disable-web-search", "--no-subagents", "--no-plan", "--disallowed-tools"],
        }
    added = apply_json_ticket(body, answers)  # type: ignore[arg-type]
    return {
        "needed": True,
        "questions": questions,
        "answers": answers,
        "exit_tests": [{"n": a["n"], "path": a["path"], "assertion": a["assertion"]} for a in added],
        "turns": sum(c["turns"] for c in calls),
        "cost_usd": sum(c["cost_usd"] for c in calls),
        "calls": calls,
        "skill_source": skill_source,
        "modular_ci_source": rule_source,
        "flags": ["--disable-web-search", "--no-subagents", "--no-plan", "--disallowed-tools"],
    }


def run(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in {"-h", "--help"}:
        print(__doc__)
        return 2 if len(argv) < 2 else 0
    ticket_path = Path(argv[1])
    if not ticket_path.is_file():
        raise GrillError(f"ticket not found: {ticket_path}")
    paths: list[str] = []
    diff_ref = None
    answers = None
    repo = Path.cwd()
    i = 2
    while i < len(argv):
        flag = argv[i]
        if flag == "--paths":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                paths.append(argv[i])
                i += 1
            continue
        if flag in {"--diff", "--answers", "--repo", "--max-turns"}:
            if i + 1 >= len(argv):
                raise GrillError(f"{flag} needs a value")
            value = argv[i + 1]
            if flag == "--diff":
                diff_ref = value
            elif flag == "--answers":
                answers = Path(value)
            elif flag == "--repo":
                repo = Path(value)
            i += 2
            continue
        raise GrillError(f"unknown argument {flag}")
    cap = parse_cap(argv)
    kind, data = load_ticket(ticket_path)
    text = ticket_text(kind, data)
    makefile_diff = ""
    if diff_ref:
        diff_paths, makefile_diff = diff_names(repo, diff_ref)
        paths = paths + diff_paths
    # Explicit paths (--paths, --diff) are shared. Each ticket also sees its own text.
    if not needs_grill(paths + paths_from_text(text), text, makefile_diff):
        print("no grill needed")
        return 0
    root = repo_root()
    skill, skill_source = skill_text(root)
    rule, rule_source = modular_ci_text(repo, root)
    if kind == "markdown":
        result = _one(data, "markdown", paths, makefile_diff, skill, skill_source, rule, rule_source, cap, answers)
        if not result.get("needed"):
            print("no grill needed")
            return 0
        ticket_path.write_text(result.pop("markdown"), encoding="utf-8")
        record = {"ticket": str(ticket_path), **result}
    elif kind == "ticket":
        result = _one(data, "ticket", paths, makefile_diff, skill, skill_source, rule, rule_source, cap, answers)
        if not result.get("needed"):
            print("no grill needed")
            return 0
        ticket_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        record = {"ticket": str(ticket_path), **result}
    else:
        items = data if kind == "batch-list" else data["tickets"]  # type: ignore[index]
        per = []
        any_needed = False
        for item in items:
            if not isinstance(item, dict):
                continue
            one = _one(item, "ticket", paths, makefile_diff, skill, skill_source, rule, rule_source, cap, answers)
            one["id"] = item.get("id")
            per.append(one)
            any_needed = any_needed or bool(one.get("needed"))
        if not any_needed:
            print("no grill needed")
            return 0
        text_out = json.dumps(data, indent=2) + "\n"
        if kind == "batch-list":
            text_out = json.dumps(items, indent=2) + "\n"
        ticket_path.write_text(text_out, encoding="utf-8")
        record = {
            "ticket": str(ticket_path),
            "skill_source": skill_source,
            "modular_ci_source": rule_source,
            "turns": sum(int(p.get("turns") or 0) for p in per),
            "cost_usd": sum(float(p.get("cost_usd") or 0) for p in per),
            "exit_tests": [row for p in per for row in p.get("exit_tests") or []],
            "tickets": per,
        }
    record_path = Path(str(ticket_path) + ".grill.json")
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(
        f"grill ok questions={len(record.get('questions') or record.get('exit_tests') or [])} "
        f"exit_tests={len(record.get('exit_tests') or [])} "
        f"turns={record.get('turns')} cost={record.get('cost_usd')}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv if argv is not None else sys.argv)
    except GrillError as exc:
        print(f"grill failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
