#!/usr/bin/env bash
# Installs the desk-control service as a per-user launchd LaunchAgent.
#
# Fills in the template with this machine's actual paths (poetry location,
# this project's directory, log path) and bootstraps it.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$SCRIPT_DIR/com.desk-control.service.plist.template"
LABEL="com.desk-control.service"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_PATH="$HOME/Library/Logs/desk-control.log"

POETRY_PATH="$(command -v poetry || true)"
if [ -z "$POETRY_PATH" ]; then
    echo "error: 'poetry' not found on PATH. Install it first (https://python-poetry.org)." >&2
    exit 1
fi
POETRY_DIR="$(dirname "$POETRY_PATH")"

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"

sed \
    -e "s#__POETRY_PATH__#$POETRY_PATH#g" \
    -e "s#__POETRY_DIR__#$POETRY_DIR#g" \
    -e "s#__PROJECT_DIR__#$PROJECT_DIR#g" \
    -e "s#__LOG_PATH__#$LOG_PATH#g" \
    "$TEMPLATE" > "$DEST"

echo "Wrote $DEST"

if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
    echo "Service already loaded, restarting..."
    launchctl bootout "gui/$(id -u)" "$DEST" 2>/dev/null || true
fi

launchctl bootstrap "gui/$(id -u)" "$DEST"
echo "Installed and started $LABEL"
launchctl list | grep "$LABEL" || true
