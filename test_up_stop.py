"""Second live write test: send UP briefly, then STOP ourselves.

Safety: only run this while watching the desk with the physical controller
within reach. Movement will last about 1 second before we stop it.
"""

import asyncio

from bleak import BleakClient, BleakScanner

import protocol

DEVICE_NAME = "BLE SPP"
WRITE_UUID = "0000fee2-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000fee1-0000-1000-8000-00805f9b34fb"

MOVE_SECONDS = 1.0


def notification_handler(sender, data: bytearray):
    hex_str = " ".join(f"{b:02X}" for b in data)
    parsed = protocol.parse_notification(bytes(data))
    if parsed:
        print(f"< FEE1  {hex_str}   height={parsed['height_cm']:.1f}cm  "
              f"active_cmd=0x{parsed['active_cmd']:02X}  "
              f"checksum_valid={parsed['checksum_valid']}")
    else:
        print(f"< FEE1  {hex_str}   (unrecognized)")


async def main():
    print(f"Scanning for '{DEVICE_NAME}'...")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10)
    if device is None:
        print("Device not found. Make sure JSBLE is not connected to it.")
        return

    print(f"Found {device.address}. Connecting...")
    async with BleakClient(device) as client:
        print("Connected.")
        await client.start_notify(NOTIFY_UUID, notification_handler)

        print()
        print(f"About to send UP, wait {MOVE_SECONDS}s, then send STOP.")
        input("Press Enter to confirm you are watching the desk and ready to intervene... ")

        print("Sending UP:", protocol.UP_FRAME.hex(" ").upper())
        await client.write_gatt_char(WRITE_UUID, protocol.UP_FRAME, response=True)

        await asyncio.sleep(MOVE_SECONDS)

        print("Sending STOP:", protocol.STOP_FRAME.hex(" ").upper())
        await client.write_gatt_char(WRITE_UUID, protocol.STOP_FRAME, response=True)

        print("Watching for any further notifications for 5 seconds...")
        await asyncio.sleep(5)

        print("Done. Disconnecting.")


if __name__ == "__main__":
    asyncio.run(main())
