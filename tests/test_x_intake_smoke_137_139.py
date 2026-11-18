"""Entries 137-139 smokes (neatroots, Hermes Teammates, OpenCode Skill Creator): pins and missing prereqs exit 2,
broken rules, open configs, a leaky ledger, misplaced start-up writes and real-HOME changes FAIL, timeouts FAIL with
the real-HOME check kept.

Each tool is a small Python stub (shebang = this interpreter) that behaves like the real thing for what the smoke does;
knobs are baked into the stub text because the smoke gives its children a clean env. neatroots and the skill creator
are Node programs, so the stub is a fake `node` that answers `--version`, runs a fake `cli.js check` over the JSONL
fixtures (repeat, sk- secret and --checks requires_before rules) or plays the skill-creator driver (reads the fixture
SKILL.md files, writes the bundled skill under XDG_CONFIG_HOME). Hermes Teammates is Python, so the stub is a fake
clone: a git repo with plugin.yaml and small teammates_config.py / teammates_store.py modules. Parent HOME is a temp dir
this test owns; children get another temp HOME, so a planted real-HOME write uses the parent HOME's absolute path. bwrap
is found on the smoke process PATH, so tests that need a plant to land set PATH to an empty dir (children use a fixed
system PATH). Receipts go to a temp $PFY_SMOKE_RECEIPT_DIR.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "examples/x-intake-local/smoke_137_139.py"
_RECEIPTS = tempfile.TemporaryDirectory(prefix="pfy-xintake-137-receipts-")
RECEIPT_DIR = Path(_RECEIPTS.name)
HAVE_GIT = shutil.which("git") is not None


def tearDownModule() -> None:
    _RECEIPTS.cleanup()


def _write_stub(path: Path, knobs: dict, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!{sys.executable}\nK = {knobs!r}\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


COMMON = r'''
import json, os, re, sys, time
if K.get("plant"):
    exec(K["plant"])
'''

# fake node for neatroots: `node --version`, `node cli.js --version`, `node cli.js check ...`
NR_NODE = COMMON + r'''
a = sys.argv[1:]
if a == ["--version"]:
    time.sleep(K.get("sleep_version", 0))
    print("v" + K.get("node", "24.14.1"))
    sys.exit(0)
if a[1:] == ["--version"]:
    print(K.get("cli_version", "0.2.9"))
    sys.exit(0)
assert a[1] == "check", a
rest = a[2:]
files, checks, only, js = [], [], None, False
i = 0
while i < len(rest):
    x = rest[i]
    if x == "--json":
        js = True
    elif x == "--only":
        i += 1
        only = rest[i].split(",")
    elif x == "--checks":
        i += 1
        checks.append(rest[i])
    else:
        files.append(x)
    i += 1
tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), "neatroots-check-stub")
os.makedirs(tmp, exist_ok=True)
lib = ["repeated-tool-call", "secret-in-output"] + ["r%d" % n for n in range(11)]
proj = []
for d in checks:
    for f in sorted(os.listdir(d)):
        if "requires_before" in open(os.path.join(d, f)).read():
            proj.append("pfy-refund-needs-lookup")
rules = (lib + proj) if not only or K.get("only_ignored") else [r for r in lib + proj if r in only]
runs, errors = [], []
for f in files:
    try:
        lines = [json.loads(l) for l in open(f) if l.strip()]
    except ValueError as e:
        print("x %s: %s" % (f, e), file=sys.stderr)
        if not K.get("leave_tmp"):
            os.rmdir(tmp)
        sys.exit(1 if K.get("broken_exit_1") else 2)
    if K.get("mutate_fixture"):
        open(f, "a").write("\n")
    for t in lines:
        kids = t.get("children", [])
        tools = [c for c in kids if c.get("kind") == "TOOL"]
        llms = [c for c in kids if c.get("kind") == "LLM"]
        fs = []
        sigs = [json.dumps([c["name"], c.get("input"), c.get("output")]) for c in tools]
        if not K.get("no_repeat") and any(sigs.count(s) >= 3 for s in sigs):
            fs.append({"check_id": "repeated-tool-call", "params": {"tool": tools[0]["name"], "count": "3"}})
        if any(re.search(r"sk-[A-Za-z0-9_-]{20,}", str(c.get("output"))) for c in llms):
            p = {"count": "1"}
            if K.get("echo_secret"):
                p["match"] = re.search(r"sk-[A-Za-z0-9_-]{20,}", str(llms[0].get("output"))).group(0)
            fs.append({"check_id": "secret-in-output", "params": p})
        names = [c["name"] for c in tools]
        if proj and ("refund" in names and "lookup_order" not in names or K.get("project_everywhere")):
            fs.append({"check_id": "pfy-refund-needs-lookup", "params": {"tool": "refund"}})
        if K.get("clean_finding") and t["name"] == "pfy-clean":
            fs.append({"check_id": "r1", "params": {}})
        fs = [x for x in fs if x["check_id"] in rules]
        runs.append({"file": f, "root_name": t["name"], "findings": fs})
if not K.get("leave_tmp"):
    os.rmdir(tmp)
out = {"runs": runs, "rules": rules, "errors": errors}
print(json.dumps(out) if js else "summary")
sys.exit(1 if any(r["findings"] for r in runs) else 0)
'''

# fake node for the skill creator: `node --version`, `node driver.mjs spec.json`
OSC_NODE = COMMON + r'''
a = sys.argv[1:]
if a == ["--version"]:
    time.sleep(K.get("sleep_version", 0))
    print("v" + K.get("node", "20.19.2"))
    sys.exit(0)
spec = json.load(open(a[1]))
if K.get("error"):
    print(json.dumps({"error": "Error: Cannot find package '@opencode-ai/plugin'"}))
    sys.exit(0)
xdg, cache = os.environ["XDG_CONFIG_HOME"], os.environ["XDG_CACHE_HOME"]
root = os.environ["HOME"] if K.get("bundle_to_home") else xdg
if not K.get("skip_bundle"):
    d = os.path.join(root, "opencode", "skills", "opencode-skill-creator")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "SKILL.md"), "w").write("---\nname: opencode-skill-creator\n---\n")
if K.get("write_status"):
    os.makedirs(os.path.join(xdg, "opencode"), exist_ok=True)
    open(os.path.join(xdg, "opencode", "opencode-skill-creator-update-check.json"), "w").write("{}")
if K.get("write_cache"):
    os.makedirs(os.path.join(cache, "opencode", "packages"), exist_ok=True)
tools = ["skill_validate", "skill_parse", "skill_eval"] + ["t%d" % n for n in range(11)]
if K.get("fewer_tools"):
    tools = tools[:-1]
out = {"tools": sorted(tools)}
ALLOWED = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
for s in ("good", "badkey", "BadName", "missing"):
    p = os.path.join(spec["proj"], "skills", s, "SKILL.md")
    if not os.path.exists(p):
        out[s] = {"valid": False, "message": "SKILL.md not found"}
        continue
    fm = dict(l.split(": ", 1) for l in open(p).read().split("---")[1].strip().splitlines())
    extra = set(fm) - ALLOWED
    if extra and not K.get("accept_badkey"):
        out[s] = {"valid": False, "message": "Unexpected key(s) in SKILL.md frontmatter: " + ", ".join(sorted(extra))}
    elif not re.fullmatch(r"[a-z0-9-]+", fm["name"]) and not K.get("accept_badname"):
        out[s] = {"valid": False, "message": "Name '%s' should be kebab-case" % fm["name"]}
    else:
        out[s] = {"valid": True, "message": "Skill is valid!"}
gp = os.path.join(spec["proj"], "skills", "good", "SKILL.md")
fm = dict(l.split(": ", 1) for l in open(gp).read().split("---")[1].strip().splitlines())
out["parse"] = {"name": fm["name"], "description": fm["description"]}
if K.get("mutate_fixture"):
    open(gp, "a").write("x")
print(json.dumps(out))
'''

HT_CONFIG = r'''
import re, time
K = __K__
if K.get("plant"):
    exec(K["plant"])
time.sleep(K.get("sleep_import", 0))
NAME = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
FIELDS = {"description", "instructions", "toolsets", "model", "route", "reasoning_effort"}


def parse(raw):
    errors, teammates, invalid = [], {}, {}
    res = {"max_live_runs": 4}
    v = raw.get("max_live_runs", 4)
    if isinstance(v, int) and 1 <= v <= 16:
        res["max_live_runs"] = v
    elif K.get("keep_bad_setting"):
        res["max_live_runs"] = v
    else:
        errors.append("max_live_runs: expected integer 1..16; using default")
    for name, vals in raw.get("teammates", {}).items():
        if not NAME.fullmatch(name) and not K.get("accept_bad_name"):
            errors.append("invalid teammate name: " + name)
            invalid[name] = errors[-1:]
            continue
        start, warn = len(errors), []
        if not K.get("accept_unknown_key"):
            for k in sorted(set(vals) - FIELDS):
                errors.append("%s: unknown key %s" % (name, k))
        t = {"description": vals.get("description", ""), "instructions": vals.get("instructions", ""),
             "toolsets": vals.get("toolsets")}
        if len(t["instructions"]) > 4000:
            if K.get("invalid_on_long"):
                errors.append(name + ".instructions: too long")
            elif not K.get("no_clip"):
                t["instructions"] = t["instructions"][:4000]
                warn.append(name + ".instructions: clipped to 4000")
        ts = vals.get("toolsets")
        if ts is not None and not (isinstance(ts, list) and ts) and not K.get("accept_empty_toolsets"):
            errors.append(name + ".toolsets: expected 1-24 toolset names")
        if ts is None and K.get("default_toolsets"):
            t["toolsets"] = ["all"]
        teammates[name] = t
        if len(errors) > start:
            invalid[name] = errors[start:]
        errors.extend(warn)
    res.update(teammates=teammates, invalid_teammates=invalid, config_errors=errors)
    return res
'''

HT_STORE = r'''
import sqlite3
K = __K__
COLS = {"run_id", "teammate", "owner_session_id", "goal", "status", "instance_id", "pid", "created_at", "summary"}


class Store:
    def __init__(self, conn):
        self.conn = conn
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, teammate TEXT, owner_session_id TEXT,"
                     " goal TEXT, status TEXT, instance_id TEXT, pid INTEGER, created_at REAL, summary TEXT)")

    def insert(self, row):
        if not set(row) <= COLS and not K.get("accept_columns"):
            raise ValueError("unknown run columns")
        row = {k: v for k, v in row.items() if k in COLS}
        with self.conn:
            self.conn.execute("INSERT INTO runs (%s) VALUES (%s)" % (",".join(row), ",".join("?" * len(row))),
                              tuple(row.values()))

    def admit(self, row, cap):
        live = self.conn.execute("SELECT count(*) FROM runs WHERE owner_session_id=? AND status='running'",
                                 (row["owner_session_id"],)).fetchone()[0]
        if live >= cap and not K.get("no_cap"):
            return False
        self.insert(row)
        return True

    def get(self, run_id, owner):
        r = self.conn.execute("SELECT * FROM runs WHERE run_id=? AND owner_session_id=?", (run_id, owner)).fetchone()
        return dict(r) if r else None

    def finish(self, run_id, status, **values):
        if status not in {"succeeded", "failed", "interrupted", "cancelled", "unknown"} and not K.get("any_status"):
            raise ValueError("not a terminal status")
        where = "" if K.get("no_cas") else " AND status='running'"
        with self.conn:
            c = self.conn.execute("UPDATE runs SET status=? WHERE run_id=?" + where, (status, run_id))
        return c.rowcount == 1
'''


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory(prefix="pfy-xintake-137-test-")
        self.base = Path(self._td.name)
        self.home = self.base / "realhome"
        self.home.mkdir()
        self.nobwrap = self.base / "emptypath"
        self.nobwrap.mkdir()

    def tearDown(self) -> None:
        for p in self.base.rglob("*"):
            if not p.is_symlink():
                p.chmod(0o755 if p.is_dir() else 0o644)
        self._td.cleanup()

    def env(self, *, no_bwrap: bool = False, **extra: str) -> dict[str, str]:
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(("NEATROOTS_", "HT_", "HERMES_TEAMMATES_", "OSC_")) or key == "PFY_XINTAKE_TIMEOUT":
                env.pop(key, None)
        env["HOME"] = str(self.home)  # so $PFY_TMP lookups find nothing
        env["PFY_SMOKE_RECEIPT_DIR"] = str(RECEIPT_DIR)
        env["PATH"] = str(self.nobwrap) if no_bwrap else env.get("PATH", "/usr/bin:/bin")
        env.update(extra)
        return env

    def run_entry(self, entry: str, env: dict[str, str]) -> tuple[int, dict]:
        p = subprocess.run([sys.executable, SCRIPT, "--entry", entry], cwd=str(ROOT), env=env,
                           capture_output=True, text=True, timeout=180)
        self.assertNotIn("Traceback", p.stderr + p.stdout)
        receipt = json.loads((RECEIPT_DIR / entry / "latest.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["exit_code"], p.returncode)
        return p.returncode, receipt

    def plant_home(self, rel: str) -> str:
        target = self.home / rel
        return f"import pathlib; p = pathlib.Path({str(target)!r}); p.mkdir(parents=True, exist_ok=True); " \
               "(p / 'x').write_text('planted')"

    def assert_failed(self, code: int, r: dict, check: str) -> None:
        self.assertEqual(code, 1, r)
        self.assertFalse(r["checks"][check], r)
        self.assertIn(check, r["reason"])

    def assert_home_changed(self, r: dict, rel: str) -> None:
        self.assertFalse(r["checks"]["real_home_untouched"], r)
        self.assertIn(f"~/{rel}", r["real_home_changed"])
        self.assertIn(f"~/{rel}", r["reason"])


TEMP_HOME_PLANT = "import os; open(os.path.join(os.environ['HOME'], 'x'), 'w').write('x')"


# ---------------------------------------------------------------- neatroots
class NeatrootsTests(Base):
    def stub(self, version: str = "0.2.9", **knobs) -> dict[str, str]:
        app = self.base / "app"
        (app / "neatroots/dist").mkdir(parents=True, exist_ok=True)
        (app / "neatroots/dist/cli.js").write_text("// stub\n")
        (app / "neatroots/package.json").write_text(json.dumps({"version": version}))
        node = _write_stub(self.base / "bin/node", knobs, NR_NODE)
        return {"NEATROOTS_APP": str(app), "NEATROOTS_NODE": str(node)}

    def go(self, *, no_bwrap: bool = False, timeout: str = "", version: str = "0.2.9", **knobs) -> tuple[int, dict]:
        extra = self.stub(version, **knobs)
        if timeout:
            extra["PFY_XINTAKE_TIMEOUT"] = timeout
        return self.run_entry("neatroots", self.env(no_bwrap=no_bwrap, **extra))

    def test_missing_app_exits_2(self) -> None:
        code, r = self.run_entry("neatroots", self.env(NEATROOTS_APP=str(self.base / "nope")))
        self.assertEqual(code, 2)
        self.assertIn("neatroots not found", r["reason"])

    def test_old_node_exits_2(self) -> None:
        code, r = self.go(node="20.19.2")
        self.assertEqual(code, 2)
        self.assertIn("Node 22+", r["reason"])

    def test_package_version_mismatch_exits_2(self) -> None:
        code, r = self.go(version="0.2.8")
        self.assertEqual(code, 2)
        self.assertIn("0.2.8", r["reason"])

    def test_cli_version_mismatch_exits_2(self) -> None:
        code, r = self.go(cli_version="0.3.0")
        self.assertEqual(code, 2)
        self.assertIn("0.3.0", r["reason"])

    def test_happy_path_passes(self) -> None:
        code, r = self.go()
        self.assertEqual(code, 0, r)
        self.assertTrue(all(r["checks"].values()), r)
        self.assertIn("~/.neatroots", r["reason"])

    def test_clean_run_with_finding_fails(self) -> None:
        self.assert_failed(*self.go(clean_finding=True), "clean_exit_0_no_findings")

    def test_no_repeat_rule_fails(self) -> None:
        self.assert_failed(*self.go(no_repeat=True), "repeat_fires_with_params")

    def test_echoed_secret_fails(self) -> None:
        self.assert_failed(*self.go(echo_secret=True), "secret_never_echoed")

    def test_project_rule_everywhere_fails(self) -> None:
        self.assert_failed(*self.go(project_everywhere=True), "project_rule_fires_only_on_refund")

    def test_only_ignored_fails(self) -> None:
        self.assert_failed(*self.go(only_ignored=True), "only_narrows_rules")

    def test_broken_file_exit_1_fails(self) -> None:
        self.assert_failed(*self.go(broken_exit_1=True), "unparsable_file_exits_2")

    def test_left_tmpdir_fails(self) -> None:
        self.assert_failed(*self.go(leave_tmp=True), "check_tmpdir_cleaned")

    def test_fixture_write_fails(self) -> None:
        self.assert_failed(*self.go(mutate_fixture=True), "fixtures_untouched")

    def test_temp_home_write_fails(self) -> None:
        self.assert_failed(*self.go(plant=TEMP_HOME_PLANT), "home_untouched")

    def test_real_home_write_fails_without_bwrap(self) -> None:
        code, r = self.go(no_bwrap=True, plant=self.plant_home(".neatroots"))
        self.assertEqual(code, 1)
        self.assert_home_changed(r, ".neatroots")

    def test_seeded_real_home_untouched_passes(self) -> None:
        (self.home / ".neatroots/checks").mkdir(parents=True)
        (self.home / ".neatroots/checks/mine.yaml").write_text("id: mine\n")
        code, r = self.go(no_bwrap=True)
        self.assertEqual(code, 0, r)
        self.assertTrue(r["checks"]["real_home_untouched"])

    def test_timeout_fails_and_keeps_home_check(self) -> None:
        code, r = self.go(no_bwrap=True, timeout="1", sleep_version=5, plant=self.plant_home(".neatroots"))
        self.assertEqual(code, 1)
        self.assertIn("node version timeout after 1s", r["reason"])
        self.assertFalse(r["checks"]["body_completed"])
        self.assert_home_changed(r, ".neatroots")


# ---------------------------------------------------------------- teammates
@unittest.skipUnless(HAVE_GIT, "git needed for the fake clone")
class TeammatesTests(Base):
    def clone(self, version: str = "1.1.0", **knobs) -> tuple[Path, str]:
        d = self.base / "hermes-teammates"
        d.mkdir(exist_ok=True)
        (d / "plugin.yaml").write_text(f"name: hermes-teammates\nversion: {version}\n")
        (d / "teammates_config.py").write_text(HT_CONFIG.replace("__K__", repr(knobs)))
        (d / "teammates_store.py").write_text(HT_STORE.replace("__K__", repr(knobs)))
        g = ["git", "-C", str(d), "-c", "user.email=t@localhost", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
        subprocess.run(g[:3] + ["init", "-q"], check=True)
        subprocess.run(g + ["add", "-A"], check=True)
        subprocess.run(g + ["commit", "-q", "-m", "stub"], check=True)
        sha = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        return d, sha

    def go(self, *, no_bwrap: bool = False, timeout: str = "", version: str = "1.1.0", commit: str | None = None,
           **knobs) -> tuple[int, dict]:
        d, sha = self.clone(version, **knobs)
        extra = {"HERMES_TEAMMATES_DIR": str(d), "HT_COMMIT": commit or sha}
        if timeout:
            extra["PFY_XINTAKE_TIMEOUT"] = timeout
        return self.run_entry("teammates", self.env(no_bwrap=no_bwrap, **extra))

    def test_missing_clone_exits_2(self) -> None:
        code, r = self.run_entry("teammates", self.env(HERMES_TEAMMATES_DIR=str(self.base / "nope")))
        self.assertEqual(code, 2)
        self.assertIn("hermes-teammates clone not found", r["reason"])

    def test_version_mismatch_exits_2(self) -> None:
        code, r = self.go(version="1.0.0")
        self.assertEqual(code, 2)
        self.assertIn("1.0.0", r["reason"])

    def test_commit_mismatch_exits_2(self) -> None:
        code, r = self.go(commit="0" * 40)
        self.assertEqual(code, 2)
        self.assertIn("clone HEAD", r["reason"])

    def test_default_pin_rejects_other_commit(self) -> None:
        d, _ = self.clone()
        code, r = self.run_entry("teammates", self.env(HERMES_TEAMMATES_DIR=str(d)))
        self.assertEqual(code, 2)
        self.assertIn("de85f5d4793e", r["reason"])

    def test_happy_path_passes(self) -> None:
        code, r = self.go()
        self.assertEqual(code, 0, r)
        self.assertTrue(all(r["checks"].values()), r)
        self.assertEqual(r["admit"], [True, True, False, True])

    def test_unknown_key_accepted_fails(self) -> None:
        self.assert_failed(*self.go(accept_unknown_key=True), "unknown_key_fails_closed")

    def test_bad_name_accepted_fails(self) -> None:
        self.assert_failed(*self.go(accept_bad_name=True), "bad_name_fails_closed")

    def test_empty_toolsets_accepted_fails(self) -> None:
        self.assert_failed(*self.go(accept_empty_toolsets=True), "empty_toolsets_fails_closed")

    def test_toolsets_not_inherited_fails(self) -> None:
        self.assert_failed(*self.go(default_toolsets=True), "absent_toolsets_inherit")

    def test_long_instructions_not_clipped_fails(self) -> None:
        self.assert_failed(*self.go(no_clip=True), "long_instructions_clipped_not_invalid")

    def test_long_instructions_invalid_fails(self) -> None:
        self.assert_failed(*self.go(invalid_on_long=True), "long_instructions_clipped_not_invalid")

    def test_bad_setting_kept_fails(self) -> None:
        self.assert_failed(*self.go(keep_bad_setting=True), "out_of_range_setting_defaults")

    def test_no_admission_cap_fails(self) -> None:
        self.assert_failed(*self.go(no_cap=True), "admission_cap_per_session")

    def test_finish_twice_fails(self) -> None:
        self.assert_failed(*self.go(no_cas=True), "finish_is_single_terminal_cas")

    def test_nonterminal_finish_accepted_fails(self) -> None:
        self.assert_failed(*self.go(any_status=True), "finish_nonterminal_raises")

    def test_unknown_column_accepted_fails(self) -> None:
        self.assert_failed(*self.go(accept_columns=True), "unknown_column_raises")

    def test_write_into_clone_fails_without_bwrap(self) -> None:
        plant = "import pathlib; (pathlib.Path(__file__).parent / 'teammates_store.py').write_text('x = 1\\n' + " \
                "(pathlib.Path(__file__).parent / 'teammates_store.py').read_text())"
        code, r = self.go(no_bwrap=True, plant=plant)
        self.assertEqual(code, 1, r)
        self.assertFalse(r["checks"]["clone_untouched"], r)

    def test_temp_home_write_fails(self) -> None:
        self.assert_failed(*self.go(plant=TEMP_HOME_PLANT), "home_untouched")

    def test_real_home_write_fails_without_bwrap(self) -> None:
        code, r = self.go(no_bwrap=True, plant=self.plant_home(".hermes/plugin-data/hermes-teammates"))
        self.assertEqual(code, 1)
        self.assert_home_changed(r, ".hermes/plugin-data/hermes-teammates")

    def test_other_hermes_paths_not_watched(self) -> None:
        code, r = self.go(no_bwrap=True, plant=self.plant_home(".hermes/other"))
        self.assertEqual(code, 0, r)

    def test_timeout_fails_and_keeps_home_check(self) -> None:
        code, r = self.go(no_bwrap=True, timeout="2", sleep_import=6,
                          plant=self.plant_home(".hermes/plugin-data/hermes-teammates"))
        self.assertEqual(code, 1)
        self.assertIn("teammates driver timeout after 2s", r["reason"])
        self.assertFalse(r["checks"]["body_completed"])
        self.assert_home_changed(r, ".hermes/plugin-data/hermes-teammates")


# ---------------------------------------------------------------- skillcreator
class SkillCreatorTests(Base):
    def stub(self, version: str = "0.3.6", **knobs) -> dict[str, str]:
        pkg = self.base / "osc/node_modules/opencode-skill-creator"
        (pkg / "dist").mkdir(parents=True, exist_ok=True)
        (pkg / "dist/skill-creator.js").write_text("// stub\n")
        (pkg / "package.json").write_text(json.dumps({"version": version}))
        node = _write_stub(self.base / "bin/node", knobs, OSC_NODE)
        return {"OSC_DIR": str(self.base / "osc"), "OSC_NODE": str(node)}

    def go(self, *, no_bwrap: bool = False, timeout: str = "", version: str = "0.3.6", **knobs) -> tuple[int, dict]:
        extra = self.stub(version, **knobs)
        if timeout:
            extra["PFY_XINTAKE_TIMEOUT"] = timeout
        return self.run_entry("skillcreator", self.env(no_bwrap=no_bwrap, **extra))

    def test_missing_package_exits_2(self) -> None:
        code, r = self.run_entry("skillcreator", self.env(OSC_DIR=str(self.base / "nope")))
        self.assertEqual(code, 2)
        self.assertIn("opencode-skill-creator not found", r["reason"])

    def test_version_mismatch_exits_2(self) -> None:
        code, r = self.go(version="0.3.5")
        self.assertEqual(code, 2)
        self.assertIn("0.3.5", r["reason"])

    def test_old_node_exits_2(self) -> None:
        code, r = self.go(node="16.20.0")
        self.assertEqual(code, 2)
        self.assertIn("Node 18+", r["reason"])

    def test_happy_path_passes(self) -> None:
        code, r = self.go()
        self.assertEqual(code, 0, r)
        self.assertTrue(all(r["checks"].values()), r)

    def test_driver_error_fails(self) -> None:
        self.assert_failed(*self.go(error=True), "driver_report")

    def test_missing_tool_fails(self) -> None:
        self.assert_failed(*self.go(fewer_tools=True), "registers_14_tools")

    def test_unknown_key_accepted_fails(self) -> None:
        self.assert_failed(*self.go(accept_badkey=True), "unknown_key_rejected")

    def test_bad_name_accepted_fails(self) -> None:
        self.assert_failed(*self.go(accept_badname=True), "non_kebab_name_rejected")

    def test_no_bundled_skill_fails(self) -> None:
        self.assert_failed(*self.go(skip_bundle=True), "bundled_skill_lands_in_xdg")

    def test_bundle_into_home_fails(self) -> None:
        code, r = self.go(bundle_to_home=True)
        self.assertEqual(code, 1, r)
        self.assertFalse(r["checks"]["home_untouched"])
        self.assertFalse(r["checks"]["bundled_skill_lands_in_xdg"])

    def test_update_check_file_fails(self) -> None:
        self.assert_failed(*self.go(write_status=True), "auto_update_off_no_status_file")

    def test_package_cache_fails(self) -> None:
        self.assert_failed(*self.go(write_cache=True), "no_package_cache_written")

    def test_fixture_write_fails(self) -> None:
        self.assert_failed(*self.go(mutate_fixture=True), "fixtures_untouched")

    def test_real_home_skill_write_fails_without_bwrap(self) -> None:
        code, r = self.go(no_bwrap=True, plant=self.plant_home(".config/opencode/skills/opencode-skill-creator"))
        self.assertEqual(code, 1)
        self.assert_home_changed(r, ".config/opencode/skills/opencode-skill-creator")

    def test_real_home_cache_write_fails_without_bwrap(self) -> None:
        code, r = self.go(no_bwrap=True, plant=self.plant_home(".cache/opencode/packages/opencode-skill-creator@latest"))
        self.assertEqual(code, 1)
        self.assert_home_changed(r, ".cache/opencode/packages/opencode-skill-creator@latest")

    def test_real_home_status_file_fails_without_bwrap(self) -> None:
        target = self.home / ".config/opencode/opencode-skill-creator-update-check.json"
        plant = (f"import pathlib; p = pathlib.Path({str(target)!r}); p.parent.mkdir(parents=True, exist_ok=True); "
                 "p.write_text('{}')")
        code, r = self.go(no_bwrap=True, plant=plant)
        self.assertEqual(code, 1)
        self.assert_home_changed(r, ".config/opencode/opencode-skill-creator-update-check.json")

    def test_timeout_fails_and_keeps_home_check(self) -> None:
        code, r = self.go(no_bwrap=True, timeout="1", sleep_version=5,
                          plant=self.plant_home(".config/opencode/skills/opencode-skill-creator"))
        self.assertEqual(code, 1)
        self.assertIn("node version timeout after 1s", r["reason"])
        self.assertFalse(r["checks"]["body_completed"])
        self.assert_home_changed(r, ".config/opencode/skills/opencode-skill-creator")


if __name__ == "__main__":
    unittest.main()
