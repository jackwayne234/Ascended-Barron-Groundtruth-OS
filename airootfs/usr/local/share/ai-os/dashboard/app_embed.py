import shutil
import subprocess
import threading
import time
from tkinter import messagebox

from dashboard.apps import app_window_match_hints, is_browser_app
from dashboard.logging_utils import log_event
from dashboard.x11_embed import embeddable, launch_app, list_x_windows, window_class


DASHBOARD_FOCUS_WINDOW_TITLE = "AI OS Dashboard"


def launch_external_app(dashboard, app, force_front=False):
    try:
        launch_app(app)
        log_event("app_launched", f"{app['name']} (own window)", kind="user",
                  source=app.get("source"))
        if force_front:
            raise_external_app_window(dashboard, app)
        dashboard._flash(f"Opened in its own window: {app['name']}")
    except Exception as e:
        log_event("app_launch_failed", f"{app['name']}: {e}", kind="system")
        messagebox.showerror("Couldn't open app",
                             f"{app['name']} wouldn't start.\n\n{e}")


def raise_external_app_window(_dashboard, app):
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


def embed_hunt(dashboard, name, host, hid, before, klass=None):
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
    ok = embed_reparent(wid, hid) if wid else False
    dashboard.root.after(0, lambda: embed_finalize(dashboard, name, host, wid, ok))


def embed_reparent(wid, hid):
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


def embed_finalize(dashboard, name, host, wid, ok):
    try:
        alive = host.winfo_exists()
    except Exception:
        alive = False
    if not alive:
        return  # user already switched panels; _clear() handled the process
    if wid is None:
        dashboard._flash(f"{name}: no window appeared — check its own window/desktop")
        return
    if not ok:
        subprocess.run(["xdotool", "windowmap", wid], timeout=2,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        dashboard._flash(f"{name} opened in its own window")
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
                w = dashboard.root.focus_displayof()
                tk_has = w is not None and w.winfo_toplevel() is dashboard.root
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
            if tk_has or fname == DASHBOARD_FOCUS_WINDOW_TITLE:
                subprocess.run(["xdotool", "windowfocus", wid], timeout=2,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def refit_loop():
        # Desktop widgets re-apply their own saved geometry; gently put
        # them back every couple of seconds while they live in the pane.
        if not host.winfo_exists() or dashboard.embedded_wid != wid:
            return
        fit()
        dashboard.root.after(2000, refit_loop)

    def refocus_loop():
        # Focus recovery runs on its own FAST cadence (2s felt like dead
        # keyboard while signing in to Chrome — typing must come back
        # well under half a second).
        if not host.winfo_exists() or dashboard.embedded_wid != wid:
            return
        refocus()
        dashboard.root.after(400, refocus_loop)

    host.bind("<Configure>", fit)
    dashboard.embedded_wid = wid
    fit()
    # First focus hand-off so typing works immediately (sudo prompts etc.).
    subprocess.run(["xdotool", "windowfocus", wid], timeout=2,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    refit_loop()
    refocus_loop()
    log_event("app_embedded", f"{name} embedded in right pane", kind="system")
    dashboard._flash(f"{name} is running here")
