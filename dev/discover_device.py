"""One-time setup helper: find your desk's device_id.

"BLE SPP" is a generic name used by many cheap serial-over-BLE modules, so
the service needs a way to tell your specific desk apart from any other such
device that might be nearby. This scans for devices advertising that name
and prints the identifier to put in your config (see README.md).

Run this before starting the service (or with the service stopped) --
once something is connected to the desk, it stops advertising and won't
show up in this scan.
"""

import asyncio

from bleak import BleakScanner

DEVICE_NAME = "BLE SPP"


def decode_manufacturer_data(manufacturer_data: dict) -> str | None:
    for company_id, data in manufacturer_data.items():
        full = bytes([(company_id >> 8) & 0xFF, company_id & 0xFF]) + data
        try:
            return full.decode("ascii")
        except UnicodeDecodeError:
            return full.hex()
    return None


async def main():
    print(f"Scanning for devices advertising '{DEVICE_NAME}' (10s)...\n")
    found = await BleakScanner.discover(timeout=10.0, return_adv=True)

    matches = [(d, adv) for d, adv in found.values() if d.name == DEVICE_NAME]

    if not matches:
        print(f"No device named '{DEVICE_NAME}' found. Make sure:")
        print("  - the desk is powered on")
        print("  - it's not connected to another app (e.g. JSBLE)")
        print("  - this project's own service isn't currently running/connected")
        print("    to it -- a connected device stops advertising, so this scan")
        print("    won't see it. If you're running the service here for local")
        print("    testing, stop it first (Ctrl-C, or launchctl bootout")
        print("    gui/$(id -u)/com.desk-control.service if installed).")
        print("    Otherwise check ../raspberry-pi/ isn't already connected.")
        return

    if len(matches) > 1:
        print(f"Found {len(matches)} devices named '{DEVICE_NAME}' -- a device_id")
        print("is definitely worth setting so the service reliably picks the right one.\n")

    first_identifier = None
    for device, adv in matches:
        identifier = decode_manufacturer_data(adv.manufacturer_data)
        first_identifier = first_identifier or identifier
        print(f"Address:    {device.address}")
        print(f"device_id:  {identifier}")
        print()

    print("Set it with:")
    print(
        "  curl -X POST http://127.0.0.1:8842/config "
        "-H 'content-type: application/json' "
        f'-d \'{{"device_id": "{first_identifier}"}}\''
    )


if __name__ == "__main__":
    asyncio.run(main())
