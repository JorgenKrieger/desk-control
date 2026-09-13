# JSBLE Desk Control — Reverse-Engineering Specification

**Project:** Reverse-engineer the Bluetooth protocol used by a Jingshi standing desk and build a safe, local replacement/control interface.

**Status:** Investigation paused at a useful breakthrough. Resume from this document.

---

## 1. Goal

Determine the complete BLE command protocol used by the JSBLE iOS app to control the standing desk, then implement a local replacement that can:

- connect to the desk over BLE;
- read current desk height;
- receive live height/status updates;
- command upward/downward movement;
- stop movement safely;
- store/configure sit and stand heights;
- recall sit and stand presets;
- understand/implement lock/unlock if possible;
- detect/report controller and motor errors;
- eventually provide a local API/UI suitable for Home Assistant or a custom desktop/web interface.

### Safety requirement

**Do not send arbitrary or guessed commands to the physical desk.**

The desk has previously moved unexpectedly, so protocol discovery should remain read-only until a command is understood with reasonable confidence. Any first write test should preferably be a harmless/non-motion operation or a confirmed STOP command, and should be performed only when the desk is observed and can be manually stopped.

---

# 2. Known hardware/app

## Manufacturer / ecosystem

The desk appears to use the Jingshi / JS-Drive ecosystem.

The Jingshi Bluetooth documentation indicates:

- Bluetooth is BLE 5.0;
- external/integrated Bluetooth modules can control lifting tables;
- when Bluetooth is integrated into the controller, the iPhone app is JSBLE;
- Jingshi makes single-, dual-, and triple-motor controllers.

App:

- **Name:** JSBLE
- **App Store ID:** `1480144998`
- **Developer:** Hangzhou jingshi technology co., LTD.
- **Observed version:** 1.5
- The app is an iOS application running on Apple Silicon macOS.

Installed path:

```text
/Applications/JSBLE.app
/Applications/JSBLE.app/Wrapper/JSBle.app
```

Executable:

```text
/Applications/JSBLE.app/Wrapper/JSBle.app/JSBle
```

The executable is ARM64 Mach-O.

---

# 3. Reverse-engineering constraints

The executable reports:

```text
LC_ENCRYPTION_INFO_64
cryptoff 147456
cryptsize 4096
cryptid 1
```

So FairPlay encryption is present.

The executable nevertheless exposes a large amount of useful Objective-C metadata, selectors, strings, and protocol-related constants.

LLDB attachment to the running app was attempted but macOS denied it:

```text
attach failed (Not allowed to attach to process...)
```

We intentionally did **not** weaken macOS security protections.

Current strategy:

1. static analysis;
2. strings / Objective-C metadata;
3. binary searches;
4. potentially controlled runtime observation;
5. only later, carefully controlled BLE writes.

---

# 4. BLE device

The physical desk advertises as:

```text
BLE SPP
```

Manufacturer data:

```text
30 31 30 36 35 34 31 39
```

ASCII:

```text
01065419
```

This is related to the QR/device identifier:

```text
10065419
```

The exact relationship is unknown.

---

# 5. GATT structure

Bleak discovered:

```text
SERVICE: 0000fee0-0000-1000-8000-00805f9b34fb

    CHARACTERISTIC:
    0000fee2-0000-1000-8000-00805f9b34fb
    properties = write-without-response, write

    CHARACTERISTIC:
    0000fee1-0000-1000-8000-00805f9b34fb
    properties = notify
```

Additional services:

```text
SERVICE:
0000180a-0000-1000-8000-00805f9b34fb

    CHARACTERISTIC:
    00002a50-0000-1000-8000-00805f9b34fb
    properties = read
```

and:

```text
SERVICE:
00010203-0405-0607-0809-0a0b0c0d1912

    CHARACTERISTIC:
    00010203-0405-0607-0809-0a0b0c0d2b12
    properties = write-without-response, read
```

The FEE0 characteristics have descriptors:

```text
FEE2 descriptor 2901:
Phone->Module

FEE1 descriptor 2901:
Module->Phone
```

Likely architecture:

```text
Phone/app
    |
    | FEE2
    v
BLE module / desk controller

desk controller
    |
    | FEE1 notifications
    v
Phone/app
```

This resembles a BLE-to-serial/SPP bridge, although that should not yet be treated as proven implementation detail.

The `180A / 2A50` read returned:

```text
V1.1.8.
```

The additional `10203...` service appears associated with OTA functionality.

---

# 6. Confirmed telemetry protocol

Read-only BLE monitoring has captured FEE1 notifications while moving the desk.

Recurring format:

```text
5A 06 00 HH LL 00 CC
```

Observed interpretation:

```text
5A       = frame/header
06       = message type / command identifier / length (exact meaning TBD)
00       = fixed observed byte
HH LL    = 16-bit position value
00       = fixed observed byte
CC       = checksum
```

Confirmed examples:

```text
5A 06 00 03 20 00 29
5A 06 00 04 03 00 0D
5A 06 00 04 47 00 51
5A 06 00 04 46 00 50
```

Checksum:

```text
CC = (0x06 + HH + LL) & 0xFF
```

The position counter appears approximately equivalent to tenths of a centimetre / millimetres.

Examples:

```text
~99.0 cm  -> 03 DE = 990
~99.1 cm  -> 03 DF = 991
~99.2 cm  -> 03 E0 = 992

100 cm     -> 03 ED = 1005
105 cm     -> 04 1A = 1050
108 cm     -> 04 39 = 1081
110 cm     -> 04 4B = 1099
```

Some display/packet differences are expected because the desk display is coarser and samples were not always captured at exactly the same instant.

**Conclusion:** FEE1 definitely provides useful live position/status telemetry.

---

# 7. App protocol-related strings

The executable contains:

```text
FEE0
FEE1
FEE2
BLE SPP
```

It also contains:

```text
kPeripheralCurrentHeightUpdateNoticiation
currentHeight
5a06
5a09
```

Important Objective-C properties/selectors:

```text
readCharacteristic
writeCharacteristic
connectedPerpheral
peripheral
setCurrentHeight:
updateCurrentHeight:
setReadCharacteristic:
setWriteCharacteristic:
writeCharacteristic
```

Bluetooth APIs:

```text
CBPeripheral
CBPeripheralDelegate

maximumWriteValueLengthForType:

writeValue:
writeValue:forCharacteristic:type:
writeValue:forCharacteristic:type:completionBlock:

writeValue:forDescriptor:
writeValue:forDescriptor:completionBlock:

peripheral:didWriteValueForCharacteristic:error:
peripheral:didWriteValueForDescriptor:error:
```

This confirms that JSBLE uses CoreBluetooth and writes through `CBPeripheral`.

---

# 8. App controls

The executable contains:

```text
Control_sit
Control_stand
Control_Lock
Control_Disconnect
Control_lockDevice
Control_lockDevice_desc
Control_disconnectDevice
Control_Control_disconnectDevice_desc
```

Height-related strings:

```text
set_height
set_sit_height
set_stand_height
```

Controllers:

```text
SettingHeightController
SettingHeightCell
```

The UI therefore appears to support:

### Manual movement

- Up
- Down

### Preset movement

- Sit
- Stand

### Preset configuration

- Set sit height
- Set stand height

### Other

- Lock
- Disconnect

The exact BLE packet for each operation is unknown.

---

# 9. Error strings

The app contains:

```text
01 Main power is to high
02 Screw clearance over 1cm
03 Hand Controller no connect
04 Hand Controller communication error
05 Blocked off Stop
06 Main power start error
07 Main power run protect
08 The table tilt when it is running
09 Main power High temperature protect

11 Motor1 no connect
12 Motor1 Current sampling error
13 Motor1 lose phase line
14 Motor1 Hall error
15 Motor1 phase shor
16 Motor1 blocked
17 Motor1 direction error
18 Motor1 over load

21 Motor2 no connect
22 Motor2 Current sampling error
23 Motor2 lose phase line
24 Motor2 Hall error
25 Motor2 phase short
26 Motor2 blocked
27 Motor2 direction error
28 Motor2 over load

40 Tandem line drops
41 Tandem signal error
42 eeprom error
43 Gyro-sensor error
```

These should eventually be mapped to actual status/error packets.

---

# 10. Important negative finding

The executable contains the ASCII string:

```text
5a09
```

but a raw byte search found:

```text
5a09: 0 hits
```

Also:

```text
5a0600: 0 hits
5a0900: 0 hits
```

The only actual `5A 06` byte sequence found was:

```text
0x249fc
```

but it was not a complete captured status packet.

Therefore:

**Do not assume the string `5a09` is itself a hard-coded packet.**

It is likely a protocol/message identifier represented as a string, or otherwise used by code that constructs packets dynamically.

---

# 11. Current protocol hypothesis

Likely architecture:

```text
                   BLE
JSBLE app  <-------------------->  BLE SPP module
                                      |
                                      | proprietary serial protocol
                                      v
                                desk controller
                                      |
                                      v
                                motor controller
```

Known:

```text
5A 06 ... = current-height/status notification
```

Unknown:

```text
5A ?? ... = UP
5A ?? ... = DOWN
5A ?? ... = STOP
5A ?? ... = SIT
5A ?? ... = STAND
5A ?? ... = save preset
5A ?? ... = lock/unlock
5A ?? ... = error/status
```

These are hypotheses, not established facts.

---

# 12. Main objectives

## A. Reconstruct frame format

Determine:

- header;
- message/command ID;
- payload length;
- payload fields;
- checksum;
- request/response relationship;
- whether commands and telemetry use the same framing.

## B. Identify movement commands

Find exact FEE2 payloads for:

```text
UP
DOWN
STOP
```

These are the highest-priority commands.

## C. Identify preset behavior

Determine whether SIT/STAND are:

1. controller-side preset commands, or
2. app-side closed-loop movement.

For example, app-side movement might behave like:

```text
target = stored_sit_height

while current_height != target:
    send movement command
    wait for FEE1 height notification
```

Controller-side behavior might instead be:

```text
send "recall preset 1"
```

## D. Determine preset storage

Find out whether `set_sit_height` / `set_stand_height`:

- save locally in the app;
- write to controller EEPROM;
- write to a preset slot;
- or do something else.

## E. Identify lock/unlock

Determine whether lock means:

- UI lock;
- controller lock;
- child lock;
- motor lock;
- communication lock.

## F. Decode errors

Map the known error descriptions to actual packets/status bytes.

---

# 13. Immediate next static-analysis steps

### Protocol-like strings

```bash
cd "/Applications/JSBLE.app/Wrapper/JSBle.app"

strings ./JSBle | grep -Ei '^5a[0-9a-f]+$'
```

Also:

```bash
strings ./JSBle | grep -Ei '0x5a|0X5A|command|packet|checksum|checkSum|crc'
```

### Find surrounding strings/classes

```bash
strings ./JSBle | grep -B50 -A50 'updateCurrentHeight:'
```

```bash
strings ./JSBle | grep -B50 -A50 'writeCharacteristic'
```

```bash
strings ./JSBle | grep -B50 -A50 'settingHeight:'
```

Goal: identify the BLE/protocol-handling class.

### Inspect the lone raw `5A06`

```bash
xxd -g 1 -s 0x249c0 -l 128 ./JSBle
```

Determine whether it is actually protocol-related.

---

# 14. Preferred runtime strategy

If static analysis stalls, observe the app rather than guessing.

The desired observation:

```text
Press UP
    ↓
CoreBluetooth
    ↓
writeValue:forCharacteristic:type:
    ↓
exact FEE2 bytes
```

Potential approaches:

- Objective-C runtime instrumentation;
- DYLD/interposition where applicable;
- Frida if compatible with this Apple Silicon/iOS-app environment;
- system-level CoreBluetooth observation;
- another permitted runtime instrumentation mechanism.

Do not disable SIP or other major macOS security protections just to attach a debugger.

---

# 15. BLE capture logger

A read-only Python/Bleak listener already exists.

Future logging should record:

```text
timestamp
notification bytes
message type
decoded position
checksum validity
```

Example:

```text
12:31:04.123  5A 06 00 04 4B 00 55
                 type=06
                 position=1099
                 checksum=valid
```

The logger should remain read-only during protocol discovery.

---

# 16. Target software architecture

Once the protocol is known:

```text
BLE transport
      ↓
Desk protocol codec
      ↓
Desk state model
      ↓
Control API
      ↓
UI / Home Assistant
```

Potential Python structure:

```text
desk_control/
    ble.py
    protocol.py
    models.py
    controller.py
    cli.py
```

Potential API:

```python
desk.connect()

desk.height
desk.is_moving
desk.errors

desk.move_up()
desk.move_down()
desk.stop()

desk.move_to_sit()
desk.move_to_stand()

desk.set_sit_height()
desk.set_stand_height()

desk.lock()
desk.unlock()
```

Do not implement write methods until their packets are known.

---

# 17. Acceptance criteria

## BLE

Document:

- discovery;
- device identification;
- service UUID;
- write characteristic;
- notify characteristic;
- connection behavior;
- notification subscription.

## Protocol

Document:

- frame structure;
- command IDs;
- payload encoding;
- checksum;
- acknowledgements;
- errors.

## Controls

Implement and verify:

- UP;
- DOWN;
- STOP;
- SIT;
- STAND;
- set SIT;
- set STAND;
- lock/unlock;
- status/error reporting.

## Final implementation

A local program should be able to:

1. connect;
2. display current height;
3. receive live updates;
4. perform controlled movement;
5. stop;
6. recall presets;
7. report errors.

---

# 18. Safety

This controls a physical actuator.

For first command testing:

- desk must remain visually observable;
- physical controller must be accessible;
- use very short movements;
- keep hands and body away from moving mechanisms;
- never work underneath the desk while testing;
- never leave the desk unattended;
- test only when sufficiently alert.

The original motivation includes unexpected desk movement, so the replacement must not introduce another uncontrolled movement mechanism.

---

# 19. Current stopping point

### High confidence

- JSBLE is the relevant official app.
- Desk advertises as `BLE SPP`.
- FEE0 is the relevant service.
- FEE2 is Phone → Module.
- FEE1 is Module → Phone.
- FEE1 provides live height/status notifications.
- `5A 06 00 HH LL 00 CC` is confirmed telemetry.
- `HH LL` is approximately a 0.1 cm position counter.
- Checksum for observed `06` packets is `(06 + HH + LL) & 0xFF`.
- JSBLE has explicit concepts for current height, BLE characteristics, sit/stand presets, up/down controls, lock, and disconnect.
- JSBLE contains `5a06` and `5a09` strings.
- `5A 09` is not present as literal bytes in the executable.

### Unknown

- UP packet;
- DOWN packet;
- STOP packet;
- SIT packet;
- STAND packet;
- preset storage;
- lock protocol;
- complete frame structure;
- acknowledgements;
- error packet structure;
- exact meaning of `5A09`.

### Best next move

**Do not guess commands.**

First determine how JSBLE constructs FEE2 writes, preferably through runtime instrumentation or further static analysis.

The objective is to reach a statement like:

> “When JSBLE's user presses this button, it sends this exact frame over FEE2; these bytes have these meanings; the desk responds with these FEE1 packets.”

Once that is established, implementing a local replacement is primarily an engineering task rather than BLE guesswork.

---

# 20. Session update — captured via PacketLogger (macOS Bluetooth HCI sniffing)

Real JSBLE traffic was captured non-invasively using Apple's PacketLogger tool (part of
“Additional Tools for Xcode”), which taps the Mac's own Bluetooth HCI stack. This requires
installing a Bluetooth logging configuration profile from
`developer.apple.com/bug-reporting/profiles-and-logs/?platform=macos&name=bluetooth` and a
reboot; no code injection, debugging, or SIP changes were involved. `.pklg` captures are decoded
with `pklg_decode.py` in this repo (little-endian record header: `len, ts_sec, ts_usec, type`,
per-record payload parsed down through HCI ACL → L2CAP → ATT).

## ATT handles (this connection)

```text
0x000A = FEE2 (write; commands go here)
0x000D = FEE1 (notify; telemetry arrives here)
```

JSBLE writes with **Write Request** (waits for response), not write-without-response, despite
FEE2 advertising both properties.

## Corrected checksum rule (supersedes section 6)

The earlier `CC = (0x06 + HH + LL) & 0xFF` formula only worked because the status byte happened
to be `0x00` in those examples. The real rule, confirmed across both notification and command
frames:

```text
CS = (sum of every byte between the header byte and the checksum byte) & 0xFF
```

## Corrected telemetry frame model (supersedes section 6)

Byte 2 (previously “00 = fixed observed byte”) actually echoes the currently-active command byte
while the desk is moving under that command, and reads `0x00` when idle/coasting between explicit
commands:

```text
5A 06 <ACTIVE_CMD> HH LL 00 CC
```

## FEE2 command frame format

```text
A5 <LEN> <CMD> [PARAMS...] <CS>
```

## Confirmed commands (resolved with isolated single-action captures)

| Bytes | Meaning | Confidence |
|---|---|---|
| `A5 03 12 15` | **UP** — movement start | High |
| `A5 03 14 17` | **DOWN** — movement start | High — confirmed via an isolated down-only capture (`log/log-down-only.pklg`): these were the very first bytes sent, immediately followed by descending height. (Supersedes an earlier draft of this doc that misread this as STOP, based on an ambiguous mixed UP/SIT/STAND capture where DOWN was actually pressed briefly after UP.) |
| `A5 03 10 13` | **STOP** | High — confirmed via a long (~10s) isolated UP hold followed by staying connected and idle for 24 more real seconds before disconnecting (`log/log-up.pklg`). After the two `10 13` writes, FEE1 went completely silent for the full 24s (the desk only sends telemetry while actually moving), with no further movement. |
| `A5 05 31 HH LL CS` | **Move to absolute height.** `HH LL` = target height, big-endian, 0.1cm units (same encoding as telemetry). Observed `02 BC` = 700 → 70.0cm on SIT; `04 4C` = 1100 → 110.0cm on STAND. | High — confirmed via a clean isolated SIT-only capture (`log/log-sit.pklg`): two writes of this frame, then the desk glided autonomously and smoothly all the way to the exact target height, with zero other commands involved. |

**Key implication:** SIT/STAND are not “recall preset slot” commands — JSBLE sends the controller
an absolute target height directly, and the controller performs its own closed-loop move
end-to-end with no further app involvement. This resolves objective 12.C: positioning is
controller-side, but the *preset heights themselves* are most likely stored app-side (in JSBLE),
since the app supplies the literal height value each time rather than a slot index. A local
replacement can implement `move_to(height_cm)` generically using this one command — SIT and STAND
are just this command with the user's stored sit/stand heights.

## Movement command send pattern

Observed pattern across all captures: the app sends the relevant command frame **twice**, ~150-
250ms apart (both as `WRITE_REQ`, i.e. with response), then relies on the desk's own controller to
carry out the full movement autonomously — periodic `5A 06 <cmd> HH LL 00 CC` notifications arrive
roughly every 200-270ms while moving, with `<cmd>` echoing the last command byte while it's
“fresh” and falling back to `00` once the controller considers itself just coasting/idle-updating.

Confirmed with a long (~10.4s) isolated UP hold (`log/log-up.pklg`): **no periodic keep-alive/
repeat traffic exists at all.** JSBLE sends the UP command exactly twice at touch-down and nothing
else for the entire hold — the desk moves continuously and autonomously start-to-stop from that
single command. There is no BLE-level watchdog requiring the app to keep pinging while a button is
held; “hold to move” is purely a JSBLE UI/UX choice. The desk also only emits FEE1 telemetry while
actually moving — confirmed by 24 seconds of complete silence on FEE1/FEE2 after STOP was sent and
before the connection was intentionally closed.

## Open questions

- `set_sit_height` / `set_stand_height` behavior — not yet captured. Likely candidates: either
  they simply cause the app to remember a value locally (no BLE write at all beyond confirming
  current position), or they issue some other command. Needs an isolated capture of pressing
  “set sit height” specifically.
- Lock/unlock — not yet captured.
- Error/status packets — not yet captured (would need to induce a real fault condition, which is
  out of scope for now).
- Whether UP/DOWN behave differently on a much longer hold (repeat traffic, safety timeout, etc).
