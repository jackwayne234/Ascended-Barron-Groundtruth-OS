import tkinter as tk
from tkinter import messagebox

from dashboard.app_grid_ui import (
    archiveable_builtin_apps,
    build_app_pick_choices,
    create_choice_listbox,
    render_app_tiles,
)
from dashboard.apps import (
    MIN_APP_SQUARES,
    load_archived_builtins,
    save_app_slots,
    save_archived_builtins,
    scan_desktop_apps,
)
from dashboard.logging_utils import log_event


def builtin_apps(dashboard):
    # key, label, command, archiveable. Keys are stable so archived choices
    # survive dashboard restarts and future label tweaks.
    return [
        ("todo_list", "To-Do List", dashboard.open_eisenhower, False),
    ]


def builtin_by_key(dashboard):
    return {key: (name, cmd, archiveable) for key, name, cmd, archiveable in builtin_apps(dashboard)}


def archive_builtin_key(dashboard, key, name):
    archived = load_archived_builtins()
    if key not in archived:
        archived.append(key)
        save_archived_builtins(archived)
        log_event("builtin_app_archived", name, kind="user", key=key)
    dashboard._draw_app_tiles()
    dashboard._flash(f"Archived: {name}")


def restore_builtin_key(dashboard, key):
    by_key = builtin_by_key(dashboard)
    if key not in by_key:
        return
    name, _cmd, _archiveable = by_key[key]
    archived = [k for k in load_archived_builtins() if k != key]
    save_archived_builtins(archived)
    log_event("builtin_app_restored", name, kind="user", key=key)
    dashboard._draw_app_tiles()
    dashboard._flash(f"Added back: {name}")


def archive_apps_dialog(dashboard, panel_bg, ink_fg, body_fg, accent_bg, accent2_bg, font_name):
    archiveable = archiveable_builtin_apps(builtin_apps(dashboard), load_archived_builtins())
    win = tk.Toplevel(dashboard.root)
    win.title("Archive Apps")
    win.configure(bg=panel_bg, padx=18, pady=18)
    tk.Label(
        win,
        text="Pick app buttons to tuck away.\nArchived apps disappear from Apps, but show up in Add App.",
        bg=panel_bg,
        fg=ink_fg,
        font=(font_name, 11, "bold"),
        justify="left",
    ).pack(anchor="w")
    if not archiveable:
        tk.Label(
            win,
            text="No archiveable app buttons are currently visible.",
            bg=panel_bg,
            fg=body_fg,
            font=(font_name, 11),
            justify="left",
        ).pack(anchor="w", pady=10)
    else:
        choices = [{"kind": "builtin", "key": key, "name": name} for key, name in archiveable]
        lb = create_choice_listbox(win, choices, body_fg, accent_bg, ink_fg, font_name, width=42)
        lb.pack(fill="both", expand=True, pady=10)

        def archive_selected(_e=None):
            sel = lb.curselection()
            if not sel:
                messagebox.showinfo("Archive Apps", "Click an app first.", parent=win)
                return
            key, name = archiveable[sel[0]]
            win.destroy()
            archive_builtin_key(dashboard, key, name)

        lb.bind("<Double-Button-1>", archive_selected)
        tk.Button(
            win,
            text="Archive selected",
            command=archive_selected,
            bg=accent2_bg,
            fg=ink_fg,
            font=(font_name, 11, "bold"),
            relief="raised",
            bd=2,
            padx=10,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=(0, 6))
    tk.Button(
        win,
        text="✕ Close",
        command=win.destroy,
        bg="#13233c",
        fg=ink_fg,
        font=(font_name, 11, "bold"),
        relief="raised",
        bd=2,
        padx=10,
        pady=6,
        cursor="hand2",
    ).pack(side="right")
    dashboard._popup_prep(win)


def draw_app_tiles(dashboard, ink_fg, good_fg, muted_fg, body_fg, accent_bg, font_name):
    tp = getattr(dashboard, "tile_pady", 10)  # compact on short screens
    archived = set(load_archived_builtins())
    builtins = [
        (key, name, cmd, archiveable)
        for key, name, cmd, archiveable in builtin_apps(dashboard)
        if key not in archived
    ]
    render_app_tiles(
        dashboard.app_grid,
        builtins,
        dashboard.app_slots,
        MIN_APP_SQUARES,
        tp,
        dashboard._archive_builtin_key,
        dashboard._app_launch,
        dashboard._app_remove,
        dashboard._app_pick,
        ink_fg,
        good_fg,
        muted_fg,
        body_fg,
        accent_bg,
        font_name,
    )


def app_remove(dashboard, idx):
    app = dashboard.app_slots[idx]
    if messagebox.askyesno(
        "Clear square",
        f"Take {app['name']} off this square?\n\n(The app itself is NOT deleted — its Desktop icon stays.)",
    ):
        dashboard.app_slots.pop(idx)
        save_app_slots(dashboard.app_slots)
        log_event("app_unplaced", app["name"], kind="user")
        dashboard._draw_app_tiles()
        dashboard._flash(f"Square cleared: {app['name']}")


def app_pick(dashboard, panel_bg, ink_fg, body_fg, accent_bg, accent2_bg, good_fg, font_name):
    """Fill a square: pick one of the apps already built (Desktop icons),
    or kick off building a brand-new one with AI."""
    win = tk.Toplevel(dashboard.root)
    win.title("Add App to a Square")
    win.configure(bg=panel_bg, padx=18, pady=18)
    tk.Label(
        win,
        text=(
            "Pick an archived built-in app to add back,\n"
            "pick one of your Desktop icons, or build a new one.\n"
            "Tip: right-click a filled square to clear it."
        ),
        bg=panel_bg,
        fg=ink_fg,
        font=(font_name, 11, "bold"),
        justify="left",
    ).pack(anchor="w")
    choices = build_app_pick_choices(
        load_archived_builtins(),
        builtin_by_key(dashboard),
        scan_desktop_apps(),
        {a.get("source") for a in dashboard.app_slots},
    )
    lb = create_choice_listbox(win, choices, body_fg, accent_bg, ink_fg, font_name)
    lb.pack(fill="both", expand=True, pady=10)

    def place(_e=None):
        sel = lb.curselection()
        if not sel:
            messagebox.showinfo("Add App", "Click an app in the list first.", parent=win)
            return
        choice = choices[sel[0]]
        if choice["kind"] == "builtin":
            win.destroy()
            restore_builtin_key(dashboard, choice["key"])
            return
        app = choice["app"]
        dashboard.app_slots.append(app)
        save_app_slots(dashboard.app_slots)
        log_event("app_placed", app["name"], kind="user", source=app["source"])
        win.destroy()
        dashboard._draw_app_tiles()
        dashboard._flash(f"Placed in a square: {app['name']}")

    lb.bind("<Double-Button-1>", place)

    row = tk.Frame(win, bg=panel_bg)
    row.pack(fill="x")
    tk.Button(
        row,
        text="Place in square",
        command=place,
        bg=accent2_bg,
        fg=ink_fg,
        font=(font_name, 11, "bold"),
        relief="raised",
        bd=2,
        padx=10,
        pady=6,
        cursor="hand2",
    ).pack(side="left", padx=(0, 6))
    tk.Button(
        row,
        text="Build a new app",
        command=lambda: dashboard._app_build_new(win),
        bg=good_fg,
        fg=ink_fg,
        font=(font_name, 11, "bold"),
        relief="raised",
        bd=2,
        padx=10,
        pady=6,
        cursor="hand2",
    ).pack(side="left", padx=(0, 6))
    tk.Button(
        row,
        text="✕ Close",
        command=win.destroy,
        bg="#13233c",
        fg=ink_fg,
        font=(font_name, 11, "bold"),
        relief="raised",
        bd=2,
        padx=10,
        pady=6,
        cursor="hand2",
    ).pack(side="right")
    dashboard._popup_prep(win)
