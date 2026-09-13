import asyncio
from bleak import BleakClient, BleakScanner


DEVICE_NAME = "BLE SPP"

SERVICE_UUID = "0000fee0-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000fee1-0000-1000-8000-00805f9b34fb"
WRITE_UUID = "0000fee2-0000-1000-8000-00805f9b34fb"


def format_bytes(data: bytearray) -> str:
    """Format BLE data as uppercase hexadecimal."""
    return " ".join(f"{byte:02X}" for byte in data)


def notification_handler(sender, data):
    """Called whenever the desk sends us a notification."""
    print(f"← FEE1  {format_bytes(data)}")


async def find_device():
    print(f"Scanning for '{DEVICE_NAME}'...\n")

    devices = await BleakScanner.discover(timeout=10)

    for device in devices:
        if device.name == DEVICE_NAME:
            return device

    return None


async def main():
    device = await find_device()

    if device is None:
        print(f"Could not find '{DEVICE_NAME}'.")
        print("Make sure the desk is powered on and not connected to JSBLE.")
        return

    print(f"Found: {device.name}")
    print(f"Address: {device.address}")
    print()

    print("Connecting...")

    async with BleakClient(device) as client:
        print("Connected.")
        print()

        # Subscribe to desk → computer notifications.
        await client.start_notify(NOTIFY_UUID, notification_handler)

        print("Listening for desk notifications.")
        print()
        print("The program is READ-ONLY.")
        print("It will NOT send anything to the desk.")
        print()
        print("Press Ctrl+C to stop.")
        print()

        # Keep the connection alive.
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDisconnected.")
