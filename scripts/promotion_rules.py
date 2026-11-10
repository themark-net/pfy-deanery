#!/usr/bin/env python3
"""Rule-based promotion: the engine for data/promotion-rules.json.

Every stage move (I0 to I4) and every tier_ceiling raise is decided by the
rules file. Nobody signs off. See docs/ops/promotion-rules.md.

The rules file names, for each mode and each target stage, the rule IDs that
must pass. This module holds one check function per rule ID. Loading fails
closed (RuleError) when the file names a rule with no check, a check has no
rule entry, a transition names an undeclared rule, or a hard stop is not a
hard_stop rule.

  python3 scripts/promotion_rules.py --slug SLUG [--mode apply|scan|ceiling|launch] [--target I3]

prints one line per rule: pass|fail <rule> <detail>. It writes nothing.

Modes (a rule is checked only in the modes it lists):
  apply    catalog_apply_verdict.py with a verdict
  scan     catalog_apply_verdict.py --scan (no verdict)
  ceiling  catalog_auto_raise.py, with the latest VERDICT.json
  launch   catalog_auto_raise.py --launch-check

Ledger: ledger_entry() and append_ledger() write one promotion_history entry
on the card per decision: kind, from, to, result, passed rule IDs, failed
rule IDs with details, the rules version, the verdict path, and the date.
An entry equal to the last one apart from the date is not appended again.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RULES_REL = "data/promotion-rules.json"
STAGES = ("I0", "I1", "I2", "I3", "I4")
RANK = {stage: index for index, stage in enumerate(STAGES)}
MODES = ("apply", "scan", "ceiling", "launch")
TRACKS = ("default", "security")
TRIAL_NAME = "sandbox-trial.json"
SECRET_PARTS = (".ssh", ".gnupg", ".aws", ".grok", ".config", ".netrc", ".dev.vars", "auth.json", ".docker", ".kube")


class RuleError(Exception):
    """The rules file or a check is unusable. Callers fail closed."""


def _ar():
    from scripts import catalog_auto_raise
    return catalog_auto_raise


def _av():
    from scripts import catalog_apply_verdict
    return catalog_apply_verdict


@dataclass
class Ctx:
    card: dict
    slug: str
    root: Path
    name: str = ""
    verdict: dict | None = None
    approved: frozenset = frozenset()
    mode: str = "apply"
    cache: dict = field(default_factory=dict)


# ---------------------------------------------------------------- rules file

def rules_path(root: Path | None) -> Path:
    if root is not None:
        candidate = Path(root) / RULES_REL
        if candidate.is_file():
            return candidate
    return ROOT / RULES_REL


def load_rules(root: Path | None = None) -> dict:
    path = rules_path(root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuleError(f"{RULES_REL}: unreadable ({exc})") from exc
    if not isinstance(data, dict) or not isinstance(data.get("version"), int):
        raise RuleError(f"{RULES_REL}: needs an integer version")
    rules = data.get("rules")
    if not isinstance(rules, dict) or not rules:
        raise RuleError(f"{RULES_REL}: rules must be a non-empty object")
    for rid, spec in rules.items():
        if rid not in CHECKS:
            raise RuleError(f"{RULES_REL}: rule {rid} has no check in scripts/promotion_rules.py")
        if not isinstance(spec, dict) or not isinstance(spec.get("modes"), list) or not spec["modes"]:
            raise RuleError(f"{RULES_REL}: rule {rid} needs a modes list")
        for mode in spec["modes"]:
            if mode not in MODES:
                raise RuleError(f"{RULES_REL}: rule {rid} has unknown mode {mode!r}")
        if not isinstance(spec.get("check"), str) or not spec["check"].strip():
            raise RuleError(f"{RULES_REL}: rule {rid} needs check text")
    for rid in CHECKS:
        if rid not in rules:
            raise RuleError(f"{RULES_REL}: check {rid} is not declared in rules")
    stops = data.get("hard_stops")
    if not isinstance(stops, list):
        raise RuleError(f"{RULES_REL}: hard_stops must be a list")
    for rid in stops:
        if rid not in rules or rules[rid].get("hard_stop") is not True:
            raise RuleError(f"{RULES_REL}: hard stop {rid} is not a hard_stop rule")
    for rid, spec in rules.items():
        if spec.get("hard_stop") is True and rid not in stops:
            raise RuleError(f"{RULES_REL}: hard_stop rule {rid} is missing from hard_stops")
    for kind in ("stage", "ceiling"):
        table = data.get(kind)
        if not isinstance(table, dict):
            raise RuleError(f"{RULES_REL}: {kind} must be an object")
        for track in TRACKS:
            steps = table.get(track)
            if not isinstance(steps, dict) or not steps:
                raise RuleError(f"{RULES_REL}: {kind}.{track} must be a non-empty object")
            for stage, ids in steps.items():
                if stage not in RANK or stage == "I0":
                    raise RuleError(f"{RULES_REL}: {kind}.{track} has bad stage {stage!r}")
                if not isinstance(ids, list):
                    raise RuleError(f"{RULES_REL}: {kind}.{track}.{stage} must be a list")
                for rid in ids:
                    if rid not in rules:
                        raise RuleError(f"{RULES_REL}: {kind}.{track}.{stage} names undeclared rule {rid}")
    launch = data.get("launch")
    if not isinstance(launch, list) or any(rid not in rules for rid in launch):
        raise RuleError(f"{RULES_REL}: launch must list declared rules")
    return data


def is_hard_stop(rules: dict, rid: str) -> bool:
    return rules["rules"].get(rid, {}).get("hard_stop") is True


def version_label(rules: dict) -> str:
    return f"{RULES_REL}@v{rules['version']}"


def track_of(card: dict) -> str:
    return "security" if _ar().risk_track(card) == "security" else "default"


def rule_ids(rules: dict, kind: str, track: str, target: str) -> list[str]:
    """Cumulative rule IDs for every step up to and including target."""
    steps = rules[kind][track]
    out: list[str] = []
    for stage in STAGES[1:]:
        if RANK[stage] > RANK[target]:
            break
        for rid in steps.get(stage, []):
            if rid not in out:
                out.append(rid)
    return out


def evaluate(rules: dict, ctx: Ctx, ids: list[str], target: str) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []
    for rid in ids:
        if ctx.mode not in rules["rules"][rid]["modes"]:
            continue
        ok, detail = CHECKS[rid](ctx, target)
        results.append((rid, ok, detail))
    return results


def stage_allowed(rules: dict, ctx: Ctx, kind: str = "stage", top: str = "I4") -> tuple[str, list[tuple[str, bool, str]], list[tuple[str, bool, str]]]:
    """Highest stage whose rules all pass, its results, and the first failing step's results."""
    track = track_of(ctx.card)
    steps = rules[kind][track]
    allowed = "I0"
    passed: list[tuple[str, bool, str]] = []
    for stage in STAGES[1:]:
        if RANK[stage] > RANK[top]:
            break
        if kind == "ceiling" and stage not in steps:
            continue
        results = evaluate(rules, ctx, rule_ids(rules, kind, track, stage), stage)
        if any(not ok for _rid, ok, _d in results):
            return allowed, passed, results
        allowed = stage
        passed = results
    return allowed, passed, []


def launch_results(rules: dict, ctx: Ctx) -> list[tuple[str, bool, str]]:
    ctx.mode = "launch"
    return evaluate(rules, ctx, list(rules["launch"]), "I1")


# ---------------------------------------------------------------- ledger

def ledger_entry(rules: dict, kind: str, old: object, target: str, result: str,
                 results: list[tuple[str, bool, str]], today: str, verdict_rel: str = "") -> dict:
    entry = {
        "kind": kind,
        "from": old if isinstance(old, str) else "",
        "to": target,
        "result": result,
        "passed": [rid for rid, ok, _d in results if ok],
        "failed": [{"rule": rid, "detail": detail} for rid, ok, detail in results if not ok],
        "rules": version_label(rules),
        "by": "rules",
        "date": today,
    }
    if verdict_rel:
        entry["verdict"] = verdict_rel
    return entry


def _strip_date(entry: object) -> object:
    if isinstance(entry, dict):
        return {k: v for k, v in entry.items() if k != "date"}
    return entry


def append_ledger(card: dict, entry: dict) -> bool:
    """Append entry to card['promotion_history'] unless the last one matches. True when appended."""
    history = card.get("promotion_history")
    history = list(history) if isinstance(history, list) else []
    same_kind = [item for item in history if isinstance(item, dict) and item.get("kind") == entry["kind"]]
    if same_kind:
        last = same_kind[-1]
        if _strip_date(last) == _strip_date(entry):
            return False
        # Re-applying the verdict that already moved the card is a no-op.
        if (
            entry.get("result") == "stay"
            and isinstance(last, dict)
            and last.get("result") in ("promote", "demote", "stay")
            and {k: v for k, v in last.items() if k not in ("date", "from", "result")}
            == {k: v for k, v in entry.items() if k not in ("date", "from", "result")}
        ):
            return False
    history.append(entry)
    card["promotion_history"] = history
    return True


# ---------------------------------------------------------------- checks

def _ok(detail: str = "") -> tuple[bool, str]:
    return True, detail


def _fail(detail: str) -> tuple[bool, str]:
    return False, detail


def c_not_excluded(ctx: Ctx, target: str) -> tuple[bool, str]:
    from scripts.catalog_eval_queue import QueueError, exclusion_reason
    try:
        reason = exclusion_reason(ctx.root, ctx.slug)
    except QueueError as exc:
        return _fail(f"exclusions unreadable: {exc}")
    if reason:
        return _fail(f"excluded: {reason}")
    return _ok()


def c_classifiable(ctx: Ctx, target: str) -> tuple[bool, str]:
    track = _ar().risk_track(ctx.card)
    if track == "unknown":
        return _fail("risk_class is invalid or the card has no uses, features, or tags to classify")
    return _ok(track)


def c_evidence(ctx: Ctx, target: str) -> tuple[bool, str]:
    stage, kinds = _av().evidence_ceiling(ctx.card, ctx.root, ctx.slug)
    have = min(RANK[stage], 2)
    need = min(RANK[target], 2)
    if have < need:
        return _fail(f"evidence {STAGES[have]}: {kinds}")
    return _ok(f"evidence {stage}: {kinds}")


def c_tier(ctx: Ctx, target: str) -> tuple[bool, str]:
    tier = ctx.card.get("tier_ceiling")
    tier = tier.strip() if isinstance(tier, str) else ""
    if tier not in RANK:
        return _ok("no tier_ceiling")
    if RANK[target] > RANK[tier]:
        return _fail(f"tier_ceiling {tier} caps {target}")
    return _ok(f"tier_ceiling {tier}")


def _gate(ctx: Ctx, key: str) -> tuple[bool, str]:
    verdict = ctx.verdict
    if not isinstance(verdict, dict):
        return _fail("no verdict")
    if verdict.get(key) != "pass":
        return _fail(f"{key} {verdict.get(key)!s}")
    return _ok(f"{key} pass")


def c_modularity(ctx: Ctx, target: str) -> tuple[bool, str]:
    return _gate(ctx, "modularity_gate")


def c_value(ctx: Ctx, target: str) -> tuple[bool, str]:
    return _gate(ctx, "value_gate")


def c_receipt(ctx: Ctx, target: str) -> tuple[bool, str]:
    problem = _av().receipt_problem(ctx.card, ctx.root, ctx.slug)
    if problem:
        return _fail(problem)
    return _ok("main-run receipt on origin/main")


def c_self_pipeline(ctx: Ctx, target: str) -> tuple[bool, str]:
    cap = _av()._self_pipeline_cap(ctx.name or ctx.slug, ctx.card)
    if cap is not None:
        return _fail("self_pipeline blocks I3 for a CI, testing, or review tool")
    return _ok()


def c_embed(ctx: Ctx, target: str) -> tuple[bool, str]:
    if _av()._has_embed(ctx.card):
        return _ok()
    return _fail("missing-embed")


def c_sandlock_verdict(ctx: Ctx, target: str) -> tuple[bool, str]:
    if not isinstance(ctx.verdict, dict):
        return _fail("no verdict")
    if ctx.verdict.get("sandbox") != "sandlock":
        return _fail("security verdict without sandbox sandlock")
    return _ok()


def _trial(ctx: Ctx) -> tuple[dict | None, str]:
    if "trial" in ctx.cache:
        return ctx.cache["trial"]
    rels: list[str] = []
    raw = ctx.card.get("evidence")
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and item.strip().endswith(TRIAL_NAME):
                text = item.strip()
                if ":" in text.split("/", 1)[0]:
                    text = text.split(":", 1)[1].strip()
                rels.append(text)
    default = f"eval/integrate/{ctx.slug}/{TRIAL_NAME}"
    if default not in rels:
        rels.append(default)
    found: tuple[dict | None, str] = (None, f"no {default}")
    for rel in rels:
        if rel.startswith("/") or ".." in Path(rel).parts:
            continue
        path = ctx.root / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            found = (None, f"{rel}: malformed")
            continue
        if not isinstance(data, dict):
            found = (None, f"{rel}: malformed")
            continue
        found = (data, rel)
        break
    ctx.cache["trial"] = found
    return found


def c_trial_clean(ctx: Ctx, target: str) -> tuple[bool, str]:
    data, rel = _trial(ctx)
    if data is None:
        return _fail(rel)
    problems = []
    if data.get("slug") != ctx.slug:
        problems.append("slug")
    if data.get("run_kind") != "sandbox-trial":
        problems.append("run_kind")
    if data.get("sandbox") != "sandlock":
        problems.append("sandbox")
    if data.get("outcome") != "ok":
        problems.append("outcome")
    if data.get("exit_code") != 0:
        problems.append("exit_code")
    if data.get("unsandboxed_lines") != 0:
        problems.append("unsandboxed_lines")
    if "scan_verdict" in data and data.get("scan_verdict") != "CLEAN":
        problems.append("scan_verdict")
    if problems:
        return _fail(f"{rel}: not clean ({', '.join(problems)})")
    return _ok(rel)


WRITE_ROOTS = ("./tmp/", "/tmp/", "$TMPDIR/", "$TMP/")


def profile_problems(profile: object) -> list[str]:
    """Empty when the sandlock profile is read-only by the rule."""
    if not isinstance(profile, dict):
        return ["profile missing"]
    problems: list[str] = []
    writes = profile.get("writes")
    if not isinstance(writes, list):
        problems.append("writes missing")
    else:
        for item in writes:
            text = str(item)
            if text != "/dev/null" and (".." in text.split("/") or not text.startswith(WRITE_ROOTS)):
                problems.append(f"write outside tmp: {text}")
    network = profile.get("network")
    if network != "deny" and not (isinstance(network, dict) and isinstance(network.get("pinned"), list)):
        problems.append(f"network {network!r}")
    if profile.get("sudo") is not False:
        problems.append("sudo not ruled out")
    if profile.get("clean_env") is not True:
        problems.append("env not clean")
    reads = profile.get("reads")
    if not isinstance(reads, list):
        problems.append("reads missing")
    else:
        for item in reads:
            text = str(item).rstrip("/")
            if text in ("$HOME", "~", "/home", "/root") or text.startswith("/home/") and text.count("/") <= 2:
                problems.append(f"reads the real home: {text}")
            elif any(part in text.split("/") for part in SECRET_PARTS):
                problems.append(f"reads a secrets path: {text}")
    return problems


def c_profile(ctx: Ctx, target: str) -> tuple[bool, str]:
    data, rel = _trial(ctx)
    if data is None:
        return _fail(rel)
    problems = profile_problems(data.get("profile"))
    if problems:
        return _fail(f"{rel}: {'; '.join(problems)}")
    return _ok(rel)


def wiring_problems(card: dict, root: Path, slug: str) -> list[str]:
    wiring = card.get("wiring")
    if not isinstance(wiring, dict):
        return ["card has no wiring"]
    mode = wiring.get("mode")
    where = wiring.get("where")
    if mode not in ("advisory", "non-blocking", "deny-only"):
        return [f"wiring mode {mode!r} is not advisory, non-blocking, or deny-only"]
    if not isinstance(where, str) or not where.strip() or where.startswith("/") or ".." in Path(where).parts:
        return ["wiring where is not a repo path"]
    path = root / where
    if not path.is_file():
        return [f"wiring where {where} is missing"]
    if mode == "deny-only":
        test = wiring.get("fail_open_test")
        if not isinstance(test, str) or not (root / test).is_file():
            return ["deny-only guard has no fail_open_test file"]
        return []
    if where.startswith(".github/workflows/"):
        lines = path.read_text(encoding="utf-8").splitlines()
        marker = f"# pfy-advisory: {slug}"
        for index, line in enumerate(lines):
            if line.strip() != marker:
                continue
            for follow in lines[index + 1:index + 30]:
                if follow.strip() == "continue-on-error: true":
                    return []
                if follow.strip().startswith("- name:") or follow.strip().startswith("# pfy-advisory:"):
                    break
            return [f"{where}: step {marker!r} lacks continue-on-error: true"]
        return [f"{where}: no step marked {marker!r}"]
    return []


def c_wiring(ctx: Ctx, target: str) -> tuple[bool, str]:
    problems = wiring_problems(ctx.card, ctx.root, ctx.slug)
    if problems:
        return _fail("; ".join(problems))
    wiring = ctx.card["wiring"]
    return _ok(f"{wiring['mode']} {wiring['where']}")


def c_ci_green(ctx: Ctx, target: str) -> tuple[bool, str]:
    from scripts.catalog_park_retry import main_green, main_sha
    if "green" not in ctx.cache:
        sha = main_sha(ctx.root)
        ctx.cache["green"] = (main_green(ctx.root, sha), sha)
    green, sha = ctx.cache["green"]
    short = sha[:8] if sha else "?"
    if not green:
        return _fail(f"eval-structural not green on origin/main {short}")
    return _ok(f"eval-structural green on {short}")


def _hard(rid: str):
    def check(ctx: Ctx, target: str) -> tuple[bool, str]:
        stops = dict(_ar().hard_stops(ctx.card, ctx.approved))
        if rid in stops:
            return _fail(stops[rid])
        return _ok()
    return check


CHECKS = {
    "R-not-excluded": c_not_excluded,
    "R-classifiable": c_classifiable,
    "R-evidence": c_evidence,
    "R-tier-ceiling": c_tier,
    "R-modularity-gate": c_modularity,
    "R-value-gate": c_value,
    "R-main-receipt": c_receipt,
    "R-self-pipeline": c_self_pipeline,
    "R-embed": c_embed,
    "S-sandlock-verdict": c_sandlock_verdict,
    "S-sandlock-trial-clean": c_trial_clean,
    "S-profile-readonly": c_profile,
    "S-wiring": c_wiring,
    "S-ci-green": c_ci_green,
    "HS-live-money": _hard("HS-live-money"),
    "HS-release-deploy": _hard("HS-release-deploy"),
    "HS-secrets": _hard("HS-secrets"),
    "HS-runtime-takeover": _hard("HS-runtime-takeover"),
    "HS-gpu-unapproved": _hard("HS-gpu-unapproved"),
    "HS-pull-over-25gb-unapproved": _hard("HS-pull-over-25gb-unapproved"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print the promotion rules for one card. Writes nothing.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--slug", required=True)
    parser.add_argument("--mode", default="apply", choices=MODES)
    parser.add_argument("--target", default="I3", choices=STAGES[1:])
    parser.add_argument("--verdict", default="")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        rules = load_rules(root)
        card = json.loads((root / "data" / "stages" / f"{args.slug}.json").read_text(encoding="utf-8"))
        verdict = None
        if args.verdict:
            verdict = json.loads(Path(args.verdict).read_text(encoding="utf-8"))
        elif args.mode in ("ceiling", "apply"):
            _path, verdict = _ar().latest_verdict(root, args.slug)
        approved = _ar().load_approvals(root).get(args.slug, frozenset())
    except (RuleError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    ctx = Ctx(card=card, slug=args.slug, root=root, name=str(card.get("name") or args.slug),
              verdict=verdict, approved=approved, mode=args.mode)
    kind = "ceiling" if args.mode == "ceiling" else "stage"
    track = track_of(card)
    if args.mode == "launch":
        results = launch_results(rules, ctx)
    else:
        results = evaluate(rules, ctx, rule_ids(rules, kind, track, args.target), args.target)
    print(f"track {track}")
    for rid, ok, detail in results:
        print(f"{'pass' if ok else 'fail'}\t{rid}\t{detail}")
    return 0 if all(ok for _r, ok, _d in results) else 3


if __name__ == "__main__":
    raise SystemExit(main())
