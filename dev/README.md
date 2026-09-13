# desk-control (dev / reverse-engineering)

![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Protocol](https://img.shields.io/badge/protocol-reverse--engineered-success)
![License](https://img.shields.io/badge/license-MIT-blue)

The original implementation, the reverse-engineering history, and the local
development/test environment for this project. **Not the live deployment**
-- that's [`../raspberry-pi/`](../raspberry-pi/README.md), an always-on Pi
reachable over the home network. The `desk` CLI lives at
[`../cli/`](../cli/README.md) now (not Mac-specific, works from anywhere).

Use this directory to develop/test protocol or controller changes locally
on a Mac -- faster than iterating against the Pi over SSH, and this is
where PacketLogger captures happen if more of the desk's protocol ever
needs reverse-engineering (lock/unlock, error codes -- see Status below).
Running its service is optional and only for that purpose; only one of
`dev/` and `raspberry-pi/` can hold the desk's BLE connection at a time.

## Status

The core protocol is fully reverse-engineered and implemented: live height,
up/down movement, stop, and moving to an absolute height (which is how
sit/stand presets work). See [`specs/reverse-engineer.md`](specs/reverse-engineer.md)
for the full investigation log and confirmed frame formats.

Not yet reverse-engineered: lock/unlock, and decoding error/status packets.

## Safety

This controls a physical motorized desk. The desk has **no built-in movement
timeout** -- a single "move" command runs until an explicit stop is sent, so
this project's own service enforces a stop after 20 seconds as a safety net
(see `controller.py`). If you're extending this project: verify any new
command via passive observation first, and test physical movement only while
watching the desk with the physical/manual controller within reach.

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

## API

Same API as `../raspberry-pi/`'s service -- see
[`../cli/README.md`](../cli/README.md) or `service.py` here directly.
Binds to `127.0.0.1` only (unlike the Pi, this was never meant to be
reachable from other devices).

## Configuration

Sit/stand heights and `device_id` are stored in
`~/Library/Application Support/desk-control/config.json`, editable directly
or via `POST /config`.

`device_id` matters because `"BLE SPP"` is a generic name used by many cheap
serial-over-BLE modules, not unique to this desk -- without it, the service
just connects to the first device it finds advertising that name, which
might not be your desk. Find yours with `poetry run python discover_device.py`.
It's the ASCII decoding of the desk's BLE manufacturer data, which appears
tied to the QR/serial identifier on the physical unit (see
[`specs/reverse-engineer.md`](specs/reverse-engineer.md) section 4). If you
ever need to dig deeper with a full PacketLogger capture, see
[`log/README.md`](log/README.md).

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
