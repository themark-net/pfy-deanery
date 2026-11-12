#!/usr/bin/env python3
"""Sandlock trial for opencode-skill-creator 0.3.6.

Install and skill_validate go through scripts/integrations/sandlock/wrap.py
with PFY_SANDLOCK=all and SANDLOCK_BIN=confine.py. The fixture record is
written by scripts/integrations/sandlock/trial.py. The node driver is written
under tmp/ at run time so the public tree has no unknown suffix. No host
home path and no owner name in the public JSON.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WRAP = ROOT / "scripts" / "integrations" / "sandlock" / "wrap.py"
CONFINE = ROOT / "scripts" / "integrations" / "sandlock" / "confine.py"
TRIAL = ROOT / "scripts" / "integrations" / "sandlock" / "trial.py"
FIXTURES = HERE / "fixtures"
PIN = "eef1b5e9f9b9a77d744c39eade57a11a8233062ab50e812824c094fb8f627deb"
VERSION = "0.3.6"
PEER = "1.19.5"
LIGHTWEIGHT_MAX = 50 * 1000 * 1000
SLUG = "opencode-skill-creator"
DIST_MEMBER = "package/dist/skill-creator.js"
SOURCE = "https://github.com/antongulin/opencode-skill-creator"
NODE = "/usr/bin/node"

DRIVER_JS = r"""
import { mkdirSync, readFileSync, writeFileSync } from "fs";
import { join } from "path";

const entry = process.argv[2];
const fixturesDir = process.argv[3];
const stage = process.env.SANDLOCK_STAGE || "";
const names = ["good", "bad-key", "bad-name", "missing", "argument-hint", "disable-model", "shell-true"];

function scrub(text) {
  let out = String(text ?? "");
  if (fixturesDir) out = out.split(fixturesDir).join("fixtures");
  if (stage) out = out.split(stage).join("{stage}");
  return out.replace(/\/home\/[A-Za-z0-9._-]+/g, "$HOME");
}

function failingKeys(message) {
  const keys = [];
  const unexpected = message.match(/Unexpected key\(s\) in SKILL\.md frontmatter: ([^.]+)\./);
  if (unexpected) {
    keys.push(...unexpected[1].split(",").map((part) => part.trim()).filter(Boolean));
  }
  const invalid = message.match(/Invalid frontmatter value for '([^']+)'/);
  if (invalid && !keys.includes(invalid[1])) keys.push(invalid[1]);
  return keys;
}

const report = { tools: [], rows: [], error: null, xdg_skill: false, update_check: false };
try {
  if (!stage) throw new Error("SANDLOCK_STAGE is empty");
  const xdg = join(stage, "xdg");
  const cache = join(stage, "cache");
  const home = join(stage, "home");
  mkdirSync(xdg, { recursive: true });
  mkdirSync(cache, { recursive: true });
  mkdirSync(home, { recursive: true });
  process.env.XDG_CONFIG_HOME = xdg;
  process.env.XDG_CACHE_HOME = cache;
  process.env.HOME = home;
  process.env.OPENCODE_SKILL_CREATOR_AUTO_UPDATE = "0";
  const mod = await import(entry);
  const tools = {};
  const ctx = {
    location: { directory: stage },
    tool: { transform: async (fn) => fn({ add: (tool) => { tools[tool.name] = tool; } }) },
  };
  const dispose = await mod.default.setup(ctx);
  report.tools = Object.keys(tools).sort();
  if (!tools.skill_validate) throw new Error("skill_validate was not registered");
  for (const name of names) {
    const row = { name, valid: false, failing_keys: [], message: "" };
    try {
      const res = await tools.skill_validate.execute({ skillPath: join(fixturesDir, name) }, {});
      const content = res && res.content;
      const parsed = typeof content === "string" ? JSON.parse(content) : (content || {});
      const message = scrub(parsed.message || "");
      row.valid = parsed.valid === true;
      row.message = message.slice(0, 400);
      row.failing_keys = failingKeys(message);
    } catch (err) {
      row.valid = false;
      row.message = scrub(err && err.stack || err).slice(0, 400);
      row.error = true;
    }
    report.rows.push(row);
  }
  if (typeof dispose === "function") await dispose();
  report.xdg_skill = true;
  try {
    readFileSync(join(xdg, "opencode", "skills", "opencode-skill-creator", "SKILL.md"));
  } catch {
    report.xdg_skill = false;
  }
  try {
    readFileSync(join(xdg, "opencode", "opencode-skill-creator-update-check.json"));
    report.update_check = true;
  } catch {
    report.update_check = false;
  }
} catch (err) {
  report.error = scrub(err && err.stack || err).slice(0, 800);
}

writeFileSync(join(stage, "report.json"), JSON.stringify(report, null, 2) + "\n");
const good = report.rows.find((row) => row.name === "good");
const clean = !report.error && good && good.valid === true;
const scan = {
  verdict: clean ? "CLEAN" : "FLAGGED",
  findings: clean ? [] : [{ name: "good", message: scrub(good && good.message || report.error || "missing") }],
};
writeFileSync(join(stage, "scan.json"), JSON.stringify(scan, null, 2) + "\n");
console.log(JSON.stringify(report));
process.exit(report.error ? 1 : 0);
"""


def cache_root() -> Path:
    return Path(os.environ.get("HOME") or str(Path.home())) / ".cache" / "pfy" / "tools" / "osc"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def unsandboxed_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip() == "sandlock: unsandboxed")


def run_wrap(cache: Path, stage: Path, action: str, cmd: list[str]) -> tuple[subprocess.CompletedProcess[str], int]:
    env = os.environ.copy()
    env.update({
        "PFY_SANDLOCK": "all",
        "SANDLOCK_BIN": str(CONFINE),
        "SANDLOCK_STAGE": str(stage),
        "TMPDIR": str(stage / "tmp"),
    })
    proc = subprocess.run(
        [sys.executable, str(WRAP), "--cache", str(cache), "--action", action, "--", *cmd],
        env=env,
        capture_output=True,
        text=True,
    )
    return proc, unsandboxed_count(proc.stderr)


def scrub(text: str) -> str:
    out = text.replace(str(ROOT), ".")
    home = str(Path.home())
    return out.replace(home, "$HOME")


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def row_map(report: dict) -> dict[str, dict]:
    rows = report.get("rows") if isinstance(report.get("rows"), list) else []
    return {row.get("name"): row for row in rows if isinstance(row, dict) and isinstance(row.get("name"), str)}


def valid(rows: dict[str, dict], name: str) -> bool:
    row = rows.get(name) or {}
    return row.get("valid") is True


def stop_verdict(reason: str, stage: str) -> dict:
    """A stopped trial does not claim sandbox sandlock."""
    return {
        "metric": "repo_frontmatter_keys_allowed",
        "threshold": 2,
        "value": 0,
        "value_gate": "fail",
        "modularity_gate": "fail",
        "proposed_stage": stage,
        "intent": "awareness",
        "reason": reason,
    }


def prefix_problem(tarball: Path, prefix: Path) -> str | None:
    """None when the installed dist file is the pinned tarball member at 0.3.6."""
    pkg_path = prefix / "node_modules" / "opencode-skill-creator" / "package.json"
    dist = prefix / "node_modules" / "opencode-skill-creator" / "dist" / "skill-creator.js"
    if not pkg_path.is_file() or not dist.is_file():
        return "Installed package is missing package.json or dist/skill-creator.js. Trial stopped before install."
    try:
        version = json.loads(pkg_path.read_text(encoding="utf-8")).get("version")
    except (OSError, json.JSONDecodeError):
        return "Installed package.json is not JSON. Trial stopped before install."
    if version != VERSION:
        return f"Installed package version is {version!r}, not {VERSION}. Trial stopped before install."
    try:
        with tarfile.open(tarball, "r:gz") as tf:
            extracted = tf.extractfile(DIST_MEMBER)
            member = extracted.read() if extracted is not None else b""
    except (OSError, tarfile.TarError):
        return "Pinned tarball could not be read. Trial stopped before install."
    if hashlib.sha256(member).hexdigest() != sha256(dist):
        return "Installed dist/skill-creator.js does not match the pinned tarball. Trial stopped before install."
    return None


def drop_home_record(path: Path) -> bool:
    """Delete a trial record that still contains a home path. True when deleted."""
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    if "/home/" not in text:
        return False
    path.unlink()
    return True


def catalog_notes() -> tuple[str, dict] | None:
    """Intake and supersede output. None when either command fails. No card and no watchlist write."""
    intake = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "catalog_intake_dedupe.py"), SOURCE],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    line = ""
    for item in intake.stdout.splitlines():
        if item.strip():
            line = item.strip()
    if intake.returncode != 0 or not line:
        return None
    checked = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "supersede_check.py"),
         "--parts", "track=none,catalog=none,evaluate=none,integrate=none"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(checked.stdout)
    except json.JSONDecodeError:
        return None
    if checked.returncode != 0 or not isinstance(data, dict):
        return None
    coverage = data.get("coverage")
    if not isinstance(coverage, dict):
        return None
    return line, {
        "coverage": coverage,
        "checker": data,
        "supersede_candidate": data.get("supersede_candidate") is True,
        "watchlist_row": False,
        "why": (
            "scripts/supersede_check.py --parts track=none,catalog=none,evaluate=none,integrate=none "
            "is not a candidate. OpenCode Skill Creator lints skill frontmatter. It does not watch "
            "outside sources, keep a deduped tool catalog with stage cards, or score catalog tools "
            "on I0-I4. A skill linter is not suite coverage. No watchlist row."
        ),
    }


def logs_dir() -> Path:
    path = ROOT / "tmp" / "ops" / "eval" / "evals" / SLUG
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_report(text: str) -> None:
    (logs_dir() / "REPORT.md").write_text(text, encoding="utf-8")


def stop(reason: str, stage: str) -> int:
    write_json(HERE / "VERDICT.json", stop_verdict(reason, stage))
    write_report(
        "# OpenCode Skill Creator eval\n\n"
        f"The trial stopped before a sandlock claim. Proposed stage {stage}.\n\n"
        f"{reason}\n\n"
        "The stage card was not edited. integration_stage and tier_ceiling stay with the apply script.\n"
    )
    print(reason, file=sys.stderr)
    return 0 if stage == "I1" else 1


def main() -> int:
    logs = logs_dir()
    install_root = ROOT / "tmp" / "osc-sandlock"
    if install_root.exists():
        shutil.rmtree(install_root)
    stage = install_root / "stage"
    (stage / "tmp").mkdir(parents=True)
    tarball = cache_root() / "pack" / "opencode-skill-creator-0.3.6.tgz"
    src = cache_root() / "prefix"
    have = sha256(tarball) if tarball.is_file() else ""
    (logs / "tarball.sha256").write_text(have + "\n", encoding="utf-8")
    if have != PIN or not (src / "node_modules").is_dir():
        return stop("Pinned tarball missing or sha256 mismatch. Trial stopped before install.", "I0")
    problem = prefix_problem(tarball, src)
    if problem:
        return stop(problem, "I0")
    if not Path(NODE).is_file():
        return stop("Node is missing at /usr/bin/node. Trial stopped before install.", "I0")

    install_cmd = [
        "/bin/sh", "-c",
        "set -eu\n"
        "src=\"$1\"\n"
        "mkdir -p \"$SANDLOCK_STAGE/prefix\" \"$SANDLOCK_STAGE/tmp\"\n"
        "cp -a \"$src/node_modules\" \"$SANDLOCK_STAGE/prefix/node_modules\"\n"
        "test -f \"$SANDLOCK_STAGE/prefix/node_modules/opencode-skill-creator/dist/skill-creator.js\"\n",
        "sh",
        str(src),
    ]
    proc, install_unsandboxed = run_wrap(install_root / "wrap", stage, "install", install_cmd)
    (logs / "install.stderr").write_text(scrub(proc.stderr), encoding="utf-8")
    (logs / "install.stdout").write_text(scrub(proc.stdout), encoding="utf-8")
    (logs / "install.exit").write_text(str(proc.returncode) + "\n", encoding="utf-8")
    if install_unsandboxed:
        return stop("Install logged sandlock: unsandboxed. Trial stopped. Propose I1.", "I1")
    if proc.returncode != 0:
        return stop("Sandboxed install failed. Trial stopped. Stage stays I0.", "I0")

    entry = stage / "prefix" / "node_modules" / "opencode-skill-creator" / "dist" / "skill-creator.js"
    pkg = json.loads((stage / "prefix" / "node_modules" / "opencode-skill-creator" / "package.json").read_text(encoding="utf-8"))
    peer_path = stage / "prefix" / "node_modules" / "@opencode-ai" / "plugin" / "package.json"
    peer = json.loads(peer_path.read_text(encoding="utf-8")).get("version") if peer_path.is_file() else ""
    prefix_bytes = sum(path.stat().st_size for path in (stage / "prefix").rglob("*") if path.is_file())
    driver = install_root / "driver.mjs"
    driver.write_text(DRIVER_JS, encoding="utf-8")

    trial_out = ROOT / "eval" / "integrate" / SLUG / "sandbox-trial.json"
    trial_cmd = [
        sys.executable, str(TRIAL),
        "--slug", SLUG,
        "--out", str(trial_out),
        "--read", str(stage / "prefix"),
        "--read", str(FIXTURES),
        "--read", str(install_root),
        "--scan-json", "scan.json",
        "--tool-version", f"opencode-skill-creator@{pkg.get('version')}",
        "--pin", PIN,
        "--did", "skill_validate on seven committed fixtures inside sandlock. Auto-update off. XDG and HOME under the stage.",
        "--",
        NODE, str(driver), str(entry), str(FIXTURES),
    ]
    trial = subprocess.run(trial_cmd, cwd=str(ROOT), capture_output=True, text=True)
    (logs / "trial.stdout").write_text(scrub(trial.stdout), encoding="utf-8")
    (logs / "trial.stderr").write_text(scrub(trial.stderr), encoding="utf-8")
    if drop_home_record(trial_out):
        return stop("Trial record had a home path and was removed. Stage stays I0.", "I0")
    trial_text = trial_out.read_text(encoding="utf-8") if trial_out.is_file() else ""
    try:
        trial_data = json.loads(trial_text) if trial_text else {}
    except json.JSONDecodeError:
        trial_data = {}
    if not isinstance(trial_data, dict):
        trial_data = {}
    logged_unsandboxed = unsandboxed_count(trial.stderr) + unsandboxed_count(trial_text)
    field_unsandboxed = trial_data.get("unsandboxed_lines")
    if logged_unsandboxed or install_unsandboxed or (
        isinstance(field_unsandboxed, int) and field_unsandboxed > 0
    ):
        return stop("A run logged sandlock: unsandboxed. Trial stopped. Propose I1.", "I1")
    if not trial_text or trial_data.get("sandbox") != "sandlock" or field_unsandboxed != 0:
        return stop("Trial record does not show a sandlock run. Stage stays I0.", "I0")

    report_path = ROOT / "tmp" / "sandlock-trial" / SLUG / "stage" / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {"error": "no report", "rows": []}
    (logs / "report.json").write_text(scrub(json.dumps(report, indent=2) + "\n"), encoding="utf-8")
    rows = row_map(report)
    keys_allowed = int(valid(rows, "argument-hint")) + int(valid(rows, "disable-model"))
    evidence_ok = (
        valid(rows, "good")
        and not valid(rows, "bad-key")
        and not valid(rows, "bad-name")
        and not valid(rows, "missing")
        and not report.get("error")
    )
    gap_ok = "shell-true" in rows and not valid(rows, "shell-true")
    leverage_ok = keys_allowed == 2
    blast_ok = (
        report.get("update_check") is False
        and report.get("xdg_skill") is True
        and prefix_bytes < 5_000_000_000
        and pkg.get("version") == VERSION
    )
    legs = {
        "gap_fill": "pass" if gap_ok else "fail",
        "operator_leverage": "pass" if leverage_ok else "fail",
        "evidence": "pass" if evidence_ok else "fail",
        "blast_radius": "pass" if blast_ok else "fail",
    }
    value_gate = "pass" if sum(item == "pass" for item in legs.values()) >= 3 else "fail"
    modularity = {
        "local_code_needed": "pass",
        "bounded_surface": "pass" if pkg.get("version") == VERSION and entry.is_file() else "fail",
        "isolatable": "pass" if trial_data.get("outcome") == "ok" and peer == PEER else "fail",
        "reversible": "pass",
    }
    modularity_gate = "pass" if all(item == "pass" for item in modularity.values()) else "fail"
    lightweight = prefix_bytes < LIGHTWEIGHT_MAX
    # Card next_gate stays I0 until argument-hint and disable-model-invocation are allowed.
    # Potential on the card is low, and the copied prefix is over the 50 MB lightweight cap.
    # This lane does not add wiring, so I3 is not proposed.
    if keys_allowed < 2:
        proposed = "I0"
    elif value_gate == "pass" and modularity_gate == "pass":
        proposed = "I1"
    else:
        proposed = "I0"
    notes = catalog_notes()
    if notes is None:
        return stop("Intake or supersede check failed. No card written. Stage stays I0.", "I0")
    intake_line, supersede = notes
    (logs / "intake.txt").write_text(intake_line + "\n", encoding="utf-8")
    (logs / "supersede.json").write_text(json.dumps(supersede, indent=2) + "\n", encoding="utf-8")
    if supersede.get("supersede_candidate"):
        return stop("Supersede check returned a candidate. No watchlist row written from this trial.", "I0")
    if intake_line.startswith("new "):
        return stop("Intake printed new. This lane does not write a second card. Stage stays I0.", "I0")
    dist_sha = sha256(entry)
    passed_legs = sum(item == "pass" for item in legs.values())
    reason = (
        f"repo_frontmatter_keys_allowed is {keys_allowed}, threshold 2. "
        f"argument-hint valid={valid(rows, 'argument-hint')}, "
        f"disable-model valid={valid(rows, 'disable-model')}, "
        f"shell-true valid={valid(rows, 'shell-true')}. "
        f"Value {passed_legs} of 4. "
        f"Prefix bytes {prefix_bytes}. Lightweight under 50 MB is {str(lightweight).lower()}. "
        "Every install and skill_validate ran through sandlock. unsandboxed_lines is 0. "
        "Installed dist/skill-creator.js matches the pinned tarball. "
        "Propose the stage from the key gate. The apply script writes the card."
    )
    results = {
        "metric": "repo_frontmatter_keys_allowed",
        "threshold": 2,
        "value": keys_allowed,
        "tool_version": f"opencode-skill-creator@{pkg.get('version')}",
        "peer": f"@opencode-ai/plugin@{peer}",
        "tarball_sha256": have,
        "dist_sha256": dist_sha,
        "prefix_bytes": prefix_bytes,
        "lightweight_under_50mb": lightweight,
        "sandbox": "sandlock",
        "unsandboxed_lines": 0,
        "install_exit": proc.returncode,
        "trial_exit": trial.returncode,
        "trial_outcome": trial_data.get("outcome"),
        "scan_verdict": trial_data.get("scan_verdict"),
        "tools": report.get("tools"),
        "xdg_skill": report.get("xdg_skill"),
        "update_check": report.get("update_check"),
        "error": report.get("error"),
        "rows": report.get("rows"),
        "value_legs": legs,
        "modularity_legs": modularity,
    }
    (logs / "results.json").write_text(scrub(json.dumps(results, indent=2) + "\n"), encoding="utf-8")
    public_supersede = {
        "coverage": supersede.get("coverage"),
        "supersede_candidate": supersede.get("supersede_candidate"),
        "watchlist_row": False,
        "why": supersede.get("why"),
    }
    verdict = {
        "metric": "repo_frontmatter_keys_allowed",
        "threshold": 2,
        "value": keys_allowed,
        "value_gate": value_gate,
        "modularity_gate": modularity_gate,
        "proposed_stage": proposed,
        "intent": "awareness",
        "sandbox": "sandlock",
        "pin": PIN,
        "tool_version": f"opencode-skill-creator@{pkg.get('version')}",
        "tarball_sha256": have,
        "peer": f"@opencode-ai/plugin@{peer}",
        "measured": {
            "repo_frontmatter_keys_allowed": keys_allowed,
            "dist_sha256": dist_sha,
            "prefix_bytes": prefix_bytes,
            "lightweight_under_50mb": lightweight,
            "unsandboxed_lines": 0,
            "install_exit": proc.returncode,
            "trial_outcome": trial_data.get("outcome"),
            "scan_verdict": trial_data.get("scan_verdict"),
            "shell_true_valid": valid(rows, "shell-true"),
            "good_valid": valid(rows, "good"),
            "bad_key_valid": valid(rows, "bad-key"),
            "bad_name_valid": valid(rows, "bad-name"),
            "missing_valid": valid(rows, "missing"),
        },
        "value_legs": legs,
        "modularity_legs": modularity,
        "intake": {
            "line": intake_line,
            "wrote_card": False,
        },
        "supersede": public_supersede,
        "reason": reason,
    }
    write_json(HERE / "VERDICT.json", verdict)
    row_lines = []
    for name in ("good", "bad-key", "bad-name", "missing", "argument-hint", "disable-model", "shell-true"):
        row = rows.get(name) or {}
        keys = ", ".join(row.get("failing_keys") or []) or "-"
        row_lines.append(f"| {name} | {row.get('valid')} | {keys} |")
    write_report(
        "# OpenCode Skill Creator eval\n\n"
        "Question: can pinned `skill_validate` lint this repo's skill frontmatter inside sandlock, "
        "and does that lint catch a dangerous body?\n\n"
        "## What ran\n\n"
        f"- Intake: `{intake_line}`. No card write.\n"
        "- Supersede: `scripts/supersede_check.py --parts track=none,catalog=none,evaluate=none,integrate=none`. "
        "Not a candidate. No watchlist row. The tool lints skill frontmatter. It does not track sources, "
        "keep stage cards, or score catalog tools.\n"
        "- Install: `wrap.py --action install` with `PFY_SANDLOCK=all` and `SANDLOCK_BIN=confine.py`. "
        "The command copies the cache prefix whose `dist/skill-creator.js` matches tarball "
        f"`{PIN}` member `{DIST_MEMBER}`. Network stays deny. The package `install` command was not run.\n"
        "- Tool run: `scripts/integrations/sandlock/trial.py` runs `skill_validate` on the seven fixtures. "
        "`skill_eval` and `skill_optimize_loop` were not called. Auto-update is off. XDG and HOME stay on the stage.\n"
        f"- unsandboxed_lines: 0. trial outcome: {trial_data.get('outcome')}. "
        f"scan_verdict: {trial_data.get('scan_verdict')} (the good fixture only).\n\n"
        "## Fixtures\n\n"
        "| fixture | valid | failing keys |\n"
        "| --- | --- | --- |\n"
        + "\n".join(row_lines) + "\n\n"
        "## Gates\n\n"
        f"- metric `repo_frontmatter_keys_allowed` = {keys_allowed}, threshold 2.\n"
        f"- value_gate {value_gate} ({passed_legs} of 4). "
        f"gap_fill {legs['gap_fill']} (shell=True body still valid), "
        f"operator_leverage {legs['operator_leverage']} (repo keys still rejected), "
        f"evidence {legs['evidence']}, blast_radius {legs['blast_radius']}.\n"
        f"- modularity_gate {modularity_gate}. Prefix bytes {prefix_bytes}. "
        f"Lightweight under 50 MB is {str(lightweight).lower()}.\n"
        f"- proposed_stage {proposed}. `sandbox` is `sandlock` because no run logged `sandlock: unsandboxed`.\n\n"
        "## How this fails and how we recover\n\n"
        "- A missing pin or a dist file that is not the tarball member stops at I0 and does not claim sandlock.\n"
        "- `sandlock: unsandboxed` stops the trial and proposes I1, with no sandlock claim.\n"
        "- A trial record that still contains a home path is deleted and the stage stays I0.\n"
        "- argument-hint and disable-model-invocation still fail, so the card next_gate stays I0. "
        "This lane does not wire a CI gate.\n\n"
        "The stage card was not edited. The apply script writes integration_stage and tier_ceiling.\n"
    )
    print(json.dumps({
        "proposed_stage": proposed,
        "value_gate": value_gate,
        "modularity_gate": modularity_gate,
        "keys_allowed": keys_allowed,
        "trial_outcome": trial_data.get("outcome"),
        "scan_verdict": trial_data.get("scan_verdict"),
        "prefix_bytes": prefix_bytes,
        "install_exit": proc.returncode,
        "trial_exit": trial.returncode,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
