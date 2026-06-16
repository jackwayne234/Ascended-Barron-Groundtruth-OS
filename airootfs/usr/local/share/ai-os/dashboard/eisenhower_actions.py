import tkinter as tk
from tkinter import messagebox, simpledialog
import uuid

from dashboard.eisenhower_ui import (
    build_eisenhower_action_bar,
    build_eisenhower_grid,
    build_quadrant_chooser,
    populate_eisenhower_lists,
    render_done_task_list,
)
from dashboard.logging_utils import log_event
from dashboard.tasks import (
    QUADS,
    _now_iso,
    eisen_done_tasks,
    load_tasks,
    restore_eisen_done_task,
    save_tasks,
    tasks_path,
)


def open_eisenhower(dashboard, work_zone_title, panel_bg, ink_fg, body_fg, muted_fg, accent_bg, accent2_bg, font_name):
    dashboard._clear()
    dashboard.pane_title.set(work_zone_title)
    dashboard._flash("Opened Eisenhower full matrix")
    log_event("panel_opened", "Eisenhower Tasks", kind="user")
    dashboard.eisen_data = load_tasks()
    dashboard.eisen_lists = {}
    dashboard.eisen_index = {}
    dashboard.eisen_sel = None

    build_eisenhower_action_bar(
        dashboard.content,
        panel_bg,
        ink_fg,
        body_fg,
        accent_bg,
        accent2_bg,
        font_name,
        dashboard._eisen_add,
        dashboard.open_selected_project_terminal,
        dashboard._eisen_done,
        dashboard._eisen_move,
        dashboard._eisen_show_done_tasks,
        dashboard._eisen_delete,
    )

    tk.Label(
        dashboard.content,
        text='Tip: pick a task, then "Open Project Terminal" to work on it in its own folder. Everything you do is logged locally as training data.',
        bg=panel_bg,
        fg=body_fg,
        font=(font_name, 10),
        anchor="w",
        justify="left",
    ).pack(fill="x", padx=12, pady=(2, 0))

    _grid, lists = build_eisenhower_grid(
        dashboard.content,
        QUADS,
        panel_bg,
        ink_fg,
        body_fg,
        accent_bg,
        font_name,
        dashboard._eisen_on_select,
    )
    dashboard.eisen_lists = lists
    eisen_refresh(dashboard, reload=False)


def eisen_active(dashboard, key):
    return [
        t for t in dashboard.eisen_data.get("tasks", [])
        if t.get("quadrant") == key and not t.get("completed")
    ]


def eisen_refresh(dashboard, reload=True):
    if reload:
        dashboard.eisen_data = load_tasks()
    dashboard.eisen_sel = None
    if dashboard.eisen_lists:
        try:
            tasks_by_quad = {key: eisen_active(dashboard, key) for key, *_ in QUADS}
            populate_eisenhower_lists(dashboard.eisen_lists, dashboard.eisen_index, QUADS, tasks_by_quad)
        except tk.TclError:
            dashboard.eisen_lists = None
    active = sum(1 for t in dashboard.eisen_data.get("tasks", []) if not t.get("completed"))
    dashboard.status.set(f"{active} active tasks  ·  file: {tasks_path().name}")


def eisen_on_select(dashboard, key):
    if not dashboard.eisen_lists:
        return
    for k, lb in dashboard.eisen_lists.items():
        if k != key:
            lb.selection_clear(0, "end")
    sel = dashboard.eisen_lists[key].curselection()
    if sel:
        dashboard.eisen_sel = dashboard.eisen_index[key][sel[0]]
        dashboard._flash(f"Selected: {dashboard.eisen_sel.get('title', '')}")
        log_event("task_selected", dashboard.eisen_sel.get("title", ""), kind="user", quadrant=key)


def eisen_need_sel(dashboard, what):
    if not dashboard.eisen_sel:
        messagebox.showinfo(what, "Click a task to select it first.")
        return False
    return True


def eisen_quad_chooser(dashboard, title_text, on_choose, panel_bg, ink_fg, body_fg, font_name):
    win = tk.Toplevel(dashboard.root)
    win.title("Choose quadrant")
    win.configure(bg=panel_bg, padx=18, pady=18)
    build_quadrant_chooser(win, title_text, QUADS, panel_bg, ink_fg, body_fg, font_name, on_choose)
    dashboard._popup_prep(win)


def eisen_add(dashboard, panel_bg, ink_fg, body_fg, font_name):
    title = simpledialog.askstring("Add Task", "What's the task?", parent=dashboard.root)
    if not title or not title.strip():
        return

    def choose(q, win):
        dashboard.eisen_data.setdefault("tasks", []).append({
            "id": str(uuid.uuid4()), "title": title.strip(), "quadrant": q,
            "completed": False, "created_at": _now_iso(), "updated_at": _now_iso(),
            "completed_at": None,
        })
        save_tasks(dashboard.eisen_data)
        log_event("task_added", title.strip(), kind="user", quadrant=q)
        win.destroy()
        eisen_refresh(dashboard, reload=False)
        dashboard._flash(f"Added: {title.strip()}")

    eisen_quad_chooser(dashboard, f"Add: {title.strip()}", choose, panel_bg, ink_fg, body_fg, font_name)


def eisen_delete(dashboard):
    if not eisen_need_sel(dashboard, "Delete"):
        return
    t = dashboard.eisen_sel
    if messagebox.askyesno("Delete task", f"Delete this task?\n\n{t.get('title', '')}"):
        dashboard.eisen_data["tasks"] = [x for x in dashboard.eisen_data.get("tasks", []) if x.get("id") != t.get("id")]
        save_tasks(dashboard.eisen_data)
        log_event("task_deleted", t.get("title", ""), kind="user", quadrant=t.get("quadrant"))
        eisen_refresh(dashboard, reload=False)
        dashboard._flash(f"Deleted: {t.get('title', '')}")


def eisen_done(dashboard):
    if not eisen_need_sel(dashboard, "Mark Done"):
        return
    t = dashboard.eisen_sel
    t["completed"] = True
    t["completed_at"] = _now_iso()
    t["updated_at"] = _now_iso()
    save_tasks(dashboard.eisen_data)
    log_event("task_completed", t.get("title", ""), kind="user", quadrant=t.get("quadrant"))
    eisen_refresh(dashboard, reload=False)
    dashboard._flash(f"Done: {t.get('title', '')}")


def eisen_select_task_by_id(dashboard, task_id):
    if not dashboard.eisen_lists:
        return
    for key, lb in dashboard.eisen_lists.items():
        lb.selection_clear(0, "end")
        for idx, task in enumerate(dashboard.eisen_index.get(key, [])):
            if task.get("id") == task_id:
                lb.selection_set(idx)
                lb.see(idx)
                dashboard.eisen_sel = task
                return


def eisen_show_done_tasks(dashboard, panel_bg, ink_fg, body_fg, muted_fg, accent_bg, font_name):
    dashboard.eisen_data = load_tasks()
    done_tasks = eisen_done_tasks(dashboard.eisen_data)
    quad_labels = {key: title for key, title, _sub, _color in QUADS}

    win = tk.Toplevel(dashboard.root)
    win.title("Done Tasks")
    win.configure(bg=panel_bg, padx=16, pady=16)
    tk.Label(win, text="Done Tasks", bg=panel_bg, fg=ink_fg, font=(font_name, 13, "bold")).pack(anchor="w")
    tk.Label(win, text="Select a done task to restore it.", bg=panel_bg, fg=body_fg, font=(font_name, 10)).pack(anchor="w", pady=(2, 8))

    search_var = tk.StringVar()
    search = tk.Entry(win, textvariable=search_var, bg="#0b1626", fg=ink_fg, insertbackground=ink_fg, relief="flat", font=(font_name, 11))
    search.insert(0, "")
    search.pack(fill="x", pady=(0, 8))
    search.focus_set()
    tk.Label(win, text="Search done tasks", bg=panel_bg, fg=muted_fg, font=(font_name, 9)).pack(anchor="w", pady=(0, 4))

    empty = tk.Label(win, text="No done tasks yet", bg=panel_bg, fg=muted_fg, font=(font_name, 11), pady=10)
    lb = tk.Listbox(win, bg="#0b1626", fg=body_fg, font=(font_name, 10), width=72, height=12,
                    selectbackground=accent_bg, selectforeground=ink_fg,
                    relief="flat", highlightthickness=0, activestyle="none")
    visible = []

    def render(*_args):
        query = search_var.get().strip()
        visible[:] = render_done_task_list(lb, empty, done_tasks, query, quad_labels)

    def restore_selected(*_args):
        sel = lb.curselection()
        if not sel or sel[0] >= len(visible):
            return
        restored = restore_eisen_done_task(dashboard.eisen_data, visible[sel[0]].get("id"))
        if restored is None:
            return
        save_tasks(dashboard.eisen_data)
        log_event("task_restored", restored.get("title", ""), kind="user", quadrant=restored.get("quadrant"))
        win.destroy()
        eisen_refresh(dashboard, reload=False)
        eisen_select_task_by_id(dashboard, restored.get("id"))
        dashboard._flash(f"Restored: {restored.get('title', '')}")

    search_var.trace_add("write", render)
    lb.bind("<Double-Button-1>", restore_selected)
    lb.bind("<Return>", restore_selected)
    win.bind("<Return>", restore_selected)
    win.bind("<Escape>", lambda _e: win.destroy())
    render()
    tk.Button(win, text="Close", command=win.destroy, bg="#13233c", fg=body_fg,
              font=(font_name, 10, "bold"), relief="raised", bd=2, padx=10, pady=6,
              cursor="hand2").pack(fill="x", pady=(10, 0))
    dashboard._popup_prep(win)


def eisen_move(dashboard, panel_bg, ink_fg, body_fg, font_name):
    if not eisen_need_sel(dashboard, "Move"):
        return
    t = dashboard.eisen_sel

    def choose(q, win):
        t["quadrant"] = q
        t["updated_at"] = _now_iso()
        save_tasks(dashboard.eisen_data)
        log_event("task_moved", f"{t.get('title', '')} -> {q}", kind="user", quadrant=q)
        win.destroy()
        eisen_refresh(dashboard, reload=False)
        dashboard._flash(f"Moved: {t.get('title', '')}")

    eisen_quad_chooser(dashboard, t.get("title", ""), choose, panel_bg, ink_fg, body_fg, font_name)
