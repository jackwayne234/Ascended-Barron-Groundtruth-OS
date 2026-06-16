import datetime
import tkinter as tk


def build_eisenhower_action_bar(parent, panel_bg, ink, body, accent, accent2, font_name,
                                on_add, on_open_terminal, on_done, on_move, on_done_tasks, on_delete):
    bar = tk.Frame(parent, bg=panel_bg)
    bar.pack(fill="x", padx=8, pady=(8, 2))

    def add_button(text, cmd, color="#13233c"):
        tk.Button(bar, text=text, command=cmd, bg=color, fg=ink,
                  activebackground=accent, activeforeground=ink, relief="raised", bd=2,
                  font=(font_name, 10, "bold"), padx=10, pady=5, cursor="hand2").pack(side="left", padx=3)

    add_button("+ Add Task", on_add, accent2)
    add_button("Open Project Terminal", on_open_terminal, accent)
    add_button("✓ Mark Done", on_done)
    add_button("↔ Move", on_move)
    add_button("Done Tasks", on_done_tasks)
    add_button("Delete", on_delete, "#7f1d1d")
    return bar


def build_eisenhower_grid(parent, quads, panel_bg, ink, body, accent, font_name, on_select):
    grid = tk.Frame(parent, bg=panel_bg)
    grid.pack(fill="both", expand=True, padx=8, pady=8)
    lists = {}
    for i, (key, title, sub, color) in enumerate(quads):
        quad = tk.Frame(grid, bg=panel_bg, highlightbackground=color, highlightthickness=2)
        quad.grid(row=i // 2, column=i % 2, sticky="nsew", padx=6, pady=6)
        head = tk.Frame(quad, bg=color)
        head.pack(fill="x")
        tk.Label(head, text=title, bg=color, fg=ink, font=(font_name, 12, "bold"),
                 pady=5, padx=10, anchor="w").pack(side="left")
        tk.Label(head, text=sub, bg=color, fg="#e5e7eb", font=(font_name, 8),
                 pady=5, padx=6).pack(side="right")
        lb = tk.Listbox(quad, bg="#0b1626", fg=body, font=(font_name, 11),
                        selectbackground=accent, selectforeground=ink,
                        relief="flat", highlightthickness=0, activestyle="none")
        sb = tk.Scrollbar(quad, orient="vertical", command=lb.yview,
                          bg="#ffffff", troughcolor="#334155",
                          activebackground="#e5e7eb", borderwidth=1,
                          relief="raised", width=18, highlightthickness=1)
        lb.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(2, 5), pady=5)
        lb.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        lb.bind("<<ListboxSelect>>", lambda _e, qkey=key: on_select(qkey))
        lb.bind("<Double-Button-1>", lambda _e, qkey=key: on_select(qkey))
        lists[key] = lb
    for r in range(2):
        grid.rowconfigure(r, weight=1)
    for c in range(2):
        grid.columnconfigure(c, weight=1)
    return grid, lists


def populate_eisenhower_lists(eisen_lists, eisen_index, quads, tasks_by_quad):
    for key, *_ in quads:
        lb = eisen_lists[key]
        lb.delete(0, "end")
        items = tasks_by_quad[key]
        eisen_index[key] = items
        for task in items:
            lb.insert("end", "  " + task.get("title", "Untitled"))


def build_quadrant_chooser(win, title_text, quads, panel_bg, ink, body, font_name, on_choose):
    tk.Label(win, text=title_text, bg=panel_bg, fg=ink, font=(font_name, 12, "bold"),
             wraplength=380).pack(anchor="w", pady=(0, 10))
    for key, title, sub, color in quads:
        tk.Button(win, text=f"{title} — {sub}", command=lambda q=key: on_choose(q, win),
                  bg=color, fg=ink, font=(font_name, 11, "bold"), relief="raised", bd=2,
                  padx=10, pady=8, cursor="hand2").pack(fill="x", pady=4)
    tk.Button(win, text="Cancel", command=win.destroy, bg="#13233c", fg=body,
              font=(font_name, 10, "bold"), relief="raised", bd=2, padx=10, pady=6,
              cursor="hand2").pack(fill="x", pady=(10, 0))


def done_task_preview(task):
    for key in ("notes", "description", "details", "body"):
        raw = str(task.get(key) or "").strip()
        if raw:
            return " ".join(raw.split())[:80]
    return ""


def format_done_at(task):
    raw = task.get("completed_at") or ""
    if not raw:
        return "completed date unknown"
    try:
        dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return raw[:16]


def done_task_matches(task, query):
    if not query:
        return True
    haystack = " ".join(str(task.get(k) or "") for k in ("title", "notes", "description", "details", "quadrant"))
    return query.lower() in haystack.lower()


def render_done_task_list(listbox, empty_label, done_tasks, query, quad_labels):
    visible = []
    listbox.delete(0, "end")
    for task in done_tasks:
        if not done_task_matches(task, query):
            continue
        visible.append(task)
        title = task.get("title", "Untitled")
        quad = quad_labels.get(task.get("quadrant"), task.get("quadrant", "Unknown"))
        extra = done_task_preview(task)
        line = f"{title}  ·  {quad}  ·  {format_done_at(task)}"
        if extra:
            line += f"  ·  {extra}"
        listbox.insert("end", line)
    if visible:
        empty_label.pack_forget()
        if not listbox.winfo_ismapped():
            listbox.pack(fill="both", expand=True)
        listbox.selection_clear(0, "end")
        listbox.selection_set(0)
    else:
        listbox.pack_forget()
        empty_label.config(text="No done tasks yet" if not done_tasks else "No matching done tasks")
        empty_label.pack(fill="x")
    return visible
