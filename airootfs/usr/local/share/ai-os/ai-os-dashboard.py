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
from tkinter import ttk, messagebox, simpledialog

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

# ---------- extracted dashboard support modules ----------
from dashboard.constants import (
    ACCENT,
    ACCENT2,
    AMBER,
    BG,
    BODY,
    FONT,
    GOOD,
    HEAD,
    INK,
    MUTED,
    PANEL,
    SUB,
    WORK_ZONE_TITLE,
)
from dashboard.app_grid_ui import build_apps_header_actions
from dashboard.apps import (
    app_available,
    is_browser_app,
    load_app_slots,
)
from dashboard.app_embed import (
    embed_finalize,
    embed_hunt,
    embed_reparent,
    launch_external_app,
    raise_external_app_window,
)
from dashboard.app_grid_actions import (
    app_pick,
    app_remove,
    archive_apps_dialog,
    archive_builtin_key,
    builtin_apps,
    builtin_by_key,
    draw_app_tiles,
    restore_builtin_key,
)
from dashboard.eisenhower_actions import (
    eisen_active,
    eisen_add,
    eisen_delete,
    eisen_done,
    eisen_move,
    eisen_need_sel,
    eisen_on_select,
    eisen_quad_chooser,
    eisen_refresh,
    eisen_select_task_by_id,
    eisen_show_done_tasks,
    open_eisenhower as open_eisenhower_panel,
)
from dashboard.logging_utils import (
    log_event,
    log_file_write,
)
from dashboard.paths import (
    EMBED,
    HOME,
    INSTALLER_PATH,
    SESSIONS_DIR,
)
from dashboard.panels import build_footer as build_dashboard_footer, open_settings as open_settings_panel
from dashboard.terminal_support import find_terminal, x11_env
from dashboard.settings import get_setting, set_setting
from dashboard.settings_ui import render_update_banner
from dashboard.tasks import (
    _now_iso,
    build_agents_md,
    ensure_ground_truth,
    load_tasks,
    project_folder_for_task,
    safe_folder_name,
    save_tasks,
)
from dashboard.ui_helpers import (
    build_titled_box,
    flash_status,
    prepare_popup,
)
from dashboard.ui_runtime import (
    biglog_refresh,
    biglog_test_now,
    pick_timezone,
    relayout as relayout_dashboard,
    resource_tick,
    show_resource_details,
    tick as dashboard_tick,
    toggle_fs,
    wifi_tick,
)
from dashboard.updates import (
    has_update_backup,
    installed_version_str,
    latest_remote_release,
    parse_version,
)
from dashboard.weather_support import WAPP
from dashboard.weather_ui import compose_forecast_run, set_canvas_message
from dashboard.work_zone import open_setup_script as work_zone_open_setup_script, show_welcome as work_zone_show_welcome
from dashboard.x11_embed import embeddable, launch_app, list_x_windows, window_class



# ---------- app squares ----------

# The Apps grid squares hold REAL apps. Every .desktop icon on the Desktop (the
# apps the user already built) can be placed into a square; new apps
# can be added once their icon lands on the Desktop. Placements persist in apps.json.
# In VM mode the dashboard dir is read-only squashfs, so persisted app-square
# placements live in the writable state dir; on the host apps.json stays beside
# the script exactly as before (host behavior unchanged).

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
        latest = getattr(self, "latest_version", None)
        dismissed = get_setting("banner_dismissed_version", "")
        should_show = bool(getattr(self, "update_available", False) and latest and dismissed != latest)
        render_update_banner(
            self.update_banner,
            self.status_bar,
            latest,
            should_show,
            lambda: self.open_setup_script("Update OS", "/usr/local/bin/ai-os-update"),
            self._dismiss_update_banner,
            AMBER,
            INK,
            FONT,
        )

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
        return open_settings_panel(self, PANEL, INK, SUB, BODY, MUTED, ACCENT, FONT)

    # ---- footer: volume + power controls ----
    def _build_footer(self, root):
        return build_dashboard_footer(self, root, HEAD, BODY, GOOD, INK, SUB, MUTED, FONT)

    def _wifi_tick(self):
        return wifi_tick(self)

    def _resource_tick(self):
        return resource_tick(self)

    def _show_resource_details(self, _e=None):
        return show_resource_details(self)

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
        """Launch the guarded install-to-external-drive flow (C10) in a terminal.

        This is only the launcher + a first 'are you sure' gate. ALL of the
        disk selection and the real safety confirmations (refuse the live
        medium / in-use disks, type the exact disk name, type ERASE) live in
        the installer itself, so they happen in the terminal where the user can
        read them. The installed system boots straight to the dashboard as the
        single user 'barron' — no login, no password (locked decision)."""
        installer = shutil.which("ai-os-install-to-disk") or INSTALLER_PATH
        if not os.path.exists(installer):
            messagebox.showerror("Install to external drive",
                                 "The installer isn't available on this system.",
                                 parent=self.root)
            return
        if not messagebox.askyesno(
                "Install to external drive",
                "Install Ascended Barron: GroundTruth OS onto an external drive?\n\n"
                "A terminal will open and guide you. It ERASES the external drive you "
                "choose — but nothing is touched until you pick a drive and "
                "type ERASE to confirm.\n\n"
                "The installed system boots straight to the dashboard: no "
                "login and no password (you can add one later).",
                parent=self.root):
            log_event("install_to_external_drive_cancelled", "user declined at first prompt", kind="user")
            return
        log_event("install_to_external_drive", "user launched the external-drive installer", kind="user")
        shell_command = (f"sudo {shlex.quote(installer)}; "
                         "echo; read -rp 'Press Enter to close this window...' _")
        args = find_terminal(shell_command)
        if not args:
            messagebox.showerror("Install to external drive",
                                 "No terminal emulator is installed to run the installer.",
                                 parent=self.root)
            return
        try:
            subprocess.Popen(args, start_new_session=True, env=x11_env())
        except Exception as e:
            messagebox.showerror("Install to external drive",
                                 f"Couldn't start the installer:\n\n{e}", parent=self.root)

    # ---- helpers ----
    def _biglog_refresh(self):
        return biglog_refresh(self, MUTED)

    def _biglog_test_now(self, _e=None):
        return biglog_test_now(self, MUTED)

    def _tick(self):
        return dashboard_tick(self)

    def _pick_timezone(self, _e=None):
        return pick_timezone(self, HEAD, INK, MUTED, BODY, ACCENT, ACCENT2, FONT)

    def _toggle_fs(self, _e=None):
        return toggle_fs(self)

    def _relayout(self, _e=None):
        return relayout_dashboard(self, _e=_e)

    def _flash(self, msg):
        flash_status(self.root, self.status, self.status_bar, msg, GOOD)

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
        prepare_popup(self.root, win)

    def _box(self, parent, title, header_right=None):
        return build_titled_box(parent, title, PANEL, HEAD, INK, FONT, header_right=header_right)

    def _work_zone_default_title(self):
        return WORK_ZONE_TITLE

    # ---- sidebar: app tiles ----
    def _build_app_grid(self, parent):
        box = self._box(
            parent,
            "Apps",
            header_right=lambda host: build_apps_header_actions(
                host,
                self._archive_apps_dialog,
                lambda: self._app_build_new(None),
                INK,
                ACCENT,
                FONT,
            ),
        )
        # Takes the whole sidebar below the to-do list (the weather moved to a
        # bottom ticker) — room for many more app squares.
        box.pack(fill="both", expand=True, pady=(0, 10))
        self.app_grid = tk.Frame(box, bg=PANEL)
        self.app_grid.pack(fill="x", padx=8, pady=8)
        self.app_slots = load_app_slots()
        self._draw_app_tiles()

    def _builtin_apps(self):
        return builtin_apps(self)

    def _builtin_by_key(self):
        return builtin_by_key(self)

    def _archive_builtin_key(self, key, name):
        return archive_builtin_key(self, key, name)

    def _restore_builtin_key(self, key):
        return restore_builtin_key(self, key)

    def _archive_apps_dialog(self):
        return archive_apps_dialog(self, PANEL, INK, BODY, ACCENT, ACCENT2, FONT)

    def _draw_app_tiles(self):
        return draw_app_tiles(self, INK, GOOD, MUTED, BODY, ACCENT, FONT)

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
        return launch_external_app(self, app, force_front=force_front)

    def _raise_external_app_window(self, app):
        return raise_external_app_window(self, app)

    def _embed_hunt(self, name, host, hid, before, klass=None):
        return embed_hunt(self, name, host, hid, before, klass=klass)

    def _embed_reparent(self, wid, hid):
        return embed_reparent(wid, hid)

    def _embed_finalize(self, name, host, wid, ok):
        return embed_finalize(self, name, host, wid, ok)

    def _app_remove(self, idx):
        return app_remove(self, idx)

    def _app_pick(self):
        return app_pick(self, PANEL, INK, BODY, ACCENT, ACCENT2, GOOD, FONT)

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
        set_canvas_message(self.fc_canvas, msg, MUTED, FONT)

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
                try:
                    self.root.after(delay_ms,
                                    lambda: threading.Thread(target=self._fc_fetch,
                                                             daemon=True).start())
                except (RuntimeError, tk.TclError):
                    return
            except Exception:
                pass
        try:
            self.root.after(0, apply)
        except (RuntimeError, tk.TclError):
            return

    def _fc_compose(self, c, x0, d, h):
        """Draw one run of the ticker line starting at x0; return its end x."""
        draw_data = dict(d)
        draw_data["forecast"] = [dict(day, date_obj=datetime.datetime.strptime(day["date"], "%Y-%m-%d"))
                                 for day in d.get("forecast", [])[:7]]
        return compose_forecast_run(c, x0, draw_data, h, WAPP)

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
        return work_zone_open_setup_script(self, title, script_path, PANEL, BODY, FONT)

    def show_welcome(self):
        return work_zone_show_welcome(self, PANEL, BODY, FONT)

    # ---- Eisenhower full matrix (opens in the right pane) ----
    def open_eisenhower(self):
        return open_eisenhower_panel(self, WORK_ZONE_TITLE, PANEL, INK, BODY, MUTED, ACCENT, ACCENT2, FONT)

    def _eisen_active(self, key):
        return eisen_active(self, key)

    def _eisen_refresh(self, reload=True):
        return eisen_refresh(self, reload=reload)

    def _eisen_on_select(self, key):
        return eisen_on_select(self, key)

    def _eisen_need_sel(self, what):
        return eisen_need_sel(self, what)

    def _eisen_quad_chooser(self, title_text, on_choose):
        return eisen_quad_chooser(self, title_text, on_choose, PANEL, INK, BODY, FONT)

    def _eisen_add(self):
        return eisen_add(self, PANEL, INK, BODY, FONT)

    def _eisen_delete(self):
        return eisen_delete(self)

    def _eisen_done(self):
        return eisen_done(self)

    def _eisen_select_task_by_id(self, task_id):
        return eisen_select_task_by_id(self, task_id)

    def _eisen_show_done_tasks(self):
        return eisen_show_done_tasks(self, PANEL, INK, BODY, MUTED, ACCENT, FONT)

    def _eisen_move(self):
        return eisen_move(self, PANEL, INK, BODY, FONT)



def keep_dashboard_in_background(root):
    """Keep the dashboard as the desktop/background layer.

    Startup-only desktop hints were not enough on the live openbox laptop:
    clicking the dashboard still pushed the terminal/browser behind it. Keep the
    no-idle-polling behavior, but add an event-driven restore after dashboard
    clicks/focus so the user's last normal window comes right back to the top.
    """
    if os.environ.get("AI_OS_DASHBOARD_BACKGROUND", "1") == "0":
        return

    dashboard_pid = os.getpid()

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
        # Tk's internal winfo_id can be a wrapper/child, not the real top-level
        # managed by openbox. Discover the openbox-managed client list via xprop
        # so the real dashboard top-level is still found even when xdotool is not
        # installed on the live laptop.
        for wid in root_stacking_order():
            cls = window_prop(wid, "WM_CLASS").lower()
            pid = window_pid(wid)
            if pid == dashboard_pid and ('"tk"' in cls or "ai-os-dashboard" in cls):
                ids.append(wid)
        # Title search is only a fallback, and ONLY Tk-ish windows survive the
        # later filter. Terminals/apps may intentionally share the title.
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
            pid = window_pid(wid)
            name = ""
            if shutil.which("xdotool"):
                try:
                    name = subprocess.check_output(["xdotool", "getwindowname", str(wid)],
                                                   text=True, stderr=subprocess.DEVNULL,
                                                   timeout=1).strip().lower()
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
            try:
                root.lower()
            except Exception:
                pass
            if shutil.which("xdotool"):
                subprocess.run(["xdotool", "windowlower", wid],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=2)

    def restore_window_after_dashboard_click():
        # Dashboard controls still need a moment to work. For example, the
        # volume slider lives on the dashboard footer; immediately raising a
        # browser during a drag made volume feel broken.
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
    wants_fullscreen = os.environ.get("AI_OS_FULLSCREEN") == "1" or "--fullscreen" in sys.argv
    if wants_fullscreen:
        # In bare X with no window manager, size the dashboard to the real screen
        # ourselves. On the openbox laptop, though, a true desktop/background
        # window should not also keep the WM's FULLSCREEN state — that can fight
        # the BELOW/SKIP_TASKBAR/SKIP_PAGER desktop-layer hints.
        root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")
        if os.environ.get("AI_OS_DASHBOARD_BACKGROUND", "1") == "0":
            root.attributes("-fullscreen", True)
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
