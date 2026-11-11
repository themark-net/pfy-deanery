# Exo optional lab (exoharness)

Optional **lab** only. Not the default harness. Not a Grok replacement. Do not vendor Exo into this repo. Personal lab-IT — not a commercial cage product.

Pin: [exoharness/exo](https://github.com/exoharness/exo)

## First-time setup (official one-liner, no extra flags)

git and Docker are required. Docker on PATH by itself is **not** ready.

```bash
curl -fsSL https://raw.githubusercontent.com/exoharness/exo/main/setup.sh -o setup.sh
bash setup.sh
```

Day-to-day: `./exo.sh` in the Exo checkout (often `~/exo/` or this repo root if you keep a local copy untracked).

## pfy

```bash
./pfy start exo
```

Detects `$ROOT/exo.sh`, `$HOME/exo/exo.sh`, or `exo.sh` on PATH. If present, execs that script and passes `LOCAL_OPENAI_BASE_URL` / `OPENAI_BASE_URL` when the local detector is ready. No invented Exo flags.

If missing: `STUB harness: exo`, [issue #60](https://github.com/themark-net/pfy-deanery/issues/60), the setup one-liner above, exit 2.

`./pfy harness use exo` does **not** change `default_harness` (stays grok).

## Patterns

See [docs/ops/exo-self-mod-patterns.md](../../docs/ops/exo-self-mod-patterns.md).
