import datetime
import json
import pathlib
import time
import uuid

from dashboard.constants import GOOD
from dashboard.paths import AI_OS_LIB_DIR, BIG_LOG_PATH, LOG_DIR, LOG_PATH

SESSION_ID = uuid.uuid4().hex[:8]
EVENTS = []

try:
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
    try:
        BIG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with BIG_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass
    return rec


def log_file_write(path, note=""):
    name = pathlib.Path(path).name
    log_event("file_write", f"wrote {name}" + (f" — {note}" if note else ""), kind="file", path=str(path))


def biglog_health_summary(max_age_seconds=300):
    """Small tester-facing BigLog health check for the AI OS dashboard."""
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
