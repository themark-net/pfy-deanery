# Module: Exo optional lab adapter

**Purpose:** Optional **lab** path. Exec `exo.sh` from `./pfy start exo` when present. Not the default harness. Not a Grok replacement. `default_harness` stays grok. Do not vendor Exo.

Inference via `LOCAL_OPENAI_BASE_URL` from the ADR-0014 detector when ready (`OPENAI_BASE_URL` defaults to that). Do not invent Exo flags. Day-to-day control surface is `./exo.sh`.

## Entry

```bash
./pfy harness use exo    # does not change default_harness
./pfy start exo
```

Detect: `$ROOT/exo.sh` or `$HOME/exo/exo.sh` (executable) or `command -v exo.sh`. Docker on PATH is **not** ready.

Missing script: `STUB harness: exo`, issue #60, installer from `data/harnesses.json` `setup`, exit 2. `./pfy start exo` does not run the installer. No fake ready. Docker on PATH is not ready. `default_harness` stays grok.

```bash
curl -fsSL https://raw.githubusercontent.com/exoharness/exo/main/setup.sh -o setup.sh && bash setup.sh
```

git and Docker are required by upstream setup. `setup.sh` is first-time install only. After that, `./exo.sh`.

Pin: [exoharness/exo](https://github.com/exoharness/exo). Patterns: [exo-self-mod-patterns.md](../ops/exo-self-mod-patterns.md). Operator notes: [bootstrap/exo/README.md](../../bootstrap/exo/README.md).

## Not yet

- Making Exo the default harness
- Vendoring Exo into git
- Invented Exo flags
- Treating Docker-on-PATH as ready
- agent-cage as `./pfy start`
