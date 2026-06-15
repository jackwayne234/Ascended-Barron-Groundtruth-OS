#!/usr/bin/env python3
"""AI OS Dashboard — Ascended Barron seed.

One canonical dashboard. It runs directly on the host for fast iteration and the
exact same file is baked into the AI OS Arch ISO so the VM experience matches.

Design notes:
- Left sidebar = app squares; right pane = the working environment where every
  app, the Eisenhower matrix, and AI/terminal sessions open embedded.
- Footer holds the machine controls: volume slider, Restart, Power Off.
"""
import os
import re
import json
import time
import uuid
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import datetime
import pathlib
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

# ---------- palette ----------
BG = "#050b18"      # app background
HEAD = "#08111f"    # header / bars
PANEL = "#0f1b2d"   # cards / panels
INK = "#ffffff"
SUB = "#60a5fa"
BODY = "#93c5fd"
GOOD = "#a7f3d0"
ACCENT = "#2563eb"
ACCENT2 = "#16a34a"
MUTED = "#64748b"
AMBER = "#d97706"   # "update available" highlight on the Update OS tile

FONT = "DejaVu Sans"
HOME = pathlib.Path.home()
WORKSPACE = HOME / "workspace"
WORK_ZONE_TITLE = ""   # default: no title bar; specific screens (Settings, etc.) override
# Where the AI OS logging module (ai_big_log) is installed. Ships with the OS;
# the import below fails soft if it is absent (training-data buttons then no-op).
AI_OS_LIB_DIR = pathlib.Path("/usr/local/lib/ai-os")
# Install-to-disk helper (C10). Present on the live/installed OS, absent on a
# dev host — the dashboard hides the Install button when it's missing.
INSTALLER_PATH = "/usr/local/bin/ai-os-install-to-disk"

# In-pane window embedding (X window swallowing). OFF by default on the host:
# fighting GNOME/Wayland for keyboard focus made typing flaky (Chrome,
# 2026-06-06), so apps and AI sessions open as normal windows instead. The
# machinery stays for the Arch ISO, where the dashboard owns the whole
# graphical session and there is no compositor to fight — set AI_OS_EMBED=1.
EMBED = os.environ.get("AI_OS_EMBED") == "1"
TERMINAL_PANE = os.environ.get("AI_OS_TERMINAL_PANE") == "1"

# VM mode = the dashboard is running off the baked Arch ISO as root, where the
# dashboard dir lives on a read-only squashfs (/usr/local/share/ai-os/) and the
# host-only tooling (the user's AI CLI, GNOME volume stack) is absent. In VM mode we
# fail soft on missing tools and route every write to a writable state dir
# instead of the (read-only) dashboard dir. The host path is completely
# untouched (VM is False there).
VM = os.environ.get("AI_OS_VM") == "1"

# Writable state dir for VM mode (the dashboard dir is read-only squashfs there).
# On the host this is unused — apps.json + the fallback log stay beside the
# script exactly as before, so host behavior is byte-for-byte identical.
STATE_DIR = HOME / ".local" / "state" / "ai-os"

# ---------- interaction logger (training data) ----------
# Every user action, AI response, and file change is appended as a first-class
# record to a single local "big log" — a per-user training log that is
# independent of which AI you use. Records carry record_id/record_type so the
# big log's own `validate` command accepts them, and detail/data fields go
# through the big log's Redactor (secrets/PII scrubbed before they hit disk).
# The log lives in a fixed per-user data dir (no hard-coded project folder).
SESSION_ID = uuid.uuid4().hex[:8]
DASH_DIR = pathlib.Path(__file__).resolve().parent
# Self-update: the public repo the "Update OS" tile pulls from, and the files
# that record the installed version (written by ai-os-update, stamped at build).
UPDATE_REPO = "https://github.com/jackwayne234/Ascended-Barron-Groundtruth-OS.git"
INSTALLED_REV_FILE = DASH_DIR / "INSTALLED_REV"          # full commit SHA
INSTALLED_VERSION_FILE = DASH_DIR / "INSTALLED_VERSION"  # release tag, e.g. v1.1.0 (Q54)
# User settings (update-check opt-out, banner-dismiss state, …) live here — user
# data the updater never touches (Q29).
CONFIG_DIR = HOME / ".config" / "ai-os"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
# Where ai-os-update saves the pre-update backups (undo is offered when present).
UPDATE_BACKUP_DIR = HOME / ".local" / "share" / "ai-os" / "update-backups"
# In VM mode DASH_DIR is read-only squashfs, so the fallback log lives in the
# writable state dir instead; on the host it stays beside the script (unchanged).
LOG_DIR = (STATE_DIR / "logs") if VM else (DASH_DIR / "logs")
LOG_PATH = LOG_DIR / "interactions.jsonl"  # legacy history + fallback only
BIG_LOG_DIR = HOME / ".local" / "share" / "ai-os" / "big-log"
BIG_LOG_PATH = BIG_LOG_DIR / "logs" / "ai-big-log.jsonl"
SESSIONS_DIR = BIG_LOG_DIR / "sessions"  # raw AI terminal transcripts (any AI)
EVENTS = []  # recent records this session; the Logs panel also reads the file

try:  # reuse the big log's redaction rules so dashboard events match its policy
    import sys as _sys
    _sys.path.insert(0, str(AI_OS_LIB_DIR))
    from ai_big_log.logger import Redactor as _Redactor
    _REDACTOR = _Redactor()
except Exception:
    _REDACTOR = None


def _redact(value):
    if _REDACTOR is None:
        return value
    try:
        return _REDACTOR.redact(value)[0]
    except Exception:
        return value


def log_event(action, detail="", kind="system", **data):
    """Append one structured event. kind = user | ai | file | system."""
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec = {
        "record_id": f"dashboard-{SESSION_ID}-{uuid.uuid4().hex[:12]}",
        "record_type": "dashboard_event",
        "captured_at": ts,
        "session": SESSION_ID,
        "kind": kind,
        "action": action,
    }
    if detail:
        rec["detail"] = _redact(detail)
    if data:
        rec["data"] = _redact(data)
    EVENTS.append(rec)
    line = json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n"
    try:  # primary: route into the AI big log (append-only, O_APPEND is atomic)
        BIG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with BIG_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        try:  # fallback: never lose an event — keep it locally instead
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass
    return rec


def log_file_write(path, note=""):
    name = pathlib.Path(path).name
    log_event("file_write", f"wrote {name}" + (f" — {note}" if note else ""),
              kind="file", path=str(path))


def biglog_health_summary(max_age_seconds=300):
    """Small tester-facing BigLog health check for the AI OS dashboard.

    This does not replace the desktop cron/watchdog. It tells the person testing
    the booted OS whether dashboard events are landing in the local training log.
    """
    path = pathlib.Path(BIG_LOG_PATH)
    fallback = pathlib.Path(LOG_PATH)
    chosen = path if path.exists() else fallback if fallback.exists() else path
    if not chosen.exists():
        return {"state": "NOT RECORDING", "color": "#f87171", "records": 0,
                "last_action": "none", "age_seconds": None, "path": str(chosen)}
    try:
        stat = chosen.stat()
        age = max(0, int(time.time() - stat.st_mtime))
        records = 0
        last = None
        bad = 0
        with chosen.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    records += 1
                    last = rec
                except Exception:
                    bad += 1
        if bad:
            state, color = "LOG ERROR", "#f87171"
        elif chosen == fallback and chosen != path:
            state, color = "FALLBACK ONLY", "#facc15"
        elif age > max_age_seconds:
            state, color = "STALE", "#facc15"
        else:
            state, color = "RECORDING", GOOD
        return {"state": state, "color": color, "records": records,
                "last_action": (last or {}).get("action", "none"),
                "age_seconds": age, "path": str(chosen), "bad_lines": bad}
    except Exception as e:
        return {"state": "LOG ERROR", "color": "#f87171", "records": 0,
                "last_action": str(e)[:80], "age_seconds": None, "path": str(chosen)}


def format_biglog_badge(summary):
    records = summary.get("records", 0)
    return f"Local Logs: {records} lines"


# ---------- Eisenhower task store ----------
# Reads/writes the SAME tasks.json as the user's existing Eisenhower app when
# it is present, so the dashboard shows his real to-do list. Falls back to a
# local file (and a seed task) so it still works inside the minimal ISO.
EISEN_APP_DIR = WORKSPACE / "Eisenhower priority matrix to do list"

# (key, short title, subtitle, accent color) — matches the existing app's quadrants.
QUADS = [
    ("do_first", "Do First", "Urgent + Important", "#7f1d1d"),
    ("schedule", "Schedule", "Important, Not Urgent", "#166534"),
    ("delegate", "Delegate", "Urgent, Not Important", "#92400e"),
    ("delete_later", "Low Priority", "Not Urgent, Not Important", "#334155"),
]


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ---------- battery indicator ----------
def read_battery_status(base="/sys/class/power_supply"):
    """Return (capacity:int|None, status:str) for the first laptop battery."""
    base = pathlib.Path(base)
    try:
        supplies = sorted(base.glob("*"))
    except Exception:
        return None, "Unknown"
    for supply in supplies:
        try:
            typ = (supply / "type").read_text(encoding="utf-8").strip().lower()
        except Exception:
            continue
        if typ != "battery":
            continue
        try:
            raw = (supply / "capacity").read_text(encoding="utf-8").strip()
            capacity = max(0, min(100, int(raw)))
        except Exception:
            capacity = None
        try:
            status = (supply / "status").read_text(encoding="utf-8").strip()
        except Exception:
            status = "Unknown"
        return capacity, status
    return None, "Unknown"


def format_battery_indicator(capacity, status="Unknown"):
    """Small header text: state + percent (plain text — emoji render hollow on
    the ISO with no emoji font). Empty string on desktops/no battery."""
    if capacity is None:
        return ""
    status_l = (status or "").lower()
    if (("charging" in status_l and "discharging" not in status_l)
            or "full" in status_l):
        return f"Charging {capacity}%"
    return f"Battery {capacity}%"


# ---------- resource monitor ----------
def read_cpu_times():
    """Return aggregate CPU counters from /proc/stat, or None if unavailable."""
    try:
        parts = pathlib.Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()[1:]
        vals = [int(x) for x in parts]
        total = sum(vals)
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        return total, idle
    except Exception:
        return None


def cpu_percent_from(prev, cur):
    if not prev or not cur:
        return None
    total_delta = cur[0] - prev[0]
    idle_delta = cur[1] - prev[1]
    if total_delta <= 0:
        return None
    return max(0, min(100, round((1 - idle_delta / total_delta) * 100)))


def read_memory_status():
    """Return memory status focused on what matters to a user: available RAM.

    Linux live ISOs can show scary "used" RAM because tmpfs/cache/overlay live
    in memory. Available RAM is the clearer number for the user.
    """
    try:
        vals = {}
        for line in pathlib.Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", 1)
            vals[key] = int(raw.strip().split()[0])
        total = vals.get("MemTotal")
        avail = vals.get("MemAvailable")
        if not total or avail is None:
            return None
        used_pct = max(0, min(100, round((1 - avail / total) * 100)))
        avail_gib = avail / (1024 * 1024)
        total_gib = total / (1024 * 1024)
        return {"used_pct": used_pct, "avail_gib": avail_gib, "total_gib": total_gib}
    except Exception:
        return None


def read_disk_percent(path="/"):
    try:
        usage = shutil.disk_usage(path)
        if usage.total <= 0:
            return None
        return max(0, min(100, round((usage.used / usage.total) * 100)))
    except Exception:
        return None


def resource_color(cpu, mem_status, disk, battery_cap):
    vals = [v for v in (cpu, disk) if isinstance(v, int)]
    if isinstance(mem_status, dict):
        vals.append(mem_status.get("used_pct", 0))
    if battery_cap is not None:
        vals.append(100 - battery_cap)  # low battery becomes attention.
    if any(v >= 90 for v in vals) or (battery_cap is not None and battery_cap <= 15):
        return "#f87171"  # red
    if any(v >= 75 for v in vals) or (battery_cap is not None and battery_cap <= 30):
        return "#facc15"  # yellow
    return GOOD


def fmt_pct(label, value):
    return f"{label} --" if value is None else f"{label} {value}%"


def fmt_ram_available(mem_status):
    if not isinstance(mem_status, dict):
        return "RAM avail --"
    return f"RAM avail {mem_status['avail_gib']:.1f}G"


def tasks_path():
    real = EISEN_APP_DIR / "tasks.json"
    if real.exists():
        return real
    return pathlib.Path(__file__).resolve().parent / "tasks.json"


def load_tasks():
    p = tasks_path()
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            d.setdefault("tasks", [])
            return d
        except Exception:
            pass
    return {"schema_version": 1, "tasks": [
        {"id": str(uuid.uuid4()), "title": "Open Terminal in this project folder",
         "quadrant": "do_first", "completed": False, "created_at": _now_iso()},
    ]}


def eisen_done_tasks(data):
    """Return completed Eisenhower tasks, newest completed first."""
    done = [t for t in data.get("tasks", []) if t.get("completed")]
    return sorted(done, key=lambda t: t.get("completed_at") or t.get("updated_at") or "", reverse=True)


def restore_eisen_done_task(data, task_id):
    """Restore a completed task to active status and move it to the top."""
    tasks = data.setdefault("tasks", [])
    for idx, task in enumerate(tasks):
        if task.get("id") == task_id and task.get("completed"):
            task["completed"] = False
            task["completed_at"] = None
            task["updated_at"] = _now_iso()
            tasks.pop(idx)
            tasks.insert(0, task)
            return task
    return None


def save_tasks(data):
    data["updated_at"] = _now_iso()
    p = tasks_path()
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)
    log_file_write(p, f"{len(data.get('tasks', []))} tasks")


# ---- Task project folder helpers ----
def safe_folder_name(title, tid=""):
    cleaned = title.replace("/", " ").replace("\\", " ")
    cleaned = "".join(ch for ch in cleaned if ch.isprintable())
    cleaned = " ".join(cleaned.split()).strip(" .")
    if not cleaned:
        cleaned = f"task-{(tid or 'untitled')[:8]}"
    return cleaned[:120]


def project_folder_for_task(task):
    return WORKSPACE / safe_folder_name(task.get("title", ""), task.get("id", ""))



def build_agents_md(task, folder):
    return (f"# Project Helper Rules\n\n"
            f"This folder is an AI OS project connected to an Eisenhower Matrix to-do item.\n\n"
            f"Task title: {task.get('title', 'Untitled')}\n"
            f"Task id: {task.get('id', 'unknown')}\n"
            f"Quadrant: {task.get('quadrant', 'unknown')}\n"
            f"Project folder: {folder}\n\n"
            "START HERE — every session in this folder:\n"
            "1. Read `ground-truth.md` in this folder FIRST.\n"
            "2. Follow its 'AI Start Instructions' exactly.\n"
            "3. Treat ground-truth.md as the source of truth. Record questions, answers, locked\n"
            "   decisions, and progress back into that file.\n"
            "4. Do not begin implementation until ground-truth.md shows permission was granted.\n"
            "5. Keep answers short and practical.\n")


def build_ground_truth(task, folder):
    """Generic ground-truth.md matching the workspace template (see other projects)."""
    title = task.get("title", "Untitled")
    quad = task.get("quadrant", "unknown")
    today = datetime.date.today().isoformat()
    return f"""# {title} — Ground Truth

## Purpose of This File

A `ground-truth.md` file is the project’s source of truth. It tells the AI what the project is, what decisions have already been made, what still needs to be asked, what progress has happened, and whether the AI has permission to start working. The point is to stop the AI from guessing, restarting, forgetting context, or building before you’ve approved the direction.

## AI Start Instructions

When the AI is working in this folder, it should read this file first and follow these rules:

1. If the desired outcome is missing, ask: **“What do you want the desired outcome of this project to be?”**
2. If the 25-question planning pass is incomplete, ask the next missing planning question **one question at a time**.
3. Each planning question should use short multiple-choice options when useful, with one option clearly marked **recommended**.
4. Record each planning question, options offered, recommendation, user answer, and locked decision in this file.
5. After 25 questions are answered, summarize what is known, list remaining gaps, and ask whether the information is enough.
6. If the information is enough, break the project into many small execution chunks before asking for work permission. Each chunk should be small enough to run, verify, and log independently.
7. Before doing manual work in any chunk, look for existing scripts, commands, CLIs, Makefiles, tests, or automation that can do the work deterministically. Prefer script/tool execution over AI doing repetitive work directly.
8. Record the chunk plan in this file, including chunk number, goal, likely files/scripts/tools, verification step, and status.
9. Before starting work, ask: **“Do I have your permission to start working from this ground truth and chunk plan?”**
10. Do not begin implementation, research, file changes, or project work until the user gives permission.
11. Log meaningful progress in the Progress Log section.

## Desired Outcome

_Not answered yet._

## Planning Status

- Desired outcome: Not answered yet.
- 25-question planning pass: Not started.
- Enough-information checkpoint: Not completed.
- Chunk plan: Not created yet.
- Permission to start work: Not granted yet.

## Planning Q&A Ledger

### Desired Outcome Question

**Question:** What do you want the desired outcome of this project to be?

**User answer:** Not answered yet.

**Locked decision:** Not locked yet.

## Enough-Information Checkpoint

_Not reached yet. After 25 planning questions, the AI should summarize what is known, list remaining gaps, and ask whether the information is enough._

## Chunk Plan

_Not created yet. After the enough-information checkpoint is satisfied, the AI should break the project into many small execution chunks before asking permission to start. Each chunk should include:_

- Chunk number and goal
- Likely files, scripts, commands, CLIs, or tools involved
- Whether an existing script/tool should be used or a new script should be created
- Verification step
- Status: pending, in progress, complete, blocked, or deferred

## Permission to Start

_Not granted yet. The AI should ask: “Do I have your permission to start working from this ground truth and chunk plan?”_

## Progress Log

### {today}
- Created this `ground-truth.md` automatically when the task project folder was opened from the AI OS dashboard.
- Installed the reusable template: desired outcome first, planning questions, enough-information checkpoint, small chunk plan, script-first execution preference, and explicit permission before work starts.
- Source task title: `{title}`.
- Source task quadrant: `{quad}`.
"""


def ensure_ground_truth(task, folder):
    """Write ground-truth.md only if one is not already there (never overwrite real progress)."""
    gt = folder / "ground-truth.md"
    if not gt.exists():
        gt.write_text(build_ground_truth(task, folder), encoding="utf-8")
        log_file_write(gt, "ground-truth.md created")
    return gt


def x11_env():
    """Env that forces apps onto X11 (Qt/GTK/SDL): on this Wayland desktop
    native-Wayland windows are invisible to xdotool, so they can't be embedded
    into the right pane. Tk apps always use XWayland — unaffected."""
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "xcb"
    env["GDK_BACKEND"] = "x11"
    env["SDL_VIDEODRIVER"] = "x11"
    return env


def xterm_args(shell_command, into=None, geometry="110x32"):
    """Readable xterm fallback only.

    Real laptop testing showed stock xterm does not provide reliable normal
    Ctrl+Shift+C / Ctrl+Shift+V behavior here. Prefer lxterminal when present;
    keep xterm only as a last-resort fallback.
    """
    args = ["xterm"]
    if into is not None:
        args += ["-into", str(into)]
    args += [
        "-bg", "#020912", "-fg", "#a7f3d0",
        "-fa", "DejaVu Sans Mono", "-fs", "12",
        "-geometry", geometry,
        "-xrm", "XTerm*selectToClipboard: true",
        "-e", "bash", "-lc", shell_command,
    ]
    return args


def find_terminal(shell_command):
    candidates = [
        # AI OS laptop choice: lxterminal is a tiny VTE/GTK terminal with normal
        # desktop copy/paste behavior. Real xterm tests wrote ^C/^V instead.
        ("lxterminal", ["lxterminal", "--title=Ascended Barron", "-e",
                        f"bash -lc {shlex.quote(shell_command)}"]),
        # Host/developer fallbacks. ptyxis -s = its own instance, not just the
        # running --gapplication-service one.
        ("ptyxis", ["ptyxis", "-s", "--", "bash", "-lc", shell_command]),
        ("x-terminal-emulator", ["x-terminal-emulator", "-e", "bash", "-lc", shell_command]),
        ("gnome-terminal", ["gnome-terminal", "--", "bash", "-lc", shell_command]),
        ("konsole", ["konsole", "-e", "bash", "-lc", shell_command]),
        ("xfce4-terminal", ["xfce4-terminal", "--command", f"bash -lc {shlex.quote(shell_command)}"]),
        ("mate-terminal", ["mate-terminal", "-e", f"bash -lc {shlex.quote(shell_command)}"]),
        # xterm fallback only.
        ("xterm", xterm_args(shell_command)),
    ]
    for exe, args in candidates:
        if shutil.which(exe):
            return args
    return None


def wifi_indicator():
    """(text, color) for the header WiFi icon. Read-only status via nmcli — no
    geolocation, just the connection state + SSID + signal of the active link."""
    if not shutil.which("nmcli"):
        return ("Wi-Fi —", MUTED)
    try:
        out = subprocess.check_output(["nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "dev"],
                                      text=True, timeout=4, stderr=subprocess.DEVNULL)
    except Exception:
        return ("Wi-Fi ?", MUTED)
    rows = [l.split(":") for l in out.splitlines() if l]
    wifi = next((r for r in rows if r and r[0] == "wifi"), None)
    if wifi and len(wifi) >= 2 and wifi[1] == "connected":
        # Plain text only (no emoji/bars — they render hollow and the bars also
        # jittered the header). Just a steady network name.
        ssid = (wifi[2] if len(wifi) > 2 and wifi[2] else "Wi-Fi")[:9]
        return (f"Wi-Fi {ssid}", GOOD)
    eth = next((r for r in rows if r and r[0] == "ethernet"), None)
    if eth and len(eth) >= 2 and eth[1] == "connected":
        return ("Wired", GOOD)
    return ("No Wi-Fi", "#f59e0b")  # amber — click to set up


# ---------- weather (powered by the user's prebuilt desktop weather app) ----------
import threading
import importlib.util

WEATHER_APP_DIR = WORKSPACE / "desktop weather app"
WEATHER_LAUNCH = WEATHER_APP_DIR / "launch.sh"


def load_weather_app():
    """Import the real weather app as a module so the dashboard's weather
    section uses the SAME engine, config.json, palette, and colored vector
    symbols as the desktop widget — one source of truth, no duplicate code."""
    spec = importlib.util.spec_from_file_location(
        "weather_app", WEATHER_APP_DIR / "weather_app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    WAPP = load_weather_app()
except Exception:
    WAPP = None


# ---------- app squares ----------
# The Apps grid squares hold REAL apps. Every .desktop icon on the Desktop (the
# apps the user already built) can be placed into a square; new apps
# can be added once their icon lands on the Desktop. Placements persist in apps.json.
# In VM mode the dashboard dir is read-only squashfs, so persisted app-square
# placements live in the writable state dir; on the host apps.json stays beside
# the script exactly as before (host behavior unchanged).
APPS_JSON = (STATE_DIR / "apps.json") if VM else (DASH_DIR / "apps.json")
DESKTOP_DIR = HOME / "Desktop"
MIN_APP_SQUARES = 3  # pad with "+ Add App" squares so the sketch layout holds


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
    # First run: seed with the Appointment Calendar icon if it's on the Desktop.
    cal = parse_desktop_file(DESKTOP_DIR / "Appointment_Calendar.desktop")
    if cal:
        return [cal]
    # Fresh VM: pre-place every bundled Desktop icon (the ISO ships e.g. the
    # Chromium browser square) so the grid isn't empty on first boot. Host
    # behavior is unchanged (VM is False there).
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
    try:  # state dir may not exist yet in VM mode (read-only squashfs dashboard dir)
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
    installed and chromium is, substitute chromium (his cloned-profile seed
    targets Chrome, which won't exist in the minimal ISO)."""
    tokens = [t for t in shlex.split(app["exec"]) if not t.startswith("%")]
    if VM and tokens:
        exe = tokens[0]
        base = pathlib.Path(exe).name
        if base in ("google-chrome-stable", "google-chrome") and not shutil.which(exe):
            if shutil.which("chromium"):
                tokens[0] = "chromium"
    return tokens


def app_available(app):
    """Friendly presence check: is this app's launcher binary actually on this
    system? Returns the resolved tokens if so, else None. Avoids a crash/error
    dialog when a seeded entry (e.g. Chrome with a cloned profile) isn't here."""
    tokens = app_exec_tokens(app)
    if not tokens:
        return None
    exe = tokens[0]
    # Absolute path that exists, or a name resolvable on PATH.
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


def launch_app(app):
    """Launch a placed app exactly like double-clicking its Desktop icon,
    forced onto X11 so it can embed in the right pane (hit with Network IT
    Troubleshooter, a PyQt app, 2026-06-06)."""
    tokens = app_exec_tokens(app)
    return subprocess.Popen(tokens, start_new_session=True, env=x11_env())


def list_x_windows():
    """Visible top-level X window ids (used to spot an app's new window)."""
    try:
        out = subprocess.check_output(["xdotool", "search", "--onlyvisible", ""],
                                      text=True, stderr=subprocess.DEVNULL, timeout=3)
        return {ln.strip() for ln in out.splitlines() if ln.strip()}
    except Exception:
        return set()


def window_class(wid):
    """WM_CLASS of an X window, lowercased ('' if unknown)."""
    try:
        out = subprocess.check_output(["xprop", "-id", wid, "WM_CLASS"], text=True,
                                      stderr=subprocess.DEVNULL, timeout=2)
        return out.lower()
    except Exception:
        return ""


def embeddable(wid):
    """Never adopt the window manager's own windows (GNOME's frame windows
    share the app's title; stealing one breaks the whole desktop)."""
    cls = window_class(wid)
    return "mutter" not in cls and "gnome-shell" not in cls


# ---------- settings (user prefs; updater never touches these) — Q29 ----------
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


# ---------- version helpers (self-update) — Q30/Q54 ---------------------------
def installed_version_str():
    """The friendly release name (e.g. v1.1.0). Falls back to a short commit or
    'unknown' on older/dev builds that predate the version marker."""
    try:
        v = INSTALLED_VERSION_FILE.read_text(encoding="utf-8").strip()
        if v:
            return v
    except Exception:
        pass
    try:
        rev = INSTALLED_REV_FILE.read_text(encoding="utf-8").strip().split()[0]
        if rev:
            return rev[:7]
    except Exception:
        pass
    return "unknown"


def parse_version(s):
    """'v1.2.3' -> (1,2,3); None if it isn't a plain release tag (e.g. dev-…)."""
    if not s:
        return None
    m = re.match(r"^v(\d+)\.(\d+)\.(\d+)$", s.strip())
    return tuple(int(g) for g in m.groups()) if m else None


def latest_remote_release():
    """Highest published release tag (vX.Y.Z) on GitHub, or None. Pre-release
    tags (e.g. -rc1) are ignored. One small, quiet network call (Q1)."""
    try:
        out = subprocess.check_output(
            ["git", "ls-remote", "--tags", "--refs", UPDATE_REPO],
            timeout=20, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    best = None
    for line in out.splitlines():
        ref = line.split("refs/tags/")[-1].strip() if "refs/tags/" in line else ""
        v = parse_version(ref)
        if v and (best is None or v > best[0]):
            best = (v, ref)
    return best[1] if best else None


def has_update_backup():
    """True if ai-os-update has a backup to undo (Q57 greys the button otherwise)."""
    try:
        return any(p.is_dir() for p in UPDATE_BACKUP_DIR.iterdir())
    except Exception:
        return False


class Dashboard:
    """Layout matches the user's paper sketch (IMG_0622): left column =
    app tiles + 7-day forecast; right side = one big terminal / interactive app
    window where everything opens."""

    QUAD_FG = {"do_first": "#f87171", "schedule": "#4ade80",
               "delegate": "#fbbf24", "delete_later": "#94a3b8"}

    def __init__(self, root):
        self.root = root
        root.title("Ascended Barron")
        root.configure(bg=BG)
        self.status = tk.StringVar(value="READY")
        self.eisen_data = load_tasks()
        self.eisen_sel = None
        self.eisen_lists = None    # full-matrix listboxes when that view is open
        self.eisen_index = {}
        self.term_proc = None      # embedded terminal process, if any
        self.embedded_wid = None   # adopted app X window living in the pane

        st = ttk.Style()
        st.theme_use("clam")

        # slim header
        header = tk.Frame(root, bg=HEAD)
        header.pack(fill="x")
        row = tk.Frame(header, bg=HEAD)
        row.pack(fill="x", padx=16, pady=8)
        tk.Label(row, text="Ascended Barron", bg=HEAD, fg=INK,
                 font=(FONT, 20, "bold")).pack(side="left")
        self.clock = tk.StringVar()
        self.battery = tk.StringVar()
        tk.Label(row, textvariable=self.battery, bg=HEAD, fg=GOOD,
                 font=(FONT, 10, "bold"), width=13, anchor="e").pack(side="right", padx=(12, 0))
        self.wifi_status = tk.StringVar(value="Wi-Fi …")
        # Fixed width + right-anchor so status changes never shift the header.
        self.wifi_label = tk.Label(row, textvariable=self.wifi_status, bg=HEAD, fg=MUTED,
                                   font=(FONT, 10, "bold"), cursor="hand2", width=16, anchor="e")
        self.wifi_label.pack(side="right", padx=(12, 0))
        self.wifi_label.bind("<Button-1>",
                             lambda e: self.open_setup_script("WiFi Setup", "/usr/local/bin/ai-os-wifi-setup"))
        self.biglog_status = tk.StringVar(value="Local Logs: checking")
        self.biglog_label = tk.Label(row, textvariable=self.biglog_status, bg=HEAD, fg=MUTED,
                                     font=(FONT, 10, "bold"), cursor="hand2")
        self.biglog_label.pack(side="right", padx=(12, 12))
        self.biglog_label.bind("<Button-1>", self._biglog_test_now)
        self.clock_label = tk.Label(row, textvariable=self.clock, bg=HEAD, fg=MUTED,
                                    font=(FONT, 11), cursor="hand2")
        self.clock_label.pack(side="right")
        self.clock_label.bind("<Button-1>", self._pick_timezone)  # click clock -> set timezone
        self._tick()
        self._biglog_refresh()
        self._wifi_tick()

        self.status_bar = tk.Label(root, textvariable=self.status, bg="#022c22", fg=GOOD,
                                   font=(FONT, 11, "bold"), pady=6, anchor="w", padx=16)
        self.status_bar.pack(fill="x")

        # Thin "update available" banner — dismissible per-version (Q17/Q33).
        # Created here so it always slots directly under the status bar; it is
        # packed/unpacked on demand by _refresh_update_banner (empty until then).
        self.update_banner = tk.Frame(root, bg=AMBER)

        # Bottom bars are packed BEFORE the main area (with side="bottom") so
        # a tall right pane (e.g. the full Eisenhower matrix) compresses
        # instead of pushing them off the screen — pack clips whatever was
        # packed last when space runs out (footer was clipped on the 1024x768
        # VM screen, 2026-06-06).
        self._build_footer(root)
        self._build_weather_ticker(root)

        main = tk.Frame(root, bg=BG)
        main.pack(fill="both", expand=True)

        # ---- left sidebar ----
        side = tk.Frame(main, bg=BG, width=400)
        side.pack(side="left", fill="y", padx=(12, 6), pady=10)
        side.pack_propagate(False)
        self._build_app_grid(side)

        # ---- right pane: Work Zone for open apps/windows ----
        right = tk.Frame(main, bg=PANEL, highlightbackground="#1e3a5f", highlightthickness=1)
        right.pack(side="left", fill="both", expand=True, padx=(6, 12), pady=10)
        self.pane_title = tk.StringVar(value=WORK_ZONE_TITLE)
        self.pane_title_label = tk.Label(right, textvariable=self.pane_title, bg=HEAD, fg=INK,
                                          font=(FONT, 13, "bold"), pady=8, padx=14, anchor="w")
        # Auto-show the title bar when a non-empty title is set, hide it when
        # the title is cleared. Welcome (no title) → no header bar; Settings
        # (title="Settings") → header shows. Avoids an empty bar at the top.
        def _sync_pane_title_label(*_):
            if self.pane_title.get():
                if not self.pane_title_label.winfo_ismapped():
                    self.pane_title_label.pack(fill="x")
            else:
                self.pane_title_label.pack_forget()
        self.pane_title.trace_add("write", _sync_pane_title_label)
        self.content = tk.Frame(right, bg=PANEL)
        self.content.pack(fill="both", expand=True)

        root.bind("<Escape>", self._toggle_fs)
        root.bind("<Control-q>", lambda _e: root.destroy())
        # Responsive: re-balance the sidebar whenever the window changes size
        # (e.g. moving between the vertical 1080x1920 and the 2560x1080 screen).
        root.bind("<Configure>", self._relayout)
        root.after(200, self._relayout)
        log_event("dashboard_started", "AI OS dashboard opened (sketch layout)", kind="system")
        # Boot straight into the to-do list — it's the heart of the OS. The
        # welcome/empty-space view still shows when you close an app or terminal.
        self.open_eisenhower()
        # Quietly check GitHub for a newer release; the Update OS tile turns
        # amber + a banner shows if one is available. Delayed + threaded so it
        # never slows boot.
        self.update_available = False
        self.latest_version = None
        self.root.after(3000, self._schedule_update_check)

    # ---- self-update: is a newer version available? ----
    def _schedule_update_check(self):
        """Kick off a background version check now, then re-check every 6 hours."""
        threading.Thread(target=self._update_check_worker, daemon=True).start()
        self.root.after(6 * 60 * 60 * 1000, self._schedule_update_check)

    def _update_check_worker(self):
        """Compare the installed RELEASE TAG against the latest published one.
        Fail silent (opt-out / no network / dev build = leave things alone, never
        a false alarm). Q1/Q8."""
        if not get_setting("update_check_enabled", True):
            return  # the user turned the update check off (Q8)
        local = parse_version(installed_version_str())
        if local is None:
            return  # dev/unknown build — don't flag
        latest = latest_remote_release()
        lv = parse_version(latest or "")
        if lv and lv > local:
            self.latest_version = latest
            self.root.after(0, self._set_update_available)

    def _set_update_available(self):
        if not getattr(self, "update_available", False):
            self.update_available = True
            log_event("update_available",
                      f"a newer version is on GitHub ({getattr(self, 'latest_version', '?')})",
                      kind="system")
            if hasattr(self, "app_grid"):
                self._draw_app_tiles()
            self._refresh_update_banner()

    # ---- self-update: banner, settings (Q17/Q43/Q56) ----
    def _refresh_update_banner(self):
        """Show/hide the thin 'update available' banner. Dismiss hides it for the
        current version; it returns only when a newer version appears (Q17/Q33)."""
        if not hasattr(self, "update_banner"):
            return
        for w in self.update_banner.winfo_children():
            w.destroy()
        latest = getattr(self, "latest_version", None)
        dismissed = get_setting("banner_dismissed_version", "")
        if not (getattr(self, "update_available", False) and latest and dismissed != latest):
            self.update_banner.pack_forget()
            return
        tk.Label(self.update_banner,
                 text=f"  A new version ({latest}) is available — open “Update OS” to get it.",
                 bg=AMBER, fg="#1a1206", font=(FONT, 10, "bold"), anchor="w"
                 ).pack(side="left", fill="x", expand=True, pady=4)
        tk.Button(self.update_banner, text="Update OS",
                  command=lambda: self.open_setup_script("Update OS", "/usr/local/bin/ai-os-update"),
                  bg="#1a1206", fg=INK, font=(FONT, 9, "bold"), relief="flat",
                  padx=8, pady=1, cursor="hand2").pack(side="right", padx=(4, 6), pady=4)
        tk.Button(self.update_banner, text="✕", command=self._dismiss_update_banner,
                  bg=AMBER, fg="#1a1206", font=(FONT, 10, "bold"), relief="flat",
                  padx=6, pady=1, cursor="hand2").pack(side="right", pady=4)
        self.update_banner.pack(fill="x", after=self.status_bar)

    def _dismiss_update_banner(self):
        latest = getattr(self, "latest_version", "")
        if latest:
            set_setting("banner_dismissed_version", latest)
        self._refresh_update_banner()

    def _check_updates_now(self):
        """Manual 'Check for updates now' (Q56) — same check, on demand."""
        self._flash("Checking for updates…")

        def worker():
            latest = latest_remote_release()
            cur = parse_version(installed_version_str())
            lv = parse_version(latest or "")

            def done():
                if lv and cur and lv > cur:
                    self.latest_version = latest
                    self._set_update_available()
                    self._flash(f"Update available: {latest}")
                else:
                    self._flash("You're up to date.")
            self.root.after(0, done)
        threading.Thread(target=worker, daemon=True).start()

    def _undo_last_update(self):
        if not has_update_backup():
            messagebox.showinfo("Undo Last Update", "There's no update to undo yet.", parent=self.root)
            return
        self.open_setup_script("Undo Last Update", "/usr/local/bin/ai-os-rollback")

    def open_settings(self):
        """Settings screen — updates section only in v1.1.0 (Q43/Q56)."""
        self._clear()
        self.pane_title.set("Settings")
        wrap = tk.Frame(self.content, bg=PANEL)
        wrap.pack(fill="both", expand=True, padx=20, pady=16)
        tk.Label(wrap, text="Settings", bg=PANEL, fg=INK,
                 font=(FONT, 16, "bold")).pack(anchor="w")
        tk.Label(wrap, text="Updates", bg=PANEL, fg=SUB,
                 font=(FONT, 12, "bold")).pack(anchor="w", pady=(14, 4))
        tk.Label(wrap, text=f"Current version:  {installed_version_str()}",
                 bg=PANEL, fg=BODY, font=(FONT, 11)).pack(anchor="w", pady=2)

        self._setting_update_check = tk.BooleanVar(value=bool(get_setting("update_check_enabled", True)))

        def toggle_check():
            on = bool(self._setting_update_check.get())
            set_setting("update_check_enabled", on)
            self._flash("Update checks " + ("on" if on else "off"))
        tk.Checkbutton(wrap, text="Automatically check for updates (one small check on startup)",
                       variable=self._setting_update_check, command=toggle_check,
                       bg=PANEL, fg=BODY, selectcolor="#0b1626", activebackground=PANEL,
                       activeforeground=INK, font=(FONT, 11), anchor="w").pack(anchor="w", pady=2)

        def btn(parent, text, cmd, color="#13233c", state="normal"):
            return tk.Button(parent, text=text, command=cmd, bg=color, fg=INK,
                             activebackground=ACCENT, activeforeground=INK, relief="raised",
                             bd=2, font=(FONT, 11, "bold"), padx=10, pady=6, cursor="hand2",
                             state=state)
        row = tk.Frame(wrap, bg=PANEL)
        row.pack(anchor="w", pady=(10, 2))
        btn(row, "Check for updates now", self._check_updates_now).pack(side="left", padx=(0, 6))
        btn(row, "Update OS", lambda: self.open_setup_script("Update OS", "/usr/local/bin/ai-os-update"), ACCENT).pack(side="left", padx=6)

        row2 = tk.Frame(wrap, bg=PANEL)
        row2.pack(anchor="w", pady=(8, 2))
        undo_state = "normal" if has_update_backup() else "disabled"
        btn(row2, "Undo last update", self._undo_last_update, "#7c2d12", undo_state).pack(side="left")
        tk.Label(row2, text=("" if undo_state == "normal" else "  (nothing to undo yet)"),
                 bg=PANEL, fg=MUTED, font=(FONT, 10)).pack(side="left", padx=6)
        log_event("settings_opened", kind="user")

    # ---- footer: volume + power controls ----
    def _build_footer(self, root):
        """Bottom bar = the machine controls (replaced the Barron script
        router 2026-06-06): volume slider, Restart, Power Off. The power
        buttons are REAL — each one confirms before acting."""
        footer = tk.Frame(root, bg=HEAD)
        # side="bottom": packed before the main area so it can never be
        # clipped by a tall pane (see __init__).
        footer.pack(side="bottom", fill="x")
        tk.Label(footer, text="Esc = windowed/fullscreen     Ctrl+Q = quit",
                 bg=HEAD, fg=BODY, font=(FONT, 10), pady=6, padx=16).pack(side="left")
        # No Open Terminal tile; the only terminal entry points are the
        # "Open Project Terminal" button in the Eisenhower panel and any
        # terminal launcher on the desktop. Footer stays uncluttered.
        self.resource_status = tk.StringVar(value="CPU --  RAM avail --  Storage --")
        self.resource_label = tk.Label(footer, textvariable=self.resource_status,
                                       bg=HEAD, fg=GOOD, font=(FONT, 10, "bold"),
                                       pady=6, padx=10, cursor="hand2")
        self.resource_label.pack(side="left", padx=(8, 4))
        self.resource_label.bind("<Button-1>", self._show_resource_details)
        self._cpu_prev = read_cpu_times()
        self.root.after(2000, self._resource_tick)
        # Current version (Q30/Q44) — quiet, click to open Settings.
        self.version_label = tk.Label(footer, text=installed_version_str(),
                                      bg=HEAD, fg=MUTED, font=(FONT, 10),
                                      pady=6, padx=10, cursor="hand2")
        self.version_label.pack(side="left", padx=(4, 4))
        self.version_label.bind("<Button-1>", lambda _e: self.open_settings())
        # Volume slider only when an audio backend exists (PipeWire/wpctl or
        # ALSA/amixer). In the minimal VM neither may be present — hide it
        # rather than show a dead control. The host always has wpctl, so this
        # branch is always taken there (unchanged).
        if shutil.which("wpctl") or shutil.which("amixer"):
            tk.Label(footer, text="🔊 Volume", bg=HEAD, fg=BODY,
                     font=(FONT, 10)).pack(side="left", padx=(8, 4))
            self.vol_var = tk.IntVar(value=self._volume_read())
            self._vol_after = self._vol_log_after = None
            self.volume_scale = tk.Scale(footer, from_=0, to=100, orient="horizontal", variable=self.vol_var,
                                         command=self._volume_changed, length=170, showvalue=True,
                                         bg=HEAD, fg=BODY, troughcolor="#1e3a5f", highlightthickness=0,
                                         activebackground=SUB, bd=0, font=(FONT, 8), sliderrelief="raised",
                                         cursor="hand2")
            self.volume_scale.pack(side="left", pady=2)
            self.volume_scale.bind("<ButtonPress-1>", self._volume_capture_focus)
            self.volume_scale.bind("<ButtonRelease-1>", self._volume_restore_focus)
        # No AI setup button: use the terminal for normal commands.
        # Settings goes in the bottom-right corner alongside the machine controls
        # (Install / Restart / Power Off). Packed first → ends up rightmost.
        tk.Button(footer, text="⚙ Settings",
                  command=self.open_settings,
                  bg="#1e3a5f", fg=INK, activebackground="#2563eb", activeforeground=INK,
                  relief="raised", bd=2, font=(FONT, 10, "bold"), padx=10, pady=4,
                  cursor="hand2").pack(side="right", padx=(4, 6), pady=4)
        tk.Button(footer, text="⏻ Power Off",
                  command=lambda: self._power("poweroff", "Power Off"),
                  bg="#7f1d1d", fg=INK, activebackground="#b91c1c", activeforeground=INK,
                  relief="raised", bd=2, font=(FONT, 10, "bold"), padx=10, pady=4,
                  cursor="hand2").pack(side="right", padx=4, pady=4)
        tk.Button(footer, text="⟳ Restart",
                  command=lambda: self._power("reboot", "Restart"),
                  bg="#92400e", fg=INK, activebackground="#b45309", activeforeground=INK,
                  relief="raised", bd=2, font=(FONT, 10, "bold"), padx=10, pady=4,
                  cursor="hand2").pack(side="right", padx=4, pady=4)
        # Install-to-disk (C10): only show when the installer is present (i.e. on
        # the live/installed OS, not on a dev host), so there's never a dead button.
        if shutil.which("ai-os-install-to-disk") or os.path.exists(INSTALLER_PATH):
            tk.Button(footer, text="💾 Install to disk",
                      command=self._install_to_disk,
                      bg="#155e75", fg=INK, activebackground="#0e7490", activeforeground=INK,
                      relief="raised", bd=2, font=(FONT, 10, "bold"), padx=10, pady=4,
                      cursor="hand2").pack(side="right", padx=4, pady=4)

    def _wifi_tick(self):
        text, color = wifi_indicator()
        if hasattr(self, "wifi_status"):
            self.wifi_status.set(text)
        if hasattr(self, "wifi_label"):
            self.wifi_label.configure(fg=color)
        self.root.after(6000, self._wifi_tick)

    def _resource_tick(self):
        cur = read_cpu_times()
        cpu = cpu_percent_from(getattr(self, "_cpu_prev", None), cur)
        self._cpu_prev = cur
        mem_status = read_memory_status()
        disk = read_disk_percent("/")
        # Battery stays in the top-right header only. Keep the bottom resource
        # monitor focused on CPU/RAM/live changes space so it does not duplicate the header.
        parts = [fmt_pct("CPU", cpu), fmt_ram_available(mem_status), fmt_pct("Storage", disk)]
        if hasattr(self, "resource_status"):
            self.resource_status.set("  •  ".join(parts))
        if hasattr(self, "resource_label"):
            self.resource_label.configure(fg=resource_color(cpu, mem_status, disk, None))
        self.root.after(2000, self._resource_tick)

    def _show_resource_details(self, _e=None):
        cpu = fmt_pct("CPU", cpu_percent_from(getattr(self, "_cpu_prev", None), read_cpu_times()))
        mem_status = read_memory_status()
        mem = fmt_ram_available(mem_status)
        if isinstance(mem_status, dict):
            mem += f" ({mem_status['used_pct']}% used by apps/cache/live system)"
        disk = fmt_pct("Live changes space", read_disk_percent("/"))
        msg = ("Resource Monitor\n\n"
               f"{cpu}\n{mem}\n{disk}\n\n"
               "Battery stays in the top-right corner. Green is fine, yellow is getting high, red needs attention. RAM shows available memory because live ISO cache can make used RAM look scary. Live changes space is the temporary writable space for this boot, not the full USB drive.")
        messagebox.showinfo("Resources", msg, parent=self.root)

    def _volume_read(self):
        """Current output volume 0-100. wpctl (PipeWire) first, amixer fallback."""
        try:
            out = subprocess.check_output(
                ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
                text=True, stderr=subprocess.DEVNULL, timeout=2)
            return max(0, min(100, int(round(float(out.split()[1]) * 100))))
        except Exception:
            pass
        try:
            out = subprocess.check_output(["amixer", "sget", "Master"], text=True,
                                          stderr=subprocess.DEVNULL, timeout=2)
            pct = out.split("[")[1].split("%")[0]
            return max(0, min(100, int(pct)))
        except Exception:
            return 50

    def _volume_capture_focus(self, _e=None):
        """Remember the app that was visible before the volume slider stole
        focus. This fixes the laptop case where adjusting volume left Chromium
        hidden behind the fullscreen dashboard."""
        # The background-layer guard normally returns the last app to the top.
        # Pause that while the user is actually dragging/clicking the volume
        # slider, or the app gets raised before Tk can finish the volume change.
        self._dashboard_raise_paused_until = time.monotonic() + 4.0
        self.root._dashboard_raise_paused_until = self._dashboard_raise_paused_until
        self._volume_prev_focus = None
        if not shutil.which("xdotool"):
            return
        try:
            wid = subprocess.check_output(["xdotool", "getwindowfocus"], text=True,
                                          stderr=subprocess.DEVNULL, timeout=2).strip()
            if wid:
                self._volume_prev_focus = wid
        except Exception:
            pass

    def _volume_restore_focus(self, _e=None):
        # Let Tk finish applying/logging the slider value, then put the browser/app
        # back on top. Too-fast restore made the volume feel broken after the
        # dashboard-background fix because focus was taken back mid-interaction.
        self._dashboard_raise_paused_until = time.monotonic() + 1.2
        self.root._dashboard_raise_paused_until = self._dashboard_raise_paused_until
        self.root.after(1300, self._raise_last_or_visible_browser_window)

    def _raise_last_or_visible_browser_window(self):
        if not shutil.which("xdotool"):
            return
        candidates = []
        prev = getattr(self, "_volume_prev_focus", None)
        if prev:
            candidates.append(prev)
        for klass in ("chromium", "Chromium", "chrome", "Chrome", "firefox", "Firefox"):
            try:
                out = subprocess.check_output(["xdotool", "search", "--onlyvisible", "--class", klass],
                                              text=True, stderr=subprocess.DEVNULL, timeout=2)
                candidates.extend([ln.strip() for ln in out.splitlines() if ln.strip()])
            except Exception:
                pass
        seen = []
        for wid in candidates:
            if wid and wid not in seen and embeddable(wid):
                seen.append(wid)
        for wid in reversed(seen):
            cls = window_class(wid)
            try:
                title = subprocess.check_output(["xdotool", "getwindowname", wid], text=True,
                                                stderr=subprocess.DEVNULL, timeout=2).lower()
            except Exception:
                title = ""
            if any(h in cls or h in title for h in ("chromium", "chrome", "firefox", "browser")):
                try:
                    subprocess.run(["xdotool", "windowmap", wid, "windowraise", wid,
                                    "windowactivate", "--sync", wid], timeout=4,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
                return

    def _volume_changed(self, _v=None):
        # The slider fires for every pixel while dragging — debounce so we
        # don't spawn a process per pixel. Keep the dashboard/app raise guard
        # paused while the user is adjusting volume.
        self._dashboard_raise_paused_until = time.monotonic() + 2.0
        self.root._dashboard_raise_paused_until = self._dashboard_raise_paused_until
        if self._vol_after:
            self.root.after_cancel(self._vol_after)
        self._vol_after = self.root.after(60, self._volume_apply)

    def _volume_apply(self):
        self._vol_after = None
        n = self.vol_var.get()
        # Popen, NOT run: a blocking call here stalls Tk's after() timers and
        # the weather ticker visibly froze while dragging (seen 2026-06-06).
        try:
            if shutil.which("wpctl"):
                subprocess.Popen(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{n}%"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif shutil.which("amixer"):
                self._alsa_set_output_volume(n)
        except Exception:
            pass
        # Log once per adjustment, not once per drag step.
        if self._vol_log_after:
            self.root.after_cancel(self._vol_log_after)
        self._vol_log_after = self.root.after(
            1200, lambda: log_event("volume_set", f"{self.vol_var.get()}%", kind="user",
                                    volume=self.vol_var.get()))

    def _alsa_set_output_volume(self, n):
        """ALSA fallback used on the live AI OS laptop. The visible volume dial
        changed Master, but the real laptop speakers stayed muted because the
        Speaker/Headphone mixer switches were off. Set the common output
        controls together and unmute them so the dial means audible volume.
        """
        for control in ("Master", "Speaker", "Headphone"):
            subprocess.Popen(["amixer", "-q", "sset", control, f"{n}%", "unmute"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _power(self, verb, label):
        """REAL power control (his spec 2026-06-06: buttons instead of Barron's
        simulated scripts). Always confirms first — this is the actual machine."""
        if not messagebox.askyesno(
                label, f"{label} the computer now?\n\n"
                       "All open apps and AI sessions will close."):
            log_event("power_cancelled", label, kind="user")
            return
        log_event("power", f"user confirmed {label}", kind="user", action_verb=verb)
        try:
            subprocess.Popen(["systemctl", verb], start_new_session=True)
        except Exception as e:
            messagebox.showerror(label, f"Couldn't {label.lower()} the machine:\n\n{e}")

    def _install_to_disk(self):
        """Launch the guarded install-to-disk flow (C10) in a terminal.

        This is only the launcher + a first 'are you sure' gate. ALL of the
        disk selection and the real safety confirmations (refuse the live
        medium / in-use disks, type the exact disk name, type ERASE) live in
        the installer itself, so they happen in the terminal where the user can
        read them. The installed system boots straight to the dashboard as the
        single user 'barron' — no login, no password (locked decision)."""
        installer = shutil.which("ai-os-install-to-disk") or INSTALLER_PATH
        if not os.path.exists(installer):
            messagebox.showerror("Install to disk",
                                 "The installer isn't available on this system.",
                                 parent=self.root)
            return
        if not messagebox.askyesno(
                "Install to disk",
                "Install Ascended Barron: GroundTruth OS onto a disk?\n\n"
                "A terminal will open and guide you. It ERASES the disk you "
                "choose — but nothing is touched until you pick a disk and "
                "type ERASE to confirm.\n\n"
                "The installed system boots straight to the dashboard: no "
                "login and no password (you can add one later).",
                parent=self.root):
            log_event("install_to_disk_cancelled", "user declined at first prompt", kind="user")
            return
        log_event("install_to_disk", "user launched the disk installer", kind="user")
        shell_command = (f"sudo {shlex.quote(installer)}; "
                         "echo; read -rp 'Press Enter to close this window...' _")
        args = find_terminal(shell_command)
        if not args:
            messagebox.showerror("Install to disk",
                                 "No terminal emulator is installed to run the installer.",
                                 parent=self.root)
            return
        try:
            subprocess.Popen(args, start_new_session=True, env=x11_env())
        except Exception as e:
            messagebox.showerror("Install to disk",
                                 f"Couldn't start the installer:\n\n{e}", parent=self.root)

    # ---- helpers ----
    def _biglog_refresh(self):
        summary = biglog_health_summary()
        if hasattr(self, "biglog_status"):
            self.biglog_status.set(format_biglog_badge(summary))
        if hasattr(self, "biglog_label"):
            self.biglog_label.configure(fg=summary.get("color", MUTED))
        self._biglog_last_summary = summary
        self.root.after(10000, self._biglog_refresh)

    def _biglog_test_now(self, _e=None):
        rec = log_event("biglog_test", "User clicked BigLog test on AI OS dashboard",
                        kind="system", test_source="dashboard_click")
        summary = biglog_health_summary(max_age_seconds=60)
        self._biglog_last_summary = summary
        if hasattr(self, "biglog_status"):
            self.biglog_status.set(format_biglog_badge(summary))
        if hasattr(self, "biglog_label"):
            self.biglog_label.configure(fg=summary.get("color", MUTED))
        msg = ("BigLog training-data capture\n\n"
               f"State: {summary.get('state')}\n"
               f"Records: {summary.get('records')}\n"
               f"Last action: {summary.get('last_action')}\n"
               f"Test record id: {rec.get('record_id')}\n\n"
               f"Path:\n{summary.get('path')}\n\n"
               "Scope: dashboard actions are logged here. AI conversations started from a project terminal are captured as local session transcripts (any AI). Folder actions are logged when done through the dashboard, watchers, or imported tool logs.")
        messagebox.showinfo("BigLog status", msg, parent=self.root)
        self._flash(f"BigLog test: {summary.get('state')}")

    def _tick(self):
        self.clock.set(datetime.datetime.now().strftime("%A %d %B %Y  ·  %I:%M %p"))
        if hasattr(self, "battery"):
            cap, status = read_battery_status()
            self.battery.set(format_battery_indicator(cap, status))
        # Minute-level clock/battery updates are enough and reduce dashboard churn.
        self.root.after(5000, self._tick)

    def _pick_timezone(self, _e=None):
        """Click the clock to choose a timezone (the OS ships as UTC). Sets it
        with timedatectl via passwordless sudo; the clock updates next tick.
        On the live USB this resets each boot; on an installed system it sticks."""
        try:
            zones = subprocess.check_output(["timedatectl", "list-timezones"], text=True).split()
        except Exception as e:
            messagebox.showerror("Timezone", f"Couldn't list timezones:\n\n{e}", parent=self.root)
            return
        try:
            current = subprocess.check_output(
                ["timedatectl", "show", "-p", "Timezone", "--value"], text=True).strip()
        except Exception:
            current = ""
        win = tk.Toplevel(self.root); win.title("Choose timezone"); win.configure(bg=HEAD)
        tk.Label(win, text="Pick your timezone", bg=HEAD, fg=INK,
                 font=(FONT, 14, "bold")).pack(padx=16, pady=(14, 2))
        tk.Label(win, text=f"Current: {current or 'unknown'}   ·   type to filter (e.g. New_York)",
                 bg=HEAD, fg=MUTED, font=(FONT, 10)).pack(padx=16, pady=(0, 6))
        fvar = tk.StringVar()
        ent = tk.Entry(win, textvariable=fvar, bg="#0b1a2e", fg=INK, insertbackground=INK,
                       font=(FONT, 11), relief="flat")
        ent.pack(fill="x", padx=16, pady=4); ent.focus_set()
        lb = tk.Listbox(win, bg="#0b1a2e", fg=INK, font=(FONT, 10), height=15,
                        selectbackground=ACCENT, activestyle="none", highlightthickness=0)
        lb.pack(fill="both", expand=True, padx=16, pady=6)
        def refill(*_):
            f = fvar.get().strip().lower().replace(" ", "_")
            lb.delete(0, "end")
            for z in zones:
                if f in z.lower():
                    lb.insert("end", z)
            if current in lb.get(0, "end"):
                idx = list(lb.get(0, "end")).index(current); lb.selection_set(idx); lb.see(idx)
        refill(); fvar.trace_add("write", refill)
        def apply(_e=None):
            sel = lb.curselection()
            tz = lb.get(sel[0]) if sel else fvar.get().strip()
            if tz not in zones:
                messagebox.showinfo("Timezone", "Pick a timezone from the list.", parent=win); return
            try:
                subprocess.run(["sudo", "timedatectl", "set-timezone", tz], check=True)
                log_event("timezone_set", f"user set timezone to {tz}", kind="user")
                self.clock.set(datetime.datetime.now().strftime("%A %d %B %Y  ·  %I:%M %p"))
                self._flash(f"Timezone set to {tz}")
                win.destroy()
            except Exception as e:
                messagebox.showerror("Timezone", f"Couldn't set timezone:\n\n{e}", parent=win)
        lb.bind("<Double-Button-1>", apply); ent.bind("<Return>", apply)
        btns = tk.Frame(win, bg=HEAD); btns.pack(fill="x", padx=16, pady=12)
        tk.Button(btns, text="Set timezone", command=apply, bg=ACCENT2, fg=INK,
                  font=(FONT, 10, "bold"), relief="raised", bd=2, padx=10, pady=4,
                  cursor="hand2").pack(side="left")
        tk.Button(btns, text="✕ Close", command=win.destroy, bg="#13233c", fg=BODY,
                  font=(FONT, 10, "bold"), relief="raised", bd=2, padx=10, pady=4,
                  cursor="hand2").pack(side="right")
        win.geometry("440x560")

    def _toggle_fs(self, _e=None):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    def _relayout(self, _e=None):
        """Adapt the sidebar to the window height so app squares get room:
        tall screen = roomy (13 task rows), short/horizontal screen = compact
        (fewer rows, tighter app tiles). <Configure> fires for every child via
        bindtags, so only react to the toplevel itself."""
        if _e is not None and _e.widget is not self.root:
            return
        h = self.root.winfo_height()
        if h < 300:  # not mapped yet
            return
        pady = 10 if h >= 1300 else 5
        if pady == getattr(self, "_layout_key", None):
            return
        self._layout_key = pady
        self.tile_pady = pady
        self._draw_app_tiles()

    def _flash(self, msg):
        self.status.set(msg)
        self.status_bar.configure(bg="#16a34a", fg="#ffffff")
        self.root.after(600, lambda: self.status_bar.configure(bg="#022c22", fg=GOOD))

    def _clear(self):
        if getattr(self, "embedded_wid", None) and embeddable(self.embedded_wid):
            # Politely close the adopted app window (falls back to kill); doing
            # it before the host frame dies avoids ugly X errors in the app.
            for verb in ("windowclose", "windowkill"):
                try:
                    r = subprocess.run(["xdotool", verb, self.embedded_wid],
                                       timeout=2, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                    if r.returncode == 0:
                        break
                except Exception:
                    pass
            self.embedded_wid = None
        if self.term_proc is not None:
            # Kill the whole process group: launchers are often bash -> python,
            # and the orphaned child would die ugly when its X window vanishes.
            try:
                os.killpg(self.term_proc.pid, signal.SIGTERM)
            except Exception:
                try:
                    self.term_proc.terminate()
                except Exception:
                    pass
            self.term_proc = None
        self.eisen_lists = None
        for w in self.content.winfo_children():
            w.destroy()

    def _popup_prep(self, win):
        """No-window-manager survival kit for dialog Toplevels: the ISO runs
        bare X, so popups get NO title bar — no close button, no dragging. The
        Add-App window sat over the top of the VM screen with no way to
        dismiss it (the user hit this 2026-06-06). Center the dialog over
        the dashboard and let Escape close it; callers also add their own
        visible Close/Cancel button (the reliable path — Escape needs the
        popup to hold keyboard focus)."""
        win.transient(self.root)
        win.bind("<Escape>", lambda _e: win.destroy())
        win.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_reqwidth()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - win.winfo_reqheight()) // 3
        win.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        win.lift()
        win.focus_set()

    def _box(self, parent, title, header_right=None):
        """A titled panel: the 'title' label on the left of the header strip,
        and an optional caller-built widget on the right (e.g. quick-action
        buttons). header_right, if given, is called with the header Frame and
        should return a child widget to pack(side="right") into it."""
        box = tk.Frame(parent, bg=PANEL, highlightbackground="#1e3a5f", highlightthickness=1)
        header = tk.Frame(box, bg=HEAD)
        header.pack(fill="x")
        tk.Label(header, text=title, bg=HEAD, fg=INK, font=(FONT, 12, "bold"),
                 pady=6, padx=10, anchor="w").pack(side="left")
        if header_right is not None:
            try:
                widget = header_right(header)
                if widget is not None:
                    widget.pack(side="right", padx=8, pady=4)
            except Exception:
                pass
        return box

    # ---- sidebar: app tiles ----
    def _build_app_grid(self, parent):
        # Top-of-panel quick actions: Create App + Archive Apps, sitting right
        # of the "Apps" label. The Archive Apps tile that used to live in the
        # grid is removed (now redundant with the header button).
        def _apps_header_right(host):
            bar = tk.Frame(host, bg=HEAD)
            tk.Button(bar, text="＋ Create App",
                      command=lambda: self._app_build_new(None),
                      bg=GOOD, fg=INK, activebackground=ACCENT, activeforeground=INK,
                      font=(FONT, 9, "bold"), relief="raised", bd=1,
                      padx=8, pady=2, cursor="hand2").pack(side="left", padx=(0, 4))
            tk.Button(bar, text="Archive Apps",
                      command=self._archive_apps_dialog,
                      bg="#13233c", fg=INK, activebackground=ACCENT, activeforeground=INK,
                      font=(FONT, 9, "bold"), relief="raised", bd=1,
                      padx=8, pady=2, cursor="hand2").pack(side="left")
            return bar
        box = self._box(parent, "Apps", header_right=_apps_header_right)
        # Takes the whole sidebar below the to-do list (the weather moved to a
        # bottom ticker) — room for many more app squares.
        box.pack(fill="both", expand=True, pady=(0, 10))
        self.app_grid = tk.Frame(box, bg=PANEL)
        self.app_grid.pack(fill="x", padx=8, pady=8)
        self.app_slots = load_app_slots()
        self._draw_app_tiles()

    def _builtin_apps(self):
        # key, label, command, archiveable. Keys are stable so archived choices
        # survive dashboard restarts and future label tweaks.
        return [
            ("todo_list", "To-Do List", self.open_eisenhower, False),
        ]

    def _builtin_by_key(self):
        return {key: (name, cmd, archiveable) for key, name, cmd, archiveable in self._builtin_apps()}

    def _archive_builtin_key(self, key, name):
        archived = load_archived_builtins()
        if key not in archived:
            archived.append(key)
            save_archived_builtins(archived)
            log_event("builtin_app_archived", name, kind="user", key=key)
        self._draw_app_tiles()
        self._flash(f"Archived: {name}")

    def _restore_builtin_key(self, key):
        by_key = self._builtin_by_key()
        if key not in by_key:
            return
        name, _cmd, _archiveable = by_key[key]
        archived = [k for k in load_archived_builtins() if k != key]
        save_archived_builtins(archived)
        log_event("builtin_app_restored", name, kind="user", key=key)
        self._draw_app_tiles()
        self._flash(f"Added back: {name}")

    def _archive_apps_dialog(self):
        archiveable = [(key, name) for key, name, _cmd, archiveable in self._builtin_apps()
                       if archiveable and key not in load_archived_builtins()]
        win = tk.Toplevel(self.root)
        win.title("Archive Apps")
        win.configure(bg=PANEL, padx=18, pady=18)
        tk.Label(win, text="Pick app buttons to tuck away.\n"
                           "Archived apps disappear from Apps, but show up in Add App.",
                 bg=PANEL, fg=INK, font=(FONT, 11, "bold"), justify="left").pack(anchor="w")
        if not archiveable:
            tk.Label(win, text="No archiveable app buttons are currently visible.",
                     bg=PANEL, fg=BODY, font=(FONT, 11), justify="left").pack(anchor="w", pady=10)
        else:
            lb = tk.Listbox(win, bg="#0b1626", fg=BODY, font=(FONT, 11),
                            selectbackground=ACCENT, selectforeground=INK,
                            relief="flat", highlightthickness=0, activestyle="none",
                            height=min(10, max(4, len(archiveable))), width=42)
            for _key, name in archiveable:
                lb.insert("end", "  " + name)
            lb.pack(fill="both", expand=True, pady=10)

            def archive_selected(_e=None):
                sel = lb.curselection()
                if not sel:
                    messagebox.showinfo("Archive Apps", "Click an app first.", parent=win)
                    return
                key, name = archiveable[sel[0]]
                win.destroy()
                self._archive_builtin_key(key, name)
            lb.bind("<Double-Button-1>", archive_selected)
            tk.Button(win, text="Archive selected", command=archive_selected,
                      bg=ACCENT2, fg=INK, font=(FONT, 11, "bold"), relief="raised",
                      bd=2, padx=10, pady=6, cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(win, text="✕ Close", command=win.destroy, bg="#13233c", fg=INK,
                  font=(FONT, 11, "bold"), relief="raised", bd=2, padx=10, pady=6,
                  cursor="hand2").pack(side="right")
        self._popup_prep(win)

    def _draw_app_tiles(self):
        for w in self.app_grid.winfo_children():
            w.destroy()
        tp = getattr(self, "tile_pady", 10)  # compact on short screens
        archived = set(load_archived_builtins())
        builtins = [(key, name, cmd, archiveable)
                    for key, name, cmd, archiveable in self._builtin_apps()
                    if key not in archived]
        # (Archive Apps used to be a tile here; now it's a top-of-panel button
        # next to the "Apps" label — see _build_app_grid header_right.)
        for i, (key, name, cmd, archiveable) in enumerate(builtins):
            tile_bg = "#13233c"
            tile_name = name
            b = tk.Button(self.app_grid, text=tile_name, command=cmd, bg=tile_bg, fg=INK,
                          activebackground=ACCENT, activeforeground=INK,
                          relief="raised", bd=2, font=(FONT, 10, "bold"),
                          padx=6, pady=tp, cursor="hand2", wraplength=160)
            if archiveable:
                b.bind("<Button-3>", lambda _e, k=key, n=name: self._archive_builtin_key(k, n))
            b.grid(row=i // 2, column=i % 2, sticky="nsew", padx=4, pady=4)
        # User squares: placed apps, padded with at least one "+ Add App" square.
        n = max(len(self.app_slots) + 1, MIN_APP_SQUARES)
        for j in range(n):
            i = len(builtins) + j
            if j < len(self.app_slots):
                app = self.app_slots[j]
                b = tk.Button(self.app_grid, text=app["name"],
                              command=lambda a=app: self._app_launch(a),
                              bg="#13233c", fg=GOOD, activebackground=ACCENT,
                              activeforeground=INK, relief="raised", bd=2,
                              font=(FONT, 10, "bold"), padx=6, pady=tp,
                              cursor="hand2", wraplength=160)
                b.bind("<Button-3>", lambda _e, k=j: self._app_remove(k))
            else:
                b = tk.Button(self.app_grid, text="＋ Add App",
                              command=self._app_pick,
                              bg="#0b1626", fg=MUTED, activebackground="#13233c",
                              activeforeground=BODY, relief="ridge", bd=1,
                              font=(FONT, 9), padx=6, pady=max(tp - 2, 4),
                              cursor="hand2", wraplength=160)
            b.grid(row=i // 2, column=i % 2, sticky="nsew", padx=4, pady=4)
        self.app_grid.columnconfigure(0, weight=1)
        self.app_grid.columnconfigure(1, weight=1)

    def _app_launch(self, app):
        """Open a placed app. Default: its own normal window (reliable focus
        and typing). With AI_OS_EMBED=1 (the ISO), it opens INSIDE the right
        pane instead: launch, wait for its X window, reparent it in."""
        # Friendly guard: a seeded square may point at an app that isn't on
        # THIS system (e.g. Chrome with his cloned profile inside the minimal
        # VM). Say so calmly instead of crashing or popping an error dialog.
        if app_available(app) is None:
            log_event("app_unavailable", app["name"], kind="system",
                      source=app.get("source"))
            self._flash(f"{app['name']} is not installed on this system.")
            return
        if is_browser_app(app):
            # Chromium/browser windows were getting swallowed behind the right
            # pane on the laptop. Browsers are better as normal windows; open
            # them externally and actively raise/focus the window so Alt-Tab is
            # not required.
            self._app_launch_external(app, force_front=True)
            return
        if not EMBED or not shutil.which("xdotool"):
            self._app_launch_external(app, force_front=True)
            return
        self._clear()
        self.pane_title.set(WORK_ZONE_TITLE)
        host = tk.Frame(self.content, bg="#020912")
        host.pack(fill="both", expand=True)
        host.update_idletasks()
        before = list_x_windows()
        try:
            proc = launch_app(app)
        except Exception as e:
            log_event("app_launch_failed", f"{app['name']}: {e}", kind="system")
            messagebox.showerror("Couldn't open app",
                                 f"{app['name']} wouldn't start.\n\n{e}")
            self.show_welcome()
            return
        self.term_proc = proc  # _clear() kills it when another panel opens
        log_event("app_launched", f"{app['name']} (embedding in pane)", kind="user",
                  source=app.get("source"))
        self._flash(f"Opening here: {app['name']} …")
        threading.Thread(target=self._embed_hunt,
                         args=(app["name"], host, host.winfo_id(), before),
                         daemon=True).start()

    def _app_launch_external(self, app, force_front=False):
        try:
            launch_app(app)
            log_event("app_launched", f"{app['name']} (own window)", kind="user",
                      source=app.get("source"))
            if force_front:
                self._raise_external_app_window(app)
            self._flash(f"Opened in its own window: {app['name']}")
        except Exception as e:
            log_event("app_launch_failed", f"{app['name']}: {e}", kind="system")
            messagebox.showerror("Couldn't open app",
                                 f"{app['name']} wouldn't start.\n\n{e}")

    def _raise_external_app_window(self, app):
        """Best-effort focus fix for normal app windows. The laptop report was
        Chromium opening behind the dashboard/right pane and requiring Alt-Tab.
        Keep this conservative: find a matching visible top-level window, then
        map/raise/activate it a few times while the app finishes starting."""
        if not shutil.which("xdotool"):
            return
        hints = app_window_match_hints(app)
        before = list_x_windows()

        def worker():
            deadline = time.time() + (18 if is_browser_app(app) else 8)
            target = None
            while time.time() < deadline:
                candidates = sorted(list_x_windows())
                # Prefer new windows, but include old ones because Chromium may
                # reuse an existing single-instance window.
                candidates = [w for w in candidates if w not in before] + [w for w in candidates if w in before]
                for cand in candidates:
                    if not embeddable(cand):
                        continue
                    cls = window_class(cand)
                    try:
                        title = subprocess.check_output(["xdotool", "getwindowname", cand],
                                                        text=True, stderr=subprocess.DEVNULL,
                                                        timeout=2).lower()
                    except Exception:
                        title = ""
                    if not hints or any(h in cls or h in title for h in hints):
                        target = cand
                        break
                if target:
                    for _ in range(4):
                        subprocess.run(["xdotool", "windowmap", target, "windowraise", target,
                                        "windowactivate", "--sync", target],
                                       timeout=4, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                        time.sleep(0.35)
                    return
                time.sleep(0.25)

        threading.Thread(target=worker, daemon=True).start()

    def _embed_hunt(self, name, host, hid, before, klass=None):
        """Background: find the app's X window, then adopt it into the pane.
        His Tk apps carry no _NET_WM_PID and their launchers detach, so match
        by window TITLE (it equals the .desktop Name) — or by WM_CLASS when
        given (terminal windows are titled 'bash', not the app name).
        Single-instance apps may already have a window from before the
        launch — steal that one. Wait generously: Chrome's first start on the
        cloned 2.4 GB profile took >12s and ended up floating (2026-06-06)."""
        start = time.time()
        wid = None
        while time.time() - start < 45 and wid is None:
            new = sorted(list_x_windows() - before)
            named = []
            for cand in new:
                if not embeddable(cand):
                    continue
                try:
                    wname = subprocess.check_output(
                        ["xdotool", "getwindowname", cand], text=True,
                        stderr=subprocess.DEVNULL, timeout=2).strip()
                except Exception:
                    wname = ""
                named.append(cand)
                title_hit = wname and (name.lower() in wname.lower()
                                       or wname.lower() in name.lower())
                class_hit = klass and klass.lower() in window_class(cand)
                if title_hit or class_hit:
                    wid = cand
                    break
            if wid is None and time.time() - start > 3:
                # single-instance app: its window predates our launch
                try:
                    out = subprocess.check_output(
                        ["xdotool", "search", "--name", name], text=True,
                        stderr=subprocess.DEVNULL, timeout=2)
                    ids = [ln.strip() for ln in out.splitlines()
                           if ln.strip() and embeddable(ln.strip())]
                    if ids:
                        wid = ids[0]
                except Exception:
                    pass
            if wid is None and named and time.time() - start > 7:
                wid = named[0]  # last resort: first new app window
            if wid is None:
                time.sleep(0.3)
        ok = self._embed_reparent(wid, hid) if wid else False
        self.root.after(0, lambda: self._embed_finalize(name, host, wid, ok))

    def _embed_reparent(self, wid, hid):
        """Pull an app window into the pane (runs in the hunt thread). GNOME
        races us: on withdraw it reparents the window back to the root, which
        can undo our reparent — so verify the parent really is the pane and
        retry a few times."""
        def x(*args):
            subprocess.run(["xdotool", *args], timeout=3,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(5):
            x("windowunmap", "--sync", wid)
            time.sleep(0.25)          # let GNOME finish withdrawing it
            x("windowreparent", wid, str(hid))
            time.sleep(0.2)
            x("windowmap", wid)
            time.sleep(0.3)
            try:
                out = subprocess.check_output(["xwininfo", "-id", wid, "-children"],
                                              text=True, stderr=subprocess.DEVNULL,
                                              timeout=2)
                parent = next((ln for ln in out.splitlines()
                               if "Parent window id" in ln), "")
                if format(int(hid), "#x") in parent:
                    return True
            except Exception:
                pass
        return False

    def _embed_finalize(self, name, host, wid, ok):
        try:
            alive = host.winfo_exists()
        except Exception:
            alive = False
        if not alive:
            return  # user already switched panels; _clear() handled the process
        if wid is None:
            self._flash(f"{name}: no window appeared — check its own window/desktop")
            return
        if not ok:
            subprocess.run(["xdotool", "windowmap", wid], timeout=2,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._flash(f"{name} opened in its own window")
            return

        def fit(_e=None):
            try:
                subprocess.run(["xdotool", "windowmove", wid, "0", "0",
                                "windowsize", wid, str(max(50, host.winfo_width())),
                                str(max(50, host.winfo_height())),
                                "windowmap", wid],
                               timeout=2, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            except Exception:
                pass

        def refocus():
            # Terminals (Update OS etc.) need KEYBOARD focus, which
            # stays on the Tk window after reparenting — typing went nowhere.
            # Hand X input focus to the embedded app, but ONLY while the
            # dashboard itself really holds the keyboard. CAUTION (2026-06-06):
            # when the user is typing in a native-Wayland window (his
            # terminal), XWayland's pointer position AND focused-window are
            # both STALE — an eager version of this loop stole his keystrokes
            # mid-word. So every signal here must say "dashboard":
            #   1. Tk reports focus inside THIS toplevel (None when another
            #      app or a Wayland surface has the keyboard; a dashboard
            #      dialog like "+ Add" reports its own toplevel → no steal), OR
            #   2. X focus sits on Tk's hidden WRAPPER window (mutter parks it
            #      there; its id is undiscoverable but it carries the title).
            try:
                q = subprocess.check_output(
                    ["xdotool", "getmouselocation", "--shell"], text=True,
                    stderr=subprocess.DEVNULL, timeout=2)
                pos = dict(ln.split("=") for ln in q.strip().splitlines())
                hx, hy = host.winfo_rootx(), host.winfo_rooty()
                over = (hx <= int(pos["X"]) <= hx + host.winfo_width()
                        and hy <= int(pos["Y"]) <= hy + host.winfo_height())
                if not over:
                    return
                try:
                    w = self.root.focus_displayof()
                    tk_has = w is not None and w.winfo_toplevel() is self.root
                except Exception:
                    tk_has = False
                focused = subprocess.check_output(
                    ["xdotool", "getwindowfocus"], text=True,
                    stderr=subprocess.DEVNULL, timeout=2).strip()
                if focused == str(int(wid, 0)):
                    return  # embedded app already has the keyboard
                try:
                    fname = subprocess.check_output(
                        ["xdotool", "getwindowname", focused], text=True,
                        stderr=subprocess.DEVNULL, timeout=2).strip()
                except Exception:
                    fname = ""
                if tk_has or fname == "AI OS Dashboard":
                    subprocess.run(["xdotool", "windowfocus", wid], timeout=2,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            except Exception:
                pass

        def refit_loop():
            # Desktop widgets re-apply their own saved geometry; gently put
            # them back every couple of seconds while they live in the pane.
            if not host.winfo_exists() or self.embedded_wid != wid:
                return
            fit()
            self.root.after(2000, refit_loop)

        def refocus_loop():
            # Focus recovery runs on its own FAST cadence (2s felt like dead
            # keyboard while signing in to Chrome — typing must come back
            # well under half a second).
            if not host.winfo_exists() or self.embedded_wid != wid:
                return
            refocus()
            self.root.after(400, refocus_loop)
        host.bind("<Configure>", fit)
        self.embedded_wid = wid
        fit()
        # First focus hand-off so typing works immediately (sudo prompts etc.).
        subprocess.run(["xdotool", "windowfocus", wid], timeout=2,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        refit_loop()
        refocus_loop()
        log_event("app_embedded", f"{name} embedded in right pane", kind="system")
        self._flash(f"{name} is running here")

    def _app_remove(self, idx):
        app = self.app_slots[idx]
        if messagebox.askyesno("Clear square",
                               f"Take {app['name']} off this square?\n\n"
                               "(The app itself is NOT deleted — its Desktop icon stays.)"):
            self.app_slots.pop(idx)
            save_app_slots(self.app_slots)
            log_event("app_unplaced", app["name"], kind="user")
            self._draw_app_tiles()
            self._flash(f"Square cleared: {app['name']}")

    def _app_pick(self):
        """Fill a square: pick one of the apps already built (Desktop icons),
        or kick off building a brand-new one with AI."""
        win = tk.Toplevel(self.root)
        win.title("Add App to a Square")
        win.configure(bg=PANEL, padx=18, pady=18)
        tk.Label(win, text="Pick an archived built-in app to add back,\n"
                           "pick one of your Desktop icons, or build a new one.\n"
                           "Tip: right-click a filled square to clear it.",
                 bg=PANEL, fg=INK, font=(FONT, 11, "bold"), justify="left").pack(anchor="w")
        placed = {a.get("source") for a in self.app_slots}
        archived = load_archived_builtins()
        by_key = self._builtin_by_key()
        choices = []
        for key in archived:
            if key in by_key:
                name, _cmd, _archiveable = by_key[key]
                choices.append({"kind": "builtin", "key": key, "name": name})
        for a in scan_desktop_apps():
            if a["source"] not in placed:
                choices.append({"kind": "desktop", "app": a, "name": a["name"]})
        lb = tk.Listbox(win, bg="#0b1626", fg=BODY, font=(FONT, 11),
                        selectbackground=ACCENT, selectforeground=INK,
                        relief="flat", highlightthickness=0, activestyle="none",
                        height=min(12, max(4, len(choices))), width=48)
        for choice in choices:
            prefix = "↩  " if choice["kind"] == "builtin" else "  "
            lb.insert("end", prefix + choice["name"])
        lb.pack(fill="both", expand=True, pady=10)

        def place(_e=None):
            sel = lb.curselection()
            if not sel:
                messagebox.showinfo("Add App", "Click an app in the list first.", parent=win)
                return
            choice = choices[sel[0]]
            if choice["kind"] == "builtin":
                win.destroy()
                self._restore_builtin_key(choice["key"])
                return
            app = choice["app"]
            self.app_slots.append(app)
            save_app_slots(self.app_slots)
            log_event("app_placed", app["name"], kind="user", source=app["source"])
            win.destroy()
            self._draw_app_tiles()
            self._flash(f"Placed in a square: {app['name']}")
        lb.bind("<Double-Button-1>", place)

        row = tk.Frame(win, bg=PANEL)
        row.pack(fill="x")
        tk.Button(row, text="Place in square", command=place, bg=ACCENT2, fg=INK,
                  font=(FONT, 11, "bold"), relief="raised", bd=2, padx=10, pady=6,
                  cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(row, text="Build a new app", command=lambda: self._app_build_new(win),
                  bg=GOOD, fg=INK, font=(FONT, 11, "bold"), relief="raised", bd=2,
                  padx=10, pady=6, cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(row, text="✕ Close", command=win.destroy, bg="#13233c", fg=INK,
                  font=(FONT, 11, "bold"), relief="raised", bd=2, padx=10, pady=6,
                  cursor="hand2").pack(side="right")
        self._popup_prep(win)

    def _app_build_new(self, parent_win=None):
        """Build a brand-new app with AI: name it, create a project folder +
        a ground-truth.md named for it, and open a terminal right inside it to
        start building. Once it's built, place it in a square via Add App."""
        name = simpledialog.askstring(
            "Build a new app",
            "Name your app (this becomes its project folder):",
            parent=parent_win or self.root)
        if not name or not name.strip():
            return
        name = name.strip()
        task = {"id": str(uuid.uuid4()), "title": name, "quadrant": "do_first",
                "completed": False, "created_at": _now_iso(), "updated_at": _now_iso(),
                "completed_at": None}
        self.eisen_data.setdefault("tasks", []).append(task)
        save_tasks(self.eisen_data)
        log_event("task_added", name, kind="user", quadrant="do_first", via="build_app")
        self._eisen_refresh(reload=False)
        self.eisen_sel = task
        if parent_win is not None:
            try:
                parent_win.destroy()
            except Exception:
                pass
        # Create the project folder + ground-truth.md + AGENTS.md and open a
        # terminal in it to start building (same flow as Work-with-AI on a task).
        self.open_selected_project_terminal()

    # ---- bottom weather ticker (the user's prebuilt weather app) ----
    def _build_weather_ticker(self, parent):
        """Slim full-width strip along the bottom of the screen: current
        conditions + the 7-day forecast in one line, same colored symbols as
        his desktop widget. If the line is wider than the window it scrolls
        across like a news ticker; otherwise it sits still. Clicking it still
        opens the real weather widget. (Replaced the sidebar card 2026-06-06 —
        it ate sidebar space he wants for app squares.)"""
        self.fc_data = None
        self._fc_after = None
        self.fc_canvas = tk.Canvas(parent, bg=HEAD, height=46,
                                   highlightthickness=0, bd=0, cursor="hand2")
        # side="bottom": packed before the main area (after the footer, so it
        # sits just above it) — see the packing-order note in __init__.
        self.fc_canvas.pack(side="bottom", fill="x")
        self.fc_canvas.bind("<Button-1>", self._fc_open_widget)
        self.fc_canvas.bind("<Configure>", lambda _e: self._fc_draw())
        self._fc_text("Loading weather…")
        if WAPP:
            threading.Thread(target=self._fc_fetch, daemon=True).start()
        else:
            # Weather engine couldn't be imported (missing weather_app.py or a
            # bad import). Stay calm — no error dialog — and just say so.
            self._fc_text("Weather unavailable — click here to open your weather widget.")

    def _fc_text(self, msg):
        c = self.fc_canvas
        c.delete("all")
        c.create_text(16, 23, text=msg, anchor="w", fill=MUTED, font=(FONT, 10))

    def _fc_fetch(self):
        try:
            data = WAPP.fetch_weather(WAPP.load_config())
        except Exception:
            data = None

        def apply():
            try:
                if data:
                    self.fc_data = data
                    self._fc_draw()
                    # Normal refresh: keep the always-visible strip current.
                    delay_ms = 30 * 60 * 1000
                else:
                    self._fc_text("Weather unavailable (retrying…) — "
                                  "click here to open your weather widget.")
                    # On live boot, the dashboard can start before Wi-Fi/DNS is
                    # ready. Retry soon instead of staying unavailable for 30 min.
                    delay_ms = 30 * 1000
                self.root.after(delay_ms,
                                lambda: threading.Thread(target=self._fc_fetch,
                                                         daemon=True).start())
            except Exception:
                pass
        self.root.after(0, apply)

    def _fc_compose(self, c, x0, d, h):
        """Draw one run of the ticker line starting at x0; return its end x."""
        cy = h // 2
        ib = WAPP.draw_weather_symbol(c, x0, cy - 13, d.get("code"), 26)
        x = ib[2] + 10
        t = c.create_text(x, cy, text=f"{d['temp']}°F  {d['condition']}",
                          anchor="w", fill=WAPP.TEXT, font=("Ubuntu", 13, "bold"))
        x = c.bbox(t)[2] + 14
        details = []
        if d.get("feels_like") is not None:
            details.append(f"Feels {d['feels_like']}°")
        if d.get("humidity") is not None:
            details.append(f"Humidity {d['humidity']}%")
        if d.get("wind") is not None:
            details.append(f"Wind {d['wind']} mph")
        if details:
            t = c.create_text(x, cy, text="  ·  ".join(details), anchor="w",
                              fill=WAPP.MUTED, font=("Ubuntu", 10, "bold"))
            x = c.bbox(t)[2] + 28
        for day in d.get("forecast", [])[:7]:
            dt = datetime.datetime.strptime(day["date"], "%Y-%m-%d")
            t = c.create_text(x, cy, text=dt.strftime("%a"), anchor="w",
                              fill=WAPP.MUTED, font=("Ubuntu", 11, "bold"))
            x = c.bbox(t)[2] + 6
            ib = WAPP.draw_weather_symbol(c, x, cy - 9, day.get("code"), 18)
            x = ib[2] + 6
            t = c.create_text(x, cy, text=f"{day['hi']}°/{day['lo']}°",
                              anchor="w", fill=WAPP.TEMP,
                              font=("Ubuntu", 11, "bold"))
            x = c.bbox(t)[2] + 24
        t = c.create_text(x, cy, anchor="w", fill=WAPP.DIM, font=("Ubuntu", 9),
                          text=(f"{d['location']} · Updated {d['updated']} · "
                                "click = open widget"))
        return c.bbox(t)[2]

    def _fc_draw(self):
        if not (WAPP and self.fc_data):
            return
        c, d = self.fc_canvas, self.fc_data
        w, h = c.winfo_width(), c.winfo_height()
        if w < 80 or h < 20:
            return
        if self._fc_after:  # stop a previous scroll loop before redrawing
            try:
                c.after_cancel(self._fc_after)
            except Exception:
                pass
            self._fc_after = None
        c.delete("all")
        end = self._fc_compose(c, 14, d, h)
        if end <= w - 14:
            return  # whole line fits (ultrawide) — no need to scroll
        # Too wide (vertical screen): draw a second copy and loop seamlessly.
        run = end + 80
        self._fc_compose(c, 14 + run, d, h)
        c.addtag_all("ticker")
        self._fc_off = 0

        def step():
            c.move("ticker", -1, 0)
            self._fc_off += 1
            if self._fc_off >= run:
                c.move("ticker", run, 0)
                self._fc_off = 0
            self._fc_after = c.after(30, step)
        self._fc_after = c.after(1500, step)

    def _fc_open_widget(self, _e=None):
        """Clicking the weather strip retries weather immediately.

        This is better for live boot: the user can fix Wi-Fi, click the
        weather area once, and see the forecast refresh without waiting for the
        automatic retry timer.
        """
        if WAPP:
            self._fc_text("Checking weather now…")
            log_event("weather_retry_clicked", "Weather strip retry", kind="user")
            threading.Thread(target=self._fc_fetch, daemon=True).start()
        else:
            self._flash("Weather widget is not installed on this system.")
            self._fc_text("Weather unavailable — weather widget is missing.")

    # ---- Work Zone: open apps, terminals, and task windows ----
    def _project_terminal_shell_command(self, folder):
        # Wrap the interactive shell in `script` so the WHOLE session transcript
        # — including whatever AI CLI the user runs inside — is captured to a
        # local file. This is AI-agnostic: it records by terminal, not by tool,
        # so any AI (or none) is logged automatically. The transcript feeds the
        # local training-data export. We tell the user it is being recorded.
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        safe = safe_folder_name(folder.name) or "session"
        transcript = SESSIONS_DIR / f"{ts}-{safe}.log"
        q_transcript = shlex.quote(str(transcript))
        q_sessions = shlex.quote(str(SESSIONS_DIR))
        # Home-relativize the folder for the banner so it reads like the
        # approved copy (~/workspace/<task>/) but stays the REAL path — no
        # placeholder. Falls back to the absolute path if it isn't under $HOME.
        try:
            disp = "~/" + str(folder.relative_to(HOME))
        except ValueError:
            disp = str(folder)
        if not disp.endswith("/"):
            disp += "/"
        # The approved first-run banner (locked, Q3). Built as Python strings and
        # quoted per-line with shlex so apostrophes / box-drawing / quotes survive
        # the shell. The folder path is printed dynamically (real task name).
        bar = "════════════════════════════════════════════════════════════════"
        banner = [
            bar,
            "  ✅ Project created.",
            "",
            f"  • Folder created:        {disp}",
            "  • Ground truth created:  ground-truth.md  (your project's plan & memory)",
            "  • No need to cd — you're already in the right folder.",
            "",
            "  ── Recommended next step ───────────────────────────────────────",
            "  1. Install your AI CLI of choice (Claude Code, or any other).",
            "  2. Start it in this folder.",
            '  3. Tell it:  "Read ground-truth.md and follow it."',
            "",
            "  ground-truth.md will guide both you and the AI through the",
            "  whole project — planning, decisions, steps, and progress.",
            "  This terminal is yours. You have full freedom here.",
            bar,
            "",
            # C3 privacy notice — kept: any AI session in this terminal is
            # captured locally as training data the user owns. Honest + local-only.
            "  This session is recorded locally as training data you own",
            "  (nothing is uploaded by the OS):",
            f"    {transcript}",
            "",
        ]
        lines = ["clear", f"cd {shlex.quote(str(folder))}"]
        lines += ["echo " + shlex.quote(b) for b in banner]
        lines.append(f"mkdir -p {q_sessions}")
        # `script` captures the session to the transcript. If it is missing
        # for any reason, fall back to a plain shell so the terminal still works.
        lines.append(
            f"if command -v script >/dev/null 2>&1; then exec script -q --flush -c bash {q_transcript}; else exec bash; fi")
        return "; ".join(lines)

    def open_selected_project_terminal(self):
        if not self._eisen_need_sel("Open Project Terminal"):
            return
        task = self.eisen_sel
        title = task.get("title", "Untitled")
        folder = project_folder_for_task(task)
        created = not folder.exists()
        folder.mkdir(parents=True, exist_ok=True)
        if created:
            log_event("folder_created", str(folder), kind="file", path=str(folder))
        sel = folder / ".eisenhower-selected-task.json"
        sel.write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
        log_file_write(sel, "selected task")
        ensure_ground_truth(task, folder)
        agents = folder / "AGENTS.md"
        if not agents.exists():
            agents.write_text(build_agents_md(task, folder), encoding="utf-8")
            log_file_write(agents, "AGENTS.md created")
        cmd = self._project_terminal_shell_command(folder)
        args = find_terminal(cmd)
        if args:
            subprocess.Popen(args, start_new_session=True)
            self._flash(f"Opened project terminal: {title}")
            log_event("terminal_opened", "selected project terminal", kind="system",
                      task=title, folder=str(folder))
            return
        msg = "No terminal emulator is installed. Install lxterminal or xterm, then try again."
        self._clear()
        self.pane_title.set(WORK_ZONE_TITLE)
        tk.Label(self.content, text=msg, bg=PANEL, fg=BODY, font=(FONT, 13),
                 justify="left", wraplength=900).pack(expand=True)
        self._flash("No terminal emulator found")


    def open_setup_script(self, title, script_path):
        """Open one of the simple setup scripts as an Apps button.
        Each button runs in a real terminal so the user can see plain PASS/FAIL output."""
        self._clear()
        self.pane_title.set(WORK_ZONE_TITLE)
        quoted = shlex.quote(script_path)
        cmd = f"if [ -x {quoted} ]; then {quoted}; else echo 'Missing setup script: {script_path}'; read -rp 'Press Enter to close...' _; fi"
        if (EMBED or TERMINAL_PANE) and shutil.which("xterm"):
            host = tk.Frame(self.content, bg="#020912")
            host.pack(fill="both", expand=True)
            host.update_idletasks()
            self.term_proc = subprocess.Popen(
                xterm_args(cmd, into=host.winfo_id()),
                start_new_session=True)
            self._flash(f"Running: {title}")
            log_event("setup_script_opened", title, kind="system", script=script_path)
            return
        args = find_terminal(cmd)
        if args:
            subprocess.Popen(args, start_new_session=True)
            self._flash(f"Running: {title}")
            log_event("setup_script_opened", title, kind="system", script=script_path)
            return
        msg = f"No terminal emulator is installed, so {title} cannot run."
        tk.Label(self.content, text=msg, bg=PANEL, fg=BODY, font=(FONT, 13),
                 justify="left", wraplength=900).pack(expand=True)
        self._flash("No terminal emulator found")

    def show_welcome(self):
        # Terminals and apps open as movable windows in normal laptop mode.
        self._clear()
        self.pane_title.set(WORK_ZONE_TITLE)
        where = "right here" if EMBED else "in its own window"
        msg = ("This is empty space for your windows: open apps, terminals,\n"
               "and task work can go here. Drag windows here if you want to keep them organized.\n\n"
               f"•  Apps and task windows open {where}; use this space to arrange them.\n"
               "•  Select a task, then open a terminal in its project folder.\n\n"
               "•  Volume, Restart and Power Off live in the bottom bar.\n\n"
               "Everything you do is logged locally as training data.")
        wrap = tk.Frame(self.content, bg=PANEL)
        wrap.pack(expand=True)
        tk.Label(wrap, text=msg, bg=PANEL, fg=BODY, font=(FONT, 13),
                 justify="left").pack()

    # ---- Eisenhower full matrix (opens in the right pane) ----
    def open_eisenhower(self):
        self._clear()
        self.pane_title.set(WORK_ZONE_TITLE)
        self._flash("Opened Eisenhower full matrix")
        log_event("panel_opened", "Eisenhower Tasks", kind="user")
        self.eisen_data = load_tasks()
        self.eisen_lists = {}
        self.eisen_index = {}
        self.eisen_sel = None

        # Two rows of buttons — all six in one row overflow the pane on the
        # 1024x768 VM screen (Delete/Refresh were cut off at the right edge,
        # 2026-06-06).
        bars = tk.Frame(self.content, bg=PANEL)
        bars.pack(fill="x", padx=8, pady=(8, 2))
        row1 = tk.Frame(bars, bg=PANEL)
        row1.pack(fill="x")
        row2 = tk.Frame(bars, bg=PANEL)
        row2.pack(fill="x", pady=(4, 0))

        def tb(row, text, cmd, color="#13233c"):
            tk.Button(row, text=text, command=cmd, bg=color, fg=INK,
                      activebackground=ACCENT, activeforeground=INK, relief="raised", bd=2,
                      font=(FONT, 10, "bold"), padx=10, pady=5, cursor="hand2").pack(side="left", padx=3)
        tb(row1, "➕ Add Task", self._eisen_add, ACCENT2)
        tb(row1, "Open Project Terminal", self.open_selected_project_terminal, ACCENT)
        tb(row2, "✓ Mark Done", self._eisen_done)
        tb(row2, "Done Tasks", self._eisen_show_done_tasks)
        tb(row2, "↔ Move", self._eisen_move)
        tb(row2, "🗑 Delete", self._eisen_delete, "#7f1d1d")

        # One-line orientation so first-time users know the core loop now that
        # this view is the boot default (replaces the old welcome screen).
        tk.Label(self.content,
                 text="Tip: pick a task, then \"Open Project Terminal\" to work on it in its own folder. "
                      "Everything you do is logged locally as training data.",
                 bg=PANEL, fg=BODY, font=(FONT, 10), anchor="w",
                 justify="left").pack(fill="x", padx=12, pady=(2, 0))

        grid = tk.Frame(self.content, bg=PANEL)
        grid.pack(fill="both", expand=True, padx=8, pady=8)
        for i, (key, title, sub, color) in enumerate(QUADS):
            q = tk.Frame(grid, bg=PANEL, highlightbackground=color, highlightthickness=2)
            q.grid(row=i // 2, column=i % 2, sticky="nsew", padx=6, pady=6)
            head = tk.Frame(q, bg=color)
            head.pack(fill="x")
            tk.Label(head, text=title, bg=color, fg=INK, font=(FONT, 12, "bold"),
                     pady=5, padx=10, anchor="w").pack(side="left")
            tk.Label(head, text=sub, bg=color, fg="#e5e7eb", font=(FONT, 8),
                     pady=5, padx=6).pack(side="right")
            lb = tk.Listbox(q, bg="#0b1626", fg=BODY, font=(FONT, 11),
                            selectbackground=ACCENT, selectforeground=INK,
                            relief="flat", highlightthickness=0, activestyle="none")
            sb = tk.Scrollbar(q, orient="vertical", command=lb.yview,
                              bg="#ffffff", troughcolor="#334155",
                              activebackground="#e5e7eb", borderwidth=1,
                              relief="raised", width=18, highlightthickness=1)
            lb.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y", padx=(2, 5), pady=5)
            lb.pack(side="left", fill="both", expand=True, padx=5, pady=5)
            lb.bind("<<ListboxSelect>>", lambda _e, k=key: self._eisen_on_select(k))
            lb.bind("<Double-Button-1>", lambda _e, k=key: self._eisen_on_select(k))
            self.eisen_lists[key] = lb
        for r in range(2):
            grid.rowconfigure(r, weight=1)
        for c in range(2):
            grid.columnconfigure(c, weight=1)
        self._eisen_refresh(reload=False)

    def _eisen_active(self, key):
        return [t for t in self.eisen_data.get("tasks", [])
                if t.get("quadrant") == key and not t.get("completed")]

    def _eisen_refresh(self, reload=True):
        if reload:
            self.eisen_data = load_tasks()
        self.eisen_sel = None
        if self.eisen_lists:
            try:
                for key, *_ in QUADS:
                    lb = self.eisen_lists[key]
                    lb.delete(0, "end")
                    items = self._eisen_active(key)
                    self.eisen_index[key] = items
                    for t in items:
                        lb.insert("end", "  " + t.get("title", "Untitled"))
            except tk.TclError:
                self.eisen_lists = None
        active = sum(1 for t in self.eisen_data.get("tasks", []) if not t.get("completed"))
        self.status.set(f"{active} active tasks  ·  file: {tasks_path().name}")

    def _eisen_on_select(self, key):
        if not self.eisen_lists:
            return
        for k, lb in self.eisen_lists.items():
            if k != key:
                lb.selection_clear(0, "end")
        sel = self.eisen_lists[key].curselection()
        if sel:
            self.eisen_sel = self.eisen_index[key][sel[0]]
            self._flash(f"Selected: {self.eisen_sel.get('title', '')}")
            log_event("task_selected", self.eisen_sel.get("title", ""), kind="user", quadrant=key)

    def _eisen_need_sel(self, what):
        if not self.eisen_sel:
            messagebox.showinfo(what, "Click a task to select it first.")
            return False
        return True

    def _eisen_quad_chooser(self, title_text, on_choose):
        win = tk.Toplevel(self.root)
        win.title("Choose quadrant")
        win.configure(bg=PANEL, padx=18, pady=18)
        tk.Label(win, text=title_text, bg=PANEL, fg=INK, font=(FONT, 12, "bold"),
                 wraplength=380).pack(anchor="w", pady=(0, 10))
        for key, t, sub, color in QUADS:
            tk.Button(win, text=f"{t} — {sub}", command=lambda q=key: on_choose(q, win),
                      bg=color, fg=INK, font=(FONT, 11, "bold"), relief="raised", bd=2,
                      padx=10, pady=8, cursor="hand2").pack(fill="x", pady=4)
        tk.Button(win, text="Cancel", command=win.destroy, bg="#13233c", fg=BODY,
                  font=(FONT, 10, "bold"), relief="raised", bd=2, padx=10, pady=6,
                  cursor="hand2").pack(fill="x", pady=(10, 0))
        self._popup_prep(win)

    def _eisen_add(self):
        title = simpledialog.askstring("Add Task", "What's the task?", parent=self.root)
        if not title or not title.strip():
            return

        def choose(q, win):
            self.eisen_data.setdefault("tasks", []).append({
                "id": str(uuid.uuid4()), "title": title.strip(), "quadrant": q,
                "completed": False, "created_at": _now_iso(), "updated_at": _now_iso(),
                "completed_at": None})
            save_tasks(self.eisen_data)
            log_event("task_added", title.strip(), kind="user", quadrant=q)
            win.destroy()
            self._eisen_refresh(reload=False)
            self._flash(f"Added: {title.strip()}")
        self._eisen_quad_chooser(f"Add: {title.strip()}", choose)

    def _eisen_delete(self):
        if not self._eisen_need_sel("Delete"):
            return
        t = self.eisen_sel
        if messagebox.askyesno("Delete task", f"Delete this task?\n\n{t.get('title', '')}"):
            self.eisen_data["tasks"] = [x for x in self.eisen_data.get("tasks", [])
                                        if x.get("id") != t.get("id")]
            save_tasks(self.eisen_data)
            log_event("task_deleted", t.get("title", ""), kind="user",
                      quadrant=t.get("quadrant"))
            self._eisen_refresh(reload=False)
            self._flash(f"Deleted: {t.get('title', '')}")

    def _eisen_done(self):
        if not self._eisen_need_sel("Mark Done"):
            return
        t = self.eisen_sel
        t["completed"] = True
        t["completed_at"] = _now_iso()
        t["updated_at"] = _now_iso()
        save_tasks(self.eisen_data)
        log_event("task_completed", t.get("title", ""), kind="user",
                  quadrant=t.get("quadrant"))
        self._eisen_refresh(reload=False)
        self._flash(f"Done: {t.get('title', '')}")

    def _eisen_select_task_by_id(self, task_id):
        if not self.eisen_lists:
            return
        for key, lb in self.eisen_lists.items():
            lb.selection_clear(0, "end")
            for idx, task in enumerate(self.eisen_index.get(key, [])):
                if task.get("id") == task_id:
                    lb.selection_set(idx)
                    lb.see(idx)
                    self.eisen_sel = task
                    return

    def _eisen_show_done_tasks(self):
        self.eisen_data = load_tasks()
        done_tasks = eisen_done_tasks(self.eisen_data)
        quad_labels = {key: title for key, title, _sub, _color in QUADS}

        win = tk.Toplevel(self.root)
        win.title("Done Tasks")
        win.configure(bg=PANEL, padx=16, pady=16)
        tk.Label(win, text="Done Tasks", bg=PANEL, fg=INK,
                 font=(FONT, 13, "bold")).pack(anchor="w")
        tk.Label(win, text="Select a done task to restore it.", bg=PANEL, fg=BODY,
                 font=(FONT, 10)).pack(anchor="w", pady=(2, 8))

        search_var = tk.StringVar()
        search = tk.Entry(win, textvariable=search_var, bg="#0b1626", fg=INK,
                          insertbackground=INK, relief="flat", font=(FONT, 11))
        search.insert(0, "")
        search.pack(fill="x", pady=(0, 8))
        search.focus_set()
        tk.Label(win, text="Search done tasks", bg=PANEL, fg=MUTED,
                 font=(FONT, 9)).pack(anchor="w", pady=(0, 4))

        empty = tk.Label(win, text="No done tasks yet", bg=PANEL, fg=MUTED,
                         font=(FONT, 11), pady=10)
        lb = tk.Listbox(win, bg="#0b1626", fg=BODY, font=(FONT, 10), width=72, height=12,
                        selectbackground=ACCENT, selectforeground=INK,
                        relief="flat", highlightthickness=0, activestyle="none")
        visible = []

        def preview(task):
            for key in ("notes", "description", "details", "body"):
                raw = str(task.get(key) or "").strip()
                if raw:
                    return " ".join(raw.split())[:80]
            return ""

        def fmt_done_at(task):
            raw = task.get("completed_at") or ""
            if not raw:
                return "completed date unknown"
            try:
                dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                return raw[:16]

        def matches(task, query):
            if not query:
                return True
            haystack = " ".join(str(task.get(k) or "") for k in
                                ("title", "notes", "description", "details", "quadrant"))
            return query.lower() in haystack.lower()

        def render(*_args):
            query = search_var.get().strip()
            visible.clear()
            lb.delete(0, "end")
            for task in done_tasks:
                if not matches(task, query):
                    continue
                visible.append(task)
                title = task.get("title", "Untitled")
                quad = quad_labels.get(task.get("quadrant"), task.get("quadrant", "Unknown"))
                extra = preview(task)
                line = f"{title}  ·  {quad}  ·  {fmt_done_at(task)}"
                if extra:
                    line += f"  ·  {extra}"
                lb.insert("end", line)
            if visible:
                empty.pack_forget()
                if not lb.winfo_ismapped():
                    lb.pack(fill="both", expand=True)
                lb.selection_clear(0, "end")
                lb.selection_set(0)
            else:
                lb.pack_forget()
                empty.config(text="No done tasks yet" if not done_tasks else "No matching done tasks")
                empty.pack(fill="x")

        def restore_selected(*_args):
            sel = lb.curselection()
            if not sel or sel[0] >= len(visible):
                return
            restored = restore_eisen_done_task(self.eisen_data, visible[sel[0]].get("id"))
            if restored is None:
                return
            save_tasks(self.eisen_data)
            log_event("task_restored", restored.get("title", ""), kind="user",
                      quadrant=restored.get("quadrant"))
            win.destroy()
            self._eisen_refresh(reload=False)
            self._eisen_select_task_by_id(restored.get("id"))
            self._flash(f"Restored: {restored.get('title', '')}")

        search_var.trace_add("write", render)
        lb.bind("<Double-Button-1>", restore_selected)
        lb.bind("<Return>", restore_selected)
        win.bind("<Return>", restore_selected)
        win.bind("<Escape>", lambda _e: win.destroy())
        render()
        tk.Button(win, text="Close", command=win.destroy, bg="#13233c", fg=BODY,
                  font=(FONT, 10, "bold"), relief="raised", bd=2, padx=10, pady=6,
                  cursor="hand2").pack(fill="x", pady=(10, 0))
        self._popup_prep(win)

    def _eisen_move(self):
        if not self._eisen_need_sel("Move"):
            return
        t = self.eisen_sel

        def choose(q, win):
            t["quadrant"] = q
            t["updated_at"] = _now_iso()
            save_tasks(self.eisen_data)
            log_event("task_moved", f"{t.get('title', '')} -> {q}", kind="user", quadrant=q)
            win.destroy()
            self._eisen_refresh(reload=False)
            self._flash(f"Moved: {t.get('title', '')}")
        self._eisen_quad_chooser(t.get("title", ""), choose)



def keep_dashboard_in_background(root):
    """Keep the dashboard as the desktop/background layer.

    Startup-only desktop hints were not enough on the live openbox laptop:
    clicking the dashboard still pushed the terminal/browser behind it. Keep the
    no-idle-polling behavior, but add an event-driven restore after dashboard
    clicks/focus so the user's last normal window comes right back to the top.
    """
    if os.environ.get("AI_OS_DASHBOARD_BACKGROUND", "1") == "0":
        return

    def dashboard_ids():
        ids = []
        try:
            ids.append(str(root.winfo_id()))
        except Exception:
            pass
        # Tk's internal winfo_id can be a wrapper/child, not the real top-level
        # managed by openbox. Search the title too, but ONLY keep Tk windows.
        # Terminals/apps may also be titled "Ascended Barron" and must remain
        # normal windows above the desktop layer.
        if shutil.which("xdotool"):
            try:
                out = subprocess.check_output(["xdotool", "search", "--name",
                                               "Ascended Barron"],
                                              text=True, stderr=subprocess.DEVNULL,
                                              timeout=2)
                ids.extend([line.strip() for line in out.splitlines() if line.strip()])
            except Exception:
                pass
        clean = []
        for wid in dict.fromkeys(ids):
            if not wid:
                continue
            cls = window_prop(wid, "WM_CLASS").lower()
            name = ""
            if shutil.which("xdotool"):
                try:
                    name = subprocess.check_output(["xdotool", "getwindowname", str(wid)],
                                                   text=True, stderr=subprocess.DEVNULL,
                                                   timeout=1).strip().lower()
                except Exception:
                    name = ""
            if '"tk"' in cls or "ai-os-dashboard" in cls or ("ascended barron" in name and not cls):
                clean.append(wid)
        return clean

    def window_prop(wid, prop):
        if not shutil.which("xprop"):
            return ""
        try:
            return subprocess.check_output(["xprop", "-id", str(wid), prop],
                                           text=True, stderr=subprocess.DEVNULL,
                                           timeout=1)
        except Exception:
            return ""

    def root_stacking_order():
        if not shutil.which("xprop"):
            return []
        try:
            out = subprocess.check_output(["xprop", "-root", "_NET_CLIENT_LIST_STACKING"],
                                          text=True, stderr=subprocess.DEVNULL,
                                          timeout=1)
        except Exception:
            return []
        if "#" not in out:
            return []
        ids = []
        for token in out.split("#", 1)[1].replace(",", " ").split():
            token = token.strip()
            if not token:
                continue
            try:
                ids.append(str(int(token, 16)))
            except Exception:
                pass
        return ids

    def is_normal_user_window(wid, dash_set):
        if wid in dash_set:
            return False
        wtype = window_prop(wid, "_NET_WM_WINDOW_TYPE").lower()
        if any(blocked in wtype for blocked in ("desktop", "dock", "splash", "toolbar", "menu")):
            return False
        try:
            name = subprocess.check_output(["xdotool", "getwindowname", str(wid)],
                                           text=True, stderr=subprocess.DEVNULL,
                                           timeout=1).strip().lower()
        except Exception:
            name = ""
        cls = window_prop(wid, "WM_CLASS").lower()
        if '"tk"' in cls or "ai-os-dashboard" in cls:
            return False
        return True

    def top_normal_window(dash_set):
        top = None
        for wid in root_stacking_order():
            if is_normal_user_window(wid, dash_set):
                top = wid
        return top

    def apply_desktop_type_once():
        ids = dashboard_ids()
        for wid in ids:
            if shutil.which("xprop"):
                subprocess.run(["xprop", "-id", wid, "-f", "_NET_WM_WINDOW_TYPE",
                                "32a", "-set", "_NET_WM_WINDOW_TYPE",
                                "_NET_WM_WINDOW_TYPE_DESKTOP"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=2)
                subprocess.run(["xprop", "-id", wid, "-f", "_NET_WM_STATE",
                                "32a", "-set", "_NET_WM_STATE",
                                "_NET_WM_STATE_BELOW, _NET_WM_STATE_SKIP_TASKBAR, _NET_WM_STATE_SKIP_PAGER"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=2)
            if shutil.which("xdotool"):
                subprocess.run(["xdotool", "windowlower", wid],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=2)

    def restore_window_after_dashboard_click():
        if not shutil.which("xdotool"):
            return
        # Dashboard controls still need a moment to work. For example, the
        # volume slider lives on the dashboard footer; immediately raising a
        # browser during a drag made volume feel broken.
        if time.monotonic() < getattr(root, "_dashboard_raise_paused_until", 0):
            return
        dash_set = set(dashboard_ids())
        target = top_normal_window(dash_set)
        if not target:
            return
        try:
            subprocess.run(["xdotool", "windowmap", target, "windowraise", target,
                            "windowactivate", "--sync", target],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=3)
        except Exception:
            pass

    # Apply a short startup burst because the openbox-managed top-level may not
    # exist at the first Tk tick. After these startup attempts, stop periodic
    # polling completely.
    for delay_ms in (250, 750, 1500, 3000):
        root.after(delay_ms, apply_desktop_type_once)

    # Openbox still stacks/activates the dashboard when the user clicks it.
    # Event-driven restore fixes that exact visible bug without an idle poller.
    root.bind_all("<ButtonRelease>", lambda _e: root.after(150, restore_window_after_dashboard_click), add="+")
    root.bind("<FocusIn>", lambda _e: root.after(150, restore_window_after_dashboard_click), add="+")


def main():
    root = tk.Tk()
    # Ask Tk/X11 for a real desktop-type window before Openbox maps it.
    # The xprop fallback below re-applies this after mapping for reliability.
    try:
        root.attributes("-type", "desktop")
    except tk.TclError:
        pass
    root.geometry("1300x820")
    if os.environ.get("AI_OS_FULLSCREEN") == "1" or "--fullscreen" in os.sys.argv:
        root.attributes("-fullscreen", True)
        # The ISO runs bare X with NO window manager, so the fullscreen hint
        # above is ignored there and the window stayed at its 1300x820 request
        # — cut off on the right of the VM screen (the user hit this
        # 2026-06-06). Size it to the real screen ourselves; harmless on the
        # host, where the WM honors the hint anyway.
        root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")
    keep_dashboard_in_background(root)
    dash = Dashboard(root)
    # Optional: open a specific panel on launch (used for previews/screenshots).
    start = os.environ.get("AI_OS_START_VIEW", "").lower()
    opener = {"eisenhower": dash.open_eisenhower}.get(start)
    if opener:
        root.after(150, opener)
    # Optional: auto-open a placed app square on launch (previews/screenshots).
    start_app = os.environ.get("AI_OS_START_APP", "")
    if start_app:
        for a in dash.app_slots:
            if a["name"].lower() == start_app.lower():
                root.after(800, lambda a=a: dash._app_launch(a))
                break
    root.mainloop()


if __name__ == "__main__":
    main()
