"""Local storage for desk presets.

The desk controller itself has no concept of stored presets (confirmed: SIT
and STAND just send an absolute target height). So the app-side height values
have to live somewhere -- here, rather than in the Chinese app.
"""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "desk-control"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULTS = {
    "sit_height_cm": 70.0,
    "stand_height_cm": 110.0,
    # Identifies your specific desk unit among devices advertising the
    # generic name "BLE SPP" (see specs/reverse-engineer.md section 4 --
    # this is the ASCII decoding of the desk's BLE manufacturer data, which
    # appears tied to the QR/serial identifier on the physical unit). Find
    # yours with a PacketLogger capture (log/README.md) if it's not already
    # known. Leave as None to match on name only (fine if you know only one
    # such device is nearby, but risks connecting to the wrong device).
    "device_id": None,
}


def load() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    data = json.loads(CONFIG_PATH.read_text())
    return {**DEFAULTS, **data}


def save(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    merged = {**load(), **config}
    CONFIG_PATH.write_text(json.dumps(merged, indent=2))
