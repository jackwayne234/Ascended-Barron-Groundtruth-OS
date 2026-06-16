import re
import subprocess

from dashboard.paths import INSTALLED_REV_FILE, INSTALLED_VERSION_FILE, UPDATE_BACKUP_DIR, UPDATE_REPO


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
