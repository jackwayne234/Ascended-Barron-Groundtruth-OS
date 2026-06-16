# Update 2 — Next-session plan: divide the dashboard monolith into modules

Date: 2026-06-15
Repo: Ascended-Barron-Groundtruth-OS
Primary target file: `airootfs/usr/local/share/ai-os/ai-os-dashboard.py`

## Purpose

The next session should focus on turning the large single-file dashboard into a modular structure.

Right now, the main dashboard file is the biggest technical risk in the repo. It is large, carries mixed responsibilities, and is the clearest long-term maintainability problem.

This next phase is not a branding pass. It is a structure pass.

Do not start by renaming `ai-os-dashboard.py`.
Do not start by changing product language.
Do not start by changing behavior unless needed to safely extract modules.

The first goal is to split responsibilities while preserving behavior.

## Ground rules for the next session

1. Preserve behavior first.
   - No feature redesign unless necessary.
   - No UI rewrite.
   - No workflow-story rewrite.

2. Make small safe moves.
   - Extract code in slices.
   - Verify after each extraction.

3. Keep naming conservative for now.
   - The current internal `ai-os-*` namespace can stay during the split.
   - Revisit naming only after the modular structure is stable.

4. Prefer low-risk separations first.
   - constants
   - helpers
   - logging helpers
   - task/store utilities
   - updater/status helpers
   - small UI sections

5. Do not break shipped paths casually.
   - The file is referenced by build scripts, NOTICE, sample docs, manifest, and internal window-matching logic.
   - Structural extraction is good. Abrupt path churn is not.

## Recommended first objective

Create a modular package structure under the same shipped area and start moving non-UI logic out of `ai-os-dashboard.py`.

A likely target structure could look like this:

```text
airootfs/usr/local/share/ai-os/
  ai-os-dashboard.py
  dashboard/
    __init__.py
    constants.py
    paths.py
    logging_utils.py
    settings.py
    battery.py
    tasks.py
    updates.py
    system_checks.py
    ui_helpers.py
```

This is a suggested direction, not a locked layout.

## Best extraction order

### Phase 1: inventory and boundaries
- Read `ai-os-dashboard.py`
- Identify major responsibility clusters
- Mark which sections are:
  - pure constants
  - filesystem/path config
  - logging/event writing
  - task storage / task loading
  - updater state and version checks
  - system status helpers
  - UI rendering helpers
  - app/screen classes and main app orchestration

Output wanted from this phase:
- a short module map
- a proposed extraction order

### Phase 2: extract safest code first
Start with modules least likely to change runtime behavior:
- constants / colors / fonts
- path constants
- tiny pure helpers
- battery/status formatting helpers
- logging helpers if they are not tightly coupled to widget state

After each extraction:
- run Python compile checks
- confirm imports still work

### Phase 3: extract state and store logic
Then move logic that handles:
- settings file paths / settings load-save
- task storage
- update-state helpers
- system status helpers

These are still lower risk than cutting through the main UI class too early.

### Phase 4: extract UI helper sections
Only after the helpers and stores are stable:
- extract reusable widget builders
- footer/header helper builders
- status badge helpers
- screen/subpanel helpers where practical

### Phase 5: decide whether to split the main app class
At that point, decide whether:
- one main app class should remain, with helpers imported from modules
or
- multiple screen/controller modules should be introduced

The answer should come from what the file looks like after phases 1–4, not from premature architecture taste.

## Things to inspect early in the next session

Search for:
- places where the file self-references its own name or path
- window matching logic using `ai-os-dashboard`
- places where updater/build scripts rely on the file path
- any assumptions about `__file__` location
- any functions with hidden coupling to tkinter widget state

Known areas already seen in this session:
- build script verifies `usr/local/share/ai-os/ai-os-dashboard.py`
- NOTICE mentions `ai-os-dashboard.py`
- shipped sample project points at the file path
- window-matching logic includes `ai-os-dashboard`

That means modularization should probably keep a small top-level launcher file in place while imports move underneath it.

## Recommended implementation pattern

Best likely pattern:
- keep `ai-os-dashboard.py` as the thin entrypoint for now
- move extracted logic into a sibling `dashboard/` package
- gradually reduce the main file until it becomes mostly startup + app wiring

That gives you:
- low path churn
- preserved build expectations
- cleaner internal organization
- freedom to rename later if desired

## Verification checklist for the next session

After each meaningful extraction, verify:
- `python3 -m py_compile` still passes
- shell/build helper syntax still passes if touched
- imports resolve from the shipped path layout
- no broken references to moved symbols
- manifest regenerated if shipped files change
- docs only updated if behavior/path changes actually require it

## Suggested next-session opening instruction

Use this as the opening instruction for the next session:

```text
Open `updates/update2.md` first and follow it. The goal is to start modularizing `airootfs/usr/local/share/ai-os/ai-os-dashboard.py` without changing user-facing behavior. Begin with an inventory of responsibility clusters and propose the safest extraction order, then start Phase 1 and Phase 2 with real file changes and verification.
```

## Expected outcome for the next session

A good next session should ideally produce:
- a module map
- an initial extracted package structure
- the first safe modules moved out
- the dashboard still compiling and behaving the same
- a clean summary of what was extracted and what remains

## Progress log — completed modularization work in this track

The work described above has now started and advanced well beyond the initial Phase 1/Phase 2 target.

### What was completed

1. Kept the shipped entrypoint path in place.
   - `airootfs/usr/local/share/ai-os/ai-os-dashboard.py` still exists at the same shipped path.
   - The build/update/startup assumptions that rely on that path were preserved.

2. Created a sibling modular package under the same shipped area.
   - Added `airootfs/usr/local/share/ai-os/dashboard/`

3. Extracted the following modules from the monolith:
   - `dashboard/__init__.py`
   - `dashboard/constants.py`
   - `dashboard/paths.py`
   - `dashboard/logging_utils.py`
   - `dashboard/system_checks.py`
   - `dashboard/tasks.py`
   - `dashboard/settings.py`
   - `dashboard/updates.py`
   - `dashboard/apps.py`
   - `dashboard/terminal_support.py`
   - `dashboard/connectivity.py`
   - `dashboard/weather_support.py`
   - `dashboard/x11_embed.py`
   - `dashboard/app_embed.py`
   - `dashboard/work_zone.py`
   - `dashboard/app_grid_actions.py`
   - `dashboard/eisenhower_actions.py`
   - `dashboard/panels.py`
   - `dashboard/ui_runtime.py`
   - `dashboard/ui_helpers.py`
   - `dashboard/weather_ui.py`
   - `dashboard/app_grid_ui.py`
   - `dashboard/eisenhower_ui.py`
   - `dashboard/settings_ui.py`

4. Extracted responsibility clusters now moved out of `ai-os-dashboard.py`:
   - palette/constants
   - path and environment helpers
   - logging helpers / BigLog status helpers
   - battery / CPU / RAM / disk helpers
   - task store and project-folder helpers
   - settings helpers
   - version/update helpers
   - app metadata/state helpers
   - terminal launch/X11 environment helpers
   - Wi-Fi status helper
   - weather-app loading/bootstrap helper
   - X11 embed/window helpers
   - app launch/embed orchestration helpers (`_app_launch_external`, `_raise_external_app_window`, `_embed_hunt`, `_embed_reparent`, `_embed_finalize`)
   - work-zone helpers (`open_setup_script`, `show_welcome`, centered message rendering)
   - app-grid interaction glue (`_builtin_apps`, `_builtin_by_key`, `_archive_builtin_key`, `_restore_builtin_key`, `_archive_apps_dialog`, `_draw_app_tiles`, `_app_remove`, `_app_pick`)
   - Eisenhower interaction glue (`open_eisenhower`, `_eisen_active`, `_eisen_refresh`, `_eisen_on_select`, `_eisen_need_sel`, `_eisen_quad_chooser`, `_eisen_add`, `_eisen_delete`, `_eisen_done`, `_eisen_select_task_by_id`, `_eisen_show_done_tasks`, `_eisen_move`)
   - screen/subpanel builders (`open_settings`, `_build_footer`)
   - runtime UI utility methods (`_wifi_tick`, `_resource_tick`, `_show_resource_details`, `_biglog_refresh`, `_biglog_test_now`, `_tick`, `_pick_timezone`, `_toggle_fs`, `_relayout`)
   - reusable UI helpers (`_flash`, popup prep, titled panel builder, resource-detail message formatting)
   - weather ticker rendering helpers
   - app-grid UI helpers (header actions, archiveable built-in filtering, add-app choice building, tile rendering)
   - Eisenhower UI helpers (action bar, quadrant grid construction, quadrant chooser, done-task filtering/rendering)
   - settings/update UI helpers (update banner rendering, settings updates panel construction)

5. Rewired imports so the launcher file now imports those extracted modules.

6. Moved the app launch/embed orchestration block out of the `Dashboard` class body.
   - Added `dashboard/app_embed.py`
   - Left thin wrapper methods in `ai-os-dashboard.py` so the class interface stays stable while the shipped launcher path remains unchanged.

7. Moved the setup-script / welcome-pane work-zone slice out of the `Dashboard` class body.
   - Added `dashboard/work_zone.py`
   - Left thin wrapper methods in `ai-os-dashboard.py` for `open_setup_script()` and `show_welcome()` so call sites and shipped behavior stay stable.

8. Moved the app-grid interaction glue slice out of the `Dashboard` class body.
   - Added `dashboard/app_grid_actions.py`
   - Left thin wrapper methods in `ai-os-dashboard.py` for the built-in app map, archive/restore flow, app-grid redraw, app removal, and add-app picker so call sites and shipped behavior stay stable.

9. Moved the Eisenhower interaction glue slice out of the `Dashboard` class body.
   - Added `dashboard/eisenhower_actions.py`
   - Left thin wrapper methods in `ai-os-dashboard.py` for the task-board open/select/add/delete/done/restore/move flow so call sites and shipped behavior stay stable.

10. Moved the remaining screen/subpanel builder slice out of the `Dashboard` class body.
   - Added `dashboard/panels.py`
   - Left thin wrapper methods in `ai-os-dashboard.py` for `open_settings()` and `_build_footer()` so call sites and shipped behavior stay stable.

11. Moved the remaining runtime UI utility slice out of the `Dashboard` class body.
   - Added `dashboard/ui_runtime.py`
   - Left thin wrapper methods in `ai-os-dashboard.py` for Wi-Fi/resource/BigLog/clock/timezone/fullscreen/relayout behavior so call sites and shipped behavior stay stable.

12. Regenerated `airootfs/usr/local/share/ai-os/MANIFEST.sha256` after shipped-file changes.

### Verification completed during this work

After each major extraction pass, the following checks were run successfully:
- `python3 -m py_compile` on `ai-os-dashboard.py` and the extracted dashboard modules
- runtime smoke checks via `runpy.run_path('ai-os-dashboard.py', ...)`
- manifest refresh via `bash tools/gen-manifest.sh`

Observed result:
- the dashboard still imports successfully
- extracted helpers resolve correctly from the shipped path layout
- no shipped-path churn was introduced

### Coupling risks confirmed and preserved

These earlier warnings were confirmed correct and were respected during the work:
- `build.sh` verifies `usr/local/share/ai-os/ai-os-dashboard.py`
- `ai-os-update` expects that dashboard path to exist
- startup scripts execute that dashboard path directly
- window-matching logic still includes `ai-os-dashboard`
- `__file__`/path behavior mattered enough that keeping the top-level launcher was the right pattern

### Current status after this progress

The non-UI helper/state/support layers have been substantially extracted.

The app launch/embed orchestration slice has now also been moved out of the main class body into `dashboard/app_embed.py`, while keeping `ai-os-dashboard.py` as the shipped launcher and preserving the existing `Dashboard` method surface through thin delegating wrappers.

The setup-script / welcome-pane work-zone slice has now also been moved out into `dashboard/work_zone.py`, again keeping the launcher path stable and preserving the existing `Dashboard` method surface through thin delegating wrappers.

The app-grid interaction glue slice has now also been moved out into `dashboard/app_grid_actions.py`, again keeping the launcher path stable and preserving the existing `Dashboard` method surface through thin delegating wrappers.

The Eisenhower interaction glue slice has now also been moved out into `dashboard/eisenhower_actions.py`, again keeping the launcher path stable and preserving the existing `Dashboard` method surface through thin delegating wrappers.

The remaining screen/subpanel builder slice has now also been moved out into `dashboard/panels.py`.

The remaining runtime UI utility slice has now also been moved out into `dashboard/ui_runtime.py`.

At this point, the planned slice-based modularization track described in this note has been completed. The launcher still exists at the shipped path, but it is now much thinner and mostly acts as bootstrap + wiring.

What remains is optional follow-on cleanup rather than one of the previously planned extraction slices:
- decide whether to keep one main `Dashboard` class or split controller/screen responsibilities further
- prune now-unused imports/helpers from `ai-os-dashboard.py`
- do a behavior-focused live QA pass after the structural split

### Recommended next step from here

The originally planned extraction slices are complete.

Best next steps from here are optional follow-on cleanup / verification:
1. run a behavior-focused live QA pass against the dashboard after the structural split
2. prune now-unused imports/helpers from `ai-os-dashboard.py`
3. decide whether the thinner launcher should stay as one `Dashboard` class or be split further only if live behavior stays stable

## Next-session handoff note

Start the next session by opening this file first.

Current ground truth:
- `airootfs/usr/local/share/ai-os/ai-os-dashboard.py` is still the shipped entrypoint and must stay in place for now.
- The following helper/UI modules have already been extracted under `airootfs/usr/local/share/ai-os/dashboard/`:
  - constants / paths / logging / system checks
  - tasks / settings / updates / apps
  - terminal support / connectivity / weather support / x11 embed
  - app embed / work zone / app-grid actions / Eisenhower actions / panels / ui runtime / ui helpers / weather UI / app-grid UI / Eisenhower UI / settings UI
- `MANIFEST.sha256` has been refreshed after these shipped-file changes.

Primary next target:
- the planned slice-based modularization track is complete
- optional follow-on work now is:
  - behavior-focused live QA after the structural split
  - pruning now-unused imports/helpers from `ai-os-dashboard.py`
  - only then deciding whether to split the thinner launcher further

Rules for the next session:
1. preserve user-facing behavior
2. do not rename `ai-os-dashboard.py`
3. keep the top-level shipped path stable
4. make small safe moves only
5. update this file with real progress before stopping

Required verification after each meaningful extraction:
- `python3 -m py_compile airootfs/usr/local/share/ai-os/ai-os-dashboard.py airootfs/usr/local/share/ai-os/dashboard/*.py`
- runtime smoke check using `runpy.run_path('ai-os-dashboard.py', ...)`
- `bash tools/gen-manifest.sh`

## Progress log — live laptop / window-manager QA after modularized payload sync

Date: 2026-06-16
Target laptop: `192.168.50.11`

Ground-truth checks completed on the live laptop after the modularized payload was copied over:

1. Runtime/process state after live patch
   - SSH reachable as `root`.
   - Remote dashboard SHA still matches local verified SHA:
     - `833bbfc14fd40debd8cf1588b2b1892317d7b279a57c108521da943c192b6f74`
   - Remote module directory exists and contains 24 files under `/usr/local/share/ai-os/dashboard/`.
   - Remote compile check passed:
     - `python3 -m py_compile /usr/local/share/ai-os/ai-os-dashboard.py /usr/local/share/ai-os/dashboard/*.py`
   - X/Openbox/dashboard were all running on the laptop:
     - `Xorg`
     - `openbox`
     - `python3 /usr/local/share/ai-os/ai-os-dashboard.py`
   - `ai-os-dashboard.service` was not the thing currently keeping the dashboard alive during this pass.
     - `systemctl is-active ai-os-dashboard.service` returned inactive
     - `journalctl -u ai-os-dashboard.service -b` had no entries
   - The live dashboard process was running as user `barron` on `DISPLAY=:0`.

2. Dashboard/background-layer live X11 state
   - Live dashboard top-level window was present and identifiable as Tk:
     - `WM_NAME = "Ascended Barron"`
     - `WM_CLASS = "tk", "Tk"`
   - Live window type was correct:
     - `_NET_WM_WINDOW_TYPE_DESKTOP`
   - But the live `_NET_WM_STATE` was not the full expected desktop/background set.
     - Observed: `_NET_WM_STATE_FULLSCREEN`
     - Not observed during this pass: `_NET_WM_STATE_BELOW`, `_NET_WM_STATE_SKIP_TASKBAR`, `_NET_WM_STATE_SKIP_PAGER`
   - This means the dashboard is not yet proving the full true-background EWMH state on the live laptop, even though its type is `DESKTOP`.

3. Tooling available / missing on the live laptop
   - Present: `xprop`, `python3`, `lxterminal`, `xterm`
   - Missing: `xdotool`, `wmctrl`, `xwininfo`
   - Attempting a minimal `pacman -Sy --noconfirm xdotool` install was blocked by the live package-trust state:
     - `warning: Public keyring not found; have you run 'pacman-key --init'?`
     - `error: keyring is not writable`
   - So this pass adapted to the already-present tools instead of mutating package trust just for QA.

4. Visible app/window launch behavior verified live
   - Launching a normal terminal window under the live X session produced a separate visible top-level window:
     - `WM_CLASS = "lxterminal", "Lxterminal"`
     - `_NET_WM_WINDOW_TYPE_NORMAL`
   - After launch, that terminal became the active window:
     - `_NET_ACTIVE_WINDOW` moved to the terminal window id
   - The dashboard remained a separate `Tk` desktop-typed window underneath it.

5. Real dashboard UI controls exercised live via Tk send (no fake source-only test)
   - The live dashboard widget tree was introspected directly from the running Tk app on `DISPLAY=:0`.
   - The footer `⚙ Settings` button was found and invoked on the live dashboard.
   - The live Settings/Updates panel was confirmed present after invocation, including:
     - `Settings`
     - `Updates`
     - `Current version:  v1.1.2`
     - `Check for updates now`
     - `Update OS`
     - `Undo last update`

6. Real Settings → Update OS behavior verified live
   - The live `Update OS` button was found by visible text and invoked from the running dashboard.
   - Result on the laptop:
     - a new `lxterminal` window opened
     - it became the active window
     - it was a normal top-level X window above the dashboard
     - the updater process started:
       - `lxterminal --title=Ascended Barron -e bash -lc 'if [ -x /usr/local/bin/ai-os-update ]; then /usr/local/bin/ai-os-update; ...'`
       - `/usr/local/bin/ai-os-update`
       - re-exec temp copy `/tmp/ai-os-update.*`
   - So the real Settings → Update OS path is visibly launching on the live laptop.

7. Focus/stacking conclusion from this pass
   - The good news:
     - normal app windows launch visibly above the dashboard
     - the real Settings button exists and opens the live Updates panel
     - the real `Update OS` button launches a visible active terminal window on the laptop
   - Remaining concern:
     - the dashboard background helper’s click/focus restore path is gated on `xdotool`, and `xdotool` is absent on the live laptop
     - the live dashboard window also did not show the expected `BELOW/SKIP_TASKBAR/SKIP_PAGER` states during this pass
   - A programmatic Settings invocation while a terminal window was open did not by itself steal `_NET_ACTIVE_WINDOW`, but that is not the same as a physical mouse-click test.
   - Therefore this pass confirms launch/update visibility, but does not fully clear the physical click/focus regression risk on the live laptop while `xdotool` is absent and the dashboard EWMH state is incomplete.

## Progress log — live patch to reduce xdotool dependence and remove fullscreen WM state

Date: 2026-06-16
Target laptop: `192.168.50.11`

Follow-on live patch completed after the QA note above.

1. Source/live patch applied
   - Patched `airootfs/usr/local/share/ai-os/ai-os-dashboard.py`
   - New dashboard SHA after patch:
     - local: `194b6bddcac8ba97512fc0d908e2180f2318ee12cd93f93875ce7db2c2bc0a0d`
     - live laptop: `194b6bddcac8ba97512fc0d908e2180f2318ee12cd93f93875ce7db2c2bc0a0d`
   - Refreshed `airootfs/usr/local/share/ai-os/MANIFEST.sha256`

2. What changed
   - The dashboard background helper no longer depends on `xdotool` just to discover the real openbox-managed Tk top-level window.
   - It now falls back to the X11 client list via `xprop` and always tries `root.lower()` when re-applying desktop/background behavior.
   - The click/focus restore hook now still re-applies desktop/background lowering even when `xdotool` is absent.
   - The dashboard launcher logic no longer forces WM fullscreen state when the dashboard is meant to act as a desktop/background layer; it still sizes to the real screen.

3. Required verification completed after the patch
   - `python3 -m py_compile airootfs/usr/local/share/ai-os/ai-os-dashboard.py airootfs/usr/local/share/ai-os/dashboard/*.py`
   - runtime smoke check via `runpy.run_path('ai-os-dashboard.py', run_name='smoke')`
   - `bash tools/gen-manifest.sh`
   - live laptop copy installed over SSH and relaunched

4. Live X11 result after relaunch
   - Dashboard still appears as:
     - `WM_NAME = "Ascended Barron"`
     - `WM_CLASS = "tk", "Tk"`
     - `_NET_WM_WINDOW_TYPE_DESKTOP`
   - Important improvement:
     - `_NET_WM_STATE` is now empty instead of `FULLSCREEN`
   - So the patch successfully removed the fullscreen WM state that was fighting desktop/background behavior.
   - Openbox still did not show explicit `BELOW/SKIP_TASKBAR/SKIP_PAGER` atoms in the observed property dump, but the dashboard is now a desktop-typed window without fullscreen state.

5. Live behavior result after relaunch
   - Real Settings → Update OS still opens a visible `lxterminal` window above the dashboard and starts the updater.
   - With another normal terminal window already open, invoking the real live `⚙ Settings` button did not steal `_NET_ACTIVE_WINDOW`; the normal app window stayed active and stacked above the dashboard.

6. Remaining truth after this patch
   - This patch improved the live laptop state materially:
     - no forced fullscreen WM state on the dashboard
     - less dependence on `xdotool` for background-layer correctness
     - launch/update visibility still works after the patch
     - Settings invocation still does not yank focus from an already active normal window in the synthetic live test
   - `xdotool` is still absent on the laptop, so the stronger raise/activate path for restoring a previously focused normal window is still unavailable there.
   - A real physical mouse-click retest on the laptop is still the acceptance gate for the exact gesture Christopher reported earlier.

## Progress log — Open Project Terminal live fix

Date: 2026-06-16
Target laptop: `192.168.50.11`

Christopher reported: selecting `test task` and pressing `Open Project Terminal` did not open a terminal window.

1. Root cause found
   - `open_selected_project_terminal()` calls `_project_terminal_shell_command(folder)`.
   - That helper used `safe_folder_name(folder.name)`.
   - `safe_folder_name` had been moved into `dashboard/tasks.py` during modularization, but `ai-os-dashboard.py` was still using it without importing it.
   - Result: the button handler could update the project files/folder, then crash before launching the terminal.

2. Fix applied
   - Added `safe_folder_name` back to the `from dashboard.tasks import (...)` import list in `airootfs/usr/local/share/ai-os/ai-os-dashboard.py`.

3. Verification completed
   - local compile passed:
     - `python3 -m py_compile airootfs/usr/local/share/ai-os/ai-os-dashboard.py airootfs/usr/local/share/ai-os/dashboard/*.py`
   - live dashboard patched and relaunched
   - live dashboard hash after fix:
     - `223f784453b4a002a90745cfcd7beb3c448e8a949216a49be3a9324d79b5e141`
   - exact launcher path was then verified on the laptop using the same dashboard code path:
     - a real `lxterminal` normal window appeared above the dashboard
     - a new transcript file was created under `/home/barron/.local/share/ai-os/big-log/sessions/`
     - observed example: `20260616-050851-test task.log`

4. Cleanup
   - A leftover Tk messagebox from automation was closed so the live dashboard returned to a clean state.

## Progress log — storage label changed from percent to free gigabytes

Date: 2026-06-16
Target laptop: `192.168.50.11`

Christopher requested that the footer resource label show storage in gigabytes instead of a percentage.

1. What changed
   - The footer resource label now shows free storage in gigabytes:
     - from `Storage 3%`
     - to `Storage free 107.1G` on the live laptop at verification time
   - Warning colors still use underlying used-percent thresholds, so the color behavior did not get weaker just because the visible text changed.
   - The resource details popup was updated to keep both views:
     - visible free gigabytes
     - used percent and total size in the details text

2. Files patched
   - `airootfs/usr/local/share/ai-os/dashboard/system_checks.py`
   - `airootfs/usr/local/share/ai-os/dashboard/ui_runtime.py`
   - `airootfs/usr/local/share/ai-os/dashboard/ui_helpers.py`

3. Verification completed
   - local compile passed:
     - `python3 -m py_compile airootfs/usr/local/share/ai-os/ai-os-dashboard.py airootfs/usr/local/share/ai-os/dashboard/*.py`
   - patched files were copied to the live laptop and the dashboard relaunched
   - live file hashes matched local for the three patched dashboard modules
   - live footer text was read directly from the running Tk dashboard and showed:
     - `CPU 0%  •  RAM avail 6.8G  •  Storage free 107.1G`

## Final acceptance snapshot — all changes logged for this pass

Date: 2026-06-16
Target laptop: `192.168.50.11`

Christopher confirmed: `everything looks good` after the live fixes in this pass.

Accepted live state at the end of this pass:

1. Dashboard/window-manager state
   - Dashboard remains a Tk window with:
     - `WM_NAME = "Ascended Barron"`
     - `WM_CLASS = "tk", "Tk"`
     - `_NET_WM_WINDOW_TYPE_DESKTOP`
   - The dashboard no longer carries `_NET_WM_STATE_FULLSCREEN` on the live openbox laptop.
   - Settings invocation and normal app windows no longer showed the earlier obvious focus/stacking failure in the verified live checks.

2. Launch/update/task-work behavior
   - Real `Settings → Update OS` opens a visible `lxterminal` window above the dashboard and starts the updater.
   - `Open Project Terminal` now works again for selected tasks.
   - Project-terminal transcript capture is active under `/home/barron/.local/share/ai-os/big-log/sessions/`.

3. Footer resource text
   - Footer resource text now shows storage as free gigabytes instead of percent.
   - Verified live footer example:
     - `CPU 0%  •  RAM avail 6.8G  •  Storage free 107.1G`

4. Canonical source files changed during this pass
   - `airootfs/usr/local/share/ai-os/ai-os-dashboard.py`
   - `airootfs/usr/local/share/ai-os/dashboard/system_checks.py`
   - `airootfs/usr/local/share/ai-os/dashboard/ui_runtime.py`
   - `airootfs/usr/local/share/ai-os/dashboard/ui_helpers.py`
   - `airootfs/usr/local/share/ai-os/MANIFEST.sha256`
   - `updates/update2.md`

5. Final verified hashes
   - `ai-os-dashboard.py`
     - local/live: `223f784453b4a002a90745cfcd7beb3c448e8a949216a49be3a9324d79b5e141`
   - `dashboard/system_checks.py`
     - local/live: `c1e59eae02d12748395832ef00b95685c5fa02523cc08380bc161d081ddfc1dd`
   - `dashboard/ui_runtime.py`
     - local/live: `a1e89f58bdb5c6ff9570bf761ef5846a2b715e6d6ebf1f9a8b749c7aecaf4a8e`
   - `dashboard/ui_helpers.py`
     - local/live: `1791101624ceb833d783e1e842f09ed3fc258f0bdc8eb6cd6663519935f3c703`
   - `MANIFEST.sha256`
     - local: `7ebaf9780daf055dbba867ae19a655b359f5b066008fbd75fd5ab00a15f68ac6`

6. Scope note
   - This file now includes the modularization progress already completed earlier, the live QA findings, the background/fullscreen fix, the `Open Project Terminal` fix, the storage-label change, and the final accepted live state for this pass.

## Follow-up verification note — stronger remote live retest after acceptance snapshot

Date: 2026-06-16
Target laptop: `192.168.50.11`

A follow-up remote live retest was completed while preparing the next release.

What was verified live:
- the dashboard was still running as a Tk desktop window on `DISPLAY=:0`
- launching a normal `lxterminal` window still created a separate `_NET_WM_WINDOW_TYPE_NORMAL` window above the dashboard
- invoking the real live `⚙ Settings` button through Tk send while that terminal window remained open still produced the expected Settings/Updates controls
- after that invocation, both windows were still present:
  - dashboard: `WM_CLASS = "tk", "Tk"`, `_NET_WM_WINDOW_TYPE_DESKTOP`
  - terminal: `WM_CLASS = "lxterminal", "Lxterminal"`, `_NET_WM_WINDOW_TYPE_NORMAL`

Scope limit:
- this was a stronger remote live retest, but it was still not a literal human physical mouse-click test on the laptop hardware
- so it materially reduced uncertainty again, but direct physical click behavior is only proven if Christopher re-tests that exact gesture on-device
