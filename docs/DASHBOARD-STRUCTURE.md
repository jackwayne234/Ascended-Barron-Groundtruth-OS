# Dashboard structure

Purpose:
Document the post-modularization dashboard layout so release verification and future cleanup can refer to real module boundaries instead of treating the dashboard as one giant file.

## Ground rule

Keep `airootfs/usr/local/share/ai-os/ai-os-dashboard.py` as the shipped entrypoint for now.
It is still the stable path used by build/update/startup flows.
The modularized support code lives under `airootfs/usr/local/share/ai-os/dashboard/`.

## Current structure

Entrypoint:
- `airootfs/usr/local/share/ai-os/ai-os-dashboard.py`
  - bootstraps Tk
  - owns the `Dashboard` class
  - wires imported helpers/modules together
  - should stay thin compared with the old monolith

Support package:
- `airootfs/usr/local/share/ai-os/dashboard/__init__.py`
  - package marker
- `dashboard/constants.py`
  - palette, fonts, shared visible constants
- `dashboard/paths.py`
  - stable paths and environment-sensitive file locations
- `dashboard/logging_utils.py`
  - event/log writing helpers and BigLog status helpers
- `dashboard/system_checks.py`
  - battery, CPU, RAM, disk, and similar machine-status helpers
- `dashboard/tasks.py`
  - task storage, project-folder helpers, and bundled ground-truth helpers
- `dashboard/settings.py`
  - settings load/save helpers
- `dashboard/updates.py`
  - version parsing and update-state helpers
- `dashboard/apps.py`
  - app-slot metadata and app availability helpers
- `dashboard/terminal_support.py`
  - terminal discovery and X11 environment helpers
- `dashboard/connectivity.py`
  - Wi-Fi/connectivity helpers
- `dashboard/weather_support.py`
  - weather app bootstrap helpers
- `dashboard/x11_embed.py`
  - window listing/class checks and embed eligibility helpers
- `dashboard/background_layer.py`
  - desktop/background window-layer behavior and event-driven focus/stack restore helpers
- `dashboard/app_embed.py`
  - external-app launch/embed/reparent/focus helpers
- `dashboard/work_zone.py`
  - welcome/setup-script work-zone helpers
- `dashboard/app_grid_actions.py`
  - app-grid behavior and built-in app archive/restore/add/remove flows
- `dashboard/eisenhower_actions.py`
  - task-board selection/add/delete/done/move helpers
- `dashboard/panels.py`
  - screen/subpanel builders such as Settings and footer wiring
- `dashboard/ui_runtime.py`
  - recurring runtime UI ticks, status refreshes, timezone/fullscreen/layout helpers
- `dashboard/ui_helpers.py`
  - reusable popup/panel/status helper functions
- `dashboard/weather_ui.py`
  - forecast/ticker rendering helpers
- `dashboard/app_grid_ui.py`
  - app-grid header/tile rendering helpers
- `dashboard/eisenhower_ui.py`
  - Eisenhower board rendering helpers
- `dashboard/settings_ui.py`
  - settings/update banner rendering helpers

## Verification implications after modularization

The dashboard can no longer be treated as a single-file compile check.
A meaningful guard now needs to verify both:
1. the launcher still imports the module package correctly
2. the modularized dashboard still boots through a real Tk/X smoke pass

Current repo guard:
- `tools/check-dashboard-integrity.sh`
  - compiles `ai-os-dashboard.py` plus every `dashboard/*.py` module
  - runs `xvfb-run -a python3 qa/dashboard_smoke.py`
- `.github/workflows/check-dashboard-integrity.yml`
  - runs that guard automatically when the launcher, dashboard package, or smoke harness changes

## Naming/path cleanup status

Do not rename `ai-os-dashboard.py` yet.
Do not churn shipped paths yet.
Now that the structure is documented and the smoke guard exists, future cleanup can be judged against real module boundaries instead of guesswork.

That future cleanup should only happen after:
1. the thinner launcher stays stable across real QA passes
2. the current shipped-path assumptions are intentionally updated together
3. the release-story docs are updated in the same pass if user-visible behavior changes

## Current decision on further splitting

Keep one main `Dashboard` class for now.

Reason:
- the post-modularization release has now been built, updated on a real laptop, and accepted in real use
- the current launcher has been reduced further by moving the background-layer behavior into `dashboard/background_layer.py`
- there is not yet evidence that another controller/screen split would buy enough clarity to justify more churn in shipped paths and method wiring

Revisit this only if a future change shows one of these concrete problems:
- repeated merge conflicts inside the same remaining `Dashboard` methods
- a new feature that cuts across several screen areas and keeps forcing wide launcher edits
- a bugfix that is hard to verify because one remaining method still owns too many unrelated responsibilities

## Background window semantics status

The repo now treats background-window behavior as its own support slice in `dashboard/background_layer.py` instead of leaving that logic buried at the bottom of the launcher.

Current practical status:
- real release/update behavior is accepted on the laptop
- the dashboard still uses desktop/background hints plus an event-driven restore path
- explicit `_NET_WM_STATE_BELOW` / `SKIP_TASKBAR` / `SKIP_PAGER` atoms were not treated as the sole release gate, because the user-facing behavior is now the stronger ground truth

If a future session reopens this topic, use real visible behavior as the gate first, then inspect EWMH/X11 details as supporting evidence
