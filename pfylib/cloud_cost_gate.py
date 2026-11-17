"""Cost-gate a paid Grok call with the 11/11 model-choice rules.

Prints the estimate from ``pfylib.model_choice.quote`` first. Unattended
calls without a covering ``--max-usd`` (optionally paired with ``--yes``)
skip with $0 spend and do not start grok. A covering cap alone is approval.
``--yes`` without a cap is not. This module does not invoke a model.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Mapping

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "pfylib"  # noqa: A001

from pfylib.model_choice import (  # noqa: E402
    ModelCallError,
    _gate_unapproved_cloud,
    sys_isatty,
)

SKIP_EXIT = 4
DEFAULT_MODEL = "grok-4.7"


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def env_flag(name: str, env: Mapping[str, str] | None = None) -> bool:
    src = os.environ if env is None else env
    return str(src.get(name) or "").strip().lower() in ("1", "true", "yes")


def env_max_usd(env: Mapping[str, str] | None = None) -> float | None:
    src = os.environ if env is None else env
    raw = str(src.get("PFY_CLOUD_MAX_USD") or "").strip()
    if not raw:
        return None
    return float(raw)


def env_model(env: Mapping[str, str] | None = None) -> str:
    src = os.environ if env is None else env
    name = str(src.get("PFY_CLOUD_MODEL") or "").strip()
    return name or DEFAULT_MODEL


def skip_line(reason: str) -> str:
    text = (reason or "not approved").rstrip()
    if text.endswith("."):
        text = text[:-1]
    if "No model was called" in text:
        if "$0 spend" not in text:
            text = text.replace("No model was called", "$0 spend. No model was called")
        if not text.lower().startswith("skipping:"):
            text = "skipping: " + text
        return text
    return "skipping: %s. $0 spend. No model was called." % text


def gate_cloud_prompt(
    prompt: str,
    *,
    model: str | None = None,
    yes: bool = False,
    max_usd: float | None = None,
    isatty: bool | None = None,
    answer: str | None = None,
    root: Path | None = None,
    input_fn=None,
    env: Mapping[str, str] | None = None,
) -> dict:
    """Print the estimate. Return ``{allowed, reason, model}``. Never starts grok."""
    src = os.environ if env is None else env
    chosen = (model or env_model(src)).strip() or DEFAULT_MODEL
    approved_yes = bool(yes) or env_flag("PFY_CLOUD_YES", src)
    cap = max_usd if max_usd is not None else env_max_usd(src)
    tty = sys_isatty() if isatty is None else isatty
    reply = answer
    if tty and not approved_yes and cap is None and reply is None:
        if input_fn is not None:
            reply = input_fn("Proceed? [y/N] ")
        else:
            print("Proceed? [y/N]", file=sys.stderr, flush=True)
            try:
                reply = input("").strip()
            except EOFError:
                reply = ""
    try:
        _gate_unapproved_cloud(
            prompt,
            chosen,
            root=root or package_root(),
            yes=approved_yes,
            max_usd=cap,
            isatty=tty,
            answer=reply,
        )
        return {"allowed": True, "reason": "", "model": chosen}
    except (ModelCallError, ValueError) as exc:
        reason = skip_line(str(exc))
        return {"allowed": False, "reason": reason, "model": chosen}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pfylib.cloud_cost_gate")
    parser.add_argument("--prompt-file", help="file whose bytes are priced")
    parser.add_argument("--prompt", default="", help="literal prompt; used if no file")
    parser.add_argument("--model", default="", help="default grok-4.7")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--max-usd", type=float, default=None)
    parser.add_argument(
        "--isatty",
        choices=("auto", "yes", "no"),
        default="auto",
        help="test seam; production leaves this at auto",
    )
    parser.add_argument("--answer", default=None, help="test seam for a TTY reply")
    args = parser.parse_args(argv)
    if args.prompt_file:
        path = Path(args.prompt_file)
        try:
            prompt = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(skip_line("cannot read prompt file: %s" % exc), file=sys.stderr)
            return 1
    else:
        prompt = args.prompt
    if not prompt:
        print(skip_line("missing prompt"), file=sys.stderr)
        return 1
    tty: bool | None
    if args.isatty == "yes":
        tty = True
    elif args.isatty == "no":
        tty = False
    else:
        tty = None
    verdict = gate_cloud_prompt(
        prompt,
        model=args.model or None,
        yes=bool(args.yes),
        max_usd=args.max_usd,
        isatty=tty,
        answer=args.answer,
    )
    if verdict["allowed"]:
        return 0
    print(verdict["reason"], file=sys.stderr)
    return SKIP_EXIT


if __name__ == "__main__":
    raise SystemExit(main())
