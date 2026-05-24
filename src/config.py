import json
import os
from pathlib import Path

_AUTHORS = None


def _load():
    global _AUTHORS
    if _AUTHORS is not None:
        return _AUTHORS
    env_val = os.environ.get("NOTE_AUTHORS")
    if env_val:
        _AUTHORS = json.loads(env_val)
    else:
        path = Path(__file__).parent.parent / "config" / "authors.json"
        with open(path, encoding="utf-8") as f:
            _AUTHORS = json.load(f)
    return _AUTHORS


NOTE_AUTHORS = _load()
