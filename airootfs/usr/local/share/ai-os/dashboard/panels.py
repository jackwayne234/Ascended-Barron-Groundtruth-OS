import tkinter as tk
import shutil

from dashboard.logging_utils import log_event
from dashboard.settings import get_setting, set_setting
from dashboard.settings_ui import build_settings_updates_panel
from dashboard.system_checks import read_cpu_times
from dashboard.updates import has_update_backup, installed_version_str


def open_settings(dashboard, panel_bg, ink_fg, sub_fg, body_fg, muted_fg, accent_bg, font_name):
    """Settings screen — updates section only in v1.1.0 (Q43/Q56)."""
    dashboard._clear()
    dashboard.pane_title.set("Settings")
    dashboard._setting_update_check = tk.BooleanVar(value=bool(get_setting("update_check_enabled", True)))

    def toggle_check():
        on = bool(dashboard._setting_update_check.get())
        set_setting("update_check_enabled", on)
        dashboard._flash("Update checks " + ("on" if on else "off"))

    undo_state = "normal" if has_update_backup() else "disabled"
    build_settings_updates_panel(
        dashboard.content,
        panel_bg,
        ink_fg,
        sub_fg,
        body_fg,
        muted_fg,
        accent_bg,
        font_name,
        installed_version_str(),
        dashboard._setting_update_check,
        toggle_check,
        dashboard._check_updates_now,
        lambda: dashboard.open_setup_script("Update OS", "/usr/local/bin/ai-os-update"),
        dashboard._undo_last_update,
        undo_state,
    )
    log_event("settings_opened", kind="user")


def build_footer(dashboard, root, head_bg, body_fg, good_fg, ink_fg, sub_fg, muted_fg, font_name):
    """Bottom bar = the machine controls (replaced the Barron script
    router 2026-06-06): volume slider, Restart, Power Off. The power
    buttons are REAL — each one confirms before acting."""
    footer = tk.Frame(root, bg=head_bg)
    footer.pack(side="bottom", fill="x")
    tk.Label(footer, text="Esc = windowed/fullscreen     Ctrl+Q = quit",
             bg=head_bg, fg=body_fg, font=(font_name, 10), pady=6, padx=16).pack(side="left")

    dashboard.resource_status = tk.StringVar(value="CPU --  RAM avail --  Storage --")
    dashboard.resource_label = tk.Label(footer, textvariable=dashboard.resource_status,
                                        bg=head_bg, fg=good_fg, font=(font_name, 10, "bold"),
                                        pady=6, padx=10, cursor="hand2")
    dashboard.resource_label.pack(side="left", padx=(8, 4))
    dashboard.resource_label.bind("<Button-1>", dashboard._show_resource_details)
    dashboard._cpu_prev = read_cpu_times()
    dashboard.root.after(2000, dashboard._resource_tick)

    dashboard.version_label = tk.Label(footer, text=installed_version_str(),
                                       bg=head_bg, fg=muted_fg, font=(font_name, 10),
                                       pady=6, padx=10, cursor="hand2")
    dashboard.version_label.pack(side="left", padx=(4, 4))
    dashboard.version_label.bind("<Button-1>", lambda _e: dashboard.open_settings())

    if shutil.which("wpctl") or shutil.which("amixer"):
        tk.Label(footer, text="Volume", bg=head_bg, fg=body_fg,
                 font=(font_name, 10)).pack(side="left", padx=(8, 4))
        dashboard.vol_var = tk.IntVar(value=dashboard._volume_read())
        dashboard._vol_after = dashboard._vol_log_after = None
        dashboard.volume_scale = tk.Scale(
            footer, from_=0, to=100, orient="horizontal", variable=dashboard.vol_var,
            command=dashboard._volume_changed, length=170, showvalue=True,
            bg=head_bg, fg=body_fg, troughcolor="#1e3a5f", highlightthickness=0,
            activebackground=sub_fg, bd=0, font=(font_name, 8), sliderrelief="raised",
            cursor="hand2"
        )
        dashboard.volume_scale.pack(side="left", pady=2)
        dashboard.volume_scale.bind("<ButtonPress-1>", dashboard._volume_capture_focus)
        dashboard.volume_scale.bind("<ButtonRelease-1>", dashboard._volume_restore_focus)

    tk.Button(footer, text="⚙ Settings",
              command=dashboard.open_settings,
              bg="#1e3a5f", fg=ink_fg, activebackground="#2563eb", activeforeground=ink_fg,
              relief="raised", bd=2, font=(font_name, 10, "bold"), padx=10, pady=4,
              cursor="hand2").pack(side="right", padx=(4, 6), pady=4)
    tk.Button(footer, text="Power Off",
              command=lambda: dashboard._power("poweroff", "Power Off"),
              bg="#7f1d1d", fg=ink_fg, activebackground="#b91c1c", activeforeground=ink_fg,
              relief="raised", bd=2, font=(font_name, 10, "bold"), padx=10, pady=4,
              cursor="hand2").pack(side="right", padx=4, pady=4)
    tk.Button(footer, text="⟳ Restart",
              command=lambda: dashboard._power("reboot", "Restart"),
              bg="#92400e", fg=ink_fg, activebackground="#b45309", activeforeground=ink_fg,
              relief="raised", bd=2, font=(font_name, 10, "bold"), padx=10, pady=4,
              cursor="hand2").pack(side="right", padx=4, pady=4)
