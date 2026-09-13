# dev

The original implementation, the reverse-engineering history, and the
local development/test environment -- see [the root README](../README.md)
for the full project story, architecture, and API reference. **Not the
live deployment** -- that's [`../raspberry-pi/`](../raspberry-pi/README.md).
The CLI lives at [`../cli/`](../cli/README.md) (not Mac-specific).

Use this directory to develop/test protocol or controller changes locally
on a Mac -- faster than iterating against the Pi over SSH, and this is
where PacketLogger captures happen if more of the desk's protocol ever
needs reverse-engineering (lock/unlock, error codes). Running its service
is optional and only for that purpose; only one of `dev/` and
`raspberry-pi/` can hold the desk's BLE connection at a time.

The full investigation log is [`specs/reverse-engineer.md`](specs/reverse-engineer.md)
-- read this before doing any further protocol work; don't re-derive
what's already confirmed there.

## Safety

Same as the root README: verify any new command via passive observation
first, and test physical movement only while watching the desk with the
physical/manual controller within reach.

## Running the service locally

```bash
poetry install
git config core.hooksPath .githooks  # optional: enables the gitleaks pre-commit hook, see ../.githooks/README.md
poetry run python discover_device.py  # find your desk's device_id
poetry run uvicorn service:app --host 127.0.0.1 --port 8842
```

Then, from another terminal, set your config:

```bash
curl -X POST http://127.0.0.1:8842/config -H 'content-type: application/json' \
  -d '{"device_id": "<from discover_device.py>", "sit_height_cm": 70, "stand_height_cm": 110}'
```

Point the CLI at it instead of the Pi for testing:

```bash
DESK_CONTROL_URL=http://127.0.0.1:8842 ../cli/desk status
```

Binds to `127.0.0.1` only (unlike the Pi, this was never meant to be
reachable from other devices).

## Configuration

Stored in `~/Library/Application Support/desk-control/config.json`,
editable directly or via `POST /config`. `device_id` is the ASCII decoding
of the desk's BLE manufacturer data (see `specs/reverse-engineer.md`
section 4) -- find yours with `discover_device.py`. If you need to dig
deeper with a full PacketLogger capture, see [`log/README.md`](log/README.md).

## How it works

```
protocol.py     the confirmed BLE frame codec (checksums, command/telemetry encoding)
controller.py   Desk class: holds the BLE connection, tracks live height, movement + safety watchdog
config.py       local storage for sit/stand preset heights (the desk itself has no preset storage)
service.py      FastAPI app exposing the above over HTTP, for local testing
discover_device.py  one-time setup helper: finds your desk's device_id
pklg_decode.py  decodes macOS PacketLogger (.pklg) captures, for further protocol investigation
log/            where local captures go (gitignored -- see log/README.md)
specs/          the reverse-engineering investigation log
```

## Requirements

- macOS (uses `bleak`, which uses CoreBluetooth)
- [Poetry](https://python-poetry.org/)
- Python >=3.11
