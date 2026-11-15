#!/usr/bin/env python3
"""Tier-1 scored coding task via LiteLLM → local OpenAI-compatible endpoint.

Exit: 0 pass, 1 fail, 2 skip (missing model/prereq).
"""
from __future__ import annotations

import argparse
import importlib.util
import ipaddress
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


def _normalize_ascii_punct(s: str) -> str:
    """Map common smart punctuation that breaks Python syntax (small models)."""
    table = str.maketrans(
        {
            "\u2013": "-",  # en dash
            "\u2014": "-",  # em dash
            "\u2212": "-",  # minus
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u00a0": " ",
        }
    )
    return s.translate(table)


def extract_python(text: str) -> str:
    """Pull executable Python from model output (fences, def blocks, or raw).

    Keep leading ``import`` / ``from`` / blank / comment lines that appear
    *before* the first ``def``/``class``. Models often put ``import re``
    above ``def slugify``; dropping that preamble causes ``NameError: re``.
    """
    text = _normalize_ascii_punct(text.strip())
    m = re.search(r"```(?:python)?\s*([\s\S]*?)```", text, re.I)
    if m:
        text = m.group(1).strip()
        text = _normalize_ascii_punct(text)

    # Prefer a contiguous def … body (stop at next top-level prose/heading)
    def_m = re.search(
        r"(^|\n)((?:def|class)\s+\w+[\s\S]*)",
        text,
    )
    if not def_m:
        return text

    before = text[: def_m.start(2)]
    preamble: list[str] = []
    for line in before.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("#")
            or stripped.startswith(("import ", "from "))
        ):
            preamble.append(line)
        # else: drop prose / markdown before the code block

    body = def_m.group(2)
    # If we matched a class, keep full class body similarly
    lines: list[str] = []
    for i, line in enumerate(body.splitlines()):
        if i == 0:
            lines.append(line)
            continue
        # Stop when model resumes prose after the function/class
        if line.strip() and not line[0].isspace() and not line.startswith(
            ("def ", "class ", "@", "import ", "from ", "#")
        ):
            break
        lines.append(line)
    text = "\n".join([*preamble, *lines]).rstrip()
    # Collapse leading blank lines from empty preamble noise
    return text.lstrip("\n")


def load_tests(path: Path):
    spec = importlib.util.spec_from_file_location("task_tests", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load tests: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "run_tests"):
        raise RuntimeError("test_task.py must define run_tests(ns) -> list[str]")
    return mod.run_tests


def _host_is_local_stdlib(url: str) -> bool:
    """Same rule as pfylib.model_choice.host_is_local. Used when that import fails."""
    raw = (url or "").strip()
    if not raw:
        return False
    if "://" not in raw:
        raw = "http://" + raw
    host = (urlparse(raw).hostname or "").lower().rstrip(".")
    if not host:
        return False
    if host in {"localhost", "host.docker.internal"} or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    doc = ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24") if ip.version == 4 else ("2001:db8::/32",)
    if any(ip in ipaddress.ip_network(net) for net in doc):
        return False
    return bool(ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_unspecified)


def _host_is_local(url: str) -> bool:
    try:
        from pfylib.model_choice import host_is_local
    except ImportError:
        return _host_is_local_stdlib(url)
    return host_is_local(url)


def _paid_host_block(
    base: str,
    model_name: str,
    prompt: str,
    max_tokens: int,
    *,
    yes: bool,
    max_usd: float | None,
    paid_ok: bool,
    isatty: bool,
    answer: str | None,
) -> str | None:
    """None when the chat host may be called. Otherwise the refusal text.

    Local hosts, including the harness default, are $0 and are not asked.
    A public host with only the local ollama:* price is refused. That $0
    row is not a paid quote.
    """
    if _host_is_local(base):
        return None
    local_alt = (
        "model choice: host %s is not local. "
        "Local alternative is http://host.docker.internal:11435/v1 at $0 "
        "(unset OPENAI_BASE_URL)."
        % base
    )
    print(local_alt, file=sys.stderr)
    try:
        from pfylib.model_choice import (
            ModelCallError,
            PriceCoverageError,
            UnknownModelPrice,
            _confirm,
            _paid_blocked,
            count_tokens,
            price_age_days,
            quote,
        )
    except ImportError:
        return (
            "no price helper on this copy. No model was called. %s" % local_alt
        )
    prompt_tokens, method = count_tokens(prompt)
    completion = max_tokens if max_tokens and max_tokens > 0 else 512
    try:
        priced = quote(model_name, prompt_tokens, completion)
    except (UnknownModelPrice, PriceCoverageError) as exc:
        return "%s. No model was called. %s" % (exc, local_alt)
    provider = str(priced.get("provider") or "")
    if provider.lower() == "local" or (
        float(priced["price_in"]) <= 0 and float(priced["price_out"]) <= 0
    ):
        return (
            "no paid price for %r on a non-local host. No model was called. %s"
            % (model_name, local_alt)
        )
    stale_days = price_age_days(priced["fetched"])
    stale = stale_days > int(priced["stale_after_days"])
    line = (
        "cost estimate: $%s for %s prompt tokens + %s completion-token allowance (%s) "
        "on %s (%s $%.2f/$%.2f per 1M, %s, fetched %s). "
        "No call is sent until you say yes."
        % (
            priced["cost_text"],
            f"{prompt_tokens:,}",
            f"{completion:,}",
            method,
            model_name,
            provider,
            priced["price_in"],
            priced["price_out"],
            priced["source_short"],
            priced["fetched"],
        )
    )
    print(line, file=sys.stderr)
    if stale:
        print(
            "Price for %s was fetched %s (older than %s days)."
            % (model_name, priced["fetched"], priced["stale_after_days"]),
            file=sys.stderr,
        )
    if paid_ok and stale:
        return "stale price. No model was called. %s" % local_alt
    if not paid_ok:
        # A covering cap, or --yes plus that cap, is the off-TTY approval.
        # On a TTY with neither, one line (y or yes) is the approval.
        if bool(isatty) and not yes and answer is None and max_usd is None and not stale:
            try:
                answer = input("").strip()
            except EOFError:
                answer = ""
        try:
            block = _confirm(
                yes=bool(yes),
                max_usd=max_usd,
                cost=float(priced["cost_usd"]),
                cost_text=priced["cost_text"],
                isatty=bool(isatty),
                answer=answer,
                stale=stale,
                accept_stale=False,
            )
        except ModelCallError as exc:
            return "%s. No model was called. %s" % (exc, local_alt)
        if block:
            return "%s. No model was called. %s %s" % (block, line, local_alt)
    if _paid_blocked():
        return "paid cloud call blocked. No model was called. %s" % local_alt
    return None


def resolve_model(local_tags: list[str] | None = None, *, probe: bool = False) -> str:
    """EVAL_MODEL, else LITELLM_SMOKE_MODEL, else model_choice.

    Suite and single-task runs use eval-suite. EVAL_MODE=matrix uses matrix.
    Both are Ollama-only: a cloud choice is refused and the committed local
    model stays. local_tags, or probe=True (GET /api/tags, no pull), may
    select the committed qwen2.5:14b fallback when qwen3.6:35b is not listed.
    An empty tag list keeps qwen3.6:35b. EVAL_MODEL does not switch.
    """
    explicit = (os.environ.get("EVAL_MODEL") or "").strip()
    if explicit:
        return explicit
    smoke = (os.environ.get("LITELLM_SMOKE_MODEL") or "").strip()
    if smoke:
        return smoke
    task = "matrix" if (os.environ.get("EVAL_MODE") or "").strip() == "matrix" else "eval-suite"
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from pfylib.model_choice import detect_local_models, runner_choice
        tags = local_tags
        if tags is None and probe:
            tags = detect_local_models()
        _backend, model, _source = runner_choice(
            task, transport="ollama", root=root, local_tags=tags,
        )
        return model or "qwen3.6:35b"
    except Exception:
        return "qwen3.6:35b"


def _llama_ngram_or_none(prompt: str, max_tokens: int) -> str | None:
    """Opt-in ngram decode. None keeps the current engine and the same arguments."""
    path = Path(__file__).resolve().parents[2] / "scripts" / "integrations" / "llama_ngram" / "run.py"
    if not path.is_file():
        print("llama ngram: run.py missing, baseline engine", file=sys.stderr)
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location("llama_ngram_run", path)
    if spec is None or spec.loader is None:
        print("llama ngram: cannot load run.py, baseline engine", file=sys.stderr)
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        return mod.complete_for_lane(prompt, max_tokens)
    except Exception as exc:
        print("llama ngram: %s, baseline engine" % exc, file=sys.stderr)
        return None



def _chat_completion(
    *,
    model_name: str,
    base: str,
    api_key: str,
    prompt: str,
    max_tokens: int = 512,
) -> str:
    """OpenAI-compatible chat; litellm optional (self-hosted runners often lack it)."""
    if os.environ.get("PFY_LLAMA_NGRAM") == "1":
        routed = _llama_ngram_or_none(prompt, max_tokens)
        if routed is not None:
            return routed
    try:
        from litellm import completion  # type: ignore

        resp = completion(
            model=f"openai/{model_name}",
            api_base=base.rstrip("/"),
            api_key=api_key,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0,
        )
        return (resp.choices[0].message.content or "").strip()
    except ImportError:
        pass
    except Exception:
        # misconfigured litellm → try raw HTTP
        pass

    import json
    import urllib.request

    url = base.rstrip("/") + "/chat/completions"
    body = json.dumps(
        {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0,
            "stream": False,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        return (data["choices"][0]["message"]["content"] or "").strip()
    except Exception as e:  # noqa: BLE001
        # Ollama native generate fallback
        host = base.rstrip("/").removesuffix("/v1")
        if ":11435" in host:
            host = host.replace(":11435", ":11434")
        gen_url = host + "/api/generate"
        gbody = json.dumps(
            {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0, "num_predict": max_tokens},
            }
        ).encode("utf-8")
        greq = urllib.request.Request(
            gen_url,
            data=gbody,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(greq, timeout=180) as resp:  # noqa: S310
                gdata = json.loads(resp.read().decode("utf-8"))
            return (gdata.get("response") or "").strip()
        except Exception as e2:  # noqa: BLE001
            raise RuntimeError(f"chat failed openai={e!r} ollama={e2!r}") from e2


def score_task(
    task: str,
    tasks_root: Path,
    *,
    model_name: str | None = None,
    base: str | None = None,
    api_key: str | None = None,
    max_tokens: int = 512,
    yes: bool = False,
    max_usd: float | None = None,
    paid_ok: bool = False,
    isatty: bool = False,
    answer: str | None = None,
) -> dict:
    """Run one task; return result dict with pass/failures (never raises for score fails)."""
    task_dir = tasks_root / task
    prompt_path = task_dir / "prompt.txt"
    tests_path = task_dir / "test_task.py"
    if not prompt_path.is_file() or not tests_path.is_file():
        return {
            "task": task,
            "model": model_name or resolve_model(),
            "pass": False,
            "failures": [f"task incomplete: {task_dir}"],
            "error": "incomplete_task",
            "skip": False,
        }

    base = (base or os.environ.get("OPENAI_BASE_URL", "http://host.docker.internal:11435/v1")).rstrip(
        "/"
    )
    model_name = model_name or resolve_model()
    api_key = api_key or os.environ.get("OLLAMA_API_KEY", "ollama")
    litellm_model = f"openai/{model_name}"

    prompt = prompt_path.read_text(encoding="utf-8")
    block = _paid_host_block(
        base,
        model_name,
        prompt,
        max_tokens,
        yes=yes,
        max_usd=max_usd,
        paid_ok=paid_ok,
        isatty=isatty,
        answer=answer,
    )
    if block:
        return {
            "task": task,
            "model": litellm_model,
            "pass": False,
            "failures": [block],
            "error": "paid_host",
            "skip": False,
        }
    try:
        raw = _chat_completion(
            model_name=model_name,
            base=base,
            api_key=api_key,
            prompt=prompt,
            max_tokens=max_tokens,
        )
    except Exception as e:  # noqa: BLE001
        return {
            "task": task,
            "model": litellm_model,
            "pass": False,
            "failures": [f"completion failed: {e}"],
            "error": "completion",
            "skip": False,
        }
    code = extract_python(raw)
    if not code:
        return {
            "task": task,
            "model": litellm_model,
            "pass": False,
            "failures": ["empty model code"],
            "error": "empty",
            "code_preview": "",
            "raw_chars": len(raw),
            "skip": False,
        }

    ns: dict = {}
    try:
        exec(compile(code, "<candidate>", "exec"), ns, ns)  # noqa: S102
    except Exception as e:  # noqa: BLE001
        return {
            "task": task,
            "model": litellm_model,
            "pass": False,
            "failures": [f"compile/exec: {type(e).__name__}: {e}"],
            "error": "exec",
            "code_preview": code[:500],
            "raw_chars": len(raw),
            "skip": False,
        }

    run_tests = load_tests(tests_path)
    fails = run_tests(ns)
    return {
        "task": task,
        "model": litellm_model,
        "pass": len(fails) == 0,
        "failures": fails,
        "code_preview": code[:500],
        "raw_chars": len(raw),
        "code_chars": len(code),
        "skip": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--task",
        default="001-is-palindrome",
        help="Task directory name under tasks/",
    )
    ap.add_argument(
        "--tasks-root",
        type=Path,
        default=Path(__file__).resolve().parent / "tasks",
    )
    ap.add_argument("--yes", action="store_true", help="accept the printed estimate")
    ap.add_argument("--approve-cost", action="store_true", help="same as --yes; still needs a cap")
    ap.add_argument("--max-usd", type=float, default=None, help="USD cap; at or above the estimate is approval")
    ap.add_argument("--max-cost", type=float, default=None, help="alias of --max-usd")
    args = ap.parse_args()

    model_name = resolve_model(probe=True)
    base = os.environ.get("OPENAI_BASE_URL", "http://host.docker.internal:11435/v1").rstrip("/")
    print(f"eval tier1: task={args.task} base={base} model=openai/{model_name}", flush=True)
    try:
        tty = sys.stdin.isatty()
    except Exception:
        tty = False
    cap = args.max_usd if args.max_usd is not None else args.max_cost
    result = score_task(
        args.task,
        args.tasks_root,
        model_name=model_name,
        base=base,
        yes=bool(args.yes or args.approve_cost),
        max_usd=cap,
        isatty=tty,
    )
    print(
        f"eval: model_output_chars={result.get('raw_chars', '?')} "
        f"code_chars={result.get('code_chars', '?')}",
        flush=True,
    )
    print(
        json.dumps(
            {k: result[k] for k in ("task", "model", "pass", "failures") if k in result},
            indent=2,
        ),
        flush=True,
    )

    if result.get("error") == "paid_host":
        print("SCORE: SKIP", flush=True)
        for failure in result.get("failures") or []:
            print(f"  - {failure}", flush=True)
        return 2

    if result.get("error") == "exec":
        print(f"SCORE: FAIL ({result['failures'][0]})", flush=True)
        print("--- code ---", flush=True)
        print((result.get("code_preview") or "")[:2000], flush=True)
        return 1

    if not result.get("pass"):
        print("SCORE: FAIL", flush=True)
        for f in result.get("failures") or []:
            print(f"  - {f}", flush=True)
        return 1

    print("SCORE: PASS", flush=True)
    out = os.environ.get("EVAL_RESULT_JSON")
    if out:
        Path(out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
