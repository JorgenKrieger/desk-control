# systemd service

Runs `service.py` as a per-user `systemd` unit, so it starts at boot and
restarts itself if it ever crashes -- no root required (BLE access works as
a regular user on this Pi, see `../specs/port-to-raspberry-pi.md` section 7).

```bash
./install.sh    # generates the unit for this machine and starts it
./uninstall.sh  # stops it and removes the unit
```

Useful commands once installed:

```bash
systemctl --user status desk-control.service
systemctl --user restart desk-control.service
journalctl --user -u desk-control.service -f   # logs
```

A per-user unit normally stops when your login/SSH session ends --
`install.sh` also enables "lingering" (`loginctl enable-linger`) so the
service keeps running independent of any active login, which is the whole
point of an always-on Pi. If that step fails, run it yourself:
`sudo loginctl enable-linger $(whoami)`.

`desk-control.service.template` is machine-agnostic (the project's actual
path is filled in by `install.sh`); the generated
`~/.config/systemd/user/desk-control.service` is not checked into this repo.
