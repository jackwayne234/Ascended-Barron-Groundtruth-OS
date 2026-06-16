import pathlib
import shutil

from dashboard.constants import GOOD


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
    if capacity is None:
        return ""
    status_l = (status or "").lower()
    if (("charging" in status_l and "discharging" not in status_l)
            or "full" in status_l):
        return f"Charging {capacity}%"
    return f"Battery {capacity}%"


def read_cpu_times():
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


def read_disk_status(path="/"):
    try:
        usage = shutil.disk_usage(path)
        if usage.total <= 0:
            return None
        used_pct = max(0, min(100, round((usage.used / usage.total) * 100)))
        free_gib = usage.free / (1024 ** 3)
        total_gib = usage.total / (1024 ** 3)
        return {"used_pct": used_pct, "free_gib": free_gib, "total_gib": total_gib}
    except Exception:
        return None


def resource_color(cpu, mem_status, disk_status, battery_cap):
    vals = [v for v in (cpu,) if isinstance(v, int)]
    if isinstance(disk_status, dict):
        vals.append(disk_status.get("used_pct", 0))
    if isinstance(mem_status, dict):
        vals.append(mem_status.get("used_pct", 0))
    if battery_cap is not None:
        vals.append(100 - battery_cap)
    if any(v >= 90 for v in vals) or (battery_cap is not None and battery_cap <= 15):
        return "#f87171"
    if any(v >= 75 for v in vals) or (battery_cap is not None and battery_cap <= 30):
        return "#facc15"
    return GOOD


def fmt_pct(label, value):
    return f"{label} --" if value is None else f"{label} {value}%"


def fmt_ram_available(mem_status):
    if not isinstance(mem_status, dict):
        return "RAM avail --"
    return f"RAM avail {mem_status['avail_gib']:.1f}G"


def fmt_storage_free(disk_status):
    if not isinstance(disk_status, dict):
        return "Storage free --"
    return f"Storage free {disk_status['free_gib']:.1f}G"
