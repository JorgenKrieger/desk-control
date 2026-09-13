# desk-control

![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Protocol](https://img.shields.io/badge/protocol-reverse--engineered-success)
![License](https://img.shields.io/badge/license-MIT-blue)

A local, self-hosted replacement for the manufacturer's BLE app for a Jingshi
standing desk (advertises as `BLE SPP`) -- no more depending on the original
app just to move a desk. The BLE protocol was reverse-engineered by passively
sniffing the official app's own Bluetooth traffic (no jailbreak, no
debugger, no SIP changes), and a small background service now exposes the
desk over a local HTTP API for use from your own scripts, hotkeys, or
automations.

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

## Quick start

```bash
poetry install

# run the service directly (foreground, for development)
poetry run uvicorn service:app --host 127.0.0.1 --port 8842

# or install it as a background service that starts at login (see launchd/)
./launchd/install.sh
```

Once running:

```bash
curl http://127.0.0.1:8842/status
curl -X POST http://127.0.0.1:8842/stand
curl -X POST http://127.0.0.1:8842/sit
curl -X POST http://127.0.0.1:8842/stop
curl -X POST http://127.0.0.1:8842/move_to -H 'content-type: application/json' -d '{"height_cm": 95}'
```

## API

| Method & path | Description |
|---|---|
| `GET /status` | `{connected, height_cm, is_moving}` |
| `POST /up` | Start moving up |
| `POST /down` | Start moving down |
| `POST /stop` | Stop movement |
| `POST /move_to` | Body: `{"height_cm": number}` -- move to an absolute height |
| `POST /sit` | Move to the stored sit height |
| `POST /stand` | Move to the stored stand height |
| `GET /config` | Current stored config (see below) |
| `POST /config` | Body: `{"sit_height_cm"?, "stand_height_cm"?, "device_id"?}` -- update config |

The service binds to `127.0.0.1` only and is meant to be called by things
running on the same machine (a hotkey tool, a calendar-based automation,
etc.), not exposed to the network.

## Configuration

Sit/stand heights and `device_id` are stored in
`~/Library/Application Support/desk-control/config.json`, editable directly
or via `POST /config`.

`device_id` matters if you have more than one BLE device nearby that
advertises as `"BLE SPP"` -- it's a generic name used by many cheap
serial-over-BLE modules, not unique to this desk, so without it the service
just connects to the first matching name it finds. Set it to disambiguate:
it's the ASCII decoding of the desk's BLE manufacturer data, which appears
tied to the QR/serial identifier on the physical unit (see
[`specs/reverse-engineer.md`](specs/reverse-engineer.md) section 4). Find
yours with a PacketLogger capture -- see [`log/README.md`](log/README.md).

## How it works

```
protocol.py     the confirmed BLE frame codec (checksums, command/telemetry encoding)
controller.py   Desk class: holds the BLE connection, tracks live height, movement + safety watchdog
config.py       local storage for sit/stand preset heights (the desk itself has no preset storage)
service.py      FastAPI app exposing the above over HTTP
launchd/        run service.py as a per-user background service at login
pklg_decode.py  decodes macOS PacketLogger (.pklg) captures, for further protocol investigation
log/            where local captures go (gitignored -- see log/README.md)
specs/          the reverse-engineering investigation log
```

The desk itself needs no pairing/preset storage on its end -- the app-side
`config.json` (under `~/Library/Application Support/desk-control/`) just
remembers your sit/stand heights and sends them as an absolute move-to-height
command, the same way the original app does.

## Requirements

- macOS (uses `bleak`, which uses CoreBluetooth)
- [Poetry](https://python-poetry.org/)
- Python >=3.11
