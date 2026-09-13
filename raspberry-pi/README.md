# desk-control (Raspberry Pi)

![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-c51a4a)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Protocol](https://img.shields.io/badge/protocol-reverse--engineered-success)
![License](https://img.shields.io/badge/license-MIT-blue)

This is the **primary, always-on** deployment of desk-control -- a local,
self-hosted replacement for the manufacturer's BLE app for a Jingshi
standing desk (advertises as `BLE SPP`). It runs as a per-user `systemd`
service on a Raspberry Pi Zero W, reachable over your home network, so
control doesn't depend on a laptop being awake. See
[`../dev/README.md`](../dev/README.md) for the original reverse-engineering
story and protocol details, and
[`specs/port-to-raspberry-pi.md`](specs/port-to-raspberry-pi.md) for how
this port was validated on the real hardware.

## Status

Live and working: BLE connect, live height, up/down/stop, and move-to
(sit/stand presets) all confirmed end-to-end on the actual Pi Zero W, as a
regular non-root user, reachable over the LAN. The Mac's own service has
been retired in favor of this one -- see `../dev/README.md`.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**1. Find your desk's `device_id`** (needed since `"BLE SPP"` is a generic
name other devices might also advertise):

```bash
.venv/bin/python3 discover_device.py
```

Note the printed `device_id`.

**2. Start the service** for now, to set config:

```bash
.venv/bin/uvicorn service:app --host 0.0.0.0 --port 8842
```

**3. Set your config** (device_id from step 1, your actual sit/stand
heights) from another terminal:

```bash
curl -X POST http://localhost:8842/config -H 'content-type: application/json' \
  -d '{"device_id": "<from step 1>", "sit_height_cm": 70, "stand_height_cm": 110}'
```

Stop the foreground service (Ctrl-C), then **install it as a real
always-on service**:

```bash
cd systemd && ./install.sh
```

This starts it now, at every boot, restarts it if it crashes, and enables
lingering so it keeps running independent of any SSH login. See
[`systemd/README.md`](systemd/README.md).

## Using it

From any device on your network:

```bash
curl http://<pi-address>:8842/status
curl -X POST http://<pi-address>:8842/stand
```

Or use the CLI (in `../cli/`, works from any machine, not just the Mac) --
already points at the Pi by default. See [`../cli/README.md`](../cli/README.md).

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

**Note on network exposure:** this binds to `0.0.0.0`, deliberately --
unlike the Mac version, the whole point of the Pi is to be reachable from
other devices on your home network. That means anything on your network can
move the desk. Judged an acceptable tradeoff for a private network with no
guest access; revisit (a shared-secret header, or firewalling to specific
device IPs) if that assumption ever stops holding. See `service.py`'s
docstring and `specs/port-to-raspberry-pi.md` section 3.3.

## Configuration

Sit/stand heights and `device_id` are stored in
`~/.config/desk-control/config.json`, editable directly or via
`POST /config`.

`device_id` is the ASCII decoding of the desk's BLE manufacturer data,
which appears tied to the QR/serial identifier on the physical unit (see
`../dev/specs/reverse-engineer.md` section 4). Find yours with
`discover_device.py`.

## How it works

```
protocol.py     the confirmed BLE frame codec (checksums, command/telemetry encoding)
controller.py   Desk class: holds the BLE connection, tracks live height, movement + safety watchdog
config.py       local storage for sit/stand preset heights (the desk itself has no preset storage)
service.py      FastAPI app exposing the above over HTTP, bound to 0.0.0.0
discover_device.py  one-time setup helper: finds your desk's device_id
systemd/        run service.py as a per-user systemd service at boot
specs/          the reverse-engineering log (copied from dev/) and the Pi port plan
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
