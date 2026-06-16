import tkinter as tk
from typing import Literal


def render_update_banner(update_banner, status_bar, latest, should_show,
                         on_update, on_dismiss, amber, ink, font_name):
    for widget in update_banner.winfo_children():
        widget.destroy()
    if not should_show:
        update_banner.pack_forget()
        return
    tk.Label(update_banner,
             text=f"  A new version ({latest}) is available — open “Update OS” to get it.",
             bg=amber, fg="#1a1206", font=(font_name, 10, "bold"), anchor="w"
             ).pack(side="left", fill="x", expand=True, pady=4)
    tk.Button(update_banner, text="Update OS",
              command=on_update,
              bg="#1a1206", fg=ink, font=(font_name, 9, "bold"), relief="flat",
              padx=8, pady=1, cursor="hand2").pack(side="right", padx=(4, 6), pady=4)
    tk.Button(update_banner, text="✕", command=on_dismiss,
              bg=amber, fg="#1a1206", font=(font_name, 10, "bold"), relief="flat",
              padx=6, pady=1, cursor="hand2").pack(side="right", pady=4)
    update_banner.pack(fill="x", after=status_bar)


def settings_action_button(parent, text, cmd, ink, accent, font_name,
                           color="#13233c", state: Literal["normal", "active", "disabled"] = "normal"):
    return tk.Button(parent, text=text, command=cmd, bg=color, fg=ink,
                     activebackground=accent, activeforeground=ink, relief="raised",
                     bd=2, font=(font_name, 11, "bold"), padx=10, pady=6, cursor="hand2",
                     state=state)


def build_settings_updates_panel(content, panel_bg, ink, sub, body, muted, accent, font_name,
                                 current_version, update_check_var, on_toggle_check,
                                 on_check_now, on_update_os, on_undo, undo_state):
    wrap = tk.Frame(content, bg=panel_bg)
    wrap.pack(fill="both", expand=True, padx=20, pady=16)
    tk.Label(wrap, text="Settings", bg=panel_bg, fg=ink,
             font=(font_name, 16, "bold")).pack(anchor="w")
    tk.Label(wrap, text="Updates", bg=panel_bg, fg=sub,
             font=(font_name, 12, "bold")).pack(anchor="w", pady=(14, 4))
    tk.Label(wrap, text=f"Current version:  {current_version}",
             bg=panel_bg, fg=body, font=(font_name, 11)).pack(anchor="w", pady=2)
    tk.Checkbutton(wrap, text="Automatically check for updates (one small check on startup)",
                   variable=update_check_var, command=on_toggle_check,
                   bg=panel_bg, fg=body, selectcolor="#0b1626", activebackground=panel_bg,
                   activeforeground=ink, font=(font_name, 11), anchor="w").pack(anchor="w", pady=2)
    row = tk.Frame(wrap, bg=panel_bg)
    row.pack(anchor="w", pady=(10, 2))
    settings_action_button(row, "Check for updates now", on_check_now, ink, accent, font_name).pack(side="left", padx=(0, 6))
    settings_action_button(row, "Update OS", on_update_os, ink, accent, font_name, accent).pack(side="left", padx=6)
    row2 = tk.Frame(wrap, bg=panel_bg)
    row2.pack(anchor="w", pady=(8, 2))
    settings_action_button(row2, "Undo last update", on_undo, ink, accent, font_name, "#7c2d12", undo_state).pack(side="left")
    tk.Label(row2, text=("" if undo_state == "normal" else "  (nothing to undo yet)"),
             bg=panel_bg, fg=muted, font=(font_name, 10)).pack(side="left", padx=6)
    return wrap
