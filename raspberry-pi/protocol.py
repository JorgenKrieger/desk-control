"""Jingshi desk BLE protocol codec.

Confirmed via passive PacketLogger capture of JSBLE's own traffic (see
specs/reverse-engineer.md, section 20). Frame formats:

Commands (phone -> desk, FEE2):
    A5 <LEN> <CMD> [PARAMS...] <CS>

Telemetry (desk -> phone, FEE1):
    5A 06 <ACTIVE_CMD> <HH> <LL> 00 <CS>

Checksum (both directions): sum of every byte between the header byte and the
checksum byte, truncated to 8 bits.

Height is encoded as a big-endian 16-bit value in units of 0.1cm.
"""

CMD_UP = 0x12
CMD_DOWN = 0x14
CMD_STOP = 0x10
CMD_MOVE_TO = 0x31

NOTIFY_HEADER = 0x5A
COMMAND_HEADER = 0xA5


def checksum(payload: bytes) -> int:
    return sum(payload) & 0xFF


def build_command(cmd: int, params: bytes = b"") -> bytes:
    length = len(params) + 3
    body = bytes([length, cmd]) + params
    return bytes([COMMAND_HEADER]) + body + bytes([checksum(body)])


def encode_height(height_cm: float) -> bytes:
    tenths = round(height_cm * 10)
    return tenths.to_bytes(2, "big")


def decode_height(hh: int, ll: int) -> float:
    return ((hh << 8) | ll) / 10


UP_FRAME = build_command(CMD_UP)
DOWN_FRAME = build_command(CMD_DOWN)
STOP_FRAME = build_command(CMD_STOP)


def move_to_frame(height_cm: float) -> bytes:
    return build_command(CMD_MOVE_TO, encode_height(height_cm))


def parse_notification(data: bytes):
    """Parse a FEE1 notification. Returns a dict, or None if not recognized."""
    if len(data) != 7 or data[0] != NOTIFY_HEADER or data[1] != 0x06:
        return None

    active_cmd, hh, ll, _reserved, cs = data[2], data[3], data[4], data[5], data[6]
    body = data[1:6]
    valid = checksum(body) == cs

    return {
        "active_cmd": active_cmd,
        "height_cm": decode_height(hh, ll),
        "checksum_valid": valid,
    }


if __name__ == "__main__":
    assert UP_FRAME == bytes.fromhex("A5031215"), UP_FRAME.hex()
    assert DOWN_FRAME == bytes.fromhex("A5031417"), DOWN_FRAME.hex()
    assert STOP_FRAME == bytes.fromhex("A5031013"), STOP_FRAME.hex()
    assert move_to_frame(70.0) == bytes.fromhex("A50531 02BC F4".replace(" ", "")), move_to_frame(70.0).hex()
    assert move_to_frame(110.0) == bytes.fromhex("A50531 044C 86".replace(" ", "")), move_to_frame(110.0).hex()
    print("protocol.py self-check OK")
