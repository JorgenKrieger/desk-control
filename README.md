# desk-control

A local, self-hosted replacement for the manufacturer's BLE app for a Jingshi
standing desk -- see [`mac/README.md`](mac/README.md) for the full project
story, the reverse-engineered protocol, and how it works.

This repo has two parts:

- **[`mac/`](mac/README.md)** -- the working, live-tested implementation
  running on a Mac (background service via `launchd`, BLE via CoreBluetooth).
- **[`raspberry-pi/`](raspberry-pi/README.md)** -- a from-`mac/` starting
  point being ported to run on an always-on Raspberry Pi Zero W instead, so
  desk control doesn't depend on a laptop being awake. See
  [`raspberry-pi/specs/port-to-raspberry-pi.md`](raspberry-pi/specs/port-to-raspberry-pi.md)
  for the porting plan -- the code there hasn't been changed yet, only copied.
