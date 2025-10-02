import json
from pathlib import Path

DEFAULTS = {
    "status": "online",
    "custom_status": "github:ZeleMarsh7mary/@zeleresia",
    "heartbeat_interval": 50,
    "auto_join_voice": False,
    "voice_channel_id": ""
}

def load_config(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = DEFAULTS.copy()
        save_config(path, data)
    changed = False
    for k, v in DEFAULTS.items():
        if k not in data:
            data[k] = v
            changed = True
    if changed:
        save_config(path, data)
    return data

def save_config(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
