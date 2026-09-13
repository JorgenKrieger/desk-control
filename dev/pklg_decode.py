"""Decode an Apple PacketLogger (.pklg) Bluetooth HCI capture.

Format (little-endian on this host):
    uint32  length      # bytes following this field: 8 (timestamp) + 1 (type) + len(payload)
    uint32  ts_sec
    uint32  ts_usec
    uint8   type        # HCI packet type, see PACKET_TYPES
    bytes   payload      # length - 9 bytes

Focused on extracting ATT (GATT) operations carried inside ACL data packets,
since the desk's commands/notifications ride on the ATT protocol over BLE.
"""

import struct
import sys

PACKET_TYPES = {
    0x00: "HCI_CMD",
    0x01: "HCI_EVENT",
    0x02: "ACL_SENT",       # host -> controller
    0x03: "ACL_RECEIVED",   # controller -> host
    0x08: "SCO_SENT",
    0x09: "SCO_RECEIVED",
    0x0C: "ISO_SENT",
    0x0D: "ISO_RECEIVED",
    0xFC: "NOTE",
}

ATT_CID = 0x0004

ATT_OPCODES = {
    0x01: "ERROR_RSP",
    0x02: "EXCHANGE_MTU_REQ",
    0x03: "EXCHANGE_MTU_RSP",
    0x04: "FIND_INFORMATION_REQ",
    0x05: "FIND_INFORMATION_RSP",
    0x06: "FIND_BY_TYPE_VALUE_REQ",
    0x07: "FIND_BY_TYPE_VALUE_RSP",
    0x08: "READ_BY_TYPE_REQ",
    0x09: "READ_BY_TYPE_RSP",
    0x0A: "READ_REQ",
    0x0B: "READ_RSP",
    0x0C: "READ_BLOB_REQ",
    0x0D: "READ_BLOB_RSP",
    0x10: "READ_BY_GROUP_TYPE_REQ",
    0x11: "READ_BY_GROUP_TYPE_RSP",
    0x12: "WRITE_REQ",
    0x13: "WRITE_RSP",
    0x16: "PREPARE_WRITE_REQ",
    0x17: "PREPARE_WRITE_RSP",
    0x18: "EXECUTE_WRITE_REQ",
    0x19: "EXECUTE_WRITE_RSP",
    0x1B: "HANDLE_VALUE_NOTIFICATION",
    0x1D: "HANDLE_VALUE_INDICATION",
    0x1E: "HANDLE_VALUE_CONFIRMATION",
    0x52: "WRITE_CMD",
}

WRITE_LIKE = {0x12, 0x52}       # write request / write command -> host wrote this
NOTIFY_LIKE = {0x1B, 0x1D}      # notification / indication -> device sent this


def format_bytes(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def iter_records(path):
    with open(path, "rb") as f:
        data = f.read()

    offset = 0
    n = len(data)
    while offset + 9 <= n:
        length, ts_sec, ts_usec, pkt_type = struct.unpack_from("<IIIB", data, offset)
        record_end = offset + 4 + length
        if length < 9 or record_end > n:
            break
        payload = data[offset + 13: record_end]
        yield ts_sec, ts_usec, pkt_type, payload
        offset = record_end


def parse_acl(payload: bytes):
    """Return (att_opcode, handle_or_None, value) if this ACL payload carries ATT, else None."""
    if len(payload) < 4:
        return None

    handle_flags, acl_len = struct.unpack_from("<HH", payload, 0)
    l2cap = payload[4:4 + acl_len]
    if len(l2cap) < 4:
        return None

    l2cap_len, cid = struct.unpack_from("<HH", l2cap, 0)
    body = l2cap[4:4 + l2cap_len]
    if cid != ATT_CID or len(body) < 1:
        return None

    opcode = body[0]
    handle = None
    value = b""
    if opcode in WRITE_LIKE or opcode in NOTIFY_LIKE:
        if len(body) >= 3:
            handle = struct.unpack_from("<H", body, 1)[0]
            value = body[3:]
    else:
        value = body[1:]

    return opcode, handle, value


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <capture.pklg>")
        raise SystemExit(1)

    path = sys.argv[1]
    type_counts = {}

    for ts_sec, ts_usec, pkt_type, payload in iter_records(path):
        type_counts[pkt_type] = type_counts.get(pkt_type, 0) + 1

        type_name = PACKET_TYPES.get(pkt_type)
        if type_name == "NOTE":
            continue

        if pkt_type not in (0x02, 0x03):
            continue

        parsed = parse_acl(payload)
        if not parsed:
            continue

        opcode, handle, value = parsed
        opcode_name = ATT_OPCODES.get(opcode, f"0x{opcode:02X}")

        direction = "->" if pkt_type == 0x02 else "<-"
        time_str = f"{ts_sec}.{ts_usec:06d}"

        handle_str = f"handle=0x{handle:04X}" if handle is not None else ""
        value_str = format_bytes(value) if value else ""

        print(f"{time_str}  {direction}  {opcode_name:28s} {handle_str:14s} {value_str}")

    print("\n--- packet type counts ---", file=sys.stderr)
    for pkt_type, count in sorted(type_counts.items()):
        name = PACKET_TYPES.get(pkt_type, f"0x{pkt_type:02X}")
        print(f"{name:16s} {count}", file=sys.stderr)


if __name__ == "__main__":
    main()
