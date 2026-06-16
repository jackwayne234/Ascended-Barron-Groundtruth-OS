import tkinter as tk


def build_apps_header_actions(host, on_archive, on_create, ink, accent, font_name):
    """Pack the Apps header action buttons into the provided header frame."""
    tk.Button(host, text="Archive Apps",
              command=on_archive,
              bg="#13233c", fg=ink, activebackground=accent, activeforeground=ink,
              font=(font_name, 9, "bold"), relief="raised", bd=1,
              padx=8, pady=2, cursor="hand2").pack(side="right", padx=(0, 6), pady=4)
    tk.Button(host, text="+ Create App",
              command=on_create,
              bg="#13233c", fg=ink, activebackground=accent, activeforeground=ink,
              font=(font_name, 9, "bold"), relief="raised", bd=1,
              padx=8, pady=2, cursor="hand2").pack(side="right", padx=(4, 0), pady=4)
    return None


def archiveable_builtin_apps(builtin_apps, archived_keys):
    return [(key, name) for key, name, _cmd, archiveable in builtin_apps
            if archiveable and key not in archived_keys]


def build_app_pick_choices(archived_keys, by_key, desktop_apps, placed_sources):
    choices = []
    for key in archived_keys:
        if key in by_key:
            name, _cmd, _archiveable = by_key[key]
            choices.append({"kind": "builtin", "key": key, "name": name})
    for app in desktop_apps:
        if app["source"] not in placed_sources:
            choices.append({"kind": "desktop", "app": app, "name": app["name"]})
    return choices


def create_choice_listbox(parent, choices, body_color, accent, ink, font_name, width=48):
    lb = tk.Listbox(parent, bg="#0b1626", fg=body_color, font=(font_name, 11),
                    selectbackground=accent, selectforeground=ink,
                    relief="flat", highlightthickness=0, activestyle="none",
                    height=min(12, max(4, len(choices))), width=width)
    for choice in choices:
        prefix = "↩  " if choice.get("kind") == "builtin" else "  "
        lb.insert("end", prefix + choice["name"])
    return lb


def render_app_tiles(app_grid, builtins, app_slots, min_app_squares, tile_pady,
                     on_builtin_archive, on_app_launch, on_app_remove, on_add_app,
                     ink, good, muted, body, accent, font_name):
    for widget in app_grid.winfo_children():
        widget.destroy()
    for i, (key, name, cmd, archiveable) in enumerate(builtins):
        button = tk.Button(app_grid, text=name, command=cmd, bg="#13233c", fg=ink,
                           activebackground=accent, activeforeground=ink,
                           relief="raised", bd=2, font=(font_name, 10, "bold"),
                           padx=6, pady=tile_pady, cursor="hand2", wraplength=160)
        if archiveable:
            button.bind("<Button-3>", lambda _e, k=key, n=name: on_builtin_archive(k, n))
        button.grid(row=i // 2, column=i % 2, sticky="nsew", padx=4, pady=4)
    total_slots = max(len(app_slots) + 1, min_app_squares)
    for j in range(total_slots):
        i = len(builtins) + j
        if j < len(app_slots):
            app = app_slots[j]
            button = tk.Button(app_grid, text=app["name"],
                               command=lambda a=app: on_app_launch(a),
                               bg="#13233c", fg=good, activebackground=accent,
                               activeforeground=ink, relief="raised", bd=2,
                               font=(font_name, 10, "bold"), padx=6, pady=tile_pady,
                               cursor="hand2", wraplength=160)
            button.bind("<Button-3>", lambda _e, k=j: on_app_remove(k))
        else:
            button = tk.Button(app_grid, text="+ Add App",
                               command=on_add_app,
                               bg="#0b1626", fg=muted, activebackground="#13233c",
                               activeforeground=body, relief="ridge", bd=1,
                               font=(font_name, 9), padx=6, pady=max(tile_pady - 2, 4),
                               cursor="hand2", wraplength=160)
        button.grid(row=i // 2, column=i % 2, sticky="nsew", padx=4, pady=4)
    app_grid.columnconfigure(0, weight=1)
    app_grid.columnconfigure(1, weight=1)
