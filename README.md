# desk-control

![Protocol](https://img.shields.io/badge/protocol-reverse--engineered-success)
![License](https://img.shields.io/badge/license-MIT-blue)

A local, self-hosted replacement for the manufacturer's BLE app for a
Jingshi standing desk (advertises as `BLE SPP`) -- no more depending on the
original app just to move a desk.

The desk's BLE protocol was fully reverse-engineered by passively sniffing
the official app's own Bluetooth traffic -- no jailbreak, no debugger, no
modified security settings. That protocol now runs behind a small HTTP API
on an always-on Raspberry Pi, controllable via curl or your own automations
(Hammerspoon hotkeys, calendar-based standing reminders, Home Assistant,
etc.).

## Status

Live and working: BLE connect, live height tracking, up/down/stop, and
moving to an absolute height (which is how sit/stand presets work), all
confirmed end-to-end on real hardware. Not yet reverse-engineered:
lock/unlock, and decoding error/status packets. Full investigation log:
[`specs/reverse-engineer.md`](specs/reverse-engineer.md).

## Safety

This controls a physical motorized desk. The desk has **no built-in
movement timeout** -- a single "move" command runs until an explicit stop
is sent, so this project's own service enforces a stop after 20 seconds as
a safety net. If you're extending this project: verify any new command via
passive observation first, and test physical movement only while watching
the desk with the physical/manual controller within reach.

## Architecture

```
                    HTTP (port 8842)
  curl, Hammerspoon,  ───────────────────►  systemd service on a Pi  ───BLE───►  desk
  Home Assistant, ...                        (always-on, home network)
```

A per-user `systemd` service on a Raspberry Pi Zero W, bound to `0.0.0.0` so
it's reachable over your home network.

See [`specs/port-to-raspberry-pi.md`](specs/port-to-raspberry-pi.md) for
how this was validated on the real hardware (dependency compatibility, BLE
permissions, etc.) -- worth reading if you're setting this up on different
Pi hardware or a different OS image.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**1. Find your desk's `device_id`:**

```bash
.venv/bin/python3 discover_device.py
```

**2. Start the service** temporarily, to set config:

```bash
.venv/bin/uvicorn service:app --host 0.0.0.0 --port 8842
```

**3. Set your config** (device_id from step 1, your actual sit/stand
heights) from another terminal:

```bash
curl -X POST http://localhost:8842/config -H 'content-type: application/json' \
  -d '{"device_id": "<from step 1>", "sit_height_cm": 70, "stand_height_cm": 110}'
```

**4. Stop the foreground service** (Ctrl-C), then install it as a real
always-on service:

```bash
cd systemd && ./install.sh
```

This starts it now, at every boot, restarts it if it crashes, and enables
lingering so it keeps running independent of any SSH login. See
[`systemd/README.md`](systemd/README.md).

## Using it

```bash
curl http://<pi-address>:8842/status
curl -X POST http://<pi-address>:8842/stand
curl -X POST http://<pi-address>:8842/sit
```

or with any HTTP client, Hammerspoon hotkey, Home Assistant integration, etc.

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
| `GET /config` | Current stored config |
| `POST /config` | Body: `{"sit_height_cm"?, "stand_height_cm"?, "device_id"?}` -- update config |

`device_id` disambiguates your specific desk, since `"BLE SPP"` is a
generic name other devices might also advertise -- find yours with
`discover_device.py`.

## Network exposure

Binding to `0.0.0.0` is deliberate -- the whole point of the Pi is to be
reachable from other devices on your home network. That means anything on
your network can move the desk (no authentication). Judged an acceptable
tradeoff for a private network with no guest access; revisit (a
shared-secret header, or firewalling to specific device IPs) if that
assumption ever stops holding. See `service.py`'s docstring and
`specs/port-to-raspberry-pi.md` section 3.3.

## Configuration

Stored in `~/.config/desk-control/config.json` on the Pi, editable directly
or via `POST /config`.

## How it works

```
protocol.py     the confirmed BLE frame codec (checksums, command/telemetry encoding)
controller.py   Desk class: holds the BLE connection, tracks live height, movement + safety watchdog
config.py       local storage for sit/stand preset heights (the desk itself has no preset storage)
service.py      FastAPI app exposing the above over HTTP, bound to 0.0.0.0
discover_device.py  one-time setup helper: finds your desk's device_id
systemd/        run service.py as a per-user systemd service at boot
specs/          the reverse-engineering log and the Pi port plan
```

## Requirements

- A Raspberry Pi running a reasonably recent OS (validated on a Zero W
  running Raspbian 13/trixie, Python 3.13, glibc 2.41 -- see
  `specs/port-to-raspberry-pi.md` section 7 for why the OS recency matters
  on older Pi hardware)
- `python3-dev` (`sudo apt-get install -y python3-dev`) -- needed to
  compile `bleak`'s Linux BLE backend (`dbus-fast`) on first install; only
  happens once, the built wheel is cached afterward
- Python >=3.11
