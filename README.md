# desk-control

![Protocol](https://img.shields.io/badge/protocol-reverse--engineered-success)
![License](https://img.shields.io/badge/license-MIT-blue)

A local, self-hosted replacement for the manufacturer's BLE app for a
Jingshi standing desk (advertises as `BLE SPP`) -- no more depending on the
original app just to move a desk.

The desk's BLE protocol was fully reverse-engineered by passively sniffing
the official app's own Bluetooth traffic -- no jailbreak, no debugger, no
modified security settings. That protocol now runs behind a small HTTP API
on an always-on Raspberry Pi, controllable from a CLI, curl, or your own
automations (Hammerspoon hotkeys, calendar-based standing reminders, etc.).

## Status

Live and working: BLE connect, live height tracking, up/down/stop, and
moving to an absolute height (which is how sit/stand presets work), all
confirmed end-to-end on real hardware. Not yet reverse-engineered:
lock/unlock, and decoding error/status packets. Full investigation log:
[`dev/specs/reverse-engineer.md`](dev/specs/reverse-engineer.md).

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
  desk CLI  ───────────────────────────►  systemd service on a Pi  ───BLE───►  desk
  (or curl,                                (always-on, home network)
   Hammerspoon,
   Home Assistant, ...)
```

- **[`raspberry-pi/`](raspberry-pi/README.md)** -- the live, primary,
  always-on deployment: a `systemd` service reachable over your home
  network.
- **[`cli/`](cli/README.md)** -- a small, dependency-free command-line
  client, usable from any machine with Python 3 and network access to the
  service.
- **[`dev/`](dev/README.md)** -- the original implementation, the
  reverse-engineering history, and the local development/test environment.
  Not live; useful for developing protocol/controller changes (only one of
  `dev/` and `raspberry-pi/` can hold the desk's BLE connection at a time).

## Quick start

**To control your desk:** set up [`raspberry-pi/`](raspberry-pi/README.md)
on a Pi, then use [`cli/`](cli/README.md) from any machine on your network:

```bash
./cli/desk status
./cli/desk stand
./cli/desk sit
```

**To develop or reverse-engineer further:** see
[`dev/README.md`](dev/README.md).

## API

The same HTTP API is exposed by both `raspberry-pi/` and `dev/`'s services:

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
`discover_device.py` (in `raspberry-pi/` or `dev/`).

## Requirements

See [`raspberry-pi/README.md`](raspberry-pi/README.md) (deployment),
[`cli/README.md`](cli/README.md) (client), or
[`dev/README.md`](dev/README.md) (development) for what each part needs.
