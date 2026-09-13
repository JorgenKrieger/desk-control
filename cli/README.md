# desk CLI

A small, dependency-free command-line client for the desk-control service
(whichever machine it's running on -- normally the Raspberry Pi, see
[`../raspberry-pi/`](../raspberry-pi/README.md)). Not Mac- or Pi-specific:
`cli.py` only uses the Python standard library, so this runs anywhere with
Python 3 and network access to the service.

```bash
./desk status
./desk up
./desk down
./desk stop
./desk sit
./desk stand
./desk move-to 95
./desk config get
./desk config set --sit 72 --stand 112
```

Put this directory on your `PATH` (or symlink `desk` into somewhere already
on it, e.g. `ln -s "$(pwd)/desk" ~/.local/bin/desk`) to run `desk status`
from anywhere.

By default this points at the Raspberry Pi
(`http://0.0.0.0:8842`). Override with the `DESK_CONTROL_URL`
environment variable to point elsewhere (e.g. `../dev/`'s service running
locally for development).
