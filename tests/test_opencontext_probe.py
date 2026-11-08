"""OpenContext probe: key-error search stays skipped, empty files stay misses.

The child is eval/evq1107/opencontext/probe.py. Each test runs that script
against stub oc and rg binaries in a temp dir. No network, no model, no real
oc binary.
"""

from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "opencontext" / "probe.py"
RESULTS = ROOT / "eval" / "evq1107" / "opencontext" / "results.json"

OC_STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path
    args = sys.argv[1:]
    contexts = Path(os.environ["OPENCONTEXT_CONTEXTS_ROOT"])
    meta_path = Path(os.environ["OPENCONTEXT_ROOT"]) / "meta.json"

    def load():
        if not meta_path.is_file():
            return []
        return json.loads(meta_path.read_text(encoding="utf-8"))

    def save(rows):
        meta_path.write_text(json.dumps(rows), encoding="utf-8")

    if args[:2] == ["folder", "create"]:
        (contexts / args[2]).mkdir(parents=True, exist_ok=True)
        sys.stdout.write('Folder ready at "%s".\\n' % args[2])
        raise SystemExit(0)
    if args[:2] == ["doc", "create"]:
        folder, name = args[2], args[3]
        desc = args[args.index("-d") + 1] if "-d" in args else ""
        dest = contexts / folder / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("", encoding="utf-8")
        rows = load()
        rows.append({
            "doc_name": name,
            "rel_path": "%s/%s" % (folder, name),
            "abs_path": str(dest),
            "description": desc,
        })
        save(rows)
        sys.stdout.write('Created doc "%s/%s".\\n' % (folder, name))
        raise SystemExit(0)
    if args[:2] == ["context", "manifest"]:
        sys.stdout.write(json.dumps(load()))
        raise SystemExit(0)
    if args[:1] == ["search"]:
        # Token on stdout must not turn a key error into a hit.
        sys.stdout.write(json.dumps([{"text": args[1]}]))
        sys.stderr.write(
            "Error: API key not configured. Set OPENAI_API_KEY "
            "or configure in ~/.opencontext/config.toml\\n"
        )
        raise SystemExit(1)
    sys.stderr.write("unexpected %s\\n" % args)
    raise SystemExit(2)
    """
)

RG_STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import sys
    needle = sys.argv[-1]
    if needle.startswith("OC1107_NOVEL_"):
        raise SystemExit(1)
    sys.stdout.write("docs/example.md\\n")
    raise SystemExit(0)
    """
)


class OpenContextProbeTests(unittest.TestCase):
    def _run(self, tmp: Path) -> dict:
        home = tmp / "home"
        scratch = tmp / "tmp"
        store = tmp / "store"
        out = tmp / "out.json"
        for path in (home, scratch):
            path.mkdir()
        oc = tmp / "oc"
        rg = tmp / "rg"
        oc.write_text(OC_STUB, encoding="utf-8")
        rg.write_text(RG_STUB, encoding="utf-8")
        oc.chmod(oc.stat().st_mode | stat.S_IEXEC)
        rg.chmod(rg.stat().st_mode | stat.S_IEXEC)
        before = RESULTS.read_bytes()
        proc = subprocess.run(
            [
                sys.executable,
                str(PROBE),
                "--out",
                str(out),
                "--oc-bin",
                str(oc),
                "--rg-bin",
                str(rg),
                "--store",
                str(store),
                "--home",
                str(home),
                "--tmp",
                str(scratch),
                "--skip-pins",
                "--skip-home",
            ],
            cwd=ROOT,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertEqual(RESULTS.read_bytes(), before)
        self.assertTrue(out.is_file(), proc.stdout)
        return json.loads(out.read_text(encoding="utf-8"))

    def test_key_error_stays_skipped_and_manifest_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="oc-search-") as raw:
            doc = self._run(Path(raw))
        search = doc["search_keyword"]
        self.assertEqual(search["exit"], 1)
        self.assertTrue(search["stdout_has_novel"])
        self.assertTrue(search["skipped_api_key"])
        self.assertEqual(doc["h1_graded_cases"], 0)
        manifest = doc["manifest_after_create"]
        self.assertEqual(manifest["exit"], 0)
        self.assertTrue(manifest["parse_ok"])
        self.assertEqual(manifest["doc_count"], 8)
        self.assertEqual(manifest["novel_hits"], 8)
        self.assertEqual(manifest["repo_hits"], 0)
        self.assertEqual(doc["manifest_second"]["novel_hits"], 8)

    def test_empty_doc_is_a_miss_and_body_write_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="oc-body-") as raw:
            doc = self._run(Path(raw))
        self.assertEqual(doc["doc_create_ok"], 8)
        self.assertEqual(doc["file_walk_before_body_novel"], 0)
        self.assertEqual(doc["file_walk_before_body_repo"], 0)
        self.assertEqual(doc["bodies_written"], 8)
        self.assertEqual(doc["file_walk_after_body_novel"], 8)
        self.assertEqual(doc["file_walk_after_body_repo"], 0)
        self.assertEqual(doc["second_process_exit"], 0)
        self.assertEqual(doc["second_process_novel"], 8)
        self.assertEqual(doc["second_process_repo"], 0)
        self.assertEqual(doc["novel_walk_agreement"], 8)
        self.assertEqual(doc["repo_novel_hits"], 0)
        self.assertEqual(doc["repo_known_hits"], 8)


if __name__ == "__main__":
    unittest.main()
