# Porting desk-control to a Raspberry Pi Zero W

**Status:** Planning. The code in this directory is currently an unmodified
copy of `mac/` -- nothing has been changed yet. This document is the plan
for what needs to change and why, to be worked through before/while doing
the actual port.

**Target hardware:** original Raspberry Pi Zero W (single-core ARM11,
ARMv6, 1GHz, 512MB RAM) -- *not* the newer Pi Zero 2 W (quad-core ARMv8).
This distinction matters a lot for package compatibility (see below).

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

### 3.1 Web framework -- likely the biggest blocker

`mac/service.py` uses FastAPI (which requires Pydantic v2) and
`uvicorn[standard]` (which pulls in `uvloop`/`httptools`). Pydantic v2's
core (`pydantic-core`) is written in Rust; `uvloop`/`httptools` are C
extensions. None of these reliably have prebuilt wheels for ARMv6:

- ARMv6 isn't a standard "manylinux" wheel target most packages publish
  binaries for, so installing likely means compiling from source.
- Confirmed real-world reports of `pydantic-core` specifically requiring a
  newer glibc (2.33+) than what ships on Raspberry Pi OS for this chip
  (2.31) -- meaning even a wheel, if one existed, may not run.
- Compiling `pydantic-core` needs a Rust toolchain, which is a rough
  proposition on 512MB RAM / one 1GHz core (slow at best, may fail on
  memory during compilation).

**Recommended fix:** drop FastAPI and Pydantic. Use `Starlette` directly
(the pure-Python framework FastAPI itself is built on -- no Rust core) and
parse/validate the small JSON request bodies by hand instead of via Pydantic
models (our API surface is tiny: a handful of simple fields, not worth a
validation library). Use plain `uvicorn` (no `[standard]` extra) -- falls
back to asyncio's default event loop and the pure-Python `h11` HTTP parser,
which is functionally identical at our scale (a handful of requests per
minute).

**Alternative considered:** try installing as-is first and see if Raspberry
Pi's own prebuilt-wheel mirror (piwheels) has something usable that a
generic PyPI/wheel search didn't surface. Worth a quick empirical check
before committing to the rewrite, but don't assume it'll work -- have the
Starlette rewrite as the fallback plan, not a maybe.

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

### 3.4 BLE permissions on Linux

Unlike macOS (where CoreBluetooth access is gated by a one-time system
permission prompt), `bleak`'s Linux backend (via BlueZ/`dbus-fast`) commonly
needs either running as root or granting the Python binary explicit
capabilities:

```bash
sudo setcap 'cap_net_raw,cap_net_admin+eip' "$(readlink -f "$(command -v python3)")"
```

(or run the systemd unit as root, simpler but coarser). This is a common
stumbling block for anyone new to Linux BLE work and should be tested and
documented explicitly, not assumed to "just work" the way it does on macOS.

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

- [ ] Flash Raspberry Pi OS Lite (32-bit -- this chip can't run 64-bit at
      all) and get SSH access
- [ ] Confirm the system Python version satisfies `requires-python >=3.11`
- [ ] Try a plain `pip install fastapi pydantic uvicorn[standard]` to see
      empirically whether piwheels saves us the rewrite (see 3.1) -- don't
      spend more than a few minutes on this before falling back to the
      Starlette rewrite
- [ ] Rewrite `service.py` (Starlette instead of FastAPI/Pydantic) if
      needed
- [ ] Update `pyproject.toml`/`poetry.lock` for this directory accordingly
- [ ] `setcap` (or run-as-root) for BLE permissions
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
- Keep Poetry, or is a plain `venv` + `pip` simpler on such constrained
  hardware? (Poetry itself is pure Python and should be fine, but worth
  reconsidering given how much this port is already about minimizing
  dependency weight.)
