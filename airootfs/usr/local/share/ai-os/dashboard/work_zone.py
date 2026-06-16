import shlex
import shutil
import subprocess
import tkinter as tk

from dashboard.logging_utils import log_event
from dashboard.paths import EMBED, TERMINAL_PANE
from dashboard.terminal_support import find_terminal, xterm_args


WORK_ZONE_HOST_BG = "#020912"


def render_center_message(content_host, message, panel_bg, body_fg, font_name):
    wrap = tk.Frame(content_host, bg=panel_bg)
    wrap.pack(expand=True)
    tk.Label(wrap, text=message, bg=panel_bg, fg=body_fg, font=(font_name, 13),
             justify="left", wraplength=900).pack()


def open_setup_script(dashboard, title, script_path, panel_bg, body_fg, font_name):
    """Open one of the simple setup scripts as an Apps button.
    Each button runs in a real terminal so the user can see plain PASS/FAIL output."""
    dashboard._clear()
    dashboard.pane_title.set(dashboard._work_zone_default_title())
    quoted = shlex.quote(script_path)
    cmd = (
        f"if [ -x {quoted} ]; then {quoted}; "
        f"else echo 'Missing setup script: {script_path}'; read -rp 'Press Enter to close...' _; fi"
    )
    if (EMBED or TERMINAL_PANE) and shutil.which("xterm"):
        host = tk.Frame(dashboard.content, bg=WORK_ZONE_HOST_BG)
        host.pack(fill="both", expand=True)
        host.update_idletasks()
        dashboard.term_proc = subprocess.Popen(
            xterm_args(cmd, into=host.winfo_id()),
            start_new_session=True,
        )
        dashboard._flash(f"Running: {title}")
        log_event("setup_script_opened", title, kind="system", script=script_path)
        return
    args = find_terminal(cmd)
    if args:
        subprocess.Popen(args, start_new_session=True)
        dashboard._flash(f"Running: {title}")
        log_event("setup_script_opened", title, kind="system", script=script_path)
        return
    msg = f"No terminal emulator is installed, so {title} cannot run."
    render_center_message(dashboard.content, msg, panel_bg, body_fg, font_name)
    dashboard._flash("No terminal emulator found")


def show_welcome(dashboard, panel_bg, body_fg, font_name):
    # Terminals and apps open as movable windows in normal laptop mode.
    dashboard._clear()
    dashboard.pane_title.set(dashboard._work_zone_default_title())
    where = "right here" if EMBED else "in its own window"
    msg = (
        "This is empty space for your windows: open apps, terminals,\n"
        "and task work can go here. Drag windows here if you want to keep them organized.\n\n"
        f"•  Apps and task windows open {where}; use this space to arrange them.\n"
        "•  Select a task, then open a terminal in its project folder.\n\n"
        "•  Volume, Restart and Power Off live in the bottom bar.\n\n"
        "Everything you do is logged locally as training data."
    )
    render_center_message(dashboard.content, msg, panel_bg, body_fg, font_name)
