#!/usr/bin/env bash
# Stops and removes the desk-control user systemd unit.
set -euo pipefail

LABEL="desk-control.service"
DEST="$HOME/.config/systemd/user/$LABEL"

if [ -f "$DEST" ]; then
    systemctl --user disable --now "$LABEL" 2>/dev/null || true
    rm -f "$DEST"
    systemctl --user daemon-reload
    echo "Removed $DEST"
else
    echo "Not installed ($DEST not found)"
fi
