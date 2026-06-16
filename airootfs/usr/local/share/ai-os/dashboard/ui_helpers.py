import tkinter as tk


def flash_status(root, status_var, status_bar, msg, good_color):
    status_var.set(msg)
    status_bar.configure(bg="#16a34a", fg="#ffffff")
    root.after(600, lambda: status_bar.configure(bg="#022c22", fg=good_color))


def prepare_popup(root, win):
    """Center a popup over the dashboard and let Escape close it."""
    win.transient(root)
    win.bind("<Escape>", lambda _e: win.destroy())
    win.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - win.winfo_reqwidth()) // 2
    y = root.winfo_rooty() + (root.winfo_height() - win.winfo_reqheight()) // 3
    win.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    win.lift()
    win.focus_set()


def build_titled_box(parent, title, panel_bg, head_bg, ink, font_name, header_right=None):
    """Create a titled panel with an optional header-right widget builder."""
    box = tk.Frame(parent, bg=panel_bg, highlightbackground="#1e3a5f", highlightthickness=1)
    header = tk.Frame(box, bg=head_bg)
    header.pack(fill="x")
    tk.Label(header, text=title, bg=head_bg, fg=ink, font=(font_name, 12, "bold"),
             pady=6, padx=10, anchor="w").pack(side="left")
    if header_right is not None:
        try:
            widget = header_right(header)
            if widget is not None:
                widget.pack(side="right", padx=8, pady=4)
        except Exception:
            pass
    return box


def resource_details_message(cpu_text, mem_status, mem_text, disk_text, disk_status=None):
    if isinstance(mem_status, dict):
        mem_text += f" ({mem_status['used_pct']}% used by apps/cache/live system)"
    if isinstance(disk_status, dict):
        disk_text += f" ({disk_status['used_pct']}% used of {disk_status['total_gib']:.1f}G total)"
    return (
        "Resource Monitor\n\n"
        f"{cpu_text}\n{mem_text}\n{disk_text}\n\n"
        "Battery stays in the top-right corner. Green is fine, yellow is getting high, red needs attention. RAM shows available memory because live ISO cache can make used RAM look scary. Storage shows free space in gigabytes, while warning colors still track how full the live writable space is."
    )
