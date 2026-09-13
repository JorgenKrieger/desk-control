# desk-control

A local, self-hosted replacement for the manufacturer's BLE app for a Jingshi
standing desk -- see [`mac/README.md`](mac/README.md) for the full project
story and the reverse-engineered protocol.

This repo has two parts:

- **[`raspberry-pi/`](raspberry-pi/README.md)** -- the live, primary,
  always-on deployment: a `systemd` service on a Raspberry Pi Zero W,
  reachable over the home network.
- **[`mac/`](mac/README.md)** -- the original implementation and the
  reference for protocol/investigation details. No longer the live
  deployment, but still useful for development (only one of the two can
  hold the desk's BLE connection at a time). The `desk` CLI here points at
  the Pi by default.
