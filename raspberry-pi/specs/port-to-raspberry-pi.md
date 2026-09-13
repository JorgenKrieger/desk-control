# Porting desk-control to a Raspberry Pi Zero W

**Status:** Live and deployed. The dependency-compatibility risk was
resolved empirically against the real Pi over SSH (sections 3.1 and 7),
the environment is set up and working end-to-end on the actual hardware
(section 7's follow-up), and the service is installed and running as a
`systemd` unit (section 3.2, `../systemd/`). This document remains as the
record of what changed, why, and what's still open (see the checklist and
open questions below) -- most of the original plan is done, not aspirational
anymore.

**Target hardware:** original Raspberry Pi Zero W (single-core ARM11,
ARMv6, 1GHz, 512MB RAM) -- *not* the newer Pi Zero 2 W (quad-core ARMv8).
This distinction matters a lot for package compatibility (see below).
Confirmed actual specs on the real device: 426MB usable RAM + 425MB swap,
running Raspbian 13 (trixie), Python 3.13.5, glibc 2.41, BlueZ 5.82.

---

## 1. Why

The Mac implementation works well, but ties desk control to the Mac being
awake and on the same machine (`mac/service.py` binds to `127.0.0.1` only).
An always-on Pi makes this real infrastructure: reachable over the home
network regardless of what the Mac is doing, which also unblocks a future
Home Assistant integration (HA would run as its own separate always-on
process, needing network access to this service -- `127.0.0.1`-only would
never satisfy that).

## 2. What ports unchanged

`protocol.py`, `controller.py`, and `config.py` are pure Python with no
macOS-specific dependencies -- the BLE frame codec, the `Desk` class, and
preset storage logic should all work as-is. `bleak` (the BLE library used
throughout) supports Linux via BlueZ, so the actual Bluetooth communication
code (`connect`, `move_up`, notification handling, etc.) shouldn't need
logic changes.

## 3. What has to change, and why

### 3.1 Web framework -- resolved empirically, less scary than it looked

**Update: tested directly against the real Pi over SSH (see section 7 for
the full log). The original concern below was based on generic/older
reports and turned out not to apply to this specific, very recently
imaged Pi. No framework rewrite is needed.**

The original worry: `mac/service.py` uses FastAPI (which requires Pydantic
v2) and `uvicorn[standard]` (which pulls in `uvloop`/`httptools`). Pydantic
v2's core (`pydantic-core`) is written in Rust; `uvloop`/`httptools` are C
extensions, and ARMv6 isn't a standard "manylinux" wheel target most
packages publish binaries for. There were also real-world reports of
`pydantic-core` requiring a newer glibc (2.33+) than older Raspberry Pi OS
images ship (2.31).

**What's actually true on this Pi:**

- This Pi's glibc is 2.41 (Raspbian 13/trixie is a recent image) -- the
  glibc concern doesn't apply here at all.
- `pydantic-core` has a **prebuilt wheel for `linux_armv6l`/cp313** on
  piwheels. No Rust compile needed, installs instantly.
- `httptools`, `pyyaml`, `watchfiles`, `websockets` also have prebuilt
  armv6l wheels.
- Plain `fastapi` + `uvicorn` (no `[standard]` extra) installs cleanly in
  under 2 minutes, zero compilation.
- The only package that lacks a wheel and compiles from source is
  `uvloop` (part of `uvicorn[standard]`) -- and it's not needed. It's a
  performance optimization (a faster event loop) that's irrelevant at our
  scale (a handful of requests per minute), and compiling it pushed the Pi
  to a near-unresponsive memory-thrashing state (see section 7).

**Decision: keep FastAPI + Pydantic as-is. Just don't use
`uvicorn[standard]` -- install plain `uvicorn`.** No Starlette rewrite, no
manual JSON validation. This directory's `service.py`, `pyproject.toml`
still need their dependency line changed from `uvicorn[standard]` to
`uvicorn`, but nothing else about the web layer needs to change.

### 3.2 Process supervision: `launchd` -> `systemd`

`mac/launchd/` (the install script, uninstall script, and plist template)
is macOS-only. Needs a Linux equivalent:

- A `systemd` unit file (analogous to the plist template) with `Restart=on-failure`
  and a sane `RestartSec` (mirrors the plist's `KeepAlive`/`ThrottleInterval`).
- An install/uninstall script pair using `systemctl enable --now` /
  `systemctl disable --now` instead of `launchctl bootstrap`/`bootout`.
- Decide: run as the default `pi`/user account, or a dedicated service
  user? Affects the config file path (see 3.5) and BLE permissions (see
  3.4).

### 3.3 Network exposure -- a real decision, not just config

`mac/service.py` deliberately binds to `127.0.0.1` because on the Mac
everything calling it (Hammerspoon, `desk` CLI) runs on the same machine.
On the Pi, the entire point is to be reachable from other devices (this
Mac's Hammerspoon, a future Home Assistant instance) -- so it needs to bind
to `0.0.0.0` (or the Pi's specific LAN address) instead.

**This changes the threat model.** On the Mac, the worst case of an open
port is "another process on your own single-user laptop." On the Pi, it's
"anything on your home network can move the desk," which is a bigger
surface (a compromised IoT device, a guest on your Wi-Fi, etc.). Open
question to decide before/during the port, not something to default
silently:

- Accept the risk as-is (reasonable for a private home network with no
  guest access -- consistent with how a lot of home BLE/IoT bridges work).
- Or add a minimal shared-secret check (e.g. a header the CLI/Hammerspoon
  send, checked against a value in `config.json`) -- cheap to add, avoids
  "anyone on my Wi-Fi" being literally true.
- Or restrict via the Pi's own firewall (`ufw`/`iptables`) to specific
  device IPs (the Mac, a future HA box) -- more setup, most precise.

### 3.4 BLE permissions on Linux -- tested, works out of the box

**Update: tested directly (section 7). No `setcap`, no root needed.**
Scanning, connecting, writing (the safe STOP-probe), and receiving a
notification all worked as the regular `jorgen` user with zero special
permission setup. The `setcap`/root concern below was the standard general
advice for Linux BLE work, but this Pi's default BlueZ/D-Bus policy already
allows a normal local user to do everything this project needs.

Original concern, kept for reference in case a future OS image or user
setup behaves differently: unlike macOS (where CoreBluetooth access is
gated by a one-time system permission prompt), `bleak`'s Linux backend (via
BlueZ/`dbus-fast`) can sometimes need either running as root or granting
the Python binary explicit capabilities:

```bash
sudo setcap 'cap_net_raw,cap_net_admin+eip' "$(readlink -f "$(command -v python3)")"
```

Not needed here, but keep this in mind if a fresh install ever behaves
differently.

**Related finding from section 7:** `dbus-fast` (the library `bleak` uses
for BlueZ/D-Bus on Linux) is not pure Python as generally described -- it
ships an optional Cython-accelerated C extension with no prebuilt armv6l
wheel, so installing it means an on-device compile (~7 small `.c` files,
several minutes, see section 7). This succeeded safely and only needs to
happen once (the built wheel gets cached in `~/.cache/pip/wheels/`), but
plan for it as a real step, and make sure `python3-dev` is installed first
(see 3.1's sibling finding in section 7 -- a fresh Raspberry Pi OS install
doesn't include Python's development headers, which are needed to compile
*any* C extension, not just this one).

### 3.5 Config file location

`config.py` currently writes to `~/Library/Application Support/desk-control/`
(macOS-specific). Linux equivalent: `~/.config/desk-control/config.json`
(XDG convention) if running as a normal user, or `/etc/desk-control/config.json`
if running as a dedicated service account/root. Depends on the decision in
3.2.

### 3.6 Device discovery

`discover_device.py` should work unchanged (matching is by device name +
reconstructed manufacturer data, not a hardcoded address), but expect to
*see* different-looking addresses than on the Mac -- BlueZ reports real MAC
addresses (`AA:BB:CC:DD:EE:FF`), whereas macOS's CoreBluetooth reports an
opaque UUID instead of the real address for privacy reasons. This is
expected, not a bug.

## 4. What should NOT need re-deriving

The confirmed BLE protocol itself (`specs/reverse-engineer.md`, copied into
this directory) doesn't change -- it's a property of the desk, not of which
computer talks to it. Don't re-run the whole reverse-engineering process.

**Do** re-verify the write path (UP/DOWN/STOP) once actually running on the
Pi before trusting it unattended, per this project's standing safety rule --
same protocol, but a genuinely different Bluetooth stack underneath
(BlueZ instead of CoreBluetooth), so a fresh confirmation pass with the
desk observed and the physical controller in reach is warranted before
walking away from it.

## 5. Rough migration checklist

- [x] Flash Raspberry Pi OS Lite and get SSH access -- done, running
      Raspbian 13 (trixie)
- [x] Confirm the system Python version satisfies `requires-python >=3.11`
      -- 3.13.5, confirmed
- [x] Try a plain `pip install fastapi pydantic uvicorn[standard]`
      empirically -- done (section 7): no Starlette rewrite needed, just
      drop the `[standard]` extra
- [x] Confirm `bleak` itself installs -- done (section 7): works, but
      needs `python3-dev` installed first, and the `dbus-fast` compile
      takes several minutes the first time
- [x] Install `python3-dev` on the real deployment install -- done
- [x] Update `pyproject.toml`: `uvicorn[standard]` -> `uvicorn`, and added
      `requirements.txt` since the Pi uses plain `pip`/`venv`, not Poetry
- [x] Real deployment venv set up at `~/desk-control/.venv` on the Pi
      (rsynced source files, not the throwaway test venv), all deps
      installed cleanly (`dbus-fast`'s cached wheel reused instantly, no
      recompile)
- [x] Test opening a real BLE connection through BlueZ -- confirmed
      working with zero special permissions (section 7): scan, connect,
      write, and notification receipt all succeeded as a regular user
- [ ] Write the `systemd` unit + install/uninstall scripts
- [ ] Update `config.py`'s config path for Linux
- [ ] Decide and implement the network-exposure approach (3.3)
- [ ] Re-verify UP/DOWN/STOP live, desk observed, before trusting it
      unattended
- [ ] Update this directory's own `README.md` to reflect what's actually
      true once done (right now it's still a verbatim copy of the Mac one)

## 6. Open questions to decide during the port

- Which user account runs the service (affects 3.2, 3.4, 3.5)?
- Network exposure approach (3.3)?
- ~~Keep Poetry, or is a plain `venv` + `pip` simpler?~~ **Decided: plain
  `venv` + `pip`.** No `pip` module by default on a fresh image, but
  `python3 -m venv` bundles a working one via `ensurepip`, so no
  `apt`/sudo is even needed. `poetry.lock` was removed from this directory
  in favor of `requirements.txt`; `pyproject.toml` is kept as a dependency
  reference but isn't the actual install mechanism here. The real
  deployment venv lives at `~/desk-control/.venv` on the Pi itself, set up
  from the rsynced source files (see section 7's follow-up).

## 7. Empirical testing log (2026-09-13, over SSH to the real Pi)

Ran directly against the actual Pi Zero W to resolve the dependency-risk
questions in 3.1 and 3.4 empirically rather than guessing. Full story,
since some of it is worth remembering if this needs debugging again later:

**Environment confirmed:** Raspbian 13 (trixie), armv6l, 1 CPU, 426MB RAM +
425MB swap, Python 3.13.5, git 2.47.3, BlueZ 5.82 (service active), glibc
2.41. No `pip` or `poetry` preinstalled, but `python3 -m venv` bundles a
working `pip` via `ensurepip` with no `apt`/sudo needed.

**Test 1 -- `fastapi` + `uvicorn[standard]`:** failed the first time with
```
uvloop/loop.c:27:10: fatal error: Python.h: No such file or directory
```
-- not an ARMv6/Rust/glibc problem, just missing Python dev headers (a
totally standard, easy fix: `sudo apt-get install -y python3-dev`). Every
other package in this install (`pydantic-core` included) had already
downloaded as a prebuilt wheel with no issue.

**Test 2 -- retried after `python3-dev`:** past the missing-headers error,
`uvloop` began compiling its bundled `libuv` C library file-by-file
(`-j1`, single-threaded, this chip has one core). This took a genuinely
long time (20+ minutes) and got progressively riskier: at one point a
single `cc1` process alone was using **239MB RAM** (over half the Pi's
total), swap climbed to 261MB used, and the Pi became briefly almost
unreachable over SSH (a `ping` showed 164ms-3.1s round-trip times and
packets arriving out of order -- the system was thrashing, not actually
offline). The compile was still making genuine progress (confirmed via the
process tree, moving through different `libuv` source files each check),
but given `uvloop` isn't actually needed, this was killed rather than
risking an actual OOM crash: `kill -9` on the `cc1`/`gcc`/`pip` process
tree, after which the Pi recovered cleanly within seconds (memory freed,
ping latency back to normal, load average settling).

**Test 3 -- plain `fastapi` + `uvicorn` (no `[standard]`):** installed
cleanly in under 2 minutes, 100% prebuilt wheels, zero compilation. This is
the combination to actually use.

**Test 4 -- `bleak`:** revealed a finding not anticipated by section 3.4:
`dbus-fast` (bleak's Linux/BlueZ backend) is not pure Python -- it has an
optional Cython-accelerated C extension with no armv6l wheel, so it also
needs an on-device compile. Unlike `uvloop`, this went smoothly: about 7
small `.c` files (`message_bus.c`, `service.c`, `signature.c`, `unpack.c`,
`_private/address.c`, `_private/marshaller.c`, `_private/unmarshaller.c`),
each one compiling in a couple of minutes with memory recovering to a
healthy level between files (never dropped below ~28MB free, vs. `uvloop`
which pushed it to near-zero). Total wall time was long only because of
how this was monitored in small increments over the conversation, not
because of continuous heavy compute -- the actual `dbus-fast` build itself
is modest. Finished successfully, and pip cached the built wheel
(`dbus_fast-5.0.22-cp313-cp313-linux_armv6l.whl` in
`~/.cache/pip/wheels/`), so this compile only needs to happen once per Pi;
future installs reuse the cached wheel. `import bleak` and
`import dbus_fast` both confirmed working afterward.

**Bottom line:** the entire dependency stack this project needs installs
and imports successfully on this exact Pi. The only real casualty is
`uvicorn[standard]`'s `uvloop` extra, which isn't needed anyway. No
Starlette rewrite, no alternate BLE library -- `mac/`'s actual code should
port with minimal changes once the process-supervision (3.2), network
(3.3), and BLE-permission (3.4) pieces are done.

**Follow-up session -- real deployment venv + BLE runtime test:** rsynced
the actual source files (`config.py`, `controller.py`, `protocol.py`,
`service.py`, `cli.py`, `discover_device.py`, `pklg_decode.py`,
`pyproject.toml`, `requirements.txt`) to `~/desk-control` on the Pi (not
the throwaway `~/desk-port-test`), created a real venv there, and installed
from `requirements.txt`. Confirmed `dbus-fast`'s wheel cache is shared
across venvs for the same user -- this install reused the previously-built
wheel instantly, no recompile, finished in under 2.5 minutes total.

Then tested the actual BLE runtime end-to-end using our own `controller.py`
unchanged: `discover_device.py` found the desk from the Pi's physical
location (confirming BLE range is fine), reporting its real BlueZ MAC
address (`57:4C:62:F0:49:FF` -- as expected, a real address rather than
macOS's opaque CoreBluetooth UUID) and the same `device_id` (`01065419`)
already known from the Mac side. A follow-up test using `Desk.connect()` +
`Desk.refresh_height()` (the safe STOP-probe) + `Desk.disconnect()`
succeeded fully as a **regular, non-root user with no `setcap`** -- connect,
write, notification receipt, and clean disconnect all worked first try.
(Note: had to briefly stop the Mac's own service during this test, since
the desk can only hold one BLE connection at a time and stops advertising
while connected -- restored afterward.)

This closes out the two biggest remaining unknowns from the original plan:
BLE permissions on Linux are a non-issue on this setup, and `controller.py`
genuinely needs zero changes to work identically over BlueZ instead of
CoreBluetooth.
