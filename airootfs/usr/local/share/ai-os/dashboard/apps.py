import json
import os
import pathlib
import shlex
import shutil

from dashboard.logging_utils import log_file_write
from dashboard.paths import DASH_DIR, HOME, STATE_DIR, VM

APPS_JSON = (STATE_DIR / "apps.json") if VM else (DASH_DIR / "apps.json")
DESKTOP_DIR = HOME / "Desktop"
MIN_APP_SQUARES = 3


def parse_desktop_file(path):
    """Read Name/Exec from a .desktop launcher. Returns dict or None."""
    name = exec_line = None
    in_entry = False
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("["):
                in_entry = (line == "[Desktop Entry]")
            elif in_entry and line.startswith("Name=") and name is None:
                name = line[5:].strip()
            elif in_entry and line.startswith("Exec=") and exec_line is None:
                exec_line = line[5:].strip()
    except Exception:
        return None
    if not name or not exec_line:
        return None
    return {"name": name, "exec": exec_line, "source": str(path)}


def scan_desktop_apps():
    """Every .desktop icon on the Desktop = an app that can go in a square."""
    apps = []
    for p in sorted(DESKTOP_DIR.glob("*.desktop")):
        app = parse_desktop_file(p)
        if app:
            apps.append(app)
    return apps


def _default_app_slots():
    cal = parse_desktop_file(DESKTOP_DIR / "Appointment_Calendar.desktop")
    if cal:
        return [cal]
    if VM:
        return scan_desktop_apps()
    return []


def load_app_state():
    try:
        data = json.loads(APPS_JSON.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    slots = data.get("slots")
    if not isinstance(slots, list):
        slots = _default_app_slots()
    archived = data.get("archived_builtins")
    if not isinstance(archived, list):
        archived = []
    clean_archived = []
    for key in archived:
        if isinstance(key, str) and key not in clean_archived:
            clean_archived.append(key)
    return {"slots": slots, "archived_builtins": clean_archived}


def save_app_state(state):
    try:
        APPS_JSON.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    slots = state.get("slots", []) if isinstance(state, dict) else []
    archived = state.get("archived_builtins", []) if isinstance(state, dict) else []
    APPS_JSON.write_text(json.dumps({"slots": slots, "archived_builtins": archived}, indent=2) + "\n",
                         encoding="utf-8")
    log_file_write(APPS_JSON, "app state saved")


def load_app_slots():
    return load_app_state()["slots"]


def load_archived_builtins():
    return load_app_state()["archived_builtins"]


def save_app_slots(slots):
    state = load_app_state()
    state["slots"] = slots
    save_app_state(state)


def save_archived_builtins(keys):
    state = load_app_state()
    clean = []
    for key in keys:
        if isinstance(key, str) and key not in clean:
            clean.append(key)
    state["archived_builtins"] = clean
    save_app_state(state)


def app_exec_tokens(app):
    """Tokens to run a placed app (its Exec line minus %-field codes). In VM
    mode, if the seeded entry points at google-chrome-stable but that isn't
    installed and chromium is, substitute chromium."""
    tokens = [t for t in shlex.split(app["exec"]) if not t.startswith("%")]
    if VM and tokens:
        exe = tokens[0]
        base = pathlib.Path(exe).name
        if base in ("google-chrome-stable", "google-chrome") and not shutil.which(exe):
            if shutil.which("chromium"):
                tokens[0] = "chromium"
    return tokens


def app_available(app):
    tokens = app_exec_tokens(app)
    if not tokens:
        return None
    exe = tokens[0]
    if (os.path.isabs(exe) and os.path.exists(exe)) or shutil.which(exe):
        return tokens
    return None


def app_search_text(app):
    try:
        parts = [app.get("name", ""), *app_exec_tokens(app)]
    except Exception:
        parts = [app.get("name", "")]
    return " ".join(str(p) for p in parts).lower()


def is_browser_app(app):
    text = app_search_text(app)
    return any(hint in text for hint in ("chromium", "chrome", "firefox", "browser"))


def app_window_match_hints(app):
    text = app_search_text(app)
    hints = []
    if "chromium" in text:
        hints.append("chromium")
    if "chrome" in text:
        hints.append("chrome")
    if "firefox" in text:
        hints.append("firefox")
    if "browser" in text and not hints:
        hints.append("browser")
    name = app.get("name", "").strip().lower()
    if name:
        hints.append(name)
    clean = []
    for hint in hints:
        if hint and hint not in clean:
            clean.append(hint)
    return clean
