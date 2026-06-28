import json
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "state.json"

DEFAULT_STATE = {"target_chat": None, "placeholder": "@태그", "stages": {}}


def load_state() -> dict:
    if not STATE_PATH.exists():
        return json.loads(json.dumps(DEFAULT_STATE))
    with STATE_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
