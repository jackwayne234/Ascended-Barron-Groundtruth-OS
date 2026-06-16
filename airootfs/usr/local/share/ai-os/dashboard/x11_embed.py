import subprocess

from dashboard.apps import app_exec_tokens
from dashboard.terminal_support import x11_env


def launch_app(app):
    """Launch a placed app exactly like double-clicking its Desktop icon,
    forced onto X11 so it can embed in the right pane."""
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
    """Never adopt the window manager's own windows."""
    cls = window_class(wid)
    return "mutter" not in cls and "gnome-shell" not in cls
