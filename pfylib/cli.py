"""``./pfy toolset`` and ``./pfy hedge`` front end (ADR-0017).

Invoked by the thin bash dispatcher as ``python3 "$ROOT/pfylib/cli.py" <verb> ...``
or as ``python3 -m pfylib <verb> ...``. Stdlib only.

Exit codes: 0 READY (or dry-run / listing), 1 FAIL, 2 usage, 3 STUB (honest
"not wired" plan -- distinct from failure so scripts can tell the two apart).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "pfylib"  # noqa: A001 -- PEP 366 so relative imports work when run by path

from . import hedge, model_choice, registry, setup, toolsets  # noqa: E402

EXIT_READY, EXIT_FAIL, EXIT_USAGE, EXIT_STUB = 0, 1, 2, 3


def _emit(obj: dict, as_json: bool, text: str | None = None) -> None:
    if as_json:
        print(json.dumps(obj, indent=2, sort_keys=True))
    else:
        print(text if text is not None else obj.get("copy", ""))


def _exit_for(obj: dict) -> int:
    live = obj.get("live")
    if live == "STUB":
        return EXIT_STUB
    if live == "READY":
        return EXIT_READY
    return EXIT_FAIL


# --------------------------------------------------------------- toolset ---


def _toolset_list(args) -> int:
    rows = registry.toolset_rows(args.root)
    if args.json:
        print(json.dumps(rows, indent=2))
        return EXIT_READY
    hids = registry.harness_ids(args.root)
    for t in rows:
        impl = t.get("implementation") or {}
        counts = {s: sum(1 for h in hids if (impl.get(h) or {}).get("status") == s) for s in toolsets.STATUSES}
        print(
            "%-14s %-44s lanes=%-11s catalog=%-22s impl %d · partial %d · stub %d"
            % (
                t.get("id"),
                str(t.get("title") or "")[:44],
                "/".join(t.get("lanes") or []),
                str(t.get("catalog_tool") or "null")[:22],
                counts["implemented"],
                counts["partial"],
                counts["stub"],
            )
        )
    print("")
    print("%d toolsets × %d harnesses (data/toolsets.json × data/harnesses.json role=harness)" % (len(rows), len(hids)))
    return EXIT_READY


def _toolset_matrix(args) -> int:
    problems = registry.validate(root_dir=args.root)
    if args.json:
        print(json.dumps({"rows": toolsets.matrix(args.root), "problems": problems}, indent=2))
    else:
        print(toolsets.matrix_text(args.root))
        for p in problems:
            print("PROBLEM: %s" % p)
    return EXIT_FAIL if problems else EXIT_READY


def _print_plan(p: dict, *, show_brief: bool) -> None:
    print(p.get("copy", ""))
    if p.get("status") or p.get("how"):
        print("  status: %s%s" % (p.get("status") or "?", (" · " + p["how"]) if p.get("how") else ""))
    if p.get("error"):
        print("  error:  %s" % p["error"])
    if p.get("note"):
        print("  note:   %s" % p["note"])
    if p.get("env"):
        print("  env:")
        for line in toolsets.export_env_lines(p):
            print("    %s" % line)
    if p.get("files"):
        print("  files:")
        for f in p["files"]:
            print("    %-14s %s" % (f.get("mode", "write"), f.get("path")))
    if p.get("commands"):
        print("  commands: %s" % " | ".join(p["commands"]))
    if p.get("applied"):
        print("  applied:")
        for a in p["applied"]:
            print("    %-10s %s" % (a.get("result"), a.get("path")))
    if p.get("failed"):
        print("  failed:")
        for a in p["failed"]:
            print("    %s → %s" % (a.get("path"), a.get("result")))
    if p.get("next_step"):
        print("  next:   %s" % p["next_step"])
    if show_brief and p.get("brief"):
        print("")
        print(p["brief"].rstrip("\n"))


def _toolset_plan(args) -> int:
    p = toolsets.plan(args.toolset, args.harness, args.lane, root_dir=args.root, state=args.state)
    if args.env_only:
        for line in toolsets.export_env_lines(p):
            print(line)
        return _exit_for(p)
    if args.json:
        _emit(p, True)
    else:
        _print_plan(p, show_brief=args.brief)
    return _exit_for(p)


def _toolset_apply(args) -> int:
    p = toolsets.plan(args.toolset, args.harness, args.lane, root_dir=args.root, state=args.state)
    out = toolsets.apply(p, yes=args.yes, state=args.state, root_dir=args.root)
    if args.json:
        _emit(out, True)
    else:
        _print_plan(out, show_brief=args.brief)
    return _exit_for(out)


def _toolset_validate(args) -> int:
    problems = registry.validate(root_dir=args.root)
    if args.json:
        print(json.dumps({"ok": not problems, "problems": problems}, indent=2))
    elif problems:
        for p in problems:
            print("FAIL %s" % p)
    else:
        print("READY toolsets.json × harnesses.json well-formed · %d toolsets · %d harnesses" % (len(registry.toolset_ids(args.root)), len(registry.harness_ids(args.root))))
    return EXIT_FAIL if problems else EXIT_READY


# ----------------------------------------------------------------- hedge ---


def _hedge_decide(args) -> int:
    kw = dict(state=args.state, root_dir=args.root)
    if args.budget is not None:
        kw["budget"] = args.budget
    if args.local is not None:
        kw["local"] = {"engine": "override", "base_url": "", "status": "ready" if args.local == "ready" else "missing"}
    rec = hedge.decide_and_record(args.task, **kw) if args.record else hedge.decide(args.task, **kw)
    if args.json:
        _emit(rec, True)
    else:
        print(rec.get("copy", ""))
        print("  local: %s (%s)%s" % (rec.get("local_engine"), rec.get("local_status"), (" " + rec["local_base_url"]) if rec.get("local_base_url") else ""))
        print("  cloud: budget %s · spent %s · remaining %s · cost/task %s · profile %s" % (rec.get("budget"), rec.get("spent"), rec.get("remaining"), rec.get("cost"), rec.get("profile")))
        if rec.get("recorded") is not None:
            print("  recorded: %s credit(s) → %s" % (rec.get("recorded"), rec.get("ledger")))
        if rec.get("next_step"):
            print("  next:  %s" % rec["next_step"])
    return EXIT_READY if rec.get("ok") else EXIT_FAIL


def _hedge_ledger(args) -> int:
    if args.reset:
        path = hedge.reset_ledger(args.state)
        _emit({"ok": True, "live": "READY", "ledger": str(path), "copy": "READY ledger reset · %s" % path}, args.json)
        return EXIT_READY
    led = hedge.load_ledger(args.state)
    budget = hedge.budget_from_env() if args.budget is None else args.budget
    out = {
        "ok": True,
        "live": "READY",
        "ledger": str(hedge.ledger_path(args.state)),
        "budget": budget,
        "spent": led.get("spent", 0),
        "remaining": max(0, budget - int(led.get("spent") or 0)),
        "entries": led.get("entries", []),
    }
    if "error" in led:
        out["error"] = led["error"]
    if args.json:
        _emit(out, True)
        return EXIT_READY
    print("hedge ledger · %s" % out["ledger"])
    print("  budget %d · spent %d · remaining %d · %d entr%s" % (budget, out["spent"], out["remaining"], len(out["entries"]), "y" if len(out["entries"]) == 1 else "ies"))
    if out.get("error"):
        print("  error: %s" % out["error"])
    for e in out["entries"][-args.tail:]:
        print("  %-20s %-5s %-11s %4s  %s" % (e.get("when"), e.get("lane"), e.get("task") or "-", e.get("amount"), e.get("note") or ""))
    return EXIT_READY


def _setup_verb(args) -> int:
    return setup.cmd_setup(args)


def _model_choice_show(args) -> int:
    if args.json:
        rows = []
        for task in model_choice.TASK_ORDER:
            backend, model, source = model_choice.resolve(task, root=args.root)
            rows.append({"task": task, "backend": backend, "model": model, "source": source})
        _emit({"tasks": rows}, True)
        return EXIT_READY
    print(model_choice.show_text(root=args.root))
    return EXIT_READY


def _model_choice_set(args) -> int:
    spec = args.spec
    if "=" not in spec:
        spec = "%s=%s" % (args.task, spec)
    task, backend, model = model_choice.apply_assignment(spec)
    print("model-choice %s %s:%s" % (task, backend, model))
    return EXIT_READY


def _model_choice_prompt(args) -> int:
    args.model_choice_prompt = True
    code = model_choice.setup_from_args(args)
    return EXIT_READY if code in (None, 0) else int(code)


def _compare_verb(args) -> int:
    try:
        result = model_choice.run_compare(
            args.task,
            against=args.against,
            run=args.run or None,
            last=bool(args.last) or not args.run,
            yes=bool(args.yes),
            max_usd=args.max_usd,
            accept_stale=bool(args.accept_stale_price),
            out=args.out or None,
            root=args.root,
        )
    except model_choice.UnknownModelPrice as exc:
        print("UnknownModelPrice: %s" % exc, file=sys.stderr)
        return EXIT_FAIL
    except (model_choice.PriceCoverageError, model_choice.CompareBusy, model_choice.ModelCallError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_FAIL
    return EXIT_READY if result.get("ok") else EXIT_FAIL


def _doctor_verb(args) -> int:
    return setup.cmd_doctor(args)


def _uninstall_verb(args) -> int:
    return setup.cmd_uninstall(args)


def _hedge_record(args) -> int:
    rec = hedge.record(args.amount, lane=args.lane, task=args.task or "", note=args.note or "", state=args.state, budget=args.budget)
    _emit(rec, args.json)
    return EXIT_READY if rec.get("ok") else EXIT_FAIL


# ---------------------------------------------------------------- parser ---


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="pfy", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=None, help="repo root (default: PFY_ROOT or auto)")
    ap.add_argument("--state", type=Path, default=None, help="state dir (default: PFY_STATE_DIR or ~/.pfy-mentat)")
    verbs = ap.add_subparsers(dest="verb", required=True)

    ts = verbs.add_parser("toolset", help="toolset × harness matrix, plan, apply")
    tsub = ts.add_subparsers(dest="sub", required=True)
    p = tsub.add_parser("list", help="one line per toolset")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=_toolset_list)
    p = tsub.add_parser("matrix", help="toolset × harness status grid (implemented/partial/stub)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=_toolset_matrix)
    for name, fn in (("plan", _toolset_plan), ("apply", _toolset_apply)):
        p = tsub.add_parser(name, help="%s <toolset> --harness <h> [--lane local|cloud]" % name)
        p.add_argument("toolset")
        p.add_argument("--harness", required=True)
        p.add_argument("--lane", choices=list(toolsets.LANES), default=None)
        p.add_argument("--json", action="store_true")
        p.add_argument("--brief", action="store_true", help="also print the brief text")
        if name == "plan":
            p.add_argument("--env", dest="env_only", action="store_true", help="print only `export K=V` lines (for eval)")
        else:
            p.add_argument("--yes", action="store_true", help="actually write files (under $PFY_STATE_DIR or the harness config dir); default is dry-run")
            p.set_defaults(env_only=False)
        p.set_defaults(fn=fn)
    p = tsub.add_parser("validate", help="shape-check data/toolsets.json against data/harnesses.json")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=_toolset_validate)

    hg = verbs.add_parser("hedge", help="local-first lane policy + cloud credit ledger")
    hsub = hg.add_subparsers(dest="sub", required=True)
    p = hsub.add_parser("decide", help="pick lane for one task: local first, cloud only within PFY_CLOUD_BUDGET")
    p.add_argument("--task", required=True, choices=list(hedge.TASKS))
    p.add_argument("--budget", type=int, default=None, help="override PFY_CLOUD_BUDGET")
    p.add_argument("--local", choices=["ready", "missing"], default=None, help="override detector (tests/offline)")
    p.add_argument("--record", action="store_true", help="debit the ledger if the lane is cloud")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=_hedge_decide)
    p = hsub.add_parser("ledger", help="show (or --reset) the hedge ledger")
    p.add_argument("--budget", type=int, default=None)
    p.add_argument("--tail", type=int, default=20)
    p.add_argument("--reset", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=_hedge_ledger)
    p = hsub.add_parser("record", help="append a spend entry: record <amount> [--lane cloud|local]")
    p.add_argument("amount", type=int)
    p.add_argument("--lane", choices=list(hedge.LANES), default="cloud")
    p.add_argument("--task", default="")
    p.add_argument("--note", default="")
    p.add_argument("--budget", type=int, default=None)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=_hedge_record)

    sp = verbs.add_parser("setup", help="install catalog items into harness configs")
    sp.add_argument("--preset", action="append", default=None)
    sp.add_argument("--item", action="append", default=None)
    sp.add_argument("--harness", action="append", default=None)
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--yes", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--all-detected", action="store_true")
    sp.add_argument("--model-choice", action="append", default=None, help="task=backend:model (repeatable)")
    sp.set_defaults(fn=_setup_verb)

    mc = verbs.add_parser("model-choice", help="show or set the per-task local/cloud model")
    msub = mc.add_subparsers(dest="sub", required=True)
    p = msub.add_parser("show", help="print each task class")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=_model_choice_show)
    p = msub.add_parser("set", help="set <task> <backend:model>")
    p.add_argument("task")
    p.add_argument("spec")
    p.set_defaults(fn=_model_choice_set)
    p = msub.add_parser("prompt", help="setup prompt (Enter keeps the current row)")
    p.add_argument("--model-choice", action="append", default=None)
    p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=_model_choice_prompt)

    cp = verbs.add_parser("compare", help="cost-gated cross-model compare (catalog-fit)")
    cp.add_argument("task")
    cp.add_argument("--against", required=True)
    cp.add_argument("--run", default="")
    cp.add_argument("--last", action="store_true")
    cp.add_argument("--yes", action="store_true")
    cp.add_argument("--max-usd", type=float, default=None)
    cp.add_argument("--accept-stale-price", action="store_true")
    cp.add_argument("--out", default="")
    cp.set_defaults(fn=_compare_verb)

    sp = verbs.add_parser("doctor", help="read-only install status (does not exec delegates)")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--harness", action="append", default=None)
    sp.add_argument("--item", action="append", default=None)
    sp.set_defaults(fn=_doctor_verb)

    sp = verbs.add_parser("uninstall", help="remove ledger-owned installs")
    sp.add_argument("--yes", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(fn=_uninstall_verb)
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return EXIT_USAGE if e.code not in (0, None) else 0
    try:
        return int(args.fn(args))
    except FileNotFoundError as e:
        print("FAIL missing file: %s" % e, file=sys.stderr)
        return EXIT_FAIL
    except (ValueError, json.JSONDecodeError) as e:
        print("FAIL bad data: %s" % e, file=sys.stderr)
        return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
