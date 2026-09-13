#!/usr/bin/env bash
# Installs the desk-control service as a per-user systemd unit (no root
# needed -- BLE access works as a regular user on this setup, see
# specs/port-to-raspberry-pi.md section 7).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$SCRIPT_DIR/desk-control.service.template"
LABEL="desk-control.service"
DEST_DIR="$HOME/.config/systemd/user"
DEST="$DEST_DIR/$LABEL"

if [ ! -x "$PROJECT_DIR/.venv/bin/uvicorn" ]; then
    echo "error: $PROJECT_DIR/.venv/bin/uvicorn not found." >&2
    echo "Set up the venv first: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

mkdir -p "$DEST_DIR"
sed "s#__PROJECT_DIR__#$PROJECT_DIR#g" "$TEMPLATE" > "$DEST"
echo "Wrote $DEST"

systemctl --user daemon-reload
systemctl --user enable --now "$LABEL"
echo "Installed and started $LABEL"

# Without this, a user-level service stops when the SSH session/login
# session ends -- lingering keeps it running independent of any login,
# which is the whole point of an always-on service.
if loginctl enable-linger "$(whoami)" 2>&1; then
    echo "Linger enabled -- service will keep running after logout/reboot."
else
    echo "warning: could not enable linger (may need: sudo loginctl enable-linger $(whoami))" >&2
fi

systemctl --user status "$LABEL" --no-pager || true
