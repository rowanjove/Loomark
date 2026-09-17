import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_DATA_DIR = DATA_DIR / "projects"
DB_PATH = DATA_DIR / "loomark.db"
PLUGINS_DIR = BASE_DIR / "plugins"

# Ensure essential directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = DATA_DIR / "settings.json"

def load_settings() -> dict:
    import json
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def deep_merge(target: dict, source: dict) -> dict:
    """Recursively merge source into target dictionary, ignoring None values."""
    for k, v in source.items():
        if v is None:
            continue
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            deep_merge(target[k], v)
        else:
            target[k] = v
    return target

def save_settings(data: dict) -> None:
    import json
    current = load_settings()
    deep_merge(current, data)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)

DEFAULT_PORT = int(os.getenv("LOOMARK_PORT", "8765"))
DEFAULT_HOST = os.getenv("LOOMARK_HOST", "127.0.0.1")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# Concurrency Presets
CONCURRENCY_PRESETS = {
    "gentle": {
        "max_concurrent": 3,
        "domain_concurrent": 1,
        "domain_delay_ms": 1500,
        "timeout_seconds": 30,
    },
    "balanced": {
        "max_concurrent": 10,
        "domain_concurrent": 3,
        "domain_delay_ms": 500,
        "timeout_seconds": 20,
    },
    "fast": {
        "max_concurrent": 25,
        "domain_concurrent": 6,
        "domain_delay_ms": 100,
        "timeout_seconds": 15,
    }
}
