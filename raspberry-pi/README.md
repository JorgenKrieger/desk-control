# raspberry-pi

The live, primary, always-on deployment -- see [the root README](../README.md)
for the full project story, architecture, and API reference. This is a
per-user `systemd` service on a Raspberry Pi Zero W, bound to `0.0.0.0` so
it's reachable over your home network (unlike `../dev/`, which binds to
`127.0.0.1` only).

See [`specs/port-to-raspberry-pi.md`](specs/port-to-raspberry-pi.md) for
how this port was validated on the real hardware (dependency compatibility,
BLE permissions, etc.) -- worth reading if you're setting this up on
different Pi hardware or a different OS image.

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
```

or with [`../cli/`](../cli/README.md), which already points here by default.

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
