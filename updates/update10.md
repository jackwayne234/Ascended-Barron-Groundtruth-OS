# Update 10 — Modularization support work after the dashboard split begins

Purpose:
Capture the follow-on release/repo work that becomes easier once `ai-os-dashboard.py` is no longer a monolith.

Why this matters:
The dashboard modularization is not just a code-quality project. It should also make release verification, smaller diffs, and safer review easier.

What this track was meant to answer:
- what release verification should change now that the dashboard has a real module package
- whether repo checks can become module-aware instead of treating the dashboard like one file
- whether internal docs should describe the new dashboard structure
- whether path/name cleanup should happen now or stay deferred

## Starting ground truth for this track

By the time this track opened, the modularization work from `updates/update2.md` was already complete enough that:
- `airootfs/usr/local/share/ai-os/ai-os-dashboard.py` remained the shipped launcher path
- the extracted support code lived under `airootfs/usr/local/share/ai-os/dashboard/`
- the dashboard smoke harness already existed at `qa/dashboard_smoke.py`
- release/process docs still mostly talked about compile checks, not module-aware dashboard verification
- there was no dedicated repo doc describing the post-split dashboard structure
- there was no dedicated CI guard focused on launcher + module package + smoke QA together

## Progress log — module-aware release/repo support added

Date: 2026-06-16

This session continued only the open post-modularization support track and completed the most obvious follow-on repo/release work.

### What was added

1. Added a module-aware dashboard verification guard.
   - New file: `tools/check-dashboard-integrity.sh`
   - It now verifies the modularized dashboard as one unit by:
     - confirming the shipped launcher still exists
     - confirming the `dashboard/` package still exists
     - compiling `ai-os-dashboard.py`
     - compiling every `dashboard/*.py` module
     - running the real smoke harness with `xvfb-run -a python3 qa/dashboard_smoke.py`

2. Added a dedicated CI workflow for dashboard-integrity checks.
   - New file: `.github/workflows/check-dashboard-integrity.yml`
   - It runs when the launcher, dashboard package, smoke harness, or the guard script changes.
   - It installs the smoke-test dependencies needed on GitHub Actions and then runs the dashboard-integrity guard.

3. Added an internal structure doc for the modularized dashboard.
   - New file: `docs/DASHBOARD-STRUCTURE.md`
   - It records the current launcher/package split and what each extracted module is responsible for.
   - It also explains why the repo now needs launcher + module + smoke verification instead of only a single-file compile command.

4. Updated release-process docs to use the new modular guard.
   - Updated `docs/RELEASE-CHECKLIST.md`
     - old single-file compile gate replaced with `bash tools/check-dashboard-integrity.sh`
   - Updated `docs/RELEASE-STORY-WORKFLOW.md`
     - added the modularization verification note so dashboard changes trigger the correct verification reflex

### Decision recorded in this track

1. Release verification should now be module-aware.
   - After the split, a bare `py_compile` line is not the best release/repo guard anymore.
   - The meaningful guard is: launcher exists + module package exists + launcher/modules compile + smoke harness boots and exercises the dashboard.

2. Internal docs should describe the new structure.
   - That is now handled by `docs/DASHBOARD-STRUCTURE.md`.
   - This gives future sessions a concrete module map instead of forcing them to rediscover the split from imports.

3. Path/name cleanup should still wait.
   - `ai-os-dashboard.py` remains the shipped launcher path.
   - No rename/path churn was done in this track.
   - Future cleanup should only happen after the thinner launcher stays stable across more live QA and after the build/update/startup assumptions are intentionally updated together.

## Verification completed in this track

The new module-aware guard was exercised for real.

Commands run successfully:

```sh
bash tools/check-dashboard-integrity.sh
```

Observed result:
- Python compile check passed for `ai-os-dashboard.py` and all `dashboard/*.py` modules
- the Xvfb smoke harness ran successfully
- smoke result reported:
  - `all_steps_passed: true`
  - `steps: 10`
  - `failures: 0`

## Outcome of this track

This update track is now complete.

It answered the open post-modularization support questions with real repo changes:
- release verification is now module-aware
- the dashboard structure is now documented
- CI now has a dedicated modular-dashboard guard
- path/name cleanup is explicitly deferred until stability justifies it

## Recommended next-session prompt

All currently logged update tracks are complete.

If you start a new track later, base it on a real current product need rather than reopening this one by default.
