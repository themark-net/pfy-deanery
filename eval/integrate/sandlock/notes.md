# sandlock integrate notes

Wiring: `scripts/integrations/sandlock/wrap.py` around one install or one run. Production binary adapter: `scripts/integrations/sandlock/confine.py`. Fixture: `eval/integrate/sandlock/fixtures/hello.sh`.

The on-main receipt is `eval/integrate/sandlock/receipt.json`. After the wiring SHA is on `origin/main`, the driver runs `eval/integrate/sandlock/run-on-main.sh`, which writes that file in the worktree. The driver does not commit it. This notes file is the receipt `log_path`. It is not a substitute for that receipt.

Timeouts: self-test 30 seconds, command 120 seconds. A start that then times out exits 124 and is not retried unsandboxed. A miss before the starter marker logs `sandlock: unsandboxed` and runs the command once.

Flag: `PFY_SANDLOCK=auto` (default) sandboxes install only. `all` sandboxes install and run. `off` sandboxes neither.

Cache: `PFY_SANDLOCK_CACHE` or `~/.cache/pfy/tools/integrate-sandlock/lane`. The lock and the success receipt stay inside the caller cache. The hash includes the action, the command, and `SANDLOCK_BIN`.
