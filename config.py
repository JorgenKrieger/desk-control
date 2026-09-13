"""Local storage for desk presets.

The desk controller itself has no concept of stored presets (confirmed: SIT
and STAND just send an absolute target height). So the app-side height values
have to live somewhere -- here, rather than in the Chinese app.
"""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / "Library" / "Application Support" / "desk-control"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULTS = {
    "sit_height_cm": 70.0,
    "stand_height_cm": 110.0,
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
