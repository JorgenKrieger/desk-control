# desk-control

A local, self-hosted replacement for the manufacturer's BLE app for a Jingshi
standing desk -- see [`dev/README.md`](dev/README.md) for the full project
story and the reverse-engineered protocol.

This repo has three parts:

- **[`raspberry-pi/`](raspberry-pi/README.md)** -- the live, primary,
  always-on deployment: a `systemd` service on a Raspberry Pi Zero W,
  reachable over the home network.
- **[`cli/`](cli/README.md)** -- a small, dependency-free command-line
  client (`desk status`, `desk stand`, etc.), usable from any machine with
  Python 3 and network access to wherever the service is running.
- **[`dev/`](dev/README.md)** -- the original implementation, the
  reverse-engineering history, and the local development/test environment.
  No longer the live deployment, but still where protocol/controller work
  happens (only one of `dev/` and `raspberry-pi/` can hold the desk's BLE
  connection at a time).
