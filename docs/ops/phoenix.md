# Phoenix trace sink (loopback)

Arize Phoenix 21.0.0 is the local trace store for lane spans. One process serves the UI, OTLP/HTTP (`/v1/traces`), and GraphQL (`/graphql`) on `PHOENIX_PORT`, and OTLP gRPC on `PHOENIX_GRPC_PORT`. Deanery does not reimplement the store. A later lane-graph view reads this process.

The PyPI pin is `config/phoenix/version.txt` (one line). `scripts/phoenix_service.sh` `install` and `unit` read that file. Default pin: arize-phoenix 21.0.0.

## Ports and data

| What | Where |
|------|--------|
| UI, OTLP/HTTP, GraphQL | `127.0.0.1:6006` (`PFY_PHOENIX_PORT`) |
| OTLP gRPC | `127.0.0.1:4317` (`PFY_PHOENIX_GRPC_PORT`). gRPC uses `PHOENIX_HOST` too. |
| SQLite and working files | `$PFY_STATE_DIR/phoenix` or `~/.pfy-mentat/phoenix` (`phoenix.db`) |
| venv | `${PFY_TOOL_CACHE:-$HOME/.cache/pfy}/tools/phoenix/venv` |
| Process home | `.../tools/phoenix/home` (not the operator home) |

Retention defaults to 30 days (`PFY_PHOENIX_RETENTION_DAYS`). The upstream default is unlimited.

## Operator commands

The operator runs `enable` and `disable`. An agent session must not start or stop the unit.

```bash
scripts/phoenix_service.sh install   # uv venv + pinned package; prints the version
scripts/phoenix_service.sh unit      # print the user unit; writes nothing
scripts/phoenix_service.sh enable    # write ~/.config/systemd/user/pfy-phoenix.service, enable --now
scripts/phoenix_service.sh status    # up/down and the pinned version
scripts/phoenix_service.sh url
scripts/phoenix_service.sh disable   # stop, disable, delete the unit file only
```

`enable` creates the state directory and the process home. `disable` does not delete traces.

`unit` sets `PHOENIX_TELEMETRY_ENABLED=false`, turns off the built-in assistant, bash, web, and GitHub tools, and sets `PHOENIX_ENABLE_MCP_SERVER=false` (the server accepts `false`). It sets `NoNewPrivileges=yes`. It does not set `PrivateTmp` or `IPAddressAllow`/`IPAddressDeny`: those need a user namespace or BPF, which this user manager is not granted. Authentication variables are left unset. Phoenix keeps authentication off for a loopback host.

## View from another machine

The UI is only on loopback. From a laptop:

```bash
ssh -N -L 6006:127.0.0.1:6006 <nimo-host>
```

Then open `http://127.0.0.1:6006/`. If `PFY_PHOENIX_PORT` is not 6006, use that port on both sides of `-L`. `scripts/phoenix_service.sh url` prints the pair.

## Why loopback only

`PFY_PHOENIX_HOST` exists so a bad host can be refused in a test. `unit` and `enable` exit 2 for anything other than `127.0.0.1`, `::1`, or `localhost`, and they print no unit. A non-loopback host is where Phoenix turns authentication on, and it would expose traces. This sink does not take privilege and does not control the host.

## License

Phoenix is Elastic License 2.0 (ELv2). Internal self-hosting is allowed, including commercial and research use inside our own pipeline. We cannot offer Phoenix as a managed service. It is not copyleft.

## Remove

1. `scripts/phoenix_service.sh disable` (operator).
2. Delete `${PFY_TOOL_CACHE:-$HOME/.cache/pfy}/tools/phoenix` if you also want the venv gone.
3. Delete `$PFY_STATE_DIR/phoenix` (or `~/.pfy-mentat/phoenix`) only when you want the traces gone. `disable` leaves that directory.

Catalog: [sources/entries/180-arize-phoenix.md](../../sources/entries/180-arize-phoenix.md). The heavier alternative we did not install is [sources/entries/181-langfuse.md](../../sources/entries/181-langfuse.md).
