"""Command-line client for the desk-control service.

A thin wrapper around the same HTTP API Hammerspoon/automations would call
(see service.py) -- nothing here talks to the desk directly, it's just nicer
to type `desk stand` than a curl one-liner.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# The Raspberry Pi is the primary always-on controller (see
# raspberry-pi/specs/port-to-raspberry-pi.md) -- this Mac's own service is
# dev/reference only and isn't normally running. Override with
# DESK_CONTROL_URL if you're pointing at something else (e.g. running the
# Mac service locally for development).
BASE_URL = os.environ.get("DESK_CONTROL_URL", "http://0.0.0.0:8842")


def request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("content-type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.load(resp)
    except urllib.error.URLError as exc:
        print(f"Could not reach the desk-control service at {BASE_URL}: {exc}", file=sys.stderr)
        print("Is it running? (poetry run uvicorn service:app --host 127.0.0.1 --port 8842)", file=sys.stderr)
        sys.exit(1)
    except urllib.error.HTTPError as exc:
        detail = json.load(exc).get("detail", exc.reason)
        print(f"Error: {detail}", file=sys.stderr)
        sys.exit(1)


def print_status(status: dict) -> None:
    if not status["connected"]:
        print("Not connected to the desk.")
        return

    height = status["height_cm"]
    height_str = f"{height:.1f}cm" if height is not None else "unknown"
    moving_str = "moving" if status["is_moving"] else "idle"
    print(f"{height_str}  ({moving_str})")


def cmd_status(args):
    print_status(request("GET", "/status"))


def cmd_simple_action(path: str):
    def handler(args):
        request("POST", path)
        print_status(request("GET", "/status"))
    return handler


def cmd_move_to(args):
    request("POST", "/move_to", {"height_cm": args.height_cm})
    print_status(request("GET", "/status"))


def cmd_config_get(args):
    print(json.dumps(request("GET", "/config"), indent=2))


def cmd_config_set(args):
    body = {}
    if args.sit_height_cm is not None:
        body["sit_height_cm"] = args.sit_height_cm
    if args.stand_height_cm is not None:
        body["stand_height_cm"] = args.stand_height_cm
    if args.device_id is not None:
        body["device_id"] = args.device_id

    if not body:
        print("Nothing to set. Pass at least one of --sit, --stand, --device-id.", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(request("POST", "/config", body), indent=2))
    print("\nRestart the service for device_id changes to take effect.")


def main():
    parser = argparse.ArgumentParser(prog="desk", description="Control the standing desk.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show current height and movement state").set_defaults(func=cmd_status)
    subparsers.add_parser("up", help="Start moving up").set_defaults(func=cmd_simple_action("/up"))
    subparsers.add_parser("down", help="Start moving down").set_defaults(func=cmd_simple_action("/down"))
    subparsers.add_parser("stop", help="Stop movement").set_defaults(func=cmd_simple_action("/stop"))
    subparsers.add_parser("sit", help="Move to the stored sit height").set_defaults(func=cmd_simple_action("/sit"))
    subparsers.add_parser("stand", help="Move to the stored stand height").set_defaults(func=cmd_simple_action("/stand"))

    move_to_parser = subparsers.add_parser("move-to", help="Move to a specific height")
    move_to_parser.add_argument("height_cm", type=float)
    move_to_parser.set_defaults(func=cmd_move_to)

    config_parser = subparsers.add_parser("config", help="View or change stored config")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)

    config_subparsers.add_parser("get", help="Show current config").set_defaults(func=cmd_config_get)

    config_set_parser = config_subparsers.add_parser("set", help="Update config")
    config_set_parser.add_argument("--sit", dest="sit_height_cm", type=float, help="Sit height in cm")
    config_set_parser.add_argument("--stand", dest="stand_height_cm", type=float, help="Stand height in cm")
    config_set_parser.add_argument("--device-id", dest="device_id", help="Desk device identifier")
    config_set_parser.set_defaults(func=cmd_config_set)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
