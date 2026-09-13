#!/usr/bin/env bash
# Stops and removes the desk-control launchd LaunchAgent.
set -euo pipefail

LABEL="com.desk-control.service"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ -f "$DEST" ]; then
    launchctl bootout "gui/$(id -u)" "$DEST" 2>/dev/null || true
    rm -f "$DEST"
    echo "Removed $DEST"
else
    echo "Not installed ($DEST not found)"
fi
