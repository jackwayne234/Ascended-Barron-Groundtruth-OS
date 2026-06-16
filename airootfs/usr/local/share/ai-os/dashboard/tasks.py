import datetime
import json
import pathlib
import uuid

from dashboard.logging_utils import log_file_write
from dashboard.paths import DASH_DIR, WORKSPACE

EISEN_APP_DIR = WORKSPACE / "Eisenhower priority matrix to do list"
QUADS = [
    ("do_first", "Do First", "Urgent + Important", "#7f1d1d"),
    ("schedule", "Schedule", "Important, Not Urgent", "#166534"),
    ("delegate", "Delegate", "Urgent, Not Important", "#92400e"),
    ("delete_later", "Low Priority", "Not Urgent, Not Important", "#334155"),
]


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def tasks_path():
    real = EISEN_APP_DIR / "tasks.json"
    if real.exists():
        return real
    return DASH_DIR / "tasks.json"


def load_tasks():
    p = tasks_path()
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            d.setdefault("tasks", [])
            return d
        except Exception:
            pass
    return {"schema_version": 1, "tasks": [
        {"id": str(uuid.uuid4()), "title": "Open Terminal in this project folder",
         "quadrant": "do_first", "completed": False, "created_at": _now_iso()},
    ]}


def eisen_done_tasks(data):
    """Return completed Eisenhower tasks, newest completed first."""
    done = [t for t in data.get("tasks", []) if t.get("completed")]
    return sorted(done, key=lambda t: t.get("completed_at") or t.get("updated_at") or "", reverse=True)


def restore_eisen_done_task(data, task_id):
    """Restore a completed task to active status and move it to the top."""
    tasks = data.setdefault("tasks", [])
    for idx, task in enumerate(tasks):
        if task.get("id") == task_id and task.get("completed"):
            task["completed"] = False
            task["completed_at"] = None
            task["updated_at"] = _now_iso()
            tasks.pop(idx)
            tasks.insert(0, task)
            return task
    return None


def save_tasks(data):
    data["updated_at"] = _now_iso()
    p = tasks_path()
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)
    log_file_write(p, f"{len(data.get('tasks', []))} tasks")


def safe_folder_name(title, tid=""):
    cleaned = title.replace("/", " ").replace("\\", " ")
    cleaned = "".join(ch for ch in cleaned if ch.isprintable())
    cleaned = " ".join(cleaned.split()).strip(" .")
    if not cleaned:
        cleaned = f"task-{(tid or 'untitled')[:8]}"
    return cleaned[:120]


def project_folder_for_task(task):
    return WORKSPACE / safe_folder_name(task.get("title", ""), task.get("id", ""))


def build_agents_md(task, folder):
    return (f"# Project Helper Rules\n\n"
            f"This folder is an AI OS project connected to an Eisenhower Matrix to-do item.\n\n"
            f"Task title: {task.get('title', 'Untitled')}\n"
            f"Task id: {task.get('id', 'unknown')}\n"
            f"Quadrant: {task.get('quadrant', 'unknown')}\n"
            f"Project folder: {folder}\n\n"
            "START HERE — every session in this folder:\n"
            "1. Read `ground-truth.md` in this folder FIRST.\n"
            "2. Follow its 'AI Start Instructions' exactly.\n"
            "3. Treat ground-truth.md as the source of truth. Record questions, answers, locked\n"
            "   decisions, and progress back into that file.\n"
            "4. Do not begin implementation until ground-truth.md shows permission was granted.\n"
            "5. Keep answers short and practical.\n")


def build_ground_truth(task, folder):
    """Generic ground-truth.md matching the workspace template (see other projects)."""
    title = task.get("title", "Untitled")
    quad = task.get("quadrant", "unknown")
    today = datetime.date.today().isoformat()
    return f"""# {title} — Ground Truth

## Purpose of This File

A `ground-truth.md` file is the project’s source of truth. It tells the AI what the project is, what decisions have already been made, what still needs to be asked, what progress has happened, and whether the AI has permission to start working. The point is to stop the AI from guessing, restarting, forgetting context, or building before you’ve approved the direction.

## AI Start Instructions

When the AI is working in this folder, it should read this file first and follow these rules:

1. If the desired outcome is missing, ask: **“What do you want the desired outcome of this project to be?”**
2. If the 25-question planning pass is incomplete, ask the next missing planning question **one question at a time**.
3. Each planning question should use short multiple-choice options when useful, with one option clearly marked **recommended**.
4. Record each planning question, options offered, recommendation, user answer, and locked decision in this file.
5. After 25 questions are answered, summarize what is known, list remaining gaps, and ask whether the information is enough.
6. If the information is enough, break the project into many small execution chunks before asking for work permission. Each chunk should be small enough to run, verify, and log independently.
7. Before doing manual work in any chunk, look for existing scripts, commands, CLIs, Makefiles, tests, or automation that can do the work deterministically. Prefer script/tool execution over AI doing repetitive work directly.
8. Record the chunk plan in this file, including chunk number, goal, likely files/scripts/tools, verification step, and status.
9. Before starting work, ask: **“Do I have your permission to start working from this ground truth and chunk plan?”**
10. Do not begin implementation, research, file changes, or project work until the user gives permission.
11. Log meaningful progress in the Progress Log section.

## Desired Outcome

_Not answered yet._

## Planning Status

- Desired outcome: Not answered yet.
- 25-question planning pass: Not started.
- Enough-information checkpoint: Not completed.
- Chunk plan: Not created yet.
- Permission to start work: Not granted yet.

## Planning Q&A Ledger

### Desired Outcome Question

**Question:** What do you want the desired outcome of this project to be?

**User answer:** Not answered yet.

**Locked decision:** Not locked yet.

## Enough-Information Checkpoint

_Not reached yet. After 25 planning questions, the AI should summarize what is known, list remaining gaps, and ask whether the information is enough._

## Chunk Plan

_Not created yet. After the enough-information checkpoint is satisfied, the AI should break the project into many small execution chunks before asking permission to start. Each chunk should include:_

- Chunk number and goal
- Likely files, scripts, commands, CLIs, or tools involved
- Whether an existing script/tool should be used or a new script should be created
- Verification step
- Status: pending, in progress, complete, blocked, or deferred

## Permission to Start

_Not granted yet. The AI should ask: “Do I have your permission to start working from this ground truth and chunk plan?”_

## Progress Log

### {today}
- Created this `ground-truth.md` automatically when the task project folder was opened from the AI OS dashboard.
- Installed the reusable template: desired outcome first, planning questions, enough-information checkpoint, small chunk plan, script-first execution preference, and explicit permission before work starts.
- Source task title: `{title}`.
- Source task quadrant: `{quad}`.
"""


def ensure_ground_truth(task, folder):
    """Write ground-truth.md only if one is not already there (never overwrite real progress)."""
    gt = folder / "ground-truth.md"
    if not gt.exists():
        gt.write_text(build_ground_truth(task, folder), encoding="utf-8")
        log_file_write(gt, "ground-truth.md created")
    return gt
