#!/usr/bin/env python3
"""Local solo vs coder/reviewer trial for catalog entry 194.

Deanery check wrapper for the multi-agents address shape. It does not install
the upstream package. The default worker is sdk@litellm/ollama/qwen3.6:35b.
Chat goes to a local Ollama /api/chat. That path is priced at $0, so
--max-cost 0 is a normal local run. Paid providers and workers this trial
cannot price are refused before any model call. A missing local tag exits 2
and is not pulled. --repo is left untouched unless --apply is set and --repo
is under this worktree's tmp/. A finished run writes the JSON record and a
plain-text summary beside it (pass/fail per arm, tokens, cost_usd, seconds,
refused).

Usage (from the repo root):
  python3 examples/multiagents-trial/trial.py --max-cost 0
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib.model_choice import host_is_local  # noqa: E402

# Grading loads the task's test_task.py. Do not write __pycache__ into that checkout.
sys.dont_write_bytecode = True

DEFAULT_WORKER = "sdk@litellm/ollama/qwen3.6:35b"
DEFAULT_HOST = "http://127.0.0.1:11434"
PAID_HARNESS = {"claude", "codex"}
PAID_PROVIDER = {
    "openai",
    "anthropic",
    "claude",
    "xai",
    "x-ai",
    "grok",
    "openrouter",
    "gemini",
    "google",
    "azure",
    "azure_ai",
    "mistral",
    "cohere",
    "modal",
    "codex",
    "fireworks",
    "together",
    "together_ai",
    "groq",
    "deepseek",
    "vertex_ai",
    "bedrock",
    "sagemaker",
}
LOCAL_PROVIDER = {"ollama", "ollama_chat"}
CODER_SYSTEM = (
    "You write exactly one Python function. "
    "Output only the function source. No markdown fences."
)
REVIEWER_SYSTEM = (
    "You are the reviewer. The coder's function is below, with check failures. "
    "Return the full corrected function and nothing else."
)

_HARNESS = None


class Stop(Exception):
    def __init__(self, reason: str, code: int = 2):
        super().__init__(reason)
        self.reason = reason
        self.code = code


class Unpriced(Stop):
    def __init__(self, reason: str):
        super().__init__(reason, 2)


def _harness():
    global _HARNESS
    if _HARNESS is None:
        path = ROOT / "examples" / "eval-harness" / "run_scored_task.py"
        spec = importlib.util.spec_from_file_location("ma_trial_scored", path)
        if spec is None or spec.loader is None:
            raise Stop("cannot load the scored-task helper", 1)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _HARNESS = mod
    return _HARNESS


def under_tmp(path: Path) -> bool:
    try:
        path.resolve().relative_to((ROOT / "tmp").resolve())
    except ValueError:
        return False
    return True


def classify(spec: str) -> dict:
    text = (spec or "").strip()
    refused = {"address": text, "kind": "unpriced", "model": None, "provider": None}
    if "@" not in text:
        refused["reason"] = "unpriced worker refused: %s" % (text or "(empty)")
        return refused
    harness, rest = text.split("@", 1)
    harness_l = harness.strip().lower()
    rest = rest.strip()
    if harness_l in PAID_HARNESS:
        return {
            "address": text,
            "kind": "paid",
            "model": None,
            "provider": harness_l,
            "reason": "paid provider refused: %s" % text,
        }
    if harness_l != "sdk":
        refused["reason"] = "unpriced worker refused: %s" % text
        return refused
    if not rest.lower().startswith("litellm/"):
        return {
            "address": text,
            "kind": "paid",
            "model": rest or None,
            "provider": "openai",
            "reason": "paid provider refused: %s uses the OpenAI SDK client" % text,
        }
    parts = rest.split("/")
    provider = parts[1].lower() if len(parts) > 1 else ""
    model = "/".join(parts[2:]) if len(parts) > 2 else ""
    if not provider or not model:
        refused["reason"] = "unpriced worker refused: %s" % text
        return refused
    if provider in PAID_PROVIDER:
        return {
            "address": text,
            "kind": "paid",
            "model": model,
            "provider": provider,
            "reason": "paid provider refused: %s" % text,
        }
    if provider in LOCAL_PROVIDER:
        return {
            "address": text,
            "kind": "local",
            "model": model,
            "provider": provider,
            "reason": "",
        }
    refused["provider"] = provider
    refused["model"] = model
    refused["reason"] = "unpriced worker refused: %s" % text
    return refused


def normalize_host(raw: str | None) -> str:
    text = (raw or "").strip() or DEFAULT_HOST
    if "://" not in text:
        text = "http://" + text
    return text.rstrip("/")


def public_host(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = ":%d" % parsed.port if parsed.port else ""
    scheme = parsed.scheme or "http"
    return "%s://%s%s" % (scheme, host, port)


def _get_json(url: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise Stop("cannot list local tags; refusing to pull", 2)
    return data


def _post_json(url: str, payload: dict, timeout: float) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise Stop("local chat failed: response was not an object", 1)
    return data


def list_tags(host: str, timeout: float) -> list[str]:
    try:
        data = _get_json(host + "/api/tags", timeout)
    except (OSError, urllib.error.URLError, json.JSONDecodeError, UnicodeError, TimeoutError):
        raise Stop("cannot list local tags; refusing to pull", 2) from None
    names = []
    for row in data.get("models") or []:
        if isinstance(row, dict) and row.get("name"):
            names.append(str(row["name"]))
    return names


def chat(host: str, model: str, system: str, user: str, timeout: float) -> dict:
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    try:
        data = _post_json(host + "/api/chat", payload, timeout)
    except (OSError, urllib.error.URLError, json.JSONDecodeError, UnicodeError, TimeoutError) as exc:
        raise Stop("local chat failed: %s" % exc, 1) from None
    if "prompt_eval_count" not in data or "eval_count" not in data:
        raise Unpriced("unpriced local response: missing token counts")
    try:
        tokens_in = int(data["prompt_eval_count"])
        tokens_out = int(data["eval_count"])
    except (TypeError, ValueError):
        raise Unpriced("unpriced local response: missing token counts") from None
    cached_raw = data.get("prompt_cache_hit_tokens", 0) or 0
    try:
        cached = int(cached_raw)
    except (TypeError, ValueError):
        cached = 0
    message = data.get("message") if isinstance(data.get("message"), dict) else {}
    text = message.get("content") or ""
    if not isinstance(text, str):
        text = str(text)
    return {
        "text": text,
        "tokens_in": tokens_in,
        "tokens_cached": cached,
        "tokens_out": tokens_out,
    }


def grade(code: str, tests: Path, scratch: Path) -> list[str]:
    if not (code or "").strip():
        return ["empty model code"]
    held = scratch / "hidden_tests"
    held.mkdir(parents=True, exist_ok=True)
    local_tests = held / "test_task.py"
    # Read the task tests once and grade the copy, so the source tree is not imported.
    if not local_tests.exists() or local_tests.read_text(encoding="utf-8") != tests.read_text(encoding="utf-8"):
        local_tests.write_text(tests.read_text(encoding="utf-8"), encoding="utf-8")
    ns: dict = {}
    try:
        exec(compile(code, "<candidate>", "exec"), ns, ns)  # noqa: S102
    except Exception as exc:
        return ["compile/exec: %s: %s" % (type(exc).__name__, exc)]
    try:
        run_tests = _harness().load_tests(local_tests)
        return [str(item) for item in run_tests(ns)]
    except Exception as exc:
        return ["check failed: %s: %s" % (type(exc).__name__, exc)]


def extract(text: str) -> str:
    return _harness().extract_python(text or "")


def signature(root: Path) -> dict[str, str]:
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for name in filenames:
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _tree_changed(repo: Path | None, before: dict | None, before_git: str | None) -> bool:
    if repo is None:
        return False
    return signature(repo) != before or porcelain(repo) != before_git


def porcelain(repo: Path) -> str | None:
    if not (repo / ".git").exists():
        return None
    proc = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return proc.stdout


def _arm(passed: bool, fails: list[str], calls: list[dict], code: str, seconds: float) -> dict:
    return {
        "pass": passed,
        "failures": fails[:8],
        "calls": len(calls),
        "tokens_in": sum(item["tokens_in"] for item in calls),
        "tokens_cached": sum(item["tokens_cached"] for item in calls),
        "tokens_out": sum(item["tokens_out"] for item in calls),
        "cost_usd": 0,
        "seconds": seconds,
        "code": code,
    }


def run_solo(host: str, model: str, prompt: str, tests: Path, scratch: Path, timeout: float) -> dict:
    started = time.perf_counter()
    coder = chat(host, model, CODER_SYSTEM, prompt, timeout)
    code = extract(coder["text"])
    fails = grade(code, tests, scratch)
    return _arm(not fails, fails, [coder], code, time.perf_counter() - started)


def run_review(host: str, model: str, prompt: str, tests: Path, scratch: Path, timeout: float) -> dict:
    started = time.perf_counter()
    coder = chat(host, model, CODER_SYSTEM, prompt, timeout)
    coder_code = extract(coder["text"])
    coder_fails = grade(coder_code, tests, scratch)
    reviewer_user = (
        prompt
        + "\n\nCoder function:\n"
        + coder_code
        + "\n\nCheck failures:\n"
        + "\n".join(coder_fails)
    )
    reviewer = chat(host, model, REVIEWER_SYSTEM, reviewer_user, timeout)
    reviewer_code = extract(reviewer["text"])
    reviewer_fails = grade(reviewer_code, tests, scratch)
    if not reviewer_fails:
        code, fails, passed = reviewer_code, reviewer_fails, True
    elif not coder_fails:
        code, fails, passed = coder_code, coder_fails, True
    else:
        code, fails, passed = reviewer_code, reviewer_fails, False
    return _arm(passed, fails, [coder, reviewer], code, time.perf_counter() - started)


def compare(solo: dict, review: dict) -> dict:
    solo_pass = bool(solo["pass"])
    review_pass = bool(review["pass"])
    if solo_pass and not review_pass:
        winner = "solo"
    elif review_pass and not solo_pass:
        winner = "review"
    elif solo_pass and review_pass:
        winner = "tie"
    else:
        winner = "neither"
    return {
        "solo_pass": solo_pass,
        "review_pass": review_pass,
        "winner": winner,
        "extra_seconds": review["seconds"] - solo["seconds"],
        "extra_tokens": (review["tokens_in"] + review["tokens_out"])
        - (solo["tokens_in"] + solo["tokens_out"]),
    }


def _blank(worker: dict | None, max_cost, task: str | None) -> dict:
    local = bool(worker and worker.get("kind") == "local")
    return {
        "entry": 194,
        "tool": "multiagents-trial",
        "task": task,
        "address": None if worker is None else worker.get("address"),
        "model": None if worker is None else worker.get("model"),
        "provider": None if worker is None else worker.get("provider"),
        "local": local,
        "priced": False,
        "max_cost_usd": max_cost,
        "cost_usd": None,
        "applied": False,
        "refused": "",
    }


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Entry 194 local solo vs coder/reviewer trial.")
    parser.add_argument(
        "--task",
        default=str(ROOT / "examples" / "eval-harness" / "tasks" / "001-is-palindrome"),
    )
    parser.add_argument("--worker", default=DEFAULT_WORKER)
    parser.add_argument("--max-cost", type=float, default=None)
    parser.add_argument("--repo", default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--out", default=None)
    parser.add_argument("--scratch", default=None)
    parser.add_argument("--host", default=None)
    parser.add_argument("--timeout", type=float, default=180.0)
    return parser.parse_args(argv)


def summary_path(out: Path) -> Path:
    if out.suffix.lower() == ".json":
        sibling = out.with_suffix(".txt")
    else:
        sibling = out.with_name(out.name + ".txt")
    if sibling == out:
        sibling = out.with_name(out.name + ".summary.txt")
    return sibling


def _shown(value) -> str:
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, float):
        return format(value, ".6f")
    return str(value)


def render_summary(rec: dict) -> str:
    """Short plain text beside the JSON record. Blank fields stay blank."""
    lines = []
    arms = rec.get("arms") if isinstance(rec.get("arms"), dict) else {}
    for name in ("solo", "review"):
        arm = arms.get(name)
        if not isinstance(arm, dict):
            lines.append("%s: absent" % name)
            continue
        verdict = "pass" if arm.get("pass") else "fail"
        lines.append(
            "%s: %s tokens_in=%s tokens_cached=%s tokens_out=%s cost_usd=%s seconds=%s"
            % (
                name,
                verdict,
                _shown(arm.get("tokens_in")),
                _shown(arm.get("tokens_cached")),
                _shown(arm.get("tokens_out")),
                _shown(arm.get("cost_usd")),
                _shown(arm.get("seconds")),
            )
        )
    lines.append("tokens_in=%s" % _shown(rec.get("tokens_in")))
    lines.append("tokens_cached=%s" % _shown(rec.get("tokens_cached")))
    lines.append("tokens_out=%s" % _shown(rec.get("tokens_out")))
    lines.append("cost_usd=%s" % _shown(rec.get("cost_usd")))
    lines.append("seconds=%s" % _shown(rec.get("seconds")))
    lines.append("refused: %s" % (rec.get("refused") or ""))
    return "\n".join(lines) + "\n"


def emit(out: Path, rec: dict) -> None:
    if not under_tmp(out):
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    summary = summary_path(out)
    if under_tmp(summary) and summary.resolve() != out.resolve():
        summary.write_text(render_summary(rec), encoding="utf-8")


def execute(args: argparse.Namespace) -> tuple[int, dict, Path]:
    out = Path(args.out) if args.out else ROOT / "tmp" / "multiagents-trial" / "latest.json"
    scratch = Path(args.scratch) if args.scratch else ROOT / "tmp" / "multiagents-trial" / "scratch"
    if not under_tmp(out) or not under_tmp(scratch):
        raise Stop("refusing to write outside this repo's tmp/", 2)
    task = Path(args.task)
    worker = classify(args.worker)
    rec = _blank(worker, args.max_cost, task.name)
    if args.max_cost is None or not math.isfinite(args.max_cost) or args.max_cost < 0:
        rec["refused"] = "bad --max-cost" if args.max_cost is not None else "pass --max-cost (use 0 for a local run)"
        return 2, rec, out
    if worker["kind"] != "local":
        rec["refused"] = worker["reason"]
        return 2, rec, out
    repo = Path(args.repo) if args.repo else None
    if args.apply and (repo is None or not under_tmp(repo)):
        rec["refused"] = "refusing --apply outside this repo's tmp/; rerun without --apply"
        return 2, rec, out
    if repo is not None and not repo.is_dir():
        rec["refused"] = "repo is not a directory"
        return 2, rec, out
    prompt_path = task / "prompt.txt"
    tests_path = task / "test_task.py"
    if not prompt_path.is_file() or not tests_path.is_file():
        rec["refused"] = "task is missing prompt.txt or test_task.py"
        return 2, rec, out
    host = normalize_host(args.host or os.environ.get("OLLAMA_HOST") or DEFAULT_HOST)
    rec["host"] = public_host(host)
    if not host_is_local(host):
        rec["refused"] = "refusing non-local model host"
        return 2, rec, out
    before = signature(repo) if repo is not None else None
    before_git = porcelain(repo) if repo is not None else None
    names = list_tags(host, min(5.0, args.timeout if args.timeout > 0 else 5.0))
    if worker["model"] not in names:
        rec["refused"] = "local tag %s is not installed; refusing to pull" % worker["model"]
        return 2, rec, out
    prompt = prompt_path.read_text(encoding="utf-8")
    scratch.mkdir(parents=True, exist_ok=True)
    arms: dict[str, dict] = {}
    try:
        arms["solo"] = run_solo(host, worker["model"], prompt, tests_path, scratch, args.timeout)
        (scratch / "solo.py").write_text(arms["solo"]["code"], encoding="utf-8")
        arms["review"] = run_review(host, worker["model"], prompt, tests_path, scratch, args.timeout)
        (scratch / "review.py").write_text(arms["review"]["code"], encoding="utf-8")
    except Unpriced as exc:
        rec["arms"] = arms
        rec["refused"] = exc.reason
        rec["priced"] = False
        rec["cost_usd"] = None
        if _tree_changed(repo, before, before_git):
            rec["refused"] = "working tree changed during the run"
            return 1, rec, out
        return 2, rec, out
    if _tree_changed(repo, before, before_git):
        rec["arms"] = arms
        rec["refused"] = "working tree changed during the run"
        rec["priced"] = False
        rec["cost_usd"] = None
        return 1, rec, out
    solo = arms["solo"]
    review = arms["review"]
    rec.update(
        {
            "local": True,
            "priced": True,
            "cost_usd": 0,
            "applied": False,
            "seconds": solo["seconds"] + review["seconds"],
            "tokens_in": solo["tokens_in"] + review["tokens_in"],
            "tokens_cached": solo["tokens_cached"] + review["tokens_cached"],
            "tokens_out": solo["tokens_out"] + review["tokens_out"],
            "arms": arms,
            "comparison": compare(solo, review),
        }
    )
    rec.pop("refused", None)
    if args.apply:
        chosen = review if review["pass"] else solo if solo["pass"] else None
        if chosen is None:
            rec["refused"] = "no passing arm to apply"
            return 1, rec, out
        code = chosen["code"]
        if code and not code.endswith("\n"):
            code += "\n"
        (repo / "solution.py").write_text(code, encoding="utf-8")
        rec["applied"] = True
    return 0, rec, out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out = Path(args.out) if args.out else ROOT / "tmp" / "multiagents-trial" / "latest.json"
    try:
        code, rec, out = execute(args)
    except Stop as exc:
        worker = classify(getattr(args, "worker", DEFAULT_WORKER))
        task = Path(args.task).name if getattr(args, "task", None) else None
        rec = _blank(worker, args.max_cost, task)
        rec["refused"] = exc.reason
        code = exc.code
        if not under_tmp(out):
            print(exc.reason, file=sys.stderr)
            return code
    if under_tmp(out):
        emit(out, rec)
    reason = rec.get("refused")
    if reason:
        print(reason, file=sys.stderr)
    elif code == 0:
        comparison = rec.get("comparison") or {}
        print(
            "solo pass=%s review pass=%s cost_usd=%s winner=%s"
            % (
                rec["arms"]["solo"]["pass"],
                rec["arms"]["review"]["pass"],
                rec["cost_usd"],
                comparison.get("winner"),
            )
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
