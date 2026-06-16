import datetime
import subprocess
import time
import shutil
import tkinter as tk
from tkinter import messagebox

from dashboard.connectivity import wifi_indicator
from dashboard.logging_utils import biglog_health_summary, format_biglog_badge, log_event
from dashboard.system_checks import (
    cpu_percent_from,
    fmt_pct,
    fmt_ram_available,
    fmt_storage_free,
    format_battery_indicator,
    read_battery_status,
    read_cpu_times,
    read_disk_status,
    read_memory_status,
    resource_color,
)
from dashboard.ui_helpers import resource_details_message
from dashboard.x11_embed import embeddable, window_class


def wifi_tick(dashboard):
    text, color = wifi_indicator()
    if hasattr(dashboard, "wifi_status"):
        dashboard.wifi_status.set(text)
    if hasattr(dashboard, "wifi_label"):
        dashboard.wifi_label.configure(fg=color)
    dashboard.root.after(6000, dashboard._wifi_tick)


def resource_tick(dashboard):
    cur = read_cpu_times()
    cpu = cpu_percent_from(getattr(dashboard, "_cpu_prev", None), cur)
    dashboard._cpu_prev = cur
    mem_status = read_memory_status()
    disk_status = read_disk_status("/")
    parts = [fmt_pct("CPU", cpu), fmt_ram_available(mem_status), fmt_storage_free(disk_status)]
    if hasattr(dashboard, "resource_status"):
        dashboard.resource_status.set("  •  ".join(parts))
    if hasattr(dashboard, "resource_label"):
        dashboard.resource_label.configure(fg=resource_color(cpu, mem_status, disk_status, None))
    dashboard.root.after(2000, dashboard._resource_tick)


def show_resource_details(dashboard):
    cpu = fmt_pct("CPU", cpu_percent_from(getattr(dashboard, "_cpu_prev", None), read_cpu_times()))
    mem_status = read_memory_status()
    mem = fmt_ram_available(mem_status)
    disk_status = read_disk_status("/")
    disk = fmt_storage_free(disk_status)
    msg = resource_details_message(cpu, mem_status, mem, disk, disk_status)
    messagebox.showinfo("Resources", msg, parent=dashboard.root)


def biglog_refresh(dashboard, muted_fg):
    summary = biglog_health_summary()
    if hasattr(dashboard, "biglog_status"):
        dashboard.biglog_status.set(format_biglog_badge(summary))
    if hasattr(dashboard, "biglog_label"):
        dashboard.biglog_label.configure(fg=summary.get("color", muted_fg))
    dashboard._biglog_last_summary = summary
    dashboard.root.after(10000, dashboard._biglog_refresh)


def biglog_test_now(dashboard, muted_fg):
    rec = log_event("biglog_test", "User clicked BigLog test on AI OS dashboard", kind="system", test_source="dashboard_click")
    summary = biglog_health_summary(max_age_seconds=60)
    dashboard._biglog_last_summary = summary
    if hasattr(dashboard, "biglog_status"):
        dashboard.biglog_status.set(format_biglog_badge(summary))
    if hasattr(dashboard, "biglog_label"):
        dashboard.biglog_label.configure(fg=summary.get("color", muted_fg))
    msg = (
        "BigLog training-data capture\n\n"
        f"State: {summary.get('state')}\n"
        f"Records: {summary.get('records')}\n"
        f"Last action: {summary.get('last_action')}\n"
        f"Test record id: {rec.get('record_id')}\n\n"
        f"Path:\n{summary.get('path')}\n\n"
        "Scope: dashboard actions are logged here. AI conversations started from a project terminal are captured as local session transcripts (any AI). Folder actions are logged when done through the dashboard, watchers, or imported tool logs."
    )
    messagebox.showinfo("BigLog status", msg, parent=dashboard.root)
    dashboard._flash(f"BigLog test: {summary.get('state')}")


def tick(dashboard):
    dashboard.clock.set(datetime.datetime.now().strftime("%A %d %B %Y  ·  %I:%M %p"))
    if hasattr(dashboard, "battery"):
        cap, status = read_battery_status()
        dashboard.battery.set(format_battery_indicator(cap, status))
    dashboard.root.after(5000, dashboard._tick)


def pick_timezone(dashboard, head_bg, ink_fg, muted_fg, body_fg, accent_bg, accent2_bg, font_name):
    try:
        zones = subprocess.check_output(["timedatectl", "list-timezones"], text=True).split()
    except Exception as e:
        messagebox.showerror("Timezone", f"Couldn't list timezones:\n\n{e}", parent=dashboard.root)
        return
    try:
        current = subprocess.check_output(["timedatectl", "show", "-p", "Timezone", "--value"], text=True).strip()
    except Exception:
        current = ""
    win = tk.Toplevel(dashboard.root)
    win.title("Choose timezone")
    win.configure(bg=head_bg)
    tk.Label(win, text="Pick your timezone", bg=head_bg, fg=ink_fg,
             font=(font_name, 14, "bold")).pack(padx=16, pady=(14, 2))
    tk.Label(win, text=f"Current: {current or 'unknown'}   ·   type to filter (e.g. New_York)",
             bg=head_bg, fg=muted_fg, font=(font_name, 10)).pack(padx=16, pady=(0, 6))
    fvar = tk.StringVar()
    ent = tk.Entry(win, textvariable=fvar, bg="#0b1a2e", fg=ink_fg, insertbackground=ink_fg,
                   font=(font_name, 11), relief="flat")
    ent.pack(fill="x", padx=16, pady=4)
    ent.focus_set()
    lb = tk.Listbox(win, bg="#0b1a2e", fg=ink_fg, font=(font_name, 10), height=15,
                    selectbackground=accent_bg, activestyle="none", highlightthickness=0)
    lb.pack(fill="both", expand=True, padx=16, pady=6)

    def refill(*_):
        f = fvar.get().strip().lower().replace(" ", "_")
        lb.delete(0, "end")
        for z in zones:
            if f in z.lower():
                lb.insert("end", z)
        if current in lb.get(0, "end"):
            idx = list(lb.get(0, "end")).index(current)
            lb.selection_set(idx)
            lb.see(idx)

    refill()
    fvar.trace_add("write", refill)

    def apply(_e=None):
        sel = lb.curselection()
        tz = lb.get(sel[0]) if sel else fvar.get().strip()
        if tz not in zones:
            messagebox.showinfo("Timezone", "Pick a timezone from the list.", parent=win)
            return
        try:
            subprocess.run(["sudo", "timedatectl", "set-timezone", tz], check=True)
            log_event("timezone_set", f"user set timezone to {tz}", kind="user")
            dashboard.clock.set(datetime.datetime.now().strftime("%A %d %B %Y  ·  %I:%M %p"))
            dashboard._flash(f"Timezone set to {tz}")
            win.destroy()
        except Exception as e:
            messagebox.showerror("Timezone", f"Couldn't set timezone:\n\n{e}", parent=win)

    lb.bind("<Double-Button-1>", apply)
    ent.bind("<Return>", apply)
    btns = tk.Frame(win, bg=head_bg)
    btns.pack(fill="x", padx=16, pady=12)
    tk.Button(btns, text="Set timezone", command=apply, bg=accent2_bg, fg=ink_fg,
              font=(font_name, 10, "bold"), relief="raised", bd=2, padx=10, pady=4,
              cursor="hand2").pack(side="left")
    tk.Button(btns, text="✕ Close", command=win.destroy, bg="#13233c", fg=body_fg,
              font=(font_name, 10, "bold"), relief="raised", bd=2, padx=10, pady=4,
              cursor="hand2").pack(side="right")
    win.geometry("440x560")


def toggle_fs(dashboard):
    dashboard.root.attributes("-fullscreen", not dashboard.root.attributes("-fullscreen"))


def relayout(dashboard, _e=None):
    if _e is not None and _e.widget is not dashboard.root:
        return
    h = dashboard.root.winfo_height()
    if h < 300:
        return
    pady = 10 if h >= 1300 else 5
    if pady == getattr(dashboard, "_layout_key", None):
        return
    dashboard._layout_key = pady
    dashboard.tile_pady = pady
    dashboard._draw_app_tiles()
