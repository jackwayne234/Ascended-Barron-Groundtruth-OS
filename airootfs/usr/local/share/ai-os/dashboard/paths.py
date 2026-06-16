import os
import pathlib

HOME = pathlib.Path.home()
WORKSPACE = HOME / "workspace"
AI_OS_LIB_DIR = pathlib.Path("/usr/local/lib/ai-os")
INSTALLER_PATH = "/usr/local/bin/ai-os-install-to-disk"
EMBED = os.environ.get("AI_OS_EMBED") == "1"
TERMINAL_PANE = os.environ.get("AI_OS_TERMINAL_PANE") == "1"
VM = os.environ.get("AI_OS_VM") == "1"
STATE_DIR = HOME / ".local" / "state" / "ai-os"
DASH_DIR = pathlib.Path(__file__).resolve().parent.parent
UPDATE_REPO = "https://github.com/jackwayne234/Ascended-Barron-Groundtruth-OS.git"
INSTALLED_REV_FILE = DASH_DIR / "INSTALLED_REV"
INSTALLED_VERSION_FILE = DASH_DIR / "INSTALLED_VERSION"
CONFIG_DIR = HOME / ".config" / "ai-os"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
UPDATE_BACKUP_DIR = HOME / ".local" / "share" / "ai-os" / "update-backups"
LOG_DIR = (STATE_DIR / "logs") if VM else (DASH_DIR / "logs")
LOG_PATH = LOG_DIR / "interactions.jsonl"
BIG_LOG_DIR = HOME / ".local" / "share" / "ai-os" / "big-log"
BIG_LOG_PATH = BIG_LOG_DIR / "logs" / "ai-big-log.jsonl"
SESSIONS_DIR = BIG_LOG_DIR / "sessions"
