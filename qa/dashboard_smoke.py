#!/usr/bin/env python3
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import time
import traceback

REPO = pathlib.Path(__file__).resolve().parents[1]
DASH_PATH = REPO / 'airootfs/usr/local/share/ai-os/ai-os-dashboard.py'
OUT_DIR = REPO / 'qa-output' / 'dashboard-smoke'
SHOT_DIR = OUT_DIR / 'screenshots'
OUT_DIR.mkdir(parents=True, exist_ok=True)
SHOT_DIR.mkdir(parents=True, exist_ok=True)


def load_dashboard_module():
    spec = importlib.util.spec_from_file_location('ai_os_dashboard', DASH_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Could not load dashboard module from {DASH_PATH}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def capture_display(name):
    path = SHOT_DIR / f'{name}.png'
    subprocess.run(['import', '-display', os.environ['DISPLAY'], '-window', 'root', str(path)], check=True)
    return str(path)


def settle(root, delay=0.25):
    end = time.time() + delay
    while time.time() < end:
        root.update_idletasks()
        root.update()
        time.sleep(0.03)


def list_toplevels(root):
    tops = []
    for widget in root.winfo_children():
        try:
            if widget.winfo_class() == 'Toplevel':
                tops.append(widget)
        except Exception:
            pass
    return tops


def find_first_listbox(widget):
    if widget.winfo_class() == 'Listbox':
        return widget
    for child in widget.winfo_children():
        found = find_first_listbox(child)
        if found is not None:
            return found
    return None


def close_extra_toplevels(root):
    for top in list_toplevels(root):
        try:
            top.destroy()
        except Exception:
            pass
    settle(root, 0.1)


def main():
    mod = load_dashboard_module()

    dialog_log = []

    def fake_showinfo(title, message, parent=None):
        dialog_log.append({'kind': 'showinfo', 'title': title, 'message': str(message)[:300]})
        return 'ok'

    def fake_showerror(title, message, parent=None):
        dialog_log.append({'kind': 'showerror', 'title': title, 'message': str(message)[:300]})
        return 'ok'

    def fake_askyesno(title, message, parent=None):
        dialog_log.append({'kind': 'askyesno', 'title': title, 'message': str(message)[:300], 'answer': True})
        return True

    def fake_askstring(title, prompt, parent=None):
        dialog_log.append({'kind': 'askstring', 'title': title, 'prompt': str(prompt)[:300], 'answer': 'QA Task'})
        return 'QA Task'

    mod.messagebox.showinfo = fake_showinfo
    mod.messagebox.showerror = fake_showerror
    mod.messagebox.askyesno = fake_askyesno
    mod.simpledialog.askstring = fake_askstring

    root = mod.tk.Tk()
    root.geometry('1300x820+0+0')
    root.title('Ascended Barron QA Smoke')
    dash = mod.Dashboard(root)

    results = []
    failures = []

    def run_step(name, fn, after=None):
        try:
            fn()
            settle(root, 0.35)
            if after:
                after()
                settle(root, 0.25)
            shot = capture_display(name)
            results.append({'step': name, 'status': 'ok', 'screenshot': shot})
        except Exception:
            failures.append({'step': name, 'traceback': traceback.format_exc()})
            results.append({'step': name, 'status': 'failed'})
        finally:
            settle(root, 0.1)

    run_step('01-welcome', lambda: dash.show_welcome())
    run_step('02-settings', lambda: dash.open_settings())
    run_step('03-eisenhower', lambda: dash.open_eisenhower())

    def select_first_task():
        if dash.eisen_lists and 'do_first' in dash.eisen_lists:
            lb = dash.eisen_lists['do_first']
            if lb.size() > 0:
                lb.selection_clear(0, 'end')
                lb.selection_set(0)
                dash._eisen_on_select('do_first')

    run_step('04-eisenhower-selected', lambda: None, after=select_first_task)
    run_step('05-eisenhower-add-dialog', lambda: dash._eisen_add())
    close_extra_toplevels(root)
    run_step('06-eisenhower-done', lambda: dash._eisen_done(), after=select_first_task)
    run_step('07-done-tasks-dialog', lambda: dash._eisen_show_done_tasks())
    close_extra_toplevels(root)
    run_step('08-app-archive-dialog', lambda: dash._archive_apps_dialog())
    close_extra_toplevels(root)
    run_step('09-app-pick-dialog', lambda: dash._app_pick())
    close_extra_toplevels(root)
    run_step('10-biglog-status', lambda: dash._biglog_test_now())

    report = {
        'display': os.environ.get('DISPLAY'),
        'results': results,
        'failures': failures,
        'dialog_log': dialog_log,
        'all_steps_passed': not failures,
    }
    (OUT_DIR / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    try:
        root.destroy()
    except Exception:
        pass

    print(json.dumps({'all_steps_passed': not failures, 'steps': len(results), 'failures': len(failures), 'output_dir': str(OUT_DIR)}, indent=2))
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
