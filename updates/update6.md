# Update 6 — Manifest hygiene and shipped-file discipline

Purpose:
Reduce the chance of forgetting to refresh `MANIFEST.sha256` after changing shipped files inside `airootfs`.

Why this matters:
This session found a real release blocker: shipped docs changed, but the manifest had not been regenerated yet.

Ground truth:
If shipped files under `airootfs/usr/local/share/ai-os/` or other managed paths change, regenerate:
- `airootfs/usr/local/share/ai-os/MANIFEST.sha256`

Current command:
```sh
./tools/gen-manifest.sh
```

Goals for a future session:
1. Identify exactly which paths are covered by the manifest and updater expectations.
2. Document when manifest regeneration is required.
3. Decide whether to add a repo note, helper script output warning, or CI check.
4. Optionally add a lightweight stale-manifest detection step.

Possible future improvements:
- pre-commit reminder script
- CI check that detects shipped-file changes without manifest changes
- release checklist item with explicit pass/fail

Caution:
- do not add complicated automation that becomes brittle
- a simple guard is better than a fancy one nobody trusts

Recommended next-session prompt:
Open `updates/update6.md` first. Audit how `MANIFEST.sha256` is used, document exactly when it must be regenerated, and propose the simplest reliable guard against stale manifest commits.

## Progress snapshot — 2026-06-16

What was completed in this session:

1. Audited how the manifest is actually used.
   - `tools/gen-manifest.sh` regenerates the committed manifest from the managed shipped-file roots.
   - `build.sh` regenerates the same manifest into the staged profile during ISO build.
   - `airootfs/usr/local/bin/ai-os-update` uses the shipped manifest to:
     - detect locally modified managed files before overwrite
     - remove managed files that were dropped in a newer release

2. Identified the real failure mode.
   - A stale committed `airootfs/usr/local/share/ai-os/MANIFEST.sha256` can be hidden by the build path because `build.sh` regenerates the manifest into the staged ISO anyway.
   - That means local source/history/review can still be wrong even when a build artifact ends up with a regenerated manifest.
   - So the guard needs to catch stale commits before or during review/CI, not only during release build staging.

3. Documented the exact managed roots covered by the manifest logic.
   - Included by the manifest generation logic:
     - `airootfs/usr/local/share/ai-os/**`
     - `airootfs/usr/local/lib/ai-os/**`
     - `airootfs/usr/local/bin/ai-os-*`
     - `airootfs/usr/local/bin/start-ai-os-*`
   - Excluded:
     - `INSTALLED_REV`
     - `INSTALLED_VERSION`
     - `MANIFEST.sha256`
     - `__pycache__`

4. Added the simplest reliable guard.
   - New local checker script:
     - `tools/check-manifest.sh`
   - Behavior:
     - regenerates the manifest into a temp file
     - compares it to the committed `MANIFEST.sha256`
     - exits non-zero with a diff if the committed manifest is stale
     - prints the refresh command:
       - `bash tools/gen-manifest.sh`

5. Added a lightweight CI check.
   - New workflow:
     - `.github/workflows/check-manifest.yml`
   - Runs on pull requests and pushes to `main` when the managed roots or manifest-tooling files change.
   - Calls:
     - `bash tools/check-manifest.sh`

6. Updated the release checklist to use the new guard.
   - `docs/RELEASE-CHECKLIST.md` now names the managed roots more explicitly and uses:
     - `bash tools/check-manifest.sh`
     - `bash tools/gen-manifest.sh`

### Verification completed

1. Syntax-checked the new checker:
   - `bash -n tools/check-manifest.sh`
2. Ran the checker locally:
   - `bash tools/check-manifest.sh`
   - result: `MANIFEST.sha256 is current.`
3. Confirmed the workflow file passed write-time YAML validation.

### Current status

The main goal of this track is now satisfied:
- the managed manifest scope is documented clearly
- the exact regeneration trigger is clearer
- there is now a simple local check and a simple CI guard against stale manifest commits

### Why this guard is the right size

This is intentionally small:
- one checker script
- one CI workflow
- no complicated inference about what a human "meant" to ship

That keeps the guard understandable and trustworthy while still catching the real mistake that already happened.