# Bumblebee ev1107

Verdict: PROMOTE I2. v0.1.2 exact-matches a known-bad lockfile entry and does not echo the fixture token. It does not flag an npx git selector or a plaintext env value. `scripts/pfy_mcp_scan.py` is the advisory install check for those two MCP signals. The check is not on the pipeline, so this lane does not call it I3.

## Pin

`command -v go` was empty, so this lane did not build from source. Host is linux x86_64. Install path: `~/.cache/pfy/tools/bumblebee/`.

```bash
mkdir -p ~/.cache/pfy/tools/bumblebee
cd ~/.cache/pfy/tools/bumblebee
curl -fsSL -o checksums.txt https://github.com/perplexityai/bumblebee/releases/download/v0.1.2/checksums.txt
curl -fsSL -o bumblebee_0.1.2_linux_amd64.tar.gz https://github.com/perplexityai/bumblebee/releases/download/v0.1.2/bumblebee_0.1.2_linux_amd64.tar.gz
sha256sum -c checksums.txt --ignore-missing
tar -xzf bumblebee_0.1.2_linux_amd64.tar.gz
./bumblebee version
sha256sum ./bumblebee bumblebee_0.1.2_linux_amd64.tar.gz
```

`checksums.txt` line for the linux amd64 tarball:

`53b080cf3ddb692b0c4e5492ef4785b4c54daf1624fcd0fcba3958116a0be8d9  bumblebee_0.1.2_linux_amd64.tar.gz`

`sha256sum -c` printed `OK`.

Binary sha256: `3b46f98ab8fa6345a5d39c7483ff37c51b2ee7699aabe51f2a54133f357f6c7a`

Binary size: 6738104 bytes. ELF x86-64, statically linked, stripped.

`bumblebee version`:

```text
bumblebee v0.1.2
commit: cc57710eeaf685e7b89924a36c8583cad0a378fe
built:  2026-06-18T15:03:13Z
go:     go1.25.11
```

`bumblebee selftest` printed `selftest OK (5 findings in 2ms)` and, on a rerun, `5 findings in 3ms`. `/usr/bin/time` wall was 0.00s both times. The embedded fixtures use a fake package name. No network.

## What was scanned

Two roots only. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `TMPDIR` for the direct binary runs pointed at `~/.cache/pfy/tools/bumblebee/iso-home` and `~/.cache/pfy/tools/bumblebee/tmp`. Profile was `deep` with an explicit `--root`. Baseline was not used: `bumblebee roots --profile baseline` on that empty home still listed `/usr/lib/python3` and `/usr/local/lib`, which are outside the two roots.

Worktree, with `--exclude tmp` so the fixture was not part of this count:

```bash
bumblebee scan --profile deep --root "$WT" --exclude tmp \
  --exposure-catalog ~/.cache/pfy/tools/bumblebee/threat_intel \
  --output file --output-file "$WT/tmp/bumblebee-scan/worktree.ndjson"
```

2427 files considered, 0 package records, 0 findings, scanner duration 11ms, wall 0.02s. This repo has `gui/operator/package.json` and `harness/write-guard-mcp/pyproject.toml` and no lockfile, `go.sum`, or MCP JSON. Those two manifests were not inventoried.

Fixture home: `tmp/bumblebee-fixture-home/` (gitignored). Three MCP files and two lockfiles.

| File | Contents |
|------|----------|
| `.cursor/mcp.json` | local `node ./server.js`, no env |
| `.codeium/windsurf/mcp_config.json` | `npx -y` plus a `github:` selector |
| `.config/Claude/claude_desktop_config.json` | `npx -y @example/mcp-server` and env key `API_TOKEN` set to the ticket placeholder |
| `bad-app/package-lock.json` | `node-ipc` 10.1.1 (catalog hit) and `left-pad` 1.3.0 |
| `clean-app/package-lock.json` | `node-ipc` 9.0.0 (not in the catalog versions) |

```bash
bumblebee scan --profile deep --root "$WT/tmp/bumblebee-fixture-home" \
  --exposure-catalog ~/.cache/pfy/tools/bumblebee/threat_intel/node-ipc-credential-stealer.json \
  --output file --output-file "$WT/tmp/bumblebee-scan/fixture.ndjson"
```

6 files considered, 6 package records, 1 finding, scanner duration 868us, wall 0.00s.

The finding is `node-ipc` 10.1.1, severity critical, catalog id `socket-2026-05-14-npm-node-ipc-credential-stealer`, evidence `exact name+version match (version=10.1.1)`, source `bad-app/package-lock.json`. `node-ipc` 9.0.0 and `left-pad` 1.3.0 were inventoried and were not findings.

MCP records, all confidence low:

| Server | package_name recorded | Finding |
|--------|----------------------|---------|
| `local-notes` | `local-notes` (the server id, not `node`) | no |
| `git-tool` | `git-tool` (the server id). The record has no `requested_spec` field, so the `github:` selector is gone | no |
| `paid-tool` | `@example/mcp-server` | no |

The placeholder string and the key `API_TOKEN` were absent from the fixture NDJSON, stdout, and stderr. Bumblebee does not flag the token because it does not emit env values. That is the right leak behavior and a miss for an install check.

A separate one-file root with only `package.json` depending on `node-ipc` 10.1.1: 1 file considered, 0 package records, 0 findings, 164us. v0.1.2 reads the lockfile, not the bare manifest.

## Wrapper

`scripts/pfy_mcp_scan.py` refuses `$HOME` and the home config tops (`.grok`, `.claude`, `.codex`, `.config`, `.local`) before it starts the scanner. It skips symlink files and symlink directories. It flags a git selector and a secret-like env key without printing the selector or the value. It treats a Bumblebee `record_type=finding` as a package advisory. Exit 0 / 1 / 2. Lookup is `PFY_BUMBLEBEE_BIN`, then `PATH`, then `~/.cache/pfy/tools/bumblebee/bumblebee`. A set but missing `PFY_BUMBLEBEE_BIN` does not fall through. Operator notes: `docs/ops/bumblebee-mcp-scan.md`.

Measured with the real binary:

| Command | Exit | Wall | Result |
|---------|------|------|--------|
| `--root "$HOME"` | 2 | 0.07s | refused, scanner not started |
| `--root` fixture, node-ipc catalog | 1 | 0.07s | 3 advisories: git-selector `git-tool`, package `node-ipc` 10.1.1, plaintext-env key `API_TOKEN` |
| `--root` worktree, full `threat_intel` catalog, fixture moved aside | 0 | 0.15s | CLEAN, 0 findings |

The placeholder was not in `eval/ev1107/bumblebee/fixture-receipt.json`. Receipts: `fixture-receipt.json`, `worktree-receipt.json`. Counts: `scan-summary.json`.

## Tests

`python3 -m unittest tests.test_pfy_mcp_scan` (6 tests, stubs only, no network, no real binary). Each test is a fail path and a recovery path.

The tests failed before `scripts/pfy_mcp_scan.py` existed (6 failures, the interpreter could not open the file).

Redaction mutant: `redact()` returned its input unchanged. `test_scanner_leak_is_redacted_and_finding_exits_1` then failed because stdout contained the placeholder inside `source=bad-app/<placeholder>/package-lock.json`. The function was restored. The test passes again. The mutant is not committed.

`python3 scripts/catalog_check.py` PASS. `python3 scripts/check_no_encoded_payloads.py` PASS.

## Comparison

| Question | write-guard-mcp (I3) | destructive-command-guard (I1) | SkillSpector (I3) | Bumblebee v0.1.2 | this wrapper |
|----------|----------------------|--------------------------------|-------------------|------------------|--------------|
| Sees a lockfile version and matches a catalog | no | no | no | yes, exact name and version | yes, via the binary |
| Sees an MCP command line | no | no | no | inventory only; git selectors collapsed to the server id | flags git selectors |
| Sees a plaintext env token | no, unless a write path matches a secret glob | no | no | no, and it does not echo the value | names the key, hides the value |
| Mediates a write or blocks a shell command | yes (audit / enforce) | yes (shell) | no | no | no |
| Skill directory static scan | no | no | yes | no | no |

write-guard remains the write gate. Bumblebee does not replace it. The non-goal stays.

False positives on this run: none. `node-ipc` 9.0.0, `left-pad` 1.3.0, `local-notes`, and `NODE_ENV=production` were not flagged. The worktree scan was a true negative, and it was also a blind scan: there is no lockfile here to be right about.

False negatives: the git selector, the env token, and a bare `package.json`. Non-JSON MCP configs are out of scope for v0.1.2.

## Gates

Value (3 of 4 required for I3):

1. Gap fill: yes. None of the three neighbors inventory lockfiles or MCP launch lines.
2. Operator leverage: yes, as a same-day advisory command. Not as a default make target.
3. Evidence: yes. Selftest, fixture, worktree, and the stub tests.
4. Blast radius: yes. Apache-2.0, one 6738104 byte static binary, read-only, no weights, no network on the scan.

4 of 4. Modularity (all 4 required):

1. Local code needed: yes. The README says env values are not emitted. The run showed a `github:` npx arg produces a record with no `requested_spec` field and no finding.
2. Bounded surface: yes. `scan`, `roots`, `selftest`, `version`.
3. Isolatable: yes. Cache path, not the product runtime.
4. Reversible: yes. Delete `~/.cache/pfy/tools/bumblebee/`. The pin and the entry remain.

I3 is not the verdict. "Integrated" needs an operator path that this lane must not wire (no pregate, CI, or make target). The lane's I3 bar also asks for `self_pipeline` evidence that the tool is used on this repo's pipeline. One eval scan is not that. `catalog_check.py` does not classify this card as CI, testing, or review, so a missing `self_pipeline` field is allowed. Marking `applied` for a one-shot would be a fake pass.

I2 is the ad-hoc probe. The binary stays in the cache. Potential stays medium: the supply-chain match is real, and the MCP install check is only real with the wrapper, and only for JSON hosts. `tier_ceiling` stays I1 because that is the A-tier formula cap. The ceiling is not the stage.

`catalog_stage_eval.py --apply` does not rewrite `integration_stage`. It does rewrite `uses`, `features`, and `next_gate` from `data/catalog_stage_handoff.json`. This lane does not edit that shared file.

## Risks

| How it fails | How we recover |
|--------------|----------------|
| The scanner copies a config value into a field the wrapper keeps | Redact secret-like env values before stdout and the receipt. The leak test fails if redaction is removed. |
| Someone passes `$HOME` or `~/.grok` | Exit 2 before the binary starts. |
| A fixture symlink points at a real config | Skip symlink files and symlink directories. |
| Bumblebee returns clean on an npx git server | The wrapper still exits 1 and names the server and the file. It does not print the selector. |
| The binary is missing | Exit 2 with a next step. Local MCP advisories are still printed, so the git selector is not dropped. |
| Exact version match misses a nearby bad release | `node-ipc` 9.0.0 was present and correctly not flagged. Do not read a clean scan as "this name is safe at every version." |
| The dependency is only in `package.json` or `pyproject.toml` | Measured miss. The check applies to lockfiles and installed metadata. |
| An env key merely contains `token` or `secret` | Advisory only. The key is named, the value stays hidden, and nothing in this lane blocks. |
| A later `--apply` restores the old handoff sentence on the card | `integration_stage` stays. The verdict and this report stay. A single-threaded catalog pass can update the handoff row. |

## Next gate

A separate ticket, after a grill, can add a cage smoke that runs `scripts/pfy_mcp_scan.py` on a fixture. That is the point where `self_pipeline` can say `applied`. Do not add the script to pregate or CI from this result.

## How this tool would run in the pipeline

1. Trigger: an operator, or a future cage smoke, runs the wrapper on an explicit worktree or fixture before trusting a new MCP server or a lockfile. Not a commit hook.
2. It reads that root and an optional exposure catalog. It writes the `--out` receipt. It does not call a hosted model and it does not use the network. The child home is a scratch directory.
3. Exit 0 starts nothing. Exit 1 waits for a person to read the receipt. Exit 2 stops the check and prints the next step.
4. A person re-enters on exit 1 or exit 2. Wiring a gate comes back to Mark as a separate ticket.
5. Two runs do not share a state file. The scanner is read-only. The caller picks the receipt path. No model lock.
