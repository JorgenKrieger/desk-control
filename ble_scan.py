import asyncio
import string

from bleak import BleakClient, BleakScanner


DEVICE_NAME = "BLE SPP"

NOTIFY_UUID = "0000fee1-0000-1000-8000-00805f9b34fb"


def format_bytes(data: bytes) -> str:
    return " ".join(f"{byte:02X}" for byte in data)


def printable_ascii(data: bytes) -> str:
    return "".join(
        chr(byte)
        if chr(byte) in string.printable and byte not in (10, 13)
        else "."
        for byte in data
    )


def describe_properties(characteristic) -> str:
    return ", ".join(characteristic.properties)


async def find_device():
    print(f"Scanning for '{DEVICE_NAME}'...")
    print()

    devices = await BleakScanner.discover(timeout=10)

    for device in devices:
        if device.name == DEVICE_NAME:
            return device

    return None


async def read_descriptor(client, descriptor):
    try:
        value = await client.read_gatt_descriptor(descriptor.handle)

        print(f"        Value (hex):   {format_bytes(value)}")

        ascii_value = printable_ascii(value)

        if any(char != "." for char in ascii_value):
            print(f"        Value (ASCII): {ascii_value}")

    except Exception as exc:
        print(f"        Read failed:   {exc}")


async def read_characteristic(client, characteristic):
    try:
        data = await client.read_gatt_char(characteristic.uuid)

        print(f"      Value (hex):   {format_bytes(data)}")

        ascii_value = printable_ascii(data)

        if any(char != "." for char in ascii_value):
            print(f"      Value (ASCII): {ascii_value}")

    except Exception as exc:
        print(f"      Read failed:   {exc}")


async def dump_services(client):
    print()
    print("=" * 72)
    print("GATT SERVICES")
    print("=" * 72)

    for service in client.services:
        print()
        print("SERVICE")
        print(f"  UUID: {service.uuid}")

        for characteristic in service.characteristics:
            print()
            print("  CHARACTERISTIC")
            print(f"    UUID:       {characteristic.uuid}")
            print(f"    Properties: {describe_properties(characteristic)}")

            if characteristic.descriptors:
                print("    Descriptors:")

                for descriptor in characteristic.descriptors:
                    print(f"      UUID: {descriptor.uuid}")
                    await read_descriptor(client, descriptor)

            if "read" in characteristic.properties:
                await read_characteristic(client, characteristic)


def notification_handler(sender, data):
    print()
    print("-" * 72)
    print("NOTIFICATION")
    print("-" * 72)

    print(f"  Characteristic: {sender}")
    print(f"  Hex:            {format_bytes(data)}")

    ascii_value = printable_ascii(data)

    if any(char != "." for char in ascii_value):
        print(f"  ASCII:          {ascii_value}")

    # Known desk position/status packet.
    if len(data) == 7 and data[0] == 0x5A and data[1] == 0x06:
        high = data[3]
        low = data[4]

        position = (high << 8) | low
        height_cm = position / 10

        expected_checksum = (0x06 + high + low) & 0xFF

        print()
        print(f"  Position value:   {position} (0x{position:04X})")
        print(f"  Estimated height: {height_cm:.1f} cm")

        print()
        print(f"  Checksum byte:    0x{data[6]:02X}")
        print(f"  Expected checksum: 0x{expected_checksum:02X}")

        if data[6] == expected_checksum:
            print("  Checksum:         OK")
        else:
            print("  Checksum:         MISMATCH")


async def main():
    device = await find_device()

    if device is None:
        print(f"Could not find '{DEVICE_NAME}'.")
        print()
        print("Make sure:")
        print("  - the desk is powered on")
        print("  - JSBLE is not connected")
        print("  - nRF Connect is not connected")
        return

    print("=" * 72)
    print("DEVICE")
    print("=" * 72)

    print(f"Name:       {device.name}")
    print(f"Address:    {device.address}")
    print(f"Details:    {device.details}")

    print()
    print("Connecting...")

    try:
        async with BleakClient(device) as client:

            print("Connected.")

            print()
            print("=" * 72)
            print("CONNECTION INFO")
            print("=" * 72)

            print(f"Connected:  {client.is_connected}")

            await dump_services(client)

            print()
            print("=" * 72)
            print("NOTIFICATIONS")
            print("=" * 72)

            try:
                await client.start_notify(
                    NOTIFY_UUID,
                    notification_handler
                )

                print()
                print("Subscribed to:")
                print(f"  {NOTIFY_UUID}")
                print()
                print("Listening for notifications.")
                print("Move the desk if you want to generate more data.")
                print()
                print("Press Ctrl+C to stop.")

            except Exception as exc:
                print()
                print(f"Could not subscribe to notifications: {exc}")

            while True:
                await asyncio.sleep(1)

    except Exception as exc:
        print()
        print("=" * 72)
        print("CONNECTION ERROR")
        print("=" * 72)
        print()
        print(exc)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print("Stopped.")
