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
[`raspberry-pi/specs/reverse-engineer.md`](raspberry-pi/specs/reverse-engineer.md).

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

- **[`raspberry-pi/`](raspberry-pi/README.md)** -- the whole project: the
  reverse-engineered protocol, the controller, the HTTP service, and the
  `systemd` unit that keeps it always-on over your home network.

## Quick start

Set up [`raspberry-pi/`](raspberry-pi/README.md) on a Pi, then control the
desk with curl or any HTTP client on your network:

```bash
curl http://<pi-address>:8842/status
curl -X POST http://<pi-address>:8842/stand
curl -X POST http://<pi-address>:8842/sit
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
| `GET /config` | Current stored config |
| `POST /config` | Body: `{"sit_height_cm"?, "stand_height_cm"?, "device_id"?}` -- update config |

`device_id` disambiguates your specific desk, since `"BLE SPP"` is a
generic name other devices might also advertise -- find yours with
`raspberry-pi/discover_device.py`.

## Requirements

See [`raspberry-pi/README.md`](raspberry-pi/README.md) for what's needed to
deploy this.
