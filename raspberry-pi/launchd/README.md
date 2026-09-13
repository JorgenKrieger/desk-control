# launchd service

Runs `service.py` as a per-user background service via macOS `launchd`, so it
starts at login and restarts itself if it ever crashes.

```bash
./install.sh    # generates the plist for this machine and starts the service
./uninstall.sh  # stops it and removes the LaunchAgent
```

Useful commands once installed:

```bash
launchctl list | grep com.desk-control.service
launchctl kickstart -k gui/$(id -u)/com.desk-control.service   # restart
tail -f ~/Library/Logs/desk-control.log
```

`com.desk-control.service.plist.template` is machine-agnostic (`poetry`
location, this project's path, and log path are filled in by `install.sh`);
the generated `~/Library/LaunchAgents/com.desk-control.service.plist` is not
checked into this repo.
