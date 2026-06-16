import json

from dashboard.paths import SETTINGS_FILE


def load_settings():
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(s):
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(s, indent=2, sort_keys=True), encoding="utf-8")
        return True
    except Exception:
        return False


def get_setting(key, default=None):
    return load_settings().get(key, default)


def set_setting(key, value):
    s = load_settings()
    s[key] = value
    save_settings(s)
