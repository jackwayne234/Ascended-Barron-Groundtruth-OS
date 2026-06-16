import os
import shutil
import subprocess
import time


def keep_dashboard_in_background(root):
    """Keep the dashboard as the desktop/background layer.

    Startup-only desktop hints were not enough on the live openbox laptop:
    clicking the dashboard could still push the terminal/browser behind it.
    Keep the no-idle-polling behavior, but add an event-driven restore after
    dashboard clicks/focus so the user's last normal window comes right back to
    the top.
    """
    if os.environ.get("AI_OS_DASHBOARD_BACKGROUND", "1") == "0":
        return

    dashboard_pid = os.getpid()

    def window_prop(wid, prop):
        if not shutil.which("xprop"):
            return ""
        try:
            return subprocess.check_output(
                ["xprop", "-id", str(wid), prop],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=1,
            )
        except Exception:
            return ""

    def root_stacking_order():
        if not shutil.which("xprop"):
            return []
        try:
            out = subprocess.check_output(
                ["xprop", "-root", "_NET_CLIENT_LIST_STACKING"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=1,
            )
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

    def window_pid(wid):
        prop = window_prop(wid, "_NET_WM_PID")
        if "=" not in prop:
            return None
        try:
            return int(prop.split("=", 1)[1].strip().split()[0])
        except Exception:
            return None

    def dashboard_ids():
        ids = []
        try:
            ids.append(str(root.winfo_id()))
        except Exception:
            pass
        for wid in root_stacking_order():
            cls = window_prop(wid, "WM_CLASS").lower()
            pid = window_pid(wid)
            if pid == dashboard_pid and ('"tk"' in cls or "ai-os-dashboard" in cls):
                ids.append(wid)
        if shutil.which("xdotool"):
            try:
                out = subprocess.check_output(
                    ["xdotool", "search", "--name", "Ascended Barron"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                ids.extend([line.strip() for line in out.splitlines() if line.strip()])
            except Exception:
                pass
        clean = []
        for wid in dict.fromkeys(ids):
            if not wid:
                continue
            cls = window_prop(wid, "WM_CLASS").lower()
            pid = window_pid(wid)
            name = ""
            if shutil.which("xdotool"):
                try:
                    name = subprocess.check_output(
                        ["xdotool", "getwindowname", str(wid)],
                        text=True,
                        stderr=subprocess.DEVNULL,
                        timeout=1,
                    ).strip().lower()
                except Exception:
                    name = ""
            if '"tk"' in cls or "ai-os-dashboard" in cls or (pid == dashboard_pid and "ascended barron" in name):
                clean.append(wid)
        return clean

    def is_normal_user_window(wid, dash_set):
        if wid in dash_set:
            return False
        wtype = window_prop(wid, "_NET_WM_WINDOW_TYPE").lower()
        if any(blocked in wtype for blocked in ("desktop", "dock", "splash", "toolbar", "menu")):
            return False
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
                subprocess.run(
                    [
                        "xprop",
                        "-id",
                        wid,
                        "-f",
                        "_NET_WM_WINDOW_TYPE",
                        "32a",
                        "-set",
                        "_NET_WM_WINDOW_TYPE",
                        "_NET_WM_WINDOW_TYPE_DESKTOP",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                subprocess.run(
                    [
                        "xprop",
                        "-id",
                        wid,
                        "-f",
                        "_NET_WM_STATE",
                        "32a",
                        "-set",
                        "_NET_WM_STATE",
                        "_NET_WM_STATE_BELOW, _NET_WM_STATE_SKIP_TASKBAR, _NET_WM_STATE_SKIP_PAGER",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
            try:
                root.lower()
            except Exception:
                pass
            if shutil.which("xdotool"):
                subprocess.run(
                    ["xdotool", "windowlower", wid],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )

    def restore_window_after_dashboard_click():
        if time.monotonic() < getattr(root, "_dashboard_raise_paused_until", 0):
            return
        apply_desktop_type_once()
        if not shutil.which("xdotool"):
            return
        dash_set = set(dashboard_ids())
        target = top_normal_window(dash_set)
        if not target:
            return
        try:
            subprocess.run(
                ["xdotool", "windowmap", target, "windowraise", target, "windowactivate", "--sync", target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
        except Exception:
            pass

    for delay_ms in (250, 750, 1500, 3000):
        root.after(delay_ms, apply_desktop_type_once)

    root.bind_all(
        "<ButtonRelease>",
        lambda _e: root.after(150, restore_window_after_dashboard_click),
        add="+",
    )
    root.bind(
        "<FocusIn>",
        lambda _e: root.after(150, restore_window_after_dashboard_click),
        add="+",
    )
