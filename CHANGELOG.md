# Changelog

All notable changes to the Deanery product surface are recorded here. The
version is `[project] version` in `pyproject.toml`. There are no earlier
git tags; 0.5.0 is the first numbered entry.

## 0.5.0 - 2026-11-17

See [docs/release-notes/v0.5.0.md](docs/release-notes/v0.5.0.md) for the
user-facing note. Items below are taken from the git log and issue comments.

### Added

- `pfy launch` dry-run paths for Claude Code, llama.cpp, Grok, and Cursor
  subscription, plus a TTY picker and `--` passthrough.
- Hermes and Gemini adapters with setup round-trips.
- Cursor MCP/skills setup, doctor, and uninstall.
- A shared apply ledger used by both the CLI apply path and the Loop
  "Launch session" path.
- `pfy --version` and a read-only `pfy update --check`.
- `pfy catalog validate` rejection of secret-looking `args` and `env`
  values.

### Changed

- `install.sh` defaults to the `main` branch, with optional `PFY_REF` to
  pin a branch, tag, or SHA. Once the `v0.5.0` tag exists, pin this
  release with `PFY_REF=v0.5.0`. The default stays `main`.
- Ollama pulls over 25 GB are refused unless the operator opts in.
- The parked-lane cost gate skips unattended Grok calls unless a cost yes
  has been shown.
- CORPUS / #309 and #305 follow-ups landed on main (public TODO cleanup,
  corpus sloptrim, Entry 148 hook removal, and related tests).

### Known limits

- `pfy launch` live exec is not in this release (pfy-mentat #53 smoke at
  6:02 PM PT on 2026-11-17 exited 3; the model was never loaded).
- Laguna (#25) and Colibri (#24) are untested on this release (weights
  not already pulled; no pulls).
